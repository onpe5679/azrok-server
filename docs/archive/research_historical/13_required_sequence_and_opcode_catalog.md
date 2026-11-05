# Azrok 서버 프로토콜 복원: 필수 시퀀스와 opcode 카탈로그

Date: 2026-03-31
Target: `Azrok.exe`
Goal: 패킷만으로 클라이언트를 정상 플레이 가능한 상태까지 밀어 올리기 위한 서버 응답 순서를 복원한다.
Evidence: `azrok_server.py`, `docs/research`, Ghidra decompilation

## 먼저 바로잡아야 할 핵심 4가지

1. 기존 문서와 서버 코드가 `0x0010`, `0x0011`이라고 부르던 stat/curve packet은 wire opcode 기준으로는 `0x000A`, `0x000B`일 가능성이 매우 높다.
   - 근거: `FUN_0059DD20`이 raw opcode `10`을 `FUN_0059ECA0`로, raw opcode `11`을 `FUN_0059EEE0`로 직접 라우팅한다.
2. `S->C 0x0000`은 4바이트 짜리 login stub가 아니다.
   - `FUN_0059E070`과 `FUN_0050D1C0` 기준으로 최소 약 `0x183` 바이트 규모의 구조체다.
3. `S->C 0x0007`은 단순 filler가 아니라 네이티브 로딩/자기(self) bootstrap을 여는 핵심 packet이다.
   - common handler `FUN_0050CBC0` case `7`이 곧바로 `FUN_0050D290`을 타고 room code를 연다.
4. `S->C 0x0064`는 state-1 진입 후 authoritative self packet이지, local self entity를 처음 만드는 packet이 아니다.
   - local self entity는 그보다 앞선 `FUN_006130B0` stage-0 bootstrap에서 만들어진다.

## 현재 가장 강한 필수 서버 시퀀스

### 1. 연결/초기화 구간

1. 클라이언트는 먼저 `C->S 0x0000` 큰 hello blob를 보낸다.
2. 서버는 heartbeat `C->S 0x0016`에 `S->C 0x0016(00)`으로 답해야 한다.
3. `S->C 0x0000`도 결국 구현해야 하지만, 현재까지는 정확한 full layout이 완전히 복원되지는 않았다.
   - 다만 4바이트 zero stub는 명백히 틀리다.

### 2. 캐릭터 생성 직후

1. `C->S 0x0004` 수신
2. 서버는 `S->C 0x0002`를 보낸다.
3. 이어서 `S->C 0x0003`을 보낸다.
   - `payload+1`은 NUL-terminated path string이다.
   - 첫 방 후보는 `Data\\Space\\PatHouse`.
   - 첫 바이트는 manager `gm+0x31C63`에 저장되는 flag인데, 의미는 아직 완전히 확정되지 않았다.

### 3. 첫 zone/setup 구간

1. `C->S 0x0007` 수신
2. 서버는 아래 4개를 coherent하게 연달아 보내야 한다.
   - `S->C 0x0007`
   - `S->C 0x0005`
   - `S->C 0x000A`
   - `S->C 0x000B`
3. 이 첫 `S->C 0x0007`이 들어가면 클라이언트 내부 common handler가 `FUN_0050D290`을 호출해 로딩 code를 선택한다.
   - `gm+0x31C72 == 0` and `gm+0x31C73 == 0`이면 `100`
   - `gm+0x31C72 != 0`이면 `0x6E`
   - `gm+0x31C73 != 0`이면 `0x6F`
4. `FUN_0050A0F0` case `0`은 `room.wmb`를 load한 뒤 post-load code `100`을 queue한다.
5. 이후 `FUN_0050B400(100)` -> `FUN_00614370` -> stage `0`의 `FUN_006130B0`로 들어간다.

### 4. local bootstrap이 서버에 다시 보내는 것

`FUN_006130B0`는 stage-0에서 local self를 만든 뒤 `FUN_005AB710`을 통해 outbound `C->S 0x0064(<1 byte>)`를 직접 보낸다.

이 packet의 의미:

- 단순 쓰레기 ack가 아니다.
- local bootstrap status byte다.
- 서버는 이 packet을 절대 echo하면 안 된다.

### 5. state-1 authoritative self 구간

1. 첫 `C->S 0x0017` 수신
2. 서버는 `S->C 0x0064`를 보내야 한다.
   - 이것이 `FUN_00594310`에서 dispatch state를 `1`로 바꾸고, 동시에 `FUN_00615650` heavy self handler로 들어가는 유일하게 확인된 packet이다.
3. PatHouse first-room 가설을 따를 때 `0x0064 entry byte`는 `0x00` 또는 `0x14`가 더 자연스럽다.
   - `0x0A`, `0x0B`는 Plaza scene code `0x2E`, `0x2F`를 강제로 세팅한다.
4. optional follow-up으로는 `S->C 0x0069(self_id, x, y, 0)` 정도만 남긴다.
5. 현재 서버가 같이 보내는 `S->C 0x0066(self_id)`와 `S->C 0x0068(self_id)`는 self actor id 기준으로 사실상 no-op다.

### 6. late loading / tutorial-ready 구간

1. late stage에서 `S->C 0x006E(slot, 0)`가 추가로 필요할 가능성이 높다.
   - `FUN_006169D0`는 `payload[1] == 0`일 때만 ready/setup path를 탄다.
2. repeated late `C->S 0x0007`에는 silence보다 coherent한 `S->C 0x0007` 재응답이 더 유력하다.

## 서버가 처리해야 하는 주요 inbound opcode

### 현재까지 관측된 C->S

| Opcode | 의미 | 서버 대응 |
| --- | --- | --- |
| `0x0000` | 초기 hello / login-side open blob | full layout 미복원. 현재 무응답 또는 향후 정확한 `S->C 0x0000` 필요 |
| `0x0016` | heartbeat | `S->C 0x0016(00)` |
| `0x0004` | 캐릭터 생성/선택 | `S->C 0x0002`, `0x0003` |
| `0x0007` | zone/setup 요청 | `S->C 0x0007`, `0x0005`, `0x000A`, `0x000B` |
| `0x0001` | disconnect-ish / transition marker | echo 금지 |
| `0x0017` | authoritative state-1 pivot 직전 신호 | 첫 회에 `S->C 0x0064` |
| `0x0064` | client local bootstrap status byte | echo 금지, 의미 보존 필요 |

## 클라이언트가 수신 처리하는 주요 S->C opcode

### state-0 공통/주요

| Opcode | 주요 함수 | 용도 |
| --- | --- | --- |
| `0x0000` | `FUN_0059E070`, `FUN_0050D0E0` | large login/state struct |
| `0x0001` | `FUN_0059E1C0`, `FUN_0050D360` | close/error/status |
| `0x0002` | `FUN_0059D150` | transition trigger |
| `0x0003` | `FUN_0050D200` | path/space arm |
| `0x0005` | `FUN_0059EBD0`, `FUN_0050CFF0` | state dword + subtype side effects |
| `0x0007` | `FUN_0059E330`, `FUN_0050D290` | setup blob + native loading path arm |
| `0x000A` | `FUN_0059ECA0` | keyed stat registry |
| `0x000B` | `FUN_0059EEE0` | XP curve |

### state-1 extra

| Opcode | 주요 함수 | 용도 |
| --- | --- | --- |
| `0x0003` | `FUN_00615610` | state-1 path/string refresh |
| `0x000C` | `FUN_006165B0` | 4 selector slot live update/clear |
| `0x0064` | `FUN_00615650` | authoritative self placement |
| `0x0065` | `FUN_00615B20` | actor finalize |
| `0x0066` | `FUN_00615B50` | actor record array |
| `0x0067` | `FUN_00615D00` | actor remove / cleanup |
| `0x0068` | `FUN_00615D50` | actor position record |
| `0x0069` | `FUN_00615E70` | actor position commit |
| `0x006A` | `FUN_00615FF0` | complex actor/message update |
| `0x006B` | `FUN_00615340` | local toggle/state |
| `0x006C` | `FUN_00615410` | actor toggle/state |
| `0x006D` | `FUN_006154E0` | scene/state shift to `0x31` branch |
| `0x006E` | `FUN_006169D0` | ready/setup |
| `0x006F` | `FUN_00616B20` | appearance slot update |
| `0x0070` | `FUN_00616860` | scene/item/event update |
| `0x0071` | `FUN_00616510` | generated text/notification |
| `0x03E8` | `FUN_006167E0` | state-1 reset/error path |

## 최종 결론

현재 목표 기준으로 서버가 반드시 맞춰야 하는 최소 골격은 아래다.

1. `0x0004` 뒤 `0x0002`, `0x0003`
2. 첫 `0x0007` 뒤 coherent한 `0x0007`, `0x0005`, `0x000A`, `0x000B`
3. client local `0x0064`는 echo 금지
4. 첫 `0x0017` 뒤 authoritative `0x0064`
5. late stage에서 필요 시 `0x006E`와 repeated `0x0007` 재응답

가장 치명적인 현재 오해는 두 가지다.

- stat packets의 wire 번호를 `0x0010/0x0011`로 보는 것
- `0x0064` 하나만 맞추면 self bootstrap이 끝난다고 보는 것
