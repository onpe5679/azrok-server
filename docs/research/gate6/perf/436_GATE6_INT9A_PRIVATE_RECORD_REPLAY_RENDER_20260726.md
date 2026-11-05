# 436. INT 0x9A specialized private record, pinned replay, and render

Date: 2026-07-26  
Status: **VERIFIED record/replay render integrity; FPS remains NOT VERIFIED**

## Fresh private record and artifact separation

After the user-owned service loop restarted 8765, the new listener was Python
PID 14340 (started 06:48:59), later than
`tools/boxedwine_local/server.py` (05:48:42) containing the private upload
allowlist.  The pre-record generic raw baseline was:

```text
profiles/azrok-jit-record-raw.zip
37,840,834 bytes
mtime 2026-07-25T15:54:00.9327955Z
SHA-256 3533DFB2B2B6A18F029065E2DCDEC3A14F6C25CCEDCC68208DFD51A64F32F165
```

A watcher-provided fresh primary process ran only the exact private record
route (`runtimeStem=...int9aspecialized1`, `int9aSpecialized=1`,
`jit-record=true`, `jitCacheUrl=off`).  After actual PatHouse entry, the
export preparation table contained 47,756 cache/meta rows; the physical save
button then completed with 48,902 blocks and 62,997,481 bytes.  The private
archive exists at `profiles/azrok-jit-record-int9aspecialized1.zip`, while the
generic raw's byte count, mtime, and full SHA-256 are unchanged.  This directly
proves path separation together with the new handler's private archive output.

The raw archive carries exactly 48,902 wasm entries and a manifest
`privateRecord` of:

```text
kind = int9a-specialized
stem = boxedwine.upstreamjit64fn6inlineabi2int9aspecialized1
abi  = 1
```

Its archive SHA-256 is
`c3cbd6e0470e859f28fc6c6e73076014c953a0316ef419f29653f5523a8252a8`.
The authoritative uncompressed `boxedwine-jit-manifest.json` entry is
23,058,274 bytes with SHA-256
`9edf1c54a92cf945571c6e2cdf04c3971644269e908a2bf67295893bd157b095`.

## Transform contract and pins

The first transform correctly failed closed because the raw manifest does not
carry the MT direct-stitch `nextOp`/`pfnJitCode` witnesses.  The exact live
private runtime directly returned `nextOp=740` and `pfnJitCode=12` (and the
already-recorded depth/bailout 1660/132), so the retained single transform used
only `--mt-next-op-offset 740` and `--mt-pfn-jit-code-offset 12` plus the exact
raw-entry SHA and explicit local `binaryen_js.js` path.  A second accidental
duplicate transform process was stopped before output; only the original
process completed the artifact.  No FPS sample ran while either process used
CPU.

The output has 154 groups, 48,902 entries, 41,721 direct-call-site patches,
and exact runtime identity `azrok-int9a-specialized-v1` with raw identity/ABI1.
Its archive SHA-256 is
`d15212ce3fe3d5cbca2b3717780d1e8efb2d92a47f9b1d8c479554c63abd4f03`; its
uncompressed `boxedwine-jit-grouped-manifest.json` SHA-256 is
`5d0c8502d7d189f38128b97f675d0cc734a704d11dd8eb91f0eb2812e2b2ef17`.

Those three exact lower-case values now pin the INT9A page replay identity.
Node VM mutation tests directly verify raw/archive/grouped-manifest/runtime-ABI
and wrong-stem mismatches reject.  The MRG preflight initially rejected the
recognized INT9A identity as unknown; the minimal allowlist correction defers
only `azrok-int9a-specialized-v1` to its own strict gate, while an arbitrary
unknown identity remains rejected. Page/pipeline syntax and server AST pass.

## Fresh replay render

A second fresh watcher process loaded only the exact private replay URL with
the grouped cache.  Before guest execution it directly reported:

```text
JIT groups registered = 154
JIT blocks registered = 48,902
INT9A helper ABI      = 1
```

After the known common cold bootstrap, direct CDP evidence on the same visible
1024x768 page recorded 5,345 Presents (HUD 5,280), specialized
`direct/fallback/fault=245038/0/0`, and consecutive async windows with
`submitted=120`, `reaped=120`, `inflight=1`, `max_inflight=1`, `ring_full=0`,
`sync_drains=0`, and `errors=0`.

## Decision

Private record and pinned replay render integrity are closed. This establishes
neither GPU completion nor a performance benefit. The next stage is a fresh
primary-display accepted-versus-private 30-second Present A-B-A(B) measurement
under the current working-set, memory, visibility, window-overlap, and
fresh-process hygiene gates.
