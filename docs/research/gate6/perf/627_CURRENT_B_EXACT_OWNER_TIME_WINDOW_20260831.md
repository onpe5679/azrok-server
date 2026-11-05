# 627 — Current-B exact owner time window rejects transform/dispatcher and isolates blocked read

Date: 2026-08-31 KST

## Conclusion

- **VERIFIED actual PatHouse / exact owner-thread selection:** a diagnostic
  sibling of the deployed current-B runtime/cache stamped the exact
  `KThread::currentThread()->cpu` owner into the same browser trace.  The one
  `AZROK_OWNER_CPU=23e94750` timestamp at renderer `pid=74668/tid=44904`
  joins to the unique same-pid/tid `Profile id=0x7`; its 812 chunks carry the
  same explicit profile ID on Chromium's delivery `tid=101604`.  There is no
  histogram-similarity selection and `dataLossOccurred=false`.
- **VERIFIED 30.027896-second owner window:** the profile contains 48,455
  samples.  The generated libc `__read` entry
  `v5-1054d1b5-96376265` owns `6,385,636 us = 21.265679%` of full owner wall.
  Perfect removal is an upper-bound `+27.0094%` throughput; removing
  `47.0241%` of this wait would be sufficient for a 10% frame-time reduction.
- **VERIFIED / REJECTED as revolutionary surfaces:** all fourteen sampled
  blocks covering Acknex `+49650`, `+46760`, both thunks and both complete
  transform kernels total only `731,970 us = 2.437633%` of full owner wall.
  Perfect elimination is only `+2.4985%`; ideal four/eight-worker execution is
  only `+1.8623% / +2.1794%` before rendezvous overhead.  The proposed
  generated-Wasm transform-loop parallel split cannot reach the 10% gate.
- **VERIFIED / REJECTED as a new revolutionary dispatcher pass:** exact live
  runtime-body/source witnesses identify `wasm-function[6420]` as
  `wasmStartJITOp` and `[6493]` as `NormalCPU::run`.  Their mutually exclusive
  leaves total `754,673 us = 2.513240%` of full wall (`3.192051%` of active
  time), so even perfect elimination is only `+2.5780%`.  The old #618
  28.4968% Touch2 result must not be transferred to expanded-AOT current B.
- **NOT VERIFIED TLB/soft-MMU share:** accepted grouped entries account for
  `15,647,010 us = 52.108246%` of full wall, but V8 exposes the generated
  function boundary rather than sub-entry instruction PCs.  Static emitted
  TLB/page-mask counts remain structural counts, not elapsed time.  The whole
  mapped-generated number is only a broad upper bound and cannot admit a
  mapping-epoch/span-cache implementation by itself.
- **NOT VERIFIED blocked-read removability:** the exact time surface clears
  the 10% Amdahl admission threshold, but this trace alone does not identify
  fd/object type, Wine request ID, deliberate wait semantics or dependency.
  Production-shaped read-source/Wine-request attribution must determine how
  much of the 21.27% is actually removable before implementing an in-process
  wineserver/shared-ring fast path.
- **VERIFIED deployment boundary:** all owner/stamp assets are explicit
  diagnostics.  Production runtime/cache and remote deployment remain
  unchanged.

## Actual PatHouse semantic witness

The fresh `cdp9459` run used the production scene account and the isolated
owner-thread runtime/cache.  Input ownership was single-writer: the root agent
performed the existing-character slot/connect action once; the profiler agent
performed no input.

Both independently captured screenshots visibly contain the PatHouse room,
floor/rug, furniture, pink Azron, HUD and quest text:

```text
before trace
  artifacts/performance/ownerthread_rearm_launch3_pathouse_gate_20260831.png
  SHA-256 d7b5eb080d94bb25f28867800c7927f57c3f083132bffcf9b090e76cd99c977a

after trace
  artifacts/performance/ownerthread4_rearm_cdp9459_pathouse_after.png
  SHA-256 f95d4bed3a63980b9cf5db94de3c9e134f282d2b33751fa975c5d70dd5c9b269
```

The screenshots are semantic witnesses, not FPS comparison legs.

## Exact owner/profile join

### Diagnostic ABI

The source-gated runtime exposes:

```text
_wasm_jit_get_owner_thread_identity_abi_version
_wasm_jit_get_owner_thread_identity_owner_word_address
_wasm_jit_get_owner_thread_identity_stamp_word_address
_wasm_jit_get_owner_thread_identity_owner_cpu
_wasm_jit_reset_owner_thread_identity_owner_cpu
_wasm_jit_rearm_owner_thread_identity_stamp
_wasm_jit_get_current_thread_cpu
```

The final re-arm contract does **not** use a one-shot thread-local boolean.
Reserve word 60 captures the owner CPU.  Main-realm reset stores zero to word
61; the matching owner Worker performs `CAS(word61, 0, cpu)` and emits one
`console.timeStamp` only on success.  This lets every stable-scene trace re-arm
the stamp without trying to mutate another Worker's TLS.

Pinned identity:

```text
runtime stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1ownerthread1
runtime JS    4a978761088208607c8de582d747371b9e9e35b91ff3cffaa6fa2123742c671d
runtime Wasm  a6195f02578c3d92f9f430feba75b9a11d1a969740c825c14a701219ff8f09a8
reloc map     12968584 / 262144
owner word    60 / address 12968568
stamp word    61 / address 12968572

cache         azrok-jit-grouped-multidirectloops1-ownerthread4-currentabi1-20260831.zip
cache SHA     bc319971030aa26abc1764ca122f364f02e1c6fe1c2e65327ce12d897a9422b1
manifest SHA  7f2460f76af528ea454f8af851f5706d156ec3506709e55b4911a3cd6b762fc0
groups/keys   143 / 44,395
changed       group-0010, anchor entry index 136, +27 bytes; other 142 groups byte-identical
```

### Same-trace chain

Trace start was `2026-08-31T12:26:06.752Z`.  At
`2026-08-31T12:26:09.698Z`, page read/re-arm/read returned the same nonzero
owner `602490704 = 0x23e94750`.

```text
TimeStamp      pid 74668 / tid 44904 / owner 0x23e94750
Profile header pid 74668 / tid 44904 / id 0x7
ProfileChunk   pid 74668 / delivery tid 101604 / id 0x7
chunks         812
samples        48,455
sampled wall   30,027,896 us
data loss      false
```

Chromium writes the `Profile` header on the sampled Worker but may flush
`ProfileChunk` on a trace-delivery thread.  Therefore the authoritative join
is:

```text
TimeStamp(pid,tid)
  -> unique Profile(same pid,tid).id
  -> all ProfileChunk(same pid, profile id)
```

Requiring the chunk TID itself to equal the Worker TID was an extractor bug;
it was corrected.  Selecting a similar-looking histogram is neither needed nor
permitted.  The primary analyzer now reports
`same-trace-owner-stamp-profile-id-v1`; its old `unanchored` warning is not
applied to this preselected one-profile input.

## Owner time accounting

Exclusive leaf classes sum to the complete sampled wall:

| Exclusive leaf class | Time | Full owner wall |
|---|---:|---:|
| dynamic generated Wasm | 18,922,343 us | 63.015880% |
| BoxedWine runtime Wasm | 11,018,480 us | 36.694146% |
| other | 87,073 us | 0.289974% |
| total | 30,027,896 us | 100% |

Nearest-dynamic-ancestor attribution is a separate, non-additive view:

| Attribution | Time | Full wall | Active wall |
|---|---:|---:|---:|
| libc `__read` blocked interval | 6,385,636 us | 21.265679% | excluded |
| selected active interval | 23,642,260 us | 78.734321% | 100% |
| accepted grouped-entry compute | 15,647,010 us | 52.108246% | 66.182379% |
| unresolved dynamic leaf | 6,694,357 us | 22.293793% | 28.315216% |

V8 `timeDeltas` are sampled wall-clock intervals.  They are not retired
instructions or direct CPU-utilization counters.

## Acknex transform Amdahl gate

The primary analyzer attributes every sample to the nearest uniquely mapped
dynamic grouped-Wasm ancestor, so the entry rows below are mutually exclusive.

| Region | Included basic blocks | Time | Full wall |
|---|---|---:|---:|
| outer loop | `+49650/+49659/+4966D` | 45,125 us | 0.150277% |
| transform dispatch | `+46760/+46798/+467A6` | 115,129 us | 0.383407% |
| two indirect thunks | `+84364/+84477` | 21,758 us | 0.072459% |
| 3x3 transform kernel | `+1041D7/+104233/+104283` | 225,439 us | 0.750765% |
| coordinate transform kernel | `+1042A3/+1042FD/+104352` | 324,519 us | 1.080725% |
| **complete sampled transform surface** | 14 blocks | **731,970 us** | **2.437633%** |

Bounds:

```text
perfect elimination   +2.498539%
ideal 4-Worker split  +1.862272%  (10% gate requires 13.3333% wall)
ideal 8-Worker split  +2.179415%  (10% gate requires 11.4286% wall)
```

This rejects transform-loop parallelization as the requested revolutionary
candidate even before synchronization, alias checks, fault ordering and
deterministic commit costs.  It also explains why the implemented fusion/HLE
variants in #623-#626 could not become a credible 10% current-B win.

## Dispatcher boundary changed after expanded AOT

The runtime symbol-map shortcut was tested and rejected.  Relinking the exact
owner basename/objects with only `--emit-symbol-map` produced Wasm SHA
`12ca4a80523a0bed92daf5808b7b4884a97f5a0a8abab9ecc1eafb0c60364257`,
not live SHA `a6195f...`.  The generated map therefore cannot name live
indices, including the two dominant blocked-read leaf indices `[873]` and
`[697]`.

The accepted dispatcher identities instead pin the live `a6195f...` bytes and
independently require exact source/body witnesses:

| Live index | Verified source identity | Exclusive leaf | Full wall | Active |
|---:|---|---:|---:|---:|
| 6420 | `wasmStartJITOp(CPU*, DecodedOp*)` | 579,759 us | 1.930735% | 2.452215% |
| 6493 | `NormalCPU::run()` | 174,914 us | 0.582505% | 0.739836% |
| total | dispatcher boundary | 754,673 us | 2.513240% | 3.192051% |

Witnesses include `DecodedOp::flags2 +28`, atomic `pfnJitCode +12`, owner
hazard and generated `call_indirect` for `[6420]`; and `CPU::thread +728`,
`nextOp +740`, CS base `+48`, EIP `+112`, big mode `+1632` and the next-op
indirect call for `[6493]`.

#618's Touch2 `28.4968% active / +39.8540% ideal` was valid for that older
runtime/corpus/window.  Expanded current-scene AOT and multi-direct execution
have reduced the exclusive dispatcher surface to 3.1921% active here.  It is
invalid to keep using the older percentage as the current next-step budget.

## Blocked read is the only measured 10%+ surface

The exact generated key `v5-1054d1b5-96376265` is the directly verified guest
libc `__read` cancellation entry.  Its nearest-parent decomposition is:

```text
blocked interval                    6,385,636 us / 21.265679% wall
next mapped guest caller            none
immediate frame above read          runtime [6420] / 100%
dominant runtime leaf [873]         3,237,676 us / 10.782227% wall
dominant runtime leaf [697]         3,082,584 us / 10.265734% wall
```

The stack returns through `[6420] -> [6493] -> js-to-wasm`; no second mapped
guest caller survives the dispatcher boundary.  The two runtime leaves remain
numeric identities because the mismatched symbol map is rejected.

**INFERRED candidate:** if exact fd/object/request attribution shows that at
least 47.0241% of this wait is avoidable browser-local wineserver IPC, an
in-process shared request/reply ring with socket fallback has enough Amdahl
surface for the 10% frame-time target and can generalize across Wine guests.

**NOT VERIFIED:** waiting is not the same as wasted time.  Deliberate
synchronization, server dependency, network arrival and required ordering are
not removable.  No wake-policy, read bypass or in-process wineserver change is
admitted until the production-shaped read profiler reports exact fd,
`KObject::type`, `selfFd`, requested length and Wine request ID distributions.

## TLB/soft-MMU boundary

The independent current-B census/static audit remains useful structural
evidence:

```text
top-1000 owner-hit coverage           90.950896%
static TLB lookups/selected entry      7.136038
static page masks/selected entry      14.308944
exact transform kernels                already Wasm SIMD
```

But these are emitted occurrences weighted by entry hits.  They do not prove
that every arm executes, nor assign nanoseconds.  The exact profile can bound
all accepted mapped generated code at 52.108246% wall, but cannot isolate the
TLB/translation subset because V8's dynamic-module column identifies the
function boundary rather than an instruction PC.  Therefore:

- mapping-epoch/span translation remains **NOT VERIFIED**, not promoted;
- the 52.108246% whole-generated number must not be called TLB time;
- a future candidate requires an instruction-local timer/counter or an actual
  fail-closed A/B whose only changed work is translation/guard handling.

## Production and cleanup boundary

- Production current-B runtime/cache and routing were not changed.
- Owner identity uses a separately named runtime/cache and explicit URL flag.
- Direct-fusion3/4/5 remain rejected; this owner loader is independent of
  their page block so fusion cleanup cannot remove the profiler contract.
- The mismatched symbol relink is retained only under
  `artifacts/performance/rejected_ownerthread_symbol_relink_20260831/` and is
  not a runtime candidate.

## Artifacts and reproducibility

Primary artifacts:

```text
raw all-thread trace
  artifacts/performance/ownerthread4_rearm_cdp9459_currentb_trace_20260831.json
  SHA 5740914acfd9876e395638bdf258e0178ddaf4f88b65850e9fcb7cf0399cf58f

exact owner join
  artifacts/performance/ownerthread4_rearm_cdp9459_owner_join_20260831.json
  SHA af578d5fe8732f8abb52e01d49f4164304cd4b3ea6c8bacd7b0fa037e1766790

filtered owner profile
  artifacts/performance/ownerthread4_rearm_cdp9459_owner_filtered_trace_20260831.json
  SHA 85cd0eae15b7fe8c98ca1d7979eaeb2ed03972255714bf9bb404a3934fcf660e

grouped-entry summary
  artifacts/performance/ownerthread4_rearm_cdp9459_owner_summary_20260831.json
  SHA c96f24993aa5213e266d02f31ca2ae22df399ef890a5f5fa9eb4fb29fd84574b

blocked-read stacks
  artifacts/performance/ownerthread4_rearm_cdp9459_blocked_read_stacks_20260831.json

transform/TLB bound
  artifacts/performance/ownerthread4_rearm_cdp9459_transform_tlb_bound_20260831.json

dispatcher witnesses
  artifacts/performance/ownerthread4_runtime_dispatch_hot_functions_20260831.json
```

Tools/contracts:

- `tools/browser_diagnostics/Collect-AzrokBrowserTrace.mjs`
- `tools/browser_diagnostics/extract_azrok_stamped_owner_profile.py`
- `tools/browser_diagnostics/analyze_azrok_browser_trace.py`
- `tools/browser_diagnostics/analyze_azrok_owner_blocked_read.py`
- `tools/browser_diagnostics/analyze_azrok_owner_transform_surface.py`
- `tools/browser_diagnostics/verify-ownerthread4-runtime-dispatch.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-owner-thread-identity-source.mjs`

## Decision

1. Keep the deployed current-B runtime/cache unchanged.
2. Close the transform parallel/HLE/fusion and dispatcher-rewrite axes for the
   10% goal on this current window; their perfect bounds are below 3%.
3. Do not promote TLB/span caching from static counts; its exact wall share is
   still unknown.
4. Continue only the blocked-read attribution branch.  Implement a
   generalized in-process wineserver/shared-ring candidate only if exact
   read-source data proves at least 47.0241% of the measured blocked interval
   is causally removable.
