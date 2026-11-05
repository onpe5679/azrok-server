# 188 Gate 2c Wasm unaligned-access reproduction

Date: 2026-07-20

## Scope

This document corrects the prior browser-input-build conclusion before any
further mouse or 3D rendering claims are made. It is a single startup/PatHouse
gate only; it does not expand content QA.

## Dynamic result — VERIFIED

Three independent browser launch selections all reached Acknex/Wine startup
and then failed about fifteen seconds later with the same worker exception:

```text
RuntimeError: operation does not support unaligned accesses
wasm-function[8812] -> [4165] -> [4168] -> [7466] -> [7442]
```

The affected selections were:

| selected asset | result |
|---|---|
| `boxedwine.inputtrace` rebuilt after removing the synchronous DOM query | same exception |
| `boxedwine.wsmulti` rebuilt with the same change | same exception |
| pre-existing `boxedwine.profile` | same exception |

The pre-existing profile reproduction is decisive: the error is not caused by
the new `MAIN_THREAD_EM_ASM_INT` removal, the fixed 640x480-to-1024x768 input
mapping, or the WebGL cull mapping. Those hypotheses are **DISPROVED** as the
cause of this startup failure.

`__syscall_socketpair` is also reported as unsupported earlier in the run, but
the causal relationship to the later alignment exception is **NOT VERIFIED**.

## Static boundary — VERIFIED

The rebuilt Wasm was disassembled with the local Binaryen `wasm-dis` tool.
Function 8812 itself is a small non-atomic object-construction routine; it
contains ordinary loads/stores and calls allocator helper 8741. It does not
by itself identify the faulting unaligned atomic/futex access. Therefore a
source-mapped/assertion-enabled Emscripten build is required before editing
the WSA/socket or scheduler paths.

The active Ghidra MCP bridge was queried and reported no connected instance,
so no Ghidra result is asserted for this finding.

## Consequences

- The cursor-source finding from 187 remains a static coordinate observation,
  but its rebuilt-runtime success claim is withdrawn.
- The D3D9 CW/CCW conversion remains a **VERIFIED code correction** only.
  PatHouse visual face-orientation confirmation is blocked by this earlier
  Wasm failure.
- Do not use the input-fix Wasm pair as a success baseline yet.

## Next direct measurement

Build one source-mapped/assertion-enabled copy of the same 1 GiB
multi-threaded configuration and reproduce this one startup failure. Use the
reported source location to choose the next minimal repair; do not infer that
the WSA event path is the cause merely from the nearby unsupported-syscall
warning.
