#!/usr/bin/env python3
"""Read-only search and reporting for Azrok Plaza text packet captures.

This tool never connects to the game server and never writes character state.  Its
only optional write is the report selected by ``--output``.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import glob
import html
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator, Sequence

# Keep the documented direct CLI form (`python tools/packet_capture_inspector.py`)
# working while the authoritative registry lives at the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azrok_protocol_registry import PROTOCOL_SPECS, ProtocolSpec


HEADER_RE = re.compile(
    r"^\[(?P<direction>C->S|S->C)\]\s+#(?P<seq>\d+)\s+"
    r"opcode=0x(?P<opcode>[0-9A-Fa-f]{4})\s+"
    r"payload=(?P<payload>\d+)B\s+total=(?P<total>\d+)B"
    r"(?P<suffix>.*)$"
)
HEX_RE = re.compile(r"^\s{2}[0-9A-Fa-f]{4}:\s+((?:[0-9A-Fa-f]{2}(?:\s+|$)){1,16})")
CAPTURE_TIME_RE = re.compile(r"^Time:\s+(.+?)\s*$")
META_RE = re.compile(r"\b(?P<key>t|time|timestamp|entity|entity_id|conn|connection)=(?P<value>[^\s\]]+)")
ORIGIN_RE = re.compile(r"\[(?P<origin>relay|ox|manual|macro|auto)\]")


@dataclasses.dataclass(frozen=True)
class Contract:
    """Compatibility view backed by the shared immutable registry."""

    spec: ProtocolSpec

    @property
    def label(self) -> str:
        return self.spec.label

    @property
    def category(self) -> str:
        return self.spec.category

    @property
    def lengths(self) -> tuple[int, ...] | None:
        return self.spec.payload.exact or None

    @property
    def multiple(self) -> int | None:
        return self.spec.payload.multiple

    @property
    def min_length(self) -> int | None:
        return self.spec.payload.min_length

    @property
    def persistence(self) -> str | None:
        return self.spec.persistence

    def length_error(self, size: int) -> str | None:
        return self.spec.payload.length_error(size)


CONTRACTS: dict[tuple[str, int], Contract] = {
    (spec.direction, spec.opcode): Contract(spec) for spec in PROTOCOL_SPECS
}


@dataclasses.dataclass
class PacketEvent:
    source: str
    line: int
    capture_time: str | None
    timestamp: str | None
    timestamp_kind: str
    direction: str
    seq: int
    opcode: int
    payload_len: int
    total_len: int
    origin: str
    entity: str | None
    connection: str | None
    payload: bytes
    label: str
    category: str
    persistence: str | None
    unknown: bool
    malformed: tuple[str, ...]
    decoded: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        value = dataclasses.asdict(self)
        value["opcode"] = f"0x{self.opcode:04X}"
        value["payload"] = self.payload.hex()
        value["malformed"] = list(self.malformed)
        return value


def _decode(event_direction: str, opcode: int, payload: bytes) -> dict[str, object]:
    try:
        if event_direction == "C->S" and opcode == 0x0005 and payload:
            return {"slot": payload[0]}
        if event_direction == "C->S" and opcode == 0x0006 and payload:
            return {"slot": payload[0]}
        if event_direction == "C->S" and opcode == 0x000F and payload:
            return {"energy_slot": payload[0], "item_id": 5000 + payload[0]}
        if event_direction == "C->S" and opcode == 0x0013 and len(payload) == 45:
            count, claimed_total = struct.unpack_from("<BI", payload, 0)
            item_ids = list(struct.unpack_from("<10I", payload, 5))
            return {"item_count": count, "claimed_total": claimed_total,
                    "item_ids": item_ids[:count]}
        if event_direction == "C->S" and opcode == 0x0017 and len(payload) == 6:
            kind, stat_id, value = struct.unpack("<BBI", payload)
            return {"kind": kind, "stat_id": stat_id, "value": value}
        if event_direction == "C->S" and opcode == 0x0018 and len(payload) == 3:
            b0, slot, value = payload
            slot_maxima = (9, 6, 3, 7)
            value_valid_for_slot = slot < 4 and value <= slot_maxima[slot]
            return {
                "b0": b0,
                "operation": "equip" if b0 == 0 else "clear" if b0 == 1 else "invalid",
                "slot": slot,
                "value": value,
                "b0_valid": b0 in (0, 1),
                "slot_valid": slot < 4,
                "value_valid_for_slot": value_valid_for_slot,
                # Compatibility field: a clear is not an equip validation failure.
                "value_valid_for_equip": value_valid_for_slot if b0 == 0 else None,
                "requires_current_match": b0 == 1,
                "current_match_status": (
                    "not_verifiable_from_capture; compare canonical current slot value"
                    if b0 == 1 else "not_applicable"
                ),
            }
        if event_direction == "C->S" and opcode == 0x0065 and len(payload) == 10:
            room, heading, x, y = struct.unpack("<BBii", payload)
            return {"room_kind": room, "heading": heading, "x": x, "y": y}
        if event_direction == "C->S" and opcode == 0x0066 and len(payload) == 22:
            cell, x0, y0, x1, y1, duration, flag = struct.unpack("<BiiiiiB", payload)
            return {"cell": cell, "from": [x0, y0], "to": [x1, y1],
                    "duration": duration, "path_flag": flag}
        if event_direction == "C->S" and opcode == 0x0067 and len(payload) == 15:
            cell, x, y, action, angle = struct.unpack("<BiiIH", payload)
            return {"cell": cell, "x": x, "y": y, "action": action, "angle": angle}
        if event_direction == "C->S" and opcode == 0x0068:
            if not 18 <= len(payload) <= 199:
                return {"decode_error": True, "validation_error": "chat payload must be 18..199B"}
            message_length = payload[0x10]
            if payload[0x0F] != 0:
                return {"decode_error": True, "validation_error": "chat target[13] must be NUL-terminated"}
            if message_length < 1 or len(payload) != 0x11 + message_length:
                return {"decode_error": True, "validation_error": "chat message length byte mismatch"}
            if payload[-1] != 0:
                return {"decode_error": True, "validation_error": "chat message must be NUL-terminated"}
            kind, flag = payload[0], payload[1]
            target = payload[2:0x0F].split(b"\0", 1)[0].decode("cp949", errors="replace")
            message = payload[0x11:-1].decode("cp949", errors="replace")
            return {"chat_type": kind, "flag": flag, "target": target,
                    "message_length": message_length, "message": message}
        if event_direction == "C->S" and opcode == 0x00C9 and len(payload) == 1:
            return {"level_marker": payload[0]}
        if event_direction == "C->S" and opcode == 0x00CA and len(payload) == 22:
            side, x0, y0, x1, y1, timing, timeout = struct.unpack("<BiiiiiB", payload)
            return {"side": side, "from": [x0, y0], "to": [x1, y1],
                    "timing": timing, "timeout": timeout}
        if event_direction == "S->C" and opcode == 0x0009 and len(payload) == 2:
            return {"result": payload[0], "request_opcode": f"0x{payload[1]:04X}"}
        if event_direction == "S->C" and opcode == 0x0001 and len(payload) == 1:
            return {"result": payload[0]}
        if event_direction == "S->C" and opcode == 0x0005 and len(payload) >= 2:
            decoded: dict[str, object] = {
                "result": payload[0], "request_opcode": f"0x{payload[1]:04X}"
            }
            if len(payload) >= 6:
                funcorn = struct.unpack_from("<I", payload, 2)[0]
                decoded["currency"] = funcorn
                decoded["funcorn"] = funcorn
                decoded["ack"] = (
                    "G2C_FUNCORN_ACK" if payload[1] == 0x12 else
                    "shop_result" if payload[1] == 0x13 else
                    "post_load_state"
                )
            return decoded
        if event_direction == "S->C" and opcode == 0x0008 and len(payload) >= 2:
            return {"slot": payload[0], "result": payload[1]}
        if event_direction == "S->C" and opcode == 0x000C and len(payload) == 7:
            actor_id, clear_flag, slot, value = struct.unpack("<IBBB", payload)
            return {
                "actor_id": actor_id,
                "clear_flag": clear_flag,
                "operation": "apply" if clear_flag == 0 else "clear",
                "slot": slot,
                "value": value,
                "effective_value": value if clear_flag == 0 else 0xFF,
            }
        if event_direction == "S->C" and opcode == 0x0007 and len(payload) == 472:
            return {
                "accessory_slots": list(payload[0x1D4:0x1D8]),
                "accessory_offset": "0x1D4",
            }
        if event_direction == "S->C" and opcode == 0x0066 and len(payload) % 0x1A == 0:
            records = []
            for offset in range(0, len(payload), 0x1A):
                record = payload[offset:offset + 0x1A]
                name_raw = record[7:20].split(b"\0", 1)[0]
                records.append({
                    "kind": record[0],
                    "actor_id": struct.unpack_from("<I", record, 1)[0],
                    "name": name_raw.decode("cp949", errors="replace"),
                    "accessory_slots": list(record[0x14:0x18]),
                    "pair_left": record[0x18],
                    "pair_right": record[0x19],
                })
            return {"record_stride": "0x1A", "records": records}
        if event_direction == "S->C" and opcode == 0x0067 and len(payload) == 4:
            return {"actor_id": struct.unpack("<I", payload)[0]}
        if event_direction == "S->C" and opcode == 0x00C8 and len(payload) == 14:
            result, marker, ready_ms, x, y = struct.unpack("<BBIii", payload)
            return {"result": result, "level_marker": marker, "ready_ms": ready_ms,
                    "x": x, "y": y}
        if event_direction == "S->C" and opcode == 0x00C9 and len(payload) % 32 == 0:
            return {"record_stride": 32, "record_count": len(payload) // 32}
        if event_direction == "S->C" and opcode == 0x00CA and len(payload) == 4:
            return {"actor_id": struct.unpack("<I", payload)[0]}
        if event_direction == "S->C" and opcode in (0x00CB, 0x00CD):
            return {"actor_ids": list(struct.unpack(f"<{len(payload)//4}I", payload))}
        if event_direction == "S->C" and opcode == 0x00CE and len(payload) == 131:
            return {"question": payload[:128].split(b"\0", 1)[0].decode("cp949", errors="replace"),
                    "question_type": payload[128], "correct_side": payload[129],
                    "stars": payload[130]}
        if event_direction == "S->C" and opcode == 0x00D3 and len(payload) == 4:
            return dict(zip(("first", "second"), struct.unpack("<HH", payload)))
    except (IndexError, struct.error, UnicodeError, ValueError):
        return {"decode_error": True}
    return {}


def parse_capture(path: Path) -> list[PacketEvent]:
    """Parse one legacy capture, retaining explicit evidence gaps."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    capture_time = None
    for line in lines[:12]:
        match = CAPTURE_TIME_RE.match(line)
        if match:
            capture_time = match.group(1)
            break

    events: list[PacketEvent] = []
    index = 0
    while index < len(lines):
        match = HEADER_RE.match(lines[index])
        if not match:
            index += 1
            continue
        start = index
        index += 1
        body: list[str] = []
        while index < len(lines) and not HEADER_RE.match(lines[index]):
            body.append(lines[index])
            index += 1

        direction = match.group("direction")
        opcode = int(match.group("opcode"), 16)
        payload_len = int(match.group("payload"))
        total_len = int(match.group("total"))
        suffix = match.group("suffix")
        metadata = {m.group("key"): m.group("value") for m in META_RE.finditer(suffix)}
        origin_match = ORIGIN_RE.search(suffix)
        origin = origin_match.group("origin") if origin_match else "auto"

        raw = bytearray()
        payload_hex = None
        for line in body:
            if line.lstrip().startswith("Payload only:"):
                payload_hex = line.split(":", 1)[1].strip()
            hex_match = HEX_RE.match(line)
            if hex_match:
                raw.extend(bytes.fromhex(hex_match.group(1)))
        errors: list[str] = []
        if payload_hex is not None:
            try:
                payload = bytes.fromhex(payload_hex)
            except ValueError:
                payload = b""
                errors.append("invalid payload hex")
        elif len(raw) >= 4:
            payload = bytes(raw[4:])
        else:
            payload = b""

        if total_len != payload_len + 4:
            errors.append(f"header total {total_len}B != payload+4")
        if len(raw) != total_len:
            errors.append(f"hexdump {len(raw)}B != header total {total_len}B")
        if len(payload) != payload_len:
            errors.append(f"decoded payload {len(payload)}B != header {payload_len}B")
        if len(raw) >= 4:
            wire_len, wire_opcode = struct.unpack_from("<HH", raw, 0)
            if wire_len != payload_len:
                errors.append(f"wire length {wire_len}B != header {payload_len}B")
            if wire_opcode != opcode:
                errors.append(f"wire opcode 0x{wire_opcode:04X} != header 0x{opcode:04X}")

        contract = CONTRACTS.get((direction, opcode))
        if contract:
            length_error = contract.length_error(payload_len)
            if length_error:
                errors.append(length_error)
            label, category, persistence = contract.label, contract.category, contract.persistence
        else:
            label, category, persistence = "unknown opcode", "unknown", None

        decoded = _decode(direction, opcode, payload)
        if decoded.get("validation_error"):
            errors.append(str(decoded["validation_error"]))
        explicit_time = metadata.get("t") or metadata.get("time") or metadata.get("timestamp")
        events.append(PacketEvent(
            source=str(path), line=start + 1, capture_time=capture_time,
            timestamp=explicit_time or capture_time,
            timestamp_kind="packet" if explicit_time else "capture-start-approx",
            direction=direction, seq=int(match.group("seq")), opcode=opcode,
            payload_len=payload_len, total_len=total_len, origin=origin,
            entity=metadata.get("entity") or metadata.get("entity_id"),
            connection=metadata.get("conn") or metadata.get("connection"),
            payload=payload, label=label, category=category,
            persistence=persistence, unknown=contract is None,
            malformed=tuple(dict.fromkeys(errors)), decoded=decoded,
        ))
    return events


def resolve_inputs(values: Sequence[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        candidate = Path(value)
        if candidate.is_dir():
            paths.extend(sorted(candidate.glob("packets_*.txt")))
        elif candidate.is_file():
            paths.append(candidate)
        else:
            paths.extend(Path(item) for item in sorted(glob.glob(value)))
    return list(dict.fromkeys(path.resolve() for path in paths if path.is_file()))


def parse_opcode(value: str) -> int:
    return int(value, 16 if value.lower().startswith("0x") else 0)


def filter_events(events: Iterable[PacketEvent], args: argparse.Namespace) -> list[PacketEvent]:
    result = []
    opcodes = set(args.opcode or [])
    needle = bytes.fromhex(args.contains.replace(" ", "")) if args.contains else None
    for event in events:
        if args.direction and event.direction != args.direction:
            continue
        if opcodes and event.opcode not in opcodes:
            continue
        if args.category and event.category != args.category:
            continue
        if args.entity and (event.entity or "unknown") != args.entity:
            continue
        if args.connection and (event.connection or "unknown") != args.connection:
            continue
        if args.persistence and not event.persistence:
            continue
        if args.unknown_only and not event.unknown:
            continue
        if args.malformed_only and not event.malformed:
            continue
        if args.min_len is not None and event.payload_len < args.min_len:
            continue
        if args.max_len is not None and event.payload_len > args.max_len:
            continue
        if needle is not None and needle not in event.payload:
            continue
        result.append(event)
    return result[:args.limit] if args.limit else result


def summarize(events: Sequence[PacketEvent], files: int) -> dict[str, object]:
    return {
        "files": files,
        "packets": len(events),
        "directions": dict(Counter(event.direction for event in events)),
        "categories": dict(Counter(event.category for event in events)),
        "opcodes": dict(Counter(f"{event.direction} 0x{event.opcode:04X}" for event in events)),
        "unknown": sum(event.unknown for event in events),
        "malformed": sum(bool(event.malformed) for event in events),
        "persistence_events": sum(bool(event.persistence) for event in events),
        "entity_metadata_available": sum(event.entity is not None for event in events),
        "connection_metadata_available": sum(event.connection is not None for event in events),
        "packet_timestamps_available": sum(event.timestamp_kind == "packet" for event in events),
    }


def render_text(events: Sequence[PacketEvent], summary: dict[str, object]) -> str:
    lines = [
        f"files={summary['files']} packets={summary['packets']} unknown={summary['unknown']} "
        f"malformed={summary['malformed']} persistence={summary['persistence_events']}",
        "timestamp              dir  opcode len seq  entity conn label / decoded",
    ]
    for event in events:
        timestamp = (event.timestamp or "unknown") + ("~" if event.timestamp_kind != "packet" else "")
        flags = []
        if event.persistence:
            flags.append(event.persistence)
        if event.unknown:
            flags.append("UNKNOWN")
        if event.malformed:
            flags.append("MALFORMED:" + "; ".join(event.malformed))
        decoded = json.dumps(event.decoded, ensure_ascii=False, separators=(",", ":")) if event.decoded else ""
        tail = " | ".join(item for item in [event.label, decoded, ",".join(flags)] if item)
        lines.append(f"{timestamp:<22} {event.direction:<4} 0x{event.opcode:04X} "
                     f"{event.payload_len:>3} {event.seq:>4}  {(event.entity or '-'):>6} "
                     f"{(event.connection or '-'):>4} {tail} [{Path(event.source).name}:{event.line}]")
    lines.append("~ capture start time; legacy text has no per-packet timestamp")
    return "\n".join(lines) + "\n"


def render_html(events: Sequence[PacketEvent], summary: dict[str, object]) -> str:
    rows = []
    for event in events:
        classes = " ".join(filter(None, ["unknown" if event.unknown else "", "bad" if event.malformed else ""]))
        flags = ", ".join(event.malformed) or ""
        search = " ".join((event.direction, f"0x{event.opcode:04X}", event.label,
                           event.category, event.persistence or "", json.dumps(event.decoded, ensure_ascii=False),
                           event.entity or "unknown", event.connection or "unknown")).lower()
        rows.append(
            f'<tr class="{classes}" data-search="{html.escape(search, quote=True)}" '
            f'data-direction="{event.direction}" data-category="{html.escape(event.category)}">'
            f'<td>{html.escape(event.timestamp or "unknown")}{"~" if event.timestamp_kind != "packet" else ""}</td>'
            f'<td>{event.direction}</td><td><code>0x{event.opcode:04X}</code></td>'
            f'<td>{event.payload_len}</td><td>{event.seq}</td>'
            f'<td>{html.escape(event.entity or "unknown")}</td><td>{html.escape(event.connection or "unknown")}</td>'
            f'<td>{html.escape(event.label)}<small>{html.escape(event.category)}</small></td>'
            f'<td>{html.escape(event.persistence or "")}</td>'
            f'<td><code>{html.escape(json.dumps(event.decoded, ensure_ascii=False))}</code></td>'
            f'<td class="error">{html.escape(flags)}</td>'
            f'<td title="{html.escape(event.source, quote=True)}">{html.escape(Path(event.source).name)}:{event.line}</td></tr>'
        )
    generated = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    cards = "".join(f"<div><b>{html.escape(str(value))}</b><span>{html.escape(key.replace('_', ' '))}</span></div>"
                    for key, value in summary.items() if not isinstance(value, dict))
    categories = sorted({event.category for event in events})
    options = "".join(f'<option value="{html.escape(value)}">{html.escape(value)}</option>' for value in categories)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Azrok capture report</title>
<style>body{{font:14px system-ui;margin:24px;background:#10131a;color:#e8edf7}}h1{{margin-bottom:4px}}
.note,small{{color:#9da9bd}}.cards{{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}}.cards div{{background:#1b2230;padding:10px 16px;border-radius:8px}}.cards b,.cards span{{display:block}}.cards b{{font-size:20px}}input,select{{padding:8px;background:#151b26;color:#fff;border:1px solid #3a465b;border-radius:5px;margin:0 6px 12px 0}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:7px;border-bottom:1px solid #283244;vertical-align:top}}th{{position:sticky;top:0;background:#151b26}}code{{font-size:12px;word-break:break-all}}small{{display:block}}tr.unknown{{background:#302819}}tr.bad{{background:#3a1d24}}.error{{color:#ff9cae}}</style></head><body>
<h1>Azrok capture report</h1><div class="note">Generated {html.escape(generated)}. A ~ timestamp is the capture start, not a per-packet timestamp. Legacy captures do not contain connection/entity metadata.</div>
<div class="cards">{cards}</div><input id="q" size="36" placeholder="search opcode, label, decoded value..."><select id="dir"><option value="">all directions</option><option>C-&gt;S</option><option>S-&gt;C</option></select><select id="cat"><option value="">all categories</option>{options}</select>
<table><thead><tr><th>time</th><th>dir</th><th>opcode</th><th>len</th><th>seq</th><th>entity</th><th>conn</th><th>contract</th><th>persistence</th><th>decoded</th><th>malformed</th><th>source</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<script>const q=document.querySelector('#q'),d=document.querySelector('#dir'),c=document.querySelector('#cat');function f(){{for(const r of document.querySelectorAll('tbody tr'))r.hidden=!(r.dataset.search.includes(q.value.toLowerCase())&&(!d.value||r.dataset.direction===d.value)&&(!c.value||r.dataset.category===c.value))}}q.oninput=d.onchange=c.onchange=f;</script></body></html>"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Azrok text capture inspector")
    parser.add_argument("inputs", nargs="+", help="capture file, directory, or glob")
    parser.add_argument("--direction", choices=("C->S", "S->C"))
    parser.add_argument("--opcode", action="append", type=parse_opcode, help="repeatable, e.g. 0x0007")
    parser.add_argument("--category")
    parser.add_argument("--entity", help="entity id, or 'unknown'")
    parser.add_argument("--connection", help="connection id, or 'unknown'")
    parser.add_argument("--persistence", action="store_true", help="only selected-character persistence events")
    parser.add_argument("--unknown-only", action="store_true")
    parser.add_argument("--malformed-only", action="store_true")
    parser.add_argument("--min-len", type=int)
    parser.add_argument("--max-len", type=int)
    parser.add_argument("--contains", help="payload hex subsequence")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--format", choices=("text", "json", "html"), default="text")
    parser.add_argument("--output", type=Path, help="write report here (the only write operation)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = resolve_inputs(args.inputs)
    if not paths:
        parser.error("no capture files matched")
    try:
        events = [event for path in paths for event in parse_capture(path)]
        events = filter_events(events, args)
    except ValueError as exc:
        parser.error(str(exc))
    summary = summarize(events, len(paths))
    if args.format == "json":
        report = json.dumps({"summary": summary, "packets": [event.as_dict() for event in events]},
                            ensure_ascii=False, indent=2) + "\n"
    elif args.format == "html":
        report = render_html(events, summary)
    else:
        report = render_text(events, summary)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
