import os
import tempfile
import threading
import unittest

import azrok_admin_history as history


class FakeServer:
    def __init__(self, state_dir):
        self.state_store_dir = state_dir
        self.ctl_lock = threading.RLock()
        self.client_meta = {}


class AdminHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = FakeServer(self.tmp.name)
        self.key = 'a746573746572_s0_c506c61796572'  # tester / Player
        self.server.client_meta[object()] = {
            'entity_id': 7,
            'account': 'tester',
            'proto_state': {'account_raw': b'tester', 'selected_character_key': None},
        }

    def test_login_is_account_scoped_and_chat_is_character_scoped(self):
        self.assertTrue(history.record_event(self.server, 'login', '로그인', 7))
        login = history.latest_login_by_account(self.server)
        self.assertIn('tester', login['latest'])
        self.server.client_meta[next(iter(self.server.client_meta))]['proto_state']['selected_character_key'] = self.key
        self.assertTrue(history.record_event(self.server, 'chat', '안녕하세요', 7,
                                             {'password': 'never', 'payload_hex': 'secret'}))
        access = history.history_for_key(self.server, self.key, 'access')
        chat = history.history_for_key(self.server, self.key, 'chat')
        self.assertEqual([x['event'] for x in access['entries']], ['login'])
        self.assertEqual([x['message'] for x in chat['entries']], ['안녕하세요'])
        with open(history.journal_path(self.server), encoding='utf-8') as stream:
            raw = stream.read()
        self.assertNotIn('never', raw)
        self.assertNotIn('secret', raw)
        self.assertNotIn('account_raw', raw)

    def test_unknown_account_and_chat_without_character_are_not_recorded(self):
        other = FakeServer(self.tmp.name)
        other.client_meta[object()] = {'entity_id': 8, 'proto_state': {}}
        self.assertFalse(history.record_event(other, 'login', '로그인', 8))
        self.assertFalse(history.record_event(self.server, 'chat', '안녕하세요', 7))
        self.assertFalse(os.path.exists(history.journal_path(self.server)))

    def test_admin_event_uses_canonical_key_without_live_connection(self):
        self.assertTrue(history.record_event(
            self.server, 'audit', '레벨 수정', details={'key': self.key, 'action': 'update', 'password': 'hidden'}
        ))
        result = history.history_for_key(self.server, self.key, 'audit')
        self.assertEqual(result['entries'][0]['account'], 'tester')
        self.assertEqual(result['entries'][0]['details'], {'action': 'update'})
        self.assertEqual(result['corrupt_lines'], 0)

    def test_bounded_tail_reports_incomplete_history(self):
        self.server.client_meta[next(iter(self.server.client_meta))]['proto_state']['selected_character_key'] = self.key
        for number in range(30):
            history.record_event(self.server, 'chat', f'{number} '+('x' * 100), 7)
        result = history.history_for_key(self.server, self.key, 'chat', max_bytes=1024)
        self.assertTrue(result['truncated'])
        self.assertLess(len(result['entries']), 30)
        self.assertEqual(result['entries'][0]['message'][:2], '29')

    def test_corrupt_lines_are_counted_without_exposing_them(self):
        history.record_event(self.server, 'login', '로그인', 7)
        with open(history.journal_path(self.server), 'ab') as stream:
            stream.write(b'not json\n')
        result = history.latest_login_by_account(self.server)
        self.assertEqual(result['corrupt_lines'], 1)
        self.assertIn('tester', result['latest'])

    def test_operator_history_filters_across_accounts_without_raw_payloads(self):
        history.record_event(self.server, 'login', '로그인', 7)
        history.record_event(self.server, 'chat', '테스트 메시지', details={'key': self.key})
        other = 'a6f74686572_s0_c506574'
        history.record_event(self.server, 'audit', '아이템 수정', details={'key': other})
        self.assertEqual(3, len(history.recent_history(self.server)['entries']))
        result = history.recent_history(self.server, 'chat', '메시지')
        self.assertEqual(['테스트 메시지'], [x['message'] for x in result['entries']])
        self.assertEqual('other', history.recent_history(self.server, 'audit', 'OTHER')['entries'][0]['account'])
        with self.assertRaises(ValueError):
            history.recent_history(self.server, 'raw')


if __name__ == '__main__':
    unittest.main()
