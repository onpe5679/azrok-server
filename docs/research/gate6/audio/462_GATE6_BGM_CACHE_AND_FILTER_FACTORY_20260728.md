# Gate 6: BGM cache bypass and Quartz filter-factory result

Date: 2026-07-28 KST

## Cache-key control

- **VERIFIED (package):**
  `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-cachefresh1.zip`
  is byte-identical to the retained dsound80ms BGM root:
  `329BEA48852C33C7937B9848EE37500060C31ADFA751F75CA256A8532EED4228`.
  It exists solely under a new filename so BoxedWine cannot reuse a root ZIP
  cached by the old filename.
- **VERIFIED (browser):** the cache-fresh root reached PatHouse with the graph
  guest, opened `Data/Sound/PetHouse.mp3`, and still produced zero BGM DSP
  samples.
- **VERIFIED (browser):** the cache-fresh run failed to instantiate not only
  `GStreamer splitter filter` but also `MPEG-I Stream Splitter`, `AVI Splitter`,
  and `Wave Parser`, each with `0x8007000e`.

## Consequence

- **VERIFIED:** stale root-cache content is not sufficient to explain the
  current BGM failure. The common failure is Quartz filter-object creation
  before MP3 decoding, so replacing an MP3, changing its loop logic, or
  changing the GStreamer registry alone cannot restore music.
- **NOT VERIFIED:** the cause below Wine Quartz's `IMoniker_BindToObject`
  return path. The next diagnostic must expose the class-factory/COM failure
  without the high-rate D3D audio trace displacing its startup logs.
- **NOT VERIFIED:** audible BGM in the current performance runtime. The
  private user tab has been placed on the explicit `upstreamjit64fn6inlineabi2`
  candidate with the fresh root for a genuine user-gesture check, but this is
  not yet a PCM or audible acceptance result.
