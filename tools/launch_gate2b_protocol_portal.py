"""Launch the pinned native BoxedWine/Wine11 Vulkan OX protocol test.

The local preservation server must already listen on 127.0.0.1:9200 with its
control API enabled on 9300.  Room transitions are then driven through the
control API rather than by manually clicking in-world doors.
"""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "artifacts" / "boxedwine" / "20260719_gate2b_native"
BOXEDWINE = (
    RUNTIME / "Boxedwine" / "project" / "msvc" / "BoxedWine" / "BoxedWine"
    / "x64" / "Release" / "BoxedWine.exe"
)
WINE_ROOT = RUNTIME / "azrok_root_release_wine11_vulkan"
DRIVE_D = RUNTIME / "Azrok_runtime"
FILESYSTEM = Path.home() / "AppData" / "Roaming" / "Boxedwine" / "FileSystems2" / "TinyCore15Wine11.0.zip"
STDOUT = RUNTIME / "azrok_wine11_vulkan_protocol_portal_stdout.log"
STDERR = RUNTIME / "azrok_wine11_vulkan_protocol_portal_stderr.log"


def main() -> None:
    missing = [path for path in (BOXEDWINE, WINE_ROOT, DRIVE_D, FILESYSTEM) if not path.exists()]
    if missing:
        raise SystemExit("missing runtime asset(s): " + ", ".join(map(str, missing)))

    command = [
        str(BOXEDWINE),
        "-title", "Gate2b_Azrok_Vulkan_OX_ProtocolPortal",
        "-resolution", "800x600",
        "-root", str(WINE_ROOT),
        "-zip", str(FILESYSTEM),
        "-mount_drive", str(DRIVE_D), "d",
        "-w", "/mnt/drive_d",
        "-env", "WINEDEBUG=-all",
        "-env", "LANG=ko_KR.EUC-KR",
        "-env", "LC_ALL=ko_KR.EUC-KR",
        "/bin/wine", "Azrok.exe",
        "-NX", "200", "-NWND",
        "-PL", "wine11_vulkan", "-DIR", "localauth",
        "-IP", "127.0.0.1:9200",
    ]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with STDOUT.open("w", encoding="utf-8") as output, STDERR.open("w", encoding="utf-8") as errors:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=output,
            stderr=errors,
            creationflags=flags,
        )
    print(f"BOXEDWINE_PID={process.pid}")


if __name__ == "__main__":
    main()
