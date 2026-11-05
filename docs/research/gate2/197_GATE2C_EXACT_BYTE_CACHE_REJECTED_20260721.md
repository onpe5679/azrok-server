# 197 Gate 2c interpreted exact-byte cache rejection

## Scope

This measurement used the existing single browser tab and the saved-character
automatic PatHouse entry. No native game instance and no gameplay input were
used. The earlier doorway-contaminated windows remain invalid.

## VERIFIED -- clean no-input baseline

Four consecutive 120-Present windows from the corrected `UpdateSurface`
build measured 12.88, 13.24, 12.88, and 13.02 FPS (mean 13.01 FPS). Each
window uploaded about 60.44--60.51 MB in 2161--2162 calls. Guest packet
construction/copy took 2.164--2.218 seconds and host JavaScript took about
0.35--0.39 seconds.

## VERIFIED -- content stability probe

The measurement probe found VB 136 (32,396 bytes) and VB 140 (21,528 bytes)
byte-identical over 16 observed locks. VB 59 (53,924 bytes) and VB 67 (7,280
bytes) repeatedly produced the same observed hashes and were candidates, but
their shorter primary sample is not proof for every frame. VB 79 (49,504
bytes) and VB 121 (108,940 bytes) changed repeatedly and must not be classified
as static from scene or handle identity.

## VERIFIED -- exact-byte suppression result

The guest DLL compared each lock range against a shadow of the last successful
upload and suppressed only byte-identical ranges after an initial full upload.
It did not enable the rejected host VAO/static WebGLBuffer cache. PatHouse
remained visually intact and no D3D9Web exception or bad upload was logged.

Three clean 120-Present windows measured:

| Metric | Correct baseline | Guest exact-byte cache | Change |
|---|---:|---:|---:|
| FPS | 13.01 | 11.03 | -15.2% |
| wall time / 120 frames | 9.225 s | 10.871 s | +17.9% |
| upload calls | 2161.5 | 359.7 | -83.4% |
| upload bytes | 60.48 MB | 34.74 MB | -42.6% |
| guest packet-copy time | 2.191 s | 1.275 s | -41.8% |
| host JavaScript time | about 0.35--0.39 s | 0.392 s | no useful reduction |

VB 59/67/136/140 disappeared from the upload top list, while changing VB 121
and VB 79 continued to upload almost every frame. The suppression therefore
worked as designed, but the interpreted x86 `ByteEqual` scan cost more than it
saved. About 0.916 seconds of packet copy was removed while total wall time
grew by about 1.647 seconds per 120 frames.

## VERIFIED static audit / rejection

- The current proxy's `ByteEqual` and shadow update execute as guest x86.
- The shadow duplicates every retained VB/IB allocation while resource release
  is deferred, increasing long-session memory-growth risk.
- The prototype does not exclude `D3DLOCK_DISCARD` or
  `D3DLOCK_NOOVERWRITE`, contrary to the conservative contract recorded in
  document 192.
- It has no host-resource/context generation, so a future real reset/context
  rebuild could leave a valid guest shadow for a missing host resource.

The guest exact-byte cache is therefore **REJECTED** as a performance path and
must not become the default package.

## Next gate

Keep the corrected `UpdateSurface` build as the visual baseline. If duplicate
upload elimination is pursued, perform equality or dirty-generation handling
inside BoxedWine's compiled WASM bridge so the interpreted guest does not walk
20--100 KB ranges. The native path must preserve draw/upload ordering,
invalidate on create/destroy/reset/context generation, and exclude
`DISCARD`/`NOOVERWRITE` unless their semantics are explicitly implemented.
Measure it against the 13.01 FPS baseline before adoption.
