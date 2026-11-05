"""Durable, privacy-aware packet captures for preservation analysis.

The legacy human-readable packet logs remain owned by ``azrok_server``.  This
module adds a machine-readable run directory whose JSONL records are ordered
by a capture-local sequence and made durable before ``append`` returns.
"""

from __future__ import annotations

import datetime as _datetime
import hashlib
import json
import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from azrok_protocol_registry import REGISTRY_SPEC_ID


CAPTURE_SCHEMA = "azrok.packet.capture.v1"
MANIFEST_SCHEMA = "azrok.capture.run.v1"
DEFAULT_MIN_FREE_BYTES = 1024 * 1024 * 1024

# These records can contain credentials, chat, or player-provided identity.
# Their hashes and decoded non-content semantics remain useful without keeping
# the original payload in the structured capture.  The legacy text capture is
# intentionally unchanged for backwards compatibility and must be protected
# as an operator artifact.
_SENSITIVE_PACKET_KEYS = frozenset(
    {
        ("C->S", 0x0000),  # account/password login request
        ("C->S", 0x0004),  # character name/create request
        ("C->S", 0x0064),  # Plaza bootstrap carries the self name
        ("C->S", 0x0068),  # Plaza chat
        ("S->C", 0x0000),  # roster contains character names
        ("S->C", 0x0007),  # restore blob contains identity fields
        ("S->C", 0x0066),  # actor roster records contain names
        ("S->C", 0x006A),  # chat/system text
    }
)


def _parse_non_negative_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value, 0)
    except ValueError:
        return default
    return max(0, parsed)


def choose_capture_root(workspace_dir: str | os.PathLike[str]) -> Path:
    """Choose an explicit root, then B:, then a portable workspace fallback.

    No other drive is probed.  In particular this function never checks D:.
    """

    explicit = os.environ.get("AZROK_CAPTURE_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    b_root = Path("B:/")
    if b_root.is_dir():
        return b_root / "Azrok_Captures"
    return Path(workspace_dir).resolve() / "captures_structured"


def _utc_now() -> str:
    return _datetime.datetime.now(_datetime.timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def _process_is_alive(pid: object) -> bool:
    try:
        numeric_pid = int(pid)
        if numeric_pid <= 0:
            return False
        if os.name == "nt":
            # CPython's os.kill(pid, 0) is not a reliable existence probe on
            # Windows: for a valid process it can raise WinError 87 and, on
            # some builds, surface that as SystemError.  That made a second
            # live capture mark the first writer as orphaned or abort startup.
            # A query-only handle is both non-mutating and authoritative.
            import ctypes

            process_query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [
                ctypes.c_uint32,
                ctypes.c_int,
                ctypes.c_uint32,
            ]
            kernel32.OpenProcess.restype = ctypes.c_void_p
            kernel32.GetExitCodeProcess.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32),
            ]
            kernel32.GetExitCodeProcess.restype = ctypes.c_int
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle.restype = ctypes.c_int
            handle = kernel32.OpenProcess(
                process_query_limited_information, 0, numeric_pid
            )
            if not handle:
                # Access denied still proves that the PID currently exists.
                return ctypes.get_last_error() == 5
            try:
                exit_code = ctypes.c_uint32(0)
                return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) \
                    and exit_code.value == still_active
            finally:
                kernel32.CloseHandle(handle)
        os.kill(numeric_pid, 0)
        return True
    except (OSError, SystemError, TypeError, ValueError):
        return False


def _reconcile_unclean_runs(root_dir: Path) -> None:
    """Mark orphaned manifests without inventing a graceful end time."""

    runs_dir = root_dir / "runs"
    if not runs_dir.is_dir():
        return
    for manifest_path in runs_dir.glob("*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("ended_utc") is not None:
                continue
            if manifest.get("status") in {"closed", "unclean_shutdown"}:
                continue
            writer_pid = manifest.get("writer_pid")
            if writer_pid is not None and _process_is_alive(writer_pid):
                continue
            manifest["status"] = "unclean_shutdown"
            manifest["recovered_utc"] = _utc_now()
            health = manifest.setdefault("health", {})
            health["last_error"] = "Previous capture writer exited without close()"
            temporary = manifest_path.with_suffix(".json.recovery.tmp")
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(manifest, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, manifest_path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            # A damaged prior artifact must not block a new preservation run.
            continue


class StructuredPacketCapture:
    """One append-only JSONL packet stream plus a small run manifest."""

    def __init__(
        self,
        workspace_dir: str | os.PathLike[str],
        *,
        root_dir: str | os.PathLike[str] | None = None,
        min_free_bytes: int | None = None,
        clock=time.time,
    ) -> None:
        self._clock = clock
        self._lock = threading.RLock()
        self.capture_seq = 0
        self.packets_written = 0
        self.redacted_packets = 0
        self.dropped_low_space = 0
        self.last_error: str | None = None
        self.last_write_utc: str | None = None
        self.free_bytes: int | None = None
        self.status = "initializing"
        self.closed = False
        self.started_utc = _utc_now()
        self.ended_utc: str | None = None
        self.minimum_free_bytes = (
            _parse_non_negative_int(
                os.environ.get("AZROK_CAPTURE_MIN_FREE_BYTES"),
                DEFAULT_MIN_FREE_BYTES,
            )
            if min_free_bytes is None
            else max(0, int(min_free_bytes))
        )
        self.root_dir = Path(root_dir).resolve() if root_dir else choose_capture_root(workspace_dir)
        _reconcile_unclean_runs(self.root_dir)
        stamp = _datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        self.run_id = f"{stamp}_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        self.run_dir = self.root_dir / "runs" / self.run_id
        self.packet_path = self.run_dir / "packets.jsonl"
        self.manifest_path = self.run_dir / "manifest.json"
        self._file = None

        try:
            self.run_dir.mkdir(parents=True, exist_ok=False)
            self._refresh_free_space()
            if self.free_bytes is not None and self.free_bytes < self.minimum_free_bytes:
                self.status = "paused_low_space"
            else:
                self._file = self.packet_path.open("a", encoding="utf-8", newline="\n")
                self.status = "healthy"
            self._write_manifest()
        except OSError as exc:
            self.status = "failed"
            self.last_error = f"{type(exc).__name__}: {exc}"

    @staticmethod
    def is_sensitive(direction: str, opcode: int) -> bool:
        return (str(direction), int(opcode)) in _SENSITIVE_PACKET_KEYS

    def _refresh_free_space(self) -> None:
        target = self.run_dir if self.run_dir.exists() else self.root_dir
        self.free_bytes = int(shutil.disk_usage(target).free)

    def _manifest(self) -> dict[str, Any]:
        return {
            "schema": MANIFEST_SCHEMA,
            "run_id": self.run_id,
            "writer_pid": os.getpid(),
            "started_utc": self.started_utc,
            "ended_utc": self.ended_utc,
            "status": self.status,
            "registry_spec_id": REGISTRY_SPEC_ID,
            "packet_capture": self.packet_path.name,
            "privacy": {
                "sensitive_payload_policy": "hash_only",
                "sensitive_packet_keys": [
                    {"direction": direction, "opcode": f"0x{opcode:04X}"}
                    for direction, opcode in sorted(_SENSITIVE_PACKET_KEYS)
                ],
            },
            "health": {
                "capture_seq": self.capture_seq,
                "packets_written": self.packets_written,
                "redacted_packets": self.redacted_packets,
                "dropped_low_space": self.dropped_low_space,
                "minimum_free_bytes": self.minimum_free_bytes,
                "free_bytes": self.free_bytes,
                "last_write_utc": self.last_write_utc,
                "last_error": self.last_error,
            },
        }

    def _write_manifest(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.manifest_path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(self._manifest(), handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.manifest_path)

    def _ensure_file_after_space_recovery(self) -> bool:
        self._refresh_free_space()
        if self.free_bytes is not None and self.free_bytes < self.minimum_free_bytes:
            self.status = "paused_low_space"
            self.dropped_low_space += 1
            return False
        if self._file is None:
            self._file = self.packet_path.open("a", encoding="utf-8", newline="\n")
        self.status = "healthy"
        self.last_error = None
        return True

    def append(
        self,
        *,
        direction: str,
        packet_number: int,
        opcode: int,
        payload: bytes,
        raw: bytes,
        origin: str,
        semantics: Mapping[str, Any] | None = None,
        entity_id: int | None = None,
        connection: Mapping[str, Any] | None = None,
    ) -> bool:
        """Durably append one record; failures are contained and observable."""

        payload = bytes(payload)
        raw = bytes(raw)
        semantics = dict(semantics or {})
        with self._lock:
            if self.closed:
                return False
            try:
                if not self._ensure_file_after_space_recovery():
                    try:
                        self._write_manifest()
                    except OSError as exc:
                        self.last_error = f"{type(exc).__name__}: {exc}"
                    return False
                self.capture_seq += 1
                redacted = self.is_sensitive(direction, opcode)
                record: dict[str, Any] = {
                    "schema": CAPTURE_SCHEMA,
                    "capture_seq": self.capture_seq,
                    "timestamp_utc": _utc_now(),
                    "timestamp_unix_ns": time.time_ns(),
                    "direction": str(direction),
                    "packet_number": int(packet_number),
                    "opcode": f"0x{int(opcode):04X}",
                    "opcode_int": int(opcode),
                    "origin": str(origin),
                    "payload_length": len(payload),
                    "raw_length": len(raw),
                    "payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    "payload_storage": "redacted_hash_only" if redacted else "hex",
                    "payload_hex": None if redacted else payload.hex(),
                    "registry_spec_id": REGISTRY_SPEC_ID,
                    "protocol_spec_id": semantics.get("protocol_spec_id"),
                    "semantics": {
                        key: semantics.get(key)
                        for key in (
                            "meaning", "category", "risk", "contract_length",
                            "contract_length_error",
                        )
                        if key in semantics
                    },
                    "entity_id": entity_id,
                }
                if not redacted and "decoded" in semantics:
                    record["semantics"]["decoded"] = semantics.get("decoded")
                if connection:
                    record["connection"] = {
                        key: connection[key]
                        for key in ("entity_id", "room_kind", "room_name")
                        if key in connection
                    }
                line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                self._file.write(line + "\n")
                self._file.flush()
                os.fsync(self._file.fileno())
                self.packets_written += 1
                if redacted:
                    self.redacted_packets += 1
                self.last_write_utc = record["timestamp_utc"]
                try:
                    self._write_manifest()
                except OSError as exc:
                    # The packet itself is already fsync'd and therefore was
                    # captured successfully.  Expose manifest lag as degraded
                    # health without misreporting the packet append as failed.
                    self.status = "degraded"
                    self.last_error = f"{type(exc).__name__}: {exc}"
                return True
            except (OSError, TypeError, ValueError) as exc:
                self.status = "failed"
                self.last_error = f"{type(exc).__name__}: {exc}"
                return False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            try:
                self._refresh_free_space()
            except OSError as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
                if self.status == "healthy":
                    self.status = "degraded"
            return {
                "schema": CAPTURE_SCHEMA,
                "status": self.status,
                "writable": self.status == "healthy" and not self.closed,
                "run_id": self.run_id,
                "root_dir": str(self.root_dir),
                "run_dir": str(self.run_dir),
                "packet_path": str(self.packet_path),
                "manifest_path": str(self.manifest_path),
                "capture_seq": self.capture_seq,
                "packets_written": self.packets_written,
                "redacted_packets": self.redacted_packets,
                "dropped_low_space": self.dropped_low_space,
                "minimum_free_bytes": self.minimum_free_bytes,
                "free_bytes": self.free_bytes,
                "last_write_utc": self.last_write_utc,
                "last_error": self.last_error,
                "privacy_policy": "sensitive payload hash only",
            }

    def close(self) -> None:
        with self._lock:
            if self.closed:
                return
            self.closed = True
            self.ended_utc = _utc_now()
            try:
                if self._file is not None:
                    self._file.flush()
                    os.fsync(self._file.fileno())
                    self._file.close()
                    self._file = None
                if self.status == "healthy":
                    self.status = "closed"
                self._write_manifest()
            except OSError as exc:
                self.status = "failed"
                self.last_error = f"{type(exc).__name__}: {exc}"


__all__ = [
    "CAPTURE_SCHEMA",
    "MANIFEST_SCHEMA",
    "StructuredPacketCapture",
    "choose_capture_root",
]
