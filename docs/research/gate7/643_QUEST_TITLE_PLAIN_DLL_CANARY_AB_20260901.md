# 643 — Quest-title plain-DLL canary A/B

Date: 2026-09-01 KST

## Scope

첨부된 quest-list 상단 제목의 glyph-edge 깨짐을 확인하기 위해, production fastboot4 앱과 동일한 ZIP에서 `d3d9.dll` 한 파일만 plain build로 바꾼 immutable canary를 실제 playazrok browser session에서 실행했다.

## Candidate identity

| Item | Control | Canary |
|---|---|---|
| app ZIP | `...fastboot4.zip` | `...fastboot4questtitleplain1.zip` |
| ZIP member difference | baseline | `d3d9.dll` 하나 |
| control DLL | 24,576 B, SHA-256 `2de7d207...487194d9`, recycle on | — |
| canary DLL | — | 23,040 B, SHA-256 `cfa6d289...d5e7f`, recycle off |
| canary ZIP SHA-256 | — | `22705cfadf7ce25f0bde4a3426e1ee5d1bf3fbe36b51e03057e836f51b5eeb76` |

The canary is published as a distinct app asset only. Production/default app, r10 JS/Wasm/cache, and existing account state remain unchanged.

## Actual browser A/B

### Invalid first attempt — excluded

An initial direct URL lacked the server-list-issued `instance`, account, and launcher fields. It entered a heartbeat/draw loop without a valid game session and is excluded from visual comparison. A custom `build=questtitle_plain1` also failed the r10 runtime-build-token contract; preserving the r10 token fixed that URL contract.

### Valid actual-ticket attempt

- **VERIFIED:** the browser opened `azrok_server_list.html`, obtained a private account-bound ticket, and navigated with exact r10 runtime/cache identity plus `run_azrok_account.bat`.
- **VERIFIED control:** recycle-on fastboot4 reached the original character-selection screen, Korean `캐릭터 선택`, scene art, and FPS render loop with no browser console errors.
- **VERIFIED canary:** changing only the app ZIP to the plain-DLL canary while retaining the same account-bound URL, launcher, root, r10 runtime/cache, and WSS bridge reached the original character-selection screen and rendered its Korean title/art. No console error was produced in this valid attempt.
- **NOT VERIFIED:** the quest panel was not reached. The original character-create control did not transition in this automated pass, so the observed upper quest-title defect cannot be compared or declared fixed.

## Interpretation

The historical #600 generic-DLL fastboot5 boot regression remains a direct result for that package generation. It does **not** prove the current r10 ticketed canary cannot boot: the current valid-ticket canary did boot to character selection. Conversely, character-selection text is insufficient evidence for the quest-list AA path. The title fix remains unproven.

## Next direct gate

Reach a fresh character's PatHouse quest panel using the same server-list issuance path, capture control and canary at identical viewport/scene, and compare the upper row title against the lower body. If the canary fixes it, then promote only after a fresh re-entry and full title panel visual acceptance. If it does not, capture the relevant texture handle and sampler/blend/alpha states with `diagnostics=1` and modify that proven subpath rather than changing the global DLL mode.
