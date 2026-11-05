"""Exercise protocol-context identity through the authenticated chat handler."""
import io
import json
import threading
import unittest
from unittest.mock import patch

from azrok_server import AzrokServer
from azrok_private_access import issue_browser_ticket
from tools.boxedwine_local.server import RangeRequestHandler


class PrivateChatIdentityTests(unittest.TestCase):
    def test_thirteen_byte_account_survives_context_and_opens_own_chat(self):
        secret = b'private-chat-test-secret-32-bytes!'
        account = 'a123456789012'
        server = AzrokServer.__new__(AzrokServer)
        server.proto_lock = threading.RLock()
        server.ctl_lock = threading.RLock()
        server.proto_state = {}
        conn = object()
        server.client_meta = {conn: {'proto_state': {'account_name': account}}}
        with server._client_protocol_context(conn):
            pass
        self.assertEqual(server.client_meta[conn]['account'], account)
        ticket = issue_browser_ticket(secret, 'browser_123456789012345678901234', account)
        handler = RangeRequestHandler.__new__(RangeRequestHandler)
        handler.private_access_secret = secret
        handler.private_account_registry = object()
        handler.client_address = ('127.0.0.1', 1234)
        handler._private_json_body = lambda: {'instance': ticket}
        results = []
        handler._send_private_json = results.append
        handler.send_error = lambda *args: self.fail(str(args))
        overview = {'server': {'players': [
            {'account': account[:-1] + '3', 'connected': True, 'entity_id': 99, 'room_kind': 27},
            {**server.client_meta[conn], 'connected': True, 'entity_id': 7, 'room_kind': 27},
        ]}}
        with patch('tools.boxedwine_local.server.urlopen', return_value=io.BytesIO(json.dumps(overview).encode())):
            handler.serve_private_chat_state()
        self.assertTrue(results[0]['ready'])
        self.assertEqual(results[0]['entity_id'], 7)


if __name__ == '__main__':
    unittest.main()
