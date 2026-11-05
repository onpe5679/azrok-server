# 292 — v3 pair replay black-frame triage

## Status

**VERIFIED dynamic/static/build/browser:** the initial black canvas observed
immediately after v3 launch was a pre-input game state, not a render-failure
proof.  A game input pulse is required before classifying the PatHouse scene.

## Measurement contract

The previous HUD accumulator was not sufficiently strict because it could
consume duplicate worker/window samples and used 120-Present sample edges.
The PatHouse page now has an opt-in measurement-only control (`presentCapture=1`)
which directly samples same-window `D3D9WebDebug.presents` over 30 seconds,
requires visible state throughout, CSS canvas 1024x768 at both endpoints, a
29.950--30.250 second wall interval, and a positive direct delta.  It fails
closed.  It retains the project metric: guest `COMMAND.PRESENT` submitted to
the host, not GPU/compositor completion.

The accepted ABI2 A1 control reached visible PatHouse before and after capture:
1,451 Presents in 30.003 seconds = **48.3619 FPS**.  This is only an A1
baseline; no pair candidate performance conclusion follows.

## Initial black-canvas observation corrected

**NOT A FAILURE:** `boxedwine.threadedtailabi2` with
`azrok-jit-grouped-threadedtailabi2.zip` registers the exact v3 pair contract:
147 groups, 34,322 entries, 24,304 patches and `jitReplayPair=registered`.
initially showed a black canvas before any game input. Browser console had no
host error and the guest log reported `D3D9WEB_PRESENT_WINDOW`, but neither
signal proves the scene has progressed. The required input pulse was omitted
in that first observation, so it cannot be used as a rendering conclusion.

Static review found the original 24,304 patches correspond to 3,472 typed
store-sinking direct tails (seven relocation operands each).  Those tails
remove both eight GP stores and `wasmHelper_fetchNextOp`; the latter normally
sets `cpu->nextOp`.  This was a plausible but unproven cause.

## Direct-tail isolation

**VERIFIED smoke artifact:** rebuilt a same-record v3 pair artifact with
`--no-direct-calls --mt-pfn-jit-code-offset 12`:

- `azrok-jit-grouped-threadedtailabi2-nodirect-smoke2.zip`
- SHA-256 `cb21cbc0d23eda698e0226dfeb696fcf1bd1e82017da2dfe9edc928dd89f6703`
- 147 groups, 34,322 typed entries, **0** direct patches,
  `directCalls=false`.

Its browser loader reported pair registration with exact 147/34,322/0 counts.
After the required `512,384,140ms` input pulse, it rendered the normal visible
1024x768 PatHouse scene with character, furniture, carpet and Korean HUD.
Therefore the prior black pre-input image is invalid evidence, and neither
the direct store-sinking tail nor the merged pair loader is accepted or
rejected on it.  The no-direct artifact is a correctness smoke only.

## Next

**VERIFIED REJECTED:** returned to the original 24,304-patch v3 cache and
issued the same `512,384,140ms` pulse.  Eight seconds later its 1024x768
canvas remained entirely black.  The otherwise identical 0-patch pair cache
had rendered PatHouse after that same progression.  This is a controlled
direct/no-direct render-integrity split: the 3,472 store-sinking typed direct
tails are the current root-cause scope, and the direct-tail artifact is
disabled from A-B-A.

The next implementation must preserve `cpu->nextOp` on the typed direct-tail
success path (or prove an equivalent exact update), then add a real multi-block
guest regression before rebuilding a fresh cache.  Do not claim a performance
result for either v3 artifact yet.
