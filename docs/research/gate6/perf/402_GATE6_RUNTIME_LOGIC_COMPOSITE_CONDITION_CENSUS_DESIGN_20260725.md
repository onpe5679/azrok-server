# 402 -- Runtime-lazy logical composite conditions: private census design

Date: 2026-07-25  
Status: **VERIFIED static/dynamic design; private coverage diagnostic authorized, candidate implementation not yet authorized**.

## Independent hot path

The completed condition census records these six helper entries over a steady
15-second PatHouse interval: BE 2,369; NBE 103,886; L 88,700; NL 70,015; LE
241,115; NLE 6,275.  Their total is **513,360 / 15 s = 34,224/s** (310).
This does not reopen P/NP, Z/NZ, B/NB or S/NS: those cards remain closed.

311 correctly rejects a general runtime composite inline because `FLAGS_NULL`
may represent a producer whose CF/OF needs `dst`, `src`, `result`, `oldCF` or
CFOF handling.  A smaller exact subset exists but has not been measured:
runtime logical `TEST`, `AND`, `OR`, `XOR` in **b8 or b32**.  These eight types
have CF=OF=0, so for a width-masked result their conditions are exactly:

```text
BE=ZF, NBE=!ZF, L=SF, NL=!SF, LE=ZF|SF, NLE=!(ZF|SF)
```

The existing compile-known emitter already uses this arithmetic for b8/b32
logical producers (`wasm/jitWasmCodeGen.cpp:13627-13709`).  Runtime b16 is
**not** included: it is absent from the existing arm and remains helper-only
until a separate static proof and fixture close that width.

## Fail-closed scope

Only the eight b8/b32 logical enum values may admit.  `FLAGS_NONE`, CFOF and
its predecessor, all b16 producers, ADD/ADC/SBB/SUB/CMP/INC/DEC/NEG, shifts,
DSHL/DSHR and unknown/future type IDs must execute the existing helper.
In particular, CFOF cannot be treated as logical merely because its current
type appears benign: CF/OF are materialized while ZF/SF refer to the prior
producer (`cpu.cpp:883-893`).  `FLAGS_NULL` is compile-time knowledge loss,
not an instruction to guess the runtime CPU type.

## Authorized first step: coverage only

Create one private isolated cache-OFF diagnostic macro/ABI, not a candidate.
It must count for each of BE/NBE/L/NL/LE/NLE:

- helper entries by effective runtime lazy type (including explicit CFOF/prev
  and invalid buckets);
- potential logical-helper coverage split by b8/b32 producer; and
- retained helper fallback.

The diagnostic snapshot must prove each helper entry is partitioned by runtime
type, explicitly account for every CFOF predecessor, and reconcile each
potential b8/b32 logical subset against its type rows. It does not claim a
direct admission yet. Any unknown
type, counter partition mismatch, ABI/layout mismatch, record/replay flag or
mixed diagnostic mode rejects before guest start.  The page uses a visible
PatHouse cache-OFF interval with explicit pre/post reads; it collects no FPS.

Only material nonzero steady admission opens a separate runtime-inline
candidate.  That candidate still requires exhaustive b8/b32 result-boundary
differentials, every excluded producer/CFOF fallback row, stale
`currentLazyFlags=FLAGS_NULL`/block-merge/bailout fixtures, then cache-OFF
render -> record/replay -> fresh-process A-B-A(B).
