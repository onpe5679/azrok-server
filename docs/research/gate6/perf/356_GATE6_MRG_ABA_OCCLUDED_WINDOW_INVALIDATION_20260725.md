# 356 -- MRG A-B-A occluded-window invalidation (2026-07-25)

## VERIFIED -- cache artifacts remain valid

The accepted current-ABI replay artifact remains a valid repaired control:
94 groups, 30,550 entries, 28,944 patches, live reloc map `12968408`, and a
passing ABI2 cache verifier. The isolated MRG2 no-direct replay remains valid:
95 groups and 30,636 blocks, with its previously documented identity pins.
Both rendered PatHouse before the measurement attempt. Neither artifact is to
be rebuilt for this correction.

## VERIFIED -- all first-pass performance numbers are invalid

The first A-B-A attempt produced these direct-Present numbers:

| leg | value (FPS) | disposition |
| --- | ---: | --- |
| accepted A1 | 3.8851 | INVALID |
| MRG2 no-direct B | 9.3967 | INVALID |
| accepted A2 | 3.5534 | INVALID |

The Edge launch omitted
`--disable-backgrounding-occluded-windows`. The Edge window was fully hidden
behind the maximized ChatGPT window, so these are occluded-renderer-throttled
samples rather than a performance comparison. Their visible-page and
1024x768 checks do not repair that missing process-level condition. The
collapsed control (roughly one twelfth of the established 43--50 FPS range)
is an independent environment-invalidity signal.

The numerical B/A separation is retained only as evidence of the erroneous
condition. It is **not** a candidate adoption, rejection, or estimate of MRG
benefit. Any provisional MRG performance conclusion is expressly withdrawn.

## Required remeasurement contract

The browser has to be restarted with the full diagnostic flags, including:

```
--disable-backgrounding-occluded-windows
--disable-renderer-backgrounding
--disable-background-timer-throttling
```

For every future leg, before sampling, record:

1. exactly one CDP `page` target and the expected URL;
2. `document.visibilityState === "visible"`;
3. CSS display canvas exactly 1024x768 and direct Present growth;
4. the complete process launch flag contract, including the occlusion flag;
5. an accepted baseline in the established 43--50 FPS range.

If the first accepted A is outside that range, stop and discard it before
navigating to MRG. Otherwise measure a fresh accepted A -> MRG B -> accepted
A sequence. Only that sequence may decide the MRG card.

## VERIFIED -- post-relaunch A1 did not reach a sample

After the corrected Edge relaunch, the sole `about:blank` page was navigated
to the accepted current-ABI replay URL only (no new tab). Before startup,
CDP reported `document.visibilityState="visible"`; after startup it reported
visible CSS 1024x768 and `JIT 그룹 등록 완료: 94 groups, 30550 blocks`.
Thus the replay asset registered successfully.

This leg is nevertheless not a baseline sample: for more than two minutes
after `Showing Window`, direct `D3D9WebDebug.presents` remained zero, the HUD
remained `FPS --`, and no `COMMAND.PRESENT`/D3D9 probe reached the page. The
runtime was alive (`runtimeInitialized=true`, `isRunning=true`, `EXITSTATUS=0`)
without a JS abort or D3D9 error. At the same time the localhost bridge had no
established 9201 connection and its logs had not advanced after an earlier
relay close. This is a separate game/bridge-session startup observation, not
a cache verdict and not an MRG FPS result.

Per the required contract, this zero-Present A1 is discarded before any B
navigation. MRG remains **NOT DECIDED** pending a normal accepted baseline.

## VERIFIED -- corrected-flag A1 is also outside the required baseline band

The corrected Edge instance subsequently completed the delayed normal lobby
selection and rendered PatHouse. A direct capture passed its mechanical gate:
visible document, CSS 1024x768, 30,000.4 ms wall time, 1,586 Presents, and
`52.8660` FPS. This is not occluded-window evidence and demonstrates that the
repaired accepted cache can render in the new browser instance.

It is still **invalid for this MRG comparison**. The required accepted
baseline band for this card is 43--50 FPS, and 52.8660 is above it. Per the
predeclared rule, the leg is discarded before B and no candidate navigation or
performance claim occurs.

During the same delayed startup, the server logged a parser declaration of
17,735 (`0x4547`). Because its parser reads the first two bytes as little-
endian payload length, this is directly consistent with `47 45` (`GE`), the
prefix of HTTP `GET`; it cannot be derived from the server's valid 387-byte
lobby frame (`83 01 00 00`). The current evidence does not identify whether
the bridge or another local probe supplied that HTTP stream, so it is not
assigned as the FPS cause. It is retained as a separate bridge-framing lead.

**Status: MRG NOT DECIDED.** A fresh accepted baseline inside 43--50 FPS is
required before an accepted A -> MRG B -> accepted A sequence may resume.

## VERIFIED -- repeated accepted control confirms range mismatch

Without navigating away from the accepted page, a second mechanically valid
visible 1024x768 direct-Present window measured 30,000.5 ms, 1,655 Presents,
and **55.1657 FPS**. It is also outside the required 43--50 FPS band. The two
corrected-flag controls (52.8660 and 55.1657) therefore establish a presently
higher-range environment, not a one-off transition sample. Both are retained
as invalid-for-comparison controls; no MRG B leg was run.

## VERIFIED -- historical baseline band has a cache-corpus confound

The old historical accepted archive (now fail-closed by 355) contains 41,625
recorded entries in 134 merged Wasm groups. The required rebuilt current-ABI
control contains 30,550 entries in 94 groups: 26.61% fewer entries and 31.75%
less merged Wasm (29.87 MB versus 43.76 MB). Direct rewrites are 9,648 versus
10,813, generic tails 209,969 versus 300,477, and patches 28,944 versus
32,439. The ABI is otherwise the same; only reloc map base changes from
12964392 to 12968408, which is exactly why the old archive cannot be replayed.

Therefore the 52.8660/55.1657 current-control observations do not directly
prove a browser anomaly: the forced replacement control has a materially
different record corpus from the source of the historical 43--50 FPS band.
The static difference is a strong confound but not a direct causal proof of
the higher result. The explicit 43--50 gate remains honored (so no B leg has
been run), while a new same-corpus baseline policy must be resolved before a
valid MRG comparison can proceed.

The key-level audit tightens that boundary. Of current's 30,550 keys, 28,842
(94.41%) overlap the old archive; 1,708 are current-only and 12,783 old keys
are absent. Those old-only keys account for 33.67% of old static Wasm bytes,
48.74% of old operation count, 47.96% of emulated bytes, and 46.00% of
relocations. Common keys preserve opcode/emulated-length/relocation count
exactly, and 28,814 (99.90%) preserve Wasm byte size. This proves coverage
non-equivalence rather than a broad current-runtime code change.

It remains **INFERRED**, not verified, that the coverage difference contributes
to the 52--55 FPS shift: no archive contains identical-scene execution
frequency, cache-miss/recompile, V8 tier, or foreground covariates. Historical
accepted controls themselves also include values above 50 (e.g. 50.0406 and
51.03), so 52--55 alone does not prove a regression or a benefit. A new
same-current-corpus baseline policy or paired runtime/covariate evidence is
needed before this card may replace the user-mandated 43--50 admission gate.

## Decision -- current-corpus relative gate approved

The 43--50 FPS admission band is now retired **only as an admission gate**.
It remains preserved above as the historical 134-group corpus observation; that
archive is unreplayable on the served runtime because of 355's reloc-map ABI
mismatch. The verified current 94-group/30,550-entry ABI-matching cache is the
only valid accepted control for this card.

The user approved a relative same-session comparison. Because the two current
accepted controls differ by about 4.3%, the prescribed run is expanded from
A-B-A to **A-B-A-B**. Every leg must carry the 357 launch/HWND/known-overlap
evidence plus visible 1024x768 direct-Present validation. Candidate effect is
decided from the median of adjacent A/B boundaries against the existing +/-3%
noise rule. If that extended result remains within noise, MRG is NOT DECIDED.

## SUPERSEDED decision -- see 359

The authorized current-corpus A-B-A-B completed after this record.  MRG2
no-direct is **REJECTED** for performance by the -21.49% adjacent-boundary
median; the historical occluded values above remain invalid.  Full leg and
artifact evidence is in 359.
