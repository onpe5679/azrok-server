# 138 Gate 2b: named CLI startup contract removes the WDL-injection race

Date: 2026-07-19

Status: **VERIFIED**. This supersedes the Gate 2b conclusion in 137 that the
`c0000005` was a native BoxedWine D3D/render-path blocker.

## Exact startup contract

The successful native BoxedWine / Wine 11 command line is:

```text
Azrok.exe -NX 200 -NWND -PL player -DIR localauth -IP 127.0.0.1:9200
```

The disposable mount contains the original-hash-matched `med.exe`. No original
game executable bytes, imports, socket hooks, or WDL memory pointers were
patched.

## Root cause of the old fault

The deferred guest-launcher injection path faults before its external poll can
observe `0x006e8430`, even with a 1-ms initial cadence:

```text
AZROK_GUEST_FAULT eip=00654453 ... return=00508CE6
AZROK_GUEST_FAULT_ARGS ... source=00000000
AZROK_GUEST_INIT_SERVER_DWORDS 00000000 00000000 00000000 00000000
[ERROR] Child exited before engine initialization: 3221225477
```

`FUN_004edb10` passes the empty WDL server-string data pointer to
`FUN_00508b30`; its `strtok(param2, ":")` path then supplies the null source
to the CRT string operation at `0x00654453`. This is a startup race in the
deferred WDL-memory injection approach, not a D3D9 device failure.

The installer-style named CLI supplies server/user/auth at process startup and
removes that race.

## Gate 2b result after the named CLI (VERIFIED)

| Stage | Result | Direct evidence |
|---|---|---|
| (a) launch | PASS | Wine launched the exact named command and created the OpenGL window. |
| (b) D3D device | PASS | Same Wine 11 mount recorded `Direct3DCreate9`, `d3d9_CreateDevice`, and `wined3d_device_create`. |
| (c) visible screen | PASS | Windows.Graphics.Capture captured the nonblank character-selection/lobby UI. |
| (d) frames | PASS | A second capture three seconds later contained changed animated character and tooltip pixels; prior WineD3D trace recorded Present calls. |
| (e) server connection | PASS | The server accepted TCP, received 106-byte C2S `0x0000` login, and completed paced lobby bootstrap / heartbeats. |

## Newly measured environment gaps (not blockers to the five-stage result)

1. The default guest locale has active code page 437. Supplying
   `LANG=ko_KR.EUC-KR` and `LC_ALL=ko_KR.EUC-KR` changes it to 949. The Korean
   client must use that environment; some server-supplied top-line text remains
   to be verified byte-for-byte.
2. `-nosound` disables all audio and was deliberately used in early render
   tests. Removing it enables DirectSound/MMDevice mixing through OSS
   `/dev/dsp`; audible effects are therefore not a generic sound failure.
3. Background MP3 playback remains blocked. `Data\\Sound\\PetHouse.mp3` and
   other BGM files exist in the mounted runtime, but Wine Quartz logs failures
   to create `MPEG-I Stream Splitter`. The bundled guest GStreamer executable
   itself fails to load `libpcre2-8.so.0`, identifying a runtime dependency
   gap rather than missing game media.
4. Character creation causes the server to send the verified
   `Data\\Space\\PatHouse` scene response, and the full `PatHouse` asset folder
   (including `room.wmb`, models, and textures) is present. Its 3D room output
   is still NOT VERIFIED in native BoxedWine and must be measured separately
   from the now-working 2D UI path.

## Evidence artifacts

- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_hoststack_full_0343_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_fastpoll_full_0346_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_cli_named_nx200_0350_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_named_kokr_audio_0405_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_locale_probe_0401_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_locale_probe_kokr_0402_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_gstreamer_probe_detail_0411_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/server_9200_hoststack_full_stdout.log`
