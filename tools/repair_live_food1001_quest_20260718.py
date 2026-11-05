"""One-shot, fail-closed recovery for the captured food1001 quest commit.

The old server durably committed the refrigerator decrement, ignored the
natural C2S 0012[40,2], and rejected the following C2S 0011 because the client
clears only the row kind and leaves aux/value stale.  The packet sequence and
the exact canonical preimage are preserved in run 20260718T200538_52232_e3b06bea.

This script accepts only that exact preimage, then uses the production atomic
state writer and durable transaction journal to finish the missing FunCorn
credit and row retirement once.  It is intentionally not a general migration.
"""

from __future__ import annotations

import hashlib
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import azrok_server  # noqa: E402


STATE_DIR = os.path.join(ROOT, "server_state", "profile_playable_v2")
KEY = "a706c61796572_s0_c417a726f6b31"
STATE_PATH = os.path.join(STATE_DIR, f"{KEY}_state_v1.json")
EXPECTED_SHA256 = "44e472bbf1d6a402dbb36bb6fef57498292134e089f56c58ab72595c9415a75f"
COMPLETION_KEY = "g1:r1:k0:a1001:c40"


def sha256_file(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main() -> int:
    actual_sha = sha256_file(STATE_PATH)
    if actual_sha != EXPECTED_SHA256:
        raise SystemExit(
            f"refusing recovery: canonical SHA changed: {actual_sha}"
        )

    server = azrok_server.AzrokServer.__new__(azrok_server.AzrokServer)
    server.state_store_dir = STATE_DIR
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

    state = server._load_canonical_character_state(key=KEY)
    exact_preimage = (
        int(state.get("revision", -1)) == 3
        and int(state.get("currency", -1)) == 950
        and int(state["inventory"]["food"][1]) == 0
        and state["runtime_rows"][1]
        == {"kind": 0, "aux": 1001, "value": 26073020}
        and int(state["runtime_row_meta"][1].get("generation", -1)) == 1
        and list(state.get("completed_runtime_rows") or []) == []
    )
    if not exact_preimage:
        raise SystemExit("refusing recovery: canonical semantic preimage changed")

    working = dict(state)
    working["runtime_rows"] = [dict(row) for row in state["runtime_rows"]]
    working["runtime_row_meta"] = [
        dict(meta) for meta in state["runtime_row_meta"]
    ]
    working["completed_runtime_rows"] = list(
        state.get("completed_runtime_rows") or []
    )
    working["currency"] = 990
    working["runtime_rows"][1] = {"kind": 0xFF, "aux": 0xFF, "value": 0}
    working["runtime_row_meta"][1] = {
        "generation": 0,
        "issued_evolution": int(
            state["runtime_row_meta"][1].get("issued_evolution", 0)
        ),
    }
    working["completed_runtime_rows"].append(COMPLETION_KEY)

    committed = server._save_canonical_character_state(
        working,
        key=KEY,
        mutation={
            "kind": "quest_reward_capture_recovery",
            "request_opcode": "0x0012+0x0011",
            "packet_seq": 342,
            "changed_fields": [
                "currency",
                "runtime_rows",
                "runtime_row_meta",
                "completed_runtime_rows",
            ],
            "capture_run": "20260718T200538_52232_e3b06bea",
            "reward_channel": 2,
            "funcorn_awarded": 40,
        },
    )
    if not committed:
        raise SystemExit("recovery atomic save failed")

    repaired = server._load_canonical_character_state(key=KEY)
    receipt = server.proto_state.get("last_mutation_transaction") or {}
    if not (
        int(repaired.get("revision", -1)) == 4
        and int(repaired.get("currency", -1)) == 990
        and repaired["runtime_rows"][1]
        == {"kind": 0xFF, "aux": 0xFF, "value": 0}
        and COMPLETION_KEY in repaired.get("completed_runtime_rows", [])
        and receipt.get("result") == "committed"
        and receipt.get("journal_status") == "durable"
    ):
        raise SystemExit("recovery postcondition verification failed")

    print(
        "recovery committed",
        f"revision={repaired['revision']}",
        f"funcorn={repaired['currency']}",
        f"sha256={sha256_file(STATE_PATH)}",
        f"transaction={receipt.get('transaction_id')}",
        f"journal={receipt.get('journal_status')}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
