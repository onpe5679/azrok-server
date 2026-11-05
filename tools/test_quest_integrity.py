"""Isolated packet-contract checks for quest state transitions."""

import contextlib
import io
import struct
import tempfile
import unittest

from tools import test_server_contract_layers as contracts


EMPTY = {'kind': 0xFF, 'aux': 0xFF, 'value': 0}


def rows_packet(rows):
    return struct.pack(
        '<10H10H10I',
        *[row['kind'] for row in rows],
        *[row['aux'] for row in rows],
        *[row['value'] for row in rows],
    )


class QuestIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = contracts.CanonicalStateContractTests().make_server(self.temp.name)

    def empty_state(self):
        state = self.server._load_canonical_character_state()
        state['runtime_rows'] = [dict(EMPTY) for _ in range(10)]
        state['runtime_row_meta'] = [
            {'generation': 0, 'issued_evolution': 0} for _ in range(10)
        ]
        state['completed_runtime_rows'] = []
        state['currency'] = 0
        self.assertTrue(self.server._save_canonical_character_state(state))
        return state

    def packet(self, opcode, payload, number):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.server._build_response(opcode, payload, pkt_num=number)

    def test_stage_zero_cannot_insert_ordinary_quest_then_credit(self):
        self.empty_state()
        rows = [dict(EMPTY) for _ in range(10)]
        rows[0] = {'kind': 1, 'aux': 31, 'value': 0}
        self.packet(0x0011, rows_packet(rows), 100)
        self.assertEqual('rejected', self.server.proto_state['last_runtime_rows_0011']['status'])
        self.packet(0x0012, struct.pack('<IB', 22, 2), 101)
        self.assertEqual('rejected', self.server.proto_state['last_quest_reward']['status'])
        state = self.server._load_canonical_character_state()
        self.assertEqual(0, state['currency'])
        self.assertEqual(EMPTY, state['runtime_rows'][0])

    def test_evolved_client_can_issue_valid_ordinary_quest(self):
        state = self.empty_state()
        snapshot = bytearray(0xC4)
        snapshot[5] = 1
        state['snapshot_hex'] = snapshot.hex()
        self.assertTrue(self.server._save_canonical_character_state(state))
        rows = [dict(EMPTY) for _ in range(10)]
        rows[0] = {'kind': 1, 'aux': 31, 'value': 26073020}
        self.packet(0x0011, rows_packet(rows), 100)
        self.assertEqual('committed', self.server.proto_state['last_runtime_rows_0011']['status'])
        self.assertEqual(rows[0], self.server._load_canonical_character_state()['runtime_rows'][0])

    def test_evolved_ordinary_quest_needs_native_packed_date(self):
        state = self.empty_state()
        snapshot = bytearray(0xC4)
        snapshot[5] = 1
        state['snapshot_hex'] = snapshot.hex()
        self.assertTrue(self.server._save_canonical_character_state(state))
        for value in (0, 26081325, 26130006):
            rows = [dict(EMPTY) for _ in range(10)]
            rows[0] = {'kind': 1, 'aux': 31, 'value': value}
            self.packet(0x0011, rows_packet(rows), 100 + value % 10)
            self.assertEqual('rejected', self.server.proto_state['last_runtime_rows_0011']['status'])
        self.assertEqual(EMPTY, self.server._load_canonical_character_state()['runtime_rows'][0])

    def test_captured_multirow_ordinary_issue_pattern_is_preserved(self):
        # 2026-07-22 native capture: kind3/aux1 coexists with locally
        # issued skill and food rows, then a kind2/aux1009 row appears.
        state = self.empty_state()
        snapshot = bytearray(0xC4)
        snapshot[5] = 1
        state['snapshot_hex'] = snapshot.hex()
        state['runtime_rows'][0] = {'kind': 3, 'aux': 1, 'value': 0}
        state['runtime_row_meta'][0] = {'generation': 1, 'issued_evolution': 1}
        self.assertTrue(self.server._save_canonical_character_state(state))
        rows = [dict(row) for row in state['runtime_rows']]
        additions = (
            {'kind': 1, 'aux': 33, 'value': 26080406},
            {'kind': 0, 'aux': 1001, 'value': 26080415},
            {'kind': 0, 'aux': 1003, 'value': 26080419},
            {'kind': 2, 'aux': 1009, 'value': 26080508},
        )
        for number, row in enumerate(additions, 1):
            rows[number] = row
            self.packet(0x0011, rows_packet(rows), 100 + number)
            self.assertEqual('committed', self.server.proto_state['last_runtime_rows_0011']['status'])
        self.assertEqual(rows, self.server._load_canonical_character_state()['runtime_rows'])

    def test_tutorial_cannot_skip_or_reissue_completed_step(self):
        state = self.empty_state()
        rows = [dict(EMPTY) for _ in range(10)]
        rows[0] = {'kind': 5, 'aux': 202, 'value': 0}
        self.packet(0x0011, rows_packet(rows), 100)
        self.assertEqual('rejected', self.server.proto_state['last_runtime_rows_0011']['status'])
        state['completed_runtime_rows'] = ['g1:r0:k5:a212:c100']
        self.assertTrue(self.server._save_canonical_character_state(state))
        rows[0] = {'kind': 5, 'aux': 212, 'value': 0}
        self.packet(0x0011, rows_packet(rows), 101)
        self.assertEqual('rejected', self.server.proto_state['last_runtime_rows_0011']['status'])

    def test_completed_tutorial_cannot_pay_again_from_another_slot(self):
        state = self.empty_state()
        state['completed_runtime_rows'] = ['g1:r0:k5:a212:c100']
        state['runtime_rows'][7] = {'kind': 5, 'aux': 212, 'value': 0}
        state['runtime_row_meta'][7]['generation'] = 2
        self.assertTrue(self.server._save_canonical_character_state(state))
        retired = [dict(row) for row in state['runtime_rows']]
        retired[7] = dict(EMPTY)
        self.packet(0x0011, rows_packet(retired), 100)
        self.packet(0x0012, struct.pack('<IB', 100, 2), 101)
        self.assertEqual('rejected', self.server.proto_state['last_quest_reward']['status'])
        final = self.server._load_canonical_character_state()
        self.assertEqual(0, final['currency'])
        self.assertEqual(state['runtime_rows'][7], final['runtime_rows'][7])

    def test_final_tutorial_reward_allows_adjacent_local_growth_aux_zero(self):
        state = self.empty_state()
        chain = (212, 202, 203, 227)
        state['completed_runtime_rows'] = [
            f'g1:r0:k5:a{aux}:c100' for aux in chain
        ]
        state['runtime_rows'][0] = {'kind': 5, 'aux': 201, 'value': 26092508}
        state['runtime_row_meta'][0]['generation'] = 1
        self.assertTrue(self.server._save_canonical_character_state(state))
        empty = [dict(EMPTY) for _ in range(10)]
        self.packet(0x0011, rows_packet(empty), 100)
        self.assertEqual('pending_0012', self.server.proto_state['last_runtime_rows_0011']['status'])
        ack = self.packet(0x0012, struct.pack('<IB', 100, 2), 101)
        self.assertIsNotNone(ack)
        proposed = [dict(EMPTY) for _ in range(10)]
        proposed[0] = {'kind': 3, 'aux': 0, 'value': 26092508}
        self.packet(0x0011, rows_packet(proposed), 102)
        self.assertEqual('committed', self.server.proto_state['last_runtime_rows_0011']['status'])
        final = self.server._load_canonical_character_state()
        self.assertEqual(proposed[0], final['runtime_rows'][0])
        self.assertEqual(100, final['currency'])
        before_growth = bytearray(0xC4)
        struct.pack_into('<H', before_growth, 0x0A + 2 * 2, 350)
        self.assertTrue(self.server._save_character_state_snapshot(before_growth))
        self.packet(0x0010, b'\x00\x01', 103)
        self.packet(0x0011, rows_packet(empty), 104)
        self.assertEqual('pending_0007', self.server.proto_state['last_runtime_rows_0011']['status'])
        after_growth = bytearray(before_growth)
        after_growth[5] = 1
        self.assertTrue(self.server._save_character_state_snapshot(after_growth))
        grown = self.server._load_canonical_character_state()
        self.assertEqual(1, bytes.fromhex(grown['snapshot_hex'])[5])
        self.assertEqual(EMPTY, grown['runtime_rows'][0])
        self.assertEqual(100, grown['currency'])
        restarted = contracts.CanonicalStateContractTests().make_server(self.temp.name)
        restored = restarted._load_canonical_character_state()
        self.assertEqual(1, bytes.fromhex(restored['snapshot_hex'])[5])
        self.assertEqual(100, restored['currency'])
        self.assertEqual(EMPTY, restored['runtime_rows'][0])

    def test_final_tutorial_growth_requires_immediately_prior_reward(self):
        state = self.empty_state()
        state['completed_runtime_rows'] = [
            f'g1:r0:k5:a{aux}:c100' for aux in (212, 202, 203, 227, 201)
        ]
        self.assertTrue(self.server._save_canonical_character_state(state))
        rows = [dict(EMPTY) for _ in range(10)]
        rows[0] = {'kind': 3, 'aux': 0, 'value': 26092508}
        self.packet(0x0011, rows_packet(rows), 200)
        self.assertEqual('rejected', self.server.proto_state['last_runtime_rows_0011']['status'])

    def test_reward_cannot_remove_unrelated_active_row(self):
        state = self.empty_state()
        state['runtime_rows'][0] = {'kind': 1, 'aux': 31, 'value': 1}
        state['runtime_rows'][1] = {'kind': 1, 'aux': 32, 'value': 1}
        state['runtime_row_meta'][0]['generation'] = 1
        state['runtime_row_meta'][1]['generation'] = 1
        self.assertTrue(self.server._save_canonical_character_state(state))
        self.packet(0x0012, struct.pack('<IB', 22, 2), 100)
        self.packet(0x0011, rows_packet([dict(EMPTY) for _ in range(10)]), 101)
        self.assertEqual('rejected', self.server.proto_state['last_runtime_rows_0011']['status'])
        final = self.server._load_canonical_character_state()
        self.assertEqual(0, final['currency'])
        self.assertEqual(state['runtime_rows'], final['runtime_rows'])

    def test_lost_reward_pair_cannot_retire_row_on_followup(self):
        state = self.empty_state()
        state['runtime_rows'][0] = {'kind': 1, 'aux': 31, 'value': 1}
        state['runtime_row_meta'][0]['generation'] = 1
        self.assertTrue(self.server._save_canonical_character_state(state))
        self.packet(0x0012, struct.pack('<IB', 22, 2), 100)
        self.packet(0x0011, rows_packet([dict(EMPTY) for _ in range(10)]), 102)
        self.packet(0x0011, rows_packet([dict(EMPTY) for _ in range(10)]), 103)
        self.assertEqual('rejected', self.server.proto_state['last_runtime_rows_0011']['status'])
        self.assertEqual(state['runtime_rows'], self.server._load_canonical_character_state()['runtime_rows'])

    def test_new_exact_reward_pair_releases_invalidated_row(self):
        state = self.empty_state()
        state['runtime_rows'][0] = {'kind': 1, 'aux': 31, 'value': 26080406}
        state['runtime_row_meta'][0]['generation'] = 1
        self.assertTrue(self.server._save_canonical_character_state(state))
        retired = [dict(EMPTY) for _ in range(10)]
        self.packet(0x0012, struct.pack('<IB', 22, 2), 100)
        self.packet(0x0011, rows_packet(retired), 102)
        self.assertIn('invalidated_quest_reward_rows', self.server.proto_state)
        self.packet(0x0012, struct.pack('<IB', 22, 2), 103)
        ack = self.packet(0x0011, rows_packet(retired), 104)
        self.assertIsNotNone(ack)
        self.assertEqual(22, self.server._load_canonical_character_state()['currency'])
        self.assertNotIn('invalidated_quest_reward_rows', self.server.proto_state)

    def test_growth_completion_must_name_active_row(self):
        self.empty_state()
        self.packet(0x0010, b'\x02\x01', 100)
        self.assertEqual('rejected', self.server.proto_state['last_growth_route_0010']['status'])
        self.assertNotIn('pending_growth_route_0010', self.server.proto_state)


if __name__ == '__main__':
    unittest.main()
