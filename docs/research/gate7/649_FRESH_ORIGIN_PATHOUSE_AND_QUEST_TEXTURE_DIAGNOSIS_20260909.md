# 649 — Fresh-origin PatHouse and quest texture diagnosis

Date: 2026-09-09 KST

## Scope and current boundary

The user reports failure to enter 3D PatHouse after character creation in a
completely new browser session. Baby-food UI cannot be checked until that works.
Fresh creation and upper quest-list font corrections are deployed. This document
separates runtime acceptance from the opt-in diagnostic instrumentation.

## VERIFIED

- Local and production `azrok_server.py` initially matched SHA-256
  `967248e6078ee448eebe0759a9fd0a2f41a6f222842264f1c796cd0a4dca4b41`.
- Running production core accepted an isolated diagnostic character and emitted
  standalone `0006[00,00]`, then `0003/0007/0005/000A/000B` after a client `0007`.
  The 472-byte S2C `0007` contained food byte `0xEA=1`, `0xEB=0`, all other food
  counts zero. The #642 reason-for-new-food correction is active in the process.
- Existing persisted inventories are preserved. The first in-app browser test
  reused a previous account with a character; it is excluded from fresh-origin
  acceptance evidence.
- A new loopback origin `http://localhost:18769` proxies production assets and
  issues a new browser account. Only the launch script is adapted to use public
  production WSS from localhost and expose opt-in input/texture diagnostics.
  Existing browser storage is not deleted. This is an isolated-origin test,
  not a claim of a clean physical browser profile on the public origin.
- `d3d9web-runtime.js` diagnostic dumps now decode actual D3D formats 21/22/23/26,
  ignore non-base mip levels, guard missing textures, and retain a bounded recent
  resource sheet. Indexed draws with vertex declarations are now traceable using
  their actual layout. These changes are behind existing trace opt-in/arm gates.
- Source-based pixel/bounds/layout checks and page contracts passed. Runtime
  SHA-256 `101438a7c4e294745a0cb3f50731b43f6fbbdb9b12ff911a089a445d2786b852`
  was deployed with page import key `questtitle-formatdump14`; no service restart.
  Pre-change copies are in production `rollback/questtrace-20260909`.

## Verification boundary

Actual fresh creation, room entry, quest font, baby-food icon/description and
natural tutorial completion/reward have all been verified below. The clean
storage test uses an isolated origin connected to production WSS, not a separate
physical browser profile on the public origin.

## VERIFIED — fresh-session root cause and server correction

In the isolated-origin failure session, the actual screen retained the purple
SelectEgg background and empty naming popup, with HUD and tutorial overlaid.
This was not a 3D PatHouse acceptance.

Production entity 39 sent **zero C2S 0004 creation requests and zero C2S 0007
requests**. On its eighth heartbeat the server nevertheless sent
`0003/0007/0005/000A/000B`. The 472-byte restore had date zero but all food
counts zero, and no canonical character file existed. The source switch
`SERVER_AUTO_CREATE_ENABLED = True` enabled exactly this rescue-era path,
despite the adjacent comment requiring it to remain disabled. It bypasses the
verified CreateEgg transaction and UI-cleanup ACK.

The switch is now `False`. A new regression waits through 12 heartbeats and
asserts no scene bundle, selected binding, or canonical creation; an actual
subsequent C2S 0004 still receives standalone 0006, followed by a correct fresh
room bundle and baby food after C2S 0007. The old True switch fails the same
test on heartbeat eight. Focused regression: 152 tests PASS.

The corrected core SHA-256 is
`deb645dbad39335be003fb0a978b3183f85c14462d3aa9f1c8cc9e640a6a7034`.
It was deployed and only `azrok-core` restarted. GUI acceptance is being run
on another previously unused origin, port 18770.

Evidence: `artifacts/20260909_fresh_origin_entity39_sanitized_wire.json` and
`artifacts/20260909_postfix_regression.txt`. No existing character was modified.

## VERIFIED — why the trace arm collected no draws

`ensureRenderer` reassigns the runtime's canvas to the WebGL overlay
`d3d9web-canvas`, while the old page button armed only the source `canvas`.
The failure session showed source arm=1 but no command counters or trace rows.
The button now selects the actual overlay, falling back to the shared source.
Runtime import key is `questtitle-formatdump15`, runtime SHA-256
`79378751a366bc66d2dc6bd57179e9aad60c2229d93883908b2e64ea1dfd6704`.
This corrects the diagnostic arm, not the font rendering itself.

## VERIFIED — fresh-origin corrected GUI acceptance

The second unused origin, port 18770, had a new account and no canonical files.
Ten actual heartbeat requests passed without an unsolicited scene bundle.
The naming popup remained usable. Real key input entered `freshnine`, and the
confirm button produced C2S 0004, standalone S2C 0006, natural C2S 0007, and the
normal room bundle. Canonical revision 2 contained tutorial 5/212 and baby food
1000=1, hamburger1001=0. The same process then visibly rendered the carpet,
furniture, room, baby character, named HUD, and quest panel. No reselect or
reload intervened between creation and the 3D room.

Evidence: `artifacts/20260909_fresh_origin_entity3_fixed_sanitized_wire.json`
and live CUA screenshot from in-app browser tab 3. This demonstrates the
server regression repair on an isolated production-proxy origin; it does not
claim a separately installed physical browser has been tested.

## VERIFIED — actual upper/lower texture identification

With the corrected overlay arm, the visible title maps exactly to the saved
decompiler coordinates. Both draws are UP, FVF708, stride40, A4R4G4B4(format26),
1024x32, same UV and render state. Source setup and actual drawing agree.

| Draw | Screen minimum | Handle | Raw FNV |
|---|---|---:|---|
| Upper broken title | 828,232 | 7206 | 7c75ad85 |
| Lower readable title | 795,390 | 7204 | a96b6c9d |

Both use SRCALPHA/INVSRCALPHA, alpha blend enabled, alpha test/depth disabled,
color write15. Thus the previous zero-row trace did not disprove A4 usage.
The complete source-glyph rasterization hypothesis is being tested with an
immutable root changing only Wine user.reg FontSmoothing from2 to0.

## VERIFIED — same-character font A/B

The canary root `...xim25koreanlocale2-questfontsmoothing0-1.zip` differs only
in user.reg's FontSmoothing setting. All archive members and CRCs were checked;
its SHA-256 is `0fb9ad83dcf616a7f8c5c886122168ae3b6c03487a59d0eb44952de38c964ecb`.
On previously unused origin18771, the same character `freshnine` re-entered
PatHouse with the upper title fully readable. Lower title/body and the 3D room
remained readable/visible. Baseline upper FNV7c75ad85 became aff6a715; lower
a96b6c9d became ad97e03b. Geometry, A4 format and render states were identical.
The hash change alone is not proof because transparent RGB bytes are included;
the actual screen supplies the visual acceptance. Evidence summary is
`artifacts/20260909_quest_title_same_character_ab.json`.

Saved Ghidra output identifies upper RGB1/1/1, bold12 text, while lower uses
RGB8/43/76. Wine11's grayscale glyph path floors partial coverage multiplied by
RGB1 to zero; the client packer treats RGBzero as alpha0. Disabling smoothing
avoids that interaction. The actual final Wine aa_flags value has not been
sampled with a debugger; the setting-level cause is separated by the real A/B.

Root-only promotion would not repair existing prefixes: IDBFS is mounted at
`/root` per origin, not per root archive name. A new immutable app candidate
adds one idempotent `reg add` before launching Azrok to apply FontSmoothing0
also to existing prefixes. Retained origin18770 using the original root and
the new app also showed the complete upper title in PatHouse (tab5).

## VERIFIED — font app production promotion

The immutable app `...fastboot4_questfont1.zip` changes only
`run_azrok_account.bat`, adding the FontSmoothing REG_SZ0 command before launch.
App SHA256: `d92ca039cc8268c975891b1061605818c388e0c67eeade5d20f7d5e82679efa8`.
No game executable, renderer shader, root default or HLE default was changed.
The production launcher now selects this app, and old fastboot3/4/5 URLs migrate
to it while preserving identity, root, runtime and other query parameters.
Actual migration-JS execution tests and 44 page/home contracts passed.
Public HTTP bytes match local SHA256 for all three promoted files:

- azrok_launch.js: `d16567b03c05ad6bb05b14dcb8368efcf3d00ae67a860b15bbd5acd1eaef87cd`
- azrok_server_list.html: `2f3d5d5c8e65656f60414b8c311cc90e8a78054c4511c25ca716caaf55748add`
- index_d3d9web_pathouse.html: `8cc2403dc0294395ded4dae718e42111ed8bb29de4d1e3f31dc4d76c4f838117`

Pre-promotion static files are retained in production
`rollback/questfont-default-20260909`. Static promotion required no restart.

## VERIFIED — additional returning-character boundary

Retained-origin tab5 waited on the selection screen until the existing-character
rescue auto-select sent a scene on heartbeat8. The room/title rendered, but the
HUD name and food inventory were empty. Entity5 had zero natural C2S0005/0007;
server binding selected freshnine with canonical food1. Thus this screenshot
validates font rasterization, but does not validate complete character readiness.
Normal selection and removal of that rescue shortcut are being checked.

Both rescue flags are now False; the obsolete --auto-select-existing service
argument is removed. Production core was restarted and is active with server
SHA256 `480dacc0dfb791582fc0e5891a473b0219bb2b6bbb7efe82c8d26664fab682d8`.
The added returning-character test waits12 heartbeats without an unsolicited
bundle, then selects via actual C2S0005. The old True setting fails at heartbeat8.
Final focused server/content/home regression:153 tests passed.

## VERIFIED — final default completely fresh-origin acceptance

Origin18772 had no existing account or prefix. Its normal server-list launcher
selected questfont1 automatically. A new `newnine` character was created through
the actual GUI after waiting on the naming screen; there was no synthetic scene.
The same process entered the visible 3D room with its correct HUD name, complete
upper and lower quest titles, and the first tutorial dialogue. Opening the baby's
actual radial Food menu showed the pink baby-food bottle in inventory slot0;
hover showed the Korean baby-food description. This is direct icon evidence,
unlike the earlier retained freshnine session's blank grid. Original Refri_0.wis
also independently decodes to a valid bottle; no icon patch was applied.
Evidence: live CUA tab7 and
`artifacts/20260909_origin18772_newnine_sanitized_wire.json`.

## VERIFIED — actual baby-food tutorial completion

`FUN_00519030` emits event type2 when the same slot is released twice within
500ms (with double-click enabled by `005192D0`); ordinary release emits type1.
`FUN_005CFCA0` requires type2 before the food consumer `005D27C0`. This corrects
#125's imprecise release/click label. Single diagnostic pulses only showed the
tooltip. Two100ms mouse pulses180ms apart entered the original food action.
No synthetic consumer call or client binary patch was used.

The actual GUI showed the food tutorial complete, currency0→100, and the next
upper/lower title `용변을 보자` fully readable in the 3D room. Production wire
at13:49:52Z recorded0011 retire→0012 reward100/channel2→S2C0005 ACK→0011 next→0007.
Canonical revision5 confirms currency100, kind5/aux202/value19 and completed
key `g1:r0:k5:a212:c100`, with a saved snapshot.

The infant path does not emit the general-food0014/0008 pair. Baby-food quantity
remains1 in canonical; do not describe this acceptance as inventory1→0.
The scoped user outcome is actual feeding and tutorial progress, both confirmed.
