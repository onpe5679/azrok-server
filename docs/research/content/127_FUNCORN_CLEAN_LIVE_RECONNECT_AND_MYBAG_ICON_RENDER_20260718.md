# FunCorn clean live, 재접속 영속화, MyBag 아이콘 렌더 분리

Date: 2026-07-18

## 결론

- **VERIFIED (clean live, injected real consumer):** 격리 namespace `qa_funcorn_clean_20260718`에서 FunCorn950, food1001=1, kind0 row로 시작해 실제 MyBag consumer `0x189/type2`를 1회 실행했습니다. wire는 `0014 -> 0008 -> 0012 -> 0011 -> 0007`, ACK는 `S2C0005 subtype12 / 990`이었습니다.
- **VERIFIED (natural user live):** 별도 namespace `qa_funcorn_icon_20260718`에서 사용자가 화면의 첫 번째 빈 슬롯을 실제 마우스로 클릭했습니다. 같은 wire와 ACK가 재현됐고 UI `소지금`이 즉시 `950 -> 990`으로 바뀌었습니다. 따라서 슬롯은 blank처럼 보여도 실제 hit target/소비 경로는 정상입니다.
- **VERIFIED (server+client restart):** 첫 격리 서버와 클라이언트를 모두 종료한 뒤 같은 namespace로 재기동했습니다. `S2C0005 subtype0`은 FunCorn990, 자연 C2S0008은 food sum0이었고 화면도 `소지금 990`이었습니다. canonical revision4, 완료키 1개, journal 4행은 변하지 않아 duplicate +40이 없었습니다.
- **VERIFIED (not a protocol gap):** S2C0007 음식 수량 복원, local item1001/tooltip 매핑, local `Refri_1.wis`, `View_Cook -> SetBmp`, C2S0014 소비까지 모두 살아 있습니다. 아이콘 body를 위한 별도 server opcode는 없습니다.
- **VERIFIED (UI symptom only):** `Refri_1.wis`를 독립 decode하면 정상 햄버거 그림입니다. 런타임 `View_Cook`은 15개 fallback BMAP 설정 뒤 보유 item용 추가 SetBmp까지 총 16회 실행합니다. 그런데 슬롯 body만 blank입니다.
- **REFUTED:** coincident tooltip/condition layer가 자연 클릭을 영구 차단한다는 가설은 사용자 자연 클릭 성공으로 폐기합니다. 자동화의 즉시 단발 클릭 실패는 hover/input-frame 부족 가능성이 있으나 **INFERRED**입니다.
- **NOT VERIFIED:** 2011년 원본 서비스 환경에서도 같은 blank 아이콘이 있었는지, 현대 Windows/GPU의 Acknex/DirectX 호환성 문제인지 원본 클라이언트 자체 표시 버그인지는 구분하지 못했습니다.

## 1. clean live A — 실제 consumer와 atomic reward

- namespace: `qa_funcorn_clean_20260718`
- server/client: port9217/control9310, PID102640/PID104564
- capture: `B:\Azrok_Captures\runs\20260718T211836_102640_b002950c\packets.jsonl`
- direct consumer artifact: `artifacts/dynamic-analysis/FUNCORN_QA_DIRECT_ITEM_189.txt`

| capture seq | 방향/opcode | payload/결과 |
|---:|---|---|
| 255 | C2S0014 | `e903`, food1001 |
| 256 | C2S0008 | exact41, food sum0 |
| 257 | C2S0012 | `2800000002`, amount40/channel2 |
| 258 | C2S0011 | kindFF + stale aux/value |
| 259 | S2C0005 | `0012de030000`, result0/subtype12/FunCorn990 |
| 260 | C2S0007 | exact196 snapshot |

Durable transactions:

1. inventory snapshot: revision1→2, food1→0
2. reward+row retire: revision2→3, FunCorn950→990, completed key 추가
3. state snapshot: revision3→4

최종 canonical:

- SHA256 `866e01ee4df412f3cee697f0024f88a0afca5e5d64d586274c168ddc09cbc019`
- row1 `{kind:255, aux:255, value:0}`
- completed `g1:r1:k0:a1001:c40`
- journal 마지막 `sha256_after`와 disk/API SHA 일치

## 2. 실제 서버·클라이언트 재기동

- restart capture: `B:\Azrok_Captures\runs\20260718T214256_66416_1486862f\packets.jsonl`
- S2C0007 exact472는 privacy policy에 따라 hash-only입니다.
- 뒤이은 S2C0005 `0000de030000`이 post-load FunCorn990을 확인합니다.
- 자연 C2S0008 exact41은 food/ingredient quantity sum0입니다.
- screenshot: `artifacts/dynamic-analysis/FUNCORN_QA_RECONNECT_AFTER.png`
- restart 후 canonical revision4/SHA/journal 4행은 불변입니다.

따라서 disk write만이 아니라 새 서버가 disk를 읽어 새 클라이언트 model/UI까지 990을 복원한 것이 VERIFIED입니다.

## 3. clean live B — 사용자 자연 클릭

- namespace: `qa_funcorn_icon_20260718`
- capture: `B:\Azrok_Captures\runs\20260718T215018_108820_3f54c45a\packets.jsonl`
- 사용자가 화면의 첫 번째 blank 슬롯을 직접 클릭했습니다.

| capture seq | 방향/opcode | payload/결과 |
|---:|---|---|
| 135 | C2S0014 | `e903` |
| 136 | C2S0008 | food sum0 |
| 137 | C2S0012 | `2800000002` |
| 138 | C2S0011 | 완료 row kindFF |
| 139 | S2C0005 | `0012de030000`, FunCorn990 |
| 140 | C2S0007 | exact196 |

화면 증거 `artifacts/dynamic-analysis/FUNCORN_ICON_QA_NATURAL_USER_CLICK_SUCCESS.png`는 소지금990을 보여 줍니다. canonical도 revision4/FunCorn990/food0/normalized row/completed key로 일치합니다.

## 4. MyBag blank 아이콘의 경계

### 정적/자산 근거

- `FUN_005CEE90`: `Refri_0..32.wis`를 로드합니다.
- `FUN_005D0730`: 보유 food 목록을 slot `0x189..0x197`에 매핑하고 BMAP을 지정합니다.
- Naver ILK의 구조 동형 이름은 `CPopupMyBag::View_Cook()`, `CPopupMyBag::CheckMyBagItem(int)`, `CPopupMyBag::CheckMyBagItemToolTip(int,int)`입니다. 현 Plaza 주소 직접 심볼이 아니므로 주소→이름은 **INFERRED (cross-build structural match)**입니다.
- `Refri_1.wis` 독립 decode 결과는 33x33 정상 햄버거 그림입니다.

### 런타임 근거

`artifacts/dynamic-analysis/FUNCORN_ICON_QA_SETBMP_TRACE_3.txt`:

- `myBagSetBmpById` 총 16회: 15개 fallback + 보유 item 추가 설정
- slot0/button393 fallback BMAP 요청과 `CGameButton` normal/hover/down 3필드의 동일 포인터 갱신을 직접 관측
- 동시에 UI는 15개 slot body를 blank로 표시
- hover tooltip과 사용자 click/consume는 정상

그러므로 서버 inventory/프로토콜, item ID, tooltip, hit target, consume producer는 결함 범위에서 제외됩니다. 남는 범위는 client BMAP 최종 선택/alpha/draw ordering 또는 구형 엔진 렌더 호환성입니다.

## 5. 자동화와 capture 보강

- Windows 다중 서버에서 `os.kill(pid, 0)`가 `WinError87/SystemError`를 내던 capture liveness probe를 query-only `OpenProcess/GetExitCodeProcess`로 교체했습니다.
- `tools/prepare_funcorn_clean_live_qa.py`는 `--namespace`를 받아 기존 canonical overwrite를 거부하는 격리 fixture로 일반화했습니다.
- `tools/auto_azrok_ui.py`와 elevated request boundary에 hover용 `move_rel`을 추가했습니다.
- Frida observer는 MyBag `SetBmp`를 read-only 계측합니다. 소비를 위한 `0x189/type2` 주입은 clean live A의 진단용이며 일반 플레이 경로에 필요하지 않습니다.

## 판정

Quest FunCorn layer와 재접속 영속화는 종료합니다. MyBag 아이콘은 플레이 차단 갭이 아니라 표시-only 호환성 조사 항목입니다. protocol/server에 아이콘용 synthetic opcode나 client binary patch를 추가하지 않습니다.
