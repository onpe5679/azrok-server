# -*- coding: utf-8 -*-
"""Regression tests for the read-only operator control-room layer."""
import json
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import unittest
import urllib.request

from azrok_control import (
    ACCESSORY_SLOT_CONTRACTS,
    ACCESSORY_UNLOCK_ROWS,
    ControlServer,
    PROTOCOL_CONTRACTS,
    _accessory_packet_view,
    _binding_view,
    _canonical_readonly_summary,
    _cursor_page,
    _cursor_query,
    build_control_snapshot,
)
from azrok_control_page import PAGE
from azrok_private_access import PrivateAccountRegistry


class _FakeServer:
    def __init__(self, state_dir, proto):
        self.ctl_lock = threading.RLock()
        self.mutation_lock = threading.RLock()
        self._proto = proto
        self.conn = object()
        self.connections = [self.conn]
        self.client_meta = {
            self.conn: {'entity_id': 7, 'proto_state': proto},
        }
        self.state_dir = state_dir
        self.ox_automation_updates = None

    def _active_proto_state(self):
        return self._proto

    def snapshot(self):
        return {
            'server': {'clients': 1, 'players': [{'entity_id': 7, 'protocol': {}}]},
            'content': {
                'content_profile': 'minimal',
                'state_namespace': 'test_scope',
                'state_store_dir': self.state_dir,
            },
            'events': [
                {'seq': 1, 'kind': 'purchase', 'severity': 'warn',
                 'message': 'rejected', 'details': {'reason': 'unbound'}},
            ],
            'mutation_journal': {
                'file': 'mutation_transactions_v1.jsonl',
                'latest_seq': 0,
                'failures': 0,
                'corrupt_lines': 0,
                'sequence_gaps': 0,
                'durable': True,
            },
        }

    def ox_configure_automation(self, **updates):
        self.ox_automation_updates = dict(updates)
        return True, 'OX automatic-after-C8 policy updated'

    def ox_snapshot(self):
        policy = {'enabled': True}
        if self.ox_automation_updates:
            policy.update(self.ox_automation_updates)
        return {
            'timer_mode': 'automatic-after-client-c8',
            'admission_mode': 'client_c8_only',
            'unsolicited_006e': False,
            'inferred_timing_policy': policy,
            'question_count': 2,
            'rooms': {},
        }


class ControlObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix='azrok-control-test-')

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def _bound_proto(self):
        key = 'a75736572_s0_c506574'
        return {
            'account_raw': b'user',
            'char_name_raw': b'Pet',
            'character_slot': 0,
            'client_0005_seen': True,
            'selected_character_key': key,
        }, key

    def test_binding_requires_explicit_matching_selected_key(self):
        proto, key = self._bound_proto()
        view = _binding_view(proto, self.tempdir)
        self.assertTrue(view['bound'])
        self.assertEqual(view['selected_key'], key)

        proto['selected_character_key'] = key + '00'
        view = _binding_view(proto, self.tempdir)
        self.assertFalse(view['bound'])
        self.assertIn('does not match', view['reason'])

    def test_canonical_summary_is_read_only_and_bounded(self):
        proto, key = self._bound_proto()
        binding = _binding_view(proto, self.tempdir)
        path = binding['canonical_path']
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({
                'schema_version': 1,
                'revision': 7,
                'currency': 950,
                'inventory': {'energy': [1, 0, 2], 'toy': [0, 1]},
                'accessory_slots': [0xFF, 2, 3, 7],
                'active_loadouts': {'toy': [1]},
                'runtime_rows': [{}, {}],
            }, handle)
        before = os.stat(path).st_mtime_ns
        summary = _canonical_readonly_summary(binding)
        after = os.stat(path).st_mtime_ns
        self.assertTrue(summary['available'])
        self.assertEqual(summary['currency'], 950)
        self.assertEqual(summary['inventory']['energy']['quantity'], 3)
        self.assertEqual(summary['inventory']['energy']['owned_slots'], 2)
        self.assertEqual(summary['accessory_slots'], [0xFF, 2, 3, 7])
        self.assertEqual(summary['schema'], 1)
        self.assertEqual(summary['revision'], 7)
        with open(path, 'rb') as handle:
            self.assertEqual(summary['sha256'], hashlib.sha256(handle.read()).hexdigest())
        self.assertEqual(before, after)

    def test_snapshot_exposes_per_client_binding_and_recent_decisions(self):
        proto, key = self._bound_proto()
        path = os.path.join(self.tempdir, key + '_state_v1.json')
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({'schema': 'v1', 'currency': 12, 'inventory': {}}, handle)
        result = build_control_snapshot(_FakeServer(self.tempdir, proto))
        self.assertTrue(result['operator']['binding']['bound'])
        self.assertEqual(result['operator']['canonical']['currency'], 12)
        self.assertEqual(result['operator']['recent_decisions'][0]['kind'], 'purchase')
        self.assertTrue(result['server']['players'][0]['protocol']['binding']['bound'])

    def test_protocol_contracts_are_direction_specific_and_unique(self):
        keys = [(row['dir'], row['opcode']) for row in PROTOCOL_CONTRACTS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn(('C->S', '0x0007'), keys)
        self.assertIn(('S->C', '0x0007'), keys)
        unresolved = [row for row in PROTOCOL_CONTRACTS if row['status'] == 'NOT VERIFIED']
        self.assertTrue(unresolved)
        c2s_unresolved = next(row for row in unresolved
                              if (row['dir'], row['opcode']) == ('C->S', '0x000B'))
        self.assertEqual(c2s_unresolved['policy'], 'observe only')
        self.assertTrue(all(row['policy'] == 'emit disabled'
                            for row in unresolved if row['dir'] == 'S->C'))
        accessory = next(row for row in PROTOCOL_CONTRACTS
                         if (row['dir'], row['opcode']) == ('C->S', '0x0018'))
        self.assertEqual(accessory['status'], 'VERIFIED')
        self.assertIn('set/clear', accessory['policy'])
        remote_update = next(row for row in PROTOCOL_CONTRACTS
                             if (row['dir'], row['opcode']) == ('S->C', '0x000C'))
        self.assertEqual(remote_update['length'], '7')

    def test_cursor_page_reports_ring_gap_and_bounded_progress(self):
        items = [{'seq': seq, 'value': str(seq)} for seq in range(5, 10)]
        page = _cursor_page(items, after_seq=1, limit=2)
        self.assertEqual([item['seq'] for item in page['items']], [5, 6])
        self.assertEqual(page['oldest_seq'], 5)
        self.assertEqual(page['latest_seq'], 9)
        self.assertEqual(page['dropped_before_seq'], 4)
        self.assertTrue(page['gap'])
        self.assertTrue(page['overflow'])
        self.assertTrue(page['has_more'])
        self.assertEqual(page['next_seq'], 6)
        self.assertTrue(page['sequence_monotonic'])

        caught_up = _cursor_page(items, after_seq=8, limit=2)
        self.assertEqual([item['seq'] for item in caught_up['items']], [9])
        self.assertFalse(caught_up['gap'])
        self.assertFalse(caught_up['has_more'])
        self.assertEqual(caught_up['next_seq'], 9)
        self.assertEqual(_cursor_query('after_seq=3&limit=999'), (3, 200))
        with self.assertRaises(ValueError):
            _cursor_query('after_seq=-1')

    def test_http_cursor_endpoints_and_lightweight_overview(self):
        proto, _key = self._bound_proto()
        fake = _FakeServer(self.tempdir, proto)
        fake.packet_ring = [
            {'seq': seq, 'dir': 'C->S', 'opcode': '0x0016', 'hex': '00'}
            for seq in range(7, 12)
        ]
        fake.event_ring = [
            {'seq': seq, 'kind': 'test', 'message': str(seq)}
            for seq in range(3, 6)
        ]
        fake.mutation_ring = [
            {'seq': seq, 'kind': 'purchase', 'result': 'committed'}
            for seq in range(21, 24)
        ]
        control = ControlServer(fake, port=0)
        self.assertTrue(control.start())
        port = control.httpd.server_port
        try:
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/api/packets?after_seq=8&limit=2',
                    timeout=2) as response:
                packets = json.load(response)
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/api/events?after_seq=0&limit=1',
                    timeout=2) as response:
                events = json.load(response)
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/api/transactions?after_seq=21&limit=1',
                    timeout=2) as response:
                transactions = json.load(response)
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/api/overview', timeout=2
            ) as response:
                overview = json.load(response)
        finally:
            control.stop()

        self.assertEqual(packets['kind'], 'packets')
        self.assertEqual([item['seq'] for item in packets['items']], [9, 10])
        self.assertEqual(packets['next_seq'], 10)
        self.assertTrue(packets['has_more'])
        self.assertEqual(events['kind'], 'events')
        self.assertTrue(events['gap'])
        self.assertEqual(events['oldest_seq'], 3)
        self.assertEqual(transactions['kind'], 'transactions')
        self.assertEqual([item['seq'] for item in transactions['items']], [22])
        self.assertTrue(transactions['has_more'])
        self.assertNotIn('packets', overview)
        self.assertNotIn('events', overview)
        self.assertNotIn('proto_state', overview)
        self.assertEqual(overview['cursor']['packets']['oldest_seq'], 7)
        self.assertEqual(overview['cursor']['transactions']['oldest_seq'], 21)
        self.assertNotIn('items', overview['cursor']['packets'])
        self.assertNotIn('items', overview['cursor']['events'])
        self.assertNotIn('items', overview['cursor']['transactions'])

    def test_http_ox_automation_updates_only_typed_policy_fields(self):
        proto, _key = self._bound_proto()
        fake = _FakeServer(self.tempdir, proto)
        control = ControlServer(fake, port=0)
        self.assertTrue(control.start())
        port = control.httpd.server_port
        request = urllib.request.Request(
            f'http://127.0.0.1:{port}/api/ox/automation',
            data=json.dumps({
                'enabled': False,
                'ready_delay_ms': 900,
                'room_id': 'ignored-by-policy',
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                result = json.load(response)
        finally:
            control.stop()
        self.assertTrue(result['ok'])
        self.assertEqual(fake.ox_automation_updates, {
            'enabled': False,
            'ready_delay_ms': 900,
        })
        self.assertFalse(result['ox']['unsolicited_006e'])

    def test_private_account_admin_api_redacts_browser_ids_and_requires_confirmation(self):
        proto, _key = self._bound_proto()
        registry = PrivateAccountRegistry(
            os.path.join(self.tempdir, 'private_accounts.json'), b'control-test-recovery-secret'
        )
        browser_id = 'browser_7c0f4e07-1bf8-4df2-8e75-1c4d3bd3d9e6'
        account_id = registry.session_account(browser_id)
        control = ControlServer(_FakeServer(self.tempdir, proto), port=0, private_account_registry=registry)
        self.assertTrue(control.start())
        port = control.httpd.server_port
        try:
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/api/private-accounts', timeout=2) as response:
                snapshot = json.load(response)
            self.assertNotIn(browser_id, repr(snapshot))
            account_row = next(row for row in snapshot['accounts'] if row['account'] == account_id)
            self.assertEqual(account_row['binding_count'], 1)
            bad_request = urllib.request.Request(
                f'http://127.0.0.1:{port}/api/private-accounts/clear-bindings',
                data=json.dumps({'account': account_id}).encode('utf-8'),
                headers={'Content-Type': 'application/json'}, method='POST')
            with self.assertRaises(urllib.error.HTTPError) as bad_response:
                urllib.request.urlopen(bad_request, timeout=2)
            self.assertEqual(bad_response.exception.code, 400)
            recovery_request = urllib.request.Request(
                f'http://127.0.0.1:{port}/api/private-accounts/recovery-code',
                data=json.dumps({'account': account_id}).encode('utf-8'),
                headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(recovery_request, timeout=2) as response:
                recovery_result = json.load(response)
            self.assertTrue(recovery_result['ok'])
            self.assertTrue(recovery_result['recovery_code'])
            removed_password_request = urllib.request.Request(
                f'http://127.0.0.1:{port}/api/private-accounts/password',
                data=json.dumps({'account': account_id, 'password': 'obsolete'}).encode('utf-8'),
                headers={'Content-Type': 'application/json'}, method='POST')
            with self.assertRaises(urllib.error.HTTPError) as removed_response:
                urllib.request.urlopen(removed_password_request, timeout=2)
            self.assertEqual(removed_response.exception.code, 404)
            release_request = urllib.request.Request(
                f'http://127.0.0.1:{port}/api/private-accounts/clear-bindings',
                data=json.dumps({'account': account_id, 'confirmation': f'RELEASE {account_id}'}).encode('utf-8'),
                headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(release_request, timeout=2) as response:
                release_result = json.load(response)
        finally:
            control.stop()
        self.assertEqual(release_result['released'], 1)
        self.assertEqual(
            registry.import_recovery_code(
                'browser_8c0f4e07-1bf8-4df2-8e75-1c4d3bd3d9e6',
                recovery_result['recovery_code'],
            ),
            account_id,
        )

    def test_accessory_views_decode_only_verified_wire_offsets(self):
        self_blob = bytearray(472)
        self_blob[0x1D4:0x1D8] = bytes((0xFF, 0, 3, 7))
        actor = bytearray(0x1A)
        actor[1:5] = (123).to_bytes(4, 'little')
        actor[0x14:0x18] = bytes((9, 6, 0xFF, 0))
        packets = [
            {'seq': 1, 'dir': 'S->C', 'opcode': '0x0007',
             'hex': self_blob.hex(), 'decoded': {}},
            {'seq': 2, 'dir': 'S->C', 'opcode': '0x0066',
             'hex': actor.hex(), 'decoded': {}},
            {'seq': 3, 'dir': 'C->S', 'opcode': '0x0018',
             'hex': '000102', 'decoded': {}},
            {'seq': 4, 'dir': 'S->C', 'opcode': '0x000C',
             'hex': (123).to_bytes(4, 'little').hex() + '010100', 'decoded': {}},
            {'seq': 5, 'dir': 'S->C', 'opcode': '0x000C',
             'hex': (1).to_bytes(4, 'little').hex() + '000009', 'decoded': {}},
        ]
        view = _accessory_packet_view(packets)
        self.assertEqual(len(ACCESSORY_SLOT_CONTRACTS), 4)
        self.assertEqual(view['current_self'], [9, 0, 3, 7])
        self.assertEqual(view['current_self_baseline_seq'], 1)
        self.assertEqual(view['current_self_update_seq'], 5)
        self.assertEqual(view['current_self_packet_seq'], 5)
        self.assertEqual(view['current_self_source'], 's2c_000c_delta')
        self.assertEqual(view['remote_by_actor']['123'], [9, 0xFF, 0xFF, 0])
        self.assertEqual(view['recent_c2s_0018'][0]['action'], 'set')
        self.assertEqual(view['recent_c2s_0018'][0]['slot'], 1)
        self.assertEqual(view['recent_s2c_000c'][0]['effective_value'], 0xFF)
        self.assertEqual(view['level_stat']['meaning'], 'level')
        self.assertEqual(len(view['unlock_rows']), 9)
        self.assertEqual(
            [(row['resource_id'], row['group'], row['threshold'])
             for row in ACCESSORY_UNLOCK_ROWS],
            [(20000, 4, 50), (20001, 1, 200), (20002, 3, 100),
             (20003, 2, 50), (20004, 4, 200), (30000, 4, 100),
             (30001, 5, 200), (30002, 3, 150), (40000, 2, 150)],
        )
        self.assertEqual(ACCESSORY_UNLOCK_ROWS[4]['evolution_min'], 3)
        self.assertIn('accessory_slots', packets[0]['decoded'])

    def test_accessory_self_delta_is_sequential_and_does_not_replace_canonical(self):
        baseline = bytearray(472)
        baseline[0x1D4:0x1D8] = bytes((0xFF, 2, 3, 0xFF))
        newer_baseline = bytearray(baseline)
        newer_baseline[0x1D4:0x1D8] = bytes((4, 2, 3, 0xFF))
        packets = [
            {'seq': 10, 'dir': 'S->C', 'opcode': '0x0007',
             'hex': baseline.hex(), 'decoded': {}},
            {'seq': 11, 'dir': 'S->C', 'opcode': '0x000C',
             'hex': (1).to_bytes(4, 'little').hex() + '000005', 'decoded': {}},
            {'seq': 12, 'dir': 'S->C', 'opcode': '0x000C',
             'hex': (1).to_bytes(4, 'little').hex() + '010005', 'decoded': {}},
            {'seq': 13, 'dir': 'S->C', 'opcode': '0x0007',
             'hex': newer_baseline.hex(), 'decoded': {}},
            {'seq': 14, 'dir': 'S->C', 'opcode': '0x000C',
             'hex': (1).to_bytes(4, 'little').hex() + '000300', 'decoded': {}},
        ]
        view = _accessory_packet_view(packets)
        self.assertEqual(view['current_self'], [4, 2, 3, 0])
        self.assertEqual(view['current_self_baseline_seq'], 13)
        self.assertEqual(view['current_self_update_seq'], 14)
        self.assertEqual(view['current_self_source'], 's2c_000c_delta')

    def test_accessory_projection_is_recipient_scoped_and_tracks_roster_teardown(self):
        def baseline(values):
            blob = bytearray(472)
            blob[0x1D4:0x1D8] = bytes(values)
            return blob.hex()

        def actor_record(actor_id, values):
            record = bytearray(0x1A)
            record[1:5] = int(actor_id).to_bytes(4, 'little')
            record[0x14:0x18] = bytes(values)
            return record.hex()

        packets = [
            {'seq': 1, 'entity_id': 7, 'dir': 'S->C', 'opcode': '0x0007',
             'hex': baseline((0xFF, 1, 2, 3)), 'decoded': {}},
            {'seq': 2, 'entity_id': 8, 'dir': 'S->C', 'opcode': '0x0007',
             'hex': baseline((9, 6, 3, 7)), 'decoded': {}},
            {'seq': 3, 'entity_id': 7, 'dir': 'S->C', 'opcode': '0x0066',
             'hex': actor_record(22, (1, 2, 3, 4)), 'decoded': {}},
            {'seq': 4, 'entity_id': 8, 'dir': 'S->C', 'opcode': '0x000C',
             'hex': (1).to_bytes(4, 'little').hex() + '000000', 'decoded': {}},
            {'seq': 5, 'entity_id': 7, 'dir': 'S->C', 'opcode': '0x000C',
             'hex': (22).to_bytes(4, 'little').hex() + '000005', 'decoded': {}},
            {'seq': 6, 'entity_id': 7, 'dir': 'S->C', 'opcode': '0x0067',
             'hex': (22).to_bytes(4, 'little').hex(), 'decoded': {}},
            {'seq': 7, 'entity_id': 7, 'dir': 'S->C', 'opcode': '0x0066',
             'hex': actor_record(23, (4, 3, 2, 1)), 'decoded': {}},
            {'seq': 8, 'entity_id': 7, 'dir': 'S->C', 'opcode': '0x0065',
             'hex': '00', 'decoded': {}},
            {'seq': 9, 'entity_id': 8, 'dir': 'C->S', 'opcode': '0x0018',
             'hex': '000000', 'decoded': {}},
        ]

        after_remove = _accessory_packet_view(packets[:6], target_entity_id=7)
        self.assertEqual(after_remove['remote_by_actor'], {})

        view = _accessory_packet_view(packets, target_entity_id=7)
        self.assertEqual(view['target_entity_id'], 7)
        self.assertEqual(view['current_self'], [0xFF, 1, 2, 3])
        self.assertEqual(view['current_self_source'], 's2c_0007_baseline')
        self.assertEqual(view['remote_by_actor'], {})
        self.assertEqual(view['recent_c2s_0018'], [])
        self.assertTrue(packets[5]['decoded']['remote_accessory_removed_actor_id'] == 22)
        self.assertTrue(packets[7]['decoded']['remote_accessories_reset'])
        self.assertNotIn('accessory_slots', packets[1]['decoded'])

    def test_control_snapshot_targets_active_entity_accessory_runtime(self):
        proto, _key = self._bound_proto()
        fake = _FakeServer(self.tempdir, proto)
        own = bytearray(472)
        own[0x1D4:0x1D8] = bytes((1, 2, 3, 4))
        other = bytearray(472)
        other[0x1D4:0x1D8] = bytes((9, 6, 3, 7))
        base_snapshot = fake.snapshot

        def snapshot():
            result = base_snapshot()
            result['content']['active_entity_id'] = 7
            result['packets'] = [
                {'seq': 1, 'entity_id': 7, 'dir': 'S->C', 'opcode': '0x0007',
                 'hex': own.hex(), 'decoded': {}},
                {'seq': 2, 'entity_id': 8, 'dir': 'S->C', 'opcode': '0x0007',
                 'hex': other.hex(), 'decoded': {}},
                {'seq': 3, 'entity_id': 8, 'dir': 'S->C', 'opcode': '0x000C',
                 'hex': (1).to_bytes(4, 'little').hex() + '000005', 'decoded': {}},
            ]
            return result

        fake.snapshot = snapshot
        result = build_control_snapshot(fake)
        self.assertEqual(result['operator']['accessories']['target_entity_id'], 7)
        self.assertEqual(result['operator']['accessories']['current_self'], [1, 2, 3, 4])

    def test_http_exposes_enriched_state_and_protocol_catalog(self):
        proto, _key = self._bound_proto()
        control = ControlServer(_FakeServer(self.tempdir, proto), port=0)
        self.assertTrue(control.start())
        port = control.httpd.server_port
        try:
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/api/state', timeout=2) as response:
                state = json.load(response)
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/api/protocol', timeout=2) as response:
                catalog = json.load(response)
            with urllib.request.urlopen(
                    f'http://127.0.0.1:{port}/api/protocol/specs', timeout=2) as response:
                registry = json.load(response)
        finally:
            control.stop()
        self.assertTrue(state['operator']['binding']['bound'])
        self.assertGreater(len(catalog['contracts']), 30)
        self.assertEqual(len(catalog['accessory_slots']), 4)
        self.assertEqual(catalog['registry_schema'], 'azrok.protocol.registry.v1')
        self.assertEqual(catalog['registry_spec_id'], registry['spec_id'])
        self.assertEqual(registry['schema'], 'azrok.protocol.registry.v1')
        self.assertEqual(len(registry['specs']), len(PROTOCOL_CONTRACTS))
        self.assertTrue(registry['spec_id'].startswith('sha256:'))
        self.assertIn('VERIFIED', catalog['accessory_policy']['c2s_0018_b0'])
        self.assertEqual(len(catalog['accessory_policy']['unlock_rows']), 9)

    def test_page_contains_safe_write_boundary_and_operator_tools(self):
        for marker in (
            '안전 조회 영역 (read-only)', '위험한 수동 변경 도구 열기',
            'sendConfirm', 'originFilter', 'categoryFilter', 'packetDetail',
            'bindingBadge', 'contractSearch', '/api/protocol/specs',
            'protocolSpecBadge', 'accessoryBadge', 'renderAccessories', 'C→S0018',
            'mutation_journal', 'JOURNAL HEALTH', 'DEGRADED',
            'structured_capture', 'JSONL CAPTURE', 'CAPTURE PRIVACY',
            '/api/private-accounts/recovery-code', '복구 코드 발급',
            'function showRecoveryCode', '모든 기기 연결 해제',
        ):
            self.assertIn(marker, PAGE)
        self.assertNotIn('/api/private-accounts/password', PAGE)
        self.assertNotIn('비밀번호 저장', PAGE)
        self.assertNotIn('const meaning={', PAGE)
        self.assertIn('meaning=Object.fromEntries(protocolSpecs.map', PAGE)

    def test_page_contains_phase_aware_confirmed_ox_operator_panel(self):
        for marker in (
            'OX 운영 패널', 'oxPhaseBadge', 'oxMetrics', 'oxRoster',
            'oxQuestionIndex', 'oxDuration', 'oxExitMode', 'oxStatus', 'oxAutoToggle',
            'function renderOx(s)', 'function runOxAction(action)',
            'function runOxAutomation()', "'/api/ox/automation'",
            "'/api/ox/prepare'", "'/api/ox/question'",
            "'/api/ox/tick'", "'/api/ox/finish'",
            'room?.deadline_at', 'room?.participants', 'room?.answers',
            'room?.next_action', 'ox.inferred_timing_policy',
        ):
            self.assertIn(marker, PAGE)
        self.assertIn("if(!confirm(`OX room", PAGE)
        self.assertIn("response.ok&&data.ok!==false", PAGE)
        self.assertIn("oxNotice={text:message,ok}", PAGE)
        self.assertIn("duration_ms는 1..300000", PAGE)
        self.assertIn("CD/D2/D4는 상호 배타적인 종료 원인", PAGE)

    def test_embedded_javascript_syntax(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        match = re.search(r'<script>([\s\S]*)</script>', PAGE)
        self.assertIsNotNone(match)
        completed = subprocess.run(
            [node, '--check', '-'], input=match.group(1), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_incremental_cursor_browser_mock_merges_monotonic_bounded_ring(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        script = re.search(r'<script>([\s\S]*)</script>', PAGE).group(1)
        expression = re.search(
            r'^const mergeCursorItems=(.+);$', script, re.MULTILINE
        )
        self.assertIsNotNone(expression)
        mock = f"""
const mergeCursorItems={expression.group(1)};
const merged=mergeCursorItems(
  [{{seq:2,value:'old'}},{{seq:3,value:'old3'}}],
  [{{seq:3,value:'new3'}},{{seq:4,value:'new4'}}], 3);
if (JSON.stringify(merged.map(x=>x.seq)) !== '[2,3,4]') process.exit(2);
if (merged[1].value !== 'new3') process.exit(3);
const bounded=mergeCursorItems(merged,[{{seq:5}},{{seq:6}}],3);
if (JSON.stringify(bounded.map(x=>x.seq)) !== '[4,5,6]') process.exit(4);
"""
        completed = subprocess.run(
            [node, '-e', mock], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for marker in (
            '/api/overview', "fetchCursor('packets'", "fetchCursor('events'",
            'after_seq=',
            'cursor_status', 'cursorBadge', 'cursor ring overflow',
            "fallbackState('cursor-fallback: ",
        ):
            self.assertIn(marker, PAGE)


if __name__ == '__main__':
    unittest.main()
