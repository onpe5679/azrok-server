"""Add independent, source-only private guest launchers to the web app ZIP.

The original executable and all preserved client data are deliberately copied
unchanged.  This script adds only four small command-line launchers so the
private browser-admission registry can give five new devices distinct local
player names without a binary patch.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import zipfile
from pathlib import Path


# Use the verified StateBlock default-state package as the immutable base.
# It contains the D3DRS_COLORWRITEENABLE seeding fix required when chat opens.
DEFAULT_APP = Path(__file__).resolve().parent / "boxedwine_local" / "apps" / "Azrok_D3D9Web_pathouse_guesttexrecycle4_rsdefaults1.zip"
DEFAULT_OUTPUT = DEFAULT_APP.with_name("Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1.zip")
def _guest_launcher(player: str) -> str:
    """Keep every automatic guest on the same verified SEH/D3D9 path as player."""
    return (
        "@echo off\r\n"
        "reg add \"HKCU\\Software\\Wine\\DllOverrides\" /v d3d9 /d native /f\r\n"
        "set WINEDLLOVERRIDES=d3d9=n\r\n"
        "set WINEDEBUG=-all,+seh\r\n"
        "set LANG=ko_KR.EUC-KR\r\n"
        "set LC_ALL=ko_KR.EUC-KR\r\n"
        "start /b acklog_tail.exe\r\n"
        f"Azrok.exe -diag -NX 200 -NWND -PL {player} -DIR localauth -IP 127.0.0.1:9201\r\n"
        "echo D3D9WEB_PATHOUSE_EXITCODE=%ERRORLEVEL%\r\n"
    )


NEW_LAUNCHERS = {
    f"run_azrok_{player}.bat": _guest_launcher(player)
    for player in ("player3", "player4", "player5", "player6")
}


def build_app(source_path: Path, output_path: Path) -> None:
    with zipfile.ZipFile(source_path, "r") as source:
        with tempfile.NamedTemporaryFile(dir=output_path.parent, suffix=".zip", delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
                for entry in source.infolist():
                    # Replace guest launchers if a later source package already
                    # contains them, rather than preserving an older safety
                    # preamble under the same ZIP path.
                    if entry.filename in NEW_LAUNCHERS:
                        continue
                    target.writestr(entry, source.read(entry.filename))
                for name, content in NEW_LAUNCHERS.items():
                    target.writestr(name, content.encode("ascii"))
            os.replace(temporary_path, output_path)
        finally:
            temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, default=DEFAULT_APP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_app(args.app, args.output)


if __name__ == "__main__":
    main()
