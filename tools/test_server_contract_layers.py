# -*- coding: utf-8 -*-
"""Contract tests for login, canonical state, and chat relay layers."""

import os
import hashlib
import inspect
import json
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import azrok_server as server_module
import azrok_control as control_module
from azrok_protocol_registry import find_spec


def parse_frames(server, data):
    frames, rest = server._parse_packets(data)
    if rest:
        raise AssertionError(f'unparsed frame tail: {rest.hex()}')
    return [(opcode, payload) for opcode, payload, _raw in frames]


class LoginContractTests(unittest.TestCase):
    def setUp(self):
        self.server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        self.server.proto_state = {}

    def login_payload(self):
        payload = bytearray(0x6A)
        payload[0] = 1
        payload[1:5] = b'user'
        payload[14:18] = b'pass'
        return bytes(payload)

    def test_login_decoder_requires_exact_106_bytes(self):
        for size in (105, 107):
            with self.assertRaises(ValueError):
                server_module.decode_c2s_login_0000(b'\x00' * size)
        login_type, user, password = server_module.decode_c2s_login_0000(
            self.login_payload()
        )
        self.assertEqual((login_type, user, password), (1, b'user', b'pass'))

    def test_login_identity_is_saved_before_heartbeat_paced_lobby(self):
        response = self.server._build_response(0x0000, self.login_payload(), pkt_num=1)
        self.assertIsNone(response)
        self.assertEqual(self.server.proto_state['account_raw'], b'user')
        self.assertFalse(self.server.proto_state.get('login_response_sent', False))

    def test_post_logout_reconnect_stays_at_character_picker(self):
        self.server.manual_select_accounts = {b'user'}
        response = self.server._build_response(0x0000, self.login_payload(), pkt_num=1)
        self.assertIsNone(response)
        self.assertTrue(self.server.proto_state['auto_select_existing_sent'])
        self.assertTrue(self.server.proto_state['logout_character_picker_reconnect'])
        self.assertNotIn(b'user', self.server.manual_select_accounts)

    def test_first_heartbeat_sends_working_heartbeat_calibration_and_lobby_order(self):
        self.server._build_response(0x0000, self.login_payload(), pkt_num=1)
        frames = parse_frames(
            self.server,
            self.server._build_response(0x0016, b'\x00', pkt_num=2),
        )
        self.assertEqual([opcode for opcode, _payload in frames], [0x0016, 0x0004, 0x0000])
        self.assertEqual(frames[0][1], b'\x00')
        self.assertEqual(len(frames[1][1]), 5)
        self.assertEqual(frames[1][1][0], 0)
        self.assertEqual(len(frames[2][1]), 0x183)
        self.assertEqual(frames[2][1][0:2], b'\x00\x00')
        self.assertEqual(frames[2][1][2:6], b'\xFF' * 4)
        self.assertEqual(frames[2][1][0x56], 0)
        self.assertTrue(self.server.proto_state['login_response_sent'])

    def test_lobby_bootstrap_recovers_account_scoped_occupied_slot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = server_module.AzrokServer.__new__(server_module.AzrokServer)
            server.proto_state = {'account_raw': b'accountA', 'char_name_raw': b'Player'}
            server.state_store_dir = temp_dir
            snapshot = bytearray(0xC4)
            snapshot[0x05] = 1
            struct.pack_into('<H', snapshot, 0x0C, 26)
            path = os.path.join(
                temp_dir,
                'a6163636f756e7441_s2_c417a726f6b31_state_v1.json',
            )
            with open(path, 'w', encoding='utf-8') as state_file:
                state_file.write('{"schema_version":1,"character":{"species":2},'
                                 f'"snapshot_hex":"{bytes(snapshot).hex()}"}}')
            payload = server._build_login_bootstrap_0000()

        self.assertEqual(payload[0x01], 1)
        self.assertEqual(payload[0x02:0x06], b'\x02\xFF\xFF\xFF')
        self.assertEqual(payload[0x06], 26)
        self.assertEqual(payload[0x0A], 1)
        self.assertEqual(payload[0x0E:0x1B].split(b'\x00', 1)[0], b'Azrok1')
        self.assertEqual(server.proto_state['lobby_slots'][0]['storage_slot'], 2)

    def test_lobby_bootstrap_falls_back_to_legacy_snapshot_for_level_stage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = server_module.AzrokServer.__new__(server_module.AzrokServer)
            server.proto_state = {'account_raw': b'accountA', 'char_name_raw': b'Player'}
            server.state_store_dir = temp_dir
            canonical = os.path.join(
                temp_dir,
                'a6163636f756e7441_s0_c417a726f6b31_state_v1.json',
            )
            with open(canonical, 'w', encoding='utf-8') as state_file:
                state_file.write('{"schema_version":1,"snapshot_hex":null}')
            snapshot = bytearray(0xC4)
            snapshot[0x05] = 1
            struct.pack_into('<H', snapshot, 0x0C, 26)
            with open(os.path.join(temp_dir, '417a726f6b31_c2s0007.bin'), 'wb') as raw_file:
                raw_file.write(snapshot)
            payload = server._build_login_bootstrap_0000()

        self.assertEqual(payload[0x06], 26)
        self.assertEqual(payload[0x0A], 1)

    def test_hansol_kind1_requests_are_answered_after_login(self):
        self.server._build_response(0x0000, self.login_payload(), pkt_num=1)
        self.server._build_response(0x0016, b'\x00', pkt_num=2)
        self.server.proto_state['hansol_calibration_active'] = True
        self.server.proto_state['calib_0004_count'] = 0
        frames = parse_frames(
            self.server,
            self.server._build_response(0x0016, b'\x01', pkt_num=3),
        )
        self.assertEqual([opcode for opcode, _payload in frames], [0x0016, 0x0004])
        self.assertEqual(frames[1][1][0], 1)

    def test_all_local_facility_kind1_requests_start_exact_plaza_return(self):
        expected_facilities = {0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C}
        self.assertEqual(set(server_module.LOCAL_FACILITY_ROOM_KINDS), expected_facilities)
        for room_kind in sorted(expected_facilities):
            with self.subTest(room_kind=room_kind):
                self.server.proto_state = {
                    'current_room_kind': room_kind,
                    'login_response_sent': True,
                }
                frames = parse_frames(
                    self.server,
                    self.server._build_response(0x0016, b'\x01', pkt_num=10),
                )
                self.assertEqual(frames, [(0x0016, b'\x00'), (0x000D, b'\x00')])
                self.assertTrue(self.server.proto_state['facility_plaza_return_sent'])
                self.assertTrue(self.server.proto_state['hansol_calibration_active'])

                # The following five requests are calibration samples, not
                # duplicate transition preludes.  This is the exact observed
                # count before the client naturally emits C2S 0x0064.
                for sample in range(5):
                    frames = parse_frames(
                        self.server,
                        self.server._build_response(
                            0x0016, b'\x01', pkt_num=11 + sample
                        ),
                    )
                    self.assertEqual(
                        [opcode for opcode, _payload in frames],
                        [0x0016, 0x0004],
                    )
                    self.assertEqual(frames[1][1][0], 1)
                    self.assertNotIn(0x000D, [opcode for opcode, _payload in frames])
                self.assertEqual(
                    self.server.proto_state['hansol_calibration_samples_sent'],
                    5,
                )

    def test_kind1_is_not_treated_as_facility_exit_in_pathouse_or_plaza(self):
        for room_kind in (server_module.LOCAL_PAT_HOUSE_ROOM_KIND, 0x01,
                          server_module.PLAZA_ROOM_KIND, None):
            with self.subTest(room_kind=room_kind):
                self.server.proto_state = {
                    'current_room_kind': room_kind,
                    'login_response_sent': True,
                }
                frames = parse_frames(
                    self.server,
                    self.server._build_response(0x0016, b'\x01', pkt_num=12),
                )
                self.assertEqual(frames, [(0x0016, b'\x00')])
                self.assertFalse(self.server.proto_state.get('facility_plaza_return_sent', False))

    def test_parser_rejects_oversized_declared_payload(self):
        bad = struct.pack('<HH', server_module.MAX_SAFE_PACKET_PAYLOAD + 1, 7)
        with self.assertRaises(ValueError):
            self.server._parse_packets(bad)

    def test_protocol_context_syncs_selected_character_identity_to_relay_meta(self):
        server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        conn = object()
        server.proto_lock = threading.RLock()
        server.ctl_lock = threading.RLock()
        server.proto_state = {}
        server.proto_template = {}
        server.client_meta = {conn: {'name': 'Player', 'proto_state': {}}}

        with server._client_protocol_context(conn):
            server.proto_state.update({
                'char_name_raw': b'Azrok1',
                'account_name': 'player',
                'char_type': 2,
            })

        self.assertEqual(server.client_meta[conn]['name'], 'Azrok1')
        self.assertEqual(server.client_meta[conn]['account'], 'player')
        self.assertEqual(server.client_meta[conn]['char_type'], 2)

    def test_invalid_character_slot_does_not_change_identity_or_state_key(self):
        server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        conn = object()
        server.ctl_lock = threading.RLock()
        server.proto_state = {
            'character_slot': 0,
            'lobby_slots': {0: {'species': 2}},
        }
        server.client_meta = {
            conn: {'name': 'Azrok1', 'room_kind': None, 'char_type': 2},
        }

        server._update_client_identity(conn, 0x0005, b'\x01')

        self.assertEqual(server.proto_state['character_slot'], 0)
        self.assertIsNone(server.client_meta[conn]['room_kind'])
        self.assertEqual(server.client_meta[conn]['char_type'], 2)


class CanonicalStateContractTests(unittest.TestCase):
    def make_server(self, temp_dir):
        server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        server.proto_state = {
            'account_raw': b'accountA',
            'character_slot': 2,
            'char_name_raw': b'Azrok1',
        }
        server.state_store_dir = temp_dir
        server.saved_character_states = {}
        server.saved_server_states = {}
        server._add_event = lambda *args, **kwargs: None
        server._entity_id_for_proto_state = lambda _state: 1
        server.proto_state['client_0005_seen'] = True
        server.proto_state['selected_character_key'] = server._character_state_key()
        return server

    @staticmethod
    def accessory_progression_state(stats=None, evolution=0):
        snapshot = bytearray(0xC4)
        snapshot[0x05] = evolution
        for stat_id, value in (stats or {}).items():
            struct.pack_into('<H', snapshot, 0x0A + int(stat_id) * 2, int(value))
        return {'snapshot_hex': bytes(snapshot).hex()}

    def test_account_slot_character_keys_are_isolated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            key_a = server._character_state_key()
            server.proto_state['character_slot'] = 3
            key_b = server._character_state_key()
            server.proto_state['account_raw'] = b'accountB'
            key_c = server._character_state_key()
        self.assertEqual(len({key_a, key_b, key_c}), 3)

    def test_full_account_reset_archives_account_and_legacy_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.ctl_lock = threading.RLock()
            server.client_meta = {}
            server.manual_select_accounts = {b'accountA'}
            key = server._character_state_key()
            canonical = server._canonical_state_path(key)
            snapshot = server._character_state_path(key)
            legacy = os.path.join(temp_dir, '417a726f6b31_c2s0007.bin')
            with open(canonical, 'w', encoding='utf-8') as handle:
                handle.write('{"schema_version":1}')
            with open(snapshot, 'wb') as handle:
                handle.write(b'account snapshot')
            with open(legacy, 'wb') as handle:
                handle.write(b'legacy snapshot')
            server.saved_character_states[key] = b'cached'
            server.saved_server_states[key] = {'cached': True}

            ok, result = server.reset_preserved_account_state('accountA')

            self.assertTrue(ok, result)
            self.assertEqual(result['archived_files'], 3)
            self.assertFalse(os.path.exists(canonical))
            self.assertFalse(os.path.exists(snapshot))
            self.assertFalse(os.path.exists(legacy))
            self.assertEqual(len(os.listdir(result['archive_dir'])), 3)
            self.assertNotIn(key, server.saved_character_states)
            self.assertNotIn(key, server.saved_server_states)
            self.assertNotIn(b'accountA', server.manual_select_accounts)

    def test_full_account_reset_refuses_a_connected_account(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.ctl_lock = threading.RLock()
            server.client_meta = {
                object(): {
                    'entity_id': 7,
                    'proto_state': {'account_raw': b'accountA'},
                }
            }
            server.manual_select_accounts = set()
            ok, result = server.reset_preserved_account_state('accountA')
            self.assertFalse(ok)
            self.assertEqual(result['connected_entities'], [7])

    def test_inventory_runtime_rows_and_currency_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['inventory']['food'][1] = 4
            state['inventory']['gym'][7] = 2
            state['runtime_rows'][1] = {'kind': 1, 'aux': 32, 'value': 9}
            state['currency'] = 345
            self.assertTrue(server._save_canonical_character_state(state))

            server.saved_server_states = {}
            loaded = server._load_canonical_character_state()
            zone = bytearray(0x1D8)
            server._apply_canonical_server_state(zone)

        self.assertEqual(loaded['currency'], 345)
        self.assertEqual(zone[0xEA + 1], 4)
        self.assertEqual(zone[0x11D + 7], 2)
        self.assertEqual(struct.unpack_from('<H', zone, 0x134 + 2)[0], 1)
        self.assertEqual(struct.unpack_from('<H', zone, 0x148 + 2)[0], 32)
        self.assertEqual(struct.unpack_from('<I', zone, 0x15C + 4)[0], 9)

    def test_canonical_revision_and_exact_sha_advance_after_atomic_replace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            self.assertEqual(state['revision'], 0)
            self.assertTrue(server._save_canonical_character_state(
                state, mutation={
                    'kind': 'test_commit',
                    'changed_fields': ['currency'],
                }
            ))
            first = server.mutation_ring[-1]
            path = server._canonical_state_path()
            with open(path, 'rb') as handle:
                first_raw = handle.read()
            self.assertEqual(state['revision'], 1)
            self.assertEqual(first['result'], 'committed')
            self.assertEqual((first['revision_before'], first['revision_after']), (0, 1))
            self.assertEqual(first['sha256_after'], hashlib.sha256(first_raw).hexdigest())
            self.assertNotIn(server._character_state_key(), json.dumps(first))

            state['currency'] = 77
            self.assertTrue(server._save_canonical_character_state(
                state, mutation={
                    'kind': 'test_commit',
                    'changed_fields': ['currency'],
                }
            ))
            second = server.mutation_ring[-1]
            with open(path, 'rb') as handle:
                second_raw = handle.read()

        self.assertEqual(state['revision'], 2)
        self.assertEqual((second['revision_before'], second['revision_after']), (1, 2))
        self.assertEqual(second['sha256_before'], hashlib.sha256(first_raw).hexdigest())
        self.assertEqual(second['sha256_after'], hashlib.sha256(second_raw).hexdigest())

    def test_canonical_replace_failure_keeps_revision_sha_and_no_commit_receipt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            self.assertTrue(server._save_canonical_character_state(state))
            path = server._canonical_state_path()
            with open(path, 'rb') as handle:
                before = handle.read()
            state['currency'] = 123
            with mock.patch.object(
                    server_module.os, 'replace', side_effect=OSError('injected replace failure')):
                self.assertFalse(server._save_canonical_character_state(
                    state, mutation={'kind': 'test_failure'}
                ))
            with open(path, 'rb') as handle:
                after = handle.read()

        self.assertEqual(state['revision'], 1)
        self.assertEqual(after, before)
        self.assertEqual(server.mutation_ring[-1]['result'], 'rejected')
        self.assertEqual(server.mutation_ring[-1]['revision_before'], 1)
        self.assertIsNone(server.mutation_ring[-1]['revision_after'])
        self.assertEqual(
            [row['result'] for row in server.mutation_ring],
            ['committed', 'rejected'],
        )

    def test_durable_mutation_journal_recovers_sequence_and_tail_after_restart(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = self.make_server(temp_dir)
            state = first._load_canonical_character_state()
            self.assertTrue(first._save_canonical_character_state(
                state, mutation={'kind': 'first'}
            ))
            state['currency'] = 42
            self.assertTrue(first._save_canonical_character_state(
                state, mutation={'kind': 'second', 'changed_fields': ['currency']}
            ))
            journal_path = os.path.join(temp_dir, 'mutation_transactions_v1.jsonl')
            with open(journal_path, encoding='utf-8') as journal:
                rows = [json.loads(line) for line in journal]
            self.assertEqual([row['seq'] for row in rows], [1, 2])
            self.assertTrue(all(row['schema'] == 'azrok.mutation.transaction.v1'
                                for row in rows))

            restarted = self.make_server(temp_dir)
            restarted._ensure_mutation_runtime()
            self.assertEqual(restarted.mutation_seq, 2)
            self.assertEqual([row['seq'] for row in restarted.mutation_ring], [1, 2])
            self.assertTrue(all(row['journal_status'] == 'durable'
                                for row in restarted.mutation_ring))
            loaded = restarted._load_canonical_character_state()
            loaded['currency'] = 43
            self.assertTrue(restarted._save_canonical_character_state(
                loaded, mutation={'kind': 'third'}
            ))
            self.assertEqual(restarted.mutation_ring[-1]['transaction_id'],
                             'tx-00000003')

    def test_truncated_journal_tail_is_preserved_and_next_row_is_separate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            self.assertTrue(server._save_canonical_character_state(state))
            journal_path = os.path.join(temp_dir, 'mutation_transactions_v1.jsonl')
            with open(journal_path, 'ab') as journal:
                journal.write(b'{"truncated":')

            restarted = self.make_server(temp_dir)
            restarted._ensure_mutation_runtime()
            self.assertEqual(restarted.mutation_seq, 1)
            self.assertEqual(restarted.mutation_journal_corrupt_lines, 1)
            loaded = restarted._load_canonical_character_state()
            loaded['currency'] = 5
            self.assertTrue(restarted._save_canonical_character_state(loaded))
            with open(journal_path, encoding='utf-8') as journal:
                lines = journal.read().splitlines()
            self.assertEqual(len(lines), 3)
            self.assertEqual(json.loads(lines[-1])['seq'], 2)

    def test_journal_append_failure_does_not_rollback_committed_canonical(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            events = []
            server._add_event = lambda kind, message, **kw: events.append(
                (kind, kw.get('severity'), kw.get('details') or {})
            )
            state = server._load_canonical_character_state()
            state['currency'] = 91
            with mock.patch.object(
                    server, '_append_mutation_journal',
                    return_value=(False, 'injected journal failure')):
                self.assertTrue(server._save_canonical_character_state(
                    state, mutation={'kind': 'journal_fault'}
                ))
            with open(server._canonical_state_path(), encoding='utf-8') as canonical:
                persisted = json.load(canonical)

        receipt = server.mutation_ring[-1]
        self.assertEqual(persisted['currency'], 91)
        self.assertEqual(receipt['result'], 'committed')
        self.assertEqual(receipt['journal_status'], 'failed')
        self.assertEqual(state['revision'], 1)
        self.assertTrue(any(kind == 'audit_journal_failure' and severity == 'error'
                            for kind, severity, _details in events))

    def test_accessory_slots_roundtrip_and_restore_at_s2c_0007_tail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            self.assertEqual(state['accessory_slots'], [0xFF] * 4)
            state['accessory_slots'] = [9, 0xFF, 3, 7]
            self.assertTrue(server._save_canonical_character_state(state))

            server.saved_server_states = {}
            loaded = server._load_canonical_character_state()
            zone = server._build_zone_0007_draft(b'')

        self.assertEqual(loaded['accessory_slots'], [9, 0xFF, 3, 7])
        self.assertEqual(zone[0x1D4:0x1D8], bytes((9, 0xFF, 3, 7)))

    def test_accessory_unlock_preserves_tier1_and_enforces_level_boundary(self):
        self.assertTrue(
            server_module.evaluate_accessory_unlock({}, 0, 0)['allowed']
        )
        self.assertFalse(
            server_module.evaluate_accessory_unlock({}, 3, 1)['allowed']
        )
        locked = self.accessory_progression_state({1: 9})
        allowed = self.accessory_progression_state({1: 10})
        self.assertFalse(
            server_module.evaluate_accessory_unlock(locked, 3, 1)['allowed']
        )
        evidence = server_module.evaluate_accessory_unlock(allowed, 3, 1)
        self.assertTrue(evidence['allowed'])
        self.assertEqual(
            (evidence['stat_id'], evidence['actual'], evidence['threshold']),
            (1, 10, 10),
        )

    def test_accessory_unlock_uses_exact_five_group_aggregates(self):
        state = self.accessory_progression_state({
            30: 50,
            31: 50, 32: 60, 33: 90,
            34: 20, 35: 15, 36: 15,
            37: 30, 38: 30, 39: 40,
            40: 199, 66: 1,
        })
        progression = server_module.accessory_progression_from_canonical(state)
        self.assertEqual(
            progression['group_totals'],
            {1: 200, 2: 50, 3: 100, 4: 50, 5: 200},
        )
        for selector in ((1, 1), (1, 3), (1, 2), (1, 0), (2, 1)):
            with self.subTest(selector=selector):
                self.assertTrue(
                    server_module.evaluate_accessory_unlock(
                        state, selector[0], selector[1]
                    )['allowed']
                )

        below = self.accessory_progression_state({31: 50, 32: 60, 33: 89})
        self.assertFalse(
            server_module.evaluate_accessory_unlock(below, 1, 1)['allowed']
        )

    def test_accessory_unlock_evolution_gate_is_inclusive_at_stage_three(self):
        stage2 = self.accessory_progression_state({30: 200}, evolution=2)
        stage3 = self.accessory_progression_state({30: 200}, evolution=3)
        rejected = server_module.evaluate_accessory_unlock(stage2, 1, 4)
        accepted = server_module.evaluate_accessory_unlock(stage3, 1, 4)
        self.assertFalse(rejected['allowed'])
        self.assertEqual(rejected['minimum_evolution'], 3)
        self.assertTrue(accepted['allowed'])

    def test_locked_accessory_set_never_saves_acks_or_relays(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            source = object()
            peer = object()
            server.connections = [source, peer]
            server.ctl_lock = threading.RLock()
            server.client_meta = {
                source: {
                    'entity_id': 2,
                    'room_kind': server_module.PLAZA_ROOM_KIND,
                    'visible_remote_actor_ids': {3},
                    'proto_state': server.proto_state,
                },
                peer: {
                    'entity_id': 3,
                    'room_kind': server_module.PLAZA_ROOM_KIND,
                    'visible_remote_actor_ids': {2},
                    'proto_state': {},
                },
            }
            state = server._load_canonical_character_state()
            state.update(self.accessory_progression_state({30: 49}))
            self.assertTrue(server._save_canonical_character_state(state))
            emitted = []
            server._emit = (
                lambda conn, data, **kwargs:
                emitted.append((conn, data)) or True
            )

            with mock.patch.object(
                server, '_save_canonical_character_state', wraps=server._save_canonical_character_state
            ) as save:
                self.assertFalse(server._process_accessory_0018(
                    source, b'\x00\x01\x00', pkt_num=20
                ))
                save.assert_not_called()

            self.assertEqual(emitted, [])
            self.assertEqual(state['accessory_slots'], [0xFF] * 4)
            self.assertNotIn('accessory_slots', server.client_meta[source])

    def test_accessory_slots_reject_invalid_canonical_and_actor_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['accessory_slots'] = [10, 0, 0, 0]
            self.assertFalse(server._save_canonical_character_state(state))
            self.assertFalse(os.path.exists(server._canonical_state_path()))

            with open(server._canonical_state_path(), 'w', encoding='utf-8') as state_file:
                json.dump({
                    'schema_version': 1,
                    'accessory_slots': [9, 7, 3, 7],
                }, state_file)
            server.saved_server_states = {}
            self.assertEqual(
                server._load_canonical_character_state()['accessory_slots'],
                [0xFF] * 4,
            )

            with self.assertRaises(ValueError):
                server._build_state_0066_actor_record(
                    2, 1, b'Peer', accessory_slots=[0, 7, 0, 0]
                )

    def test_s2c_0066_roster_projects_peer_canonical_accessories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            peer_key = server._selected_character_state_key()
            state = server._load_canonical_character_state(key=peer_key)
            state['accessory_slots'] = [1, 2, 3, 7]
            self.assertTrue(
                server._save_canonical_character_state(state, key=peer_key)
            )
            # Exercise the read-only disk projection, not just the hot cache.
            server.saved_server_states = {}

            recipient = object()
            peer = object()
            server.connections = [recipient, peer]
            server.ctl_lock = threading.RLock()
            server.client_meta = {
                recipient: {
                    'entity_id': 2, 'name': 'Self', 'char_type': 0,
                    'room_kind': server_module.PLAZA_ROOM_KIND,
                    'visible_remote_actor_ids': set(), 'proto_state': {},
                },
                peer: {
                    'entity_id': 3, 'name': 'Peer', 'char_type': 1,
                    'room_kind': server_module.PLAZA_ROOM_KIND,
                    'x': 10, 'y': 20, 'visible_remote_actor_ids': set(),
                    'proto_state': {
                        'client_0005_seen': True,
                        'selected_character_key': peer_key,
                    },
                },
            }
            emitted = []
            server._emit = (
                lambda conn, data, **kwargs:
                emitted.append((conn, data)) or True
            )

            server._send_room_roster(recipient, server_module.PLAZA_ROOM_KIND)
            roster_frames = [
                frame for conn, raw in emitted if conn is recipient
                for frame in parse_frames(server, raw)
            ]

        actor = next(payload for opcode, payload in roster_frames if opcode == 0x0066)
        # S2C 0x0066 only constructs a previously unseen non-self remote
        # actor.  A self-id record is ignored before its name/appearance is
        # copied, so the roster must never try to use it as a self-profile
        # update channel.
        self.assertNotIn(
            server_module.DEFAULT_ACTOR_ID,
            [struct.unpack_from('<I', payload, 0x01)[0]
             for opcode, payload in roster_frames if opcode == 0x0066],
        )
        self.assertEqual(actor[0x14:0x18], bytes((1, 2, 3, 7)))

    def test_c2s_0018_persists_and_s2c_000c_acks_and_relays(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            source = object()
            peer = object()
            hidden_peer = object()
            other_room = object()
            server.connections = [source, peer, hidden_peer, other_room]
            server.ctl_lock = threading.RLock()
            server.client_meta = {
                source: {
                    'entity_id': 2, 'room_kind': server_module.PLAZA_ROOM_KIND,
                    'visible_remote_actor_ids': {3},
                    'proto_state': server.proto_state,
                },
                peer: {
                    'entity_id': 3, 'room_kind': server_module.PLAZA_ROOM_KIND,
                    'visible_remote_actor_ids': {2}, 'proto_state': {},
                },
                hidden_peer: {
                    'entity_id': 4, 'room_kind': server_module.PLAZA_ROOM_KIND,
                    'visible_remote_actor_ids': set(), 'proto_state': {},
                },
                other_room: {
                    'entity_id': 5, 'room_kind': 8,
                    'visible_remote_actor_ids': {2}, 'proto_state': {},
                },
            }
            emitted = []
            server._emit = (
                lambda conn, data, **kwargs:
                emitted.append((conn, data)) or True
            )

            self.assertTrue(server._process_accessory_0018(
                source, b'\x00\x03\x07', pkt_num=10
            ))
            self.assertEqual(
                server._load_canonical_character_state()['accessory_slots'],
                [0xFF, 0xFF, 0xFF, 7],
            )
            self.assertEqual([conn for conn, _raw in emitted], [source, peer])
            self_ack = parse_frames(server, emitted[0][1])
            peer_update = parse_frames(server, emitted[1][1])
            self.assertEqual(
                self_ack,
                [(0x000C, struct.pack('<IBBB', 1, 0, 3, 7))],
            )
            self.assertEqual(
                peer_update,
                [(0x000C, struct.pack('<IBBB', 2, 0, 3, 7))],
            )

            emitted.clear()
            self.assertTrue(server._process_accessory_0018(
                source, b'\x01\x03\x07', pkt_num=11
            ))
            self.assertEqual(
                server._load_canonical_character_state()['accessory_slots'][3],
                0xFF,
            )
            self.assertEqual(
                parse_frames(server, emitted[0][1]),
                [(0x000C, struct.pack('<IBBB', 1, 1, 3, 7))],
            )

            # Clearing the same old value again is stale and emits nothing.
            emitted.clear()
            self.assertFalse(server._process_accessory_0018(
                source, b'\x01\x03\x07', pkt_num=12
            ))
            self.assertEqual(emitted, [])

            # A forged value cannot clear a newer canonical selector.
            self.assertTrue(server._process_accessory_0018(
                source, b'\x00\x03\x07', pkt_num=13
            ))
            emitted.clear()
            self.assertFalse(server._process_accessory_0018(
                source, b'\x01\x03\x06', pkt_num=14
            ))
            self.assertEqual(emitted, [])
            self.assertEqual(
                server._load_canonical_character_state()['accessory_slots'][3], 7
            )

    def test_c2s_0018_unbound_or_failed_save_never_emits_or_mutates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            source = object()
            server.connections = [source]
            server.ctl_lock = threading.RLock()
            server.client_meta = {
                source: {
                    'entity_id': 2, 'room_kind': server_module.PLAZA_ROOM_KIND,
                    'visible_remote_actor_ids': set(),
                    'proto_state': server.proto_state,
                },
            }
            emitted = []
            server._emit = (
                lambda conn, data, **kwargs:
                emitted.append((conn, data)) or True
            )
            before = list(
                server._load_canonical_character_state()['accessory_slots']
            )

            with mock.patch.object(
                server, '_save_canonical_character_state', return_value=False
            ):
                self.assertFalse(server._process_accessory_0018(
                    source, b'\x00\x00\x01'
                ))
            self.assertEqual(emitted, [])
            self.assertEqual(
                server._load_canonical_character_state()['accessory_slots'], before
            )

            server.proto_state['selected_character_key'] = None
            with mock.patch.object(
                server, '_load_canonical_character_state',
                side_effect=AssertionError('unbound request loaded canonical'),
            ):
                self.assertFalse(server._process_accessory_0018(
                    source, b'\x00\x00\x01'
                ))
            self.assertEqual(emitted, [])

    def test_legacy_stage1_runtime_row_migrates_from_aux0_to_next_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            snapshot = bytearray(0xC4)
            snapshot[0x05] = 1
            rows = [
                {'kind': 3, 'aux': 0, 'value': 0},
                *[{'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(9)],
            ]
            path = server._canonical_state_path()
            with open(path, 'w', encoding='utf-8') as state_file:
                import json
                json.dump({
                    'schema_version': 1,
                    'snapshot_hex': bytes(snapshot).hex(),
                    'runtime_rows': rows,
                }, state_file)
            loaded = server._load_canonical_character_state()

        self.assertEqual(loaded['runtime_rows'][0], {'kind': 3, 'aux': 1, 'value': 0})
        self.assertEqual(loaded['runtime_row_meta'][0]['generation'], 2)
        self.assertEqual(loaded['runtime_row_meta'][0]['issued_evolution'], 1)

    def test_legacy_duplicate_kind3_rows_are_sanitized_to_one_active_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            snapshot = bytearray(0xC4)
            rows = [
                {'kind': 3, 'aux': 0, 'value': 0},
                {'kind': 3, 'aux': 1, 'value': 0},
                *[{'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(8)],
            ]
            meta = [
                {'generation': 1, 'issued_evolution': 0},
                {'generation': 2, 'issued_evolution': 1},
                *[{'generation': 0, 'issued_evolution': 0} for _ in range(8)],
            ]
            with open(server._canonical_state_path(), 'w', encoding='utf-8') as state_file:
                import json
                json.dump({
                    'schema_version': 1,
                    'snapshot_hex': bytes(snapshot).hex(),
                    'runtime_rows': rows,
                    'runtime_row_meta': meta,
                }, state_file)

            loaded = server._load_canonical_character_state()

        self.assertEqual(loaded['runtime_rows'][0], rows[0])
        self.assertEqual(
            loaded['runtime_rows'][1],
            {'kind': 0xFF, 'aux': 0xFF, 'value': 0},
        )
        self.assertEqual(loaded['runtime_row_meta'][1]['generation'], 0)
        self.assertEqual(server.proto_state['duplicate_kind3_rows_sanitized'], 1)

    def test_legacy_binary_snapshot_is_promoted_into_canonical_stage_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            rows = [
                {'kind': 3, 'aux': 0, 'value': 0},
                *[{'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(9)],
            ]
            with open(server._canonical_state_path(), 'w', encoding='utf-8') as state_file:
                import json
                json.dump({
                    'schema_version': 1,
                    'snapshot_hex': None,
                    'runtime_rows': rows,
                    'currency': 950,
                }, state_file)
            snapshot = bytearray(0xC4)
            snapshot[0x05] = 1
            with open(server._character_state_path(), 'wb') as raw_file:
                raw_file.write(snapshot)

            loaded_snapshot = server._load_character_state_snapshot()
            server.saved_server_states = {}
            promoted = server._load_canonical_character_state()

        self.assertEqual(loaded_snapshot[0x05], 1)
        self.assertEqual(promoted['snapshot_hex'], bytes(snapshot).hex())
        self.assertEqual(promoted['runtime_rows'][0], {'kind': 3, 'aux': 1, 'value': 0})
        self.assertEqual(promoted['runtime_row_meta'][0]['issued_evolution'], 1)
        self.assertEqual(promoted['currency'], 950)

    def test_name_only_legacy_snapshot_is_folded_into_existing_canonical_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            canonical = server._default_canonical_character_state()
            canonical['currency'] = 950
            canonical['inventory']['food'][1] = 1
            canonical['snapshot_hex'] = None
            self.assertTrue(server._save_canonical_character_state(canonical))

            snapshot = bytearray(0xC4)
            snapshot[0x05] = 1
            legacy_path = server._character_state_path(
                server._legacy_character_state_key()
            )
            with open(legacy_path, 'wb') as state_file:
                state_file.write(snapshot)

            server.saved_server_states = {}
            loaded_snapshot = server._load_character_state_snapshot()
            migrated = server._load_canonical_character_state()

        self.assertEqual(loaded_snapshot[0x05], 1)
        self.assertEqual(migrated['currency'], 950)
        self.assertEqual(migrated['inventory']['food'][1], 1)
        self.assertEqual(
            migrated['runtime_rows'][0], {'kind': 3, 'aux': 1, 'value': 0}
        )
        self.assertEqual(migrated['runtime_row_meta'][0]['generation'], 2)
        self.assertEqual(migrated['runtime_row_meta'][0]['issued_evolution'], 1)
        self.assertEqual(bytes.fromhex(migrated['snapshot_hex'])[0x05], 1)

    def test_fresh_mode_pairs_are_zero_not_ff_sentinel(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            zone = server._build_zone_0007_draft(b'')

        self.assertEqual(zone[0x184:0x18C], b'\x00' * 8)
        self.assertEqual(zone[0x18C:0x1AC], b'\x00' * 0x20)

    def test_fresh_character_starts_with_food_and_infant_toy2000(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._default_canonical_character_state()
            zone = server._build_zone_0007_draft(b'')

        self.assertEqual(state['inventory']['food'][0], 1)
        self.assertEqual(sum(state['inventory']['food']), 1)
        self.assertEqual(zone[0x0EA], 1)
        self.assertNotIn('food', state['active_loadouts'])
        self.assertEqual(state['inventory']['toy'][0], 1)
        self.assertEqual(zone[0x113], 1)

    def test_legacy_ff_clamp_mode_pair_signature_is_sanitized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            snapshot = bytearray(0xC4)
            snapshot[0x9C:0xA4] = b'\x02' * 8
            clean, changed = server._sanitize_c2s_mode_pairs(snapshot)

        self.assertTrue(changed)
        self.assertEqual(clean[0x9C:0xA4], b'\x00' * 8)
        self.assertEqual(clean[0xA4:0xC4], b'\x00' * 0x20)

    def test_valid_disease_mode_and_packed_date_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            snapshot = bytearray(0xC4)
            snapshot[0x9C + 6] = 2
            struct.pack_into('<I', snapshot, 0xA4 + 6 * 4, 26071808)
            clean, changed = server._sanitize_c2s_mode_pairs(snapshot)

        self.assertFalse(changed)
        self.assertEqual(clean[0x9C + 6], 2)
        self.assertEqual(struct.unpack_from('<I', clean, 0xA4 + 6 * 4)[0], 26071808)

    def test_runtime_row_policy_auto_retires_only_kind3(self):
        policies = server_module.RUNTIME_ROW_SERVER_POLICIES
        self.assertEqual(set(policies), {0, 1, 2, 3, 5})
        self.assertEqual(
            {kind for kind, policy in policies.items() if policy['auto_retire']},
            {3},
        )
        for kind in (0, 1, 2, 5):
            self.assertTrue(policies[kind]['reason'])

    def test_kind0_1_2_5_snapshot_effects_do_not_retire_or_credit(self):
        # Each delta is a real client-side quest effect, but none proves which
        # action caused it.  The locally removed row and currency callback are
        # absent from C2S, so the server must preserve the row and balance.
        cases = (
            (0, 1001, 7, 50, 40),   # food wish: stat7 -10
            (1, 32, 32, 0, 16),     # training: skill stat32 +16
            (2, 0xCF, 7, 50, 40),   # feed/exercise: stat7 -10
            (5, 212, 2, 0, 40),     # stage-0 tutorial: EXP +40
        )
        for kind, aux, stat_id, before_value, after_value in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp_dir:
                server = self.make_server(temp_dir)
                before = bytearray(0xC4)
                before[0x05] = 0
                struct.pack_into('<H', before, 0x0A + stat_id * 2, before_value)
                self.assertTrue(server._save_character_state_snapshot(before))

                state = server._load_canonical_character_state()
                state['runtime_rows'] = [
                    {'kind': 0xFF, 'aux': 0xFF, 'value': 0}
                    for _ in range(10)
                ]
                state['runtime_row_meta'] = [
                    {'generation': 0, 'issued_evolution': 0}
                    for _ in range(10)
                ]
                state['runtime_rows'][0] = {'kind': kind, 'aux': aux, 'value': 0}
                state['runtime_row_meta'][0] = {
                    'generation': 1, 'issued_evolution': 0,
                }
                state['currency'] = 321
                self.assertTrue(server._save_canonical_character_state(state))

                after = bytearray(before)
                struct.pack_into('<H', after, 0x0A + stat_id * 2, after_value)
                self.assertTrue(server._save_character_state_snapshot(after))
                loaded = server._load_canonical_character_state()

                self.assertEqual(loaded['runtime_rows'][0], {
                    'kind': kind, 'aux': aux, 'value': 0,
                })
                self.assertEqual(loaded['completed_runtime_rows'], [])
                self.assertEqual(loaded['currency'], 321)
                self.assertEqual(
                    server.proto_state['runtime_row_completion_policy'][
                        'active_fail_closed_kinds'
                    ],
                    [kind],
                )

    def test_kind3_row_retires_once_on_proven_evolution_edge_without_currency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            before = bytearray(0xC4)
            before[0x05] = 0
            struct.pack_into('<H', before, 0x0A + 2 * 2, 350)
            self.assertTrue(server._save_character_state_snapshot(before))

            after = bytearray(before)
            after[0x05] = 1
            self.assertTrue(server._save_character_state_snapshot(after))
            state = server._load_canonical_character_state()
            completion_count = len(state['completed_runtime_rows'])

            # An identical reconnect/periodic echo cannot complete or credit
            # the already retired generation again.
            self.assertTrue(server._save_character_state_snapshot(after))
            replayed = server._load_canonical_character_state()

        self.assertEqual(
            state['runtime_rows'][0],
            {'kind': 0xFF, 'aux': 0xFF, 'value': 0},
        )
        self.assertEqual(state['runtime_row_meta'][0]['generation'], 1)
        self.assertEqual(state['runtime_row_meta'][0]['issued_evolution'], 1)
        self.assertEqual(state['currency'], server_module.STARTER_CURRENCY)
        self.assertEqual(completion_count, 1)
        self.assertEqual(len(replayed['completed_runtime_rows']), 1)
        self.assertEqual(
            server.proto_state['last_runtime_row_completion']['currency_awarded'], 0
        )
        self.assertIsNone(
            server.proto_state['last_runtime_row_completion']['next_row']
        )

    def test_natural_growth_order_buffers_removal_then_accepts_client_next_route(self):
        def pack_rows(rows):
            return struct.pack(
                '<10H10H10I',
                *[row['kind'] for row in rows],
                *[row['aux'] for row in rows],
                *[row['value'] for row in rows],
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            before = bytearray(0xC4)
            struct.pack_into('<H', before, 0x0A + 2 * 2, 350)
            self.assertTrue(server._save_character_state_snapshot(before))

            empty = [
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0}
                for _ in range(10)
            ]
            self.assertIsNone(
                server._build_response(0x0010, b'\x00\x01', pkt_num=30)
            )
            self.assertIsNone(
                server._build_response(0x0011, pack_rows(empty), pkt_num=31)
            )
            self.assertEqual(
                server.proto_state['last_runtime_rows_0011']['status'],
                'pending_0007',
            )

            after = bytearray(before)
            after[0x05] = 1
            self.assertTrue(server._save_character_state_snapshot(after))
            self.assertNotIn('pending_growth_completion_0011', server.proto_state)
            self.assertEqual(
                server.proto_state['last_runtime_row_completion'][
                    'correlated_0011_packet_seq'
                ],
                31,
            )

            self.assertIsNone(
                server._build_response(0x0010, b'\x02\x00', pkt_num=32)
            )
            proposed = [dict(row) for row in empty]
            proposed[0] = {'kind': 3, 'aux': 2, 'value': 0}
            self.assertIsNone(
                server._build_response(0x0011, pack_rows(proposed), pkt_num=33)
            )
            final = server._load_canonical_character_state()

        self.assertEqual(final['runtime_rows'][0], proposed[0])

    def test_kind3_stage_edge_without_visible_threshold_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            before = bytearray(0xC4)
            self.assertTrue(server._save_character_state_snapshot(before))
            after = bytearray(before)
            after[0x05] = 1
            self.assertFalse(server._save_character_state_snapshot(after))
            state = server._load_canonical_character_state()

        self.assertEqual(state['runtime_rows'][0]['kind'], 3)
        self.assertEqual(state['completed_runtime_rows'], [])
        self.assertEqual(bytes.fromhex(state['snapshot_hex'])[0x05], 0)
        self.assertNotIn('last_runtime_row_completion', server.proto_state)

    def test_kind3_stage_jump_cannot_skip_issued_evolution_edge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            before = bytearray(0xC4)
            struct.pack_into('<H', before, 0x0A + 2 * 2, 350)
            self.assertTrue(server._save_character_state_snapshot(before))
            after = bytearray(before)
            after[0x05] = 2
            self.assertFalse(server._save_character_state_snapshot(after))
            server._load_character_state_snapshot()
            state = server._load_canonical_character_state()

        self.assertEqual(state['runtime_rows'][0], {'kind': 3, 'aux': 0, 'value': 0})
        self.assertEqual(state['runtime_row_meta'][0]['issued_evolution'], 0)
        self.assertEqual(state['completed_runtime_rows'], [])

    def test_first_snapshot_cannot_jump_past_server_issued_stage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            submitted = bytearray(0xC4)
            submitted[0x05] = 3

            self.assertFalse(server._save_character_state_snapshot(submitted))
            state = server._load_canonical_character_state()

        self.assertIsNone(state['snapshot_hex'])
        self.assertEqual(state['runtime_rows'][0], {'kind': 3, 'aux': 0, 'value': 0})
        self.assertEqual(state['runtime_row_meta'][0]['issued_evolution'], 0)

    def test_default_runtime_route_matches_selected_existing_evolution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_state['selected_evolution'] = 2
            state = server._default_canonical_character_state()

        self.assertEqual(
            state['runtime_rows'][0],
            {'kind': 3, 'aux': server_module.EVOLUTION_AUX_STAGE2, 'value': 0},
        )
        self.assertEqual(state['runtime_row_meta'][0]['issued_evolution'], 2)

    def test_cached_stale_snapshot_cannot_reissue_earlier_kind3_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            stage2 = bytearray(0xC4)
            stage2[0x05] = 2
            state['snapshot_hex'] = bytes(stage2).hex()
            state['runtime_rows'][0] = {'kind': 3, 'aux': 4, 'value': 0}
            state['runtime_row_meta'][0] = {'generation': 3, 'issued_evolution': 2}
            state['completed_runtime_rows'] = ['g1:r0:k3:a0:e1', 'g2:r0:k3:a1:e2']
            self.assertTrue(server._save_canonical_character_state(state))
            stale = bytearray(stage2)
            stale[0x05] = 1
            server.saved_character_states[server._character_state_key()] = bytes(stale)

            self.assertEqual(server._load_character_state_snapshot()[0x05], 1)
            preserved = server._load_canonical_character_state()

        self.assertEqual(preserved['runtime_rows'][0], {'kind': 3, 'aux': 4, 'value': 0})
        self.assertEqual(preserved['runtime_row_meta'][0], {'generation': 3, 'issued_evolution': 2})
        self.assertEqual(len(preserved['completed_runtime_rows']), 2)

    def test_canonical_save_failure_does_not_advance_raw_or_memory_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            key = server._character_state_key()
            old = bytes(0xC4)
            new = bytearray(old)
            struct.pack_into('<H', new, 0x0A + 0x20 * 2, 5)
            raw_path = server._character_state_path(key)
            with open(raw_path, 'wb') as raw_file:
                raw_file.write(old)
            server.saved_character_states[key] = old

            with mock.patch.object(
                server, '_save_canonical_character_state', return_value=False
            ):
                self.assertFalse(server._save_character_state_snapshot(new))

            with open(raw_path, 'rb') as raw_file:
                raw_after = raw_file.read()

        self.assertEqual(raw_after, old)
        self.assertEqual(server.saved_character_states[key], old)
        self.assertNotIn('last_content_save_payload', server.proto_state)

    def test_duplicate_live_character_session_is_rejected_before_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.ctl_lock = threading.RLock()
            current_state = {
                'account_raw': b'accountA',
                'lobby_slots': {
                    0: {
                        'storage_slot': 2,
                        'species': 2,
                        'evolution': 1,
                        'name_hex': b'Azrok1'.hex(),
                    },
                },
            }
            other_state = {
                'account_raw': b'accountA',
                'character_slot': 2,
                'char_name_raw': b'Azrok1',
                'client_0005_seen': True,
            }
            current = object()
            other = object()
            server.proto_state = current_state
            server.client_meta = {
                current: {'proto_state': current_state},
                other: {'proto_state': other_state},
            }

            self.assertIsNone(server._build_response(0x0005, b'\x00', pkt_num=1))

        self.assertNotIn('character_slot', current_state)
        self.assertEqual(
            current_state['last_character_select_reject']['reason'],
            'character already active on another connection',
        )

    def test_character_logout_releases_only_lease_and_actor_then_allows_reselect(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.ctl_lock = threading.RLock()
            server.connections = []
            server.client_meta = {}
            server.proto_state.update({
                'account_name': 'accountA',
                'login_response_sent': True,
                'account_has_characters': True,
                'char_created': True,
                'char_type': 2,
                'selected_evolution': 0,
                'wire_character_slot': 0,
                'zone_request_count': 1,
                'lobby_slots': {
                    0: {
                        'slot': 0, 'storage_slot': 2,
                        'name_hex': b'Azrok1'.hex(),
                        'species': 2, 'evolution': 0,
                    },
                    1: {
                        'slot': 1, 'storage_slot': 3,
                        'name_hex': b'Azrok2'.hex(),
                        'species': 1, 'evolution': 0,
                    },
                },
            })
            canonical = server._default_canonical_character_state()
            canonical['currency'] = 777
            self.assertTrue(server._save_canonical_character_state(canonical))
            canonical_path = server._canonical_state_path()
            # The post-logout roster refresh is rebuilt from durable account
            # files, so persist the second fixture character as a real slot.
            server.proto_state.update({
                'character_slot': 3,
                'char_name_raw': b'Azrok2',
                'char_type': 1,
                'selected_evolution': 0,
            })
            self.assertTrue(
                server._save_canonical_character_state(
                    server._default_canonical_character_state()
                )
            )
            server.proto_state.update({
                'character_slot': 2,
                'char_name_raw': b'Azrok1',
                'char_type': 2,
                'selected_evolution': 0,
            })
            server._bind_selected_character_identity()
            with open(canonical_path, 'rb') as saved_file:
                before_logout = saved_file.read()

            source = object()
            peer = object()
            server.connections = [source, peer]
            server.client_meta = {
                source: {
                    'entity_id': 2,
                    'room_kind': server_module.PLAZA_ROOM_KIND,
                    'room_name': 'plaza',
                    'x': 10, 'y': 20, 'heading': 3,
                    'movement_generation': 4,
                    'visible_remote_actor_ids': {3},
                    'roster_bootstrapped': True,
                    'ox_room_id': None,
                    'ox_round_generation': None,
                    'name': 'Azrok1', 'char_type': 2,
                    'proto_state': server.proto_state,
                },
                peer: {
                    'entity_id': 3,
                    'room_kind': server_module.PLAZA_ROOM_KIND,
                    'visible_remote_actor_ids': {2},
                    'proto_state': {},
                },
            }
            relays = []
            server._emit = lambda conn, data, **kwargs: relays.append((conn, data))

            frames = parse_frames(
                server, server._build_response(0x0002, b'', pkt_num=9)
            )
            with open(canonical_path, 'rb') as saved_file:
                after_logout = saved_file.read()

            self.assertEqual(frames, [(0x0002, b'')])
            self.assertEqual(before_logout, after_logout)
            self.assertEqual(server.proto_state['account_raw'], b'accountA')
            self.assertEqual(len(server.proto_state['lobby_slots']), 2)
            self.assertIsNone(server._selected_character_state_key())
            self.assertTrue(server.proto_state['explicit_character_logout'])
            self.assertTrue(server.proto_state['auto_select_existing_sent'])
            self.assertIsNone(server.client_meta[source]['room_kind'])
            self.assertEqual(server.client_meta[source]['visible_remote_actor_ids'], set())
            self.assertEqual(server.client_meta[peer]['visible_remote_actor_ids'], set())
            self.assertEqual(
                parse_frames(server, relays[0][1]),
                [(0x0067, struct.pack('<I', 2))],
            )

            self.assertIsNone(
                server._build_response(0x0007, bytes(0xC4), pkt_num=10)
            )
            completion = parse_frames(
                server, server._build_response(0x0001, b'', pkt_num=11)
            )
            self.assertEqual(completion, [(0x0001, b'\x00')])
            self.assertTrue(server.proto_state['logout_completion_0007_seen'])
            self.assertTrue(server.proto_state['logout_completion_0001_seen'])
            self.assertTrue(server.proto_state['logout_exit_response_sent'])
            with open(canonical_path, 'rb') as saved_file:
                self.assertEqual(saved_file.read(), before_logout)

            # The wrapper, not an in-process roster refresh, owns the return
            # to server selection after this clean original-client exit.
            heartbeat_frames = parse_frames(
                server, server._build_response(0x0016, b'\x00', pkt_num=12)
            )
            self.assertNotIn(0x0000, [opcode for opcode, _ in heartbeat_frames])

    def test_character_logout_rejects_nonempty_payload_without_state_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            selected_key = server._selected_character_state_key()

            self.assertIsNone(
                server._build_response(0x0002, b'\x00', pkt_num=1)
            )

        self.assertEqual(server._selected_character_state_key(), selected_key)
        self.assertNotIn('explicit_character_logout', server.proto_state)

    def test_kind3_exact_branch_requirements_include_inventory_for_aux5(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            snapshot = bytearray(0xC4)

            def set_stat(index, value):
                struct.pack_into('<H', snapshot, 0x0A + index * 2, value)

            set_stat(1, 25)
            for index in range(30, 66):
                set_stat(index, 120)
            set_stat(36, 450)
            set_stat(32, 450)
            set_stat(52, 120)

            self.assertFalse(server._kind3_requirements_met(state, snapshot, 5))
            state['inventory']['furniture'][16] = 1
            state['inventory']['furniture'][13] = 1
            self.assertTrue(server._kind3_requirements_met(state, snapshot, 5))

    def test_kind3_aux2_requires_exact_skill_sum_and_global_thresholds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            snapshot = bytearray(0xC4)

            def set_stat(index, value):
                struct.pack_into('<H', snapshot, 0x0A + index * 2, value)

            set_stat(1, 12)
            for index in range(30, 66):
                set_stat(index, 30)
            set_stat(42, 40)
            set_stat(43, 40)
            set_stat(31, 34)
            set_stat(32, 33)
            set_stat(33, 33)
            self.assertTrue(server._kind3_requirements_met(state, snapshot, 2))
            set_stat(33, 32)
            self.assertFalse(server._kind3_requirements_met(state, snapshot, 2))

    def test_character_delete_archives_account_slot_and_returns_0008_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            filename = 'a6163636f756e7441_s2_c417a726f6b31_state_v1.json'
            with open(os.path.join(temp_dir, filename), 'w', encoding='utf-8') as state_file:
                state_file.write('{"schema_version":1}')
            legacy = '417a726f6b31_c2s0007.bin'
            with open(os.path.join(temp_dir, legacy), 'wb') as raw_file:
                raw_file.write(b'\x00' * 0xC4)
            server.proto_state['lobby_slots'] = {
                0: {'slot': 0, 'storage_slot': 2, 'name_hex': '417a726f6b31'}
            }

            frames = parse_frames(
                server, server._build_response(0x0006, b'\x00', pkt_num=1)
            )
            archived = os.listdir(os.path.join(temp_dir, 'deleted'))
            receipt = dict(server.mutation_ring[-1])

        self.assertEqual(frames, [(0x0008, b'\x00\x00')])
        self.assertTrue(any(name.startswith(filename + '.') for name in archived))
        self.assertTrue(any(name.startswith(legacy + '.') for name in archived))
        self.assertEqual(receipt['kind'], 'character_delete')
        self.assertEqual(receipt['result'], 'committed')
        self.assertEqual(receipt['journal_status'], 'durable')
        self.assertEqual(receipt['metadata']['archive']['status'], 'archived')
        self.assertEqual(receipt['metadata']['archive']['moved_files'], 2)

    def test_character_create_delete_reconnect_lobby_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_state.update({
                'character_slot': 0,
                'char_name_raw': b'Player',
                'lobby_slots': {},
            })
            name = b'DeleteMe' + b'\x00' * 5

            created = server._build_response(
                0x0004, bytes((1,)) + name + b'\x00', pkt_num=1
            )
            canonical_name = (
                'a6163636f756e7441_s0_c44656c6574654d65_state_v1.json'
            )
            self.assertIsNotNone(created)
            self.assertTrue(os.path.exists(os.path.join(temp_dir, canonical_name)))

            first_reconnect = server_module.AzrokServer.__new__(
                server_module.AzrokServer
            )
            first_reconnect.proto_state = {
                'account_raw': b'accountA',
                'char_name_raw': b'Player',
            }
            first_reconnect.state_store_dir = temp_dir
            roster = first_reconnect._build_login_bootstrap_0000()
            self.assertEqual(roster[0x01], 1)
            self.assertEqual(
                roster[0x0E:0x1B].split(b'\x00', 1)[0], b'DeleteMe'
            )

            frames = parse_frames(
                server, server._build_response(0x0006, b'\x00', pkt_num=2)
            )
            self.assertEqual(frames, [(0x0008, b'\x00\x00')])
            self.assertFalse(os.path.exists(os.path.join(temp_dir, canonical_name)))
            archived = os.listdir(os.path.join(temp_dir, 'deleted'))
            self.assertTrue(
                any(name.startswith(canonical_name + '.') for name in archived)
            )

            second_reconnect = server_module.AzrokServer.__new__(
                server_module.AzrokServer
            )
            second_reconnect.proto_state = {
                'account_raw': b'accountA',
                'char_name_raw': b'Player',
            }
            second_reconnect.state_store_dir = temp_dir
            empty_roster = second_reconnect._build_login_bootstrap_0000()
            self.assertEqual(empty_roster[0x01], 0)
            self.assertEqual(empty_roster[0x02:0x06], b'\xFF' * 4)

    def test_non_tail_character_delete_archives_and_redensifies_logical_slots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            names = [
                'a6163636f756e7441_s0_c4669727374_state_v1.json',
                'a6163636f756e7441_s2_c5365636f6e64_state_v1.json',
            ]
            for name in names:
                with open(os.path.join(temp_dir, name), 'w', encoding='utf-8') as state_file:
                    state_file.write('{"schema_version":1}')
            server.proto_state['lobby_slots'] = {
                0: {'slot': 0, 'storage_slot': 0, 'name_hex': '4669727374'},
                1: {'slot': 1, 'storage_slot': 2, 'name_hex': '5365636f6e64'},
            }

            frames = parse_frames(
                server, server._build_response(0x0006, b'\x00', pkt_num=1)
            )

            self.assertEqual(frames, [(0x0008, b'\x00\x00')])
            self.assertFalse(os.path.exists(os.path.join(temp_dir, names[0])))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, names[1])))
            self.assertEqual(sorted(server.proto_state['lobby_slots']), [0])
            surviving = server.proto_state['lobby_slots'][0]
            self.assertEqual(surviving['slot'], 0)
            self.assertEqual(surviving['storage_slot'], 2)
            receipt = server.mutation_ring[-1]
            self.assertEqual(receipt['kind'], 'character_delete')
            self.assertEqual(receipt['result'], 'committed')
            self.assertEqual(receipt['metadata']['archive']['status'], 'archived')

    def test_character_delete_rolls_back_partial_archive_before_failure_ack(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            names = [
                'a6163636f756e7441_s2_c417a726f6b31_state_v1.json',
                'a6163636f756e7441_s2_c417a726f6b31_c2s0007.bin',
            ]
            for name in names:
                with open(os.path.join(temp_dir, name), 'wb') as state_file:
                    state_file.write(b'{}')
            server.proto_state['lobby_slots'] = {
                0: {'slot': 0, 'storage_slot': 2, 'name_hex': '417a726f6b31'}
            }
            real_replace = os.replace
            archive_moves = 0

            def flaky_replace(source, destination):
                nonlocal archive_moves
                if os.path.dirname(destination).endswith('deleted'):
                    archive_moves += 1
                    if archive_moves == 2:
                        raise OSError('injected archive failure')
                return real_replace(source, destination)

            with mock.patch.object(server_module.os, 'replace', side_effect=flaky_replace):
                frames = parse_frames(
                    server, server._build_response(0x0006, b'\x00', pkt_num=1)
                )

            self.assertEqual(frames, [(0x0008, b'\x00\x01')])
            self.assertTrue(all(os.path.exists(os.path.join(temp_dir, name)) for name in names))
            receipt = server.mutation_ring[-1]
            self.assertEqual(receipt['kind'], 'character_delete')
            self.assertEqual(receipt['result'], 'rejected')
            self.assertTrue(receipt['metadata']['archive']['rollback_attempted'])
            self.assertFalse(receipt['metadata']['archive']['rollback_failed'])

    def test_selected_slot_species_stage_drive_zone_and_invalid_slot_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_state['lobby_slots'] = {
                0: {
                    'slot': 0,
                    'storage_slot': 2,
                    'name_hex': '417a726f6b31',
                    'species': 1,
                    'evolution': 2,
                }
            }
            frames = parse_frames(
                server, server._build_response(0x0005, b'\x00', pkt_num=1)
            )
            zone = next(payload for opcode, payload in frames if opcode == 0x0007)

            self.assertEqual(zone[0x01:0x03], b'\x01\x02')
            self.assertIsNone(server._build_response(0x0005, b'\x01', pkt_num=2))

    def test_character_create_uses_free_storage_slot_and_saves_canonical_immediately(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_state.update({
                'character_slot': 0,
                'char_name_raw': b'Player',
                'lobby_slots': {
                    0: {
                        'slot': 0,
                        'storage_slot': 2,
                        'name_hex': '4f6c64',
                        'species': 2,
                        'evolution': 0,
                    }
                },
            })
            name = b'Newbie' + b'\x00' * 7
            payload = bytes((1,)) + name + bytes((1,))
            response = server._build_response(0x0004, payload, pkt_num=1)

            self.assertIsNotNone(response)
            self.assertEqual(server.proto_state['wire_character_slot'], 1)
            self.assertEqual(server.proto_state['character_slot'], 0)
            canonical = os.path.join(
                temp_dir,
                'a6163636f756e7441_s0_c4e6577626965_state_v1.json',
            )
            self.assertTrue(os.path.exists(canonical))
            self.assertNotIn('post_create_select_replay_pending', server.proto_state)
            frames = parse_frames(server, response)
            self.assertEqual([opcode for opcode, _payload in frames], [0x0006])
            self.assertEqual(frames[0][1], b'\x00\x00')
            self.assertTrue(server.proto_state['fresh_create_ack_sent'])
            selected = parse_frames(
                server, server._build_response(
                    0x0007, b'\x00' * 196, pkt_num=2
                )
            )
            self.assertEqual(
                [opcode for opcode, _payload in selected],
                [0x0003, 0x0007, 0x0005, 0x000A, 0x000B],
            )

    def test_existing_account_waits_for_real_client_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            self.assertTrue(server._save_canonical_character_state(state))
            canonical_path = server._canonical_state_path()
            with open(canonical_path, 'rb') as handle:
                before = handle.read()
            server.proto_state = {}
            login = bytearray(106)
            login[0] = 1
            login[1:9] = b'accountA'
            server._build_response(0x0000, login, pkt_num=1)
            for sequence in range(2, 14):
                frames = parse_frames(
                    server, server._build_response(0x0016, b'\x00', pkt_num=sequence)
                )
                self.assertTrue(all(opcode in (0x0016, 0x0004, 0x0000)
                                    for opcode, _payload in frames))
                self.assertIsNone(server._selected_character_state_key())
            self.assertTrue(server.proto_state['account_has_characters'])
            with open(canonical_path, 'rb') as handle:
                self.assertEqual(handle.read(), before)
            selected = parse_frames(
                server, server._build_response(0x0005, b'\x00', pkt_num=14)
            )
            self.assertIsNotNone(server._selected_character_state_key())
            self.assertIn(0x0007, [opcode for opcode, _payload in selected])
            zone = next(payload for opcode, payload in selected if opcode == 0x0007)
            self.assertEqual(zone[0xEA], 1)

    def test_fresh_account_waits_past_eight_heartbeats_for_real_create(self):
        with tempfile.TemporaryDirectory() as temp_dir, \
                mock.patch.object(server_module, 'CONTENT_PROFILE', 'playable'), \
                mock.patch.object(server_module, 'SERVER_AUTO_SELECT_EXISTING_ENABLED', True):
            server = self.make_server(temp_dir)
            server.proto_state = {}
            login = bytearray(106)
            login[0] = 1
            login[1:14] = b'FreshWait2026'
            self.assertIsNone(server._build_response(0x0000, login, pkt_num=1))

            for sequence in range(2, 14):
                frames = parse_frames(
                    server, server._build_response(0x0016, b'\x00', pkt_num=sequence)
                )
                self.assertTrue(all(opcode in (0x0016, 0x0004, 0x0000)
                                    for opcode, _payload in frames))
                self.assertFalse(server.proto_state.get('char_created'))
                self.assertIsNone(server._selected_character_state_key())
                self.assertEqual(os.listdir(temp_dir), [])

            create = bytes((2,)) + b'FreshSep9'.ljust(13, b'\x00') + b'\x00'
            ack = parse_frames(server, server._build_response(0x0004, create, pkt_num=14))
            self.assertEqual(ack, [(0x0006, b'\x00\x00')])
            self.assertTrue(os.path.isfile(server._canonical_state_path()))
            frames = parse_frames(
                server, server._build_response(0x0007, bytes(196), pkt_num=15)
            )
            self.assertEqual([opcode for opcode, _payload in frames],
                             [0x0003, 0x0007, 0x0005, 0x000A, 0x000B])
            zone = next(payload for opcode, payload in frames if opcode == 0x0007)
            self.assertEqual(struct.unpack_from('<I', zone, 3)[0], 0)
            self.assertEqual((zone[0xEA], zone[0xEB]), (1, 0))

    def test_first_account_character_create_does_not_schedule_select_replay(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_state['lobby_slots'] = {}
            name = b'First' + b'\x00' * 8
            payload = bytes((2,)) + name + bytes((0,))

            response = server._build_response(0x0004, payload, pkt_num=1)

            self.assertIsNotNone(response)
            self.assertNotIn('post_create_select_replay_pending', server.proto_state)
            frames = parse_frames(server, response)
            self.assertEqual([opcode for opcode, _payload in frames], [0x0006])
            self.assertEqual(frames[0][1], b'\x00\x00')
            self.assertTrue(server.proto_state['fresh_create_ack_sent'])
            self.assertTrue(server.proto_state['client_0005_seen'])

    def test_fresh_create_never_imports_same_name_legacy_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir, \
                mock.patch.object(server_module, 'CONTENT_PROFILE', 'playable'), \
                mock.patch.object(server_module, 'NATIVE_FRESH_TUTORIAL_ENABLED', True):
            server = self.make_server(temp_dir)
            server.proto_state.update({
                'character_slot': 0,
                'char_name_raw': b'Player',
                'lobby_slots': {},
            })
            legacy = bytearray(0xC4)
            legacy[0x05] = 1
            struct.pack_into('<H', legacy, 0x0A + 56 * 2, 3)
            with open(
                server._character_state_path(b'Azrok1'.hex()), 'wb'
            ) as legacy_file:
                legacy_file.write(legacy)

            name = b'Azrok1' + b'\x00' * 7
            response = server._build_response(
                0x0004, bytes((2,)) + name + bytes((0,)), pkt_num=1
            )
            ack = parse_frames(server, response)
            self.assertEqual([opcode for opcode, _payload in ack], [0x0006])
            self.assertEqual(ack[0][1], b'\x00\x00')
            frames = parse_frames(
                server, server._build_response(
                    0x0007, b'\x00' * 196, pkt_num=2
                )
            )
            zone = next(payload for opcode, payload in frames if opcode == 0x0007)

        self.assertEqual(struct.unpack_from('<I', zone, 0x03)[0], 0)
        self.assertEqual(zone[0x02], 0)
        self.assertEqual(
            struct.unpack_from('<H', zone, 0x0B + 56 * 2)[0],
            server_module.PLAYABLE_CONTENT_STATS[56],
        )
        self.assertTrue(server.proto_state['legacy_state_import_suppressed'])
        self.assertFalse(server.proto_state['saved_state_loaded'])
        self.assertNotIn('legacy_state_migrated_from', server.proto_state)
        self.assertNotIn('fresh_character_create_in_progress', server.proto_state)

    def make_purchase(self, item_ids, claimed_total, stack_tail=b''):
        payload = bytearray(0x2D)
        payload[0] = len(item_ids)
        struct.pack_into('<I', payload, 1, claimed_total)
        struct.pack_into(f'<{len(item_ids)}H', payload, 5, *item_ids)
        if stack_tail:
            start = 5 + len(item_ids) * 2
            payload[start:start + len(stack_tail)] = stack_tail[:0x2D - start]
        return bytes(payload)

    def test_purchase_decoder_ignores_uninitialized_tail(self):
        payload = self.make_purchase([1001], 50, b'\x48\x01\xFE\xFF' * 9)
        self.assertEqual(
            server_module.decode_c2s_purchase_0013(payload),
            (1, 50, [1001]),
        )
        self.assertEqual(len(server_module.SHOP_ITEM_CATALOG), 97)

    def test_purchase_commit_is_atomic_and_returns_unlock_ack(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['currency'] = 1000
            self.assertTrue(server._save_canonical_character_state(state))

            frames = parse_frames(
                server,
                server._build_response(
                    0x0013,
                    self.make_purchase([1001], 50, b'\x48\x01' * 19),
                    pkt_num=1,
                ),
            )
            loaded = server._load_canonical_character_state()

        self.assertEqual(frames, [(0x0005, struct.pack('<BBI', 0, 0x13, 950))])
        self.assertEqual(loaded['currency'], 950)
        self.assertEqual(loaded['inventory']['food'][1], 1)

    def test_purchase_rejects_forged_total_without_partial_mutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['currency'] = 1000
            self.assertTrue(server._save_canonical_character_state(state))

            frames = parse_frames(
                server,
                server._build_response(
                    0x0013, self.make_purchase([1001], 1), pkt_num=1
                ),
            )
            loaded = server._load_canonical_character_state()

        self.assertEqual(frames, [(0x0005, struct.pack('<BBI', 1, 0x13, 1000))])
        self.assertEqual(loaded['currency'], 1000)
        self.assertEqual(loaded['inventory']['food'][1], 0)

    def test_unselected_session_mutations_fail_closed_before_canonical_load(self):
        """A login/bootstrap Player placeholder is never storage authority."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_state.update({
                'character_slot': 0,
                'char_name_raw': b'Player',
                'zone_request_count': 1,
            })
            server.proto_state.pop('client_0005_seen', None)
            server.proto_state.pop('selected_character_key', None)
            server.saved_character_states = {}
            server.saved_server_states = {}

            purchase = parse_frames(
                server,
                server._build_response(
                    0x0013, self.make_purchase([5000], 0), pkt_num=1
                ),
            )
            self.assertIsNone(server._process_item_use(0x000F, b'\x00'))
            self.assertFalse(
                server._save_character_state_snapshot(bytes(0xC4))
            )
            created_files = os.listdir(temp_dir)
            self.assertEqual(created_files, ['mutation_transactions_v1.jsonl'])
            with open(
                os.path.join(temp_dir, created_files[0]), encoding='utf-8'
            ) as journal:
                rejected = [json.loads(line) for line in journal]

        self.assertEqual(
            purchase,
            [(0x0005, struct.pack('<BBI', 1, 0x13, 0))],
        )
        self.assertEqual(
            server.proto_state['last_purchase']['reason'],
            'purchase requires selected character identity',
        )
        self.assertEqual(
            server.proto_state['last_item_use']['reason'],
            'item use requires selected character identity',
        )
        self.assertEqual(
            server.proto_state['last_state_save_reject']['reason'],
            'state save requires selected character identity',
        )
        self.assertEqual([row['result'] for row in rejected],
                         ['rejected', 'rejected', 'rejected'])
        self.assertNotIn('6163636f756e7441', json.dumps(rejected))
        self.assertEqual(server.saved_server_states, {})

    def test_unselected_zone_overlay_cannot_import_player_legacy_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_state.update({
                'account_raw': b'accountA',
                'character_slot': 0,
                'char_name_raw': b'Player',
            })
            server.proto_state.pop('client_0005_seen', None)
            server.proto_state.pop('selected_character_key', None)
            server.saved_character_states = {}
            server.saved_server_states = {}
            legacy_key = b'Player'.hex()
            legacy_path = server._character_state_path(legacy_key)
            with open(legacy_path, 'wb') as legacy_file:
                legacy_file.write(bytes(0xC4))

            zone = bytearray(0x1D8)
            self.assertIsNone(
                server._build_response(0x0007, bytes(0xC4), pkt_num=1)
            )
            self.assertIsNone(server._load_character_state_snapshot())
            self.assertFalse(server._apply_saved_character_state(zone))
            self.assertFalse(server._apply_canonical_server_state(zone))
            player_canonical = server._canonical_state_path(
                f'a{b"accountA".hex()}_s0_c{b"Player".hex()}'
            )
            canonical_exists = os.path.exists(player_canonical)

        self.assertFalse(canonical_exists)
        self.assertEqual(server.saved_server_states, {})
        self.assertIsNone(server.proto_state['saved_state_key'])

    def test_unselected_0017_cannot_bleed_into_later_selected_character(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_state = {
                'account_raw': b'accountA',
                'account_name': 'accountA',
                'character_slot': 0,
                'char_name_raw': b'Player',
                'lobby_slots': {
                    0: {
                        'storage_slot': 2,
                        'species': 2,
                        'evolution': 0,
                        'name_hex': b'Ener103'.hex(),
                    },
                },
            }
            server.saved_character_states = {}
            server.saved_server_states = {}

            poison = struct.pack('<BBI', 0x07, 0x37, 999)
            self.assertIsNone(
                server._build_response(0x0017, poison, pkt_num=1)
            )
            self.assertNotIn('c2s_0017_stat_authority', server.proto_state)
            self.assertIsNotNone(
                server._build_response(0x0005, b'\x00', pkt_num=2)
            )
            self.assertIsNotNone(server._selected_character_state_key())

            incoming = bytearray(0xC4)
            incoming[0x05] = 0
            self.assertTrue(server._save_character_state_snapshot(incoming))
            selected_key = server._selected_character_state_key()
            server.saved_server_states = {}
            selected = server._load_canonical_character_state(key=selected_key)
            saved_snapshot = bytes.fromhex(selected['snapshot_hex'])
            stat55 = struct.unpack_from('<H', saved_snapshot, 0x0A + 0x37 * 2)[0]

        self.assertNotEqual(stat55, 999)
        self.assertEqual(
            server.proto_state['last_c2s_0017_reject']['reason'],
            'stat authority requires selected character identity',
        )

    def test_relogin_resets_stale_character_before_new_account_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_template = {
                'char_name_raw': b'Player',
                'account_raw': b'',
                'account_name': '',
                'character_slot': 0,
                'client_0005_seen': False,
                'selected_character_key': None,
                'login_response_sent': False,
            }
            server.proto_state = {
                'account_raw': b'accountA',
                'account_name': 'accountA',
                'character_slot': 2,
                'char_name_raw': b'EnerA',
                'client_0005_seen': True,
                'selected_character_key': (
                    f'a{b"accountA".hex()}_s2_c{b"EnerA".hex()}'
                ),
                'lobby_slots': {
                    0: {
                        'storage_slot': 2,
                        'species': 2,
                        'evolution': 0,
                        'name_hex': b'EnerA'.hex(),
                    },
                },
                'c2s_0017_stat_authority': {0x37: 999},
            }
            login = bytearray(0x6A)
            login[0] = 1
            login[1:9] = b'accountB'

            self.assertIsNone(
                server._build_response(0x0000, bytes(login), pkt_num=1)
            )
            self.assertIsNone(
                server._build_response(0x0005, b'\x00', pkt_num=2)
            )
            purchase = parse_frames(
                server,
                server._build_response(
                    0x0013, self.make_purchase([5000], 0), pkt_num=3
                ),
            )
            stale_cross_account = server._canonical_state_path(
                f'a{b"accountB".hex()}_s2_c{b"EnerA".hex()}'
            )
            stale_exists = os.path.exists(stale_cross_account)

        self.assertEqual(server.proto_state['account_raw'], b'accountB')
        self.assertEqual(server.proto_state['char_name_raw'], b'Player')
        self.assertNotIn('lobby_slots', server.proto_state)
        self.assertFalse(server.proto_state.get('client_0005_seen'))
        self.assertIsNone(server.proto_state.get('selected_character_key'))
        self.assertNotIn('c2s_0017_stat_authority', server.proto_state)
        self.assertEqual(
            purchase,
            [(0x0005, struct.pack('<BBI', 1, 0x13, 0))],
        )
        self.assertFalse(stale_exists)

    def test_concurrent_rejected_lease_purchase_cannot_target_player_canonical(self):
        """Reproduce seq116/117: rejected 0005 then raw 0013 beside owner."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            server.proto_lock = threading.RLock()
            server.ctl_lock = threading.RLock()
            server.proto_template = {}

            owner_state = {
                'account_raw': b'accountA',
                'account_name': 'accountA',
                'character_slot': 2,
                'wire_character_slot': 0,
                'char_name_raw': b'Ener103',
                'char_type': 2,
                'selected_evolution': 0,
                'client_0005_seen': True,
            }
            server.proto_state = owner_state
            owner_key = server._character_state_key()
            owner_state['selected_character_key'] = owner_key
            owner_canonical = server._default_canonical_character_state()
            owner_canonical['currency'] = 1000
            self.assertTrue(
                server._save_canonical_character_state(
                    owner_canonical, key=owner_key
                )
            )

            raw_state = {
                'account_raw': b'accountA',
                'account_name': 'accountA',
                'character_slot': 0,
                'char_name_raw': b'Player',
                'lobby_slots': {
                    0: {
                        'storage_slot': 2,
                        'species': 2,
                        'evolution': 0,
                        'name_hex': b'Ener103'.hex(),
                    },
                },
            }
            owner_conn = object()
            raw_conn = object()
            server.client_meta = {
                owner_conn: {
                    'name': 'Ener103', 'proto_state': owner_state,
                },
                raw_conn: {
                    'name': 'Player', 'proto_state': raw_state,
                },
            }
            server.proto_state = {}
            start = threading.Barrier(2)
            results = {}

            def owner_purchase():
                start.wait()
                with server._client_protocol_context(owner_conn):
                    results['owner'] = parse_frames(
                        server,
                        server._build_response(
                            0x0013, self.make_purchase([1001], 50), pkt_num=116
                        ),
                    )

            def raw_rejected_select_then_purchase():
                start.wait()
                with server._client_protocol_context(raw_conn):
                    results['raw_select'] = server._build_response(
                        0x0005, b'\x00', pkt_num=115
                    )
                    results['raw'] = parse_frames(
                        server,
                        server._build_response(
                            0x0013, self.make_purchase([5000], 0), pkt_num=117
                        ),
                    )

            threads = [
                threading.Thread(target=owner_purchase),
                threading.Thread(target=raw_rejected_select_then_purchase),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertTrue(all(not thread.is_alive() for thread in threads))

            server.saved_server_states = {}
            owner_after = server._load_canonical_character_state(key=owner_key)
            player_key = f'a{b"accountA".hex()}_s0_c{b"Player".hex()}'
            player_path = server._canonical_state_path(player_key)
            player_exists = os.path.exists(player_path)

        self.assertIsNone(results['raw_select'])
        self.assertEqual(
            results['owner'],
            [(0x0005, struct.pack('<BBI', 0, 0x13, 950))],
        )
        self.assertEqual(
            results['raw'],
            [(0x0005, struct.pack('<BBI', 1, 0x13, 0))],
        )
        self.assertEqual(owner_after['currency'], 950)
        self.assertEqual(owner_after['inventory']['food'][1], 1)
        self.assertEqual(owner_after['inventory']['energy'][0], 0)
        self.assertFalse(player_exists)
        self.assertNotIn('selected_character_key', raw_state)
        self.assertEqual(
            raw_state['last_character_select_reject']['reason'],
            'character already active on another connection',
        )
        self.assertEqual(
            raw_state['last_purchase']['reason'],
            'purchase requires selected character identity',
        )

    def test_toy_and_gym_loadouts_persist_without_consuming_ownership(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            for index in (0, 2, 4, 6):
                state['inventory']['toy'][index] = 1
            for index in (0, 3, 6):
                state['inventory']['gym'][index] = 1
            self.assertTrue(server._save_canonical_character_state(state))

            self.assertIsNone(server._process_item_use(0x000D, b'\x00\x02\x04\x06'))
            self.assertIsNone(server._process_item_use(0x000E, b'\x00\x03\x06'))
            server.saved_server_states = {}
            loaded = server._load_canonical_character_state()

        self.assertEqual(loaded['active_loadouts']['toy'], [0, 2, 4, 6])
        self.assertEqual(loaded['active_loadouts']['gym'], [0, 3, 6])
        self.assertEqual([loaded['inventory']['toy'][i] for i in (0, 2, 4, 6)], [1] * 4)
        self.assertEqual([loaded['inventory']['gym'][i] for i in (0, 3, 6)], [1] * 3)

    def test_s2c_0007_never_truncates_toy_gym_loadouts_into_effect_bytes(self):
        """+0x125 is 11 furniture u8 ids, not a loadout restoration field."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            for index in (0, 2, 4, 6):
                state['inventory']['toy'][index] = 1
            state['active_loadouts']['toy'] = [0, 2, 4, 6]
            state['active_loadouts']['gym'] = [0, 3, 6]
            self.assertTrue(server._save_canonical_character_state(state))

            zone = server._build_zone_0007_draft(b'')

        self.assertEqual(zone[0x125:0x130], b'\xFF' * 11)
        # Ownership still restores through the proven quantity arrays.
        self.assertEqual(zone[0x113:0x11D], bytes(state['inventory']['toy']))
        self.assertEqual(zone[0x11D:0x125], bytes(state['inventory']['gym']))

    def test_client_granted_defaults_and_toy_residue_are_interoperable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            fresh = server._load_canonical_character_state()
            self.assertEqual([fresh['inventory']['toy'][i] for i in (1, 4, 7)], [1] * 3)
            self.assertEqual([fresh['inventory']['gym'][i] for i in (0, 3, 6)], [1] * 3)

            # FUN_0059C790 returns three default toy entries but its caller
            # transmits four bytes.  0xFE models the undefined trailing byte.
            self.assertIsNone(server._process_item_use(0x000D, b'\x01\x04\x07\xFE'))
            # An in-range but unowned residue must also be ignored.
            self.assertIsNone(server._process_item_use(0x000D, b'\x01\x04\x07\x08'))
            loaded = server._load_canonical_character_state()

        self.assertEqual(loaded['active_loadouts']['toy'], [1, 4, 7])

    def test_energy_consumption_is_atomic_and_acknowledged_only_after_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['inventory']['energy'][1] = 2
            self.assertTrue(server._save_canonical_character_state(state))

            response = server._process_item_use(0x000F, b'\x01')
            self.assertEqual(parse_frames(server, response), [(0x0009, b'\x00\x0F')])
            committed = server._load_canonical_character_state()
            self.assertEqual(committed['inventory']['energy'][1], 1)

            with mock.patch.object(
                server, '_save_canonical_character_state', return_value=False
            ):
                self.assertIsNone(server._process_item_use(0x000F, b'\x01'))

        self.assertEqual(server._load_canonical_character_state()['inventory']['energy'][1], 1)

    def test_0014_food_waits_for_0008_and_medicine_alone_decrements(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['inventory']['food'][9] = 2
            state['inventory']['ingredient'][0] = 2
            state['inventory']['drug'][0] = 2
            self.assertTrue(server._save_canonical_character_state(state))

            self.assertEqual(
                server_module.decode_c2s_item_consume_0014(struct.pack('<H', 1009)),
                1009,
            )
            self.assertIsNone(
                server._build_response(0x0014, struct.pack('<H', 1009), pkt_num=31)
            )
            witnessed = server._load_canonical_character_state()
            self.assertEqual(witnessed['inventory']['food'][9], 2)
            self.assertEqual(
                server.proto_state['last_item_consume']['status'],
                'witness_pending_0008',
            )

            food = list(witnessed['inventory']['food'])
            food[9] = 1
            ingredient = list(witnessed['inventory']['ingredient'])
            ingredient[0] = 1
            payload_0008 = bytes(food + ingredient)
            self.assertIsNone(
                server._build_response(0x0008, payload_0008, pkt_num=32)
            )
            correlated = server.proto_state['last_inventory_snapshot']['correlated_0014']
            self.assertEqual(correlated['food_quantity_before'], 2)
            self.assertEqual(correlated['food_quantity_after'], 1)
            self.assertEqual(correlated['food_quantity_delta'], -1)
            self.assertEqual(correlated['action_projection'], 'consume')
            self.assertEqual(correlated['ingredient_delta'], [-1, 0, 0])

            self.assertIsNone(
                server._build_response(0x0014, struct.pack('<H', 4000), pkt_num=33)
            )
            server.saved_server_states = {}
            committed = server._load_canonical_character_state()

        self.assertEqual(committed['inventory']['food'][9], 1)
        self.assertEqual(committed['inventory']['ingredient'][0], 1)
        self.assertEqual(committed['inventory']['drug'][0], 1)
        self.assertEqual(
            server.proto_state['last_item_consume']['status'],
            'committed_medicine_delta',
        )

    def test_0014_empty_food_slot_is_a_production_witness_until_0008(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['inventory']['ingredient'][0] = 2
            self.assertTrue(server._save_canonical_character_state(state))
            self.assertEqual(state['inventory']['food'][6], 0)
            self.assertEqual(state['inventory']['ingredient'][0], 2)

            self.assertIsNone(
                server._build_response(0x0014, struct.pack('<H', 1006), pkt_num=41)
            )
            self.assertEqual(
                server.proto_state['last_item_consume']['status'],
                'witness_pending_0008',
            )
            self.assertEqual(server._load_canonical_character_state()['inventory']['food'][6], 0)

            food = list(state['inventory']['food'])
            food[6] = 1
            ingredient = list(state['inventory']['ingredient'])
            ingredient[0] = 1
            self.assertIsNone(
                server._build_response(0x0008, bytes(food + ingredient), pkt_num=42)
            )
            correlated = server.proto_state['last_inventory_snapshot']['correlated_0014']

        self.assertEqual(correlated['item_id'], 1006)
        self.assertEqual(correlated['food_quantity_before'], 0)
        self.assertEqual(correlated['food_quantity_after'], 1)
        self.assertEqual(correlated['food_quantity_delta'], 1)
        self.assertEqual(correlated['action_projection'], 'produce')
        self.assertEqual(correlated['ingredient_delta'], [-1, 0, 0])

    def test_0014_rejects_non_wire_domains_malformed_unknown_and_unowned_drug(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            before = server._load_canonical_character_state()
            for payload in (
                b'\x00', struct.pack('<H', 9999),
                struct.pack('<H', 1500), struct.pack('<H', 2000),
                struct.pack('<H', 2500), struct.pack('<H', 3000),
                struct.pack('<H', 5000), struct.pack('<H', 0),
            ):
                self.assertIsNone(server._process_item_consume_0014(payload, pkt_num=40))
            after = server._load_canonical_character_state()
        self.assertEqual(after['inventory'], before['inventory'])
        self.assertEqual(server.proto_state['last_item_consume']['status'], 'rejected')

    def test_exact_inventory_snapshots_atomically_replace_without_ack(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            food = [0] * 38
            food[0], food[32] = 4, 7
            ingredient = [3, 2, 1]
            self.assertIsNone(
                server._build_response(0x0008, bytes(food + ingredient), pkt_num=50)
            )
            self.assertIsNone(
                server._build_response(0x0009, bytes(range(1, 11)), pkt_num=51)
            )
            self.assertIsNone(
                server._build_response(0x000A, bytes(range(1, 9)), pkt_num=52)
            )
            server.saved_server_states = {}
            loaded = server._load_canonical_character_state()
            self.assertEqual(loaded['inventory']['food'], food)
            self.assertEqual(loaded['inventory']['ingredient'], ingredient)
            self.assertEqual(loaded['inventory']['toy'], list(range(1, 11)))
            self.assertEqual(loaded['inventory']['gym'], list(range(1, 9)))

            before = json.loads(json.dumps(loaded['inventory']))
            with mock.patch.object(
                server, '_save_canonical_character_state', return_value=False
            ):
                self.assertIsNone(
                    server._process_inventory_snapshot(0x0009, b'\x09' * 10, pkt_num=53)
                )
            self.assertEqual(server._load_canonical_character_state()['inventory'], before)

    def test_inventory_growth_decoders_reject_wrong_shapes(self):
        projection = server_module.decode_c2s_inventory_snapshot(
            0x0008, bytes([1] * 33 + [0] * 5 + [2, 3, 4])
        )
        self.assertEqual(projection['food'][:2], [1, 1])
        self.assertEqual(projection['ingredient'], [2, 3, 4])
        self.assertEqual(
            server_module.decode_c2s_growth_route_0010(b'\x06\x01'),
            (6, 1),
        )
        empty = [{'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(10)]
        payload = struct.pack(
            '<10H10H10I',
            *[row['kind'] for row in empty],
            *[row['aux'] for row in empty],
            *[row['value'] for row in empty],
        )
        self.assertEqual(server_module.decode_c2s_runtime_rows_0011(payload), empty)
        stale_empty = list(empty)
        stale_empty[1] = {'kind': 0xFF, 'aux': 1001, 'value': 26073020}
        stale_payload = struct.pack(
            '<10H10H10I',
            *[row['kind'] for row in stale_empty],
            *[row['aux'] for row in stale_empty],
            *[row['value'] for row in stale_empty],
        )
        self.assertEqual(
            server_module.decode_c2s_runtime_rows_0011(stale_payload), empty
        )
        for call in (
            lambda: server_module.decode_c2s_inventory_snapshot(0x0008, b'\0' * 40),
            lambda: server_module.decode_c2s_inventory_snapshot(
                0x0008, bytes([0] * 33 + [1] + [0] * 7)
            ),
            lambda: server_module.decode_c2s_growth_route_0010(b'\x07\x00'),
            lambda: server_module.decode_c2s_growth_route_0010(b'\x00\x02'),
            lambda: server_module.decode_c2s_runtime_rows_0011(b'\0' * 79),
        ):
            with self.assertRaises(ValueError):
                call()

    def test_0010_0011_correlate_rows_and_preserve_server_next_route(self):
        def pack_rows(rows):
            return struct.pack(
                '<10H10H10I',
                *[row['kind'] for row in rows],
                *[row['aux'] for row in rows],
                *[row['value'] for row in rows],
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['runtime_rows'] = [
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(10)
            ]
            state['runtime_row_meta'] = [
                {'generation': 0, 'issued_evolution': 0} for _ in range(10)
            ]
            snapshot = bytearray(0xC4)
            snapshot[5] = 0
            state['snapshot_hex'] = snapshot.hex()
            self.assertTrue(server._save_canonical_character_state(state))

            self.assertIsNone(server._build_response(0x0010, b'\x02\x00', pkt_num=60))
            inserted = [
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(10)
            ]
            inserted[0] = {'kind': 3, 'aux': 2, 'value': 0}
            self.assertIsNone(
                server._build_response(0x0011, pack_rows(inserted), pkt_num=61)
            )
            self.assertEqual(
                server._load_canonical_character_state()['runtime_rows'][0], inserted[0]
            )

            self.assertIsNone(server._build_response(0x0010, b'\x02\x01', pkt_num=62))
            advanced = server._load_canonical_character_state()
            snapshot[5] = 1
            advanced['snapshot_hex'] = snapshot.hex()
            advanced['runtime_rows'][0] = {'kind': 3, 'aux': 4, 'value': 0}
            advanced['runtime_row_meta'][0] = {
                'generation': 2, 'issued_evolution': 1,
            }
            self.assertTrue(server._save_canonical_character_state(advanced))
            removed = [
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(10)
            ]
            self.assertIsNone(
                server._build_response(0x0011, pack_rows(removed), pkt_num=63)
            )
            final = server._load_canonical_character_state()
            self.assertEqual(
                final['runtime_rows'][0], {'kind': 3, 'aux': 4, 'value': 0}
            )
            self.assertEqual(final['runtime_row_meta'][0]['generation'], 2)

    def test_food_quest_0012_and_stale_empty_0011_credit_funcorn_atomically(self):
        def pack_rows(rows):
            return struct.pack(
                '<10H10H10I',
                *[row['kind'] for row in rows],
                *[row['aux'] for row in rows],
                *[row['value'] for row in rows],
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['currency'] = 950
            state['inventory']['food'] = [0] * 38
            state['inventory']['food'][1] = 1
            state['inventory']['ingredient'] = [0, 0, 0]
            state['runtime_rows'] = [
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(10)
            ]
            state['runtime_rows'][1] = {
                'kind': 0, 'aux': 1001, 'value': 26073020,
            }
            state['runtime_row_meta'] = [
                {'generation': 0, 'issued_evolution': 1} for _ in range(10)
            ]
            state['runtime_row_meta'][1]['generation'] = 1
            state['completed_runtime_rows'] = []
            self.assertTrue(server._save_canonical_character_state(state))

            self.assertIsNone(
                server._build_response(0x0014, struct.pack('<H', 1001), pkt_num=70)
            )
            self.assertIsNone(
                server._build_response(0x0008, b'\0' * 41, pkt_num=71)
            )
            self.assertIsNone(
                server._build_response(0x0012, struct.pack('<IB', 40, 2), pkt_num=72)
            )
            outgoing = [dict(row) for row in state['runtime_rows']]
            outgoing[1] = {'kind': 0xFF, 'aux': 1001, 'value': 26073020}
            ack = server._build_response(
                0x0011, pack_rows(outgoing), pkt_num=73
            )
            self.assertEqual(
                server._make_packet(0x0005, struct.pack('<BBI', 0, 0x12, 990)),
                ack,
            )

            final = server._load_canonical_character_state()
            self.assertEqual(0, final['inventory']['food'][1])
            self.assertEqual(990, final['currency'])
            self.assertEqual(
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0},
                final['runtime_rows'][1],
            )
            self.assertEqual(1, len(final['completed_runtime_rows']))
            self.assertEqual(
                'committed', server.proto_state['last_quest_reward']['status']
            )
            self.assertEqual(
                990, server.proto_state['last_quest_reward']['funcorn_after']
            )
            self.assertEqual(
                '0x12', server.proto_state['last_quest_reward']['ack_subtype']
            )

            self.assertIsNone(
                server._build_response(0x0012, struct.pack('<IB', 40, 2), pkt_num=74)
            )
            self.assertEqual(
                'rejected', server.proto_state['last_quest_reward']['status']
            )
            self.assertEqual(990, server._load_canonical_character_state()['currency'])

            with self.assertRaises(ValueError):
                server_module.decode_c2s_quest_reward_0012(
                    struct.pack('<IB', 40, 1)
                )

    def test_tutorial_0011_then_0012_then_next_0011_credits_funcorn(self):
        def pack_rows(rows):
            return struct.pack(
                '<10H10H10I',
                *[row['kind'] for row in rows],
                *[row['aux'] for row in rows],
                *[row['value'] for row in rows],
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            state = server._load_canonical_character_state()
            state['currency'] = 0
            state['runtime_rows'] = [
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(10)
            ]
            state['runtime_rows'][0] = {'kind': 5, 'aux': 212, 'value': 0}
            state['runtime_row_meta'] = [
                {'generation': 0, 'issued_evolution': 0} for _ in range(10)
            ]
            state['runtime_row_meta'][0]['generation'] = 1
            state['completed_runtime_rows'] = []
            self.assertTrue(server._save_canonical_character_state(state))

            retired = [
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(10)
            ]
            self.assertIsNone(
                server._build_response(0x0011, pack_rows(retired), pkt_num=80)
            )
            # Retirement is buffered rather than being persisted without its
            # immediately following FunCorn reward.
            self.assertEqual(
                {'kind': 5, 'aux': 212, 'value': 0},
                server._load_canonical_character_state()['runtime_rows'][0],
            )
            ack = server._build_response(
                0x0012, struct.pack('<IB', 100, 2), pkt_num=81
            )
            self.assertEqual(
                server._make_packet(0x0005, struct.pack('<BBI', 0, 0x12, 100)),
                ack,
            )
            committed = server._load_canonical_character_state()
            self.assertEqual(100, committed['currency'])
            self.assertEqual(
                {'kind': 0xFF, 'aux': 0xFF, 'value': 0},
                committed['runtime_rows'][0],
            )
            self.assertEqual(1, len(committed['completed_runtime_rows']))

            next_rows = [dict(row) for row in retired]
            next_rows[0] = {'kind': 5, 'aux': 202, 'value': 0}
            self.assertIsNone(
                server._build_response(0x0011, pack_rows(next_rows), pkt_num=82)
            )
            final = server._load_canonical_character_state()
            self.assertEqual({'kind': 5, 'aux': 202, 'value': 0}, final['runtime_rows'][0])
            self.assertEqual(100, final['currency'])
            self.assertEqual('committed', server.proto_state['last_quest_reward']['status'])

    def test_all_quest_funcorn_tables_match_static_switches(self):
        expected = {}
        expected.update({(0, aux): 40 for aux in (1001, 1002, 1003)})
        expected.update({(0, aux): 45 for aux in (1004, 1005)})
        expected.update({(0, aux): 38 for aux in (1006, 1007, 1008, 1009)})
        expected.update({(0, aux): 43 for aux in range(1015, 1020)})
        expected.update({(0, aux): 48 for aux in range(1024, 1029)})
        expected.update({(1, aux): 22 for aux in range(31, 40)})
        expected.update({(1, aux): 19 for aux in range(40, 45)})
        expected.update({(1, aux): 21 for aux in range(49, 54)})
        expected.update({(1, aux): 24 for aux in range(58, 63)})
        expected.update({(2, aux): 24 for aux in range(1006, 1011)})
        expected.update({(2, aux): 29 for aux in range(1015, 1020)})
        expected.update({(2, aux): 35 for aux in range(1024, 1029)})
        expected.update({(5, aux): 100 for aux in (212, 202, 203, 227, 201)})

        for row, amount in expected.items():
            with self.subTest(row=row):
                self.assertEqual(
                    server_module.quest_funcorn_reward_for_runtime_row(*row),
                    amount,
                )
        for row in ((0, 1000), (0, 1010), (1, 30), (1, 63),
                    (2, 0xCF), (2, 0x102), (3, 0), (5, 200)):
            with self.subTest(unrewarded=row):
                self.assertIsNone(
                    server_module.quest_funcorn_reward_for_runtime_row(*row)
                )

    def test_kind0_kind1_kind2_reward_then_retire_ack_matrix(self):
        def pack_rows(rows):
            return struct.pack(
                '<10H10H10I',
                *[row['kind'] for row in rows],
                *[row['aux'] for row in rows],
                *[row['value'] for row in rows],
            )

        for quest_kind, quest_aux, amount in (
            (0, 1004, 45),
            (1, 31, 22),
            (2, 1006, 24),
        ):
            with self.subTest(kind=quest_kind, aux=quest_aux), \
                    tempfile.TemporaryDirectory() as temp_dir:
                server = self.make_server(temp_dir)
                state = server._load_canonical_character_state()
                state['currency'] = 100
                state['runtime_rows'] = [
                    {'kind': 0xFF, 'aux': 0xFF, 'value': 0} for _ in range(10)
                ]
                state['runtime_rows'][2] = {
                    'kind': quest_kind, 'aux': quest_aux, 'value': 0,
                }
                state['runtime_row_meta'] = [
                    {'generation': 0, 'issued_evolution': 0} for _ in range(10)
                ]
                state['runtime_row_meta'][2]['generation'] = 1
                state['completed_runtime_rows'] = []
                self.assertTrue(server._save_canonical_character_state(state))

                self.assertIsNone(server._build_response(
                    0x0012, struct.pack('<IB', amount, 2), pkt_num=90
                ))
                retired = [dict(row) for row in state['runtime_rows']]
                retired[2] = {'kind': 0xFF, 'aux': 0xFF, 'value': 0}
                ack = server._build_response(
                    0x0011, pack_rows(retired), pkt_num=91
                )
                expected_balance = 100 + amount
                self.assertEqual(
                    server._make_packet(
                        0x0005, struct.pack('<BBI', 0, 0x12, expected_balance)
                    ),
                    ack,
                )
                final = server._load_canonical_character_state()
                self.assertEqual(expected_balance, final['currency'])
                self.assertEqual(
                    {'kind': 0xFF, 'aux': 0xFF, 'value': 0},
                    final['runtime_rows'][2],
                )
                self.assertEqual(1, len(final['completed_runtime_rows']))

    def test_item_use_rejects_unowned_out_of_range_and_malformed_loadouts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server = self.make_server(temp_dir)
            self.assertIsNone(server._process_item_use(0x000F, b'\x00'))
            self.assertIsNone(server._process_item_use(0x000F, b'\x03'))
            self.assertIsNone(server._process_item_use(0x000D, b'\x00\x00\x01\x02'))
            state = server._load_canonical_character_state()

        self.assertEqual(state['inventory']['energy'], [0] * 20)
        self.assertEqual(state['active_loadouts']['toy'], [1, 4, 7])


class ChatContractTests(unittest.TestCase):
    def make_chat(self, chat_type=0, flag=0, target=b'', message=b'hello'):
        payload = bytearray(0x12 + len(message))
        payload[0] = chat_type
        payload[1] = flag
        payload[2:2 + min(13, len(target))] = target[:13]
        payload[0x0F] = 0
        payload[0x10] = len(message) + 1
        payload[0x11:0x11 + len(message)] = message
        payload[-1] = 0
        return bytes(payload)

    def test_chat_decoder_and_text_builder_offsets(self):
        chat = server_module.decode_c2s_0068_chat(
            self.make_chat(chat_type=1, flag=7, target=b'Peer', message=b'hello')
        )
        self.assertEqual(chat['target_raw'], b'Peer')
        self.assertEqual(chat['message_raw'], b'hello')

        server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        out = server._build_state_006A_text_record(1, 7, 22, b'Sender', b'hello')
        self.assertEqual(out[0:2], b'\x01\x07')
        self.assertEqual(struct.unpack_from('<I', out, 2)[0], 22)
        self.assertEqual(out[6:13], b'Sender\x00')
        self.assertEqual(out[0x15:], b'hello\x00')

    def test_public_chat_routes_to_self_and_same_plaza_peers(self):
        server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        source = object()
        peer = object()
        local_room = object()
        server.connections = [source, peer, local_room]
        server.client_meta = {
            source: {'entity_id': 2, 'name': 'Sender', 'account': 'a', 'room_kind': server_module.PLAZA_ROOM_KIND},
            peer: {'entity_id': 3, 'name': 'Peer', 'account': 'b', 'room_kind': server_module.PLAZA_ROOM_KIND},
            local_room: {'entity_id': 4, 'name': 'Local', 'account': 'c', 'room_kind': 8},
        }
        server.ctl_lock = threading.RLock()
        server.event_ring = []
        server.event_seq = 0
        emitted = []
        server._emit = lambda conn, data, **kwargs: emitted.append((conn, data)) or True

        self.assertTrue(server._relay_chat_0068(source, self.make_chat(), pkt_num=9))
        self.assertEqual([conn for conn, _data in emitted], [source, peer])
        self_id = parse_frames(server, emitted[0][1])[0][1]
        peer_id = parse_frames(server, emitted[1][1])[0][1]
        self.assertEqual(struct.unpack_from('<I', self_id, 2)[0], 1)
        self.assertEqual(struct.unpack_from('<I', peer_id, 2)[0], 2)


class PlazaMovementRelayContractTests(unittest.TestCase):
    """C2S 0x0066 carries a duration; S2C 0x0068 record[5] needs a deadline.

    0x0061A710 gates the whole walk branch - the walk state and the
    ``vec_to_angle`` facing alike - on ``synced_now < record[5]``, so
    ``record[5]`` must be absolute.  The C2S side measured 217 and 795 ms on
    two live click-to-move steps, so it is relative.  Forwarding it verbatim
    fails that comparison on the first frame and renders as a teleport with no
    facing; so does falling back to a lone placement frame.  Doc 538.
    """

    def make_server(self):
        server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        source = object()
        peer = object()
        server.connections = [source, peer]
        server.ctl_lock = threading.RLock()
        server.client_meta = {
            source: {
                'entity_id': 2, 'room_kind': server_module.PLAZA_ROOM_KIND,
                'visible_remote_actor_ids': set(), 'movement_generation': 0,
                'x': 100, 'y': 100, 'heading': 0,
            },
            peer: {
                'entity_id': 3, 'room_kind': server_module.PLAZA_ROOM_KIND,
                'visible_remote_actor_ids': {2}, 'movement_generation': 0,
            },
        }
        server.event_ring = []
        server.event_seq = 0
        emitted = []
        server._emit = lambda conn, data, **kwargs: emitted.append((conn, data)) or True
        return server, source, peer, emitted

    def records(self, server, emitted):
        out = []
        for _conn, data in emitted:
            for opcode, payload in parse_frames(server, data):
                self.assertEqual(opcode, 0x0068)
                self.assertEqual(len(payload), server_module.STATE_0068_RECORD_SIZE)
                out.append(struct.unpack('<6I', payload))
        return out

    def test_measured_duration_becomes_an_absolute_deadline(self):
        server, source, peer, emitted = self.make_server()
        before = int(time.time() * 1000) & 0xFFFFFFFF
        # 217 is one of the two durations measured on the wire.
        self.assertTrue(server._start_plaza_movement_relay(
            source, 2, 100, 100, 400, 500, 217, 0, pkt_num=7,
        ))
        after = int(time.time() * 1000) & 0xFFFFFFFF
        # One packet, not an interpolated burst.
        self.assertEqual([conn for conn, _d in emitted], [peer])
        record = self.records(server, emitted)[0]
        self.assertEqual(record[0], 2)
        self.assertEqual((record[1], record[2]), (100, 100))
        self.assertEqual((record[3], record[4]), (400, 500))
        self.assertNotEqual(record[5], 0, 'record[5] == 0 is the idle branch')
        self.assertNotEqual(record[5], 217, 'a duration on the wire is a teleport')
        self.assertTrue(before + 217 <= record[5] <= after + 217, record[5])
        # The destination becomes authoritative; the client animates the way.
        self.assertEqual(
            (server.client_meta[source]['x'], server.client_meta[source]['y']),
            (400, 500),
        )
        self.assertEqual(server.client_meta[source]['movement_duration_ms'], 217)

    def test_zero_duration_places_the_actor_without_a_walking_record(self):
        server, source, peer, emitted = self.make_server()
        self.assertTrue(server._start_plaza_movement_relay(
            source, 2, 100, 100, 400, 500, 0, 0, pkt_num=7,
        ))
        record = self.records(server, emitted)[0]
        self.assertEqual(record[5], 0)
        self.assertEqual((record[1], record[2]), (400, 500))
        self.assertEqual(server.client_meta[source]['movement_duration_rejects'], 1)

    def test_implausible_duration_never_becomes_a_deadline(self):
        server, source, peer, emitted = self.make_server()
        absurd = server_module.PLAZA_MOVEMENT_MAX_DURATION_MS + 1
        self.assertTrue(server._start_plaza_movement_relay(
            source, 2, 100, 100, 400, 500, absurd, 0, pkt_num=7,
        ))
        self.assertEqual(self.records(server, emitted)[0][5], 0)
        self.assertEqual(server.client_meta[source]['movement_arrival_tick'], 0)

    def test_negative_duration_is_rejected_not_wrapped(self):
        # decode_c2s_0066 reads this dword with '<i'.  A negative value must
        # not become a huge unsigned deadline.
        server, source, peer, emitted = self.make_server()
        self.assertTrue(server._start_plaza_movement_relay(
            source, 2, 100, 100, 400, 500, -5000, 0, pkt_num=7,
        ))
        self.assertEqual(self.records(server, emitted)[0][5], 0)
        self.assertEqual(server.client_meta[source]['movement_duration_rejects'], 1)

    def test_invisible_peer_still_gates_the_walking_record(self):
        server, source, peer, emitted = self.make_server()
        server.client_meta[peer]['visible_remote_actor_ids'] = set()
        self.assertFalse(server._start_plaza_movement_relay(
            source, 2, 100, 100, 400, 500, 1200, 0, pkt_num=7,
        ))
        self.assertEqual(emitted, [])


class SocialStateContractTests(unittest.TestCase):
    def make_server(self):
        server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        source = object()
        peer = object()
        local_room = object()
        server.connections = [source, peer, local_room]
        server.client_meta = {
            source: {
                'entity_id': 2,
                'room_kind': server_module.PLAZA_ROOM_KIND,
                'visible_remote_actor_ids': {3},
            },
            peer: {
                'entity_id': 3,
                'room_kind': server_module.PLAZA_ROOM_KIND,
                'visible_remote_actor_ids': {2},
            },
            local_room: {
                'entity_id': 4,
                'room_kind': 8,
                'visible_remote_actor_ids': set(),
            },
        }
        server.ctl_lock = threading.RLock()
        server.event_ring = []
        server.event_seq = 0
        emitted = []
        server._emit = lambda conn, data, **kwargs: emitted.append((conn, data)) or True
        return server, source, peer, local_room, emitted

    def test_community_self_selection_gets_full_latch_compatible_response(self):
        server, source, peer, _local_room, emitted = self.make_server()
        self.assertEqual(
            server_module.decode_c2s_006c_community(struct.pack('<I', 1)), 1
        )
        self.assertTrue(
            server._relay_community_006c(source, struct.pack('<I', 1), pkt_num=12)
        )
        self.assertEqual(
            parse_frames(server, emitted[0][1]),
            [(0x0070, struct.pack('<BBHII', 1, 1, 0, 0, 0))],
        )
        self.assertTrue(server.event_ring[-1]['details']['relay'])
        self.assertEqual(
            server.event_ring[-1]['details']['reply_opcode'],
            '0x0070',
        )
        self.assertEqual(server.event_ring[-1]['details']['reply_form'], 'latched_12_byte')
        self.assertEqual(
            server.event_ring[-1]['details']['verified_c2s_fields'],
            ['target_actor_id'],
        )
        self.assertEqual(server.event_ring[-1]['details']['target_kind'], 'self')

    def test_community_answers_visible_peer_with_unranked_info(self):
        # Measured 2026-07-30: clicking the other avatar sends that peer's id,
        # not 1.  Treating it as impersonation dropped every remote-targeted
        # request, so clicking a remote character did nothing.
        server, source, peer, _local_room, emitted = self.make_server()
        server.client_meta[peer]['proto_state'] = {
            'client_0005_seen': True,
            'selected_character_key': 'peer-character',
        }
        snapshot = bytearray(0xC4)
        struct.pack_into('<H', snapshot, 0x0A + 1 * 2, 7)
        struct.pack_into('<H', snapshot, 0x0A + 2 * 2, 4321)
        server.saved_server_states = {
            'peer-character': {'snapshot_hex': snapshot.hex()},
        }
        self.assertTrue(server._relay_community_006c(source, struct.pack('<I', 3), pkt_num=5))
        self.assertTrue(server._relay_community_006c(source, struct.pack('<I', 3), pkt_num=6))
        self.assertEqual(len(emitted), 2)
        self.assertIs(emitted[1][0], source)
        self.assertEqual(
            parse_frames(server, emitted[0][1]),
            [(0x0070, struct.pack('<BBHII', 7, 1, 0, 0, 0))],
        )
        self.assertEqual(
            parse_frames(server, emitted[1][1]),
            [(0x0070, struct.pack('<BBHII', 7, 1, 0, 0, 0))],
        )
        details = server.event_ring[-1]['details']
        self.assertEqual(details['target_actor_id'], 3)
        self.assertEqual(details['target_kind'], 'visible_peer')
        self.assertTrue(details['relay'])
        self.assertEqual(details['reply_form'], 'latched_12_byte')
        self.assertEqual(details['score_state'], 'unranked')
        self.assertEqual(
            server.client_meta[source]['community_target_actor_id'], 3
        )

    def test_community_rejects_bad_length_and_invisible_target(self):
        server, source, _peer, _local_room, emitted = self.make_server()
        self.assertFalse(server._relay_community_006c(source, b'\x01', pkt_num=1))
        self.assertFalse(
            server._relay_community_006c(source, struct.pack('<I', 99), pkt_num=2)
        )
        self.assertEqual(emitted, [])
        self.assertEqual(
            [event['kind'] for event in server.event_ring],
            ['community_reject', 'community_reject'],
        )

    def test_community_latched_full_response_reaches_real_socket(self):
        server, source, _peer, _local_room, _emitted = self.make_server()
        sending, receiving = socket.socketpair()
        receiving.settimeout(2)
        try:
            server.connections[0] = sending
            server.client_meta[sending] = server.client_meta.pop(source)
            server.paused = False
            server._log_packet = lambda *args, **kwargs: None
            server._emit = server_module.AzrokServer._emit.__get__(server)
            for expected in (
                struct.pack('<BBHII', 1, 1, 0, 0, 0),
                struct.pack('<BBHII', 1, 1, 0, 0, 0),
            ):
                self.assertTrue(server._relay_community_006c(
                    sending, struct.pack('<I', 3), pkt_num=1,
                ))
                frame = receiving.recv(16)
                self.assertEqual(
                    frame, struct.pack('<HH', len(expected), 0x0070) + expected,
                )
        finally:
            sending.close()
            receiving.close()

    def test_accessory_0018_and_000c_exact_codecs(self):
        self.assertEqual(
            server_module.decode_c2s_0018_accessory(b'\x00\x03\x07'),
            (0, 3, 7),
        )
        self.assertEqual(
            server_module.decode_c2s_0018_accessory(b'\x01\x03\x07'),
            (1, 3, 7),
        )
        self.assertEqual(
            server_module.build_s2c_accessory_000c(3, 0, 3, 7),
            struct.pack('<IBBB', 3, 0, 3, 7),
        )

    def test_accessory_codecs_reject_bad_shape_action_slot_and_apply_value(self):
        for payload in (
            b'\x00\x00', b'\x02\x00\x01', b'\x00\x04\x01',
            b'\x00\x01\x07',
        ):
            with self.assertRaises(ValueError):
                server_module.decode_c2s_0018_accessory(payload)
        with self.assertRaises(ValueError):
            server_module.build_s2c_accessory_000c(0, 0, 0, 0)


class OxMode2ContractTests(unittest.TestCase):
    def make_server(self):
        server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        self.a = object()
        self.b = object()
        server.connections = [self.a, self.b]
        server.client_meta = {
            self.a: {
                'entity_id': 2, 'name': 'Alice', 'char_type': 1,
                'room_kind': server_module.PLAZA_ROOM_KIND,
                'x': 100, 'y': 200, 'proto_state': {},
                'visible_remote_actor_ids': set(),
            },
            self.b: {
                'entity_id': 3, 'name': 'Bob', 'char_type': 2,
                'room_kind': server_module.PLAZA_ROOM_KIND,
                'x': -100, 'y': 200, 'proto_state': {},
                'visible_remote_actor_ids': set(),
            },
        }
        server.ctl_lock = threading.RLock()
        server.proto_lock = threading.RLock()
        server.proto_state = {}
        server.event_ring = []
        server.event_seq = 0
        server.paused = False
        server.packet_ring = []
        server.emit_seq = 0
        self.emitted = []
        server._emit = (
            lambda conn, data, **kwargs:
            self.emitted.append((conn, data, kwargs.get('origin'))) or True
        )
        server._ensure_ox_runtime()
        return server

    def frames_for(self, server, conn):
        frames = []
        for target, raw, _origin in self.emitted:
            if target is conn:
                frames.extend(parse_frames(server, raw))
        return frames

    def enter_both(self, server):
        self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        self.assertTrue(server._handle_ox_enter(self.b, b'', pkt_num=2))

    def test_natural_006b_portal_request_is_plaza_scoped_and_emits_exact_006e(self):
        server = self.make_server()
        self.assertFalse(server._handle_ox_enter(
            self.a, b'', pkt_num=6, require_portal=True
        ))
        self.assertEqual(server.client_meta[self.a]['room_kind'], server_module.PLAZA_ROOM_KIND)
        self.assertTrue(server._handle_ox_portal_request_006b(self.a, b'', pkt_num=7))
        self.assertEqual(self.frames_for(server, self.a), [(0x006E, b'\x00\x00')])
        self.assertEqual(self.emitted[-1][2], 'ox')
        self.assertEqual(server.event_ring[-1]['details']['next_expected'], 'C2S 0x00C8')

        # A duplicate click while the client is changing scene must not emit
        # a second hazardous ready commit.
        self.assertTrue(server._handle_ox_portal_request_006b(self.a, b'', pkt_num=8))
        self.assertEqual(self.frames_for(server, self.a), [(0x006E, b'\x00\x00')])

        server.client_meta[self.b]['room_kind'] = server_module.LOCAL_PAT_HOUSE_ROOM_KIND
        self.assertFalse(server._handle_ox_portal_request_006b(self.b, b'', pkt_num=9))
        self.assertFalse(server._handle_ox_portal_request_006b(self.a, b'\x00', pkt_num=10))

        server.client_meta[self.a]['ox_portal_006b_at'] = (
            time.monotonic() - server_module.OX_PORTAL_C8_TTL_SECONDS - 1.0
        )
        self.assertFalse(server._handle_ox_enter(
            self.a, b'', pkt_num=11, require_portal=True
        ))
        self.assertTrue(server._handle_ox_portal_request_006b(self.a, b'', pkt_num=12))
        self.assertTrue(server._handle_ox_enter(
            self.a, b'', pkt_num=13, require_portal=True
        ))
        self.assertEqual(server.client_meta[self.a]['room_kind'], server_module.LOCAL_OX_ROOM_KIND)

    def test_exact_builders_and_fail_closed_ranges(self):
        c8 = server_module.build_s2c_ox_enter_00c8(x=-7, y=9)
        self.assertEqual(len(c8), 14)
        self.assertEqual(struct.unpack('<BBIii', c8), (0, 0, 0, -7, 9))
        c9 = server_module.build_s2c_ox_remote_00c9(
            2, 1, b'A', 4, 5, level_marker=7,
            descriptor_1=9, appearance=b'\x01\x02\x03\x04',
        )
        self.assertEqual(len(c9), 32)
        self.assertEqual(c9[0], 7)
        self.assertEqual(struct.unpack_from('<I', c9, 1)[0], 2)
        self.assertEqual(c9[5:7], b'\x01\x09')
        self.assertEqual(c9[7:20], b'A\x00' + b'\x00' * 11)
        self.assertEqual(c9[0x14:0x18], b'\x01\x02\x03\x04')
        self.assertEqual(struct.unpack_from('<ii', c9, 0x18), (4, 5))
        ce = server_module.build_s2c_ox_question_00ce(
            '1 + 1 = 2', 0, 0, 3
        )
        self.assertEqual(len(ce), 0x83)
        self.assertEqual(ce[0x80:], b'\x00\x00\x03')
        with self.assertRaises(ValueError):
            server_module.decode_c2s_ox_enter_00c8(b'\x00')
        with self.assertRaises(ValueError):
            server_module.build_s2c_ox_question_00ce('bad', 4, 0, 1)
        with self.assertRaises(ValueError):
            server_module.build_s2c_ox_question_00ce('bad', 0, 0, 4)
        with self.assertRaises(ValueError):
            server_module.validate_s2c_ox_payload(0x00D0, b'\x00' * 23)

        runtime_timeout_ca = bytes.fromhex(
            '0100000000000000000000000000000000f78fdc7201'
        )
        decoded_ca = server_module.decode_c2s_ox_answer_00ca(runtime_timeout_ca)
        self.assertEqual(decoded_ca['side'], 1)
        self.assertEqual(decoded_ca['current_x'], 0)
        self.assertEqual(decoded_ca['destination_x'], 0)
        self.assertEqual(decoded_ca['timing'], 0x72DC8FF7)
        self.assertTrue(decoded_ca['timeout'])
        self.assertEqual(server_module.decode_c2s_ox_leave_00c9(b'\x00'), 0)
        for malformed in (
            b'', b'\x00' * 21, b'\x00' * 23,
            struct.pack('<BiiiiiB', 2, 0, 0, 0, 0, 0, 0),
            struct.pack('<BiiiiiB', 0, 0, 0, 0, 0, 0, 2),
            struct.pack('<BiiiiiB', 0, 0, 0, 1, 0, 0, 1),
        ):
            with self.assertRaises(ValueError):
                server_module.decode_c2s_ox_answer_00ca(malformed)
        with self.assertRaises(ValueError):
            server_module.decode_c2s_ox_leave_00c9(b'')

        server = self.make_server()
        c2s_semantics = server._packet_semantics('C->S', 0x00C8, b'')
        c9_semantics = server._packet_semantics('C->S', 0x00C9, b'\x00')
        ca_semantics = server._packet_semantics(
            'C->S', 0x00CA, runtime_timeout_ca
        )
        s2c_semantics = server._packet_semantics('S->C', 0x00CE, ce, origin='ox')
        self.assertEqual(c2s_semantics['category'], 'ox')
        self.assertEqual(c2s_semantics['decoded']['scene_ready'], True)
        self.assertEqual(c9_semantics['category'], 'ox')
        self.assertEqual(c9_semantics['decoded']['level_marker'], 0)
        self.assertEqual(ca_semantics['category'], 'ox')
        self.assertEqual(ca_semantics['decoded']['side'], 1)
        self.assertTrue(ca_semantics['decoded']['timeout'])
        self.assertEqual(s2c_semantics['category'], 'ox')
        self.assertEqual(s2c_semantics['decoded']['correct_side'], 0)

    def test_packet_semantics_metadata_and_lengths_come_from_shared_registry(self):
        server = self.make_server()
        accessory = find_spec('S->C', 0x000C)
        semantics = server._packet_semantics(
            'S->C', 0x000C, struct.pack('<IBBB', 7, 0, 1, 2), origin='relay'
        )
        self.assertEqual(accessory.label, semantics['meaning'])
        self.assertEqual(accessory.category, semantics['category'])
        self.assertEqual(accessory.risk, semantics['risk'])
        self.assertEqual(accessory.stable_id, semantics['protocol_spec_id'])
        self.assertIsNone(semantics['contract_length_error'])

        malformed = server._packet_semantics('S->C', 0x0067, b'\0' * 8)
        self.assertIn('expected 4B', malformed['contract_length_error'])
        self.assertEqual({}, malformed['decoded'])
        unknown = server._packet_semantics('C->S', 0xBEEF, b'')
        self.assertEqual('unknown', unknown['category'])
        self.assertIsNone(unknown['protocol_spec_id'])
        self.assertNotIn('catalog =', inspect.getsource(server_module.AzrokServer._packet_semantics))

    def test_enter_is_separate_from_ready_question_and_roster_ids_are_remote(self):
        server = self.make_server()
        self.enter_both(server)
        a_frames = self.frames_for(server, self.a)
        b_frames = self.frames_for(server, self.b)
        self.assertEqual([op for op, _ in a_frames], [0x00C8, 0x00C9])
        self.assertEqual([op for op, _ in b_frames], [0x00C8, 0x00C9])
        self.assertEqual(struct.unpack_from('<I', a_frames[1][1], 1)[0], 3)
        self.assertEqual(struct.unpack_from('<I', b_frames[1][1], 1)[0], 2)
        self.assertNotIn(0x00CC, [op for op, _ in a_frames + b_frames])
        self.assertNotIn(0x00CE, [op for op, _ in a_frames + b_frames])

        before = server.ox_snapshot()
        self.emitted.clear()
        self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=3))
        self.assertEqual(self.emitted, [])
        self.assertEqual(server.ox_snapshot(), before)

    def test_plaza_to_ox_removes_old_state1_actor_before_admission(self):
        server = self.make_server()
        server.client_meta[self.b]['visible_remote_actor_ids'] = {2}
        self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        b_frames = self.frames_for(server, self.b)
        self.assertEqual([op for op, _ in b_frames], [0x0067])
        self.assertEqual(struct.unpack('<I', b_frames[0][1])[0], 2)
        self.assertEqual(server.client_meta[self.a]['room_kind'], server_module.LOCAL_OX_ROOM_KIND)

    def test_ca_side_is_answer_and_cb_translates_self_per_recipient(self):
        server = self.make_server()
        self.enter_both(server)
        self.emitted.clear()
        self.assertEqual(server.ox_prepare(), (True, 'OX ready countdown sent'))
        ok, _msg = server.ox_open_question(
            question_index=0, duration_ms=1000, now=100.0
        )
        self.assertTrue(ok)

        # Generic movement remains useful telemetry, but cannot submit an OX
        # answer.  Dedicated CA byte 0 is the authoritative side selection.
        movement_a = struct.pack('<BiiiiiB', 20, 0, -1, -1, -1, 250, 0)
        movement_b = struct.pack('<BiiiiiB', 14, -1, -1, 0, -1, 250, 0)
        with mock.patch.object(server_module.time, 'monotonic', return_value=100.5):
            server._relay_to_room_peers(self.a, 0x0066, movement_a, pkt_num=3)
            server._relay_to_room_peers(self.b, 0x0066, movement_b, pkt_num=4)

        # Movement to the peer is mode-2 D0; state-1 0068 is forbidden.
        movement_ops = [
            op for conn in (self.a, self.b)
            for op, _payload in self.frames_for(server, conn)
        ]
        self.assertIn(0x00D0, movement_ops)
        self.assertNotIn(0x0068, movement_ops)

        answer_a = struct.pack('<BiiiiiB', 0, 0, -1, -1, -1, 250, 0)
        answer_b = struct.pack('<BiiiiiB', 1, -1, -1, 0, -1, 250, 0)
        self.assertTrue(server._handle_ox_answer_00ca(
            self.a, answer_a, pkt_num=5, received_at=100.5
        ))
        self.assertTrue(server._handle_ox_answer_00ca(
            self.b, answer_b, pkt_num=6, received_at=100.5
        ))

        self.assertTrue(server.ox_tick(now=101.0)[0])
        a_cb = [p for op, p in self.frames_for(server, self.a) if op == 0x00CB][-1]
        b_cb = [p for op, p in self.frames_for(server, self.b) if op == 0x00CB][-1]
        self.assertEqual(struct.unpack('<I', a_cb)[0], 3)
        self.assertEqual(struct.unpack('<I', b_cb)[0], 1)
        self.assertEqual(server.ox_snapshot()['rooms']['default']['survivors'], [2])

        self.emitted.clear()
        self.assertTrue(server.ox_finish(exit_mode='cd')[0])
        a_cd = [p for op, p in self.frames_for(server, self.a) if op == 0x00CD][-1]
        b_cd = [p for op, p in self.frames_for(server, self.b) if op == 0x00CD][-1]
        self.assertEqual(struct.unpack('<I', a_cd)[0], 1)
        self.assertEqual(struct.unpack('<I', b_cd)[0], 2)

    def test_deadline_equality_and_late_generation_are_fail_closed(self):
        server = self.make_server()
        self.enter_both(server)
        server.ox_prepare()
        server.ox_open_question(question_index=0, duration_ms=1000, now=10.0)
        answer = struct.pack('<BiiiiiB', 0, 0, 0, 10, 10, 250, 0)
        self.assertFalse(
            server._handle_ox_answer_00ca(
                self.a, answer, pkt_num=3, received_at=11.0
            )
        )
        self.assertTrue(server.ox_tick(now=11.0)[0])
        self.assertEqual(
            server.ox_snapshot()['rooms']['default']['losers'], [2, 3]
        )

        server.ox_prepare()
        server.ox_open_question(question_index=0, duration_ms=1000, now=20.0)
        with server.ctl_lock:
            server.client_meta[self.a]['ox_round_generation'] -= 1
        self.assertFalse(
            server._handle_ox_answer_00ca(
                self.a, answer, pkt_num=4, received_at=20.5
            )
        )

    def test_c9_immediately_exits_arms_hansol_and_returns_000d_prelude(self):
        server = self.make_server()
        self.enter_both(server)
        self.assertTrue(server.ox_prepare()[0])
        self.emitted.clear()

        self.assertTrue(server._handle_ox_leave_00c9(
            self.a, b'\x00', pkt_num=7
        ))
        room = server.ox_snapshot()['rooms']['default']
        self.assertEqual(room['participants'], [3])
        self.assertEqual(room['survivors'], [3])
        self.assertIsNone(server.client_meta[self.a]['room_kind'])
        self.assertEqual(
            server.client_meta[self.a]['room_name'], 'Plaza transition pending'
        )
        self.assertEqual(self.frames_for(server, self.a), [(0x000D, b'\x00')])
        b_frames = self.frames_for(server, self.b)
        self.assertEqual([op for op, _payload in b_frames], [0x00CA])
        self.assertEqual(struct.unpack('<I', b_frames[0][1])[0], 2)

        proto = server.client_meta[self.a]['proto_state']
        self.assertTrue(proto['hansol_calibration_active'])
        self.assertEqual(proto['hansol_calibration_samples_sent'], 0)
        self.assertEqual(proto['calib_0004_count'], 0)
        with server._client_protocol_context(self.a):
            calibration = server._build_response(0x0016, b'\x01', pkt_num=8)
        frames = parse_frames(server, calibration)
        self.assertIn(0x0004, [opcode for opcode, _payload in frames])
        sample = [payload for opcode, payload in frames if opcode == 0x0004][-1]
        self.assertEqual(sample[0], 1)
        self.assertEqual(proto['hansol_calibration_samples_sent'], 1)

        # The same exact teardown may race another departure path.
        before = list(self.emitted)
        self.assertTrue(server._handle_ox_leave_00c9(
            self.a, b'\x00', pkt_num=9
        ))
        self.assertEqual(self.emitted, before)
        self.assertFalse(server._handle_ox_leave_00c9(
            self.b, b'', pkt_num=10
        ))

    def test_finish_causes_are_mutually_exclusive_and_disconnect_broadcasts_ca(self):
        server = self.make_server()
        self.enter_both(server)
        self.emitted.clear()
        server.ox_prepare()
        server.ox_open_question(question_index=0, duration_ms=1, now=1.0)
        server.ox_tick(now=1.001)
        self.emitted.clear()
        self.assertTrue(server.ox_finish()[0])
        for conn in (self.a, self.b):
            self.assertEqual(
                [op for op, _payload in self.frames_for(server, conn)],
                [0x00CD],
            )
        self.assertTrue(all(len(parse_frames(server, raw)) == 1 for _c, raw, _o in self.emitted))

        for exit_mode, expected_opcode in (('d2', 0x00D2), ('d4', 0x00D4)):
            server = self.make_server()
            self.enter_both(server)
            server.ox_prepare()
            self.emitted.clear()
            self.assertTrue(server.ox_finish(exit_mode=exit_mode)[0])
            for conn in (self.a, self.b):
                self.assertEqual(
                    [op for op, _payload in self.frames_for(server, conn)],
                    [expected_opcode],
                )
        self.assertFalse(server.ox_finish(exit_mode='pair')[0])

        server = self.make_server()
        self.enter_both(server)
        self.emitted.clear()
        self.assertTrue(server._ox_remove_participant(self.a, pkt_num=9))
        b_frames = self.frames_for(server, self.b)
        self.assertEqual([op for op, _ in b_frames], [0x00CA])
        self.assertEqual(struct.unpack('<I', b_frames[0][1])[0], 2)

    def test_last_disconnect_cancels_stale_round_for_next_admission(self):
        server = self.make_server()
        self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        server.ox_prepare()
        server.ox_open_question(question_index=0, duration_ms=1000, now=1.0)
        self.assertTrue(server._ox_remove_participant(self.a, pkt_num=2))
        with server.ctl_lock:
            server.connections.remove(self.a)
            server.client_meta.pop(self.a)

        empty = server.ox_snapshot()['rooms']['default']
        self.assertEqual(empty['phase'], 'idle')
        self.assertEqual(empty['participants'], [])
        self.assertIsNone(empty['deadline_at'])
        self.assertIsNone(empty['question'])

        self.assertTrue(server._handle_ox_enter(self.b, b'', pkt_num=3))
        self.assertTrue(server.ox_prepare()[0])
        self.assertTrue(server.ox_open_question(
            question_index=0, duration_ms=1000, now=2.0
        )[0])

    def test_d2_natural_0064_return_removes_ox_member_and_rearms_plaza_roster(self):
        server = self.make_server()
        self.enter_both(server)
        self.emitted.clear()
        server.client_meta[self.a]['roster_bootstrapped'] = True
        server.client_meta[self.a]['visible_remote_actor_ids'] = {3}
        self.assertTrue(server._prepare_ox_plaza_return(self.a, pkt_num=8))
        server.proto_state = server.client_meta[self.a]['proto_state']
        server._update_client_identity(self.a, 0x0064, b'\x00')

        room = server.ox_snapshot()['rooms']['default']
        self.assertEqual(room['participants'], [3])
        self.assertEqual(room['survivors'], [3])
        self.assertEqual(server.client_meta[self.a]['room_kind'], server_module.PLAZA_ROOM_KIND)
        self.assertFalse(server.client_meta[self.a]['roster_bootstrapped'])
        self.assertEqual(server.client_meta[self.a]['visible_remote_actor_ids'], set())
        b_ca = self.frames_for(server, self.b)
        self.assertEqual([op for op, _ in b_ca], [0x00CA])
        self.assertEqual(struct.unpack('<I', b_ca[0][1])[0], 2)

    def test_direct_0065_exit_clears_ox_generation_and_state1_visibility(self):
        server = self.make_server()
        self.enter_both(server)
        server.ox_prepare()
        server.ox_open_question(question_index=0, duration_ms=1000, now=1.0)
        server.client_meta[self.a]['visible_remote_actor_ids'] = {3, 99}
        self.emitted.clear()

        payload = struct.pack(
            '<BBii', server_module.PLAZA_ROOM_KIND, 0, 10, 20
        )
        server._relay_to_room_peers(self.a, 0x0065, payload, pkt_num=8)

        meta = server.client_meta[self.a]
        self.assertEqual(meta['room_kind'], server_module.PLAZA_ROOM_KIND)
        self.assertIsNone(meta['ox_room_id'])
        self.assertIsNone(meta['ox_round_generation'])
        self.assertFalse(meta['roster_bootstrapped'])
        self.assertEqual(meta['visible_remote_actor_ids'], set())
        self.assertNotIn(2, server.ox_snapshot()['rooms']['default']['participants'])
        self.assertEqual(
            [op for op, _payload in self.frames_for(server, self.b)], [0x00CA]
        )

    def test_midround_c8_is_spectator_until_next_fresh_match(self):
        server = self.make_server()
        self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        server.ox_prepare()
        server.ox_open_question(question_index=0, duration_ms=1000, now=1.0)

        self.assertTrue(server._handle_ox_enter(self.b, b'', pkt_num=2))
        open_room = server.ox_snapshot()['rooms']['default']
        self.assertEqual(open_room['participants'], [2, 3])
        self.assertEqual(open_room['survivors'], [2])

        self.assertTrue(server._handle_ox_answer_00ca(
            self.a, struct.pack('<BiiiiiB', 0, 0, -1, 0, -1, 250, 0),
            pkt_num=3, received_at=1.5,
        ))
        self.assertTrue(server.ox_tick(now=2.0)[0])
        closed = server.ox_snapshot()['rooms']['default']
        self.assertEqual(closed['losers'], [])
        self.assertEqual(closed['survivors'], [2])

        server.ox_finish(exit_mode='d4')
        server.ox_prepare()
        fresh = server.ox_snapshot()['rooms']['default']
        self.assertEqual(fresh['survivors'], [2, 3])

    def test_explicit_side_cell_configuration_is_validated(self):
        server = self.make_server()
        self.assertTrue(server.ox_configure([21], [14])[0])
        self.assertEqual(server.ox_snapshot()['side_cells'], {'0': [21], '1': [14]})
        custom = [
            {'text': '5 > 2', 'type': 0, 'correct_side': 0, 'stars': 2}
        ]
        self.assertTrue(server.ox_configure(questions=custom)[0])
        self.assertEqual(server.ox_snapshot()['question_count'], 1)
        self.assertFalse(server.ox_configure([], None)[0])
        self.assertFalse(server.ox_configure([36], None)[0])
        self.assertFalse(server.ox_configure(questions=[])[0])
        self.assertFalse(server.ox_configure(side0_cells=[14])[0])
        self.assertFalse(server.ox_configure(questions=[{
            'text': 123, 'correct_side': 0,
        }])[0])
        self.assertFalse(server.ox_configure(questions=[{
            'text': 'emoji \U0001f600', 'correct_side': 0,
        }])[0])
        self.assertFalse(server.ox_open_question(question_index=-1)[0])

    def test_ca_side_is_authoritative_over_diagnostic_side_cells(self):
        server = self.make_server()
        self.enter_both(server)
        server.ox_prepare()
        server.ox_open_question(question_index=0, duration_ms=1000, now=5.0)
        self.assertTrue(server.ox_configure(side0_cells=[22])[0])
        # Coordinates/cells intentionally disagree with the configured side;
        # the dedicated side byte still controls judgement.
        self.assertTrue(server._handle_ox_answer_00ca(
            self.a, struct.pack('<BiiiiiB', 0, 9999, 9999, -5, -5, 1, 0),
            pkt_num=3, received_at=5.5,
        ))
        server.ox_tick(now=6.0)
        self.assertEqual(server.ox_snapshot()['rooms']['default']['survivors'], [2])

    def test_finished_prepare_starts_fresh_match_but_closed_prepare_keeps_survivors(self):
        server = self.make_server()
        self.enter_both(server)
        server.ox_prepare()
        server.ox_open_question(question_index=0, duration_ms=1, now=1.0)
        server._handle_ox_answer_00ca(
            self.a, struct.pack('<BiiiiiB', 0, 0, -1, 0, -1, 0, 0),
            pkt_num=3, received_at=1.0005,
        )
        server.ox_tick(now=1.001)
        server.ox_prepare()
        closed_next = server.ox_snapshot()['rooms']['default']
        self.assertEqual(closed_next['survivors'], [2])
        self.assertEqual(closed_next['generation'], 1)

        server.ox_finish(exit_mode='d4')
        server.ox_prepare()
        fresh = server.ox_snapshot()['rooms']['default']
        self.assertEqual(fresh['survivors'], [2, 3])
        self.assertEqual(fresh['generation'], 0)
        self.assertEqual(fresh['answers'], {})
        self.assertEqual(fresh['losers'], [])
        self.assertEqual(len(fresh['history']), 1)
        self.assertEqual(fresh['match_generation'], 2)
        self.assertIsNone(fresh['finish_exit_mode'])

    def test_automatic_solo_correct_round_finishes_cd_and_keeps_c9_000d_return(self):
        server = self.make_server()
        self.assertTrue(server.ox_configure_automation(
            admission_grace_ms=1000,
            ready_delay_ms=500,
            question_duration_ms=1000,
            result_hold_ms=500,
            exit_stall_ms=1000,
            max_rounds=1,
        )[0])
        with mock.patch.object(server_module.time, 'monotonic', return_value=10.0):
            self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        self.emitted.clear()

        self.assertEqual(server.ox_auto_step(now=10.999), [])
        self.assertEqual(server.ox_auto_step(now=11.0)[0]['action'], 'prepare')
        self.assertEqual(self.frames_for(server, self.a), [(0x00CC, b'')])

        self.assertEqual(
            server.ox_auto_step(now=11.5)[0]['action'], 'open_question'
        )
        self.assertEqual(self.frames_for(server, self.a)[-1][0], 0x00CE)
        answer = struct.pack('<BiiiiiB', 0, 0, 0, -310, -616, 250, 0)
        self.assertTrue(server._handle_ox_answer_00ca(
            self.a, answer, pkt_num=2, received_at=12.0
        ))
        self.assertEqual(
            server.ox_auto_step(now=12.5)[0]['action'], 'close_question'
        )
        self.assertEqual(self.frames_for(server, self.a)[-1], (0x00CB, b''))
        self.assertEqual(server.ox_auto_step(now=13.0)[0]['action'], 'finish_cd')
        self.assertEqual(
            self.frames_for(server, self.a)[-1],
            (0x00CD, struct.pack('<I', 1)),
        )

        self.emitted.clear()
        self.assertTrue(server._handle_ox_leave_00c9(
            self.a, b'\x00', pkt_num=3
        ))
        self.assertEqual(self.frames_for(server, self.a), [(0x000D, b'\x00')])
        snapshot = server.ox_snapshot()
        self.assertEqual(snapshot['timer_mode'], 'automatic-after-client-c8')
        self.assertEqual(snapshot['admission_mode'], 'client_c8_only')
        self.assertFalse(snapshot['unsolicited_006e'])

    def test_automatic_two_client_round_eliminates_one_then_finishes_survivor(self):
        server = self.make_server()
        server.ox_configure_automation(
            admission_grace_ms=1000,
            ready_delay_ms=500,
            question_duration_ms=1000,
            result_hold_ms=500,
            exit_stall_ms=1000,
            max_rounds=2,
        )
        with mock.patch.object(server_module.time, 'monotonic', return_value=1.0):
            self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        with mock.patch.object(server_module.time, 'monotonic', return_value=1.2):
            self.assertTrue(server._handle_ox_enter(self.b, b'', pkt_num=2))
        self.emitted.clear()

        server.ox_auto_step(now=2.2)
        server.ox_auto_step(now=2.7)
        answer_a = struct.pack('<BiiiiiB', 0, 0, 0, -310, -616, 1, 0)
        answer_b = struct.pack('<BiiiiiB', 1, 0, 0, 344, -419, 1, 0)
        self.assertTrue(server._handle_ox_answer_00ca(
            self.a, answer_a, pkt_num=3, received_at=3.0
        ))
        self.assertTrue(server._handle_ox_answer_00ca(
            self.b, answer_b, pkt_num=4, received_at=3.0
        ))
        server.ox_auto_step(now=3.7)
        self.assertEqual(
            server.ox_snapshot()['rooms']['default']['survivors'], [2]
        )

        # The verified loser path owns its C9 before the result hold chooses
        # CD for the sole remaining survivor.
        self.assertTrue(server._handle_ox_leave_00c9(
            self.b, b'\x00', pkt_num=5
        ))
        self.emitted.clear()
        transition = server.ox_auto_step(now=4.2)[0]
        self.assertEqual(transition['action'], 'finish_cd')
        self.assertEqual(self.frames_for(server, self.b), [])
        self.assertEqual(
            self.frames_for(server, self.a),
            [(0x00CD, struct.pack('<I', 1))],
        )
        self.assertTrue(server._handle_ox_leave_00c9(
            self.a, b'\x00', pkt_num=6
        ))
        self.assertEqual(
            server.ox_snapshot()['rooms']['default']['phase'], 'idle'
        )

    def test_automatic_two_client_tie_advances_then_finishes_at_round_limit(self):
        server = self.make_server()
        server.ox_configure_automation(
            admission_grace_ms=0,
            ready_delay_ms=100,
            question_duration_ms=1000,
            result_hold_ms=100,
            exit_stall_ms=1000,
            max_rounds=2,
        )
        with mock.patch.object(server_module.time, 'monotonic', return_value=1.0):
            self.enter_both(server)
        self.emitted.clear()
        server.ox_auto_step(now=1.0)   # CC
        server.ox_auto_step(now=1.1)   # question 0 / side 0
        answer0 = struct.pack('<BiiiiiB', 0, 0, 0, -310, -616, 1, 0)
        for pkt_num, conn in enumerate((self.a, self.b), 3):
            self.assertTrue(server._handle_ox_answer_00ca(
                conn, answer0, pkt_num=pkt_num, received_at=1.5
            ))
        server.ox_auto_step(now=2.1)
        transition = server.ox_auto_step(now=2.2)[0]
        self.assertEqual(transition['action'], 'prepare_next')
        self.assertEqual(
            server.ox_snapshot()['rooms']['default']['survivors'], [2, 3]
        )

        server.ox_auto_step(now=2.31)  # question 1 / side 1
        answer1 = struct.pack('<BiiiiiB', 1, 0, 0, 344, -419, 1, 0)
        for pkt_num, conn in enumerate((self.a, self.b), 5):
            self.assertTrue(server._handle_ox_answer_00ca(
                conn, answer1, pkt_num=pkt_num, received_at=2.5
            ))
        server.ox_auto_step(now=3.31)
        transition = server.ox_auto_step(now=3.41)[0]
        self.assertEqual(transition['action'], 'finish_cd')
        room = server.ox_snapshot()['rooms']['default']
        self.assertEqual(room['phase'], 'finished')
        self.assertEqual(room['rounds_completed'], 2)
        for conn in (self.a, self.b):
            self.assertEqual(self.frames_for(server, conn)[-1][0], 0x00CD)

    def test_automatic_timeout_loser_waits_for_natural_c9_without_forced_finish(self):
        server = self.make_server()
        server.ox_configure_automation(
            admission_grace_ms=0,
            ready_delay_ms=0,
            question_duration_ms=1000,
            result_hold_ms=500,
            exit_stall_ms=1000,
            max_rounds=1,
        )
        with mock.patch.object(server_module.time, 'monotonic', return_value=5.0):
            self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        self.emitted.clear()
        server.ox_auto_step(now=5.0)
        server.ox_auto_step(now=5.0)
        server.ox_auto_step(now=6.0)
        ops = [op for op, _payload in self.frames_for(server, self.a)]
        self.assertEqual(ops, [0x00CC, 0x00CE, 0x00CB])
        self.assertNotIn(0x00CD, ops)
        self.assertNotIn(0x00D2, ops)
        self.assertNotIn(0x00D4, ops)

        self.assertTrue(server._handle_ox_leave_00c9(
            self.a, b'\x00', pkt_num=2
        ))
        self.assertEqual(
            server.ox_snapshot()['rooms']['default']['phase'], 'idle'
        )

    def test_ready_late_join_receives_cc_but_question_late_join_is_spectator(self):
        server = self.make_server()
        server.ox_configure_automation(
            admission_grace_ms=0,
            ready_delay_ms=1000,
            question_duration_ms=1000,
        )
        with mock.patch.object(server_module.time, 'monotonic', return_value=1.0):
            self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        self.emitted.clear()
        server.ox_auto_step(now=1.0)
        with mock.patch.object(server_module.time, 'monotonic', return_value=1.2):
            self.assertTrue(server._handle_ox_enter(self.b, b'', pkt_num=2))
        b_ops = [op for op, _payload in self.frames_for(server, self.b)]
        self.assertEqual(b_ops[-1], 0x00CC)
        self.assertEqual(
            server.ox_snapshot()['rooms']['default']['survivors'], [2, 3]
        )

        server = self.make_server()
        server.ox_configure_automation(
            admission_grace_ms=0,
            ready_delay_ms=0,
            question_duration_ms=1000,
        )
        with mock.patch.object(server_module.time, 'monotonic', return_value=2.0):
            self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        server.ox_auto_step(now=2.0)
        server.ox_auto_step(now=2.0)
        self.emitted.clear()
        with mock.patch.object(server_module.time, 'monotonic', return_value=2.2):
            self.assertTrue(server._handle_ox_enter(self.b, b'', pkt_num=2))
        room = server.ox_snapshot()['rooms']['default']
        self.assertEqual(room['survivors'], [2])
        self.assertEqual(room['spectators'], [3])
        self.assertNotIn(0x00CE, [op for op, _payload in self.frames_for(server, self.b)])

    def test_last_loser_c9_rearms_stalled_spectator_fresh_match(self):
        server = self.make_server()
        server.ox_configure_automation(
            admission_grace_ms=0,
            ready_delay_ms=0,
            question_duration_ms=1000,
            result_hold_ms=100,
            exit_stall_ms=1000,
            max_rounds=1,
        )
        with mock.patch.object(server_module.time, 'monotonic', return_value=1.0):
            self.assertTrue(server._handle_ox_enter(self.a, b'', pkt_num=1))
        server.ox_auto_step(now=1.0)
        server.ox_auto_step(now=1.0)
        with mock.patch.object(server_module.time, 'monotonic', return_value=1.2):
            self.assertTrue(server._handle_ox_enter(self.b, b'', pkt_num=2))
        room = server.ox_snapshot()['rooms']['default']
        self.assertEqual(room['survivors'], [2])
        self.assertEqual(room['spectators'], [3])

        # A gives no answer, so the only judged player loses.  At result hold
        # the loser is still present; automation intentionally consumes the
        # due token and waits for the verified C9 instead of forcing D2/D4.
        server.ox_auto_step(now=2.0)
        transition = server.ox_auto_step(now=2.1)[0]
        self.assertEqual(transition['action'], 'await_c9')
        stalled = server.ox_snapshot()['rooms']['default']
        self.assertIsNone(stalled['next_due_at'])
        self.assertEqual(stalled['participants'], [2, 3])

        with mock.patch.object(server_module.time, 'monotonic', return_value=2.2):
            self.assertTrue(server._handle_ox_leave_00c9(
                self.a, b'\x00', pkt_num=3
            ))
        rearmed = server.ox_snapshot()['rooms']['default']
        self.assertEqual(rearmed['participants'], [3])
        self.assertEqual(rearmed['spectators'], [3])
        self.assertEqual(rearmed['next_action'], 'await_c9')
        self.assertEqual(rearmed['next_due_at'], 2.2)

        self.emitted.clear()
        transition = server.ox_auto_step(now=2.2)[0]
        self.assertEqual(transition['action'], 'await_c9')
        fresh = server.ox_snapshot()['rooms']['default']
        self.assertEqual(fresh['phase'], 'ready')
        self.assertEqual(fresh['survivors'], [3])
        self.assertEqual(fresh['spectators'], [])
        self.assertEqual(self.frames_for(server, self.b), [(0x00CC, b'')])

    def test_scheduler_thread_has_bounded_lifecycle_and_never_invents_006e(self):
        server = self.make_server()
        self.assertTrue(server.ox_configure_automation(scheduler_poll_ms=10)[0])
        server.running = True
        self.assertTrue(server._start_ox_scheduler())
        self.assertTrue(server.ox_scheduler_thread.is_alive())
        server.running = False
        self.assertTrue(server._stop_ox_scheduler())
        self.assertFalse(server.ox_scheduler_thread.is_alive())
        self.assertNotIn(
            0x006E,
            [
                opcode
                for conn in (self.a, self.b)
                for opcode, _payload in self.frames_for(server, conn)
            ],
        )
        self.assertFalse(server.ox_configure_automation(
            question_duration_ms=999
        )[0])
        self.assertFalse(server.ox_configure_automation(enabled='yes')[0])

    def test_control_transitions_keep_cc_before_ce_under_concurrency(self):
        server = self.make_server()
        self.enter_both(server)
        original_emit = server._emit
        cc_started = threading.Event()
        allow_cc = threading.Event()

        def blocking_emit(conn, data, **kwargs):
            frames = parse_frames(server, data)
            if frames and frames[0][0] == 0x00CC and not cc_started.is_set():
                cc_started.set()
                self.assertTrue(allow_cc.wait(2))
            return original_emit(conn, data, **kwargs)

        server._emit = blocking_emit
        results = {}
        prepare = threading.Thread(
            target=lambda: results.setdefault('prepare', server.ox_prepare())
        )
        prepare.start()
        self.assertTrue(cc_started.wait(1))
        opened = threading.Thread(
            target=lambda: results.setdefault(
                'open', server.ox_open_question(
                    question_index=0, duration_ms=1000, now=1.0
                )
            )
        )
        opened.start()
        time.sleep(0.02)
        self.assertNotIn('open', results)
        allow_cc.set()
        prepare.join(2)
        opened.join(2)
        self.assertFalse(prepare.is_alive())
        self.assertFalse(opened.is_alive())
        self.assertTrue(results['prepare'][0])
        self.assertTrue(results['open'][0])
        for conn in (self.a, self.b):
            ops = [op for op, _payload in self.frames_for(server, conn)]
            self.assertLess(ops.index(0x00CC), ops.index(0x00CE))

    def test_explicit_control_routes_drive_and_report_a_round(self):
        server = self.make_server()
        self.enter_both(server)
        control = control_module.ControlServer(server, port=0)
        self.assertTrue(control.start())
        port = control.httpd.server_address[1]

        def call(path, body=None):
            data = json.dumps(body).encode('utf-8') if body is not None else None
            request = urllib.request.Request(
                f'http://127.0.0.1:{port}{path}', data=data,
                method='POST' if data is not None else 'GET',
                headers={'Content-Type': 'application/json'},
            )
            try:
                with urllib.request.urlopen(request, timeout=2) as response:
                    return response.status, json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read().decode('utf-8'))

        try:
            status, configured = call(
                '/api/ox/configure', {'side0_cells': [20], 'side1_cells': [14]}
            )
            self.assertEqual(status, 200)
            self.assertTrue(configured['ok'])
            self.assertEqual(call('/api/ox', [1, 2, 3])[0], 400)
            self.assertEqual(
                call('/api/ox/prepare', {'room_id': ['bad']})[0], 400
            )
            self.assertEqual(call('/api/ox/prepare', {})[0], 200)
            self.assertEqual(
                call('/api/ox/question', {'question_index': 0, 'duration_ms': 1})[0],
                200,
            )
            tick_status, tick_body = call('/api/ox/tick', {})
            for _attempt in range(10):
                if tick_status == 200:
                    break
                self.assertIn('deadline', tick_body.get('message', ''))
                time.sleep(0.01)
                tick_status, tick_body = call('/api/ox/tick', {})
            self.assertEqual(tick_status, 200)
            self.assertEqual(call('/api/ox/finish', {})[0], 200)
            status, snapshot = call('/api/ox/status')
            self.assertEqual(status, 200)
            self.assertEqual(snapshot['rooms']['default']['phase'], 'finished')
            self.assertEqual(snapshot['rooms']['default']['finish_exit_mode'], 'cd')
        finally:
            control.stop()


if __name__ == '__main__':
    unittest.main(verbosity=2)
