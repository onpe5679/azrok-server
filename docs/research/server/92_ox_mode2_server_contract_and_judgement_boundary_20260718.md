# OX mode-2 서버 계약 + 판정 경계 (2026-07-18)

> **PARTIALLY SUPERSEDED by 96 (94 실측 포함).** §2, §4~§7의 C→S 답안·side 방향·cell 판정은 정정되었습니다. 답안은 dedicated `00CA` 22B의 side이며 `00C9` 1B는 teardown/leave입니다. side0=음의 X/왼쪽, side1=양의 X/오른쪽이고 0066/0067은 일반 이동 telemetry입니다. S→C 디스패치·CE/CB 계약은 계속 유효합니다.

정적 분석 전용 기록입니다. `Azrok_original.exe`의 `CGameOXQuiz` vtable, mode-2 수신
디스패처, OX UI/결과 핸들러와 `Data/Space/OXquiz/OXQuiz.wmb`의 배치 경계를 직접
대조했습니다. 동적 클라이언트, x32dbg, Frida는 사용하지 않았습니다.

표기: **VERIFIED**=디컴파일 본문 또는 WMB 원자료 직접 확인,
**INFERRED**=직접 근거를 조합한 구현 정책, **NOT VERIFIED**=원본 서버에만 있던 정보.

## 1. 핵심 정정: OX에는 mode-2 전용 서버 프로토콜이 있다

`CGameOXQuiz::vftable`은 `0x006AE904`이고 마지막 슬롯은
`thunk_FUN_00605EE0`입니다. `FUN_00605EE0`은 mode-2 S→C 디스패처이며
다음 opcode를 직접 소비합니다.

따라서 75/87의 "OX 전용 opcode 0개"는 **state-1 표에 한정하면 맞지만 전체 OX
프로토콜 결론으로는 틀렸습니다.** OX 입장 뒤 `mode=2`에서는 `0x00C8..0x00D4`가
전용 라운드/로스터/질문/판정 프로토콜입니다. 일반 `0x0066/0x0067`은 답안 위치
전송에 재사용됩니다.

## 2. C→S: 클라이언트가 실제로 보내는 OX 입력 (VERIFIED)

| opcode | payload | 직접 근거 | 서버 계약 |
|---|---:|---|---|
| `0x00C8` | **0B** | `FUN_005FF1E0` → `FUN_005ABD50(200,NULL,0)` | OX 씬 로드 완료/참가 요청. exact 0B만 허용 |
| `0x0066` | **22B** | `FUN_0061B510` → `FUN_005AB7B0` | 이동 시작. `[currentCell:u8][curX:i32][curY:i32][dstX:i32][dstY:i32][duration:i32][pathFlag:u8]` |
| `0x0067` | **15B** | `FUN_00619900` → `FUN_005AB830` | 도착 commit. `[cell:u8][x:i32][y:i32][action:u32][angle:u16]` |

OX 클래스 코드 범위 `0x005FF000..0x00607800`의 직접 송신 호출을 전수 확인하면
전용 송신은 `0x00C8` 한 번뿐입니다. 질문 popup `FUN_005F6180`은 버튼 큐 결과를
폐기합니다. 답은 버튼 opcode가 아니라 일반 이동 `0066/0067`로 제출됩니다.

`0066.byte0`은 88의 114건 wire 실측처럼 목적지가 아니라 `curX/curY`의 cell입니다.
따라서 서버는 `dstX/dstY`를 마감 답으로 선확정하면 안 됩니다.

## 3. S→C mode-2 전체 디스패치 (VERIFIED 구조)

`FUN_00605EE0`의 switch와 각 callee의 실제 field read/write를 기준으로 정리했습니다.
"exact"는 핸들러가 읽는 고정 구조 또는 `len/N` 반복 단위입니다.

| opcode | payload 계약 | 핸들러 | 클라이언트 상태 변화 |
|---|---|---|---|
| `0x00C8` | **14B**: `[result:u8][levelMarker:u8][readyMs:u32][x:i32][y:i32]` | `FUN_00606B90` | `result==0`이면 self 좌표/로스터/UI를 만들고 mode-2 활성. 비0이면 즉시 OX 종료 |
| `0x00C9` | **N×32B** remote records | `FUN_00606EF0` | remote actor upsert + 좌표 적용 |
| `0x00CA` | **4B** actor id | dispatcher → `FUN_005F80F0` 등 | remote actor 제거 |
| `0x00CB` | **N×4B** actor-id 목록 | `FUN_006071B0` | 목록의 각 actor에 action `0x2C`; self 포함 시 result state=2. **패자 목록** |
| `0x00CC` | **0B** | `FUN_00607670` → `FUN_005F91B0` | ready/start countdown UI 시작 |
| `0x00CD` | **N×4B** (값은 읽지 않고 count만 사용) | `FUN_00607530` | 최종 result state=3, count 표시, 종료 지연 시작 |
| `0x00CE` | **131B(0x83)** question record | `FUN_006069A0` | 질문/정답 side/난이도 표시, 이동 허용, 이전 result timer 해제 |
| `0x00CF` | NUL-terminated text | `FUN_00607120` | type-3 질문/공지 변형 표시 |
| `0x00D0` | **24B** actor-state record | `FUN_00606E20` | 다른 actor 좌표 또는 0068형 상태 적용 |
| `0x00D1` | 없음 | switch에 case 없음 | 보내지 말 것 |
| `0x00D2` | **0B** | `FUN_00602830` | mode0 복귀 + Plaza room `0x6E` enqueue |
| `0x00D3` | **4B** `[u16,u16]` | `FUN_00607720` | OX UI 카운터 두 값 저장 |
| `0x00D4` | **0B** | `FUN_006076F0` | 다음 tick에 OX 종료하도록 flag 설정 |

### C9 32B remote record

`FUN_00606EF0`이 직접 읽는 레이아웃입니다.

| offset | size | 의미 |
|---:|---:|---|
| `+0x00` | 1 | level/roster marker (`FUN_005F55F0`의 표시 index) |
| `+0x01` | 4 | actor id |
| `+0x05` | 1 | actor descriptor byte 0 |
| `+0x06` | 1 | actor descriptor byte 1 |
| `+0x07` | 13 | NUL-padded name |
| `+0x14` | 4 | appearance bytes |
| `+0x18` | 4 | x |
| `+0x1C` | 4 | y |

## 4. CE 질문 레코드와 정답 side (VERIFIED)

`FUN_006069A0`의 정확한 read:

| offset | size | 의미 | 소비처 |
|---:|---:|---|---|
| `+0x00` | 128 | NUL-terminated 질문 텍스트 버퍼 | `FUN_005F6590` |
| `+0x80` | 1 | 질문 표시 type/prefix(1/2/3/기타) | `FUN_005F6590(text,type)` |
| `+0x81` | 1 | **정답 side code** | `CGameOXQuiz+0x7C`에 저장 |
| `+0x82` | 1 | 별/난이도 표시 개수 | `FUN_005F62A0` |

`+0x81`은 단순 UI 장식 추정이 아닙니다. `FUN_006071B0`이 CB 패자 목록을 처리할 때
같은 `this+0x7C`를 읽어 정답 side 결과 이펙트와 표시 위치를 선택합니다.

- `sideCode==0` → `FUN_00605CE0(1)` → result effect world x=`+359`
- `sideCode!=0` → `FUN_00605CE0(0)` → result effect world x=`-369`

따라서 **code 0은 양의 X 쪽, code 1은 음의 X 쪽**이라는 클라이언트 visual-side
매핑은 VERIFIED입니다. 자산 index `OX0.../OX1...` 및 O=0 관례를 보면
`0=O, 1=X`가 강한 INFERRED이지만, 글자 자체의 런타임 표시는 아직 직접 실측하지
않았으므로 이 이름 라벨은 VERIFIED로 올리지 않습니다.

## 5. side→cell 후보를 WMB 경계로 좁힘

`OXQuiz.wmb` header의 직접 경계는 다음과 같습니다.

```text
x = -2205 .. +2205
y = -2214 .. +2214
```

클라이언트 cell 공식은
`((y+9000)/3000) + ((x+9000)/3000)*6`입니다. 이 경계 전체는 x/y 각각
bin 2(음수) 또는 bin 3(0 이상)에만 들어갑니다.

| visual side | WMB x 범위 | 가능한 grid cells |
|---|---:|---|
| side code 0 | `x >= 0` | **20, 21** |
| side code 1 | `x < 0` | **14, 15** |

여기서 code→X 부호는 VERIFIED이고, WMB 경계→cell 산술도 VERIFIED입니다.
그러나 실제 원본 서버가 경계선/장외/충돌불가 영역을 어떤 polygon으로 잘랐는지는
클라이언트 바이너리에 없습니다. 따라서 서버 기본 후보는 위 집합으로 둘 수 있지만
**정식 판정 테이블은 설정 가능**해야 하며 활성 라운드 A/B 실측 전에는 INFERRED입니다.

## 6. 마감 timestamp와 current/arrival 우선순위: 클라이언트에는 없다

OX 클라이언트는 정답을 계산하지 않습니다.

1. CE가 질문과 정답 side byte를 표시합니다.
2. 클라이언트는 위치를 0066/0067로 보고합니다.
3. **서버가 판정한 뒤 CB actor-id 패자 목록을 보냅니다.**
4. 클라이언트는 CB 목록을 그대로 `oxlose` action `0x2C`로 적용합니다.

`FUN_006071B0`의 `GetTickCount()` write(`CGameOXQuiz+0x77`)는 판정 시각이 아니라
CB 결과를 받은 뒤 결과 UI를 유지하는 시작점입니다. `FUN_005FF5B0`은 그로부터
`0x1963`ms(6499ms)가 지나면 다음 단계/퇴장을 실행합니다. CE와 movement 경로 어디에도
client-side cutoff timestamp 또는 좌표-vs-answer 비교가 없습니다.

따라서 아래는 **NOT VERIFIED(original-server-only)**입니다.

- deadline과 같은 tick에 들어온 packet의 포함/제외 규칙
- 0066 current snapshot과 0067 arrival이 경쟁할 때 원본 서버의 tie-break
- 장외/중앙선/이동중 actor의 원본 처리

## 7. 구현 가능한 최소 OX 라운드 state machine

아래는 위 wire 계약을 지키면서 불명확한 부분을 서버 정책으로 격리하는 최소 구현안입니다.

1. **ENTER**: Plaza에서 OX 입장 승인 후 C→S C8 exact0을 받습니다. 소켓을 별도 OX room에
   가입시키고 S→C C8(14B)을 보냅니다. 기존 참가자는 C9 32B records로 동기화합니다.
2. **READY**: S→C CC를 보내 countdown UI를 시작합니다. 질문 전 movement는 저장하되 답으로
   채택하지 않습니다.
3. **QUESTION_OPEN**: 서버가 `question[128], type, correctSide, stars`를 고정하고 CE 131B를
   broadcast합니다. `round_open_monotonic`, `deadline_monotonic`, `round_generation`을 저장합니다.
4. **MOVE**: exact 0066/0067만 검증합니다. 0066은 claimed cell이 `cell(curX,curY)`와 같아야
   하며 destination은 답으로 쓰지 않습니다. 0067은 `cell(x,y)` 일치 시 arrival을 최신
   권위 위치로 승격합니다.
5. **CLOSE**: 단일 lock 안에서 round를 closed로 바꾸고 deadline 이후 packet을 다음 round에도
   재사용하지 않습니다. 구현 정책은 `deadline 이전 마지막 valid current/arrival event`를
   사용하고 동일 timestamp는 server receive sequence로 결정합니다(INFERRED policy).
6. **JUDGE**: side0 기본 `{20,21}`, side1 기본 `{14,15}`와 비교합니다. 다른 cell/무응답은
   fail-closed loser입니다. 패자 actor ids를 CB의 N×4B payload로 broadcast합니다.
7. **NEXT/FINISH**: 생존자가 남으면 다음 CE입니다. 정상 final은 CD만, 강제 종료는
   D2 또는 D4 하나만 보냅니다. 세 경로 모두 클라이언트 내부에서 C9 teardown으로
   수렴합니다. C9 수신 뒤 서버는 000D calibration으로 Plaza 복귀를 이어갑니다.
   D0는 remote actor 24B 상태 갱신, D3는 UI counter 갱신에만 사용합니다.

### 반드시 fail-closed로 둘 지점

- CE는 정확히 0x83B, C8/CC/D2/D4는 정확히 0B가 아니면 전송 금지
- C9는 32B 배수, CB/CD는 4B 배수, D0는 24B, D3는 4B가 아니면 전송 금지
- question string은 128B 안에서 NUL 종료; CP949 변환 실패 문자열은 거부
- round generation이 다른 늦은 0066/0067은 무시
- side table 밖 cell, 중앙/장외, 마지막 권위 위치가 없는 참가자는 loser
- 패자 목록은 현재 OX room의 actor id만 허용

## 8. 서버 코드 반영 경계

이 조사에서는 실행 중인 동적 재시작 트랙과 충돌하지 않도록 `azrok_server.py`를 수정하지
않았습니다. wire builder/validator와 라운드 state machine을 구현할 근거는 확보됐지만,
실제 자동 진입을 켜기 전에는 다음 두 값을 설정/동적 확인해야 합니다.

1. `side code 0/1`의 화면 글자 라벨(O/X) — 기본은 `0=O,1=X` INFERRED
2. side cell 기본 `{20,21}/{14,15}`의 활성 라운드 실측

핵심 보존 계약은 이미 확정됐습니다. **정답은 CE+0x81, 판정 결과는 CB 패자 actor-id
목록이며, 클라이언트는 마감 판정을 하지 않습니다.**

Related: 75, 82, 84, 87, 88, 90, `world/70_scene_map_and_plaza_hansol_correction_20260717.md`.

## 9. 96 정정 요약

이 문서의 과거 구현 지침 중 다음은 더 이상 사용하면 안 됩니다.

- `0066/0067` cell을 OX 답안으로 판정하지 않습니다.
- `side0={20,21}`, `side1={14,15}` 판정표를 사용하지 않습니다.
- dedicated C→S `CA`의 `side`를 generation/deadline 안에서 직접 판정합니다.
- side geometry 표기는 `side0={14,15}`(음의 X/왼쪽),
  `side1={20,21}`(양의 X/오른쪽)이며 진단용일 뿐 판정 권위가 아닙니다.
- C→S C9는 CB loser/CD final/D2/D4가 이미 exit 경로에 진입한 뒤 보내는 통지입니다.
  membership을 즉시 제거하고 `000D[00]` calibration을 시작합니다. 상세는 97입니다.
