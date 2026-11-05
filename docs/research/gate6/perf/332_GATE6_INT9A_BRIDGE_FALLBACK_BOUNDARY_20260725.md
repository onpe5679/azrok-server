# 332 INT 0x9A bridge fallback boundary

## Status

**VERIFIED static/dynamic-evidence audit; no INT 0x9A optimization candidate is
open.** No code, build, browser run, cache, replay, or FPS sample was performed
for this card.

## What EOC1 measures

EOC1 observed 786,355 `Int9A` tags over 22.337 s (11.29% of `fn_8`, about
35,204/s). It records only the decoded opcode immediately before canonical
single-op emulation ([317](317_GATE6_EMULATE_OPCODE_CENSUS_20260724.md)); it
does not identify the stack command index, D3D9Web dispatch type, JS roundtrip,
scene phase, CPU time, or completed Present epoch. Therefore that count is not
a bridge-call count or a CPU-cost measurement.

## Direct static boundary

The dynamic JIT explicitly routes `dynamic_int9A` to `emulateSingleOp`
(`source/emulation/cpu/jit/jitOther.h:141-143`). Canonical execution reaches
`normal_int9A`, which reads stack index and calls `callD3D9Web`, then performs
normal `NEXT()` (`source/emulation/cpu/normal/normal_other.h:201-210`). In the
active D3D9Web configuration, `common_int9A` has the same callback path
(`source/emulation/cpu/common/common_other.cpp:43-50`).

`callD3D9Web` accepts its dedicated bridge range, reads stack arguments,
performs index-specific host dispatch, and returns results through EAX
(`source/opengl/d3d9web.cpp:802-835`). Its MT dispatch can entail a synchronous
main-thread JavaScript roundtrip. Removing the helper boundary would therefore
have to retain stack read/fault behavior, EAX, EIP/NEXT, GP/segment
synchronization, SMC bailout, ordering, and JS-visible synchronous effects.
There is no safe generic generated-Wasm substitute.

## Dynamic-evidence boundary

Existing source already has `BOXEDWINE_D3D9WEB_INT_CENSUS`: it logs bridge
index/bytes, generic inner opcode and guest-batch information every render
thread 120 Presents. `BOXEDWINE_D3D9WEB_BRIDGE_PROFILE` independently emits
per-index `calls` and `callMicros` on that cadence. Neither tag has a retained
Azrok run. The old phase 2/3 traces are synthetic index 0/1 proofs, not an
Azrok command-composition sample.

`callMicros` is synchronous bridge wall residence, including proxy/wait, not
CPU-exclusive time. The two existing records do not carry a shared sequence
identifier, and worker CPU sampling is also unjoined, so EOC1's opcode count
cannot currently be attributed to command type, wall cost, or CPU time.

## Reopen condition

Only a private cache-OFF diagnostic may reopen this card. Reuse the existing
`INT_CENSUS + BRIDGE_PROFILE` instrumentation but emit one shared 120-Present
sequence ID/record. It must remain no replay/cache/FPS and treat trap elapsed
as wall residence, not CPU time. CPU-exclusive ranking additionally requires
same-TID/epoch worker CPU sampling. Until then INT 0x9A is held closed; the
MOVSB/MOVSD paths are unrelated.
