# 371 -- Current-corpus parity private build and fresh raw record (2026-07-25)

Status: **VERIFIED build/static/browser record; grouped replay and FPS verdict pending**

## Private runtime identity

- **VERIFIED (build):** `azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeParityCurrent` is an isolated `Build/ParityCurrent1`, `-O3`, SIMD/pthread production target with only `BOXEDWINE_WASM_JIT_INLINE_PARITY` beyond the accepted ABI2 production flags. Its final JS/Wasm are 327,046/3,049,219 bytes with SHA-256 `29BD177C776B79B77AFB7E7E917B4BF08662127D66C9F67BEA05AED01B04D1C3` / `66CC9CC9FF83C09F03CD8F10556073819284064938D4CE83C349047BA19B0F6B`.
- **VERIFIED (static/build):** Initial build exposed a fail-closed P0: a compile-time parity macro alone had no loader-observable identity. `wasm_jit_get_inline_parity_abi_version()` was added and exported only by this private target; source returns 1 only under `BOXEDWINE_WASM_JIT_INLINE_PARITY`. The rebuilt glue binds the export as `Module._wasm_jit_get_inline_parity_abi_version`.
- **VERIFIED (static):** The grouped-cache pipeline now accepts a mutually exclusive `--parity-current-runtime-stem` plus exact `--parity-current-raw-manifest-sha256`, and emits `runtimeIdentity={kind:'azrok-parity-current1-v1', runtimeStem, rawManifestSha256, requiredInlineParityAbiVersion:1}`. The page requires exact private stem/URL/mode, identity, raw/grouped/archive pins and live witness before registration. Pins deliberately remain null until the transform output is independently hashed; this makes replay fail closed during construction.

## Fresh record (not a timing sample)

- **VERIFIED (browser/CDP):** The one permitted Edge page was navigated to the private cache-OFF record URL. It was `document.visibilityState=visible`, CSS canvas `1024x768`, private witness=1, record active, and direct Present advanced. Normal `(100,500,140)` and `(90,722,140)` input pulses reached PatHouse; calling the established record-export preparation produced 34,190 cache/meta rows before final save.
- **VERIFIED (browser/file):** Final save uploaded 35,492 v5 blocks / 46,164,910 archive bytes. It was immediately preserved as `tools/boxedwine_local/profiles/azrok-jit-record-paritycurrent1-20260725-144826.zip`, SHA-256 `A98BC3F6C14AB69868D236E17B3BA5580222191828551D00D8C1EAB448990A69`; the generic upload alias was restored to the R2 census source SHA `6BD19F44148B8BE19BA51F6C6AB4CDAB011FF02350A41F478F3221729F304AFF`.
- **VERIFIED (live ABI):** The parity module reported `next=740`, `depth=1660`, `bailout=132`, `pfn=12`, `relocMapBase=12968408`, `capacity=262144`, and inline-fetch ABI 2 with offsets `728:72:36:112:48:1632:652`, matching the live current-ABI control contract.
- **VERIFIED (pipeline fail-closed):** First transform attempt correctly rejected the *archive* SHA used as the raw-manifest pin. The pipeline reported the actual raw-manifest SHA `f05ae717db34e948c201c427ada95e9700a41bfa5c9763c9599798bfea694e87`; no output archive was produced. The exact-pin rerun produced 113 groups / 35,492 entries / 29,181 patches, archive SHA `D69C7358636408FA3787EF37D6E1B0EA5F3EAEB567B744AEFFBA11D0A1A70C4A`, and grouped-manifest SHA `F7FDBEDD0D1DA51C62875A99691C53D671C180754C61E6D8EC0073331EDC92DC`. The page pins all three values; browser replay/render remains pending.

No cache replay/render or FPS sample is claimed in this document. Runtime-lazy Z/NZ remains excluded until this candidate is decided.
