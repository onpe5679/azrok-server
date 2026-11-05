#!/usr/bin/env python3
"""Extract navigation metadata from an Acknex WMB6 level and render an SVG map.

The output contains only placement metadata and a schematic drawing.  It does
not copy textures, meshes, or any other game asset into the generated files.

PatHouse is the first supported map.  The WMB6 entity directory layout used
here is validated against ``Data/Space/PatHouse/room.wmb``.  Unknown record
sizes are retained in JSON/CSV instead of being guessed as model entities.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


ENTITY_DIRECTORY_OFFSET_FIELD = 0x7C
ENTITY_DIRECTORY_SIZE_FIELD = 0x80
WORLD_BOUNDS_FIELD = 0x9C


@dataclass
class Record:
    index: int
    relative_offset: int
    byte_size: int
    record_kind: str
    x: float | None = None
    y: float | None = None
    z: float | None = None
    pan: float | None = None
    tilt: float | None = None
    roll: float | None = None
    scale_x: float | None = None
    scale_y: float | None = None
    scale_z: float | None = None
    name: str = ""
    resource: str = ""
    wmb_action: str = ""
    category: str = ""
    category_evidence: str = ""
    runtime_type: int | None = None
    runtime_action: int | None = None
    runtime_evidence: str = ""
    navigation_note: str = ""
    color_r: float | None = None
    color_g: float | None = None
    color_b: float | None = None
    range: float | None = None


RUNTIME_ANNOTATIONS: dict[str, dict[str, Any]] = {
    "dm_door_0003_057": {
        "category": "bathroom_internal_door",
        "category_evidence": (
            "VERIFIED: WMB bathroom-cluster placement and user visual correction"
        ),
        "runtime_type": 0x24,
        "runtime_action": 0x26,
        "runtime_evidence": (
            "VERIFIED static default type/action; prior outside-exit identity was false"
        ),
        "navigation_note": "Bathroom/internal door; do not use as the outside target",
    },
    "doorframe_01": {
        "category": "outside_exit_frame",
        "category_evidence": (
            "VERIFIED: WMB record colocated with gate_mun outside-gate assembly"
        ),
        "runtime_type": 0x1F,
        "runtime_action": 0x26,
        "runtime_evidence": "VERIFIED static default type/action",
        "navigation_note": "Frame colocated with the actual far-left outside gate",
    },
    "gate_mun_MDL_048": {
        "category": "outside_exit_gate",
        "category_evidence": (
            "INFERRED (strong): user far-left correction plus WMB gate/frame placement"
        ),
        "runtime_evidence": (
            "NOT VERIFIED: exact gate surface to mirror_01/type 0x20/action 0x6F binding"
        ),
        "navigation_note": "Far-left outside gate candidate; exact 0x6F hit provenance pending",
    },
    "mirror_01": {
        "category": "wardrobe_mirror",
        "category_evidence": "VERIFIED visible identity correction",
        "runtime_type": 0x20,
        "runtime_action": 0x6F,
        "runtime_evidence": (
            "VERIFIED static descriptor; NOT VERIFIED binding to visible outside mesh"
        ),
        "navigation_note": "Wardrobe/mirror; do not use as the visible exit marker",
    },
}


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _f32s(data: bytes, offset: int, count: int) -> tuple[float, ...]:
    return struct.unpack_from("<" + "f" * count, data, offset)


def _fixed_ascii(data: bytes, offset: int, size: int = 32) -> str:
    raw = data[offset : offset + size].split(b"\0", 1)[0]
    return raw.decode("ascii", errors="replace")


def _ascii_sequences(data: bytes, start: int, end: int) -> list[str]:
    """Return printable NUL-delimited strings from a model entity record.

    WMB6 uses different string-slot widths for the compact (0x88) and extended
    (0x174) records.  Scanning their bounded string area avoids imposing the
    wrong width while still refusing to read into a neighbouring record.
    """
    result: list[str] = []
    current = bytearray()
    for value in data[start:end]:
        if 32 <= value < 127:
            current.append(value)
        else:
            if len(current) >= 3:
                result.append(current.decode("ascii"))
            current.clear()
    if len(current) >= 3:
        result.append(current.decode("ascii"))
    return result


def _infer_category(name: str, resource: str, action: str) -> tuple[str, str]:
    key = f"{name} {resource}".lower()
    if "wall" in key or "sky" in key or "gate_mun" in key:
        return "structure", "INFERRED from WMB entity/resource name"
    if any(word in key for word in ("shadow", ".tga", "grass", "foot", "food1")):
        return "decal", "INFERRED from WMB resource extension/name"
    if "door" in key:
        return "door_like", "INFERRED from WMB entity/resource name"
    if any(
        word in key
        for word in (
            "vacuum",
            "foodmaker",
            "shower",
            "bath",
            "bellow",
            "boiler",
            "elefan",
            "firewood",
        )
    ):
        return "care_prop_candidate", "INFERRED from WMB entity/resource name"
    if action:
        return "scripted_prop", "INFERRED from non-empty WMB action field"
    return "prop", "INFERRED from WMB model record"


def parse_wmb6(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 0x140 or data[:4] != b"WMB6":
        raise ValueError(f"not a supported WMB6 file: {path}")

    directory_offset = _u32(data, ENTITY_DIRECTORY_OFFSET_FIELD)
    directory_size = _u32(data, ENTITY_DIRECTORY_SIZE_FIELD)
    if directory_offset + directory_size > len(data):
        raise ValueError("entity directory extends beyond file")

    count = _u32(data, directory_offset)
    if count == 0 or count > 100_000:
        raise ValueError(f"implausible WMB6 entity record count: {count}")
    table_end = directory_offset + 4 + count * 4
    if table_end > directory_offset + directory_size:
        raise ValueError("entity offset table extends beyond directory")

    relative_offsets = struct.unpack_from("<" + "I" * count, data, directory_offset + 4)
    record_base = directory_offset + 4
    records: list[Record] = []

    for index, relative_offset in enumerate(relative_offsets):
        next_offset = (
            relative_offsets[index + 1]
            if index + 1 < count
            else directory_size - 4
        )
        byte_size = next_offset - relative_offset
        absolute = record_base + relative_offset
        if byte_size < 0 or absolute + byte_size > directory_offset + directory_size:
            raise ValueError(f"record {index} has invalid bounds")

        if byte_size == 0x24:
            x, y, z, r, g, b, light_range = _f32s(data, absolute, 7)
            records.append(
                Record(
                    index=index,
                    relative_offset=relative_offset,
                    byte_size=byte_size,
                    record_kind="light",
                    x=x,
                    y=y,
                    z=z,
                    category="light",
                    category_evidence="VERIFIED WMB6 0x24 light record layout",
                    color_r=r,
                    color_g=g,
                    color_b=b,
                    range=light_range,
                )
            )
            continue

        # PatHouse also ends with one compact 0x84 model record (gate_mun).
        # Its common transform/string prefix is identical to the 0x88/0x174
        # records; only the trailing WMB-specific fields are shorter.
        if byte_size in (0x84, 0x88, 0x174):
            x, y, z, pan, tilt, roll, sx, sy, sz = _f32s(data, absolute, 9)
            strings = _ascii_sequences(
                data, absolute + 0x24, absolute + min(byte_size, 0xC0)
            )
            name = strings[0] if strings else ""
            resource = strings[1] if len(strings) > 1 else ""
            action = strings[2] if len(strings) > 2 else ""
            category, category_evidence = _infer_category(name, resource, action)
            annotation = RUNTIME_ANNOTATIONS.get(name, {})
            records.append(
                Record(
                    index=index,
                    relative_offset=relative_offset,
                    byte_size=byte_size,
                    record_kind="model_entity",
                    x=x,
                    y=y,
                    z=z,
                    pan=pan,
                    tilt=tilt,
                    roll=roll,
                    scale_x=sx,
                    scale_y=sy,
                    scale_z=sz,
                    name=name,
                    resource=resource,
                    wmb_action=action,
                    category=annotation.get("category", category),
                    category_evidence=annotation.get(
                        "category_evidence", category_evidence
                    ),
                    runtime_type=annotation.get("runtime_type"),
                    runtime_action=annotation.get("runtime_action"),
                    runtime_evidence=annotation.get("runtime_evidence", ""),
                    navigation_note=annotation.get("navigation_note", ""),
                )
            )
            continue

        records.append(
            Record(
                index=index,
                relative_offset=relative_offset,
                byte_size=byte_size,
                record_kind="unknown",
                category="unknown",
                category_evidence="NOT VERIFIED: unsupported WMB6 record layout",
            )
        )

    min_x, min_y, min_z, max_x, max_y, max_z = _f32s(
        data, WORLD_BOUNDS_FIELD, 6
    )
    return {
        "format": "WMB6",
        "source": str(path.as_posix()),
        "source_size": len(data),
        "entity_directory_offset": directory_offset,
        "entity_directory_size": directory_size,
        "record_count": count,
        "world_bounds": {
            "min_x": min_x,
            "min_y": min_y,
            "min_z": min_z,
            "max_x": max_x,
            "max_y": max_y,
            "max_z": max_z,
            "evidence": "VERIFIED values read directly from WMB6 header",
        },
        "records": records,
    }


def _load_overlay(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("overlay JSON must contain an object")
    return value


def _finite_xy(records: Iterable[Record], kind: str = "model_entity") -> list[tuple[float, float]]:
    return [
        (record.x, record.y)
        for record in records
        if record.record_kind == kind
        and record.x is not None
        and record.y is not None
        and math.isfinite(record.x)
        and math.isfinite(record.y)
    ]


def _map_bounds(records: list[Record], world_bounds: dict[str, float]) -> tuple[float, float, float, float]:
    # Model placement bounds produce a much more useful room-scale map than the
    # whole compiled BSP extent.  Exclude sky/special outliers but always retain
    # the two known doors and the mirror landmark.
    focus = [
        record
        for record in records
        if record.record_kind == "model_entity"
        and record.category not in {"decal"}
        and "sky" not in record.name.lower()
        and record.x is not None
        and record.y is not None
        and abs(record.x) < 2000
        and abs(record.y) < 2000
    ]
    points = _finite_xy(focus)
    if not points:
        return (
            world_bounds["min_x"],
            world_bounds["min_y"],
            world_bounds["max_x"],
            world_bounds["max_y"],
        )
    xs, ys = zip(*points)
    pad = max(120.0, 0.08 * max(max(xs) - min(xs), max(ys) - min(ys)))
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def render_svg(parsed: dict[str, Any], overlay: dict[str, Any]) -> str:
    records: list[Record] = parsed["records"]
    world_bounds = parsed["world_bounds"]
    min_x, min_y, max_x, max_y = _map_bounds(records, world_bounds)

    width, height = 1280, 960
    margin_left, margin_top, margin_right, margin_bottom = 95, 100, 300, 85
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    world_w = max(max_x - min_x, 1.0)
    world_h = max(max_y - min_y, 1.0)
    scale = min(plot_w / world_w, plot_h / world_h)
    used_w, used_h = world_w * scale, world_h * scale
    left = margin_left + (plot_w - used_w) / 2
    top = margin_top + (plot_h - used_h) / 2

    def project(x: float, y: float) -> tuple[float, float]:
        return left + (x - min_x) * scale, top + (max_y - y) * scale

    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="960" viewBox="0 0 1280 960">',
        "<style>",
        "text{font-family:Segoe UI,Malgun Gothic,sans-serif;fill:#d9e5ee}",
        ".small{font-size:11px}.label{font-size:13px;font-weight:600}.title{font-size:25px;font-weight:700}",
        ".sub{font-size:13px;fill:#9fb4c4}.grid{stroke:#263947;stroke-width:1}.axis{stroke:#607d8b;stroke-width:1.5}",
        "</style>",
        '<rect width="1280" height="960" fill="#101820"/>',
        '<text x="48" y="43" class="title">PatHouse WMB6 navigation map</text>',
        '<text x="48" y="68" class="sub">Metadata-only schematic · X right / Y up · compiled geometry bounds are larger than this room-focused view</text>',
        f'<rect x="{left:.2f}" y="{top:.2f}" width="{used_w:.2f}" height="{used_h:.2f}" fill="#162630" stroke="#58717f" stroke-width="2"/>',
    ]

    step = 200
    gx = math.ceil(min_x / step) * step
    while gx <= max_x:
        px, _ = project(gx, min_y)
        out.append(f'<line x1="{px:.2f}" y1="{top:.2f}" x2="{px:.2f}" y2="{top+used_h:.2f}" class="grid"/>')
        out.append(f'<text x="{px+3:.2f}" y="{top+used_h-5:.2f}" class="small">{gx:g}</text>')
        gx += step
    gy = math.ceil(min_y / step) * step
    while gy <= max_y:
        _, py = project(min_x, gy)
        out.append(f'<line x1="{left:.2f}" y1="{py:.2f}" x2="{left+used_w:.2f}" y2="{py:.2f}" class="grid"/>')
        out.append(f'<text x="{left+4:.2f}" y="{py-4:.2f}" class="small">{gy:g}</text>')
        gy += step
    if min_x <= 0 <= max_x:
        px, _ = project(0, min_y)
        out.append(f'<line x1="{px:.2f}" y1="{top:.2f}" x2="{px:.2f}" y2="{top+used_h:.2f}" class="axis"/>')
    if min_y <= 0 <= max_y:
        _, py = project(min_x, 0)
        out.append(f'<line x1="{left:.2f}" y1="{py:.2f}" x2="{left+used_w:.2f}" y2="{py:.2f}" class="axis"/>')

    palette = {
        "outside_exit_gate": "#ff5252",
        "outside_exit_frame": "#26c6da",
        "bathroom_internal_door": "#29b6f6",
        "wardrobe_mirror": "#ffa726",
        "care_prop_candidate": "#ab47bc",
        "scripted_prop": "#7e57c2",
        "door_like": "#29b6f6",
        "structure": "#78909c",
        "decal": "#546e7a",
        "prop": "#8bc34a",
    }
    labelled = {
        "dm_door_0003_057",
        "gate_mun_MDL_048",
        "doorframe_01",
        "mirror_01",
        "vacuumcleaner_01",
        "foodmaker_01",
        "shower_01",
        "bathfuni_01",
        "bathbox_01",
        "room_sky_0003_061",
    }
    # Draw inferred footprints first.  Radius is category-based and is only a
    # visual navigation aid; the JSON labels this as schematic, not collision.
    for record in records:
        if record.record_kind != "model_entity" or record.x is None or record.y is None:
            continue
        if not (min_x <= record.x <= max_x and min_y <= record.y <= max_y):
            continue
        px, py = project(record.x, record.y)
        color = palette.get(record.category, "#90a4ae")
        radius = 17 if record.category in {"structure", "door_like"} else 11
        if record.category == "outside_exit_gate":
            out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="25" fill="#ff5252" opacity="0.16"/>')
            out.append(f'<path d="M {px:.2f} {py-13:.2f} L {px+4:.2f} {py-4:.2f} L {px+14:.2f} {py-3:.2f} L {px+6:.2f} {py+4:.2f} L {px+9:.2f} {py+14:.2f} L {px:.2f} {py+8:.2f} L {px-9:.2f} {py+14:.2f} L {px-6:.2f} {py+4:.2f} L {px-14:.2f} {py-3:.2f} L {px-4:.2f} {py-4:.2f} Z" fill="#ff5252" stroke="#fff" stroke-width="1.5"/>')
        elif record.category == "outside_exit_frame":
            out.append(f'<rect x="{px-9:.2f}" y="{py-9:.2f}" width="18" height="18" fill="{color}" stroke="#fff" stroke-width="1.2" transform="rotate(45 {px:.2f} {py:.2f})"/>')
        else:
            out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{radius}" fill="{color}" opacity="0.28"/>')
            out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" fill="{color}"/>')
        if record.name in labelled or record.category in {"outside_exit_gate", "outside_exit_frame", "bathroom_internal_door", "wardrobe_mirror"}:
            label = html.escape(record.name)
            label_on_left = px > left + used_w - 170
            label_x = px - 12 if label_on_left else px + 11
            anchor = ' text-anchor="end"' if label_on_left else ""
            out.append(f'<text x="{label_x:.2f}" y="{py-9:.2f}" class="label"{anchor}>{label}</text>')
            out.append(f'<text x="{label_x:.2f}" y="{py+7:.2f}" class="small"{anchor}>({record.x:g}, {record.y:g}, z={record.z:.1f})</text>')

    for key, color, label in (
        ("player", "#ffeb3b", "PLAYER"),
        ("camera", "#00e5ff", "CAMERA"),
    ):
        point = overlay.get(key)
        if isinstance(point, dict) and isinstance(point.get("x"), (int, float)) and isinstance(point.get("y"), (int, float)):
            px, py = project(float(point["x"]), float(point["y"]))
            out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="10" fill="none" stroke="{color}" stroke-width="3"/>')
            out.append(f'<text x="{px+14:.2f}" y="{py+4:.2f}" class="label" fill="{color}">{label}</text>')

    legend_x = width - margin_right + 28
    out.extend(
        [
            f'<text x="{legend_x}" y="125" class="label">Navigation landmarks</text>',
            f'<circle cx="{legend_x+8}" cy="153" r="8" fill="#ff5252"/><text x="{legend_x+25}" y="158" class="small">outside gate candidate: (522, 801)</text>',
            f'<circle cx="{legend_x+8}" cy="181" r="8" fill="#26c6da"/><text x="{legend_x+25}" y="186" class="small">gate frame: (526, 802)</text>',
            f'<circle cx="{legend_x+8}" cy="209" r="8" fill="#29b6f6"/><text x="{legend_x+25}" y="214" class="small">bath door: (-813, -107)</text>',
            f'<circle cx="{legend_x+8}" cy="237" r="8" fill="#ffa726"/><text x="{legend_x+25}" y="242" class="small">mirror: (-336, 1152)</text>',
            f'<text x="{legend_x}" y="286" class="label">Route cue</text>',
            f'<text x="{legend_x}" y="309" class="small">The outside gate is far left</text>',
            f'<text x="{legend_x}" y="327" class="small">and below the room&apos;s central</text>',
            f'<text x="{legend_x}" y="345" class="small">furniture cluster in world XY.</text>',
            f'<text x="{legend_x}" y="387" class="label">Evidence limits</text>',
            f'<text x="{legend_x}" y="410" class="small">Circles are schematic footprints.</text>',
            f'<text x="{legend_x}" y="428" class="small">They are not collision polygons.</text>',
            f'<text x="{legend_x}" y="446" class="small">WMB header world bounds:</text>',
            f'<text x="{legend_x}" y="464" class="small">X {world_bounds["min_x"]:g}..{world_bounds["max_x"]:g}</text>',
            f'<text x="{legend_x}" y="482" class="small">Y {world_bounds["min_y"]:g}..{world_bounds["max_y"]:g}</text>',
            f'<text x="48" y="925" class="sub">Source: {html.escape(parsed["source"])} · {parsed["record_count"]} directory records · generated without embedding original assets</text>',
            "</svg>",
        ]
    )
    return "\n".join(out)


def _write_csv(path: Path, records: list[Record]) -> None:
    fields = list(Record.__dataclass_fields__)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def build_outputs(wmb_path: Path, output_dir: Path, overlay_path: Path | None) -> dict[str, Path]:
    parsed = parse_wmb6(wmb_path)
    overlay = _load_overlay(overlay_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = wmb_path.stem
    json_path = output_dir / f"{stem}_minimap.json"
    csv_path = output_dir / f"{stem}_minimap.csv"
    svg_path = output_dir / f"{stem}_minimap.svg"

    serializable = dict(parsed)
    serializable["records"] = [asdict(record) for record in parsed["records"]]
    serializable["map_semantics"] = {
        "x_axis": "right",
        "y_axis": "up (SVG projection is inverted)",
        "footprints": "schematic category radii; NOT VERIFIED collision geometry",
        "overlay": overlay,
    }
    json_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(csv_path, parsed["records"])
    svg_path.write_text(render_svg(parsed, overlay), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "svg": svg_path}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wmb", type=Path, help="source WMB6 file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/minimap"),
        help="directory for JSON, CSV, and SVG outputs",
    )
    parser.add_argument(
        "--overlay",
        type=Path,
        help='optional JSON with {"player":{"x":...,"y":...},"camera":...}',
    )
    args = parser.parse_args()
    outputs = build_outputs(args.wmb, args.output_dir, args.overlay)
    for kind, path in outputs.items():
        print(f"{kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
