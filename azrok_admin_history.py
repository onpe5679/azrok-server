"""Small durable journal for authenticated access, chat and admin events.

This deliberately does not mirror the packet ring.  A bounded tail read is
reported as incomplete instead of presenting it as all historical activity.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone


_LOCK = threading.RLock()
_TAIL_BYTES = 8 * 1024 * 1024
_KEY_RE = re.compile(r"^a([0-9a-fA-F]{2,26})_s\d+_c[0-9a-fA-F]+$")
_DETAIL_KEYS = frozenset((
    "action", "event", "room", "reason", "outcome", "target", "item_id",
    "quantity", "old_value", "new_value", "backup_path", "key", "account",
))


def journal_path(server):
    state_dir = getattr(server, "state_store_dir", None)
    if not isinstance(state_dir, str) or not state_dir:
        raise ValueError("server.state_store_dir is required")
    return os.path.join(state_dir, "admin_history_v1.jsonl")


def _account_from_key(key):
    if not isinstance(key, str):
        return ""
    match = _KEY_RE.fullmatch(key)
    if not match:
        return ""
    try:
        return bytes.fromhex(match.group(1)).decode("cp949")
    except (ValueError, UnicodeDecodeError):
        return ""


def _identity(server, entity_id, details):
    account = ""
    key = ""
    if entity_id is not None:
        lock = getattr(server, "ctl_lock", None)
        if lock is None:
            raise ValueError("server.ctl_lock is required")
        with lock:
            for meta in getattr(server, "client_meta", {}).values():
                if int(meta.get("entity_id") or 0) != int(entity_id):
                    continue
                state = meta.get("proto_state") or {}
                account = str(meta.get("account") or state.get("account_name") or "").strip()
                raw = state.get("account_raw")
                if not account and isinstance(raw, (bytes, bytearray)):
                    account = bytes(raw).split(b"\0", 1)[0].decode("cp949", "replace").strip()
                key = str(state.get("selected_character_key") or "")
                break
    # Admin mutations have no player connection. Their target is an explicit
    # canonical character key, never a credential or arbitrary filesystem path.
    if not key and isinstance(details.get("key"), str) and _KEY_RE.fullmatch(details["key"]):
        key = details["key"]
    if not account and key:
        account = _account_from_key(key)
    return account[:64], key[:160]


def _kind_event(kind, details):
    if kind in ("login", "logout", "character_selected", "leave"):
        return "access", kind
    if kind in ("session", "access"):
        event = details.get("event")
        return "access", event if event in ("login", "logout", "character_selected", "leave") else "session"
    if kind in ("admin", "audit"):
        return "audit", str(details.get("event") or details.get("action") or "change")[:64]
    if kind == "chat":
        return "chat", "chat"
    raise ValueError("unsupported admin history event kind")


def record_event(server, kind, message, entity_id=None, details=None):
    """Append one authenticated semantic event and fsync it.

    Returns False when no authenticated account is known. Passwords, login
    payloads and packet bytes are never accepted through ``details``.
    """
    details = details if isinstance(details, dict) else {}
    normalized_kind, event = _kind_event(kind, details)
    account, key = _identity(server, entity_id, details)
    if not account:
        return False
    if normalized_kind == "chat" and not key:
        return False
    safe_details = {}
    for name, value in details.items():
        if name not in _DETAIL_KEYS or name in ("key", "account"):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe_details[name] = value[:240] if isinstance(value, str) else value
    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "kind": normalized_kind,
        "event": event,
        "account": account,
        "key": key or None,
        "entity_id": int(entity_id) if entity_id is not None else None,
        "message": str(message)[:2000],
        "details": safe_details,
    }
    line = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    path = journal_path(server)
    with _LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "ab") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
    return True


def _read_tail(server, max_bytes=_TAIL_BYTES):
    path = journal_path(server)
    if not os.path.isfile(path):
        return [], False, 0
    max_bytes = max(1024, min(int(max_bytes), _TAIL_BYTES))
    with _LOCK, open(path, "rb") as stream:
        size = stream.seek(0, os.SEEK_END)
        start = max(0, size - max_bytes)
        stream.seek(start)
        if start:
            stream.readline()  # discard a possibly incomplete first line
        data = stream.read()
    entries = []
    corrupt = 0
    for line in data.splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict) and item.get("kind") in ("access", "chat", "audit"):
                entries.append(item)
            else:
                corrupt += 1
        except (UnicodeDecodeError, json.JSONDecodeError):
            corrupt += 1
    return entries, bool(start), corrupt


def history_for_key(server, key, kind="access", limit=200, max_bytes=_TAIL_BYTES):
    """Return recent entries and an explicit completeness flag."""
    if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
        raise ValueError("invalid canonical character key")
    if kind not in ("access", "chat", "audit"):
        raise ValueError("kind must be access, chat or audit")
    account = _account_from_key(key)
    limit = max(1, min(int(limit), 500))
    records, truncated, corrupt = _read_tail(server, max_bytes)
    matched = [item for item in records if item.get("kind") == kind and (
        item.get("key") == key or (kind == "access" and not item.get("key")
                                    and item.get("account") == account)
    )]
    return {"entries": matched[-limit:][::-1], "truncated": truncated,
            "more_matching": len(matched) > limit, "corrupt_lines": corrupt}


def latest_login_by_account(server, max_bytes=_TAIL_BYTES):
    """Return login timestamps observed in the bounded journal tail."""
    records, truncated, corrupt = _read_tail(server, max_bytes)
    latest = {}
    for item in records:
        if item.get("kind") == "access" and item.get("event") == "login" and item.get("account"):
            latest[item["account"]] = item.get("at")
    return {"latest": latest, "truncated": truncated, "corrupt_lines": corrupt}


def recent_history(server, kind="all", query="", limit=200):
    """Private operator timeline across accounts, with explicit bounded coverage."""
    if kind not in ("all", "access", "chat", "audit"):
        raise ValueError("invalid history kind")
    if not isinstance(query, str) or len(query) > 200:
        raise ValueError("search must be at most 200 characters")
    query = query.strip().casefold()
    limit = max(1, min(int(limit), 500))
    records, truncated, corrupt = _read_tail(server)
    matched = [item for item in records if (kind == 'all' or item.get('kind') == kind)
               and (not query or query in (' '.join(str(item.get(field) or '')
                   for field in ('account', 'message', 'event'))).casefold())]
    return {'entries': matched[-limit:][::-1], 'truncated': truncated,
            'more_matching': len(matched) > limit, 'corrupt_lines': corrupt}
