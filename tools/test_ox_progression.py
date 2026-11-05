"""Durable OX result acceptance in isolated character stores."""

import os
import tempfile
import unittest

from azrok_ox_progression import (
    load_ox_progression, ox_info_projection, ox_preservation_ranking,
    record_ox_result,
)
from tools import test_server_contract_layers as contract_tests


def _selected(name):
    raw = name.encode('ascii')
    account = b'test'
    return {
        'client_0005_seen': True,
        'account_raw': account,
        'char_name_raw': raw,
        'character_slot': 0,
        'selected_character_key': f'a{account.hex()}_s0_c{raw.hex()}',
    }


class OxProgressionTests(unittest.TestCase):
    def test_two_players_repeated_finish_disconnect_and_restart(self):
        helper = contract_tests.OxMode2ContractTests()
        server = helper.make_server()
        with tempfile.TemporaryDirectory() as directory:
            server.state_store_dir = directory
            alice = _selected('Alice')
            bob = _selected('Bob')
            server.client_meta[helper.a]['proto_state'] = alice
            server.client_meta[helper.b]['proto_state'] = bob
            helper.enter_both(server)
            self.assertTrue(server.ox_prepare()[0])
            self.assertTrue(server.ox_open_question(
                question_index=0, duration_ms=1000, now=10.0,
            )[0])
            room = server.ox_rooms['default']
            room['answers'][2] = {
                'generation': room['generation'],
                'side': room['question']['correct_side'],
            }
            self.assertTrue(server.ox_tick(now=11.0)[0])
            self.assertEqual(
                ox_info_projection(directory, bob['selected_character_key'])['eliminations'],
                1,
            )
            self.assertFalse(server.ox_tick(now=11.0)[0])
            self.assertTrue(server.ox_finish()[0])
            self.assertFalse(server.ox_finish()[0])
            self.assertTrue(server._ox_remove_participant(helper.b))
            self.assertTrue(server._ox_remove_participant(helper.a))
            # A new process reads the same files; no in-memory cache is used.
            self.assertEqual(
                ox_info_projection(directory, alice['selected_character_key'])['wins'], 1,
            )
            self.assertEqual(
                ox_info_projection(directory, bob['selected_character_key'])['matches'], 1,
            )
            self.assertEqual(
                ox_info_projection(directory, alice['selected_character_key'])['points'], 1,
            )
            self.assertEqual(len(os.listdir(directory)), 2)
            ranking = ox_preservation_ranking(directory)
            self.assertEqual([row['wins'] for row in ranking], [1, 0])
            self.assertEqual([row['rank'] for row in ranking], [1, 2])

    def test_match_id_is_durable_idempotency_key(self):
        with tempfile.TemporaryDirectory() as directory:
            key = _selected('Alice')['selected_character_key']
            match_id = 'a' * 32
            self.assertTrue(record_ox_result(directory, key, match_id, 'won', 2))
            self.assertFalse(record_ox_result(directory, key, match_id, 'won', 2))
            self.assertEqual(len(load_ox_progression(directory, key)['results']), 1)
            self.assertEqual(ox_info_projection(directory, key)['gauge_denominator'], 1)
            self.assertEqual(ox_info_projection(directory, key)['gauge_numerator'], 1)

    def test_failed_persistence_does_not_emit_adjudication(self):
        helper = contract_tests.OxMode2ContractTests()
        server = helper.make_server()
        with tempfile.TemporaryDirectory() as directory:
            server.state_store_dir = directory
            server.client_meta[helper.a]['proto_state'] = _selected('Alice')
            server.client_meta[helper.b]['proto_state'] = _selected('Bob')
            helper.enter_both(server)
            self.assertTrue(server.ox_prepare()[0])
            self.assertTrue(server.ox_open_question(now=10.0, duration_ms=1000)[0])
            # A regular file cannot be used as a result-store directory.
            blocked = os.path.join(directory, 'blocked')
            with open(blocked, 'w', encoding='utf-8') as stream:
                stream.write('x')
            server.state_store_dir = blocked
            helper.emitted.clear()
            ok, _message = server.ox_tick(now=11.0)
            self.assertFalse(ok)
            self.assertEqual(server.ox_rooms['default']['phase'], 'question')
            self.assertEqual(helper.emitted, [])

    def test_character_delete_archives_ox_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            server = contract_tests.CanonicalStateContractTests().make_server(directory)
            key = 'a6163636f756e7441_s2_c417a726f6b31'
            with open(os.path.join(directory, key + '_state_v1.json'),
                      'w', encoding='utf-8') as stream:
                stream.write('{"schema_version":1}')
            record_ox_result(directory, key, 'b' * 32, 'won', 1)
            server.ox_pending_results = [(key, 'c' * 32, 'abandoned', 0)]
            server.proto_state['lobby_slots'] = {
                0: {'slot': 0, 'storage_slot': 2, 'name_hex': '417a726f6b31'},
            }
            self.assertTrue(server._archive_account_character_slot(0))
            self.assertEqual(server.ox_pending_results, [])
            server._ox_retry_pending_results()
            self.assertEqual(ox_info_projection(directory, key)['matches'], 0)
            archived = os.listdir(os.path.join(directory, 'deleted'))
            self.assertTrue(any(name.startswith(key + '_ox_v1.json.')
                                for name in archived))

    def test_abandonment_is_counted_without_win_point(self):
        helper = contract_tests.OxMode2ContractTests()
        server = helper.make_server()
        with tempfile.TemporaryDirectory() as directory:
            server.state_store_dir = directory
            alice = _selected('Alice')
            server.client_meta[helper.a]['proto_state'] = alice
            helper.enter_both(server)
            self.assertTrue(server.ox_prepare()[0])
            self.assertTrue(server.ox_open_question(now=10.0)[0])
            self.assertTrue(server._ox_remove_participant(helper.a))
            projection = ox_info_projection(directory, alice['selected_character_key'])
            self.assertEqual(projection['abandonments'], 1)
            self.assertEqual(projection['wins'], 0)
            self.assertEqual(projection['points'], 0)

    def test_disconnect_result_retries_after_store_recovers(self):
        helper = contract_tests.OxMode2ContractTests()
        server = helper.make_server()
        with tempfile.TemporaryDirectory() as directory:
            alice = _selected('Alice')
            server.client_meta[helper.a]['proto_state'] = alice
            server.state_store_dir = directory
            helper.enter_both(server)
            self.assertTrue(server.ox_prepare()[0])
            self.assertTrue(server.ox_open_question(now=10.0)[0])
            blocked = os.path.join(directory, 'blocked')
            with open(blocked, 'w', encoding='utf-8') as stream:
                stream.write('x')
            server.state_store_dir = blocked
            self.assertTrue(server._ox_remove_participant(helper.a))
            self.assertEqual(len(server.ox_pending_results), 1)
            server.state_store_dir = directory
            server.ox_auto_step(now=10.1)
            self.assertEqual(server.ox_pending_results, [])
            self.assertEqual(
                ox_info_projection(directory, alice['selected_character_key'])['abandonments'],
                1,
            )

    def test_win_points_cross_client_tier_display_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            key = _selected('Alice')['selected_character_key']
            for index in range(151):
                record_ox_result(directory, key, f'{index:032x}', 'won', 1)
            projected = ox_info_projection(directory, key)
            self.assertEqual(projected['wins'], 151)
            self.assertEqual(projected['points'], 151)
            self.assertEqual(projected['tier'], 2)


if __name__ == '__main__':
    unittest.main()
