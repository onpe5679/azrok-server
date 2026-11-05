import struct
import unittest

from azrok_server import (
    AzrokServer,
    LOCAL_ROOM_NAMES_BY_WIRE_KIND,
    PATHOUSE_ROOM_KINDS,
    decode_c2s_0065,
    decode_c2s_0066,
    decode_c2s_0067,
    world_grid_cell,
)


class ServerRoomMappingTests(unittest.TestCase):
    def test_verified_local_room_wire_kinds(self):
        expected = {
            0x01: "pathouse",
            0x06: "playroom",
            0x08: "gym",
            0x09: "magic",
            0x07: "cook",
            0x0B: "shop",
            0x0A: "library",
            0x0C: "ground",
        }
        self.assertEqual(LOCAL_ROOM_NAMES_BY_WIRE_KIND, expected)
        self.assertEqual(
            {kind: AzrokServer._room_name_from_kind(kind) for kind in expected},
            expected,
        )
        self.assertEqual(AzrokServer._room_name_from_kind(3), "kind 0x03")
        self.assertEqual(AzrokServer._room_name_from_kind(4), "kind 0x04")

    def test_playroom_packet_uses_signed_coordinates(self):
        payload = bytes.fromhex("06074ef1ffffb0f0ffff")
        self.assertEqual(decode_c2s_0065(payload), (0x06, 0x07, -3762, -3920))

    def test_decoder_rejects_short_payload(self):
        with self.assertRaises(ValueError):
            decode_c2s_0065(struct.pack("<BBi", 6, 7, -3762))

    def test_movement_packets_use_signed_coordinates(self):
        p66 = struct.pack("<BiiiiiB", 3, -10, 20, -30, -40, 1234, 1)
        self.assertEqual(
            decode_c2s_0066(p66),
            (3, -10, 20, -30, -40, 1234, 1),
        )
        p67 = struct.pack("<BiiIH", 4, -50, -60, 0x10203040, 0x5060)
        self.assertEqual(
            decode_c2s_0067(p67),
            (4, -50, -60, 0x10203040, 0x5060),
        )

    def test_live_0066_layout_exposes_current_cell_and_destination(self):
        payload = bytes.fromhex(
            "1b7b0f0000c30000001b0f0000a8010000dd04000000"
        )
        self.assertEqual(
            decode_c2s_0066(payload),
            (0x1B, 3963, 195, 3867, 424, 1245, 0),
        )
        self.assertEqual(world_grid_cell(3867, 424), 0x1B)

        # Real wire sample from packets_20260717_080648.txt: byte0 follows
        # current (3963,195)=27 while the clicked destination is cell 26.
        crossing = bytes.fromhex(
            "1b7b0f0000c3000000390c000013ffffff6912000000"
        )
        decoded = decode_c2s_0066(crossing)
        self.assertEqual(decoded, (27, 3963, 195, 3129, -237, 4713, 0))
        self.assertEqual(world_grid_cell(decoded[1], decoded[2]), 27)
        self.assertEqual(world_grid_cell(decoded[3], decoded[4]), 26)

    def test_world_grid_cell_covers_signed_outer_cells(self):
        self.assertEqual(world_grid_cell(-8999, -8999), 0)
        self.assertEqual(world_grid_cell(8999, 8999), 35)

    def test_pathouse_bootstrap_and_wire_kinds_are_both_counted(self):
        self.assertEqual(PATHOUSE_ROOM_KINDS, frozenset((-1, 1)))


if __name__ == "__main__":
    unittest.main()
