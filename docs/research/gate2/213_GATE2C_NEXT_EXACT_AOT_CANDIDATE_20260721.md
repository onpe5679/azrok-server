# 213 Gate 2c next exact AOT candidate after the missed AA80 entry

Date: 2026-07-21

## Scope

This is a static selection pass over document 201's already accepted
`sample_us=863111`, `dropped=0` PatHouse window. It does not start another
game, collect a new broad profile, edit production code, or build BoxedWine.
The exact `acknex.dll` SHA-256 remains
`876f6870f6858c3829c0830415bf30cf7dd375590810eef231a7e6b1a68eedc6`.
Ghidra was rerun on that binary to verify the candidates' function bodies,
CFGs, and instruction contracts.

## VERIFIED -- the 4A6D0 aggregate does not justify another entry guess

Document 201's `FUN_1004a6d0` total of 51,252 sampled us is exactly the sum
of six 16-byte buckets inside the later AA region:

| Bucket RVA | Sampled us |
|---|---:|
| `0x4AAE0` | 11,509 |
| `0x4AA80` | 9,521 |
| `0x4AB50` | 8,483 |
| `0x4ABB0` | 8,006 |
| `0x4AB30` | 7,771 |
| `0x4AA70` | 5,962 |
| **Sum** | **51,252** |

There is no top-32 bucket at the function entry `0x4A6D0`, the six-float x87
lerp/store loop `0x4A836..0x4A8C1`, or the six-dword copy loop
`0x4A8D0..0x4A905`. The prior function aggregate therefore gives those two
front loops no direct measured support. Document 212 then proved that the
exact `0x4AA80` entry itself is not reached by the fixed current scene.

Whole-function replacement is also a poor recovery attempt. Ghidra verifies
396 instructions, 109 x87 instructions, multiple global writes, vertex-buffer
Lock/Unlock through indirect COM calls, nine call instructions total, and
data-dependent loops. It would enlarge the state/fault/rendering contract without a measured
remaining entry. The old 5.94% figure must not be reused as its post-212 AOT
ceiling.

## VERIFIED -- remaining measured families

The independent transform chain remains larger than the indexed-submission
function after removing all 4A6D0 buckets:

| Candidate | Mapped sampled us | Guest sampled share | Acknex share | Static obstacle |
|---|---:|---:|---:|---|
| `FUN_10049630` + `FUN_10046760` | 50,442 | 5.844% | 9.628% | outer-loop call plus two imported transform thunks |
| `FUN_10046760` alone | 37,623 | 4.359% | 7.181% | two imported transform thunks and a store-heavy copy fallback |
| `FUN_1008df5d` | 35,497 | 4.113% | 6.775% | six indirect D3D calls and a guest-write run counter |

`FUN_1008df5d` is 388 bytes / 129 instructions / 23 basic blocks. Its three
mapped buckets (`0x8E050`, `0x8E060`, `0x8E0A0`) are the material-ID scan that
groups runs before `DrawIndexedPrimitive`. A whole-function AOT would have to
preserve SetVertexDeclaration, SetStreamSource, SetIndices and draw calls at
their exact positions. A call-free same-material superblock is plausible, but
it writes and increments `[EBP+8]`; document 206's current WASM memory tier is
read-only. It is therefore the next target after a precise guest-store tier,
not the lowest-risk target now.

Ghidra verifies `FUN_10046760` as 111 bytes / 47 instructions. It either calls
two imported position/normal transform thunks or copies six dwords. Its
largest bucket is `0x46780` at 17,765 sampled us (2.058% of all guest sampled
time, 3.391% of Acknex), larger than any other remaining single Acknex bucket
in the accepted window.

## VERIFIED -- selected first gate: `0x10046780..0x1004678C`

The next exact-entry probe and, only if nonzero, next AOT/JIT target is the
12-byte decision trace beginning at original VA `0x10046780`:

```asm
10046780  JL   100467AA
10046782  TEST ECX,ECX
10046784  JZ   100467AA
10046786  CMP  dword ptr [ECX+4],3
1004678A  JNZ  100467AA
            ; otherwise fall through to 1004678C
```

Byte SHA-256:
`545cc01e90d77ccc2845d96f804873064f0cf7e39e67e9667c25c6363fe5f05e`.

This trace has five instructions, two direct successors, one conditional
32-bit guest read, no guest write, no stack change, no call, no x87, and no
SSE. It consumes the incoming lazy signed result of `TEST EAX,EAX`. A taken
first branch must preserve that incoming lazy tuple; the second branch leaves
the `TEST ECX` tuple; the final branch/fallthrough leaves the `CMP32` tuple.
The only possible memory fault is the final `[ECX+4]` read and occurs only if
both earlier branches fall through.

That contract fits the already verified direct-branch semantics in document
207 and the read-only soft-MMU preflight in document 206. Failed page
validation must fall back at `0x10046780` before committing state, so the
interpreter reproduces the exact earlier TEST and fault ordering. Successful
execution commits only lazy flags and selected EIP (`0x100467AA` or
`0x1004678C`). It does not cross a D3D or imported transform call, so its
render-state risk is materially lower than either whole function.

## Ceiling and decision

- **VERIFIED measurement ceiling:** the supporting 16-byte bucket is 17,765
  us, or 2.058% of the accepted guest sample and 3.391% of Acknex. This is a
  bucket ceiling, not time proven to start exactly at `0x10046780`.
- **INFERRED ideal frame ceiling:** if that entire share transferred directly
  to frame time and the trace became free, speed would rise by only 2.10%
  (`1/(1-0.02058)`). At the current 33--34 FPS release band this is roughly
  +0.69--0.71 FPS. Actual gain must be smaller.
- **DECISION:** add one bounded relocation-aware exact-entry counter for
  `0x10046780`; do not build an AOT on the bucket alone. If the counter is
  nonzero, this five-instruction branch/read trace is the first implementation
  target. If zero, reject it exactly as document 212 rejected AA80, then test
  the independently measured `0x1008E05E` scan entry rather than guessing a
  4A6D0 front-loop entry.

No single candidate closes the 33--34 to 65 FPS gap. The value of this target
is that it is an exact, reusable branch-plus-read integration gate with a
measured ceiling and no rendering-call surface.

## Artifacts

- (로그 원본은 공개본에서 뺐다) — acknex_transform_chain_ghidra_20260721
- (로그 원본은 공개본에서 뺐다) — acknex_transform_helpers_ghidra_20260721
- (로그 원본은 공개본에서 뺐다) — acknex_next_aot_candidates_ghidra_20260721
- `tools/ghidra/ExportFunctionContract.java`

## NOT VERIFIED

- The exact relocated `0x10046780` entry count in the current fixed PatHouse
  scene is not yet measured; the old profiler key is only 16-byte granular.
- No AOT/JIT implementation, native differential oracle, browser A/B, visual
  result, or FPS gain is claimed here.
