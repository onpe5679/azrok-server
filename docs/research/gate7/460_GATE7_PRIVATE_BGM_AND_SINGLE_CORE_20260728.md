# Gate 7: private browser BGM route and single-core gateway

> **BGM PCM conclusion SUPERSEDED by 461.** The later direct graph trace
> showed `PetHouse.mp3` opening, but the Quartz GStreamer splitter failing and
> all reported BGM DSP samples being zero. Keep the network findings below;
> do not use this document as evidence that the default route produces BGM.

Date: 2026-07-28 KST

## Result

- **VERIFIED (browser):** the default route had regressed to `Azrok_D3D9Web_pathouse_guestbatch1` / `run_azrok_seh.bat`. That guest starts effects but does not register Quartz and `winegstreamer`, so it is not a valid BGM launch route.
- **VERIFIED (browser):** the shell accepted only 11,025 or 22,050 Hz and silently changed the page's requested `audioFreq=44100` to 11,025 Hz. The shell now accepts 44,100 Hz. A fresh launch logged root `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1`, app `Azrok_D3D9Web_pathouse_audiofix1`, program `run_azrok_audiofix.bat`, and `setting audioFreq to: 44100`.
- **SUPERSEDED by 461 (browser):** the earlier nonzero `D3D9WEB_AUDIO_DSP_WRITE` interpretation was not a valid BGM proof. A later direct graph trace established zero BGM PCM after a Quartz GStreamer splitter failure.
- **VERIFIED (browser):** the corrected BGM route rendered 72.3--81.4 FPS in the visible HUD while entering the local game flow. This is not the canonical three-by-30-second Present performance gate.
- **VERIFIED (runtime):** an HTTPS asset server and WSS bridge listen only on `<lan-ip>:8765` and `<lan-ip>:9201`. The game core and GUI remain loopback-only at `127.0.0.1:9200` and `127.0.0.1:9300`; there is no public or wildcard listener in this configuration.
- **VERIFIED (runtime):** WSS requests without the instance token and with a wrong token were closed with policy code 1008; a valid token connected. The token is intentionally not written to this document or to bridge logs.
- **VERIFIED (browser + GUI):** a private HTTPS/WSS browser session reached character selection at about 73 FPS. The loopback GUI simultaneously reported one shared core with two connected identities, `player` and `peer111`.

## Single-core topology

```
private browser -- HTTPS <lan-ip>:8765
private browser -- WSS + token <lan-ip>:9201
                                   |
                                   v
                         loopback core 127.0.0.1:9200
                         loopback GUI  127.0.0.1:9300
```

The bridge target is fixed loopback, never client-controlled. This avoids a second game instance and avoids exposing a TCP service or GUI on the private NIC.

## Remaining gates

- **NOT VERIFIED:** a fresh restricted-IP two-browser Plaza proof with both peers in the same room, reciprocal 0x0066/0x0068, and targeted 0x0067 leave. The historical two-browser evidence is documented in 253, but this fresh Gate 7 run has only reached two authenticated connections and the GUI state.
- **NOT VERIFIED:** a human audible BGM check and long-duration BGM+SFX mix on the corrected release route.
- **NOT VERIFIED:** mobile-device or genuine mobile-emulation 50 FPS evidence.
- **NOT VERIFIED:** canonical direct-Present 3x30s all-at-least-50 FPS gate.
