# 565. Dynamic accounts, recovery codes, and account-bound tickets (2026-08-26)

> **PARTIALLY SUPERSEDED by 580.** 계정·티켓·동적 launcher 설계는 유효하지만,
> 매 표시마다 회전하고 한 번 가져오면 소비되던 복구 코드 정책은 계정별 안정
> 코드와 명시적 재생성 정책으로 교체되었습니다.

> **PARTIALLY SUPERSEDED by 567.** The account, recovery, and ticket design remains
> valid, but `dynamicaccounts1` did not boot the original client: Wine 11
> `findstr` rejected every generated account before `Azrok.exe`. Document 567
> replaces only that launcher generation and records live original-client proof.

## Scope

Replace the temporary `player2`--`player6` browser pool and scrypt password UI
with unlimited server-generated accounts, password-free device continuity, and
one-time recovery-code transfer. Preserve the original four-character roster
per account and keep all network listeners private.

## VERIFIED — implementation and automated contracts

- `PrivateAccountRegistry` schema v2 eagerly migrates v1 browser bindings,
  preserves the account IDs, and removes the obsolete password-hash field from
  the durable JSON. New browsers receive distinct 13-byte-or-shorter
  `[A-Za-z0-9_]` account IDs; there is no five-slot launcher pool.
- A browser can rotate a one-time `azr1-...` recovery code. The registry stores
  only `sha256$<digest>`, consumes the code on one successful import, and rejects
  reuse. The loopback GUI can issue the same code for an operator-selected
  account and still shows only one-way browser references.
- Admission ticket v2 signs expiry, browser ID, and account ID. The WSS bridge
  buffers the first original-client `C2S 0x0000[106B]` frame and opens the core
  connection only when its account field equals the signed ticket account.
  A transport URL can therefore no longer select an arbitrary known account.
- The immutable app
  `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts1.zip`
  adds only `run_azrok_account.bat`. Existing ZIP entries and the original game
  binary are byte-identical to utf8ime2. The launcher accepts only the
  server-generated safe account argument and keeps native D3D9, `+seh`,
  `C.UTF-8`, and the existing guest BGM route.
- The landing page automatically creates a new account for a new browser, sends
  the signed account as the BoxedWine program argument, and offers recovery-code
  import instead of account/password login. The game page can issue and copy a
  replacement one-time recovery code; password and copied transport-code UI are
  removed.
- The original account model remains separate: `azrok_server.py` still builds
  four lobby character records per account and canonical save keys remain
  account + slot + character name. Document 564 implements `C2S 0x0002` logout
  so a user can return to that roster and select another character.
- Focused automated verification: private admission/control/page contracts and
  server logout contracts pass. The dynamic-app test proves every source ZIP
  entry is unchanged and the WSS test proves fragmented login buffering plus
  mismatched-account rejection.

## VERIFIED — safety boundaries

- Core `9200` and GUI `9300` remain loopback-only.
- Browser HTTPS/WSS binds are still limited by `parse_private_ipv4_bind` and
  `is_private_client` to loopback, RFC1918, or Tailscale/CGNAT addresses.
- A configured access secret accepts v2 account-bound tickets only; legacy
  transport tokens are not accepted by that path.
- Recovery codes are bearer credentials. The GUI shows a newly issued code only
  until it is hidden/refreshed, and issuing another code invalidates the prior
  one.

## VERIFIED — controlled live restart (2026-08-26 23:37--23:40 KST)

- Fresh listeners: core/GUI `127.0.0.1:9200/9300`, LAN
  `<lan-ip>:8765/9201`, and Tailscale `<tailscale-ip>:8765/9201`.
  No wildcard or public-address listener exists.
- LAN and Tailscale HTTPS roots, loopback GUI, and the immutable dynamic app
  returned HTTP 200. The migrated live registry is schema v2 with seven legacy
  accounts, nine preserved browser bindings, and no `passwords` field.
- Live `/api/private-session` returned a v2 ticket whose signed account was
  `player2`; its account claim and launcher matched the preserved binding.
- A real TLS WebSocket sent the login header fragmented across frames. Matching
  `player2` reached the core and received 405 bytes; a `player3` login using the
  same ticket was rejected before TCP connect with close code 1008 and reason
  `private account claim rejected`.
- Live recovery-code issuance returned the `azr1-` format and the plaintext was
  absent from the registry file. The removed password endpoint returns 404.
- Headless Edge screenshots visually confirmed the loopback GUI's dynamic
  account panel (`7 accounts`, no quantity limit, recovery issue and device
  release controls) and the LAN recovery-import form. Screenshots:
  `logs/gui_accounts_v2_full.png`, `logs/recovery_page_v2.png`.
- Full `tools/test_*.py` discovery passed **254/254** after the restart build.

## NOT VERIFIED

- Physical phone/second-PC recovery import and subsequent character selection.
- Live original-client logout to the four-slot screen and re-entry using another
  slot. Static client analysis and automated server contracts are verified in
  document 564; physical UI acceptance remains the user test gate.
- Sustained high-volume account creation. The fixed artificial limit is gone,
  but disk/resource load is not claimed to be unbounded in the mathematical
  sense.
