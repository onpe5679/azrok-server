# 289. Gate 6 threaded typed-body fallthrough repair

## VERIFIED dynamic/static/build/browser; performance gate still incomplete

The first tail-enabled cache-OFF browser candidate reached the real local
PatHouse bootstrap packet sequence, but its runtime-generated Wasm groups
repeatedly failed compilation. The direct worker diagnostic was:

`WebAssembly.Module(): Compiling function #N failed: expected 8 elements on the stack for fallthru, found 0`.

This is not a bridge, protocol, or replay-cache failure. The browser connection
accepted TCP, sent C2S slot-0 `0x0005`, and received the normal
`Data\\Space\\PatHouse` `0x0003` followed by `0x0007`, `0x0005`, `0x000A`, and
`0x000B` bootstrap sequence.

## Root cause: VERIFIED static

`JitWasmCodeGen::commitJIT()` previously ended a normal decoded-block
fallthrough with only `endFunction()`. That is legal for the legacy
`(cpu, reloc) -> void` body. The register-threaded body instead has
`(cpu, reloc, eax..edi) -> (eax..edi)`, and only explicit block-exit paths
pushed its eight result values before `return`. A block whose final decoded op
advanced past `lastOpEip` therefore produced a typed Wasm function whose
fallthrough stack was empty.

The merger is not the source: it copies the typed body and changes the wrapper
internal-call index only.

## Fix: VERIFIED build and runtime regression

`commitJIT()` now turns normal fallthrough into `writeEip(...)` plus
`blockExit()` before `endFunction()`. This preserves legacy semantics by
refreshing `nextOp` and synchronizing architectural state; the typed exit also
returns all eight GP values. An initial tuple-only diagnostic change was
replaced because it would have omitted the EIP/nextOp update.

The candidate target rebuilt successfully and its 3,050,506-byte Wasm passes
`WebAssembly.validate`. Existing loader (9 cases), store-sink, and two-entry
pair fixtures pass.

## Ordinary-fallthrough regression: VERIFIED browser execution

The regression is now an independent `TestMultiThreadedJit` entry (zero-based
index 22), rather than a suffix of the existing runtime-group test whose known
broker snapshot failure can return before the new assertion. It initializes its
own CPU/batching state, emits two one-op ordinary `INC` blocks in the exact
`currentEip > lastOpEip` shape, publishes them as a two-slot typed runtime
group, and executes both through the regular wrapper path.

The visible browser ran only this entry and reported every stage successful:
`bootstrap`, `decoded`, `first-pending`, `pair-publish`, `first-execute`, and
`second-execute`, followed by
`MT WASM typed fallthrough regression runtime-group publish/EIP/nextOp/GP OK`
and `0 tests FAILED in 0s`. The test checks EAX/ECX effects, exact EIP advance,
and the canonical dispatcher result (`nextOp` is a `TestEnd` with length 2).

`nextOp` is intentionally tested by semantics, not object identity. Under
`__TEST`, `DecodedOpCache::add` does not cache `TestEnd`, so the fallthrough
helper's EIP-based decode produces a distinct but semantically correct object
from `first->next`. The temporary pointer-equality failure therefore exposed a
test assumption, not a runtime regression. The validated test Wasm SHA-256 is
`71CDE9981967BE9EAFF26A303041E678A0681277A89F6DBD4EE7FAC181801191`.

## Cache-OFF browser render: VERIFIED

One visible candidate tab with no `jitCacheUrl` reached normal automatic
selection and then rendered the 1024x768 PatHouse scene: wall, carpet, table
and stool geometry, pet character and shadow, and Korean HUD were all visible.
The bridge recorded a contiguous async ring (`gaps=0`, `reorders=0`,
`errors=0`). The console did not contain either the former runtime-install
failure or the eight-result fallthrough compile error. The result is a render
integrity gate only: title/selection-screen Presents and this startup run are
not a 30-second PatHouse performance sample.

## Next gate

The typed normal-fallthrough correctness gate is complete. Before any A-B-A,
produce a fresh dual-entry cache and prove the deployed loader's fail-closed
record/replay registration path. No FPS value is claimed by this document.
