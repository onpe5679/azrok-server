# 529 게이트5 — 브라우저 클라이언트가 광장에 진입했다 (2026-07-30)

날짜: 2026-07-30
**이 카드는 #476 과 #507 의 핵심 블로커를 뒤집는다.**
선행: #528(정지·부팅 수정), #512(좌표 수정 + inputProbe), #476, #507, 네이티브 실증(2026-07-17)
원본 실행파일·게임 자산·런타임 바이너리 무수정.

## 1. 뒤집힌 기록

| 문서 | 그때의 기록 | 지금 |
|---|---|---|
| #476 | "브라우저 입력은 C2S `0x0066`/`0x0067`/`0x0019` 를 **전혀 만들지 않는다**. 계속되는 C2S 는 하트비트뿐" | `0x0066`·`0x0067` **다수 관측** |
| #507 | `plaza_clients=0`, `peer_count=0`, `visible_remote_actor_count=0` | 클라이언트가 **광장에 서 있다** |

## 2. 증거 (VERIFIED)

### 패킷 (서버 로그, `logs/browser_server_9200.out.log`)

```text
[RECV #71] opcode=0x0064, payload=1B     [SEND] opcode=0x0064, payload=27B
[RECV #73] opcode=0x0066, payload=22B
[RECV #74] opcode=0x0066, payload=22B
[RECV #76] opcode=0x0067, payload=15B
[RECV #77] opcode=0x0066    [RECV #78] opcode=0x0067
[RECV #79] opcode=0x0066    [RECV #80] opcode=0x0067
[RECV #81] opcode=0x0066    [RECV #82] opcode=0x0066
```

`0x0066` = 액터 upsert(22B), `0x0067` = 이동(15B). 하루 종일 `0x0016` 하트비트만 나오던
채널에서 처음으로 월드 패킷이 흘렀다.

### 화면

`artifacts/audio/scene_after_door.png` — 분수·GYM 건물·"welcome to Azroke" 간판·우상단
광장 미니맵이 있는 야외. 좌하단 정보창 `이름: Azrok1 / 레벨: 26 / 단계: 레드론`,
캐릭터 머리 위 이름표 `Guest`. PatHouse 실내가 아니라 **광장**이다.

### 입력 파이프라인 (#512 의 수정이 실제로 유효함을 확인)

```json
{"abi":1,"type":"mouseup","trusted":true,"clientX":940,"clientY":712,
 "canvasX":319.69,"canvasY":300,"canvasWidth":640,"canvasHeight":480}
```

- `trusted:true` — CDP 합성 입력도 신뢰 이벤트로 들어간다.
- 요청한 게스트 좌표 (320,300) → `canvasX 319.69` 로 정확히 변환된다.
- `canvasWidth/Height` 가 **640x480** 으로 잡힌다. #512 가 고친 백킹 크기 인식이 살아 있다.

## 3. 어떻게 눌렀나

문은 **카메라를 우클릭 드래그로 돌린 뒤** 눌렀다. 사용자가 직접 클릭했고, 패킷 직전
`inputProbe` 가 남긴 좌표는 다음과 같다.

```text
canvasX 209.69  canvasY 200.00
canvasX 220.94  canvasY 178.75
canvasX 263.44  canvasY 174.38   <- 직후 SEND 0x0004 발생
```

**주의**: 이 좌표는 그때의 카메라 방향에 딸린 값이며 고정 좌표가 아니다.
기본 카메라에서 상단 문간(게스트 x 241~469, y 0~96)을 여러 번 눌러 봤지만
전부 하트비트만 나왔다 — 즉 **좌표를 외워 재사용할 수 없고 카메라 상태가 선행 조건**이다.

## 4. 왜 이제 됐나 (INFERRED — 단정하지 말 것)

세 가지가 동시에 달라졌고 어느 것이 결정적인지는 아직 가르지 않았다.

1. **#528 의 정지 수정.** 이전 시도는 게스트가 2.4~2.9초마다 87~185ms 멈추는 상태에서
   입력을 넣고 있었다. 지금은 정지 0회다. 입력 타이밍이 히트테스트에 영향을 줬을 수 있다.
2. **#512 의 좌표 수정이 실제로 재시도된 적이 없었다.** INDEX 가 명시적으로
   "그 뒤 광장 진입을 다시 시도한 기록이 없다" 고 적어 두었다.
3. **카메라 회전.** 기본 카메라에서는 문이 클릭 가능한 위치에 없었을 수 있다.
   #476 의 "바닥 클릭·포인터락·키보드·드래그" 목록에 카메라 회전 후 문 클릭은 없다.

## 5. 재현 구성

```text
root  = TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1
app   = Azrok_D3D9Web_pathouse_guesttexrecycle4
p     = run_azrok_web.bat            (세션 B 는 run_azrok_peer111.bat)
stem  = boxedwine.upstreamjit64fn6inlineabi2
URL  += &webBgmFallback=0&inputProbe=1&debugConsole=1&lean=0
캔버스: 백킹 640x480, CSS 1024x768, 스케일 1.6
```

판정은 화면이 아니라 **서버 로그의 opcode** 로 한다. `0x0066`/`0x0067` 이 뜨면 진입이다.

## 6. 상호 가시성 달성 (VERIFIED)

두 브라우저 세션이 **같은 광장에서 서로를 렌더링한다.**

- 세션 A: 포트 9222, `run_azrok_web.bat`, 계정 `player` → 캐릭터 `Azrok1`(분홍 레드론)
- 세션 B: 포트 9223, `run_azrok_peer111.bat`, 계정 `peer111` → 캐릭터 `Player`(하늘색·왕관)

`artifacts/audio/plaza_B.png` 에 두 캐릭터가 이름표 `Player` / `Azrok1` 와 함께 나란히 찍혔다.
사용자 육안 확인으로 **양방향** 가시성도 확정됐다("둘 다 서로 보여").

서버 릴레이 실측 (최근 250줄):

```text
SEND/relay opcode=0x0068  20건    (액터 위치)
SEND/relay opcode=0x0066   6건    (액터 upsert)
```

**#507 의 `plaza_clients=0` · `visible_remote_actor_count=0` 은 이것으로 뒤집혔다.**

## 7. 릴레이 품질 결함 — 각도 고정과 순간이동 (VERIFIED, 원인 확정)

사용자 관찰: "상대편 각도가 항상 고정되어 있고, 움직일 때마다 순간이동한다. 걷는 것 같지도 않다."

두 증상 모두 **서버가 이미 받은 데이터를 버리는 것**이 원인이다. 디코더가 그대로 말한다.

```python
def decode_c2s_0066(payload):   # 22B
    """Decode exact movement intent: cell, endpoints, duration, path flag."""
    struct.unpack('<BiiiiiB', payload)   # cell, 시작(x1,y1), 끝(x2,y2), duration, pathflag

def decode_c2s_0067(payload):   # 15B
    """Decode exact arrival commit: cell, signed position, action, angle."""
    struct.unpack('<BiiIH', payload)     # cell, x, y, action, angle
```

| 증상 | 원인 | 위치 |
|---|---|---|
| 각도 고정 | `_build_state_0068_actor_position_record(entity_id, x=x, y=y)` 로 호출해 `heading` 이 기본값 **0** 으로 고정된다. `0x0067` 의 `angle` 은 어디에도 쓰이지 않는다 | `azrok_server.py:5817` / 빌더 `:9422` |
| 순간이동 | `0x0066` 은 **시작점·끝점·duration** 을 다 담은 "이동 의도" 인데, 서버는 끝점 `x,y` 만 뽑아 즉시 1회 전송한다. 보간도, 이동 의도 전달도 없다 | `azrok_server.py:5816-5826` |
| 동작 없음 | `0x0067` 자체가 릴레이되지 않는다. 코드 주석: `C2S 0x0067 contains local action state whose S2C mapping is not yet verified` | `azrok_server.py:5829` |

`0x0068` 레코드는 6 dword `[entity_id][x][y][z][heading][mode_flag]` 이므로 **heading 을 실을 자리는 이미 있다.**
필요한 값도 클라이언트가 이미 보내고 있다. 서버가 연결만 해 주면 된다.

## 8. 다음 (NOT VERIFIED)

- **두 세션 상호 가시성** — 게이트5 의 본체. 세션 B(`peer111`)를 별도 브라우저·포트 9223 에
  올려 같은 광장에서 서로를 보는지 확인해야 한다. `visible_remote_actor_count`, `plaza_clients`.
- **서버 GUI(9300) 동시 정상 작동** — GUI 는 HTML 대시보드이고 데이터는 WebSocket 으로
  보인다. `/api/macros`, `/api/ox/automation`, `/api/protocol/specs` 외 상태 엔드포인트 미확인.
- **문 클릭의 자동화** — 카메라 의존성 때문에 고정 좌표로는 불가. 카메라 회전을 포함한
  절차를 만들거나, 원본의 히트테스트 조건을 정적으로 규명해야 한다.
