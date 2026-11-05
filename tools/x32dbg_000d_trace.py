#!/usr/bin/env python3
"""Automated x32dbg trace for the packet-driven PatHouse -> Plaza transition.

This uses the already-installed x64dbg-automate plugin and Python client.  It
does not modify the executable on disk and it never writes game state.  The
only transient code changes are ordinary debugger software breakpoints.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from x64dbg_automate import X64DbgClient
from x64dbg_automate.events import EventType
from x64dbg_automate.models import BreakpointType
from x32dbg_path import resolve_x32dbg


X32DBG = resolve_x32dbg()

# Ordered checkpoints recovered by the static-analysis pass.  Return-site
# checkpoints make it possible to distinguish a successful cleanup call from
# a call that raised or never returned.
CHECKPOINTS = {
    0x00568770: "transition_entry",
    0x0050A802: "scene_006e_write",
    0x005687D0: "status_cleanup_call",
    0x005687D2: "status_cleanup_return",
    0x005687F9: "azron_cleanup_call",
    0x005687FB: "azron_cleanup_return",
    0x00568822: "calendar_cleanup_call",
    0x00568824: "calendar_cleanup_return",
    0x0056888B: "state_list_cleanup_call",
    0x0056888D: "state_list_cleanup_return",
    0x005284A2: "flag_31c72_write",
    0x0059DE50: "calibration_reset_entry",
    0x0059DFED: "first_c2s_0016_send",
    0x005688D5: "reset_return",
    0x005688DB: "transition_return",
    # Room-code/loader and Hansol-stage checkpoints.  These are read-only
    # software breakpoints used to distinguish the OX convergence point from
    # the earlier Plaza/Hansol room selection path.
    0x0050A7F0: "scene_request_enqueue",
    0x0050A880: "postload_scene_bridge",
    0x0050A0F0: "room_code_dispatch",
    0x0050B400: "room_initializer",
    0x00614370: "hansol_stage_entry",
    0x006143EC: "hansol_stage0_send",
    0x005AB738: "send_0064_setup",
    0x00615650: "handle_s2c_0064",
    0x006169D0: "handle_s2c_006e",
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def main() -> int:
    ap = argparse.ArgumentParser()
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--pid", type=int)
    target.add_argument("--session-pid", type=int,
                        help="connect to an existing x32dbg automate session")
    ap.add_argument("--log", required=True)
    ap.add_argument("--ready-file", default="")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    log_path = Path(args.log).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ready_path = Path(args.ready_file).resolve() if args.ready_file else None
    if ready_path and ready_path.exists():
        ready_path.unlink()

    out = log_path.open("w", encoding="utf-8", buffering=1)

    def emit(kind: str, **fields) -> None:
        record = {"time": now(), "kind": kind, **fields}
        line = json.dumps(record, ensure_ascii=False)
        print(line, flush=True)
        out.write(line + "\n")

    client = X64DbgClient(X32DBG)
    attached = False
    try:
        if args.session_pid:
            client.attach_session(args.session_pid)
            session_pid = args.session_pid
            if not client.is_debugging():
                raise RuntimeError("existing x32dbg session has no debuggee")
        else:
            session_pid = client.start_session_attach(args.pid)
        attached = True
        emit("attached", target_pid=args.pid, debugger_pid=session_pid,
             reused_session=bool(args.session_pid))

        existing = {int(bp.addr) for bp in client.get_breakpoints(BreakpointType.BpNormal)}
        for addr, name in CHECKPOINTS.items():
            if addr in existing:
                continue
            if not client.set_breakpoint(addr, name=name):
                raise RuntimeError(f"failed to set breakpoint {name} at 0x{addr:08X}")
        emit("breakpoints_ready", count=len(CHECKPOINTS))
        client.clear_debug_events()
        if ready_path:
            ready_path.parent.mkdir(parents=True, exist_ok=True)
            ready_path.write_text(str(session_pid), encoding="ascii")
        if not client.is_running():
            resumed = client.go()
            # Another controller may have resumed the shared x32dbg session
            # between our status check and the run command.  Running is the
            # desired postcondition, so accept that race explicitly.
            if not resumed and not client.is_running():
                raise RuntimeError("failed to resume debuggee")
        emit("running")

        deadline = time.monotonic() + args.timeout
        success = False
        while time.monotonic() < deadline:
            event = client.get_latest_debug_event()
            if event is None:
                time.sleep(0.025)
                continue

            if event.event_type == EventType.EVENT_BREAKPOINT:
                addr = int(event.event_data.addr)
                name = CHECKPOINTS.get(addr, event.event_data.name or "breakpoint")
                regs = client.get_regs().context
                esp = int(regs.esp)
                stack = client.read_memory(esp, 0x20).hex()
                emit(
                    "checkpoint",
                    name=name,
                    address=f"0x{addr:08X}",
                    eax=f"0x{regs.eax:08X}",
                    ebx=f"0x{regs.ebx:08X}",
                    ecx=f"0x{regs.ecx:08X}",
                    edx=f"0x{regs.edx:08X}",
                    esi=f"0x{regs.esi:08X}",
                    edi=f"0x{regs.edi:08X}",
                    ebp=f"0x{regs.ebp:08X}",
                    esp=f"0x{regs.esp:08X}",
                    eip=f"0x{regs.eip:08X}",
                    stack_20=stack,
                )
                if addr == 0x005688DB:
                    success = True
                    emit("core_success")
                    # The transition return breakpoint is still a stopped
                    # debugger state. Resume before observing calibration;
                    # detaching while stopped leaves the client message loop
                    # suspended and makes the next S->C 0x0004 appear lost.
                    if not client.go() and not client.is_running():
                        raise RuntimeError("failed to resume after transition return")
                    continue
                if not client.go():
                    raise RuntimeError(f"failed to resume after {name}")

            elif event.event_type == EventType.EVENT_EXCEPTION:
                ex = event.event_data
                regs = client.get_regs().context
                emit(
                    "exception",
                    code=f"0x{int(ex.ExceptionCode):08X}",
                    address=f"0x{int(ex.ExceptionAddress):08X}",
                    first_chance=bool(ex.dwFirstChance),
                    eip=f"0x{regs.eip:08X}",
                    eax=f"0x{regs.eax:08X}",
                    ecx=f"0x{regs.ecx:08X}",
                    edx=f"0x{regs.edx:08X}",
                    esp=f"0x{regs.esp:08X}",
                    stack_40=client.read_memory(int(regs.esp), 0x40).hex(),
                )
                # Preserve the stopped state long enough for post-mortem reads.
                break
            elif event.event_type == EventType.EVENT_EXIT_PROCESS:
                emit("process_exit", code=f"0x{int(event.event_data.dwExitCode):08X}")
                attached = False
                break

        else:
            emit("timeout", seconds=args.timeout)

        if attached:
            # On failure the process can still be inspected through the log;
            # detach without terminating the game.  On success this also lets
            # the normal packet handshake continue without debugger latency.
            try:
                for addr in CHECKPOINTS:
                    client.clear_breakpoint(addr)
            except Exception as exc:
                emit("clear_breakpoints_error", error=repr(exc))
            try:
                detached = client.detach()
                emit("detached", ok=bool(detached), success=success)
                attached = not detached
            except Exception as exc:
                emit("detach_error", error=repr(exc))
        return 0 if success else 2
    except Exception as exc:
        emit("fatal", error=repr(exc))
        return 1
    finally:
        if ready_path and ready_path.exists():
            ready_path.unlink()
        try:
            client.detach_session()
        except Exception:
            pass
        out.close()


if __name__ == "__main__":
    raise SystemExit(main())
