> **PARTIALLY SUPERSEDED by 556.** The boot-progress result remains valid. Promoting only `C.UTF-8` did not make Korean text visible in the user's Plaza Edit; #556 replaces the final Wine delivery conclusion.

# 555. Boot progress and Korean IME production route (2026-08-08)

## Scope

The normal private-browser launch previously showed a silent black canvas for roughly 45–50 seconds, and committed Korean text reached the BoxedWine FIFO but did not appear in the original Wine/Azrok edit path. This change adds a visible boot state machine and promotes the isolated UTF-8 Unix-locale app candidate without changing `Azrok.exe`, game data, the Windows ACP949 root, server protocol, or the production korean5 runtime.

## VERIFIED — live browser boot progress

- The page shows a modal progress surface from launch until the first real D3D9 `Present`.
- Live stages were observed in the LAN in-app browser: `게임 파일 불러오는 중`, `원본 Azrok 클라이언트 부팅 중`, elapsed 1/25/35 seconds, and `첫 게임 화면 표시 완료` at the first frame around 47–48 seconds.
- Fatal JIT/cache/runtime promise rejections remain visible even when the lean console is hidden.
- The first real frame hides the progress surface; a timer alone cannot declare success.

## VERIFIED — browser to Wine XIM boundary

- The transparent browser input stayed focused through runtime initialization and the first rendered frame.
- Live Plaza commit `한글` produced UTF-8 6 bytes / 2 scalars.
- The 38-word debug runtime showed successful XOpenIM, XCreateIC and XSetICFocus, then two synthetic XmbLookupString calls, two `XLookupChars` results, six returned bytes, last status 2, FIFO served 2, depth 0, drops 0.
- Wine 11 source shows `xim_set_result_string()` decodes those bytes with `ntdll_umbstowcs()` and the process Unix codepage, not the string returned by `XLocaleOfIM()`.

## VERIFIED — locale mismatch and production routing

- The old private launchers requested `ko_KR.EUC-KR`, but the root contains neither a locale archive nor a `ko_KR/LC_CTYPE` locale object. Wine can therefore fall back to C/CP20127 while the fake XIM returns UTF-8.
- The immutable app `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime1.zip` changes only the five automatic private launchers (player2–player6) to `LANG/LC_ALL=C.UTF-8`; all original game/runtime/root data remains unchanged.
- The private landing page now issues that app stem for new sessions.
- Existing URLs carrying the old `guestprofiles6_rsdefaults1` app stem are migrated in the game page before BoxedWine configuration, so old bookmarks do not remain on the lossy locale path.
- LAN live responses contain both the new admission app stem and the boot-progress contract.
- The page also suppresses control-key `keypress` duplication while preserving SDL keydown/keyup.

## Dynamic debugging boundary

- A packet-level S2C `0x000D` trigger was used to reach Plaza; the unmodified client naturally completed its `0x0064` transition and rendered the 3D scene.
- The debug2 single-key export returned bitmask 3 for one SDL Enter press/release pair.
- Browser automation still did not visibly open the Plaza chat edit, so a visible Korean chat string and natural C2S `0x006A` remain **NOT VERIFIED** in this run. The production locale fix is promoted because the lossy conversion boundary is directly established, but final human-keyboard Plaza acceptance remains required.
- A disposable player6 account was opened only to the species-selection page. No character-create packet was sent and no player6 state file was created.

## Verification

- `python -m unittest discover -s tools -p "test_*.py"`: 234/234 pass.
- LAN landing response: UTF-8 IME app stem present.
- LAN game-page response: UTF-8 migration and boot-progress markup present.
- Live browser: korean5 debug runtimes kept currentabi1 `12968408/262144`; Plaza remained rendered during XIM probes.
