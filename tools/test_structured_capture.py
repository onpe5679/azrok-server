import hashlib
import json
import os
import sys
import tempfile
import threading
import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azrok_capture import StructuredPacketCapture, _process_is_alive, choose_capture_root


class StructuredPacketCaptureTests(unittest.TestCase):
    def test_process_liveness_probe_handles_live_and_missing_pid(self):
        self.assertTrue(_process_is_alive(os.getpid()))
        self.assertFalse(_process_is_alive(2_147_483_647))

    def test_explicit_capture_root_wins_without_other_drive_probe(self):
        with tempfile.TemporaryDirectory() as tempdir:
            with mock.patch.dict(os.environ, {"AZROK_CAPTURE_DIR": tempdir}, clear=False):
                self.assertEqual(choose_capture_root(ROOT), Path(tempdir).resolve())

    def test_parallel_appends_have_unique_monotonic_capture_sequence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            capture = StructuredPacketCapture(ROOT, root_dir=tempdir, min_free_bytes=0)

            def write(index):
                capture.append(
                    direction="C->S",
                    packet_number=index % 3,
                    opcode=0x0066,
                    payload=bytes((index,)),
                    raw=b"frame" + bytes((index,)),
                    origin="test",
                    semantics={
                        "meaning": "movement report",
                        "category": "multiplayer",
                        "risk": "known",
                        "protocol_spec_id": "test-spec",
                        "decoded": {"index": index},
                    },
                    entity_id=9,
                    connection={"entity_id": 9, "room_kind": 12, "room_name": "Plaza"},
                )

            threads = [threading.Thread(target=write, args=(index,)) for index in range(24)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            capture.close()

            rows = [json.loads(line) for line in capture.packet_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["capture_seq"] for row in rows], list(range(1, 25)))
            self.assertEqual({row["protocol_spec_id"] for row in rows}, {"test-spec"})
            self.assertTrue(all(row["entity_id"] == 9 for row in rows))
            self.assertTrue(all(row["payload_storage"] == "hex" for row in rows))
            manifest = json.loads(capture.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "closed")
            self.assertEqual(manifest["health"]["packets_written"], 24)

    def test_sensitive_chat_keeps_hashes_but_not_payload_or_decoded_text(self):
        with tempfile.TemporaryDirectory() as tempdir:
            capture = StructuredPacketCapture(ROOT, root_dir=tempdir, min_free_bytes=0)
            secret = "비밀 대화".encode("cp949")
            raw = b"header" + secret
            self.assertTrue(
                capture.append(
                    direction="C->S",
                    packet_number=4,
                    opcode=0x0068,
                    payload=secret,
                    raw=raw,
                    origin="auto",
                    semantics={
                        "meaning": "chat transmit",
                        "category": "community",
                        "risk": "known",
                        "protocol_spec_id": "chat-spec",
                        "decoded": {"message": "비밀 대화", "target": "Player"},
                    },
                )
            )
            capture.close()
            row = json.loads(capture.packet_path.read_text(encoding="utf-8"))
            self.assertEqual(row["payload_storage"], "redacted_hash_only")
            self.assertIsNone(row["payload_hex"])
            self.assertNotIn("decoded", row["semantics"])
            self.assertEqual(row["payload_sha256"], hashlib.sha256(secret).hexdigest())
            self.assertEqual(row["raw_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertNotIn("비밀", capture.packet_path.read_text(encoding="utf-8"))
            self.assertTrue(StructuredPacketCapture.is_sensitive("C->S", 0x0064))

    def test_manifest_counters_are_durable_before_close(self):
        with tempfile.TemporaryDirectory() as tempdir:
            capture = StructuredPacketCapture(ROOT, root_dir=tempdir, min_free_bytes=0)
            self.assertTrue(
                capture.append(
                    direction="C->S",
                    packet_number=1,
                    opcode=0x0016,
                    payload=b"\x00",
                    raw=b"frame",
                    origin="test",
                )
            )
            manifest = json.loads(capture.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "healthy")
            self.assertEqual(manifest["health"]["capture_seq"], 1)
            self.assertEqual(manifest["health"]["packets_written"], 1)
            self.assertIsNotNone(manifest["health"]["last_write_utc"])
            capture.close()

    def test_new_run_reconciles_dead_writer_manifest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            runs = Path(tempdir) / "runs"
            prior = runs / "prior"
            prior.mkdir(parents=True)
            manifest_path = prior / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema": "azrok.capture.run.v1",
                        "run_id": "prior",
                        "writer_pid": 2_147_483_647,
                        "started_utc": "2026-07-18T00:00:00.000Z",
                        "ended_utc": None,
                        "status": "healthy",
                        "health": {"capture_seq": 7, "packets_written": 7},
                    }
                ),
                encoding="utf-8",
            )
            capture = StructuredPacketCapture(ROOT, root_dir=tempdir, min_free_bytes=0)
            reconciled = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(reconciled["status"], "unclean_shutdown")
            self.assertIsNotNone(reconciled["recovered_utc"])
            self.assertIsNone(reconciled["ended_utc"])
            self.assertEqual(reconciled["health"]["packets_written"], 7)
            self.assertIn("without close", reconciled["health"]["last_error"])
            capture.close()

    def test_free_space_guard_drops_packet_and_reports_health(self):
        Usage = namedtuple("Usage", "total used free")
        with tempfile.TemporaryDirectory() as tempdir:
            capture = StructuredPacketCapture(ROOT, root_dir=tempdir, min_free_bytes=0)
            capture.minimum_free_bytes = 1
            with mock.patch("azrok_capture.shutil.disk_usage", return_value=Usage(100, 100, 0)):
                written = capture.append(
                    direction="C->S",
                    packet_number=1,
                    opcode=0x0016,
                    payload=b"\x00",
                    raw=b"frame",
                    origin="test",
                )
                health = capture.snapshot()
            self.assertFalse(written)
            self.assertEqual(health["status"], "paused_low_space")
            self.assertFalse(health["writable"])
            self.assertEqual(health["dropped_low_space"], 1)
            self.assertEqual(health["capture_seq"], 0)
            capture.close()

    def test_server_keeps_legacy_text_and_exposes_structured_health(self):
        from azrok_server import AzrokServer

        with tempfile.TemporaryDirectory() as tempdir:
            structured_root = Path(tempdir) / "machine-readable"
            with mock.patch.dict(
                os.environ, {"AZROK_CAPTURE_DIR": str(structured_root)}, clear=False
            ):
                server = AzrokServer(0, log_dir=tempdir)
                payload = b"account-and-password".ljust(106, b"\x00")
                raw = b"wire-header" + payload
                server._log_packet("C->S", 1, 0x0000, payload, raw, conn=None)
                state = server.snapshot()
                structured_path = Path(
                    state["server"]["structured_capture"]["packet_path"]
                )
                legacy_path = Path(server.capture_path)
                server.stop()

            row = json.loads(structured_path.read_text(encoding="utf-8"))
            self.assertEqual(row["payload_storage"], "redacted_hash_only")
            self.assertIsNone(row["payload_hex"])
            self.assertIn("6163636f756e74", legacy_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["server"]["structured_capture"]["status"], "healthy"
            )


if __name__ == "__main__":
    unittest.main()
