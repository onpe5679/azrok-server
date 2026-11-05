# 520 Gate 6 desktop BGM-on sustained Present result (2026-07-28)

## VERIFIED

- One existing isolated desktop Edge game tab was brought to the foreground;
  no tab was created for this measurement.  The live original guest canvas
  was visible at CSS `1024x768`, and its BGM compatibility sink reported
  `playing` throughout.
- Three adjacent direct native `COMMAND.PRESENT` windows were measured without
  a build or cache-generation step between them:

  | window | Presents | duration | FPS |
  | --- | ---: | ---: | ---: |
  | 1 | 2,160 | 30.014 s | 71.967 |
  | 2 | 2,160 | 30.037 s | 71.912 |
  | 3 | 2,040 | 30.041 s | 67.907 |

- The minimum observed window is `67.907 FPS`, above the requested desktop
  50-FPS floor while BGM remained active.

## SCOPE

- This is the isolated desktop browser path and a direct Present measurement;
  it does not substitute for the separately required physical-phone test or
  for reciprocal Plaza remote-actor proof.
