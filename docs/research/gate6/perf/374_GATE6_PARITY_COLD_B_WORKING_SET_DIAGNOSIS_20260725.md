# 374 -- parity cold-B working-set diagnosis (2026-07-25)

> **SUPERSEDED in part by 416.** The historical diagnosis remains valid, but
> its future invocation phrase using a cold pre-sample A working-set reference
> is replaced by the healthy control A post-sample reference required by 416.

Status: **VERIFIED diagnostic only; no parity FPS or verdict**

## Question and method

373 left two competing explanations for the 5.72--5.90GiB B-process state:
the private parity corpus itself might require that footprint, or an A-to-B
same-tab navigation might retain prior Wasm/renderer memory.  A human-created
fresh isolated Edge instance was directly rechecked through CDP: exactly one
`about:blank` page, all four local services listening, required anti-throttling
flags present, and 482.47MiB combined Edge working set at our preflight.

No accepted A was loaded.  The sole page navigated directly to the existing
private B URL and used the existing 113/35,492/29,181 replay; no build, record
or cache regeneration occurred.  This is a memory diagnosis, never a
30-second FPS sample and never an A/B leg.

## Cold B result

**VERIFIED:** B directly reported parity ABI witness 1, replay registered,
113 groups, 35,492 entries, 29,181 patches, visible CSS 1024x768.  Initial
input sent before Wine reported `Showing Window` produced no Present and is
not used.  After the later normal centre input, the visible page had
**7,938 direct Presents** (HUD 7,920) and the sole Edge tree was
**4,019.02MiB** across 10 processes; its largest process was **3,496.43MiB**.

That is **1,701.44MiB below** the 5,720.46MiB A-to-B pre-gate stop and
**1,885.75MiB below** the 5,904.77MiB repeated reject.  It is also slightly
below the admitted A retry's 4,225.28MiB pre-sample tree value.  Thus B alone
does not exhibit a distinctive 5GiB-plus footprint.

**INFERRED -- operational conclusion:** The prior 5GiB B state is retained
memory from same-tab page replacement (or its renderer lifetime), not an
intrinsic parity-candidate memory requirement.  The direct contrast strongly
supports this; it is not a byte-level browser allocator proof.  Performance
legs must therefore use a fresh isolated browser process per leg, and all
comparisons remain cold-process relative comparisons.

## Static scope check

**VERIFIED:** The parity main Wasm is only 695 bytes larger than control.  Its
cache is genuinely larger -- 113 vs 94 groups, 35,492 vs 30,550 entries,
36,420,837 vs 29,869,761 merged group-Wasm bytes -- mostly 4,976 parity-only
recorded entries.  C++ retains one group-byte copy, adding about 6.55MiB, and
worker-local group instances can amplify native memory only as groups execute.
These bounded corpus differences cannot by themselves explain the observed
1.70--1.89GiB same-tab excess; no attribution of that excess to parity
semantics is permitted.

## Required follow-up

The requested direct browser-restart capability probe follows this diagnostic.
If it succeeds, each performance leg will be launched with the exact standard
runner flag set and a new profile/port lifecycle.  The first cold A explicitly
establishes its working-set baseline; later legs must carry a prior reference
and have their before/after gates recorded.  Re-run parity A-B-A-B only under
that per-leg cold-process protocol.

## Direct restart capability probe

**VERIFIED:** The diagnostic B instance was closed cleanly through CDP
`Browser.close`; port 9222 and every `msedge` process then disappeared while
8765/9200/9201/9300 remained listening.  A separate attempt to launch Edge
with the exact `Invoke-AzrokBrowserPresentSample.ps1` Default argument set
(fresh `--user-data-dir`, 9222, the three anti-throttling flags,
`--enable-automation`, autoplay policy and `--new-window`) was rejected by
the execution policy before process creation.  A post-attempt probe confirms
zero Edge processes and no 9222 listener.  This agent therefore cannot perform
the required per-leg browser restart; human launch remains required.  No
policy bypass was attempted.

## Cold-leg attach contract hardening

**VERIFIED static repair:** The attached sampler now requires a mandatory
leg role and output CSV.  `ControlA` alone may establish a zero-prior baseline;
`CandidateB` must carry a positive prior.  It rejects a role/cache/stem mismatch
(A: accepted ABI2 + 94/30,550/28,944 cache; B: parity ABI1 +
113/35,492/29,181 cache and `parityCurrent=1`), any `--js-flags` override,
and active compiler/build processes.  Before a timing window it also reads the
page's live replay identity and parity witness.  Thus a human-launched cold
leg cannot silently convert B into a baseline, use the wrong corpus, run with
NoLiftoff/other V8 flags, or run while a rebuild is active.

For each human restart, the operational sequence is: confirm a single blank
CDP page and one isolated Edge tree before navigation; navigate/start the
specified leg; wait for the matching replay identity and normal Presents; then
run the attached sampler with `ControlA -EstablishWorkingSetBaseline` for the
first A, or the prior valid cold-leg pre-sample MiB for every later A/B leg.
The sampler records/rejects both working-set boundaries.  Its visibility and
z-order assertions remain start/end snapshots, not a claim of pixel-perfect
mid-window occlusion proof.
