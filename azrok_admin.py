"""Read-only, bounded projections for the private character administration UI.

The caller owns authentication and any write transaction.  This module never
opens a state file for writing and does not expose raw snapshots or packet data.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import struct
from pathlib import Path


KEY_RE = re.compile(r"^a([0-9a-f]{2,26})_s([0-3])_c([0-9a-f]{2,64})$")
STATE_SUFFIX = "_state_v1.json"
INVENTORY_SIZES = {
    "furniture": 33, "drug": 15, "energy": 20, "food": 38,
    "ingredient": 3, "toy": 10, "gym": 8, "book": 1,
}
ITEM_ID_BASE = {
    "furniture": 0, "drug": 4000, "energy": 5000, "food": 1000,
    "ingredient": 1500, "toy": 2000, "gym": 2500, "book": 3000,
}
ITEM_ID_COUNTS = {
    "furniture": 33, "drug": 6, "energy": 3, "food": 33,
    "ingredient": 3, "toy": 10, "gym": 8, "book": 1,
}
UNIQUE_INVENTORIES = frozenset(("furniture", "toy", "gym", "book"))
KOREAN_CATEGORIES = {
    "furniture": "가구", "drug": "약", "energy": "에너지",
    "food": "음식", "ingredient": "재료", "toy": "장난감",
    "gym": "운동기구", "book": "책",
}
VERIFIED_ITEM_LABELS = {1000: "이유식"}
STAT_COUNT = 66
SNAPSHOT_SIZE = 0xC4
MAX_STATE_BYTES = 256 * 1024


def parse_character_key(key: str) -> dict:
    if not isinstance(key, str) or not (match := KEY_RE.fullmatch(key)):
        raise ValueError("invalid character key")
    account_hex, slot, name_hex = match.groups()
    return {
        "key": key,
        "account": bytes.fromhex(account_hex).decode("cp949", "replace"),
        "slot": int(slot),
        "name": bytes.fromhex(name_hex).decode("cp949", "replace"),
    }


def _state_path(state_dir: str | Path, key: str) -> Path:
    parse_character_key(key)
    return Path(state_dir) / (key + STATE_SUFFIX)


def _read_state(path: Path) -> dict:
    if path.stat().st_size > MAX_STATE_BYTES:
        raise ValueError("state document exceeds size limit")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("unsupported state document")
    return document


def _snapshot_stats(document: dict) -> tuple[int | None, int | None, list[int] | None]:
    raw = document.get("snapshot_hex")
    if not isinstance(raw, str) or len(raw) != SNAPSHOT_SIZE * 2:
        return None, None, None
    try:
        snapshot = bytes.fromhex(raw)
    except ValueError:
        return None, None, None
    stats = [struct.unpack_from("<H", snapshot, 0x0A + i * 2)[0]
             for i in range(STAT_COUNT)]
    return snapshot[5], stats[1], stats


def _inventory(document: dict) -> dict:
    source = document.get("inventory") or {}
    result = {}
    for name, size in INVENTORY_SIZES.items():
        values = source.get(name)
        if isinstance(values, list) and len(values) == size:
            result[name] = [int(v) for v in values if type(v) is int and 0 <= v <= 255]
            if len(result[name]) != size:
                result[name] = []
        else:
            result[name] = []
    return result


def character_detail(state_dir: str | Path, key: str) -> dict:
    """Return a sanitized canonical projection; missing files raise FileNotFoundError."""
    path = _state_path(state_dir, key)
    document = _read_state(path)
    identity = parse_character_key(key)
    stage, level, stats = _snapshot_stats(document)
    saved = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
    rows = document.get("runtime_rows") or []
    return {
        **identity,
        "currency": int(document.get("currency", 0)),
        "revision": int(document.get("revision", 0)),
        "species": int((document.get("character") or {}).get("species", 0)),
        "evolution": stage,
        "level": level,
        "stats": stats,
        "inventory": _inventory(document),
        "accessory_slots": list(document.get("accessory_slots") or []),
        "active_loadouts": document.get("active_loadouts") or {},
        "active_quests": [
            {"slot": index, "kind": int(row["kind"]),
             "aux": int(row["aux"]), "value": int(row["value"])}
            for index, row in enumerate(rows[:10])
            if isinstance(row, dict) and int(row.get("kind", 255)) != 255
        ],
        "completed_quest_count": len(document.get("completed_runtime_rows") or []),
        "state_saved_utc": saved.isoformat(),
        "activity_basis": "state_file_mtime_not_login",
    }


def list_characters(state_dir: str | Path, *, limit: int = 200,
                    account: str | None = None) -> list[dict]:
    """List direct canonical files only; excludes archived and test subdirs."""
    if not 1 <= limit <= 1000:
        raise ValueError("limit out of range")
    directory = Path(state_dir)
    found = []
    for path in directory.glob("*" + STATE_SUFFIX):
        if not path.is_file():
            continue
        key = path.name[:-len(STATE_SUFFIX)]
        try:
            identity = parse_character_key(key)
            if account is not None and identity["account"] != account:
                continue
            found.append((path.stat().st_mtime, key))
        except (OSError, ValueError):
            continue
    found.sort(reverse=True)
    results = []
    for _mtime, key in found[:limit]:
        try:
            detail = character_detail(directory, key)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        results.append({field: detail[field] for field in (
            "key", "account", "slot", "name", "currency", "revision",
            "species", "evolution", "level", "state_saved_utc", "activity_basis",
        )})
    return results


def list_accounts(state_dir: str | Path, registry_snapshot: dict | None = None,
                  players: list[dict] | None = None, *, limit: int = 1000) -> list[dict]:
    """Merge registry identities with saved characters; never infer login time."""
    characters = list_characters(state_dir, limit=limit)
    by_account: dict[str, dict] = {}
    for item in (registry_snapshot or {}).get("accounts", ()):
        if not isinstance(item, dict) or not isinstance(item.get("account"), str):
            continue
        account = item["account"]
        by_account[account] = {
            "account": account, "characters": [],
            "binding_count": int(item.get("binding_count", 0)),
            "online": False,
        }
    for character in characters:
        account = character["account"]
        by_account.setdefault(account, {
            "account": account, "characters": [], "binding_count": 0,
            "online": False,
        })["characters"].append(character)
    for player in players or ():
        if not isinstance(player, dict):
            continue
        account = player.get("account")
        if isinstance(account, str) and account in by_account:
            by_account[account]["online"] = True
    result = list(by_account.values())
    for account in result:
        saved = [c["state_saved_utc"] for c in account["characters"]]
        account["latest_state_saved_utc"] = max(saved) if saved else None
        account["activity_basis"] = "state_file_mtime_not_login"
        account["last_login"] = None
    result.sort(key=lambda a: (a["latest_state_saved_utc"] or "", a["account"]), reverse=True)
    return result[:limit]


def character_admin_view(state_dir: str | Path, key: str,
                         item_labels: dict[int, str] | None = None) -> dict:
    """Render the stable shape consumed by the character editor."""
    detail = character_detail(state_dir, key)
    labels = {**VERIFIED_ITEM_LABELS, **(item_labels or {})}
    inventory = []
    for name, values in detail["inventory"].items():
        for slot, quantity in enumerate(values):
            item_id = ITEM_ID_BASE[name] + slot
            reserved = slot >= ITEM_ID_COUNTS[name]
            category = KOREAN_CATEGORIES[name]
            inventory.append({"item_id": item_id, "quantity": quantity,
                              "name": labels.get(item_id, f"{category} {slot + 1}" +
                                                 (" (예약 슬롯)" if reserved else "")),
                              "category": category, "reserved": reserved})
    editable = {
        "currency": {"value": detail["currency"], "label": "펀콘",
                     "type": "integer", "min": 0, "max": 0xFFFFFFFF},
    }
    return {
        "key": key, "revision": detail["revision"],
        "account": detail["account"],
        "character": {"name": detail["name"], "slot": detail["slot"],
                      "species": detail["species"], "level": detail["level"],
                      "evolution": detail["evolution"]},
        "editable_fields": editable, "inventory": inventory,
        "item_labels": {str(item["item_id"]): item["name"] for item in inventory},
        "stats": detail["stats"],
        "active_quests": detail["active_quests"],
        "completed_quest_count": detail["completed_quest_count"],
        "state_saved_utc": detail["state_saved_utc"],
        "activity_basis": detail["activity_basis"],
    }


def validate_patch(document: dict, patch: dict) -> dict:
    """Validate a bounded proposed admin edit and return normalized fields.

    The write owner must reload under its lock, check revision, and use the
    canonical server save path.  This deliberately does not mutate document.
    """
    if not isinstance(document, dict) or not isinstance(patch, dict):
        raise ValueError("invalid state patch")
    if set(patch) - {"expected_revision", "currency", "inventory"}:
        raise ValueError("unsupported editable field")
    revision = patch.get("expected_revision")
    if type(revision) is not int or revision != document.get("revision"):
        raise ValueError("state revision conflict")
    result = {"expected_revision": revision}
    if "currency" in patch:
        result["currency"] = validate_currency_edit(patch["currency"])
    if "inventory" in patch:
        edits = patch["inventory"]
        if not isinstance(edits, list) or not 1 <= len(edits) <= sum(INVENTORY_SIZES.values()):
            raise ValueError("invalid inventory patch size")
        normalized = []
        seen = set()
        for item in edits:
            if not isinstance(item, dict) or set(item) != {"name", "slot", "quantity"}:
                raise ValueError("invalid inventory patch entry")
            name, slot, quantity = validate_inventory_edit(
                item["name"], item["slot"], item["quantity"])
            if (name, slot) in seen:
                raise ValueError("duplicate inventory slot")
            seen.add((name, slot))
            current = (document.get("inventory") or {}).get(name)
            if not isinstance(current, list) or len(current) != INVENTORY_SIZES[name]:
                raise ValueError("missing canonical inventory")
            normalized.append({"name": name, "slot": slot, "quantity": quantity})
        result["inventory"] = normalized
    if len(result) == 1:
        raise ValueError("empty state patch")
    return result


def validate_inventory_edit(name: str, slot: int, quantity: int) -> tuple[str, int, int]:
    """Validate a proposed edit; caller must enforce locking and persistence."""
    if name not in INVENTORY_SIZES or type(slot) is not int or type(quantity) is not int:
        raise ValueError("invalid inventory edit")
    if not 0 <= slot < ITEM_ID_COUNTS[name] or not 0 <= quantity <= 255:
        raise ValueError("inventory edit outside wire limits")
    if name in UNIQUE_INVENTORIES and quantity > 1:
        raise ValueError("unique inventory quantity exceeds one")
    return name, slot, quantity


def validate_currency_edit(amount: int) -> int:
    if type(amount) is not int or not 0 <= amount <= 0xFFFFFFFF:
        raise ValueError("currency outside wire limits")
    return amount


def capture_history(capture_root: str | Path, run_id: str, *,
                    entity_id: int | None = None, limit: int = 100) -> dict:
    """Project one capture run without exposing packet bodies or chat content.

    Capture records have no durable account key.  An entity filter narrows the
    display but cannot establish ownership across connections or runs.
    """
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
        raise ValueError("invalid capture run")
    if entity_id is not None and (type(entity_id) is not int or entity_id < 0):
        raise ValueError("invalid entity id")
    if not 1 <= limit <= 500:
        raise ValueError("limit out of range")
    path = Path(capture_root) / "runs" / run_id / "packets.jsonl"
    events = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream):
            if line_number >= 100_000:
                break
            if len(line) > 128 * 1024:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("schema") != "azrok.packet.capture.v1":
                continue
            if entity_id is not None and record.get("entity_id") != entity_id:
                continue
            opcode = record.get("opcode_int")
            if type(opcode) is not int:
                continue
            events.append({
                "timestamp_utc": record.get("timestamp_utc"),
                "direction": record.get("direction"),
                "opcode": f"0x{opcode:04X}",
                "category": (record.get("semantics") or {}).get("category"),
                "entity_id": record.get("entity_id"),
                "content_redacted": True,
            })
            if len(events) > limit:
                events.pop(0)
    return {"run_id": run_id, "events": events,
            "identity_basis": "entity_id_per_run_only_unverified_account_link",
            "chat_text_available": False}
