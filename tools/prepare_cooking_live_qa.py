"""Create a fail-closed isolated fixture for one natural cooking cycle.

The fixture starts with two tier-1 ingredients (item 1500), no cooked food,
and a caller-selected Toast proficiency (stat40).  ``--toast-success`` pins
stat40 to its verified first-tier maximum (40), so the original local success
check has a 100 percent success threshold.  The fixture also seeds kitchen
cleanliness (stat23) above the local foodmaker availability gate and retains
the source character's completed tutorial rows: the foodmaker is otherwise
correctly rejected by the client before any recipe callback.  It uses the
production canonical writer/journal and refuses to overwrite an existing
namespace.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import struct
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import azrok_server  # noqa: E402


KEY = "a706c61796572_s0_c417a726f6b31"
SOURCE = os.path.join(
    ROOT, "server_state", "profile_playable_v2", f"{KEY}_state_v1.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default="qa_cooking_clean_20260718")
    proficiency = parser.add_mutually_exclusive_group()
    proficiency.add_argument(
        "--stat40", type=int, default=5,
        help="Toast proficiency to seed (0..40; default: 5)",
    )
    proficiency.add_argument(
        "--toast-success", action="store_true",
        help="seed stat40=40, the verified first-tier maximum",
    )
    parser.add_argument(
        "--kitchen-cleanliness", type=int, default=80,
        help="seed stat23 (kitchen cleanliness) in 1..100; default: 80",
    )
    args = parser.parse_args(argv)
    namespace = args.namespace
    stat40 = 40 if args.toast_success else args.stat40
    kitchen_cleanliness = args.kitchen_cleanliness
    if not namespace or len(namespace) > 64 or not all(
        ch.isalnum() or ch in "_-" for ch in namespace
    ):
        raise SystemExit("namespace must match [A-Za-z0-9_-]{1,64}")
    if not 0 <= stat40 <= 40:
        raise SystemExit("stat40 must be within the verified first-tier range 0..40")
    if not 1 <= kitchen_cleanliness <= 100:
        raise SystemExit("kitchen cleanliness must be within 1..100")

    state_dir = os.path.join(ROOT, "server_state", namespace)
    target = os.path.join(state_dir, f"{KEY}_state_v1.json")
    if os.path.exists(target):
        raise SystemExit(f"refusing to overwrite existing QA canonical: {target}")
    os.makedirs(state_dir, exist_ok=True)

    with open(SOURCE, "r", encoding="utf-8") as handle:
        state = copy.deepcopy(json.load(handle))

    state["revision"] = 0
    state["inventory"]["food"] = [0] * 38
    state["inventory"]["ingredient"] = [2, 0, 0]

    snapshot = bytearray.fromhex(state["snapshot_hex"])
    if len(snapshot) != 196:
        raise SystemExit(f"unexpected source snapshot length: {len(snapshot)}")
    struct.pack_into("<H", snapshot, 0x0A + 40 * 2, stat40)
    struct.pack_into("<H", snapshot, 0x0A + 23 * 2, kitchen_cleanliness)
    stat_total = sum(
        struct.unpack_from("<H", snapshot, 0x0A + stat_id * 2)[0]
        for stat_id in range(0x1E, 0x42)
    )
    struct.pack_into("<I", snapshot, 0x96, stat_total & 0xFFFFFFFF)
    state["snapshot_hex"] = snapshot.hex()

    server = azrok_server.AzrokServer.__new__(azrok_server.AzrokServer)
    server.state_store_dir = state_dir
    server.saved_character_states = {}
    server.saved_server_states = {}
    server.proto_state = {
        "account_raw": b"player",
        "character_slot": 0,
        "char_name_raw": b"Azrok1",
        "selected_character_key": KEY,
        "client_0005_seen": True,
    }
    server._add_event = lambda *args, **kwargs: None
    server._entity_id_for_proto_state = lambda _state: 1

    committed = server._save_canonical_character_state(
        state,
        key=KEY,
        mutation={
            "kind": "qa_cooking_clean_seed",
            "request_opcode": None,
            "packet_seq": None,
            "changed_fields": [
                "inventory.food",
                "inventory.ingredient[0]",
                "snapshot_hex.stat40",
                "snapshot_hex.stat23",
                "source_runtime_rows_retained",
                "source_completed_runtime_rows_retained",
            ],
            "purpose": "natural cooking 0008/0007 persistence verification",
        },
    )
    if not committed:
        raise SystemExit("QA cooking seed atomic save failed")

    loaded = server._load_canonical_character_state(key=KEY)
    loaded_snapshot = bytes.fromhex(loaded["snapshot_hex"])
    receipt = server.proto_state.get("last_mutation_transaction") or {}
    valid = (
        loaded["inventory"]["ingredient"] == [2, 0, 0]
        and sum(loaded["inventory"]["food"]) == 0
        and struct.unpack_from("<H", loaded_snapshot, 0x0A + 40 * 2)[0] == stat40
        and struct.unpack_from("<H", loaded_snapshot, 0x0A + 23 * 2)[0]
        == kitchen_cleanliness
        and receipt.get("result") == "committed"
        and receipt.get("journal_status") == "durable"
    )
    if not valid:
        raise SystemExit("QA cooking seed postcondition verification failed")

    print(
        "qa cooking seed committed",
        f"namespace={namespace}",
        f"revision={loaded['revision']}",
        "ingredient1500=2",
        "food_sum=0",
        f"stat40={stat40}",
        f"stat23={kitchen_cleanliness}",
        f"transaction={receipt.get('transaction_id')}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
