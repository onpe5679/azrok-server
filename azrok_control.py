# -*- coding: utf-8 -*-
"""
Azrok Plaza - Server Control Panel

An in-process HTTP/JSON control surface over a running AzrokServer, plus a
self-contained web UI. Three consumers share one API:

    web page   - this module serves it at /
    azrok_ctl  - CLI client (azrok_ctl.py)
    agents     - call the CLI, or hit the endpoints directly

Design: docs/superpowers/specs/2026-07-17-server-control-panel-design.md

Stdlib only, on purpose: the rest of this project is ctypes + stdlib, and a debug
tool is not worth a dependency. The page polls; WebSocket from stdlib buys nothing.
"""
import hashlib
import json
import os
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from azrok_protocol_registry import legacy_contracts, registry_json
from azrok_private_access import PrivateAccountRegistry

DEFAULT_CONTROL_PORT = 9300
DEFAULT_CURSOR_LIMIT = 100
MAX_CURSOR_LIMIT = 200


# Operator-facing compatibility projection from the immutable typed registry.
PROTOCOL_CONTRACTS = legacy_contracts()


ACCESSORY_SLOT_CONTRACTS = (
    {'slot': 0, 'label': '머리위/후광 효과', 'range': '0..9', 'minimum': 0, 'maximum': 9},
    {'slot': 1, 'label': '얼굴/머리 착용', 'range': '0..6', 'minimum': 0, 'maximum': 6},
    {'slot': 2, 'label': '등 착용', 'range': '0..3', 'minimum': 0, 'maximum': 3},
    {'slot': 3, 'label': '탈것 (ride)', 'range': '0..7', 'minimum': 0, 'maximum': 7},
)

ACCESSORY_GROUPS = {
    1: {'label': 'gym', 'stats': '31..33'},
    2: {'label': 'playroom', 'stats': '34..36'},
    3: {'label': 'magic', 'stats': '37..39'},
    4: {'label': 'knowledge', 'stats': '30'},
    5: {'label': 'cook/extended skills', 'stats': '40..66'},
}

ACCESSORY_UNLOCK_ROWS = (
    {'resource_id': 20000, 'slot': 1, 'value': 0, 'group': 4, 'threshold': 50},
    {'resource_id': 20001, 'slot': 1, 'value': 1, 'group': 1, 'threshold': 200},
    {'resource_id': 20002, 'slot': 1, 'value': 2, 'group': 3, 'threshold': 100},
    {'resource_id': 20003, 'slot': 1, 'value': 3, 'group': 2, 'threshold': 50},
    {'resource_id': 20004, 'slot': 1, 'value': 4, 'group': 4, 'threshold': 200, 'evolution_min': 3},
    {'resource_id': 30000, 'slot': 2, 'value': 0, 'group': 4, 'threshold': 100},
    {'resource_id': 30001, 'slot': 2, 'value': 1, 'group': 5, 'threshold': 200},
    {'resource_id': 30002, 'slot': 2, 'value': 2, 'group': 3, 'threshold': 150},
    {'resource_id': 40000, 'slot': 3, 'value': 0, 'group': 2, 'threshold': 150},
)


def _normalize_accessory_slots(values):
    if not isinstance(values, (list, tuple)) or len(values) != 4:
        return None
    try:
        slots = [int(value) for value in values]
    except (TypeError, ValueError):
        return None
    for meta, value in zip(ACCESSORY_SLOT_CONTRACTS, slots):
        if value != 0xFF and not meta['minimum'] <= value <= meta['maximum']:
            return None
    return slots


def _decode_accessory_slots_from_hex(payload_hex, offset):
    try:
        payload = bytes.fromhex(payload_hex or '')
    except (TypeError, ValueError):
        return None
    if len(payload) < offset + 4:
        return None
    return _normalize_accessory_slots(list(payload[offset:offset + 4]))


def _accessory_packet_view(packets, target_entity_id=None):
    """Decode wire-proven accessory fields for one recipient/client.

    ``target_entity_id`` is optional for compatibility with offline capture
    callers.  The live control snapshot supplies it so recipient-local actor
    id 1 and remote actor namespaces from simultaneous clients never mix.
    """
    self_slots = None
    self_seq = None
    self_baseline_seq = None
    self_update_seq = None
    self_source = None
    remote = {}
    c2s_commits = []
    s2c_updates = []
    for packet in packets:
        if target_entity_id is not None:
            try:
                packet_entity_id = int(packet.get('entity_id'))
            except (TypeError, ValueError):
                continue
            if packet_entity_id != int(target_entity_id):
                continue
        direction, opcode = packet.get('dir'), packet.get('opcode')
        payload_hex = packet.get('hex') or ''
        if direction == 'S->C' and opcode == '0x0007':
            decoded = _decode_accessory_slots_from_hex(payload_hex, 0x1D4)
            if decoded is not None:
                self_slots, self_seq = decoded, packet.get('seq')
                self_baseline_seq = self_seq
                self_update_seq = None
                self_source = 's2c_0007_baseline'
                packet.setdefault('decoded', {})['accessory_slots'] = decoded
                packet['decoded']['accessory_offset'] = '0x1D4'
        elif direction == 'S->C' and opcode == '0x0066':
            try:
                payload = bytes.fromhex(payload_hex)
            except (TypeError, ValueError):
                continue
            if payload and len(payload) % 0x1A == 0:
                records = []
                for offset in range(0, len(payload), 0x1A):
                    actor_id = int.from_bytes(payload[offset + 1:offset + 5], 'little')
                    slots = _normalize_accessory_slots(
                        list(payload[offset + 0x14:offset + 0x18])
                    )
                    if slots is not None:
                        remote[str(actor_id)] = slots
                        records.append({'actor_id': actor_id, 'accessory_slots': slots})
                packet.setdefault('decoded', {})['remote_accessories'] = records
        elif direction == 'S->C' and opcode == '0x0065':
            # The verified handler tears down the fixed/self actor and clears
            # the complete remote roster.  Self appearance is restored by its
            # own state path; only the remote projection is invalidated here.
            remote.clear()
            packet.setdefault('decoded', {})['remote_accessories_reset'] = True
        elif direction == 'S->C' and opcode == '0x0067':
            try:
                payload = bytes.fromhex(payload_hex)
            except (TypeError, ValueError):
                continue
            if len(payload) >= 4:
                actor_id = int.from_bytes(payload[:4], 'little')
                remote.pop(str(actor_id), None)
                packet.setdefault('decoded', {})['remote_accessory_removed_actor_id'] = actor_id
        elif direction == 'C->S' and opcode == '0x0018':
            try:
                payload = bytes.fromhex(payload_hex)
            except (TypeError, ValueError):
                continue
            if len(payload) == 3:
                packet.update({
                    'meaning': 'accessory set/clear commit',
                    'category': 'accessory', 'risk': 'normal',
                })
                action, slot, value = payload
                valid = action in (0, 1) and 0 <= slot <= 3
                effective = value if action == 0 else 0xFF
                if valid and action == 0:
                    valid = _normalize_accessory_slots([
                        effective if idx == slot else 0xFF for idx in range(4)
                    ]) is not None
                commit = {
                    'seq': packet.get('seq'), 'action': 'set' if action == 0 else 'clear' if action == 1 else 'invalid',
                    'action_code': action, 'slot': slot, 'value': value,
                    'effective_value': effective, 'valid_contract': valid,
                }
                c2s_commits.append(commit)
                packet.setdefault('decoded', {}).update(commit)
        elif direction == 'S->C' and opcode == '0x000C':
            try:
                payload = bytes.fromhex(payload_hex)
            except (TypeError, ValueError):
                continue
            if len(payload) == 7:
                packet.update({
                    'meaning': 'actor accessory set/clear update',
                    'category': 'accessory', 'risk': 'normal',
                })
                actor_id = int.from_bytes(payload[:4], 'little')
                clear_flag, slot, value = payload[4:]
                effective = value if clear_flag == 0 else 0xFF
                valid = 0 <= slot <= 3
                if valid and clear_flag == 0:
                    valid = _normalize_accessory_slots([
                        effective if idx == slot else 0xFF for idx in range(4)
                    ]) is not None
                update = {
                    'seq': packet.get('seq'), 'actor_id': actor_id,
                    'clear_flag': clear_flag, 'action': 'set' if clear_flag == 0 else 'clear',
                    'slot': slot, 'value': value, 'effective_value': effective,
                    'valid_contract': valid,
                }
                s2c_updates.append(update)
                packet.setdefault('decoded', {}).update(update)
                if valid and actor_id == 1 and self_slots is not None:
                    # S2C 0x000C is recipient-local: actor 1 is the client's
                    # fixed self actor, while peer recipients receive the
                    # server entity id.  Apply the ACK after the most recent
                    # S2C 0x0007 baseline without changing the canonical view.
                    self_slots[slot] = effective
                    self_seq = packet.get('seq')
                    self_update_seq = self_seq
                    self_source = 's2c_000c_delta'
                elif valid and str(actor_id) in remote:
                    remote[str(actor_id)][slot] = effective
    return {
        'slots': [dict(row) for row in ACCESSORY_SLOT_CONTRACTS],
        'empty_value': 0xFF,
        'current_self': self_slots,
        'current_self_packet_seq': self_seq,
        'current_self_baseline_seq': self_baseline_seq,
        'current_self_update_seq': self_update_seq,
        'current_self_source': self_source,
        'target_entity_id': target_entity_id,
        'remote_by_actor': remote,
        'recent_c2s_0018': c2s_commits[-8:],
        'recent_s2c_000c': s2c_updates[-8:],
        'ownership': 'stat-derived; no server inventory field required',
        'level_stat': {'stat_id': 1, 'meaning': 'level', 'status': 'VERIFIED'},
        'unlock_groups': {str(key): dict(value) for key, value in ACCESSORY_GROUPS.items()},
        'unlock_rows': [dict(row) for row in ACCESSORY_UNLOCK_ROWS],
        'unlock_validation': 'VERIFIED static table; ownership is derived from persisted stats',
    }


def _identity_key(proto):
    """Rebuild the current identity key without invoking server mutations."""
    account = proto.get('account_raw') or b''
    name = proto.get('char_name_raw') or b'Player'
    if isinstance(account, str):
        account = account.encode('cp949', errors='ignore')
    if isinstance(name, str):
        name = name.encode('cp949', errors='ignore')
    account = bytes(account).split(b'\0', 1)[0][:13]
    name = bytes(name).split(b'\0', 1)[0][:32] or b'Player'
    if not account:
        return name.hex()
    return f"a{account.hex()}_s{int(proto.get('character_slot', 0)) & 3}_c{name.hex()}"


def _binding_view(proto, state_store_dir):
    selected = proto.get('selected_character_key')
    current = _identity_key(proto)
    bound = bool(proto.get('client_0005_seen') and isinstance(selected, str)
                 and selected and selected == current)
    path = os.path.join(state_store_dir, f'{selected}_state_v1.json') if bound else None
    result = {
        'bound': bound,
        'selected_key': selected if isinstance(selected, str) else None,
        'current_key': current,
        'reason': None if bound else (
            'character selection/create has not established an immutable key'
            if not proto.get('client_0005_seen') else 'selected key does not match current identity'
        ),
        'canonical_path': path,
        'canonical_exists': bool(path and os.path.isfile(path)),
    }
    return result


def _canonical_readonly_summary(binding):
    """Read an existing canonical document; never create or migrate one."""
    path = binding.get('canonical_path')
    if not path or not os.path.isfile(path):
        return {'available': False, 'path': path}
    try:
        if os.path.getsize(path) > 1024 * 1024:
            raise ValueError('canonical document exceeds 1 MiB')
        with open(path, 'rb') as handle:
            raw = handle.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('canonical document exceeds 1 MiB')
        state = json.loads(raw.decode('utf-8'))
        inventories = {}
        for name, values in (state.get('inventory') or {}).items():
            if not isinstance(values, list):
                continue
            clean = [max(0, int(value)) for value in values]
            inventories[name] = {
                'slots': len(clean),
                'owned_slots': sum(1 for value in clean if value > 0),
                'quantity': sum(clean),
                'values': clean,
            }
        accessory_key = next((
            key for key in ('accessory_slots', 'accessories', 'appearance_slots')
            if key in state
        ), None)
        accessory_slots = _normalize_accessory_slots(
            state.get(accessory_key) if accessory_key else None
        )
        return {
            'available': True,
            'path': path,
            'schema': state.get('schema_version'),
            'revision': state.get('revision', 0),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'currency': int(state.get('currency', 0)),
            'inventory': inventories,
            'active_loadouts': state.get('active_loadouts') or {},
            'runtime_rows': len(state.get('runtime_rows') or []),
            'accessory_slots': accessory_slots,
            'accessory_source_key': accessory_key,
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {'available': False, 'path': path, 'error': str(exc)}


def build_control_snapshot(server):
    """Add read-only operator context without widening the game-server API."""
    snapshot = server.snapshot()
    state_dir = (snapshot.get('content') or {}).get('state_store_dir') or ''
    active_proto = getattr(server, '_active_proto_state')()
    binding = _binding_view(active_proto, state_dir)
    canonical = _canonical_readonly_summary(binding)
    packets = [
        {**packet, 'decoded': dict(packet.get('decoded') or {})}
        for packet in (snapshot.get('packets') or [])
    ]
    snapshot['packets'] = packets
    active_entity_id = (snapshot.get('content') or {}).get('active_entity_id')
    accessories = _accessory_packet_view(
        packets, target_entity_id=active_entity_id
    )
    accessories['canonical'] = canonical.get('accessory_slots')
    accessories['canonical_source_key'] = canonical.get('accessory_source_key')
    snapshot['operator'] = {
        'content_profile': (snapshot.get('content') or {}).get('content_profile'),
        'state_namespace': (snapshot.get('content') or {}).get('state_namespace'),
        'state_store_dir': state_dir,
        'binding': binding,
        'canonical': canonical,
        'accessories': accessories,
        'mutation_journal': snapshot.get('mutation_journal') or {},
        'transactions': list(reversed(snapshot.get('transactions') or []))[:12],
        'recent_decisions': [
            event for event in reversed(snapshot.get('events') or [])
            if event.get('severity') in ('warn', 'error')
            or event.get('kind') in (
                'transaction', 'purchase', 'item_use', 'content_save',
                'state_save_reject',
            )
        ][:12],
    }
    # Per-client binding state is indispensable when a rejected second lease is
    # connected beside an authoritative owner.  Read only the already-owned
    # dictionaries under the control lock; never call canonical loaders here.
    by_entity = {}
    with server.ctl_lock:
        for conn, meta in server.client_meta.items():
            if conn not in server.connections:
                continue
            proto = meta.get('proto_state') or {}
            by_entity[meta.get('entity_id')] = _binding_view(proto, state_dir)
    for player in (snapshot.get('server') or {}).get('players') or []:
        player.setdefault('protocol', {})['binding'] = by_entity.get(player.get('entity_id'), {})
    return snapshot


def _cursor_query(query):
    """Parse a bounded, forward-only cursor query."""
    values = parse_qs(query, keep_blank_values=True)
    raw_after = (values.get('after_seq') or ['0'])[-1]
    raw_limit = (values.get('limit') or [str(DEFAULT_CURSOR_LIMIT)])[-1]
    try:
        after_seq = int(raw_after, 10)
        limit = int(raw_limit, 10)
    except (TypeError, ValueError) as exc:
        raise ValueError('after_seq and limit must be decimal integers') from exc
    if after_seq < 0:
        raise ValueError('after_seq must be non-negative')
    limit = max(1, min(MAX_CURSOR_LIMIT, limit))
    return after_seq, limit


def _cursor_page(items, after_seq=0, limit=DEFAULT_CURSOR_LIMIT):
    """Return one monotonic page and make ring loss explicit."""
    ordered = []
    previous = None
    for item in items:
        try:
            seq = int(item.get('seq'))
        except (AttributeError, TypeError, ValueError):
            continue
        if previous is not None and seq <= previous:
            raise ValueError('cursor source sequence is not strictly monotonic')
        previous = seq
        ordered.append(dict(item))

    oldest = int(ordered[0]['seq']) if ordered else None
    latest = int(ordered[-1]['seq']) if ordered else None
    gap = bool(oldest is not None and int(after_seq) < oldest - 1)
    available = [item for item in ordered if int(item['seq']) > int(after_seq)]
    page = available[:int(limit)]
    next_seq = int(page[-1]['seq']) if page else int(after_seq)
    return {
        'items': page,
        'after_seq': int(after_seq),
        'next_seq': next_seq,
        'oldest_seq': oldest,
        'latest_seq': latest,
        'dropped_before_seq': (oldest - 1) if oldest is not None else None,
        'gap': gap,
        'overflow': gap,
        'has_more': len(available) > len(page),
        'limit': int(limit),
        'sequence_monotonic': True,
    }


def _ring_items(server, name):
    """Copy one live ring under its owner lock without mutating state."""
    attrs = {
        'packets': ('packet_ring', server.ctl_lock),
        'events': ('event_ring', server.ctl_lock),
        'transactions': ('mutation_ring', getattr(server, 'mutation_lock', server.ctl_lock)),
    }
    if name == 'transactions' and hasattr(server, '_ensure_mutation_runtime'):
        server._ensure_mutation_runtime()
        attrs['transactions'] = ('mutation_ring', server.mutation_lock)
    attr, lock = attrs.get(name, ('event_ring', server.ctl_lock))
    with lock:
        ring = getattr(server, attr, None)
        if ring is not None:
            return [dict(item) for item in ring]
    snapshot = server.snapshot()
    return [dict(item) for item in (snapshot.get(name) or [])]


def build_control_overview(server):
    """Return the current operator summary without packet/event raw rings."""
    state = build_control_snapshot(server)
    operator = state.get('operator') or {}
    packet_cursor = _cursor_page(_ring_items(server, 'packets'), limit=1)
    event_cursor = _cursor_page(_ring_items(server, 'events'), limit=1)
    transaction_cursor = _cursor_page(_ring_items(server, 'transactions'), limit=1)
    packet_cursor.pop('items', None)
    event_cursor.pop('items', None)
    transaction_cursor.pop('items', None)
    return {
        'server': state.get('server') or {},
        'multiplayer': state.get('multiplayer') or {},
        'ox': state.get('ox') or {},
        'content': state.get('content') or {},
        'transition': state.get('transition') or {},
        'paused': bool(state.get('paused')),
        'pending': state.get('pending') or [],
        'operator': {
            key: operator.get(key) for key in (
                'content_profile', 'state_namespace', 'state_store_dir',
                'binding', 'canonical', 'accessories', 'transactions',
                'mutation_journal', 'recent_decisions',
            )
        },
        'cursor': {
            'packets': packet_cursor,
            'events': event_cursor,
            'transactions': transaction_cursor,
        },
    }


class _Handler(BaseHTTPRequestHandler):
    server_version = "AzrokControl/1.0"

    # The AzrokServer instance; set by ControlServer.
    azrok = None
    private_account_registry = None

    def log_message(self, fmt, *args):
        pass  # the game server owns the console; don't interleave HTTP noise

    # ── plumbing ──

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, text):
        body = text.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            n = int(self.headers.get('Content-Length') or 0)
        except ValueError as exc:
            raise ValueError('invalid Content-Length') from exc
        if n < 0 or n > 1024 * 1024:
            raise ValueError('JSON body must be at most 1048576 bytes')
        if not n:
            return {}
        body = json.loads(self.rfile.read(n).decode('utf-8'))
        if not isinstance(body, dict):
            raise ValueError('JSON body must be an object')
        return body

    # ── routes ──

    def do_GET(self):
        try:
            parsed = urlsplit(self.path)
            path = parsed.path
            if path.startswith('/api/admin/'):
                from azrok_admin_service import accounts, detail
                from azrok_admin_history import history_for_key, recent_history
                query = parse_qs(parsed.query)
                try:
                    if path == '/api/admin/accounts':
                        return self._send_json(accounts(self.azrok, self.private_account_registry))
                    key = query.get('key', [''])[0]
                    if path == '/api/admin/character':
                        return self._send_json(detail(self.azrok, key))
                    if path == '/api/admin/history':
                        if not key:
                            return self._send_json(recent_history(self.azrok,
                                query.get('kind', ['all'])[0], query.get('q', [''])[0]))
                        return self._send_json(history_for_key(self.azrok, key,
                            query.get('kind', ['access'])[0]))
                except (ValueError, TypeError) as exc:
                    return self._send_json({'error': str(exc)}, 400)
                except FileNotFoundError:
                    return self._send_json({'error': '캐릭터 저장을 찾을 수 없습니다.'}, 404)
            if path in ('/', '/index.html', '/admin'):
                from azrok_operator_page import PAGE as OPERATOR_PAGE
                return self._send_html(OPERATOR_PAGE)
            if path == '/debug':
                return self._send_html(PAGE)
            if path == '/api/state':
                return self._send_json(build_control_snapshot(self.azrok))
            if path == '/api/overview':
                return self._send_json(build_control_overview(self.azrok))
            if path in ('/api/packets', '/api/events', '/api/transactions'):
                try:
                    after_seq, limit = _cursor_query(parsed.query)
                    name = path.rsplit('/', 1)[-1]
                    page = _cursor_page(
                        _ring_items(self.azrok, name),
                        after_seq=after_seq, limit=limit,
                    )
                except ValueError as exc:
                    return self._send_json({'error': str(exc)}, 400)
                page['kind'] = name
                return self._send_json(page)
            if path == '/api/protocol':
                registry = registry_json()
                return self._send_json({
                    'contracts': PROTOCOL_CONTRACTS,
                    'registry_schema': registry['schema'],
                    'registry_spec_id': registry['spec_id'],
                    'accessory_slots': ACCESSORY_SLOT_CONTRACTS,
                    'accessory_policy': {
                        'empty_value': 0xFF,
                        'ownership': 'stat-derived; no server inventory field',
                        'c2s_0018_b0': 'VERIFIED: 0=set, 1=clear',
                        'self_restore': 'S2C 0x0007 payload +0x1D4',
                        'remote_restore': 'S2C 0x0066 record +0x14..0x17',
                        'remote_update': 'S2C 0x000C exact 7B; clear=0 set, nonzero -> 0xFF',
                        'level_stat': 'stat1 = level (VERIFIED)',
                        'unlock_groups': ACCESSORY_GROUPS,
                        'unlock_rows': ACCESSORY_UNLOCK_ROWS,
                    },
                })
            if path == '/api/protocol/specs':
                return self._send_json(registry_json())
            if path == '/api/macros':
                from azrok_server import MACROS
                return self._send_json({k: v['desc'] for k, v in MACROS.items()})
            if path == '/api/ox/status':
                return self._send_json(self.azrok.ox_snapshot())
            if path == '/api/ox/ranking':
                from azrok_ox_progression import ox_preservation_ranking
                return self._send_json({
                    'policy': 'preservation_win_count_v1',
                    'ranking': ox_preservation_ranking(self.azrok.state_store_dir),
                })
            if path == '/api/private-accounts':
                if self.private_account_registry is None:
                    return self._send_json({'error': 'private account registry unavailable'}, 503)
                return self._send_json(self.private_account_registry.admin_snapshot())
            self._send_json({'error': 'not found'}, 404)
        except Exception as e:
            traceback.print_exc()
            self._send_json({'error': str(e)}, 500)

    def do_POST(self):
        try:
            if self.path.startswith('/api/admin/'):
                # Browser requests must originate from this private console.
                origin = self.headers.get('Origin')
                if (origin and urlsplit(origin).netloc != self.headers.get('Host')) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                    return self._send_json({'error': '다른 사이트에서 요청할 수 없습니다.'}, 403)
                if self.headers.get_content_type() != 'application/json':
                    return self._send_json({'error': 'JSON 요청이 필요합니다.'}, 415)
            try:
                body = self._read_json()
            except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
                return self._send_json({'error': f'bad JSON body: {exc}'}, 400)
            srv = self.azrok

            if self.path == '/api/admin/character':
                from azrok_admin_service import mutate
                try:
                    ok, result = mutate(srv, body)
                    return self._send_json(result, 200 if ok else 409)
                except (ValueError, TypeError, KeyError) as exc:
                    return self._send_json({'error': str(exc)}, 400)
                except FileNotFoundError:
                    return self._send_json({'error': '캐릭터 저장을 찾을 수 없습니다.'}, 404)

            if self.path == '/api/send':
                opcode = body.get('opcode')
                if isinstance(opcode, str):
                    opcode = int(opcode, 16 if opcode.lower().startswith('0x') else 10)
                if opcode is None:
                    return self._send_json({'error': 'opcode required'}, 400)
                try:
                    payload = bytes.fromhex((body.get('payload') or '').replace(' ', ''))
                except ValueError as e:
                    return self._send_json({'error': f'bad payload hex: {e}'}, 400)
                target_entity = body.get('entity_id')
                ok, msg = srv.inject(opcode, payload, entity_id=target_entity)
                return self._send_json({'ok': ok, 'message': msg}, 200 if ok else 409)

            if self.path == '/api/chat/say':
                # Host-side IME bridge: BoxedWine has no IME, so Korean can
                # never be composed inside the game's own input field.  The
                # browser does have one, so the finished text comes in here and
                # goes out on the ordinary S2C 0x006A chat path.
                entity_id = body.get('entity_id')
                if entity_id is None:
                    return self._send_json({'error': 'entity_id required'}, 400)
                try:
                    entity_id = int(entity_id)
                except (TypeError, ValueError):
                    return self._send_json({'error': 'entity_id must be an integer'}, 400)
                ok, msg = srv.say_as_player(
                    entity_id, body.get('message'),
                    chat_type=int(body.get('chat_type') or 0),
                    flag=int(body.get('flag') or 0),
                )
                return self._send_json({'ok': ok, 'message': msg}, 200 if ok else 409)

            if self.path == '/api/private-accounts/recovery-code':
                if self.private_account_registry is None:
                    return self._send_json({'error': 'private account registry unavailable'}, 503)
                account_id = body.get('account')
                if not isinstance(account_id, str):
                    return self._send_json({'error': 'account is required'}, 400)
                try:
                    recovery_code = self.private_account_registry.admin_export_recovery_code(account_id)
                except ValueError as exc:
                    return self._send_json({'error': str(exc)}, 400)
                return self._send_json({
                    'ok': True,
                    'account': account_id,
                    'recovery_code': recovery_code,
                    'message': f'Recovery code issued for {account_id}',
                })

            if self.path == '/api/private-accounts/clear-bindings':
                if self.private_account_registry is None:
                    return self._send_json({'error': 'private account registry unavailable'}, 503)
                account_id = body.get('account')
                confirmation = body.get('confirmation')
                if not isinstance(account_id, str) or confirmation != f'RELEASE {account_id}':
                    return self._send_json({'error': 'explicit RELEASE <account> confirmation required'}, 400)
                try:
                    released = self.private_account_registry.admin_clear_bindings(account_id)
                except ValueError as exc:
                    return self._send_json({'error': str(exc)}, 400)
                return self._send_json({
                    'ok': True,
                    'account': account_id,
                    'released': released,
                    'message': f'Released {released} browser binding(s) from {account_id}',
                })

            if self.path == '/api/private-accounts/reset-state':
                account_id = body.get('account')
                confirmation = body.get('confirmation')
                if (not isinstance(account_id, str)
                        or confirmation != f'RESET {account_id}'):
                    return self._send_json({
                        'error': 'explicit RESET <account> confirmation required'
                    }, 400)
                ok, result = srv.reset_preserved_account_state(account_id)
                return self._send_json(
                    {'ok': ok, **result}, 200 if ok else 409
                )

            if self.path == '/api/macro':
                name = body.get('name')
                ok, msg = srv.run_macro(name)
                return self._send_json({'ok': ok, 'message': msg}, 200 if ok else 409)

            if self.path == '/api/pause':
                paused = srv.set_paused(bool(body.get('enabled')))
                return self._send_json({'ok': True, 'paused': paused})

            if self.path in ('/api/step', '/api/drop'):
                action = 'step' if self.path.endswith('step') else 'drop'
                ok, msg = srv.release_one(action)
                return self._send_json({'ok': ok, 'message': msg}, 200 if ok else 409)

            if self.path == '/api/protostate':
                key = body.get('key')
                if not key:
                    return self._send_json({'error': 'key required'}, 400)
                old = srv.set_proto_state(key, body.get('value'))
                return self._send_json({'ok': True, 'key': key, 'old': repr(old)})

            ox_routes = {
                '/api/ox/enter': 'enter',
                '/api/ox/prepare': 'prepare',
                '/api/ox/question': 'open',
                '/api/ox/tick': 'tick',
                '/api/ox/finish': 'finish',
                '/api/ox/counter': 'counter',
                '/api/ox/configure': 'configure',
                '/api/ox/automation': 'automation',
            }
            if self.path == '/api/ox' or self.path in ox_routes:
                action = ox_routes.get(
                    self.path, str(body.get('action') or '').lower()
                )
                room_id = body.get('room_id', 'default')
                if room_id is None:
                    room_id = 'default'
                if (not isinstance(room_id, str) or not room_id
                        or len(room_id) > 64
                        or any(ord(char) < 0x20 for char in room_id)):
                    return self._send_json(
                        {'error': 'room_id must be a non-empty string of at most 64 characters'},
                        400,
                    )
                if action == 'enter':
                    ok, msg = srv.request_ox_portal(entity_id=body.get('entity_id'))
                elif action == 'prepare':
                    ok, msg = srv.ox_prepare(room_id=room_id)
                elif action == 'open':
                    ok, msg = srv.ox_open_question(
                        room_id=room_id,
                        question_index=body.get('question_index'),
                        duration_ms=body.get('duration_ms', 16000),
                    )
                elif action == 'tick':
                    ok, msg = srv.ox_tick(room_id=room_id)
                elif action == 'finish':
                    ok, msg = srv.ox_finish(
                        room_id=room_id, exit_mode=body.get('exit_mode', 'cd')
                    )
                elif action == 'counter':
                    ok, msg = srv.ox_counter(
                        body.get('first'), body.get('second'), room_id=room_id
                    )
                elif action == 'configure':
                    ok, msg = srv.ox_configure(
                        side0_cells=body.get('side0_cells'),
                        side1_cells=body.get('side1_cells'),
                        questions=body.get('questions'),
                    )
                elif action == 'automation':
                    allowed = (
                        'enabled', 'admission_grace_ms', 'ready_delay_ms',
                        'question_duration_ms', 'result_hold_ms',
                        'exit_stall_ms', 'scheduler_poll_ms', 'max_rounds',
                    )
                    updates = {key: body[key] for key in allowed if key in body}
                    ok, msg = srv.ox_configure_automation(**updates)
                else:
                    return self._send_json({'error': 'unknown OX action'}, 400)
                return self._send_json(
                    {'ok': ok, 'message': msg, 'ox': srv.ox_snapshot()},
                    200 if ok else 409,
                )

            self._send_json({'error': 'not found'}, 404)
        except Exception as e:
            traceback.print_exc()
            self._send_json({'error': str(e)}, 500)


class ControlServer:
    """Runs the control API next to the game server, in the same process."""

    def __init__(self, azrok_server, port=DEFAULT_CONTROL_PORT, private_account_registry=None):
        self.azrok = azrok_server
        self.port = port
        if private_account_registry is not None and not isinstance(private_account_registry, PrivateAccountRegistry):
            raise TypeError('private_account_registry must be a PrivateAccountRegistry or None')
        self.private_account_registry = private_account_registry
        self.httpd = None
        self.thread = None

    def start(self):
        handler = type('Handler', (_Handler,), {
            'azrok': self.azrok,
            'private_account_registry': self.private_account_registry,
        })
        try:
            self.httpd = ThreadingHTTPServer(('127.0.0.1', self.port), handler)
        except OSError as e:
            # The debug UI must never stop the game from launching.
            print(f"  [CTL] control panel disabled - port {self.port} unavailable ({e})")
            return False
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        print(f"  [CTL] Control panel: http://127.0.0.1:{self.port}")
        return True

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


_LEGACY_PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Azrok Control</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; background:#14161a; color:#d6dae0;
         font:13px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace; }
  header { display:flex; align-items:center; gap:14px; padding:9px 14px;
           background:#1b1f25; border-bottom:1px solid #2b313a; position:sticky; top:0; z-index:5; }
  h1 { font-size:13px; margin:0; letter-spacing:.08em; color:#8fb3ff; font-weight:600; }
  .pill { padding:2px 8px; border-radius:10px; background:#252b33; font-size:11px; }
  .pill.on { background:#1d4a2b; color:#7fe0a0; }
  .pill.off { background:#4a1d1d; color:#f0a0a0; }
  .pill.warn { background:#4a3a1d; color:#f0d0a0; }
  main { display:grid; grid-template-columns: 320px 1fr 300px; gap:1px; background:#2b313a;
         height:calc(100vh - 41px); }
  section { background:#14161a; overflow:auto; padding:10px 12px; }
  h2 { font-size:11px; text-transform:uppercase; letter-spacing:.1em; color:#6b7686;
       margin:0 0 8px; font-weight:600; }
  h2:not(:first-child) { margin-top:18px; }
  table { border-collapse:collapse; width:100%; }
  td { padding:1px 6px 1px 0; vertical-align:top; }
  td.k { color:#6b7686; white-space:nowrap; }
  td.v { color:#d6dae0; word-break:break-all; }
  .t { color:#5a6472; }
  .cs { color:#7fe0a0; }  .sc { color:#8fb3ff; }
  .op { font-weight:600; }
  .hex { color:#8a93a0; word-break:break-all; }
  .man { color:#f0d0a0; }
  button { background:#252b33; color:#d6dae0; border:1px solid #39414d; border-radius:4px;
           padding:4px 9px; font:inherit; font-size:12px; cursor:pointer; }
  button:hover:not(:disabled) { background:#2f3742; border-color:#4a5563; }
  button:disabled { opacity:.4; cursor:not-allowed; }
  button.pri { background:#1d3a5c; border-color:#2d5a8c; color:#a8ccff; }
  button.dng { background:#4a1d1d; border-color:#6b2b2b; color:#f0a0a0; }
  input { background:#0e1013; color:#d6dae0; border:1px solid #39414d; border-radius:4px;
          padding:4px 7px; font:inherit; font-size:12px; }
  .row { display:flex; gap:5px; margin-bottom:6px; align-items:center; flex-wrap:wrap; }
  .macro { border:1px solid #2b313a; border-radius:5px; padding:8px; margin-bottom:8px; }
  .macro .desc { color:#6b7686; font-size:11px; margin:5px 0 7px; line-height:1.45; }
  #log div { padding:1px 0; border-bottom:1px solid #1c2026; }
  #msg { padding:5px 8px; border-radius:4px; font-size:12px; margin-bottom:8px; display:none; }
  #msg.ok { background:#1d4a2b; color:#9fe8b8; display:block; }
  #msg.err { background:#4a1d1d; color:#f0b0b0; display:block; }
  .pend { background:#2a2418; border:1px solid #4a3a1d; border-radius:4px; padding:6px;
          margin-bottom:6px; font-size:11px; }
  .dim { color:#5a6472; font-style:italic; }
</style></head><body>
<header>
  <h1>AZROK CONTROL</h1>
  <span class="pill" id="conn">-</span>
  <span class="pill" id="clients">-</span>
  <span class="pill" id="pause">-</span>
  <button id="btnPause">Pause</button>
  <button id="btnStep" disabled>Step</button>
  <button id="btnDrop" class="dng" disabled>Drop</button>
  <span class="pill" id="cap" title="capture file">-</span>
</header>
<main>
  <section>
    <h2>Watches <span class="dim" id="wnote"></span></h2>
    <table id="watches"></table>
    <h2>proto_state</h2>
    <table id="pstate"></table>
    <div class="row" style="margin-top:8px">
      <input id="psKey" placeholder="key" size="16">
      <input id="psVal" placeholder="value" size="8">
      <button id="btnPs">set</button>
    </div>
  </section>
  <section>
    <h2>Packets <span class="dim" id="pcount"></span></h2>
    <div id="log"></div>
  </section>
  <section>
    <div id="msg"></div>
    <h2>Send S&#8594;C</h2>
    <div class="row">
      <input id="op" placeholder="0x0016" size="7">
      <button id="btnSend" class="pri">send</button>
    </div>
    <div class="row"><input id="pay" placeholder="payload hex (optional)" style="width:100%"></div>
    <h2>Macros</h2>
    <div id="macros"></div>
    <h2>Pending</h2>
    <div id="pending"></div>
  </section>
</main>
<script>
const $ = s => document.querySelector(s);
let paused = false, lastSeq = -1;

function msg(t, ok) {
  const m = $('#msg'); m.textContent = t; m.className = ok ? 'ok' : 'err';
  clearTimeout(m._t); m._t = setTimeout(() => m.className = '', 4000);
}
async function post(path, body) {
  const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                              body: JSON.stringify(body || {})});
  const j = await r.json().catch(() => ({}));
  msg(j.message || j.error || (r.ok ? 'ok' : 'failed'), r.ok);
  refresh();
  return j;
}

function rowsFrom(obj) {
  return Object.entries(obj).map(([k, v]) =>
    `<tr><td class="k">${k}</td><td class="v">${v === null ? '<span class="dim">-</span>' : v}</td></tr>`
  ).join('');
}

function renderPackets(pkts) {
  if (pkts.length && pkts[pkts.length-1].seq === lastSeq) return;
  lastSeq = pkts.length ? pkts[pkts.length-1].seq : -1;
  const atBottom = $('#log').scrollTop + $('#log').clientHeight >= $('#log').scrollHeight - 40;
  $('#log').innerHTML = pkts.map(p => {
    const cls = p.dir === 'C->S' ? 'cs' : 'sc';
    const arrow = p.dir === 'C->S' ? 'C&#8594;S' : 'S&#8594;C';
    const tag = p.origin !== 'auto' ? ` <span class="man">[${p.origin}]</span>` : '';
    const hex = p.hex ? ` <span class="hex">${p.hex.slice(0,72)}${p.hex.length>72?'…':''}</span>` : '';
    return `<div><span class="t">${p.t}</span> <span class="${cls}">${arrow}</span>
            <span class="op">${p.opcode}</span> <span class="t">${p.len}B</span>${tag}${hex}</div>`;
  }).join('');
  if (atBottom) $('#log').scrollTop = $('#log').scrollHeight;
}

async function refresh() {
  let s;
  try { s = await (await fetch('/api/state')).json(); }
  catch { $('#conn').textContent = 'server down'; $('#conn').className = 'pill off'; return; }

  const listen = s.server.listen_address || `${s.server.bind_host || '127.0.0.1'}:${s.server.port}`;
  $('#conn').textContent = `${listen} up ${s.server.uptime}s`;
  $('#conn').className = 'pill on';
  $('#clients').textContent = s.server.clients ? `${s.server.clients} client` : 'no client';
  $('#clients').className = 'pill ' + (s.server.clients ? 'on' : 'off');
  paused = s.paused;
  $('#pause').textContent = paused ? 'PAUSED' : 'running';
  $('#pause').className = 'pill ' + (paused ? 'warn' : 'on');
  $('#btnPause').textContent = paused ? 'Resume' : 'Pause';
  $('#cap').textContent = (s.server.capture || '').split(/[\\/]/).pop();

  const w = s.watches || {};
  $('#wnote').textContent = w.note || '';
  $('#watches').innerHTML = rowsFrom(Object.fromEntries(
    Object.entries(w).filter(([k]) => k !== 'note')));
  $('#pstate').innerHTML = rowsFrom(s.proto_state || {});
  $('#pcount').textContent = `${s.packets.length}`;
  renderPackets(s.packets || []);

  const pend = s.pending || [];
  $('#btnStep').disabled = !pend.length;
  $('#btnDrop').disabled = !pend.length;
  $('#pending').innerHTML = pend.length
    ? pend.map(p => `<div class="pend">held [${p.origin}] <span class="hex">${p.hex.slice(0,60)}</span></div>`).join('')
    : '<div class="dim">nothing held</div>';
  $('#btnSend').disabled = !s.server.clients;
}

$('#btnPause').onclick = () => post('/api/pause', {enabled: !paused});
$('#btnStep').onclick  = () => post('/api/step');
$('#btnDrop').onclick  = () => post('/api/drop');
$('#btnSend').onclick  = () => post('/api/send', {opcode: $('#op').value.trim(),
                                                  payload: $('#pay').value.trim()});
$('#btnPs').onclick    = () => {
  let v = $('#psVal').value.trim();
  if (v === 'true') v = true; else if (v === 'false') v = false;
  else if (v !== '' && !isNaN(v)) v = Number(v);
  post('/api/protostate', {key: $('#psKey').value.trim(), value: v});
};
$('#pay').onkeydown = e => { if (e.key === 'Enter') $('#btnSend').click(); };

fetch('/api/macros').then(r => r.json()).then(ms => {
  $('#macros').innerHTML = Object.entries(ms).map(([n, d]) =>
    `<div class="macro"><button data-m="${n}" class="pri">run ${n}</button>
     <div class="desc">${d}</div></div>`).join('');
  document.querySelectorAll('[data-m]').forEach(b =>
    b.onclick = () => post('/api/macro', {name: b.dataset.m}));
});

refresh();
setInterval(refresh, 250);
</script></body></html>
"""

# The API above intentionally stays stable.  The dashboard derives its Korean
# interpretation from the existing snapshot so CLI clients and server packet
# semantics remain completely independent from presentation.
from azrok_control_page import PAGE

_SUPERSEDED_PAGE = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Azrok 실시간 제어실</title>
<style>
:root{color-scheme:dark;--bg:#0c1118;--p:#151d28;--p2:#1a2533;--line:#2a3748;--tx:#dce7f5;--mu:#8291a5;--b:#70a9ff;--g:#62d99b;--y:#efc36e;--r:#ff7f87}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:13px/1.45 Consolas,monospace}
header{height:52px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#111823;border-bottom:1px solid var(--line);box-shadow:0 4px 18px #0008;position:relative;z-index:2}
h1{font:700 14px system-ui;margin:0 9px 0 0;color:#b9d3ff}h2{font:700 11px system-ui;letter-spacing:.08em;text-transform:uppercase;color:#91a2b8;margin:0}h3{font:700 12px system-ui;margin:0 0 6px}
.spacer{flex:1}.pill{padding:3px 8px;border-radius:12px;background:#253244;color:#adbacb;font-size:11px;white-space:nowrap}.pill.on,.ok{background:#153d2d;color:#8ce7b6}.pill.off,.bad{background:#4a2026;color:#ffb1b6}.pill.warn,.warn{background:#49391c;color:#f4d18a}
button,input,select{font:inherit}button{background:#202b3a;color:var(--tx);border:1px solid #3a4a60;border-radius:5px;padding:5px 9px;cursor:pointer}button:hover:not(:disabled){background:#2b3a4d}button:disabled{opacity:.4}button.pri{background:#18375d;color:#b9d6ff;border-color:#315e90}button.risk,button.dng{background:#4a2026;color:#ffc0c5;border-color:#75343c}
input,select{background:#0a0f16;color:var(--tx);border:1px solid #34445a;border-radius:5px;padding:5px 7px;min-width:0}
main{height:calc(100vh - 52px);display:grid;grid-template-columns:minmax(310px,360px) minmax(480px,1fr) minmax(310px,370px);gap:1px;background:var(--line)}.pane{background:var(--bg);padding:11px;overflow:auto}.packetpane{display:flex;flex-direction:column;overflow:hidden}
.title{display:flex;align-items:center;justify-content:space-between;margin:2px 1px 8px}.card{background:linear-gradient(145deg,var(--p2),var(--p));border:1px solid var(--line);border-radius:8px;padding:10px;margin-bottom:9px;box-shadow:0 3px 12px #0003}
.scene{border-left:4px solid var(--b)}.scene.ok{border-left-color:var(--g)}.scene.warn{border-left-color:var(--y)}.scene.bad{border-left-color:var(--r)}.sceneName{font:750 21px system-ui;margin:2px 0}.sub{color:var(--mu);font:12px/1.5 system-ui}
.metrics{display:grid;grid-template-columns:1fr 1fr;gap:6px}.metric{background:#0e151e;border:1px solid #263246;border-radius:6px;padding:7px}.metric b{display:block;color:var(--mu);font-size:10px;font-weight:400}.metric span{font-weight:700}.check{display:flex;gap:7px;padding:3px 0}.check.pass i{color:var(--g)}.check.fail i{color:var(--r)}.check i{width:14px;text-align:center;font-style:normal;font-weight:bold}.admit{margin-top:8px;border-radius:6px;padding:8px;font-family:system-ui}
.player{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:7px 0;border-bottom:1px solid #243043}.player:last-child{border-bottom:0}.player b{font-size:12px}.player span{color:var(--mu);font-size:11px}.player .room{color:#9fc8ff;text-align:right}
.toolbar,.row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:6px 0}.grow input{flex:1}.toolbar input{width:105px}#log{flex:1;overflow:auto;min-height:160px;background:#080c12;border:1px solid #222e3d;border-radius:7px}
.pkt{display:grid;grid-template-columns:76px 48px 58px 42px minmax(120px,1fr);gap:5px;padding:4px 7px;border-bottom:1px solid #151e29}.pkt:hover{background:#111b28}.pkt.manual{background:#2d2618}.time,.dim{color:var(--mu)}.cs{color:var(--g)}.sc{color:var(--b)}.op{font-weight:bold}.hex{color:#77879b;word-break:break-all}.meaning{color:#bac8d9}.origin{color:var(--y)}.tag{display:inline-block;padding:0 5px;border-radius:8px;font-size:10px;background:#54242b;color:#ffb5ba;margin-left:4px}
.macro{border:1px solid var(--line);border-radius:7px;padding:8px;margin:7px 0;background:#101722}.macro .desc,.small{font:11px/1.45 system-ui;color:var(--mu)}.gloss{padding:7px 0;border-bottom:1px solid #243043}.gloss b{color:#a9caff}.gloss span{display:block;color:#98a8ba;margin-top:2px}.pend{padding:6px;background:#382d1b;border:1px solid #65502b;border-radius:5px;margin:5px 0}
table{border-collapse:collapse;width:100%}td{padding:2px 6px 2px 0;vertical-align:top}td.k{color:var(--mu);white-space:nowrap}td.v{word-break:break-all}details{margin-top:9px}summary{color:#8798ae;cursor:pointer}#msg{display:none;padding:8px;border-radius:6px;margin-bottom:8px;font-family:system-ui}#msg.ok,#msg.err{display:block}#msg.err{background:#4a2026;color:#ffc0c5}
@media(max-width:1050px){main{grid-template-columns:330px 1fr}.right{display:none}}@media(max-width:720px){header{height:auto;min-height:52px;flex-wrap:wrap;padding:8px}main{height:auto;display:block}.packetpane{height:70vh}}
</style></head><body>
<header><h1>AZROK 실시간 제어실</h1><span id="conn" class="pill">서버 확인 중</span><span id="clients" class="pill">게임 확인 중</span><span id="pause" class="pill">트래픽 확인 중</span><span class="spacer"></span><button id="btnAuto">자동 스크롤</button><button id="btnPause">패킷 일시정지</button><button id="btnStep" disabled>1개 통과</button><button id="btnDrop" class="dng" disabled>1개 폐기</button></header>
<main><section class="pane"><div class="title"><h2>현재 플레이어와 게임 상태</h2><span id="phase" class="pill">phase -</span></div><div id="scene" class="card scene"><div id="sceneName" class="sceneName">연결 대기</div><div id="sceneDesc" class="sub">게임 상태를 읽고 있습니다.</div></div><div class="card"><h3>Players / room membership</h3><div id="players"><span class="dim">연결된 플레이어 없음</span></div></div><div class="card"><div id="metrics" class="metrics"></div></div>
<div class="title"><h2>Protocol readiness</h2><span id="ready" class="pill">-</span></div><div class="card"><div id="checks"></div><div id="admit" class="admit"></div></div>
<details><summary>원시 watches / proto_state</summary><div class="card"><h3>Watches <span id="wnote" class="small"></span></h3><table id="watches"></table><h3 style="margin-top:12px">proto_state</h3><table id="pstate"></table><div class="row grow"><input id="psKey" placeholder="proto key"><input id="psVal" placeholder="value"><button id="btnPs">설정</button></div></div></details></section>
<section class="pane packetpane"><div class="title"><h2>실시간 패킷 <span id="pcount" class="dim"></span></h2><span id="follow" class="pill">최신 추적</span></div><div class="toolbar"><select id="dir"><option value="">양방향</option><option>C->S</option><option>S->C</option></select><input id="opf" placeholder="opcode 검색"><button id="clear">필터 지우기</button><span id="cap" class="small"></span></div><div id="log"></div></section>
<section class="pane right"><div id="msg"></div><div class="title"><h2>실험 제어</h2></div><div class="card"><h3>S→C 수동 송신 <span class="tag">주의</span></h3><div class="row"><input id="op" placeholder="0x0016" size="8"><button id="btnSend" class="pri">송신</button></div><div class="row grow"><input id="pay" placeholder="payload hex (선택)"></div></div><div class="card"><h3>매크로</h3><div id="macros"></div></div><div class="card"><h3>보류 중인 자동 패킷</h3><div id="pending"></div></div><div class="title"><h2>핵심 opcode 빠른 해석</h2></div><div id="gloss" class="card"></div></section></main>
<script>
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),num=v=>typeof v==='number'?v:(typeof v==='string'&&/^0x/i.test(v)?parseInt(v,16):Number(v||0));
let serverPaused=false,lastSeq=-1,state=null,macroReady=false,autoScroll=localStorage.getItem('azrokAutoScroll')!=='off';
const glossary=[['C→S 0x0016','heartbeat / 전환 calibration 요청. payload 01은 전환 샘플 요청입니다.'],['S→C 0x0004','calibration 샘플. packet-faithful 전환은 01 샘플 5회를 사용합니다.'],['S→C 0x000D','방 밖 전환 시작. room code 0x6E를 enqueue하며 child gate는 all-zero 또는 검증된 57 pan_create / 21 null fingerprint만 허용합니다.'],['C→S 0x0064','stage-0 bootstrap 보고. 그대로 echo하면 안 됩니다.'],['S→C 0x0064','authoritative self. entry_kind는 이미 로드된 공간에 self actor를 적용하며 목적지 selector가 아닙니다.'],['S→C 0x006E','OX 진입을 강제하는 ready commit. 지원 Plaza 경로에서는 보내지 않으며, both는 진단용입니다.'],['C→S 0x0019','PatHouse 문 클릭. legacy memory shortcut은 기본 봉인되며 env opt-in 진단에서만 활성화됩니다.'],['0x0003 / 0x0007','공간 root와 플레이어 상태 bootstrap입니다. 실제 목적 공간은 room-code loader chain이 정합니다.']];
$('#gloss').innerHTML=glossary.map(x=>`<div class="gloss"><b>${x[0]}</b><span>${x[1]}</span></div>`).join('');
glossary.push(['C→S 0x0065','로컬 방 전환 보고(<kind, direction, x, y>) · 서버 ACK가 아닙니다.']);
glossary.push(['C→S 0x0066 / 0x0067','이동·정지/방향 보고 · 멀티플레이 중계용입니다.']);
glossary.push(['C→S 0x006C','E/community 토글 보고 · 무응답이면 로컬 UI 경계를 먼저 확인합니다.']);
$('#gloss').innerHTML=glossary.map(x=>`<div class="gloss"><b>${x[0]}</b><span>${x[1]}</span></div>`).join('');
function msg(t,ok){let m=$('#msg');m.textContent=t;m.className=ok?'ok':'err';clearTimeout(m._t);m._t=setTimeout(()=>m.className='',5000)}
async function post(path,body){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})}),j=await r.json().catch(()=>({}));msg(j.message||j.error||(r.ok?'완료':'실패'),r.ok);refresh();return j}
function rows(o){return Object.entries(o).map(([k,v])=>`<tr><td class="k">${esc(k)}</td><td class="v">${v===null?'<span class="dim">-</span>':esc(v)}</td></tr>`).join('')}
function renderPlayers(ps){let el=$('#players');if(!el)return;if(!ps.length){el.innerHTML='<span class="dim">연결된 플레이어 없음</span>';return}el.innerHTML=ps.map(p=>{let xy=(p.x==null||p.y==null)?'좌표 -':`(${p.x}, ${p.y})`;return`<div class="player"><b>#${esc(p.entity_id)} ${esc(p.name||'Player')}</b><span class="room">${esc(p.room_name||'미확인')}</span><span>${esc(p.addr||'')} · ${xy}</span><span>last ${esc(p.last_opcode||'-')} · idle ${esc(p.idle_s??'-')}s</span></div>`}).join('')}
function meaning(p){let o=String(p.opcode).toUpperCase(),h=(p.hex||'').toLowerCase(),d=p.dir;if(o==='0X0016')return d==='C->S'?`heartbeat${h.startsWith('01')?' · 전환 요청 01':''}`:'heartbeat 응답';if(o==='0X0004'&&d==='S->C')return`calibration · kind=${(h.slice(0,2)||'--').toUpperCase()}`;if(o==='0X000D')return'room 0x6E enqueue · child 78-field fail-closed';if(o==='0X0019')return'PatHouse 문 클릭 · legacy shortcut 기본 봉인';if(o==='0X0003')return'공간 root staging';if(o==='0X0007')return d==='C->S'?'client 상태 보고':'player bootstrap';if(o==='0X0064'&&d==='C->S')return`로컬 bootstrap · ${h.slice(0,2)}`;if(o==='0X0064'){let k=h.slice(0,2).toUpperCase();return`authoritative self · entry ${k} (목적지 selector 아님)`}if(o==='0X0065'&&d==='C->S'){let k=parseInt(h.slice(0,2)||'00',16);let names={1:'pathouse',6:'playroom',7:'cook',8:'gym',9:'magic',10:'library',11:'shop',12:'ground'};return`로컬 방 전환 보고 · ${names[k]||`kind 0x${k.toString(16).padStart(2,'0')}`} (서버 ACK 아님)`}if(o==='0X0066'&&d==='C->S')return'이동 보고 · from/to 좌표';if(o==='0X0067'&&d==='C->S')return'정지/방향 보고';if(o==='0X006C'&&d==='C->S')return'E/community 토글 보고';if(o==='0X006E')return`ready commit · mode=${h.slice(0,2)} result=${h.slice(2,4)}`;if(o==='0X000C')return d==='C->S'?'selector snapshot (echo 금지)':'selector update';return''}
function packets(ps){let newest=ps.length?ps.at(-1).seq:-1;if(newest===lastSeq&&$('#log').children.length)return;lastSeq=newest;let d=$('#dir').value,q=$('#opf').value.trim().toUpperCase(),shown=ps.filter(p=>(!d||p.dir===d)&&(!q||String(p.opcode).toUpperCase().includes(q)));$('#pcount').textContent=`${shown.length}/${ps.length}`;$('#log').innerHTML=shown.map(p=>{let manual=p.origin!=='auto',risk=p.opcode==='0x0019';return`<div class="pkt ${manual?'manual':''}"><span class="time">${esc(p.t)}</span><span class="${p.dir==='C->S'?'cs':'sc'}">${esc(p.dir)}</span><span class="op">${esc(p.opcode)}</span><span class="dim">${esc(p.len)}B</span><span><span class="meaning">${esc(meaning(p))}</span>${manual?` <span class="origin">[${esc(p.origin)}]</span>`:''}${risk?'<span class="tag">위험</span>':''}<br><span class="hex">${esc((p.hex||'').slice(0,120))}${(p.hex||'').length>120?'…':''}</span></span></div>`}).join('')||'<div class="dim" style="padding:12px">조건에 맞는 패킷이 없습니다.</div>';if(autoScroll){let l=$('#log');l.scrollTop=l.scrollHeight}$('#follow').textContent=autoScroll?'최신 패킷 추적 중':'자동 추적 꺼짐';$('#follow').className='pill '+(autoScroll?'on':'warn')}
function sceneOf(w){if(!w.gm)return['프로세스 연결 대기','GameManager가 아직 준비되지 않았습니다.','bad'];let sc=num(w.scene_opcode),lo=num(w.logic_state),ph=num(w.phase_31792),f=num(w.flag_31c72);if(sc===111||lo===5)return['OX 퀴즈','0x006E ready commit이 0x6F/OXQuiz.wmb를 선택한 진단 경로입니다.','ok'];if(sc===110&&ph===4&&lo===1)return['Plaza','scene_opcode=110 / phase=4 · authoritative 0x0064만 응답한 지원 경로입니다.','ok'];if(lo===4)return['Plaza 후보','logic_state=4 · 화면과 패킷으로 추가 확인이 필요합니다.','warn'];if(sc===110)return[f?'Hansol stage-0 대기':'Hansol / Plaza 전환 후보','scene_opcode=110 · C→S 0x0064가 없으면 timing 정체입니다.','warn'];if(sc===100||lo===2)return['PatHouse','실내 플레이 상태 · 매크로 전 readiness를 확인하십시오.','ok'];if(ph)return['씬 전환 진행 중',`phase=${ph}, scene=${sc} · 목적지 미확정`,'warn'];return['초기화 / 미확인',`logic=${lo}, scene=${sc} · 후보를 확정하지 않습니다.`,'bad']}
function childPanelStatus(w){let st=String(w.transition_cleanup_children_state||'unreadable'),total=num(w.transition_cleanup_children_total),zero=num(w.transition_cleanup_children_zero),nonzero=num(w.transition_cleanup_children_nonzero),readable=num(w.transition_cleanup_children_readable_nonzero),invalid=Array.isArray(w.transition_cleanup_children_invalid)?w.transition_cleanup_children_invalid:[],unknown=Array.isArray(w.transition_cleanup_children_unknown)?w.transition_cleanup_children_unknown:[];if(w.transition_cleanup_children_ok===true&&st==='all_zero')return{ok:true,text:`${zero}/${total} null-safe`};if(w.transition_cleanup_children_ok===true&&st==='clean_pan_create_fingerprint')return{ok:true,text:`${nonzero} pan_create / ${zero} null · PANEL+BMAP readable`};if(st==='occupancy_mismatch'){let detail=unknown[0]?` · ${unknown[0]}`:'';return{ok:false,text:`차단 OCCUPANCY MISMATCH: ${nonzero} nonzero / ${zero} null${detail}`}}if(st==='invalid'||st==='unreadable_root'){let detail=invalid[0]?` · ${invalid[0]}`:'';return{ok:false,text:`차단 INVALID: ${st}, nonzero ${nonzero}, readable ${readable}${detail}`}}return{ok:false,text:`차단 ${st}: ${zero}/${total} zero, nonzero ${nonzero}`}}
function render(s){let w=s.watches||{},p=s.proto_state||{},[n,d,c]=sceneOf(w);$('#sceneName').textContent=n;$('#sceneDesc').textContent=d;$('#scene').className='card scene '+c;$('#phase').textContent=`phase ${w.phase_31792??'-'}`;$('#phase').className='pill '+(c==='ok'?'on':c);let vp=w.transition_vptrs_ok===true?'4/4 expected 일치':(w.transition_vptrs_ok===false?'헤더 불일치':'헤더 확인 중'),child=childPanelStatus(w);let ms=[['SELF ACTOR',w.self_actor_id||'없음'],['LOGIC STATE',w.logic_state??'-'],['SCENE OPCODE',w.scene_opcode??'-'],['PHASE 31792',w.phase_31792??'-'],['SCENE GUARD 31796',w.phase_31796??'-'],['READY 31C71',w.flag_31c71??'-'],['HANSOL 31C72',w.flag_31c72??'-'],['SCENE LATCH',w.scene_ready_latch??'-'],['NEXUS',w.nexus??'-'],['0x000D HEADERS',vp],['0x000D CHILD PANELS',child.text],['CALENDAR VPTR',w.vptr_popup_calendar??'-'],['STAGED SPACE ROOT',w.notice_path||'없음'],['NOTICE ARMED',`${w.notice_armed_d0??'-'}/${w.notice_armed_d1??'-'} · count ${w.notice_countdown_d7??'-'}`]];$('#metrics').innerHTML=ms.map(x=>`<div class="metric"><b>${x[0]}</b><span>${esc(x[1])}</span></div>`).join('');let cs=[[s.server.clients>0,'게임 클라이언트 연결'],[p.char_created===true,'캐릭터 bootstrap 완료'],[p.zone_request_seen===true&&num(p.zone_request_count)>=2,'client 0x0007 왕복 안정화'],[num(p.calib_0004_count)>=5,'bootstrap calibration 00 샘플 5회 완료'],[num(p.stable_heartbeat_count)>=2,'안정 heartbeat 2회 확인 (timing heuristic)'],[num(w.phase_31792)===2,'phase_31792가 PatHouse 준비값 2'],[num(w.scene_ready_latch)!==0,'scene ready latch가 활성'],[num(w.scene_opcode)===100,'scene_opcode 100 (PatHouse)'],[w.transition_vptrs_ok===true,'0x000D 객체 헤더 vtable 4개 expected 일치'],[child.ok,child.ok?`0x000D child panels ${child.text}`:`0x000D child panels ${child.text}`]];macroReady=cs.every(x=>x[0]);$('#checks').innerHTML=cs.map(x=>`<div class="check ${x[0]?'pass':'fail'}"><i>${x[0]?'✓':'×'}</i><span>${x[1]}</span></div>`).join('');let fail=cs.filter(x=>!x[0]).map(x=>x[1]);$('#ready').textContent=macroReady?`10조건 충족 · ${child.text}`:`${fail.length}개 조건 미충족`;$('#ready').className='pill '+(macroReady?'on':'off');$('#admit').className='admit '+(macroReady?'ok':'bad');$('#admit').innerHTML=macroReady?`<b>실행 가능</b> · header 4/4와 child panel ${esc(child.text)} 검사를 통과했습니다.`:`<b>지금 실행하면 위험합니다.</b><br>${fail.map(x=>'• '+esc(x)).join('<br>')}`;let hb=document.querySelector('[data-m="hansol"]');if(hb){hb.className=macroReady?'pri':'risk';hb.title=macroReady?`10조건 충족 · ${child.text}`:'조건 미충족'}$('#wnote').textContent=w.note||'';$('#watches').innerHTML=rows(Object.fromEntries(Object.entries(w).filter(x=>x[0]!=='note')));$('#pstate').innerHTML=rows(p)}
async function refresh(){let s;try{let r=await fetch('/api/state');if(!r.ok)throw 0;s=await r.json()}catch{$('#conn').textContent='제어 서버 응답 없음';$('#conn').className='pill off';return}state=s;$('#conn').textContent=`서버 :${s.server.port} · ${s.server.uptime}s`;$('#conn').className='pill on';$('#clients').textContent=s.server.clients?`게임 ${s.server.clients}개 연결`:'게임 연결 없음';$('#clients').className='pill '+(s.server.clients?'on':'off');serverPaused=s.paused;$('#pause').textContent=serverPaused?'자동 패킷 정지됨':'자동 패킷 흐름 정상';$('#pause').className='pill '+(serverPaused?'warn':'on');$('#btnPause').textContent=serverPaused?'패킷 재개':'패킷 일시정지';$('#cap').textContent=(s.server.capture||'').split(/[\\/]/).pop();render(s);renderPlayers(s.server.players||[]);packets(s.packets||[]);let pe=s.pending||[];$('#btnStep').disabled=!pe.length;$('#btnDrop').disabled=!pe.length;$('#pending').innerHTML=pe.length?pe.map(x=>`<div class="pend">보류 [${esc(x.origin)}] <span class="hex">${esc(x.hex.slice(0,70))}</span></div>`).join(''):'<span class="dim">보류 중인 패킷 없음</span>';$('#btnSend').disabled=!s.server.clients}
function autoBtn(){$('#btnAuto').textContent=`자동 스크롤: ${autoScroll?'켜짐':'꺼짐'}`;$('#btnAuto').className=autoScroll?'pri':''}$('#btnAuto').onclick=()=>{autoScroll=!autoScroll;localStorage.setItem('azrokAutoScroll',autoScroll?'on':'off');autoBtn();if(autoScroll){let l=$('#log');l.scrollTop=l.scrollHeight}};$('#btnPause').onclick=()=>post('/api/pause',{enabled:!serverPaused});$('#btnStep').onclick=()=>post('/api/step');$('#btnDrop').onclick=()=>post('/api/drop');$('#btnSend').onclick=()=>post('/api/send',{opcode:$('#op').value.trim(),payload:$('#pay').value.trim()});$('#btnPs').onclick=()=>{let v=$('#psVal').value.trim();if(v==='true')v=true;else if(v==='false')v=false;else if(v!==''&&!isNaN(v))v=Number(v);post('/api/protostate',{key:$('#psKey').value.trim(),value:v})};$('#pay').onkeydown=e=>{if(e.key==='Enter')$('#btnSend').click()};$('#dir').onchange=$('#opf').oninput=()=>{lastSeq=-2;packets(state?.packets||[])};$('#clear').onclick=()=>{$('#dir').value='';$('#opf').value='';lastSeq=-2;packets(state?.packets||[])};
fetch('/api/macros').then(r=>r.json()).then(ms=>{$('#macros').innerHTML=Object.entries(ms).map(([n,d])=>`<div class="macro"><button data-m="${esc(n)}" class="pri">${esc(n)} 실행</button><div class="desc">${esc(d)}</div></div>`).join('');document.querySelectorAll('[data-m]').forEach(b=>b.onclick=()=>{if(b.dataset.m==='hansol'&&!macroReady&&!confirm('Hansol readiness 조건이 충족되지 않았습니다. 정체 또는 충돌 위험이 있습니다. 그래도 실행하시겠습니까?'))return;post('/api/macro',{name:b.dataset.m})});if(state)render(state)});autoBtn();refresh();setInterval(refresh,250);
</script></body></html>"""
