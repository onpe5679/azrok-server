"""Unit contracts for private browser-identifier WSS admission."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import unittest
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from azrok_private_access import (
    browser_ticket_claims,
    is_private_client,
    issue_browser_ticket,
    PrivateAccountRegistry,
    valid_account_id,
    validate_browser_ticket,
)
from tools.build_utf8_ime_app import _rewrite_launcher
from tools.ws_tcp_bridge import read_account_bound_login


SECRET = b"private-test-secret-at-least-16-bytes"
BROWSER_ID = "browser_7c0f4e07-1bf8-4df2-8e75-1c4d3bd3d9e6"
APP_PACKAGE = (
    Path(__file__).resolve().parent
    / "boxedwine_local"
    / "apps"
    / "Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1.zip"
)
UTF8_IME_APP_PACKAGE = APP_PACKAGE.with_name(
    "Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime1.zip"
)
UTF8_IME_APP_SHA256 = "3b5c69fac8916dc610b57ae341e1a27756e4ca08d1aa6335cc36584fcbaf8dad"
UTF8_IME_LAUNCHERS = {
    "run_azrok_multi2.bat",
    "run_azrok_player3.bat",
    "run_azrok_player4.bat",
    "run_azrok_player5.bat",
    "run_azrok_player6.bat",
}
ROOT_PACKAGE = (
    Path(__file__).resolve().parent
    / "boxedwine_local"
    / "fs"
    / (
        "TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-"
        "pcrestd1-noprefixupd1-acp949-xim1.zip"
    )
)
WINE_NTDLL_ENV = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "wine11_source"
    / "wine-11.0"
    / "dlls"
    / "ntdll"
    / "unix"
    / "env.c"
)
ASSET_SERVER = Path(__file__).resolve().parent / "boxedwine_local" / "server.py"
DYNAMIC_APP_PACKAGE = APP_PACKAGE.with_name(
    "Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2.zip"
)
UTF8_IME2_APP_PACKAGE = APP_PACKAGE.with_name(
    "Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2.zip"
)


class PrivateBrowserAdmissionTests(unittest.TestCase):
    def test_dynamic_account_app_adds_only_the_argument_launcher(self) -> None:
        self.assertTrue(DYNAMIC_APP_PACKAGE.is_file())
        with zipfile.ZipFile(UTF8_IME2_APP_PACKAGE) as source, zipfile.ZipFile(
            DYNAMIC_APP_PACKAGE
        ) as candidate:
            self.assertEqual(candidate.namelist()[:-1], source.namelist())
            self.assertEqual(candidate.namelist()[-1], "run_azrok_account.bat")
            for entry in source.infolist():
                self.assertEqual(candidate.read(entry.filename), source.read(entry.filename))
            launcher = candidate.read("run_azrok_account.bat").decode("ascii")
            self.assertNotIn("findstr", launcher.lower())
            self.assertIn('if "%~1"=="" exit /b 87', launcher)
            self.assertIn("-PL %~1 -DIR localauth -IP 127.0.0.1:9201", launcher)
            self.assertNotIn("\r\r\n", candidate.read("run_azrok_account.bat").decode("ascii"))

    def test_wss_buffers_fragmented_login_and_enforces_ticket_account(self) -> None:
        account = "a123456789012"
        payload = bytearray(0x6A)
        payload[0] = 1
        payload[1:1 + len(account)] = account.encode("ascii")
        packet = len(payload).to_bytes(2, "little") + b"\x00\x00" + bytes(payload)

        class FakeWebSocket:
            def __init__(self, parts):
                self.parts = iter(parts)

            async def recv(self):
                return next(self.parts)

        actual = asyncio.run(
            read_account_bound_login(FakeWebSocket([packet[:3], packet[3:40], packet[40:]]), account)
        )
        self.assertEqual(actual, packet)
        with self.assertRaisesRegex(ValueError, "does not match"):
            asyncio.run(read_account_bound_login(FakeWebSocket([packet]), "a999999999999"))

    def test_asset_server_streams_full_and_range_responses_in_bounded_chunks(self) -> None:
        source = ASSET_SERVER.read_text(encoding="utf-8")
        body = source.split("def copyfile", 1)[1].split("def main", 1)[0]
        self.assertIn("while remaining is None or remaining", body)
        self.assertIn("chunk_size = 1024 * 1024", body)
        self.assertIn("source.read(chunk_size)", body)
        self.assertNotIn("super().copyfile", body)

    def test_private_chat_bridge_requires_ticket_and_relays_only_by_bound_account(self) -> None:
        source = ASSET_SERVER.read_text(encoding="utf-8")
        body = source.split("def serve_private_chat_say", 1)[1].split("def do_POST", 1)[0]
        self.assertIn("browser_ticket_claims", body)
        self.assertIn('message.encode("cp949")', body)
        self.assertIn("len(encoded) > 120", body)
        self.assertIn('account_id = str(claims["account_id"])', body)
        self.assertIn('player.get("account") == account_id', body)
        self.assertIn('f"{self.private_control_base_url}/api/chat/say"', body)
        self.assertIn('"/api/private-chat-say": self.serve_private_chat_say', source)
        self.assertIn('"/api/private-chat-state": self.serve_private_chat_state', source)
        state_body = source.split("def serve_private_chat_state", 1)[1].split("def do_POST", 1)[0]
        self.assertIn("browser_ticket_claims", state_body)
        self.assertIn('player.get("account") == account_id', state_body)
        self.assertIn('"ready": room_kind == 27', state_body)

    def test_utf8_ime_app_changes_only_private_guest_unix_locale(self) -> None:
        self.assertEqual(
            hashlib.sha256(UTF8_IME_APP_PACKAGE.read_bytes()).hexdigest(),
            UTF8_IME_APP_SHA256,
        )
        with zipfile.ZipFile(APP_PACKAGE) as source, zipfile.ZipFile(
            UTF8_IME_APP_PACKAGE
        ) as candidate:
            self.assertEqual(source.namelist(), candidate.namelist())
            for source_info, candidate_info in zip(
                source.infolist(), candidate.infolist()
            ):
                name = source_info.filename
                with self.subTest(name=name):
                    self.assertEqual(source_info.date_time, candidate_info.date_time)
                    self.assertEqual(source_info.external_attr, candidate_info.external_attr)
                    original = source.read(name)
                    actual = candidate.read(name)
                    if name in UTF8_IME_LAUNCHERS:
                        expected = _rewrite_launcher(original, name)
                        self.assertEqual(actual, expected)
                        self.assertNotIn(b"ko_KR.EUC-KR", actual)
                        self.assertEqual(
                            actual.count(b"echo D3D9WEB_WINEUNIXCP=%WINEUNIXCP%"), 1
                        )
                    else:
                        self.assertEqual(actual, original)

    def test_utf8_ime_locale_matches_wine_xim_unix_conversion_contract(self) -> None:
        source = WINE_NTDLL_ENV.read_text(encoding="utf-8")
        self.assertIn("static CPTABLEINFO unix_cp = { CP_UTF8", source)
        self.assertIn('setlocale( LC_CTYPE, "" )', source)
        self.assertIn('{ "ANSIX341968", 20127 }', source)
        self.assertIn("if (unix_cp.CodePage != CP_UTF8) return cp_mbstowcs", source)
        with zipfile.ZipFile(ROOT_PACKAGE) as root:
            names = root.namelist()
        self.assertNotIn("usr/lib/locale/locale-archive", names)
        self.assertFalse(any(name.endswith("ko_KR/LC_CTYPE") for name in names))
        self.assertIn("opt/wine/share/wine/nls/c_20127.nls", names)

    def test_guest_launchers_keep_native_d3d9_and_seh_diagnostics(self) -> None:
        """Pin the deployed launcher contract without claiming OX recovery.

        ``+seh`` exposes Wine exception diagnostics.  The web OX crash is an
        unhandled Acknex invalid-BMAP dereference, so this assertion must never
        be interpreted as an exception-ignore or continue-after-fault policy.
        """

        launchers = {
            "player2": "run_azrok_multi2.bat",
            "player3": "run_azrok_player3.bat",
            "player4": "run_azrok_player4.bat",
            "player5": "run_azrok_player5.bat",
            "player6": "run_azrok_player6.bat",
        }
        self.assertTrue(APP_PACKAGE.is_file(), APP_PACKAGE)
        with zipfile.ZipFile(APP_PACKAGE) as package:
            names = package.namelist()
            for account, launcher in launchers.items():
                with self.subTest(account=account, launcher=launcher):
                    self.assertEqual(names.count(launcher), 1)
                    text = package.read(launcher).decode("ascii")
                    self.assertIn("set WINEDLLOVERRIDES=d3d9=n", text)
                    self.assertIn("set WINEDEBUG=-all,+seh", text)
                    self.assertIn(
                        f"Azrok.exe -diag -NX 200 -NWND -PL {account} "
                        "-DIR localauth -IP 127.0.0.1:9201",
                        text,
                    )
                    self.assertNotIn("OX_IGNORE", text.upper())

    def test_private_sources_are_limited_to_lan_or_tailscale(self) -> None:
        self.assertTrue(is_private_client(str(ipaddress.ip_network("192.168.0.0/16")[300])))
        self.assertTrue(is_private_client(str(ipaddress.ip_network("100.64.0.0/10")[300])))
        self.assertFalse(is_private_client("8.8.8.8"))
        self.assertFalse(is_private_client("0.0.0.0"))

    def test_ticket_round_trip_and_expiry(self) -> None:
        ticket = issue_browser_ticket(SECRET, BROWSER_ID, "player2", now=1000, ttl_seconds=600)
        self.assertTrue(validate_browser_ticket(SECRET, ticket, now=1599))
        self.assertFalse(validate_browser_ticket(SECRET, ticket, now=1601))
        self.assertEqual(browser_ticket_claims(SECRET, ticket, now=1200)["account_id"], "player2")

    def test_ticket_is_bound_to_the_secret_and_payload(self) -> None:
        ticket = issue_browser_ticket(SECRET, BROWSER_ID, "player2", now=1000, ttl_seconds=600)
        self.assertFalse(validate_browser_ticket(b"different-private-test-secret", ticket, now=1200))
        self.assertFalse(validate_browser_ticket(SECRET, ticket.replace(BROWSER_ID, BROWSER_ID[:-1] + "x"), now=1200))
        self.assertFalse(validate_browser_ticket(SECRET, ticket, now=1200, expected_account="player3"))
        self.assertTrue(validate_browser_ticket(SECRET, ticket, now=1200, expected_account="player2"))

    def test_browser_binding_persists_and_stable_recovery_binds_more_browsers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = PrivateAccountRegistry(Path(directory) / "accounts.json", SECRET)
            account = registry.session_account(BROWSER_ID)
            self.assertTrue(valid_account_id(account))
            self.assertEqual(len(account), 13)
            recovery_code = registry.export_recovery_code(BROWSER_ID)
            second_browser = "browser_2f7e4e07-1bf8-4df2-8e75-1c4d3bd3d9e6"
            self.assertEqual(registry.import_recovery_code(second_browser, recovery_code), account)
            third_browser = "browser_2f7e4e07-1bf8-4df2-8e75-1c4d3bd3d9e7"
            self.assertEqual(registry.import_recovery_code(third_browser, recovery_code), account)
            self.assertEqual(registry.export_recovery_code(second_browser), recovery_code)
            self.assertEqual(registry.session_account(BROWSER_ID), account)
            self.assertEqual(registry.session_account(second_browser), account)
            self.assertEqual(registry.launcher_for("player"), "run_azrok_seh.bat")
            self.assertEqual(registry.launcher_for(account), "run_azrok_account.bat")

    def test_new_browsers_receive_unbounded_distinct_dynamic_accounts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = PrivateAccountRegistry(Path(directory) / "accounts.json", SECRET)
            browsers = [
                f"browser_{index:02d}0f4e07-1bf8-4df2-8e75-1c4d3bd3d9e6"
                for index in range(20)
            ]
            accounts = [registry.session_account(browser) for browser in browsers]
            self.assertEqual(len(set(accounts)), len(browsers))
            self.assertTrue(all(valid_account_id(account) for account in accounts))
            self.assertEqual(registry.admin_snapshot()["allocation"]["limit"], None)

    def test_recovery_code_is_stable_until_explicit_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = PrivateAccountRegistry(Path(directory) / "accounts.json", SECRET)
            account = registry.session_account(BROWSER_ID)
            first_code = registry.export_recovery_code(BROWSER_ID)
            self.assertEqual(registry.export_recovery_code(BROWSER_ID), first_code)
            second_code = registry.export_recovery_code(BROWSER_ID, rotate=True)
            self.assertNotEqual(first_code, second_code)
            snapshot = registry.admin_snapshot()
            item = next(item for item in snapshot["accounts"] if item["account"] == account)
            self.assertTrue(item["recovery_code_active"])
            self.assertEqual(item["binding_count"], 1)
            self.assertNotIn(BROWSER_ID, repr(snapshot))
            registry_text = (Path(directory) / "accounts.json").read_text(encoding="utf-8")
            self.assertNotIn(first_code, registry_text)
            self.assertNotIn(second_code, registry_text)
            self.assertTrue(item["browser_refs"][0].startswith("browser…"))
            with self.assertRaisesRegex(ValueError, "recovery rejected"):
                registry.import_recovery_code(
                    "browser_7f0f4e07-1bf8-4df2-8e75-1c4d3bd3d9e6", first_code
                )
            self.assertEqual(registry.admin_clear_bindings(account), 1)
            after = registry.admin_snapshot()
            item_after = next(item for item in after["accounts"] if item["account"] == account)
            self.assertTrue(item_after["recovery_code_active"])
            self.assertEqual(item_after["binding_count"], 0)
            self.assertEqual(
                registry.import_recovery_code(
                    "browser_7f0f4e07-1bf8-4df2-8e75-1c4d3bd3d9e6",
                    second_code,
                ),
                account,
            )
            self.assertEqual(
                registry.import_recovery_code(
                    "browser_6f0f4e07-1bf8-4df2-8e75-1c4d3bd3d9e6",
                    second_code,
                ),
                account,
            )

    def test_full_reset_retires_account_recovery_and_other_browser_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = PrivateAccountRegistry(Path(directory) / "accounts.json", SECRET)
            old_account = registry.session_account(BROWSER_ID)
            old_code = registry.export_recovery_code(BROWSER_ID)
            second_browser = "browser_2f7e4e07-1bf8-4df2-8e75-1c4d3bd3d9e6"
            registry.import_recovery_code(second_browser, old_code)

            result = registry.replace_browser_account(BROWSER_ID, old_account)

            self.assertEqual(result["old_account"], old_account)
            self.assertNotEqual(result["account"], old_account)
            self.assertEqual(result["released_bindings"], 2)
            self.assertEqual(registry.session_account(BROWSER_ID), result["account"])
            self.assertNotEqual(registry.session_account(second_browser), old_account)
            with self.assertRaisesRegex(ValueError, "recovery rejected"):
                registry.import_recovery_code(
                    "browser_7f0f4e07-1bf8-4df2-8e75-1c4d3bd3d9e6", old_code
                )
            accounts = {
                item["account"] for item in registry.admin_snapshot()["accounts"]
            }
            self.assertNotIn(old_account, accounts)
            self.assertIn(result["account"], accounts)

    def test_v1_registry_migrates_bindings_and_drops_password_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "accounts.json"
            path.write_text(
                '{"version":1,"bindings":{"' + BROWSER_ID + '":"player2"},'
                '"passwords":{"player2":"scrypt$obsolete$obsolete"}}',
                encoding="utf-8",
            )
            registry = PrivateAccountRegistry(path, SECRET)
            self.assertEqual(registry.session_account(BROWSER_ID), "player2")
            code = registry.export_recovery_code(BROWSER_ID)
            stored = path.read_text(encoding="utf-8")
            self.assertIn('"version":3', stored)
            self.assertNotIn("scrypt", stored)
            self.assertNotIn(code, stored)


if __name__ == "__main__":
    unittest.main()
