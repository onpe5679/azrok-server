# 218 Gate 2c relocation-aware multi-entry probe set

Date: 2026-07-21

## Scope

This is a static successor-selection pass for the case where the current
browser measurement finds zero entries at `acknex.dll+0x46780`. It reuses the
accepted document 201 PatHouse window (`sample_us=863111`, `dropped=0`) and the
exact Ghidra contracts already exported for the same acknex.dll SHA-256:

`876f6870f6858c3829c0830415bf30cf7dd375590810eef231a7e6b1a68eedc6`

It does not start another game, alter production dispatch, or claim that a
16-byte profiler bucket proves an exact entry. The purpose is to put several
cheap exact-entry questions into the next probe-only browser session instead
of spending one session per guess.

## VERIFIED -- five exact EIPs are sufficient for the next split

| Priority | Exact original VA | Static role | Side-effect surface if later compiled | Measurement ceiling |
|---:|---:|---|---|---:|
| 1 | `0x1008E0A0` | material-scan loop latch | `INC EDI`, one conditional 32-bit read at `[ESI+0x264]`, `CMP`, branch; no guest write/call/x87/SSE | at most the 8DF5D family's 35,497 us / 4.113% guest |
| 2 | `0x1008E05E` | material-ID scan body entry | two object/array reads plus a stack-argument compare before a split; the equal successor increments `[EBP+8]`, and a later mismatch successor can reach an indirect D3D draw | at most the same 35,497 us / 4.113% family |
| 3 | `0x100467AA` | six-dword transform fallback copy | six ordered data reads and six guest writes; trailing POP/RET also reads the guest stack and selects an indirect return if included; no call/x87/SSE | at most the 19,858 us / 2.301% residual of `FUN_10046760` after its 17,765-us `0x46780` bucket |
| 4 | `0x10046760` | exact transform-or-copy function entry | global/object reads, then either two imported transform calls or the copy fallback | 37,623 us / 4.359% mapped function ceiling |
| 5 | `0x10049650` | outer object loop header | direct call to `0x10046760`, three register increments, global count read, loop branch | 12,819 us / 1.485% mapped outer-function ceiling |

The ceilings above are deliberately conservative family ceilings. They are
not assigned to an exact instruction unless a counter proves that entry is
live. In particular, documents 201 and 213 preserve only the 35,497-us sum of
the three mapped 8DF5D buckets (`0x8E050`, `0x8E060`, `0x8E0A0`), not their
individual values. The exact `0x8E0A0` share is therefore **NOT VERIFIED** and
must not be reported as 4.113%.

`0x1008E0A0` is the lowest-risk new implementation candidate. Ghidra verifies:

```asm
1008E0A0  INC EDI
1008E0A1  CMP EDI,dword ptr [ESI+264h]
1008E0A7  JC  1008E05E
           ; otherwise 1008E0A9
```

It fits the existing read-only soft-MMU and direct-branch tiers. A successful
helper would commit EDI, the exact `CMP32` lazy tuple, and one of two EIPs. A
failed read preflight must side-exit before changing EDI or flags. Unlike the
`0x8E05E` body, this latch has no guest store and does not cross the indirect
draw call.

`0x100467AA` is the best write-tier candidate if the transform function is
entered while `0x46780` remains zero. The exact block is a straight ordered
copy from `[ESI+0..0x14]` to `[EDI+0..0x14]`. Three pops and `RET` follow, so a
first write-tier helper can stop before `0x467CC` rather than absorb an
indirect-return contract. Its entry count, together with the `0x46760`
function-entry count, separates the
fallback-copy path from the transform-call path without inferring either from
the old bucket.

`0x10049650` is diagnostic rather than a first whole-trace replacement. Its
counter gives the outer-loop trip count and its ratio to `0x46760` checks that
the expected one transform-or-copy call per object iteration is actually
dispatcher-visible. Compiling across the direct call is not approved by this
document.

## VERIFIED -- one-session relocation-aware probe is behavior-neutral

The current probe already resolves targets using the runtime module pair:

```text
runtime_target = current_address - process.getModuleEip(current_address) + RVA
```

and only after `getModuleName(address).endsWith("acknex.dll", true)`. The next
probe can reuse that single resolved module base for an array of the five RVAs
above. Each comparison only increments a probe-local `thread_local` counter;
it must always continue into the existing interpreter/AOT dispatcher and must
never return `true` merely because a counter matched.

For observability without log flooding:

1. publish a mandatory zero marker for all five RVAs after resolution;
2. publish hits only at count 1 and powers of two;
3. include RVA, relocated address, and count in each worker message;
4. keep the build probe-only and restore the counter-free release afterward.

The five additional integer comparisons are instrumentation overhead, so this
session is for reachability and relative counts, not FPS. One fully rendered
and visually accepted PatHouse interval is enough to reject zero-count entries
as scene-inapplicable.

## Decision tree

- If `0x8E0A0 > 0`, build its native differential oracle first; it is the only
  new candidate that already fits the read-only/branch production tier.
- If `0x46760 > 0`, `0x46780 = 0`, and `0x467AA > 0`, add the precise
  transactional guest-write tier around the six-dword copy rather than
  guessing another transform path.
- If `0x8E05E > 0` but `0x8E0A0 = 0`, retain the body as a write-tier candidate
  and inspect its actual successor mix before crossing a draw call.
- `0x49650` is used to validate outer-loop coverage and is not compiled across
  its direct call until a resumable call-boundary design exists.
- Entries that remain zero after a screenshot-confirmed steady PatHouse window
  are rejected for this scene even if their old 16-byte buckets were hot.

Even the largest listed family has an idealized speed ceiling of only 1.0429x
(about +1.42 to +1.46 FPS from a 33--34 FPS baseline). These probes select
reusable block-JIT tier work; no one result can close the 65 FPS gap.

## Evidence

- `docs/research/201_GATE2C_POST_DRAWUP_FUNCTION_STATE_AND_HOST_LIFETIME_20260721.md`
- `docs/research/213_GATE2C_NEXT_EXACT_AOT_CANDIDATE_20260721.md`
- `docs/research/216_GATE2C_46780_BRANCH_READ_NATIVE_DIFFERENTIAL_FIXTURE_20260721.md`
- (로그 원본은 공개본에서 뺐다) — acknex_transform_chain_ghidra_20260721
- (로그 원본은 공개본에서 뺐다) — acknex_next_aot_candidates_ghidra_20260721

## NOT VERIFIED

- Exact browser entry counts for all five RVAs.
- Individual sampled-us values of the `0x8E050`, `0x8E060`, and `0x8E0A0`
  buckets; only their accepted mapped-function sum is retained.
- Any production implementation, browser rendering/FPS improvement, or 65 FPS
  implication.
