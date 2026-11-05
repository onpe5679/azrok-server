# 140 Gate 2b: Wine 10 does not restore the missing PatHouse room

Date: 2026-07-19

Status: **VERIFIED** for the direct runtime comparison.

## Why this comparison was run

The local BoxedWine 26R1 source explicitly warns that Wine 11 has
OpenGL/Direct3D issues and recommends trying Wine 10 when a game has a black
screen. This made Wine 10 the lowest-cost version-isolation test after 139,
without modifying the game binary or beginning a replacement renderer.

## Inputs and isolation

- Same custom native BoxedWine 26R1 executable as 139.
- Same unmodified disposable `Azrok_runtime` mount and named client contract.
- Fresh BoxedWine root for the Wine 10 prefix:
  `azrok_root_release_wine10`.
- Official BoxedWine filesystem
  `TinyCore15Wine10.0.zip`, 156,582,181 bytes, internal `Wine 10.0`, SHA-256
  `F0ED13EAF0C11BC95B229E2A747F04167C4E63445DC274D122758BD7E84B5572`.
- Fresh isolated preservation-server namespace and account.
- No D3D trace was enabled (`WINEDEBUG=-all`); this run is a visual
  compatibility comparison rather than a call-count run.

The exact launch contract was:

```text
Azrok.exe -NX 200 -NWND -PL wine10_scene -DIR localauth -IP 127.0.0.1:9200
LANG=ko_KR.EUC-KR
LC_ALL=ko_KR.EUC-KR
```

## PatHouse UI entry contract (VERIFIED)

For a comparable client-side PatHouse transition, the required UI order is:

1. Select one of the four Azrok characters.
2. Click the lower-left create button.
3. Enter the character name.
4. Confirm creation.

Clicking create before selecting an Azrok is not an equivalent scene-entry
route and must not be used for subsequent rendering comparisons.

## Result

Wine 10 created the OpenGL window, displayed the character-creation UI,
connected to the local server, followed the UI entry contract above, created
the isolated character, and reached the PatHouse outer UI. The server received
the normal post-create state traffic.

The visible PatHouse result remained the same failure observed on Wine 11:

- purple UI/fallback canvas remains where the 3D room should be;
- dynamic Korean text is still garbled despite the CP949 environment;
- no claim is made about BGM because this comparison deliberately used
  `-nosound`.

Wine 10 does **not** restore the room on the clarified UI route. The earlier
Wine 11 sample in 139 predates that route clarification, so a strict
Wine-11-versus-Wine-10 conclusion remains **NOT VERIFIED** until Wine 11 is
repeated with the same select-then-create sequence. This result does not yet
distinguish a shared WineD3D fixed-function issue from BoxedWine's x86/GL
integration.

## Gate 2b comparison status

| Stage | Wine 10 result |
|---|---|
| (a) launch | PASS |
| (b) D3D device | NOT independently traced; 2D D3D UI display is consistent with device creation |
| (c) visible screen | PASS for 2D UI; PatHouse room composition FAIL |
| (d) frames | PASS visually; no performance claim from this run |
| (e) server connection | PASS |

## Decision impact

Wine 10 reproduces the missing composition on the strict UI route. Repeat the
Wine 11 side with the same route before ruling out a Wine-version-only
workaround. The project should not infer browser/WebGL viability from the
current runs, and should not build a drop-in WebGL backend until this renderer
failure is isolated against a non-BoxedWine desktop Wine path or an equivalent
targeted WineD3D comparison.

## Evidence

- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine10_scene_0445_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/server_9200_wine10_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/source/ui/utils/boxedTranslation.cpp`
