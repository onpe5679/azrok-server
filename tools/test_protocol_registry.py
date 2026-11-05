import dataclasses
import json
import unittest

from azrok_protocol_registry import (
    METADATA_SPEC_ID,
    NATIVE_PROTOCOL_LINKS,
    NATIVE_PROTOCOL_SYMBOLS,
    ORIGINAL_C2S_SENDERS,
    ORIGINAL_WIRE_FRAME,
    PROTOCOL_BY_DIRECTION,
    PROTOCOL_BY_MODE,
    PROTOCOL_SPECS,
    REGISTRY_SPEC_ID,
    PayloadRule,
    compute_registry_spec_id,
    find_spec,
    legacy_contracts,
    registry_json,
)


class ProtocolRegistryTests(unittest.TestCase):
    C2S_OPCODES = {
        0x0000, 0x0002, 0x0004, 0x0005, 0x0006, 0x0007, 0x0008, 0x0009, 0x000A,
        0x000B, 0x000D, 0x000E, 0x000F, 0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0016,
        0x0017, 0x0018, 0x0019, 0x0064, 0x0065, 0x0066, 0x0067, 0x0068,
        0x0069, 0x006A, 0x006B, 0x006C, 0x00C8, 0x00C9, 0x00CA,
    }
    S2C_OPCODES = {
        0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x0008, 0x0009,
        0x000A, 0x000B, 0x000C, 0x000D, 0x0016, 0x0064, 0x0065, 0x0066,
        0x0067, 0x0068, 0x0069, 0x006A, 0x006B, 0x006C, 0x006D, 0x006E, 0x0070, 0x00C8, 0x00C9,
        0x00CA, 0x00CB, 0x00CC, 0x00CD, 0x00CE, 0x00CF, 0x00D0, 0x00D1,
        0x00D2, 0x00D3, 0x00D4,
    }

    def test_union_has_all_74_directional_entries(self):
        self.assertEqual(74, len(PROTOCOL_SPECS))
        self.assertEqual(
            self.C2S_OPCODES,
            {spec.opcode for spec in PROTOCOL_SPECS if spec.direction == "C->S"},
        )
        self.assertEqual(
            self.S2C_OPCODES,
            {spec.opcode for spec in PROTOCOL_SPECS if spec.direction == "S->C"},
        )
        self.assertEqual(74, len(PROTOCOL_BY_DIRECTION))
        self.assertEqual(
            len(PROTOCOL_BY_MODE),
            sum(len(spec.modes) for spec in PROTOCOL_SPECS),
        )

    def test_unresolved_c2s_000b_is_explicit_not_verified(self):
        spec = find_spec("C->S", 0x000B)
        self.assertIsNotNone(spec)
        self.assertEqual("NOT VERIFIED", spec.status)
        self.assertEqual("not_verified", spec.implementation)
        self.assertFalse(spec.payload.constrained)

    def test_character_logout_is_exact_empty_in_both_directions(self):
        request = find_spec("C->S", 0x0002)
        ack = find_spec("S->C", 0x0002)
        self.assertEqual((0,), request.payload.exact)
        self.assertEqual((0,), ack.payload.exact)
        self.assertEqual("VERIFIED", request.status)
        self.assertEqual("VERIFIED", ack.status)

    def test_character_create_result_is_exact_two_bytes(self):
        ack = find_spec("S->C", 0x0006)
        self.assertIsNotNone(ack)
        self.assertEqual((2,), ack.payload.exact)
        self.assertEqual("VERIFIED", ack.status)

    def test_inventory_and_growth_reports_have_verified_exact_contracts(self):
        expected = {
            0x0008: (41, 'inventory-snapshot'),
            0x0009: (10, 'inventory-snapshot'),
            0x000A: (8, 'inventory-snapshot'),
            0x0010: (2, 'runtime-row-correlation'),
            0x0011: (80, 'runtime-row-snapshot'),
            0x0012: (5, 'quest-reward-correlation'),
            0x0014: (2, 'medicine-mutation'),
        }
        for opcode, (size, persistence) in expected.items():
            with self.subTest(opcode=opcode):
                spec = find_spec("C->S", opcode)
                self.assertEqual("VERIFIED", spec.status)
                self.assertEqual("implemented", spec.implementation)
                self.assertEqual((size,), spec.payload.exact)
                self.assertEqual(persistence, spec.persistence)

    def test_direction_and_mode_are_not_merged(self):
        c2s = find_spec("C->S", 0x0068, 1)
        s2c = find_spec("S->C", 0x0068, 1)
        self.assertEqual("chat transmit", c2s.label)
        self.assertEqual("remote actor position", s2c.label)
        self.assertIsNone(find_spec("C->S", 0x0068, 0))
        self.assertEqual(("2",), find_spec("C->S", 0x00CA, 2).modes)
        self.assertIsNone(find_spec("C->S", 0x00CA, 1))
        # A common entry is an explicit fallback, not a claim about live mode.
        self.assertEqual("login/connect request", find_spec("C->S", 0x0000, 2).label)

    def test_corrected_item_room_and_chat_length_boundaries(self):
        toy = find_spec("C->S", 0x000D).payload
        gym = find_spec("C->S", 0x000E).payload
        room = find_spec("C->S", 0x0065).payload
        chat = find_spec("C->S", 0x0068).payload

        self.assertIsNone(toy.length_error(4))
        self.assertIsNotNone(toy.length_error(8))
        self.assertIsNone(gym.length_error(3))
        self.assertIsNotNone(gym.length_error(8))

        self.assertIsNotNone(room.length_error(9))
        self.assertIsNone(room.length_error(10))
        self.assertIsNone(room.length_error(18))

        self.assertIsNotNone(chat.length_error(17))
        self.assertIsNone(chat.length_error(18))
        self.assertIsNone(chat.length_error(199))
        self.assertIsNotNone(chat.length_error(200))
        self.assertEqual("18..199", chat.display())

    def test_alternative_and_multiple_length_rules_remain_typed(self):
        result = find_spec("S->C", 0x0005).payload
        actors = find_spec("S->C", 0x0066).payload
        self.assertIsNone(result.length_error(2))
        self.assertIsNone(result.length_error(6))
        self.assertIsNotNone(result.length_error(4))
        self.assertIsNone(actors.length_error(52))
        self.assertIsNotNone(actors.length_error(27))

    def test_single_actor_and_nonempty_batch_boundaries(self):
        plaza_remove = find_spec("S->C", 0x0067).payload
        ox_remove = find_spec("S->C", 0x00CA).payload
        ox_remote = find_spec("S->C", 0x00C9).payload
        for rule in (plaza_remove, ox_remove):
            self.assertIsNone(rule.length_error(4))
            self.assertIsNotNone(rule.length_error(0))
            self.assertIsNotNone(rule.length_error(8))
        self.assertIsNotNone(ox_remote.length_error(0))
        self.assertIsNone(ox_remote.length_error(32))
        self.assertIsNone(ox_remote.length_error(64))
        self.assertIsNotNone(ox_remote.length_error(33))

    def test_ox_d1_is_explicit_forbidden_tombstone(self):
        spec = find_spec("S->C", 0x00D1, 2)
        self.assertEqual("fail_closed", spec.implementation)
        self.assertEqual("forbidden", spec.risk)
        self.assertIn("emit forbidden", spec.policy)

    def test_payload_rule_rejects_ambiguous_or_invalid_constraints(self):
        with self.assertRaises(TypeError):
            PayloadRule(exact=[1])
        with self.assertRaises(ValueError):
            PayloadRule(exact=(2, 1))
        with self.assertRaises(ValueError):
            PayloadRule(exact=(1,), min_length=1)
        with self.assertRaises(ValueError):
            PayloadRule(min_length=3, max_length=2)
        with self.assertRaises(ValueError):
            PayloadRule(multiple=0)

    def test_registry_and_specs_are_immutable(self):
        spec = PROTOCOL_SPECS[0]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            spec.label = "changed"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            spec.payload.min_length = 1
        with self.assertRaises(TypeError):
            PROTOCOL_BY_DIRECTION[("C->S", 0xFFFF)] = spec

    def test_spec_id_is_deterministic_order_independent_and_content_sensitive(self):
        self.assertRegex(REGISTRY_SPEC_ID, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(REGISTRY_SPEC_ID, compute_registry_spec_id(PROTOCOL_SPECS))
        self.assertEqual(REGISTRY_SPEC_ID, compute_registry_spec_id(reversed(PROTOCOL_SPECS)))
        changed = (dataclasses.replace(PROTOCOL_SPECS[0], label="changed"),) + PROTOCOL_SPECS[1:]
        self.assertNotEqual(REGISTRY_SPEC_ID, compute_registry_spec_id(changed))

    def test_typed_json_is_serializable_fresh_and_carries_spec_id(self):
        first = registry_json()
        second = registry_json()
        self.assertEqual("azrok.protocol.registry.v1", first["schema"])
        self.assertEqual(REGISTRY_SPEC_ID, first["spec_id"])
        self.assertEqual(METADATA_SPEC_ID, first["metadata_spec_id"])
        self.assertEqual(74, len(first["specs"]))
        self.assertEqual(23, len(first["native_symbols"]))
        self.assertIn('"spec_id": "sha256:', json.dumps(first))

        first["specs"][0]["label"] = "client-side mutation"
        self.assertNotEqual(first["specs"][0]["label"], second["specs"][0]["label"])
        self.assertEqual("login/connect request", PROTOCOL_SPECS[0].label)

    def test_recovered_native_symbols_are_separate_from_wire_links(self):
        self.assertRegex(METADATA_SPEC_ID, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(23, len(NATIVE_PROTOCOL_SYMBOLS))
        family_counts = {
            family: sum(symbol.family == family for symbol in NATIVE_PROTOCOL_SYMBOLS)
            for family in ("C2G", "G2C", "S2C")
        }
        self.assertEqual({"C2G": 9, "G2C": 7, "S2C": 7}, family_counts)
        plaza = next(
            symbol for symbol in NATIVE_PROTOCOL_SYMBOLS
            if symbol.name == "S2C_PLAZAENTER_ACK"
        )
        self.assertEqual("string_identifier", plaza.kind)
        links = {
            (link.direction, link.opcode, link.native_name): link
            for link in NATIVE_PROTOCOL_LINKS
        }
        self.assertEqual(
            "VERIFIED",
            links[("C->S", 0x0011, "C2G_UPDATEQUESTLIST_REQ")].status,
        )
        self.assertEqual("VERIFIED", links[("C->S", 0x0013, "C2G_SHOP_REQ")].status)
        self.assertNotIn(("C->S", 0x0012, "C2G_QUEST_REQ"), links)
        self.assertFalse(any(link.direction == "S->C" for link in NATIVE_PROTOCOL_LINKS))

    def test_native_frame_and_sender_metadata_do_not_invent_structure_links(self):
        self.assertEqual(
            ("payload_length:u16", "opcode:u16"),
            ORIGINAL_WIRE_FRAME["header_fields"],
        )
        self.assertEqual(4, ORIGINAL_WIRE_FRAME["header_size"])
        self.assertEqual(261, ORIGINAL_WIRE_FRAME["sender_payload_max"])
        senders = {row[0]: row for row in ORIGINAL_C2S_SENDERS}
        self.assertEqual("C2G_UPDATEQUESTLIST_REQ", senders[0x0011][3])
        self.assertEqual("C2G_SHOP_REQ", senders[0x0013][3])
        self.assertIsNone(senders[0x0012][3])
        self.assertIsNone(senders[0x0014][3])
        document = registry_json()
        self.assertEqual("payload_length + 4", document["native_wire_frame"]["total_length"])
        reward = next(row for row in document["native_c2s_senders"] if row["opcode"] == 0x0012)
        self.assertIsNone(reward["native_structure"])

    def test_legacy_projection_is_complete_and_uses_corrected_lengths(self):
        rows = legacy_contracts()
        self.assertEqual(74, len(rows))
        self.assertTrue(all(set(row) == {
            "dir", "opcode", "length", "status", "policy", "meaning"
        } for row in rows))
        by_key = {(row["dir"], row["opcode"]): row for row in rows}
        self.assertEqual("4", by_key[("C->S", "0x000D")]["length"])
        self.assertEqual("3", by_key[("C->S", "0x000E")]["length"])
        self.assertEqual(">=10", by_key[("C->S", "0x0065")]["length"])
        self.assertEqual("18..199", by_key[("C->S", "0x0068")]["length"])
        self.assertEqual("NOT VERIFIED", by_key[("C->S", "0x000B")]["status"])


if __name__ == "__main__":
    unittest.main()
