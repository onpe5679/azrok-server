> **ARCHIVED (2026-07-17).** 이 문서는 대체됨 — 현재 확정 사실은 ../INDEX.md 참조.

# Crash Timeline And Failure Modes

## Useful Crash Families

| Time (KST) | Offset | Interpreted VA | Meaning |
| --- | --- | --- | --- |
| 10:01:12 | `0x0021571E` | `0x0061571E` | `0x00615650` wrote through a missing self entity |
| 10:06:19 | `0x00216AD2` | `0x00616AD2` | early network `0x006E` touched an object too early |
| 10:36:58 | `0x001D407F` | `0x005D407F` | state-1 `0x0003` replay crashed in the state-1 string handler |
| 11:39:51 | `0x001B6213` | `0x005B6213` | deeper `0x0064` tail crash after partial self-bootstrap progress |
| 12:29:53 | `0x0014550F` | `0x0054550F` | direct `SendC2S_0064_LocalBootstrapStatus (0x006130B0)` bootstrap used the wrong local context object |
| 12:38:01 | `0x0010B712` | `0x0050B712` | `FUN_0050B400(0x6E)` was called with the wrong `this`, so `gm+0x31796` write crashed |
| 13:12:46 | `0x002084CD` | `0x006084CD` | local scene bootstrap reached `FUN_006084A0`, but `ent_for_name("sky_MDL_325")` returned null |
| 13:24:08 | `0x002159EC` | `0x006159EC` | late tail of `HandleS2C_0064_ApplyAuthoritativeSelf (0x00615650)` faulted after the E1515 popup/error path had already gone wrong |
| 13:52:15 | `0x002159EC` | `0x006159EC` | same late-tail crash reproduced after self-id reconcile; the final wrapper reacquire is now the active patch target |
| 13:59:32 | `unknown+0x00000002` | n/a | post-close crash after `popup+0x9C = 1`; current best fit is a null/invalid indirect call target in stage 6 `FUN_00614720` |
| 19:05:46 | `0x0011B110` | `0x0051B110` | next-screen confirm popup crash; `FUN_0051b0e0` wrote through a missing child widget pointer at `this+0x3d` |
| secondary | `0x0026AFE2` | `0x0066AFE2` | recurring follow-on failure, not the main decision point |

## What Each Crash Ruled Out

- `0x0021571E`
  - proved that `0x0064` needs a real singleton self entity
- `0x00216AD2`
  - ruled out early network `0x006E`
- `0x001D407F`
  - ruled out early state-1 `0x0003` replay
- `0x001B6213`
  - proved that getting past the first null-entity fault still leaves deeper
    runtime prerequisites missing
- `0x0014550F`
  - proved that calling `SendC2S_0064_LocalBootstrapStatus (0x006130B0)` directly is too context-sensitive
- `0x0010B712`
  - proved the `0x6E` local scene dispatcher is the right general area, but
    the call convention must be correct
- `0x002084CD`
  - proved the local bootstrap can now get past the original self-null stage
  - shifted the blocker to missing named scene assets during `FUN_00614370`
  stage 3
- `0x002159EC`
  - shows that even after self entity creation and self-id reconciliation, the
    final loading-close handoff can still die while reacquiring `this+4`
  - points to a tail-specific close-path fix rather than more early packet work
- `unknown+0x00000002`
  - shows that once the close handoff is preserved, the next blocker is a
    post-close indirect call target rather than the old wrapper-reacquire fault
  - points to stage-6 manager/object virtual calls as the next patch area
- `0x0011B110`
  - shows that the client can now progress past the pure loading-screen phase
  - shifts the next blocker to a popup/UI child object that is missing at
    confirm-click time
  - supports a narrow null-guard around `FUN_0051b0e0` instead of more loading
    protocol changes

## Current Safe vs Unsafe Ideas

Still safe enough to keep testing:

- `0x0064`
- `0x0065`
- `0x0066`
- `0x0068`
- `0x0069`
- local-scene bootstrap through `FUN_0050B400(0x6E)` with a correct `ECX = gm`
- a null guard around `FUN_006084A0` sky initialization
- Plaza-aligned `0x0003` scene choice
- a null guard around stage-4 water/sound `ent_playloop`
- a tail guard that feeds logged `gm` directly into `FUN_0050A840`
- stage-6 virtual-call guards around the four `FUN_00614720` indirect calls

Still unsafe or premature:

- state-1 `0x0003` replay
- early network `0x006E`
- direct `SendC2S_0064_LocalBootstrapStatus (0x006130B0)` one-shot call

## Current Decision Rule

If the next crash still happens after the corrected `ECX = gm` fix, the next
target should be:

- the internal stage flow under `FUN_00614370`, especially scene-asset stages

not:

- more random packet additions
- more actor-list packets on the self id path

## 2026-03-30 Evening Addendum

- No new single decisive crash family replaced the current late-stage reading.
- The most important reclassification was visual, not symbolic:
  - several "better-looking" screens were still just baked loading-state art
- What the evening session ruled out:
  - `AZROK_SCENE_READY_FORCE=0` as a real progress fix
  - `HIGH_RESOURCE_STATS` as a direct fix for the wrong-screen state
  - raw `PatHouse` path reroute as a sufficient fix
- What the evening session promoted in priority:
  - later repeated client `0x0007` handling
  - less invasive popup policy
  - distinguishing true in-world transition from progressed loading art
