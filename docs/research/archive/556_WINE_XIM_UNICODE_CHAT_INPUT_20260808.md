> **SUPERSEDED by 557.** The XIM/VK_PACKET experiment did not produce accepted Hangul in Azrok's ANSI Edit control. Production Plaza chat now keeps browser IME text on the host and returns it through the preserved S2C 0x006A path.

# 556. Wine XIM Unicode chat input (2026-08-08)

## Scope

Fix the remaining Plaza Korean-input failure without changing `Azrok.exe`, game data, or the server protocol. The previous route proved UTF-8 reached Wine `xim_set_result_string()`, but the user still observed no Korean text.

## VERIFIED — corrected loss boundary

- #552 proved browser composition -> BoxedWine FIFO -> fake XIC -> `XmbLookupString` -> `XLookupChars` -> Wine `xim_set_result_string()` with 6 UTF-8 bytes for two Hangul syllables.
- Wine 11 `winex11.drv/xim.c` converted those bytes with `ntdll_umbstowcs()`, then used `WINE_IME_POST_UPDATE`. `win32u/imm.c` queues that result and posts `WM_WINE_IME_NOTIFY`; this was the only unverified boundary left.
- The user's test after #555 directly disproved the claim that `C.UTF-8` alone completed the Edit path.

## VERIFIED — implementation and packaging

- `xim_set_result_string()` now keeps the Wine UTF-8 -> UTF-16 conversion but emits each committed UTF-16 unit through Wine's normal `KEYEVENTF_UNICODE` down/up hardware-input path.
- This produces the standard `VK_PACKET`/`WM_CHAR` route and does not use clipboard, Ctrl+V, an Azrok-specific window message, or an original-binary patch.
- The rebuilt 32-bit `winex11.so` was compiled and linked successfully. The stripped artifact SHA-256 is `116B75FED507F726BE0B782A81C9E9683AEEFF562A59B014E3619A416276694B`.
- Immutable root `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim2unicode1.zip` was created from xim1 by replacing exactly `opt/wine/lib/wine/i386-unix/winex11.so`. ZIP SHA-256 is `3EEF7C431B961E5338A2779627B50C13B3C32B87AFEEB9991D5D84E749F67881`.
- LAN HTTPS returned the new root with HTTP 200 and the exact 167,595,714-byte size. Live HTML selected xim2unicode1 by default and retains `imeRootRollback=1` for explicit xim1 rollback.
- A live in-app browser booted the new root into the original character screen and an existing character, then a direct S2C 0x000D transition reached the rendered Plaza/OX area without a client crash.

## VERIFIED — raw Latin leakage removal

- Plaza chat now has one browser text owner. The first Enter enables chat text mode; the next Enter or Escape leaves it.
- While chat text mode is active, printable physical key events are stopped before SDL, and browser `input`/`compositionend` text (ASCII and non-ASCII) alone enters the XIM/Unicode path.
- Enter, Escape, Backspace and navigation keys retain the original SDL path. This removes the duplicate US-layout `l4j10`/`dkssud` stream without suppressing gameplay keys outside chat mode.

## Verification

- Focused static/package/page tests: 40/40 passed.
- Full `tools/test_*.py` suite: 236/236 passed.
- Browser boot, immutable-root load, original character UI, existing-character load, and Plaza render: VERIFIED live.

## NOT VERIFIED

- The in-app automation could not open the Plaza Edit with Enter (the same automation limitation recorded before #556), and it cannot synthesize a real OS Korean IME composition. The final visible Hangul glyph and natural C2S 0x006A from a physical user session remain the acceptance check.
- If the user still sees no Hangul after a full reload on xim2unicode1, the next boundary is `VK_PACKET`/`WM_CHAR` consumption inside the Acknex window procedure; do not return to clipboard or locale-only fixes.
