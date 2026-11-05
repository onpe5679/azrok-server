# Azrok 서버 프로토콜 복원: payload 맵과 숨은 상태

Date: 2026-03-31
Target functions:
- `FUN_0059E070`, `FUN_0050D1C0`
- `FUN_0059E330`
- `FUN_0059EBD0`
- `FUN_0059ECA0`
- `FUN_0059EEE0`
- `FUN_00615650`
- `FUN_006165B0`
- `FUN_006169D0`

## 1. `S->C 0x0000`: 현재 서버가 가장 크게 틀린 packet

### 확정된 사실

- state-0 primary handler `FUN_0059E070`는 `payload[1]`, `payload[0x56]`, `payload[0x57...]`, `payload[0xBB...]`를 읽는다.
- state-0 secondary handler `FUN_0050D0E0`는 `FUN_0050D1C0`를 통해 packet 전체를 manager 내부 버퍼로 복사한다.
- `FUN_0050D1C0`는 약 `0x183` 바이트를 복사한다.

### 현재까지 복원된 layout

| Offset | Size | 의미 |
| --- | --- | --- |
| `+0x00` | `u8` | status/type |
| `+0x01` | `u8` | mode-like value, `FUN_0059D890`를 통해 manager `+0x1E8` 저장 |
| `+0x56` | `u8` | record count |
| `+0x57` | `count * u16` | record id array |
| `+0xBB` | `count * u32` | record value array |

### 실무 결론

- 현재 `azrok_server.py`의 `S->C 0x0000 = 4 zero bytes`는 wire-correct가 아니다.
- 이 packet을 정확히 복원하지 않으면 protocol-complete 서버라고 부를 수 없다.

## 2. `S->C 0x0003`: path arm packet

`FUN_0050D200(payload)` 기준:

| Offset | Size | 의미 |
| --- | --- | --- |
| `+0x00` | `u8` | unresolved mode flag, manager `gm+0x31C63`에 저장 |
| `+0x01` | C-string | NUL-terminated path string |

현재 가장 강한 path 후보:

- `Data\\Space\\PatHouse`

주의:

- 첫 바이트는 아직 완전히 확정되지 않았다.
- 현재 서버의 hardcoded `0x01`은 근거가 약하다.

## 3. `S->C 0x0007`: 핵심 setup blob (`0x1D8 = 472B`)

### 확정 field map

| Offset | Size | 소비 함수 | 의미 |
| --- | --- | --- | --- |
| `+0x00` | `u8` | `FUN_0059E2D0` | manager `+0x134` status byte |
| `+0x01` | `u8` | `FUN_0059D860` | species / char type -> manager `+300` |
| `+0x02` | `u8` | `FUN_00599150` | subtype / pet-evo related -> manager `+0x130` |
| `+0x03` | `u32` | `FUN_005A8C90` | decimal-packed datetime `YYMMDDHH` |
| `+0x07` | `u32` | `FUN_0059E300` | state dword -> manager `+0x1EC` |
| `+0x0B` | `70 * u16` | `FUN_005A4880(idx,val)` | indexed stat bag |
| `+0x97` | `0x21 bytes` | `FUN_0059BC00` | list/set block A |
| `+0xB8` | `0x0F bytes` | `FUN_0059BC00` | list/set block B |
| `+0xC7` | `0x14 bytes` | `FUN_0059BC00` | list/set block C |
| `+0xEA` | `0x26 bytes` | `FUN_0059BC00` | list/set block D |
| `+0x110` | `0x03 bytes` | `FUN_0059BC00` | list/set block E |
| `+0x113` | `0x0A bytes` | `FUN_0059BC00` | list/set block F |
| `+0x11D` | `0x08 bytes` | `FUN_0059BC00` | list/set block G |
| `+0x125` | `0x0B bytes` | `FUN_0059A6E0` | raw event/stat codes |
| `+0x131` | `0x01 byte` | `FUN_0059BC00` | single-entry list block |
| `+0x134` | `10 * u16` | filter + `FUN_005A5AB0` | table A type |
| `+0x148` | `10 * u16` | `FUN_005A5AB0` | table B type |
| `+0x15C` | `10 * u32` | `FUN_005A5AB0` | table payload |
| `+0x184` | `8 * u8` | `FUN_005AA6F0` | mode byte |
| `+0x18C` | `8 * u32` | `FUN_005AA6F0` | mode payload |
| `+0x1D4` | `4 * u8` | `FUN_005AB080` | bootstrap selector bytes |

### `+0x125..+0x12F`는 절대 zero-fill 금지

`FUN_0059A6E0`는 이 11바이트를 즉시 event/stat code로 해석한다.

유효 code range:

- `0..32`
- `1000..1032`
- `1500..1502`
- `2000..2009`
- `2500..2507`
- `3000`
- `4000..4005`
- `5000..5002`

실무 규칙:

- 비어 있으면 `0xFF` sentinel 사용
- `0x00`은 실제 low-id code다

### `70*u16` stat bag은 CSV row order와 다르다

확정된 사실:

- wire bag은 `0..69` 총 70 slot이다.
- visible schema는 `lgc.tmp` 57행과 강하게 연결되지만, raw wire order와 동일하지 않다.
- `azrok_server.py`의 `INIT_CSV_STATS`처럼 `init.csv`를 평평하게 복사하는 방식은 틀렸다.

강한 복원:

- visible row와 초반 다수 slot은 겹친다.
- 후반부는 hidden slot이 끼어든다.
- 내부 71-name table 기준으로 tail에는 `펫진화`, `펫`, `명령횟수`, `턴횟수` 계열이 존재한다.
- `FUN_0059E330` loop는 `0..69`까지만 쓰므로 `턴횟수`는 내부 이름 테이블에는 있어도 raw wire bag에서는 직접 쓰지 않는 것으로 보인다.

### `+0x1D4..+0x1D7` selector 바이트

이 4바이트는 `FUN_006130B0` stage-0 bootstrap에서 바로 읽혀 `FUN_00521E90(slot, value, 0)`로 들어간다.

유효 범위:

- slot 0: `0..9`
- slot 1: `0..6`
- slot 2: `0..51`
- slot 3: `0..71`

규칙:

- `0`은 유효한 lowest selector
- clear/no-op는 `0xFF`

## 4. `S->C 0x0005`: post-load state packet (`6B`)

`FUN_0059EBD0(payload)` 기준:

| Offset | Size | 의미 |
| --- | --- | --- |
| `+0x00` | `u8` | status |
| `+0x01` | `u8` | subtype `0x00`, `0x12`, `0x13` |
| `+0x02` | `u32` | state dword |

세부 동작:

- subtype `0x13`, status `0`
  - `FUN_005A9B50()` 실행
  - 마지막 `0x0007` stat cache를 keyed registry로 replay
  - 그 뒤 state dword 저장
- subtype `0x12` 또는 `0x00`, status `0`
  - state dword만 저장

실무 규칙:

- `0x0005 +0x02..+0x05`는 `0x0007 +0x07..+0x0A`와 맞춰야 한다.

## 5. `S->C 0x000A`: keyed stat registry (`150B`)

`FUN_0059ECA0(payload)` 기준:

| Group | Offset | Count | Key space |
| --- | --- | ---: | --- |
| 0 | `+0x00` | 22 x `u16` | `1,2,4,5,...,31,32` |
| 1 | `+0x2C` | 6 x `u16` | `2002,2003,2005,2006,2008,2009` |
| 2 | `+0x38` | 5 x `u16` | `2501,2502,2504,2505,2507` |
| 3 | `+0x42` | 32 x `u16` | `1001..1032` |
| 4 | `+0x82` | 3 x `u16` | `1500..1502` |
| 5 | `+0x88` | 1 x `u16` | `3000` |
| 6 | `+0x8A` | 6 x `u16` | `4000..4005` |

### Group 0이 가장 중요하다

group0 22개는 flat 22 stat가 아니다.

실제 의미:

- 11개 stat의 `current/max` pair

예:

- IQ: current, max
- 레벨: current, max
- 경험치: current, max
- 허기: current, max
- ...
- 봉에너지: current, max
- 마지막 core stat 1개: current, max

즉 현재 `azrok_server.py`처럼

```text
0, 25, 33000, 10, 80, 80, ...
```

형태로 flat row-order를 보내면 구조 자체가 맞지 않는다.

## 6. `S->C 0x000B`: XP curve (`62B`)

`FUN_0059EEE0 -> FUN_005A50F0`

구조:

- `31 * u16`
- `DAT_006E0A88[i]`에 zero-extend 저장

복원된 curve:

```text
0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500,
5500, 6600, 7800, 9100, 10500, 12000, 13600, 15300, 17100, 19000,
21000, 23100, 25300, 27600, 30000, 32500, 35100, 37800, 40600, 43500,
60001
```

주의:

- index 22는 `25300`이 맞다.

## 7. `S->C 0x0064`: authoritative self packet (`0x1B`)

`FUN_00615650(payload)` 기준:

| Offset | Size | 의미 |
| --- | --- | --- |
| `+0x00` | `u8` | entry byte. 허용값 `0x00`, `0x0A`, `0x0B`, `0x14` |
| `+0x01` | `u32` | actor/entity id |
| `+0x06` | `u32` | x |
| `+0x0A` | `u32` | y |
| `+0x12` | `u8` | appearance A |
| `+0x13` | `u8` | appearance B |
| `+0x14` | `u16` | year |
| `+0x16` | `u8` | month-1 |
| `+0x17` | `u8` | day |
| `+0x18` | `u8` | hour |
| `+0x19` | `u8` | minute |
| `+0x1A` | `u8` | second |

entry byte 차이:

- `0x0A` -> Plaza state `0x2E`
- `0x0B` -> Plaza state `0x2F`
- `0x00`, `0x14` -> Plaza 강제 없음

## 8. `S->C 0x000C`: live selector update

`FUN_006165B0(payload)` 기준:

| Offset | Size | 의미 |
| --- | --- | --- |
| `+0x00` | `u32` | actor id |
| `+0x04` | `u8` | clear flag. `0`이면 set, nonzero면 clear |
| `+0x05` | `u8` | selector slot index (`0..3`) |
| `+0x06` | `u8` | selector value |

동작:

- self actor 또는 다른 actor의 4 selector slot을 runtime에 변경/clear한다.
- 결국 `FUN_00521E90(slot, value, 0)`로 들어간다.

## 9. `S->C 0x006E`와 `0x006F`

### `0x006E`

`FUN_006169D0(payload)` 기준:

| Offset | Size | 의미 |
| --- | --- | --- |
| `+0x00` | `u8` | selector/index byte |
| `+0x01` | `u8` | branch selector. `0`일 때만 ready/setup path |

확정 side effect:

- `payload[0]`가 manager field 두 곳에 저장된다.
- `gm+0x129B = 1`
- local event `0x0C6`

### `0x006F`

`FUN_00616B20(payload)` 기준:

| Offset | Size | 의미 |
| --- | --- | --- |
| `+0x00` | `u8` | appearance slot index |
| `+0x01` | `u8` | new value |

## 10. 현재 payload 쪽에서 가장 위험한 오해

1. `0x0007` stat bag은 `init.csv` row order 그대로 넣으면 된다는 생각
2. `0x000A group0`을 flat 22 values로 보내는 구현
3. `0x0007 +0x125..+0x12F`를 zero-fill하는 구현
4. `0x0007 +0x1D4..+0x1D7`에서 `0`을 빈 값으로 보는 구현
5. `0x0064 entry byte 0x0A/0x0B`를 무조건 정답으로 보는 구현
