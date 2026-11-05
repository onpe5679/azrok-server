# 516 BGM guest-request boundary (2026-07-28)

## VERIFIED

- The prior web fallback armed and started `PetHouse.mp3` on the page's first
  browser gesture, including the launch button, before the Wine guest had
  booted or opened an MP3 path.
- That sound was the original MP3 asset delivered by a browser audio sink, not
  a playback request made by the original Azrok executable.  It therefore
  crossed the preservation boundary even though it did not replace or patch
  the executable.

## IMPLEMENTED

- The first gesture now only resumes a silent Web Audio context.
- Browser BGM playback is gated on the guest filesystem observer seeing the
  original executable open one of its mapped MP3 files.  A `PetHouse.mp3`
  request is recognized even when it is already the fallback's default track.
- The observer attempts immediate installation and retries until the guest FS
  becomes observable.  There is no `Present` or URL-track recovery trigger:
  a missed original MP3 open produces no browser BGM rather than speculative
  early playback.  The manual BGM recovery controls use this same gate.
- `startAzrok()` no longer invokes the BGM rearm routine before guest boot.

## VERIFIED (fresh isolated runtime)

- A freshly loaded private diagnostic page reported no guest MP3 request, no
  BGM start timestamp, and a paused BGM element before its run button was
  activated.
- After the run click, the page remained BGM-silent through JIT registration.
  On the real rendered guest run, it reached 3,360 visible native
  `COMMAND.PRESENT` samples; the guest FS observer then recorded
  `intro.mp3` at `82,486.960 ms` and the browser media sink started at
  `82,506.820 ms` (about 19.86 ms later).
- This proves the new browser-side ordering for that run: no pre-boot audio,
  then original guest MP3 open, then fallback playback.  The source remains
  the delivered original MP3 asset; no executable replacement or binary patch
  was used.

## NOT VERIFIED

- Physical speaker audibility and a human-operated pointer are separate from
  this isolated CDP-input sequence and remain to be confirmed on the user
  path.  The timing result itself is direct runtime evidence, not an
  inference from source inspection.
