"""Fail-closed recovery for missed tutorial FunCorn and infant toy 2000.

Run only while the Azrok core is stopped so its in-memory canonical cache
cannot race the recovery transaction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import azrok_server as server_module


KEY_RE = re.compile(r"^a([0-9a-f]+)_s([0-3])_c([0-9a-f]+)$")


def recover(
    state_dir: Path,
    key: str,
    *,
    expected_sha256: str,
    expected_revision: int,
    expected_currency: int,
    expected_active_aux: int,
    funcorn_credit: int,
    completed_aux: tuple[int, ...],
) -> dict:
    match = KEY_RE.fullmatch(key)
    if not match:
        raise ValueError("invalid account-scoped character key")
    path = state_dir / f"{key}_state_v1.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest().lower() != expected_sha256.lower():
        raise ValueError("canonical SHA-256 precondition failed")
    document = json.loads(raw.decode("utf-8"))
    if int(document.get("revision", -1)) != expected_revision:
        raise ValueError("canonical revision precondition failed")
    if int(document.get("currency", -1)) != expected_currency:
        raise ValueError("FunCorn precondition failed")
    rows = document.get("runtime_rows") or []
    if not any(
        int(row.get("kind", 0xFF)) == 5
        and int(row.get("aux", 0xFF)) == expected_active_aux
        for row in rows
    ):
        raise ValueError("active tutorial row precondition failed")
    inventory = document.get("inventory") or {}
    toys = inventory.get("toy")
    if not isinstance(toys, list) or len(toys) != 10 or int(toys[0]) != 0:
        raise ValueError("toy2000 recovery precondition failed")

    server = server_module.AzrokServer.__new__(server_module.AzrokServer)
    account_hex, slot_text, character_hex = match.groups()
    server.proto_state = {
        "account_raw": bytes.fromhex(account_hex),
        "character_slot": int(slot_text),
        "char_name_raw": bytes.fromhex(character_hex),
        "client_0005_seen": True,
        "selected_character_key": key,
        "selected_evolution": 0,
    }
    server.state_store_dir = str(state_dir)
    server.saved_character_states = {}
    server.saved_server_states = {}
    server._add_event = lambda *args, **kwargs: None
    server._entity_id_for_proto_state = lambda _state: None

    state = server._load_canonical_character_state(key=key)
    working = json.loads(json.dumps(state))
    working["inventory"]["toy"][0] = 1
    working["currency"] = expected_currency + funcorn_credit
    completed = list(working.get("completed_runtime_rows") or [])
    for aux in completed_aux:
        completion_key = f"g1:r0:k5:a{int(aux)}:c100"
        if completion_key in completed:
            raise ValueError("tutorial completion was already recovered")
        completed.append(completion_key)
    working["completed_runtime_rows"] = completed[-256:]
    if not server._save_canonical_character_state(
        working,
        key=key,
        mutation={
            "kind": "recover_missed_tutorial_onboarding",
            "request_opcode": "operator-recovery",
            "changed_fields": [
                "currency",
                "inventory.toy[0]",
                "completed_runtime_rows",
            ],
            "missed_tutorial_aux": list(completed_aux),
            "funcorn_credit": funcorn_credit,
        },
    ):
        raise RuntimeError("canonical recovery transaction failed")
    recovered = server._load_canonical_character_state(key=key)
    return {
        "revision": int(recovered["revision"]),
        "currency": int(recovered["currency"]),
        "toy2000": int(recovered["inventory"]["toy"][0]),
        "completed_count": len(recovered.get("completed_runtime_rows") or []),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-revision", type=int, required=True)
    parser.add_argument("--expected-currency", type=int, required=True)
    parser.add_argument("--expected-active-aux", type=int, required=True)
    parser.add_argument("--funcorn-credit", type=int, required=True)
    parser.add_argument("--completed-aux", type=int, nargs="+", required=True)
    args = parser.parse_args()
    result = recover(
        args.state_dir,
        args.key,
        expected_sha256=args.expected_sha256,
        expected_revision=args.expected_revision,
        expected_currency=args.expected_currency,
        expected_active_aux=args.expected_active_aux,
        funcorn_credit=args.funcorn_credit,
        completed_aux=tuple(args.completed_aux),
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
