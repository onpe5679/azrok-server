# -*- coding: utf-8 -*-
"""
Azrok Plaza - Combined IAT Hook + Local TCP Server
1. Hooks connect() via Entry Point Stomping to force 127.0.0.1:9000
2. Runs a local TCP server on port 9000 to accept the game's connection
3. Captures and displays all packets the game sends (protocol analysis)

Run: python azrok_server.py
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import struct
import os
import sys
import time
import socket
import threading
import select
import datetime
import uuid
from collections import deque
from contextlib import contextmanager

from azrok_capture import StructuredPacketCapture
from azrok_network import parse_private_ipv4_bind
from azrok_protocol_registry import find_spec
from azrok_ox_progression import record_ox_result, selected_ox_character_key, ox_info_projection

# How many recent packets the control panel keeps in memory for /api/state.
CTL_RING_SIZE = 400

# Internal grouping key for the client-local PatHouse bootstrap.  This is not
# sent on the wire: both clients have completed the same C2S 0x0007 bootstrap,
# so the server can safely rebuild the remote-actor roster without inventing a
# room-membership packet or waiting for a later door report.
LOCAL_PAT_HOUSE_ROOM_KIND = -1
# Internal-only room key for the mode-2 OX dispatcher.  It must never share
# the Plaza/state-1 actor relay: the same numeric opcodes have different
# receive handlers after CGameOXQuiz becomes active.
LOCAL_OX_ROOM_KIND = -2
DEFAULT_OX_ROOM_ID = 'default'
OX_PORTAL_C8_TTL_SECONDS = 30.0
# Original client movement timing is based on GetTickCount(), so the C2S
# 0x0066 duration is milliseconds.  S2C 0x0068 has no wire fields for the
# complete movement intent; relay a bounded-rate sequence of its existing
# six-dword position records instead.
PLAZA_MOVEMENT_RELAY_INTERVAL_MS = 50
# 'intent' = one walking record carrying the sender's own absolute arrival
# deadline (the original contract).  'interpolate' = repeated placement frames
# (smooth, but no walk state and no facing).  See doc 538.
PLAZA_MOVEMENT_RELAY_MODE = os.environ.get(
    'AZROK_PLAZA_MOVE_MODE', 'intent'
).strip().lower()
# Ceiling on the C2S 0x0066 duration the walking record is built from.  A
# deadline that is not a short distance in our own future renders as an
# instant teleport with no facing, so an implausible duration never becomes one.
PLAZA_MOVEMENT_MAX_DURATION_MS = 60000
OX_SIDE_CELLS_DEFAULT = {
    # Diagnostic geometry only.  Judgement uses C2S CA.side directly.
    0: frozenset((14, 15)),  # negative X / left
    1: frozenset((20, 21)),  # positive X / right
}
OX_SAMPLE_QUESTIONS = (
    # Preservation-safe, newly authored samples.  No original question text
    # is embedded in the server.
    {'text': '1 + 1 = 2', 'type': 0, 'correct_side': 0, 'stars': 1},
    {'text': '3 is an even number', 'type': 0, 'correct_side': 1, 'stars': 1},
)

# Automatic OX timing is a preservation-server policy, not a recovered
# original-server constant.  The wire boundaries are verified, while these
# delays remain deliberately configurable and are surfaced in the control
# snapshot as ``inferred_timing_policy``.
OX_AUTO_POLICY_DEFAULTS = {
    'enabled': True,
    'admission_mode': 'client_c8_only',
    'admission_grace_ms': 2000,
    'ready_delay_ms': 750,
    'question_duration_ms': 16000,
    'result_hold_ms': 7000,
    'exit_stall_ms': 12000,
    'scheduler_poll_ms': 50,
    # Zero means one pass through the configured preservation-safe bank.
    'max_rounds': 0,
}


def _ox_auto_policy_from_env():
    """Return bounded automatic-after-C8 policy values.

    No setting in this policy can emit the state-1 0x006E ready commit.  OX
    automation begins only after the original client has sent exact C2S C8.
    """
    policy = dict(OX_AUTO_POLICY_DEFAULTS)
    enabled = os.environ.get('AZROK_OX_AUTO', '1').strip().lower()
    policy['enabled'] = enabled not in ('0', 'false', 'no', 'off')
    bounds = {
        'admission_grace_ms': (0, 30000),
        'ready_delay_ms': (0, 30000),
        'question_duration_ms': (1000, 300000),
        'result_hold_ms': (0, 30000),
        'exit_stall_ms': (1000, 120000),
        'scheduler_poll_ms': (10, 1000),
        'max_rounds': (0, 1000),
    }
    env_names = {
        key: 'AZROK_OX_' + key.upper()
        for key in bounds
    }
    for key, (minimum, maximum) in bounds.items():
        raw = os.environ.get(env_names[key])
        if raw is None:
            continue
        try:
            value = int(raw, 0)
        except ValueError:
            continue
        if minimum <= value <= maximum:
            policy[key] = value
    return policy
PATHOUSE_ROOM_KINDS = frozenset((LOCAL_PAT_HOUSE_ROOM_KIND, 0x01))
# Direction-specific C→S 0x0065 observations use kind 0x1B in Plaza.  The
# C→S 0x0064 Hansol bootstrap is the first packet-faithful Plaza boundary we
# can observe even when no movement report has been emitted yet.
PLAZA_ROOM_KIND = 0x1B

# C→S 0x0065 reports a wire kind chosen by FUN_006122C0.  It is not the
# Plaza portal selector: selector 1 (Playroom), for example, reports kind 6.
LOCAL_ROOM_NAMES_BY_WIRE_KIND = {
    0x01: 'pathouse',
    0x06: 'playroom',
    0x08: 'gym',
    0x09: 'magic',
    0x07: 'cook',
    0x0B: 'shop',
    0x0A: 'library',
    0x0C: 'ground',
}

# The local facility screens do not emit a dedicated exit opcode.  Live
# captures from Gym, Cook and Library show that pressing their OutMap exit
# button changes the ordinary C2S 0x0016 heartbeat payload from 00 to 01.  The
# original server answers that transition request with S2C 0x000D[00], after
# which the client requests five kind-01 calibration samples and naturally
# emits C2S 0x0064 for Plaza.  PatHouse is deliberately excluded because it
# has its own exact C2S 0x0019 exit request.
LOCAL_FACILITY_ROOM_KINDS = frozenset(
    kind for kind in LOCAL_ROOM_NAMES_BY_WIRE_KIND
    if kind not in PATHOUSE_ROOM_KINDS
)


def world_grid_cell(x, y):
    """Return the client's 6x6 world cell using C-style signed division."""
    def trunc_div(value, divisor):
        return value // divisor if value >= 0 else -((-value) // divisor)
    return trunc_div(int(y) + 9000, 3000) + trunc_div(int(x) + 9000, 3000) * 6


def decode_c2s_0065(payload):
    """Decode <kind,direction,signed x,signed y> from a room-entry report."""
    if len(payload) < 10:
        raise ValueError('C2S 0x0065 payload must be at least 10 bytes')
    return struct.unpack_from('<BBii', payload, 0)


def decode_c2s_0066(payload):
    """Decode exact movement intent: cell, endpoints, duration, path flag."""
    if len(payload) != 22:
        raise ValueError('C2S 0x0066 payload must be exactly 22 bytes')
    return struct.unpack('<BiiiiiB', payload)


def decode_c2s_0067(payload):
    """Decode exact arrival commit: cell, signed position, action, angle."""
    if len(payload) != 15:
        raise ValueError('C2S 0x0067 payload must be exactly 15 bytes')
    return struct.unpack('<BiiIH', payload)


def decode_c2s_ox_enter_00c8(payload):
    """Validate the exact empty mode-2 OX scene-ready request."""
    if len(payload) != 0:
        raise ValueError('C2S 0x00C8 OX enter payload must be exactly 0 bytes')
    return True


def decode_c2s_ox_leave_00c9(payload):
    """Decode the exact one-byte OX teardown/leave notification."""
    if len(payload) != 1:
        raise ValueError('C2S 0x00C9 OX leave payload must be exactly 1 byte')
    return payload[0]


def decode_c2s_ox_answer_00ca(payload):
    """Decode the exact dedicated OX answer/movement record.

    Layout is byte-compatible in size with C2S 0066, but byte 0 is the OX
    side code (0=negative-X/left, 1=positive-X/right), never a world cell.
    The last dword is a duration for active movement and a synchronized tick
    value for the client-generated timeout submission.
    """
    if len(payload) != 22:
        raise ValueError('C2S 0x00CA OX answer payload must be exactly 22 bytes')
    side, cur_x, cur_y, dst_x, dst_y, timing, timeout_flag = struct.unpack(
        '<BiiiiiB', payload
    )
    if side not in (0, 1):
        raise ValueError('C2S 0x00CA OX side must be 0 or 1')
    if timeout_flag not in (0, 1):
        raise ValueError('C2S 0x00CA OX timeout flag must be 0 or 1')
    if timeout_flag == 1 and (cur_x != dst_x or cur_y != dst_y):
        raise ValueError('C2S 0x00CA timeout submission must have current=destination')
    return {
        'side': side,
        'current_x': cur_x,
        'current_y': cur_y,
        'destination_x': dst_x,
        'destination_y': dst_y,
        'timing': timing,
        'timeout': bool(timeout_flag),
    }


def build_s2c_ox_enter_00c8(result=0, level_marker=0, ready_ms=0, x=0, y=0):
    """Build the exact 14-byte OX admission record.

    ``result=0`` is the only admission path.  Ghidra shows that non-zero
    exits immediately.  A non-zero ``ready_ms`` invokes an additional UI
    path whose server meaning is not known, so the supported safe default is
    zero.  Countdown (CC) and question (CE) are explicit later triggers.
    """
    if result not in (0, 1):
        raise ValueError('OX enter result must be 0 or 1')
    if not 0 <= int(level_marker) <= 0xFF:
        raise ValueError('OX level marker must fit u8')
    if not 0 <= int(ready_ms) <= 0xFFFFFFFF:
        raise ValueError('OX ready value must fit u32')
    if not -0x80000000 <= int(x) <= 0x7FFFFFFF:
        raise ValueError('OX x must fit i32')
    if not -0x80000000 <= int(y) <= 0x7FFFFFFF:
        raise ValueError('OX y must fit i32')
    return struct.pack('<BBIii', result, int(level_marker), int(ready_ms), int(x), int(y))


def build_s2c_ox_remote_00c9(actor_id, char_type, name_raw, x, y,
                              level_marker=0, descriptor_1=0,
                              appearance=None):
    """Build one exact 32-byte mode-2 remote actor record."""
    if not 0 < int(actor_id) <= 0xFFFFFFFF:
        raise ValueError('OX remote actor id must be a non-zero u32')
    for label, value in (
        ('level marker', level_marker), ('character type', char_type),
        ('descriptor byte 1', descriptor_1),
    ):
        if not 0 <= int(value) <= 0xFF:
            raise ValueError(f'OX {label} must fit u8')
    if isinstance(name_raw, str):
        name_raw = name_raw.encode('cp949', errors='strict')
    safe_name = bytes(name_raw or b'Player').split(b'\x00', 1)[0]
    if len(safe_name) > 12:
        raise ValueError('OX actor name must fit the 13-byte NUL slot')
    if appearance is None:
        appearance = bytes((int(char_type), 0, 0, 0))
    appearance = bytes(appearance)
    if len(appearance) != 4:
        raise ValueError('OX actor appearance must be exactly 4 bytes')
    if not -0x80000000 <= int(x) <= 0x7FFFFFFF:
        raise ValueError('OX actor x must fit i32')
    if not -0x80000000 <= int(y) <= 0x7FFFFFFF:
        raise ValueError('OX actor y must fit i32')
    record = bytearray(32)
    record[0] = int(level_marker)
    struct.pack_into('<I', record, 1, int(actor_id))
    record[5] = int(char_type)
    record[6] = int(descriptor_1)
    record[7:7 + len(safe_name)] = safe_name
    record[7 + len(safe_name)] = 0
    record[0x14:0x18] = appearance
    struct.pack_into('<ii', record, 0x18, int(x), int(y))
    return bytes(record)


def build_s2c_ox_actor_ids(opcode, actor_ids):
    """Build CA/CB/CD actor-id arrays with opcode-specific exact sizes."""
    ids = [int(value) for value in actor_ids]
    if opcode == 0x00CA and len(ids) != 1:
        raise ValueError('S2C 0x00CA requires exactly one actor id')
    if opcode not in (0x00CA, 0x00CB, 0x00CD):
        raise ValueError('OX actor-id builder supports only CA/CB/CD')
    if len(set(ids)) != len(ids):
        raise ValueError('OX actor-id list must not contain duplicates')
    if any(value <= 0 or value > 0xFFFFFFFF for value in ids):
        raise ValueError('OX actor ids must be non-zero u32 values')
    return b''.join(struct.pack('<I', value) for value in ids)


def build_s2c_ox_question_00ce(text, question_type, correct_side, stars):
    """Build the exact 131-byte question record, failing closed.

    The client has explicit prefix branches for types 1..3 and a safe default
    branch for 0; the preservation server intentionally accepts only 0..3.
    Its star widget owns exactly three pointers, so values above three would
    make FUN_005F62A0 index out of bounds.
    """
    if isinstance(text, str):
        text = text.encode('cp949', errors='strict')
    text = bytes(text)
    if b'\x00' in text or len(text) > 127:
        raise ValueError('OX question must be at most 127 non-NUL CP949 bytes')
    if int(question_type) not in (0, 1, 2, 3):
        raise ValueError('OX question type must be 0..3')
    if int(correct_side) not in (0, 1):
        raise ValueError('OX correct side must be 0 or 1')
    if not 0 <= int(stars) <= 3:
        raise ValueError('OX stars must be 0..3')
    payload = bytearray(0x83)
    payload[:len(text)] = text
    payload[len(text)] = 0
    payload[0x80] = int(question_type)
    payload[0x81] = int(correct_side)
    payload[0x82] = int(stars)
    return bytes(payload)


def validate_s2c_ox_payload(opcode, payload):
    """Validate every implemented mode-2 payload before transmission."""
    payload = bytes(payload)
    exact = {
        0x00C8: 14, 0x00CA: 4, 0x00CC: 0, 0x00CE: 0x83,
        0x00D0: 24, 0x00D2: 0, 0x00D3: 4, 0x00D4: 0,
    }
    if opcode in exact and len(payload) != exact[opcode]:
        raise ValueError(f'S2C 0x{opcode:04X} payload must be exactly {exact[opcode]} bytes')
    if opcode == 0x00C9 and (not payload or len(payload) % 32):
        raise ValueError('S2C 0x00C9 payload must be a non-empty multiple of 32 bytes')
    if opcode in (0x00CB, 0x00CD) and len(payload) % 4:
        raise ValueError(f'S2C 0x{opcode:04X} payload must be a multiple of 4 bytes')
    if opcode not in exact and opcode not in (0x00C9, 0x00CB, 0x00CD):
        raise ValueError(f'unsupported OX S2C opcode 0x{opcode:04X}')
    return payload


def ox_serialized(method):
    """Serialize one complete OX state transition, including its wire emits.

    ``ox_lock`` protects the room dictionaries, but a transition also updates
    client metadata and emits one or more ordered packets after releasing that
    lock.  A separate re-entrant operation lock keeps control requests and
    socket lifecycle events from interleaving those multi-step boundaries.
    """
    def wrapped(self, *args, **kwargs):
        self._ensure_ox_runtime()
        with self.ox_action_lock:
            return method(self, *args, **kwargs)
    wrapped.__name__ = method.__name__
    wrapped.__doc__ = method.__doc__
    return wrapped


def decode_c2s_login_0000(payload):
    """Decode the exact mode-0 login request: type + user[13] + pass[92]."""
    if len(payload) != 0x6A:
        raise ValueError('C2S 0x0000 login payload must be exactly 106 bytes')
    login_type = payload[0]
    user_raw = bytes(payload[1:14]).split(b'\x00', 1)[0]
    password_raw = bytes(payload[14:106]).split(b'\x00', 1)[0]
    return login_type, user_raw, password_raw


def decode_c2s_0068_chat(payload):
    """Decode the direction-specific C2S 0x0068 chat record.

    Layout: type, flag, target[13], NUL, messageLength, CP949 message+NUL.
    The client caps the complete payload below 0xC8 bytes.
    """
    if len(payload) < 0x12 or len(payload) >= 0xC8:
        raise ValueError('C2S 0x0068 chat payload must be 18..199 bytes')
    message_length = payload[0x10]
    if message_length < 1 or len(payload) != 0x11 + message_length:
        raise ValueError('C2S 0x0068 chat message length is inconsistent')
    if payload[0x0F] != 0 or payload[-1] != 0:
        raise ValueError('C2S 0x0068 chat strings must be NUL terminated')
    target_raw = bytes(payload[0x02:0x0F]).split(b'\x00', 1)[0]
    message_raw = bytes(payload[0x11:-1])
    return {
        'type': payload[0],
        'flag': payload[1],
        'target_raw': target_raw,
        'message_raw': message_raw,
    }


def decode_c2s_006c_community(payload):
    """Decode the C2S 0x006C target actor id (1 = the sender's own avatar)."""
    if len(payload) != 4:
        raise ValueError('C2S 0x006C community payload must be exactly 4 bytes')
    return struct.unpack('<I', payload)[0]


def decode_c2s_0018_accessory(payload):
    """Decode exact accessory update ``[clear_flag, slot, value]``."""
    if len(payload) != 3:
        raise ValueError('C2S 0x0018 accessory payload must be exactly 3 bytes')
    clear_flag, slot, value = payload
    if clear_flag not in (0, 1):
        raise ValueError('C2S 0x0018 accessory clear flag must be 0 or 1')
    if slot >= 4:
        raise ValueError('C2S 0x0018 accessory slot is out of range')
    if clear_flag == 0 and value > ACCESSORY_SLOT_MAX_VALUES[slot]:
        raise ValueError('C2S 0x0018 accessory value is out of range')
    return clear_flag, slot, value


def build_s2c_accessory_000c(actor_id, clear_flag, slot, value):
    """Build exact S2C 0x000C actor appearance update (7 bytes)."""
    actor_id = int(actor_id)
    clear_flag = int(clear_flag)
    slot = int(slot)
    value = int(value)
    if not 0 < actor_id <= 0xFFFFFFFF:
        raise ValueError('S2C 0x000C actor id must be a non-zero u32')
    if clear_flag not in (0, 1):
        raise ValueError('S2C 0x000C clear flag must be 0 or 1')
    if not 0 <= slot < 4:
        raise ValueError('S2C 0x000C accessory slot is out of range')
    if not 0 <= value <= 0xFF:
        raise ValueError('S2C 0x000C accessory value must fit u8')
    return struct.pack('<IBBB', actor_id, clear_flag, slot, value)


def decode_c2s_purchase_0013(payload):
    """Decode the fixed 45-byte shop commit record.

    Only ``count`` item slots are initialized by the client.  The remaining
    bytes are stack residue and must never be interpreted as item ids.
    """
    if len(payload) != 0x2D:
        raise ValueError('C2S 0x0013 purchase payload must be exactly 45 bytes')
    count = payload[0]
    if count < 1 or count > 20:
        raise ValueError('C2S 0x0013 item count must be 1..20')
    claimed_total = struct.unpack_from('<I', payload, 1)[0]
    item_ids = list(struct.unpack_from(f'<{count}H', payload, 5))
    return count, claimed_total, item_ids


def decode_c2s_item_consume_0014(payload):
    """Decode the little-endian item-id witness emitted after a decrement."""
    if len(payload) != 2:
        raise ValueError('C2S 0x0014 item consume payload must be exactly 2 bytes')
    return struct.unpack('<H', payload)[0]


def decode_c2s_inventory_snapshot(opcode, payload):
    """Decode the exact client-owned quantity snapshots 0008/0009/000A."""
    payload = bytes(payload)
    if opcode == 0x0008:
        if len(payload) != 41:
            raise ValueError('C2S 0x0008 inventory snapshot must be exactly 41 bytes')
        if any(payload[33:38]):
            raise ValueError('C2S 0x0008 food padding bytes 33..37 must be zero')
        return {'food': list(payload[:38]), 'ingredient': list(payload[38:41])}
    if opcode == 0x0009:
        if len(payload) != 10:
            raise ValueError('C2S 0x0009 toy snapshot must be exactly 10 bytes')
        return {'toy': list(payload)}
    if opcode == 0x000A:
        if len(payload) != 8:
            raise ValueError('C2S 0x000A gym snapshot must be exactly 8 bytes')
        return {'gym': list(payload)}
    raise ValueError(f'unsupported inventory snapshot opcode 0x{opcode:04X}')


def decode_c2s_growth_route_0010(payload):
    """Decode [kind-3 aux, flag], where flag 0 proposes and 1 completes."""
    if len(payload) != 2:
        raise ValueError('C2S 0x0010 growth route must be exactly 2 bytes')
    aux, flag = payload
    if aux > 6:
        raise ValueError('C2S 0x0010 growth aux must be 0..6')
    if flag not in (0, 1):
        raise ValueError('C2S 0x0010 growth flag must be 0 or 1')
    return aux, flag


def decode_c2s_runtime_rows_0011(payload):
    """Decode 10*u16 kind, 10*u16 aux, then 10*u32 value."""
    if len(payload) != 80:
        raise ValueError('C2S 0x0011 runtime-row snapshot must be exactly 80 bytes')
    kinds = struct.unpack_from('<10H', payload, 0)
    auxes = struct.unpack_from('<10H', payload, 20)
    values = struct.unpack_from('<10I', payload, 40)
    rows = [
        {'kind': kinds[index], 'aux': auxes[index], 'value': values[index]}
        for index in range(10)
    ]
    # Natural quest completion clears only the kind word.  The client leaves
    # the previous aux/value bytes stale (food1001 live: FF/1001/26073020), so
    # kind==0x00FF is the sole empty-row authority.  Canonicalize those stale
    # tails before comparing or persisting the projection.
    rows = [
        {'kind': 0xFF, 'aux': 0xFF, 'value': 0}
        if row['kind'] == 0xFF else row
        for row in rows
    ]
    if sum(row['kind'] == 3 for row in rows) > 1:
        raise ValueError('C2S 0x0011 contains duplicate active kind-3 rows')
    return rows


def decode_c2s_quest_reward_0012(payload):
    """Decode C2G_QUEST_REQ reward fields: amount:u32 + channel:u8."""
    if len(payload) != 5:
        raise ValueError('C2S 0x0012 quest reward must be exactly 5 bytes')
    amount, reward_channel = struct.unpack('<IB', payload)
    if amount <= 0:
        raise ValueError('C2S 0x0012 quest reward amount must be positive')
    # All three verified quest reward producers pass the literal channel 2.
    # It is not a second-currency selector: the recovered original symbols
    # expose FunCorn as the sole balance and G2C_PRICE_ACK as a price catalogue.
    if reward_channel != 2:
        raise ValueError('C2S 0x0012 quest reward channel must be 2')
    return amount, reward_channel


def decode_c2s_item_use(opcode, payload):
    """Decode the three exact item-use/loadout reports from the client.

    The original client contains exact senders for all three records.  Static
    reachability is narrower: energy has a natural inventory-UI producer,
    while the shipped toy/gym UI has no direct path to the common sender.
    Keep those two decoders for protocol compatibility without pretending
    that S2C 0x0007 can request them through its one-byte effect-code rows.
    """
    layouts = {
        0x000D: ('toy', 4, 10),
        0x000E: ('gym', 3, 8),
        0x000F: ('energy', 1, 3),
    }
    if opcode not in layouts:
        raise ValueError(f'unsupported item-use opcode 0x{opcode:04X}')
    inventory_name, expected_size, slot_count = layouts[opcode]
    if len(payload) != expected_size:
        raise ValueError(
            f'C2S 0x{opcode:04X} item-use payload must be exactly '
            f'{expected_size} bytes'
        )
    raw_indices = list(payload)
    # FUN_0059ACD0 seeds and activates only three toy entries, but the caller
    # always transmits four bytes after FUN_0059C790 and ignores its returned
    # count.  The fourth byte is therefore stack residue until a real fourth
    # toy is active.  Validate the three guaranteed serialized entries here;
    # the server handler decides whether byte 4 is an owned fourth item or
    # ignorable residue.
    if opcode == 0x000D:
        guaranteed = raw_indices[:3]
        if any(index >= slot_count for index in guaranteed):
            raise ValueError(f'C2S 0x{opcode:04X} item index is out of range')
        if guaranteed != sorted(set(guaranteed)):
            raise ValueError(
                f'C2S 0x{opcode:04X} active loadout must be unique and ordered'
            )
        return inventory_name, raw_indices
    else:
        indices = raw_indices
    if any(index >= slot_count for index in indices):
        raise ValueError(f'C2S 0x{opcode:04X} item index is out of range')
    if opcode in (0x000D, 0x000E) and indices != sorted(set(indices)):
        raise ValueError(
            f'C2S 0x{opcode:04X} active loadout must be unique and ordered'
        )
    return inventory_name, indices


def load_azrok_item_catalog(path):
    """Read the locally owned Azrok.dat item ids, domains, and prices.

    The variable strings and model names are skipped rather than exposed by
    the server.  Only the interoperability fields required to validate a
    purchase are retained.
    """
    with open(path, 'rb') as item_file:
        data = item_file.read()
    if len(data) < 4:
        raise ValueError('Azrok.dat is truncated')
    item_count = struct.unpack_from('<I', data, 0)[0]
    if item_count < 1 or item_count > 4096:
        raise ValueError(f'Azrok.dat item count is invalid: {item_count}')
    pos = 4

    def read_u16():
        nonlocal pos
        if pos + 2 > len(data):
            raise ValueError('Azrok.dat ended inside an item record')
        value = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        return value

    def read_u32():
        nonlocal pos
        if pos + 4 > len(data):
            raise ValueError('Azrok.dat ended inside an item record')
        value = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        return value

    def skip_wide_string():
        nonlocal pos
        char_count = read_u32()
        byte_count = char_count * 2
        if char_count > 4096 or pos + byte_count > len(data):
            raise ValueError('Azrok.dat contains an invalid wide string')
        pos += byte_count

    catalog = {}
    for _record_index in range(item_count):
        outer_id = read_u32()
        read_u32()  # serialized object reference; process-local and unused
        item_id = read_u32()
        domain = read_u32()
        skip_wide_string()  # name
        skip_wide_string()  # effect description
        price = read_u32()
        read_u32()  # flags/reserved
        read_u16()  # has-model flag
        model_count = read_u16()
        read_u16()  # reserved
        if model_count > 64:
            raise ValueError('Azrok.dat model count is invalid')
        for _model_index in range(model_count):
            skip_wide_string()
        if outer_id != item_id or item_id in catalog or domain > 7:
            raise ValueError('Azrok.dat item identity/domain is inconsistent')
        catalog[item_id] = {'domain': domain, 'price': price}
    if pos != len(data):
        raise ValueError(f'Azrok.dat has {len(data) - pos} unexpected trailing bytes')
    return catalog

# ═══════════════════════════════════════════════════════════x
#  Windows API
# ═══════════════════════════════════════════════════════════
CREATE_SUSPENDED = 0x00000004
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04

if os.name == 'nt':
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
else:
    # The preservation TCP server is platform-neutral.  These handles are
    # required only by the optional native Windows client launcher and its
    # read-only process/window diagnostics.
    kernel32 = None
    user32 = None
hook_base_global = 0


def list_process_windows(hProcess):
    """Return visible top-level windows owned by the attached game process.

    Acknex error boxes are separate ``#32770`` windows.  Capturing only the
    main render window therefore leaves a convincing but stale gameplay frame
    behind while an E1201 modal is active.  Keep this observer read-only and
    cheap enough for the control panel's one-second polling path.
    """
    try:
        pid = int(kernel32.GetProcessId(hProcess))
    except Exception:
        return []
    if pid <= 0:
        return []

    windows = []
    enum_proc_type = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def window_text(hwnd):
        length = int(user32.GetWindowTextLengthW(hwnd))
        if length <= 0:
            return ''
        buf = ctypes.create_unicode_buffer(min(length + 1, 1024))
        user32.GetWindowTextW(hwnd, buf, len(buf))
        return buf.value

    def window_class(hwnd):
        buf = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hwnd, buf, len(buf))
        return buf.value

    def top_cb(hwnd, _lparam):
        owner_pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
        if owner_pid.value != pid or not user32.IsWindowVisible(hwnd):
            return True

        child_texts = []

        def child_cb(child, _child_lparam):
            text = window_text(child).strip()
            if text and text not in child_texts:
                child_texts.append(text)
            return len(child_texts) < 8

        child_proc = enum_proc_type(child_cb)
        user32.EnumChildWindows(hwnd, child_proc, 0)
        title = window_text(hwnd).strip()
        if title or child_texts:
            windows.append({
                'hwnd': f'0x{int(hwnd):X}',
                'class': window_class(hwnd),
                'title': title,
                'child_texts': child_texts,
            })
        return len(windows) < 8

    callback = enum_proc_type(top_cb)
    user32.EnumWindows(callback, 0)
    return windows

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
        ("lpReserved2", ctypes.c_void_p), ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD),
    ]

def read_mem(hProc, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(hProc, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    return buf.raw[:n.value] if ok else None

def write_mem(hProc, addr, data):
    if isinstance(data, bytearray):
        data = bytes(data)
    n = ctypes.c_size_t(0)
    return kernel32.WriteProcessMemory(hProc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n))

def flush_icache(hProc, addr, size):
    try:
        kernel32.FlushInstructionCache(hProc, ctypes.c_void_p(addr), size)
    except Exception:
        pass

def read_dword(hProc, addr):
    d = read_mem(hProc, addr, 4)
    return struct.unpack('<I', d)[0] if d and len(d) == 4 else 0


def read_word(hProc, addr):
    d = read_mem(hProc, addr, 2)
    return struct.unpack('<H', d)[0] if d and len(d) == 2 else 0


def read_byte(hProc, addr):
    d = read_mem(hProc, addr, 1)
    return d[0] if d and len(d) == 1 else 0


def read_c_string(hProc, addr, max_len=260):
    """Read a bounded client string for diagnostics without modifying memory."""
    data = read_mem(hProc, addr, max_len)
    if not data:
        return ''
    raw = data.split(b'\x00', 1)[0]
    try:
        return raw.decode('ascii')
    except UnicodeDecodeError:
        return raw.decode('cp949', errors='replace')


def read_dispatch_owner_chain(hProc):
    """Read the WDL string chain used by FUN_004EDB10.

    The ``+0x0C`` values under the ``+0x9A0``, ``+0x998`` and ``+0x9AC``
    engine records are string-data pointers (IP:PORT, username and authkey).
    FUN_00508B30's implicit ``this`` (the GameManager) is not one of those
    string arguments; decompiler __thiscall rendering can otherwise make the
    first string pointer look like a dispatcher object.  This is read-only.
    """
    # `DAT_006e8430` is a global pointer value, not an inline structure at
    # the image address.  Ghidra's expression therefore means:
    #   engine_root = *(u32 *)0x006e8430
    #   ip_holder   = *(u32 *)(engine_root + 0x9a0)
    # Each +0xC result is a WDL string-data pointer, not a CGameManager.
    static_addr = 0x006E8430
    engine_root = read_dword(hProc, static_addr)
    owner_9a0 = read_dword(hProc, engine_root + 0x9A0) if engine_root >= 0x10000 else 0
    owner_plus_c = read_dword(hProc, owner_9a0 + 0x0C) if owner_9a0 >= 0x10000 else 0
    owner_998 = read_dword(hProc, engine_root + 0x998) if engine_root >= 0x10000 else 0
    owner_998_c = read_dword(hProc, owner_998 + 0x0C) if owner_998 >= 0x10000 else 0
    owner_9ac = read_dword(hProc, engine_root + 0x9AC) if engine_root >= 0x10000 else 0
    owner_9ac_c = read_dword(hProc, owner_9ac + 0x0C) if owner_9ac >= 0x10000 else 0
    result = {
        'engine_static': f'0x{static_addr:08X}',
        'engine_root': f'0x{engine_root:08X}' if engine_root >= 0x10000 else 'unresolved',
        '_engine_root_address': engine_root,
        'engine_9a0_ptr': owner_9a0,
        'engine_9a0_string_ptr': owner_plus_c,
        'engine_9a0_string': read_c_string(hProc, owner_plus_c, 128) if owner_plus_c >= 0x10000 else '',
        'engine_998_string_ptr': f'0x{owner_998_c:08X}' if owner_998_c >= 0x10000 else 'unresolved',
        'engine_998_string': read_c_string(hProc, owner_998_c, 128) if owner_998_c >= 0x10000 else '',
        'engine_9ac_string_ptr': f'0x{owner_9ac_c:08X}' if owner_9ac_c >= 0x10000 else 'unresolved',
        'engine_9ac_string': read_c_string(hProc, owner_9ac_c, 128) if owner_9ac_c >= 0x10000 else '',
    }
    if owner_9a0 >= 0x10000:
        result['engine_9a0_ptr'] = f'0x{owner_9a0:08X}'
        result['engine_9a0_probe'] = {
            f'+0x{off:X}': (
                f'0x{read_dword(hProc, owner_9a0 + off):08X}'
                if read_mem(hProc, owner_9a0 + off, 4) else 'unreadable'
            )
            for off in (0x00, 0x04, 0x08, 0x0C, 0x10, 0x14, 0x18, 0x1C)
        }
    else:
        result['engine_9a0_ptr'] = 'unresolved'
    if owner_plus_c >= 0x10000:
        result['engine_9a0_string_ptr'] = f'0x{owner_plus_c:08X}'
    else:
        result['engine_9a0_string_ptr'] = 'unresolved'
        result['engine_9a0_string'] = ''
    return result


# CGameManager vtable = 0x0069D0A4 (verified from constructor FUN_00507df0)
CGAMEMANAGER_VTABLE = 0x0069D0A4
_cached_gm_real = 0
_dispatch_owner_scan_cache = {}
_dispatch_owner_scan_lock = threading.RLock()


class _MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wt.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wt.DWORD),
        ('Protect', wt.DWORD),
        ('Type', wt.DWORD),
    ]


MEM_COMMIT = 0x1000
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_WRITECOPY = 0x08
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
READABLE_PAGE_PROTECTS = {
    PAGE_READONLY, PAGE_READWRITE, PAGE_WRITECOPY,
    PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE, PAGE_EXECUTE_WRITECOPY,
}
# The inbound-dispatch vtable base is 0x006A618C.  0x006A6198 is the
# +0x0C slot (FUN_004D8720), not the vtable itself.  Ghidra's constructor
# trace shows that the live CLogicManager is an embedded CGame subobject at
# CGame+0x17756.  Since find_real_gm() returns CGameManager and CGame starts
# at gm+0xE4A, the owner is gm+0x185A0; all +0x163D8/+0x163E4 fields below
# are relative to that subobject, not to the CGameManager base.
# Both vtables occupy the same embedded logic object during its lifecycle:
# CLogicJSDB is the pre-promotion object and CLogicManager is the promoted
# state-1 dispatcher.  0x006A6198 is only the latter table's +0x0C slot.
DISPATCH_PRE_OWNER_VTABLE = 0x006A6154
DISPATCH_OWNER_VTABLE = 0x006A618C
DISPATCH_OWNER_VTABLES = {
    DISPATCH_PRE_OWNER_VTABLE: 'CLogicJSDB',
    DISPATCH_OWNER_VTABLE: 'CLogicManager',
}
DISPATCH_OWNER_SUBOBJECT_OFFSET = 0x185A0


def find_dispatch_owner_candidates(hProc, gm, ttl=1.0):
    """Reverse-search the writer's concrete gate value without modifying memory.

    The instruction-level startup call pushes the outer CGameManager as the
    first stack argument to ``FUN_00594130`` while ECX is the embedded CLogic
    owner.  The callee therefore stores ``gm`` (not the IP-string buffer) at
    ``logic + 0x163D8``.  Searching that exact DWORD is more decisive than
    treating a stack-scanned CGameManager candidate as the dispatcher owner.
    Results are cached briefly because
    the control panel polls /api/state once per second and a full user-space
    scan is intentionally expensive.
    """
    target = gm if gm >= 0x10000 else 0
    if not target:
        return {'target': 'unresolved', 'candidates': [], 'scan': 'gm_unresolved'}
    now = time.monotonic()
    key = (int(hProc), gm, target)
    with _dispatch_owner_scan_lock:
        cached = _dispatch_owner_scan_cache.get(key)
        if cached and now - cached['at'] < ttl:
            return cached['value']

    target_bytes = struct.pack('<I', target & 0xFFFFFFFF)
    candidates = []
    raw_hits = []
    regions = 0
    scanned_bytes = 0
    address = 0x10000
    max_address = 0x7FFF0000
    started = time.monotonic()
    mbi = _MEMORY_BASIC_INFORMATION()
    while address < max_address:
        queried = kernel32.VirtualQueryEx(
            hProc, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if not queried:
            address += 0x10000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            address += 0x10000
            continue
        regions += 1
        protect = int(mbi.Protect)
        readable = (
            int(mbi.State) == MEM_COMMIT
            and not (protect & PAGE_GUARD)
            and not (protect & PAGE_NOACCESS)
            and (protect & 0xFF) in READABLE_PAGE_PROTECTS
        )
        if readable:
            chunk_size = 0x100000
            for offset in range(0, size, chunk_size):
                want = min(chunk_size, size - offset)
                chunk = read_mem(hProc, base + offset, want)
                if not chunk:
                    continue
                scanned_bytes += len(chunk)
                search_from = 0
                while True:
                    hit = chunk.find(target_bytes, search_from)
                    if hit < 0:
                        break
                    field_addr = base + offset + hit
                    candidate = field_addr - 0x163D8
                    mode = read_dword(hProc, candidate + 0x163E4) if candidate >= 0x10000 else 0xFFFFFFFF
                    vptr = read_dword(hProc, candidate) if candidate >= 0x10000 else 0
                    if len(raw_hits) < 64:
                        raw_hits.append({
                            'field': f'0x{field_addr:08X}',
                            'object': f'0x{candidate:08X}' if candidate >= 0x10000 else 'invalid',
                            'mode': mode,
                            'vptr': f'0x{vptr:08X}',
                        })
                    if mode in (0, 1, 2) and vptr:
                        vtable_match = vptr in DISPATCH_OWNER_VTABLES
                        if vtable_match and not any(c['object'] == candidate for c in candidates):
                            candidates.append({
                                'object': f'0x{candidate:08X}',
                                'gate_field': f'0x{field_addr:08X}',
                                'gate_value': f'0x{target:08X}',
                                'mode': mode,
                                'vptr': f'0x{vptr:08X}',
                                'vtable_match': vtable_match,
                                'vtable_kind': DISPATCH_OWNER_VTABLES.get(vptr, 'unknown'),
                            })
                    search_from = hit + 1
        address = base + size

    value = {
        'target': f'0x{target:08X}',
        'raw_hits': raw_hits,
        'candidates': candidates,
        'scan': {
            'regions': regions,
            'bytes': scanned_bytes,
            'elapsed_ms': round((time.monotonic() - started) * 1000, 1),
        },
    }
    with _dispatch_owner_scan_lock:
        _dispatch_owner_scan_cache[key] = {'at': time.monotonic(), 'value': value}
    return value


def find_dispatch_vtable_candidates(hProc, ttl=1.0):
    """Locate objects whose first DWORD is the inbound-dispatch vtable.

    This independent read-only scan remains useful when the gate writer has
    not run yet: it can identify the real owner even when reverse-searching
    the startup gate value ``gm`` produces zero hits.
    """
    now = time.monotonic()
    key = (int(hProc), 'dispatch-vtable', tuple(sorted(DISPATCH_OWNER_VTABLES)))
    with _dispatch_owner_scan_lock:
        cached = _dispatch_owner_scan_cache.get(key)
        if cached and now - cached['at'] < ttl:
            return cached['value']
    needles = {
        struct.pack('<I', vptr): vptr
        for vptr in DISPATCH_OWNER_VTABLES
    }
    hits = []
    regions = 0
    scanned_bytes = 0
    address = 0x10000
    max_address = 0x7FFF0000
    started = time.monotonic()
    mbi = _MEMORY_BASIC_INFORMATION()
    while address < max_address:
        queried = kernel32.VirtualQueryEx(
            hProc, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if not queried:
            address += 0x10000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            address += 0x10000
            continue
        regions += 1
        protect = int(mbi.Protect)
        readable = (
            int(mbi.State) == MEM_COMMIT
            and not (protect & PAGE_GUARD)
            and not (protect & PAGE_NOACCESS)
            and (protect & 0xFF) in READABLE_PAGE_PROTECTS
        )
        if readable:
            for offset in range(0, size, 0x100000):
                chunk = read_mem(hProc, base + offset, min(0x100000, size - offset))
                if not chunk:
                    continue
                scanned_bytes += len(chunk)
                for needle, vptr_value in needles.items():
                    search_from = 0
                    while True:
                        hit = chunk.find(needle, search_from)
                        if hit < 0:
                            break
                        object_addr = base + offset + hit
                        mode = read_dword(hProc, object_addr + 0x163E4)
                        gate = read_dword(hProc, object_addr + 0x163D8)
                        entry = {
                            'object': f'0x{object_addr:08X}',
                            'vptr': f'0x{vptr_value:08X}',
                            'vtable_kind': DISPATCH_OWNER_VTABLES[vptr_value],
                            'mode': mode,
                            'gate': f'0x{gate:08X}',
                            'gate_is_nonzero': bool(gate),
                        }
                        if not any(x['object'] == entry['object'] for x in hits):
                            hits.append(entry)
                        search_from = hit + 1
        address = base + size
    value = {
        'vtables': {
            f'0x{vptr:08X}': kind
            for vptr, kind in DISPATCH_OWNER_VTABLES.items()
        },
        'objects': hits[:128],
        'scan': {
            'regions': regions,
            'bytes': scanned_bytes,
            'elapsed_ms': round((time.monotonic() - started) * 1000, 1),
        },
    }
    with _dispatch_owner_scan_lock:
        _dispatch_owner_scan_cache[key] = {'at': time.monotonic(), 'value': value}
    return value


def read_dispatch_owner_subobject(hProc, gm):
    """Read the statically verified CLogicManager embedded in CGame.

    ``FUN_00507DF0`` creates CGame at ``gm+0xE4A``; ``FUN_0052F900`` then
    loads ``ECX = CGame + 0x17756`` (absolute ``gm+0x185A0``) before
    constructing the logic manager, and ``FUN_00593F30`` installs
    ``0x006A618C`` as its vptr.
    This is deliberately read-only: a mismatch is reported as evidence, not
    repaired by writing a vtable or by changing dispatch state.
    """
    owner = gm + DISPATCH_OWNER_SUBOBJECT_OFFSET if gm >= 0x10000 else 0
    if not owner:
        return {
            'object': 'unresolved',
            'vptr': 'unresolved',
            'vtable_match': False,
            'gate': 0,
            'mode': 0,
            'validated': False,
        }
    vptr = read_dword(hProc, owner)
    gate = read_dword(hProc, owner + 0x163D8)
    mode = read_dword(hProc, owner + 0x163E4)
    return {
        'object': f'0x{owner:08X}',
        'vptr': f'0x{vptr:08X}',
        'vtable_match': vptr in DISPATCH_OWNER_VTABLES,
        'vtable_kind': DISPATCH_OWNER_VTABLES.get(vptr, 'unknown'),
        'state1_dispatch_ready': vptr == DISPATCH_OWNER_VTABLE,
        'gate': gate,
        'mode': mode,
        'validated': vptr in DISPATCH_OWNER_VTABLES and mode in (0, 1, 2),
    }

# Read-only safety preflight for the four unconditional virtual calls made by
# Plaza_TransitionFromRoom (S->C 0x000D, payload 00).  These values are part of
# the original client image; the server must never synthesize or repair them.
# A mismatch means the embedded UI object lifetime is invalid and the packet
# transition must be deferred.
TRANSITION_VPTR_SPECS = (
    ('popup_status',     0x4AEA5, 0x006ADA34),
    ('popup_azron_info', 0x4A793, 0x006AE3C4),
    ('popup_calendar',   0x4ADD0, 0x006A7D6C),
    ('popup_state_list', 0x4ABED, 0x006AD970),
)

# Child PANEL* fields consumed unconditionally by the four 0x000D cleanup
# methods. Offsets are relative to ui_root (gm+0x4A78F). A null field is
# explicitly safe. A non-null readable pointer is still not sufficient proof
# that Acknex pan_remove/bmap_purge will accept it, so it remains UNKNOWN until
# allocator/provenance evidence exists.
TRANSITION_CHILD_HANDLE_SPECS = tuple(
    [('status_74', 0x716 + 0x74)]
    + [(f'status_78_{i}', 0x716 + 0x78 + i * 4) for i in range(6)]
    + [(f'status_90_{i}', 0x716 + 0x90 + i * 4) for i in range(6)]
    + [(f'azron_{offset:02x}', 0x004 + offset)
       for offset in (0x73, 0x77, 0x7B, 0x7F, 0x83, 0x87, 0x8B)]
    + [(f'azron_8f_{i}', 0x004 + 0x8F + i * 4) for i in range(10)]
    + [(f'azron_{offset:02x}', 0x004 + offset) for offset in (0xDF, 0xE3)]
    + [(f'calendar_{offset:02x}', 0x641 + offset)
       for offset in (0xB2, 0xB6, 0xBA, 0xBE, 0xC2)]
    + [('state_list_73', 0x45E + 0x73)]
    + [(f'state_list_{row}_{col}', 0x45E + 0x77 + row * 0x14 + col * 4)
       for row in range(8) for col in range(5)]
)

# Exact normal PatHouse setup fingerprint, recovered from the four setup
# functions: every listed field receives the direct return value of pan_create.
# All remaining 21 fields stay zero. Runtime admission additionally requires
# each PANEL and non-null BMAP pointer to remain readable.
TRANSITION_CHILD_EXPECTED_NONZERO = frozenset(
    ['status_74']
    + [f'status_78_{i}' for i in range(6)]
    + [f'status_90_{i}' for i in range(2, 6)]
    + [f'azron_{offset:02x}' for offset in (0x73, 0x77, 0x7B, 0x7F, 0x83, 0x87, 0x8B)]
    + [f'azron_8f_{i}' for i in range(10)]
    + [f'azron_{offset:02x}' for offset in (0xDF, 0xE3)]
    + [f'calendar_{offset:02x}' for offset in (0xB2, 0xB6, 0xBA, 0xBE, 0xC2)]
    + ['state_list_73']
    + [f'state_list_{row}_{col}'
       for row, count in enumerate((3, 3, 3, 3, 3, 2, 2, 2))
       for col in range(count)]
)


def inspect_transition_cleanup_children(hProc, gm):
    """Classify the 78 child PANEL handles used by S->C 0x000D cleanup."""
    ui_root = gm + 0x4A78F
    # StateList is the highest object touched by the recovered child fields.
    snapshot = read_mem(hProc, ui_root, 0xB61)
    if not snapshot or len(snapshot) != 0xB61:
        return {
            'state': 'unreadable_root', 'ok': False, 'total': len(TRANSITION_CHILD_HANDLE_SPECS),
            'zero': 0, 'nonzero': 0, 'readable_nonzero': 0,
            'invalid': ['ui_root_snapshot'], 'unknown': [],
        }

    zero = 0
    readable_nonzero = 0
    invalid = []
    unknown = []
    missing_expected = []
    for name, root_offset in TRANSITION_CHILD_HANDLE_SPECS:
        handle = struct.unpack_from('<I', snapshot, root_offset)[0]
        if handle == 0:
            zero += 1
            if name in TRANSITION_CHILD_EXPECTED_NONZERO:
                missing_expected.append(name)
            continue
        panel = read_mem(hProc, handle, 0x30)
        if not panel or len(panel) != 0x30:
            invalid.append(f'{name}=0x{handle:08X}:panel_unreadable')
            continue
        bmap = struct.unpack_from('<I', panel, 0x24)[0]
        if bmap:
            bmap_probe = read_mem(hProc, bmap, 4)
            if not bmap_probe or len(bmap_probe) != 4:
                invalid.append(f'{name}=0x{handle:08X}:bmap_0x{bmap:08X}_unreadable')
                continue
        readable_nonzero += 1
        if name not in TRANSITION_CHILD_EXPECTED_NONZERO:
            unknown.append(f'{name}=0x{handle:08X}')

    nonzero = len(TRANSITION_CHILD_HANDLE_SPECS) - zero
    if invalid:
        state = 'invalid'
    elif nonzero == 0:
        # Valid early PatHouse state: none of the optional popup panels has
        # been constructed yet, so every cleanup slot is already null-safe.
        state = 'all_zero'
    elif missing_expected or unknown:
        state = 'occupancy_mismatch'
    elif nonzero == len(TRANSITION_CHILD_EXPECTED_NONZERO):
        state = 'clean_pan_create_fingerprint'
    else:
        state = 'occupancy_mismatch'
    return {
        'state': state,
        'ok': state in {'all_zero', 'clean_pan_create_fingerprint'},
        'total': len(TRANSITION_CHILD_HANDLE_SPECS),
        'zero': zero,
        'nonzero': nonzero,
        'readable_nonzero': readable_nonzero,
        'invalid': invalid,
        'unknown': unknown,
        'missing_expected': missing_expected,
    }

def find_real_gm(hProc):
    """Find the real CGameManager by scanning stack memory for vtable pointer."""
    global _cached_gm_real
    if _cached_gm_real:
        # Verify cache is still valid
        val = read_dword(hProc, _cached_gm_real)
        if val == CGAMEMANAGER_VTABLE:
            return _cached_gm_real
        _cached_gm_real = 0

    # CGameManager is stack-allocated in main loop. Scan typical stack range.
    # Stack grows down from high addresses. Scan 0x00100000-0x00300000 range.
    vtable_bytes = struct.pack('<I', CGAMEMANAGER_VTABLE)
    for base in range(0x00100000, 0x00300000, 0x10000):
        chunk = read_mem(hProc, base, 0x10000)
        if not chunk:
            continue
        off = 0
        while True:
            idx = chunk.find(vtable_bytes, off)
            if idx == -1:
                break
            candidate = base + idx
            # Verify: gm+0x31792 should be a valid scene mode (0-5)
            mode = read_dword(hProc, candidate + 0x31792)
            if mode <= 5:
                # Verify: gm+0x31946 should be non-zero (gate)
                gate = read_dword(hProc, candidate + 0x31946)
                if gate != 0:
                    _cached_gm_real = candidate
                    print(f"    [GM] Found real CGameManager at 0x{candidate:08X} (mode={mode}, gate=0x{gate:08X})")
                    return candidate
            off = idx + 4
    return 0


# ═══════════════════════════════════════════════════════════
#  Hook Builder
# ═══════════════════════════════════════════════════════════
SERVER_PORT = 9200  # 9000 is reserved by Windows Hyper-V (range 8951-9050)
SERVER_PORT_NET = socket.htons(SERVER_PORT)  # network byte order

REQUESTED_SPACE_NAME = os.environ.get('AZROK_SPACE_NAME', 'PatHouse').strip() or 'PatHouse'
STRICT_SPACE_NAME = os.environ.get('AZROK_STRICT_SPACE_NAME', '').strip() == '1'
DEFAULT_CONTENT_PROFILE = 'shipped'
CONTENT_PROFILE = os.environ.get(
    'AZROK_CONTENT_PROFILE', DEFAULT_CONTENT_PROFILE
).strip().lower() or DEFAULT_CONTENT_PROFILE
if CONTENT_PROFILE not in {'shipped', 'playable', 'minimal'}:
    raise ValueError('AZROK_CONTENT_PROFILE must be one of: shipped, playable, minimal')
STATE_STORE_NAMESPACE = os.environ.get('AZROK_STATE_NAMESPACE', '').strip()
if any(not (ch.isalnum() or ch in '-_') for ch in STATE_STORE_NAMESPACE):
    raise ValueError('AZROK_STATE_NAMESPACE may contain only letters, digits, - and _')

# S2C 0x000A is a 75-u16 item-domain registry, not character progression
# stats.  The exact binary table is the supported default.  The old guessed
# table survives only as an explicit comparison profile.
DEFAULT_ITEM_REGISTRY_000A_PROFILE = 'binary'
_legacy_binary_000a = os.environ.get('AZROK_USE_BINARY_0010_DEFAULTS', '').strip()
if 'AZROK_000A_PROFILE' in os.environ:
    ITEM_REGISTRY_000A_PROFILE = (
        os.environ['AZROK_000A_PROFILE'].strip().lower()
        or DEFAULT_ITEM_REGISTRY_000A_PROFILE
    )
elif _legacy_binary_000a:
    ITEM_REGISTRY_000A_PROFILE = 'binary' if _legacy_binary_000a == '1' else 'custom'
else:
    ITEM_REGISTRY_000A_PROFILE = DEFAULT_ITEM_REGISTRY_000A_PROFILE
if ITEM_REGISTRY_000A_PROFILE not in {'binary', 'custom'}:
    raise ValueError('AZROK_000A_PROFILE must be one of: binary, custom')
ITEM_REGISTRY_000A_HIGH_RESOURCE_DIAGNOSTIC = (
    os.environ.get('AZROK_HIGH_RESOURCE_STATS', '').strip() == '1'
)
LEGACY_FORCE_PLAZA_ON_LOBBY = os.environ.get('AZROK_LEGACY_FORCE_PLAZA_ON_LOBBY', '').strip() == '1'
# Historical diagnostic path: C->S 0x0019 directly wrote client memory and
# replayed a broad setup bundle. It contaminates packet-only experiments and
# therefore stays disabled unless a researcher opts in explicitly.
LEGACY_0019_MEMORY_SHORTCUT = os.environ.get('AZROK_LEGACY_0019_MEMORY_SHORTCUT', '').strip() == '1'
LATE_READY_006E = os.environ.get('AZROK_LATE_READY_006E', '').strip() == '1'

def _parse_int_env(name, default):
    raw = os.environ.get(name, '').strip()
    if not raw:
        return default
    try:
        return int(raw, 0)
    except ValueError as exc:
        raise ValueError(f'{name} must be an integer, e.g. 0x0A or 10') from exc


STARTER_CURRENCY = max(0, min(0xFFFFFFFF, _parse_int_env('AZROK_STARTER_CURRENCY', 0)))
EVOLUTION_AUX_STAGE1 = _parse_int_env('AZROK_EVOLUTION_AUX_STAGE1', 1)
EVOLUTION_AUX_STAGE2 = _parse_int_env('AZROK_EVOLUTION_AUX_STAGE2', 4)
if EVOLUTION_AUX_STAGE1 not in (1, 2, 3):
    raise ValueError('AZROK_EVOLUTION_AUX_STAGE1 must be 1, 2, or 3')
if EVOLUTION_AUX_STAGE2 not in (4, 5, 6):
    raise ValueError('AZROK_EVOLUTION_AUX_STAGE2 must be 4, 5, or 6')

# Runtime-row automatic completion is intentionally narrower than row import.
# Kinds 0/1/2/5 export their client-authored row projection through C2S 0x0011;
# reward-bearing completions also export C2S 0x0012(amount, channel=2), which
# must be correlated with the exact row retirement before FunCorn is credited.
# Kind 3 has a different server-visible witness: the monotonic evolution edge,
# branch thresholds, and its 0010/0011/0007 sequence.  Never infer any of these
# completions from coincidental stat deltas or reconnect echoes alone.
RUNTIME_ROW_SERVER_POLICIES = {
    0: {
        'meaning': 'food wish: actions 0xD4/0xDB matched by item id',
        'client_effect': 'stat7 decrease plus local no-op currency callback',
        'auto_retire': False,
        'reason': 'requires exact 0012 reward plus 0011 row retirement; never stat-only',
    },
    1: {
        'meaning': 'minigame/training matched by resolved skill stat',
        'client_effect': 'skill-stat bonus plus local no-op currency callback',
        'auto_retire': False,
        'reason': 'requires exact 0012 reward plus 0011 row retirement; never stat-only',
    },
    2: {
        'meaning': 'feed/exercise action matched by action or food id',
        'client_effect': 'stat7 decrease plus optional local no-op currency callback',
        'auto_retire': False,
        'reason': 'reward rows require 0012+0011; no-FunCorn rows retire via 0011 only',
    },
    3: {
        'meaning': 'growth/evolution threshold',
        'client_effect': 'exact evolution-stage commit without currency',
        'auto_retire': True,
        'reason': 'exact monotonic stage edge and branch thresholds are in C2S 0x0007',
    },
    5: {
        'meaning': 'stage-0 tutorial action chain',
        'client_effect': 'stat2 EXP bonus, next local row, no-op currency callback',
        'auto_retire': False,
        'reason': 'requires preceding 0011 retirement, adjacent 0012, and next-row 0011',
    },
}


def quest_funcorn_reward_for_runtime_row(kind, aux):
    """Return the exact hard-coded corn reward for a locally completed row."""
    kind = int(kind)
    aux = int(aux)
    if kind == 0:
        if aux in (1001, 1002, 1003):
            return 40
        if aux in (1004, 1005):
            return 45
        if aux in (1006, 1007, 1008, 1009):
            return 38
        if aux in (1015, 1016, 1017, 1018, 1019):
            return 43
        if aux in (1024, 1025, 1026, 1027, 1028):
            return 48
    elif kind == 1:
        if 31 <= aux <= 39:
            return 22
        if 40 <= aux <= 44:
            return 19
        if 49 <= aux <= 53:
            return 21
        if 58 <= aux <= 62:
            return 24
    elif kind == 2:
        if 1006 <= aux <= 1010:
            return 24
        if 1015 <= aux <= 1019:
            return 29
        if 1024 <= aux <= 1028:
            return 35
    elif kind == 5 and aux in (212, 202, 203, 227, 201):
        return 100
    return None


PLAZA_REPLY_MODE = os.environ.get('AZROK_PLAZA_REPLY_MODE', '0064').strip().lower()
if PLAZA_REPLY_MODE not in {'both', '0064', '006e', 'none'}:
    raise ValueError('AZROK_PLAZA_REPLY_MODE must be one of: both, 0064, 006e, none')
STATE_0064_ENTRY_KIND = _parse_int_env('AZROK_0064_ENTRY_KIND', 0x0A) & 0xFF
POPUP_HARD_BYPASSES = os.environ.get('AZROK_POPUP_HARD_BYPASSES', '').strip() == '1'
UI_POPUP_BYPASSES = os.environ.get('AZROK_UI_POPUP_BYPASSES', '').strip() == '1'
# The rescue-era heartbeat auto-create path does not execute the verified
# C2S 0x0004 create transaction (lease, durable canonical, selected binding).
# Keep it disabled rather than entering a non-persistent world identity.
SERVER_AUTO_CREATE_ENABLED = False
# A server-side selector does not perform the client's character-picker
# transition.  Live freshnine reconnect accepted the bundle while keeping a
# blank HUD and never sending its post-load 0007/0017/0008.  Require the real
# C2S 0005 even when a legacy launcher still requests the startup assist.
SERVER_AUTO_SELECT_EXISTING_ENABLED = False
SERVER_AUTO_SELECT_HEARTBEATS = _parse_int_env(
    'AZROK_AUTO_SELECT_HEARTBEATS', 8
)
if not 1 <= SERVER_AUTO_SELECT_HEARTBEATS <= 8:
    raise ValueError('AZROK_AUTO_SELECT_HEARTBEATS must be in 1..8')
# The native zero-date bootstrap creates tutorial row kind=5/aux=212.  A live
# fresh-browser regression proved that replacing this with a current date does
# not create a compatible shortcut: the client keeps the character-select
# backdrop, never initializes PatHouse 3D and emits only heartbeats.  Keep the
# original zero-date path enabled by default; an explicit 0 remains available
# only as a narrow diagnostic control.
NATIVE_FRESH_TUTORIAL_ENABLED = (
    os.environ.get('AZROK_NATIVE_FRESH_TUTORIAL', '1').strip() != '0'
)
SKIP_STAGE9_TUTORIAL_EVENT = os.environ.get('AZROK_SKIP_STAGE9_TUTORIAL_EVENT', '').strip() == '1'
SCENE_READY_FORCE = os.environ.get('AZROK_SCENE_READY_FORCE', '1').strip() != '0'
LATE_ZONE_0007_REPLY = os.environ.get('AZROK_LATE_ZONE_0007_REPLY', '').strip() == '1'
PRE_RESUME_DELAY_MS = int(os.environ.get('AZROK_PRE_RESUME_DELAY_MS', '0').strip() or '0')
AZRON_SPECIES = int(os.environ.get('AZROK_SPECIES', '2').strip())  # 0=Ark, 1=Abo, 2=Paz, 3=Tero
# Stage 0 keeps PatHouse's real outside interaction (mirror_01/type 0x20)
# locked.  The restored playable default starts at stage 1 so the natural
# action 0x6F -> C2S 0x0019 exit contract is available; stage 0 remains an
# The only live-playable, zero-binary-patch bootstrap is stage 0.  Injecting
# stage 1 either during bootstrap or after a stable PatHouse load reproducibly
# enters phase 3 and raises Acknex E1201 "Nexus too small (40)".  Higher stages
# remain explicit diagnostics until the accompanying growth-state contract is
# reconstructed; do not treat this byte as a standalone outside-unlock flag.
AZRON_EVOLUTION = min(int(os.environ.get('AZROK_EVOLUTION', '0').strip()), 3)  # 0-3 (stage 4 has no model assets)
PRE_LOADER_DELAY_MS = int(os.environ.get('AZROK_PRE_LOADER_DELAY_MS', '0').strip() or '0')
ENTER_SPACE_NAME = REQUESTED_SPACE_NAME
# Rescue-era fallback kept behind an explicit opt-in switch only. In packet-first
# mode we should respect the requested space name instead of silently remapping
# `Lobby` to `Plaza`.
if LEGACY_FORCE_PLAZA_ON_LOBBY and not STRICT_SPACE_NAME and REQUESTED_SPACE_NAME.lower() == 'lobby':
    ENTER_SPACE_NAME = 'Plaza'
ENTER_SPACE_OVERRIDDEN = ENTER_SPACE_NAME != REQUESTED_SPACE_NAME
ENTER_SPACE_0003_PATH = f'Data\\Space\\{ENTER_SPACE_NAME}'.encode('ascii', errors='ignore') + b'\x00'
ZONE_0007_SIZE = 0x1D8
POST_LOAD_0005_SIZE = 0x06
ITEM_REGISTRY_000A_SIZE = 0x96
STAT_TABLE_0011_SIZE = 0x3E
STATE_0064_SIZE = 0x1B
STATE_0068_RECORD_SIZE = 0x18
STATE_0066_RECORD_SIZE = 0x1A
STATE_0069_SIZE = 0x10
LOGIN_0000_REQUEST_SIZE = 0x6A
LOGIN_0000_BOOTSTRAP_SIZE = 0x183
CHAT_006A_FIXED_SIZE = 0x15
COMMUNITY_006C_SIZE = 0x06
CANONICAL_STATE_SCHEMA_VERSION = 1
DEFAULT_ACCESSORY_SLOTS = (0xFF, 0xFF, 0xFF, 0xFF)
# Inclusive catalogue maxima recovered from the client.  0xFF is the only
# empty/unequipped sentinel; values between a slot maximum and 0xFE are never
# accepted into canonical state or emitted to the client.
ACCESSORY_SLOT_MAX_VALUES = (9, 6, 3, 7)
# Exact derived-unlock rows constructed at CPopupAccessory+0x1CC.  The key is
# the wire selector (slot, value), not a separately persisted ownership id.
# Each value is (stat group, inclusive threshold, minimum evolution or None).
ACCESSORY_GROUP_UNLOCK_ROWS = {
    (1, 0): (4, 50, None),
    (1, 1): (1, 200, None),
    (1, 2): (3, 100, None),
    (1, 3): (2, 50, None),
    (1, 4): (4, 200, 3),
    (2, 0): (4, 100, None),
    (2, 1): (5, 200, None),
    (2, 2): (3, 150, None),
    (3, 0): (2, 150, None),
}
# Exact direct-stat tier-2 gates in FUN_005B2CB0.  stat1 is the character
# level; these selectors are deliberately separate from the nine-row table.
ACCESSORY_LEVEL_UNLOCKS = {
    (0, 5): 7,   # HEART
    (0, 6): 5,   # ANGEL
    (3, 1): 10,  # PIG
    (3, 2): 3,   # Penguin
    (3, 3): 4,   # Dog
    (3, 4): 4,   # Cat
}
ACCESSORY_SINGLE_STAT_UNLOCKS = {
    (0, 9): (30, 200),  # MortarBoard / knowledge
}
ACCESSORY_ALL_STAT_UNLOCKS = {
    (0, 4): ((37, 100), (38, 100), (39, 100)),  # ANGELRING / magic
}
INVENTORY_0007_FIELDS = (
    ('furniture', 0x097, 33),
    ('drug', 0x0B8, 15),
    ('energy', 0x0C7, 20),
    ('food', 0x0EA, 38),
    ('ingredient', 0x110, 3),
    ('toy', 0x113, 10),
    ('gym', 0x11D, 8),
    ('book', 0x131, 1),
)


def normalize_accessory_slots(values):
    """Return one validated four-byte appearance vector, or ``None``.

    Ownership is derived locally from progression stats.  The server stores
    only the equipped selector bytes and therefore has no safe reason to clamp
    an unknown value into a different accessory.
    """
    if not isinstance(values, (list, tuple, bytes, bytearray)) or len(values) != 4:
        return None
    clean = []
    for slot, upper in enumerate(ACCESSORY_SLOT_MAX_VALUES):
        try:
            value = int(values[slot])
        except (TypeError, ValueError):
            return None
        if value != 0xFF and not 0 <= value <= upper:
            return None
        clean.append(value)
    return clean


def accessory_progression_from_canonical(state):
    """Decode the selected character's authoritative accessory progression.

    C2S 0x0007 stores evolution at +0x05 and 70 little-endian u16 stats at
    +0x0A.  A missing or malformed canonical snapshot cannot prove a derived
    unlock and is therefore returned as ``None`` rather than substituted with
    profile defaults or live relay metadata.
    """
    if not isinstance(state, dict):
        return None
    snapshot_hex = state.get('snapshot_hex')
    if not isinstance(snapshot_hex, str) or len(snapshot_hex) != 0xC4 * 2:
        return None
    try:
        snapshot = bytes.fromhex(snapshot_hex)
    except ValueError:
        return None
    if len(snapshot) != 0xC4:
        return None
    stats = struct.unpack_from('<70H', snapshot, 0x0A)
    return {
        'evolution': int(snapshot[0x05]),
        'level': int(stats[1]),
        'stats': stats,
        'group_totals': {
            1: sum(stats[31:34]),
            2: sum(stats[34:37]),
            3: sum(stats[37:40]),
            4: int(stats[30]),
            5: sum(stats[40:67]),
        },
    }


def evaluate_accessory_unlock(state, slot, value):
    """Return fail-closed unlock evidence for one accessory selector.

    Selectors without a recovered derived gate are the client's unconditional
    tier-1 catalogue and remain usable even before a first canonical snapshot.
    """
    try:
        slot = int(slot)
        value = int(value)
    except (TypeError, ValueError):
        return {'allowed': False, 'rule': 'invalid_selector'}
    if (
        slot not in range(len(ACCESSORY_SLOT_MAX_VALUES))
        or value not in range(ACCESSORY_SLOT_MAX_VALUES[slot] + 1)
    ):
        return {'allowed': False, 'rule': 'invalid_selector'}

    selector = (slot, value)
    gated = (
        selector in ACCESSORY_GROUP_UNLOCK_ROWS
        or selector in ACCESSORY_LEVEL_UNLOCKS
        or selector in ACCESSORY_SINGLE_STAT_UNLOCKS
        or selector in ACCESSORY_ALL_STAT_UNLOCKS
    )
    if not gated:
        return {'allowed': True, 'rule': 'tier1'}

    progression = accessory_progression_from_canonical(state)
    if progression is None:
        return {'allowed': False, 'rule': 'canonical_progression_missing'}
    stats = progression['stats']

    if selector in ACCESSORY_LEVEL_UNLOCKS:
        threshold = ACCESSORY_LEVEL_UNLOCKS[selector]
        actual = progression['level']
        return {
            'allowed': actual >= threshold,
            'rule': 'level',
            'stat_id': 1,
            'actual': actual,
            'threshold': threshold,
        }

    if selector in ACCESSORY_SINGLE_STAT_UNLOCKS:
        stat_id, threshold = ACCESSORY_SINGLE_STAT_UNLOCKS[selector]
        actual = int(stats[stat_id])
        return {
            'allowed': actual >= threshold,
            'rule': 'single_stat',
            'stat_id': stat_id,
            'actual': actual,
            'threshold': threshold,
        }

    if selector in ACCESSORY_ALL_STAT_UNLOCKS:
        requirements = ACCESSORY_ALL_STAT_UNLOCKS[selector]
        actual = {stat_id: int(stats[stat_id]) for stat_id, _ in requirements}
        return {
            'allowed': all(actual[stat_id] >= threshold
                           for stat_id, threshold in requirements),
            'rule': 'all_stats',
            'actual': actual,
            'thresholds': dict(requirements),
        }

    group, threshold, minimum_evolution = ACCESSORY_GROUP_UNLOCK_ROWS[selector]
    actual = progression['group_totals'][group]
    evolution = progression['evolution']
    return {
        'allowed': (
            actual >= threshold
            and (minimum_evolution is None or evolution >= minimum_evolution)
        ),
        'rule': 'group',
        'group': group,
        'actual': actual,
        'threshold': threshold,
        'evolution': evolution,
        'minimum_evolution': minimum_evolution,
    }

# Exact item-id to S2C 0x0007 quantity-slot mapping recovered from the client.
# An id outside these ranges is never allowed to mutate canonical state.
SHOP_ITEM_INVENTORY_RANGES = (
    (0, 32, 'furniture', 0),
    (1000, 1032, 'food', 1000),
    (1500, 1502, 'ingredient', 1500),
    (2000, 2009, 'toy', 2000),
    (2500, 2507, 'gym', 2500),
    (3000, 3000, 'book', 3000),
    (4000, 4005, 'drug', 4000),
    (5000, 5002, 'energy', 5000),
)
SHOP_UNIQUE_INVENTORIES = frozenset(('furniture', 'toy', 'gym', 'book'))
CLIENT_GRANTED_DEFAULT_ITEMS = {
    'toy': (1, 4, 7),
    'gym': (0, 3, 6),
}
# The original new-character initializer grants and activates infant toy 2000
# before the PatHouse tutorial.  Our authoritative S2C 0x0007 inventory import
# otherwise overwrites that local grant with zero and hides the BabyToy/play
# ring button.  The first feed tutorial specifically instructs the player to
# use baby food (item 1000), which is food slot 0.  Keep these server grants
# separate from the later toy/gym default loadouts.
SERVER_GRANTED_STARTER_ITEMS = {
    'food': (0,),
    'toy': (0,),
}
AZROK_ITEM_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Azrok.dat')
try:
    SHOP_ITEM_CATALOG = load_azrok_item_catalog(AZROK_ITEM_CATALOG_PATH)
except (OSError, ValueError) as exc:
    # Fail closed for purchases while keeping protocol analysis and already
    # restored rooms usable when the user's original data file is absent.
    print(f'[WARN] Shop transactions disabled: {exc}')
    SHOP_ITEM_CATALOG = {}
# CGamePeer's receive reassembly buffer is an inline 0x2000-byte region at
# +0x2050.  The four-byte frame header occupies the first four bytes, so any
# declared payload above 0x1FFC overwrites the cursor/remaining metadata at
# +0x4050/+0x4054.  RemoteActorPool_AllocUnusedSlot is independently fixed at
# 100 slots (indices 0..99).
CLIENT_RECEIVE_BUFFER_SIZE = 0x2000
MAX_SAFE_PACKET_PAYLOAD = CLIENT_RECEIVE_BUFFER_SIZE - 4
MAX_REMOTE_ACTORS_PER_CLIENT = 100
DEFAULT_ACTOR_ID = 1
DEFAULT_SPAWN_X = 0x0F7B
DEFAULT_SPAWN_Y = 0x00C3
# Original 0x006D9D48: six Plaza chairs, two seat (x, y, heading) triples each.
PLAZA_CHAIR_SEAT_TRANSFORMS = (
    ((-333, 1014, 132), (-255, 1071, 132)),
    ((-521, 788, 144), (-461, 876, 144)),
    ((-650, 545, 157), (-607, 643, 157)),
    ((-1200, -2903, -1), (-1201, -3018, -1)),
    ((-1264, -3192, -31), (-1321, -3286, -31)),
    ((-3851, 2110, -18), (-3890, 1995, -18)),
)
STATE1_OPCODE100_CALL_ORIGINAL = b'\xE8\xBF\xA8\xEC\xFF'
STATE1_OPCODE100_CALL_PATCHED = b'\x90' * 5
STATE1_OPCODE100_GUARD_SITE_VA = 0x615709
STATE1_OPCODE100_GUARD_SITE_ORIGINAL = b'\x89\x45\xF8\x8B\x45\x08'
STATE1_OPCODE100_GUARD_RESUME_VA = 0x61570F
STATE1_OPCODE100_GUARD_SKIP_VA = 0x6159E9
STATE1_OPCODE100_GUARD_STUB_RVA = 0x180
STATE1_SCENE_BOOTSTRAP_VA = 0x0050B400
STATE1_SELF_WRAPPER_GETTER_VA = 0x004D7FA0
STATE1_SELF_ACTOR_RECONCILE_VA = 0x00615AF0
STATE1_TAIL_CLOSE_GUARD_SITE_VA = 0x006159E9
STATE1_TAIL_CLOSE_GUARD_SITE_ORIGINAL = b'\x8B\x45\xFC\x8B\x48\x04\xE8\x95\xB9\xEC\xFF'
STATE1_TAIL_CLOSE_GUARD_RESUME_VA = 0x006159F4
STATE1_TAIL_CLOSE_GUARD_STUB_RVA = 0x340
STATE1_LOADING_CLOSE_VA = 0x004E1389
STATE1_OPCODE6E_SKIP_TAIL_SITE_VA = 0x0050B57F
STATE1_OPCODE6E_SKIP_TAIL_ORIGINAL = b'\xEB\x0E'
STATE1_OPCODE6E_SKIP_TAIL_PATCHED = b'\xEB\x28'
POPUP_CLOSE_SAFE_SITE_VA = 0x005CA6F0
POPUP_CLOSE_SAFE_SITE_ORIGINAL = b'\x8B\x4D\xFC\xE8\x23\x1C\xF1\xFF'
POPUP_CLOSE_SAFE_RESUME_VA = 0x005CA6F8
POPUP_CLOSE_SAFE_STUB_RVA = 0x700
POPUP_CHILD_NULL_LATCH_SITE_VA = 0x005CA8C4
POPUP_CHILD_NULL_LATCH_SITE_ORIGINAL = b'\x8B\x45\xFC\xC6\x80\x9C\x00\x00\x00\x01'
POPUP_CHILD_NULL_LATCH_RESUME_VA = 0x005CA8CE
POPUP_CHILD_NULL_LATCH_STUB_RVA = 0xAC0
POPUP_UPDATE_GATE_SITE_VA = 0x005CA6CC
POPUP_UPDATE_GATE_SITE_ORIGINAL = b'\x8B\x45\xFC\x0F\xB6\x88\x9B\x00\x00\x00\x85\xC9\x74\x08\x8B\x4D\xFC\xE8\x32\x14\xF1\xFF'
POPUP_UPDATE_GATE_RESUME_VA = 0x005CA6E2
POPUP_UPDATE_FN_VA = 0x005CAA50
POPUP_UPDATE_GATE_STUB_RVA = 0xB80
POPUP_FINALIZE_VCALL_SKIP_SITE_VA = 0x005CA9E1
POPUP_FINALIZE_VCALL_SKIP_SITE_ORIGINAL = b'\x8B\x45\xFC\x8B\x10\x8B\x4D\xFC\x8B\x42\x0C\xFF\xD0'
POPUP_FINALIZE_VCALL_SKIP_PATCHED = b'\xE9\x08\x00\x00\x00' + (b'\x90' * 8)
POPUP_BAR_UPDATE_GUARD_SITE_VA = 0x005CAC3C
POPUP_BAR_UPDATE_GUARD_SITE_ORIGINAL = b'\x8B\x45\xFC\x8B\x88\x9D\x00\x00\x00\xC7\x41\x1C\x00\x40\x00\x00'
POPUP_BAR_UPDATE_GUARD_RESUME_VA = 0x005CAC4C
POPUP_BAR_UPDATE_GUARD_SKIP_VA = 0x005CACA9
POPUP_BAR_UPDATE_GUARD_STUB_RVA = 0xB00
POPUP_TEARDOWN_SKIP_CALLS = (
    (0x005CA562, b'\xE8\x1F\x08\xF1\xFF', b'\x83\xC4\x04\xB0\x01'),
    (0x005CA5A4, b'\xE8\xDD\x07\xF1\xFF', b'\x83\xC4\x04\xB0\x01'),
)
EQUIP_POPUP_CAUTION_SKIP_SITE_VA = 0x005B7E17
EQUIP_POPUP_CAUTION_SKIP_SITE_ORIGINAL = b'\x68\x01\x04\x00\x00'
EQUIP_POPUP_CAUTION_SKIP_TARGET_VA = 0x005B7FD9
EQUIP_POPUP_OPEN_SKIP_SITE_VA = 0x005BC112
EQUIP_POPUP_OPEN_SKIP_SITE_ORIGINAL = (
    b'\x6A\x64\x6A\x64\x6A\x64\x6A\x01\x6A\x0F\x6A\x00\x6A\x00\x68\xFF\x00\x00\x00'
)
EQUIP_POPUP_OPEN_SKIP_TARGET_VA = 0x005BC158
SCENE_STAGE9_TUTORIAL_SKIP_SITE_VA = 0x00614525
SCENE_STAGE9_TUTORIAL_SKIP_SITE_ORIGINAL = (
    b'\x6A\xFF\x6A\x01\x68\x22\x04\x00\x00\x8B\x45\xFC\x8B\x48\x04'
    b'\xE8\x78\x88\xEC\xFF\x8B\xC8\xE8\xDA\x38\xEC\xFF\x8B\xC8\xE8\xB7\x4F\xEC\xFF'
)
SCENE_STAGE9_TUTORIAL_SKIP_TARGET_VA = 0x00614547
SCENE_STAGE_PROGRESS_SITE_VA = 0x006143C6
SCENE_STAGE_PROGRESS_SITE_ORIGINAL = b'\x8B\x45\xF4\x89\x45\xAC'
SCENE_STAGE_PROGRESS_RESUME_VA = 0x006143CC
SCENE_STAGE_PROGRESS_STUB_RVA = 0x480
SCENE_STAGE6_VCALL_SITE_ORIGINAL = b'\x8B\x55\xB8\x8B\x02\x8B\x4D\xB8\x8B\x50\x04\xFF\xD2'
SCENE_STAGE6_VCALL_MIN_TARGET = 0x00010000
SCENE_STAGE6_VCALL_GUARDS = (
    (0x006147A5, 0x006147B2, 0x380),
    (0x0061481D, 0x0061482A, 0x3C0),
    (0x0061485D, 0x0061486A, 0x400),
    (0x006148F9, 0x00614906, 0x440),
)
SCENE_WRAPPER_VCALL_SITE_ORIGINAL = b'\x8B\x4D\xFC\x8B\x11\x8B\x4D\xFC\x8B\x42\x04\xFF\xD0'
SCENE_WRAPPER_VCALL_GUARDS = (
    (0x005CE010, 0x005CE01D, 0x500),
    (0x005FC034, 0x005FC041, 0x540),
    (0x005F38C0, 0x005F38CD, 0x580),
    (0x005F2120, 0x005F212D, 0x5C0),
)
SCENE_POSTLOAD_VCALL_SITE_VA = 0x005BF2DF
SCENE_POSTLOAD_VCALL_SITE_ORIGINAL = b'\x8B\x4D\xFC\x8B\x11\x8B\x4D\xFC\x8B\x42\x04\xFF\xD0'
SCENE_POSTLOAD_VCALL_RESUME_VA = 0x005BF2EC
SCENE_POSTLOAD_VCALL_STUB_RVA = 0x600
SCENE_PHASE5_VCALL_GUARDS = (
    (0x005FEC26, b'\x8B\x45\xFC\x8B\x50\x08\x8B\x42\x08\xFF\xD0', 0x005FEC31, 0x740, 0x08, 0x08),
    (0x005FEC98, b'\x8B\x45\xFC\x8B\x50\x08\x8B\x42\x04\xFF\xD0', 0x005FECA3, 0x780, 0x08, 0x04),
)
SCENE_HUD_VCALL_GUARDS = (
    (0x00511C83, b'\x8B\x45\xFC\x8B\x50\x04\x8B\x42\x14\xFF\xD0', 0x00511C8E, 0x7C0, 0x04, 0x14),
    (0x00511CD7, b'\x8B\x45\xFC\x8B\x90\x16\x07\x00\x00\x8B\x42\x14\xFF\xD0', 0x00511CE5, 0x800, 0x716, 0x14),
    (0x00511D03, b'\x8B\x45\xFC\x8B\x90\x41\x06\x00\x00\x8B\x42\x14\xFF\xD0', 0x00511D11, 0x840, 0x641, 0x14),
    (0x00511D2F, b'\x8B\x45\xFC\x8B\x90\xEF\x07\x00\x00\x8B\x42\x14\xFF\xD0', 0x00511D3D, 0x880, 0x7EF, 0x14),
    (0x00511D77, b'\x8B\x45\xFC\x8B\x90\x7E\x16\x00\x00\x8B\x42\x04\xFF\xD0', 0x00511D85, 0x8C0, 0x167E, 0x04),
    (0x00511DA3, b'\x8B\x45\xFC\x8B\x90\x15\x13\x00\x00\x8B\x42\x14\xFF\xD0', 0x00511DB1, 0x900, 0x1315, 0x14),
    (0x00511DBA, b'\x8B\x45\xFC\x8B\x90\xA0\x01\x00\x00\x8B\x42\x14\xFF\xD0', 0x00511DC8, 0x940, 0x01A0, 0x14),
    (0x00511DD1, b'\x8B\x45\xFC\x8B\x90\x09\x18\x00\x00\x8B\x42\x14\xFF\xD0', 0x00511DDF, 0x980, 0x1809, 0x14),
)
SCENE_MANAGER_VCALL_GUARDS = (
    (0x00614A27, b'\x8B\x4D\xB8\x8B\x11\x8B\x4D\xB8\x8B\x42\x0C\xFF\xD0', 0x00614A34, 0x9C0, 0x0C),
    (0x00614A42, b'\x8B\x4D\xB8\x8B\x11\x8B\x4D\xB8\x8B\x42\x0C\xFF\xD0', 0x00614A4F, 0xA00, 0x0C),
    (0x00614A5D, b'\x8B\x4D\xB8\x8B\x11\x8B\x4D\xB8\x8B\x42\x0C\xFF\xD0', 0x00614A6A, 0xA40, 0x0C),
    (0x00614B08, b'\x8B\x4D\xB8\x8B\x11\x8B\x4D\xB8\x8B\x42\x0C\xFF\xD0', 0x00614B15, 0xA80, 0x0C),
)
SCENE_POSTLOAD_READY_FORCE_SITE_VA = 0x00614547
SCENE_POSTLOAD_READY_FORCE_SITE_ORIGINAL = b'\x8B\x45\xFC\x8B\x48\x04\xE8\x42\xCD\xEC\xFF'
SCENE_POSTLOAD_READY_FORCE_RESUME_VA = 0x00614552
SCENE_POSTLOAD_READY_FORCE_STUB_RVA = 0x680
SCENE_POSTLOAD_READY_FIELD_OFFSET = 0x31946
SCENE_POSTLOAD_CLEANUP_BRANCH_VA = 0x00614554
SCENE_POSTLOAD_CLEANUP_BRANCH_ORIGINAL = b'\x75\x22'
SCENE_POSTLOAD_CLEANUP_BRANCH_PATCHED = b'\xEB\x22'
SCENE_LOCAL_ENTITY_GUARD_SITE_VA = 0x005F3AF1
SCENE_LOCAL_ENTITY_GUARD_SITE_ORIGINAL = b'\x8B\x45\xF8\x8B\x48\x10'
SCENE_LOCAL_ENTITY_GUARD_RESUME_VA = 0x005F3AF7
SCENE_LOCAL_ENTITY_GUARD_SKIP_VA = 0x005F3B48
SCENE_LOCAL_ENTITY_GUARD_STUB_RVA = 0xBC0
SCENE_SELF_VISUAL_GUARD_SITE_VA = 0x0052515B
SCENE_SELF_VISUAL_GUARD_SITE_ORIGINAL = b'\x8B\x55\xFC\x8B\x8A\x99\x00\x00\x00\x89\x41\x10'
SCENE_SELF_VISUAL_GUARD_RESUME_VA = 0x00525167
SCENE_SELF_VISUAL_GUARD_SKIP_VA = 0x005251A7
SCENE_SELF_VISUAL_GUARD_STUB_RVA = 0xC00
UI_CHILD_STATE_GUARD_SITE_VA = 0x0051B0E0
UI_CHILD_STATE_GUARD_SITE_ORIGINAL = b'\x55\x8B\xEC\x83\xEC\x44'
UI_CHILD_STATE_GUARD_STUB_RVA = 0xD00
SCENE_SKY_GUARD_SITE_VA = 0x006084CA
SCENE_SKY_GUARD_SITE_ORIGINAL = b'\x8B\x48\x39\xC7\x41\x34\x00\x04\x0A\x00'
SCENE_SKY_GUARD_RESUME_VA = 0x006084D4
SCENE_SKY_GUARD_SKIP_VA = 0x006084E7
SCENE_SKY_GUARD_STUB_RVA = 0x220
SCENE_WATER_GUARD_SITE_VA = 0x0060E8E6
SCENE_WATER_GUARD_SITE_ORIGINAL = (
    b'\x6A\x64\x8B\x45\xF8\x8B\x4D\xFC\x8B\x94\x81\x71\x0C\x00\x00\x52'
    b'\x8B\x45\xF8\x8B\x4D\xFC\x8B\x94\x81\x59\x0C\x00\x00\x52\xE8\x6A'
    b'\x22\xED\xFF\x83\xC4\x0C'
)
SCENE_WATER_GUARD_RESUME_VA = 0x0060E90C
SCENE_WATER_GUARD_STUB_RVA = 0x280
ENT_PLAYLOOP_VA = 0x004E0B73
HOOK_LOG_GM_RVA = 0x118
HOOK_LOG_OPCODE100_COUNT_RVA = 0x11C
HOOK_LOG_SELF_INIT_COUNT_RVA = 0x120
HOOK_LOG_SCENE_STAGE_RVA = 0x124
HOOK_LOG_SCENE_STAGE_COUNT_RVA = 0x128

def _load_shipped_content_stats():
    """Load the 57 current values shipped in init.csv using lgc.tmp order."""
    init_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'init.csv')
    rows = []
    with open(init_path, 'r', encoding='cp949', newline='') as init_file:
        for line_number, line in enumerate(init_file, 1):
            if not line.strip():
                continue
            columns = [part.strip() for part in line.rstrip('\r\n').split(',')]
            if len(columns) != 4:
                raise ValueError(
                    f'{init_path}:{line_number}: expected name,current,min,max'
                )
            try:
                current_value = int(columns[1], 10)
                int(columns[2], 10)
                int(columns[3], 10)
            except ValueError as exc:
                raise ValueError(
                    f'{init_path}:{line_number}: non-integer stat field'
                ) from exc
            if current_value < 0 or current_value > 0xFFFF:
                raise ValueError(
                    f'{init_path}:{line_number}: current value outside u16'
                )
            rows.append((columns[0], current_value))

    if len(rows) != 55:
        raise ValueError(f'{init_path}: expected 55 stat rows, got {len(rows)}')

    # Guard the exact insertion boundary and the three content indices that
    # independently anchor the corrected schema.
    expected_names = {
        24: '청소카운터',
        25: '용변카운터',
        30: '아령경험',
        53: '펫진화',
        54: '펫',
    }
    for row_index, expected_name in expected_names.items():
        if rows[row_index][0] != expected_name:
            raise ValueError(
                f'{init_path}: row {row_index + 1} expected {expected_name!r}, '
                f'got {rows[row_index][0]!r}'
            )

    current_values = [value for _name, value in rows]
    # lgc.tmp adds IQ before init.csv and meal/food counter between the
    # cleanup and toilet counters.  The result is indices 0..56 inclusive:
    # idx32=dumbbell, idx55=pet evolution, idx56=pet.
    stats = [0] + current_values[:25] + [0] + current_values[25:]
    if len(stats) != 57:
        raise AssertionError(f'corrected shipped stat count is {len(stats)}, expected 57')
    return tuple(stats)


SHIPPED_CONTENT_STATS = _load_shipped_content_stats()
MINIMAL_CONTENT_STATS = {
    1: 1,
    3: 50,
    4: 50,
    5: 50,
    6: 50,
    7: 10,
    8: 50,
    9: 100,
}
def _build_original_fresh_content_stats(char_type, seed_material=b''):
    """Mirror Stats_ApplyLocalArchetypeSeed@005A3020 for a fresh Azron.

    The native reset path uses C ``rand()`` for IQ and hygiene.  Replaying its
    process-global RNG on the server would make an account change values after
    an interrupted first login, so derive the same in-range results from the
    private character identity.  Every fixed value and both random ranges are
    taken directly from the decompiled client routine; only the RNG source is
    a deterministic preservation-server policy.
    """
    try:
        species = int(char_type)
    except (TypeError, ValueError):
        species = AZRON_SPECIES
    if species not in range(4):
        species = AZRON_SPECIES & 0x03
    if isinstance(seed_material, str):
        seed_material = seed_material.encode('utf-8', errors='surrogatepass')
    seed_material = bytes(seed_material or b'')
    digest = hashlib.sha256(
        b'azrok-original-fresh-stats-v1\0' + bytes((species,)) + seed_material
    ).digest()

    stats = [0] * 70
    stats[1] = 1
    stats[3] = 100
    stats[5] = 100
    stats[6] = 100
    stats[9] = 300
    for stat_id in range(18, 25):
        stats[stat_id] = 100

    archetypes = {
        0: ((50, 50, 70, 70, 60, 60, 50, 50), (60, 20), (20, 70)),
        1: ((50, 50, 50, 50, 60, 60, 70, 70), (40, 20), (30, 60)),
        2: ((50, 50, 30, 30, 40, 40, 50, 50), (20, 20), (40, 50)),
        3: ((60, 60, 60, 60, 40, 40, 30, 30), (40, 20), (20, 70)),
    }
    baselines, hygiene_range, iq_range = archetypes[species]
    stats[10:18] = baselines
    stats[4] = hygiene_range[0] + digest[0] % hygiene_range[1]
    stats[0] = iq_range[0] + digest[1] % iq_range[1]
    return tuple(stats)


def _fresh_content_seed_material(proto_state):
    """Return one stable account/slot/name seed without exposing credentials."""
    proto_state = proto_state or {}
    parts = []
    for key in ('account_raw', 'char_name_raw'):
        value = proto_state.get(key) or b''
        if isinstance(value, str):
            value = value.encode('cp949', errors='ignore')
        parts.append(bytes(value).split(b'\0', 1)[0])
    parts.append(str(int(proto_state.get('character_slot', 0)) & 0x03).encode('ascii'))
    return b'\0'.join(parts) if any(parts[:2]) else b''


# Production ``playable`` now means the native fresh-character seed, not the
# old level-25 demo with only progression counters zeroed.  Keep the constant
# as the identity-free Paz fixture used by isolated packet-builder tests.
PLAYABLE_CONTENT_STATS = _build_original_fresh_content_stats(AZRON_SPECIES)


ITEM_REGISTRY_000A_BINARY_DEFAULTS = {
    # These are the client binary's built-in registry defaults from:
    # DAT_006e1110 / DAT_006e1220 / DAT_006e1270 / DAT_006e12b0 /
    # DAT_006e13b0 / DAT_006e13c8 / DAT_006e13d0.
    'group0': [
        1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000,
        2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000,
    ],
    'group1': [200, 500, 200, 500, 200, 500],
    'group2': [200, 500, 200, 500, 200],
    'group3': [
        30, 30, 30, 40, 40, 100, 100, 100, 100, 100, 100, 100, 100, 100,
        200, 200, 200, 200, 200, 200, 200, 200, 200, 300, 300, 300, 300,
        300, 300, 300, 300, 300,
    ],
    'group4': [100, 200, 300],
    'group5': [200],
    'group6': [100, 500, 100, 500, 100, 500],
}

ITEM_REGISTRY_000A_DIAGNOSTIC_CUSTOM_VALUES = {
    # Historical guessed values retained only for explicit A/B diagnostics.
    'group0': [
        1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000,
        2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000, 1000, 2000,
    ],
    'group1': [500, 600, 500, 600, 500, 600],
    'group2': list(ITEM_REGISTRY_000A_BINARY_DEFAULTS['group2']),
    'group3': [
        500, 0, 500, 500, 80, 500, 500, 500, 500, 500, 500, 500, 500, 500,
        500, 30, 30, 30, 30, 30, 70, 70, 70, 70, 70, 110, 110, 110, 110,
        110, 1, 2,
    ],
    'group4': [80, 80, 0],
    'group5': list(ITEM_REGISTRY_000A_BINARY_DEFAULTS['group5']),
    'group6': list(ITEM_REGISTRY_000A_BINARY_DEFAULTS['group6']),
}
ITEM_REGISTRY_000A_DIAGNOSTIC_HIGH_OVERRIDES = {
    # Historical diagnostic mutation.  These are item-domain values, not
    # character resources; never apply them without the explicit env switch.
    'group1': [500, 500, 500, 500, 500, 500],
    'group2': [500, 500, 500, 500, 500],
    'group4': [300, 300, 300],
    'group5': [500],
    'group6': [500, 500, 500, 500, 500, 500],
}

STAT_TABLE_0011_DEFAULTS = [
    0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500, 5500, 6600, 7800,
    9100, 10500, 12000, 13600, 15300, 17100, 19000, 21000, 23100, 25300,
    27600, 30000, 32500, 35100, 37800, 40600, 43500, 60001,
]

# ═══════════════════════════════════════════════════════════
#  Runtime Patches  (applied after IAT hook is installed)
# ═══════════════════════════════════════════════════════════
DISPATCH_FLAG_CHECK_VA  = 0x591DC7   # JZ +0x16 (skip processing if flag=0)
STATE1_OPCODE100_CALL_VA = 0x6137C1  # CALL thunk_FUN_00615650 inside state-1 opcode 100 case
# Original bytes: 74 16  →  Patch to: 90 90 (NOP NOP = always process)

def apply_runtime_patches(hProcess, hook_base):
    """
    Patch the packet dispatch function to ALWAYS process incoming packets,
    bypassing the this+0x4076 flag check that may prevent packet handling.
    """
    old_prot = wt.DWORD(0)
    patched_any = False

    # Patch 1: Force dispatch to always process packets
    # VA 0x591DC7: change JZ +0x16 (74 16) → NOP NOP (90 90)
    addr = DISPATCH_FLAG_CHECK_VA
    original = read_mem(hProcess, addr, 2)
    if original == b'\x74\x16':
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(addr), 2,
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        write_mem(hProcess, addr, b'\x90\x90')
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(addr), 2,
                                   old_prot.value, ctypes.byref(old_prot))
        print("    [PATCH] Dispatch flag bypass applied (JZ→NOP)")
        patched_any = True
    elif original == b'\x90\x90':
        print("    [PATCH] Dispatch flag bypass already present")
        patched_any = True
    else:
        print(f"    [WARN] Unexpected bytes at dispatch: {original.hex() if original else 'None'}")

    # ── All rescue/guard patches REMOVED ──
    # Goal: server sends correct packets so the game runs naturally.
    # Previous patches (null guards, vcall guards, tail guards, ready force, etc.)
    # were workarounds for incorrect server data. With correct protocol implementation
    # (S->C 0x0004 calibration, proper 0x0007 stats, correct 0x0003 path), these
    # should not be needed.
    #
    # Removed patches:
    #   - state1_opcode100_null_guard (reentrant bootstrap)
    #   - scene_sky_null_guard, scene_water_null_guard
    #   - state1_tail_close_guard
    #   - scene_postload_ready_force (replaced by S->C 0x0004 calibration)
    #   - scene_stage6_vcall_guards, scene_wrapper_vcall_guards
    #   - scene_local_entity_guard, scene_self_visual_guard
    #   - scene_postload_vcall_guard, scene_phase5_vcall_guards
    #   - scene_hud_vcall_guards, scene_manager_vcall_guards
    #   - state1_opcode6e_skip_tail
    #   - popup hard/UI bypasses
    print("    [INFO] Rescue patches removed - relying on correct server protocol")

    # Gate NOP (Patch 2) REMOVED: server no longer sends S->C 0x0002 during login.
    # Instead, server sends S->C 0x0003 + S->C 0x0007 proactively (no transition trigger needed).
    # Gate stays -1 from constructor. Room loading pipeline runs naturally.

    # Force nexus=200 AFTER engine_open (WDL script may have overridden our default)
    # The nexus integer at 0x102FC540 controls buffer allocation in level_load
    ACKNEX_NEXUS_INT_VA = 0x102FC540
    old_prot_nx2 = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ACKNEX_NEXUS_INT_VA), 4,
                               PAGE_READWRITE, ctypes.byref(old_prot_nx2))
    old_nexus = read_dword(hProcess, ACKNEX_NEXUS_INT_VA)
    write_mem(hProcess, ACKNEX_NEXUS_INT_VA, struct.pack('<I', 200))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ACKNEX_NEXUS_INT_VA), 4,
                               old_prot_nx2.value, ctypes.byref(old_prot_nx2))
    new_nexus = read_dword(hProcess, ACKNEX_NEXUS_INT_VA)
    print(f"    [PATCH] Acknex nexus forced: {old_nexus} -> {new_nexus} (at runtime, post engine_open)")

    # All popup/UI/stage9 rescue patches removed — server protocol handles these naturally

    return patched_any


def set_state1_opcode100_handler_skip(hProcess, enabled):
    """
    Toggle the state-1 opcode 100 body call at 0x6137C1.

    enabled=True  -> NOP the call so opcode 100 only flips logic state to 1
    enabled=False -> restore the original CALL thunk_FUN_00615650
    """
    addr = STATE1_OPCODE100_CALL_VA
    current = read_mem(hProcess, addr, 5)
    if current not in (STATE1_OPCODE100_CALL_ORIGINAL, STATE1_OPCODE100_CALL_PATCHED):
        return False

    target = STATE1_OPCODE100_CALL_PATCHED if enabled else STATE1_OPCODE100_CALL_ORIGINAL
    if current == target:
        return True

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(addr), 5,
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, addr, target))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(addr), 5,
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, addr, 5)
    return ok


def install_state1_opcode100_null_guard_safe(hProcess, hook_base):
    """Null-guard only: if self entity is null, skip to safe resume.
    Does NOT call FUN_0050B400 (prevents reentrant bootstrap)."""
    site = STATE1_OPCODE100_GUARD_SITE_VA
    current = read_mem(hProcess, site, len(STATE1_OPCODE100_GUARD_SITE_ORIGINAL))
    if current != STATE1_OPCODE100_GUARD_SITE_ORIGINAL:
        return False

    stub_addr = hook_base + STATE1_OPCODE100_GUARD_STUB_RVA
    gm_log_addr = hook_base + HOOK_LOG_GM_RVA
    hit_log_addr = hook_base + HOOK_LOG_OPCODE100_COUNT_RVA
    stub = bytearray()
    # Replicate original: mov [ebp-8], eax; then test eax
    stub += b'\x89\x45\xF8'  # mov [ebp-8], eax (original displaced instruction)
    stub += b'\x52'          # push edx (save)
    stub += b'\x8B\x55\xFC'  # mov edx, [ebp-4]
    stub += b'\x8B\x52\x04'  # mov edx, [edx+4]
    stub += b'\x89\x15' + struct.pack('<I', gm_log_addr)  # mov [gm_log], edx
    stub += b'\xFF\x05' + struct.pack('<I', hit_log_addr)  # inc [hit_count]
    stub += b'\x5A'          # pop edx
    stub += b'\x85\xC0'      # test eax, eax
    # If eax != 0 (entity exists), resume normal path
    stub += b'\x0F\x85' + struct.pack(
        '<i',
        STATE1_OPCODE100_GUARD_RESUME_VA - (stub_addr + len(stub) + 6)
    )
    # eax == 0 (entity null): just skip to safe exit, NO bootstrap call
    stub += b'\x8B\x45\x08'  # mov eax, [ebp+8] (restore payload ptr for skip path)
    stub += b'\xE9' + struct.pack(
        '<i',
        STATE1_OPCODE100_GUARD_SKIP_VA - (stub_addr + len(stub) + 5)
    )

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    # Patch call site to jump to our stub
    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5))
    patch += b'\x90' * (len(STATE1_OPCODE100_GUARD_SITE_ORIGINAL) - 5)
    old_prot2 = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot2))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot2.value, ctypes.byref(old_prot2))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_state1_opcode100_null_guard(hProcess, hook_base):
    site = STATE1_OPCODE100_GUARD_SITE_VA
    current = read_mem(hProcess, site, len(STATE1_OPCODE100_GUARD_SITE_ORIGINAL))
    if current != STATE1_OPCODE100_GUARD_SITE_ORIGINAL:
        return False

    stub_addr = hook_base + STATE1_OPCODE100_GUARD_STUB_RVA
    gm_log_addr = hook_base + HOOK_LOG_GM_RVA
    hit_log_addr = hook_base + HOOK_LOG_OPCODE100_COUNT_RVA
    self_init_count_addr = hook_base + HOOK_LOG_SELF_INIT_COUNT_RVA
    stub = bytearray()
    stub += b'\x89\x45\xF8'  # mov [ebp-8], eax
    stub += b'\x52'          # push edx
    stub += b'\x8B\x55\xFC'  # mov edx, [ebp-4]
    stub += b'\x8B\x52\x04'  # mov edx, [edx+4]
    stub += b'\x89\x15' + struct.pack('<I', gm_log_addr)          # mov [gm_log], edx
    stub += b'\xFF\x05' + struct.pack('<I', hit_log_addr)         # inc dword ptr [hit_log]
    stub += b'\x5A'          # pop edx
    stub += b'\x85\xC0'      # test eax, eax
    stub += b'\x0F\x85' + struct.pack(
        '<i',
        STATE1_OPCODE100_GUARD_RESUME_VA - (stub_addr + len(stub) + 6)
    )
    stub += b'\xFF\x05' + struct.pack('<I', self_init_count_addr) # inc dword ptr [bootstrap_count]
    stub += b'\x60'          # pushad
    stub += b'\x8B\x0D' + struct.pack('<I', gm_log_addr)          # mov ecx, [gm_log]
    stub += b'\x6A\x6E'      # push 0x6E (Plaza bootstrap - produces C->S 0x0064)
    stub += b'\xB8' + struct.pack('<I', STATE1_SCENE_BOOTSTRAP_VA)      # mov eax, FUN_0050B400
    stub += b'\xFF\xD0'      # call eax (this=gm, arg=0x6E, callee does RET 4)
    stub += b'\x8B\x45\x08'  # mov eax, [ebp+8]
    stub += b'\xFF\x70\x01'  # push dword ptr [eax+1]   ; authoritative actor id from S->C 0x0064
    stub += b'\x8B\x0D' + struct.pack('<I', gm_log_addr)          # mov ecx, [gm_log]
    stub += b'\xB8' + struct.pack('<I', STATE1_SELF_WRAPPER_GETTER_VA)   # mov eax, getter
    stub += b'\xFF\xD0'      # call eax
    stub += b'\x8B\xC8'      # mov ecx, eax
    stub += b'\xB8' + struct.pack('<I', STATE1_SELF_ACTOR_RECONCILE_VA)  # mov eax, FUN_00615AF0
    stub += b'\xFF\xD0'      # call eax
    stub += b'\x61'          # popad
    stub += b'\x8B\x45\x08'  # mov eax, [ebp+8]
    stub += b'\xE9' + struct.pack(
        '<i',
        STATE1_OPCODE100_GUARD_SKIP_VA - (stub_addr + len(stub) + 5)
    )

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + b'\x90'
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_scene_sky_null_guard(hProcess, hook_base):
    site = SCENE_SKY_GUARD_SITE_VA
    current = read_mem(hProcess, site, len(SCENE_SKY_GUARD_SITE_ORIGINAL))
    if current != SCENE_SKY_GUARD_SITE_ORIGINAL:
        return False

    stub_addr = hook_base + SCENE_SKY_GUARD_STUB_RVA
    stub = bytearray()
    stub += b'\x8B\x48\x39'  # mov ecx, [eax+0x39]
    stub += b'\x85\xC9'      # test ecx, ecx
    stub += b'\x74\x0C'      # jz skip the whole tail if the sky entity is still missing
    stub += b'\xC7\x41\x34\x00\x04\x0A\x00'  # mov dword ptr [ecx+0x34], 0x000A0400
    stub += b'\xE9' + struct.pack(
        '<i',
        SCENE_SKY_GUARD_RESUME_VA - (stub_addr + len(stub) + 5)
    )
    stub += b'\xE9' + struct.pack(
        '<i',
        SCENE_SKY_GUARD_SKIP_VA - (stub_addr + len(stub) + 5)
    )

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(SCENE_SKY_GUARD_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_scene_water_null_guard(hProcess, hook_base):
    site = SCENE_WATER_GUARD_SITE_VA
    current = read_mem(hProcess, site, len(SCENE_WATER_GUARD_SITE_ORIGINAL))
    if current != SCENE_WATER_GUARD_SITE_ORIGINAL:
        return False

    stub_addr = hook_base + SCENE_WATER_GUARD_STUB_RVA
    stub = bytearray()
    stub += b'\x56'  # push esi
    stub += b'\x57'  # push edi
    stub += b'\x8B\x45\xF8'  # mov eax, [ebp-8]
    stub += b'\x8B\x4D\xFC'  # mov ecx, [ebp-4]
    stub += b'\x8B\xB4\x81\x71\x0C\x00\x00'  # mov esi, [ecx+eax*4+0xC71] ; sound
    stub += b'\x8B\xBC\x81\x59\x0C\x00\x00'  # mov edi, [ecx+eax*4+0xC59] ; entity
    stub += b'\x85\xF6'      # test esi, esi
    stub += b'\x74\x14'      # jz no_play
    stub += b'\x85\xFF'      # test edi, edi
    stub += b'\x74\x10'      # jz no_play
    stub += b'\x6A\x64'      # push 0x64
    stub += b'\x56'          # push esi
    stub += b'\x57'          # push edi
    stub += b'\xB8' + struct.pack('<I', ENT_PLAYLOOP_VA)  # mov eax, ent_playloop
    stub += b'\xFF\xD0'      # call eax
    stub += b'\x83\xC4\x0C'  # add esp, 0xC
    stub += b'\xEB\x02'      # jmp done
    stub += b'\x33\xC0'      # no_play: xor eax, eax
    stub += b'\x5F'          # done: pop edi
    stub += b'\x5E'          # pop esi
    stub += b'\xE9' + struct.pack(
        '<i',
        SCENE_WATER_GUARD_RESUME_VA - (stub_addr + len(stub) + 5)
    )

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(SCENE_WATER_GUARD_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_state1_tail_close_guard(hProcess, hook_base):
    site = STATE1_TAIL_CLOSE_GUARD_SITE_VA
    current = read_mem(hProcess, site, len(STATE1_TAIL_CLOSE_GUARD_SITE_ORIGINAL))
    if current != STATE1_TAIL_CLOSE_GUARD_SITE_ORIGINAL:
        return False

    stub_addr = hook_base + STATE1_TAIL_CLOSE_GUARD_STUB_RVA
    gm_log_addr = hook_base + HOOK_LOG_GM_RVA
    stub = bytearray()
    stub += b'\x8B\x0D' + struct.pack('<I', gm_log_addr)  # mov ecx, [gm_log]
    stub += b'\x85\xC9'                                  # test ecx, ecx
    stub += b'\x74\x07'                                  # jz skip the close call if gm was never captured
    stub += b'\xB8' + struct.pack('<I', STATE1_LOADING_CLOSE_VA)  # mov eax, thunk_FUN_0050A840
    stub += b'\xFF\xD0'                                  # call eax
    stub += b'\xE9' + struct.pack(
        '<i',
        STATE1_TAIL_CLOSE_GUARD_RESUME_VA - (stub_addr + len(stub) + 5)
    )

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(STATE1_TAIL_CLOSE_GUARD_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_scene_stage_progress_tap(hProcess, hook_base):
    site = SCENE_STAGE_PROGRESS_SITE_VA
    current = read_mem(hProcess, site, len(SCENE_STAGE_PROGRESS_SITE_ORIGINAL))
    if current != SCENE_STAGE_PROGRESS_SITE_ORIGINAL:
        return False

    stub_addr = hook_base + SCENE_STAGE_PROGRESS_STUB_RVA
    stage_log_addr = hook_base + HOOK_LOG_SCENE_STAGE_RVA
    stage_count_addr = hook_base + HOOK_LOG_SCENE_STAGE_COUNT_RVA
    stub = bytearray()
    stub += b'\x8B\x45\xF4'                                  # mov eax, [ebp-0xc]
    stub += b'\x89\x45\xAC'                                  # mov [ebp-0x54], eax
    stub += b'\xA3' + struct.pack('<I', stage_log_addr)      # mov [stage_log], eax
    stub += b'\xFF\x05' + struct.pack('<I', stage_count_addr) # inc dword ptr [stage_count]
    stub += b'\xE9' + struct.pack(
        '<i',
        SCENE_STAGE_PROGRESS_RESUME_VA - (stub_addr + len(stub) + 5)
    )

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + b'\x90'
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_scene_stage6_vcall_guards(hProcess, hook_base):
    old_prot = wt.DWORD(0)

    for site, resume_va, stub_rva in SCENE_STAGE6_VCALL_GUARDS:
        current = read_mem(hProcess, site, len(SCENE_STAGE6_VCALL_SITE_ORIGINAL))
        if current != SCENE_STAGE6_VCALL_SITE_ORIGINAL:
            return False

        stub_addr = hook_base + stub_rva
        stub = bytearray()
        stub += b'\x8B\x55\xB8'  # mov edx, [ebp-0x48]
        stub += b'\x85\xD2'      # test edx, edx
        stub += b'\x0F\x84' + struct.pack('<i', 0)  # jz skip
        skip_jz_1 = len(stub) - 4
        stub += b'\x8B\x02'      # mov eax, [edx]
        stub += b'\x85\xC0'      # test eax, eax
        stub += b'\x0F\x84' + struct.pack('<i', 0)  # jz skip
        skip_jz_2 = len(stub) - 4
        stub += b'\x8B\xCA'      # mov ecx, edx
        stub += b'\x8B\x50\x04'  # mov edx, [eax+4]
        stub += b'\x81\xFA' + struct.pack('<I', SCENE_STAGE6_VCALL_MIN_TARGET)  # cmp edx, 0x10000
        stub += b'\x0F\x82' + struct.pack('<i', 0)  # jb skip
        skip_jb = len(stub) - 4
        stub += b'\xFF\xD2'      # call edx
        stub += b'\xE9' + struct.pack('<i', 0)  # jmp resume
        resume_after_call = len(stub) - 4
        skip_offset = len(stub)
        stub += b'\x83\xC4\x04'  # add esp, 4 ; discard already-pushed argument
        stub += b'\xE9' + struct.pack('<i', 0)  # jmp resume
        resume_after_skip = len(stub) - 4

        struct.pack_into('<i', stub, skip_jz_1, stub_addr + skip_offset - (stub_addr + skip_jz_1 + 4))
        struct.pack_into('<i', stub, skip_jz_2, stub_addr + skip_offset - (stub_addr + skip_jz_2 + 4))
        struct.pack_into('<i', stub, skip_jb, stub_addr + skip_offset - (stub_addr + skip_jb + 4))
        struct.pack_into('<i', stub, resume_after_call, resume_va - (stub_addr + resume_after_call + 4))
        struct.pack_into('<i', stub, resume_after_skip, resume_va - (stub_addr + resume_after_skip + 4))

        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        if not write_mem(hProcess, stub_addr, bytes(stub)):
            kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                       old_prot.value, ctypes.byref(old_prot))
            return False
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, stub_addr, len(stub))

        patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(SCENE_STAGE6_VCALL_SITE_ORIGINAL) - 5))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        ok = bool(write_mem(hProcess, site, patch))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, site, len(patch))
        if not ok:
            return False

    return True


def install_scene_wrapper_vcall_guards(hProcess, hook_base):
    old_prot = wt.DWORD(0)

    for site, resume_va, stub_rva in SCENE_WRAPPER_VCALL_GUARDS:
        current = read_mem(hProcess, site, len(SCENE_WRAPPER_VCALL_SITE_ORIGINAL))
        if current != SCENE_WRAPPER_VCALL_SITE_ORIGINAL:
            return False

        stub_addr = hook_base + stub_rva
        stub = bytearray()
        stub += b'\x8B\x4D\xFC'  # mov ecx, [ebp-4]
        stub += b'\x85\xC9'      # test ecx, ecx
        stub += b'\x0F\x84' + struct.pack('<i', 0)  # jz skip
        skip_jz_1 = len(stub) - 4
        stub += b'\x8B\x11'      # mov edx, [ecx]
        stub += b'\x85\xD2'      # test edx, edx
        stub += b'\x0F\x84' + struct.pack('<i', 0)  # jz skip
        skip_jz_2 = len(stub) - 4
        stub += b'\x8B\x42\x04'  # mov eax, [edx+4]
        stub += b'\x3D' + struct.pack('<I', SCENE_STAGE6_VCALL_MIN_TARGET)  # cmp eax, 0x10000
        stub += b'\x0F\x82' + struct.pack('<i', 0)  # jb skip
        skip_jb = len(stub) - 4
        stub += b'\xFF\xD0'      # call eax
        stub += b'\xE9' + struct.pack('<i', 0)  # jmp resume
        resume_after_call = len(stub) - 4
        skip_offset = len(stub)
        stub += b'\x83\xC4\x04'  # add esp, 4 ; emulate callee cleanup when skipping
        stub += b'\xE9' + struct.pack('<i', 0)  # jmp resume
        resume_after_skip = len(stub) - 4

        struct.pack_into('<i', stub, skip_jz_1, stub_addr + skip_offset - (stub_addr + skip_jz_1 + 4))
        struct.pack_into('<i', stub, skip_jz_2, stub_addr + skip_offset - (stub_addr + skip_jz_2 + 4))
        struct.pack_into('<i', stub, skip_jb, stub_addr + skip_offset - (stub_addr + skip_jb + 4))
        struct.pack_into('<i', stub, resume_after_call, resume_va - (stub_addr + resume_after_call + 4))
        struct.pack_into('<i', stub, resume_after_skip, resume_va - (stub_addr + resume_after_skip + 4))

        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        if not write_mem(hProcess, stub_addr, bytes(stub)):
            kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                       old_prot.value, ctypes.byref(old_prot))
            return False
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, stub_addr, len(stub))

        patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(SCENE_WRAPPER_VCALL_SITE_ORIGINAL) - 5))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        ok = bool(write_mem(hProcess, site, patch))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, site, len(patch))
        if not ok:
            return False

    return True


def install_scene_postload_vcall_guard(hProcess, hook_base):
    site = SCENE_POSTLOAD_VCALL_SITE_VA
    current = read_mem(hProcess, site, len(SCENE_POSTLOAD_VCALL_SITE_ORIGINAL))
    if current != SCENE_POSTLOAD_VCALL_SITE_ORIGINAL:
        return False

    stub_addr = hook_base + SCENE_POSTLOAD_VCALL_STUB_RVA
    old_prot = wt.DWORD(0)
    stub = bytearray()
    stub += b'\x8B\x4D\xFC'  # mov ecx, [ebp-4]
    stub += b'\x85\xC9'      # test ecx, ecx
    stub += b'\x0F\x84' + struct.pack('<i', 0)  # jz skip
    skip_jz_1 = len(stub) - 4
    stub += b'\x8B\x11'      # mov edx, [ecx]
    stub += b'\x85\xD2'      # test edx, edx
    stub += b'\x0F\x84' + struct.pack('<i', 0)  # jz skip
    skip_jz_2 = len(stub) - 4
    stub += b'\x8B\x42\x04'  # mov eax, [edx+4]
    stub += b'\x3D' + struct.pack('<I', SCENE_STAGE6_VCALL_MIN_TARGET)  # cmp eax, 0x10000
    stub += b'\x0F\x82' + struct.pack('<i', 0)  # jb skip
    skip_jb = len(stub) - 4
    stub += b'\xFF\xD0'      # call eax
    stub += b'\xE9' + struct.pack('<i', 0)  # jmp resume
    resume_after_call = len(stub) - 4
    skip_offset = len(stub)
    stub += b'\x83\xC4\x04'  # add esp, 4 ; emulate callee cleanup when skipping
    stub += b'\xE9' + struct.pack('<i', 0)  # jmp resume
    resume_after_skip = len(stub) - 4

    struct.pack_into('<i', stub, skip_jz_1, stub_addr + skip_offset - (stub_addr + skip_jz_1 + 4))
    struct.pack_into('<i', stub, skip_jz_2, stub_addr + skip_offset - (stub_addr + skip_jz_2 + 4))
    struct.pack_into('<i', stub, skip_jb, stub_addr + skip_offset - (stub_addr + skip_jb + 4))
    struct.pack_into('<i', stub, resume_after_call, SCENE_POSTLOAD_VCALL_RESUME_VA - (stub_addr + resume_after_call + 4))
    struct.pack_into('<i', stub, resume_after_skip, SCENE_POSTLOAD_VCALL_RESUME_VA - (stub_addr + resume_after_skip + 4))

    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(SCENE_POSTLOAD_VCALL_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_scene_local_entity_guard(hProcess, hook_base):
    site = SCENE_LOCAL_ENTITY_GUARD_SITE_VA
    resume = SCENE_LOCAL_ENTITY_GUARD_RESUME_VA
    skip = SCENE_LOCAL_ENTITY_GUARD_SKIP_VA
    stub_addr = hook_base + SCENE_LOCAL_ENTITY_GUARD_STUB_RVA
    original = read_mem(hProcess, site, len(SCENE_LOCAL_ENTITY_GUARD_SITE_ORIGINAL))
    if original != SCENE_LOCAL_ENTITY_GUARD_SITE_ORIGINAL:
        return False

    stub = bytearray()
    stub += b'\x8B\x45\xF8'                                      # mov eax, [ebp-8]
    stub += b'\x85\xC0'                                          # test eax, eax
    stub += b'\x0F\x85' + struct.pack('<i', 0)                   # jnz have_entity
    have_entity_jnz = len(stub) - 4
    stub += b'\x8B\x55\xFC'                                      # mov edx, [ebp-4]
    stub += b'\x33\xC0'                                          # xor eax, eax
    stub += b'\x89\x42\x7B'                                      # mov [edx+0x7b], eax
    stub += b'\x89\x42\x7F'                                      # mov [edx+0x7f], eax
    stub += b'\x89\x82\x83\x00\x00\x00'                          # mov [edx+0x83], eax
    stub += b'\xE9' + struct.pack('<i', 0)                       # jmp skip / epilogue
    skip_jmp = len(stub) - 4
    have_entity_offset = len(stub)
    stub += b'\x8B\x48\x10'                                      # have_entity: mov ecx, [eax+0x10]
    stub += b'\xE9' + struct.pack('<i', 0)                       # jmp resume
    resume_jmp = len(stub) - 4

    struct.pack_into('<i', stub, have_entity_jnz, stub_addr + have_entity_offset - (stub_addr + have_entity_jnz + 4))
    struct.pack_into('<i', stub, skip_jmp, skip - (stub_addr + skip_jmp + 4))
    struct.pack_into('<i', stub, resume_jmp, resume - (stub_addr + resume_jmp + 4))

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(SCENE_LOCAL_ENTITY_GUARD_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_scene_self_visual_guard(hProcess, hook_base):
    site = SCENE_SELF_VISUAL_GUARD_SITE_VA
    resume = SCENE_SELF_VISUAL_GUARD_RESUME_VA
    skip = SCENE_SELF_VISUAL_GUARD_SKIP_VA
    stub_addr = hook_base + SCENE_SELF_VISUAL_GUARD_STUB_RVA
    original = read_mem(hProcess, site, len(SCENE_SELF_VISUAL_GUARD_SITE_ORIGINAL))
    if original != SCENE_SELF_VISUAL_GUARD_SITE_ORIGINAL:
        return False

    stub = bytearray()
    stub += b'\x8B\x55\xFC'                                      # mov edx, [ebp-4]
    stub += b'\x8B\x8A\x99\x00\x00\x00'                          # mov ecx, [edx+0x99]
    stub += b'\x85\xC9'                                          # test ecx, ecx
    stub += b'\x0F\x84' + struct.pack('<i', 0)                   # jz skip tail
    skip_jz = len(stub) - 4
    stub += b'\x89\x41\x10'                                      # mov [ecx+0x10], eax
    stub += b'\xE9' + struct.pack('<i', 0)                       # jmp resume
    resume_jmp = len(stub) - 4

    struct.pack_into('<i', stub, skip_jz, skip - (stub_addr + skip_jz + 4))
    struct.pack_into('<i', stub, resume_jmp, resume - (stub_addr + resume_jmp + 4))

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(stub)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(stub))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(SCENE_SELF_VISUAL_GUARD_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_ui_child_state_guard(hProcess, hook_base):
    guards = (
        (
            0x0051B0FE,
            b'\x8B\x48\x3D\xC7\x41\x1C\x00\x40\x00\x00',
            hook_base + UI_CHILD_STATE_GUARD_STUB_RVA,
            0x0051B108,
            b'\xC7\x41\x1C\x00\x40\x00\x00',
        ),
        (
            0x0051B10D,
            b'\x8B\x48\x3D\xC7\x41\x1C\x00\x00\x00\x00',
            hook_base + UI_CHILD_STATE_GUARD_STUB_RVA + 0x40,
            0x0051B117,
            b'\xC7\x41\x1C\x00\x00\x00\x00',
        ),
    )

    old_prot = wt.DWORD(0)
    for site, original, stub_addr, resume_va, store_bytes in guards:
        current = read_mem(hProcess, site, len(original))
        if current != original:
            return False

        stub = bytearray()
        stub += b'\x8B\x48\x3D'                          # mov ecx, [eax+0x3d]
        stub += b'\x85\xC9'                              # test ecx, ecx
        stub += b'\x74\x07'                              # jz short skip_store
        stub += store_bytes                              # mov [ecx+0x1c], 0 / 0x4000
        stub += b'\xE9' + struct.pack('<i', resume_va - (stub_addr + len(stub) + 5))

        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        if not write_mem(hProcess, stub_addr, bytes(stub)):
            kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                       old_prot.value, ctypes.byref(old_prot))
            return False
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, stub_addr, len(stub))

        patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(original) - 5))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        ok = bool(write_mem(hProcess, site, patch))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, site, len(patch))
        if not ok:
            return False

    return True


def install_scene_phase5_vcall_guards(hProcess, hook_base):
    old_prot = wt.DWORD(0)

    for site, original, resume_va, stub_rva, object_disp, slot_disp in SCENE_PHASE5_VCALL_GUARDS:
        current = read_mem(hProcess, site, len(original))
        if current != original:
            return False

        stub_addr = hook_base + stub_rva
        stub = bytearray()
        stub += b'\x8B\x45\xFC'                                  # mov eax, [ebp-4]
        stub += b'\x8B\x90' + struct.pack('<I', object_disp)     # mov edx, [eax+disp]
        stub += b'\x85\xD2'                                      # test edx, edx
        stub += b'\x0F\x84' + struct.pack('<i', 0)               # jz skip
        skip_jz_1 = len(stub) - 4
        stub += b'\x8B\x42' + bytes([slot_disp])                 # mov eax, [edx+slot]
        stub += b'\x85\xC0'                                      # test eax, eax
        stub += b'\x0F\x84' + struct.pack('<i', 0)               # jz skip
        skip_jz_2 = len(stub) - 4
        stub += b'\x3D' + struct.pack('<I', SCENE_STAGE6_VCALL_MIN_TARGET)  # cmp eax, 0x10000
        stub += b'\x0F\x82' + struct.pack('<i', 0)               # jb skip
        skip_jb = len(stub) - 4
        stub += b'\xFF\xD0'                                      # call eax
        stub += b'\xE9' + struct.pack('<i', 0)                   # jmp resume
        resume_after_call = len(stub) - 4
        skip_offset = len(stub)
        stub += b'\xE9' + struct.pack('<i', 0)                   # jmp resume
        resume_after_skip = len(stub) - 4

        struct.pack_into('<i', stub, skip_jz_1, stub_addr + skip_offset - (stub_addr + skip_jz_1 + 4))
        struct.pack_into('<i', stub, skip_jz_2, stub_addr + skip_offset - (stub_addr + skip_jz_2 + 4))
        struct.pack_into('<i', stub, skip_jb, stub_addr + skip_offset - (stub_addr + skip_jb + 4))
        struct.pack_into('<i', stub, resume_after_call, resume_va - (stub_addr + resume_after_call + 4))
        struct.pack_into('<i', stub, resume_after_skip, resume_va - (stub_addr + resume_after_skip + 4))

        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        if not write_mem(hProcess, stub_addr, bytes(stub)):
            kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                       old_prot.value, ctypes.byref(old_prot))
            return False
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, stub_addr, len(stub))

        patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(original) - 5))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        ok = bool(write_mem(hProcess, site, patch))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, site, len(patch))
        if not ok:
            return False

    return True


def install_scene_hud_vcall_guards(hProcess, hook_base):
    old_prot = wt.DWORD(0)

    for site, original, resume_va, stub_rva, object_disp, slot_disp in SCENE_HUD_VCALL_GUARDS:
        current = read_mem(hProcess, site, len(original))
        if current != original:
            return False

        stub_addr = hook_base + stub_rva
        stub = bytearray()
        stub += b'\x8B\x45\xFC'                                  # mov eax, [ebp-4]
        stub += b'\x8B\x90' + struct.pack('<I', object_disp)     # mov edx, [eax+disp]
        stub += b'\x85\xD2'                                      # test edx, edx
        stub += b'\x0F\x84' + struct.pack('<i', 0)               # jz skip
        skip_jz_1 = len(stub) - 4
        stub += b'\x8B\x42' + bytes([slot_disp])                 # mov eax, [edx+slot]
        stub += b'\x85\xC0'                                      # test eax, eax
        stub += b'\x0F\x84' + struct.pack('<i', 0)               # jz skip
        skip_jz_2 = len(stub) - 4
        stub += b'\x3D' + struct.pack('<I', SCENE_STAGE6_VCALL_MIN_TARGET)  # cmp eax, 0x10000
        stub += b'\x0F\x82' + struct.pack('<i', 0)               # jb skip
        skip_jb = len(stub) - 4
        stub += b'\xFF\xD0'                                      # call eax
        stub += b'\xE9' + struct.pack('<i', 0)                   # jmp resume
        resume_after_call = len(stub) - 4
        skip_offset = len(stub)
        stub += b'\xE9' + struct.pack('<i', 0)                   # jmp resume
        resume_after_skip = len(stub) - 4

        struct.pack_into('<i', stub, skip_jz_1, stub_addr + skip_offset - (stub_addr + skip_jz_1 + 4))
        struct.pack_into('<i', stub, skip_jz_2, stub_addr + skip_offset - (stub_addr + skip_jz_2 + 4))
        struct.pack_into('<i', stub, skip_jb, stub_addr + skip_offset - (stub_addr + skip_jb + 4))
        struct.pack_into('<i', stub, resume_after_call, resume_va - (stub_addr + resume_after_call + 4))
        struct.pack_into('<i', stub, resume_after_skip, resume_va - (stub_addr + resume_after_skip + 4))

        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        if not write_mem(hProcess, stub_addr, bytes(stub)):
            kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                       old_prot.value, ctypes.byref(old_prot))
            return False
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, stub_addr, len(stub))

        patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(original) - 5))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        ok = bool(write_mem(hProcess, site, patch))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, site, len(patch))
        if not ok:
            return False

    return True


def install_scene_manager_vcall_guards(hProcess, hook_base):
    old_prot = wt.DWORD(0)

    for site, original, resume_va, stub_rva, slot_disp in SCENE_MANAGER_VCALL_GUARDS:
        current = read_mem(hProcess, site, len(original))
        if current != original:
            return False

        stub_addr = hook_base + stub_rva
        stub = bytearray()
        stub += b'\x8B\x4D\xB8'                                  # mov ecx, [ebp-0x48]
        stub += b'\x85\xC9'                                      # test ecx, ecx
        stub += b'\x0F\x84' + struct.pack('<i', 0)               # jz skip
        skip_jz_1 = len(stub) - 4
        stub += b'\x8B\x11'                                      # mov edx, [ecx]
        stub += b'\x85\xD2'                                      # test edx, edx
        stub += b'\x0F\x84' + struct.pack('<i', 0)               # jz skip
        skip_jz_2 = len(stub) - 4
        stub += b'\x8B\x42' + bytes([slot_disp])                 # mov eax, [edx+slot]
        stub += b'\x85\xC0'                                      # test eax, eax
        stub += b'\x0F\x84' + struct.pack('<i', 0)               # jz skip
        skip_jz_3 = len(stub) - 4
        stub += b'\x3D' + struct.pack('<I', SCENE_STAGE6_VCALL_MIN_TARGET)  # cmp eax, 0x10000
        stub += b'\x0F\x82' + struct.pack('<i', 0)               # jb skip
        skip_jb = len(stub) - 4
        stub += b'\xFF\xD0'                                      # call eax
        stub += b'\xE9' + struct.pack('<i', 0)                   # jmp resume
        resume_after_call = len(stub) - 4
        skip_offset = len(stub)
        stub += b'\xE9' + struct.pack('<i', 0)                   # jmp resume
        resume_after_skip = len(stub) - 4

        struct.pack_into('<i', stub, skip_jz_1, stub_addr + skip_offset - (stub_addr + skip_jz_1 + 4))
        struct.pack_into('<i', stub, skip_jz_2, stub_addr + skip_offset - (stub_addr + skip_jz_2 + 4))
        struct.pack_into('<i', stub, skip_jz_3, stub_addr + skip_offset - (stub_addr + skip_jz_3 + 4))
        struct.pack_into('<i', stub, skip_jb, stub_addr + skip_offset - (stub_addr + skip_jb + 4))
        struct.pack_into('<i', stub, resume_after_call, resume_va - (stub_addr + resume_after_call + 4))
        struct.pack_into('<i', stub, resume_after_skip, resume_va - (stub_addr + resume_after_skip + 4))

        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        if not write_mem(hProcess, stub_addr, bytes(stub)):
            kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                       old_prot.value, ctypes.byref(old_prot))
            return False
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(stub),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, stub_addr, len(stub))

        patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(original) - 5))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        ok = bool(write_mem(hProcess, site, patch))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, site, len(patch))
        if not ok:
            return False

    return True


def patch_scene_postload_cleanup_branch(hProcess):
    current = read_mem(hProcess, SCENE_POSTLOAD_CLEANUP_BRANCH_VA, 2)
    if current == SCENE_POSTLOAD_CLEANUP_BRANCH_PATCHED:
        return True
    if current != SCENE_POSTLOAD_CLEANUP_BRANCH_ORIGINAL:
        return False
    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(SCENE_POSTLOAD_CLEANUP_BRANCH_VA), 2,
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, SCENE_POSTLOAD_CLEANUP_BRANCH_VA, SCENE_POSTLOAD_CLEANUP_BRANCH_PATCHED))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(SCENE_POSTLOAD_CLEANUP_BRANCH_VA), 2,
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, SCENE_POSTLOAD_CLEANUP_BRANCH_VA, 2)
    return ok


def patch_state1_opcode6e_skip_tail(hProcess):
    current = read_mem(hProcess, STATE1_OPCODE6E_SKIP_TAIL_SITE_VA, 2)
    if current == STATE1_OPCODE6E_SKIP_TAIL_PATCHED:
        return True
    if current != STATE1_OPCODE6E_SKIP_TAIL_ORIGINAL:
        return False
    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(STATE1_OPCODE6E_SKIP_TAIL_SITE_VA), 2,
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, STATE1_OPCODE6E_SKIP_TAIL_SITE_VA, STATE1_OPCODE6E_SKIP_TAIL_PATCHED))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(STATE1_OPCODE6E_SKIP_TAIL_SITE_VA), 2,
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, STATE1_OPCODE6E_SKIP_TAIL_SITE_VA, 2)
    return ok


def install_popup_close_safe_stub(hProcess, hook_base):
    site = POPUP_CLOSE_SAFE_SITE_VA
    resume = POPUP_CLOSE_SAFE_RESUME_VA
    stub_addr = hook_base + POPUP_CLOSE_SAFE_STUB_RVA
    original = read_mem(hProcess, site, len(POPUP_CLOSE_SAFE_SITE_ORIGINAL))
    if original != POPUP_CLOSE_SAFE_SITE_ORIGINAL:
        return False

    c = bytearray()
    c += b'\x8B\x4D\xFC'                                      # mov ecx, [ebp-4]
    c += b'\xC6\x81\x9B\x00\x00\x00\x00'                      # mov byte ptr [ecx+0x9b], 0
    c += b'\xC6\x81\x9C\x00\x00\x00\x00'                      # mov byte ptr [ecx+0x9c], 0
    c += b'\xC7\x81\x93\x00\x00\x00\x00\x00\x00\x00'          # mov dword ptr [ecx+0x93], 0
    c += b'\x8B\x81\x8F\x00\x00\x00'                          # mov eax, [ecx+0x8f]
    c += b'\x85\xC0'                                          # test eax, eax
    c += b'\x74\x0C'                                          # jz short after_visual
    c += b'\xC7\x40\x1C\x00\x00\x00\x00'                      # mov dword ptr [eax+0x1c], 0
    c += b'\xC7\x40\x20\x00\x00\x00\x00'                      # mov dword ptr [eax+0x20], 0
    c += b'\x8B\x81\x9D\x00\x00\x00'                          # mov eax, [ecx+0x9d]
    c += b'\x85\xC0'                                          # test eax, eax
    c += b'\x74\x0E'                                          # jz short after_bar0
    c += b'\x3D\x00\x00\x01\x00'                              # cmp eax, 0x10000
    c += b'\x72\x07'                                          # jb short after_bar0
    c += b'\xC7\x40\x1C\x00\x00\x00\x00'                      # mov dword ptr [eax+0x1c], 0
    c += b'\x8B\x81\xA1\x00\x00\x00'                          # mov eax, [ecx+0xa1]
    c += b'\x85\xC0'                                          # test eax, eax
    c += b'\x74\x0E'                                          # jz short after_bar1
    c += b'\x3D\x00\x00\x01\x00'                              # cmp eax, 0x10000
    c += b'\x72\x07'                                          # jb short after_bar1
    c += b'\xC7\x40\x1C\x00\x00\x00\x00'                      # mov dword ptr [eax+0x1c], 0
    c += b'\xE9' + struct.pack('<i', resume - (stub_addr + len(c) + 5))

    if not write_mem(hProcess, stub_addr, bytes(c)):
        return False

    old_prot = wt.DWORD(0)
    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(POPUP_CLOSE_SAFE_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_popup_child_null_latch(hProcess, hook_base):
    site = POPUP_CHILD_NULL_LATCH_SITE_VA
    resume = POPUP_CHILD_NULL_LATCH_RESUME_VA
    stub_addr = hook_base + POPUP_CHILD_NULL_LATCH_STUB_RVA
    original = read_mem(hProcess, site, len(POPUP_CHILD_NULL_LATCH_SITE_ORIGINAL))
    if original != POPUP_CHILD_NULL_LATCH_SITE_ORIGINAL:
        return False

    c = bytearray()
    c += b'\x8B\x45\xFC'                                      # mov eax, [ebp-4]
    c += b'\xC6\x80\x9C\x00\x00\x00\x01'                      # mov byte ptr [eax+0x9c], 1
    c += b'\xC7\x80\x9D\x00\x00\x00\x00\x00\x00\x00'          # mov dword ptr [eax+0x9d], 0
    c += b'\xC7\x80\xA1\x00\x00\x00\x00\x00\x00\x00'          # mov dword ptr [eax+0xa1], 0
    c += b'\xE9' + struct.pack('<i', resume - (stub_addr + len(c) + 5))

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(c)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(c))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(POPUP_CHILD_NULL_LATCH_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_popup_update_gate(hProcess, hook_base):
    site = POPUP_UPDATE_GATE_SITE_VA
    resume = POPUP_UPDATE_GATE_RESUME_VA
    stub_addr = hook_base + POPUP_UPDATE_GATE_STUB_RVA
    original = read_mem(hProcess, site, len(POPUP_UPDATE_GATE_SITE_ORIGINAL))
    if original != POPUP_UPDATE_GATE_SITE_ORIGINAL:
        return False

    c = bytearray()
    c += b'\x8B\x45\xFC'                                      # mov eax, [ebp-4]
    c += b'\x80\xB8\x9C\x00\x00\x00\x00'                      # cmp byte ptr [eax+0x9c], 0
    c += b'\x0F\x85' + struct.pack('<i', 0)                   # jne resume
    resume_jne = len(c) - 4
    c += b'\x0F\xB6\x88\x9B\x00\x00\x00'                      # movzx ecx, byte ptr [eax+0x9b]
    c += b'\x85\xC9'                                          # test ecx, ecx
    c += b'\x0F\x84' + struct.pack('<i', 0)                   # jz resume
    resume_jz = len(c) - 4
    c += b'\x8B\x4D\xFC'                                      # mov ecx, [ebp-4]
    c += b'\xB8' + struct.pack('<I', POPUP_UPDATE_FN_VA)      # mov eax, FUN_005CAA50
    c += b'\xFF\xD0'                                          # call eax
    c += b'\xE9' + struct.pack('<i', 0)                       # jmp resume
    resume_jmp = len(c) - 4

    struct.pack_into('<i', c, resume_jne, resume - (stub_addr + resume_jne + 4))
    struct.pack_into('<i', c, resume_jz, resume - (stub_addr + resume_jz + 4))
    struct.pack_into('<i', c, resume_jmp, resume - (stub_addr + resume_jmp + 4))

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(c)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(c))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(POPUP_UPDATE_GATE_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def install_popup_bar_update_guard(hProcess, hook_base):
    site = POPUP_BAR_UPDATE_GUARD_SITE_VA
    resume = POPUP_BAR_UPDATE_GUARD_RESUME_VA
    skip = POPUP_BAR_UPDATE_GUARD_SKIP_VA
    stub_addr = hook_base + POPUP_BAR_UPDATE_GUARD_STUB_RVA
    original = read_mem(hProcess, site, len(POPUP_BAR_UPDATE_GUARD_SITE_ORIGINAL))
    if original != POPUP_BAR_UPDATE_GUARD_SITE_ORIGINAL:
        return False

    c = bytearray()
    c += b'\x8B\x45\xFC'                                      # mov eax, [ebp-4]
    c += b'\x8B\x88\x9D\x00\x00\x00'                          # mov ecx, [eax+0x9d]
    c += b'\x85\xC9'                                          # test ecx, ecx
    c += b'\x0F\x84' + struct.pack('<i', 0)                   # jz skip
    skip_jz_1 = len(c) - 4
    c += b'\x8B\x90\xA1\x00\x00\x00'                          # mov edx, [eax+0xa1]
    c += b'\x85\xD2'                                          # test edx, edx
    c += b'\x0F\x84' + struct.pack('<i', 0)                   # jz skip
    skip_jz_2 = len(c) - 4
    c += b'\xC7\x41\x1C\x00\x40\x00\x00'                      # mov dword ptr [ecx+0x1c], 0x4000
    c += b'\xE9' + struct.pack('<i', 0)                       # jmp resume
    resume_jump = len(c) - 4
    skip_offset = len(c)
    c += b'\xE9' + struct.pack('<i', 0)                       # jmp skip
    skip_jump = len(c) - 4

    struct.pack_into('<i', c, skip_jz_1, stub_addr + skip_offset - (stub_addr + skip_jz_1 + 4))
    struct.pack_into('<i', c, skip_jz_2, stub_addr + skip_offset - (stub_addr + skip_jz_2 + 4))
    struct.pack_into('<i', c, resume_jump, resume - (stub_addr + resume_jump + 4))
    struct.pack_into('<i', c, skip_jump, skip - (stub_addr + skip_jump + 4))

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    if not write_mem(hProcess, stub_addr, bytes(c)):
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                                   old_prot.value, ctypes.byref(old_prot))
        return False
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(stub_addr), len(c),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, stub_addr, len(c))

    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(POPUP_BAR_UPDATE_GUARD_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def patch_popup_finalize_vcall_skip(hProcess):
    current = read_mem(hProcess, POPUP_FINALIZE_VCALL_SKIP_SITE_VA, len(POPUP_FINALIZE_VCALL_SKIP_SITE_ORIGINAL))
    if current == POPUP_FINALIZE_VCALL_SKIP_PATCHED:
        return True
    if current != POPUP_FINALIZE_VCALL_SKIP_SITE_ORIGINAL:
        return False
    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(POPUP_FINALIZE_VCALL_SKIP_SITE_VA), len(POPUP_FINALIZE_VCALL_SKIP_PATCHED),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, POPUP_FINALIZE_VCALL_SKIP_SITE_VA, POPUP_FINALIZE_VCALL_SKIP_PATCHED))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(POPUP_FINALIZE_VCALL_SKIP_SITE_VA), len(POPUP_FINALIZE_VCALL_SKIP_PATCHED),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, POPUP_FINALIZE_VCALL_SKIP_SITE_VA, len(POPUP_FINALIZE_VCALL_SKIP_PATCHED))
    return ok


def patch_popup_teardown_skip(hProcess):
    old_prot = wt.DWORD(0)

    for site, original, patched in POPUP_TEARDOWN_SKIP_CALLS:
        current = read_mem(hProcess, site, len(original))
        if current == patched:
            continue
        if current != original:
            return False
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patched),
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        ok = bool(write_mem(hProcess, site, patched))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patched),
                                   old_prot.value, ctypes.byref(old_prot))
        flush_icache(hProcess, site, len(patched))
        if not ok:
            return False

    return True


def patch_equip_popup_caution_skip(hProcess):
    current = read_mem(
        hProcess,
        EQUIP_POPUP_CAUTION_SKIP_SITE_VA,
        len(EQUIP_POPUP_CAUTION_SKIP_SITE_ORIGINAL),
    )
    patch = b'\xE9' + struct.pack(
        '<i',
        EQUIP_POPUP_CAUTION_SKIP_TARGET_VA - (EQUIP_POPUP_CAUTION_SKIP_SITE_VA + 5),
    )
    if current == patch:
        return True
    if current != EQUIP_POPUP_CAUTION_SKIP_SITE_ORIGINAL:
        return False

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(
        hProcess,
        ctypes.c_void_p(EQUIP_POPUP_CAUTION_SKIP_SITE_VA),
        len(patch),
        PAGE_EXECUTE_READWRITE,
        ctypes.byref(old_prot),
    )
    ok = bool(write_mem(hProcess, EQUIP_POPUP_CAUTION_SKIP_SITE_VA, patch))
    kernel32.VirtualProtectEx(
        hProcess,
        ctypes.c_void_p(EQUIP_POPUP_CAUTION_SKIP_SITE_VA),
        len(patch),
        old_prot.value,
        ctypes.byref(old_prot),
    )
    flush_icache(hProcess, EQUIP_POPUP_CAUTION_SKIP_SITE_VA, len(patch))
    return ok


def patch_equip_popup_open_skip(hProcess):
    current = read_mem(
        hProcess,
        EQUIP_POPUP_OPEN_SKIP_SITE_VA,
        len(EQUIP_POPUP_OPEN_SKIP_SITE_ORIGINAL),
    )
    patch = b'\xE9' + struct.pack(
        '<i',
        EQUIP_POPUP_OPEN_SKIP_TARGET_VA - (EQUIP_POPUP_OPEN_SKIP_SITE_VA + 5),
    )
    patch += b'\x90' * (len(EQUIP_POPUP_OPEN_SKIP_SITE_ORIGINAL) - len(patch))
    if current == patch:
        return True
    if current != EQUIP_POPUP_OPEN_SKIP_SITE_ORIGINAL:
        return False

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(
        hProcess,
        ctypes.c_void_p(EQUIP_POPUP_OPEN_SKIP_SITE_VA),
        len(patch),
        PAGE_EXECUTE_READWRITE,
        ctypes.byref(old_prot),
    )
    ok = bool(write_mem(hProcess, EQUIP_POPUP_OPEN_SKIP_SITE_VA, patch))
    kernel32.VirtualProtectEx(
        hProcess,
        ctypes.c_void_p(EQUIP_POPUP_OPEN_SKIP_SITE_VA),
        len(patch),
        old_prot.value,
        ctypes.byref(old_prot),
    )
    flush_icache(hProcess, EQUIP_POPUP_OPEN_SKIP_SITE_VA, len(patch))
    return ok


def patch_scene_stage9_tutorial_skip(hProcess):
    current = read_mem(
        hProcess,
        SCENE_STAGE9_TUTORIAL_SKIP_SITE_VA,
        len(SCENE_STAGE9_TUTORIAL_SKIP_SITE_ORIGINAL),
    )
    patch = b'\xE9' + struct.pack(
        '<i',
        SCENE_STAGE9_TUTORIAL_SKIP_TARGET_VA - (SCENE_STAGE9_TUTORIAL_SKIP_SITE_VA + 5),
    )
    patch += b'\x90' * (len(SCENE_STAGE9_TUTORIAL_SKIP_SITE_ORIGINAL) - len(patch))
    if current == patch:
        return True
    if current != SCENE_STAGE9_TUTORIAL_SKIP_SITE_ORIGINAL:
        return False

    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(
        hProcess,
        ctypes.c_void_p(SCENE_STAGE9_TUTORIAL_SKIP_SITE_VA),
        len(patch),
        PAGE_EXECUTE_READWRITE,
        ctypes.byref(old_prot),
    )
    ok = bool(write_mem(hProcess, SCENE_STAGE9_TUTORIAL_SKIP_SITE_VA, patch))
    kernel32.VirtualProtectEx(
        hProcess,
        ctypes.c_void_p(SCENE_STAGE9_TUTORIAL_SKIP_SITE_VA),
        len(patch),
        old_prot.value,
        ctypes.byref(old_prot),
    )
    flush_icache(hProcess, SCENE_STAGE9_TUTORIAL_SKIP_SITE_VA, len(patch))
    return ok


def install_scene_postload_ready_force(hProcess, hook_base):
    site = SCENE_POSTLOAD_READY_FORCE_SITE_VA
    resume = SCENE_POSTLOAD_READY_FORCE_RESUME_VA
    stub_addr = hook_base + SCENE_POSTLOAD_READY_FORCE_STUB_RVA
    original = read_mem(hProcess, site, len(SCENE_POSTLOAD_READY_FORCE_SITE_ORIGINAL))
    if original != SCENE_POSTLOAD_READY_FORCE_SITE_ORIGINAL:
        return False

    c = bytearray()
    c += b'\x8B\x45\xFC'                                      # mov eax, [ebp-4]
    c += b'\x8B\x48\x04'                                      # mov ecx, [eax+4]
    c += b'\x85\xC9'                                          # test ecx, ecx
    c += b'\x74\x12'                                          # jz short set_ready
    c += b'\x81\xF9\x00\x00\x01\x00'                          # cmp ecx, 0x10000
    c += b'\x72\x0A'                                          # jb short set_ready
    c += b'\xC7\x81' + struct.pack('<I', SCENE_POSTLOAD_READY_FIELD_OFFSET)
    c += b'\x01\x00\x00\x00'                                  # mov [ecx+0x31946], 1
    c += b'\xB8\x01\x00\x00\x00'                              # mov eax, 1
    c += b'\xE9' + struct.pack('<i', resume - (stub_addr + len(c) + 5))

    if not write_mem(hProcess, stub_addr, c):
        return False

    old_prot = wt.DWORD(0)
    patch = b'\xE9' + struct.pack('<i', stub_addr - (site + 5)) + (b'\x90' * (len(SCENE_POSTLOAD_READY_FORCE_SITE_ORIGINAL) - 5))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
    ok = bool(write_mem(hProcess, site, patch))
    kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site), len(patch),
                               old_prot.value, ctypes.byref(old_prot))
    flush_icache(hProcess, site, len(patch))
    return ok


def build_connect_hook(base):
    """
    connect() hook: forces IP=127.0.0.1, Port=9000
    Also logs original values.

    Memory layout:
      0x000: connect hook code
      0x080: ptr to real connect
      0x100: log area (port, ip, flag, count)
    """
    log_port     = base + 0x100
    log_ip       = base + 0x104
    log_flag     = base + 0x108
    log_count    = base + 0x114
    real_connect = base + 0x080

    c = bytearray()
    c += b'\x55'                                                  # push ebp
    c += b'\x8B\xEC'                                              # mov ebp, esp
    c += b'\x8B\x45\x0C'                                         # mov eax, [ebp+0xC]  ; sockaddr*

    # Log original port and IP
    c += b'\x0F\xB7\x48\x02'                                     # movzx ecx, word [eax+2]
    c += b'\x89\x0D' + struct.pack('<I', log_port)                # mov [log_port], ecx
    c += b'\x8B\x50\x04'                                         # mov edx, [eax+4]
    c += b'\x89\x15' + struct.pack('<I', log_ip)                  # mov [log_ip], edx
    c += b'\xC7\x05' + struct.pack('<I', log_flag) + b'\x01\x00\x00\x00'
    c += b'\xFF\x05' + struct.pack('<I', log_count)               # inc [log_count]

    # Force IP = 127.0.0.1  (0x0100007F in network byte order)
    c += b'\xC7\x40\x04' + struct.pack('<I', 0x0100007F)         # mov [eax+4], 127.0.0.1

    # Force Port = 9000  (network byte order)
    c += b'\x66\xC7\x40\x02' + struct.pack('<H', SERVER_PORT_NET)  # mov word [eax+2], htons(9000)

    # Forward to real connect
    c += b'\xFF\x75\x10'                                          # push [ebp+0x10]
    c += b'\xFF\x75\x0C'                                          # push [ebp+0xC]
    c += b'\xFF\x75\x08'                                          # push [ebp+0x08]
    c += b'\xFF\x15' + struct.pack('<I', real_connect)            # call [real_connect]
    c += b'\x5D'                                                  # pop ebp
    c += b'\xC2\x0C\x00'                                         # ret 12

    return bytes(c)


def collect_runtime_state(
    hProcess, gm, opcode100_hits, self_init_hits, *, deep_dispatch_scan=False
):
    player = gm + 0x35C20
    popup = gm + 0xD98
    dispatch_owner_chain = read_dispatch_owner_chain(hProcess)
    # The owner address is now constructor-verified at gm+0x185A0.  Keep the
    # historical reverse scans available for explicit diagnostics, but never
    # run them from the once-per-second control-panel/telemetry path: each scan
    # reads most of the process address space and used to take about two
    # seconds per poll.
    dispatch_owner_candidates = {
        'stack_gm_target': {
            'target': f'0x{gm:08X}' if gm >= 0x10000 else 'unresolved',
            'raw_hits': [],
            'candidates': [],
            'scan': 'skipped_direct_owner',
        },
    }
    # The +0x0C engine values are WDL string pointers, not dispatcher objects.
    # Do not feed them into the gate reverse-search; that search must remain
    # anchored to the separately verified CGameManager candidate.
    dispatch_owner_chain.pop('_engine_root_address', None)
    dispatch_vtable_candidates = {
        'vtables': {
            f'0x{address:08X}': kind
            for address, kind in DISPATCH_OWNER_VTABLES.items()
        },
        'objects': [],
        'scan': 'skipped_direct_owner',
    }
    # The dispatcher is the embedded CLogicManager subobject, not the
    # stack-scanned CGameManager base.  Ghidra constructor evidence fixes its
    # address at gm+0xE4A+0x17756 (gm+0x185A0).  Keep the old base reads out of the live
    # dispatch fields so a coincidental zero/garbage value cannot gate a test.
    logic_controller_ptr = gm + DISPATCH_OWNER_SUBOBJECT_OFFSET if gm >= 0x10000 else 0
    dispatch_owner_subobject = read_dispatch_owner_subobject(hProcess, gm)
    if deep_dispatch_scan:
        dispatch_owner_candidates['stack_gm_target'] = (
            find_dispatch_owner_candidates(hProcess, gm)
        )
        dispatch_vtable_candidates = find_dispatch_vtable_candidates(hProcess)
    elif dispatch_owner_subobject.get('validated'):
        dispatch_owner_candidates['stack_gm_target']['candidates'] = [
            dispatch_owner_subobject.copy()
        ]
        dispatch_vtable_candidates['objects'] = [
            {
                'object': dispatch_owner_subobject.get('object'),
                'vptr': dispatch_owner_subobject.get('vptr'),
                'vtable_kind': dispatch_owner_subobject.get('vtable_kind'),
                'mode': dispatch_owner_subobject.get('mode'),
                'gate': (
                    f"0x{dispatch_owner_subobject.get('gate', 0):08X}"
                    if isinstance(dispatch_owner_subobject.get('gate'), int)
                    else dispatch_owner_subobject.get('gate')
                ),
                'gate_is_nonzero': bool(dispatch_owner_subobject.get('gate')),
            }
        ]
    dispatch_gate = (
        read_dword(hProcess, logic_controller_ptr + 0x163D8)
        if logic_controller_ptr >= 0x10000 else 0
    )
    dispatch_mode = (
        read_dword(hProcess, logic_controller_ptr + 0x163E4)
        if logic_controller_ptr >= 0x10000 else 0
    )
    # Keep the historical IP-buffer address visible as a separate diagnostic,
    # but do not treat it as the gate value.  The startup disassembly pushes
    # the outer GameManager as FUN_00594130's first stack argument (the IP
    # buffer is the following argument), so the expected gate value is gm.
    # Any mismatch is evidence to investigate, never a reason to write memory.
    dispatch_gate_outer_buffer = gm + 0x31822 if gm >= 0x10000 else 0
    dispatch_gate_matches_gm = bool(gm) and dispatch_gate == gm
    dispatch_gate_matches_outer_buffer = (
        bool(dispatch_gate_outer_buffer) and dispatch_gate == dispatch_gate_outer_buffer
    )
    scene_ready_owner = read_dword(hProcess, gm + 0x348FD)
    popup_visual = read_dword(hProcess, gm + 0xE27)
    bar_9d = read_dword(hProcess, gm + 0xE35)
    bar_a1 = read_dword(hProcess, gm + 0xE39)
    transition_vptrs = {
        name: read_dword(hProcess, gm + offset)
        for name, offset, _expected in TRANSITION_VPTR_SPECS
    }
    transition_vptrs_ok = all(
        transition_vptrs[name] == expected
        for name, _offset, expected in TRANSITION_VPTR_SPECS
    )
    transition_cleanup_children = inspect_transition_cleanup_children(hProcess, gm)
    return {
        'gm': gm,
        'opcode100_hits': opcode100_hits,
        'self_init_hits': self_init_hits,
        'scene_stage': read_dword(hProcess, hook_base_global + HOOK_LOG_SCENE_STAGE_RVA) if hook_base_global else 0,
        'scene_stage_hits': read_dword(hProcess, hook_base_global + HOOK_LOG_SCENE_STAGE_COUNT_RVA) if hook_base_global else 0,
        'scene_ready_owner': scene_ready_owner,
        'scene_ready_latch': read_dword(hProcess, scene_ready_owner + SCENE_POSTLOAD_READY_FIELD_OFFSET) if scene_ready_owner >= 0x10000 else 0,
        'popup_wrapper_ptr': read_dword(hProcess, gm + 0xD94),
        'popup_ptr': read_dword(hProcess, popup),
        'popup_visual_8f': popup_visual,
        'popup_anim_93': read_dword(hProcess, gm + 0xE2B),
        'popup_flag_9b': read_byte(hProcess, gm + 0xE33),
        'popup_flag_9c': read_byte(hProcess, gm + 0xE34),
        'popup_visual_state': read_dword(hProcess, popup_visual + 0x1C) if popup_visual >= 0x10000 else 0,
        'popup_visual_state2': read_dword(hProcess, popup_visual + 0x20) if popup_visual >= 0x10000 else 0,
        'bar_9d': bar_9d,
        'bar_a1': bar_a1,
        'bar_9d_state': read_dword(hProcess, bar_9d + 0x1C) if bar_9d >= 0x10000 else 0,
        'bar_a1_state': read_dword(hProcess, bar_a1 + 0x1C) if bar_a1 >= 0x10000 else 0,
        'logic_state': read_dword(hProcess, gm + 0x2E984),
        'logic_aux_ptr': read_dword(hProcess, gm + 0x2E978),
        'logic_controller_ptr': logic_controller_ptr,
        'dispatch_gate': dispatch_gate,
        'dispatch_mode': dispatch_mode,
        'dispatch_gate_outer_buffer': dispatch_gate_outer_buffer,
        'dispatch_gate_matches_gm': dispatch_gate_matches_gm,
        'dispatch_gate_matches_outer_buffer': dispatch_gate_matches_outer_buffer,
        'dispatch_owner_subobject': dispatch_owner_subobject,
        'dispatch_owner_chain': dispatch_owner_chain,
        'dispatch_owner_candidates': dispatch_owner_candidates,
        'dispatch_vtable_candidates': dispatch_vtable_candidates,
        'phase_31792': read_dword(hProcess, gm + 0x31792),
        'phase_31796': read_dword(hProcess, gm + 0x31796),
        'scene_opcode': read_dword(hProcess, gm + 0x31AAD),
        'flag_31c71': read_byte(hProcess, gm + 0x31C71),
        'flag_31c72': read_byte(hProcess, gm + 0x31C72),
        'flag_31c73': read_byte(hProcess, gm + 0x31C73),
        'player_ptr_99': read_dword(hProcess, player + 0x99),
        'player_model_9d': read_byte(hProcess, player + 0x9D),
        'player_model_a1': read_byte(hProcess, player + 0xA1),
        'self_actor_id': read_dword(hProcess, player + 0x2F8),
        'self_owner': read_dword(hProcess, player + 0x2FC),
        'flag_31a': read_byte(hProcess, player + 0x31A),
        'cached_x': read_dword(hProcess, player + 0x11B),
        'cached_y': read_dword(hProcess, player + 0x11F),
        'transition_vptrs': transition_vptrs,
        'transition_vptrs_ok': transition_vptrs_ok,
        'transition_cleanup_children': transition_cleanup_children,
        # Mode-0 S->C 0x0003 stages the loader path in CPopupNotice.  These
        # fields are observation-only and let a path-only experiment prove
        # that the handler completed before any S->C 0x000D transition.
        'space_path_flag': read_dword(hProcess, gm + 0x31C63),
        # CPopupNotice ends 0xFD bytes after this buffer begins.  Never let a
        # diagnostic read cross into the next embedded object.
        'notice_path': read_c_string(hProcess, gm + 0x4B1F3, 0xFD),
        'notice_armed_d0': read_byte(hProcess, gm + 0x4B1E8),
        'notice_armed_d1': read_byte(hProcess, gm + 0x4B1E9),
        'notice_tick_c8': read_dword(hProcess, gm + 0x4B1E0),
        'notice_tick_cc': read_dword(hProcess, gm + 0x4B1E4),
        'notice_countdown_d7': read_dword(hProcess, gm + 0x4B1EF),
    }


def format_runtime_state(state):
    return (
        "  [STATE] "
        f"gm=0x{state['gm']:08X} "
        f"hits={state['opcode100_hits']}/{state['self_init_hits']} "
        f"stage={state['scene_stage']}#{state['scene_stage_hits']} "
        f"logic=0x{state['logic_state']:08X} "
        f"phase=0x{state['phase_31792']:08X}/0x{state['phase_31796']:08X} "
        f"scene=0x{state['scene_opcode']:08X} "
        f"transition_vptrs={'ok' if state['transition_vptrs_ok'] else 'BAD'} "
        f"cleanup_children={state['transition_cleanup_children']['state']} "
        f"gate(owner=0x{state['scene_ready_owner']:08X},latch=0x{state['scene_ready_latch']:08X}) "
        f"popup(ptr=0x{state['popup_ptr']:08X},8F=0x{state['popup_visual_8f']:08X},93=0x{state['popup_anim_93']:08X},9B={state['popup_flag_9b']:02X},9C={state['popup_flag_9c']:02X},v=0x{state['popup_visual_state']:08X}/0x{state['popup_visual_state2']:08X}) "
        f"self(id={state['self_actor_id']},owner=0x{state['self_owner']:08X},ent=0x{state['player_ptr_99']:08X},ready={state['flag_31a']:02X},model={state['player_model_9d']:02X}/{state['player_model_a1']:02X}) "
        f"xy=({state['cached_x']},{state['cached_y']}) "
        f"flags=(aux=0x{state['logic_aux_ptr']:08X},31C71={state['flag_31c71']:02X},31C72={state['flag_31c72']:02X},31C73={state['flag_31c73']:02X},bar=0x{state['bar_9d']:08X}/0x{state['bar_a1']:08X},bar_state=0x{state['bar_9d_state']:08X}/0x{state['bar_a1_state']:08X})"
    )


# ═══════════════════════════════════════════════════════════
#  TCP Server
# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════
#  Control-panel macros — named packet recipes
# ═══════════════════════════════════════════════════════════
# A step is (opcode, payload, delay_ms). `payload` is a hex string, or a callable
# taking the server and returning bytes (for anything timestamped or state-derived).

def _calib_sample(kind):
    """S->C 0x0004 = u8 sample_kind + u32 timestamp_ms."""
    return lambda srv: struct.pack('<BI', kind, int(time.time() * 1000) & 0xFFFFFFFF)


MACROS = {
    'hansol': {
        'desc': ('Hansol/Plaza transition recipe (docs/research/25_calibration_and_hansol_dispatch_2026-07-17.md). '
                 'Sends the transition prelude only. The client then naturally emits C->S 0x0064; '
                 'the supported default replies with authoritative S->C 0x0064 only. '
                 'Optional S->C 0x006E is diagnostic/OX-only and is never duplicated here.'),
        'steps': [
            # 0x000D arms the client-side Hansol transition.  The five
            # 0x0004[01] samples are emitted only in response to the client's
            # natural C->S 0x0016[01] requests; do not pre-send them here.
            (0x000D, '00', 0),
        ],
    },
    'calib_faithful': {
        'desc': ('Diagnostic only: direct 0x0004[01] injection. The Hansol macro now '
                 'uses request-driven samples from C->S 0x0016[01] instead.'),
        'steps': [(0x0004, _calib_sample(0x01), 250)] * 5,
    },
}


class AzrokServer:
    def __init__(self, port=SERVER_PORT, log_dir='.', bind_host='127.0.0.1'):
        self.port = port
        self.bind_host = parse_private_ipv4_bind(bind_host)
        self.running = False
        self.connections = []
        # Per-connection metadata is deliberately kept separate from the
        # packet protocol state.  It lets the control panel show who is in
        # which local room and gives the multiplayer relay a stable non-self
        # actor id without changing the single-client bootstrap path.
        self.client_meta = {}
        self.next_actor_id = 2
        self.hProcess = None
        self.game_packets = []  # individual parsed game packets
        self.proto_state = {
            'char_created': False,
            'zone_request_seen': False,
            'zone_request_count': 0,
            'client_0007_count': 0,
            'content_save_count': 0,
            'saved_state_loaded': False,
            'post_create_seen': False,
            'post_0017_followup_sent': False,
            'full_0064_pending': False,
            'full_0064_sent': False,
            'post_0017_heartbeat_count': 0,
            'client_0064_heartbeat_count': 0,
            'late_006e_sent': False,
            'state_0064_entry_kind': STATE_0064_ENTRY_KIND,
            'plaza_reply_mode': PLAZA_REPLY_MODE,
            'hansol_calibration_active': False,
            'hansol_calibration_samples_sent': 0,
            'stable_heartbeat_count': 0,
            'door_0019_seen': False,
            'door_0019_count': 0,
            'legacy_0019_memory_shortcut': LEGACY_0019_MEMORY_SHORTCUT,
            'char_type': 0,
            'char_name_raw': b'Player',
            'account_raw': b'',
            'account_name': '',
            'character_slot': 0,
            'client_0005_seen': False,
            'selected_character_key': None,
            'login_response_sent': False,
            'calibration_active': False,
            'calibration_samples_sent': 0,
            'calibration_completed': False,
        }
        # Keep an immutable bootstrap template so a reused-server secondary
        # client starts from a clean login state instead of inheriting the
        # first client's Plaza/calibration flags.  The response builder still
        # uses ``self.proto_state`` for compatibility; each client handler
        # swaps that reference under ``proto_lock`` for the duration of one
        # packet.
        self.proto_template = dict(self.proto_state)
        self.proto_lock = threading.RLock()
        self.log_lock = threading.Lock()
        # OX mode-2 transitions remain deterministic through ox_auto_step().
        # Production calls that function from a small scheduler thread only
        # after a natural exact C2S C8 admission.  Manual control endpoints
        # use the same operation lock and remain available.
        self.ox_lock = threading.RLock()
        self.ox_action_lock = threading.RLock()
        self.ox_rooms = {}
        self.ox_receive_seq = 0
        self.ox_side_cells = {
            side: frozenset(cells)
            for side, cells in OX_SIDE_CELLS_DEFAULT.items()
        }
        self.ox_questions = tuple(dict(question) for question in OX_SAMPLE_QUESTIONS)
        self.ox_spawn_x = int(os.environ.get('AZROK_OX_SPAWN_X', '0'), 0)
        self.ox_spawn_y = int(os.environ.get('AZROK_OX_SPAWN_Y', '0'), 0)
        self.ox_auto_policy = _ox_auto_policy_from_env()
        self.ox_scheduler_stop = threading.Event()
        self.ox_scheduler_thread = None
        self.state_store_dir = os.path.join(log_dir, 'server_state')
        if STATE_STORE_NAMESPACE:
            self.state_store_dir = os.path.join(
                self.state_store_dir, STATE_STORE_NAMESPACE
            )
        os.makedirs(self.state_store_dir, exist_ok=True)
        self.saved_character_states = {}
        self.saved_server_states = {}
        # A clean logout exits this client build after its 0002/0001 sequence.
        # Remember the account across that short reconnect so the replacement
        # client remains at the four-slot character picker instead of the
        # browser-only auto-select helper immediately choosing slot 0 again.
        self.manual_select_accounts = set()

        # ── Control-panel state (see azrok_control.py) ──
        self.ctl_lock = threading.RLock()
        self.paused = False           # gate on outbound 'auto' packets
        self.pending_out = []         # packets held at the gate, awaiting step/drop
        self.packet_ring = deque(maxlen=CTL_RING_SIZE)  # recent packets for the UI
        self.event_ring = deque(maxlen=200)
        self.mutation_ring = deque(maxlen=500)
        self.started_at = time.time()
        self.emit_seq = 0
        self.event_seq = 0
        self.mutation_seq = 0

        # Open log files immediately for real-time writing.
        # A timestamped capture keeps history: opening packets_log.txt with 'w' every
        # run is how the 2026-04-01 C->S 0x000C evidence was destroyed.
        stamp = time.strftime('%Y%m%d_%H%M%S')
        cap_dir = os.path.join(log_dir, 'captures')
        os.makedirs(cap_dir, exist_ok=True)
        self.capture_path = os.path.join(cap_dir, f"packets_{stamp}.txt")
        self.log_path = os.path.join(log_dir, "packets_log.txt")  # 'latest', kept for existing tooling
        header = (f"Azrok Plaza - Parsed Game Packets (LIVE)\n"
                  f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                  f"{'='*60}\n\n")
        self.capture_file = open(self.capture_path, 'w', encoding='utf-8')
        self.log_file = open(self.log_path, 'w', encoding='utf-8')
        for f in (self.capture_file, self.log_file):
            f.write(header)
            f.flush()
        # Machine-readable capture is a separate, privacy-aware durability
        # layer.  The historical text files above intentionally remain
        # unchanged for existing analysis tooling.
        self.structured_capture = StructuredPacketCapture(log_dir)
        self._add_event('server', '로컬 게임 서버가 시작되었습니다.', severity='info')

    def attach_process(self, hProcess):
        self.hProcess = hProcess

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._start_ox_scheduler()

    def _start_ox_scheduler(self):
        """Start the production timer that delegates to deterministic steps."""
        self._ensure_ox_runtime()
        if not self.ox_auto_policy.get('enabled'):
            return False
        if (self.ox_scheduler_thread is not None
                and self.ox_scheduler_thread.is_alive()):
            return True
        self.ox_scheduler_stop.clear()
        self.ox_scheduler_thread = threading.Thread(
            target=self._ox_scheduler_loop,
            name='azrok-ox-scheduler',
            daemon=True,
        )
        self.ox_scheduler_thread.start()
        return True

    def _stop_ox_scheduler(self):
        """Stop and bounded-join the OX scheduler without touching clients."""
        self._ensure_ox_runtime()
        self.ox_scheduler_stop.set()
        thread = self.ox_scheduler_thread
        if (thread is not None and thread.is_alive()
                and thread is not threading.current_thread()):
            thread.join(timeout=2.0)
        return thread is None or not thread.is_alive()

    def _ox_scheduler_loop(self):
        poll_seconds = max(
            0.01,
            int(self.ox_auto_policy.get('scheduler_poll_ms', 50)) / 1000.0,
        )
        while self.running and not self.ox_scheduler_stop.wait(poll_seconds):
            try:
                self.ox_auto_step()
            except Exception as exc:
                self._add_event(
                    'ox_auto_error', 'OX automatic scheduler step failed',
                    severity='error', details={'error': str(exc)[:240]},
                )

    def _run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.bind_host, self.port))
        srv.listen(5)
        srv.settimeout(1.0)
        print(f"  [SERVER] Listening on {self.bind_host}:{self.port}")

        while self.running:
            try:
                conn, addr = srv.accept()
                print(f"  [SERVER] Connection from {addr[0]}:{addr[1]}")
                with self.ctl_lock:
                    self.connections.append(conn)
                    self.client_meta[conn] = {
                        'entity_id': self.next_actor_id,
                        'addr': f'{addr[0]}:{addr[1]}',
                        'room_kind': None,
                        'room_name': '미확인',
                        'x': None,
                        'y': None,
                        'heading': 0,
                        'movement_generation': 0,
                        'char_type': 0,
                        'name': 'Player',
                        'account': '',
                        'last_opcode': None,
                        'last_seen': time.time(),
                        'rx_packets': 0,
                        'tx_packets': 0,
                        'relay_tx_packets': 0,
                        'unknown_c2s_count': 0,
                        'opcode_counts': {},
                        # Server-side mirror of the client's fixed 100-slot
                        # remote actor pool.  It lets targeted 0x0067 removals
                        # replace the unsafe full 0x0065 reset and prevents
                        # position relays for actors that were never admitted.
                        'visible_remote_actor_ids': set(),
                        'ox_room_id': None,
                        'ox_round_generation': None,
                        'last_tx_opcode': None,
                        'last_tx_at': None,
                        'connected_at': time.time(),
                        'proto_state': {
                            k: (bytes(v) if isinstance(v, (bytes, bytearray)) else v)
                            for k, v in self.proto_template.items()
                        },
                    }
                    self.next_actor_id += 1
                    joined_id = self.client_meta[conn]['entity_id']
                self._add_event(
                    'join', f'클라이언트 #{joined_id}가 연결되었습니다.',
                    entity_id=joined_id, severity='ok',
                    details={'addr': f'{addr[0]}:{addr[1]}'},
                )
                t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"  [SERVER] Accept error: {e}")
                break

        srv.close()

    def _add_event(self, kind, message, entity_id=None, severity='info', details=None):
        """Append a small semantic event for the dashboard timeline."""
        if kind in ('login', 'chat', 'leave'):
            from azrok_admin_history import record_event
            try:
                record_event(self, kind, message, entity_id=entity_id, details=details)
            except (OSError, ValueError):
                self.admin_history_failures = getattr(self, 'admin_history_failures', 0) + 1
        with self.ctl_lock:
            self.event_seq += 1
            self.event_ring.append({
                'seq': self.event_seq,
                't': time.strftime('%H:%M:%S'),
                'kind': kind,
                'severity': severity,
                'entity_id': entity_id,
                'message': message,
                'details': details or {},
            })

    def _ensure_mutation_runtime(self):
        """Initialize transaction receipt state for normal and __new__ tests."""
        if not hasattr(self, 'mutation_lock'):
            self.mutation_lock = threading.RLock()
        if not hasattr(self, 'mutation_ring'):
            self.mutation_ring = deque(maxlen=500)
        if not hasattr(self, 'mutation_seq'):
            self.mutation_seq = 0
        if not hasattr(self, 'mutation_journal_failures'):
            self.mutation_journal_failures = 0
        if not hasattr(self, 'mutation_journal_corrupt_lines'):
            self.mutation_journal_corrupt_lines = 0
        if not hasattr(self, 'mutation_journal_sequence_gaps'):
            self.mutation_journal_sequence_gaps = 0
        if not hasattr(self, 'mutation_journal_loaded_records'):
            self.mutation_journal_loaded_records = 0
        if not getattr(self, '_mutation_journal_loaded', False):
            self._load_mutation_journal()

    def _mutation_journal_path(self):
        state_dir = getattr(self, 'state_store_dir', None)
        if not isinstance(state_dir, str) or not state_dir:
            return None
        return os.path.join(state_dir, 'mutation_transactions_v1.jsonl')

    @staticmethod
    def _journal_safe_value(value, depth=0):
        """Return bounded JSON data without raw credentials or binary blobs."""
        if depth >= 4:
            return '<depth-limit>'
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value[:512]
        if isinstance(value, (bytes, bytearray, memoryview)):
            return f'<bytes:{len(value)}>'
        if isinstance(value, dict):
            safe = {}
            for raw_name, child in list(value.items())[:64]:
                name = str(raw_name)[:96]
                folded = name.lower()
                if any(token in folded for token in (
                        'password', 'account_raw', 'selected_character_key',
                        'snapshot_hex', 'payload_hex')):
                    safe[name] = '<redacted>'
                else:
                    safe[name] = AzrokServer._journal_safe_value(child, depth + 1)
            return safe
        if isinstance(value, (list, tuple, set, frozenset)):
            return [AzrokServer._journal_safe_value(child, depth + 1)
                    for child in list(value)[:64]]
        return str(value)[:512]

    def _load_mutation_journal(self):
        """Recover the durable sequence and bounded recent receipt window."""
        self._mutation_journal_loaded = True
        path = self._mutation_journal_path()
        if path is None or not os.path.isfile(path):
            return
        recovered = deque(maxlen=500)
        maximum_seq = int(getattr(self, 'mutation_seq', 0) or 0)
        corrupt = 0
        sequence_gaps = 0
        previous_seq = None
        try:
            with open(path, 'r', encoding='utf-8') as journal:
                for line in journal:
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError('journal row is not an object')
                        seq = int(row.get('seq'))
                        if seq <= 0:
                            raise ValueError('journal seq must be positive')
                        if previous_seq is not None:
                            if seq <= previous_seq:
                                raise ValueError('journal seq is not increasing')
                            if seq > previous_seq + 1:
                                sequence_gaps += 1
                        previous_seq = seq
                        row.pop('schema', None)
                        row['seq'] = seq
                        row['journal_status'] = 'durable'
                        row.pop('journal_error', None)
                        recovered.append(row)
                        maximum_seq = max(maximum_seq, seq)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        corrupt += 1
        except OSError:
            return
        self.mutation_ring.extend(recovered)
        self.mutation_seq = maximum_seq
        self.mutation_journal_corrupt_lines += corrupt
        self.mutation_journal_sequence_gaps += sequence_gaps
        self.mutation_journal_loaded_records = len(recovered)

    def _safe_journal_text(self, value, key=None):
        if value is None:
            return None
        text = str(value)
        state_dir = getattr(self, 'state_store_dir', None)
        if isinstance(state_dir, str) and state_dir:
            text = text.replace(state_dir, '<state_dir>')
        if isinstance(key, str) and key:
            text = text.replace(key, '<character_key>')
        return text[:512]

    def _append_mutation_journal(self, receipt):
        """Durably append one post-mutation receipt without rolling state back."""
        path = self._mutation_journal_path()
        if path is None:
            return False, 'state_store_dir unavailable'
        disk_row = dict(receipt)
        disk_row['schema'] = 'azrok.mutation.transaction.v1'
        disk_row.pop('journal_status', None)
        disk_row.pop('journal_error', None)
        try:
            encoded = (json.dumps(
                disk_row, ensure_ascii=False, sort_keys=True,
                separators=(',', ':'),
            ) + '\n').encode('utf-8')
            with open(path, 'a+b', buffering=0) as journal:
                if journal.tell() > 0:
                    journal.seek(-1, os.SEEK_END)
                    if journal.read(1) != b'\n':
                        journal.seek(0, os.SEEK_END)
                        journal.write(b'\n')
                    else:
                        journal.seek(0, os.SEEK_END)
                journal.write(encoded)
                os.fsync(journal.fileno())
            return True, None
        except (OSError, TypeError, ValueError) as exc:
            return False, str(exc)[:512]

    @staticmethod
    def _opaque_character_id(key):
        if not isinstance(key, str) or not key:
            return None
        digest = hashlib.sha256(key.encode('utf-8')).hexdigest()
        return f'chr_{digest[:16]}'

    def _record_mutation_transaction(
            self, mutation, result, *, key=None, reason=None,
            revision_before=None, revision_after=None,
            sha256_before=None, sha256_after=None):
        """Append one bounded receipt to the durable best-effort audit journal.

        The selected storage key contains account/name hex and must not be
        exposed in the operator event stream.  Use a stable opaque id while
        keeping the raw key only inside the persistence layer.  Journal I/O
        failure is reported separately and never rolls a committed canonical
        state mutation back.
        """
        self._ensure_mutation_runtime()
        metadata = dict(mutation or {}) if isinstance(mutation, dict) else {
            'kind': str(mutation or 'canonical_save')
        }
        kind = str(metadata.pop('kind', 'canonical_save'))[:64]
        changed_fields = metadata.pop('changed_fields', [])
        if not isinstance(changed_fields, (list, tuple)):
            changed_fields = []
        selected_key = None
        try:
            selected_key = self._selected_character_state_key()
        except (AttributeError, TypeError, ValueError):
            pass
        with self.mutation_lock:
            self.mutation_seq += 1
            receipt = {
                'seq': self.mutation_seq,
                'transaction_id': f'tx-{self.mutation_seq:08d}',
                'timestamp': datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                'kind': kind,
                'result': str(result),
                'character_id': self._opaque_character_id(key),
                'selected_key_valid': bool(key and selected_key == key),
                'request_opcode': metadata.pop('request_opcode', None),
                'packet_seq': metadata.pop('packet_seq', None),
                'revision_before': revision_before,
                'revision_after': revision_after,
                'sha256_before': sha256_before,
                'sha256_after': sha256_after,
                'changed_fields': [str(field)[:96] for field in changed_fields[:64]],
                'reason': self._safe_journal_text(reason, key=key),
                'metadata': self._journal_safe_value(metadata),
            }
            durable, journal_error = self._append_mutation_journal(receipt)
            receipt['journal_status'] = 'durable' if durable else 'failed'
            if journal_error:
                receipt['journal_error'] = self._safe_journal_text(
                    journal_error, key=key
                )
                self.mutation_journal_failures += 1
            self.mutation_ring.append(receipt)
        proto = getattr(self, 'proto_state', None)
        if isinstance(proto, dict):
            proto['last_mutation_transaction'] = dict(receipt)
        try:
            entity_id = self._entity_id_for_proto_state(self.proto_state)
        except (AttributeError, TypeError, ValueError):
            entity_id = None
        self._add_event(
            'transaction',
            f'{kind} {result}',
            entity_id=entity_id,
            severity=(
                'error' if receipt['journal_status'] == 'failed'
                else 'ok' if result == 'committed' else 'warn'
            ),
            details=dict(receipt),
        )
        if receipt['journal_status'] == 'failed':
            self._add_event(
                'audit_journal_failure',
                f'{kind} audit journal append failed',
                entity_id=entity_id,
                severity='error',
                details={
                    'transaction_id': receipt['transaction_id'],
                    'kind': kind,
                    'result': str(result),
                    'journal_status': 'failed',
                },
            )
        return receipt

    def _packet_semantics(self, direction, opcode, payload, origin='auto'):
        """Return direction-specific protocol meaning and bounded decoding."""
        spec = find_spec(direction, opcode)
        if spec is None:
            meaning, category, risk = ('미해독 opcode', 'unknown', 'unknown')
            contract_length_error = None
        else:
            meaning, category, risk = spec.label, spec.category, spec.risk
            contract_length_error = spec.payload.length_error(len(payload))
        decoded = {}
        try:
            if direction == 'C->S' and opcode == 0x00C8:
                decode_c2s_ox_enter_00c8(payload)
                decoded = {'exact_bytes': 0, 'scene_ready': True}
            elif direction == 'C->S' and opcode == 0x00C9:
                decoded = {
                    'level_marker': decode_c2s_ox_leave_00c9(payload),
                    'leave': True,
                }
            elif direction == 'C->S' and opcode == 0x00CA:
                decoded = decode_c2s_ox_answer_00ca(payload)
            elif direction == 'C->S' and opcode == 0x0013:
                count, claimed_total, item_ids = decode_c2s_purchase_0013(payload)
                decoded = {
                    'item_count': count,
                    'claimed_total': claimed_total,
                    'item_ids': item_ids,
                }
            elif direction == 'C->S' and opcode == 0x0014:
                item_id = decode_c2s_item_consume_0014(payload)
                slot = self._inventory_slot_for_item(item_id)
                decoded = {
                    'item_id': item_id,
                    'inventory': slot[0] if slot else None,
                    'slot': slot[1] if slot else None,
                }
            elif direction == 'C->S' and opcode in (0x0008, 0x0009, 0x000A):
                projection = decode_c2s_inventory_snapshot(opcode, payload)
                decoded = {
                    'inventories': {
                        name: {'slots': len(values), 'quantity_sum': sum(values)}
                        for name, values in projection.items()
                    }
                }
            elif direction == 'C->S' and opcode == 0x0010:
                aux, flag = decode_c2s_growth_route_0010(payload)
                decoded = {
                    'kind3_aux': aux,
                    'flag': flag,
                    'edge': 'proposal' if flag == 0 else 'completion_candidate',
                }
            elif direction == 'C->S' and opcode == 0x0011:
                rows = decode_c2s_runtime_rows_0011(payload)
                decoded = {
                    'active_rows': sum(row['kind'] != 0xFF for row in rows),
                    'kind3_aux': next((
                        row['aux'] for row in rows if row['kind'] == 3
                    ), None),
                }
            elif direction == 'C->S' and opcode == 0x0012:
                amount, reward_channel = decode_c2s_quest_reward_0012(payload)
                decoded = {
                    'amount': amount,
                    'reward_channel': reward_channel,
                    'currency': 'FunCorn',
                }
            elif direction == 'C->S' and opcode == 0x0065 and len(payload) >= 10:
                kind, heading, x, y = decode_c2s_0065(payload)
                decoded = {
                    'room_kind': kind,
                    'room_name': self._room_name_from_kind(kind),
                    'direction': heading,
                    'x': x,
                    'y': y,
                }
            elif direction == 'C->S' and opcode == 0x0066 and len(payload) == 22:
                cell, from_x, from_y, to_x, to_y, duration, path_flag = decode_c2s_0066(payload)
                decoded = {
                    'grid_cell': cell,  # compatibility alias: this is current_cell
                    'current_cell': cell,
                    'destination_cell': world_grid_cell(to_x, to_y),
                    'from_x': from_x, 'from_y': from_y,
                    'to_x': to_x, 'to_y': to_y, 'duration': duration,
                    'path_flag': path_flag,
                }
            elif direction == 'C->S' and opcode == 0x0067 and len(payload) == 15:
                cell, x, y, action, angle = decode_c2s_0067(payload)
                decoded = {'grid_cell': cell, 'x': x, 'y': y, 'action': action, 'angle': angle}
            elif direction == 'C->S' and opcode == 0x0007 and len(payload) >= 0xC4:
                stats = struct.unpack_from('<70H', payload, 0x0A)
                decoded = {
                    'snapshot_bytes': len(payload),
                    'natural_evolution': payload[0x05],
                    'dumbbell_stat_0x20': stats[0x20],
                    'progress_sum': struct.unpack_from('<I', payload, 0x96)[0],
                }
            elif direction == 'C->S' and opcode == 0x0068:
                chat = decode_c2s_0068_chat(payload)
                decoded = {
                    'chat_type': chat['type'],
                    'flag': chat['flag'],
                    'target': chat['target_raw'].decode('cp949', errors='replace'),
                    'message': chat['message_raw'].decode('cp949', errors='replace'),
                }
            elif direction == 'C->S' and opcode == 0x0017 and len(payload) >= 6:
                kind, stat_id, value = struct.unpack_from('<BBI', payload, 0)
                decoded = {'kind': kind, 'stat_id': stat_id, 'value': value}
            elif direction == 'C->S' and opcode == 0x0018:
                clear_flag, slot, value = decode_c2s_0018_accessory(payload)
                decoded = {
                    'clear_flag': clear_flag,
                    'action': 'clear' if clear_flag else 'apply',
                    'slot': slot,
                    'value': value,
                }
            elif direction == 'S->C' and opcode == 0x0005 and len(payload) == 6:
                status, subtype, funcorn = struct.unpack('<BBI', payload)
                decoded = {
                    'result': status,
                    'subtype': f'0x{subtype:02X}',
                    'request_opcode': f'0x{subtype:04X}',
                    'funcorn': funcorn,
                    # Compatibility alias used by the existing control UI.
                    'currency': funcorn,
                    'ack': (
                        'G2C_FUNCORN_ACK' if subtype == 0x12 else
                        'shop_result' if subtype == 0x13 else
                        'post_load_state'
                    ),
                }
            elif direction == 'S->C' and opcode == 0x000C:
                if len(payload) != 7:
                    raise ValueError('S2C 0x000C payload must be exactly 7 bytes')
                actor_id, clear_flag, slot, value = struct.unpack('<IBBB', payload)
                decoded = {
                    'actor_id': actor_id,
                    'clear_flag': clear_flag,
                    'action': 'clear' if clear_flag else 'apply',
                    'slot': slot,
                    'value': value,
                }
            elif direction == 'S->C' and opcode == 0x0067 and len(payload) == 4:
                decoded = {'entity_id': struct.unpack_from('<I', payload, 0)[0]}
            elif direction == 'S->C' and opcode == 0x0066:
                decoded = {'actor_records': len(payload) // 0x1A, 'record_size': 0x1A}
            elif direction == 'S->C' and opcode == 0x0068:
                decoded = {'position_records': len(payload) // 0x18, 'record_size': 0x18}
            elif direction == 'S->C' and opcode == 0x00C8:
                validate_s2c_ox_payload(opcode, payload)
                result, marker, ready_value, x, y = struct.unpack('<BBIii', payload)
                decoded = {
                    'result': result, 'level_marker': marker,
                    'ready_value': ready_value, 'x': x, 'y': y,
                }
            elif direction == 'S->C' and opcode == 0x00C9:
                validate_s2c_ox_payload(opcode, payload)
                decoded = {
                    'actor_records': len(payload) // 32,
                    'actor_ids': [
                        struct.unpack_from('<I', payload, offset + 1)[0]
                        for offset in range(0, len(payload), 32)
                    ],
                }
            elif direction == 'S->C' and opcode in (0x00CA, 0x00CB, 0x00CD):
                validate_s2c_ox_payload(opcode, payload)
                decoded = {
                    'actor_ids': [
                        struct.unpack_from('<I', payload, offset)[0]
                        for offset in range(0, len(payload), 4)
                    ]
                }
            elif direction == 'S->C' and opcode == 0x00CE:
                validate_s2c_ox_payload(opcode, payload)
                decoded = {
                    'question': payload[:0x80].split(b'\x00', 1)[0].decode(
                        'cp949', errors='replace'
                    ),
                    'question_type': payload[0x80],
                    'correct_side': payload[0x81],
                    'stars': payload[0x82],
                }
            elif direction == 'S->C' and opcode == 0x00D0:
                validate_s2c_ox_payload(opcode, payload)
                actor_id, x, y = struct.unpack_from('<Iii', payload, 0)
                decoded = {'actor_id': actor_id, 'x': x, 'y': y}
            elif direction == 'S->C' and opcode == 0x00D3:
                validate_s2c_ox_payload(opcode, payload)
                first, second = struct.unpack('<HH', payload)
                decoded = {'first': first, 'second': second}
            elif direction == 'S->C' and opcode in (0x00CC, 0x00D2, 0x00D4):
                validate_s2c_ox_payload(opcode, payload)
                decoded = {'exact_bytes': 0}
            elif opcode == 0x0016 and payload:
                decoded = {'sample_kind': payload[0]}
        except (struct.error, IndexError, ValueError, UnicodeError):
            decoded = {'decode_error': True}
        return {
            'meaning': meaning,
            'category': category,
            'risk': risk,
            'decoded': decoded,
            'protocol_spec_id': spec.stable_id if spec else None,
            'contract_length': spec.payload.display() if spec else None,
            'contract_length_error': contract_length_error,
        }

    def _record_client_packet(self, conn, direction, opcode, origin, semantics):
        if conn is None:
            return None
        with self.ctl_lock:
            meta = self.client_meta.get(conn)
            if meta is None:
                return None
            count_key = f'{direction} 0x{opcode:04X}'
            meta['opcode_counts'][count_key] = meta['opcode_counts'].get(count_key, 0) + 1
            if direction == 'C->S':
                meta['rx_packets'] += 1
                meta['last_opcode'] = f'0x{opcode:04X}'
                meta['last_seen'] = time.time()
                if semantics.get('category') == 'unknown':
                    meta['unknown_c2s_count'] += 1
            else:
                meta['tx_packets'] += 1
                meta['last_tx_opcode'] = f'0x{opcode:04X}'
                meta['last_tx_at'] = time.time()
                if origin == 'relay':
                    meta['relay_tx_packets'] += 1
            return meta.get('entity_id')

    def _log_packet(self, direction, num, opcode, payload, raw, origin='auto', conn=None):
        """Write a packet to both log files immediately, and record it for the control panel."""
        semantics = self._packet_semantics(direction, opcode, payload, origin)
        entity_id = self._record_client_packet(conn, direction, opcode, origin, semantics)
        with self.ctl_lock:
            connection_meta = dict(self.client_meta.get(conn, {})) if conn is not None else None
        self.structured_capture.append(
            direction=direction,
            packet_number=num,
            opcode=opcode,
            payload=payload,
            raw=raw,
            origin=origin,
            semantics=semantics,
            entity_id=entity_id,
            connection=connection_meta,
        )
        with self.log_lock:
            tag = '' if origin == 'auto' else f" [{origin}]"
            lines = [f"[{direction}] #{num} opcode=0x{opcode:04X} payload={len(payload)}B "
                     f"total={len(raw)}B{tag}\n"]
            for j in range(0, len(raw), 16):
                chunk = raw[j:j+16]
                hex_part = ' '.join(f'{b:02X}' for b in chunk)
                ascii_part = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
                lines.append(f"  {j:04X}: {hex_part:<48} {ascii_part}\n")
            if len(payload) > 0 and opcode != 0x0016:
                lines.append(f"  Payload only: {payload.hex()}\n")
            lines.append('\n')
            blob = ''.join(lines)
            for f in (self.capture_file, self.log_file):
                f.write(blob)
                f.flush()

        with self.ctl_lock:
            self.emit_seq += 1
            self.packet_ring.append({
                'seq': self.emit_seq,
                't': time.strftime('%H:%M:%S') + f".{int(time.time() * 1000) % 1000:03d}",
                'dir': direction,
                'opcode': f"0x{opcode:04X}",
                'len': len(payload),
                'origin': origin,
                'hex': payload.hex(),
                'entity_id': entity_id,
                **semantics,
            })

    def _emit(self, conn, data, origin='auto', pkt_num=0):
        """The single outbound chokepoint. Every S->C byte goes through here.

        When paused, 'auto' traffic is held until the control panel steps or drops it —
        this blocks the client handler thread on purpose; it is a protocol breakpoint.
        Manual and macro sends bypass the gate: they are already deliberate acts.
        """
        if self.paused and origin == 'auto':
            item = {'data': data, 'origin': origin,
                    'ev': threading.Event(), 'action': None}
            with self.ctl_lock:
                self.pending_out.append(item)
            item['ev'].wait()
            if item['action'] == 'drop':
                for op, pay, raw in self._parse_packets(data)[0]:
                    print(f"  [CTL] DROPPED opcode=0x{op:04X}, payload={len(pay)}B")
                return False

        try:
            conn.sendall(data)
        except Exception as e:
            print(f"  [CTL] send failed ({origin}): {e}")
            return False

        for op, pay, raw in self._parse_packets(data)[0]:
            if origin == 'auto':
                print(f"  [SEND] opcode=0x{op:04X}, payload={len(pay)}B")
                if op != 0x0016:
                    print(self._hex_dump(raw))
            else:
                print(f"  [SEND/{origin}] opcode=0x{op:04X}, payload={len(pay)}B")
            self._log_packet('S->C', pkt_num, op, pay, raw, origin=origin, conn=conn)
        return True

    # ── Control panel surface (azrok_control.py / azrok_ctl.py) ──

    def _active_conn(self):
        return self.connections[-1] if self.connections else None

    def _conn_for_entity(self, entity_id):
        """Resolve a real connected client by the server-assigned entity id.

        The control panel historically targeted only ``connections[-1]``.
        That is ambiguous as soon as a reused-server secondary joins, so the
        protocol test harness may now address one real socket explicitly.
        Entity ids are internal metadata; this does not invent a client or
        alter the wire contract.
        """
        try:
            wanted = int(entity_id)
        except (TypeError, ValueError):
            return None
        with self.ctl_lock:
            for conn, meta in self.client_meta.items():
                if conn in self.connections and int(meta.get('entity_id', -1)) == wanted:
                    return conn
        return None

    def _proto_state_for_conn(self, conn):
        with self.ctl_lock:
            meta = self.client_meta.get(conn)
            state = meta.get('proto_state') if meta else None
        return state if state is not None else self.proto_state

    def _active_proto_state(self):
        """Return the control-panel target's isolated protocol state."""
        with self.ctl_lock:
            conn = self.connections[-1] if self.connections else None
            meta = self.client_meta.get(conn) if conn is not None else None
            state = meta.get('proto_state') if meta else None
        return state if state is not None else self.proto_state

    def _entity_id_for_proto_state(self, state):
        with self.ctl_lock:
            for conn, meta in self.client_meta.items():
                if conn in self.connections and meta.get('proto_state') is state:
                    return meta.get('entity_id')
        return None

    @staticmethod
    def _room_name_from_kind(kind):
        # C2S 0x0065 is <kind,direction,x,y>; Gym is kind 0x08 and the
        # observed second byte 0x15 is direction/orientation, not a room.
        if kind == 0x15:
            return f'kind 0x{kind:02X}'
        return {
            **LOCAL_ROOM_NAMES_BY_WIRE_KIND,
            # 0x15 is the second field (direction/orientation) of C2S 0x0065,
            # not a room kind; it is handled by the guard above.
            0x1B: 'plaza (observed C2S kind)',
        }.get(kind, f'kind 0x{kind:02X}')

    def _update_client_identity(self, source, opcode, payload):
        """Remember the character fields carried by the create packet.

        The fields are display/relay metadata only; they do not alter the
        single-client protocol state machine.  Keeping this separate from the
        room relay also means a client can finish login before it enters a
        local room.
        """
        if opcode == 0x0000:
            try:
                _login_type, account_raw, _password_raw = decode_c2s_login_0000(payload)
            except ValueError:
                return
            account_name = account_raw.decode('cp949', errors='replace').strip()
            self.proto_state['account_raw'] = account_raw
            self.proto_state['account_name'] = account_name
            with self.ctl_lock:
                meta = self.client_meta.get(source)
                if meta is not None:
                    meta['account'] = account_name
                    meta['last_opcode'] = f'0x{opcode:04X}'
                    meta['last_seen'] = time.time()
            return
        if opcode == 0x0064 and payload:
            # C→S 0x0064 is the natural Hansol stage-0 completion report.
            # It is not an ACK request: the normal response builder sends
            # only the authoritative S→C 0x0064.  For relay bookkeeping it is
            # nevertheless a direct, direction-verified Plaza boundary.
            old_kind = None
            entity_id = None
            with self.ctl_lock:
                meta = self.client_meta.get(source)
                if meta is not None:
                    old_kind = meta.get('room_kind')
                    meta['room_kind'] = PLAZA_ROOM_KIND
                    meta['room_name'] = 'plaza (0064-only)'
                    # The authoritative S2C 0x0064 places every local client
                    # at the supported Plaza spawn.  Preserve that server-
                    # known fact for the first remote-actor position record;
                    # later C2S movement reports replace it with live values.
                    meta['x'] = DEFAULT_SPAWN_X
                    meta['y'] = DEFAULT_SPAWN_Y
                    meta['last_opcode'] = f'0x{opcode:04X}'
                    meta['last_seen'] = time.time()
                    if old_kind != PLAZA_ROOM_KIND:
                        meta['roster_bootstrapped'] = False
                        meta.pop('plaza_chair_request', None)
                        meta.pop('plaza_chair_seat', None)
                    entity_id = meta.get('entity_id')
            if old_kind != PLAZA_ROOM_KIND:
                self._add_event(
                    'room', f'클라이언트 #{entity_id}가 Plaza state-1 경계에 진입했습니다.',
                    entity_id=entity_id, severity='ok',
                    details={'from_kind': old_kind, 'to_kind': PLAZA_ROOM_KIND},
                )
            self.proto_state['current_room_kind'] = PLAZA_ROOM_KIND
            self.proto_state['facility_plaza_return_sent'] = False
            return
        if opcode == 0x0005 and len(payload) == 1 and payload[0] <= 3:
            # Slot/continue carries no name.  It is nevertheless the first
            # per-client evidence that the character-selection screen was
            # accepted, so expose the local PatHouse bootstrap in the panel
            # without pretending that a server room-membership opcode arrived.
            slot_record = (self.proto_state.get('lobby_slots') or {}).get(payload[0])
            if slot_record is None:
                return
            with self.ctl_lock:
                meta = self.client_meta.get(source)
                if meta is not None:
                    meta['char_type'] = int(slot_record.get('species', AZRON_SPECIES)) & 0x03
                    meta['name'] = meta.get('name') or 'Azrok1'
                    meta['room_kind'] = LOCAL_PAT_HOUSE_ROOM_KIND
                    meta['room_name'] = 'PatHouse (local)'
                    meta.pop('plaza_chair_request', None)
                    meta.pop('plaza_chair_seat', None)
                    meta['last_opcode'] = f'0x{opcode:04X}'
                    meta['last_seen'] = time.time()
            self.proto_state['current_room_kind'] = LOCAL_PAT_HOUSE_ROOM_KIND
            self.proto_state['facility_plaza_return_sent'] = False
            return
        if opcode == 0x0007 and len(payload) >= 196:
            first_client_snapshot = self.proto_state.get('client_0007_count', 0) == 0
            with self.ctl_lock:
                meta = self.client_meta.get(source)
                if meta is not None:
                    # The full C2S 0x0007 carries the client state blob but
                    # not a reliable display name/species slot.  Reuse the
                    # already verified bootstrap identity so a later state-1
                    # roster has real appearance metadata for both clients.
                    bootstrap_type = self.proto_state.get('char_type')
                    if isinstance(bootstrap_type, int) and 0 <= bootstrap_type <= 3:
                        meta['char_type'] = bootstrap_type
                    raw_name = self.proto_state.get('char_name_raw')
                    if isinstance(raw_name, (bytes, bytearray)) and raw_name:
                        try:
                            decoded_name = bytes(raw_name).split(b'\x00', 1)[0].decode('cp949', errors='ignore').strip()
                        except Exception:
                            decoded_name = ''
                        if decoded_name:
                            meta['name'] = decoded_name[:12]
                    # Only the first C2S 0x0007 belongs to the login/bootstrap
                    # boundary.  Later 196-byte packets are content-save
                    # snapshots (Gym and other local activities) and must not
                    # teleport the panel metadata back to PatHouse.
                    if first_client_snapshot and meta.get('room_kind') in (None, LOCAL_PAT_HOUSE_ROOM_KIND):
                        meta['room_kind'] = LOCAL_PAT_HOUSE_ROOM_KIND
                        meta['room_name'] = 'PatHouse (local)'
                    meta['last_opcode'] = f'0x{opcode:04X}'
                    meta['last_seen'] = time.time()
            return
        if opcode != 0x0004 or len(payload) < 15:
            return
        raw_name = bytes(payload[1:15]).split(b'\x00', 1)[0]
        try:
            name = raw_name.decode('cp949', errors='ignore').strip() or 'Player'
        except Exception:
            name = 'Player'
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if meta is not None:
                meta['char_type'] = payload[0]
                meta['name'] = name[:12]
                meta['last_opcode'] = f'0x{opcode:04X}'
                meta['last_seen'] = time.time()

    def _room_snapshot(self, room_kind):
        """Copy one room's metadata without holding the lock during sends."""
        with self.ctl_lock:
            return [
                (conn, dict(meta))
                for conn, meta in self.client_meta.items()
                if conn in self.connections and meta.get('room_kind') == room_kind
            ]

    def _send_room_roster(self, recipient, room_kind):
        """Upsert real remote actors for one state-1 Plaza recipient.

        Do not proactively emit the destructive empty S2C 0x0065 flush here.
        A clean x32dbg trace proved that sending it immediately after the
        authoritative S2C 0x0064 reaches mode 1 and then faults at 0x005F3AF4.
        There is also nothing to flush in a one-client room.  S2C 0x0066 and
        0x0068 are emitted only for real connected peers; 0x0066 cannot
        update the fixed self actor (the client rejects its self id before
        copying record fields), so deliberately keep actor id 1 out of this
        remote roster.  Removal/flush stays disabled until its direction-
        specific lifecycle contract is proven.
        """
        # Remote actor roster opcodes are state-1 Plaza traffic.  C2S 0x0065
        # also reports local-room membership, but those mode-0 rooms must not
        # receive this dispatch family.
        if room_kind != PLAZA_ROOM_KIND:
            return
        with self.ctl_lock:
            recipient_meta = self.client_meta.get(recipient)
            if recipient not in self.connections or recipient_meta is None:
                return
            current_visible = set(recipient_meta.get('visible_remote_actor_ids') or ())

        # Deduplicate real peers by entity id, keep already-visible actors
        # stable, then fill unused slots in deterministic id order.  The
        # client silently refuses its 101st remote actor, but enforcing the
        # physical limit here also prevents us from relaying state for an
        # actor that the recipient could never render.
        unique_peers = {}
        for conn, meta in self._room_snapshot(room_kind):
            if conn is recipient:
                continue
            entity_id = int(meta.get('entity_id') or 0)
            if entity_id > 0:
                unique_peers.setdefault(entity_id, (conn, meta))
        ordered_ids = sorted(unique_peers, key=lambda actor_id: (actor_id not in current_visible, actor_id))
        admitted_ids = ordered_ids[:MAX_REMOTE_ACTORS_PER_CLIENT]
        admitted = [unique_peers[actor_id] for actor_id in admitted_ids]
        admitted_set = set(admitted_ids)

        # A recipient that changes room still holds its old remote actors.
        # Remove only those stale actors; never use S2C 0x0065 after self is
        # live because that handler tears down the fixed self slot first.
        for stale_id in sorted(current_visible - admitted_set):
            payload = self._build_state_0067_actor_remove_record(stale_id)
            self._emit(recipient, self._make_packet(0x0067, payload), origin='relay')

        for conn, meta in admitted:
            name_raw = str(meta.get('name') or 'Player').encode('cp949', errors='ignore')
            peer_state = meta.get('proto_state') or {}
            peer_key = (
                peer_state.get('selected_character_key')
                if peer_state.get('client_0005_seen') else None
            )
            accessory_slots = self._read_canonical_accessory_slots(peer_key)
            evolution = self._read_canonical_actor_evolution(peer_key, peer_state)
            record = self._build_state_0066_actor_record(
                meta.get('entity_id', 0), meta.get('char_type', 0), name_raw,
                action=0 if meta.get('plaza_chair_seat') is not None else 0x0A,
                accessory_slots=accessory_slots,
                evolution=evolution,
                chair_seat=meta.get('plaza_chair_seat'),
            )
            position = self._build_state_0068_actor_position_record(
                meta.get('entity_id', 0),
                x=meta.get('x') or 0,
                y=meta.get('y') or 0,
                heading=meta.get('heading') or 0,
            )
            self._emit(recipient, self._make_packet(0x0066, record), origin='relay')
            if meta.get('plaza_chair_seat') is None:
                self._emit(recipient, self._make_packet(0x0068, position), origin='relay')
        with self.ctl_lock:
            recipient_meta = self.client_meta.get(recipient) or {}
            if recipient_meta:
                recipient_meta['visible_remote_actor_ids'] = admitted_set
            recipient_id = recipient_meta.get('entity_id')
        self._add_event(
            'roster', f'클라이언트 #{recipient_id}에 원격 액터 {len(admitted)}명을 upsert했습니다.',
            entity_id=recipient_id, severity='info',
            details={
                'peers': admitted_ids,
                'candidate_count': len(unique_peers),
                'slot_cap': MAX_REMOTE_ACTORS_PER_CLIENT,
                'capped': max(0, len(unique_peers) - len(admitted)),
            },
        )

    def _plaza_relay_position_frame(self, source, entity_id, x, y,
                                    pkt_num=0, generation=None):
        """Relay one gated Plaza S2C 0x0068 position frame.

        The lock makes a worker-generated frame and an arrival commit
        serialize on each server-wide relay path.  The recipient admission
        test intentionally remains the existing ``visible_remote_actor_ids``
        gate; this helper does not promote or invent visibility.
        """
        relay_lock = getattr(self, '_plaza_relay_lock', None)
        if relay_lock is None:
            relay_lock = threading.RLock()
            self._plaza_relay_lock = relay_lock
        with relay_lock:
            with self.ctl_lock:
                meta = self.client_meta.get(source)
                if (meta is None or source not in self.connections
                        or meta.get('room_kind') != PLAZA_ROOM_KIND):
                    return False
                if (generation is not None
                        and int(meta.get('movement_generation', 0)) != int(generation)):
                    return False
                entity_id = int(meta.get('entity_id') or entity_id)
                heading = int(meta.get('heading') or 0) & 0xFFFFFFFF
                meta['x'], meta['y'] = int(x), int(y)
                peers = []
                for peer, peer_meta in self.client_meta.items():
                    if (peer is source or peer not in self.connections
                            or peer_meta.get('room_kind') != PLAZA_ROOM_KIND):
                        continue
                    visible = set(peer_meta.get('visible_remote_actor_ids') or ())
                    if entity_id in visible:
                        peers.append(peer)
                position = self._build_state_0068_actor_position_record(
                    entity_id, x=x, y=y, heading=heading,
                )
                packet = self._make_packet(0x0068, position)

            sent = False
            for peer in peers:
                sent = bool(self._emit(
                    peer, packet, origin='relay', pkt_num=pkt_num,
                )) or sent
            if sent:
                with self.ctl_lock:
                    live_meta = self.client_meta.get(source)
                    if live_meta is not None:
                        live_meta['movement_frames_relayed'] = (
                            int(live_meta.get('movement_frames_relayed', 0)) + 1
                        )
            return sent

    def _plaza_relay_movement_intent(self, source, entity_id, start_x, start_y,
                                     end_x, end_y, arrival_tick, generation=None,
                                     pkt_num=0):
        """Relay one C2S 0x0066 intent as a single walking 0x0068.

        The interpolated variant below produces smooth positions but every
        frame takes the ``record[5] == 0`` placement branch, which sets the
        actor to state 1 (idle) and applies only x,y - so the remote actor
        slides without a walk animation and without turning.  Sending the
        intent once takes the ``record[5] != 0`` branch instead: the client
        interpolates on its own clock, plays state 2, and derives facing from
        the direction.  Same visibility gate, one packet instead of hundreds.

        ``arrival_tick`` is an absolute deadline on the shared server-synced
        clock, forwarded from the sender's own C2S 0x0066.  See doc 538.
        """
        relay_lock = getattr(self, '_plaza_relay_lock', None)
        if relay_lock is None:
            relay_lock = threading.RLock()
            self._plaza_relay_lock = relay_lock
        arrival_tick = int(arrival_tick) & 0xFFFFFFFF
        with relay_lock:
            with self.ctl_lock:
                meta = self.client_meta.get(source)
                if (meta is None or source not in self.connections
                        or meta.get('room_kind') != PLAZA_ROOM_KIND):
                    return False
                if (generation is not None
                        and int(meta.get('movement_generation', 0)) != int(generation)):
                    return False
                entity_id = int(meta.get('entity_id') or entity_id)
                # The authoritative position becomes the destination; the client
                # animates the way there itself.
                meta['x'], meta['y'] = int(end_x), int(end_y)
                peers = []
                for peer, peer_meta in self.client_meta.items():
                    if (peer is source or peer not in self.connections
                            or peer_meta.get('room_kind') != PLAZA_ROOM_KIND):
                        continue
                    visible = set(peer_meta.get('visible_remote_actor_ids') or ())
                    if entity_id in visible:
                        peers.append(peer)
                packet = self._make_packet(0x0068, self._build_state_0068_movement_record(
                    entity_id, int(start_x), int(start_y),
                    int(end_x), int(end_y), arrival_tick,
                ))

            sent = False
            for peer in peers:
                sent = bool(self._emit(
                    peer, packet, origin='relay', pkt_num=pkt_num,
                )) or sent
            if sent:
                with self.ctl_lock:
                    live_meta = self.client_meta.get(source)
                    if live_meta is not None:
                        live_meta['movement_frames_relayed'] = (
                            int(live_meta.get('movement_frames_relayed', 0)) + 1
                        )
            return sent

    def _plaza_movement_worker(self, source, entity_id, start_x, start_y,
                               end_x, end_y, duration_ms, generation,
                               pkt_num):
        """Emit interpolated 0x0068 frames for one C2S 0x0066 intent."""
        duration_ms = max(0, int(duration_ms))
        if duration_ms <= 0:
            self._plaza_relay_position_frame(
                source, entity_id, end_x, end_y,
                pkt_num=pkt_num, generation=generation,
            )
            return

        frame_count = max(
            1,
            (duration_ms + PLAZA_MOVEMENT_RELAY_INTERVAL_MS - 1)
            // PLAZA_MOVEMENT_RELAY_INTERVAL_MS,
        )
        started = time.monotonic()
        for frame_index in range(1, frame_count + 1):
            target_at = started + (duration_ms / 1000.0) * frame_index / frame_count
            delay = target_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            ratio = frame_index / frame_count
            x = int(round(start_x + (end_x - start_x) * ratio))
            y = int(round(start_y + (end_y - start_y) * ratio))
            if not self._plaza_relay_position_frame(
                    source, entity_id, x, y,
                    pkt_num=pkt_num, generation=generation):
                return

    def _start_plaza_movement_relay(self, source, entity_id, start_x, start_y,
                                    end_x, end_y, duration_ms, generation,
                                    pkt_num):
        """Relay one C2S 0x0066 intent to the peers that can see this actor.

        The sixth C2S dword is a **relative** duration in milliseconds.
        Measured 2026-07-30 on two live sessions: 217 and 795 for two ordinary
        click-to-move steps, scaling with the distance walked.  The static read
        that made it an absolute tick (doc 538 §3) came from 0x0061A420, which
        is only one of three callers of the 0x005AB7B0 packer and is not the
        one a click goes through.

        ``record[5]`` on the way back out is the opposite: 0x0061A710 compares
        it against the server-synced clock, so it must be an **absolute**
        deadline.  The conversion is the server's job:

            record[5] = server_now_ms + duration_ms

        Both clients ran their five S2C 0x0004 samples, so their clock equals
        ``int(time.time()*1000) & 0xFFFFFFFF`` - our own.  See doc 538.

        A duration outside a sane window means the sender is not walking on
        our clock at all; that falls back to interpolation, which is smooth
        even though it cannot produce the walk state or the facing.  It must
        never fall back to a single placement frame - that is a teleport.
        """
        duration_ms = int(duration_ms)
        usable = 0 < duration_ms <= PLAZA_MOVEMENT_MAX_DURATION_MS
        now_ms = int(time.time() * 1000) & 0xFFFFFFFF
        arrival_tick = (now_ms + duration_ms) & 0xFFFFFFFF
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if meta is not None:
                meta['movement_duration_ms'] = duration_ms
                meta['movement_arrival_tick'] = arrival_tick if usable else 0
                if not usable:
                    meta['movement_duration_rejects'] = (
                        int(meta.get('movement_duration_rejects', 0)) + 1
                    )
        if not usable:
            # Nothing to animate over: place the actor and stop.
            return bool(self._plaza_relay_position_frame(
                source, entity_id, end_x, end_y,
                pkt_num=pkt_num, generation=generation))
        if PLAZA_MOVEMENT_RELAY_MODE == 'intent':
            return self._plaza_relay_movement_intent(
                source, entity_id, start_x, start_y, end_x, end_y,
                arrival_tick, generation=generation, pkt_num=pkt_num,
            )
        threading.Thread(
            target=self._plaza_movement_worker,
            args=(source, entity_id, start_x, start_y, end_x, end_y,
                  duration_ms, generation, pkt_num),
            daemon=True,
        ).start()
        return True

    def _notify_room_departure(self, source, room_kind=None):
        """Remove one real departed actor from old state-1 Plaza peers.

        S2C 0x0067 consumes exactly one little-endian DWORD actor id and walks
        only the remote-actor list.  Snapshot peers before changing/removing
        source metadata, never send it to the departing source, and never send
        this state-1 opcode to local mode-0 rooms.
        """
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta:
                return
            meta.pop('plaza_chair_seat', None)
            meta.pop('plaza_chair_request', None)
            departed_id = int(meta.get('entity_id') or 0)
            departed_room = meta.get('room_kind') if room_kind is None else room_kind
            peers = [
                (conn, dict(other)) for conn, other in self.client_meta.items()
                if conn is not source
                and conn in self.connections
                and other.get('room_kind') == departed_room
            ]
        if departed_room != PLAZA_ROOM_KIND or departed_id <= 0:
            return
        payload = self._build_state_0067_actor_remove_record(departed_id)
        for peer, other in peers:
            # The binary's remote-list removal cannot remove the fixed self
            # slot, but its auxiliary target cleanup has no self guard.
            if int(other.get('entity_id') or 0) == departed_id:
                continue
            with self.ctl_lock:
                live_meta = self.client_meta.get(peer)
                visible = set(live_meta.get('visible_remote_actor_ids') or ()) if live_meta else set()
                if departed_id not in visible:
                    continue
                visible.discard(departed_id)
                live_meta['visible_remote_actor_ids'] = visible
            self._emit(peer, self._make_packet(0x0067, payload), origin='relay')

    def _notify_local_room_roster(self, source):
        """Publish real peer upserts only after state-1 Plaza admission.

        PatHouse runs dispatch mode 0, so state-1 roster packets must not be
        injected there merely because C2S 0x0007 completed.  C2S 0x0064 is
        the verified Plaza boundary; ``_update_client_identity`` changes the
        room kind before this method runs.
        """
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta or meta.get('room_kind') != PLAZA_ROOM_KIND:
                return
            if meta.get('roster_bootstrapped'):
                return
            meta['roster_bootstrapped'] = True
            targets = [
                conn for conn, other in self.client_meta.items()
                if conn in self.connections
                and other.get('room_kind') == meta.get('room_kind')
            ]
        for recipient in targets:
            self._send_room_roster(recipient, meta.get('room_kind'))

    def _ensure_ox_runtime(self):
        """Initialize OX-only fields for lightweight test/server instances."""
        if not hasattr(self, 'ox_lock'):
            self.ox_lock = threading.RLock()
        if not hasattr(self, 'ox_action_lock'):
            self.ox_action_lock = threading.RLock()
        if not hasattr(self, 'ox_rooms'):
            self.ox_rooms = {}
        if not hasattr(self, 'ox_receive_seq'):
            self.ox_receive_seq = 0
        if not hasattr(self, 'ox_side_cells'):
            self.ox_side_cells = {
                side: frozenset(cells)
                for side, cells in OX_SIDE_CELLS_DEFAULT.items()
            }
        if not hasattr(self, 'ox_questions'):
            self.ox_questions = tuple(dict(q) for q in OX_SAMPLE_QUESTIONS)
        if not hasattr(self, 'ox_spawn_x'):
            self.ox_spawn_x = 0
        if not hasattr(self, 'ox_spawn_y'):
            self.ox_spawn_y = 0
        if not hasattr(self, 'ox_auto_policy'):
            self.ox_auto_policy = _ox_auto_policy_from_env()
        if not hasattr(self, 'ox_scheduler_stop'):
            self.ox_scheduler_stop = threading.Event()
        if not hasattr(self, 'ox_scheduler_thread'):
            self.ox_scheduler_thread = None
        if not hasattr(self, 'ox_pending_results'):
            self.ox_pending_results = []

    def _ox_retry_pending_results(self):
        """Retry disconnect results after a temporary state-store failure."""
        remaining = []
        for key, match_id, outcome, rounds_survived in self.ox_pending_results:
            try:
                record_ox_result(
                    self.state_store_dir, key, match_id, outcome,
                    rounds_survived,
                )
            except (OSError, TypeError, ValueError):
                remaining.append((key, match_id, outcome, rounds_survived))
        self.ox_pending_results = remaining

    def _ox_commit_result(self, room_id, entity_id, outcome, rounds_survived):
        """Commit an adjudicated result against the identity bound at prepare."""
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            match_id = room.get('match_id')
            selected_key = room.get('result_keys', {}).get(entity_id)
        if not match_id or not selected_key:
            return False
        with self.ctl_lock:
            live_keys = [
                selected_ox_character_key(meta.get('proto_state'))
                for conn, meta in self.client_meta.items()
                if conn in self.connections
                and int(meta.get('entity_id') or 0) == entity_id
                and meta.get('ox_room_id') == room_id
            ]
        if selected_key not in live_keys:
            return False
        try:
            return record_ox_result(
                self.state_store_dir, selected_key, match_id,
                outcome, rounds_survived,
            )
        except (OSError, TypeError, ValueError) as exc:
            self._add_event(
                'ox_result_save_failed', 'OX result persistence failed',
                entity_id=entity_id, severity='warn',
                details={'error_type': type(exc).__name__},
            )
            return None

    def _ox_room_locked(self, room_id=DEFAULT_OX_ROOM_ID):
        room = self.ox_rooms.get(room_id)
        if room is None:
            room = {
                'room_id': room_id,
                'phase': 'idle',
                'match_generation': 0,
                'match_id': None,
                'result_keys': {},
                'generation': 0,
                'participants': set(),
                'survivors': set(),
                'spectators': set(),
                'answers': {},
                'positions': {},
                'question_index': None,
                'question': None,
                'correct_cells': None,
                'opened_at': None,
                'deadline_at': None,
                'closed_at': None,
                'losers': [],
                'finish_exit_mode': None,
                'last_admitted_at': None,
                'ready_at': None,
                'finished_at': None,
                'rounds_completed': 0,
                'next_action': None,
                'next_due_at': None,
                'auto_stalled_at': None,
                'last_auto_error': None,
                'history': [],
            }
            self.ox_rooms[room_id] = room
        # Keep hot-reloaded/test-created room dictionaries forward-compatible.
        room.setdefault('spectators', set())
        room.setdefault('match_id', None)
        room.setdefault('result_keys', {})
        room.setdefault('last_admitted_at', None)
        room.setdefault('ready_at', None)
        room.setdefault('finished_at', None)
        room.setdefault('rounds_completed', 0)
        room.setdefault('next_action', None)
        room.setdefault('next_due_at', None)
        room.setdefault('auto_stalled_at', None)
        room.setdefault('last_auto_error', None)
        return room

    def _ox_members(self, room_id=DEFAULT_OX_ROOM_ID, entity_ids=None):
        wanted = set(entity_ids) if entity_ids is not None else None
        with self.ctl_lock:
            return [
                (conn, dict(meta))
                for conn, meta in self.client_meta.items()
                if conn in self.connections
                and meta.get('room_kind') == LOCAL_OX_ROOM_KIND
                and meta.get('ox_room_id') == room_id
                and (wanted is None or int(meta.get('entity_id') or 0) in wanted)
            ]

    @staticmethod
    def _ox_wire_actor_id(recipient_meta, server_entity_id):
        """Translate the recipient's fixed self slot to id 1."""
        if int(recipient_meta.get('entity_id') or 0) == int(server_entity_id):
            return DEFAULT_ACTOR_ID
        return int(server_entity_id)

    def _ox_packet(self, opcode, payload=b''):
        return self._make_packet(opcode, validate_s2c_ox_payload(opcode, payload))

    def _ox_emit(self, recipient, opcode, payload=b'', pkt_num=0):
        return self._emit(
            recipient, self._ox_packet(opcode, payload),
            origin='ox', pkt_num=pkt_num,
        )

    def _ox_actor_record(self, recipient_meta, actor_meta):
        actor_id = self._ox_wire_actor_id(
            recipient_meta, actor_meta.get('entity_id')
        )
        name = str(actor_meta.get('name') or 'Player')
        name_raw = bytearray()
        for char in name:
            encoded = char.encode('cp949', errors='ignore')
            if len(name_raw) + len(encoded) > 12:
                break
            name_raw.extend(encoded)
        return build_s2c_ox_remote_00c9(
            actor_id=actor_id,
            char_type=int(actor_meta.get('char_type') or 0),
            name_raw=bytes(name_raw) or b'Player',
            x=int(actor_meta.get('x') if actor_meta.get('x') is not None else self.ox_spawn_x),
            y=int(actor_meta.get('y') if actor_meta.get('y') is not None else self.ox_spawn_y),
        )

    @ox_serialized
    def _handle_ox_portal_request_006b(self, source, payload, pkt_num=0,
                                       request_origin='natural'):
        """Answer the natural Plaza OX door request with exact 006E[0000].

        Live packet order is C2S 006B(empty) -> S2C 006E[0000] -> natural
        C2S 00C8.  This response is request-bound and is deliberately separate
        from the automatic-after-C8 round scheduler, which never invents an
        OX entry on its own.
        """
        self._ensure_ox_runtime()
        if payload != b'':
            self._add_event(
                'ox_portal_reject',
                f'C2S 0x006B must be empty, got {len(payload)} bytes',
                severity='warn',
            )
            return False
        now = time.monotonic()
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if source not in self.connections or meta is None:
                return False
            entity_id = int(meta.get('entity_id') or 0)
            if meta.get('room_kind') != PLAZA_ROOM_KIND:
                self._add_event(
                    'ox_portal_reject',
                    'OX portal request is allowed only from healthy Plaza',
                    entity_id=entity_id, severity='warn',
                    details={'room_kind': meta.get('room_kind')},
                )
                return False
            previous = meta.get('ox_portal_006b_at')
            if previous is not None and now - float(previous) < 5.0:
                self._add_event(
                    'ox_portal_duplicate',
                    'duplicate OX portal request ignored while C8 is pending',
                    entity_id=entity_id, severity='info',
                )
                return True
            meta['ox_portal_006b_at'] = now
        self._emit(
            source, self._make_packet(0x006E, b'\x00\x00'),
            origin='ox', pkt_num=pkt_num,
        )
        request_label = (
            f'client #{entity_id} requested the OX portal'
            if request_origin == 'natural' else
            f'protocol controller entered client #{entity_id} into the OX portal'
        )
        self._add_event(
            'ox_portal', request_label,
            entity_id=entity_id, severity='ok',
            details={
                'request_origin': request_origin,
                'c2s': '0x006B exact0' if request_origin == 'natural' else None,
                's2c': '0x006E[0000]',
                'next_expected': 'C2S 0x00C8',
            },
        )
        return True

    def request_ox_portal(self, entity_id=None):
        """Enter a healthy Plaza client through the exact OX portal reply.

        This is an operator control boundary for deterministic diagnostics: it
        invokes the same validated Plaza/connection/duplicate gate as a real
        empty C2S 0x006B request, emits only S2C 0x006E[0000], and leaves the
        following C2S 0x00C8 admission natural.  It intentionally does not
        fabricate or log a client-originated 0x006B packet.
        """
        source = (
            self._conn_for_entity(entity_id)
            if entity_id is not None else self._active_conn()
        )
        if source is None:
            return False, (
                'target client not connected'
                if entity_id is not None else 'no client connected'
            )
        ok = self._handle_ox_portal_request_006b(
            source, b'', request_origin='protocol-control'
        )
        return (
            True, 'OX portal control reply sent; waiting for natural C2S 0x00C8'
        ) if ok else (False, 'OX portal control request was rejected')

    @ox_serialized
    def _handle_ox_enter(self, source, payload, pkt_num=0,
                         room_id=DEFAULT_OX_ROOM_ID, require_portal=False):
        """Admit one scene-ready client and synchronize its mode-2 roster.

        Real socket dispatch sets ``require_portal`` so a Plaza C8 is accepted
        only after the same connection's natural 006B -> 006E handshake.
        Direct controller/test calls may omit it to construct an isolated OX
        room without forging a network transition.
        """
        self._ensure_ox_runtime()
        try:
            decode_c2s_ox_enter_00c8(payload)
        except ValueError as exc:
            self._add_event('ox_enter_reject', str(exc), severity='warn')
            return False

        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if source not in self.connections or meta is None:
                return False
            old_kind = meta.get('room_kind')
            if old_kind not in (PLAZA_ROOM_KIND, LOCAL_OX_ROOM_KIND):
                self._add_event(
                    'ox_enter_reject', 'OX enter is allowed only from Plaza',
                    entity_id=meta.get('entity_id'), severity='warn',
                    details={'room_kind': old_kind},
                )
                return False
            if old_kind == LOCAL_OX_ROOM_KIND:
                self._add_event(
                    'ox_enter_duplicate', 'duplicate OX C8 ignored',
                    entity_id=meta.get('entity_id'), severity='info',
                    details={'room_id': meta.get('ox_room_id')},
                )
                return True
            if require_portal:
                requested_at = meta.get('ox_portal_006b_at')
                age = (
                    time.monotonic() - float(requested_at)
                    if requested_at is not None else None
                )
                if age is None or age < 0 or age > OX_PORTAL_C8_TTL_SECONDS:
                    meta['ox_portal_006b_at'] = None
                    self._add_event(
                        'ox_enter_reject',
                        'network OX C8 requires a recent natural 006B portal request',
                        entity_id=meta.get('entity_id'), severity='warn',
                        details={
                            'portal_age_seconds': age,
                            'ttl_seconds': OX_PORTAL_C8_TTL_SECONDS,
                        },
                    )
                    return False
            meta['ox_portal_006b_at'] = None
            existing = self._ox_members(room_id)

        # Remove the actor from every old Plaza recipient before changing its
        # room key; otherwise the verified state-1 roster retains a ghost.
        if old_kind == PLAZA_ROOM_KIND:
            self._notify_room_departure(source, PLAZA_ROOM_KIND)

        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if source not in self.connections or meta is None:
                return False
            meta['room_kind'] = LOCAL_OX_ROOM_KIND
            meta['room_name'] = 'OX Quiz (mode 2)'
            meta['ox_room_id'] = room_id
            meta['ox_round_generation'] = None
            meta['x'] = self.ox_spawn_x
            meta['y'] = self.ox_spawn_y
            admitted_meta = dict(meta)

        entity_id = int(admitted_meta['entity_id'])
        admitted_at = time.monotonic()
        send_ready_to_admitted = False
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            room['participants'].add(entity_id)
            room['last_admitted_at'] = admitted_at
            # An idle admission starts the inferred cohort grace.  A client
            # that arrives while CC is already visible receives its own CC
            # after C8/C9 and joins that ready cohort.  Question/closed/
            # finished arrivals never receive the current CE and therefore
            # remain explicit spectators until a future fresh match.
            if room['phase'] == 'idle':
                room['survivors'].add(entity_id)
                room['spectators'].discard(entity_id)
                room['next_action'] = 'prepare'
                room['next_due_at'] = admitted_at + (
                    int(self.ox_auto_policy['admission_grace_ms']) / 1000.0
                )
            elif room['phase'] == 'ready':
                room['survivors'].add(entity_id)
                room['spectators'].discard(entity_id)
                room['result_keys'][entity_id] = selected_ox_character_key(
                    admitted_meta.get('proto_state')
                )
                send_ready_to_admitted = True
            else:
                room['spectators'].add(entity_id)

        # Do not bundle C8 with CC/CE.  C8 first creates the mode-2 scene;
        # countdown and question emission require separate explicit controls.
        self._ox_emit(
            source, 0x00C8,
            build_s2c_ox_enter_00c8(
                result=0, level_marker=0, ready_ms=0,
                x=self.ox_spawn_x, y=self.ox_spawn_y,
            ),
            pkt_num=pkt_num,
        )

        for peer, peer_meta in existing:
            if peer is source:
                continue
            # New client receives each existing actor using the server id;
            # each existing client receives the newcomer the same way.
            self._ox_emit(
                source, 0x00C9,
                self._ox_actor_record(admitted_meta, peer_meta),
                pkt_num=pkt_num,
            )
            self._ox_emit(
                peer, 0x00C9,
                self._ox_actor_record(peer_meta, admitted_meta),
                pkt_num=pkt_num,
            )

        if send_ready_to_admitted:
            self._ox_emit(source, 0x00CC, b'', pkt_num=pkt_num)

        self._add_event(
            'ox_enter', f'client #{entity_id} entered OX mode 2',
            entity_id=entity_id, severity='ok',
            details={'room_id': room_id},
        )
        return True

    @ox_serialized
    def _prepare_ox_plaza_return(self, source, pkt_num=0):
        """Close mode-2 membership before natural C2S 0064 changes rooms."""
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta or meta.get('room_kind') != LOCAL_OX_ROOM_KIND:
                return False
        self._ox_remove_participant(source, pkt_num=pkt_num)
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if meta is not None:
                meta['ox_room_id'] = None
                meta['ox_round_generation'] = None
                meta['roster_bootstrapped'] = False
                meta['visible_remote_actor_ids'] = set()
        return True

    @ox_serialized
    def _ox_remove_participant(self, source, pkt_num=0):
        """Broadcast mode-2 CA before a departing socket loses its metadata."""
        self._ensure_ox_runtime()
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta or meta.get('room_kind') != LOCAL_OX_ROOM_KIND:
                return False
            room_id = meta.get('ox_room_id') or DEFAULT_OX_ROOM_ID
            entity_id = int(meta.get('entity_id') or 0)
        peers = self._ox_members(room_id)
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            if (entity_id in room['survivors']
                    and (room['phase'] == 'question'
                         or room['rounds_completed'] > 0)):
                if self._ox_commit_result(
                        room_id, entity_id, 'abandoned',
                        room['rounds_completed']) is None:
                    selected_key = room['result_keys'].get(entity_id)
                    if selected_key and room.get('match_id'):
                        pending = (
                            selected_key, room['match_id'], 'abandoned',
                            room['rounds_completed'],
                        )
                        if pending not in self.ox_pending_results:
                            self.ox_pending_results.append(pending)
            room['participants'].discard(entity_id)
            room['survivors'].discard(entity_id)
            room['spectators'].discard(entity_id)
            room['answers'].pop(entity_id, None)
            room['positions'].pop(entity_id, None)
            if not room['participants']:
                # A room with no sockets must not retain an open deadline.  A
                # later C8 would otherwise join as a spectator and be unable
                # to prepare/open until an operator manually closed the stale
                # generation.
                room['phase'] = 'idle'
                room['generation'] = 0
                room['survivors'] = set()
                room['spectators'] = set()
                room['answers'] = {}
                room['positions'] = {}
                room['question_index'] = None
                room['question'] = None
                room['correct_cells'] = None
                room['opened_at'] = None
                room['deadline_at'] = None
                room['closed_at'] = None
                room['losers'] = []
                room['finish_exit_mode'] = None
                room['last_admitted_at'] = None
                room['ready_at'] = None
                room['finished_at'] = None
                room['rounds_completed'] = 0
                room['next_action'] = None
                room['next_due_at'] = None
                room['auto_stalled_at'] = None
                room['last_auto_error'] = None
            elif (room['phase'] == 'closed'
                    and room.get('next_action') == 'await_c9'
                    and room.get('next_due_at') is None
                    and not room['survivors']):
                # The result-hold step may already have consumed its token
                # while one or more judged losers were waiting for verified
                # C9 teardown.  If the last such loser now leaves and only
                # question-late spectators remain, wake ox_auto_step so it
                # can promote that spectator cohort into a fresh match.
                pending_losers = set(room['participants']).intersection(
                    room['losers']
                )
                waiting_spectators = set(room['participants']).intersection(
                    room['spectators']
                )
                if not pending_losers and waiting_spectators:
                    room['next_due_at'] = time.monotonic()
                    room['auto_stalled_at'] = None
        with self.ctl_lock:
            live = self.client_meta.get(source)
            if live is not None:
                live['ox_round_generation'] = None
        for peer, peer_meta in peers:
            if peer is source:
                continue
            wire_id = self._ox_wire_actor_id(peer_meta, entity_id)
            self._ox_emit(
                peer, 0x00CA, build_s2c_ox_actor_ids(0x00CA, [wire_id]),
                pkt_num=pkt_num,
            )
        return True

    @ox_serialized
    def _ox_record_position(self, source, cell, x, y, movement_opcode,
                            pkt_num=0, received_at=None):
        """Record generic 0066/0067 telemetry without treating it as an answer.

        Document 96 supersedes the old cell-judgement assumption: dedicated
        C2S CA carries the authoritative side.  Generic movement remains
        useful for actor position relay only.
        """
        self._ensure_ox_runtime()
        received_at = time.monotonic() if received_at is None else float(received_at)
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta or meta.get('room_kind') != LOCAL_OX_ROOM_KIND:
                return False
            room_id = meta.get('ox_room_id') or DEFAULT_OX_ROOM_ID
            entity_id = int(meta.get('entity_id') or 0)
            generation = meta.get('ox_round_generation')
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            if (room['phase'] != 'question'
                    or generation != room['generation']
                    or entity_id not in room['survivors']):
                return False
            self.ox_receive_seq += 1
            room['positions'][entity_id] = {
                'generation': generation,
                'cell': int(cell),
                'x': int(x),
                'y': int(y),
                'opcode': int(movement_opcode),
                'received_at': received_at,
                'receive_seq': self.ox_receive_seq,
                'pkt_num': int(pkt_num),
            }
        return True

    @ox_serialized
    def _handle_ox_answer_00ca(self, source, payload, pkt_num=0,
                               received_at=None):
        """Commit the dedicated side answer carried by exact C2S CA/22B."""
        self._ensure_ox_runtime()
        try:
            answer = decode_c2s_ox_answer_00ca(payload)
        except ValueError as exc:
            self._add_event('ox_answer_reject', str(exc), severity='warn')
            return False
        received_at = time.monotonic() if received_at is None else float(received_at)
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta or meta.get('room_kind') != LOCAL_OX_ROOM_KIND:
                self._add_event(
                    'ox_answer_reject', 'OX CA outside active mode-2 room',
                    severity='warn',
                )
                return False
            room_id = meta.get('ox_room_id') or DEFAULT_OX_ROOM_ID
            entity_id = int(meta.get('entity_id') or 0)
            generation = meta.get('ox_round_generation')
            meta['x'] = answer['current_x']
            meta['y'] = answer['current_y']
            meta['movement_destination_x'] = answer['destination_x']
            meta['movement_destination_y'] = answer['destination_y']
            meta['ox_last_answer_side'] = answer['side']
            meta['ox_last_answer_timeout'] = answer['timeout']
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            if (room['phase'] != 'question'
                    or generation != room['generation']
                    or entity_id not in room['survivors']
                    or received_at >= room['deadline_at']):
                self._add_event(
                    'ox_answer_reject', 'OX CA is late or from another generation',
                    entity_id=entity_id, severity='warn',
                    details={
                        'generation': generation,
                        'room_generation': room['generation'],
                        'received_at': received_at,
                        'deadline_at': room['deadline_at'],
                    },
                )
                return False
            self.ox_receive_seq += 1
            room['answers'][entity_id] = {
                **answer,
                'generation': generation,
                'received_at': received_at,
                'receive_seq': self.ox_receive_seq,
                'pkt_num': int(pkt_num),
            }
        self._ox_relay_position(
            source, answer['current_x'], answer['current_y'], pkt_num=pkt_num
        )
        self._add_event(
            'ox_answer',
            f'client #{entity_id} submitted OX side {answer["side"]}',
            entity_id=entity_id, severity='ok',
            details={
                'generation': generation,
                'side': answer['side'],
                'timeout': answer['timeout'],
                'timing': answer['timing'],
            },
        )
        return True

    @ox_serialized
    def _handle_ox_leave_00c9(self, source, payload, pkt_num=0):
        """Complete OX exit and start the verified Plaza calibration boundary.

        CB loser and CD final-result timers, plus standalone D2/D4 aborts, all
        converge on the client teardown routine that sends C9 before switching
        to mode 0 and requesting kind-01 calibration.  C9 is therefore the
        server boundary for immediate membership removal plus S2C 000D[00].
        """
        self._ensure_ox_runtime()
        try:
            level_marker = decode_c2s_ox_leave_00c9(payload)
        except ValueError as exc:
            self._add_event('ox_leave_reject', str(exc), severity='warn')
            return False
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta:
                return False
            entity_id = int(meta.get('entity_id') or 0)
            in_ox = meta.get('room_kind') == LOCAL_OX_ROOM_KIND
        if not in_ox:
            # The client's teardown can race another verified departure path.
            # Treat an exact duplicate as an idempotent notification.
            return True
        self._ox_remove_participant(source, pkt_num=pkt_num)
        with self.ctl_lock:
            live = self.client_meta.get(source)
            if live is None:
                return False
            target_state = live.get('proto_state')
            if not isinstance(target_state, dict):
                target_state = {}
                live['proto_state'] = target_state
            live['room_kind'] = None
            live['room_name'] = 'Plaza transition pending'
            live['ox_room_id'] = None
            live['ox_round_generation'] = None
            live['roster_bootstrapped'] = False
            live['visible_remote_actor_ids'] = set()
        with self.proto_lock:
            target_state['hansol_calibration_active'] = True
            target_state['hansol_calibration_samples_sent'] = 0
            target_state['calib_0004_count'] = 0
            target_state['client_0064_seen'] = False
            target_state['client_0064_count'] = 0
        # Direct runtime evidence: C9 is followed about 112 ms later by the
        # client's C2S 0016[01].  The exact 000D[00] prelude arms the existing
        # request-driven 0004[01]x5 -> 0064 Plaza bootstrap flow.
        self._emit(
            source, self._make_packet(0x000D, b'\x00'),
            origin='auto', pkt_num=pkt_num,
        )
        self._add_event(
            'ox_leave', f'client #{entity_id} left OX mode 2',
            entity_id=entity_id, severity='info',
            details={
                'level_marker': level_marker,
                's2c': '0x000D[00]',
                'hansol_calibration': 'armed',
            },
        )
        return True

    def _ox_relay_position(self, source, x, y, pkt_num=0):
        """Translate OX movement to mode-2 D0, never state-1 0068."""
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta or meta.get('room_kind') != LOCAL_OX_ROOM_KIND:
                return 0
            room_id = meta.get('ox_room_id') or DEFAULT_OX_ROOM_ID
            entity_id = int(meta.get('entity_id') or 0)
        delivered = 0
        for peer, peer_meta in self._ox_members(room_id):
            if peer is source:
                continue
            wire_id = self._ox_wire_actor_id(peer_meta, entity_id)
            payload = self._build_state_0068_actor_position_record(
                wire_id, x=int(x), y=int(y),
            )
            if self._ox_emit(peer, 0x00D0, payload, pkt_num=pkt_num):
                delivered += 1
        return delivered

    @ox_serialized
    def ox_prepare(self, room_id=DEFAULT_OX_ROOM_ID, now=None):
        """Explicitly begin the ready UI without opening a question."""
        self._ensure_ox_runtime()
        self._ox_retry_pending_results()
        now = time.monotonic() if now is None else float(now)
        all_members = self._ox_members(room_id)
        if not all_members:
            return False, 'no OX participants'
        selected_keys = {
            int(meta.get('entity_id') or 0): selected_ox_character_key(
                meta.get('proto_state')
            )
            for _conn, meta in all_members
        }
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            if room['phase'] not in ('idle', 'closed', 'finished'):
                return False, f"cannot prepare from phase {room['phase']}"
            if room['phase'] in ('idle', 'finished'):
                # A fresh match re-admits every connected participant.  Keep
                # history as an audit trail, but do not leak answers, losers,
                # or round generations across matches.
                room['match_generation'] += 1
                room['match_id'] = uuid.uuid4().hex
                room['result_keys'] = dict(selected_keys)
                room['generation'] = 0
                room['survivors'] = set(room['participants'])
                room['spectators'] = set()
                room['answers'] = {}
                room['positions'] = {}
                room['losers'] = []
                room['question_index'] = None
                room['question'] = None
                room['correct_cells'] = None
                room['opened_at'] = None
                room['deadline_at'] = None
                room['closed_at'] = None
                room['finish_exit_mode'] = None
                room['rounds_completed'] = 0
                room['finished_at'] = None
                room['auto_stalled_at'] = None
                room['last_auto_error'] = None
            room['phase'] = 'ready'
            room['ready_at'] = now
            room['next_action'] = 'open_question'
            room['next_due_at'] = now + (
                int(self.ox_auto_policy['ready_delay_ms']) / 1000.0
            )
            ready_ids = set(room['survivors'])
        # Spectators admitted during an earlier open/closed generation wait
        # for the next match instead of receiving a countdown without CE.
        members = self._ox_members(room_id, ready_ids)
        for conn, _meta in members:
            self._ox_emit(conn, 0x00CC, b'')
        return True, 'OX ready countdown sent'

    @ox_serialized
    def ox_open_question(self, room_id=DEFAULT_OX_ROOM_ID, question_index=None,
                         duration_ms=16000, now=None):
        """Open one generation and broadcast CE in a separate control step."""
        self._ensure_ox_runtime()
        try:
            duration_ms = int(duration_ms)
        except (TypeError, ValueError):
            return False, 'duration_ms must be an integer'
        if duration_ms <= 0 or duration_ms > 300000:
            return False, 'duration_ms must be 1..300000'
        now = time.monotonic() if now is None else float(now)
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            if room['phase'] not in ('ready', 'closed'):
                return False, f"cannot open question from phase {room['phase']}"
            if not room['survivors']:
                return False, 'no OX survivors'
            if question_index is None:
                question_index = room['generation'] % len(self.ox_questions)
            try:
                question_index = int(question_index)
                if not 0 <= question_index < len(self.ox_questions):
                    raise IndexError('question_index is out of range')
                question = dict(self.ox_questions[question_index])
                payload = build_s2c_ox_question_00ce(
                    question['text'], question['type'],
                    question['correct_side'], question['stars'],
                )
            except (IndexError, KeyError, TypeError, ValueError, UnicodeError) as exc:
                return False, f'invalid OX question: {exc}'
            room['generation'] += 1
            generation = room['generation']
            room['phase'] = 'question'
            room['question_index'] = question_index
            room['question'] = question
            room['correct_cells'] = sorted(
                self.ox_side_cells[int(question['correct_side'])]
            )
            room['opened_at'] = now
            room['deadline_at'] = now + duration_ms / 1000.0
            room['closed_at'] = None
            room['answers'] = {}
            room['positions'] = {}
            room['losers'] = []
            room['next_action'] = 'close_question'
            room['next_due_at'] = room['deadline_at']
            survivors = set(room['survivors'])

        members = self._ox_members(room_id, survivors)
        with self.ctl_lock:
            for conn, _meta in members:
                live = self.client_meta.get(conn)
                if live is not None:
                    live['ox_round_generation'] = generation
        for conn, _meta in members:
            self._ox_emit(conn, 0x00CE, payload)
        return True, f'OX question generation {generation} opened'

    @ox_serialized
    def ox_tick(self, room_id=DEFAULT_OX_ROOM_ID, now=None):
        """Close a due round, judge fail-closed, and broadcast recipient CBs."""
        self._ensure_ox_runtime()
        now = time.monotonic() if now is None else float(now)
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            if room['phase'] != 'question':
                return False, f"cannot close from phase {room['phase']}"
            if now < room['deadline_at']:
                return False, 'OX deadline has not elapsed'
            correct_side = int(room['question']['correct_side'])
            eligible = set(room['survivors'])
            answers = dict(room['answers'])
            losers = sorted(
                entity_id for entity_id in eligible
                if answers.get(entity_id, {}).get('generation') != room['generation']
                or answers.get(entity_id, {}).get('side') != correct_side
            )
            for entity_id in losers:
                if self._ox_commit_result(
                        room_id, entity_id, 'eliminated',
                        room['rounds_completed']) is None:
                    return False, 'OX result persistence failed'
            room['phase'] = 'closed'
            room['closed_at'] = now
            room['losers'] = losers
            room['survivors'] = eligible.difference(losers)
            room['rounds_completed'] += 1
            max_rounds = int(self.ox_auto_policy.get('max_rounds') or 0)
            if max_rounds <= 0:
                max_rounds = max(1, len(self.ox_questions))
            room['next_due_at'] = now + (
                int(self.ox_auto_policy['result_hold_ms']) / 1000.0
            )
            if not room['survivors']:
                room['next_action'] = 'await_c9'
            elif (len(room['survivors']) <= 1
                    or room['rounds_completed'] >= max_rounds):
                room['next_action'] = 'finish_cd'
            else:
                room['next_action'] = 'prepare_next'
            room['history'].append({
                'generation': room['generation'],
                'question_index': room['question_index'],
                'correct_side': correct_side,
                'judgement': 'C2S 0x00CA side equality',
                'losers': list(losers),
                'survivors': sorted(room['survivors']),
                'closed_at': now,
            })

        for recipient, recipient_meta in self._ox_members(room_id):
            wire_losers = [
                self._ox_wire_actor_id(recipient_meta, entity_id)
                for entity_id in losers
            ]
            self._ox_emit(
                recipient, 0x00CB,
                build_s2c_ox_actor_ids(0x00CB, wire_losers),
            )
        return True, f'OX generation closed; losers={losers}'

    @ox_serialized
    def ox_finish(self, room_id=DEFAULT_OX_ROOM_ID, exit_mode='cd', now=None):
        """Send one mutually exclusive OX finish cause: CD, D2, or D4."""
        self._ensure_ox_runtime()
        now = time.monotonic() if now is None else float(now)
        exit_mode = str(exit_mode).lower()
        if exit_mode not in ('cd', 'd2', 'd4'):
            return False, 'exit_mode must be cd, d2, or d4'
        with self.ox_lock:
            room = self._ox_room_locked(room_id)
            if room['phase'] not in ('closed', 'ready'):
                return False, f"cannot finish from phase {room['phase']}"
            survivors = sorted(room['survivors'])
            rounds_survived = room['rounds_completed']
            if rounds_survived:
                for entity_id in survivors:
                    if self._ox_commit_result(
                            room_id, entity_id,
                            'won' if exit_mode == 'cd' else 'aborted',
                            rounds_survived) is None:
                        return False, 'OX result persistence failed'
            room['phase'] = 'finished'
            room['answers'] = {}
            room['correct_cells'] = None
            room['deadline_at'] = None
            room['finish_exit_mode'] = exit_mode
            room['finished_at'] = now
            room['next_action'] = 'await_c9'
            room['next_due_at'] = now + (
                int(self.ox_auto_policy['exit_stall_ms']) / 1000.0
            )
        members = self._ox_members(room_id)
        with self.ctl_lock:
            for conn, _meta in members:
                live = self.client_meta.get(conn)
                if live is not None:
                    live['ox_round_generation'] = None
        for recipient, recipient_meta in members:
            if exit_mode == 'cd':
                wire_survivors = [
                    self._ox_wire_actor_id(recipient_meta, entity_id)
                    for entity_id in survivors
                ]
                self._ox_emit(
                    recipient, 0x00CD,
                    build_s2c_ox_actor_ids(0x00CD, wire_survivors),
                )
            else:
                self._ox_emit(
                    recipient, 0x00D2 if exit_mode == 'd2' else 0x00D4, b''
                )
        return True, f'OX finish cause {exit_mode.upper()} sent'

    @ox_serialized
    def ox_counter(self, first, second, room_id=DEFAULT_OX_ROOM_ID):
        """Broadcast the exact D3 pair for control-driven UI updates."""
        try:
            first, second = int(first), int(second)
        except (TypeError, ValueError):
            return False, 'counter values must be integers'
        if not 0 <= first <= 0xFFFF or not 0 <= second <= 0xFFFF:
            return False, 'counter values must fit u16'
        members = self._ox_members(room_id)
        if not members:
            return False, 'no OX participants'
        payload = struct.pack('<HH', first, second)
        for conn, _meta in members:
            self._ox_emit(conn, 0x00D3, payload)
        return True, 'OX counter sent'

    @ox_serialized
    def ox_auto_step(self, now=None):
        """Advance due OX rooms by one deterministic transition each.

        This method never admits Plaza clients and never emits S2C 0x006E.
        Its only starting point is a room created by an already validated
        natural C2S C8.  Tests call it with an explicit monotonic timestamp;
        production's small scheduler thread calls it with the real clock.
        """
        self._ensure_ox_runtime()
        self._ox_retry_pending_results()
        if not self.ox_auto_policy.get('enabled'):
            return []
        now = time.monotonic() if now is None else float(now)
        with self.ox_lock:
            room_ids = sorted(self.ox_rooms)
        transitions = []
        for room_id in room_ids:
            with self.ox_lock:
                room = self._ox_room_locked(room_id)
                action = room.get('next_action')
                due_at = room.get('next_due_at')
                phase = room.get('phase')
                if action is None or due_at is None or now < float(due_at):
                    continue

            ok = False
            message = ''
            if action == 'prepare' and phase == 'idle':
                ok, message = self.ox_prepare(room_id=room_id, now=now)
            elif action == 'open_question' and phase == 'ready':
                ok, message = self.ox_open_question(
                    room_id=room_id,
                    duration_ms=self.ox_auto_policy['question_duration_ms'],
                    now=now,
                )
            elif action == 'close_question' and phase == 'question':
                ok, message = self.ox_tick(room_id=room_id, now=now)
            elif action == 'prepare_next' and phase == 'closed':
                ok, message = self.ox_prepare(room_id=room_id, now=now)
            elif action == 'finish_cd' and phase == 'closed':
                ok, message = self.ox_finish(
                    room_id=room_id, exit_mode='cd', now=now
                )
            elif action == 'await_c9' and phase == 'closed':
                # CB losers own the verified 6.5-second teardown.  Never
                # replace that path with an inferred automatic D2/D4.  If
                # every judged loser has left but mid-round spectators remain,
                # promote only those spectators into a fresh match.
                with self.ox_lock:
                    room = self._ox_room_locked(room_id)
                    participants = set(room['participants'])
                    pending_losers = participants.intersection(room['losers'])
                    spectators = participants.intersection(room['spectators'])
                    if not pending_losers and spectators:
                        room['phase'] = 'finished'
                        room['survivors'] = set(spectators)
                        room['next_action'] = None
                        room['next_due_at'] = None
                        promote = True
                    else:
                        promote = False
                        if pending_losers and room['auto_stalled_at'] is None:
                            room['auto_stalled_at'] = now
                            room['next_due_at'] = None
                if promote:
                    ok, message = self.ox_prepare(room_id=room_id, now=now)
                else:
                    ok = True
                    message = 'awaiting verified loser C9 teardown'
                    if pending_losers:
                        self._add_event(
                            'ox_exit_stalled',
                            'OX loser C9 teardown is delayed; no forced exit sent',
                            severity='warn',
                            details={
                                'room_id': room_id,
                                'entity_ids': sorted(pending_losers),
                            },
                        )
            elif action == 'await_c9' and phase == 'finished':
                with self.ox_lock:
                    room = self._ox_room_locked(room_id)
                    if room['participants'] and room['auto_stalled_at'] is None:
                        room['auto_stalled_at'] = now
                        room['next_due_at'] = None
                        stalled = sorted(room['participants'])
                    else:
                        stalled = []
                ok = True
                message = 'awaiting verified final C9 teardown'
                if stalled:
                    self._add_event(
                        'ox_exit_stalled',
                        'OX final C9 teardown is delayed; no forced exit sent',
                        severity='warn',
                        details={'room_id': room_id, 'entity_ids': stalled},
                    )
            else:
                # A manual transition or socket lifecycle won the race.  Do
                # not replay a stale automatic token into the new phase.
                with self.ox_lock:
                    room = self._ox_room_locked(room_id)
                    if (room.get('next_action') == action
                            and room.get('next_due_at') == due_at):
                        room['next_action'] = None
                        room['next_due_at'] = None
                message = f'stale automatic action {action} ignored'

            transitions.append({
                'room_id': room_id,
                'action': action,
                'ok': bool(ok),
                'message': message,
            })
            if not ok:
                with self.ox_lock:
                    room = self._ox_room_locked(room_id)
                    room['last_auto_error'] = message
                    room['next_action'] = None
                    room['next_due_at'] = None
        return transitions

    @ox_serialized
    def ox_configure_automation(self, **updates):
        """Configure inferred timing policy without changing wire contracts."""
        allowed = {
            'admission_grace_ms': (0, 30000),
            'ready_delay_ms': (0, 30000),
            'question_duration_ms': (1000, 300000),
            'result_hold_ms': (0, 30000),
            'exit_stall_ms': (1000, 120000),
            'scheduler_poll_ms': (10, 1000),
            'max_rounds': (0, 1000),
        }
        parsed = {}
        for key, value in updates.items():
            if key == 'enabled':
                if not isinstance(value, bool):
                    return False, 'enabled must be boolean'
                parsed[key] = value
                continue
            if key not in allowed:
                return False, f'unknown OX automation setting {key}'
            try:
                value = int(value)
            except (TypeError, ValueError):
                return False, f'{key} must be an integer'
            minimum, maximum = allowed[key]
            if not minimum <= value <= maximum:
                return False, f'{key} must be {minimum}..{maximum}'
            parsed[key] = value
        if not parsed:
            return False, 'no OX automation setting supplied'
        self.ox_auto_policy.update(parsed)
        # A server started with AZROK_OX_AUTO=0 has no scheduler thread.
        # Enabling through the control API must make the new policy effective
        # immediately.  Disabling is handled by ox_auto_step() fail-closed;
        # the small daemon may remain idle until normal server shutdown.
        if (parsed.get('enabled') is True
                and getattr(self, 'running', False)):
            self._start_ox_scheduler()
        return True, 'OX automatic-after-C8 policy updated'

    @ox_serialized
    def ox_configure(self, side0_cells=None, side1_cells=None, questions=None):
        """Replace inferred side cells and/or the preservation-safe bank."""
        self._ensure_ox_runtime()
        updates = {0: side0_cells, 1: side1_cells}
        parsed = {}
        for side, cells in updates.items():
            if cells is None:
                continue
            if isinstance(cells, (str, bytes, dict)):
                return False, f'side{side}_cells must be an integer list'
            try:
                values = frozenset(int(cell) for cell in cells)
            except (TypeError, ValueError):
                return False, f'side{side}_cells must be an integer list'
            if not values or any(cell < 0 or cell >= 36 for cell in values):
                return False, f'side{side}_cells must contain grid cells 0..35'
            parsed[side] = values
        parsed_questions = None
        if questions is not None:
            if not isinstance(questions, list) or not questions:
                return False, 'questions must be a non-empty JSON list'
            parsed_questions = []
            for index, question in enumerate(questions):
                if not isinstance(question, dict):
                    return False, f'question {index} must be an object'
                try:
                    if not isinstance(question.get('text'), str):
                        raise TypeError('text must be a string')
                    normalized = {
                        'text': question['text'],
                        'type': int(question.get('type', 0)),
                        'correct_side': int(question['correct_side']),
                        'stars': int(question.get('stars', 1)),
                    }
                    build_s2c_ox_question_00ce(
                        normalized['text'], normalized['type'],
                        normalized['correct_side'], normalized['stars'],
                    )
                except (KeyError, TypeError, ValueError, UnicodeError) as exc:
                    return False, f'invalid question {index}: {exc}'
                parsed_questions.append(normalized)
        if not parsed and parsed_questions is None:
            return False, 'no OX configuration supplied'
        with self.ox_lock:
            prospective = dict(self.ox_side_cells)
            prospective.update(parsed)
            if prospective[0].intersection(prospective[1]):
                return False, 'side0_cells and side1_cells must not overlap'
            self.ox_side_cells.update(parsed)
            if parsed_questions is not None:
                self.ox_questions = tuple(parsed_questions)
        return True, 'OX configuration updated'

    def ox_snapshot(self):
        """Return JSON-safe deterministic room/controller state."""
        self._ensure_ox_runtime()
        with self.ox_lock:
            rooms = {}
            for room_id, room in self.ox_rooms.items():
                rooms[room_id] = {
                    **{
                        key: value for key, value in room.items()
                        if key not in (
                            'participants', 'survivors', 'spectators', 'answers',
                            'result_keys',
                        )
                    },
                    'participants': sorted(room['participants']),
                    'survivors': sorted(room['survivors']),
                    'spectators': sorted(room['spectators']),
                    'answers': {
                        str(entity_id): dict(answer)
                        for entity_id, answer in room['answers'].items()
                    },
                }
            return {
                'timer_mode': (
                    'automatic-after-client-c8'
                    if self.ox_auto_policy.get('enabled')
                    else 'deterministic-control'
                ),
                'admission_mode': 'client_c8_only',
                'unsolicited_006e': False,
                'inferred_timing_policy': dict(self.ox_auto_policy),
                'side_cells': {
                    str(side): sorted(cells)
                    for side, cells in self.ox_side_cells.items()
                },
                'question_count': len(self.ox_questions),
                'rooms': rooms,
            }

    def _relay_to_room_peers(self, source, opcode, payload, pkt_num):
        """Relay safe, client-originated actor updates to other clients.

        The original client uses different meanings for C->S and S->C
        opcodes.  We therefore translate movement reports into the already
        verified S->C 0x0068 record instead of echoing the original opcode.
        Single-client sessions are untouched because there are no peers.
        """
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if not meta:
                return
            old_kind = meta.get('room_kind')
            meta['last_opcode'] = f'0x{opcode:04X}'
            meta['last_seen'] = time.time()

        entity_id = meta['entity_id']
        if opcode == 0x0065 and len(payload) >= 10:
            kind, _direction, x, y = decode_c2s_0065(payload)
            if old_kind != kind:
                if old_kind == LOCAL_OX_ROOM_KIND:
                    self._ox_remove_participant(source, pkt_num=pkt_num)
                self._notify_room_departure(source, old_kind)
            with self.ctl_lock:
                meta['room_kind'] = kind
                meta['room_name'] = self._room_name_from_kind(kind)
                meta['x'], meta['y'] = x, y
                if old_kind != kind:
                    meta.pop('plaza_chair_request', None)
                    meta.pop('plaza_chair_seat', None)
                if old_kind == LOCAL_OX_ROOM_KIND:
                    meta['ox_room_id'] = None
                    meta['ox_round_generation'] = None
                    meta['roster_bootstrapped'] = False
                    meta['visible_remote_actor_ids'] = set()
                entity_id = meta.get('entity_id')
            # This method runs inside the socket's protocol context.  Retain
            # the direction-verified room kind where the heartbeat response
            # builder can distinguish a facility exit from an unrelated
            # kind-01 calibration request.
            self.proto_state['current_room_kind'] = kind
            self.proto_state['facility_plaza_return_sent'] = False
            self._add_event(
                'room', f'클라이언트 #{entity_id} 방 변경: {self._room_name_from_kind(kind)}',
                entity_id=entity_id, severity='ok',
                details={
                    'from_kind': old_kind, 'to_kind': kind,
                    'direction': _direction, 'x': x, 'y': y,
                },
            )
            # Rebuild the source's new room and every affected peer.  The
            # previous implementation sent a flush to each peer, which could
            # erase their other occupants; rebuilding each recipient's own
            # room roster avoids that multi-client corruption.
            targets = {source}
            for room_kind in (old_kind, kind):
                if room_kind is None:
                    continue
                targets.update(conn for conn, _other in self._room_snapshot(room_kind))
            for recipient in targets:
                with self.ctl_lock:
                    recipient_meta = self.client_meta.get(recipient)
                    recipient_kind = recipient_meta.get('room_kind') if recipient_meta else None
                if recipient_kind is not None:
                    self._send_room_roster(recipient, recipient_kind)
            return

        if opcode == 0x0066 and len(payload) == 22:
            # The leading byte is the cell of the *current* coordinate pair,
            # not the clicked destination.  This is wire-proven across 114
            # live movement records (doc 88).  Keep the destination separate:
            # treating it as the submitted OX answer before arrival accepts a
            # cell the actor has not reached yet.
            cell, from_x, from_y, x, y, duration_ms, path_flag = decode_c2s_0066(payload)
            current_cell = world_grid_cell(from_x, from_y)
            destination_cell = world_grid_cell(x, y)
            if cell != current_cell or not 0 <= current_cell < 36:
                self._add_event(
                    'movement_reject',
                    f'C2S 0x0066 cell {cell} != current cell {current_cell}',
                    entity_id=entity_id, severity='warn',
                    details={
                        'current_x': from_x, 'current_y': from_y,
                        'destination_x': x, 'destination_y': y,
                        'claimed_cell': cell,
                    },
                )
                return
            with self.ctl_lock:
                meta['x'], meta['y'] = from_x, from_y
                meta['movement_current_cell'] = current_cell
                meta['movement_current_at'] = time.time()
                meta['movement_destination_x'] = x
                meta['movement_destination_y'] = y
                meta['movement_destination_cell'] = destination_cell
                meta['movement_destination_at'] = time.time()
                # Sixth dword is a relative duration in ms - measured 217 and
                # 795 on two live click-to-move steps.  The S2C walking record
                # needs an absolute deadline instead; the relay converts.  Doc 538.
                meta['movement_duration_c2s'] = duration_ms
                meta['movement_path_flag'] = path_flag
                meta['movement_generation'] = int(
                    meta.get('movement_generation', 0)
                ) + 1
                movement_generation = meta['movement_generation']
        elif opcode == 0x0067 and len(payload) == 15:
            cell, x, y, action, angle = decode_c2s_0067(payload)
            computed_cell = world_grid_cell(x, y)
            if cell != computed_cell or not 0 <= computed_cell < 36:
                self._add_event(
                    'movement_reject',
                    f'C2S 0x0067 cell {cell} != arrival cell {computed_cell}',
                    entity_id=entity_id, severity='warn',
                    details={'x': x, 'y': y, 'claimed_cell': cell},
                )
                return
            with self.ctl_lock:
                meta['x'], meta['y'] = x, y
                meta['heading'] = angle
                meta['movement_action'] = action
                meta['movement_arrival_cell'] = cell
                meta['movement_arrival_at'] = time.time()
                # Arrival commits supersede any in-flight 0x0066 worker.
                meta['movement_generation'] = int(
                    meta.get('movement_generation', 0)
                ) + 1
                movement_generation = meta['movement_generation']

        # Mode-2 OX reuses the client movement reports but has a different
        # S2C dispatcher.  Commit only the verified current/arrival position,
        # relay it as D0, and return before the Plaza 0068 path.
        if old_kind == LOCAL_OX_ROOM_KIND:
            if opcode == 0x0066 and len(payload) == 22:
                self._ox_record_position(
                    source, current_cell, from_x, from_y, opcode,
                    pkt_num=pkt_num,
                )
                self._ox_relay_position(source, from_x, from_y, pkt_num=pkt_num)
            elif opcode == 0x0067 and len(payload) == 15:
                self._ox_record_position(
                    source, computed_cell, x, y, opcode,
                    pkt_num=pkt_num,
                )
                self._ox_relay_position(source, x, y, pkt_num=pkt_num)
            return

        # Local telemetry must update even in a single-client room. Only the
        # relay itself depends on the presence of a peer.
        with self.ctl_lock:
            peers = [
                (conn, other) for conn, other in self.client_meta.items()
                if conn is not source
                and conn in self.connections
                and old_kind is not None
                and other.get('room_kind') == old_kind
            ]
        if not peers:
            return

        if opcode == 0x0066 and len(payload) == 22:
            self._start_plaza_movement_relay(
                source, entity_id,
                from_x, from_y, x, y, duration_ms,
                movement_generation, pkt_num,
            )
            return

        if opcode == 0x0067 and len(payload) == 15:
            # The original S2C 0x0068 handler has no verified S2C 0x0067
            # arrival mapping.  Relay the committed position through the
            # already verified six-dword position record, carrying the
            # angle just stored above in its existing heading slot.
            self._plaza_relay_position_frame(
                source, entity_id, x, y,
                pkt_num=pkt_num, generation=movement_generation,
            )
            return

        # C2S 0x006C is handled separately because its opposite direction has
        # a verified, deliberately different six-byte layout.

    # Movement and heartbeat dominate the wire and are already decoded; every
    # other C2S opcode is rare enough to keep verbatim so a UI action can be
    # matched to the exact bytes it produced.
    C2S_RAW_CAPTURE_SKIP = frozenset((0x0016, 0x0066, 0x0067))

    def _capture_c2s_raw(self, source, opcode, payload):
        """Record one raw C2S packet so a click can be tied to its bytes."""
        if opcode in self.C2S_RAW_CAPTURE_SKIP:
            return
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            entity_id = int(meta.get('entity_id') or 0) if meta else 0
        self._add_event(
            'c2s_raw', f'C2S 0x{opcode:04X} ({len(payload)}B)',
            entity_id=entity_id, severity='info',
            details={
                'opcode': f'0x{opcode:04X}',
                'length': len(payload),
                'hex': payload.hex(),
            },
        )

    def _plaza_chair_recipients(self, source, entity_id):
        """Only peers with this actor in their state-1 remote list may receive 006C."""
        return [
            conn for conn, meta in self.client_meta.items()
            if conn is not source and conn in self.connections
            and meta.get('room_kind') == PLAZA_ROOM_KIND
            and entity_id in set(meta.get('visible_remote_actor_ids') or ())
        ]

    def _release_plaza_chair(self, source, pkt_num, *, notify_self=True):
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if meta is None:
                return False
            seat = meta.pop('plaza_chair_seat', None)
            meta.pop('plaza_chair_request', None)
            if seat is None:
                return False
            entity_id = int(meta.get('entity_id') or 0)
            peers = self._plaza_chair_recipients(source, entity_id)
            active = source in self.connections and meta.get('room_kind') == PLAZA_ROOM_KIND
            seat_x, seat_y, seat_heading = PLAZA_CHAIR_SEAT_TRANSFORMS[seat[0]][seat[1]]
            meta['x'], meta['y'], meta['heading'] = seat_x, seat_y, seat_heading
        if notify_self and active:
            # FUN_00615340's >=2 branch resets +0x32E/+0x332 and chair
            # fields, but leaves +0x107 at 0x30.  FUN_00613470 rejects
            # further clicks while that state is 0x30/0x31.  The verified
            # S2C 0069 self branch with mode 0 passes through 005250C0 and
            # changes +0x107 to 1, restoring ordinary movement eligibility.
            self._emit(source, self._make_packet(0x006B, b'\x02'), origin='relay', pkt_num=pkt_num)
            self._emit(source, self._make_packet(0x0069,
                self._build_state_0069_actor_position(
                    entity_id=DEFAULT_ACTOR_ID,
                    x=seat_x,
                    y=seat_y,
                    mode=0,
                )), origin='relay', pkt_num=pkt_num)
        for peer in peers:
            self._emit(peer, self._make_packet(0x006C, struct.pack('<BBI', seat[0], 2, entity_id)),
                       origin='relay', pkt_num=pkt_num)
            # FUN_00615410 clear leaves peer +0x107 at 0x30.  The S2C
            # 0069 remote branch for that state sets it to 1, allowing the
            # normal 0068 movement path to update the actor again.
            self._emit(peer, self._make_packet(0x0069,
                self._build_state_0069_actor_position(
                    entity_id=entity_id, x=seat_x, y=seat_y, mode=0,
                )), origin='relay', pkt_num=pkt_num)
        return True

    def _handle_plaza_chair_0069(self, source, payload, pkt_num):
        """Allocate one of the original chair's two physical seat positions.

        The original table at 0x006D9D48 has six chair rows and two distinct
        (x,y,heading) triples in each row.  Slot occupancy is restoration
        policy: the lost server's tie-breaking rule cannot be recovered.
        """
        if len(payload) != 1 or payload[0] > 5:
            self._add_event('chair_reject', '0x0069 requires chair index 0..5', severity='warn')
            return False
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if (meta is None or source not in self.connections
                    or meta.get('room_kind') != PLAZA_ROOM_KIND):
                return False
            entity_id = int(meta.get('entity_id') or 0)
            current_seat = meta.get('plaza_chair_seat')
            occupied = {
                tuple(other['plaza_chair_seat']) for conn, other in self.client_meta.items()
                if conn in self.connections and other.get('room_kind') == PLAZA_ROOM_KIND
                and other.get('plaza_chair_seat') is not None and conn is not source
            }
            seat = next(((payload[0], side) for side in (0, 1)
                         if (payload[0], side) not in occupied), None)
            meta['plaza_chair_request'] = payload[0]
            if seat is not None:
                meta['plaza_chair_seat'] = seat
                meta['x'], meta['y'], meta['heading'] = PLAZA_CHAIR_SEAT_TRANSFORMS[seat[0]][seat[1]]
            peers = self._plaza_chair_recipients(source, entity_id)
        if seat is None:
            if current_seat is not None:
                self._release_plaza_chair(source, pkt_num)
            else:
                # Client optimistically wrote +0x336 on click.  Toggle >=2
                # takes its original reset branch without indexing the table.
                self._emit(source, self._make_packet(0x006B, b'\x02'), origin='relay', pkt_num=pkt_num)
            self._add_event('chair_full', f'Plaza chair {payload[0]} is full',
                            entity_id=entity_id, severity='info')
            return False
        if current_seat is not None and current_seat != seat:
            for peer in peers:
                self._emit(peer, self._make_packet(0x006C,
                    struct.pack('<BBI', current_seat[0], 2, entity_id)),
                    origin='relay', pkt_num=pkt_num)
        self._emit(source, self._make_packet(0x006B, bytes((seat[1],))),
                   origin='relay', pkt_num=pkt_num)
        for peer in peers:
            self._emit(peer, self._make_packet(0x006C,
                struct.pack('<BBI', seat[0], seat[1], entity_id)),
                origin='relay', pkt_num=pkt_num)
        self._add_event(
            'chair_seated', f'Plaza actor {entity_id} assigned chair {seat[0]} side {seat[1]}',
            entity_id=entity_id, severity='info',
            details={'chair_index': seat[0], 'side': seat[1],
                     'policy': 'first_free_original_table_slot'},
        )
        return True

    def _handle_plaza_actor_state_006a(self, source, payload, pkt_num):
        """Clear a server-owned chair on an empty actor-state request."""
        if payload:
            self._add_event('actor_state_reject', '0x006A must be empty', severity='warn')
            return False
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if (meta is None or source not in self.connections
                    or meta.get('room_kind') != PLAZA_ROOM_KIND):
                return False
            entity_id = int(meta.get('entity_id') or 0)
            meta['plaza_actor_state_requests'] = int(meta.get('plaza_actor_state_requests') or 0) + 1
        released = self._release_plaza_chair(source, pkt_num)
        self._add_event(
            'actor_state_request', f'Plaza actor {entity_id} sent 0x006A',
            entity_id=entity_id, severity='info',
            details={'chair_released': released},
        )
        return True

    def _relay_community_006c(self, source, payload, pkt_num):
        """Validate the Plaza information-button target and answer it.

        The single dword is a **target** actor id in the sender's own id
        space, not a claim about who the sender is.  Measured 2026-07-30 on
        two live sessions: clicking your own avatar sends 1 (every client is
        self id 1), clicking the other avatar sends that peer's server entity
        id.  The previous reading treated any non-1 value as impersonation and
        rejected it, so every request aimed at another player was dropped -
        which is why clicking a remote character did nothing.

        Clicking an actor first sets the client's 0x0070 latch to zero and
        sends this dword.  Its short-form handler reads only the first four
        bytes and clears the latch.  BtnInfo (FUN_005FDAB0) sends the same
        dword again; its full-form handler reads all 12 response bytes and
        reaches FUN_005FDF80.  Always send 12 bytes: the packet length is
        consumed by the dispatcher, and guessing the client's latch from
        server-side click history fails on reselecting the same actor.
        Scoreboard fields come from the target's durable OX match records;
        characters without a recorded match begin at zero.
        S2C 0x006C is a separate actor-animation message.
        """
        try:
            target_actor_id = decode_c2s_006c_community(payload)
        except ValueError as exc:
            self._add_event('community_reject', str(exc), severity='warn')
            return False

        with self.ctl_lock:
            source_meta = self.client_meta.get(source)
            if (source_meta is None or source not in self.connections
                    or source_meta.get('room_kind') != PLAZA_ROOM_KIND):
                self._add_event(
                    'community_reject', '0x006C request outside active Plaza',
                    severity='warn',
                )
                return False
            source_entity_id = int(source_meta.get('entity_id') or 0)
            visible = set(source_meta.get('visible_remote_actor_ids') or ())
            if target_actor_id == DEFAULT_ACTOR_ID:
                target_kind = 'self'
            elif target_actor_id in visible:
                target_kind = 'visible_peer'
            else:
                target_kind = 'unknown'
            source_meta['community_target_actor_id'] = target_actor_id
            source_meta['community_target_kind'] = target_kind
            source_meta['community_requests'] = (
                int(source_meta.get('community_requests', 0)) + 1
            )

        if target_kind == 'unknown':
            self._add_event(
                'community_reject',
                f'0x006C targets actor {target_actor_id}, which this client cannot see',
                entity_id=source_entity_id, severity='warn',
                details={'visible': sorted(visible)},
            )
            return False

        if target_kind == 'self':
            target_meta = source_meta
        else:
            with self.ctl_lock:
                target_meta = next(
                    (meta for conn, meta in self.client_meta.items()
                     if conn in self.connections
                     and meta.get('room_kind') == PLAZA_ROOM_KIND
                     and int(meta.get('entity_id') or 0) == target_actor_id),
                    None,
                )
            if target_meta is None:
                return False
        target_state = target_meta.get('proto_state') or {}
        target_key = (
            target_state.get('selected_character_key')
            if target_state.get('client_0005_seen') else None
        )
        canonical = None
        if isinstance(target_key, str) and target_key:
            canonical = (getattr(self, 'saved_server_states', None) or {}).get(target_key)
            if canonical is None and getattr(self, 'state_store_dir', None):
                try:
                    with open(self._canonical_state_path(target_key), 'r', encoding='utf-8') as state_file:
                        canonical = json.load(state_file)
                except (FileNotFoundError, OSError, ValueError, TypeError):
                    pass
        progression = accessory_progression_from_canonical(canonical)
        level = progression['level'] if progression is not None else 1
        level = max(0, min(int(level), 255))
        # FUN_005FDF80 renders byte 0 as the numeric level under the
        # portrait.  Byte 1 chooses the OX tier label/threshold; tier 1
        # is the client's lowest valid tier.  The following u16 and two
        # dwords are OX points and a ratio gauge. The durable OX ledger
        # projects the documented preservation scoring policy independently
        # of pet experience and growth.
        score = {'tier': 1, 'points': 0, 'gauge_denominator': 0, 'gauge_numerator': 0}
        if target_key and getattr(self, 'state_store_dir', None):
            try:
                score = ox_info_projection(self.state_store_dir, target_key)
            except (OSError, ValueError, TypeError):
                self._add_event('ox_result_read_error', 'OX 전적을 읽을 수 없습니다.', severity='warn')
        info = struct.pack('<BBHII', level, score['tier'], score['points'],
                           score['gauge_denominator'], score['gauge_numerator'])
        delivered = self._emit(source, self._make_packet(0x0070, info), origin='relay')

        self._add_event(
            'community', f'클라이언트 #{source_entity_id}의 0x006C 요청 -> 액터 {target_actor_id}',
            entity_id=source_entity_id, severity='warn',
            details={
                'target_actor_id': target_actor_id,
                'target_kind': target_kind,
                'verified_c2s_fields': ['target_actor_id'],
                'reply_opcode': '0x0070' if delivered else None,
                'reply_form': 'latched_12_byte',
                'relay': bool(delivered),
                'score_state': 'unranked',
            },
        )
        return True

    def _process_accessory_0018(self, source, payload, pkt_num=0):
        """Persist one accessory update and emit recipient-local S2C 0x000C.

        A clear request carries the removed value as informational evidence.
        It must equal the current canonical selector so a stale or forged clear
        cannot erase a newer equipped item.
        """
        mutation_base = {
            'kind': 'accessory',
            'request_opcode': '0x0018',
            'packet_seq': int(pkt_num),
            'changed_fields': [],
        }

        def reject_transaction(reason, key=None, **metadata):
            mutation = dict(mutation_base)
            mutation.update(metadata)
            self._record_mutation_transaction(
                mutation, 'rejected', key=key, reason=reason,
            )

        try:
            clear_flag, slot, value = decode_c2s_0018_accessory(payload)
        except ValueError as exc:
            self._add_event('accessory_reject', str(exc), severity='warn')
            reject_transaction(str(exc))
            return False
        with self.ctl_lock:
            meta = self.client_meta.get(source)
            if meta is None or source not in self.connections:
                self._add_event(
                    'accessory_reject', '0x0018 request outside active session',
                    severity='warn',
                )
                reject_transaction('0x0018 request outside active session')
                return False
            entity_id = int(meta.get('entity_id') or 0)
            if entity_id <= 0:
                self._add_event(
                    'accessory_reject', '0x0018 source has no actor identity',
                    severity='warn',
                )
                reject_transaction('0x0018 source has no actor identity')
                return False
            room_kind = meta.get('room_kind')
            peers = [
                (conn, dict(other)) for conn, other in self.client_meta.items()
                if conn is not source
                and conn in self.connections
                and room_kind is not None
                and other.get('room_kind') == room_kind
                and entity_id in set(other.get('visible_remote_actor_ids') or ())
            ]

        selected_key = self._selected_character_state_key()
        if selected_key is None:
            self._add_event(
                'accessory_reject',
                '0x0018 mutation requires selected character identity',
                entity_id=entity_id, severity='warn',
            )
            reject_transaction(
                '0x0018 mutation requires selected character identity',
                slot=slot, value=value, clear_flag=clear_flag,
            )
            return False
        state = self._load_canonical_character_state(key=selected_key)
        current_slots = normalize_accessory_slots(state.get('accessory_slots'))
        if current_slots is None:
            self._add_event(
                'accessory_reject', 'canonical accessory slots are invalid',
                entity_id=entity_id, severity='warn',
            )
            reject_transaction(
                'canonical accessory slots are invalid', key=selected_key,
                slot=slot, value=value, clear_flag=clear_flag,
            )
            return False

        current_value = current_slots[slot]
        if clear_flag:
            if current_value == 0xFF or value != current_value:
                self._add_event(
                    'accessory_reject',
                    'stale accessory clear does not match canonical slot',
                    entity_id=entity_id, severity='warn',
                    details={
                        'slot': slot, 'submitted_value': value,
                        'canonical_value': current_value,
                    },
                )
                reject_transaction(
                    'stale accessory clear does not match canonical slot',
                    key=selected_key, slot=slot, value=value,
                    clear_flag=clear_flag, canonical_value=current_value,
                )
                return False
            committed_value = 0xFF
        else:
            unlock = evaluate_accessory_unlock(state, slot, value)
            if not unlock['allowed']:
                self._add_event(
                    'accessory_reject',
                    'accessory is locked by canonical character progression',
                    entity_id=entity_id, severity='warn',
                    details={
                        'slot': slot,
                        'submitted_value': value,
                        'unlock': unlock,
                    },
                )
                reject_transaction(
                    'accessory is locked by canonical character progression',
                    key=selected_key, slot=slot, value=value,
                    clear_flag=clear_flag, unlock=unlock,
                )
                return False
            committed_value = value

        working = dict(state)
        working['accessory_slots'] = list(current_slots)
        working['accessory_slots'][slot] = committed_value
        if not self._save_canonical_character_state(
                working, key=selected_key,
                mutation={
                    'kind': 'accessory',
                    'request_opcode': '0x0018',
                    'packet_seq': int(pkt_num),
                    'changed_fields': [f'accessory_slots[{slot}]'],
                    'clear_flag': clear_flag,
                    'slot': slot,
                    'value': value,
                }):
            self._add_event(
                'accessory_reject', 'canonical accessory persistence failed',
                entity_id=entity_id, severity='warn',
            )
            return False

        with self.ctl_lock:
            live_meta = self.client_meta.get(source)
            if live_meta is not None:
                live_meta['accessory_slots'] = list(working['accessory_slots'])

        self_payload = build_s2c_accessory_000c(
            DEFAULT_ACTOR_ID, clear_flag, slot, value
        )
        self._emit(
            source, self._make_packet(0x000C, self_payload),
            origin='auto', pkt_num=pkt_num,
        )
        delivered_peers = 0
        peer_payload = build_s2c_accessory_000c(
            entity_id, clear_flag, slot, value
        )
        for peer, _peer_meta in peers:
            if self._emit(
                peer, self._make_packet(0x000C, peer_payload),
                origin='relay', pkt_num=pkt_num,
            ):
                delivered_peers += 1

        self.proto_state['last_accessory_update'] = {
            'status': 'committed',
            'clear_flag': clear_flag,
            'slot': slot,
            'value': value,
            'canonical_value': committed_value,
            'peer_deliveries': delivered_peers,
        }
        self._add_event(
            'accessory',
            f'Accessory slot {slot} {"cleared" if clear_flag else "applied"}.',
            entity_id=entity_id, severity='ok',
            details=dict(self.proto_state['last_accessory_update']),
        )
        return True

    def _relay_chat_0068(self, source, payload, pkt_num):
        """Translate verified C2S 0x0068 chat into recipient S2C 0x006A.

        The two directions deliberately use different opcodes and layouts.
        Only state-1 Plaza clients are eligible recipients; feeding 0x006A to
        a mode-0 local room would hit the wrong client dispatcher.
        """
        try:
            chat = decode_c2s_0068_chat(payload)
        except ValueError as exc:
            self._add_event('chat_reject', str(exc), severity='warn')
            return False
        if chat['type'] not in (0, 1):
            self._add_event(
                'chat_reject', f"unsupported chat type {chat['type']}", severity='warn'
            )
            return False

        with self.ctl_lock:
            source_meta = self.client_meta.get(source)
            if (source_meta is None or source not in self.connections
                    or source_meta.get('room_kind') != PLAZA_ROOM_KIND):
                return False
            sender_id = int(source_meta.get('entity_id') or 0)
            sender_name = str(source_meta.get('name') or 'Player')
            sender_name_raw = sender_name.encode('cp949', errors='ignore')
            active_plaza = [
                (conn, dict(meta)) for conn, meta in self.client_meta.items()
                if conn in self.connections and meta.get('room_kind') == PLAZA_ROOM_KIND
            ]

        if chat['type'] == 0:
            recipients = active_plaza
        else:
            target_name = chat['target_raw'].decode('cp949', errors='ignore').strip().casefold()
            recipients = []
            for conn, meta in active_plaza:
                candidate_names = {
                    str(meta.get('name') or '').strip().casefold(),
                    str(meta.get('account') or '').strip().casefold(),
                }
                if conn is source or target_name in candidate_names:
                    recipients.append((conn, meta))

        delivered = 0
        for recipient, _recipient_meta in recipients:
            # The client's own fixed actor is always id 1.  Every other
            # recipient identifies the sender by the server-assigned remote id.
            wire_actor_id = DEFAULT_ACTOR_ID if recipient is source else sender_id
            text_payload = self._build_state_006A_text_record(
                kind=chat['type'],
                mode=chat['flag'],
                actor_id=wire_actor_id,
                primary_raw=sender_name_raw,
                message_raw=chat['message_raw'],
            )
            if self._emit(
                recipient, self._make_packet(0x006A, text_payload),
                origin='relay', pkt_num=pkt_num,
            ):
                delivered += 1

        self._add_event(
            'chat', f'{sender_name}: {chat["message_raw"].decode("cp949", errors="replace")}',
            entity_id=sender_id, severity='info',
            details={'type': chat['type'], 'delivered': delivered},
        )
        return delivered > 0

    def say_as_player(self, entity_id, message, chat_type=0, flag=0):
        """Speak one line as an existing Plaza actor, bypassing key input.

        The client renders EUC-KR fine - a Korean S2C 0x006A shows correctly in
        both the balloon and the log (measured 2026-07-30).  What it cannot do
        under BoxedWine is *compose* Korean: there is no IME in the emulated
        Windows, so the in-game field only ever receives ASCII.  This lets a
        host-side box that does have an IME put the finished text on the wire
        through exactly the same path a typed message takes.

        Returns ``(ok, message)``.
        """
        if not isinstance(message, str) or not message.strip():
            return False, 'message must be a non-empty string'
        if chat_type not in (0, 1):
            return False, 'chat_type must be 0 (public) or 1 (whisper)'
        try:
            message_raw = message.encode('cp949')
        except UnicodeEncodeError as exc:
            return False, f'message is not representable in EUC-KR: {exc}'
        # The record is NUL-terminated, so an embedded NUL would truncate it.
        message_raw = message_raw.split(b'\x00', 1)[0]
        if not message_raw:
            return False, 'message is empty after EUC-KR encoding'

        with self.ctl_lock:
            source = None
            for conn, meta in self.client_meta.items():
                if (conn in self.connections
                        and int(meta.get('entity_id') or 0) == int(entity_id)):
                    source = conn
                    break
            if source is None:
                return False, f'no connected client with entity_id {entity_id}'
            source_meta = self.client_meta[source]
            if source_meta.get('room_kind') != PLAZA_ROOM_KIND:
                return False, f'entity {entity_id} is not in the Plaza'
            sender_id = int(source_meta.get('entity_id') or 0)
            sender_name = str(source_meta.get('name') or 'Player')
            sender_name_raw = sender_name.encode('cp949', errors='ignore')
            recipients = [
                conn for conn, meta in self.client_meta.items()
                if conn in self.connections
                and meta.get('room_kind') == PLAZA_ROOM_KIND
            ]

        delivered = 0
        for recipient in recipients:
            wire_actor_id = DEFAULT_ACTOR_ID if recipient is source else sender_id
            try:
                text_payload = self._build_state_006A_text_record(
                    kind=chat_type, mode=flag, actor_id=wire_actor_id,
                    primary_raw=sender_name_raw, message_raw=message_raw,
                )
            except ValueError as exc:
                return False, str(exc)
            if self._emit(
                recipient, self._make_packet(0x006A, text_payload),
                origin='relay', pkt_num=0,
            ):
                delivered += 1

        self._add_event(
            'chat', f'{sender_name}: {message}', entity_id=sender_id,
            severity='info',
            details={'type': chat_type, 'delivered': delivered, 'source': 'host_ime'},
        )
        if delivered <= 0:
            return False, 'no Plaza recipient accepted the message'
        return True, f'delivered to {delivered} client(s)'

    def _players_snapshot(self):
        now = time.time()
        with self.ctl_lock:
            active = [
                (conn, meta) for conn, meta in self.client_meta.items()
                if conn in self.connections
            ]
            result = []
            for conn, meta in active:
                proto = meta.get('proto_state') or {}
                save_payload = proto.get('last_content_save_payload')
                if isinstance(save_payload, (bytes, bytearray)) and len(save_payload) > 0x05:
                    natural_evolution = int(save_payload[0x05])
                elif isinstance(save_payload, str) and len(save_payload) >= (0x05 + 1) * 2:
                    try:
                        natural_evolution = int(save_payload[0x05 * 2:0x05 * 2 + 2], 16)
                    except ValueError:
                        natural_evolution = None
                else:
                    natural_evolution = None
                room_kind = meta.get('room_kind')
                peer_count = sum(
                    1 for other_conn, other in active
                    if other_conn is not conn and other.get('room_kind') == room_kind
                ) if room_kind is not None else 0
                visible_remote_actor_count = len(meta.get('visible_remote_actor_ids') or ())
                public = {
                    k: v for k, v in meta.items()
                    if k not in (
                        'last_seen', 'last_tx_at', 'proto_state', 'opcode_counts',
                        'visible_remote_actor_ids',
                    )
                }
                result.append({
                    **public,
                    'connected': True,
                    'connected_s': round(max(0.0, now - meta.get('connected_at', now)), 1),
                    'idle_s': round(max(0.0, now - meta.get('last_seen', now)), 1),
                    'tx_idle_s': (
                        round(max(0.0, now - meta['last_tx_at']), 1)
                        if meta.get('last_tx_at') else None
                    ),
                    'peer_count': peer_count,
                    'visible_remote_actor_count': visible_remote_actor_count,
                    'roster_overflow_count': max(0, peer_count - MAX_REMOTE_ACTORS_PER_CLIENT),
                    'room_dispatch': (
                        'state-1 shared' if room_kind == PLAZA_ROOM_KIND
                        else 'mode-2 OX' if room_kind == LOCAL_OX_ROOM_KIND
                        else 'state-0 local'
                    ),
                    'opcode_counts': dict(meta.get('opcode_counts') or {}),
                    'protocol': {
                        'char_created': bool(proto.get('char_created')),
                        'zone_request_count': int(proto.get('zone_request_count') or 0),
                        'client_0007_count': int(proto.get('client_0007_count') or 0),
                        'content_save_count': int(proto.get('content_save_count') or 0),
                        'saved_state_loaded': bool(proto.get('saved_state_loaded')),
                        'last_content_save_time': proto.get('last_content_save_time'),
                        'last_content_save_sum_matches': proto.get('last_content_save_sum_matches'),
                        'pushup_stat_0x1f': proto.get('last_content_save_stat_0x1F'),
                        'dumbbell_stat_0x20': proto.get('last_content_save_stat_0x20'),
                        'rope_skipping_stat_0x21': proto.get('last_content_save_stat_0x21'),
                        'calibration_samples': int(proto.get('hansol_calibration_samples_sent') or 0),
                        'plaza_reply_mode': proto.get('plaza_reply_mode'),
                        'full_0064_sent': bool(proto.get('full_0064_sent')),
                        'door_0019_seen': bool(proto.get('door_0019_seen')),
                        'natural_evolution': natural_evolution,
                        'persisted_evolution': proto.get('persisted_evolution'),
                    },
                })
            return result

    def inject(self, opcode, payload=b'', origin='manual', entity_id=None):
        """Send an arbitrary S->C packet right now. Returns (ok, message)."""
        conn = self._conn_for_entity(entity_id) if entity_id is not None else self._active_conn()
        if conn is None:
            return False, "target client not connected" if entity_id is not None else "no client connected"
        with self.proto_lock:
            target_state = self._proto_state_for_conn(conn)
            previous = self.proto_state
            self.proto_state = target_state
            try:
                if opcode == 0x000D and payload[:1] == b'\x00':
                    # Hansol/Plaza calibration is request-driven: arm it at
                    # the exact S->C 0x000D boundary, then answer the client's
                    # C->S 0x0016[01] requests with S->C 0x0004[01] samples.
                    self.proto_state['hansol_calibration_active'] = True
                    self.proto_state['hansol_calibration_samples_sent'] = 0
                    self.proto_state['calib_0004_count'] = 0
                    self.proto_state['client_0064_seen'] = False
                    self.proto_state['client_0064_count'] = 0
                    print("  [PROTO] S->C 0x000D armed request-driven kind-01 calibration")
            finally:
                self.proto_state = previous
        try:
            pkt = self._make_packet(opcode, payload)
        except ValueError as exc:
            # Keep malformed/manual oversize traffic out of the client while
            # returning a useful control-panel error instead of an HTTP 500.
            return False, str(exc)
        ok = self._emit(conn, pkt, origin=origin)
        return ok, f"sent 0x{opcode:04X} ({len(payload)}B)" if ok else "send failed"

    def set_paused(self, enabled):
        with self.ctl_lock:
            self.paused = bool(enabled)
            if not self.paused:
                held, self.pending_out = self.pending_out, []
        if not enabled:
            for item in held:          # releasing the gate flushes everything held
                item['action'] = 'step'
                item['ev'].set()
        return self.paused

    def release_one(self, action='step'):
        """Let one held packet through ('step') or discard it ('drop')."""
        with self.ctl_lock:
            if not self.pending_out:
                return False, "nothing pending"
            item = self.pending_out.pop(0)
        item['action'] = action
        item['ev'].set()
        return True, action

    def set_proto_state(self, key, value):
        with self.proto_lock:
            state = self._active_proto_state()
            old = state.get(key)
            state[key] = value
        print(f"  [CTL] proto_state['{key}']: {old!r} -> {value!r}")
        return old

    def snapshot(self):
        """Everything the control panel renders."""
        self._ensure_mutation_runtime()
        with self.ctl_lock:
            packets = list(self.packet_ring)
            pending = [{'origin': i['origin'], 'hex': i['data'].hex()} for i in self.pending_out]
            paused = self.paused
            events = list(self.event_ring)
        with self.mutation_lock:
            transactions = [dict(item) for item in self.mutation_ring]
        safe_state = {}
        for k, v in self._active_proto_state().items():
            safe_state[k] = v.hex() if isinstance(v, (bytes, bytearray)) else v
        saved_payload_hex = safe_state.get('last_content_save_payload') or ''
        try:
            natural_evolution = int(saved_payload_hex[0x05 * 2:0x05 * 2 + 2], 16)
        except (TypeError, ValueError):
            natural_evolution = None
        outside_gate_ready = (
            natural_evolution is not None and natural_evolution >= 1
        ) or bool(safe_state.get('door_0019_seen'))
        players = self._players_snapshot()
        active_conn = self._active_conn()
        with self.ctl_lock:
            active_meta = self.client_meta.get(active_conn, {}) if active_conn is not None else {}
        active_entity_id = active_meta.get('entity_id')
        watches = self.read_watches()

        # A responsive Win32 window is not sufficient proof that Acknex's game
        # loop survived a room transition.  During the 2026-07-17 failure the
        # message pump stayed responsive while heartbeats stopped, dispatch
        # remained in state 0, and self_actor_id was never committed.  Expose a
        # conservative, read-only synthesis of those independent signals so the
        # dashboard can distinguish a healthy Plaza from that frozen loading
        # frame without modifying client memory.
        primary_player = players[0] if players else None
        scene = watches.get('scene_opcode')
        phase = watches.get('phase_31792')
        dispatch_mode = watches.get('dispatch_mode')
        self_actor_id = watches.get('self_actor_id')
        def transition_for_player(player, primary=False):
            proto = player.get('protocol') or {}
            heartbeat_idle_s = float(player.get('idle_s') or 0.0)
            heartbeat_recent = heartbeat_idle_s <= 20.0
            plaza_committed = bool(proto.get('full_0064_sent'))
            door_seen = bool(proto.get('door_0019_seen'))
            player_exit_ready = (
                (proto.get('natural_evolution') is not None and int(proto['natural_evolution']) >= 1)
                or door_seen
            )
            player_scene = scene if primary else None
            player_phase = phase if primary else None
            player_mode = dispatch_mode if primary else None
            player_self = self_actor_id if primary else None
            player_is_plaza = (
                player.get('room_kind') == PLAZA_ROOM_KIND
                or (primary and player_scene == 110 and player_phase == 4)
            )
            player_is_pathouse = (
                player.get('room_kind') in PATHOUSE_ROOM_KINDS
                or (primary and player_scene == 100 and player_phase == 2)
            )
            state1_ready = bool(
                primary
                and player_scene == 110
                and player_phase == 4
                and player_mode == 1
                and isinstance(player_self, int)
                and 0 < player_self < 0x10000
            )

            if primary and watches.get('engine_error_active'):
                code, label, severity = 'engine_error', '엔진 오류 감지', 'error'
            elif plaza_committed and primary and state1_ready and heartbeat_recent:
                code, label, severity = 'plaza_healthy', 'Plaza 정상 · state 1 / heartbeat', 'ok'
            elif plaza_committed and not primary and player_is_plaza and heartbeat_recent:
                code, label, severity = 'plaza_protocol_healthy', 'Plaza · 0x0064 / heartbeat (memory 미관측)', 'ok'
            elif plaza_committed and not heartbeat_recent:
                code, label, severity = 'post_0064_stalled', 'Plaza 로딩 정지 의심 · heartbeat 중단', 'error'
            elif door_seen:
                code, label, severity = 'transitioning', 'PatHouse → Plaza 전환 중', 'working'
            elif player_is_pathouse and player_exit_ready:
                code, label, severity = 'pathouse_exit_ready', 'PatHouse · 성장 완료 / 외출 가능', 'ok'
            elif player_is_pathouse and heartbeat_recent:
                code, label, severity = 'pathouse_stable', 'PatHouse 정상 · 성장 진행 중', 'ok'
            elif not heartbeat_recent:
                code, label, severity = 'client_stale', '게임 루프 정지 의심 · heartbeat 중단', 'warning'
            else:
                code, label, severity = 'observing', '상태 관측 중', 'working'
            return {
                'code': code,
                'label': label,
                'severity': severity,
                'scene': player_scene,
                'phase': player_phase,
                'dispatch_mode': player_mode,
                'self_actor_id': player_self,
                'full_0064_sent': plaza_committed,
                'state1_ready': state1_ready,
                'heartbeat_recent': heartbeat_recent,
                'heartbeat_idle_s': heartbeat_idle_s,
                'door_0019_seen': door_seen,
                'memory_observed': bool(primary),
            }

        for index, player in enumerate(players):
            player['transition'] = transition_for_player(player, primary=(index == 0))

        if not players:
            transition = {
                'code': 'no_client', 'label': '클라이언트 없음', 'severity': 'idle',
                'scene': None, 'phase': None, 'dispatch_mode': None, 'self_actor_id': None,
                'full_0064_sent': False, 'state1_ready': False,
                'heartbeat_recent': False, 'heartbeat_idle_s': None,
                'door_0019_seen': False, 'memory_observed': False,
            }
        elif len(players) == 1:
            transition = dict(players[0]['transition'])
        else:
            child_transitions = [player['transition'] for player in players]
            plaza_count = sum(1 for player in players if player.get('room_kind') == PLAZA_ROOM_KIND)
            pathouse_count = sum(1 for player in players if player.get('room_kind') in PATHOUSE_ROOM_KINDS)
            stale_count = sum(1 for item in child_transitions if not item.get('heartbeat_recent'))
            error_count = sum(1 for item in child_transitions if item.get('severity') == 'error')
            transition = dict(players[0]['transition'])
            transition.update({
                'code': 'multi_client_error' if error_count else 'multi_client',
                'label': (
                    f'{len(players)} clients · Plaza {plaza_count} / PatHouse {pathouse_count}'
                    + (f' · stale {stale_count}' if stale_count else ' · heartbeat 정상')
                ),
                'severity': 'error' if error_count else ('warning' if stale_count else 'ok'),
                'client_count': len(players),
                'plaza_count': plaza_count,
                'pathouse_count': pathouse_count,
                'stale_count': stale_count,
                'error_count': error_count,
            })
        return {
            'server': {
                'port': self.port,
                'bind_host': self.bind_host,
                'listen_address': f'{self.bind_host}:{self.port}',
                'running': self.running,
                'clients': len(self.connections),
                'uptime': round(time.time() - self.started_at, 1),
                'capture': self.capture_path,
                'structured_capture': self.structured_capture.snapshot(),
                'players': players,
                'memory_watch_entity_id': players[0].get('entity_id') if players else None,
            },
            'multiplayer': {
                'connected_clients': len(self.connections),
                'plaza_clients': sum(
                    1 for player in players
                    if player.get('room_kind') == PLAZA_ROOM_KIND
                ),
                'remote_actor_slots': MAX_REMOTE_ACTORS_PER_CLIENT,
                'max_visible_players_per_client': MAX_REMOTE_ACTORS_PER_CLIENT + 1,
                'receive_buffer_bytes': CLIENT_RECEIVE_BUFFER_SIZE,
                'max_declared_payload_bytes': MAX_SAFE_PACKET_PAYLOAD,
                'actor_record_bytes': STATE_0066_RECORD_SIZE,
                'max_actor_records_by_buffer': MAX_SAFE_PACKET_PAYLOAD // STATE_0066_RECORD_SIZE,
                'effective_actor_records': MAX_REMOTE_ACTORS_PER_CLIENT,
                'roster_cap_dropped_clients': sum(
                    max(0, int(player.get('peer_count') or 0) - MAX_REMOTE_ACTORS_PER_CLIENT)
                    for player in players
                ),
                'flush_0065_policy': (
                    'self/fixed actor를 먼저 teardown하고 원격 목록을 비우는 전면 reset; '
                    '0066 후속은 바이너리가 보장하지 않으므로 현재 self 확정 후 자동 전송 금지'
                ),
                'roster_mode': '0066 upsert + 0068 position, 0067 targeted leave',
            },
            'ox': self.ox_snapshot(),
            'content': {
                # configured_evolution is retained for API compatibility; it
                # is only bootstrap 0x0007[2], not the live client stage.
                'configured_evolution': AZRON_EVOLUTION,
                'content_profile': CONTENT_PROFILE,
                'state_namespace': STATE_STORE_NAMESPACE or 'default',
                'bootstrap_evolution': AZRON_EVOLUTION,
                'natural_evolution': natural_evolution,
                'persisted_evolution': safe_state.get('persisted_evolution'),
                'natural_evolution_source': (
                    'C2S 0x0007 snapshot +0x05' if natural_evolution is not None
                    else 'not observed'
                ),
                'outside_gate_required_evolution': 1,
                'outside_gate_ready': outside_gate_ready,
                'outside_gate_object': (
                    'dm_door_0003_057 / dm_door_0003.MDL / '
                    'natural C2S 0x0019 verified'
                ),
                'mirror_01_role': 'PatHouse wardrobe/mirror object; not the outside door',
                'active_entity_id': active_entity_id,
                'state_store_dir': self.state_store_dir,
                'active_content_save_count': int(safe_state.get('content_save_count') or 0),
                'saved_state_loaded': bool(safe_state.get('saved_state_loaded')),
                'last_content_save_time': safe_state.get('last_content_save_time'),
                'last_content_save_sum_matches': safe_state.get('last_content_save_sum_matches'),
                'pushup_stat_0x1f': safe_state.get('last_content_save_stat_0x1F'),
                'dumbbell_stat_0x20': safe_state.get('last_content_save_stat_0x20'),
                'rope_skipping_stat_0x21': safe_state.get('last_content_save_stat_0x21'),
            },
            'transition': transition,
            'paused': paused,
            'pending': pending,
            'proto_state': safe_state,
            'packets': packets,
            'events': events,
            'transactions': transactions,
            'mutation_journal': {
                'schema': 'azrok.mutation.transaction.v1',
                'file': 'mutation_transactions_v1.jsonl',
                'latest_seq': self.mutation_seq,
                'loaded_records': self.mutation_journal_loaded_records,
                'failures': self.mutation_journal_failures,
                'corrupt_lines': self.mutation_journal_corrupt_lines,
                'sequence_gaps': self.mutation_journal_sequence_gaps,
                'durable': (
                    self.mutation_journal_failures == 0
                    and self.mutation_journal_corrupt_lines == 0
                    and self.mutation_journal_sequence_gaps == 0
                ),
            },
            'watches': watches,
        }

    def read_watches(self):
        """A deliberately small, read-only view of client state. Not a memory browser."""
        if not self.hProcess:
            return {'gm': None, 'note': 'no process attached'}
        try:
            gm = find_real_gm(self.hProcess)
            if not gm:
                return {'gm': None, 'note': 'gm not found yet'}
            st = collect_runtime_state(self.hProcess, gm, 0, 0)
            client_windows = list_process_windows(self.hProcess)
            engine_error_dialog = next((
                window for window in client_windows
                if window.get('title', '').lower().startswith('error e')
                or any(
                    'nexus too small' in text.lower()
                    for text in window.get('child_texts', ())
                )
            ), None)
            # Acknex's Nexus arena grows from both ends.  These globals are
            # counters, not three heap pointers: free = total-bottom-top.
            nexus_bottom = read_dword(self.hProcess, 0x102FE9B0)
            nexus_total = read_dword(self.hProcess, 0x102FE9BC)
            nexus_top = read_dword(self.hProcess, 0x102FE9C0)
            nexus_base = read_dword(self.hProcess, 0x102FE9C8)
            nexus_used = min(nexus_total, nexus_bottom + nexus_top) if nexus_total else 0
            nexus_free = max(0, nexus_total - nexus_bottom - nexus_top)
            return {
                'gm': f"0x{gm:08X}",
                'flag_31c71': st['flag_31c71'],
                'flag_31c72': st['flag_31c72'],
                'flag_31c73': st['flag_31c73'],
                'scene_ready_latch': st['scene_ready_latch'],
                'phase_31792': st['phase_31792'],
                'phase_31796': st['phase_31796'],
                'scene_opcode': st['scene_opcode'],
                'self_actor_id': st['self_actor_id'],
                'logic_state': f"0x{st['logic_state']:08X}",
                'logic_controller_ptr': (
                    f"0x{st['logic_controller_ptr']:08X}"
                    if st['logic_controller_ptr'] else 'unresolved'
                ),
                'dispatch_gate': (
                    f"0x{st['dispatch_gate']:08X}"
                    if st['logic_controller_ptr'] else 'unresolved'
                ),
                'dispatch_mode': (
                    st['dispatch_mode'] if st['logic_controller_ptr']
                    else 'unresolved'
                ),
                'dispatch_gate_outer_buffer': (
                    f"0x{st['dispatch_gate_outer_buffer']:08X}"
                    if st['dispatch_gate_outer_buffer'] else 'unresolved'
                ),
                'dispatch_gate_matches_gm': st['dispatch_gate_matches_gm'],
                'dispatch_gate_matches_outer_buffer': st['dispatch_gate_matches_outer_buffer'],
                'dispatch_owner_subobject': st['dispatch_owner_subobject'],
                'dispatch_owner_chain': st['dispatch_owner_chain'],
                'dispatch_owner_candidates': st['dispatch_owner_candidates'],
                'dispatch_vtable_candidates': st['dispatch_vtable_candidates'],
                'nexus': read_dword(self.hProcess, 0x102FC540),
                'nexus_allocator': {
                    'base': f'0x{nexus_base:08X}' if nexus_base else 'unresolved',
                    'total_bytes': nexus_total,
                    'bottom_used_bytes': nexus_bottom,
                    'top_used_bytes': nexus_top,
                    'used_bytes': nexus_used,
                    'free_bytes': nexus_free,
                    'used_percent': (
                        round(nexus_used * 100.0 / nexus_total, 2)
                        if nexus_total else None
                    ),
                },
                'engine_error_active': engine_error_dialog is not None,
                'engine_error_dialog': engine_error_dialog,
                'client_windows': client_windows,
                'transition_vptrs_ok': st['transition_vptrs_ok'],
                **{
                    f'vptr_{name}': f"0x{st['transition_vptrs'][name]:08X}"
                    for name, _offset, _expected in TRANSITION_VPTR_SPECS
                },
                'transition_cleanup_children_ok': st['transition_cleanup_children']['ok'],
                'transition_cleanup_children_state': st['transition_cleanup_children']['state'],
                'transition_cleanup_children_total': st['transition_cleanup_children']['total'],
                'transition_cleanup_children_zero': st['transition_cleanup_children']['zero'],
                'transition_cleanup_children_nonzero': st['transition_cleanup_children']['nonzero'],
                'transition_cleanup_children_readable_nonzero': st['transition_cleanup_children']['readable_nonzero'],
                'transition_cleanup_children_invalid': st['transition_cleanup_children']['invalid'][:4],
                'transition_cleanup_children_unknown': st['transition_cleanup_children']['unknown'][:4],
                'transition_cleanup_children_missing_expected': st['transition_cleanup_children']['missing_expected'][:4],
                'space_path_flag': st['space_path_flag'],
                'notice_path': st['notice_path'],
                'notice_armed_d0': st['notice_armed_d0'],
                'notice_armed_d1': st['notice_armed_d1'],
                'notice_tick_c8': st['notice_tick_c8'],
                'notice_tick_cc': st['notice_tick_cc'],
                'notice_countdown_d7': st['notice_countdown_d7'],
            }
        except Exception as e:
            return {'gm': None, 'note': f'read failed: {e}'}

    def run_macro(self, name):
        """Run a named packet recipe. Returns (ok, message)."""
        macro = MACROS.get(name)
        if macro is None:
            return False, f"unknown macro '{name}' (have: {', '.join(sorted(MACROS))})"
        if self._active_conn() is None:
            return False, "no client connected"
        if name == 'hansol':
            ready, detail = self._hansol_transition_ready()
            if not ready:
                return False, f"hansol macro deferred: {detail}"
        print(f"  [CTL] macro '{name}': {len(macro['steps'])} steps")
        for i, (opcode, spec, delay_ms) in enumerate(macro['steps'], 1):
            try:
                payload = spec(self) if callable(spec) else bytes.fromhex(spec)
            except Exception as e:
                return False, f"step {i} (0x{opcode:04X}) payload build failed: {e}"
            ok, msg = self.inject(opcode, payload, origin='macro')
            if not ok:
                return False, f"step {i}/{len(macro['steps'])} (0x{opcode:04X}) failed: {msg}"
            if delay_ms:
                time.sleep(delay_ms / 1000.0)
        return True, f"macro '{name}' completed ({len(macro['steps'])} steps)"

    def _hansol_transition_ready(self):
        """Require the stable PatHouse baseline before injecting S->C 0x000D.

        Running the transition prelude while initial auto-calibration is still
        emitting S->C 0x0004[00] interleaves those packets with the Hansol
        calibration and leaves the client at scene opcode 110.  These checks
        are observational only; they do not alter client memory or protocol
        state.
        """
        state = self._active_proto_state()
        missing = []
        for key in ('char_created', 'zone_request_seen'):
            if not state.get(key):
                missing.append(f'{key}=false')
        if state.get('zone_request_count', 0) < 2:
            missing.append(f"zone_request_count={state.get('zone_request_count', 0)}<2")
        # Legacy name: this counts bootstrap 0x0004[00] packets sent by the
        # server. It is a timing/quiescence marker, not Hansol calibration.
        if state.get('calib_0004_count', 0) < 5:
            missing.append(f"bootstrap_0004_00_count={state.get('calib_0004_count', 0)}<5")
        if state.get('stable_heartbeat_count', 0) < 2:
            missing.append(f"stable_heartbeat_count={state.get('stable_heartbeat_count', 0)}<2")
        watch = self.read_watches()
        if watch.get('phase_31792') != 2:
            missing.append(f"phase_31792={watch.get('phase_31792')}")
        if not watch.get('scene_ready_latch'):
            missing.append(f"scene_ready_latch={watch.get('scene_ready_latch')}")
        if watch.get('scene_opcode') != 100:
            missing.append(f"scene_opcode={watch.get('scene_opcode')}")
        if watch.get('transition_vptrs_ok') is not True:
            actual = ','.join(
                f"{name}={watch.get(f'vptr_{name}', 'unreadable')}"
                for name, _offset, _expected in TRANSITION_VPTR_SPECS
            )
            missing.append(f"transition_vptrs_invalid({actual})")
        if watch.get('transition_cleanup_children_ok') is not True:
            missing.append(
                'transition_cleanup_children_'
                f"{watch.get('transition_cleanup_children_state', 'unreadable')}"
                f"(zero={watch.get('transition_cleanup_children_zero')}/"
                f"{watch.get('transition_cleanup_children_total')},"
                f"nonzero={watch.get('transition_cleanup_children_nonzero')})"
            )
        return (not missing, ', '.join(missing) if missing else 'baseline stable')

    @contextmanager
    def _client_protocol_context(self, conn):
        """Run one connection's protocol work against its own state.

        The recovered response contract has historically lived on
        ``self.proto_state``.  Keeping that surface avoids a risky rewrite of
        the packet builders, while this context prevents a reused-server
        secondary client from inheriting the primary client's room, timer, or
        calibration flags.  The lock also makes the temporary state swap
        deterministic when two socket threads receive packets together.
        """
        with self.proto_lock:
            with self.ctl_lock:
                meta = self.client_meta.get(conn)
                local = meta.get('proto_state') if meta else None
            if local is None:
                local = {
                    k: (bytes(v) if isinstance(v, (bytes, bytearray)) else v)
                    for k, v in self.proto_template.items()
                }
            previous = self.proto_state
            self.proto_state = local
            try:
                yield local
            finally:
                with self.ctl_lock:
                    meta = self.client_meta.get(conn)
                    if meta is not None:
                        meta['proto_state'] = self.proto_state
                        # Slot selection restores the canonical character
                        # identity inside _build_response(), after the earlier
                        # packet-level identity hook has already run.  Mirror
                        # that authoritative per-client state back into the
                        # relay metadata so peers see the real character name
                        # instead of the bootstrap placeholder "Player".
                        raw_name = self.proto_state.get('char_name_raw')
                        if isinstance(raw_name, str):
                            try:
                                raw_name = bytes.fromhex(raw_name)
                            except ValueError:
                                raw_name = raw_name.encode('cp949', errors='ignore')
                        if isinstance(raw_name, (bytes, bytearray)):
                            decoded_name = bytes(raw_name).split(b'\x00', 1)[0].decode(
                                'cp949', errors='ignore'
                            ).strip()
                            if decoded_name:
                                meta['name'] = decoded_name[:12]
                        account_name = self.proto_state.get('account_name')
                        if account_name:
                            # Account IDs use the full 13-byte login field;
                            # the 12-character display-name limit does not apply.
                            meta['account'] = str(account_name)
                        char_type = self.proto_state.get('char_type')
                        if isinstance(char_type, int) and 0 <= char_type <= 3:
                            meta['char_type'] = char_type
                self.proto_state = previous

    def _hex_dump(self, data, prefix="    ", max_bytes=256):
        """Pretty-print hex dump of data."""
        lines = []
        for i in range(0, min(len(data), max_bytes), 16):
            chunk = data[i:i+16]
            h = ' '.join(f'{b:02X}' for b in chunk)
            a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f"{prefix}{i:04X}: {h:<48} {a}")
        if len(data) > max_bytes:
            lines.append(f"{prefix}... ({len(data) - max_bytes} more bytes)")
        return '\n'.join(lines)

    def _parse_packets(self, buf):
        """
        Parse a byte buffer into individual game packets.
        Packet format: [2-byte LE payload_size][2-byte LE opcode][payload]
        Returns list of (opcode, payload, raw_bytes) and remaining unparsed bytes.
        """
        packets = []
        pos = 0
        while pos + 4 <= len(buf):
            payload_size = struct.unpack('<H', buf[pos:pos+2])[0]
            if payload_size > MAX_SAFE_PACKET_PAYLOAD:
                raise ValueError(
                    f'declared payload {payload_size} exceeds client-safe limit '
                    f'{MAX_SAFE_PACKET_PAYLOAD}'
                )
            total_size = 4 + payload_size
            if pos + total_size > len(buf):
                break  # incomplete packet, keep in buffer
            opcode = struct.unpack('<H', buf[pos+2:pos+4])[0]
            payload = buf[pos+4:pos+total_size]
            raw = buf[pos:pos+total_size]
            packets.append((opcode, payload, raw))
            pos += total_size
        return packets, buf[pos:]

    def _handle_client(self, conn, addr):
        """Handle a client connection with proper TCP stream parsing."""
        conn.settimeout(2.0)
        pkt_num = 0
        recv_buf = bytearray()  # TCP stream reassembly buffer
        login_sent = False

        while self.running:
            try:
                data = conn.recv(4096)
                if not data:
                    print(f"  [SERVER] Client disconnected")
                    break

                recv_buf.extend(data)

                # Parse all complete packets from buffer
                packets, recv_buf = self._parse_packets(bytes(recv_buf))
                recv_buf = bytearray(recv_buf)

                for opcode, payload, raw in packets:
                    pkt_num += 1

                    # Log to console
                    print(f"\n  [RECV #{pkt_num}] opcode=0x{opcode:04X}, payload={len(payload)}B, total={len(raw)}B")
                    if opcode != 0x0016:  # don't dump heartbeats
                        print(self._hex_dump(raw))

                    # Log to file (real-time)
                    self._log_packet('C->S', pkt_num, opcode, payload, raw, conn=conn)

                    # Character creation, relay, and response building all
                    # run against this socket's isolated protocol state.  A
                    # reused server may have two independent clients in
                    # different transition phases at the same time.
                    with self._client_protocol_context(conn):
                        # Character creation carries the human-readable name
                        # and avatar type used by the optional room roster.
                        if opcode == 0x0064 and payload:
                            self._prepare_ox_plaza_return(conn, pkt_num=pkt_num)
                        self._update_client_identity(conn, opcode, payload)

                        # Keep room membership and relay only direction-
                        # verified actor updates.  This is inert with one
                        # client and must happen before any response.
                        if opcode == 0x006B:
                            self._handle_ox_portal_request_006b(
                                conn, payload, pkt_num
                            )
                        elif opcode == 0x00C8:
                            self._handle_ox_enter(
                                conn, payload, pkt_num, require_portal=True
                            )
                        elif opcode == 0x00C9:
                            self._handle_ox_leave_00c9(conn, payload, pkt_num)
                        elif opcode == 0x00CA:
                            self._handle_ox_answer_00ca(conn, payload, pkt_num)
                        self._capture_c2s_raw(conn, opcode, payload)
                        if opcode in (0x0065, 0x0066, 0x0067):
                            self._relay_to_room_peers(conn, opcode, payload, pkt_num)
                        if opcode == 0x0068:
                            self._relay_chat_0068(conn, payload, pkt_num)
                        elif opcode == 0x0069:
                            self._handle_plaza_chair_0069(conn, payload, pkt_num)
                        elif opcode == 0x006A:
                            self._handle_plaza_actor_state_006a(conn, payload, pkt_num)
                        elif opcode == 0x006C:
                            self._relay_community_006c(conn, payload, pkt_num)
                        elif opcode == 0x0018:
                            self._process_accessory_0018(
                                conn, payload, pkt_num=pkt_num
                            )

                        # Build and send response using the per-client state.
                        response = self._build_response(opcode, payload, pkt_num)
                        if response:
                            self._emit(conn, response, origin='auto', pkt_num=pkt_num)

                        # Wait for the full character-state packet before
                        # sending remote actor records; this keeps both
                        # clients past character selection and avoids feeding
                        # S2C 0x0066 to a half-initialized scene.
                        if (opcode == 0x0007 and len(payload) >= 196) or opcode == 0x0064:
                            self._notify_local_room_roster(conn)

                    # Login is now answered synchronously by _build_response:
                    # S2C 0x01 auth must precede S2C 0x00 lobby bootstrap.
                    # Keep this local bit only for diagnostics; never replay a
                    # delayed 0x00 after heartbeat traffic.
                    if not login_sent:
                        with self.ctl_lock:
                            meta = self.client_meta.get(conn) or {}
                            state = meta.get('proto_state') or {}
                            login_sent = bool(state.get('login_response_sent'))

            except socket.timeout:
                continue
            except ConnectionResetError:
                print(f"  [SERVER] Connection reset by game")
                break
            except Exception as e:
                print(f"  [SERVER] Error: {e}")
                import traceback
                traceback.print_exc()
                break

        # Tell surviving mode-2 peers before the old-room metadata disappears,
        # then run the independent Plaza/state-1 departure path.
        self._ox_remove_participant(conn)
        self._notify_room_departure(conn)

        with self.ctl_lock:
            departing_meta = dict(self.client_meta.get(conn) or {})
        if departing_meta:
            self._add_event(
                'leave', f"클라이언트 #{departing_meta.get('entity_id')} 연결이 종료되었습니다.",
                entity_id=departing_meta.get('entity_id'), severity='warn',
                details={'room': departing_meta.get('room_name')},
            )

        # Drop the socket from the active list before closing, so inject()/macros never
        # pick a dead connection.
        with self.ctl_lock:
            if conn in self.connections:
                self.connections.remove(conn)
            self.client_meta.pop(conn, None)
        try:
            conn.close()
        except:
            pass

    def _make_packet(self, opcode, payload=b''):
        """
        Build a packet in the game's format:
        [2-byte LE payload_size][2-byte LE opcode][payload]
        """
        payload = bytes(payload)
        if len(payload) > MAX_SAFE_PACKET_PAYLOAD:
            raise ValueError(
                f'payload too large for Azrok client receive buffer: '
                f'{len(payload)} > {MAX_SAFE_PACKET_PAYLOAD}'
            )
        pkt = struct.pack('<HH', len(payload), opcode) + payload
        return pkt

    def _pack_u16(self, buf, offset, value):
        struct.pack_into('<H', buf, offset, value & 0xFFFF)

    def _pack_u32(self, buf, offset, value):
        struct.pack_into('<I', buf, offset, value & 0xFFFFFFFF)

    def _build_zone_datetime_code(self):
        """
        Build the 8-digit YYMMDDHH code consumed by 0x59E330 -> 0x5A8C90.

        Ghidra notes:
        - the dword at payload + 0x03 is split into decimal groups:
          [YY][MM][DD][HH]
        - if that value stays 0, the tail of 0x59E330 falls into the
          0x005A8790(-1) fallback path

        Use the local wall clock as a conservative non-zero candidate.
        """
        now = datetime.datetime.now()
        return (
            (now.year % 100) * 1000000 +
            now.month * 10000 +
            now.day * 100 +
            now.hour
        )

    def _is_valid_zone_datetime_code(self, value):
        """
        Validate the decimal YYMMDDHH-style code consumed by 0x005A8C90.

        The field is decimal-packed, not bit-packed, so values like 0x00FF0000
        are non-zero but still nonsensical once split into [YY][MM][DD][HH].
        """
        if value <= 0:
            return False

        yy = value // 1000000
        mm = (value // 10000) % 100
        dd = (value // 100) % 100
        hh = value % 100

        if yy > 99:
            return False
        if mm < 1 or mm > 12:
            return False
        if dd < 1 or dd > 31:
            return False
        if hh > 23:
            return False
        return True

    def _sanitize_c2s_mode_pairs(self, snapshot):
        """Validate the C2S 0x0007 mode/date tail before persistence.

        ModePairWriter_Import@005AA6F0 has no 0xFF sentinel.  A historic
        server draft sent 0xFF×8; stage-0 clients clamped that corruption to
        state 2×8 with zero dates.  Recognize that exact legacy signature and
        reset it to fresh state.  Disease groups 5..7 are client-authoritative
        local progression states 0..3; states 1..3 require a valid packed
        YYMMDDHH game-clock value.
        """
        if len(snapshot) < 0xC4:
            return bytes(snapshot), False
        clean = bytearray(snapshot[:0xC4])
        modes = list(clean[0x9C:0xA4])
        dates = [struct.unpack_from('<I', clean, 0xA4 + idx * 4)[0]
                 for idx in range(8)]
        changed = False

        if modes == [2] * 8 and dates == [0] * 8:
            clean[0x9C:0xA4] = b'\x00' * 8
            changed = True

        for group in (5, 6, 7):
            mode_offset = 0x9C + group
            date_offset = 0xA4 + group * 4
            mode = clean[mode_offset]
            date_value = struct.unpack_from('<I', clean, date_offset)[0]
            if mode > 3 or (mode in (1, 2, 3)
                            and not self._is_valid_zone_datetime_code(date_value)):
                clean[mode_offset] = 0
                self._pack_u32(clean, date_offset, 0)
                changed = True
        return bytes(clean), changed

    def _character_state_key(self):
        """Return an account+slot+character key for the active profile."""
        account_raw = self.proto_state.get('account_raw') or b''
        if isinstance(account_raw, str):
            account_raw = account_raw.encode('cp949', errors='ignore')
        account_raw = bytes(account_raw).split(b'\x00', 1)[0][:13]

        raw = self.proto_state.get('char_name_raw') or b'Player'
        if isinstance(raw, str):
            raw = raw.encode('cp949', errors='ignore')
        raw = bytes(raw).split(b'\x00', 1)[0][:32]
        if not raw:
            raw = b'Player'
        if not account_raw:
            # Preserve compatibility for sessions started before the exact
            # login decoder was introduced.
            return raw.hex()
        slot = int(self.proto_state.get('character_slot', 0)) & 0x03
        return f'a{account_raw.hex()}_s{slot}_c{raw.hex()}'

    def _selected_character_state_key(self):
        """Return the immutable key bound by successful create/select.

        Login alone is not character authority.  In particular, a second raw
        session can have a valid account and the bootstrap ``Player``
        placeholder after its slot selection is rejected by the exclusive
        lease.  Server-owned mutations must never let that placeholder fall
        through to a real canonical path.
        """
        if not self.proto_state.get('client_0005_seen'):
            return None
        selected_key = self.proto_state.get('selected_character_key')
        if not isinstance(selected_key, str) or not selected_key:
            return None
        current_key = self._character_state_key()
        if selected_key != current_key:
            return None
        return selected_key

    def _bind_selected_character_identity(self):
        """Bind the current explicit character identity to this session."""
        key = self._character_state_key()
        # Per-field 0x0017 authority belongs to one selected character.  A
        # reselect on the same socket must not carry it into another slot.
        self.proto_state.pop('c2s_0017_stat_authority', None)
        self.proto_state.pop('c2s_0017_authority_key', None)
        self.proto_state.pop('last_c2s_0017_authoritative_stat', None)
        self.proto_state['selected_character_key'] = key
        self.proto_state['client_0005_seen'] = True
        return key

    def _release_character_session_for_logout(self, pkt_num=0):
        """Release one selected character while preserving its account data.

        C2S 0x0002 begins the original logout transition.  Keep the
        account-scoped lobby and durable state intact while removing the
        selected-character lease and any state-1/mode-2 actor membership.
        The later C2S 0x0001 completion is answered with the original client
        exit path because a same-process lobby repaint is not live-accepted.
        """
        source = None
        if hasattr(self, 'ctl_lock') and hasattr(self, 'client_meta'):
            with self.ctl_lock:
                for conn, meta in self.client_meta.items():
                    if meta.get('proto_state') is self.proto_state:
                        source = conn
                        break

        entity_id = None
        if source is not None:
            with self.ctl_lock:
                meta = self.client_meta.get(source) or {}
                entity_id = meta.get('entity_id')
                old_room = meta.get('room_kind')
            if old_room == LOCAL_OX_ROOM_KIND:
                self._ox_remove_participant(source, pkt_num=pkt_num)
            else:
                self._notify_room_departure(source, old_room)
            with self.ctl_lock:
                meta = self.client_meta.get(source)
                if meta is not None:
                    meta['room_kind'] = None
                    meta['room_name'] = '미선택'
                    meta['x'] = None
                    meta['y'] = None
                    meta['heading'] = 0
                    meta['movement_generation'] = int(
                        meta.get('movement_generation') or 0
                    ) + 1
                    meta['visible_remote_actor_ids'] = set()
                    meta['roster_bootstrapped'] = False
                    meta['ox_room_id'] = None
                    meta['ox_round_generation'] = None
                    meta['community_target_actor_id'] = None
                    meta['name'] = 'Player'
                    meta['char_type'] = 0

        # Selection/scene fields are disposable.  Do not clear account_raw,
        # account_name, login_response_sent, account_has_characters or
        # lobby_slots: those are the account and four-slot lobby authority.
        self.proto_state['selected_character_key'] = None
        self.proto_state['client_0005_seen'] = False
        self.proto_state['char_created'] = False
        self.proto_state['char_name_raw'] = b'Player'
        self.proto_state['char_type'] = 0
        self.proto_state['character_slot'] = 0
        self.proto_state.pop('wire_character_slot', None)
        self.proto_state.pop('selected_evolution', None)
        self.proto_state.pop('c2s_0017_stat_authority', None)
        self.proto_state.pop('c2s_0017_authority_key', None)
        self.proto_state.pop('last_c2s_0017_authoritative_stat', None)
        for key, value in (
            ('zone_request_seen', False),
            ('zone_request_count', 0),
            ('client_0007_count', 0),
            ('post_create_seen', False),
            ('post_0017_followup_sent', False),
            ('full_0064_pending', False),
            ('full_0064_sent', False),
            ('client_0064_seen', False),
            ('client_0064_heartbeat_count', 0),
            ('late_006e_sent', False),
            ('stable_heartbeat_count', 0),
            ('door_0019_seen', False),
            ('door_0019_count', 0),
        ):
            self.proto_state[key] = value
        self.proto_state['explicit_character_logout'] = True
        # Belt-and-suspenders with the explicit flag: an already-running
        # --auto-select-existing server must not immediately choose slot 0.
        self.proto_state['auto_select_existing_sent'] = True
        self.proto_state['last_character_logout'] = {
            'request_opcode': '0x0002',
            'packet_seq': int(pkt_num),
            'entity_id': entity_id,
            'status': 'client_exit_pending',
        }
        account_raw = bytes(self.proto_state.get('account_raw') or b'')
        if account_raw:
            if not hasattr(self, 'manual_select_accounts'):
                self.manual_select_accounts = set()
            lock = getattr(self, 'ctl_lock', None)
            if lock is None:
                self.manual_select_accounts.add(account_raw)
            else:
                with lock:
                    self.manual_select_accounts.add(account_raw)
        if hasattr(self, '_add_event'):
            self._add_event(
                'character_logout',
                f'클라이언트 #{entity_id} 캐릭터 선택을 해제했습니다.',
                entity_id=entity_id, severity='ok',
                details={'request_opcode': '0x0002'},
            )
        return True

    def _character_session_in_use(self, account_raw, storage_slot, name_raw):
        """Reject two live sockets selecting the same persistent character."""
        if not hasattr(self, 'ctl_lock') or not hasattr(self, 'client_meta'):
            return False
        account_raw = bytes(account_raw or b'').split(b'\x00', 1)[0][:13]
        name_raw = bytes(name_raw or b'').split(b'\x00', 1)[0][:32]
        target_key = (
            f'a{account_raw.hex()}_s{int(storage_slot)}_c{name_raw.hex()}'
            if account_raw and name_raw and int(storage_slot) in range(4)
            else None
        )
        with self.ctl_lock:
            for meta in self.client_meta.values():
                other = meta.get('proto_state') or {}
                if other is self.proto_state or not other.get('client_0005_seen'):
                    continue
                other_selected_key = other.get('selected_character_key')
                if isinstance(other_selected_key, str):
                    if target_key is not None and other_selected_key == target_key:
                        return True
                    # A bound key is the lease authority.  Do not infer a
                    # second identity from mutable relay/bootstrap fields.
                    continue
                other_account = other.get('account_raw') or b''
                if isinstance(other_account, str):
                    other_account = other_account.encode('cp949', errors='ignore')
                other_name = other.get('char_name_raw') or b''
                if isinstance(other_name, str):
                    other_name = other_name.encode('cp949', errors='ignore')
                if (
                    bytes(other_account).split(b'\x00', 1)[0][:13] == account_raw
                    and int(other.get('character_slot', -1)) == int(storage_slot)
                    and bytes(other_name).split(b'\x00', 1)[0][:32] == name_raw
                ):
                    return True
        return False

    def _legacy_character_state_key(self):
        raw = self.proto_state.get('char_name_raw') or b'Player'
        if isinstance(raw, str):
            raw = raw.encode('cp949', errors='ignore')
        raw = bytes(raw).split(b'\x00', 1)[0][:32] or b'Player'
        return raw.hex()

    def _character_state_path(self, key=None):
        key = key or self._character_state_key()
        return os.path.join(self.state_store_dir, f'{key}_c2s0007.bin')

    def _canonical_state_path(self, key=None):
        key = key or self._character_state_key()
        return os.path.join(self.state_store_dir, f'{key}_state_v1.json')

    def _read_canonical_actor_evolution(self, key, peer_state=None):
        """Project the peer's persisted stage, never the recipient's profile."""
        document = (getattr(self, 'saved_server_states', None) or {}).get(key)
        if document is None and isinstance(key, str) and key and getattr(self, 'state_store_dir', None):
            try:
                with open(self._canonical_state_path(key), 'r', encoding='utf-8') as state_file:
                    document = json.load(state_file)
            except (OSError, ValueError, TypeError):
                document = None
        progression = accessory_progression_from_canonical(document)
        if progression is not None and progression['evolution'] in range(4):
            return progression['evolution']
        for field in ('persisted_evolution', 'selected_evolution'):
            stage = (peer_state or {}).get(field)
            if isinstance(stage, int) and stage in range(4):
                return stage
        return 0

    def _read_canonical_accessory_slots(self, key):
        """Read a peer's appearance without creating or poisoning its cache.

        Roster construction runs inside the recipient's protocol context.  A
        normal canonical load for a missing peer file would therefore build a
        default document from the recipient identity and cache it under the
        peer key.  Appearance projection is read-only, so use an existing cache
        entry or inspect the peer document directly and fail closed to FFx4.
        """
        default = list(DEFAULT_ACCESSORY_SLOTS)
        if not isinstance(key, str) or not key:
            return default
        cached = (getattr(self, 'saved_server_states', None) or {}).get(key)
        if isinstance(cached, dict):
            slots = normalize_accessory_slots(cached.get('accessory_slots'))
            return slots if slots is not None else default
        try:
            with open(self._canonical_state_path(key), 'r', encoding='utf-8') as state_file:
                document = json.load(state_file)
        except (FileNotFoundError, OSError, ValueError, TypeError):
            return default
        if document.get('schema_version') != CANONICAL_STATE_SCHEMA_VERSION:
            return default
        slots = normalize_accessory_slots(document.get('accessory_slots'))
        return slots if slots is not None else default

    def _default_canonical_character_state(self):
        issued_evolution = int(self.proto_state.get('selected_evolution', AZRON_EVOLUTION))
        if not 0 <= issued_evolution <= 3:
            issued_evolution = 0
        rows = [
            {'kind': 0xFF, 'aux': 0xFF, 'value': 0}
            for _ in range(10)
        ]
        if CONTENT_PROFILE == 'shipped' and issued_evolution < 3:
            route_aux = (
                0 if issued_evolution == 0 else
                EVOLUTION_AUX_STAGE1 if issued_evolution == 1 else
                EVOLUTION_AUX_STAGE2
            )
            rows[0] = {'kind': 3, 'aux': route_aux, 'value': 0}
        inventory = {
            name: [0] * size for name, _offset, size in INVENTORY_0007_FIELDS
        }
        for inventory_name, indices in CLIENT_GRANTED_DEFAULT_ITEMS.items():
            for index in indices:
                inventory[inventory_name][index] = 1
        for inventory_name, indices in SERVER_GRANTED_STARTER_ITEMS.items():
            for index in indices:
                inventory[inventory_name][index] = 1
        return {
            'schema_version': CANONICAL_STATE_SCHEMA_VERSION,
            'revision': 0,
            '_revision_valid': True,
            'character': {
                'name_hex': (self.proto_state.get('char_name_raw') or b'Player').hex(),
                'slot': int(self.proto_state.get('character_slot', 0)) & 0x03,
                'species': int(self.proto_state.get('char_type', AZRON_SPECIES)) & 0xFF,
            },
            'snapshot_hex': None,
            # PlayerState+0x1D8 is a four-dword local representation, but its
            # verified wire/storage projection is exactly four selector bytes.
            'accessory_slots': list(DEFAULT_ACCESSORY_SLOTS),
            'inventory': inventory,
            'active_loadouts': {
                name: list(indices)
                for name, indices in CLIENT_GRANTED_DEFAULT_ITEMS.items()
            },
            'runtime_rows': rows,
            # Quest/runtime rows are server-issued but removed locally.  Keep
            # an issuance generation and the evolution baseline beside each
            # row so a later C2S 0x0007 can prove a kind-3 completion without
            # treating a reconnect echo as a new completion.
            'runtime_row_meta': [
                {
                    'generation': 1 if row['kind'] != 0xFF else 0,
                    'issued_evolution': issued_evolution,
                }
                for row in rows
            ],
            'completed_runtime_rows': [],
            # S2C 0x0007 +0x07 and purchase ACK 0x0005 +0x02 both feed the
            # model+0x1F0 money setter.  Fresh profiles remain zero unless a
            # preservation operator explicitly configures starter currency.
            'currency': STARTER_CURRENCY,
        }

    def _load_canonical_character_state(self, key=None):
        key = key or self._character_state_key()
        cache = getattr(self, 'saved_server_states', None)
        if cache is None:
            cache = {}
            self.saved_server_states = cache
        if key in cache:
            return cache[key]

        state = self._default_canonical_character_state()
        path = self._canonical_state_path(key)
        try:
            with open(path, 'r', encoding='utf-8') as state_file:
                loaded = json.load(state_file)
        except FileNotFoundError:
            cache[key] = state
            return state
        except (OSError, ValueError, TypeError) as exc:
            print(f"  [STATE] Ignoring invalid canonical state {path}: {exc}")
            cache[key] = state
            return state

        if loaded.get('schema_version') != CANONICAL_STATE_SCHEMA_VERSION:
            print(
                f"  [STATE] Ignoring unsupported canonical schema in {path}: "
                f"{loaded.get('schema_version')!r}"
            )
            cache[key] = state
            return state

        loaded_revision = loaded.get('revision', 0)
        if (isinstance(loaded_revision, bool)
                or not isinstance(loaded_revision, int)
                or loaded_revision < 0):
            state['_revision_valid'] = False
            self.proto_state['canonical_revision_invalid'] = True
            print(
                f"  [STATE] Refusing invalid canonical revision in {path}: "
                f"{loaded_revision!r}"
            )
        else:
            state['revision'] = loaded_revision
            state['_revision_valid'] = True

        snapshot_hex = loaded.get('snapshot_hex')
        if isinstance(snapshot_hex, str) and len(snapshot_hex) == 0xC4 * 2:
            try:
                bytes.fromhex(snapshot_hex)
                state['snapshot_hex'] = snapshot_hex.lower()
            except ValueError:
                pass

        accessory_slots = normalize_accessory_slots(loaded.get('accessory_slots'))
        if accessory_slots is not None:
            state['accessory_slots'] = accessory_slots

        character = loaded.get('character')
        if isinstance(character, dict):
            state['character'] = dict(state['character'])
            name_hex = character.get('name_hex')
            if isinstance(name_hex, str):
                try:
                    bytes.fromhex(name_hex)
                    state['character']['name_hex'] = name_hex.lower()
                except ValueError:
                    pass
            for field, upper in (('slot', 3), ('species', 3)):
                try:
                    state['character'][field] = max(
                        0, min(upper, int(character.get(field, state['character'][field])))
                    )
                except (TypeError, ValueError):
                    pass

        loaded_inventory = loaded.get('inventory') or {}
        for name, _offset, size in INVENTORY_0007_FIELDS:
            values = loaded_inventory.get(name)
            if isinstance(values, list) and len(values) == size:
                state['inventory'][name] = [
                    max(0, min(0xFF, int(value))) for value in values
                ]

        # The binary grants these unique items in FUN_0059ACD0 on every load
        # before activating the default loadouts.  Preserve that client fact
        # in canonical ownership, including legacy JSON files written before
        # the defaults were server-owned.
        for inventory_name, indices in CLIENT_GRANTED_DEFAULT_ITEMS.items():
            for index in indices:
                state['inventory'][inventory_name][index] = max(
                    1, state['inventory'][inventory_name][index]
                )

        loaded_loadouts = loaded.get('active_loadouts') or {}
        for name, valid_sizes, slot_count in (
                ('toy', (3, 4), 10), ('gym', (3,), 8)):
            values = loaded_loadouts.get(name)
            if not isinstance(values, list) or len(values) not in valid_sizes:
                continue
            try:
                clean = [int(value) for value in values]
            except (TypeError, ValueError):
                continue
            if (
                clean == sorted(set(clean))
                and all(0 <= value < slot_count for value in clean)
                and all(state['inventory'][name][value] > 0 for value in clean)
            ):
                state['active_loadouts'][name] = clean

        rows = loaded.get('runtime_rows')
        if isinstance(rows, list) and len(rows) == 10:
            clean_rows = []
            for row in rows:
                if not isinstance(row, dict):
                    clean_rows = []
                    break
                clean_rows.append({
                    'kind': int(row.get('kind', 0xFF)) & 0xFFFF,
                    'aux': int(row.get('aux', 0xFF)) & 0xFFFF,
                    'value': int(row.get('value', 0)) & 0xFFFFFFFF,
                })
            if len(clean_rows) == 10:
                state['runtime_rows'] = clean_rows
        snapshot_stage = None
        if isinstance(state.get('snapshot_hex'), str):
            try:
                snapshot_stage = bytes.fromhex(state['snapshot_hex'])[0x05]
            except (ValueError, IndexError):
                snapshot_stage = None
        row_meta = loaded.get('runtime_row_meta')
        if isinstance(row_meta, list) and len(row_meta) == 10:
            clean_meta = []
            for idx, meta in enumerate(row_meta):
                if not isinstance(meta, dict):
                    clean_meta = []
                    break
                try:
                    generation = max(0, int(meta.get('generation', 0)))
                    issued_evolution = int(meta.get('issued_evolution', 0))
                except (TypeError, ValueError):
                    clean_meta = []
                    break
                if not 0 <= issued_evolution <= 3:
                    issued_evolution = 0
                clean_meta.append({
                    'generation': generation,
                    'issued_evolution': issued_evolution,
                })
            if len(clean_meta) == 10:
                state['runtime_row_meta'] = clean_meta
        else:
            # Additive migration for schema-v1 files written before row
            # generations existed.  The last accepted stage is the safest
            # issuance baseline: it prevents an already-restored stage from
            # satisfying a newly observed row.
            baseline = snapshot_stage if snapshot_stage in (0, 1, 2, 3) else 0
            state['runtime_row_meta'] = [
                {
                    'generation': 1 if row.get('kind') != 0xFF else 0,
                    'issued_evolution': baseline,
                }
                for row in state['runtime_rows']
            ]
            # Legacy schema-v1 files could retain aux0 after the client had
            # already evolved because row removal was never exported C2S.
            # Migrate exactly one compatibility-route row from the persisted
            # stage so an existing Red/Blue/Gold character can continue its
            # next evolution instead of being stuck on an impossible row.
            if snapshot_stage in (0, 1, 2, 3):
                active_kind3 = next((
                    idx for idx, row in enumerate(state['runtime_rows'])
                    if int(row.get('kind', 0xFF)) == 3
                ), None)
                if snapshot_stage == 3:
                    if active_kind3 is not None:
                        state['runtime_rows'][active_kind3] = {
                            'kind': 0xFF, 'aux': 0xFF, 'value': 0,
                        }
                else:
                    desired_aux = (
                        0 if snapshot_stage == 0 else
                        EVOLUTION_AUX_STAGE1 if snapshot_stage == 1 else
                        EVOLUTION_AUX_STAGE2
                    )
                    if active_kind3 is None:
                        active_kind3 = next((
                            idx for idx, row in enumerate(state['runtime_rows'])
                            if int(row.get('kind', 0xFF)) == 0xFF
                        ), None)
                    if active_kind3 is not None:
                        state['runtime_rows'][active_kind3] = {
                            'kind': 3, 'aux': desired_aux, 'value': 0,
                        }
                        state['runtime_row_meta'][active_kind3] = {
                            'generation': snapshot_stage + 1,
                            'issued_evolution': snapshot_stage,
                        }
        active_kind3_indices = [
            idx for idx, row in enumerate(state['runtime_rows'])
            if int(row.get('kind', 0xFF)) == 3
        ]
        if len(active_kind3_indices) > 1:
            baseline = snapshot_stage if snapshot_stage in range(4) else 0
            for extra_index in active_kind3_indices[1:]:
                state['runtime_rows'][extra_index] = {
                    'kind': 0xFF, 'aux': 0xFF, 'value': 0,
                }
                state['runtime_row_meta'][extra_index] = {
                    'generation': 0,
                    'issued_evolution': baseline,
                }
            self.proto_state['duplicate_kind3_rows_sanitized'] = len(
                active_kind3_indices
            ) - 1

        completed = loaded.get('completed_runtime_rows')
        if isinstance(completed, list):
            state['completed_runtime_rows'] = [
                str(key)[:96] for key in completed[-256:]
                if isinstance(key, (str, int))
            ]
        # Pre-original-route playable files could have been created with the
        # compatibility kind-3 row before any client snapshot existed.  That
        # row bypasses the native kind-5 tutorial chain.  Convert only this
        # pristine legacy signature; progressed and saved characters remain
        # byte-for-byte authoritative.
        if (
            CONTENT_PROFILE == 'playable'
            and state.get('snapshot_hex') is None
            and not state.get('completed_runtime_rows')
        ):
            live_rows = [
                index for index, row in enumerate(state['runtime_rows'])
                if int(row.get('kind', 0xFF)) != 0xFF
            ]
            if (
                len(live_rows) == 1
                and int(state['runtime_rows'][live_rows[0]].get('kind', 0xFF)) == 3
                and int(state['runtime_rows'][live_rows[0]].get('aux', 0xFF)) == 0
            ):
                row_index = live_rows[0]
                state['runtime_rows'][row_index] = {
                    'kind': 0xFF, 'aux': 0xFF, 'value': 0,
                }
                state['runtime_row_meta'][row_index] = {
                    'generation': 0, 'issued_evolution': 0,
                }
                self.proto_state['legacy_playable_kind3_seed_cleared'] = True
        try:
            state['currency'] = max(0, min(0xFFFFFFFF, int(loaded.get('currency', 0))))
        except (TypeError, ValueError):
            state['currency'] = 0
        cache[key] = state
        return state

    def _save_canonical_character_state(self, state, key=None, mutation=None):
        key = key or self._character_state_key()
        path = self._canonical_state_path(key)
        tmp_path = path + '.tmp'
        mutation = mutation or {'kind': 'canonical_save'}
        try:
            revision_before = int(state.get('revision', 0))
        except (TypeError, ValueError):
            revision_before = None
        if (state.get('_revision_valid', True) is not True
                or revision_before is None or revision_before < 0):
            reason = 'canonical revision is invalid; mutation is fail-closed'
            self._record_mutation_transaction(
                mutation, 'rejected', key=key, reason=reason,
                revision_before=revision_before,
            )
            print(f"  [STATE] {reason}: {path}")
            return False
        revision_after = revision_before + 1
        sha256_before = None
        try:
            with open(path, 'rb') as existing_file:
                sha256_before = hashlib.sha256(existing_file.read()).hexdigest()
        except FileNotFoundError:
            pass
        except OSError as exc:
            reason = f'cannot hash existing canonical state: {exc}'
            self._record_mutation_transaction(
                mutation, 'rejected', key=key, reason=reason,
                revision_before=revision_before,
            )
            print(f"  [STATE] {reason}: {path}")
            return False
        accessory_slots = normalize_accessory_slots(
            state.get('accessory_slots', DEFAULT_ACCESSORY_SLOTS)
        )
        if accessory_slots is None:
            reason = 'invalid accessory_slots'
            print(
                f"  [STATE] Refusing invalid accessory_slots for canonical "
                f"state {path}"
            )
            self._record_mutation_transaction(
                mutation, 'rejected', key=key, reason=reason,
                revision_before=revision_before,
                sha256_before=sha256_before,
            )
            return False
        # Keep the cached representation aligned with the validated document.
        state['accessory_slots'] = accessory_slots
        document = {
            'schema_version': CANONICAL_STATE_SCHEMA_VERSION,
            'revision': revision_after,
            'character': {
                'name_hex': (self.proto_state.get('char_name_raw') or b'Player').hex(),
                'slot': int(self.proto_state.get('character_slot', 0)) & 0x03,
                'species': int(self.proto_state.get('char_type', AZRON_SPECIES)) & 0x03,
            },
            'snapshot_hex': state.get('snapshot_hex'),
            'accessory_slots': accessory_slots,
            'inventory': state.get('inventory'),
            'active_loadouts': state.get('active_loadouts'),
            'runtime_rows': state.get('runtime_rows'),
            'runtime_row_meta': state.get('runtime_row_meta'),
            'completed_runtime_rows': state.get('completed_runtime_rows', [])[-256:],
            'currency': int(state.get('currency', 0)),
        }
        serialized = json.dumps(
            document, ensure_ascii=False, sort_keys=True, indent=2
        ) + '\n'
        serialized_bytes = serialized.encode('utf-8')
        sha256_after = hashlib.sha256(serialized_bytes).hexdigest()
        try:
            with open(tmp_path, 'w', encoding='utf-8', newline='\n') as state_file:
                state_file.write(serialized)
                state_file.flush()
                os.fsync(state_file.fileno())
            os.replace(tmp_path, path)
        except OSError as exc:
            print(f"  [STATE] Failed to save canonical state {path}: {exc}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            self._record_mutation_transaction(
                mutation, 'rejected', key=key, reason=str(exc),
                revision_before=revision_before,
                sha256_before=sha256_before,
            )
            return False
        state['revision'] = revision_after
        state['_revision_valid'] = True
        self.saved_server_states[key] = state
        self._record_mutation_transaction(
            mutation, 'committed', key=key,
            revision_before=revision_before, revision_after=revision_after,
            sha256_before=sha256_before, sha256_after=sha256_after,
        )
        return True

    @staticmethod
    def _inventory_slot_for_item(item_id):
        for first_id, last_id, inventory_name, base_id in SHOP_ITEM_INVENTORY_RANGES:
            if first_id <= item_id <= last_id:
                return inventory_name, item_id - base_id
        return None

    @staticmethod
    def _snapshot_stat(snapshot, stat_id):
        if snapshot is None or len(snapshot) < 0xC4 or not 0 <= stat_id < 70:
            return None
        return struct.unpack_from('<H', snapshot, 0x0A + stat_id * 2)[0]

    def _kind3_requirements_met(self, state, snapshot, aux):
        """Mirror Threshold@005A8070/BucketReq@005A82B0 exactly."""
        stats = [self._snapshot_stat(snapshot, idx) for idx in range(70)]
        if any(value is None for value in stats):
            return False
        if aux == 0:
            return stats[2] > 349

        progression_sum = sum(stats[30:66])
        if aux in (1, 2, 3):
            if stats[1] <= 11 or progression_sum <= 999:
                return False
        elif aux in (4, 5, 6):
            if stats[1] <= 24 or progression_sum <= 3999:
                return False
        else:
            return False

        if aux == 1:
            return (
                stats[40] >= 40 and stats[44] >= 40 and stats[6] >= 80
                and all(stats[idx] >= 80 for idx in range(18, 25))
            )
        if aux == 2:
            return (
                stats[43] >= 40 and stats[42] >= 40
                and sum(stats[31:34]) >= 100
            )
        if aux == 3:
            return stats[43] >= 40 and stats[21] >= 80 and stats[20] >= 80
        if aux == 4:
            return (
                stats[35] >= 450 and stats[33] >= 450 and stats[53] >= 120
                and all(stats[idx] >= 80 for idx in range(18, 25))
            )
        if aux == 5:
            furniture = (state.get('inventory') or {}).get('furniture') or []
            furniture_ok = (
                len(furniture) >= 18
                and (int(furniture[16]) > 0 or int(furniture[17]) > 0)
                and (int(furniture[13]) > 0 or int(furniture[14]) > 0)
            )
            return (
                stats[36] >= 450 and stats[32] >= 450 and stats[52] >= 120
                and furniture_ok
            )
        return (
            stats[34] >= 450 and stats[31] >= 400
            and stats[51] >= 120 and stats[7] >= 20
        )

    @staticmethod
    def _issue_next_kind3_row(state, row_index, generation, evolution):
        """Issue one deterministic compatibility route for the next stage."""
        if evolution == 1:
            next_aux = EVOLUTION_AUX_STAGE1
        elif evolution == 2:
            next_aux = EVOLUTION_AUX_STAGE2
        else:
            return None
        next_generation = generation + 1
        state['runtime_rows'][row_index] = {
            'kind': 3, 'aux': next_aux, 'value': 0,
        }
        state['runtime_row_meta'][row_index] = {
            'generation': next_generation,
            'issued_evolution': evolution,
        }
        return {
            'row_index': row_index,
            'generation': next_generation,
            'aux': next_aux,
            'issued_evolution': evolution,
            'policy': 'configured compatibility route',
        }

    def _complete_kind3_runtime_row(self, state, previous_snapshot, snapshot):
        """Retire one server-issued kind-3 row on a proven evolution edge.

        The client does not export its locally removed runtime-row table.
        Static analysis proves that kind 3 commits exactly one evolution stage
        and then removes only the lowest matching row.  The server therefore
        accepts only a monotonic edge from the row's issuance baseline to the
        exact stage implied by aux, with the visible threshold fields also
        satisfied.  Kind 3 has no currency callback, so this never credits
        money.
        """
        if len(snapshot) < 0xC4:
            return None
        rows = state.get('runtime_rows')
        meta_rows = state.get('runtime_row_meta')
        if not isinstance(rows, list) or len(rows) != 10:
            return None
        if not isinstance(meta_rows, list) or len(meta_rows) != 10:
            return None

        row_index = next((
            idx for idx, row in enumerate(rows)
            if isinstance(row, dict) and int(row.get('kind', 0xFF)) == 3
        ), None)
        if row_index is None:
            return None
        row = rows[row_index]
        try:
            aux = int(row.get('aux', 0xFF))
            generation = max(1, int(meta_rows[row_index].get('generation', 1)))
            issued_evolution = int(meta_rows[row_index].get('issued_evolution', 0))
        except (AttributeError, TypeError, ValueError):
            return None
        if aux not in range(7) or issued_evolution not in range(4):
            return None

        expected = 1 if aux == 0 else (2 if aux <= 3 else 3)
        new_evolution = snapshot[0x05]
        old_evolution = (
            previous_snapshot[0x05]
            if previous_snapshot is not None and len(previous_snapshot) >= 0xC4
            else issued_evolution
        )
        if not (
            issued_evolution < expected
            and old_evolution == issued_evolution
            and new_evolution == expected
        ):
            return None

        if not self._kind3_requirements_met(state, snapshot, aux):
            return None

        completion_key = f'g{generation}:r{row_index}:k3:a{aux}:e{expected}'
        completed = state.setdefault('completed_runtime_rows', [])
        if completion_key in completed:
            return None
        completed.append(completion_key)
        del completed[:-256]
        rows[row_index] = {'kind': 0xFF, 'aux': 0xFF, 'value': 0}
        meta_rows[row_index] = {
            'generation': generation,
            'issued_evolution': expected,
        }
        return {
            'key': completion_key,
            'row_index': row_index,
            'generation': generation,
            'aux': aux,
            'evolution_before': old_evolution,
            'evolution_after': new_evolution,
            'currency_awarded': 0,
            # The live client proposes the next route after exporting the
            # stage edge.  Issuing aux1 here raced and rejected its observed
            # aux2 proposal, so leave the row empty until C2S 0010/0011.
            'next_row': None,
            'next_row_policy': 'client proposal via C2S 0010/0011',
        }

    def _complete_runtime_row_from_snapshot(self, state, previous_snapshot, snapshot):
        """Apply only completion policies proven by server-visible evidence.

        Importing/displaying a row is not authority to retire it.  Kinds
        0/1/2/5 finish entirely inside FUN_005A6910 and their row export and
        currency callbacks resolve to local no-op vtable methods.  Record the
        active fail-closed kinds for diagnostics, then dispatch only kind 3.
        """
        active_kinds = sorted({
            int(row.get('kind', 0xFF))
            for row in (state.get('runtime_rows') or [])
            if isinstance(row, dict)
            and int(row.get('kind', 0xFF)) in RUNTIME_ROW_SERVER_POLICIES
        })
        fail_closed = [
            kind for kind in active_kinds
            if not RUNTIME_ROW_SERVER_POLICIES[kind]['auto_retire']
        ]
        self.proto_state['runtime_row_completion_policy'] = {
            'auto_retire_kinds': [3],
            'active_fail_closed_kinds': fail_closed,
            'wire_authority': 'C2S 0x0007 snapshot only',
        }
        return self._complete_kind3_runtime_row(
            state, previous_snapshot, snapshot
        )

    def _process_purchase_0013(self, payload, pkt_num=0):
        """Validate and atomically commit one server-authoritative purchase.

        Returns the exact six-byte S2C 0x0005 subtype-0x13 ACK.  Both success
        and failure must be acknowledged because the client holds its local
        purchase lock until this packet arrives.
        """
        current_balance = 0
        selected_key = None
        save_attempted = False
        try:
            selected_key = self._selected_character_state_key()
            if selected_key is None:
                raise ValueError('purchase requires selected character identity')
            state = self._load_canonical_character_state(key=selected_key)
            current_balance = max(
                0, min(0xFFFFFFFF, int(state.get('currency', 0)))
            )
            count, claimed_total, item_ids = decode_c2s_purchase_0013(payload)
            resolved = []
            computed_total = 0
            for item_id in item_ids:
                catalog_entry = SHOP_ITEM_CATALOG.get(item_id)
                slot = self._inventory_slot_for_item(item_id)
                if catalog_entry is None or slot is None:
                    raise ValueError(f'unknown or non-inventory item id {item_id}')
                computed_total += int(catalog_entry['price'])
                resolved.append((item_id, slot))
            if computed_total != claimed_total:
                raise ValueError(
                    f'claimed total {claimed_total} != catalog total {computed_total}'
                )
            if computed_total > current_balance:
                raise ValueError(
                    f'insufficient currency {current_balance} < {computed_total}'
                )

            # Copy every mutable server-owned collection before validation so
            # a rejected request cannot partially modify the cached state.
            working = dict(state)
            working['inventory'] = {
                name: list(values)
                for name, values in (state.get('inventory') or {}).items()
            }
            for item_id, (inventory_name, slot_index) in resolved:
                quantities = working['inventory'].get(inventory_name)
                if quantities is None or slot_index >= len(quantities):
                    raise ValueError(f'invalid inventory slot for item {item_id}')
                current_quantity = int(quantities[slot_index])
                if inventory_name in SHOP_UNIQUE_INVENTORIES and current_quantity:
                    raise ValueError(f'unique item {item_id} is already owned')
                if current_quantity >= 0xFF:
                    raise ValueError(f'item {item_id} quantity is full')
                quantities[slot_index] = current_quantity + 1

            new_balance = current_balance - computed_total
            working['currency'] = new_balance
            save_attempted = True
            if not self._save_canonical_character_state(
                    working, key=selected_key,
                    mutation={
                        'kind': 'purchase',
                        'request_opcode': '0x0013',
                        'packet_seq': int(pkt_num),
                        'changed_fields': ['currency', 'inventory'],
                        'item_count': count,
                    }):
                raise ValueError('canonical state persistence failed')

            self.proto_state['server_currency'] = new_balance
            self.proto_state['last_purchase'] = {
                'status': 'committed',
                'count': count,
                'claimed_total': claimed_total,
                'computed_total': computed_total,
                'item_ids': item_ids,
                'balance_before': current_balance,
                'balance_after': new_balance,
            }
            self._add_event(
                'purchase', 'Shop purchase committed.',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='ok', details=dict(self.proto_state['last_purchase']),
            )
            print(
                f"  [SHOP] committed count={count} items={item_ids} "
                f"total={computed_total} balance={current_balance}->{new_balance}"
            )
            return self._build_post_load_0005_draft(
                state_value=new_balance, subtype=0x13, status=0
            )
        except (KeyError, TypeError, ValueError) as exc:
            if not save_attempted:
                self._record_mutation_transaction(
                    {
                        'kind': 'purchase',
                        'request_opcode': '0x0013',
                        'packet_seq': int(pkt_num),
                        'changed_fields': [],
                    },
                    'rejected', key=selected_key, reason=str(exc),
                )
            self.proto_state['last_purchase'] = {
                'status': 'rejected',
                'reason': str(exc),
                'balance_after': current_balance,
            }
            self._add_event(
                'purchase', 'Shop purchase rejected.',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn', details=dict(self.proto_state['last_purchase']),
            )
            print(f"  [SHOP] rejected: {exc}; balance={current_balance}")
            return self._build_post_load_0005_draft(
                state_value=current_balance, subtype=0x13, status=1
            )

    def _process_inventory_snapshot(self, opcode, payload, pkt_num=0):
        """Atomically replace the exact client quantity projection."""
        selected_key = None
        save_attempted = False
        try:
            selected_key = self._selected_character_state_key()
            if selected_key is None:
                raise ValueError('inventory snapshot requires selected character identity')
            projected = decode_c2s_inventory_snapshot(opcode, payload)
            state = self._load_canonical_character_state(key=selected_key)
            working = dict(state)
            working['inventory'] = {
                name: list(values)
                for name, values in (state.get('inventory') or {}).items()
            }
            changed_fields = []
            for inventory_name, values in projected.items():
                current = working['inventory'].get(inventory_name)
                if not isinstance(current, list) or len(current) != len(values):
                    raise ValueError(
                        f'canonical {inventory_name} inventory length mismatch'
                    )
                if current != values:
                    working['inventory'][inventory_name] = list(values)
                    changed_fields.append(f'inventory.{inventory_name}')

            correlation = None
            pending = self.proto_state.get('pending_item_action_0014')
            if opcode == 0x0008 and isinstance(pending, dict):
                item_id = int(pending.get('item_id', -1))
                if 1000 <= item_id <= 1032:
                    slot_index = item_id - 1000
                    before_inventory = state.get('inventory') or {}
                    before_food = before_inventory.get('food') or []
                    before_ingredients = before_inventory.get('ingredient') or [0, 0, 0]
                    food_quantity_before = (
                        int(before_food[slot_index])
                        if slot_index < len(before_food) else None
                    )
                    food_quantity_after = int(projected['food'][slot_index])
                    food_quantity_delta = food_quantity_after - food_quantity_before
                    correlation = {
                        'item_id': item_id,
                        'witness_packet_seq': pending.get('packet_seq'),
                        'snapshot_packet_seq': int(pkt_num),
                        'food_quantity_before': food_quantity_before,
                        'food_quantity_after': food_quantity_after,
                        # C2S 0x0014 is an action witness, not inherently a
                        # consume: ordinary feeding projects -1, whereas a
                        # successful foodmaker roll projects +1 for the
                        # newly crafted food in its following C2S 0x0008.
                        'food_quantity_delta': food_quantity_delta,
                        'action_projection': (
                            'consume' if food_quantity_delta < 0 else
                            'produce' if food_quantity_delta > 0 else
                            'unchanged'
                        ),
                        'ingredient_delta': [
                            int(projected['ingredient'][index])
                            - int(before_ingredients[index])
                            for index in range(3)
                        ],
                    }
                self.proto_state.pop('pending_item_action_0014', None)

            if changed_fields:
                save_attempted = True
                if not self._save_canonical_character_state(
                        working, key=selected_key,
                        mutation={
                            'kind': 'inventory_snapshot',
                            'request_opcode': f'0x{opcode:04X}',
                            'packet_seq': int(pkt_num),
                            'changed_fields': changed_fields,
                        }):
                    raise ValueError('canonical inventory snapshot persistence failed')
                status = 'committed'
            else:
                status = 'unchanged'
            result = {
                'status': status,
                'opcode': f'0x{opcode:04X}',
                'changed_fields': changed_fields,
                'correlated_0014': correlation,
            }
            self.proto_state['last_inventory_snapshot'] = result
            self._add_event(
                'inventory_snapshot',
                f'C2S 0x{opcode:04X} inventory projection {status}',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='ok', details=dict(result),
            )
            return None
        except (KeyError, TypeError, ValueError) as exc:
            if not save_attempted:
                self._record_mutation_transaction(
                    {
                        'kind': 'inventory_snapshot',
                        'request_opcode': f'0x{opcode:04X}',
                        'packet_seq': int(pkt_num),
                        'changed_fields': [],
                    },
                    'rejected', key=selected_key, reason=str(exc),
                )
            self.proto_state['last_inventory_snapshot'] = {
                'status': 'rejected',
                'opcode': f'0x{opcode:04X}',
                'reason': str(exc),
            }
            self._add_event(
                'inventory_snapshot_reject', str(exc),
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn',
                details=dict(self.proto_state['last_inventory_snapshot']),
            )
            return None

    def _process_growth_route_0010(self, payload, pkt_num=0):
        """Arm a proposal/completion witness; never mutate a stage alone."""
        try:
            selected_key = self._selected_character_state_key()
            if selected_key is None:
                raise ValueError('growth route requires selected character identity')
            aux, flag = decode_c2s_growth_route_0010(payload)
            state = self._load_canonical_character_state(key=selected_key)
            stage = int(self.proto_state.get('selected_evolution', 0))
            snapshot_hex = state.get('snapshot_hex')
            if isinstance(snapshot_hex, str):
                try:
                    snapshot = bytes.fromhex(snapshot_hex)
                    if len(snapshot) >= 6:
                        stage = int(snapshot[5])
                except ValueError:
                    pass
            if flag == 1:
                active = [row for row in (state.get('runtime_rows') or [])
                          if int(row.get('kind', 0xFF)) == 3]
                if len(active) != 1 or int(active[0].get('aux', -1)) != aux:
                    raise ValueError('growth completion has no matching active kind-3 row')
            pending = {
                'aux': aux,
                'flag': flag,
                'kind': 'proposal' if flag == 0 else 'completion_candidate',
                'packet_seq': int(pkt_num),
                'baseline_evolution': stage,
                'baseline_revision': int(state.get('revision', 0)),
                'selected_key': selected_key,
                'armed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            self.proto_state['pending_growth_route_0010'] = pending
            self.proto_state['last_growth_route_0010'] = dict(pending)
            self._add_event(
                'growth_route_edge',
                f'Growth route {pending["kind"]} aux={aux} armed',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='ok',
                details={key: value for key, value in pending.items() if key != 'selected_key'},
            )
            return None
        except (TypeError, ValueError) as exc:
            self.proto_state['last_growth_route_0010'] = {
                'status': 'rejected', 'reason': str(exc),
            }
            self._add_event(
                'growth_route_reject', str(exc),
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn',
                details=dict(self.proto_state['last_growth_route_0010']),
            )
            return None

    def _process_runtime_rows_0011(self, payload, pkt_num=0):
        """Persist the client row projection without trusting it for stage edges."""
        selected_key = None
        save_attempted = False
        try:
            selected_key = self._selected_character_state_key()
            if selected_key is None:
                raise ValueError('runtime rows require selected character identity')
            incoming = decode_c2s_runtime_rows_0011(payload)
            state = self._load_canonical_character_state(key=selected_key)
            current = [dict(row) for row in (state.get('runtime_rows') or [])]
            current_meta = [
                dict(meta) for meta in (state.get('runtime_row_meta') or [])
            ]
            if len(current) != 10 or len(current_meta) != 10:
                raise ValueError('canonical runtime-row projection is invalid')
            pending = self.proto_state.get('pending_growth_route_0010')
            if isinstance(pending, dict) and pending.get('selected_key') != selected_key:
                pending = None
            pending_reward = self.proto_state.get('pending_quest_reward_0012')
            if isinstance(pending_reward, dict):
                if pending_reward.get('selected_key') != selected_key:
                    pending_reward = None
                elif int(pkt_num) != int(pending_reward.get('packet_seq', -2)) + 1:
                    self.proto_state['invalidated_quest_reward_rows'] = [
                        (int(index), dict(current[int(index)]))
                        for index in pending_reward.get('candidate_rows', [])
                        if 0 <= int(index) < len(current)
                    ]
                    raise ValueError('0011 is not adjacent to the armed 0012 reward')

            snapshot_stage = int(self.proto_state.get('selected_evolution', 0))
            snapshot_hex = state.get('snapshot_hex')
            if isinstance(snapshot_hex, str):
                try:
                    snapshot = bytes.fromhex(snapshot_hex)
                    if len(snapshot) >= 6:
                        snapshot_stage = int(snapshot[5])
                except ValueError:
                    pass

            incoming_kind3 = next((
                index for index, row in enumerate(incoming)
                if int(row.get('kind', 0xFF)) == 3
            ), None)
            current_kind3 = next((
                index for index, row in enumerate(current)
                if int(row.get('kind', 0xFF)) == 3
            ), None)
            merged = [dict(row) for row in incoming]
            for index, row in self.proto_state.get('invalidated_quest_reward_rows', ()):
                retried_reward = (
                    pending_reward is not None
                    and index in pending_reward.get('candidate_rows', ())
                )
                if current[index] == row and incoming[index] != row and not retried_reward:
                    raise ValueError('0011 would retire a reward row after correlation was lost')

            # The client issues ordinary quests locally.  Accept their valid
            # projections, but never persist a row that its own issue paths
            # cannot produce.  Stage zero is reserved for the tutorial chain.
            tutorial_chain = (212, 202, 203, 227, 201)
            completed_aux = set()
            for completion in state.get('completed_runtime_rows') or ():
                if ':k5:a' in completion:
                    try:
                        completed_aux.add(int(completion.split(':k5:a', 1)[1].split(':', 1)[0]))
                    except ValueError:
                        pass
            expected_tutorial = next((aux for aux in tutorial_chain
                                      if aux not in completed_aux), None)
            final_reward = self.proto_state.get('last_quest_reward')
            local_final_growth = (
                pending is None and pending_reward is None
                and snapshot_stage == 0 and current_kind3 is None
                and expected_tutorial is None
                and isinstance(final_reward, dict)
                and final_reward.get('status') == 'committed'
                and final_reward.get('selected_key') == selected_key
                and int(final_reward.get('kind', -1)) == 5
                and int(final_reward.get('aux', -1)) == 201
                and int(final_reward.get('reward_packet_seq', -2)) + 1 == int(pkt_num)
                and sum(before != after for before, after in zip(current, incoming)) == 1
            )
            for index, (before, after) in enumerate(zip(current, incoming)):
                if before == after or int(after.get('kind', 0xFF)) == 0xFF:
                    continue
                kind = int(after['kind'])
                aux = int(after['aux'])
                if kind == 5:
                    if snapshot_stage != 0 or aux != expected_tutorial:
                        raise ValueError('0011 tutorial row violates the original chain')
                elif kind in (0, 1, 2):
                    if snapshot_stage == 0:
                        raise ValueError('0011 ordinary quest before evolution')
                    # FUN_005A5CF0 stores PackedDate_AddDeltaWithCarry(now,
                    # delta) for new rows.  A zero value cannot be produced
                    # by the normal date path; keep legacy active rows intact.
                    value = int(after['value'])
                    year = value // 1000000
                    month = (value // 10000) % 100
                    day = (value // 100) % 100
                    hour = value % 100
                    if not (1 <= year <= 99 and 1 <= month <= 12
                            and 1 <= day <= 31 and 0 <= hour <= 23):
                        raise ValueError('0011 ordinary quest has invalid packed date')
                    if kind in (0, 1) and quest_funcorn_reward_for_runtime_row(kind, aux) is None:
                        raise ValueError('0011 ordinary quest has unknown kind/aux')
                    if kind == 2 and not (
                        quest_funcorn_reward_for_runtime_row(kind, aux) is not None
                        or aux in (0xCF, 0xDC, 0xDD, 0xDE, 0xDF, 0xE0, 0xE1, 0xE2, 0x102)
                    ):
                        raise ValueError('0011 ordinary quest has unknown kind/aux')
                elif kind == 3:
                    if not (local_final_growth and aux == 0) and (
                        not pending or int(pending.get('flag', -1)) != 0
                        or aux != int(pending['aux'])
                    ):
                        raise ValueError('0011 kind-3 proposal lacks matching 0010')
                else:
                    raise ValueError('0011 contains an unknown quest kind')

            if pending and int(pending.get('flag', -1)) == 0:
                if incoming_kind3 is None or int(incoming[incoming_kind3]['aux']) != int(pending['aux']):
                    raise ValueError('0011 does not confirm the armed kind-3 proposal')
                if (
                    current_kind3 is not None
                    and int(current[current_kind3]['aux']) != int(pending['aux'])
                ):
                    raise ValueError('0011 proposal conflicts with server active kind-3 row')
            elif pending and int(pending.get('flag', -1)) == 1:
                if incoming_kind3 is not None and int(incoming[incoming_kind3]['aux']) == int(pending['aux']):
                    raise ValueError('0011 completion snapshot still contains completed kind-3 row')
                if snapshot_stage <= int(pending.get('baseline_evolution', snapshot_stage)):
                    # Natural order observed from an unmodified client is
                    # 0010 completion -> 0011 row removal -> 0007 stage edge.
                    # Keep the removal as a bounded witness instead of
                    # rejecting it merely because the stage snapshot follows.
                    buffered = {
                        'status': 'pending_0007',
                        'packet_seq': int(pkt_num),
                        'aux': int(pending['aux']),
                        'baseline_evolution': int(
                            pending.get('baseline_evolution', snapshot_stage)
                        ),
                        'selected_key': selected_key,
                        'rows': [dict(row) for row in incoming],
                    }
                    self.proto_state['pending_growth_completion_0011'] = buffered
                    self.proto_state['last_runtime_rows_0011'] = {
                        key: value for key, value in buffered.items()
                        if key not in {'selected_key', 'rows'}
                    }
                    self._add_event(
                        'runtime_row_snapshot',
                        'Kind-3 removal buffered until the following 0007 stage edge',
                        entity_id=self._entity_id_for_proto_state(self.proto_state),
                        severity='ok',
                        details=dict(self.proto_state['last_runtime_rows_0011']),
                    )
                    return None
                if (
                    current_kind3 is not None
                    and int(current[current_kind3]['aux']) == int(pending['aux'])
                ):
                    raise ValueError('server has not completed the armed kind-3 row')
                if current_kind3 is not None:
                    merged[current_kind3] = dict(current[current_kind3])
            elif current_kind3 is not None:
                merged = [dict(row) for row in incoming]
                for index, row in enumerate(merged):
                    if int(row.get('kind', 0xFF)) == 3:
                        merged[index] = {'kind': 0xFF, 'aux': 0xFF, 'value': 0}
                merged[current_kind3] = dict(current[current_kind3])

            # The native kind-5 tutorial uses a different wire order from the
            # verified food quest: it first publishes the retired row, then
            # sends 0012(amount, channel=2), then publishes the next tutorial
            # row.  Buffer the exact one-row retirement so the adjacent 0012
            # can commit row removal and FunCorn in one durable transaction.
            # Without this, the row is saved as empty before 0012 arrives and
            # the reward is rejected for having no active candidate.
            if not pending and not pending_reward:
                changed_indices = [
                    index for index, (before, after) in enumerate(zip(current, incoming))
                    if before != after
                ]
                if len(changed_indices) == 1:
                    tutorial_index = changed_indices[0]
                    tutorial_row = current[tutorial_index]
                    incoming_row = incoming[tutorial_index]
                    if (
                        int(tutorial_row.get('kind', 0xFF)) == 5
                        and int(incoming_row.get('kind', 0xFF)) == 0xFF
                        and quest_funcorn_reward_for_runtime_row(
                            tutorial_row.get('kind', 0xFF),
                            tutorial_row.get('aux', 0xFF),
                        ) is not None
                    ):
                        buffered = {
                            'status': 'pending_0012',
                            'packet_seq': int(pkt_num),
                            'selected_key': selected_key,
                            'row_index': tutorial_index,
                            'row': dict(tutorial_row),
                            'rows': [dict(row) for row in incoming],
                        }
                        self.proto_state['pending_tutorial_retire_0011'] = buffered
                        self.proto_state['last_runtime_rows_0011'] = {
                            key: value for key, value in buffered.items()
                            if key not in {'selected_key', 'rows'}
                        }
                        self._add_event(
                            'runtime_row_snapshot',
                            'Kind-5 retirement buffered until adjacent 0012 FunCorn reward',
                            entity_id=self._entity_id_for_proto_state(self.proto_state),
                            severity='ok',
                            details=dict(self.proto_state['last_runtime_rows_0011']),
                        )
                        return None

            reward_completion = None
            if pending_reward:
                changed_indices = [index for index, (before, after)
                                   in enumerate(zip(current, incoming)) if before != after]
                candidate_rows = [
                    int(index) for index in pending_reward.get('candidate_rows', [])
                    if 0 <= int(index) < len(current)
                ]
                retired = [
                    index for index in candidate_rows
                    if incoming[index] != current[index]
                ]
                if len(retired) != 1:
                    raise ValueError('0011 does not retire exactly one 0012 reward candidate')
                reward_index = retired[0]
                if changed_indices != [reward_index]:
                    raise ValueError('0011 reward projection changes unrelated rows')
                reward_row = current[reward_index]
                reward_kind = int(reward_row.get('kind', 0xFF))
                reward_aux = int(reward_row.get('aux', 0xFF))
                reward_amount = int(pending_reward['amount'])
                if quest_funcorn_reward_for_runtime_row(reward_kind, reward_aux) != reward_amount:
                    raise ValueError('0012 reward no longer matches the retired runtime row')
                if reward_kind != 5 and int(incoming[reward_index].get('kind', 0xFF)) != 0xFF:
                    raise ValueError('0011 reward row replacement is only valid for tutorial kind 5')
                if reward_kind == 5 and int(incoming[reward_index].get('kind', 0xFF)) != 0xFF:
                    raise ValueError('0011 tutorial reward must retire before next proposal')
                generation = max(
                    1, int(current_meta[reward_index].get('generation', 1))
                )
                completion_key = (
                    f'g{generation}:r{reward_index}:k{reward_kind}:'
                    f'a{reward_aux}:c{reward_amount}'
                )
                if completion_key in (state.get('completed_runtime_rows') or []):
                    raise ValueError('0012 reward completion was already committed')
                reward_completion = {
                    'key': completion_key,
                    'row_index': reward_index,
                    'generation': generation,
                    'kind': reward_kind,
                    'aux': reward_aux,
                    'funcorn_awarded': reward_amount,
                    'reward_packet_seq': int(pending_reward['packet_seq']),
                }

            merged_meta = [dict(meta) for meta in current_meta]
            for index, (before, after) in enumerate(zip(current, merged)):
                if before == after:
                    continue
                if int(after.get('kind', 0xFF)) == 0xFF:
                    merged_meta[index] = {
                        'generation': 0,
                        'issued_evolution': snapshot_stage if snapshot_stage in range(4) else 0,
                    }
                else:
                    merged_meta[index] = {
                        'generation': max(
                            1, int(current_meta[index].get('generation', 0)) + 1
                        ),
                        'issued_evolution': snapshot_stage if snapshot_stage in range(4) else 0,
                    }

            changed = merged != current or reward_completion is not None
            if changed:
                working = dict(state)
                working['runtime_rows'] = merged
                working['runtime_row_meta'] = merged_meta
                changed_fields = ['runtime_rows', 'runtime_row_meta']
                if reward_completion is not None:
                    currency_before = int(state.get('currency', 0))
                    currency_after = currency_before + int(
                        reward_completion['funcorn_awarded']
                    )
                    if currency_after > 0xFFFFFFFF:
                        raise ValueError('quest reward would overflow currency')
                    working['currency'] = currency_after
                    completed = list(state.get('completed_runtime_rows') or [])
                    completed.append(reward_completion['key'])
                    working['completed_runtime_rows'] = completed[-256:]
                    reward_completion['funcorn_before'] = currency_before
                    reward_completion['funcorn_after'] = currency_after
                    changed_fields.extend(['currency', 'completed_runtime_rows'])
                save_attempted = True
                if not self._save_canonical_character_state(
                        working, key=selected_key,
                        mutation={
                            'kind': (
                                'quest_reward_runtime_row_snapshot'
                                if reward_completion else 'runtime_row_snapshot'
                            ),
                            'request_opcode': '0x0011',
                            'packet_seq': int(pkt_num),
                            'changed_fields': changed_fields,
                            'correlated_0010_packet_seq': (
                                pending.get('packet_seq') if pending else None
                            ),
                            'correlated_0012_packet_seq': (
                                reward_completion.get('reward_packet_seq')
                                if reward_completion else None
                            ),
                        }):
                    raise ValueError('canonical runtime-row persistence failed')
            if pending:
                self.proto_state.pop('pending_growth_route_0010', None)
            if pending_reward:
                self.proto_state.pop('pending_quest_reward_0012', None)
                self.proto_state.pop('invalidated_quest_reward_rows', None)
            if reward_completion is not None:
                self.proto_state['server_currency'] = reward_completion['funcorn_after']
                self.proto_state['last_quest_reward'] = {
                    'status': 'committed',
                    'selected_key': selected_key,
                    'ack_opcode': '0x0005',
                    'ack_subtype': '0x12',
                    **reward_completion,
                }
            result = {
                'status': 'committed' if changed else 'unchanged',
                'packet_seq': int(pkt_num),
                'correlated_0010': bool(pending),
                'active_kind3_aux': next((
                    int(row['aux']) for row in merged if int(row['kind']) == 3
                ), None),
                'quest_reward': reward_completion,
            }
            self.proto_state['last_runtime_rows_0011'] = result
            self._add_event(
                'runtime_row_snapshot',
                f'Runtime-row projection {result["status"]}',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='ok', details=dict(result),
            )
            if reward_completion is not None:
                # HandleS2C_0005_PostLoadState has an exact subtype-0x12
                # branch that writes payload[2:6] through the same FunCorn
                # setter used by S2C 0007 +0x07. Subtype 0x13 is the shop
                # result path; 0x12 is the immediate FunCorn ACK contract.
                return self._make_packet(
                    0x0005,
                    self._build_post_load_0005_draft(
                        state_value=reward_completion['funcorn_after'],
                        subtype=0x12,
                        status=0,
                    ),
                )
            return None
        except (KeyError, TypeError, ValueError) as exc:
            self.proto_state.pop('pending_quest_reward_0012', None)
            if not save_attempted:
                self._record_mutation_transaction(
                    {
                        'kind': 'runtime_row_snapshot',
                        'request_opcode': '0x0011',
                        'packet_seq': int(pkt_num),
                        'changed_fields': [],
                    },
                    'rejected', key=selected_key, reason=str(exc),
                )
            self.proto_state['last_runtime_rows_0011'] = {
                'status': 'rejected', 'reason': str(exc),
            }
            self._add_event(
                'runtime_row_snapshot_reject', str(exc),
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn',
                details=dict(self.proto_state['last_runtime_rows_0011']),
            )
            return None

    def _process_quest_reward_0012(self, payload, pkt_num=0):
        """Arm an exact FunCorn credit; adjacent 0011 row removal commits it."""
        selected_key = None
        try:
            selected_key = self._selected_character_state_key()
            if selected_key is None:
                raise ValueError('quest reward requires selected character identity')
            amount, reward_channel = decode_c2s_quest_reward_0012(payload)
            state = self._load_canonical_character_state(key=selected_key)
            rows = state.get('runtime_rows') or []
            if len(rows) != 10:
                raise ValueError('canonical runtime-row projection is invalid')
            tutorial_chain = (212, 202, 203, 227, 201)
            completed_tutorial_aux = set()
            for completion in state.get('completed_runtime_rows') or ():
                if ':k5:a' in completion:
                    try:
                        completed_tutorial_aux.add(
                            int(completion.split(':k5:a', 1)[1].split(':', 1)[0])
                        )
                    except ValueError:
                        pass
            expected_tutorial = next((aux for aux in tutorial_chain
                                      if aux not in completed_tutorial_aux), None)

            preceding_retire = self.proto_state.get('pending_tutorial_retire_0011')
            if isinstance(preceding_retire, dict):
                if preceding_retire.get('selected_key') != selected_key:
                    raise ValueError('preceding tutorial retirement belongs to another character')
                if int(pkt_num) != int(preceding_retire.get('packet_seq', -2)) + 1:
                    raise ValueError('0012 is not adjacent to the preceding tutorial retirement')
                row_index = int(preceding_retire.get('row_index', -1))
                if not 0 <= row_index < len(rows):
                    raise ValueError('preceding tutorial retirement row index is invalid')
                reward_row = dict(preceding_retire.get('row') or {})
                if rows[row_index] != reward_row:
                    raise ValueError('preceding tutorial retirement no longer matches canonical row')
                if int(reward_row.get('kind', 0xFF)) != 5:
                    raise ValueError('preceding reward order is only valid for tutorial kind 5')
                if int(reward_row.get('aux', -1)) != expected_tutorial:
                    raise ValueError('tutorial reward violates the durable chain')
                if quest_funcorn_reward_for_runtime_row(
                        reward_row.get('kind', 0xFF),
                        reward_row.get('aux', 0xFF)) != amount:
                    raise ValueError('0012 does not match the preceding tutorial retirement')
                incoming_rows = [
                    dict(row) for row in preceding_retire.get('rows', [])
                ]
                if len(incoming_rows) != 10 or int(
                        incoming_rows[row_index].get('kind', 0xFF)) != 0xFF:
                    raise ValueError('preceding tutorial retirement projection is invalid')
                meta = [dict(entry) for entry in (state.get('runtime_row_meta') or [])]
                if len(meta) != 10:
                    raise ValueError('canonical runtime-row metadata is invalid')
                generation = max(1, int(meta[row_index].get('generation', 1)))
                completion_key = (
                    f'g{generation}:r{row_index}:k5:'
                    f'a{int(reward_row.get("aux", 0xFF))}:c{amount}'
                )
                if completion_key in (state.get('completed_runtime_rows') or []):
                    raise ValueError('tutorial reward completion was already committed')
                currency_before = int(state.get('currency', 0))
                currency_after = currency_before + amount
                if currency_after > 0xFFFFFFFF:
                    raise ValueError('quest reward would overflow currency')
                meta[row_index] = {
                    'generation': 0,
                    'issued_evolution': int(
                        self.proto_state.get('selected_evolution', 0)
                    ) & 0x03,
                }
                working = dict(state)
                working['runtime_rows'] = incoming_rows
                working['runtime_row_meta'] = meta
                working['currency'] = currency_after
                completed = list(state.get('completed_runtime_rows') or [])
                completed.append(completion_key)
                working['completed_runtime_rows'] = completed[-256:]
                if not self._save_canonical_character_state(
                        working, key=selected_key,
                        mutation={
                            'kind': 'tutorial_reward_preceding_row_snapshot',
                            'request_opcode': '0x0012',
                            'packet_seq': int(pkt_num),
                            'correlated_0011_packet_seq': int(
                                preceding_retire['packet_seq']
                            ),
                            'changed_fields': [
                                'runtime_rows', 'runtime_row_meta', 'currency',
                                'completed_runtime_rows',
                            ],
                        }):
                    raise ValueError('tutorial reward persistence failed')
                self.proto_state.pop('pending_tutorial_retire_0011', None)
                self.proto_state['server_currency'] = currency_after
                self.proto_state['last_quest_reward'] = {
                    'status': 'committed',
                    'selected_key': selected_key,
                    'ack_opcode': '0x0005',
                    'ack_subtype': '0x12',
                    'key': completion_key,
                    'row_index': row_index,
                    'generation': generation,
                    'kind': 5,
                    'aux': int(reward_row.get('aux', 0xFF)),
                    'funcorn_awarded': amount,
                    'funcorn_before': currency_before,
                    'funcorn_after': currency_after,
                    'reward_packet_seq': int(pkt_num),
                }
                self._add_event(
                    'quest_reward_commit',
                    f'Tutorial FunCorn reward committed: {currency_before}->{currency_after}',
                    entity_id=self._entity_id_for_proto_state(self.proto_state),
                    severity='ok',
                    details=dict(self.proto_state['last_quest_reward']),
                )
                return self._make_packet(
                    0x0005,
                    self._build_post_load_0005_draft(
                        state_value=currency_after, subtype=0x12, status=0
                    ),
                )
            candidates = [
                index for index, row in enumerate(rows)
                if quest_funcorn_reward_for_runtime_row(
                    row.get('kind', 0xFF), row.get('aux', 0xFF)
                ) == amount
                and (int(row.get('kind', 0xFF)) != 5
                     or int(row.get('aux', -1)) == expected_tutorial)
            ]

            # A food wish has a stronger action witness: the immediately prior
            # 0014->0008 quantity edge identifies the exact aux/item id.
            inventory_edge = self.proto_state.get('last_inventory_snapshot')
            correlation = (
                inventory_edge.get('correlated_0014')
                if isinstance(inventory_edge, dict) else None
            )
            if isinstance(correlation, dict):
                snapshot_seq = int(correlation.get('snapshot_packet_seq', -2))
                item_id = int(correlation.get('item_id', -1))
                if (
                    int(pkt_num) == snapshot_seq + 1
                    and int(correlation.get('food_quantity_before', 0))
                    == int(correlation.get('food_quantity_after', 0)) + 1
                ):
                    candidates = [
                        index for index in candidates
                        if int(rows[index].get('kind', 0xFF)) == 0
                        and int(rows[index].get('aux', 0xFF)) == item_id
                    ]
            if not candidates:
                raise ValueError('0012 has no active runtime row with the exact reward')
            pending = {
                'status': 'pending_0011',
                'amount': amount,
                'reward_channel': reward_channel,
                'candidate_rows': candidates,
                'packet_seq': int(pkt_num),
                'selected_key': selected_key,
            }
            self.proto_state['pending_quest_reward_0012'] = pending
            self.proto_state['last_quest_reward'] = {
                key: value for key, value in pending.items() if key != 'selected_key'
            }
            self._add_event(
                'quest_reward_pending',
                f'Quest corn reward {amount} waiting for adjacent 0011 row removal',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='ok', details=dict(self.proto_state['last_quest_reward']),
            )
            return None
        except (KeyError, TypeError, ValueError) as exc:
            self.proto_state.pop('pending_quest_reward_0012', None)
            self.proto_state.pop('pending_tutorial_retire_0011', None)
            self._record_mutation_transaction(
                {
                    'kind': 'quest_reward',
                    'request_opcode': '0x0012',
                    'packet_seq': int(pkt_num),
                    'changed_fields': [],
                },
                'rejected', key=selected_key, reason=str(exc),
            )
            self.proto_state['last_quest_reward'] = {
                'status': 'rejected', 'reason': str(exc),
            }
            self._add_event(
                'quest_reward_reject', str(exc),
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn', details=dict(self.proto_state['last_quest_reward']),
            )
            return None

    def _process_item_consume_0014(self, payload, pkt_num=0):
        """Treat food as a 0008-correlated action witness; decrement medicine."""
        selected_key = None
        save_attempted = False
        item_id = None
        try:
            selected_key = self._selected_character_state_key()
            if selected_key is None:
                raise ValueError('item consume requires selected character identity')
            item_id = decode_c2s_item_consume_0014(payload)
            slot = self._inventory_slot_for_item(item_id)
            if slot is None:
                raise ValueError(f'unknown inventory item id {item_id}')
            inventory_name, slot_index = slot
            if inventory_name not in ('food', 'drug'):
                raise ValueError(
                    'C2S 0x0014 permits food witnesses or medicine 4000..4005 only'
                )
            state = self._load_canonical_character_state(key=selected_key)
            quantities = (state.get('inventory') or {}).get(inventory_name)
            if not isinstance(quantities, list) or slot_index >= len(quantities):
                raise ValueError(f'invalid canonical inventory slot for item {item_id}')
            quantity_before = int(quantities[slot_index])
            # Food 0x0014 is emitted for both a feed (existing count must
            # decrease) and a successful recipe result (a previously empty
            # food slot must increase in the following authoritative 0008).
            # The snapshot decides the operation.  Medicines remain a direct
            # server-owned decrement and therefore require ownership here.
            if inventory_name == 'drug' and quantity_before <= 0:
                raise ValueError(f'cannot consume unowned item {item_id}')

            if inventory_name == 'food':
                witness = {
                    'status': 'witness_pending_0008',
                    'item_id': item_id,
                    'inventory': inventory_name,
                    'slot': slot_index,
                    'quantity_before': quantity_before,
                    'packet_seq': int(pkt_num),
                }
                self.proto_state['pending_item_action_0014'] = dict(witness)
                self.proto_state['last_item_consume'] = dict(witness)
                self._add_event(
                    'item_action_witness',
                    f'food action {item_id} waiting for authoritative 0008 snapshot',
                    entity_id=self._entity_id_for_proto_state(self.proto_state),
                    severity='ok', details=dict(witness),
                )
                return None

            working = dict(state)
            working['inventory'] = {
                name: list(values)
                for name, values in (state.get('inventory') or {}).items()
            }
            working['inventory'][inventory_name][slot_index] = quantity_before - 1
            save_attempted = True
            if not self._save_canonical_character_state(
                    working, key=selected_key,
                    mutation={
                        'kind': 'medicine_consume',
                        'request_opcode': '0x0014',
                        'packet_seq': int(pkt_num),
                        'changed_fields': [
                            f'inventory.{inventory_name}[{slot_index}]'
                        ],
                        'item_id': item_id,
                    }):
                raise ValueError('canonical state persistence failed')
            self.proto_state['last_item_consume'] = {
                'status': 'committed_medicine_delta',
                'item_id': item_id,
                'inventory': inventory_name,
                'slot': slot_index,
                'quantity_before': quantity_before,
                'quantity_after': quantity_before - 1,
            }
            self._add_event(
                'medicine_consume', f'medicine item {item_id} consumed',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='ok', details=dict(self.proto_state['last_item_consume']),
            )
            return None
        except (KeyError, TypeError, ValueError) as exc:
            if not save_attempted:
                self._record_mutation_transaction(
                    {
                        'kind': 'medicine_consume_or_action_witness',
                        'request_opcode': '0x0014',
                        'packet_seq': int(pkt_num),
                        'changed_fields': [],
                        'item_id': item_id,
                    },
                    'rejected', key=selected_key, reason=str(exc),
                )
            self.proto_state['last_item_consume'] = {
                'status': 'rejected',
                'item_id': item_id,
                'reason': str(exc),
            }
            self._add_event(
                'item_consume_reject', str(exc),
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn', details=dict(self.proto_state['last_item_consume']),
            )
            return None

    def _process_item_use(self, opcode, payload, pkt_num=0):
        """Persist exact loadout reports or commit one energy consumption.

        Toy/gym packets are complete active-slot snapshots and never consume
        ownership.  Energy remains pending in the client until the exact
        successful S2C 0x0009 ``00 0F`` acknowledgment arrives, so only emit
        that packet after the canonical decrement is durable.
        """
        selected_key = None
        save_attempted = False
        try:
            selected_key = self._selected_character_state_key()
            if selected_key is None:
                raise ValueError('item use requires selected character identity')
            inventory_name, indices = decode_c2s_item_use(opcode, payload)
            state = self._load_canonical_character_state(key=selected_key)
            inventory = (state.get('inventory') or {}).get(inventory_name)
            if not isinstance(inventory, list):
                raise ValueError(f'missing canonical {inventory_name} inventory')
            if opcode == 0x000D:
                guaranteed = indices[:3]
                tail = indices[3]
                if (
                    tail < len(inventory)
                    and tail > guaranteed[-1]
                    and int(inventory[tail]) > 0
                ):
                    indices = guaranteed + [tail]
                else:
                    indices = guaranteed
            if any(index >= len(inventory) or int(inventory[index]) <= 0
                   for index in indices):
                raise ValueError(
                    f'C2S 0x{opcode:04X} references an unowned item slot'
                )

            working = dict(state)
            working['inventory'] = {
                name: list(values)
                for name, values in (state.get('inventory') or {}).items()
            }
            working['active_loadouts'] = {
                name: list(values)
                for name, values in (state.get('active_loadouts') or {}).items()
            }
            if opcode in (0x000D, 0x000E):
                working['active_loadouts'][inventory_name] = list(indices)
                action = 'loadout_saved'
            else:
                index = indices[0]
                working['inventory']['energy'][index] -= 1
                action = 'energy_consumed'

            save_attempted = True
            if not self._save_canonical_character_state(
                    working, key=selected_key,
                    mutation={
                        'kind': 'energy_consume' if opcode == 0x000F else 'active_loadout',
                        'request_opcode': f'0x{opcode:04X}',
                        'packet_seq': int(pkt_num),
                        'changed_fields': (
                            [f'inventory.energy[{indices[0]}]']
                            if opcode == 0x000F else
                            [f'active_loadouts.{inventory_name}']
                        ),
                    }):
                raise ValueError('canonical state persistence failed')
            self.proto_state['last_item_use'] = {
                'status': 'committed',
                'opcode': f'0x{opcode:04X}',
                'inventory': inventory_name,
                'indices': list(indices),
                'action': action,
            }
            self._add_event(
                'item_use', f'{inventory_name} {action}',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='ok', details=dict(self.proto_state['last_item_use']),
            )
            if opcode == 0x000F:
                return self._make_packet(0x0009, b'\x00\x0F')
            return None
        except (KeyError, TypeError, ValueError) as exc:
            if not save_attempted:
                self._record_mutation_transaction(
                    {
                        'kind': 'energy_consume' if opcode == 0x000F else 'active_loadout',
                        'request_opcode': f'0x{opcode:04X}',
                        'packet_seq': int(pkt_num),
                        'changed_fields': [],
                    },
                    'rejected', key=selected_key, reason=str(exc),
                )
            self.proto_state['last_item_use'] = {
                'status': 'rejected',
                'opcode': f'0x{opcode:04X}',
                'reason': str(exc),
            }
            self._add_event(
                'item_use_reject', str(exc),
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn', details=dict(self.proto_state['last_item_use']),
            )
            # The failure payload semantics are not captured.  Do not invent
            # an ACK that might consume or retain the client's pending item.
            return None

    def _load_character_state_snapshot(self):
        """Load one canonical 0xC4-byte C2S 0x0007 state snapshot."""
        key = self._selected_character_state_key()
        if key is None:
            # Bootstrap requests may arrive before a character is selected.
            # They may receive profile defaults, but must never import the
            # legacy Player raw mirror or create/read a Player canonical.
            self.proto_state['saved_state_loaded'] = False
            self.proto_state['saved_state_key'] = None
            self.proto_state['persisted_evolution'] = None
            return None
        # A successful C2S 0x0004 creates a brand-new account-scoped
        # canonical before its first S2C 0x0007 is built.  Do not let that
        # first bootstrap import an older raw snapshot merely because another
        # account once used the same character name (the legacy raw key has no
        # account or slot component).  Existing characters still retain the
        # one-time compatibility import below.
        if self.proto_state.get('fresh_character_create_in_progress'):
            self.proto_state['saved_state_loaded'] = False
            self.proto_state['saved_state_key'] = key
            self.proto_state['persisted_evolution'] = None
            self.proto_state['legacy_state_import_suppressed'] = True
            return None
        cached = self.saved_character_states.get(key)
        if cached is not None:
            self.proto_state['saved_state_loaded'] = True
            self.proto_state['saved_state_key'] = key
            self.proto_state['persisted_evolution'] = cached[0x05]
            return cached

        canonical = self._load_canonical_character_state(key=key)
        canonical_hex = canonical.get('snapshot_hex')
        if isinstance(canonical_hex, str):
            try:
                snapshot = bytes.fromhex(canonical_hex)
            except ValueError:
                snapshot = b''
            if len(snapshot) == 0xC4:
                snapshot, sanitized = self._sanitize_c2s_mode_pairs(snapshot)
                if sanitized:
                    self.proto_state['legacy_mode_pair_sanitized'] = True
                self.saved_character_states[key] = snapshot
                self.proto_state['saved_state_loaded'] = True
                self.proto_state['saved_state_key'] = key
                self.proto_state['persisted_evolution'] = snapshot[0x05]
                return snapshot
        path = self._character_state_path(key)
        try:
            with open(path, 'rb') as f:
                snapshot = f.read(0xC5)
        except FileNotFoundError:
            # One-time compatibility import from the old character-name-only
            # key.  It keeps existing single-player progression when the new
            # account/slot identity first becomes available.
            legacy_key = self._legacy_character_state_key()
            legacy_path = self._character_state_path(legacy_key)
            if legacy_path == path:
                self.proto_state['saved_state_loaded'] = False
                self.proto_state['saved_state_key'] = key
                self.proto_state['persisted_evolution'] = None
                return None
            try:
                with open(legacy_path, 'rb') as legacy_file:
                    snapshot = legacy_file.read(0xC5)
                self.proto_state['legacy_state_migrated_from'] = legacy_key
            except FileNotFoundError:
                self.proto_state['saved_state_loaded'] = False
                self.proto_state['saved_state_key'] = key
                self.proto_state['persisted_evolution'] = None
                return None
            except OSError as exc:
                print(f"  [STATE] Failed to load {legacy_path}: {exc}")
                return None
        except OSError as exc:
            print(f"  [STATE] Failed to load {path}: {exc}")
            return None
        if len(snapshot) != 0xC4:
            print(f"  [STATE] Ignoring invalid snapshot {path}: {len(snapshot)}B (expected 196B)")
            return None
        snapshot, sanitized = self._sanitize_c2s_mode_pairs(snapshot)
        if sanitized:
            self.proto_state['legacy_mode_pair_sanitized'] = True
        # A canonical JSON written before directional snapshots were folded
        # into it can coexist with the older name-only 196-byte save.  The
        # canonical loader runs before this compatibility fallback, so it
        # cannot infer the already-persisted evolution stage by itself.  Fold
        # the imported snapshot into that same canonical document now and
        # advance the single active kind-3 route to the stage implied by the
        # imported character.  Otherwise a stage-1 RedRon reconnects with the
        # impossible stage-0 aux=0 route even though its model is restored as
        # stage 1.
        if not isinstance(canonical.get('snapshot_hex'), str):
            migrated = dict(canonical)
            migrated['inventory'] = {
                name: list(values)
                for name, values in (canonical.get('inventory') or {}).items()
            }
            migrated['runtime_rows'] = [
                dict(row) for row in (canonical.get('runtime_rows') or [])
            ]
            migrated['runtime_row_meta'] = [
                dict(meta) for meta in (canonical.get('runtime_row_meta') or [])
            ]
            migrated['completed_runtime_rows'] = list(
                canonical.get('completed_runtime_rows') or []
            )
            stage = snapshot[0x05]
            active_kind3 = next((
                idx for idx, row in enumerate(migrated['runtime_rows'])
                if int(row.get('kind', 0xFF)) == 3
            ), None)
            if stage in (0, 1, 2, 3):
                if stage == 3:
                    if active_kind3 is not None:
                        migrated['runtime_rows'][active_kind3] = {
                            'kind': 0xFF, 'aux': 0xFF, 'value': 0,
                        }
                else:
                    desired_aux = (
                        0 if stage == 0 else
                        EVOLUTION_AUX_STAGE1 if stage == 1 else
                        EVOLUTION_AUX_STAGE2
                    )
                    if active_kind3 is None:
                        active_kind3 = next((
                            idx for idx, row in enumerate(migrated['runtime_rows'])
                            if int(row.get('kind', 0xFF)) == 0xFF
                        ), None)
                    if active_kind3 is not None:
                        migrated['runtime_rows'][active_kind3] = {
                            'kind': 3, 'aux': desired_aux, 'value': 0,
                        }
                        migrated['runtime_row_meta'][active_kind3] = {
                            'generation': stage + 1,
                            'issued_evolution': stage,
                        }
            migrated['snapshot_hex'] = snapshot.hex()
            if self._save_canonical_character_state(
                    migrated,
                    mutation={
                        'kind': 'legacy_snapshot_migration',
                        'changed_fields': [
                            'snapshot_hex', 'runtime_rows', 'runtime_row_meta'
                        ],
                    }):
                canonical = migrated
                self.proto_state['legacy_snapshot_folded_into_canonical'] = True
        self.saved_character_states[key] = snapshot
        self.proto_state['saved_state_loaded'] = True
        self.proto_state['saved_state_key'] = key
        self.proto_state['persisted_evolution'] = snapshot[0x05]
        return snapshot

    def _save_character_state_snapshot(self, client_payload):
        """Atomically persist a merged C2S 0x0007 property snapshot.

        Runtime A/B proved that stat 55/56 do not round-trip through the
        196-byte periodic snapshot: the same client reports them as 1/2 via
        C2S 0x0017, then writes 0/0 into C2S 0x0007.  Treat those two 0x0017
        deltas as the per-field authority so a later periodic save cannot
        erase the pet-evolution/species properties on reconnect.
        """
        selected_key = self._selected_character_state_key()
        if selected_key is None:
            self.proto_state['last_state_save_reject'] = {
                'reason': 'state save requires selected character identity',
            }
            self._add_event(
                'state_save_reject',
                'Rejected state snapshot without a selected character identity.',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn',
                details=dict(self.proto_state['last_state_save_reject']),
            )
            self._record_mutation_transaction(
                {
                    'kind': 'state_snapshot',
                    'request_opcode': '0x0007',
                    'changed_fields': [],
                },
                'rejected', key=None,
                reason=self.proto_state['last_state_save_reject']['reason'],
            )
            return False
        if len(client_payload) < 0xC4:
            self._record_mutation_transaction(
                {
                    'kind': 'state_snapshot',
                    'request_opcode': '0x0007',
                    'changed_fields': [],
                },
                'rejected', key=selected_key,
                reason=f'state snapshot is {len(client_payload)}B; expected at least 196B',
            )
            return False
        snapshot = bytearray(client_payload[:0xC4])
        key = selected_key

        stat_authority = self.proto_state.get('c2s_0017_stat_authority') or {}
        if self.proto_state.get('c2s_0017_authority_key') != key:
            stat_authority = {}
        merged_ids = []
        previous = self.saved_character_states.get(key)
        for stat_id in (0x37, 0x38):
            if stat_id in stat_authority:
                value = int(stat_authority[stat_id]) & 0xFFFF
            elif previous is not None and len(previous) >= 0xC4:
                value = struct.unpack_from('<H', previous, 0x0A + stat_id * 2)[0]
            elif CONTENT_PROFILE in {'shipped', 'playable'}:
                profile_stats = SHIPPED_CONTENT_STATS
                if CONTENT_PROFILE == 'playable':
                    profile_stats = _build_original_fresh_content_stats(
                        self.proto_state.get('char_type', AZRON_SPECIES),
                        _fresh_content_seed_material(self.proto_state),
                    )
                value = int(profile_stats[stat_id]) & 0xFFFF
            else:
                value = struct.unpack_from('<H', snapshot, 0x0A + stat_id * 2)[0]
            self._pack_u16(snapshot, 0x0A + stat_id * 2, value)
            merged_ids.append(stat_id)

        # +0x96 covers the persisted progression subtotal for stats 0x1E..0x41.
        # Recompute it after the authoritative-field merge instead of retaining
        # the client's subtotal for the pre-merge zero values.
        merged_stats = struct.unpack_from('<70H', snapshot, 0x0A)
        self._pack_u32(snapshot, 0x96, sum(merged_stats[0x1E:0x42]) & 0xFFFFFFFF)
        snapshot, sanitized = self._sanitize_c2s_mode_pairs(snapshot)
        if sanitized:
            self.proto_state['last_mode_pair_sanitized'] = True
        canonical = self._load_canonical_character_state(key=key)
        previous_snapshot = previous
        if previous_snapshot is None and isinstance(canonical.get('snapshot_hex'), str):
            try:
                candidate = bytes.fromhex(canonical['snapshot_hex'])
                previous_snapshot = candidate if len(candidate) == 0xC4 else None
            except ValueError:
                previous_snapshot = None
        working = dict(canonical)
        working['inventory'] = {
            name: list(values)
            for name, values in (canonical.get('inventory') or {}).items()
        }
        working['runtime_rows'] = [
            dict(row) for row in (canonical.get('runtime_rows') or [])
        ]
        working['runtime_row_meta'] = [
            dict(meta) for meta in (canonical.get('runtime_row_meta') or [])
        ]
        working['completed_runtime_rows'] = list(
            canonical.get('completed_runtime_rows') or []
        )
        completion = self._complete_runtime_row_from_snapshot(
            working, previous_snapshot, bytes(snapshot)
        )
        if previous_snapshot is not None and len(previous_snapshot) >= 0xC4:
            previous_stage = previous_snapshot[0x05]
        else:
            active_index = next((
                idx for idx, row in enumerate(working.get('runtime_rows') or [])
                if int(row.get('kind', 0xFF)) == 3
            ), None)
            if active_index is not None:
                previous_stage = int(
                    working['runtime_row_meta'][active_index].get(
                        'issued_evolution', -1
                    )
                )
            else:
                previous_stage = int(
                    self.proto_state.get('selected_evolution', -1)
                )
        submitted_stage = snapshot[0x05]
        stage_edge_valid = (
            previous_stage in range(4)
            and submitted_stage in range(4)
            and submitted_stage >= previous_stage
            and submitted_stage - previous_stage <= 1
            and (submitted_stage == previous_stage or completion is not None)
        )
        if not stage_edge_valid:
            self.proto_state['last_state_save_reject'] = {
                'reason': 'unverified evolution edge',
                'previous_evolution': previous_stage,
                'submitted_evolution': submitted_stage,
            }
            self._add_event(
                'state_save_reject',
                'Rejected non-monotonic or unverified evolution snapshot.',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn',
                details=dict(self.proto_state['last_state_save_reject']),
            )
            self._record_mutation_transaction(
                {
                    'kind': 'state_snapshot',
                    'request_opcode': '0x0007',
                    'changed_fields': [],
                },
                'rejected', key=key,
                reason=self.proto_state['last_state_save_reject']['reason'],
                revision_before=canonical.get('revision'),
            )
            return False
        working['snapshot_hex'] = snapshot.hex()
        if not self._save_canonical_character_state(
                working, key=key,
                mutation={
                    'kind': 'state_snapshot',
                    'request_opcode': '0x0007',
                    'changed_fields': [
                        'snapshot_hex', 'runtime_rows', 'runtime_row_meta',
                        'completed_runtime_rows',
                    ],
                }):
            return False

        # Canonical JSON is authoritative.  Commit it before touching the
        # legacy raw mirror so a canonical failure cannot leave the mirror or
        # in-memory snapshot one generation ahead.  The mirror remains best-
        # effort compatibility data after a durable canonical commit.
        self.saved_character_states[key] = bytes(snapshot)
        self.proto_state['saved_state_loaded'] = True
        self.proto_state['saved_state_key'] = key
        self.proto_state['persisted_evolution'] = snapshot[0x05]
        self.proto_state['last_content_save_payload'] = snapshot.hex()
        self.proto_state['last_content_save_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.proto_state['last_content_save_merged_stat_ids'] = merged_ids
        path = self._character_state_path(key)
        tmp_path = path + '.tmp'
        raw_mirror_saved = False
        try:
            with open(tmp_path, 'wb') as f:
                f.write(snapshot)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            raw_mirror_saved = True
        except OSError as exc:
            print(f"  [STATE] Canonical saved; legacy mirror failed {path}: {exc}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            self._add_event(
                'state_mirror_warning',
                'Canonical state committed but legacy raw mirror failed.',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='warn', details={'path': path, 'error': str(exc)},
            )
        self.proto_state['legacy_raw_mirror_saved'] = raw_mirror_saved
        if completion is not None:
            buffered_growth = self.proto_state.get(
                'pending_growth_completion_0011'
            )
            pending_growth = self.proto_state.get('pending_growth_route_0010')
            if (
                isinstance(buffered_growth, dict)
                and buffered_growth.get('selected_key') == key
                and int(buffered_growth.get('aux', -1))
                    == int(completion.get('aux', -2))
                and int(buffered_growth.get('baseline_evolution', -1))
                    == int(completion.get('evolution_before', -2))
            ):
                completion['correlated_0011_packet_seq'] = int(
                    buffered_growth.get('packet_seq', -1)
                )
                self.proto_state.pop('pending_growth_completion_0011', None)
                if isinstance(pending_growth, dict):
                    self.proto_state.pop('pending_growth_route_0010', None)
            self.proto_state['last_runtime_row_completion'] = completion
            self._add_event(
                'runtime_row_complete',
                'Verified kind-3 evolution row completed; no currency awarded.',
                entity_id=self._entity_id_for_proto_state(self.proto_state),
                severity='ok', details=dict(completion),
            )
            print(
                f"  [QUEST] completed {completion['key']} "
                f"evolution={completion['evolution_before']}->"
                f"{completion['evolution_after']} currency=0"
            )
        return True

    def _apply_saved_character_state(self, zone_payload):
        """Map the proven C2S save fields into the S2C 0x0007 state blob."""
        snapshot = self._load_character_state_snapshot()
        if snapshot is None:
            return False

        # The periodic C2S snapshot stores the live evolution stage at +0x05,
        # while the directional S2C bootstrap exposes that same stage at
        # +0x02.  Leaving the fresh-profile value in place made a persisted
        # stage-1 character reconnect as stage 0 even though the save and the
        # control API both correctly reported persisted_evolution=1.
        saved_stage = snapshot[0x05]
        zone_payload[0x02] = saved_stage if saved_stage <= 3 else 0

        # C2S +0x0A holds the same 70 u16 progression stats that S2C exposes
        # at +0x0B.  Gym dumbbells F8/F9/FA all update stat index 0x20.
        for idx in range(0x46):
            value = struct.unpack_from('<H', snapshot, 0x0A + idx * 2)[0]
            self._pack_u16(zone_payload, 0x0B + idx * 2, value)

        # The C2S tail has eight one-byte modes followed by eight dwords.  It
        # maps directly to the S2C +0x184/+0x18C tuple table consumed by
        # FUN_005AA6F0.
        zone_payload[0x184:0x18C] = snapshot[0x9C:0xA4]
        for idx in range(8):
            value = struct.unpack_from('<I', snapshot, 0xA4 + idx * 4)[0]
            self._pack_u32(zone_payload, 0x18C + idx * 4, value)
        return True

    def _apply_canonical_server_state(self, zone_payload):
        """Overlay server-owned state, including appearance, onto S2C 0x0007."""
        selected_key = self._selected_character_state_key()
        if selected_key is None:
            return False
        state = self._load_canonical_character_state(key=selected_key)
        inventory = state.get('inventory') or {}
        for name, offset, size in INVENTORY_0007_FIELDS:
            values = inventory.get(name)
            if not isinstance(values, list) or len(values) != size:
                continue
            zone_payload[offset:offset + size] = bytes(
                max(0, min(0xFF, int(value))) for value in values
            )

        rows = state.get('runtime_rows') or []
        if len(rows) == 10:
            for idx, row in enumerate(rows):
                self._pack_u16(zone_payload, 0x134 + idx * 2, row.get('kind', 0xFF))
                self._pack_u16(zone_payload, 0x148 + idx * 2, row.get('aux', 0xFF))
                self._pack_u32(zone_payload, 0x15C + idx * 4, row.get('value', 0))
        currency = max(0, min(0xFFFFFFFF, int(state.get('currency', 0))))
        self._pack_u32(zone_payload, 0x07, currency)
        accessory_slots = normalize_accessory_slots(state.get('accessory_slots'))
        if accessory_slots is None:
            accessory_slots = list(DEFAULT_ACCESSORY_SLOTS)
        zone_payload[0x1D4:0x1D8] = bytes(accessory_slots)
        self.proto_state['server_currency'] = currency
        return True

    def _build_zone_0007_draft(self, client_payload):
        """
        Server->client opcode 0x0007 draft.

        Ghidra notes:
        - handler: 0x59E330
        - minimum payload touched: 0x1D8 bytes
        - fields consumed before the handler starts mutating its scratch area:
          +0x00: u8
          +0x01: u8
          +0x02: u8
          +0x03: u32
          +0x07: u32
          +0x0B: 0x46 * u16
          +0x97: 0x21 bytes
          +0xB8: 0x0F bytes
          +0xC7: 0x14 bytes
          +0xEA: 0x26 bytes
          +0x110: 0x03 bytes
          +0x113: 0x0A bytes
          +0x11D: 0x08 bytes
          +0x125: 0x0B bytes
          +0x131: 0x01 byte
          +0x134: 10 * u16
          +0x148: 10 * u16
          +0x15C: 10 * u32
          +0x184: 8 * u8 mode states
          +0x18C: 8 * u32
        """
        payload = bytearray(ZONE_0007_SIZE)

        # C2S 0x0007 is a 196-byte directional snapshot with a different wire
        # layout.  Never copy its prefix into this 472-byte S2C state blob:
        # C2S checksum/mode/timestamp bytes overlap S2C inventory quantities.
        # Only _apply_saved_character_state() below restores the stat and tuple
        # ranges whose directional mappings have been proven independently.

        # Conservative defaults that avoid obviously-invalid empty state while
        # still preserving meaningful local bootstrap selectors. 0x0007 byte1
        # and byte2 are later read by FUN_006130B0 through FUN_00545500 /
        # FUN_005465C0 and become the self model selector bytes +0x9D/+0xA1.
        # Byte1 should therefore follow the selected Azron type instead of
        # blindly mirroring the client's zero-filled request field.
        proto_state = getattr(self, 'proto_state', {})
        char_type = int(proto_state.get('char_type', AZRON_SPECIES))
        if not 0 <= char_type <= 3:
            char_type = AZRON_SPECIES & 0x03
        evo_stage = int(proto_state.get('selected_evolution', AZRON_EVOLUTION))
        if not 0 <= evo_stage <= 3:
            evo_stage = 0
        payload[0x00] = 0x00  # status flag: 0 = new character
        payload[0x01] = char_type  # species → manager+0x12C (0=Ark,1=Abo,2=Paz,3=Tero)
        payload[0x02] = evo_stage  # evolution stage → manager+0x130 (0-4)
        # Native HandleS2C_0007 calls FUN_005A8790(-1) only when this packed
        # date is zero. That is the original fresh-character path which adds
        # tutorial row kind=5/aux=212.  This is required for the unmodified
        # client to leave character-select presentation and initialize the
        # PatHouse 3D scene.  A current-date fresh seed is retained only as an
        # explicit diagnostic opt-out.
        request_word_03 = (
            0 if CONTENT_PROFILE == 'playable' and NATIVE_FRESH_TUTORIAL_ENABLED
            else self._build_zone_datetime_code()
        )
        self._pack_u32(payload, 0x03, request_word_03)
        # +0x07 remains zero until its C2S/S2C relationship is proven.  The
        # same value is forwarded explicitly to the accompanying S2C 0x0005.
        self._pack_u32(payload, 0x07, 0)

        # 0x46 (70) u16 stat values consumed by FUN_005a4880.
        # shipped: [IQ] + init.csv rows 0..24 + [meal counter] + rows 25..54.
        # This fixes idx32=dumbbell, idx55=pet evolution, idx56=pet.  The
        # bootstrap header byte at +0x02 remains controlled only by
        # AZROK_EVOLUTION and is intentionally independent of stat idx55.
        # minimal is retained solely as an explicit diagnostic profile.
        playable_fresh_stats = None
        if CONTENT_PROFILE == 'playable':
            playable_fresh_stats = _build_original_fresh_content_stats(
                char_type,
                _fresh_content_seed_material(proto_state),
            )
        for idx in range(0x46):
            if CONTENT_PROFILE == 'shipped' and idx < len(SHIPPED_CONTENT_STATS):
                value = SHIPPED_CONTENT_STATS[idx]
            elif CONTENT_PROFILE == 'playable':
                value = playable_fresh_stats[idx]
            elif CONTENT_PROFILE == 'minimal':
                value = MINIMAL_CONTENT_STATS.get(idx, 0)
            else:
                value = 0
            self._pack_u16(payload, 0x0B + idx * 2, value)

        # A fresh character has two client-side species/model selectors: the
        # bootstrap header byte above and stat 56 in the imported stat table.
        # Sending a fixed shipped stat56 made newly-created non-Paz characters
        # enter PatHouse with disagreeing selectors (for example 1 vs 2), while
        # reconnect snapshots correctly carried their own authoritative value.
        # Keep only the fresh default coherent here; the persisted snapshot
        # overlay below still overwrites all 70 stats on reconnect.
        if CONTENT_PROFILE == 'shipped':
            self._pack_u16(payload, 0x0B + 56 * 2, char_type)

        # +0x125 is not a passive byte table. 0x59E330 zero-extends all 11 raw
        # bytes and feeds them to DomainCode_EmitLocalEffect as absolute item
        # ids.  The byte width makes only furniture ids 0..32 representable;
        # 1/2/7 here mean furniture ids, not toy/gym/energy domain numbers.
        # Toy (2000+), gym (2500+), and energy (5000+) must never be truncated
        # into these rows.  0xFF is the verified safe no-op sentinel.
        for idx in range(0x0B):
            payload[0x125 + idx] = 0xFF

        # +0x131 is the one-byte Book quantity list.  No recovered starter
        # grant exists, so the fresh zero buffer deliberately keeps it empty.
        payload[0x131] = 0

        # 10 runtime rows imported at the end of 0x59E330.  These rows are
        # not quest-display-only data: FUN_00596690 calls FUN_005A6910 with
        # kind 3 after each valid care/feed action, and FUN_005A6910 can run
        # the client's natural evolution evaluator only when a kind-3 row is
        # present.  Stage-0 uses aux=0 and evolves only after the post-load
        # care action proves EXP > 349.  Keep payload[2] at zero here so the
        # bootstrap handler cannot enable evolution before its stat import
        # (the native-Nexus=40 E1201 failure).
        for idx in range(10):
            self._pack_u16(payload, 0x134 + idx * 2, 0x00FF)
            self._pack_u16(payload, 0x148 + idx * 2, 0x00FF)
            self._pack_u32(payload, 0x15C + idx * 4, 0)
        if CONTENT_PROFILE == 'shipped':
            self._pack_u16(payload, 0x134, 3)  # runtime-row kind: evolution check
            self._pack_u16(payload, 0x148, 0)  # stage-0 threshold / BlueRon -> RedRon
            self._pack_u32(payload, 0x15C, 0)  # callback value; unused by threshold test

        # 8 one-byte mode entries followed by 8 dword packed-date values are
        # consumed by ModePairWriter_Import@005AA6F0.  There is no 0xFF
        # sentinel branch here: 0xFF becomes a live state 255 (or is clamped
        # to state 2 for a stage-0 Azron).  Fresh state is therefore 0×8 with
        # zero timestamps; the client's local mode progression initializes
        # the disease clocks when their predicates become active.
        for idx in range(8):
            payload[0x184 + idx] = 0
            self._pack_u32(payload, 0x18C + idx * 4, 0)

        # +0x1AC..+0x1D3 is four 10-entry domain banks.  The client overwrites
        # 16 fixed entries before importing all 40, while FUN_005AB1B0 later
        # counts every value other than 0xFF as live and expands it to
        # (group + 1) * 10000 + value.  Zero is therefore a live selector, not
        # an empty default; initialize all server-controlled entries to the
        # verified 0xFF sentinel and let the client install its fixed entries.
        payload[0x1AC:0x1D4] = b'\xFF' * 40

        # The last four raw bytes are copied by 0x59E330 through 0x5AB080 and
        # later read back during FUN_006130B0 bootstrap via FUN_005AB2B0(0..3)
        # -> FUN_00521E90(slot, value, 0). 0 is a real lowest valid selector in
        # each bucket; 0xFF is the explicit clear/sentinel path.
        for idx in range(4):
            payload[0x1D4 + idx] = 0xFF

        restored_snapshot = self._apply_saved_character_state(payload)
        if restored_snapshot:
            if CONTENT_PROFILE == 'playable':
                self._pack_u32(payload, 0x03, self._build_zone_datetime_code())
            print(
                f"  [STATE] Restored persisted C2S 0x0007 snapshot "
                f"for key={self.proto_state.get('saved_state_key')}"
            )

        self._apply_canonical_server_state(payload)

        return bytes(payload)

    def _build_post_load_0005_draft(self, state_value=0, subtype=0x00, status=0x00):
        """
        Server->client opcode 0x0005 draft.

        Ghidra notes:
        - handler: 0x59EBD0
        - minimum meaningful size: 6 bytes
        - [0] status byte
        - [1] subtype, observed branches: 0x00 / 0x12 / 0x13
          - 0x12: G2C_FUNCORN_ACK / quest FunCorn balance update
          - 0x13: shop result / inventory replay + FunCorn balance update
        - [2:6] little-endian FunCorn balance propagated via 0x59E300
        """
        payload = bytearray(POST_LOAD_0005_SIZE)
        payload[0] = status & 0xFF
        payload[1] = subtype & 0xFF
        self._pack_u32(payload, 0x02, state_value)
        return bytes(payload)

    def _build_enter_space_0003_draft(self):
        """
        Server->client opcode 0x0003 draft.

        Ghidra notes:
        - in state 1, 0x594310 routes through 0x00613740
        - opcode 3 calls 0x00615610(param_3 + 1)
        - the first byte looks like a status/flag
        - payload[1:] is treated as a NUL-terminated C string and copied
        - a baked-in candidate path present in the binary is:
          "Data\\Space\\Plaza"
        """
        return b'\x01' + ENTER_SPACE_0003_PATH

    def _discover_account_character_slots(self):
        """Recover occupied lobby slots from account-scoped canonical saves."""
        account_raw = self.proto_state.get('account_raw') or b''
        if isinstance(account_raw, str):
            account_raw = account_raw.encode('cp949', errors='ignore')
        account_hex = bytes(account_raw).split(b'\x00', 1)[0][:13].hex()
        if not account_hex or not getattr(self, 'state_store_dir', None):
            return {}
        prefix = f'a{account_hex}_s'
        suffix = '_state_v1.json'
        slots = {}
        try:
            names = os.listdir(self.state_store_dir)
        except OSError:
            return {}
        for filename in names:
            if not filename.startswith(prefix) or not filename.endswith(suffix):
                continue
            body = filename[len(prefix):-len(suffix)]
            slot_text, marker, name_hex = body.partition('_c')
            if marker != '_c' or slot_text not in {'0', '1', '2', '3'}:
                continue
            try:
                name_raw = bytes.fromhex(name_hex).split(b'\x00', 1)[0][:12]
            except ValueError:
                continue
            if not name_raw:
                continue
            path = os.path.join(self.state_store_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as state_file:
                    document = json.load(state_file)
            except (OSError, ValueError, TypeError):
                continue
            if document.get('schema_version') != CANONICAL_STATE_SCHEMA_VERSION:
                continue
            snapshot = b''
            snapshot_hex = document.get('snapshot_hex')
            if isinstance(snapshot_hex, str):
                try:
                    snapshot = bytes.fromhex(snapshot_hex)
                except ValueError:
                    snapshot = b''
            if len(snapshot) != 0xC4:
                # Pre-canonical saves were keyed by character name only.
                # Purchase can create a canonical inventory document before
                # the next C2S 0x0007, so recover lobby level/stage from the
                # legacy 196-byte snapshot instead of displaying level 0.
                legacy_path = os.path.join(
                    self.state_store_dir, f'{name_hex}_c2s0007.bin'
                )
                try:
                    with open(legacy_path, 'rb') as legacy_file:
                        legacy_snapshot = legacy_file.read(0xC5)
                    if len(legacy_snapshot) == 0xC4:
                        snapshot = legacy_snapshot
                except OSError:
                    pass
            character = document.get('character') or {}
            try:
                species = int(character.get('species', AZRON_SPECIES))
            except (TypeError, ValueError):
                species = AZRON_SPECIES
            if not 0 <= species <= 3:
                # Do not turn a corrupt 0xFF/large selector into a valid Tero.
                # The native lobby accepts exactly the four model families.
                continue
            level = 0
            evolution = 0
            if len(snapshot) == 0xC4:
                level = min(0xFF, struct.unpack_from('<H', snapshot, 0x0C)[0])
                if snapshot[0x05] <= 3:
                    evolution = snapshot[0x05]
            slot = int(slot_text)
            record = {
                'slot': slot,
                'storage_slot': slot,
                'name_hex': name_raw.hex(),
                'species': species,
                'level': level,
                'evolution': evolution,
                'path': path,
            }
            previous = slots.get(slot)
            if previous is None or os.path.getmtime(path) >= os.path.getmtime(previous['path']):
                slots[slot] = record
        # The wire protocol requires dense logical slots: payload[1] is both
        # the occupied count and the slot appended to C2S 0x0004.  Preserve
        # legacy sparse filenames as storage_slot while presenting 0..N-1 to
        # the client so a later create can never collide with an occupied key.
        dense_slots = {}
        for logical_slot, storage_slot in enumerate(sorted(slots)):
            record = dict(slots[storage_slot])
            record['slot'] = logical_slot
            record['storage_slot'] = storage_slot
            dense_slots[logical_slot] = record
        return dense_slots

    def _build_login_bootstrap_0000(self, result_code=0, lobby_mode=None):
        """Build the exact 0x183-byte mode-0 lobby/character-list blob."""
        payload = bytearray(LOGIN_0000_BOOTSTRAP_SIZE)
        payload[0x00] = int(result_code) & 0xFF
        slots = self._discover_account_character_slots()
        payload[0x01] = len(slots) & 0xFF
        # Four structure-of-arrays character records.  A signed type -1 is
        # the empty sentinel; zero fabricates an unnamed Ark character.
        payload[0x02:0x06] = b'\xFF' * 4
        payload[0x06:0x0A] = b'\xFF' * 4
        for slot, record in slots.items():
            payload[0x02 + slot] = record['species']
            payload[0x06 + slot] = record['level']
            payload[0x0A + slot] = record['evolution']
            name = bytes.fromhex(record['name_hex'])[:12]
            start = 0x0E + slot * 13
            payload[start:start + len(name)] = name
            payload[start + len(name)] = 0
            payload[0x42 + slot] = 0  # value 3 forces Hansol; normal restore is 0
        payload[0x56] = 0  # sparse lobby record count
        self.proto_state['lobby_slots'] = slots
        self.proto_state['account_has_characters'] = bool(slots)
        return bytes(payload)

    @ox_serialized
    def _archive_account_character_slot(self, slot):
        """Remove one lobby slot while retaining a preservation archive."""
        self._last_character_archive_result = {
            'status': 'rejected', 'moved_files': 0,
            'rollback_attempted': False, 'rollback_failed': False,
        }
        account_raw = self.proto_state.get('account_raw') or b''
        if isinstance(account_raw, str):
            account_raw = account_raw.encode('cp949', errors='ignore')
        account_hex = bytes(account_raw).split(b'\x00', 1)[0][:13].hex()
        slots = dict(self.proto_state.get('lobby_slots') or {})
        record = slots.get(slot)
        if not account_hex or slot not in range(4) or not record:
            return False
        storage_slot = int(record.get('storage_slot', slot))
        if storage_slot not in range(4):
            return False
        prefix = f'a{account_hex}_s{storage_slot}_c'
        try:
            names = [
                name for name in os.listdir(self.state_store_dir)
                if name.startswith(prefix)
                and (name.endswith('_state_v1.json')
                     or name.endswith('_c2s0007.bin')
                     or name.endswith('_ox_v1.json'))
            ]
        except OSError:
            return False
        # The old name-only snapshot is a compatibility source.  Archive it
        # with the slot so recreating the same name cannot resurrect deleted
        # progression through the one-time legacy import path.
        name_hex = record.get('name_hex')
        if isinstance(name_hex, str):
            legacy_name = f'{name_hex}_c2s0007.bin'
            if (legacy_name not in names
                    and os.path.isfile(os.path.join(self.state_store_dir, legacy_name))):
                names.append(legacy_name)
        if not names:
            return False
        archive_dir = os.path.join(self.state_store_dir, 'deleted')
        moved = []
        try:
            os.makedirs(archive_dir, exist_ok=True)
            stamp = time.strftime('%Y%m%d_%H%M%S')
            for name in names:
                source = os.path.join(self.state_store_dir, name)
                destination = os.path.join(archive_dir, f'{name}.{stamp}')
                counter = 1
                while os.path.exists(destination):
                    destination = os.path.join(
                        archive_dir, f'{name}.{stamp}.{counter}'
                    )
                    counter += 1
                os.replace(source, destination)
                moved.append((source, destination))
        except OSError as exc:
            print(f"  [STATE] Failed to archive slot {slot}: {exc}")
            self._last_character_archive_result.update({
                'reason': str(exc)[:256],
                'moved_files': len(moved),
                'rollback_attempted': bool(moved),
            })
            for source, destination in reversed(moved):
                try:
                    os.replace(destination, source)
                except OSError as rollback_exc:
                    self._last_character_archive_result['rollback_failed'] = True
                    print(
                        f"  [STATE] Failed to rollback archive {destination}: "
                        f"{rollback_exc}"
                    )
            return False

        cache_prefix = f'a{account_hex}_s{storage_slot}_c'
        if hasattr(self, 'ox_pending_results'):
            self.ox_pending_results = [
                row for row in self.ox_pending_results
                if not row[0].startswith(cache_prefix)
            ]
        for cache_name in ('saved_character_states', 'saved_server_states'):
            cache = getattr(self, cache_name, {})
            for key in list(cache):
                if key.startswith(cache_prefix):
                    cache.pop(key, None)
        slots.pop(slot, None)
        # The wire lobby is a dense logical array, while durable files keep
        # their original storage slot.  Deleting a middle character therefore
        # compacts only the logical keys; it must never rename or reuse the
        # surviving canonical files.
        dense_slots = {}
        for logical_slot, (_old_slot, surviving) in enumerate(
                sorted(slots.items())):
            surviving = dict(surviving)
            surviving['slot'] = logical_slot
            dense_slots[logical_slot] = surviving
        slots = dense_slots
        self.proto_state['lobby_slots'] = slots
        self.proto_state['account_has_characters'] = bool(slots)
        self._last_character_archive_result = {
            'status': 'archived', 'moved_files': len(moved),
            'rollback_attempted': False, 'rollback_failed': False,
        }
        return True

    @ox_serialized
    def reset_preserved_account_state(self, account_id):
        """Archive every durable character file owned by a disconnected account."""
        if (not isinstance(account_id, str) or not 3 <= len(account_id) <= 13
                or any(not (char.isascii() and (char.isalnum() or char == '_'))
                       for char in account_id)):
            return False, {'error': 'invalid preserved account'}
        account_raw = account_id.encode('ascii')
        with self.ctl_lock:
            connected = [
                int(meta.get('entity_id') or 0)
                for meta in self.client_meta.values()
                if bytes((meta.get('proto_state') or {}).get('account_raw') or b'')
                .split(b'\x00', 1)[0][:13] == account_raw
            ]
        if connected:
            return False, {
                'error': 'account is still connected',
                'connected_entities': connected,
            }

        account_hex = account_raw.hex()
        prefix = f'a{account_hex}_s'
        try:
            names = [
                name for name in os.listdir(self.state_store_dir)
                if name.startswith(prefix)
                and (name.endswith('_state_v1.json')
                     or name.endswith('_c2s0007.bin')
                     or name.endswith('_ox_v1.json'))
                and os.path.isfile(os.path.join(self.state_store_dir, name))
            ]
        except OSError as exc:
            return False, {'error': str(exc)[:256]}

        # A pre-account snapshot can otherwise be imported again when the new
        # identity creates a character with the same name.
        legacy_names = set()
        for name in names:
            for suffix in ('_state_v1.json', '_c2s0007.bin'):
                if not name.endswith(suffix):
                    continue
                body = name[len(prefix):-len(suffix)]
                _slot, marker, name_hex = body.partition('_c')
                if marker == '_c' and name_hex:
                    legacy_names.add(f'{name_hex}_c2s0007.bin')
        for legacy_name in sorted(legacy_names):
            if (legacy_name not in names
                    and os.path.isfile(os.path.join(self.state_store_dir, legacy_name))):
                names.append(legacy_name)

        stamp = time.strftime('%Y%m%d_%H%M%S')
        archive_dir = os.path.join(
            self.state_store_dir, 'reset_accounts', f'{account_id}_{stamp}'
        )
        moved = []
        try:
            os.makedirs(archive_dir, exist_ok=False)
            for name in names:
                source = os.path.join(self.state_store_dir, name)
                destination = os.path.join(archive_dir, name)
                os.replace(source, destination)
                moved.append((source, destination))
        except OSError as exc:
            for source, destination in reversed(moved):
                try:
                    os.replace(destination, source)
                except OSError:
                    pass
            return False, {
                'error': str(exc)[:256],
                'rollback_attempted': bool(moved),
            }

        for cache_name in ('saved_character_states', 'saved_server_states'):
            cache = getattr(self, cache_name, {})
            for key in list(cache):
                if key.startswith(prefix):
                    cache.pop(key, None)
        if hasattr(self, 'ox_pending_results'):
            self.ox_pending_results = [
                row for row in self.ox_pending_results
                if not row[0].startswith(prefix)
            ]
        with self.ctl_lock:
            self.manual_select_accounts.discard(account_raw)
        self._add_event(
            'account_reset', f'{account_id} 계정 저장 상태를 초기화했습니다.',
            severity='warn',
            details={'archived_files': len(moved), 'archive_dir': archive_dir},
        )
        return True, {
            'account': account_id,
            'archived_files': len(moved),
            'archive_dir': archive_dir,
        }

    @staticmethod
    def _build_calibration_0004_sample(kind=1):
        if kind == 0xFF:
            return b'\xFF'
        timestamp = int(time.time() * 1000) & 0xFFFFFFFF
        return struct.pack('<BI', kind & 0xFF, timestamp)

    def _build_state_0064_draft(self, entity_id=DEFAULT_ACTOR_ID,
                                entry_kind=0x00,
                                selector_0=0x00,
                                selector_1=0x00,
                                x=DEFAULT_SPAWN_X,
                                y=DEFAULT_SPAWN_Y):
        """
        Server->client opcode 0x0064 (HandleS2C_0064_ApplyAuthoritativeSelf).

        Ghidra-verified struct S2C_0064_AuthoritativeSelf (0x1B bytes):
        - +0x00: entry_kind (u8) — valid: 0x00, 0x0A, 0x0B, 0x14
        - +0x01: self_id (u32) — actor ID
        - +0x05: unknown/reserved (u8)
        - +0x06: pos_x_raw (u32) — decoded via FUN_004edde0
        - +0x0A: pos_y_raw (u32) — decoded via FUN_004edde0
        - +0x0E..+0x11: unknown/reserved (4 bytes)
        - +0x12: selector_0 / appearance A (u8)
        - +0x13: selector_1 / appearance B (u8)
        - +0x14: year (u16)
        - +0x16: month-1 (u8)
        - +0x17: day (u8)
        - +0x18: hour (u8)
        - +0x19: minute (u8)
        - +0x1A: second (u8)

        HandleS2C_0064 passes payload[0x14:0x1B] to FUN_0050EE80.  Leaving
        those seven bytes zero reaches the CRT invalid-date abort path.
        """
        payload = bytearray(STATE_0064_SIZE)

        payload[0x00] = entry_kind & 0xFF
        self._pack_u32(payload, 0x01, entity_id)
        self._pack_u32(payload, 0x06, x)
        self._pack_u32(payload, 0x0A, y)
        payload[0x12] = selector_0 & 0xFF
        payload[0x13] = selector_1 & 0xFF

        # Archive layout and the live 0x0064 handler both use a separate
        # seven-byte clock block beginning at +0x14. Month is zero-based.
        now = datetime.datetime.now()
        struct.pack_into(
            '<HBBBBB', payload, 0x14,
            now.year, now.month - 1, now.day,
            now.hour, now.minute, now.second,
        )
        return bytes(payload)

    def _build_state_0065_draft(self):
        """
        Server->client opcode 0x0065 destructive actor-container teardown.

        Ghidra notes:
        - state-1 handler 0x00613740 routes opcode 0x65 -> 0x00615B20
        - 0x00615B20 -> 0x0050D5D0
        - 0x0050D5D0 first tears down the fixed self slot at base+0x35C20,
          then clears the remote list at base+0x4A723
        - an active Plaza minimap dereferences the missing self actor on its
          next frame and faults at 0x005F3AF4

        The empty payload is structurally accepted but is not a safe live-
        Plaza probe or roster refresh.  Automatic relay never emits it.
        """
        return b''

    def _build_state_0066_draft(self):
        """
        Server->client opcode 0x0066 draft.

        Ghidra notes:
        - state-1 handler 0x00613740 routes opcode 0x66 -> 0x00615B50
        - the handler walks payload in 0x1A-byte records
        - with a zero-length payload, it safely skips the record loop and still
          executes the trailing finalize call (0x0050DA70)

        This is a low-risk follow-up while opcode 0x0064 is known to fault.
        """
        return b''

    def _build_state_0066_actor_record(self, entity_id, char_type, name_raw,
                                        action=0x0A, accessory_slots=None, evolution=0,
                                        chair_seat=None):
        """
        Server->client opcode 0x0066 single actor record.

        Record size is 0x1A bytes. Best-effort field map from 0x00615B50 /
        0x005243E0:
        - +0x00: action/state byte
        - +0x01: actor/entity id (u32)
        - +0x05: actor type / species-like byte
        - +0x06: evolution stage (actor +0xA1; information label selector)
        - +0x07: short C string (13-byte slot up to +0x13)
        - +0x14..+0x17: four appearance bytes
        - +0x18..+0x19: optional pair; use 0xFF sentinel to skip extra branch
        """
        record = bytearray(STATE_0066_RECORD_SIZE)
        record[0x00] = action & 0xFF
        self._pack_u32(record, 0x01, entity_id)
        record[0x05] = char_type & 0xFF
        if not isinstance(evolution, int) or evolution not in range(4):
            raise ValueError('S2C 0x0066 evolution stage is invalid')
        record[0x06] = evolution

        safe_name = (name_raw or b'Player').split(b'\x00', 1)[0][:12]
        record[0x07:0x07 + len(safe_name)] = safe_name
        record[0x07 + len(safe_name)] = 0x00

        if accessory_slots is None:
            accessory_slots = DEFAULT_ACCESSORY_SLOTS
        accessory_slots = normalize_accessory_slots(accessory_slots)
        if accessory_slots is None:
            raise ValueError('S2C 0x0066 accessory slots are invalid')
        record[0x14:0x18] = bytes(accessory_slots)
        if chair_seat is None:
            record[0x18] = 0xFF
            record[0x19] = 0x00
        else:
            chair, side = chair_seat
            if not (isinstance(chair, int) and isinstance(side, int)
                    and 0 <= chair <= 5 and side in (0, 1)):
                raise ValueError('S2C 0x0066 chair seat is invalid')
            record[0x18] = chair
            record[0x19] = side
        return bytes(record)

    def _build_state_0067_actor_remove_record(self, entity_id):
        """Build the exact S2C 0x0067 one-remote-actor removal payload.

        HandleS2C_0067_RemoveRemoteActor @ 0x00615D00 reads one DWORD from
        payload start without a length guard and has no repeated-record loop.
        Exactly four bytes are therefore canonical; multiple removals require
        one packet per actor.
        """
        return struct.pack('<I', entity_id & 0xFFFFFFFF)

    def _build_state_0068_actor_position_record(self, entity_id=DEFAULT_ACTOR_ID,
                                                x=DEFAULT_SPAWN_X,
                                                y=DEFAULT_SPAWN_Y,
                                                z=0, heading=0,
                                                mode_flag=0):
        """
        Server->client opcode 0x0068 single actor-position record.

        Ghidra notes:
        - state-1 handler 0x00613740 routes opcode 0x68 -> 0x00615D50
        - payload is consumed in 0x18-byte records (6 dwords)
        - for an existing non-current actor, if record[5] == 0:
          - it calls 0x00526EC0()
          - sets object state via 0x00527A40(1)
          - then calls 0x00524DA0(record[1], record[2])

        Compared with 0x0069, this path performs one more piece of actor-state
        setup before applying coordinates, so it is the stronger follow-up
        candidate after our 0x0066 action 0x0A scene bootstrap.
        """
        payload = bytearray(STATE_0068_RECORD_SIZE)
        self._pack_u32(payload, 0x00, entity_id)
        self._pack_u32(payload, 0x04, x)
        self._pack_u32(payload, 0x08, y)
        self._pack_u32(payload, 0x0C, z)
        self._pack_u32(payload, 0x10, heading)
        self._pack_u32(payload, 0x14, mode_flag)
        return bytes(payload)

    def _build_state_0068_movement_record(self, entity_id, from_x, from_y,
                                          to_x, to_y, arrival_tick):
        """Server->client 0x0068 record for the *walking* branch.

        Same 0x18-byte six-dword record, but ``record[5] != 0`` selects a
        different handler and the other fields change meaning.  Decompile
        (Azrok.exe):

            0x00615D50:  if (record[5] == 0) { 0x00527A40(1);
                                               0x00524DA0(record[1], record[2]); }
                         else                 { 0x00524EB0(record, 0); }

            0x00524EB0:  actor+0x11b = current x       (from the live entity)
                         actor+0x11f = current y
                         actor+0x123 = record[3]        <- destination x
                         actor+0x127 = record[4]        <- destination y
                         0x00525050(record[5])         -> actor+0x133
                         0x00525080(record[5], now)    -> actor+0x137, +0x13b
                         0x00527A40(2)                 -> actor+0x107 = 2 (walk)

        ``record[5]`` is an **absolute arrival deadline**, not a duration.  The
        per-frame mover 0x0061A710 proves it:

            now = GetTickCount() -/+ clock_offset       (server-synced clock)
            if (now < actor+0x137) {                    <- the whole walk branch
                vec_diff(dir, actor+0x123, entity+0x10)
                vec_to_angle(entity+0x1c, dir)          <- the facing, only here
                total   = actor+0x137 - actor+0x13b
                elapsed = now         - actor+0x13b
                step    = length(dir) * elapsed / total
                ...
            } else { snap onto actor+0x123; return done }

        Feeding it a relative duration makes ``now < record[5]`` false on the
        first frame, so the actor snaps to the destination and ``vec_to_angle``
        never runs - the teleport-without-facing regression measured
        2026-07-30.  ``actor+0x13b`` is stamped locally at receive time, so the
        server only has to supply the deadline.

        The clock is the *server's* clock: S2C 0x0004 calibration handler
        0x0059DE50 takes five ``<BI>`` samples, keeps the median
        ``|GetTickCount() - server_timestamp|`` with its sign, and commits it
        through 0x0050EDE0/0x0050CBC0 case 4 into the global consulted above.
        Our samples carry ``int(time.time()*1000) & 0xFFFFFFFF``, so a deadline
        in that same unit is directly comparable on every calibrated client.

        **There is no heading field.**  Facing comes from ``vec_to_angle`` over
        current->destination, which is why filling a "heading" slot never
        changed the rendered angle.  See doc 538.
        """
        payload = bytearray(STATE_0068_RECORD_SIZE)
        self._pack_u32(payload, 0x00, entity_id)
        self._pack_u32(payload, 0x04, from_x)
        self._pack_u32(payload, 0x08, from_y)
        self._pack_u32(payload, 0x0C, to_x)
        self._pack_u32(payload, 0x10, to_y)
        self._pack_u32(payload, 0x14, arrival_tick)
        return bytes(payload)

    def _build_state_0069_actor_position(self, entity_id=DEFAULT_ACTOR_ID,
                                         x=DEFAULT_SPAWN_X, y=DEFAULT_SPAWN_Y,
                                         mode=0):
        """
        Server->client opcode 0x0069 actor-position follow-up.

        Ghidra notes:
        - state-1 handler 0x00613740 routes opcode 0x69 -> 0x00615E70
        - when the target actor already exists and its scene code is 0x2E/0x2F
          (which matches our 0x0066 action 0x0A / 0x0B bootstrap), 0x00615E70
          routes directly to 0x00524DA0(x, y) without touching the unsafe
          current-player path used by opcode 0x0064
        - payload layout is four dwords:
          [entity_id][x][y][mode_or_flag]

        This makes 0x0069 a safer "place the spawned actor into the scene"
        candidate than 0x0064.
        """
        payload = bytearray(STATE_0069_SIZE)
        self._pack_u32(payload, 0x00, entity_id)
        self._pack_u32(payload, 0x04, x)
        self._pack_u32(payload, 0x08, y)
        self._pack_u32(payload, 0x0C, mode)
        return bytes(payload)

    def _build_state_006A_text_record(self, kind, mode, actor_id,
                                      primary_raw, message_raw):
        """Build the verified variable-size S2C 0x006A text record."""
        primary_raw = bytes(primary_raw).split(b'\x00', 1)[0][:14]
        message_raw = bytes(message_raw).split(b'\x00', 1)[0]
        payload = bytearray(CHAT_006A_FIXED_SIZE + len(message_raw) + 1)
        payload[0] = int(kind) & 0xFF
        payload[1] = int(mode) & 0xFF
        self._pack_u32(payload, 0x02, actor_id)
        payload[0x06:0x06 + len(primary_raw)] = primary_raw
        payload[0x06 + len(primary_raw)] = 0
        payload[0x15:0x15 + len(message_raw)] = message_raw
        payload[-1] = 0
        if len(payload) > MAX_SAFE_PACKET_PAYLOAD:
            raise ValueError('S2C 0x006A text exceeds the client receive buffer')
        return bytes(payload)

    def _build_state_006c_actor_state(self, state, toggle, actor_id):
        """Build verified S2C 0x006C: state, toggle, remote actor id."""
        payload = bytearray(COMMUNITY_006C_SIZE)
        payload[0] = int(state) & 0xFF
        payload[1] = int(toggle) & 0xFF
        self._pack_u32(payload, 0x02, actor_id)
        return bytes(payload)

    def _build_state_006E_draft(self, slot_index=0):
        """
        Server->client opcode 0x006E draft.

        Ghidra notes:
        - state-1 handler 0x00613740 routes opcode 0x6E -> 0x006169D0
        - if payload[1] == 0, it performs a substantial "ready / setup" path
          and sets an internal flag at +0x129B
        - the failure branch is only taken when payload[1] != 0

        Keep the secondary byte at 0 and probe with a conservative index.
        """
        return bytes([slot_index & 0xFF, 0x00])

    def _build_item_registry_000A_draft(self):
        """
        Server->client opcode 0x000A item-domain registry.

        Ghidra notes:
        - handler: 0x59ECA0
        - exact payload: 0x96 bytes = 75 grouped u16 values
        - baked keys map to Furniture/Toy/Gym/Food/Ingredient/Book/Drug IDs
        - the exact binary values are the supported default
        """
        payload = bytearray(ITEM_REGISTRY_000A_SIZE)
        defaults = dict(
            ITEM_REGISTRY_000A_BINARY_DEFAULTS
            if ITEM_REGISTRY_000A_PROFILE == 'binary'
            else ITEM_REGISTRY_000A_DIAGNOSTIC_CUSTOM_VALUES
        )
        if ITEM_REGISTRY_000A_HIGH_RESOURCE_DIAGNOSTIC:
            defaults.update(ITEM_REGISTRY_000A_DIAGNOSTIC_HIGH_OVERRIDES)

        # Group 0: 0x16 u16 entries at +0x00
        for idx, value in enumerate(defaults['group0']):
            self._pack_u16(payload, 0x00 + idx * 2, value)

        # Group 1: 6 u16 entries at +0x2C
        for idx, value in enumerate(defaults['group1']):
            self._pack_u16(payload, 0x2C + idx * 2, value)

        # Group 2: 5 u16 entries at +0x38
        for idx, value in enumerate(defaults['group2']):
            self._pack_u16(payload, 0x38 + idx * 2, value)

        # Group 3: 0x20 u16 entries at +0x42
        for idx, value in enumerate(defaults['group3']):
            self._pack_u16(payload, 0x42 + idx * 2, value)

        # Group 4: 3 u16 entries at +0x82
        for idx, value in enumerate(defaults['group4']):
            self._pack_u16(payload, 0x82 + idx * 2, value)

        # Group 5: 1 u16 entry at +0x88
        self._pack_u16(payload, 0x88, defaults['group5'][0])

        # Group 6: 6 u16 entries at +0x8A
        for idx, value in enumerate(defaults['group6']):
            self._pack_u16(payload, 0x8A + idx * 2, value)

        return bytes(payload)

    def _build_stat_table_0011_draft(self):
        """
        Server->client opcode 0x0011 draft.

        Ghidra notes:
        - handler: 0x59EEE0 -> 0x5A50F0
        - minimum payload touched: 31 * u16 = 62 bytes
        - default/current values are already present in DAT_006E0A88.
        """
        payload = bytearray(STAT_TABLE_0011_SIZE)
        for idx, value in enumerate(STAT_TABLE_0011_DEFAULTS):
            self._pack_u16(payload, idx * 2, value)
        return bytes(payload)

    def _build_response(self, opcode, payload, pkt_num):
        """
        Build server response for a single parsed game packet.

        Packet format: [2-byte LE payload_size][2-byte LE opcode][payload]

        Client opcodes observed:
          0x0000: Initial hello (106 bytes payload)
          0x0004: Character creation (15B: [1B type][14B name_euckr_padded])
                  type: 0=뮤리, 1=새지?, 2=아링?, 3=테로
          0x0016: Heartbeat (1 byte payload: 0x00)
        """

        if opcode in (0x006B, 0x00C8, 0x00C9, 0x00CA):
            # Socket-aware mode-2 handlers already consumed enter, leave, or
            # answer.  None of these C2S messages has a direct echo response.
            return None

        if opcode == 0x0000:
            # Preserve the account identity immediately, but pace the lobby
            # blob from the first heartbeat.  A live A/B on 2026-07-18 proved
            # that bundling S2C 0x0001 + 0x0000 + 0x0004 directly into this
            # receive callback makes this client build exit after packet #1.
            # The heartbeat-paced 0x0000 path is the established working
            # behavior and remains in place until the exact auth timing is
            # dynamically proven.
            try:
                login_type, account_raw, _password_raw = decode_c2s_login_0000(payload)
            except ValueError as exc:
                print(f"  [PROTO] Login rejected: {exc}")
                return self._make_packet(0x0001, b'\x01')

            # Re-login reuses the same socket state object.  Reset it in
            # place so client_meta keeps the correct reference, while stale
            # lobby slots/name/selection from account A cannot be rebound to
            # account B before B's first heartbeat rebuilds the roster.
            template = getattr(self, 'proto_template', {})
            fresh = {
                key: (bytes(value) if isinstance(value, (bytes, bytearray)) else value)
                for key, value in template.items()
            }
            self.proto_state.clear()
            self.proto_state.update(fresh)
            self.proto_state['account_raw'] = account_raw
            self.proto_state['account_name'] = account_raw.decode(
                'cp949', errors='replace'
            ).strip()
            self.proto_state['login_type'] = login_type
            if hasattr(self, 'ctl_lock'):
                self._add_event('login', '게임 계정 로그인',
                                entity_id=self._entity_id_for_proto_state(self.proto_state))
            if not hasattr(self, 'manual_select_accounts'):
                self.manual_select_accounts = set()
            lock = getattr(self, 'ctl_lock', None)
            if lock is None:
                suppress_auto_select = account_raw in self.manual_select_accounts
                self.manual_select_accounts.discard(account_raw)
            else:
                with lock:
                    suppress_auto_select = account_raw in self.manual_select_accounts
                    self.manual_select_accounts.discard(account_raw)
            if suppress_auto_select:
                self.proto_state['auto_select_existing_sent'] = True
                self.proto_state['logout_character_picker_reconnect'] = True
            print(
                f"  [PROTO] Login identity accepted: type={login_type}, "
                f"account={self.proto_state['account_name']!r}; "
                "lobby bootstrap waits for the first heartbeat"
            )
            return None

        elif opcode == 0x0016:
            # ── Heartbeat ──
            responses = bytearray()

            request_kind = payload[0] if payload else 0
            current_room_kind = self.proto_state.get('current_room_kind')
            if (request_kind == 0x01
                    and current_room_kind in LOCAL_FACILITY_ROOM_KINDS
                    and not self.proto_state.get('facility_plaza_return_sent')
                    and not self.proto_state.get('hansol_calibration_active')):
                # Verified facility-exit contract (docs 81/134): the first
                # 0016[01] asks for the Plaza transition prelude.  Keep 000D
                # separate from calibration samples; the next 0016[01]
                # begins the already-proven five-sample exchange.
                responses += self._make_packet(0x0016, b'\x00')
                responses += self._make_packet(0x000D, b'\x00')
                self.proto_state['facility_plaza_return_sent'] = True
                self.proto_state['hansol_calibration_active'] = True
                self.proto_state['hansol_calibration_samples_sent'] = 0
                self.proto_state['calib_0004_count'] = 0
                self.proto_state['client_0064_seen'] = False
                self.proto_state['client_0064_count'] = 0
                print(
                    '  [PROTO] Local facility exit request '
                    f'(kind=0x{int(current_room_kind):02X}) -> '
                    'S2C 0x000D[00]; kind-01 calibration armed'
                )
                return bytes(responses)

            if self.proto_state.get('calibration_active'):
                if request_kind == 0x01:
                    sample_count = int(
                        self.proto_state.get('calibration_samples_sent', 0)
                    )
                    if sample_count < 5:
                        responses += self._make_packet(
                            0x0004, self._build_calibration_0004_sample(kind=1)
                        )
                        self.proto_state['calibration_samples_sent'] = sample_count + 1
                    else:
                        responses += self._make_packet(
                            0x0004, self._build_calibration_0004_sample(kind=0xFF)
                        )
                        self.proto_state['calibration_active'] = False
                        self.proto_state['calibration_completed'] = True
                    return bytes(responses)
                # A legacy heartbeat may race the first calibration sample.
                # Answer it normally without fabricating a kind-0 sample.
                responses += self._make_packet(0x0016, b'\x00')
            else:
                responses += self._make_packet(0x0016, b'\x00')

            # S->C 0x0004 time calibration.  During Hansol, the client requests
            # kind=0x01 samples through C->S 0x0016[01]; bootstrap traffic uses
            # kind=0x00.  The server answers at most five matching requests.
            calib_count = self.proto_state.get('calib_0004_count', 0)
            hansol_active = self.proto_state.get('hansol_calibration_active', False)
            should_sample = (
                (hansol_active and request_kind == 0x01)
                or (
                    not self.proto_state.get('login_response_sent')
                    and not hansol_active
                    and request_kind == 0x00
                )
            )
            if should_sample and calib_count < 5:
                import time as _time
                ts = int(_time.time() * 1000) & 0xFFFFFFFF
                sample_kind = 0x01 if hansol_active else 0x00
                calib_payload = struct.pack('<BI', sample_kind, ts)  # [flag, timestamp_u32]
                responses += self._make_packet(0x0004, calib_payload)
                self.proto_state['calib_0004_count'] = calib_count + 1
                if hansol_active:
                    self.proto_state['hansol_calibration_samples_sent'] = calib_count + 1
                if calib_count == 0:
                    print(f"  [PROTO] Starting S->C 0x0004 time calibration kind=0x{sample_kind:02X}")

            # Working live bootstrap timing: the client begins heartbeat
            # traffic after C2S 0x0000, then accepts the 0x183 pet-shell cache
            # alongside the first heartbeat response.  Do not preface it with
            # S2C 0x0001 until that auth handler's live timing is recovered.
            if not self.proto_state.get('login_response_sent'):
                responses += self._make_packet(
                    0x0000,
                    self._build_login_bootstrap_0000(result_code=0),
                )
                self.proto_state['login_response_sent'] = True
                print("  [PROTO] First heartbeat -> sending paced S2C 0x0000 lobby blob")

            # A live existing-account capture showed that a newly-created
            # non-first character accepted the proactive room bundle and the
            # tutorial row, but never emitted the normal post-load 0x0017 / 
            # 0x0008 sequence.  Selecting that same logical slot immediately
            # afterwards completed PatHouse.  Replay that proven selector
            # path once, on the next heartbeat, only for this narrow case.
            if self.proto_state.pop('post_create_select_replay_pending', False):
                logical_slot = int(
                    self.proto_state.pop('post_create_select_replay_slot', -1)
                )
                selected = self._build_response(
                    0x0005, bytes((logical_slot,)), pkt_num
                ) if logical_slot in range(4) else None
                if selected:
                    responses += selected
                    self.proto_state['post_create_select_replay_sent'] = True
                    print(
                        "  [PROTO] POST-CREATE SELECT REPLAY: slot "
                        f"{logical_slot} via the proven C2S 0x0005 path"
                    )

            # Auto-create character after 8 heartbeats if no 0x0004 received
            if (SERVER_AUTO_CREATE_ENABLED
                    and not self.proto_state.get('char_created')
                    and not self.proto_state.get('account_has_characters')
                    and not self.proto_state.get('auto_create_sent')):
                self.proto_state['pre_create_heartbeat_count'] = self.proto_state.get('pre_create_heartbeat_count', 0) + 1
                if self.proto_state['pre_create_heartbeat_count'] >= 8:
                    self.proto_state['auto_create_sent'] = True
                    self.proto_state['char_created'] = True
                    self.proto_state['char_type'] = AZRON_SPECIES
                    self.proto_state['char_name_raw'] = b'Azrok1'
                    enter_space = self._build_enter_space_0003_draft()
                    # S->C 0x0003 (path) + S->C 0x0007 (setup blob) PROACTIVELY
                    # No 0x0002! It kills gate (gm+0x31946=0) with no restore.
                    # S->C 0x0003 (path) + S->C 0x0007 bundle PROACTIVELY.
                    # 0x0006 verified: CAN trigger C->S 0x0007, but crashes if sent
                    # in same packet as 0x0007 (loading not yet complete, subsystems
                    # initialized but room transition in progress). Must be sent AFTER
                    # room loading completes. For now, proactive 0x0007 is the working approach.
                    responses += self._make_packet(0x0003, enter_space)
                    zone_payload = self._build_zone_0007_draft(b'\x00' * 196)
                    zone_state = struct.unpack_from('<I', zone_payload, 0x07)[0]
                    responses += self._make_packet(0x0007, zone_payload)
                    responses += self._make_packet(0x0005, self._build_post_load_0005_draft(state_value=zone_state))
                    responses += self._make_packet(0x000A, self._build_item_registry_000A_draft())
                    responses += self._make_packet(0x000B, self._build_stat_table_0011_draft())
                    # Mark zone as already sent so subsequent C->S 0x0007 are ignored
                    # (prevents double-bundle during room init causing race condition crash)
                    self.proto_state['zone_request_count'] = 1
                    print(
                        f"  [PROTO] AUTO-CREATE: heartbeat #{self.proto_state['pre_create_heartbeat_count']} "
                        f"- sending 0x0003 + 0x0007 bundle (proactive, gate preserved)"
                    )

            # S->C 0x0064 DISABLED — natural FUN_0050B400(100) handles PatHouse bootstrap
            # Sending 0x0064 changes dispatch_state to 1, which prevents post-load processing

            # Browser-only startup assist: once the paced lobby has been on
            # screen for the same eight-heartbeat window as the retired
            # auto-create helper, continue slot 0 through the exact,
            # already-verified C2S 0x0005 selection handler. This is opt-in
            # and leaves desktop/manual selection untouched.
            if SERVER_AUTO_SELECT_EXISTING_ENABLED:
                print(
                    '  [AUTO-SELECT TRACE] '
                    f"char_created={bool(self.proto_state.get('char_created'))} "
                    f"has_characters={bool(self.proto_state.get('account_has_characters'))} "
                    f"sent={bool(self.proto_state.get('auto_select_existing_sent'))} "
                    f"pre_select={self.proto_state.get('pre_select_heartbeat_count', 0)}"
                )
            if (SERVER_AUTO_SELECT_EXISTING_ENABLED
                    and not self.proto_state.get('char_created')
                    and self.proto_state.get('account_has_characters')
                    and not self.proto_state.get('explicit_character_logout')
                    and not self.proto_state.get('auto_select_existing_sent')):
                self.proto_state['pre_select_heartbeat_count'] = (
                    self.proto_state.get('pre_select_heartbeat_count', 0) + 1
                )
                if (self.proto_state['pre_select_heartbeat_count'] >=
                        SERVER_AUTO_SELECT_HEARTBEATS):
                    self.proto_state['auto_select_existing_sent'] = True
                    selected = self._build_response(0x0005, b'\x00', pkt_num)
                    if selected:
                        responses += selected
                        print(
                            '  [PROTO] AUTO-SELECT EXISTING: slot 0 via '
                            'the C2S 0x0005 handler'
                        )

            if self.proto_state.get('client_0064_seen') and not self.proto_state.get('late_006e_sent'):
                self.proto_state['client_0064_heartbeat_count'] += 1
                if LATE_READY_006E and self.proto_state['client_0064_heartbeat_count'] >= 3:
                    ready_006e = self._build_state_006E_draft()
                    responses += self._make_packet(0x006E, ready_006e)
                    self.proto_state['late_006e_sent'] = True
                    print("  [PROTO] Post-ack heartbeat threshold reached - sending delayed 0x006E ready")

            # A Hansol prelude is safe only after bootstrap 0x0004[00] traffic
            # has stopped and the client has completed its PatHouse/zone handshake.
            if (self.proto_state.get('calib_0004_count', 0) >= 5
                    and self.proto_state.get('char_created')
                    and self.proto_state.get('zone_request_seen')
                    and self.proto_state.get('zone_request_count', 0) >= 2):
                self.proto_state['stable_heartbeat_count'] = (
                    self.proto_state.get('stable_heartbeat_count', 0) + 1
                )

            # (Delayed 0x0064 logic removed - now sent immediately from C->S 0x0064 handler)

            return bytes(responses)

        elif opcode == 0x0004:
            # ── Character creation request ──
            if len(payload) != 15:
                print(f"  [PROTO] Rejecting malformed character creation: {len(payload)}B")
                return None
            char_type = payload[0]
            char_name_raw = payload[1:14]
            char_name = char_name_raw.rstrip(b'\x00')
            character_slot = payload[14]
            slots = dict(
                self.proto_state.get('lobby_slots')
                or self._discover_account_character_slots()
            )
            dense_keys = list(range(len(slots)))
            used_storage_slots = {
                int(record.get('storage_slot', logical_slot))
                for logical_slot, record in slots.items()
            }
            storage_slot = next(
                (candidate for candidate in range(4)
                 if candidate not in used_storage_slots),
                None,
            )
            if (char_type > 3 or character_slot > 3 or not char_name
                    or sorted(slots) != dense_keys
                    or character_slot != len(slots)
                    or storage_slot is None):
                print("  [PROTO] Rejecting invalid character type/slot/name")
                return None
            if self._character_session_in_use(
                    self.proto_state.get('account_raw') or b'',
                    storage_slot, char_name):
                print("  [PROTO] Rejecting duplicate live character creation")
                return None
            try:
                name_str = char_name.decode('euc-kr')
            except:
                name_str = repr(char_name)
            print(f"  [PROTO] Character creation: type={char_type}, name='{name_str}'")

            # ── The vtable[3] handler for incoming opcodes is a STUB ──
            # But sending multiple opcodes in prev test triggered loading screen!
            # Testing narrower set to find which opcode triggers it.
            responses = bytearray()
            identity_keys = (
                'char_created', 'char_type', 'char_name_raw',
                'wire_character_slot', 'character_slot',
                'selected_evolution', 'account_has_characters',
            )
            identity_before = {
                key: (key in self.proto_state, self.proto_state.get(key))
                for key in identity_keys
            }
            self.proto_state['char_created'] = True
            self.proto_state['char_type'] = char_type
            self.proto_state['char_name_raw'] = char_name
            self.proto_state['wire_character_slot'] = character_slot
            self.proto_state['character_slot'] = storage_slot
            self.proto_state['selected_evolution'] = 0
            self.proto_state['account_has_characters'] = True
            if not hasattr(self, 'saved_character_states'):
                self.saved_character_states = {}
            if not hasattr(self, 'saved_server_states'):
                self.saved_server_states = {}
            fresh_state = self._default_canonical_character_state()
            if not self._save_canonical_character_state(
                    fresh_state,
                    mutation={
                        'kind': 'character_create',
                        'request_opcode': '0x0004',
                        'packet_seq': int(pkt_num),
                        'changed_fields': [
                            'character', 'snapshot_hex', 'inventory',
                            'active_loadouts', 'runtime_rows', 'currency',
                        ],
                    }):
                for key, (existed, value) in identity_before.items():
                    if existed:
                        self.proto_state[key] = value
                    else:
                        self.proto_state.pop(key, None)
                print("  [PROTO] Rejecting character creation: state save failed")
                return None
            self._bind_selected_character_identity()
            self.proto_state.pop('explicit_character_logout', None)
            self.proto_state.pop('logout_completion_0007_seen', None)
            self.proto_state.pop('logout_completion_0001_seen', None)
            slots[character_slot] = {
                'slot': character_slot,
                'storage_slot': storage_slot,
                'name_hex': char_name.hex(),
                'species': char_type,
                'level': 0,
                'evolution': 0,
                'path': self._canonical_state_path(),
            }
            self.proto_state['lobby_slots'] = slots
            # G2C_CREATEEGG_ACK is S2C 0006.  Result 0 closes and purges the
            # SelectEgg popup, resets the local create seed, and makes the
            # client emit a fresh C2S 0007.  Return only this ACK from the
            # C2S 0004 request.  The resulting client round trip separates it
            # from the 0007 room bundle that answers the natural request.
            self.proto_state['zone_request_count'] = 0
            self.proto_state['fresh_create_ack_sent'] = True
            responses += self._make_packet(0x0006, b'\x00\x00')

            print(
                "  [PROTO] G2C_CREATEEGG_ACK: immediate standalone "
                "S2C 0x0006[00,00]; waiting for natural C2S 0x0007"
            )
            return bytes(responses)

        elif opcode == 0x0001:
            # The normal character-logout completion is C2S 0007 followed by
            # empty C2S 0001.  Live testing proved that neither the empty 0002
            # ACK nor a later 0000 roster refresh repaints the four-slot UI:
            # the client stays on its loading screen.  A one-byte-zero S2C
            # 0001 follows the original exit handler and cleanly disconnects
            # the client; the browser wrapper then returns to server select.
            # Outside the explicit logout flow retain the historical ignore.
            if (len(payload) == 0
                    and self.proto_state.get('explicit_character_logout')):
                self.proto_state['logout_completion_0001_seen'] = True
                self.proto_state['logout_exit_response_sent'] = True
                print(
                    "  [PROTO] Character logout completion C2S 0x0001 "
                    "-> S2C 0x0001[00] clean client exit"
                )
                return self._make_packet(0x0001, b'\x00')
            print(f"  [PROTO] Client sent 0x0001 (disconnect?), payload={len(payload)}B - IGNORING (no echo)")
            return None

        elif opcode == 0x0002:
            # Original MainMenu LogOut contract: an exact empty request asks
            # the server to release only the active character/session actor,
            # then S2C 0002 returns the client to its already-populated four-
            # slot lobby.  Account identity, lobby_slots and canonical files
            # deliberately survive this transition.
            if len(payload) != 0:
                print(
                    f"  [PROTO] Rejecting malformed character logout: "
                    f"{len(payload)}B"
                )
                return None
            if self._selected_character_state_key() is None:
                print("  [PROTO] Rejecting character logout without active selection")
                return None
            self._release_character_session_for_logout(pkt_num=pkt_num)
            print("  [PROTO] Character logout accepted -> S2C 0x0002[0B]")
            return self._make_packet(0x0002)

        elif opcode == 0x0005:
            # Character-slot selection/continue is client->server in the
            # original login trace.  The reference capture sends this one
            # byte selector immediately before the first room path (0x0003),
            # while a client that was already auto-created may never emit
            # 0x0004.  Resolve the one-byte wire slot through the dense lobby
            # map before replaying the known-good bootstrap bundle.  This is
            # direction-specific; it is not an echo of S->C 0x0005.
            print(f"  [PROTO] Client 0x0005 slot/continue: payload={payload.hex()}")
            if len(payload) != 1 or payload[0] > 3:
                return None
            logical_slot = payload[0]
            slot_record = (self.proto_state.get('lobby_slots') or {}).get(logical_slot)
            if not slot_record:
                print(f"  [PROTO] Rejecting unoccupied character slot {logical_slot}")
                return None
            storage_slot = int(slot_record.get('storage_slot', logical_slot))
            species = int(slot_record.get('species', -1))
            evolution = int(slot_record.get('evolution', -1))
            if (storage_slot not in range(4) or species not in range(4)
                    or evolution not in range(4)):
                print(f"  [PROTO] Rejecting invalid character slot record {logical_slot}")
                return None
            selected_name_raw = bytes.fromhex(slot_record['name_hex'])
            if self._character_session_in_use(
                    self.proto_state.get('account_raw') or b'',
                    storage_slot, selected_name_raw):
                self.proto_state['last_character_select_reject'] = {
                    'logical_slot': logical_slot,
                    'storage_slot': storage_slot,
                    'reason': 'character already active on another connection',
                }
                print(
                    f"  [PROTO] Rejecting duplicate live character session "
                    f"slot={storage_slot}"
                )
                return None
            self.proto_state['wire_character_slot'] = logical_slot
            self.proto_state['character_slot'] = storage_slot
            self.proto_state['char_created'] = True
            self.proto_state['char_type'] = species
            self.proto_state['selected_evolution'] = evolution
            self.proto_state['char_name_raw'] = selected_name_raw
            self._bind_selected_character_identity()
            self.proto_state.pop('explicit_character_logout', None)
            self.proto_state.pop('logout_completion_0007_seen', None)
            self.proto_state.pop('logout_completion_0001_seen', None)
            enter_space = self._build_enter_space_0003_draft()
            zone_payload = self._build_zone_0007_draft(b'\x00' * 196)
            zone_state = struct.unpack_from('<I', zone_payload, 0x07)[0]
            responses = bytearray()
            responses += self._make_packet(0x0003, enter_space)
            responses += self._make_packet(0x0007, zone_payload)
            responses += self._make_packet(0x0005, self._build_post_load_0005_draft(state_value=zone_state))
            responses += self._make_packet(0x000A, self._build_item_registry_000A_draft())
            responses += self._make_packet(0x000B, self._build_stat_table_0011_draft())
            self.proto_state['zone_request_count'] = max(1, self.proto_state.get('zone_request_count', 0))
            print("  [PROTO] Client 0x0005 -> replaying 0x0003 + 0x0007 bootstrap bundle")
            return bytes(responses)

        elif opcode == 0x0006:
            # Native delete request: C2S 0006 [slot:u8].  The response is
            # direction-specific S2C 0008 [slot,result], result 0=success.
            slot = payload[0] if len(payload) == 1 else 0xFF
            slots = dict(self.proto_state.get('lobby_slots') or {})
            record = slots.get(slot) if slot in range(4) else None
            delete_key = None
            if isinstance(record, dict):
                account_raw = self.proto_state.get('account_raw') or b''
                if isinstance(account_raw, str):
                    account_raw = account_raw.encode('cp949', errors='ignore')
                account_hex = bytes(account_raw).split(b'\x00', 1)[0][:13].hex()
                name_hex = record.get('name_hex')
                storage_slot = record.get('storage_slot', slot)
                if (account_hex and isinstance(name_hex, str)
                        and int(storage_slot) in range(4)):
                    delete_key = f'a{account_hex}_s{int(storage_slot)}_c{name_hex}'
            # Durable storage slots may be sparse.  The archive helper compacts
            # only the surviving logical lobby keys after a successful delete,
            # preserving the native count/next-create invariant.
            self._last_character_archive_result = {
                'status': 'rejected', 'moved_files': 0,
                'rollback_attempted': False, 'rollback_failed': False,
                'reason': 'delete precondition failed before archive',
            }
            success = (
                len(payload) == 1
                and slot <= 3
                and sorted(slots) == list(range(len(slots)))
                and self._archive_account_character_slot(slot)
            )
            result = 0 if success else 1
            self.proto_state['last_character_delete'] = {
                'slot': slot,
                'status': 'archived' if success else 'rejected',
            }
            archive_result = dict(getattr(
                self, '_last_character_archive_result', {}
            ))
            self._record_mutation_transaction(
                {
                    'kind': 'character_delete',
                    'request_opcode': '0x0006',
                    'packet_seq': pkt_num,
                    'changed_fields': ['character_roster', 'canonical_archive'],
                    'slot': slot,
                    'archive': archive_result,
                },
                'committed' if success else 'rejected',
                key=delete_key,
                reason=None if success else (
                    archive_result.get('reason') or
                    'delete requires a dense logical slot and archive success'
                ),
            )
            print(
                f"  [PROTO] Character delete slot={slot} "
                f"result={'success' if success else 'failure'}"
            )
            return self._make_packet(0x0008, bytes((slot & 0xFF, result)))

        elif opcode == 0x0007:
            # ── Map/zone data request? (196B payload seen after char creation) ──
            print(f"  [PROTO] opcode 0x0007: payload={len(payload)}B")
            print(f"  [PROTO] Full payload hex: {payload.hex()}")
            # S2C 0002 naturally makes the client serialize once more before
            # its empty C2S 0001 completion.  The authoritative pre-logout
            # 0007 was already persisted while the lease was valid; accept
            # this duplicate without rebinding a character or writing through
            # the now-unselected placeholder identity.
            if (self.proto_state.get('explicit_character_logout')
                    and len(payload) >= 0xC4):
                self.proto_state['logout_completion_0007_seen'] = True
                print(
                    "  [STATE] Accepted post-ACK logout C2S 0x0007; "
                    "preserving the prior canonical save"
                )
                return None
            if self._selected_character_state_key() is None:
                self.proto_state['last_state_save_reject'] = {
                    'reason': 'zone/state request requires selected character identity',
                }
                print(
                    "  [STATE] Rejecting C2S 0x0007 without selected "
                    "character identity"
                )
                return None
            fresh_create_ack = bool(
                self.proto_state.get('fresh_create_ack_sent')
            )
            self.proto_state['client_0007_count'] = self.proto_state.get('client_0007_count', 0) + 1
            client_count = self.proto_state['client_0007_count']

            # Once the server has already emitted the proactive zone bundle,
            # every later 196-byte C2S 0x0007 is a client property snapshot,
            # including the first such client packet.  Static tracing proves
            # a normal Gym completion may emit exactly this single snapshot.
            # The old client_count > 1 heuristic discarded it and could lose
            # the whole action.  Only a packet received before any zone bundle
            # remains eligible to act as the legacy bootstrap request below.
            zone_bundle_sent = self.proto_state.get('zone_request_count', 0) >= 1
            if zone_bundle_sent and len(payload) >= 0xC4:
                saved = self._save_character_state_snapshot(payload)
                if saved:
                    self.proto_state['content_save_count'] = self.proto_state.get('content_save_count', 0) + 1
                    stats = struct.unpack_from('<70H', payload, 0x0A)
                    stat_sum = struct.unpack_from('<I', payload, 0x96)[0]
                    calculated_sum = sum(stats[0x1E:0x42]) & 0xFFFFFFFF
                    self.proto_state['last_content_save_stat_0x1F'] = stats[0x1F]
                    self.proto_state['last_content_save_stat_0x20'] = stats[0x20]
                    self.proto_state['last_content_save_stat_0x21'] = stats[0x21]
                    self.proto_state['last_content_save_sum'] = stat_sum
                    self.proto_state['last_content_save_sum_calculated'] = calculated_sum
                    self.proto_state['last_content_save_sum_matches'] = stat_sum == calculated_sum
                    print(
                        f"  [STATE] Stored content snapshot #{self.proto_state['content_save_count']} "
                        f"(client 0x0007 #{client_count}, "
                        f"gym[0x1F..0x21]={stats[0x1F]}/{stats[0x20]}/{stats[0x21]}, "
                        f"sum=0x{stat_sum:08X}, calculated=0x{calculated_sum:08X})"
                    )
                    entity_id = self._entity_id_for_proto_state(self.proto_state)
                    self._add_event(
                        'content_save',
                        f"클라이언트 #{entity_id} 콘텐츠 상태를 저장했습니다.",
                        entity_id=entity_id, severity='ok',
                        details={
                            'save_count': self.proto_state['content_save_count'],
                            'pushup_stat_0x1f': stats[0x1F],
                            'dumbbell_stat_0x20': stats[0x20],
                            'rope_skipping_stat_0x21': stats[0x21],
                            'sum_matches': stat_sum == calculated_sum,
                        },
                    )
                return None

            self.proto_state['zone_request_count'] = self.proto_state.get('zone_request_count', 0) + 1
            self.proto_state['last_zone_request_payload'] = payload.hex()
            self.proto_state['zone_request_seen'] = True

            if self.proto_state['zone_request_count'] > 1:
                # Repeated 0x0007: do NOT resend full bundle — it causes a reload loop.
                # The first response already armed the loading path.
                print(
                    f"  [PROTO] Repeated client 0x0007 #{self.proto_state['zone_request_count']} - "
                    f"IGNORING (bundle already sent, avoid reload loop)"
                )
                return None


            if fresh_create_ack:
                self.proto_state['fresh_character_create_in_progress'] = True
            try:
                zone_payload = self._build_zone_0007_draft(payload)
            finally:
                if fresh_create_ack:
                    self.proto_state.pop(
                        'fresh_character_create_in_progress', None
                    )
            zone_state_word = struct.unpack_from('<I', zone_payload, 0x07)[0]
            responses = bytearray()
            if fresh_create_ack:
                responses += self._make_packet(
                    0x0003, self._build_enter_space_0003_draft()
                )
                self.proto_state.pop('fresh_create_ack_sent', None)
            responses += self._make_packet(0x0007, zone_payload)
            responses += self._make_packet(0x0005, self._build_post_load_0005_draft(state_value=zone_state_word))
            responses += self._make_packet(0x000A, self._build_item_registry_000A_draft())
            responses += self._make_packet(0x000B, self._build_stat_table_0011_draft())

            print(
                "  [PROTO] Responding: "
                f"0x0007 draft ({len(zone_payload)}B) + "
                f"0x0005 draft (6B, state=0x{zone_state_word:08X}) + "
                "0x000A item registry (150B) + "
                "0x000B XP curve (62B)"
            )
            return bytes(responses)

        elif opcode in (0x000D, 0x000E, 0x000F):
            return self._process_item_use(opcode, payload, pkt_num=pkt_num)

        elif opcode == 0x0013:
            # Exact shop commit: 45B [count:u8][total:u32][item:u16 x20].
            # S2C 0x0005 subtype 0x13 is mandatory on both outcomes; it
            # unlocks the client, applies pending items on success, and sets
            # model+0x1F0 to the authoritative new balance.
            ack_payload = self._process_purchase_0013(payload, pkt_num=pkt_num)
            return self._make_packet(0x0005, ack_payload)

        elif opcode == 0x0014:
            return self._process_item_consume_0014(payload, pkt_num=pkt_num)

        elif opcode == 0x0017:
            # ── Post-creation opcode (6B payload: 07 01 00 00 00 00) ──
            print(f"  [PROTO] opcode 0x0017: payload={len(payload)}B")
            print(f"  [PROTO] Full payload hex: {payload.hex()}")
            selected_key = self._selected_character_state_key()
            if selected_key is None:
                self.proto_state['last_c2s_0017_reject'] = {
                    'reason': 'stat authority requires selected character identity',
                    'payload': payload.hex(),
                }
                print(
                    "  [STATE] Rejecting C2S 0x0017 without selected "
                    "character identity"
                )
                return None
            stat_id = 0
            if len(payload) == 6:
                kind, stat_id, value = struct.unpack('<BBI', payload)
                print(f"  [PROTO] Parsed 0x0017 => kind=0x{kind:02X}, stat_id=0x{stat_id:02X}, value=0x{value:08X}")
                if kind == 0x07 and stat_id in (0x37, 0x38):
                    authority = self.proto_state.setdefault('c2s_0017_stat_authority', {})
                    authority[stat_id] = value & 0xFFFF
                    self.proto_state['c2s_0017_authority_key'] = selected_key
                    self.proto_state['last_c2s_0017_authoritative_stat'] = stat_id
                    print(
                        f"  [STATE] C2S 0x0017 authoritative stat[{stat_id}]="
                        f"{authority[stat_id]} retained across periodic 0x0007 saves"
                    )
            self.proto_state['post_create_seen'] = True
            # S->C 0x0064 DISABLED from 0x0017 handler — natural bootstrap handles it
            if not self.proto_state.get('post_0017_followup_sent'):
                self.proto_state['post_0017_followup_sent'] = True
                print("  [PROTO] First 0x0017 - NOT sending 0x0064 (natural bootstrap active)")
            # Repeated 0x0017 is a client status/event report.  Do not turn it
            # into an unsolicited room transition: S->C 0x006E is the
            # diagnostic OX ready-commit and must only be emitted when the
            # operator explicitly selected the `both` reply mode.
            self.proto_state['post_0017_repeat_count'] = self.proto_state.get('post_0017_repeat_count', 0) + 1
            count = self.proto_state['post_0017_repeat_count']
            if PLAZA_REPLY_MODE == 'both' and count <= 3:
                print(f"  [PROTO] Repeated 0x0017 #{count} - diagnostic mode: sending 0x006E ready")
                responses = bytearray()
                responses += self._make_packet(0x006E, bytes([0x00, 0x00]))
                return bytes(responses)
            if count <= 3:
                print(f"  [PROTO] Repeated 0x0017 #{count} - no automatic 0x006E (mode={PLAZA_REPLY_MODE})")
            return None

        elif opcode in (0x0008, 0x0009, 0x000A):
            # ── Client zone/state sync (41B payload) ──
            # S->C 0x0064 crashes here because Calendar subsystem (FUN_005b59b0) is not
            # yet initialized. Calendar init requires an unknown prerequisite we haven't found.
            # PatHouse works fine WITHOUT 0x0064 (proactive 0x0007 handles everything).
            print(f"  [PROTO] Client 0x{opcode:04X} inventory snapshot: payload={len(payload)}B")
            self.proto_state[f'client_{opcode:04x}_seen'] = True
            return self._process_inventory_snapshot(opcode, payload, pkt_num=pkt_num)

        elif opcode == 0x0010:
            # ── Client stat update (2B payload) ──
            print(f"  [PROTO] Client 0x0010 growth edge: payload={payload.hex()}")
            return self._process_growth_route_0010(payload, pkt_num=pkt_num)

        elif opcode == 0x0011:
            # ── Client extended stat/event (80B payload) ──
            print(f"  [PROTO] Client 0x0011 runtime rows: payload={len(payload)}B")
            return self._process_runtime_rows_0011(payload, pkt_num=pkt_num)

        elif opcode == 0x0012:
            print(f"  [PROTO] Client 0x0012 quest corn reward: payload={payload.hex()}")
            return self._process_quest_reward_0012(payload, pkt_num=pkt_num)

        elif opcode == 0x0018:
            # _handle_client already committed the canonical update and sent
            # the exact recipient-local S2C 0x000C ACK/broadcast.
            print(
                f"  [PROTO] Client 0x0018 accessory request: payload={payload.hex()}"
            )
            return None

        elif opcode in (0x0069, 0x006A):
            # The socket dispatcher validates and records these requests.
            # Their original server replies are still unknown.
            return None

        elif opcode == 0x006C:
            # Direction-specific translation is performed by
            # _relay_community_006c before response construction.
            return None

        elif opcode == 0x0019:
            self.proto_state['door_0019_seen'] = True
            self.proto_state['door_0019_count'] = self.proto_state.get('door_0019_count', 0) + 1
            if not LEGACY_0019_MEMORY_SHORTCUT:
                # Natural PatHouse outside contract.  The client exposes this
                # action only when S2C0007 payload[2] (evolution) is nonzero.
                # The proven 0064-only Plaza route begins with S2C000D[00]
                # and then answers the client's own calibration requests; it
                # does not require the old WriteProcessMemory shortcut.
                self.proto_state['hansol_calibration_active'] = True
                self.proto_state['hansol_calibration_samples_sent'] = 0
                self.proto_state['calib_0004_count'] = 0
                self.proto_state['client_0064_seen'] = False
                self.proto_state['client_0064_count'] = 0
                entity_id = self._entity_id_for_proto_state(self.proto_state)
                self._add_event(
                    'transition',
                    f'클라이언트 #{entity_id}의 자연 PatHouse 외출 요청을 승인했습니다.',
                    entity_id=entity_id, severity='ok',
                    details={'c2s': '0x0019[00]', 's2c': '0x000D[00]', 'memory_shortcut': False},
                )
                print(
                    "  [PROTO] Client 0x0019 natural outside request -> "
                    "S2C 0x000D[00] (request-driven calibration armed, no memory write)"
                )
                return self._make_packet(0x000D, b'\x00')

            # ── Door click / PatHouse -> Plaza transition ──
            # S->C 0x000D crashes from PatHouse (vtable not initialized for Plaza subsystems).
            # Instead: set gm+0x31c72=1 via memory, send proactive 0x0003+0x0007 bundle.
            # Gate stays -1 (no 0x0002), so loading pipeline runs naturally:
            #   FUN_005ca6c0 -> FUN_0050a880 -> ButtonQueue_Push(11) -> level_load("hansol.wmb")
            print("  [LEGACY] Client 0x0019 - memory shortcut + proactive bundle (diagnostic opt-in)")
            gm_real = find_real_gm(self.hProcess)
            if gm_real:
                old_prot = wt.DWORD(0)
                # Set gm+0x31c71=1 (hansol permission) + gm+0x31c72=1 (hansol pending)
                for off in [0x31c71, 0x31c72]:
                    addr = gm_real + off
                    kernel32.VirtualProtectEx(self.hProcess, ctypes.c_void_p(addr), 1,
                                              PAGE_READWRITE, ctypes.byref(old_prot))
                    write_mem(self.hProcess, addr, b'\x01')
                    kernel32.VirtualProtectEx(self.hProcess, ctypes.c_void_p(addr), 1,
                                              old_prot.value, ctypes.byref(old_prot))
                print(f"  [PROTO] Set gm+0x31c72=1 (hansol flag)")
            else:
                print(f"  [WARN] Could not find GM - Plaza transition may fail")
            # Reset calibration so gm+0x31c71 gets set via heartbeat 0x0004 samples
            self.proto_state['calib_0004_count'] = 0
            self.proto_state['zone_request_count'] = 0
            # Send proactive bundle (no 0x0002!)
            responses = bytearray()
            plaza_path = b'Data\\Space\\Plaza\x00'
            responses += self._make_packet(0x0003, b'\x01' + plaza_path)
            zone_payload = self._build_zone_0007_draft(b'\x00' * 196)
            zone_state = struct.unpack_from('<I', zone_payload, 0x07)[0]
            responses += self._make_packet(0x0007, zone_payload)
            responses += self._make_packet(0x0005, self._build_post_load_0005_draft(state_value=zone_state))
            responses += self._make_packet(0x000A, self._build_item_registry_000A_draft())
            responses += self._make_packet(0x000B, self._build_stat_table_0011_draft())
            return bytes(responses)

        elif opcode == 0x0064:
            # C->S 0x0064 (1 byte bootstrap status from Hansol Stage 0)
            # Calendar/subsystems are now initialized (S->C 0x0064 was sent during PatHouse
            # entry via C->S 0x0008 handler). pan_create panels survive level_load.
            # Respond immediately with authoritative S->C 0x0064 for Plaza.
            # The optional 0x006E reply is diagnostic: its ready commit queues
            # the OX room, so the supported default leaves it out.
            print(f"  [PROTO] Client 0x0064 bootstrap status: payload={payload.hex()}")
            self.proto_state['client_0064_seen'] = True
            self.proto_state['hansol_calibration_active'] = False
            self.proto_state['client_0064_count'] = self.proto_state.get('client_0064_count', 0) + 1
            count = self.proto_state['client_0064_count']
            char_type = self.proto_state.get('char_type', AZRON_SPECIES) & 0xFF
            entry_kind = int(self.proto_state.get('state_0064_entry_kind', STATE_0064_ENTRY_KIND)) & 0xFF
            s2c_0064 = self._build_state_0064_draft(
                entity_id=1,
                entry_kind=entry_kind,
                selector_0=char_type,
                selector_1=char_type,
            )
            responses = bytearray()
            sent = []
            if PLAZA_REPLY_MODE in {'both', '0064'}:
                responses += self._make_packet(0x0064, s2c_0064)
                sent.append('0x0064')
                self.proto_state['full_0064_sent'] = True
            if PLAZA_REPLY_MODE in {'both', '006e'}:
                responses += self._make_packet(0x006E, bytes([0x00, 0x00]))
                sent.append('0x006E')
                self.proto_state['late_006e_sent'] = True
            summary = ' + '.join(sent) if sent else 'no reply'
            print(f"  [PROTO] C->S 0x0064 #{count} - {summary} "
                  f"(mode={PLAZA_REPLY_MODE}, entry_kind=0x{entry_kind:02X})")
            return bytes(responses) if responses else None

        else:
            # ── Unknown opcode - log it fully ──
            print(f"  [PROTO] *** NEW opcode 0x{opcode:04X}! payload={len(payload)}B ***")
            print(f"  [PROTO] Full payload hex: {payload.hex()}")

            print("  [PROTO] Unknown opcode observed - LOGGING ONLY, no automatic echo")
            return None

    def stop(self):
        self.running = False
        self._stop_ox_scheduler()
        # Release anything stuck at the pause gate, or handler threads hang forever.
        self.set_paused(False)
        for c in list(self.connections):
            try:
                c.close()
            except:
                pass
        # Close log files
        try:
            footer = f"\n{'='*60}\nSession ended: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            for f in (self.capture_file, self.log_file):
                f.write(footer)
                f.flush()
                f.close()
            print(f"\n[SAVED] Capture: {self.capture_path}")
            print(f"[SAVED] Packet log: {self.log_path}")
        except:
            pass
        # Structured durability must not depend on the legacy footer path.
        try:
            self.structured_capture.close()
            print(f"[SAVED] Structured capture: {self.structured_capture.packet_path}")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════
def main():
    exe_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(exe_dir, "Azrok.exe")

    print("=" * 60)
    print("  Azrok Plaza - Server Emulator")
    print(f"  Local server: 127.0.0.1:{SERVER_PORT}")
    print("=" * 60)
    print()

    if not os.path.exists(exe_path):
        print(f"[ERROR] {exe_path} not found!")
        return

    ENTRY_POINT   = 0x004DCC4E
    IAT_CONNECT   = 0x006F0A0C

    # ── Start local TCP server ──
    print("[1] Starting local TCP server...")
    server = AzrokServer(SERVER_PORT, log_dir=exe_dir)
    server.start()
    time.sleep(0.5)

    # ── Create process suspended ──
    print("[2] Creating Azrok.exe (SUSPENDED)...")
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()

    ok = kernel32.CreateProcessW(
        exe_path, None, None, None, False,
        CREATE_SUSPENDED, None, exe_dir,
        ctypes.byref(si), ctypes.byref(pi))

    if not ok:
        print(f"[ERROR] CreateProcess failed: {ctypes.GetLastError()}")
        server.stop()
        return

    hProcess = pi.hProcess
    hThread = pi.hThread
    server.attach_process(hProcess)
    print(f"    PID={pi.dwProcessId}")

    try:
        # ── Entry point stomping ──
        print("[3] Entry point stomping...")
        original_ep = read_mem(hProcess, ENTRY_POINT, 2)
        if not original_ep:
            print("[ERROR] Cannot read entry point!")
            kernel32.TerminateProcess(hProcess, 1)
            return

        old_prot = wt.DWORD(0)
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ENTRY_POINT), 2,
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        write_mem(hProcess, ENTRY_POINT, b'\xEB\xFE')  # jmp $
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ENTRY_POINT), 2,
                                   old_prot.value, ctypes.byref(old_prot))

        # Resume for loader
        print("[4] Running loader...")
        if PRE_LOADER_DELAY_MS > 0:
            print(f"    [WAIT] Pre-loader delay: {PRE_LOADER_DELAY_MS} ms")
            time.sleep(PRE_LOADER_DELAY_MS / 1000.0)
        kernel32.ResumeThread(hThread)
        time.sleep(3)

        # Read resolved IAT
        real_connect = read_dword(hProcess, IAT_CONNECT)
        print(f"    real connect() = 0x{real_connect:08X}")

        if real_connect < 0x10000000:
            print("[WARNING] IAT may not be resolved, waiting more...")
            time.sleep(3)
            real_connect = read_dword(hProcess, IAT_CONNECT)
            print(f"    real connect() = 0x{real_connect:08X}")

        if real_connect < 0x10000:
            print("[ERROR] Cannot resolve IAT!")
            kernel32.TerminateProcess(hProcess, 1)
            return

        # Suspend for patching
        kernel32.SuspendThread(hThread)

        # Patch acknex.dll nexus default BEFORE engine_open runs
        # At VA 0x10017EF0: MOV [0x102FC540], 0x28 (C7 05 40C52F10 28000000)
        # Change the immediate value 0x28 (40) to 0xC8 (200) at offset +6
        ACKNEX_NEXUS_DEFAULT_VA = 0x10017EF6  # byte containing 0x28
        old_prot_nx = wt.DWORD(0)
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ACKNEX_NEXUS_DEFAULT_VA), 1,
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot_nx))
        orig_nx = read_mem(hProcess, ACKNEX_NEXUS_DEFAULT_VA, 1)
        if orig_nx == b'\x28':
            write_mem(hProcess, ACKNEX_NEXUS_DEFAULT_VA, b'\xc8')
            print("    [PATCH] Acknex nexus default: 40 -> 200 (before engine_open)")
        else:
            print(f"    [WARN] Unexpected nexus default byte: {orig_nx.hex() if orig_nx else 'None'}")
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ACKNEX_NEXUS_DEFAULT_VA), 1,
                                   old_prot_nx.value, ctypes.byref(old_prot_nx))

        # NOP out WDL script nexus overrides so our default of 200 sticks
        # Two sites in acknex.dll write parsed WDL value: MOV [0x102FC540], EAX (A3 40 C5 2F 10)
        WDL_NEXUS_OVERRIDE_SITES = [0x10018414, 0x1001843D]
        nop5 = b'\x90\x90\x90\x90\x90'
        expected5 = b'\xA3\x40\xC5\x2F\x10'
        for site_va in WDL_NEXUS_OVERRIDE_SITES:
            old_prot_wdl = wt.DWORD(0)
            kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site_va), 5,
                                       PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot_wdl))
            orig_wdl = read_mem(hProcess, site_va, 5)
            if orig_wdl == expected5:
                write_mem(hProcess, site_va, nop5)
                print(f"    [PATCH] WDL nexus override NOPed at 0x{site_va:08X}")
            elif orig_wdl == nop5:
                print(f"    [PATCH] WDL nexus override already NOPed at 0x{site_va:08X}")
            else:
                print(f"    [WARN] Unexpected bytes at WDL nexus override 0x{site_va:08X}: {orig_wdl.hex() if orig_wdl else 'None'}")
            kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(site_va), 5,
                                       old_prot_wdl.value, ctypes.byref(old_prot_wdl))

        # Allocate hook memory
        print("[5] Installing hooks...")
        hook_base = kernel32.VirtualAllocEx(
            hProcess, None, 0x1000,
            MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)

        if not hook_base:
            print(f"[ERROR] VirtualAllocEx failed!")
            kernel32.TerminateProcess(hProcess, 1)
            return

        global hook_base_global
        hook_base_global = hook_base

        # Write hook code
        hook_code = build_connect_hook(hook_base)
        write_mem(hProcess, hook_base, hook_code)
        write_mem(hProcess, hook_base + 0x080, struct.pack('<I', real_connect))
        write_mem(hProcess, hook_base + 0x100, b'\x00' * 32)

        # Patch IAT
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(IAT_CONNECT), 4,
                                   PAGE_READWRITE, ctypes.byref(old_prot))
        write_mem(hProcess, IAT_CONNECT, struct.pack('<I', hook_base))
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(IAT_CONNECT), 4,
                                   old_prot.value, ctypes.byref(old_prot))

        # Restore entry point
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ENTRY_POINT), 2,
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        write_mem(hProcess, ENTRY_POINT, original_ep)
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ENTRY_POINT), 2,
                                   old_prot.value, ctypes.byref(old_prot))

        # ── Apply runtime patches ──
        print("[6] Applying runtime patches...")
        apply_runtime_patches(hProcess, hook_base)

        # Resume game
        print("[7] Starting game with hooks!")
        print()
        if PRE_RESUME_DELAY_MS > 0:
            print(f"    [WAIT] Pre-resume delay: {PRE_RESUME_DELAY_MS} ms")
            time.sleep(PRE_RESUME_DELAY_MS / 1000.0)
        kernel32.ResumeThread(hThread)

        print("=" * 60)
        print("  Game is running. All connect() -> 127.0.0.1:9000")
        print("  Waiting for packets from game...")
        print("  Press Ctrl+C to stop.")
        print("=" * 60)

        # Wait for game to exit
        runtime_last_sig = None
        while True:
            exit_code = wt.DWORD(0)
            kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code))
            if exit_code.value != 259:
                print(f"\n[!] Game exited (code: {exit_code.value})")
                break

            # Check hook log
            flag = read_dword(hProcess, hook_base + 0x108)
            count = read_dword(hProcess, hook_base + 0x114)
            if flag and count > 0:
                port_raw = read_dword(hProcess, hook_base + 0x100) & 0xFFFF
                ip_raw = read_dword(hProcess, hook_base + 0x104)
                port = socket.ntohs(port_raw)
                ip_b = struct.pack('<I', ip_raw)
                ip_str = f"{ip_b[0]}.{ip_b[1]}.{ip_b[2]}.{ip_b[3]}"

                # Only print once
                if not hasattr(main, '_logged'):
                    main._logged = True
                    print(f"\n  [HOOK] connect() intercepted!")
                    print(f"    Original: {ip_str}:{port}")
                    print(f"    Hooked to: 127.0.0.1:{SERVER_PORT}")

            gm = read_dword(hProcess, hook_base + HOOK_LOG_GM_RVA)
            if not gm:
                # 0x006E8430 stores the engine_open result, not the stack-local
                # CGameManager.  Accept only the validated stack scan fallback;
                # if it cannot find the CGameManager vtable, skip this sample.
                gm = find_real_gm(hProcess)
            opcode100_hits = read_dword(hProcess, hook_base + HOOK_LOG_OPCODE100_COUNT_RVA)
            self_init_hits = read_dword(hProcess, hook_base + HOOK_LOG_SELF_INIT_COUNT_RVA)
            if gm:
                state = collect_runtime_state(hProcess, gm, opcode100_hits, self_init_hits)
                state_sig = tuple(state.items())
                if state_sig != runtime_last_sig:
                    runtime_last_sig = state_sig
                    print()
                    print(format_runtime_state(state))

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[!] Stopped by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        kernel32.CloseHandle(hThread)
        kernel32.CloseHandle(hProcess)
        server.stop()

    # Log file is already saved in real-time by the server
    print(f"  Packet log saved at: {server.log_path}")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
