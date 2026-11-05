# Gate 2c CPU-profile semantics and guest proxy boundary

Date: 2026-07-20

## Corrected interpretation

**VERIFIED (source):** `D3D9WEB_CPU_PROFILE.samples` is not a time sample.
`normalCPU.cpp` keeps a `thread_local` executed-instruction counter and samples
one decoded opcode per 4096 instructions. Its one-second report condition is
checked only when that instruction sample fires. Consequently, sample counts
from different guest threads do not share a time denominator and cannot be
converted into module CPU percentages.

The earlier conversational interpretation that `acknex.dll` used about 96% of
CPU is withdrawn. The profile remains useful for per-thread opcode mix only.

## `proxy_us` boundary

**VERIFIED (source):** BoxedWine's `profileProxyMicros` surrounds only the
synchronous runtime-thread call which executes the already assembled command
batch. It excludes:

- command construction and payload copying inside the guest `d3d9.dll`;
- `cpu->memory->memcpy(commandBytes, arg1, arg2)` at the INT 0x9A boundary;
- growth and copying into `batchedCommandBytes`.

It includes the worker-to-main synchronous wait/scheduling and the JS/WebGL
runtime dispatch. It therefore is neither total bridge time nor pure JS time.

## Measurement required before optimization

The next timed build must report the following 120-Present sums separately:

1. guest large-payload packet-copy time;
2. guest Present INT round-trip time;
3. BoxedWine guest-memory copy time;
4. BoxedWine batch-vector copy time;
5. synchronous proxy total;
6. main-thread JS/WebGL dispatch time.

An instrumentation-off control and instrumentation-on run must use the same
steady PatHouse scene. CPU-profile module sample counts are not accepted as a
substitute for these wall-time sums.

## Static-buffer-cache decision

**VERIFIED (source and prior visual regression):** the first cache attempt
changed the WebGL array buffer without making that buffer identity part of the
vertex-input signature. The cached VAO therefore retained attributes from an
unrelated buffer, producing missing walls and character-shaped furniture.

**VERIFIED (prior probe, pending fresh persisted capture):** handle 10's first
eight full-buffer hashes differed. A static-screen assumption alone does not
permit suppressing its uploads. Any guest-side upload suppression must compare
the current lock range with a shadow of the last *successfully uploaded* bytes
and use an exact `memcmp` after a hash match. `DISCARD`/`NOOVERWRITE`, failed
uploads, recreate/reset, and invalid shadow ranges remain non-suppressible.

## Current dynamic boundary

**VERIFIED:** the resumed server, WebSocket bridge, and browser connection are
live. At heartbeat 9 the server sent the automatic PatHouse sequence (`0x0003`
with `Data\Space\PatHouse`, followed by `0x0007`, `0x0005`, `0x000A`, and
`0x000B`). At the time of this note the client still displayed its loading
advertisement, emitted no resource uploads in the latest 120-Present windows,
and had no `D3D9WEB_PHASE6_ERROR`. Those 7--11 FPS windows are loader data and
are not a PatHouse performance result.
