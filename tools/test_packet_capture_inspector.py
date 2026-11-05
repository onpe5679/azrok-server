import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from packet_capture_inspector import (
    CONTRACTS,
    _decode,
    filter_events,
    parse_capture,
    render_html,
    summarize,
)
from azrok_protocol_registry import find_spec


FIXTURE = """Azrok Plaza - Parsed Game Packets (LIVE)
Time: 2026-07-18 12:35:51
============================================================

[C->S] #4 opcode=0x0013 payload=45B total=49B entity=77 conn=raw-2
  0000: 2D 00 13 00 01 00 00 00 00 88 13 00 00 00 00 00  -...............
  0010: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
  0020: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
  0030: 00                                               .
  Payload only: 010000000088130000000000000000000000000000000000000000000000000000000000000000000000000000

[S->C] #4 opcode=0x0005 payload=6B total=10B
  0000: 06 00 05 00 00 13 E8 03 00 00                    ..........
  Payload only: 0013e8030000

[C->S] #9 opcode=0x000F payload=2B total=6B
  0000: 02 00 0F 00 00 01                                ......
  Payload only: 0001

[C->S] #10 opcode=0xBEEF payload=1B total=5B
  0000: 01 00 EF BE AA                                   .....
  Payload only: aa
"""


class CaptureInspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "packets_test.txt"
        self.path.write_text(FIXTURE, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_parse_decodes_purchase_and_metadata(self):
        events = parse_capture(self.path)
        self.assertEqual(4, len(events))
        purchase = events[0]
        self.assertEqual("shop purchase commit", purchase.label)
        self.assertEqual("currency/inventory-mutation", purchase.persistence)
        self.assertEqual("77", purchase.entity)
        self.assertEqual("raw-2", purchase.connection)
        self.assertEqual([5000], purchase.decoded["item_ids"])
        self.assertEqual(0, purchase.decoded["claimed_total"])
        self.assertFalse(purchase.malformed)
        self.assertEqual(1000, events[1].decoded["currency"])

    def test_contract_malformed_and_unknown_are_separate(self):
        events = parse_capture(self.path)
        self.assertIn("contract length 2B; expected 1B", events[2].malformed)
        self.assertFalse(events[2].unknown)
        self.assertTrue(events[3].unknown)
        self.assertFalse(events[3].malformed)

    def test_legacy_time_is_marked_approximate(self):
        event = parse_capture(self.path)[1]
        self.assertEqual("2026-07-18 12:35:51", event.timestamp)
        self.assertEqual("capture-start-approx", event.timestamp_kind)
        self.assertIsNone(event.entity)

    def test_persistence_filter_and_summary(self):
        args = Namespace(direction=None, opcode=None, category=None, entity=None,
                         connection=None, persistence=True, unknown_only=False,
                         malformed_only=False, min_len=None, max_len=None,
                         contains=None, limit=0)
        events = filter_events(parse_capture(self.path), args)
        self.assertEqual([0x0013, 0x0005, 0x000F], [event.opcode for event in events])
        summary = summarize(events, 1)
        self.assertEqual(3, summary["persistence_events"])
        self.assertEqual(1, summary["entity_metadata_available"])

    def test_html_is_searchable_and_escaped(self):
        events = parse_capture(self.path)
        report = render_html(events, summarize(events, 1))
        self.assertIn('id="q"', report)
        self.assertIn("shop purchase commit", report)
        self.assertIn("Legacy captures do not contain", report)
        self.assertIn("data-direction=\"C->S\"", report)

    def test_json_shape_remains_serializable(self):
        event = parse_capture(self.path)[0]
        encoded = json.dumps(event.as_dict())
        self.assertIn('"opcode": "0x0013"', encoded)
        self.assertIn('"payload": "01', encoded)

    def test_0018_is_accessory_only_with_verified_equip_clear_flag(self):
        contract = CONTRACTS[("C->S", 0x0018)]
        self.assertEqual("accessory equip/clear request", contract.label)
        self.assertEqual("accessory", contract.category)
        equip = _decode("C->S", 0x0018, bytes((0, 2, 3)))
        self.assertEqual("equip", equip["operation"])
        self.assertTrue(equip["b0_valid"])
        self.assertTrue(equip["value_valid_for_slot"])
        self.assertTrue(equip["value_valid_for_equip"])
        self.assertFalse(equip["requires_current_match"])
        decoded = _decode("C->S", 0x0018, bytes((1, 2, 3)))
        self.assertEqual("clear", decoded["operation"])
        self.assertEqual(2, decoded["slot"])
        self.assertEqual(3, decoded["value"])
        self.assertTrue(decoded["b0_valid"])
        self.assertTrue(decoded["value_valid_for_slot"])
        self.assertIsNone(decoded["value_valid_for_equip"])
        self.assertTrue(decoded["requires_current_match"])
        self.assertIn("not_verifiable_from_capture", decoded["current_match_status"])

    def test_000c_decodes_actor_apply_and_clear(self):
        contract = CONTRACTS[("S->C", 0x000C)]
        self.assertEqual((7,), contract.lengths)
        applied = _decode("S->C", 0x000C, (77).to_bytes(4, "little") + bytes((0, 2, 3)))
        self.assertEqual({"actor_id": 77, "clear_flag": 0, "operation": "apply",
                          "slot": 2, "value": 3, "effective_value": 3}, applied)
        cleared = _decode("S->C", 0x000C, (77).to_bytes(4, "little") + bytes((1, 2, 3)))
        self.assertEqual("clear", cleared["operation"])
        self.assertEqual(0xFF, cleared["effective_value"])

    def test_0007_decodes_four_accessory_slots_at_1d4(self):
        payload = bytearray(472)
        payload[0x1D4:0x1D8] = bytes((3, 0xFF, 2, 7))
        decoded = _decode("S->C", 0x0007, bytes(payload))
        self.assertEqual([3, 0xFF, 2, 7], decoded["accessory_slots"])
        self.assertEqual("0x1D4", decoded["accessory_offset"])

    def test_0066_decodes_name_accessories_and_pair_bytes_per_record(self):
        first = bytearray(0x1A)
        first[0] = 2
        first[1:5] = (77).to_bytes(4, "little")
        first[7:20] = b"Azrok\0".ljust(13, b"\0")
        first[0x14:0x18] = bytes((1, 2, 0xFF, 7))
        first[0x18:0x1A] = bytes((8, 9))
        second = bytearray(0x1A)
        second[1:5] = (88).to_bytes(4, "little")
        second[7:20] = b"Peer\0".ljust(13, b"\0")
        decoded = _decode("S->C", 0x0066, bytes(first + second))
        self.assertEqual("0x1A", decoded["record_stride"])
        self.assertEqual(2, len(decoded["records"]))
        self.assertEqual("Azrok", decoded["records"][0]["name"])
        self.assertEqual([1, 2, 0xFF, 7], decoded["records"][0]["accessory_slots"])
        self.assertEqual(
            (8, 9),
            (decoded["records"][0]["pair_left"], decoded["records"][0]["pair_right"]),
        )

    def test_registry_single_actor_and_nonempty_batch_lengths(self):
        for key in (("S->C", 0x0067), ("S->C", 0x00CA)):
            contract = CONTRACTS[key]
            self.assertIsNone(contract.length_error(4))
            self.assertIsNotNone(contract.length_error(8))
        ox_remote = CONTRACTS[("S->C", 0x00C9)]
        self.assertIsNotNone(ox_remote.length_error(0))
        self.assertIsNone(ox_remote.length_error(32))
        self.assertIsNone(ox_remote.length_error(64))

    def test_contract_projection_reuses_registry_and_corrected_boundaries(self):
        self.assertIs(CONTRACTS[("C->S", 0x000D)].spec, find_spec("C->S", 0x000D))
        cases = (
            (("C->S", 0x000D), 4, 8),
            (("C->S", 0x000E), 3, 8),
            (("C->S", 0x0065), 10, 9),
            (("C->S", 0x0068), 18, 17),
        )
        for key, valid, invalid in cases:
            self.assertIsNone(CONTRACTS[key].length_error(valid))
            self.assertIsNotNone(CONTRACTS[key].length_error(invalid))

    def test_direct_cli_help_keeps_root_registry_importable(self):
        script = Path(__file__).with_name("packet_capture_inspector.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--help"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("--malformed-only", completed.stdout)

    def test_chat_decoder_enforces_internal_length_and_nuls(self):
        valid = bytes((0, 0)) + b"target\0".ljust(13, b"\0") + b"\0" + bytes((3,)) + b"hi\0"
        decoded = _decode("C->S", 0x0068, valid)
        self.assertEqual("target", decoded["target"])
        self.assertEqual("hi", decoded["message"])
        for invalid in (
            valid[:0x10] + bytes((4,)) + valid[0x11:],
            valid[:0x0F] + b"X" + valid[0x10:],
            valid[:-1] + b"X",
        ):
            self.assertTrue(_decode("C->S", 0x0068, invalid)["decode_error"])


if __name__ == "__main__":
    unittest.main()
