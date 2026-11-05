"""Loopback HTTP admin contract using real server objects and disposable state."""

import json
import os
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from azrok_control import ControlServer
from azrok_server import AzrokServer
from azrok_admin_history import latest_login_by_account


class AdminHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.capture_env = mock.patch.dict(os.environ, {
            'AZROK_CAPTURE_DIR': str(Path(self.temp.name) / 'structured'),
        })
        self.capture_env.start()
        self.addCleanup(self.capture_env.stop)
        self.game = AzrokServer(port=0, log_dir=self.temp.name)
        self.addCleanup(self.game.stop)
        self.game.proto_state.update({
            'account_raw': b'test', 'char_name_raw': b'Pet',
            'character_slot': 0, 'char_type': 1,
        })
        self.key = self.game._character_state_key()
        state = self.game._default_canonical_character_state()
        state['currency'] = 4
        self.assertTrue(self.game._save_canonical_character_state(state, key=self.key))
        self.control = ControlServer(self.game, port=0)
        self.assertTrue(self.control.start())
        self.addCleanup(self.control.stop)
        self.base = 'http://127.0.0.1:' + str(self.control.httpd.server_address[1])

    def request(self, path, body=None, headers=None):
        data = None if body is None else json.dumps(body).encode('utf-8')
        request = urllib.request.Request(self.base + path, data=data,
                                         headers=headers or {},
                                         method='POST' if body is not None else 'GET')
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    def test_operator_routes_and_debugger_isolation(self):
        from azrok_operator_page import PAGE as operator_page
        from azrok_control_page import PAGE as debugger_page
        for route in ('/', '/index.html', '/admin'):
            with urllib.request.urlopen(self.base + route, timeout=5) as response:
                self.assertEqual(200, response.status)
                self.assertIn('text/html', response.headers['Content-Type'])
                self.assertEqual(operator_page, response.read().decode('utf-8'))
        with urllib.request.urlopen(self.base + '/debug', timeout=5) as response:
            self.assertEqual(200, response.status)
            self.assertEqual(debugger_page, response.read().decode('utf-8'))
        self.assertNotEqual(operator_page, debugger_page)

    def test_list_detail_edit_reload_and_archive(self):
        status, accounts = self.request('/api/admin/accounts')
        self.assertEqual(200, status)
        self.assertEqual(self.key, accounts['accounts'][0]['characters'][0]['key'])
        query = urllib.parse.urlencode({'key': self.key})
        status, detail = self.request('/api/admin/character?' + query)
        self.assertEqual(200, status)
        self.assertEqual(4, detail['editable_fields']['currency']['value'])
        revision = detail['revision']
        status, changed = self.request('/api/admin/character', {
            'key': self.key, 'action': 'update', 'expected_revision': revision,
            'changes': {'fields': {'currency': 9}, 'inventory': {'1000': 1}},
        }, {'Content-Type': 'application/json'})
        self.assertEqual(200, status, changed)
        reader = AzrokServer(port=0, log_dir=self.temp.name)
        self.addCleanup(reader.stop)
        disk = reader._load_canonical_character_state(key=self.key)
        self.assertEqual((9, 1), (disk['currency'], disk['inventory']['food'][0]))
        status, stale = self.request('/api/admin/character', {
            'key': self.key, 'action': 'update', 'expected_revision': revision,
            'changes': {'fields': {'currency': 10}},
        }, {'Content-Type': 'application/json'})
        self.assertEqual(409, status, stale)
        status, archived = self.request('/api/admin/character', {
            'key': self.key, 'action': 'archive', 'expected_revision': changed['revision'],
            'confirmation': 'Pet',
        }, {'Content-Type': 'application/json'})
        self.assertEqual(200, status, archived)
        path = Path(self.game.state_store_dir) / (self.key + '_state_v1.json')
        self.assertFalse(path.exists())
        backup = Path(self.game.state_store_dir) / 'admin_backups' / archived['backup_id']
        self.assertTrue((backup / (path.name + '.removed')).exists())

    def test_request_boundaries(self):
        status, _ = self.request('/api/admin/character?key=..%2Foutside')
        self.assertEqual(400, status)
        body = {'key': self.key, 'action': 'update', 'expected_revision': 1,
                'changes': {'fields': {'currency': 9}}}
        status, _ = self.request('/api/admin/character', body, {
            'Content-Type': 'application/json', 'Origin': 'https://other.example'})
        self.assertEqual(403, status)
        status, _ = self.request('/api/admin/character', body, {
            'Content-Type': 'text/plain'})
        self.assertEqual(415, status)
        status, _ = self.request('/api/admin/character', {**body, 'key': '../outside'},
                                 {'Content-Type': 'application/json'})
        self.assertEqual(400, status)

    def test_login_journal_is_account_bound_and_failure_is_nonfatal(self):
        conn = object()
        local = dict(self.game.proto_template)
        self.game.connections.append(conn)
        self.game.client_meta[conn] = {'entity_id': 27, 'proto_state': local}
        payload = bytearray(0x6A)
        payload[0] = 1
        payload[1:5] = b'test'
        payload[14:18] = b'pass'
        with self.game._client_protocol_context(conn):
            self.game._build_response(0x0000, bytes(payload), pkt_num=1)
        self.assertIn('test', latest_login_by_account(self.game)['latest'])
        with mock.patch('azrok_admin_history.record_event', side_effect=OSError('disk failure')):
            with self.game._client_protocol_context(conn):
                self.game._build_response(0x0000, bytes(payload), pkt_num=2)
        self.assertEqual(b'test', local['account_raw'])
        self.assertEqual(1, self.game.admin_history_failures)


if __name__ == '__main__':
    unittest.main()
