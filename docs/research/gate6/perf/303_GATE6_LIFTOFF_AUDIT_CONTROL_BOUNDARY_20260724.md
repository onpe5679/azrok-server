# Gate 6 - Liftoff / `--no-liftoff` control boundary

Date: 2026-07-24

## Scope

The requested diagnostic needs a same-Chrome, same-profile, one-tab visible
PatHouse A-B-A comparison with only `--js-flags="--no-liftoff"` changed on the
B process. This is a measurement card, not a production runtime change.

## VERIFIED control boundary

The available standard-Chrome control surface attaches to an already running
Chrome instance and can create a clean agent tab, but browser JavaScript flags
are process-start flags and cannot be added to that instance after attachment.
The previous isolated-profile launch did not expose a controllable tab on that
surface. This run reconfirmed that the standard Chrome attachment has no
supported operation for launching or attaching to an independently started
`--no-liftoff` profile process. Restarting the user's Chrome is out of scope;
the ChatGPT application was not restarted.

## Verdict

**NOT MEASURED.** No baseline or `--no-liftoff` FPS leg is recorded, and no
Liftoff/tier-up conclusion follows. Do not substitute a different browser,
mix a user Chrome process with an isolated profile, or count a launch/splash
window as a result. The card remains pending a controllable same-binary
separate Chrome or Edge process that can receive the startup flag while
preserving the one-tab A-B-A protocol.
