"""Direction- and mode-aware Azrok wire protocol registry.

This module is intentionally stdlib-only and has no dependency on the server,
control panel, or capture tools.  Those consumers can project the immutable
specifications into their own compatibility shapes without maintaining a
second opcode catalog.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping


_DIRECTIONS = frozenset(("C->S", "S->C"))
_MODES = frozenset(("common", "0", "1", "2"))
_STATUSES = frozenset(("VERIFIED", "INFERRED", "NOT VERIFIED"))
_IMPLEMENTATIONS = frozenset(("implemented", "dormant", "fail_closed", "not_verified"))
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class PayloadRule:
    """Typed payload-size constraint.

    ``exact`` is mutually exclusive with range/multiple constraints.  Range
    and multiple constraints may be combined when a future record needs both.
    An unconstrained rule represents a known opcode whose wire size is not yet
    proven; it must not be mistaken for a zero-byte record.
    """

    exact: tuple[int, ...] = ()
    min_length: int | None = None
    max_length: int | None = None
    multiple: int | None = None
    allow_empty: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.exact, tuple):
            raise TypeError("PayloadRule.exact must be a tuple")
        if any(not isinstance(value, int) or value < 0 for value in self.exact):
            raise ValueError("exact payload lengths must be non-negative integers")
        if tuple(sorted(set(self.exact))) != self.exact:
            raise ValueError("exact payload lengths must be sorted and unique")
        if self.exact and any(
            value is not None for value in (self.min_length, self.max_length, self.multiple)
        ):
            raise ValueError("exact payload lengths cannot be combined with range/multiple")
        for label, value in (("min_length", self.min_length), ("max_length", self.max_length)):
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"{label} must be a non-negative integer")
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise ValueError("min_length cannot exceed max_length")
        if self.multiple is not None and (
            not isinstance(self.multiple, int) or self.multiple <= 0
        ):
            raise ValueError("multiple must be a positive integer")

    @property
    def constrained(self) -> bool:
        return bool(self.exact) or any(
            value is not None for value in (self.min_length, self.max_length, self.multiple)
        )

    def length_error(self, size: int) -> str | None:
        if not isinstance(size, int) or size < 0:
            return "contract length must be a non-negative integer"
        if size == 0 and not self.allow_empty:
            return "contract length 0B; empty payload is not allowed"
        if self.exact and size not in self.exact:
            expected = "/".join(str(value) for value in self.exact)
            return f"contract length {size}B; expected {expected}B"
        if self.min_length is not None and size < self.min_length:
            return f"contract length {size}B; expected >= {self.min_length}B"
        if self.max_length is not None and size > self.max_length:
            return f"contract length {size}B; expected <= {self.max_length}B"
        if self.multiple is not None and size % self.multiple:
            return f"contract length {size}B; expected N*{self.multiple}B"
        return None

    def display(self) -> str:
        if self.exact:
            if len(self.exact) == 1:
                return str(self.exact[0])
            return " or ".join(str(value) for value in self.exact)
        if self.min_length is not None and self.max_length is not None:
            return f"{self.min_length}..{self.max_length}"
        if self.min_length is not None:
            return f">={self.min_length}"
        if self.max_length is not None:
            return f"<={self.max_length}"
        if self.multiple is not None:
            return f"{self.multiple}*n"
        return "variable"

    def to_json(self) -> dict[str, object]:
        return {
            "exact": list(self.exact),
            "min": self.min_length,
            "max": self.max_length,
            "multiple": self.multiple,
            "allow_empty": self.allow_empty,
            "constrained": self.constrained,
            "display": self.display(),
        }


@dataclass(frozen=True, slots=True)
class ProtocolSpec:
    direction: str
    modes: tuple[str, ...]
    opcode: int
    name: str
    label: str
    category: str
    payload: PayloadRule
    decoder: str | None = None
    authority: str = "observe"
    persistence: str | None = None
    relay: str | None = None
    risk: str = "normal"
    status: str = "VERIFIED"
    implementation: str = "implemented"
    policy: str = "observe"
    evidence: tuple[str, ...] = ()
    operator_notes: tuple[str, ...] = ()
    legacy_length: str | None = None

    def __post_init__(self) -> None:
        if self.direction not in _DIRECTIONS:
            raise ValueError(f"unsupported direction: {self.direction!r}")
        if not isinstance(self.modes, tuple) or not self.modes:
            raise TypeError("ProtocolSpec.modes must be a non-empty tuple")
        if any(mode not in _MODES for mode in self.modes):
            raise ValueError(f"unsupported modes: {self.modes!r}")
        if len(set(self.modes)) != len(self.modes):
            raise ValueError("ProtocolSpec.modes must be unique")
        if "common" in self.modes and len(self.modes) != 1:
            raise ValueError("common mode cannot be combined with numbered modes")
        if not isinstance(self.opcode, int) or not 0 <= self.opcode <= 0xFFFF:
            raise ValueError("opcode must be a 16-bit unsigned integer")
        if not _NAME_RE.fullmatch(self.name):
            raise ValueError(f"invalid stable protocol name: {self.name!r}")
        if not self.label or not self.category:
            raise ValueError("label and category are required")
        if self.status not in _STATUSES:
            raise ValueError(f"unsupported verification status: {self.status!r}")
        if self.implementation not in _IMPLEMENTATIONS:
            raise ValueError(f"unsupported implementation status: {self.implementation!r}")
        if (
            not isinstance(self.evidence, tuple)
            or not isinstance(self.operator_notes, tuple)
        ):
            raise TypeError("evidence and operator_notes must be tuples")

    @property
    def opcode_hex(self) -> str:
        return f"0x{self.opcode:04X}"

    @property
    def stable_id(self) -> str:
        return f"{self.direction}:{','.join(self.modes)}:{self.opcode_hex}:{self.name}"

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.stable_id,
            "direction": self.direction,
            "modes": list(self.modes),
            "opcode": self.opcode,
            "opcode_hex": self.opcode_hex,
            "name": self.name,
            "label": self.label,
            "category": self.category,
            "payload": self.payload.to_json(),
            "decoder": self.decoder,
            "authority": self.authority,
            "persistence": self.persistence,
            "relay": self.relay,
            "risk": self.risk,
            "status": self.status,
            "implementation": self.implementation,
            "policy": self.policy,
            "evidence": list(self.evidence),
            "operator_notes": list(self.operator_notes),
        }

    def to_legacy_contract(self) -> dict[str, str]:
        return {
            "dir": self.direction,
            "opcode": self.opcode_hex,
            "length": self.legacy_length or self.payload.display(),
            "status": self.status,
            "policy": self.policy,
            "meaning": self.label,
        }


def _exact(*values: int) -> PayloadRule:
    return PayloadRule(exact=tuple(values))


def _minimum(value: int) -> PayloadRule:
    return PayloadRule(min_length=value)


def _range(minimum: int, maximum: int) -> PayloadRule:
    return PayloadRule(min_length=minimum, max_length=maximum)


def _multiple(value: int) -> PayloadRule:
    return PayloadRule(multiple=value)


_ANY = PayloadRule()
_COMMON = ("common",)
_MODE1 = ("1",)
_MODE1_2 = ("1", "2")
_MODE2 = ("2",)


def _spec(
    direction: str,
    opcode: int,
    name: str,
    label: str,
    category: str,
    payload: PayloadRule = _ANY,
    *,
    modes: tuple[str, ...] = _COMMON,
    decoder: str | None = None,
    authority: str | None = None,
    persistence: str | None = None,
    relay: str | None = None,
    risk: str = "normal",
    status: str = "VERIFIED",
    implementation: str = "implemented",
    policy: str = "observe",
    evidence: tuple[str, ...] = (),
    operator_notes: tuple[str, ...] = (),
    legacy_length: str | None = None,
) -> ProtocolSpec:
    if authority is None:
        authority = "client_input" if direction == "C->S" else "server_output"
    return ProtocolSpec(
        direction=direction,
        modes=modes,
        opcode=opcode,
        name=name,
        label=label,
        category=category,
        payload=payload,
        decoder=decoder,
        authority=authority,
        persistence=persistence,
        relay=relay,
        risk=risk,
        status=status,
        implementation=implementation,
        policy=policy,
        evidence=evidence,
        operator_notes=operator_notes,
        legacy_length=legacy_length,
    )


@dataclass(frozen=True, slots=True)
class NativeProtocolSymbol:
    """Recovered source vocabulary, deliberately independent of wire IDs."""

    name: str
    family: str
    role: str
    kind: str = "record_type"
    status: str = "VERIFIED"
    evidence: tuple[str, ...] = ("126",)

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "family": self.family,
            "role": self.role,
            "kind": self.kind,
            "status": self.status,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class NativeProtocolLink:
    """Evidence-rated link from a native symbol to a current wire contract."""

    direction: str
    opcode: int
    native_name: str
    status: str
    qualifier: str = ""
    evidence: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        return {
            "direction": self.direction,
            "opcode": self.opcode,
            "opcode_hex": f"0x{self.opcode:04X}",
            "native_name": self.native_name,
            "status": self.status,
            "qualifier": self.qualifier,
            "evidence": list(self.evidence),
        }


# Original MSVC symbols recovered from the preserved Naver build distinguish
# Client<->Game request/ack structures from the S2C world/session family. The
# 23rd identifier (S2C_PLAZAENTER_ACK) is a raw ILK string identifier rather
# than a PAU<TYPE> function argument, so its kind is kept explicit.
NATIVE_PROTOCOL_SYMBOLS: tuple[NativeProtocolSymbol, ...] = tuple(
    NativeProtocolSymbol(name, family, role)
    for family, name, role in (
        ("C2G", "C2G_QUEST_REQ", "quest request"),
        ("C2G", "C2G_SHOP_REQ", "shop request"),
        ("C2G", "C2G_UPDATEBOOK_REQ", "book inventory update"),
        ("C2G", "C2G_UPDATEGYM_REQ", "gym inventory update"),
        ("C2G", "C2G_UPDATEPLAY_REQ", "toy/play inventory update"),
        ("C2G", "C2G_UPDATEPROPERTY_REQ", "player property update"),
        ("C2G", "C2G_UPDATEQUESTLIST_REQ", "quest-list update"),
        ("C2G", "C2G_UPDATEREFRI_REQ", "refrigerator update"),
        ("C2G", "C2G_USEMARUMONG_REQ", "Marumong use request"),
        ("G2C", "G2C_CREATEEGG_ACK", "egg creation result"),
        ("G2C", "G2C_DELETEPET_ACK", "pet deletion result"),
        ("G2C", "G2C_FUNCORN_ACK", "FunCorn balance update"),
        ("G2C", "G2C_LEVELUPBASIS_ACK", "level-up basis update"),
        ("G2C", "G2C_PRICE_ACK", "shop price catalogue update"),
        ("G2C", "G2C_RESULT_ACK", "game mutation result"),
        ("G2C", "G2C_SELECTPET_ACK", "pet selection result"),
        ("S2C", "S2C_LOGIN_ACK", "login result"),
        ("S2C", "S2C_LOGOUT_ACK", "logout result"),
        ("S2C", "S2C_MOVE_ACK", "movement update"),
        ("S2C", "S2C_NOTICE_ACK", "notice update"),
        ("S2C", "S2C_PLAYERENTER_ACK", "player-enter update"),
        ("S2C", "S2C_STOP_ACK", "movement-stop update"),
    )
) + (
    NativeProtocolSymbol(
        "S2C_PLAZAENTER_ACK", "S2C", "Plaza-enter result",
        kind="string_identifier",
    ),
)

NATIVE_PROTOCOL_LINKS: tuple[NativeProtocolLink, ...] = (
    NativeProtocolLink(
        "C->S", 0x0011, "C2G_UPDATEQUESTLIST_REQ", "VERIFIED",
        qualifier=(
            "STRUCT match: CJSLogic::SendQuestList @ 0x0059DB40; "
            "80B/10 rows and +0x70C storage agree"
        ),
        evidence=("_img2011_symbol_mapping",),
    ),
    NativeProtocolLink(
        "C->S", 0x0013, "C2G_SHOP_REQ", "VERIFIED",
        qualifier=(
            "STRUCT match: CJSLogic::SendShop @ 0x0059DC20; "
            "45B purchase commit caller @ 0x005A9A10"
        ),
        evidence=("66", "86", "126", "_img2011_symbol_mapping"),
    ),
)

ORIGINAL_DISPATCH_SYMBOLS: tuple[str, ...] = (
    "CClientPeer::Protocol(int,void*,int)",
    "CGamePeer::Protocol(int,void*,int)",
    "CGamePeer::AddPacket(int,void*,int)",
    "CPacket::MakePacket(void*,int,void*,int)",
)

# Direct Plaza/Naver symbol convergence.  The u16 header length is the payload
# length, not the total frame length: natural C2S 0x0012 packet #69 in
# captures/packets_20260718_215018.txt is exactly
# 05 00 12 00 28 00 00 00 02 (5B payload, 9B total).
ORIGINAL_WIRE_FRAME = MappingProxyType({
    "byte_order": "little-endian",
    "header_size": 4,
    "header_fields": ("payload_length:u16", "opcode:u16"),
    "total_length": "payload_length + 4",
    "sender_ring_slots": 75,
    "sender_slot_stride": 0x10D,
    "sender_payload_max": 261,
    "receiver_ring_slots": 300,
    "receiver_slot_stride": 0xA9,
    "status": "VERIFIED",
    "evidence": ("_img2011_symbol_mapping", "packets_20260718_215018:#69"),
})

# Only two native request structures currently have a reliable Plaza-address
# link.  The remaining sender rows retain their verified handler/opcode facts
# without inventing a structure name.  In particular, opcode 0x0012 is not
# linked to C2G_QUEST_REQ, and no G2C/S2C native name is linked yet.
ORIGINAL_C2S_SENDERS: tuple[tuple[int, str, int, str | None, str], ...] = (
    (0x0010, "CJSLogic vtable slot 7", 0x0059DAD0, None, "VERIFIED"),
    (0x0011, "CJSLogic::SendQuestList", 0x0059DB40, "C2G_UPDATEQUESTLIST_REQ", "VERIFIED"),
    (0x0012, "CJSLogic reward sender slot 8", 0x0059DC90, None, "VERIFIED"),
    (0x0013, "CJSLogic::SendShop", 0x0059DC20, "C2G_SHOP_REQ", "VERIFIED"),
    (0x0014, "CJSLogic::SendUseItem", 0x0059DC50, None, "VERIFIED"),
    (0x0015, "CJSLogic vtable slot 3", 0x0059DB70, None, "VERIFIED"),
    (0x0017, "CJSLogic::SendErrorReport", 0x0059DCD0, None, "VERIFIED"),
)


# Direction remains part of every key. Natural food-quest completion added the
# previously missing C2S 0x0012 CJSLogic::SendQuest report.
PROTOCOL_SPECS: tuple[ProtocolSpec, ...] = (
    _spec("C->S", 0x0000, "c2s_login_request", "login/connect request", "session", _exact(106), decoder="decode_c2s_login_0000", policy="validate", evidence=("82",)),
    _spec("C->S", 0x0002, "c2s_character_logout", "character logout / lobby return request", "session", _exact(0), persistence="preserve prior snapshot; release selected lease", policy="exact-empty + selected lease", evidence=("564",)),
    _spec("C->S", 0x0004, "c2s_character_create", "character create request", "persistence", _exact(15), persistence="character-create", policy="bind-on-success", evidence=("82",)),
    _spec("C->S", 0x0005, "c2s_character_select", "character slot select", "persistence", _exact(1), persistence="character-bind", policy="lease + bind", evidence=("82", "104")),
    _spec("C->S", 0x0006, "c2s_character_delete", "character delete request", "persistence", _exact(1), persistence="character-delete", policy="archive tail only", evidence=("102",)),
    _spec("C->S", 0x0007, "c2s_character_snapshot", "character snapshot save", "persistence", _exact(196), persistence="snapshot-save", policy="selected-key commit", evidence=("84", "104", "113")),
    _spec("C->S", 0x0008, "c2s_food_ingredient_snapshot", "food + ingredient quantity snapshot", "inventory", _exact(41), decoder="decode_c2s_inventory_snapshot", persistence="inventory-snapshot", policy="selected-key atomic replace; food pad bytes 33..37 zero", evidence=("123",)),
    _spec("C->S", 0x0009, "c2s_toy_snapshot", "toy quantity snapshot", "inventory", _exact(10), decoder="decode_c2s_inventory_snapshot", persistence="inventory-snapshot", policy="selected-key atomic replace", evidence=("123",)),
    _spec("C->S", 0x000A, "c2s_gym_snapshot", "gym quantity snapshot", "inventory", _exact(8), decoder="decode_c2s_inventory_snapshot", persistence="inventory-snapshot", policy="selected-key atomic replace", evidence=("123",)),
    _spec("C->S", 0x000B, "c2s_client_data_unresolved", "client data request/report (details unresolved)", "content", status="NOT VERIFIED", implementation="not_verified", risk="unknown", policy="observe only", evidence=("105",)),
    _spec("C->S", 0x000D, "c2s_toy_loadout", "toy active loadout", "inventory", _exact(4), decoder="decode_c2s_item_use", persistence="inventory-mutation", implementation="dormant", policy="future-compatible, fail-closed", evidence=("90", "98")),
    _spec("C->S", 0x000E, "c2s_gym_loadout", "gym active loadout", "inventory", _exact(3), decoder="decode_c2s_item_use", persistence="inventory-mutation", implementation="dormant", policy="future-compatible, fail-closed", evidence=("90", "98")),
    _spec("C->S", 0x000F, "c2s_energy_consume", "energy consume request", "inventory", _exact(1), decoder="decode_c2s_item_use", persistence="inventory-mutation", policy="atomic consume + ACK", evidence=("90", "108")),
    _spec("C->S", 0x0010, "c2s_growth_route_edge", "growth runtime-row proposal/completion edge", "content", _exact(2), decoder="decode_c2s_growth_route_0010", persistence="runtime-row-correlation", policy="arm only; require 0007 stage edge and 0011 projection", evidence=("123",)),
    _spec("C->S", 0x0011, "c2s_runtime_row_snapshot", "runtime-row full snapshot", "content", _exact(80), decoder="decode_c2s_runtime_rows_0011", persistence="runtime-row-snapshot", policy="selected-key validated projection; preserve server metadata", evidence=("123",)),
    _spec("C->S", 0x0012, "c2s_quest_funcorn_reward", "quest FunCorn reward report", "economy", _exact(5), decoder="decode_c2s_quest_reward_0012", persistence="quest-reward-correlation", policy="channel 2 only; arm exact static reward; adjacent 0011 row removal commits FunCorn atomically", evidence=("78", "125", "126")),
    _spec("C->S", 0x0013, "c2s_shop_purchase", "shop purchase commit", "economy", _exact(45), decoder="decode_c2s_purchase_0013", persistence="currency/inventory-mutation", policy="catalog + FunCorn balance + selected-key", evidence=("66", "86", "104", "126")),
    _spec("C->S", 0x0014, "c2s_item_action_witness", "food/medicine action witness", "inventory", _exact(2), decoder="decode_c2s_item_consume_0014", persistence="medicine-mutation", policy="food waits for 0008; decrement medicine 4000..4005 only", evidence=("123",)),
    _spec("C->S", 0x0016, "c2s_heartbeat", "heartbeat/calibration/facility-exit request", "session", _exact(1), policy="kind 1 in a local facility emits 000D[00] once and arms Plaza calibration", evidence=("82", "592")),
    _spec("C->S", 0x0017, "c2s_stat_report", "stat/activity report", "content", _exact(6), persistence="stat-mutation", policy="selected-key authority", evidence=("84",)),
    _spec("C->S", 0x0018, "c2s_accessory_commit", "accessory equip/clear request", "accessory", _exact(3), decoder="decode_c2s_0018_accessory", persistence="accessory-mutation", policy="validate accessory set/clear", evidence=("109", "111")),
    _spec("C->S", 0x0019, "c2s_pathouse_exit", "PatHouse exit request", "transition", evidence=("54", "82")),
    _spec("C->S", 0x0064, "c2s_plaza_stage0_ready", "Plaza stage-0 ready", "transition", evidence=("75", "82")),
    _spec("C->S", 0x0065, "c2s_room_entry", "room entry report", "room", _minimum(10), decoder="decode_c2s_0065", policy="room membership", evidence=("75", "85")),
    _spec("C->S", 0x0066, "c2s_movement_path", "movement path report", "movement", _exact(22), modes=_MODE1, decoder="decode_c2s_0066", relay="same_room", policy="validate current cell + relay", evidence=("75", "87")),
    _spec("C->S", 0x0067, "c2s_movement_arrival", "arrival/action commit", "movement", _exact(15), modes=_MODE1_2, decoder="decode_c2s_0067", relay="same_room", policy="arrival relay; mode-2 telemetry only", evidence=("75", "87", "97")),
    _spec("C->S", 0x0068, "c2s_plaza_chat", "chat transmit", "community", _range(18, 199), modes=_MODE1, decoder="decode_c2s_0068_chat", relay="same_room", policy="validate + relay", evidence=("80", "87", "89")),
    _spec("C->S", 0x0069, "c2s_plaza_chair_request", "Plaza chair index request", "content", _exact(1), modes=_MODE1, policy="allocate first free original table side 0/1; S2C 006B self + 006C visible peers", evidence=("31", "48", "540")),
    _spec("C->S", 0x006A, "c2s_actor_state_request", "actor state request", "multiplayer", _exact(0), modes=_MODE1, policy="release owned chair; S2C 006B+0069 self and 006C+0069 visible peers", evidence=("48", "75")),
    _spec("C->S", 0x006B, "c2s_ox_portal_request", "OX portal entry request", "transition", _exact(0), modes=_MODE1, policy="solicited S2C 006E[0000] only", evidence=("122",)),
    _spec("C->S", 0x006C, "c2s_user_info_request", "Plaza actor selection / user information request", "community", _exact(4), modes=_MODE1, decoder="decode_c2s_006c_community", policy="visible target; 12-byte reply with client-latched parsing", evidence=("539", "653")),
    _spec("C->S", 0x00C8, "c2s_ox_enter", "OX scene ready/enter", "ox", _exact(0), modes=_MODE2, decoder="decode_c2s_ox_enter_00c8", policy="mode-2 only", evidence=("92", "97")),
    _spec("C->S", 0x00C9, "c2s_ox_leave", "OX teardown/leave", "ox", _exact(1), modes=_MODE2, decoder="decode_c2s_ox_leave_00c9", policy="teardown", evidence=("92", "97")),
    _spec("C->S", 0x00CA, "c2s_ox_answer", "OX side answer/movement", "ox", _exact(22), modes=_MODE2, decoder="decode_c2s_ox_answer_00ca", policy="side/timing validation", evidence=("92", "97")),

    _spec("S->C", 0x0000, "s2c_login_roster", "login state / character roster", "session", _exact(387), policy="server-owned roster", evidence=("82",)),
    _spec("S->C", 0x0001, "s2c_login_result", "login result", "session", _exact(1), evidence=("82",)),
    _spec("S->C", 0x0002, "s2c_character_logout_ack", "character logout / lobby return acknowledgement", "session", _exact(0), policy="emit only for accepted C2S 0002", evidence=("564",)),
    _spec("S->C", 0x0003, "s2c_space_route", "space resource route", "transition", _minimum(2), evidence=("28", "82")),
    _spec("S->C", 0x0004, "s2c_calibration_sample", "bootstrap/Plaza calibration sample", "transition", _exact(5), evidence=("29", "82")),
    _spec("S->C", 0x0005, "s2c_mutation_result", "post-load / FunCorn / purchase result", "persistence", _exact(2, 6), persistence="mutation-result", policy="subtype 0x12=G2C_FUNCORN_ACK balance; 0x13=shop result; 0x00=post-load", evidence=("66", "78", "82", "125", "126")),
    _spec("S->C", 0x0006, "s2c_character_create_result", "character creation result / SelectEgg cleanup", "persistence", _exact(2), persistence="character-create-result", policy="result 0 only after durable create; standalone 0004 response; await natural C2S 0007 before room bundle", evidence=("20", "_img2011_symbol_mapping")),
    _spec("S->C", 0x0007, "s2c_character_restore", "canonical character/content restore", "persistence", _exact(472), persistence="snapshot-restore", policy="canonical overlay", evidence=("84", "113")),
    _spec("S->C", 0x0008, "s2c_character_delete_result", "character delete result", "persistence", _exact(2), persistence="character-delete-result", evidence=("102",)),
    _spec("S->C", 0x0009, "s2c_energy_ack", "energy consume ACK", "inventory", _exact(2), persistence="inventory-mutation-result", policy="after durable decrement only", evidence=("90", "108")),
    _spec("S->C", 0x000A, "s2c_content_auxiliary", "item/evolution auxiliary state", "content", evidence=("82",)),
    _spec("S->C", 0x000B, "s2c_experience_curve", "experience curve", "content", evidence=("82",)),
    _spec("S->C", 0x000C, "s2c_accessory_delta", "accessory actor apply/clear", "accessory", _exact(7), decoder="decode_s2c_000c_accessory", persistence="accessory-mutation-relay", relay="target_actor", policy="accessory relay", evidence=("109", "111")),
    _spec("S->C", 0x000D, "s2c_plaza_transition", "Hansol/Plaza transition start", "transition", _exact(1), risk="caution", policy="emit 00 once after facility C2S 0016[01]; then five 0004[01] calibration replies", evidence=("28", "54", "97", "592")),
    _spec("S->C", 0x0016, "s2c_heartbeat", "heartbeat response", "session", _exact(1), evidence=("82",)),
    _spec("S->C", 0x0064, "s2c_authoritative_self", "authoritative self actor", "multiplayer", modes=_MODE1, policy="self actor commit", evidence=("75", "86"), legacy_length="builder-validated"),
    _spec("S->C", 0x0065, "s2c_roster_reset", "self/remote actor screen reset", "multiplayer", modes=_MODE1, risk="timing_hazard", policy="manual timing hazard", evidence=("51", "75")),
    _spec("S->C", 0x0066, "s2c_remote_actor_upsert", "remote actor upsert", "multiplayer", _multiple(26), modes=_MODE1, decoder="decode_s2c_0066_actor_records", relay="same_room", policy="relay", evidence=("55", "75", "109")),
    _spec("S->C", 0x0067, "s2c_remote_actor_remove", "remote actor remove", "multiplayer", _exact(4), modes=_MODE1, decoder="decode_s2c_actor_remove_0067", relay="same_room", policy="single actor relay", evidence=("52", "75")),
    _spec("S->C", 0x0068, "s2c_remote_actor_position", "remote actor position", "multiplayer", _multiple(24), modes=_MODE1, decoder="decode_s2c_0068_actor_state", relay="same_room", policy="relay", evidence=("51", "75")),
    _spec("S->C", 0x0069, "s2c_remote_actor_state", "remote actor state correction", "multiplayer", modes=_MODE1, risk="unknown", status="NOT VERIFIED", implementation="not_verified", policy="emit disabled", evidence=("75",), legacy_length="unknown fields"),
    _spec("S->C", 0x006A, "s2c_actor_text", "chat/system text relay", "community", modes=_MODE1, relay="same_room", policy="relay/self echo", evidence=("75", "89")),
    _spec("S->C", 0x006B, "s2c_self_chair_toggle", "self chair state toggle", "community", _exact(1), modes=_MODE1, policy="0/1 original seat side; 2 clears self state", evidence=("75", "540")),
    _spec("S->C", 0x006C, "s2c_remote_chair_state", "remote chair state update", "community", _exact(6), modes=_MODE1, policy="same-room visible peer only; side 0/1 or clear 2", evidence=("75", "540")),
    _spec("S->C", 0x006D, "s2c_actor_stage_advance", "actor stage advance", "community", implementation="not_verified", modes=_MODE1, policy="emit disabled; handler enters 0x31 and does not unlock Plaza clicks", evidence=("75",)),
    _spec("S->C", 0x006E, "s2c_ready_commit", "OX ready commit", "transition", _exact(2), modes=_MODE1, risk="plaza_hazard", policy="only after exact C2S 006B", evidence=("30", "75", "122")),
    _spec("S->C", 0x0070, "s2c_user_info", "latched Plaza user-information response", "community", _exact(4, 12), modes=_MODE1, policy="emit 12 bytes; client latch reads 4 or 12", evidence=("23", "75", "653")),
    _spec("S->C", 0x00C8, "s2c_ox_admission", "OX admission/self", "ox", _exact(14), modes=_MODE2, policy="mode-2 only", evidence=("92", "97")),
    _spec("S->C", 0x00C9, "s2c_ox_actor_upsert", "OX remote actor upsert", "ox", PayloadRule(multiple=32, allow_empty=False), modes=_MODE2, decoder="decode_s2c_ox_remote_00c9", policy="mode-2 only; non-empty batch", evidence=("92", "97")),
    _spec("S->C", 0x00CA, "s2c_ox_actor_remove", "OX remote actor remove", "ox", _exact(4), modes=_MODE2, decoder="decode_s2c_ox_actor_remove_00ca", policy="mode-2 only; single actor", evidence=("92", "97")),
    _spec("S->C", 0x00CB, "s2c_ox_loser_list", "OX loser actor list", "ox", _multiple(4), modes=_MODE2, policy="loser list", evidence=("92", "97")),
    _spec("S->C", 0x00CC, "s2c_ox_countdown", "OX ready countdown", "ox", _exact(0), modes=_MODE2, policy="mode-2 only", evidence=("92", "97")),
    _spec("S->C", 0x00CD, "s2c_ox_final_result", "OX final result count", "ox", _multiple(4), modes=_MODE2, policy="exclusive finish cause", evidence=("92", "97")),
    _spec("S->C", 0x00CE, "s2c_ox_question", "OX question record", "ox", _exact(131), modes=_MODE2, policy="bounded authored text", evidence=("92", "97")),
    _spec("S->C", 0x00CF, "s2c_ox_notice_text", "OX question/notice text", "ox", _minimum(1), modes=_MODE2, risk="observe", evidence=("92", "97")),
    _spec("S->C", 0x00D0, "s2c_ox_actor_state", "OX remote actor state", "ox", _exact(24), modes=_MODE2, policy="mode-2 only", evidence=("92", "97")),
    _spec("S->C", 0x00D1, "s2c_ox_forbidden_d1", "OX unhandled dispatcher tombstone", "ox", modes=_MODE2, risk="forbidden", status="VERIFIED", implementation="fail_closed", policy="emit forbidden; no client switch case", evidence=("92",)),
    _spec("S->C", 0x00D2, "s2c_ox_immediate_return", "OX immediate Plaza return", "ox", _exact(0), modes=_MODE2, policy="exclusive finish cause", evidence=("92", "97")),
    _spec("S->C", 0x00D3, "s2c_ox_counter_pair", "OX UI counter pair", "ox", _exact(4), modes=_MODE2, policy="mode-2 only", evidence=("92", "97")),
    _spec("S->C", 0x00D4, "s2c_ox_deferred_exit", "OX deferred exit flag", "ox", _exact(0), modes=_MODE2, policy="exclusive finish cause", evidence=("92", "97")),
)


def _build_indexes(
    specs: Iterable[ProtocolSpec],
) -> tuple[Mapping[tuple[str, str, int], ProtocolSpec], Mapping[tuple[str, int], ProtocolSpec]]:
    by_mode: dict[tuple[str, str, int], ProtocolSpec] = {}
    by_direction: dict[tuple[str, int], ProtocolSpec] = {}
    for spec in specs:
        direction_key = (spec.direction, spec.opcode)
        if direction_key in by_direction:
            raise ValueError(f"duplicate direction/opcode registry entry: {direction_key!r}")
        by_direction[direction_key] = spec
        for mode in spec.modes:
            mode_key = (spec.direction, mode, spec.opcode)
            if mode_key in by_mode:
                raise ValueError(f"duplicate direction/mode/opcode registry entry: {mode_key!r}")
            by_mode[mode_key] = spec
    return MappingProxyType(by_mode), MappingProxyType(by_direction)


PROTOCOL_BY_MODE, PROTOCOL_BY_DIRECTION = _build_indexes(PROTOCOL_SPECS)


def find_spec(direction: str, opcode: int, mode: int | str | None = None) -> ProtocolSpec | None:
    """Return a spec without inferring an unobserved live mode.

    When a mode is supplied, an exact numbered-mode entry wins and a common
    entry is the explicit fallback.  With no mode, the direction/opcode entry
    is returned because this registry currently has one semantic record per
    directional opcode; the record's ``modes`` still describes its legality.
    """

    if mode is None:
        return PROTOCOL_BY_DIRECTION.get((direction, opcode))
    mode_text = str(mode)
    return PROTOCOL_BY_MODE.get((direction, mode_text, opcode)) or PROTOCOL_BY_MODE.get(
        (direction, "common", opcode)
    )


def compute_registry_spec_id(specs: Iterable[ProtocolSpec]) -> str:
    ordered = sorted(
        (spec.to_json() for spec in specs),
        key=lambda row: (
            str(row["direction"]),
            int(row["opcode"]),
            tuple(row["modes"]),
            str(row["name"]),
        ),
    )
    canonical = json.dumps(
        ordered, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


REGISTRY_SPEC_ID = compute_registry_spec_id(PROTOCOL_SPECS)


def compute_metadata_spec_id(
    symbols: Iterable[NativeProtocolSymbol],
    links: Iterable[NativeProtocolLink],
) -> str:
    document = {
        "symbols": sorted(
            (symbol.to_json() for symbol in symbols), key=lambda row: str(row["name"])
        ),
        "links": sorted(
            (link.to_json() for link in links),
            key=lambda row: (
                str(row["direction"]), int(row["opcode"]), str(row["native_name"])
            ),
        ),
        "dispatch_symbols": list(ORIGINAL_DISPATCH_SYMBOLS),
        "wire_frame": dict(ORIGINAL_WIRE_FRAME),
        "c2s_senders": [
            {
                "opcode": opcode,
                "handler": handler,
                "address": address,
                "native_structure": native_structure,
                "status": status,
            }
            for opcode, handler, address, native_structure, status
            in ORIGINAL_C2S_SENDERS
        ],
    }
    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


METADATA_SPEC_ID = compute_metadata_spec_id(
    NATIVE_PROTOCOL_SYMBOLS, NATIVE_PROTOCOL_LINKS
)


def registry_json() -> dict[str, object]:
    """Return a fresh, JSON-serializable typed registry document."""

    return {
        "schema": "azrok.protocol.registry.v1",
        "spec_id": REGISTRY_SPEC_ID,
        "metadata_spec_id": METADATA_SPEC_ID,
        "specs": [spec.to_json() for spec in PROTOCOL_SPECS],
        "native_symbols": [symbol.to_json() for symbol in NATIVE_PROTOCOL_SYMBOLS],
        "native_links": [link.to_json() for link in NATIVE_PROTOCOL_LINKS],
        "native_dispatch_symbols": list(ORIGINAL_DISPATCH_SYMBOLS),
        "native_wire_frame": dict(ORIGINAL_WIRE_FRAME),
        "native_c2s_senders": [
            {
                "opcode": opcode,
                "opcode_hex": f"0x{opcode:04X}",
                "handler": handler,
                "address": address,
                "address_hex": f"0x{address:08X}",
                "native_structure": native_structure,
                "status": status,
            }
            for opcode, handler, address, native_structure, status
            in ORIGINAL_C2S_SENDERS
        ],
    }


def legacy_contracts() -> tuple[dict[str, str], ...]:
    """Project specs into the current control API's six-field contract rows."""

    return tuple(spec.to_legacy_contract() for spec in PROTOCOL_SPECS)


__all__ = (
    "PayloadRule",
    "ProtocolSpec",
    "NativeProtocolSymbol",
    "NativeProtocolLink",
    "PROTOCOL_SPECS",
    "PROTOCOL_BY_MODE",
    "PROTOCOL_BY_DIRECTION",
    "NATIVE_PROTOCOL_SYMBOLS",
    "NATIVE_PROTOCOL_LINKS",
    "ORIGINAL_DISPATCH_SYMBOLS",
    "ORIGINAL_WIRE_FRAME",
    "ORIGINAL_C2S_SENDERS",
    "REGISTRY_SPEC_ID",
    "METADATA_SPEC_ID",
    "compute_registry_spec_id",
    "compute_metadata_spec_id",
    "find_spec",
    "legacy_contracts",
    "registry_json",
)
