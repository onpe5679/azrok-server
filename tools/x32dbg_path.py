"""Resolve the local x32dbg executable without probing the offline D: drive."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_x32dbg() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    configured = os.environ.get("AZROK_X32DBG_PATH", "").strip()
    candidates = [
        configured,
        r"B:\x64dbg\x32\x32dbg.exe",
        # Current official snapshot archives unpack their binaries under
        # ``release``.  Keep this explicit so a restored B: debugger never
        # revives the offline D: dependency after a reboot.
        r"B:\x64dbg\release\x32\x32dbg.exe",
        str(repo_root / "tools" / "x64dbg" / "x32" / "x32dbg.exe"),
        r"C:\x64dbg\x32\x32dbg.exe",
    ]
    for raw in candidates:
        if not raw:
            continue
        path = Path(raw)
        if path.drive.upper() == "D:":
            continue
        if path.is_file():
            return str(path)
    raise FileNotFoundError(
        "x32dbg not found on the allowed B:/workspace/C: candidates; "
        "set AZROK_X32DBG_PATH to a non-D: x32dbg.exe path"
    )
