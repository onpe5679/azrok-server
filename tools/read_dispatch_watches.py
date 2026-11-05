# -*- coding: utf-8 -*-
"""Read-only dispatch-owner watch for every live Azrok.exe process.

The control panel owns the primary launcher's process handle.  Reused
secondary clients are separate elevated processes, so this small diagnostic
opens each matching PID with PROCESS_VM_READ and applies the same static
``CGameManager -> CGame -> CLogic`` derivation.  It never calls
WriteProcessMemory and never changes client state.
"""
import ctypes
from ctypes import wintypes as wt
import json
from pathlib import Path
import subprocess
import sys

# When invoked as ``python tools/...``, Python puts ``tools`` (not the repo
# root) on sys.path.  Resolve the source module explicitly without mutating
# the game or launcher process.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import azrok_server


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
kernel32 = ctypes.windll.kernel32
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = ctypes.wintypes.BOOL


def azrok_pids():
    raw = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='Azrok.exe'\" | "
         "Select-Object -ExpandProperty ProcessId"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    return [int(line.strip()) for line in raw.splitlines() if line.strip().isdigit()]


def read_one(pid):
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid,
    )
    if not handle:
        return {'pid': pid, 'error': 'OpenProcess failed'}
    try:
        azrok_server._cached_gm_real = 0
        gm = azrok_server.find_real_gm(handle)
        if not gm:
            return {'pid': pid, 'gm': None, 'error': 'gm not found'}
        state = azrok_server.collect_runtime_state(handle, gm, 0, 0)
        owner = state['dispatch_owner_subobject']
        return {
            'pid': pid,
            'gm': f"0x{gm:08X}",
            'logic': owner.get('object'),
            'vptr': owner.get('vptr'),
            'vtable_kind': owner.get('vtable_kind'),
            'dispatch_mode': state['dispatch_mode'],
            'dispatch_gate': f"0x{state['dispatch_gate']:08X}",
            'gate_matches_gm': state['dispatch_gate_matches_gm'],
            'gate_outer_buffer': f"0x{state['dispatch_gate_outer_buffer']:08X}",
            'gate_matches_outer_buffer': state['dispatch_gate_matches_outer_buffer'],
            'scene_opcode': state['scene_opcode'],
            'phase_31792': state['phase_31792'],
            'self_actor_id': state['self_actor_id'],
            'nexus': azrok_server.read_dword(handle, 0x102FC540),
        }
    finally:
        kernel32.CloseHandle(handle)


def main():
    rows = [read_one(pid) for pid in azrok_pids()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
