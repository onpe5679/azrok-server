"""Build an immutable private-guest app with a UTF-8 Wine Unix locale.

Only player2 through player6 launchers are changed.  The preserved executable,
game data, renderer payload, and every unrelated launcher remain byte-identical
to the accepted guestprofiles6 package.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import zipfile
from pathlib import Path


APPS = Path(__file__).resolve().parent / "boxedwine_local" / "apps"
DEFAULT_APP = APPS / "Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1.zip"
DEFAULT_OUTPUT = APPS / "Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime1.zip"

TARGET_LAUNCHERS = {
    "run_azrok_multi2.bat",
    "run_azrok_player3.bat",
    "run_azrok_player4.bat",
    "run_azrok_player5.bat",
    "run_azrok_player6.bat",
}

OLD_LANG = b"set LANG=ko_KR.EUC-KR"
OLD_LC_ALL = b"set LC_ALL=ko_KR.EUC-KR"
NEW_LANG = b"set LANG=C.UTF-8"
NEW_LC_ALL = b"set LC_ALL=C.UTF-8"
WINEUNIXCP_PROBE = b"echo D3D9WEB_WINEUNIXCP=%WINEUNIXCP%"


def _rewrite_launcher(data: bytes, name: str) -> bytes:
    if data.count(OLD_LANG) != 1 or data.count(OLD_LC_ALL) != 1:
        raise ValueError(f"unexpected locale contract in {name}")
    data = data.replace(OLD_LANG, NEW_LANG)
    for newline in (b"\r\r\n", b"\r\n", b"\n"):
        old_line = OLD_LC_ALL + newline
        if old_line in data:
            return data.replace(
                old_line, NEW_LC_ALL + newline + WINEUNIXCP_PROBE + newline, 1
            )
    raise ValueError(f"locale line has no recognized terminator in {name}")


def build_app(source_path: Path, output_path: Path) -> None:
    if source_path.resolve() == output_path.resolve():
        raise ValueError("output must be a new immutable app path")

    with zipfile.ZipFile(source_path, "r") as source:
        names = source.namelist()
        missing = TARGET_LAUNCHERS.difference(names)
        if missing:
            raise ValueError(f"source is missing launchers: {sorted(missing)}")

        with tempfile.NamedTemporaryFile(
            dir=output_path.parent, suffix=".zip", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)

        changed: set[str] = set()
        try:
            with zipfile.ZipFile(temporary_path, "w") as target:
                for entry in source.infolist():
                    data = source.read(entry.filename)
                    if entry.filename in TARGET_LAUNCHERS:
                        data = _rewrite_launcher(data, entry.filename)
                        changed.add(entry.filename)
                    target.writestr(entry, data)

            if changed != TARGET_LAUNCHERS:
                raise ValueError(f"did not rewrite all launchers: {sorted(changed)}")
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
