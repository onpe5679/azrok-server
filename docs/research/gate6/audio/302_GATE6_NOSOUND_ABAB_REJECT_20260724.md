# Gate 6 - `-nosound` PatHouse A-B-A-B

Date: 2026-07-24

## Scope

This card isolates only guest `-nosound` from the accepted
`boxedwine.upstreamjit64fn6inlineabi2` runtime and its accepted grouped replay
cache. The runtime stem, replay ZIP, game package, root, websocket endpoint,
canvas size, and input hold were otherwise held constant. No build process was
running during any scored window.

## VERIFIED static route

`index_d3d9web_pathouse.html` maps the presence of the URL parameter
`nosound` to `sound=false`; `boxedwine-shell.js` then includes `-nosound` in
the guest command line. `startupArgs` keeps sound disabled, and `KDspAudioSdl`
does not open the SDL audio device. It retains the bounded time-based dummy
queue, so this is not a claim that all guest-side audio scheduling work is
removed. The query is presence based: `nosound=0` is also disabled and was not
used.

## VERIFIED integrity gates

An unscored cache-OFF `nosound=1` run passed visible 1024x768 PatHouse entry
and continuous async-ring operation with zero errors, gaps, and reorders. The
scored replay legs used the accepted ABI2 cache. Every accepted score was
captured only after a visible full PatHouse scene and a 1024x768 CSS canvas;
the direct counter is `D3D9WebDebug.presents` for 30 seconds.

The first B1 attempt produced 107.43 FPS at the selection/transition screen.
It is explicitly discarded and is not included below. The re-entered B1, A2,
and B2 all showed the full room, character, furniture, carpet, and Korean HUD
before scoring. Where the persistent `Azrok1` character appeared in the left
slot, dynamic visual inspection used its actual select path (left character
then the select control) rather than treating a blank slot as PatHouse.

## VERIFIED A-B-A-B result

| Leg | URL condition | Presents / seconds | FPS |
|---|---|---:|---:|
| A1 | sound on | 1,205 / 30.007 | 40.16 |
| B1 | `nosound=1` | 1,094 / 30.000 | 36.47 |
| A2 | sound on | 1,269 / 30.001 | 42.30 |
| B2 | `nosound=1` | 1,203 / 30.001 | 40.10 |

The two matched A-to-B effects are -9.19% (A1 to B1) and -5.20% (A2 to B2);
their median is -7.19%. Condition means are 41.23 FPS for sound-on and 38.29
FPS for `-nosound`, a -7.14% difference. A1-to-A2 drift is +5.33%, exceeding
the +/-3% noise band, so the required B2 extension was performed. Both
matching A-to-B effects remain negative outside that band.

## Verdict

**VERIFIED performance REJECTED.** `-nosound` is a valid guest configuration
and preserves the tested render path, but it does not improve this PatHouse
workload. It remains opt-in for diagnostic use only; the accepted sound-on
ABI2 route remains the default. No runtime, cache, or loader default changed.
