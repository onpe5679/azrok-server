#!/usr/bin/env python3
"""Take one read-only x32dbg thread snapshot from a stuck Azrok client."""

from __future__ import annotations

import argparse
import json
import struct
import time
from pathlib import Path

import psutil
from x64dbg_automate import X64DbgClient
from x32dbg_path import resolve_x32dbg


X32DBG = resolve_x32dbg()
AZROK_CODE_MIN = 0x00400000
AZROK_CODE_MAX = 0x00700000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()

    log_path = Path(args.log).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []

    def emit(kind: str, **fields: object) -> None:
        record = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, **fields}
        records.append(record)
        log_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    process = psutil.Process(args.pid)
    thread_cpu = {item.id: item.user_time + item.system_time for item in process.threads()}
    client = X64DbgClient(X32DBG)
    attached = False
    try:
        debugger_pid = client.start_session_attach(args.pid)
        attached = True
        emit("attached", target_pid=args.pid, debugger_pid=debugger_pid)
        if client.is_running():
            client.pause()
            client.wait_until_stopped(10)

        snapshots: list[dict] = []
        for tid, cpu_seconds in sorted(thread_cpu.items(), key=lambda item: item[1], reverse=True):
            try:
                if not client.switch_thread(tid):
                    continue
                context = client.get_regs().context
                eip = int(context.eip)
                esp = int(context.esp)
                # The main Acknex thread can be stopped inside a Win32 wait
                # with its first Azrok return address several pages above ESP.
                stack = client.read_memory(esp, 0x4000)
                returns = [
                    value
                    for value in struct.unpack(f"<{len(stack) // 4}I", stack)
                    if AZROK_CODE_MIN <= value < AZROK_CODE_MAX
                ]
                instruction = client.disassemble_at(eip)
                snapshots.append(
                    {
                        "tid": tid,
                        "cpu_seconds": round(cpu_seconds, 6),
                        "eip": f"0x{eip:08X}",
                        "esp": f"0x{esp:08X}",
                        "instruction": str(instruction) if instruction else None,
                        "azrok_stack_returns": [f"0x{value:08X}" for value in returns[:24]],
                    }
                )
            except Exception as exc:
                snapshots.append({"tid": tid, "cpu_seconds": round(cpu_seconds, 6), "error": repr(exc)})

        relevant = [row for row in snapshots if row.get("azrok_stack_returns")]
        emit(
            "thread_snapshot",
            thread_count=len(snapshots),
            relevant_count=len(relevant),
            relevant=relevant,
            top_cpu=snapshots[:20],
        )
        return 0
    except Exception as exc:
        emit("fatal", error=repr(exc))
        return 1
    finally:
        if attached:
            try:
                if not client.is_running():
                    client.go()
                emit("detached", ok=bool(client.detach()))
            except Exception as exc:
                emit("detach_error", error=repr(exc))


if __name__ == "__main__":
    raise SystemExit(main())
