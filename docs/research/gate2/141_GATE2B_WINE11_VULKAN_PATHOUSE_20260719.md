# 141 Gate 2b: Wine 11 Vulkan renderer restores visible PatHouse 3D

Date: 2026-07-19

Status: **VERIFIED** for this native BoxedWine/Wine 11 Vulkan run.

## Purpose

After WineD3D on Wine 11 submitted PatHouse indexed geometry but left the
room pixels absent (139), test the renderer selection without modifying
`Azrok.exe`, `acknex.dll`, assets, packets, or the preservation server's
PatHouse response.

## Isolation and renderer selection

- Host: the existing custom native BoxedWine 26R1 `Release|x64` build. Its
  project configuration includes `BOXEDWINE_VULKAN`.
- Guest filesystem: the same official `TinyCore15Wine11.0.zip` used by the
  previous Wine 11 run.
- Game mount: the same unmodified disposable `Azrok_runtime` mount.
- Wine prefix: `azrok_root_release_wine11_vulkan`, cloned from the saved Wine
  11 prefix before configuration. The source Wine 11 prefix remains intact.
- Exact guest registry evidence:

  ```text
  HKEY_CURRENT_USER\Software\Wine\Direct3D
      renderer    REG_SZ    vulkan
  ```

- Launch contract:

  ```text
  Azrok.exe -NX 200 -NWND -PL wine11_vulkan -DIR localauth -IP 127.0.0.1:9200
  LANG=ko_KR.EUC-KR
  LC_ALL=ko_KR.EUC-KR
  WINEDEBUG=-all
  ```

The renderer registry write and its separate `reg.exe query` were both made
inside the new Wine 11 prefix. `reg.exe` printed success; BoxedWine itself
returns exit code 1 after the unrelated guest `winebth` service warning, so
the textual registry value—not that host exit code—is the verification.

## PatHouse entry used for this renderer check

The automated BoxedWine window forwards mouse input but did not forward text
input through either Computer Use text/key events or Windows On-Screen
Keyboard. The normal fresh-character route was therefore exercised through
Azrok selection and the name prompt up to the client-side required-name
validation, but not used to create this test character.

To isolate the renderer result without changing the game executable, one
existing canonical `Azrok1` state was copied into the **new, isolated** server
namespace for account `wine11_vulkan`. On login the original client displayed
that occupied slot; its normal `C2S 0x0005` slot/continue action then caused
the preservation server to restore the state and send the usual PatHouse
bootstrap:

```text
C2S 0x0005 [00]
S2C 0x0003  Data\Space\PatHouse
S2C 0x0007  restored character snapshot
```

This is a persisted-character entry route, not a replacement protocol or a
binary patch. It is sufficient to verify the Wine renderer while leaving the
fresh-name UI automation limitation explicitly separate.

## Result (VERIFIED)

The client entered PatHouse and visibly rendered the 3D floor, rug, furniture,
and Azrok character. This replaces the previous purple/fallback PatHouse
composition in the Vulkan-configured Wine 11 run.

The local server independently recorded the expected slot selection,
`Data\Space\PatHouse` scene response, restored 0x0007 snapshot, and subsequent
client state traffic. The BoxedWine process remained live after the scene was
shown.

| Gate 2b stage | Wine 11 Vulkan result | Direct evidence |
|---|---|---|
| (a) launch | PASS | native BoxedWine window and game UI appeared |
| (b) D3D device | PASS | original D3D client rendered both UI and PatHouse 3D; no trace was enabled in this performance-safe run |
| (c) screen output | PASS | visible 2D UI **and** PatHouse floor, rug, furniture, and character |
| (d) frames | PASS (visual) | scene remained live after the transition; no FPS number was measured |
| (e) server connection | PASS | C2S login/0x0005 and S2C PatHouse bootstrap captured |

## Interpretation

**VERIFIED:** a Wine 11 configuration with `renderer=vulkan` can render the
actual PatHouse 3D scene in native BoxedWine on this host.

**INFERRED, high confidence:** the earlier missing-room result is on the
WineD3D/OpenGL composition path rather than a missing `.wmb`, missing
texture, or failed `Data\Space\PatHouse` load. The prior run had submitted
indexed geometry, while this run shows that same scene's world pixels after
only the Wine renderer backend selection changed.

**NOT VERIFIED:** this is not a strict fresh-character-create A/B because the
Vulkan run uses a pre-existing isolated slot to bypass the separately observed
automated-text-input limitation. It also does not establish browser BoxedWine
support: browser targets WebGL/WASM, not native host Vulkan. The host log has
non-fatal missing optional Vulkan-symbol messages; their relationship to the
working scene is not yet established.

## Evidence

- `artifacts/boxedwine/20260719_gate2b_native/wine11_vulkan_registry_set_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_vulkan_registry_query_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_seeded_pathouse_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/server_9200_wine11_vulkan_seeded_stdout.log`
- live native window: `Gate2b Wine11 Vulkan PatHouse seeded`
