#!/usr/bin/env python3
"""Sparse x32dbg observer for Plaza clicks and client packet senders.

This script is intended for a fresh disposable session.  It never generates UI
input or packets.  It records only functions that are expected to run on a real
button event, scene transition, or client send; hot per-frame hit-test/pop
functions are deliberately excluded.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType
from x64dbg_automate.models import BreakpointType
from x32dbg_path import resolve_x32dbg


X32DBG = resolve_x32dbg()

# Sparse checkpoints.  Do not add 0x00518D80 (per-frame hit test) or
# 0x0050FFD0 (queue poll) to the default set: both can stop every frame.
CHECKPOINTS = {
    0x0050FE80: "button_queue_push",
    0x005305D0: "local_event_queue_wrapper",
    0x0050A7F0: "scene_request_enqueue",
    0x0050B400: "room_initializer",
    0x00530FE0: "room_index_to_postload_enqueue",
    0x005318C0: "playroom_five_stage_init",
    0x00531B10: "gym_five_stage_init",
    0x00531D60: "magic_five_stage_init",
    0x00531FB0: "cook_five_stage_init",
    0x00532200: "shop_five_stage_init",
    0x00532470: "library_five_stage_init",
    0x00530890: "playroom_initial_event",
    0x005309B0: "gym_initial_event",
    0x00530AA0: "magic_initial_event",
    0x00530B90: "cook_initial_event",
    0x00530C80: "shop_initial_event",
    0x00530D70: "library_initial_event",
    0x00548000: "playroom_content_builder",
    0x00548B10: "gym_content_builder",
    0x00549650: "magic_content_builder",
    0x00549EF0: "cook_content_builder",
    0x00547C70: "shop_content_builder",
    0x0054AC20: "library_content_builder",
    0x00547BF0: "content_descriptor_insert",
    # 0x005A49B0 is intentionally excluded from the default set: live
    # calibration showed continuous per-frame reads (96 hits in ~11 s).
    0x0055A650: "shop_world_npc_setup",
    0x00542B90: "generic_room_ui_click",
    0x005E6960: "popup_ring_content_producer",
    0x005E7130: "generic_click_helper",
    # 0x0051B1F0 is a temporary click-boundary probe only.  Once a pointer
    # state is active it runs per frame (107 hits in ~23 s), so leaving it in
    # the default observer materially perturbs play.
    0x005ECFF0: "room_door_to_plaza_conditional",
    0x005EE600: "room_door_to_plaza",
    0x005EE7B0: "room_door_to_ox_quiz",
    0x00568770: "room_direct_to_plaza",
    0x00602830: "quiz_direct_to_plaza",
    0x0059DCD0: "send_c2s_0017_builder",
    0x0059D760: "send_c2s_0017_thunk",
    0x0059B0B0: "send_c2s_000c_builder",
    0x006130B0: "send_c2s_0064_builder",
    0x005AB6A0: "send_c2s_generic_thunk",
    0x005AB710: "send_c2s_0064_wire_helper",
    0x005AB760: "send_c2s_0065_builder",
    0x005AB7B0: "send_c2s_0066_builder",
    0x005AB830: "send_c2s_0067_builder",
    0x005AB950: "send_c2s_006c_builder",
    0x005CE8E0: "community_e_toggle_and_send_006c",
    # 0065 is emitted by two scene/state-transition paths.  The post-call
    # checkpoints prove that execution returned from the sender instead of
    # mistaking the outgoing notification for a synchronous request/wait.
    0x00611CD0: "transition_resolver",
    0x006121B0: "transition_region_probe",
    0x006122C0: "transition_apply_and_send_0065",
    0x0061264D: "transition_0065_send_return",
    0x00614D70: "hansol_transition_apply",
    0x00614EA0: "hansol_position_send_0065",
    0x00614F3A: "hansol_0065_send_return",
    0x00614370: "hansol_stage_entry",
    0x006143EC: "hansol_stage0_send",
}

ROOM_CHECKPOINTS = {
    address: CHECKPOINTS[address]
    for address in (
        0x0050A7F0,
        0x0050B400,
        0x00530FE0,
        0x005318C0,
        0x00531B10,
        0x00531D60,
        0x00531FB0,
        0x00532200,
        0x00532470,
        0x005ECFF0,
        0x005EE600,
        0x005EE7B0,
        0x00568770,
        0x00602830,
        0x005AB6A0,
        0x005AB760,
        # 0x00611CD0 and 0x006121B0 are resolver/probe paths, not true
        # transition boundaries.  A live 0x000D run showed 0x00611CD0
        # executing about four times per second (285 hits in 69 seconds).
        # Keep the room profile genuinely low-temperature by observing only
        # the downstream apply/send boundaries.
        0x006122C0,
        0x0061264D,
    )
}

# Stable-PatHouse door-click observer.  This is intentionally narrower than
# the general room profile: it connects a local click/event or door boundary
# to scene selection and the small set of known client send thunks without
# stopping in per-frame hit tests, resolver polling, or stat lookup paths.
DOOR_CHECKPOINTS = {
    address: CHECKPOINTS[address]
    for address in (
        0x0050FE80,  # button queue push (self-disables after ten hits)
        0x005305D0,  # local event wrapper
        0x0050A7F0,  # scene request enqueue
        0x0050B400,  # room initializer
        0x00530FE0,  # local room index -> postload code
        0x005ECFF0,  # conditional door -> Plaza
        0x005EE600,  # door -> Plaza
        0x005EE7B0,  # door -> OX quiz
        0x00568770,  # direct room -> Plaza
        0x00602830,  # quiz -> Plaza
        0x0059D760,  # C2S 0x0017 send thunk
        0x005AB6A0,  # generic C2S send thunk (opcode/payload decoder)
        0x005AB760,  # C2S 0x0065 builder
        0x005AB7B0,  # C2S 0x0066 builder
        0x005AB830,  # C2S 0x0067 builder
        0x005AB950,  # C2S 0x006C builder
        0x006122C0,  # downstream transition apply/send boundary
        0x0061264D,  # C2S 0x0065 send return
    )
}

# Input-free two-client roster observer.  These are packet-dispatch and remote
# actor lifecycle boundaries only; none is a per-frame update or UI hit test.
ROSTER_CHECKPOINTS = {
    0x00615B20: "s2c_0065_flush_remote_actors",
    0x00615B50: "s2c_0066_batch_remote_actor_spawn",
    0x00615D50: "s2c_0068_batch_actor_state",
    0x0050D5D0: "remote_actor_roster_flush_finalize",
    0x0050D790: "remote_actor_ensure_from_0066_record",
    0x005243E0: "remote_actor_init_from_0066_record",
    0x00524620: "remote_actor_finalize_spawn_visual_state",
    0x0050E560: "state1_find_remote_actor_by_id",
}

# Input-free dispatch-gate observer.  This profile is deliberately separate
# from the room/roster profiles: it observes only the startup writer and the
# outer inbound-dispatch gate/mode branch.  It does not send packets, inject
# input, run a macro, or write game memory.  Keep the profile low temperature;
# do not add the state-1 packet handlers here until the gate relationship has
# been measured on a clean client.
GATE_CHECKPOINTS = {
    0x00508B30: "client_peer_startup_initializer",
    0x00594142: "dispatch_gate_write_pre",
    0x00594148: "dispatch_gate_write_post",
    0x00594310: "dispatch_inbound_entry",
    0x00594447: "dispatch_gate_cmp",
    0x00594454: "dispatch_gate_nonzero_path",
    0x00594457: "dispatch_mode_load",
    0x0059445D: "dispatch_mode_latched",
}

# One-action Gym observer.  These checkpoints are reached only by a popup
# selection, the selected local action, its completion/stat executor, or the
# resulting property snapshot.  The two 0x0010/0x0017 builders are negative
# controls: a normal push-up delta should not require either one.
GYM_CHECKPOINTS = {
    # 0x005E3F14 is the per-frame queue consumer.  Its 0x41-only switch
    # target gives the same decisive evidence without throttling the client.
    0x005E511E: "gym_popup_0x41_switch_case",
    0x0055BDB0: "gym_local_sequence_start",
    0x0055EF4F: "gym_action_complete_before_apply",
    0x00596690: "action_stat_executor",
    0x005A4BA0: "stat_delta_apply",
    0x005A4770: "c2s_0007_property_snapshot_build",
    0x00593D10: "generic_c2s_send",
    0x0059DAD0: "c2s_0010_conditional_progress_builder",
    0x0059DCD0: "c2s_0017_out_of_range_clamp_builder",
}

# One-cart Shop observer.  These are cold validation/commit boundaries plus
# the final generic sender.  The CALL-site checkpoint at 0x005A9AB7 is decoded
# specially because its stack still begins with (payload_ptr, 0x2D) before the
# virtual call pushes a return address.
SHOP_CHECKPOINTS = {
    0x005A95B0: "shop_cart_validate_entry",
    0x005A97D5: "shop_money_compare",
    0x005A9AB7: "shop_purchase_virtual_send_call",
    0x00593D10: "generic_c2s_send",
}

# One-move OX answer observer.  OX does not use a dedicated answer opcode:
# the gated route path reaches FUN_0061B510 and serializes movement through
# C2S 0x0066.  FUN_00613C60 is intentionally excluded: live OX-inactive
# measurement proved it is a roughly 5 Hz frame boundary (301 hits/180 s),
# not a cold click boundary, and an ordinary BP can stall the client.
OX_CHECKPOINTS = {
    0x0061B510: "ox_move_route_and_answer_cell",
    0x005AB7B0: "send_c2s_0066_builder",
    0x00593D10: "generic_c2s_send",
}

# One-action PatHouse foodmaker observer.  The cook.wmb academy activity is a
# separate stat-only path; these checkpoints instead cover the refrigerator
# mutation chain reached by the home foodmaker/table.  They are cold entry
# points and leave per-frame hit testing out of the debugger profile.  An
# access violation is recorded by the generic exception branch before detach.
COOK_CHECKPOINTS = {
    0x00596690: "action_stat_executor",
    0x005A8A20: "refrigerator_get_string_food",
    0x0059C270: "inventory_get_group",
    0x0059C120: "inventory_get_group_packet",
    0x0059BE80: "inventory_delete_ingredient",
    0x0059DC50: "send_use_item_0014_builder",
    0x0059BD70: "inventory_add_food",
    0x0059B6D0: "save_refrigerator_0008_builder",
    0x005A4770: "property_snapshot_0007_builder",
    0x00593D10: "generic_c2s_send",
}


def stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def safe_read(client: X64DbgClient, address: int, size: int) -> str:
    if not address or size <= 0:
        return ""
    try:
        return client.read_memory(address, size).hex()
    except Exception as exc:
        return f"<read-error:{type(exc).__name__}>"


def safe_u32(client: X64DbgClient, address: int) -> int | None:
    """Read one little-endian u32 for observation, never for mutation."""
    if not address or address < 0x1000:
        return None
    try:
        raw = client.read_memory(address, 4)
        if len(raw) != 4:
            return None
        return int.from_bytes(raw, "little")
    except Exception:
        return None


def safe_u16(client: X64DbgClient, address: int) -> int | None:
    """Read one little-endian u16 for observation, never for mutation."""
    if not address or address < 0x1000:
        return None
    try:
        raw = client.read_memory(address, 2)
        if len(raw) != 2:
            return None
        return int.from_bytes(raw, "little")
    except Exception:
        return None


def safe_read_cstr(client: X64DbgClient, address: int, size: int = 64) -> str:
    if not address:
        return ""
    try:
        raw = client.read_memory(address, size).split(b"\0", 1)[0]
        return raw.decode("cp949", errors="replace")
    except Exception as exc:
        return f"<read-error:{type(exc).__name__}>"


def main() -> int:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--pid", type=int)
    target.add_argument("--session-pid", type=int)
    parser.add_argument("--log", required=True)
    parser.add_argument("--ready-file", default="")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument(
        "--profile",
        choices=("default", "room", "door", "roster", "gate", "gym", "shop", "ox", "cook"),
        default="default",
    )
    args = parser.parse_args()
    active_checkpoints = {
        "default": CHECKPOINTS,
        "room": ROOM_CHECKPOINTS,
        "door": DOOR_CHECKPOINTS,
        "roster": ROSTER_CHECKPOINTS,
        "gate": GATE_CHECKPOINTS,
        "gym": GYM_CHECKPOINTS,
        "shop": SHOP_CHECKPOINTS,
        "ox": OX_CHECKPOINTS,
        "cook": COOK_CHECKPOINTS,
    }[args.profile]

    log_path = Path(args.log).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ready_path = Path(args.ready_file).resolve() if args.ready_file else None
    if ready_path and ready_path.exists():
        ready_path.unlink()

    output = log_path.open("w", encoding="utf-8", buffering=1)

    def emit(kind: str, **fields) -> None:
        row = {"time": stamp(), "kind": kind, **fields}
        line = json.dumps(row, ensure_ascii=False)
        print(line, flush=True)
        output.write(line + "\n")

    if args.session_pid:
        # Check the IPC registration before constructing a client object: a
        # visible elevated x32dbg window without this lock is not an
        # automatable session and can otherwise block the runner.
        lock_path = Path(tempfile.gettempdir()) / f"xauto_session.{args.session_pid}.lock"
        if not lock_path.exists():
            raise RuntimeError(
                f"xAuto session lock is missing for x32dbg PID {args.session_pid}: {lock_path}"
            )

    client = X64DbgClient(X32DBG)
    debugger_attached = False
    breakpoint_counts: dict[int, int] = {}
    try:
        if args.session_pid:
            client.attach_session(args.session_pid)
            debugger_pid = args.session_pid
            if not client.is_debugging():
                raise RuntimeError("existing x32dbg session has no debuggee")
        else:
            debugger_pid = client.start_session_attach(args.pid)
        debugger_attached = True
        emit("attached", target_pid=args.pid, debugger_pid=debugger_pid)

        existing = {
            int(bp.addr)
            for bp in client.get_breakpoints(BreakpointType.BpNormal)
        }
        # An existing x32dbg session retains breakpoint definitions after a
        # detach.  If those stale definitions are left armed, a supposedly
        # sparse profile can stop on unrelated calibration/TLS checkpoints.
        # This observer owns its dedicated debugger session, so remove every
        # software breakpoint outside the selected profile before continuing.
        stale = sorted(existing - set(active_checkpoints))
        for address in stale:
            if not client.clear_breakpoint(address):
                raise RuntimeError(
                    f"failed to clear stale breakpoint at 0x{address:08X}"
                )
        if stale:
            emit(
                "stale_breakpoints_cleared",
                count=len(stale),
                addresses=[f"0x{address:08X}" for address in stale],
            )
        existing -= set(stale)
        for address, name in active_checkpoints.items():
            if address in existing:
                continue
            # Right after a live attach x32dbg can acknowledge the session
            # before its command loop accepts the extended named-BPX form.
            # Retry once with the minimal command; the observer already owns
            # the address-to-name mapping used in its JSONL output.
            if not client.set_breakpoint(address, name=name):
                time.sleep(0.2)
                if not client.cmd_sync(f"bpx 0x{address:x}"):
                    raise RuntimeError(f"failed to set {name} at 0x{address:08X}")
        emit("breakpoints_ready", count=len(active_checkpoints), profile=args.profile)
        client.clear_debug_events()
        if ready_path:
            ready_path.parent.mkdir(parents=True, exist_ok=True)
            ready_path.write_text(str(debugger_pid), encoding="ascii")
        if not client.is_running() and not client.go() and not client.is_running():
            raise RuntimeError("failed to resume debuggee")
        emit("running")

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            event = client.get_latest_debug_event()
            if event is None:
                time.sleep(0.02)
                continue

            if event.event_type == EventType.EVENT_BREAKPOINT:
                # x64dbg may enqueue the same software-breakpoint event twice:
                # once while stopped and once just after ``go`` has resumed the
                # debuggee.  Registers from that second notification already
                # belong to running code and must not be decoded as another
                # checkpoint (or followed by another mandatory ``go``).
                if client.is_running():
                    emit(
                        "stale_breakpoint_event_skipped",
                        address=f"0x{int(event.event_data.addr):08X}",
                    )
                    continue
                address = int(event.event_data.addr)
                # x32dbg may create loader/TLS breakpoints after attach (for
                # example when another diagnostic DLL is loaded).  They are
                # not observer checkpoints and decoding their stack as one
                # can leave the debuggee paused or turn the event into a
                # misleading trace row.  Drop the unexpected BP immediately
                # and resume; only the selected profile owns semantic stops.
                if address not in active_checkpoints:
                    cleared = client.clear_breakpoint(address)
                    emit(
                        "unexpected_breakpoint_skipped",
                        address=f"0x{address:08X}",
                        cleared=bool(cleared),
                        event_name=event.event_data.name or "breakpoint",
                    )
                    if not client.go() and not client.is_running():
                        raise RuntimeError(
                            f"failed to resume after unexpected breakpoint at 0x{address:08X}"
                        )
                    continue
                breakpoint_counts[address] = breakpoint_counts.get(address, 0) + 1
                registers = client.get_regs().context
                esp = int(registers.esp)
                stack = client.read_memory(esp, 0x80)
                dwords = [
                    int.from_bytes(stack[i:i + 4], "little")
                    for i in range(0, len(stack), 4)
                ]
                fields = {
                    "name": active_checkpoints.get(
                        address, event.event_data.name or "breakpoint"
                    ),
                    "address": f"0x{address:08X}",
                    "eax": f"0x{registers.eax:08X}",
                    "ebx": f"0x{registers.ebx:08X}",
                    "ecx": f"0x{registers.ecx:08X}",
                    "edx": f"0x{registers.edx:08X}",
                    "esi": f"0x{registers.esi:08X}",
                    "edi": f"0x{registers.edi:08X}",
                    "ebp": f"0x{registers.ebp:08X}",
                    "esp": f"0x{esp:08X}",
                    "eip": f"0x{registers.eip:08X}",
                    "return_address": f"0x{dwords[0]:08X}",
                    "stack_40": stack[:0x40].hex(),
                    "hit_count": breakpoint_counts[address],
                }
                if address == 0x0050FE80 and len(dwords) > 25:
                    fields["caller_of_queue_wrapper"] = f"0x{dwords[25]:08X}"

                if address == 0x0050FE80 and len(dwords) >= 4:
                    fields.update(
                        button_id=f"0x{dwords[1]:08X}",
                        button_param2=f"0x{dwords[2]:08X}",
                        button_param3=f"0x{dwords[3]:08X}",
                    )
                    if dwords[0] == 0x005305F4 and len(dwords) >= 26:
                        fields["wrapper_outer_return"] = (
                            f"0x{dwords[25]:08X}"
                        )
                elif address == 0x005305D0 and len(dwords) >= 3:
                    fields.update(
                        local_event_id=f"0x{dwords[1]:08X}",
                        local_event_mode=f"0x{dwords[2]:08X}",
                    )
                elif address == 0x005E6960 and len(dwords) >= 4:
                    fields.update(
                        popup_content_key=f"0x{dwords[1]:08X}",
                        popup_screen_x=dwords[2],
                        popup_screen_y=dwords[3],
                    )
                elif address == 0x00547BF0 and len(dwords) >= 4:
                    fields.update(
                        descriptor_store=f"0x{registers.ecx:08X}",
                        descriptor_index=dwords[1],
                        descriptor_name_pointer=f"0x{dwords[2]:08X}",
                        descriptor_name=safe_read_cstr(client, dwords[2]),
                        descriptor_value=f"0x{dwords[3]:08X}",
                    )
                elif address == 0x0050B400 and len(dwords) >= 2:
                    fields["room_postload_code"] = f"0x{dwords[1]:02X}"
                elif address == 0x00530FE0 and len(dwords) >= 2:
                    fields.update(
                        room_manager=f"0x{registers.ecx:08X}",
                        room_local_index=dwords[1],
                    )
                elif address == 0x0061B510:
                    # Preserve the raw integer arguments because the exact
                    # producer signature differs between the click boundary
                    # and route builder.  The first four stack arguments are
                    # sufficient to correlate start/target world pairs with
                    # the following 0x0066 payload without writing state.
                    fields.update(
                        arg1_i32=(dwords[1] if dwords[1] < 0x80000000 else dwords[1] - 0x100000000),
                        arg2_i32=(dwords[2] if dwords[2] < 0x80000000 else dwords[2] - 0x100000000),
                        arg3_i32=(dwords[3] if dwords[3] < 0x80000000 else dwords[3] - 0x100000000),
                        arg4_i32=(dwords[4] if dwords[4] < 0x80000000 else dwords[4] - 0x100000000),
                    )
                elif address == 0x005AB7B0 and len(dwords) >= 8:
                    fields.update(
                        current_cell=dwords[1] & 0xFF,
                        from_x=(dwords[2] if dwords[2] < 0x80000000 else dwords[2] - 0x100000000),
                        from_y=(dwords[3] if dwords[3] < 0x80000000 else dwords[3] - 0x100000000),
                        to_x=(dwords[4] if dwords[4] < 0x80000000 else dwords[4] - 0x100000000),
                        to_y=(dwords[5] if dwords[5] < 0x80000000 else dwords[5] - 0x100000000),
                        duration_or_tick=dwords[6],
                        path_flag=dwords[7] & 0xFF,
                    )
                elif address in (0x005ECFF0, 0x005EE600, 0x005EE7B0):
                    fields.update(
                        door_context=f"0x{registers.ecx:08X}",
                        door_slot=safe_read(client, registers.ecx + 0xBA, 4),
                    )
                elif address == 0x005AB760 and len(dwords) >= 5:
                    kind = dwords[1] & 0xFF
                    state = dwords[2] & 0xFF
                    x = dwords[3]
                    y = dwords[4]
                    payload = bytes((kind, state)) + x.to_bytes(
                        4, "little"
                    ) + y.to_bytes(4, "little")
                    fields.update(
                        transition_kind=kind,
                        transition_state=state,
                        transition_x=x,
                        transition_y=y,
                        payload=payload.hex(),
                    )
                elif address == 0x006122C0 and len(dwords) >= 2:
                    fields.update(
                        transition_controller=f"0x{registers.ecx:08X}",
                        transition_index=dwords[1],
                    )
                elif address == 0x00611CD0 and len(dwords) >= 4:
                    fields.update(
                        transition_controller=f"0x{registers.ecx:08X}",
                        probe_arg1=f"0x{dwords[1]:08X}",
                        probe_arg2=f"0x{dwords[2]:08X}",
                        probe_arg3=f"0x{dwords[3]:08X}",
                    )
                elif address == 0x006121B0 and len(dwords) >= 3:
                    fields.update(
                        region_probe_x=dwords[1],
                        region_probe_y=dwords[2],
                    )
                elif address == 0x005AB950 and len(dwords) >= 2:
                    fields.update(
                        community_target_id=dwords[1],
                        payload=dwords[1].to_bytes(4, "little").hex(),
                    )
                elif address in (0x00615B50, 0x00615D50) and len(dwords) >= 3:
                    fields.update(
                        roster_arg1=f"0x{dwords[1]:08X}",
                        roster_arg2=f"0x{dwords[2]:08X}",
                    )
                elif address == 0x00508B30:
                    # FUN_00508B30 is the normal client-peer/controller
                    # construction path.  ECX is the entry object's `this`
                    # on the function prologue; all field reads below are
                    # observational only.
                    logic = int(registers.ecx)
                    fields.update(
                        logic_pointer=f"0x{logic:08X}",
                        gate_value=safe_u32(client, logic + 0x163D8),
                        mode_value=safe_u32(client, logic + 0x163E4),
                    )
                elif address == 0x00594142:
                    # Exact MOV [EAX+0x163D8],ECX boundary, before the write
                    # executes.  EAX is the logic/controller object and ECX
                    # is the GameManager argument at this instruction.
                    logic = int(registers.eax)
                    fields.update(
                        logic_pointer=f"0x{logic:08X}",
                        game_manager=f"0x{int(registers.ecx):08X}",
                        frame_arg8=safe_u32(client, int(registers.ebp) + 8),
                        gate_before=safe_u32(client, logic + 0x163D8),
                        mode_before=safe_u32(client, logic + 0x163E4),
                    )
                elif address == 0x00594148:
                    # First instruction after the exact write.  This is the
                    # read-only confirmation that the owner pointer now
                    # equals the GameManager argument captured above.
                    logic = int(registers.eax)
                    fields.update(
                        logic_pointer=f"0x{logic:08X}",
                        game_manager=f"0x{int(registers.ecx):08X}",
                        gate_after=safe_u32(client, logic + 0x163D8),
                        mode_after=safe_u32(client, logic + 0x163E4),
                    )
                elif address == 0x00594310:
                    # FUN_00594310 entry.  ECX is the dispatch object's this.
                    logic = int(registers.ecx)
                    fields.update(
                        logic_pointer=f"0x{logic:08X}",
                        gate_value=safe_u32(client, logic + 0x163D8),
                        mode_value=safe_u32(client, logic + 0x163E4),
                    )
                elif address == 0x00594447:
                    # CMP [EAX+0x163D8],0.  Reading the operand directly is
                    # enough to distinguish the outer gate without changing
                    # EFLAGS or single-stepping the target.
                    logic = int(registers.eax)
                    fields.update(
                        logic_pointer=f"0x{logic:08X}",
                        gate_value=safe_u32(client, logic + 0x163D8),
                        mode_value=safe_u32(client, logic + 0x163E4),
                        gate_branch="nonzero-or-zero-cmp",
                    )
                elif address == 0x00594454:
                    # Fall-through immediately after JE 0x005944E0; reaching
                    # this address proves the non-zero gate branch was taken.
                    logic = safe_u32(client, int(registers.ebp) - 4)
                    fields.update(
                        logic_pointer=(
                            f"0x{logic:08X}" if logic is not None else None
                        ),
                        gate_value=(
                            safe_u32(client, logic + 0x163D8)
                            if logic is not None
                            else None
                        ),
                        branch_taken="gate_nonzero",
                    )
                elif address == 0x00594457:
                    # MOV ECX,[EAX+0x163E4] is about to execute.  The field
                    # value is read directly while EAX still holds `this`.
                    logic = int(registers.eax)
                    fields.update(
                        logic_pointer=f"0x{logic:08X}",
                        gate_value=safe_u32(client, logic + 0x163D8),
                        mode_value=safe_u32(client, logic + 0x163E4),
                    )
                elif address == 0x0059445D:
                    # The MOV above has completed; ECX now contains the mode
                    # copied from +0x163E4, providing an instruction-level
                    # latch sample without changing execution.
                    logic = int(registers.eax)
                    fields.update(
                        logic_pointer=f"0x{logic:08X}",
                        gate_value=safe_u32(client, logic + 0x163D8),
                        mode_value=safe_u32(client, logic + 0x163E4),
                        mode_latched=int(registers.ecx),
                    )
                elif address == 0x0050D790 and len(dwords) >= 3:
                    fields.update(
                        actor_record_pointer=f"0x{dwords[1]:08X}",
                        ensure_mode=dwords[2],
                        actor_record=safe_read(client, dwords[1], 0x1A),
                    )
                elif address == 0x005243E0 and len(dwords) >= 2:
                    fields.update(
                        remote_actor=f"0x{registers.ecx:08X}",
                        actor_record_pointer=f"0x{dwords[1]:08X}",
                        actor_record=safe_read(client, dwords[1], 0x1A),
                    )
                elif address == 0x0050E560 and len(dwords) >= 2:
                    fields["remote_actor_id"] = dwords[1]
                elif address == 0x005E511E:
                    fields["popup_id"] = safe_u32(client, int(registers.ebp) - 0x10)
                elif address == 0x0055BDB0 and len(dwords) >= 2:
                    action_owner = int(registers.ecx)
                    fields.update(
                        action_owner=f"0x{action_owner:08X}",
                        local_sequence=f"0x{dwords[1]:02X}",
                        static_action_table=safe_u32(client, action_owner + 0x127C7),
                        runtime_action_table=safe_u32(client, action_owner + 0x127CB),
                    )
                elif address == 0x0055EF4F:
                    fields.update(
                        apply_owner=f"0x{int(registers.ecx):08X}",
                        pending_call_stack=stack[:0x20].hex(),
                    )
                elif address == 0x00596690 and len(dwords) >= 4:
                    fields.update(
                        action_owner=f"0x{int(registers.ecx):08X}",
                        action_name_pointer=f"0x{dwords[1]:08X}",
                        action_id=f"0x{dwords[2]:02X}",
                        action_param=f"0x{dwords[3]:08X}",
                    )
                elif address == 0x005A4BA0 and len(dwords) >= 3:
                    stat_owner = int(registers.ecx)
                    stat_index = dwords[1]
                    stat_base = safe_u32(client, stat_owner + 0x5F4)
                    stat_record = (
                        stat_base + stat_index * 0x0C
                        if stat_base is not None
                        else None
                    )
                    fields.update(
                        stat_owner=f"0x{stat_owner:08X}",
                        stat_index=stat_index,
                        stat_delta=(dwords[2] if dwords[2] < 0x80000000 else dwords[2] - 0x100000000),
                        stat_base=(f"0x{stat_base:08X}" if stat_base is not None else None),
                        stat_current_before=(safe_u32(client, stat_record) if stat_record is not None else None),
                        stat_min=(safe_u32(client, stat_record + 4) if stat_record is not None else None),
                        stat_max=(safe_u32(client, stat_record + 8) if stat_record is not None else None),
                    )
                elif address == 0x005A4770 and len(dwords) >= 4:
                    snapshot_owner = int(registers.ecx)
                    payload_pointer = snapshot_owner + 0x5F8
                    fields.update(
                        snapshot_owner=f"0x{snapshot_owner:08X}",
                        snapshot_arg0=dwords[1],
                        snapshot_arg1=dwords[2],
                        snapshot_opcode=dwords[3],
                        payload_pointer=f"0x{payload_pointer:08X}",
                        payload=safe_read(client, payload_pointer, 0xC4),
                        pushup_stat_0x1f=safe_u16(client, payload_pointer + 0x48),
                    )
                elif address == 0x005A95B0 and len(dwords) >= 3:
                    model = int(registers.ecx)
                    fields.update(
                        model=f"0x{model:08X}",
                        model_vtable=(
                            f"0x{safe_u32(client, model):08X}"
                            if safe_u32(client, model) is not None else None
                        ),
                        money=safe_u32(client, model + 0x1F0),
                        purchase_lock=safe_u32(client, model + 0x808),
                        item_array_pointer=f"0x{dwords[1]:08X}",
                        item_count=dwords[2],
                        item_ids=safe_read(client, dwords[1], min(dwords[2], 20) * 4),
                    )
                elif address == 0x005A97D5:
                    model = int(registers.eax)
                    total = safe_u32(client, int(registers.ebp) - 0x20)
                    fields.update(
                        model=f"0x{model:08X}",
                        model_vtable=(
                            f"0x{safe_u32(client, model):08X}"
                            if safe_u32(client, model) is not None else None
                        ),
                        money=safe_u32(client, model + 0x1F0),
                        computed_total=total,
                        purchase_lock=safe_u32(client, model + 0x808),
                    )
                elif address == 0x005A9AB7 and len(dwords) >= 2:
                    model = int(registers.ecx)
                    buffer_pointer = dwords[0]
                    payload_length = dwords[1]
                    fields.update(
                        model=f"0x{model:08X}",
                        model_vtable=f"0x{int(registers.edx):08X}",
                        virtual_target=f"0x{int(registers.eax):08X}",
                        money=safe_u32(client, model + 0x1F0),
                        purchase_lock=safe_u32(client, model + 0x808),
                        buffer_pointer=f"0x{buffer_pointer:08X}",
                        payload_length=payload_length,
                        payload=(
                            safe_read(client, buffer_pointer, payload_length)
                            if payload_length == 0x2D else ""
                        ),
                    )
                elif address in (0x0059D760, 0x005AB6A0, 0x00593D10) and len(dwords) >= 4:
                    opcode, buffer_pointer, payload_length = dwords[1:4]
                    fields.update(
                        opcode=f"0x{opcode:04X}",
                        buffer_pointer=f"0x{buffer_pointer:08X}",
                        payload_length=payload_length,
                    )
                    if 0 <= payload_length <= 0x100:
                        fields["payload"] = safe_read(
                            client, buffer_pointer, payload_length
                        )
                emit("checkpoint", **fields)
                # The room bootstrap uses this queue helper repeatedly while
                # the first scene settles.  Leaving a software breakpoint on
                # it for the whole run can turn observation into an input
                # throttle, so capture the first ten hits and then remove
                # only this noisy checkpoint.  All room/content boundaries
                # remain armed.
                if address == 0x0050FE80 and breakpoint_counts[address] == 10:
                    if client.clear_breakpoint(address):
                        emit(
                            "checkpoint_disabled",
                            address="0x0050FE80",
                            reason="bootstrap queue repetition threshold",
                        )
                resumed = client.go()
                if not resumed and not client.is_running():
                    raise RuntimeError(
                        f"failed to resume after 0x{address:08X}"
                    )

            elif event.event_type == EventType.EVENT_EXCEPTION:
                exception = event.event_data
                registers = client.get_regs().context
                emit(
                    "exception",
                    code=f"0x{int(exception.ExceptionCode):08X}",
                    address=f"0x{int(exception.ExceptionAddress):08X}",
                    first_chance=bool(exception.dwFirstChance),
                    eip=f"0x{registers.eip:08X}",
                    esp=f"0x{registers.esp:08X}",
                    stack_40=safe_read(client, int(registers.esp), 0x40),
                )
                break
            elif event.event_type == EventType.EVENT_EXIT_PROCESS:
                emit(
                    "process_exit",
                    code=f"0x{int(event.event_data.dwExitCode):08X}",
                )
                debugger_attached = False
                break
        else:
            emit("timeout", seconds=args.timeout)

        if debugger_attached:
            for address in active_checkpoints:
                try:
                    client.clear_breakpoint(address)
                except Exception as exc:
                    emit(
                        "clear_breakpoint_error",
                        address=f"0x{address:08X}",
                        error=repr(exc),
                    )
            detached = client.detach()
            emit("detached", ok=bool(detached))
        return 0
    except Exception as exc:
        emit("fatal", error=repr(exc))
        if debugger_attached:
            # A setup failure must never leave the client silently attached to
            # an orphaned debugger.  Clear only this profile's breakpoints and
            # detach the live target without terminating it.
            for address in active_checkpoints:
                try:
                    client.clear_breakpoint(address)
                except Exception:
                    pass
            try:
                detached = client.detach()
                emit("detached_after_fatal", ok=bool(detached))
            except Exception as detach_exc:
                emit("detach_after_fatal_error", error=repr(detach_exc))
        return 1
    finally:
        if ready_path and ready_path.exists():
            ready_path.unlink()
        try:
            client.detach_session()
        except Exception:
            pass
        output.close()


if __name__ == "__main__":
    raise SystemExit(main())
