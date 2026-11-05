# Gate 6 all-music web fallback (2026-07-28)

## Result

- **VERIFIED (package):** `tools/extract_web_bgm_fallback.py` now extracts every `Data/Sound/*.mp3` member from the current game package: 15 original music files. It writes a SHA-256 manifest alongside the assets and rejects an unexpected `PetHouse.mp3` digest.
- **VERIFIED (private HTTPS serving):** all 15 music URLs returned HTTP 200 as `audio/mpeg` from the private `<lan-ip>` service.
- **VERIFIED (private browser):** the page's fallback manager can select another original BGM after initial gesture. `Oxquiz_back.mp3` reached `state=playing`, `paused=false`, `readyState=4`, and advanced to `currentTime=2.628868` seconds. This is direct decode/playback evidence for a second, distinct original BGM.
- **VERIFIED (runtime integration):** the browser fallback patches the BoxedWine filesystem `open` boundary once available. It recognizes only the 15 extracted MP3 basenames and switches the already gesture-authorized audio element to the corresponding same-origin original track. The current PetHouse track remains the initial fallback.

## Boundary

- **NOT VERIFIED:** a natural in-game transition (for example PetHouse to OX/cooking/Plaza) reaching the observed `FS.open` hook. The hook was installed during a running private game, but the initial PetHouse file had opened before that installation. A real map/minigame transition must still prove automatic selection for the full BGM-transition acceptance.
- **NOT VERIFIED:** native Wine Quartz/GStreamer MP3 output; this is the browser containment path while the verified `unix_wg_parser_create` access violation remains open.
