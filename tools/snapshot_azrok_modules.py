#!/usr/bin/env python3
"""Write a read-only Toolhelp module snapshot for one already-running process.

This deliberately uses the Windows module list rather than a debugger attach:
the output answers only which image path Windows has mapped for ``d3d9.dll``.
It neither changes the target nor keeps it stopped.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone


TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
ERROR_NO_MORE_FILES = 18


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("th32ModuleID", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD),
        ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wt.DWORD),
        ("hModule", wt.HMODULE),
        ("szModule", wt.WCHAR * 256),
        ("szExePath", wt.WCHAR * 260),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
CreateToolhelp32Snapshot.restype = wt.HANDLE
Module32FirstW = kernel32.Module32FirstW
Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
Module32FirstW.restype = wt.BOOL
Module32NextW = kernel32.Module32NextW
Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
Module32NextW.restype = wt.BOOL
CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wt.HANDLE]
CloseHandle.restype = wt.BOOL


def module_snapshot(pid: int) -> list[dict[str, object]]:
    handle = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if handle == INVALID_HANDLE_VALUE:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not Module32FirstW(handle, ctypes.byref(entry)):
            raise OSError(ctypes.get_last_error(), "Module32FirstW failed")

        modules: list[dict[str, object]] = []
        while True:
            modules.append(
                {
                    "module": entry.szModule,
                    "path": entry.szExePath,
                    "base": f"0x{int(entry.modBaseAddr or 0):08X}",
                    "size": int(entry.modBaseSize),
                }
            )
            entry = MODULEENTRY32W()
            entry.dwSize = ctypes.sizeof(entry)
            if Module32NextW(handle, ctypes.byref(entry)):
                continue
            error = ctypes.get_last_error()
            if error == ERROR_NO_MORE_FILES:
                break
            raise OSError(error, "Module32NextW failed")
        return modules
    finally:
        CloseHandle(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Windows module snapshot")
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()
    if args.pid <= 0:
        parser.error("--pid must be positive")

    log_path = Path(args.log).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        modules = module_snapshot(args.pid)
        d3d9 = [row for row in modules if str(row["module"]).lower() == "d3d9.dll"]
        record = {
            "kind": "module_snapshot",
            "pid": args.pid,
            "snapshot_utc": datetime.now(timezone.utc).isoformat(),
            "module_count": len(modules),
            "d3d9": d3d9,
            # A native proxy chain legitimately maps two same-named modules:
            # the application-local proxy and the system D3D9 it forwards to.
            # Presence, not uniqueness, is the generic loader fact.
            "d3d9_count": len(d3d9),
            "d3d9_loaded": bool(d3d9),
            "modules": modules,
        }
    except Exception as exc:  # record failures as evidence, not a silent empty list
        record = {
            "kind": "module_snapshot_error",
            "pid": args.pid,
            "error": repr(exc),
        }
        log_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1

    log_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
