"""Contracts for the server-selection page and the browser launch handoff.

The 2012 homepage restoration (the restored home page and its legacy assets) is
not part of this repository.  The page that remains is
``web/azrok_server_list.html``; the static file server
(``tools/boxedwine_local/server.py``) routes ``/`` to it.

Checks that need the BoxedWine runtime page (``index_d3d9web_pathouse.html``)
belong to the bridge repository; they are skipped here when that file is absent.
"""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SERVER = (ROOT / "tools" / "boxedwine_local" / "server.py").read_text(encoding="utf-8")
SERVER_LIST = (WEB / "azrok_server_list.html").read_text(encoding="utf-8")
LAUNCH = (WEB / "azrok_launch.js").read_text(encoding="utf-8")
STYLE = (WEB / "azrok_server_list.css").read_text(encoding="utf-8")
RUNTIME_PAGE_PATH = WEB / "index_d3d9web_pathouse.html"
RUNTIME_PAGE = (
    RUNTIME_PAGE_PATH.read_text(encoding="utf-8") if RUNTIME_PAGE_PATH.is_file() else None
)
NEEDS_RUNTIME_PAGE = unittest.skipIf(
    RUNTIME_PAGE is None,
    "index_d3d9web_pathouse.html lives in the bridge repository",
)


class WebLaunchContractTests(unittest.TestCase):
    def test_bare_root_serves_the_server_list(self) -> None:
        self.assertIn('if route == "/":', SERVER)
        self.assertIn('self.path = "/azrok_server_list.html"', SERVER)
        self.assertNotIn("azrok_home.html", SERVER)

    def test_two_stage_flow_is_explicit(self) -> None:
        self.assertIn("아즈로크 서버 선택", SERVER_LIST)
        self.assertIn("아즈로크 보존 광장", SERVER_LIST)
        self.assertIn('id="connect-button"', SERVER_LIST)
        self.assertIn('new URL("index_d3d9web_pathouse.html", location.href)', LAUNCH)
        self.assertIn('target.searchParams.set("autorun", "1")', LAUNCH)

    def test_server_list_page_is_wired_to_style_launch_and_status(self) -> None:
        self.assertIn('href="azrok_server_list.css?v=restore6"', SERVER_LIST)
        self.assertIn('src="azrok_launch.js?v=coldload2-20260927"', SERVER_LIST)
        self.assertIn('class="server-logo-image"', SERVER_LIST)
        self.assertIn('class="server-npc-image"', SERVER_LIST)
        self.assertLess(
            SERVER_LIST.index('class="server-logo-image"'), SERVER_LIST.index('id="server-title"')
        )
        self.assertLess(
            SERVER_LIST.index('id="server-title"'), SERVER_LIST.index('class="server-npc-image"')
        )
        self.assertIn(".server-npc-image{display:block;width:73px;height:73px", STYLE)
        self.assertIn("margin-left:auto", STYLE)
        self.assertIn('id="online-count"', SERVER_LIST)
        self.assertIn('fetch("/api/private-server-status"', LAUNCH)
        self.assertIn("setInterval(refreshOnlineCount, 10000)", LAUNCH)
        self.assertIn('if route == "/api/private-server-status":', SERVER)
        self.assertIn('player.get("connected") is True', SERVER)

    def test_removed_homepage_is_not_referenced(self) -> None:
        for text in (SERVER, SERVER_LIST, LAUNCH, STYLE):
            self.assertNotIn("azrok_legacy", text)
            self.assertNotIn("azrok_home.css", text)
            self.assertNotIn("azrok_home.html", text)

    def test_launch_reuses_private_admission_and_production_app_contract(self) -> None:
        self.assertIn('fetch("/api/private-session"', LAUNCH)
        self.assertIn('"X-Azrok-Browser-Id": browserId()', LAUNCH)
        self.assertIn("run_azrok_(seh|peer111|multi2|player3|player4|player5|player6|account)", LAUNCH)
        self.assertIn(
            "Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1_fastboot4_questfont1",
            LAUNCH,
        )
        self.assertIn('host === "playazrok.com"', LAUNCH)
        self.assertIn('return "wss://playazrok.com/azrok-ws"', LAUNCH)
        self.assertNotIn("korean7", LAUNCH)
        self.assertNotIn("korean8", LAUNCH)
        self.assertNotIn("compositionupdate", LAUNCH)
        self.assertNotIn("await runtimeWarmup", LAUNCH)
        self.assertNotIn("warmRuntimeCache", LAUNCH)
        self.assertIn(
            "TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim25koreanlocale2",
            LAUNCH,
        )
        self.assertNotIn("/fs/TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1.zip", LAUNCH)
        self.assertIn('target.searchParams.set("root", rootStem)', LAUNCH)
        self.assertIn("boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1", LAUNCH)
        self.assertIn('target.searchParams.set("runtimeStem", runtimeStem)', LAUNCH)
        self.assertIn(
            "/profiles/azrok-jit-grouped-multidirectloops1-currentabi1-facewishle1r10cwdrepublish1-map13009736-r1-20260901.zip",
            LAUNCH,
        )
        self.assertIn('const runtimeIdentityFlags = ["faceWisHle", "ownerThreadIdentity"', LAUNCH)
        self.assertIn('for (const flag of runtimeIdentityFlags) target.searchParams.set(flag, "1")', LAUNCH)
        self.assertIn('"Cache-Control", "public, max-age=31536000, immutable"', SERVER)
        self.assertEqual(SERVER.count("def end_headers(self) -> None:"), 1)
        self.assertIn('target.searchParams.set("ws", trustedBridge)', LAUNCH)

    def test_account_reset_endpoint_is_server_coordinated(self) -> None:
        self.assertIn("def serve_private_account_reset", SERVER)
        self.assertIn('"/api/private-account-reset": self.serve_private_account_reset', SERVER)
        self.assertIn("/api/private-accounts/reset-state", SERVER)

    @NEEDS_RUNTIME_PAGE
    def test_runtime_page_preserves_the_bridge_ws_parameter(self) -> None:
        self.assertIn("const preservedWs=d3d9WebParams.get('ws')", RUNTIME_PAGE)
        self.assertIn("target.searchParams.set('ws',preservedWs)", RUNTIME_PAGE)
        self.assertIn("/\\/azrok-ws(?:\\?|$)/.test(target)", RUNTIME_PAGE)

    @NEEDS_RUNTIME_PAGE
    def test_clean_guest_exit_relaunches_at_character_selection(self) -> None:
        self.assertIn("Module.onExit=function(code)", RUNTIME_PAGE)
        self.assertIn("if(numericCode!==0)", RUNTIME_PAGE)
        self.assertIn("class AzrokTrackedWebSocket extends AzrokNativeWebSocket", RUNTIME_PAGE)
        self.assertIn("azrokReturnToCharacterSelect()", RUNTIME_PAGE)
        self.assertIn("fetch('/api/private-session'", RUNTIME_PAGE)
        self.assertIn("target.searchParams.set('characterSelect','1')", RUNTIME_PAGE)
        self.assertIn("setTimeout(()=>azrokReturnToCharacterSelect(),2500)", RUNTIME_PAGE)
        self.assertIn("new URL('azrok_server_list.html',location.href)", RUNTIME_PAGE)


if __name__ == "__main__":
    unittest.main()
