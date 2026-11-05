# 396 -- MRG1 recovered DISPLAY6 accepted baseline

Date: 2026-07-25  
Status: **VERIFIED** baseline qualification; MRG1 candidate remains unmeasured.

## Recovered fresh controls

After direct proof that AfterFX is absent and free memory is about 146 GiB,
two independent watcher-fresh accepted controls passed the full current
contract, including exact outer rect, viewport, sole Edge tree, anti-throttle,
working-set, free-memory and present-collapse gates:

| leg | direct Presents / seconds | FPS |
| --- | --- | ---: |
| A1 | 1,382 / 30.010094 | **46.0512** |
| A2 | 1,414 / 30.010800 | **47.1164** |

The A2/A1 change is +2.31%, inside the user-specified +/-3% noise boundary.
Their two-value median is **46.5838 FPS**, fixed as the recovered DISPLAY6
accepted baseline. Its 50% collapse floor is **23.2919 FPS**. A2 carried A1
working-set 4,233 MiB, free-memory 142,862 MiB and present 46.0512 priors;
all gates passed. The new dedicated CSV retains every added gate field.

## Causal boundary

The historical pressure observations remain ineligible for candidate
disposition. Compared with them, recovered controls are higher and stable, so
memory pressure is compatible with contributing to prior instability. However,
the recovered DISPLAY6 baseline is not the historical primary-display 54 FPS
condition. This single same-display recovery therefore does **not** prove that
memory pressure alone caused the older low values, nor that display/GPU
selection is or is not causal. A persistent DISPLAY6/display-path covariate is
still **INFERRED**; WebGL renderer/adapter remains intentionally unqueried.

These 46.5838-FPS data are valid only for same-placement relative MRG1
adoption/rejection. Absolute 60/65 FPS progress still requires a separate
primary-display measurement.

## Next sequence

Run fresh MRG1 B, accepted A, and MRG1 B with `46.5838` as the present-collapse
prior and the last valid A working-set/free-memory priors. Apply adjacent
A/B boundary median +/-3% decision after all four legs.
