# Gate 6: BGM fresh-media-sink recovery

Date: 2026-07-28 KST

## VERIFIED

- The active private HTTPS game's `PetHouse.mp3` fallback was unmuted,
  `readyState=4`, and advancing while the user still reported no audible BGM.
  That browser state alone is therefore insufficient as an audibility claim.
- `PetHouse.mp3` is an original non-silent 85.21-second MP3.  Its first 30
  seconds measure -14.5 dB mean level and 0.0 dB peak by `ffmpeg
  volumedetect`.
- The BGM recovery path now destroys the prior HTML media element and creates
  a fresh element in the actual launch/recovery-button activation.  It starts
  at full volume and from the beginning, avoiding a restored tab retaining a
  live-but-silent output sink.  Guest path-driven map selection keeps using
  the same replacement-capable element.
- After reloading the live private page and using the real launch button, one
  and only one fallback element existed; it selected `PetHouse.mp3`, had
  `paused=false`, `muted=false`, `readyState=4`, full volume, and advanced to
  5.70 seconds with `webBgmFallback=playing`.

## NOT VERIFIED

- Hardware speaker/headphone audibility.  The in-app browser exposes DOM
  media state but no device output meter.  The user's report before this
  recovery was treated as a real failure signal, not overwritten by DOM
  state; confirmation must be by listening to this freshly restarted track.
