import threading
import struct
import unittest

import azrok_server


class PlazaChairStateRequestTests(unittest.TestCase):
    def make_server(self):
        server = azrok_server.AzrokServer.__new__(azrok_server.AzrokServer)
        a, b, local = object(), object(), object()
        server.connections = [a, b, local]
        server.client_meta = {
            a: {'entity_id': 2, 'room_kind': azrok_server.PLAZA_ROOM_KIND,
                'visible_remote_actor_ids': {3}},
            b: {'entity_id': 3, 'room_kind': azrok_server.PLAZA_ROOM_KIND,
                'visible_remote_actor_ids': {2}},
            local: {'entity_id': 4, 'room_kind': 8},
        }
        server.ctl_lock = threading.RLock()
        server.event_ring = []
        server.event_seq = 0
        server.proto_state = {}
        emitted = []
        server._emit = lambda conn, frame, **kwargs: emitted.append((conn, frame)) or True
        return server, a, b, local, emitted

    def test_chair_request_is_exact_and_plaza_only(self):
        server, a, b, local, emitted = self.make_server()
        for bad in (b'', b'\x06', b'\x00\x00'):
            self.assertFalse(server._handle_plaza_chair_0069(a, bad, 1))
        self.assertFalse(server._handle_plaza_chair_0069(local, b'\x00', 1))
        self.assertTrue(server._handle_plaza_chair_0069(a, b'\x05', 1))
        self.assertEqual(server.client_meta[a]['plaza_chair_request'], 5)
        self.assertEqual([(conn, struct.unpack_from('<H', frame, 2)[0]) for conn, frame in emitted],
                         [(a, 0x006B), (b, 0x006C)])
        self.assertEqual(emitted[0][1][4:], b'\x00')

    def test_same_chair_assigns_distinct_original_table_sides(self):
        server, a, b, _local, emitted = self.make_server()
        self.assertTrue(server._handle_plaza_chair_0069(a, b'\x03', 1))
        self.assertTrue(server._handle_plaza_chair_0069(b, b'\x03', 2))
        self.assertEqual(server.client_meta[a]['plaza_chair_request'], 3)
        self.assertEqual(server.client_meta[b]['plaza_chair_request'], 3)
        self.assertEqual(server.client_meta[a]['plaza_chair_seat'], (3, 0))
        self.assertEqual(server.client_meta[b]['plaza_chair_seat'], (3, 1))
        self.assertEqual([(conn, struct.unpack_from('<H', frame, 2)[0]) for conn, frame in emitted],
                         [(a, 0x006B), (b, 0x006C), (b, 0x006B), (a, 0x006C)])
        self.assertEqual(emitted[1][1][4:], struct.pack('<BBI', 3, 0, 2))
        self.assertEqual(emitted[3][1][4:], struct.pack('<BBI', 3, 1, 3))

    def test_actor_state_request_is_empty_and_plaza_only(self):
        server, a, _b, local, emitted = self.make_server()
        self.assertFalse(server._handle_plaza_actor_state_006a(a, b'\x00', 1))
        self.assertFalse(server._handle_plaza_actor_state_006a(local, b'', 1))
        self.assertTrue(server._handle_plaza_actor_state_006a(a, b'', 1))
        self.assertEqual(server.client_meta[a]['plaza_actor_state_requests'], 1)
        self.assertEqual(emitted, [])

    def test_actor_state_releases_only_owned_seat(self):
        server, a, b, _local, emitted = self.make_server()
        server._handle_plaza_chair_0069(a, b'\x03', 1)
        emitted.clear()
        self.assertTrue(server._handle_plaza_actor_state_006a(a, b'', 2))
        self.assertNotIn('plaza_chair_seat', server.client_meta[a])
        self.assertEqual([(conn, struct.unpack_from('<H', frame, 2)[0]) for conn, frame in emitted],
                         [(a, 0x006B), (a, 0x0069), (b, 0x006C), (b, 0x0069)])
        self.assertEqual(emitted[0][1][4:], b'\x02')
        self.assertEqual(emitted[1][1][4:], struct.pack('<IiiI', 1, -1200, -2903, 0))
        self.assertEqual(emitted[2][1][4:], struct.pack('<BBI', 3, 2, 2))
        self.assertEqual(emitted[3][1][4:], struct.pack('<IiiI', 2, -1200, -2903, 0))
        self.assertEqual((server.client_meta[a]['x'], server.client_meta[a]['y']), (-1200, -2903))
        self.assertTrue(server._handle_plaza_chair_0069(b, b'\x03', 3))
        self.assertEqual(server.client_meta[b]['plaza_chair_seat'], (3, 0))

    def test_full_chair_rejects_third_actor_without_colliding(self):
        server, a, b, third, emitted = self.make_server()
        server.client_meta[third]['room_kind'] = azrok_server.PLAZA_ROOM_KIND
        server.client_meta[third]['visible_remote_actor_ids'] = {2, 3}
        server._handle_plaza_chair_0069(a, b'\x01', 1)
        server._handle_plaza_chair_0069(b, b'\x01', 2)
        emitted.clear()
        self.assertFalse(server._handle_plaza_chair_0069(third, b'\x01', 3))
        self.assertNotIn('plaza_chair_seat', server.client_meta[third])
        self.assertEqual([(conn, struct.unpack_from('<H', frame, 2)[0]) for conn, frame in emitted],
                         [(third, 0x006B)])
        self.assertEqual(emitted[0][1][4:], b'\x02')

    def test_joining_peer_spawn_record_carries_allocated_seat(self):
        server, a, b, _local, emitted = self.make_server()
        server._handle_plaza_chair_0069(a, b'\x04', 1)
        record = server._build_state_0066_actor_record(
            2, 0, b'Player', chair_seat=server.client_meta[a]['plaza_chair_seat']
        )
        self.assertEqual(record[0x18:0x1A], b'\x04\x00')
        self.assertEqual(server._build_state_0066_actor_record(2, 0, b'Player')[0x18], 0xFF)
        server._read_canonical_accessory_slots = lambda *_args: None
        server._read_canonical_actor_evolution = lambda *_args: 0
        emitted.clear()
        server._send_room_roster(b, azrok_server.PLAZA_ROOM_KIND)
        self.assertEqual([(conn, struct.unpack_from('<H', frame, 2)[0]) for conn, frame in emitted],
                         [(b, 0x0066)])
        seated_record = emitted[0][1][4:]
        self.assertEqual(seated_record[0], 0)
        self.assertEqual(seated_record[0x18:0x1A], b'\x04\x00')

    def test_room_departure_and_reentry_clear_old_chair_request(self):
        server, a, _b, _local, _emitted = self.make_server()
        server._notify_room_departure = lambda *args, **kwargs: None
        server._send_room_roster = lambda *args, **kwargs: None
        self.assertTrue(server._handle_plaza_chair_0069(a, b'\x02', 1))
        server._relay_to_room_peers(a, 0x0065, struct.pack('<BBii', 8, 0, 0, 0), 2)
        self.assertNotIn('plaza_chair_request', server.client_meta[a])
        self.assertNotIn('plaza_chair_seat', server.client_meta[a])
        server._relay_to_room_peers(
            a, 0x0065, struct.pack('<BBii', azrok_server.PLAZA_ROOM_KIND, 0, 0, 0), 3
        )
        self.assertNotIn('plaza_chair_request', server.client_meta[a])
        self.assertNotIn('plaza_chair_seat', server.client_meta[a])


if __name__ == '__main__':
    unittest.main()
