# Gate 2c: `0x10046780` browser reachability rejection

Date: 2026-07-21

## Result

- **VERIFIED (browser):** the relocation-aware control marker resolved RVA
  `0x00046780` to `0x7F3A6780`, consistent with the observed Acknex base
  `0x7F360000`.
- **VERIFIED (browser):** a final full PatHouse frame rendered at 1024x768 with
  the baseline wall, doorway, carpet, table, stool, character, shadow, HUD,
  Korean text, alpha, and culling intact.
- **VERIFIED (browser):** the same live frame reported
  `dpupCount=215246`, while the monotonic exact-entry count remained `0` and
  no relocated-address mismatch was reported.
- **VERIFIED (transport logs):** the stable release-package session remained
  connected for 248.792 seconds. PatHouse bootstrap arrived as 736 bytes at
  `00:37:32.458Z`; guest follow-up writes arrived 23 ms and 38 ms later and
  decode as two C2S `0x0017` messages plus C2S `0x0008`. Heartbeats continued
  for 160.518 seconds after bootstrap before the deliberately closed browser
  tab disconnected.

Therefore the dispatcher-visible exact entry `0x10046780` is **not active in
the fixed PatHouse workload** and the 12-byte helper from documents 213/216
must not be connected to production for this workload.

## Measurement correction

The first HTML observer stored the last worker message. Because the native
counter was `thread_local`, a late zero marker could overwrite an earlier hit.
The observer was corrected to preserve a monotonic maximum and flag relocated
address disagreement before accepting the negative result.

Two earlier attempts used the obsolete
`Azrok_D3D9Web_pathouse_lockprobe.zip` package and disconnected about 1.7
seconds after bootstrap. They are excluded. The accepted run used the current
stable `Azrok_D3D9Web_pathouse_fvfcache_release1.zip`; it rendered the complete
scene and stayed live for more than 2 minutes 40 seconds after bootstrap.

## Next gate

Document 218 defines a five-entry, one-session probe set. Its counts must be
global atomic counts across pthread workers, with one zero control per RVA.
The probe build is diagnostic only and must not be used for FPS comparison.

