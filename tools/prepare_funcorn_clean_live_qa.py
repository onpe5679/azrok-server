"""Create one isolated, fail-closed live fixture for the food/FunCorn quest.

This never edits the preservation profile.  It clones its known playable
shape into a new namespace, then uses the production atomic writer and
transaction journal to seed exactly FunCorn 950, hamburger 1, and one active
food-wish row.  Refuse to overwrite an existing canonical file.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import azrok_server  # noqa: E402


KEY = "a706c61796572_s0_c417a726f6b31"
SOURCE = os.path.join(
    ROOT,
    "server_state",
    "profile_playable_v2",
    f"{KEY}_state_v1.json",
)
DEFAULT_NAMESPACE = "qa_funcorn_clean_20260718"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--namespace",
        default=DEFAULT_NAMESPACE,
        help="isolated QA namespace; existing canonical files are never overwritten",
    )
    args = parser.parse_args(argv)
    namespace = args.namespace
    if not namespace or len(namespace) > 64 or not all(
        ch.isalnum() or ch in "_-" for ch in namespace
    ):
        raise SystemExit("namespace must match [A-Za-z0-9_-]{1,64}")
    state_dir = os.path.join(ROOT, "server_state", namespace)
    target = os.path.join(state_dir, f"{KEY}_state_v1.json")
    if os.path.exists(target):
        raise SystemExit(f"refusing to overwrite existing QA canonical: {target}")
    os.makedirs(state_dir, exist_ok=True)
    with open(SOURCE, "r", encoding="utf-8") as handle:
        state = json.load(handle)

    state = copy.deepcopy(state)
    state["revision"] = 0
    state["currency"] = 950
    state["inventory"]["food"][1] = 1
    state["runtime_rows"][1] = {
        "kind": 0,
        "aux": 1001,
        "value": 26073020,
    }
    state["runtime_row_meta"][1] = {
        "generation": 1,
        "issued_evolution": 1,
    }
    state["completed_runtime_rows"] = []

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
            "kind": "qa_funcorn_clean_seed",
            "request_opcode": None,
            "packet_seq": None,
            "changed_fields": [
                "currency",
                "inventory.food[1]",
                "runtime_rows[1]",
                "runtime_row_meta[1]",
                "completed_runtime_rows",
            ],
            "purpose": "natural 0014->0008->0012->0011->0007 live verification",
        },
    )
    if not committed:
        raise SystemExit("QA seed atomic save failed")

    server.saved_server_states = {}
    loaded = server._load_canonical_character_state(key=KEY)
    receipt = server.proto_state.get("last_mutation_transaction") or {}
    valid = (
        int(loaded.get("currency", -1)) == 950
        and int(loaded["inventory"]["food"][1]) == 1
        and loaded["runtime_rows"][1]
        == {"kind": 0, "aux": 1001, "value": 26073020}
        and loaded.get("completed_runtime_rows") == []
        and receipt.get("result") == "committed"
        and receipt.get("journal_status") == "durable"
    )
    if not valid:
        raise SystemExit("QA seed postcondition verification failed")
    print(
        "qa seed committed",
        f"namespace={namespace}",
        f"revision={loaded['revision']}",
        f"funcorn={loaded['currency']}",
        f"food1001={loaded['inventory']['food'][1]}",
        f"transaction={receipt.get('transaction_id')}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
