import json
import tempfile
import unittest
from pathlib import Path

from tools.wmb6_minimap import build_outputs, parse_wmb6


ROOT = Path(__file__).resolve().parents[1]
ROOM_WMB = ROOT / "Data" / "Space" / "PatHouse" / "room.wmb"


class Wmb6MinimapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parsed = parse_wmb6(ROOM_WMB)
        cls.by_name = {
            record.name: record
            for record in cls.parsed["records"]
            if record.name
        }

    def test_pathouse_directory_and_bounds(self):
        self.assertEqual(self.parsed["format"], "WMB6")
        self.assertEqual(self.parsed["record_count"], 87)
        self.assertEqual(self.parsed["entity_directory_offset"], 0x6CED44)
        self.assertEqual(self.parsed["world_bounds"]["min_x"], -3362.0)
        self.assertEqual(self.parsed["world_bounds"]["max_y"], 3684.0)

    def test_bathroom_door_is_not_the_outside_exit(self):
        door = self.by_name["dm_door_0003_057"]
        self.assertEqual(door.resource, "dm_door_0003.MDL")
        self.assertAlmostEqual(door.x, -813.0)
        self.assertAlmostEqual(door.y, -107.0)
        self.assertAlmostEqual(door.z, 6.70908, places=4)
        self.assertEqual(door.runtime_type, 0x24)
        self.assertEqual(door.runtime_action, 0x26)
        self.assertEqual(door.category, "bathroom_internal_door")
        self.assertIn("not", door.navigation_note.lower())

    def test_outside_gate_frame_and_mirror_are_distinct(self):
        gate = self.by_name["gate_mun_MDL_048"]
        frame = self.by_name["doorframe_01"]
        mirror = self.by_name["mirror_01"]
        self.assertEqual(gate.resource, "gate_mun.MDL")
        self.assertEqual((gate.x, gate.y, gate.z), (522.0, 801.0, 126.0))
        self.assertEqual(gate.byte_size, 0x84)
        self.assertEqual(gate.category, "outside_exit_gate")
        self.assertIn("NOT VERIFIED", gate.runtime_evidence)
        self.assertEqual((frame.x, frame.y), (526.0, 802.0))
        self.assertAlmostEqual(frame.z, -0.38793, places=4)
        self.assertEqual(frame.runtime_type, 0x1F)
        self.assertEqual(frame.category, "outside_exit_frame")
        self.assertEqual((mirror.x, mirror.y), (-336.0, 1152.0))
        self.assertEqual(mirror.category, "wardrobe_mirror")
        self.assertIn("NOT VERIFIED", mirror.runtime_evidence)

    def test_outputs_contain_no_embedded_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            outputs = build_outputs(ROOM_WMB, Path(temp), None)
            self.assertEqual(set(outputs), {"json", "csv", "svg"})
            for path in outputs.values():
                self.assertTrue(path.is_file())
            value = json.loads(outputs["json"].read_text(encoding="utf-8"))
            self.assertEqual(value["record_count"], 87)
            svg = outputs["svg"].read_text(encoding="utf-8")
            self.assertIn("dm_door_0003_057", svg)
            self.assertIn("gate_mun_MDL_048", svg)
            self.assertNotIn("data:image", svg)

    def test_player_and_camera_overlay(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            overlay = temp_path / "overlay.json"
            overlay.write_text(
                json.dumps(
                    {
                        "player": {"x": -500, "y": 100, "z": 5},
                        "camera": {"x": -300, "y": 300, "z": 200},
                    }
                ),
                encoding="utf-8",
            )
            outputs = build_outputs(ROOM_WMB, temp_path / "out", overlay)
            svg = outputs["svg"].read_text(encoding="utf-8")
            self.assertIn("PLAYER", svg)
            self.assertIn("CAMERA", svg)


if __name__ == "__main__":
    unittest.main()
