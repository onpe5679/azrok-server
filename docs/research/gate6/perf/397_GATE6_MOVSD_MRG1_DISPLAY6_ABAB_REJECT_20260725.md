# 397 -- MRG1 Gen2 DISPLAY6 A-B-A-B performance rejection

Date: 2026-07-25  
Status: **VERIFIED** private MRG1 performance result: **REJECTED**.

## Valid recovered DISPLAY6 sequence

The dedicated new-schema CSV contains five fresh-profile, visible direct-Present
rows. Every row passed sole target, pinned runtime/cache identity, anti-throttle
argv, unchanged outer rect/viewport, zero upper overlap, complete Edge tree,
working-set, free-memory and present-collapse gates. The two recovered controls
first fixed baseline 46.5838 FPS (396); the performance sequence is:

| leg | role | FPS |
| --- | --- | ---: |
| A1 | accepted | 46.0512 |
| A2 | accepted | 47.1164 |
| B1 | MRG1 Gen2 private replay | 41.1543 |
| A3 | accepted | 48.7563 |
| B2 | MRG1 Gen2 private replay | 41.2957 |

Following the required adjacent A/B normalization, candidate effects are
`B1/A2 -12.6540%`, `B1/A3 -15.5918%`, and `B2/A3 -15.3018%`.
Their median is **-15.3018%**, decisively outside the +/-3% noise boundary.
B1/B2 differ only +0.3436%, while all two B rows are about 41 FPS. MRG1 stays
private and is rejected for performance. The two pre-timing CIM/process census
races produced no CSV/FPS row and are not included.

## Correctness and scope boundary

This does not overturn MRG1 correctness: 346 cache-off render, 383 Gen2
cache-off render, and 385 pinned 165-group replay render remain closed.
Correct replay/render proves semantics and liveness, not FPS benefit.

The private MRG1 raw is legacy-wrapper-only and lacks ordinary MT direct
pipeline runtime fields; its fail-closed identity requires `--no-direct-calls`.
MRG1 is therefore a whole-candidate result, not a per-MOVSD-arm attribution:

- accepted: 94 groups / 30,550 modules / 4,306 components / 29.87 MiB merged
  Wasm / 4.804 MiB ZIP / 28,944 patches;
- MRG1: 165 / 52,487 / 6,939 / 51.34 MiB / 7.554 MiB / zero patches;
- accepted owns 9,648 direct plus 209,969 generic-indirect tail rewrites
  (219,617 total); MRG1 has zero of both;
- MRG1 has 37,270 candidate edges (17,358 hot next1/2 eligible), but no-direct
  rewrites none; its raw corpus is also 71.8% larger.

It is **INFERRED**, not individually measured, that lost tail chaining and
larger module workload are the major contributors. This result does not
quantify MOVSD helper savings, wrapper overhead, or the unrelated dual-entry
R2 5,299-site question. MRG2's previous rejection remains a separate corpus.

DISPLAY6 results decide this private candidate only. They do not prove
absolute 60/65 FPS progress or GPU-adapter causality; primary-display target
assessment remains separate.
