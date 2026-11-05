# 291. Gate 6 pair replay pending-group ownership

## VERIFIED static/offline/browser; replay ownership repair complete

Fresh v3 replay stages all 147 groups but does not reach pair registration or
WS startup. This is a deterministic ownership bug, not a slow cache load.
The page chains the shell's `onRuntimeInitialized` handler before its own pair
registration handler. The shell consumes `Module.wasmJitMtPendingGroups` first
and clears it; the page then iterates `null`, throws before `main()`, and no
bridge connection can begin.

The shell generic loop also treats the page's staged rows as legacy because
they lack `registerThreadPair`, so merely avoiding the null iteration would
allow one-slot publication of a typed cache. The repair must give v3 page
staged groups explicit pair ownership, make the shell skip only those
page-owned rows, and let the page be their sole pair registrar. Legacy and all
other pending groups retain existing shell ownership.

## Repair and direct replay proof: VERIFIED

Page staged groups now carry explicit `pageOwnedReplayRegistration` and
`registerThreadPair` metadata. The deployed shell defers only that owned set
from its generic registration loop, rejects mixed ownership, and leaves all
other shell-owned groups unchanged. The page is therefore the sole v3 pair
registrar. The page verifier passes five ABI cases plus three ownership cases;
both source and deployed shells pass syntax checking and remain hash-equal.

One fresh cache-off record supplied the sole pipeline input: 34,322 blocks.
The v3 output is 5,747,568 bytes (SHA-256
`fd841501133d407edf8d29a4431e63ed277b6bf38b9dbd2d4f8c2b08c969dd4c`), with
147 groups, 34,322 typed entries, 24,304 patches, tokenWords=2, and no missing
typed exports. Its input record lacked the pfn publication offset, so the
pipeline was explicitly given `--mt-pfn-jit-code-offset 12`; the deployed tail
Wasm getter, source layout, and v3 output contract all directly agree on 12.

The visible single-tab replay then set
`data-jit-replay=registered`, `data-jit-replay-pair=registered`, and exact
147/34,322/24,304 group/entry/patch counts before rendering the normal local
PatHouse 3D room with character, carpet, furniture, and Korean HUD. This is a
replay correctness proof only. It is not a 30-second A-B-A performance sample.
