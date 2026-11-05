"""Remote actor stage must come from its own durable character profile."""
import tempfile
import threading
import unittest
import struct

import azrok_server as game
from tools import test_server_contract_layers as fixtures


class PeerEvolutionTests(unittest.TestCase):
    def test_information_reads_durable_ox_results_for_target_only(self):
        from azrok_ox_progression import record_ox_result
        helper = fixtures.SocialStateContractTests()
        server, source, peer, _, emitted = helper.make_server()
        with tempfile.TemporaryDirectory() as directory:
            server.state_store_dir = directory
            server.client_meta[peer]['proto_state'] = {
                'client_0005_seen': True, 'selected_character_key': 'peer_key'}
            record_ox_result(directory, 'peer_key', 'a' * 32, 'won', 1)
            record_ox_result(directory, 'peer_key', 'b' * 32, 'eliminated', 0)
            self.assertTrue(server._relay_community_006c(source, struct.pack('<I', 3), 1))
            payload = fixtures.parse_frames(server, emitted[0][1])[0][1]
            self.assertEqual(struct.unpack('<BBHII', payload), (1, 1, 1, 2, 1))

    def test_roster_uses_peer_saved_stage_after_cache_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            server = fixtures.CanonicalStateContractTests().make_server(directory)
            key = server._selected_character_state_key()
            state = server._load_canonical_character_state(key=key)
            snapshot = bytearray(196)
            snapshot[5] = 1
            state['snapshot_hex'] = snapshot.hex()
            self.assertTrue(server._save_canonical_character_state(state, key=key))
            server.saved_server_states = {}
            recipient, peer = object(), object()
            server.connections = [recipient, peer]
            server.ctl_lock = threading.RLock()
            server.client_meta = {
                recipient: {'entity_id': 2, 'room_kind': game.PLAZA_ROOM_KIND,
                            'proto_state': {'selected_evolution': 3}},
                peer: {'entity_id': 3, 'room_kind': game.PLAZA_ROOM_KIND,
                       'name': 'Peer', 'char_type': 0,
                       'proto_state': {'client_0005_seen': True,
                                       'selected_character_key': key,
                                       'selected_evolution': 0}},
            }
            frames = []
            server._emit = lambda conn, data, **kw: frames.extend(fixtures.parse_frames(server, data)) or True
            server._send_room_roster(recipient, game.PLAZA_ROOM_KIND)
            actor = next(payload for opcode, payload in frames if opcode == 0x66)
            self.assertEqual((actor[5], actor[6]), (0, 1))
            self.assertEqual(server.saved_server_states, {})

    def test_missing_peer_does_not_create_recipient_state_under_peer_key(self):
        with tempfile.TemporaryDirectory() as directory:
            server = fixtures.CanonicalStateContractTests().make_server(directory)
            self.assertEqual(server._read_canonical_actor_evolution('missing', {'selected_evolution': 2}), 2)
            self.assertNotIn('missing', server.saved_server_states)
            self.assertEqual(server._read_canonical_actor_evolution(None, {'selected_evolution': 8}), 0)

    def test_builder_rejects_unrenderable_stage(self):
        server = game.AzrokServer.__new__(game.AzrokServer)
        for stage in (-1, 4, None):
            with self.assertRaises(ValueError):
                server._build_state_0066_actor_record(3, 0, b'Peer', evolution=stage)


if __name__ == '__main__':
    unittest.main()

