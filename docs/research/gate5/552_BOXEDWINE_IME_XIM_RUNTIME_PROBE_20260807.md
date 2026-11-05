# 552. BoxedWine IME XIM runtime probe (2026-08-07)

## Scope

사용자가 허용한 Plaza 실브라우저 관찰에서 브라우저 조합 완료부터 공용 UTF-8 FIFO 소비까지는 통과했지만 Azrok Edit에는 한글이 나타나지 않았다. 기존 `boxedwine_ime_stat()`은 `XLookupString`과 `XmbLookupString`이 같은 `consumeTextInput()`을 호출해 어느 경로가 소비했는지 구분하지 못한다. 원본 게임 바이너리·서버 프로토콜·페이지 HTML은 수정하지 않고, fake-XIM 호출과 반환을 분리하는 immutable debug runtime을 추가했다.

## VERIFIED — 기존 korean5 라이브 손실 경계

Plaza player5에서 hidden input에 `한글` 2 scalar를 넣은 전후 공용 계측은 다음과 같다.

- 전: `queued=0, lookup=2, empty=2, served=0`
- 주입 직후: `queued=2, depth=2`
- 정착 후: `queued=2, lookup=8, badType=4, empty=2, served=2, depth=0`

따라서 브라우저 commit → `_boxedwine_inject_text_utf8` → FIFO queue → synthetic key lookup → scalar 2개 consume은 실측 통과했다. 이 수치만으로는 plain `XLookupString`이 소비했는지 XIC의 `XmbLookupString`이 소비했는지 알 수 없다.

## VERIFIED — 분리 계측 계약

`BOXEDWINE_IME_RUNTIME_DEBUG` 전용 빌드에서 다음 38개 U32 word를 `XServer` 인스턴스에 보관한다. `XServer`는 heap에 생성되므로 probe word가 WASM 정적 데이터와 currentabi1 relocation base를 이동시키지 않는다.

| index | 의미 |
|---:|---|
| 0–2 | browser inject calls, UTF-8 bytes, queued scalars |
| 3–7 | synthetic press/release received, focused X11 route, no-focus |
| 8–9 | `XOpenIM` calls/successes |
| 10–11 | `XGetIMValues` calls/successes |
| 12–13 | `XCreateIC` calls/successes |
| 14–20 | set/unset focus, destroy/close, locale modifier, locale/display queries |
| 21 | `XFilterEvent` calls |
| 22 | synthetic key의 plain `XLookupString` calls |
| 23–24 | all `XmbLookupString` calls / synthetic-key calls |
| 25–28 | `XLookupChars` results, returned-byte total, last bytes, last status |
| 29–37 | FIFO queued/lookups/bad-type/empty/served/repeat/depth/max-depth/drops |

JS/WASM 공개 계약:

- `boxedwine_ime_debug_abi_version()` = `1`
- `boxedwine_ime_debug_word_count()` = `38`
- `boxedwine_ime_debug_stat(index)`
- `boxedwine_ime_debug_copy_snapshot(output, word_count)`
- `boxedwine_ime_debug_reset()`

debug macro가 없는 production build에는 이 필드와 export가 포함되지 않는다. 기존 `boxedwine_ime_stat()`과 clipboard fallback은 보존했다.

## VERIFIED — immutable build, ABI, serving identity

- runtime stem: `boxedwine.upstreamjit64fn6inlineabi2korean5imedebug1`
- JS: 329,058 bytes, SHA-256 `A2896C2AF1D0A79F72816E67F422A61AA03D2583EFAC1FF2B17A5133C6BF4B6F`
- WASM: 3,055,288 bytes, SHA-256 `B63F75EC528D5A64905BA823FFB2BE2A8034CC165AA520405D731BD21DE833CB`
- raw WASM Node import-stub direct export: relocation map `12968408`, capacity `262144`, IME ABI `1`, word count `38`, initial stat 0=`0`
- LAN `<lan-ip>:8765`와 Tailscale `<tailscale-ip>:8765`가 위 JS/WASM과 같은 길이·해시를 제공했다.
- `index_d3d9web_pathouse.html`은 이 트랙에서 수정하지 않았다. runtime은 URL의 `runtimeStem=`으로만 선택한다.
- `python -m unittest tools.test_boxedwine_xim_contract`: 10/10 pass.
- `python -m unittest discover -s tools -p "test_*.py"`: 230/230 pass.

## 다음 라이브 판정

Plaza 진입 뒤 commit 전 baseline snapshot을 읽고, 한글 1회 commit 후 같은 snapshot의 delta를 비교한다. `XOpenIM/XCreateIC`는 부팅 중 한 번만 일어날 수 있으므로 첫 판정에서는 reset하지 않는다. reset export는 반복 주입을 격리할 때만 사용한다.

- `22 > 0`, `24 == 0`: Wine이 XIC/Xmb 경로를 만들지 못하고 plain `XLookupString`으로 소비한다. XIM 생성/선택 계약이 원인이다.
- `24 > 0`, `25 > 0`, last status `2`, returned bytes `> 0`: fake-XIM 반환은 성공했다. 손실은 Wine의 `xim_set_result_string` 이후 또는 Azrok Edit ANSI/ACP 변환 이후다.
- `0 == 0`: 페이지에서 debug runtime의 inject export를 호출하지 않은 것이다.
- `3/4 > 0`인데 `5/6 == 0` 또는 no-focus 증가: synthetic key가 focused X11 window에 도달하지 못했다.

## VERIFIED — Plaza live 판정 결과 (2026-08-08)

player5 Plaza baseline 38 word:

`[0,0,0,0,0,0,0,0,3,3,3,3,1,1,1,0,0,0,2,0,0,156,2,0,0,0,0,0,0,0,2,0,2,0,0,0,0,0]`

hidden input `한글` 정착 후:

`[1,6,2,2,2,2,2,0,3,3,3,3,1,1,1,0,0,0,2,0,0,161,6,2,2,2,6,3,2,2,8,4,2,2,0,0,2,0]`

- XIM/XIC는 생성됐다: open 3/3, get-values 3/3, create-IC 1/1, focus 1.
- 한글 2 scalar 모두 Xmb synthetic call 2, `XLookupChars` 2로 반환됐다.
- 반환 byte total delta 6, last bytes 3, last status 2다.
- FIFO도 served delta 2, depth 0으로 완전히 비었다.

따라서 fake-XIM까지의 손실 가설은 기각됐다. Wine 11 `X11DRV_KeyEvent`는 status 2에서 `xim_set_result_string()`을 호출한 뒤 hardware-input 경로 전에 반환하므로, 남은 경계는 그 함수의 Unix-byte→UTF-16 변환과 IME update/Azrok Edit 수용이다. locale 변환 A/B는 #553으로 이어진다.

## NOT VERIFIED

- `XLookupChars`가 성공한 뒤 Wine/Azrok Edit에 들어가는 마지막 구간은 아직 실측되지 않았다.
- 이 문서는 한글 Edit 성공을 주장하지 않는다.
