# 546. Guest-owned BGM, 44.1 kHz, runtime identity, and game context menu (2026-08-07)

> **IME SECTION SUPERSEDED by 549.** The BGM, 44.1 kHz, context-menu,
> IDBFS-lock, and lean-output findings remain current.  The korean2 runtime
> identity was an intermediate cache fix; 549 replaces it with korean3/xim1
> and a real `XLookupChars` fake-XIM path.

## Scope

Remove the browser/guest BGM double-play regression, restore the guest audio
quality contract, suppress the browser context menu over the complete game
surface, and separate the Korean runtime from stale browser caches.  No game
binary was patched and no public listener was added.

## VERIFIED — BGM ownership and audio rate

- The default page no longer starts a browser `<audio>`/WebAudio mirror.  The
  guest Wine/DirectSound path is the sole default owner of BGM playback.
- The browser mirror remains available only as an explicit diagnostic with
  `?webBgmFallback=1`; the four obsolete BGM control buttons were removed.
- The live shell had regressed to accepting only 22050 Hz.  A page request for
  `audioFreq=44100` therefore fell back to the 11025 Hz default and omitted the
  native `-audioFreq` argument, clamping guest output to 11025 Hz.
- Both deployed and canonical shells now accept 44100 as a numeric override
  and forward `-audioFreq 44100`.  The legacy 11025 default remains unchanged
  for unrelated launchers.
- The shell script URL was bumped to `audiofreq44100fix2`.  LAN HTTPS returned
  the new fallback guard, no BGM buttons, and the 44100 forwarding branch.

## VERIFIED — context menu and lean runtime contracts

- `contextmenu` is prevented over the whole visible `#inline` game surface,
  not only the canvas.  Right-button camera input is therefore not consumed by
  the browser menu while the game is visible.
- The Korean shell replacement had also dropped two Gate 5 protections.  The
  initial origin-wide IDBFS populate is again serialized with
  `navigator.locks`, and storage errors still complete the bootstrap callback.
- Normal play no longer appends unbounded native trace text to a hidden DOM
  textarea.  Present and profiler samples still reach their direct metric
  bridges; full trace retention is opt-in with `?debugConsole=1`.

## VERIFIED — Korean runtime identity; delivery acceptance remains open

- The deployed `korean1` WASM contains the scoped Ctrl key synthesis and
  modifier flag.  The literal `vvvv` report is therefore not evidence that the
  deployed file lacks the implementation; it is compatible with a browser
  retaining an older response under the reused `korean1&build=0` URL.
- The default page now selects the immutable `korean2` stem with build id
  `ime-ctrlkey-v2-20260807`.  LAN HTTPS returned both JS and WASM with HTTP 200.
- Source audit also found a deeper boundary: BoxedWine's XIM entry points
  (`XOpenIM`, `XCreateIC`, focus operations, `XmbLookupString`) are absent or
  panic stubs.  Wine's normal committed-text path therefore cannot currently
  be claimed.  Clipboard/Ctrl remains the deployed compatibility path while a
  minimal fake-XIM implementation is built and verified.

## Verification

- `python -m unittest discover -s tools -p "test_*.py"`: **216 passed**.
- `node --check tools/boxedwine_local/assets_d3d9web/boxedwine-shell.js`: pass.
- Live LAN HTTPS: guest-only guard, no BGM buttons, whole-game context guard,
  44100 branch, lean-output bridge, IDBFS lock, korean2 JS/WASM HTTP 200.

## NOT VERIFIED

- One audible guest BGM stream and subjective 44.1 kHz quality require the
  user's next play test.
- Plaza Edit accepting committed Korean text requires the user's next play
  test.  A static/runtime-identity pass is not promoted to input acceptance.
