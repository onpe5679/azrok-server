from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import azrok_server as server_module
from tools.recover_tutorial_onboarding_state import recover


class TutorialOnboardingRecoveryTests(unittest.TestCase):
    def test_recovery_is_exact_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_text:
            temp_dir = Path(temp_dir_text)
            server = server_module.AzrokServer.__new__(server_module.AzrokServer)
            server.proto_state = {
                "account_raw": b"accountA",
                "character_slot": 0,
                "char_name_raw": b"Test",
                "client_0005_seen": True,
            }
            key = server._character_state_key()
            server.proto_state["selected_character_key"] = key
            server.state_store_dir = str(temp_dir)
            server.saved_character_states = {}
            server.saved_server_states = {}
            server._add_event = lambda *args, **kwargs: None
            server._entity_id_for_proto_state = lambda _state: None
            state = server._default_canonical_character_state()
            state["currency"] = 0
            state["inventory"]["toy"][0] = 0
            state["runtime_rows"][0] = {"kind": 5, "aux": 227, "value": 0}
            state["runtime_row_meta"][0] = {
                "generation": 1,
                "issued_evolution": 0,
            }
            self.assertTrue(server._save_canonical_character_state(state, key=key))
            path = Path(server._canonical_state_path(key))
            before_hash = hashlib.sha256(path.read_bytes()).hexdigest()

            result = recover(
                temp_dir,
                key,
                expected_sha256=before_hash,
                expected_revision=1,
                expected_currency=0,
                expected_active_aux=227,
                funcorn_credit=300,
                completed_aux=(212, 202, 203),
            )

            self.assertEqual(result["revision"], 2)
            self.assertEqual(result["currency"], 300)
            self.assertEqual(result["toy2000"], 1)
            self.assertEqual(result["completed_count"], 3)
            with self.assertRaises(ValueError):
                recover(
                    temp_dir,
                    key,
                    expected_sha256=before_hash,
                    expected_revision=1,
                    expected_currency=0,
                    expected_active_aux=227,
                    funcorn_credit=300,
                    completed_aux=(212, 202, 203),
                )


if __name__ == "__main__":
    unittest.main()
