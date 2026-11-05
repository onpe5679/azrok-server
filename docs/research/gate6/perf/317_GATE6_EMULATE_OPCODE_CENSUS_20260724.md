# 317 — `fn_8` interpreter fallback opcode census (cache-OFF only)

Status: **VERIFIED static/build/browser / BSWAP follow-up REJECTED**

## Scope

This card starts only after the accepted `fn_6` residual investigation closed
without a replay-safe reason split (315–316).  It does not reopen any rejected
condition, parity, direct-tail, sound, or compiler-flag card.  It is a
diagnostic measurement card, not an optimization and not an FPS sample.

## Directly verified static chain

- **VERIFIED:** The accepted grouped cache has 134 groups and 12,192 static
  generated-Wasm `helpers.fn_8` callsites across 132 groups.  Import presence
  is not an execution claim.
- **VERIFIED:** `HELPER_EMULATE_SINGLE_OP = 8`; table entry 8 is
  `wasmHelper_emulateSingleOp`.
- **VERIFIED:** The helper records the `Emulate` family then calls
  `jitRunSingleOp(cpu)`, which calls `CPU::runNextSingleOp()` exactly once.
  It is therefore a C++ boundary plus canonical one-instruction decode,
  dispatch, and interpreter semantics—not an interchangeable Wasm helper.
- **VERIFIED:** The generated fallback writes mixed-block EIP as needed,
  syncs dirty GP registers, arms SMC bailout, calls `fn_8`, invalidates all GP
  and segment caches, checks bailout, then resets compile-time lazy-flag
  knowledge.  Generic helper removal is unsafe.
- **VERIFIED:** The earlier cache-OFF helper census (313) observed
  `emulate=5,938,231` across 22.302 seconds, approximately 266,264 entries/s.
  This is helper-entry coverage only, not accepted-replay coverage, CPU time,
  or FPS.

## Narrow candidate boundary

`BSWAP r32` is statically a possible later narrow candidate: it has no flags,
memory, or exception behavior and currently reaches `emulateSingleOp()`.
Its actual PatHouse coverage was initially **NOT VERIFIED**.  The completed
measurement below rejects it before optimization work.

## Diagnostic contract

The private macro `BOXEDWINE_WASM_JIT_EMULATE_OPCODE_CENSUS` deliberately
records a precise opcode tag in `CPU::tmpReg` at the same generated location
already used by the profile-only emulate path, immediately before `fn_8`.
The helper takes a mutex, increments exactly one `InstructionCount` bucket (or
the invalid bucket), and increments total.  Snapshot copy uses the same mutex,
so the page must reject unless:

```
total == invalid + sum(opcode[0..InstructionCount))
```

The runtime exposes version, opcode count, snapshot byte count, and copy APIs.
The page requires URL `emulateOpcodeCensus=1` iff runtime ABI version 1 and
checks `snapshotBytes == (opcodeCount + 2) * 8` before guest start.

## Isolation

- **VERIFIED requirement:** `jitCacheUrl=off`, no record, no replay, no FPS.
- **VERIFIED requirement:** The private diagnostic does not add a helper-table
  entry, but its globals change linear-memory layout.  It must never consume
  the accepted replay cache; 316 directly demonstrated this class of ABI
  mismatch.
- **VERIFIED:** `Build/EOC1` completed at `nice -n 19`, with only existing
  compiler warnings.  Its private artifact has 58 Wasm exports (accepted 54
  plus exactly the four census APIs), and JS glue binds all four APIs.  Private
  JS SHA-256 is `EBA4C5250C99F578224B27E26C9D7C771743A0440D488ACA28B6C1C5C20F4B4C`;
  Wasm SHA-256 is `92A122880ECE347807E23D129656BF3A7C5CA8AF6DAC0915757FF719C58334D7`.
- **VERIFIED:** A cache-OFF private session (`jitCacheUrl=off`, no record and
  no replay) passed URL/runtime ABI 1, opcode count 1,365 and snapshot layout
  10,936 bytes.  It reached the fully rendered visible 1024x768 PatHouse.
- **VERIFIED:** The final observed async ring report was
  `callbacks=120 first_seq=12241 last_seq=12360 next_seq=12361 gaps=0
  reorders=0 errors=0`; its paired frame report was error-free.  No FPS result
  is claimed because this mutex diagnostic is not a performance artifact.

## Exact dynamic measurement

After the visible PatHouse settled, the page refresh button took an exact S0
and S1 22.337 seconds apart.  The mutex snapshot invariant held at both reads
and for their delta.

| Item | Exact delta | Share of `fn_8` delta |
| --- | ---: | ---: |
| `fn_8` total | 6,965,027 | 100% |
| invalid tag | 0 | 0% |
| `Movsd` (index 402) | 2,337,560 | 33.56% |
| `Movsb` (400) | 958,656 | 13.76% |
| `Int9A` (376) | 786,355 | 11.29% |
| `FISTP_QWORD_INTEGER` (631) | 783,192 | 11.24% |
| `Bswap32` (795) | 508 | 0.00729% |

There were 26 nonzero opcode buckets; the four rows above account for 69.859%
of the exact delta.  `BSWAP` is only about 22.74 entries/s in this scene, so
its narrow semantics do not justify an optimization candidate.  The leading
`Movsd`/`Movsb`/interrupt/FPU entries are not assumed equivalent: each has
string, privileged/interrupt, or FPU semantics and needs a separate static
contract before any candidate can open.

## Next gate

`BSWAP` is closed.  The only potential next investigation is a new separate
static/dynamic pair for `Movsd`; it must first prove which string forms and
REP/DF/segment/page-crossing paths make up its 33.56% helper share.  Do not
reuse this artifact for replay, cache generation, or FPS.
