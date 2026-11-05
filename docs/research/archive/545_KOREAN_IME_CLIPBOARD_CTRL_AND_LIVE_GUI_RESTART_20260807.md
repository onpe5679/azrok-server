> **SUPERSEDED by 549.** 강제 Ctrl+V는 rollback fallback으로만 보존하며, 기본 입력 경로는 Wine XIM result-string 경로로 전환했다. GUI/계정 관리자 재시작 기록은 계속 유효하다.

# 545. Korean IME clipboard/Ctrl path and live account-GUI restart (2026-08-07)

## Scope

Finish the browser-to-Wine Korean text delivery implementation without
patching `Azrok.exe`, and activate the already implemented private-account
manager in the loopback server GUI.

## VERIFIED — browser and BoxedWine implementation

- The page keeps the transparent editable input over the canvas, preserves its
  value while composition is active, and sends committed text only after
  `compositionend`.
- The raw-key suppression condition now checks the page's own `composing`
  boolean in addition to the unreliable browser `event.isComposing` value.
  Thus an IME that reports real Latin keycodes with `isComposing === false`
  cannot leak those key events into SDL while composition is active.
- `boxedwine_paste_text_utf8()` writes the committed UTF-8 text to the host
  clipboard and synthesizes Ctrl+V through the virtual X server.  The scoped
  `g_boxedwineForceControlModifier` flag is enabled before the synthetic keys
  and cleared afterward; `getModifiers()` maps it to
  `NATIVE_CONTROL_MASK`.  This corrects the prior plain-`v` result caused by
  `SDL_GetModState()` reflecting only the physical keyboard.
- The deployed default page selects
  `boxedwine.upstreamjit64fn6inlineabi2korean1` and the ACP949 root
  `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949`.
  The runtime JS exports `_boxedwine_paste_text_utf8`; its JS/WASM files were
  built 30 seconds after the modified input source.  Deployed WASM SHA-256 is
  `DA8946847D70978CE362FEBEDCFD4E2B78963BCC105771F918ED73C24C3D3635`.
- Three focused page contracts passed: classic-script parsing, default
  Korean-runtime/ACP949 selection including the composition guard, and game
  context-menu suppression.  A separate source/deployment contract confirmed
  the forced-Control ordering and deployed paste export.

## VERIFIED — live GUI restart

- The prior loopback core/GUI process was deliberately restarted with the same
  command-line contract after user approval:
  `tools/run_server_only.py --bind 127.0.0.1 --port 9200 --control-port 9300 --content-profile playable --auto-select-existing`.
- The new process listens only on `127.0.0.1:9200` and `127.0.0.1:9300`.
  The 192/Tailscale asset and bridge listeners remain private; no public bind
  was introduced.
- Live `GET http://127.0.0.1:9300/` returned HTTP 200 with the private-account
  panel.  `GET /api/private-accounts` returned schema
  `azrok-private-account-admin-v1`, seven accounts, five automatic slots,
  three bound and two available.  Browser identifiers were redacted and
  password values/hashes were not returned.

## Rejected path

The earlier synthetic-X11 `XLookupString` path is superseded.  Instrumentation
showed `queued=58`, `served=58`, and queue depth zero, but Wine ignored the
returned string and generated `WM_CHAR` from its keycode table.  The clipboard
path reuses Wine's own `XConvertSelection(CLIPBOARD, UTF8_STRING)` and text
conversion instead of trying to bypass that behavior.

## NOT VERIFIED — user interaction boundary

- A human composition and paste into the live Plaza Edit control after this
  final guard change remains user-operated testing.  Codex did not type into
  the game because the user reserved future play tests.
- The required visible acceptance result is one committed Hangul phrase in the
  Plaza chat Edit/control and outgoing chat, with no `dkssud`-style Latin
  leakage.  Static/export/listener checks do not substitute for that result.
