# 401 -- INT 0x9A D3D9Web bridge: joined-census boundary

Date: 2026-07-25  
Status: **VERIFIED static/dynamic frontier audit; direct optimization NOT OPEN**.

## Why this is the next diagnostic, not an optimization claim

The private EOC1 cache-OFF PatHouse interval records `786,355` `Int9A`
interpreter-fallback entries in 22.337 seconds: **35,204.15/s**, 11.29% of
`fn_8` (317).  This is the only individually identified, high-frequency
fallback still not consumed by an accepted or performance-rejected Gate 6
card.  It is a rendering boundary: D3D9Web uses guest `INT 0x9A` for its
command transport.

That count is not a bridge-call count, a per-index distribution, CPU time,
JavaScript residence time, or FPS cost.  It must not be converted into an
optimization benefit.  The other EOC1 residual 21 opcode buckets total
2,098,756 / 22.337 seconds (30.13278% / 93,958.72/s), but their individual
1,365-word snapshot is not retained; the aggregate does not identify an
instruction candidate.  `flags` is also only a family aggregate
(38,279.62/s); fetch-next, conditions, MOVSD/MOVSB/FISTP, parity, Z/NZ,
R2 and `-nosound` are already closed by their own evidence.

## Direct static boundary

`Jit::dynamic_int9A` unconditionally calls `emulateSingleOp()`
(`source/emulation/cpu/jit/jitOther.h:141-143`).  That fallback owns mixed
block EIP handling, dirty-GP synchronization, `fn_8` / `runNextSingleOp`, GP
and segment invalidation, and bailout/lazy-state reset.  Normal execution is
also not a trivial leaf: `START_OP -> cpu->peek32(0) -> callD3D9Web -> NEXT`
(`normal/normal_other.h:201-210`).

`callD3D9Web` reads three stack words, range-checks the private command index,
and dispatches index-specific synchronous work that changes EAX
(`source/opengl/d3d9web.cpp:802-835`).  A future direct bridge helper would
therefore need exact stack-fault, index, EAX, ordering, EIP, active-block,
bailout and GP/segment invalidation equivalence.  Simple Wasm inlining is
not semantics-preserving and is not authorized.

## Required private joined census

Before any implementation, a cache-OFF/no-record/no-replay/no-FPS private
diagnostic must join existing `BOXEDWINE_D3D9WEB_INT_CENSUS` and
`BOXEDWINE_D3D9WEB_BRIDGE_PROFILE` data on one shared 120-Present sequence.
Each read must include:

- generated `fn_8` Int9A delta;
- bridge command-index calls and bytes;
- bridge `callMicros` by index;
- generic inner opcode and guest-batch counters; and
- if CPU ranking is claimed, the same worker TID/epoch CPU sample.

The snapshot needs a mutex/ABI/layout invariant and an exact private stem;
the page must fail closed on any sequence mismatch, invalid index partition or
mixed record/replay/capture mode.  Visible PatHouse and advancing Present are
integrity conditions only.  No FPS is permitted from this instrumented asset.

Only a materially concentrated, semantically auditable bridge sub-route can
then open a separate direct-helper design and its full fixture -> cache-OFF
render -> record/replay -> fresh A-B-A path.
