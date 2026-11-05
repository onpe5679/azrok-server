# 327 Liftoff A-B-A harness and execution boundary

## Status

**VERIFIED static harness; dynamic measurement NOT STARTED.** This is the
separate standard-browser diagnostic authorized only as an idle-slot card. It
does not alter the accepted runtime, page, cache, or game service.

## Harness repair

The original helper measured the page HUD's periodic accumulated sample rather
than the required direct Present source and ran only A-B. Its static contract
is now:

- Default Edge A1 -> `--js-flags=--no-liftoff` B -> Default Edge A2, each with
  a distinct temporary profile and CDP port;
- only B has the V8 flag; the launched browser command line is independently
  checked and recorded;
- exactly one page target, exact frozen URL at target/readiness/start/finish,
  visible start/end, 1024x768 canvas, direct `D3D9WebDebug.presents` positive
  delta and a 30-second wall-time tolerance are all hard gates;
- the measured FPS is direct Present delta / wall time, not the HUD timer;
- the Liftoff wrapper fixes `MeasureSec` to 30.

All three edited PowerShell files parse successfully. This is static proof
only; it is not a browser sample.

## Dynamic preflight

**VERIFIED:** 8765/9200/9201/9300 were all loopback listeners and no
make/Emscripten/clang/wasm-link process was active. No separate desktop
Chrome/Edge process existed before launch, so a new isolated instance would
not collide with an existing standard-browser renderer. ChatGPT and Codex
processes remained running.

## Execution boundary

The authorized attempt to start the isolated Liftoff wrapper was rejected by
the local execution policy before its child PowerShell/Edge process launched.
Therefore no Edge process, page load, CDP target, renderer, CSV row, Present
sample, or Liftoff comparison exists. Do not bypass this policy with another
browser-control surface or a synthetic runner. When a permitted process launch
is available, rerun this exact harness with the frozen accepted URL and record
pre/post asset hashes; until then Liftoff remains **NOT MEASURED**.

**VERIFIED post-attempt:** no desktop `msedge`/`chrome` process and no
`artifacts/browser_diagnostics` output directory existed after the rejection.
