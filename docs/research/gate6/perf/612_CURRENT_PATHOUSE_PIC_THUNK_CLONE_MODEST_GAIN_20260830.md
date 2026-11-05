# 612 — Current PatHouse i386 PIC-thunk clone: modest verified gain

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED structural:** an opt-in grouped-cache transform clones exact
  4-byte i386 PIC thunks into caller groups as internal, non-exported,
  non-registered functions.  The original 94 groups / 30,550 registered
  entries / 28,944 relocation patches remain fixed.
- **VERIFIED current surface:** the six exact BX/DX/AX/DI/SI/CX block hashes
  account for 1,209,674 owner-CPU entries in 20.008940 seconds: 5.9759% of all
  generated entries and 2,568.31/Present.  The selected 11 active libc/ntdll
  instances cover all but two one-hit copies.
- **VERIFIED artifact:** 16 internal functions admit 150 exact local
  `return_call` tails.  88/94 group Wasm files are byte-identical to control;
  all 94 candidate groups validate.  No clone appears in exports,
  `groups[].entries`, loader registration, or relocation-patch targets.
- **VERIFIED visual/runtime:** A-B-A-B-A all show the actual PatHouse room in
  manually reviewed before/after screenshots.  Control mean is 30.0265 FPS,
  candidate mean 31.0054 FPS: **+3.2598%**.  Four adjacent effects have a
  median of **+3.1452%**.
- **ACCEPTED experimental / NOT production:** this is a reproducible modest
  improvement for the pinned Wine 11 root, but not the requested epoch-making
  gain.  The default launcher/cache remains currentabi1 while the next larger
  region candidate is developed.
- **NOT VERIFIED general production safety:** the fast tail checks live pfn,
  bailout, and yield, but does not re-hash guest text at runtime.  Its safety
  currently depends on the explicitly pinned R-X libc/ntdll text remaining
  mapped and immutable for the process lifetime.

## Why this is reusable

The candidate is not tied to an Azrok game function.  It recognizes exact
compiler-generated i386 PIC thunks:

```text
8B 1C 24 C3   mov ebx,[esp]; ret
8B 14 24 C3   mov edx,[esp]; ret
8B 04 24 C3   mov eax,[esp]; ret
8B 3C 24 C3   mov edi,[esp]; ret
8B 34 24 C3   mov esi,[esp]; ret
8B 0C 24 C3   mov ecx,[esp]; ret
```

These occur broadly in 32-bit PIC ELF libraries.  The infrastructure can be
reused for other exact, immutable modules, although this first artifact pins
specific current keys and hashes rather than claiming universal safety.

## Final cache identity

```text
name   azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-picthunkclone11x1.zip
bytes  4806530
SHA256 7309bec3e133d969e906e3a9049177728b306d61087f8ead585456c64aa9af86
groups 94
registered entries 30550
relocation patches 28944
base direct rewrites 9648
```

Input identity:

```text
raw record ZIP SHA256 8bd2d4778dfa1c1165e459667faa5f4eb267b990b13bdb68b6c540ce3c71905e
raw manifest SHA256   176cdd642acc52c501b417dbd44a46bfb71ba704feca2d2e28f529cfe6fa38b0
ntdll.so SHA256       3a03b005d9311f521ee26c49dd395850f9a379ba0d0195559bb383309eec88b7
libc.so.6 SHA256      141319771edb3c2ffbd91d7617dc133bc70eafa3bf718defa60d11ba5a729d7d
```

Feature-off pipeline regeneration is byte-identical to control:

```text
azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip
4804035 bytes
b007fa84ac483360389d136fa45682ef774b8a7b19f8cbf214cef1d4a389035a
```

Both restored local files and live HTTP responses match these exact hashes.

## Transform contract

Every requested target must have one raw-manifest entry with:

```text
key/EIP/hash exact
opCount 2
emulatedLen 4
relocCount 0
next1/next2/jump profile count and firstTarget all zero
```

The candidate creates a clone only in a caller group that has an eligible
resolved `next1` or `next2` edge.  The clone has no publication token, export,
registration row, or relocation array.  Its fast tail requires:

```text
atomic target->pfnJitCode != 0
cpu->wasmJitBailout == 0
cpu->yield == 0
```

On any failed predicate it keeps the original generic-dispatch return.
Successful clone invocation receives `(cpu, relocBase=0)`; the thunk's own
dynamic return remains the ordinary generic dispatcher.

Static totals:

| Item | Count |
|---|---:|
| selected target keys | 11 |
| raw candidate edges | 158 |
| pattern-rejected source/group rows | 3 |
| actual clone functions | 16 |
| actual direct clone tails | 150 |
| clone generic return tails | 32 |
| changed groups | 6 |

The manifest's `admittedEdges=155` label is broader than the 150 actual
rewrites: five additional edges fail the exact optimized-body matcher and
remain on the original path.  This is fail-closed, but the statistic should be
renamed/refined before production promotion.

## Independent verification

- all 94 candidate Wasm modules pass `WebAssembly.validate`;
- all 30,550 raw key/EIP/hash/op/length/reloc identities match;
- all 28,944 relocation patches remain same-group registered reloc>0 targets;
- 16 clone indices are outside export/registration sets;
- WAT contains exactly 150 clone-local `return_call` sites;
- all 150 have pfn/bailout/yield guards;
- the positive fixture executes a clone and verifies pfn-zero, yield, and
  bailout fallback;
- feature-off and feature-on regeneration are byte-exact.

## Visual A-B-A-B-A

Every row uses the accepted Touch2 runtime and differs only by cache URL.
Scene settle is 180 seconds, warmup 20 seconds, measurement 45 seconds in a
fresh visible Edge profile/process.

| Order | Condition | Presents / wall | FPS | Visual |
|---:|---|---:|---:|---|
| 1 | A1 currentabi1 | 1,343 / 45.017250 s | 29.8330 | PatHouse before/after |
| 2 | B1 PIC clone | 1,383 / 45.009313 s | 30.7270 | PatHouse before/after |
| 3 | A2 currentabi1 | 1,339 / 45.012702 s | 29.7472 | PatHouse before/after |
| 4 | B2 PIC clone | 1,408 / 45.007480 s | 31.2837 | PatHouse before/after |
| 5 | A3 currentabi1 | 1,373 / 45.017264 s | 30.4994 | PatHouse before/after |

Condition means:

```text
A = 30.026533 FPS
B = 31.005350 FPS
B/A = +3.259839%
```

Adjacent B/A effects are:

```text
B1/A1 +2.9967%
B1/A2 +3.2938%
B2/A2 +5.1652%
B2/A3 +2.5715%
median  +3.1452%
```

Control A1→A3 drift is +2.2338%; candidate B1→B2 drift is +1.8118%.
Both remain inside the existing 3% stability boundary.

## Browser diagnostic repair

While the user's ordinary Edge profile was open, Edge 151 handed the command
line from the short-lived starter PID to a new compatibility-relaunch PID.
The original sampler inspected only the starter and failed before measurement.

`Invoke-AzrokBrowserPresentSample.ps1` now resolves the unique top-level
browser process carrying both the random diagnostic profile path and exact CDP
port, rejects `--type=` children, and never attaches to the user's normal Edge
profile.  The five accepted rows all record the resolved PID and exact command
line.  Two pre-measurement failures produced no CSV rows.

## Recovered deletion incident

During independent audit, a PowerShell helper named `RM` collided with the
pre-existing case-insensitive `rm` alias and deleted the control/candidate ZIPs.
No browser/runtime source or production asset was affected.  Exact byte-level
regeneration copies already existed in the audit temp directory; both ZIPs
were restored to their original names and reverified locally and over HTTP:

```text
control   b007fa84...9035a
candidate 7309bec3...af86
```

The deletion was therefore fully recoverable with no data loss.  Future audit
helpers must not use names that collide with shell aliases.

## Production boundary and next gate

Do not change the public/default cache yet.  Before production promotion:

1. add raw-manifest SHA pinning to the generation CLI, not only the verifier;
2. refine `admittedEdges` versus actual rewrite statistics and add a
   nonzero-patternRejected negative fixture;
3. bind the pinned root/module identity and immutable R-X text assumption to a
   loader/runtime gate, or add a stronger per-target publication identity.

The next performance candidate co-locates and routes the exact
`NtCurrentTeb -> pthread_getspecific` chain while retaining the real TLS load.
That chain exposes 2,547,603 internal transitions per 20 seconds, 12.5854% of
owner-CPU generated entries, and is a materially larger target than the small
PIC gain.

## Artifacts

- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/boxedwine-wasm-jit-cache-pipeline.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/make-internal-clone-pipeline-fixture.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-internal-clone-pipeline-fixture.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-internal-clone-cache.mjs`
- `tools/boxedwine_local/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-picthunkclone11x1.zip`
- `tools/browser_diagnostics/Invoke-AzrokBrowserPresentSample.ps1`
- `artifacts/performance/regional_picthunkclone_aba_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_picthunkclone_aba_actual_pathouse_visual-review.csv`
