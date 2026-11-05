"""Offline admin transaction checks using disposable canonical files."""

import json
import threading
import tempfile
import unittest
from pathlib import Path

import azrok_admin_service


KEY = 'a74657374_s0_c506574'


class FakeServer:
    def __init__(self, state_dir):
        self.state_store_dir = state_dir
        self.ctl_lock = threading.RLock()
        self.proto_lock = threading.RLock()
        self.ox_action_lock = threading.RLock()
        self.client_meta = {}
        self.connections = []
        self.proto_state = {'sentinel': True}
        self.saved_server_states = {KEY: {'old': True}}
        self.saved_character_states = {KEY: b'old'}

    def _ensure_ox_runtime(self):
        pass

    def _save_canonical_character_state(self, document, *, key, mutation):
        document = dict(document)
        document['revision'] += 1
        (Path(self.state_store_dir) / (key + '_state_v1.json')).write_text(
            json.dumps(document), encoding='utf-8')
        return True


class AdminServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = FakeServer(self.temp.name)
        self.state = {
            'schema_version': 1, 'revision': 1, 'currency': 4,
            'character': {'name_hex': '506574', 'species': 0, 'slot': 0},
            'inventory': {
                'furniture': [0] * 33, 'drug': [0] * 15,
                'energy': [0] * 20, 'food': [0] * 38,
                'ingredient': [0] * 3, 'toy': [0] * 10,
                'gym': [0] * 8, 'book': [0],
            },
        }
        self.path = Path(self.temp.name) / (KEY + '_state_v1.json')
        self.path.write_text(json.dumps(self.state), encoding='utf-8')

    def test_update_backup_cache_and_stale_revision(self):
        original_proto = self.server.proto_state
        ok, result = azrok_admin_service.mutate(self.server, {
            'key': KEY, 'action': 'update', 'expected_revision': 1,
            'changes': {'fields': {'currency': 9}, 'inventory': {'1000': 1}},
        })
        self.assertTrue(ok, result)
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual((2, 9, 1),
                         (saved['revision'], saved['currency'], saved['inventory']['food'][0]))
        self.assertIs(original_proto, self.server.proto_state)
        self.assertNotIn(KEY, self.server.saved_server_states)
        self.assertNotIn(KEY, self.server.saved_character_states)
        backup = Path(self.temp.name) / 'admin_backups' / result['backup_id']
        self.assertTrue((backup / self.path.name).is_file())
        ok, stale = azrok_admin_service.mutate(self.server, {
            'key': KEY, 'action': 'update', 'expected_revision': 1,
            'changes': {'fields': {'currency': 100}},
        })
        self.assertFalse(ok)
        self.assertEqual(9, json.loads(self.path.read_text(encoding='utf-8'))['currency'])

    def test_online_account_cannot_mutate_or_archive(self):
        conn = object()
        self.server.connections = [conn]
        self.server.client_meta = {conn: {'proto_state': {'account_raw': b'test'}}}
        for action in ('update', 'archive'):
            ok, _ = azrok_admin_service.mutate(self.server, {
                'key': KEY, 'action': action, 'expected_revision': 1,
                'changes': {'fields': {'currency': 9}}, 'confirmation': 'Pet',
            })
            self.assertFalse(ok)
        self.assertTrue(self.path.is_file())

    def test_archive_requires_name_and_keeps_recoverable_copy(self):
        with self.assertRaises(ValueError):
            azrok_admin_service.mutate(self.server, {
                'key': KEY, 'action': 'archive', 'expected_revision': 1,
                'confirmation': 'wrong',
            })
        self.assertTrue(self.path.is_file())
        ok, result = azrok_admin_service.mutate(self.server, {
            'key': KEY, 'action': 'archive', 'expected_revision': 1,
            'confirmation': 'Pet',
        })
        self.assertTrue(ok, result)
        self.assertFalse(self.path.exists())
        backup = Path(self.temp.name) / 'admin_backups' / result['backup_id']
        self.assertTrue((backup / (self.path.name + '.removed')).is_file())


if __name__ == '__main__':
    unittest.main()
