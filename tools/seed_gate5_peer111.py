#!/usr/bin/env python3
"""Create the bounded Gate 5 peer profile without overwriting any character.

This is a local test-fixture provisioner, not a substitute for the original
character-creation packet path.  It uses the server's canonical save function
so the lobby sees an ordinary, durable per-account slot on the next login.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import azrok_server


ACCOUNT = b"peer111"
NAME = b"Player"
SLOT = 0
SPECIES = 0
KEY = f"a{ACCOUNT.hex()}_s{SLOT}_c{NAME.hex()}"


def make_server(state_dir: Path):
    server = azrok_server.AzrokServer.__new__(azrok_server.AzrokServer)
    server.state_store_dir = str(state_dir)
    server.saved_character_states = {}
    server.saved_server_states = {}
    server.proto_state = {
        "account_raw": ACCOUNT,
        "character_slot": SLOT,
        "char_name_raw": NAME,
        "char_type": SPECIES,
        "selected_character_key": KEY,
        "client_0005_seen": True,
    }
    server._add_event = lambda *args, **kwargs: None
    server._entity_id_for_proto_state = lambda _state: 0
    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, default=ROOT / "server_state")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    state_dir = args.state_dir.resolve()
    target = state_dir / f"{KEY}_state_v1.json"
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing Gate 5 peer state: {target}")
    if args.dry_run:
        print(f"would create {target}")
        return
    state_dir.mkdir(parents=True, exist_ok=True)
    server = make_server(state_dir)
    state = server._default_canonical_character_state()
    if not server._save_canonical_character_state(
        state,
        key=KEY,
        mutation={
            "kind": "gate5_peer_fixture_provision",
            "request_opcode": None,
            "packet_seq": None,
            "changed_fields": ["character", "snapshot_hex", "inventory"],
            "purpose": "separate-account Gate 5 browser multiplayer test",
        },
    ):
        raise SystemExit("Gate 5 peer fixture save failed")
    loaded = server._load_canonical_character_state(key=KEY)
    if (loaded.get("character") or {}).get("name_hex") != NAME.hex():
        raise SystemExit("Gate 5 peer fixture canonical readback failed")
    print(f"created Gate 5 peer fixture {target}")


if __name__ == "__main__":
    main()
