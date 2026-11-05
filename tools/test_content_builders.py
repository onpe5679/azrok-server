# -*- coding: utf-8 -*-
"""Isolated contract tests for the content-state packet builders."""

import os
import struct
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import azrok_server as server_module


class ContentBuilderContractTests(unittest.TestCase):
    def setUp(self):
        self.original_content_profile = server_module.CONTENT_PROFILE
        self.original_registry_profile = server_module.ITEM_REGISTRY_000A_PROFILE
        self.original_high_registry = (
            server_module.ITEM_REGISTRY_000A_HIGH_RESOURCE_DIAGNOSTIC
        )
        self.original_evolution = server_module.AZRON_EVOLUTION
        self.original_native_fresh_tutorial = (
            server_module.NATIVE_FRESH_TUTORIAL_ENABLED
        )

        server_module.CONTENT_PROFILE = 'shipped'
        server_module.ITEM_REGISTRY_000A_PROFILE = 'binary'
        server_module.ITEM_REGISTRY_000A_HIGH_RESOURCE_DIAGNOSTIC = False
        server_module.AZRON_EVOLUTION = 0
        server_module.NATIVE_FRESH_TUTORIAL_ENABLED = False

        # Avoid sockets/files/process handles: the builders need only these
        # methods, and persisted-state overlay is tested independently.
        self.server = server_module.AzrokServer.__new__(server_module.AzrokServer)
        self.server._apply_saved_character_state = lambda _zone_payload: False
        self.server._apply_canonical_server_state = lambda _zone_payload: False

    def tearDown(self):
        server_module.CONTENT_PROFILE = self.original_content_profile
        server_module.ITEM_REGISTRY_000A_PROFILE = self.original_registry_profile
        server_module.ITEM_REGISTRY_000A_HIGH_RESOURCE_DIAGNOSTIC = (
            self.original_high_registry
        )
        server_module.AZRON_EVOLUTION = self.original_evolution
        server_module.NATIVE_FRESH_TUTORIAL_ENABLED = (
            self.original_native_fresh_tutorial
        )

    def build_zone(self, client_payload=None):
        if client_payload is None:
            client_payload = b'\x00' * 0xC4
        return self.server._build_zone_0007_draft(client_payload)

    @staticmethod
    def bind_selected_test_character(server):
        """Give a direct builder fixture the create/select authority it models."""
        server.proto_state['client_0005_seen'] = True
        server.proto_state['selected_character_key'] = server._character_state_key()
        server._add_event = lambda *args, **kwargs: None
        server._entity_id_for_proto_state = lambda _state: 1

    def test_supported_defaults_are_shipped_and_binary(self):
        self.assertEqual(server_module.DEFAULT_CONTENT_PROFILE, 'shipped')
        self.assertEqual(
            server_module.DEFAULT_ITEM_REGISTRY_000A_PROFILE, 'binary'
        )

    def test_shipped_stats_have_corrected_lgc_alignment(self):
        payload = self.build_zone()
        stats = struct.unpack_from('<70H', payload, 0x0B)

        self.assertEqual(len(payload), 0x1D8)
        self.assertEqual(tuple(stats[:57]), server_module.SHIPPED_CONTENT_STATS)
        self.assertEqual(stats[57:], (0,) * 13)
        self.assertEqual(stats[26], 0)    # meal/food counter inserted by lgc.tmp
        self.assertEqual(stats[32], 500)  # dumbbell experience
        self.assertEqual(stats[55], 1)    # pet evolution stat
        self.assertEqual(stats[56], 2)    # pet selector stat

    def test_header_evolution_is_independent_from_shipped_stat_55(self):
        payload = self.build_zone()
        stats = struct.unpack_from('<70H', payload, 0x0B)

        self.assertEqual(payload[0x02], 0)
        self.assertEqual(stats[55], 1)

    def test_fresh_species_header_and_stat56_use_the_same_selected_type(self):
        for char_type in range(4):
            with self.subTest(char_type=char_type):
                self.server.proto_state = {
                    'char_type': char_type,
                    'selected_evolution': 0,
                }
                payload = self.build_zone()
                stats = struct.unpack_from('<70H', payload, 0x0B)

                self.assertEqual(len(payload), 0x1D8)
                self.assertEqual(payload[0x01], char_type)
                self.assertEqual(payload[0x02], 0)
                self.assertEqual(stats[56], char_type)

    def test_minimal_profile_remains_explicit_diagnostic(self):
        server_module.CONTENT_PROFILE = 'minimal'
        payload = self.build_zone()
        stats = struct.unpack_from('<70H', payload, 0x0B)
        expected = tuple(
            server_module.MINIMAL_CONTENT_STATS.get(index, 0)
            for index in range(70)
        )
        self.assertEqual(stats, expected)

    def test_playable_profile_uses_native_fresh_seed_with_original_zero_date(self):
        server_module.CONTENT_PROFILE = 'playable'
        server_module.NATIVE_FRESH_TUTORIAL_ENABLED = True
        payload = self.build_zone()
        stats = struct.unpack_from('<70H', payload, 0x0B)

        self.assertEqual(stats, server_module.PLAYABLE_CONTENT_STATS)
        self.assertEqual(stats[1:3], (1, 0))
        self.assertEqual(stats[3], 100)
        self.assertEqual(stats[5:7], (100, 100))
        self.assertEqual(stats[9], 300)
        self.assertEqual(stats[18:25], (100,) * 7)
        self.assertEqual(stats[25:], (0,) * 45)
        self.assertEqual(struct.unpack_from('<10H', payload, 0x134), (0xFF,) * 10)
        self.assertEqual(struct.unpack_from('<10H', payload, 0x148), (0xFF,) * 10)
        self.assertEqual(struct.unpack_from('<I', payload, 0x03)[0], 0)
        self.assertEqual(payload[0x02], 0)

    def test_native_fresh_tutorial_current_date_remains_explicit_opt_out(self):
        server_module.CONTENT_PROFILE = 'playable'
        server_module.NATIVE_FRESH_TUTORIAL_ENABLED = False

        payload = self.build_zone()

        self.assertNotEqual(struct.unpack_from('<I', payload, 0x03)[0], 0)
        self.assertEqual(struct.unpack_from('<10H', payload, 0x134), (0xFF,) * 10)

    def test_playable_reconnect_uses_valid_date_and_saved_stats(self):
        server_module.CONTENT_PROFILE = 'playable'
        self.server.proto_state = {}
        saved = [0] * 70
        saved[1] = 7
        saved[56] = 3

        def restore(payload):
            for index, value in enumerate(saved):
                struct.pack_into('<H', payload, 0x0B + index * 2, value)
            return True

        self.server._apply_saved_character_state = restore
        payload = self.build_zone()
        stats = struct.unpack_from('<70H', payload, 0x0B)

        self.assertNotEqual(struct.unpack_from('<I', payload, 0x03)[0], 0)
        self.assertEqual(stats[1], 7)
        self.assertEqual(stats[56], 3)

    def test_c2s_prefix_and_tail_cannot_contaminate_s2c_inventory(self):
        payload = self.build_zone(b'\xA5' * 0xC4)

        self.assertEqual(struct.unpack_from('<I', payload, 0x07)[0], 0)
        inventory_ranges = (
            (0x97, 33),  # Furniture
            (0xB8, 15),  # Drug
            (0xC7, 20),  # Energy
            (0xEA, 38),  # Food
            (0x110, 3),  # Ingredient
            (0x113, 10), # Toy
            (0x11D, 8),  # Gym
            (0x131, 1),  # Book
        )
        for offset, size in inventory_ranges:
            self.assertEqual(
                payload[offset:offset + size],
                b'\x00' * size,
                f'inventory range +0x{offset:X} was contaminated',
            )
        self.assertEqual(payload[0x125:0x130], b'\xFF' * 11)
        self.assertEqual(payload[0x1D4:0x1D8], b'\xFF' * 4)

    def test_shipped_profile_has_evolution_runtime_row_but_no_starter_quests(self):
        payload = self.build_zone()
        # Runtime rows are shared infrastructure, not quest-display-only
        # data.  kind=3/aux=0 lets a later natural care action run the stage-0
        # evolution threshold without setting the bootstrap selector byte.
        self.assertEqual(
            struct.unpack_from('<10H', payload, 0x134),
            (3,) + (0xFF,) * 9,
        )
        self.assertEqual(
            struct.unpack_from('<10H', payload, 0x148),
            (0,) + (0xFF,) * 9,
        )
        self.assertEqual(struct.unpack_from('<10I', payload, 0x15C), (0,) * 10)
        self.assertEqual(payload[0x02], 0)

    def test_domain_banks_use_ff_empty_sentinel_before_client_fixed_entries(self):
        payload = self.build_zone()

        # FUN_005AB1B0 treats every value other than 0xFF as live.  The wire
        # defaults must therefore be empty even though the client subsequently
        # overwrites 16 fixed entries before importing all four 10-byte banks.
        self.assertEqual(payload[0x1AC:0x1D4], b'\xFF' * 40)
        effective = bytearray(payload[0x1AC:0x1D4])
        fixed_entries = {
            0x04: 4, 0x05: 5, 0x06: 6, 0x07: 7, 0x08: 8, 0x09: 9,
            0x0F: 5, 0x10: 6,
            0x17: 3,
            0x1F: 1, 0x20: 2, 0x21: 3, 0x22: 4, 0x23: 5,
            0x24: 6, 0x25: 7,
        }
        for offset, value in fixed_entries.items():
            effective[offset] = value

        self.assertEqual(sum(value != 0xFF for value in effective), 16)
        self.assertEqual(effective[0:10], bytes([0xFF] * 4 + list(range(4, 10))))
        self.assertEqual(effective[10:20], bytes([0xFF] * 5 + [5, 6] + [0xFF] * 3))
        self.assertEqual(effective[20:30], bytes([0xFF] * 3 + [3] + [0xFF] * 6))
        self.assertEqual(effective[30:40], bytes([0xFF] + list(range(1, 8)) + [0xFF] * 2))
        self.assertEqual(payload[0x1D4:0x1D8], b'\xFF' * 4)

    def test_000a_binary_item_registry_is_exact_75_u16(self):
        payload = self.server._build_item_registry_000A_draft()
        expected = tuple(
            value
            for group_index in range(7)
            for value in server_module.ITEM_REGISTRY_000A_BINARY_DEFAULTS[
                f'group{group_index}'
            ]
        )

        self.assertEqual(len(payload), 0x96)
        self.assertEqual(len(expected), 75)
        self.assertEqual(struct.unpack('<75H', payload), expected)

    def test_000b_xp_curve_is_unchanged(self):
        payload = self.server._build_stat_table_0011_draft()
        self.assertEqual(len(payload), 0x3E)
        self.assertEqual(
            struct.unpack('<31H', payload),
            tuple(server_module.STAT_TABLE_0011_DEFAULTS),
        )

    def test_periodic_snapshot_merges_0017_authority_for_stat_55_56(self):
        saver = server_module.AzrokServer.__new__(server_module.AzrokServer)
        saver.proto_state = {
            'char_name_raw': b'Player',
        }
        self.bind_selected_test_character(saver)
        saver.proto_state['c2s_0017_stat_authority'] = {0x37: 1, 0x38: 2}
        saver.proto_state['c2s_0017_authority_key'] = (
            saver._selected_character_state_key()
        )
        saver.saved_character_states = {}
        incoming = bytearray(0xC4)
        # Reproduce the live asymmetry: the periodic snapshot says 0/0 even
        # though the adjacent C2S0017 reports say stat55/stat56 = 1/2.
        self.assertEqual(struct.unpack_from('<2H', incoming, 0x0A + 0x37 * 2), (0, 0))

        with tempfile.TemporaryDirectory() as temp_dir:
            saver.state_store_dir = temp_dir
            self.assertTrue(saver._save_character_state_snapshot(incoming))
            stored = saver.saved_character_states[saver._character_state_key()]

        stats = struct.unpack_from('<70H', stored, 0x0A)
        self.assertEqual(stats[0x37:0x39], (1, 2))
        self.assertEqual(
            struct.unpack_from('<I', stored, 0x96)[0],
            sum(stats[0x1E:0x42]),
        )
        self.assertEqual(
            saver.proto_state['last_content_save_merged_stat_ids'],
            [0x37, 0x38],
        )

    def test_gym_stat_triad_round_trips_through_persisted_snapshot(self):
        saver = server_module.AzrokServer.__new__(server_module.AzrokServer)
        saver.proto_state = {
            'char_name_raw': b'GymRoundTrip',
        }
        self.bind_selected_test_character(saver)
        saver.proto_state['c2s_0017_stat_authority'] = {0x37: 1, 0x38: 2}
        saver.proto_state['c2s_0017_authority_key'] = (
            saver._selected_character_state_key()
        )
        saver.saved_character_states = {}
        incoming = bytearray(0xC4)
        expected = (103, 203, 303)
        for stat_id, value in zip((0x1F, 0x20, 0x21), expected):
            struct.pack_into('<H', incoming, 0x0A + stat_id * 2, value)

        with tempfile.TemporaryDirectory() as temp_dir:
            saver.state_store_dir = temp_dir
            self.assertTrue(saver._save_character_state_snapshot(incoming))
            zone_payload = bytearray(0x1D8)
            self.assertTrue(saver._apply_saved_character_state(zone_payload))

        restored = struct.unpack_from('<70H', zone_payload, 0x0B)
        self.assertEqual(restored[0x1F:0x22], expected)
        self.assertEqual(restored[0x37:0x39], (1, 2))

    def test_persisted_evolution_maps_from_c2s_05_to_s2c_02(self):
        saver = server_module.AzrokServer.__new__(server_module.AzrokServer)
        # This test exercises directional field mapping, not evolution
        # authorization.  Seed the server-issued baseline at stage 1 so the
        # first snapshot is a same-stage persistence rather than an
        # unverified 0->1 jump.
        saver.proto_state = {
            'char_name_raw': b'EvolutionRoundTrip',
            'selected_evolution': 1,
        }
        self.bind_selected_test_character(saver)
        saver.saved_character_states = {}
        incoming = bytearray(0xC4)
        incoming[0x05] = 1

        with tempfile.TemporaryDirectory() as temp_dir:
            saver.state_store_dir = temp_dir
            self.assertTrue(saver._save_character_state_snapshot(incoming))
            zone_payload = bytearray(0x1D8)
            zone_payload[0x02] = 0
            self.assertTrue(saver._apply_saved_character_state(zone_payload))

        self.assertEqual(saver.proto_state['persisted_evolution'], 1)
        self.assertEqual(zone_payload[0x02], 1)

    def test_persisted_snapshot_remains_authoritative_for_stat56(self):
        saver = server_module.AzrokServer.__new__(server_module.AzrokServer)
        saver.proto_state = {
            'char_name_raw': b'SpeciesRoundTrip',
            'char_type': 1,
        }
        self.bind_selected_test_character(saver)
        saver.proto_state['c2s_0017_stat_authority'] = {0x38: 3}
        saver.proto_state['c2s_0017_authority_key'] = (
            saver._selected_character_state_key()
        )
        saver.saved_character_states = {}
        incoming = bytearray(0xC4)
        struct.pack_into('<H', incoming, 0x0A + 56 * 2, 3)

        with tempfile.TemporaryDirectory() as temp_dir:
            saver.state_store_dir = temp_dir
            self.assertTrue(saver._save_character_state_snapshot(incoming))
            zone_payload = bytearray(0x1D8)
            self.assertTrue(saver._apply_saved_character_state(zone_payload))

        restored = struct.unpack_from('<70H', zone_payload, 0x0B)
        self.assertEqual(restored[56], 3)

    def test_first_c2s_0007_after_proactive_zone_bundle_is_persisted(self):
        receiver = server_module.AzrokServer.__new__(server_module.AzrokServer)
        receiver.proto_state = {
            'zone_request_count': 1,
            'client_0007_count': 0,
            'content_save_count': 0,
            'char_name_raw': b'BoundFixture',
        }
        self.bind_selected_test_character(receiver)
        saved_payloads = []
        events = []
        receiver._save_character_state_snapshot = (
            lambda payload: saved_payloads.append(bytes(payload)) or True
        )
        receiver._entity_id_for_proto_state = lambda _state: 2
        receiver._add_event = lambda *args, **kwargs: events.append((args, kwargs))

        snapshot = bytearray(0xC4)
        struct.pack_into('<H', snapshot, 0x0A + 0x1F * 2, 3)
        stats = struct.unpack_from('<70H', snapshot, 0x0A)
        struct.pack_into('<I', snapshot, 0x96, sum(stats[0x1E:0x42]))

        response = receiver._build_response(0x0007, bytes(snapshot), pkt_num=1)

        self.assertIsNone(response)
        self.assertEqual(saved_payloads, [bytes(snapshot)])
        self.assertEqual(receiver.proto_state['client_0007_count'], 1)
        self.assertEqual(receiver.proto_state['content_save_count'], 1)
        self.assertEqual(receiver.proto_state['last_content_save_stat_0x1F'], 3)
        self.assertEqual(len(events), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
