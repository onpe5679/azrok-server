# 540 S2C 0x0066 self-profile 불가와 0x006C 커뮤니티 상태 계약 (2026-07-30)

날짜: 2026-07-30

선행: #539, #538

근거: `docs/research/_salvage/symbols/plaza_dump.txt` 디컴파일, 원본 `Azrok_original.exe`의 `.data` 직접 읽기, #539의 2세션 실측.

제약: 원본 실행파일·게임 자산·클라이언트는 수정하지 않았다. `visible_remote_actor_ids`, `_ox_relay_position`, S2C 0x0068 릴레이는 변경하지 않았다.

---

## 결론

- **A: 구현 보류 (VERIFIED).** S2C 0x0066에는 fixed self actor를 이름/외형으로 갱신하는 action 값이 없다. self id 레코드는 생성·필드 복사·action 분기보다 앞에서 제외된다. 따라서 self id=1의 0x0066을 광장 입장 직후나 roster 갱신마다 보내는 것은 해결책이 아니다.
- **B: S2C 0x006C 중계 보류 (VERIFIED/NOT VERIFIED).** state는 C2S 0x0069의 1바이트 의자 번호 0..5에서 나온다는 직접 경로가 확인되었다. 그러나 toggle 0/1을 원본 서버가 어느 점유·해제 정책으로 정하는지는 미확정이므로 `(state,toggle,actor_id)`를 지어내 중계하지 않는다.

## A1. 0x0066 action과 self/remote 경로

**VERIFIED — `FUN_00615B50` (dump 355505-355535)** 는 0x1A 레코드마다 먼저 `FUN_0050D790(record, 1)`을 호출한다. `FUN_0050D790` (223663-223691)은 `record+1 == local_self_id`이면 즉시 0을 반환하고, 이미 등록된 remote id도 0을 반환한다. 아직 없는 **non-self** id만 슬롯을 만들고 `FUN_005243E0`을 호출한다.

`FUN_005243E0` (237831-237869)은 신규 remote 슬롯에 다음만 복사한다: id `+0x01`, type/subtype `+0x05/+0x06`, name `+0x07`, appearance `+0x14..+0x17`.

| record `+0x00` | VERIFIED 코드 효과 | 적용 범위 |
|---:|---|---|
| `0x0A` | state `0x2E`, `FUN_00600970`, `FUN_005FFBC0/005FFBF0/005FFC50`, `FUN_00526E80(1,0)` | 새 non-self remote만 |
| `0x0B` | state `0x2F`, 같은 전환열, 마지막 `FUN_00526E80(1,1)` | 새 non-self remote만 |
| 그 외 | action 자체의 분기는 없다. `+0x18 != 0xFF`일 때만 `FUN_00527A70(+0x18,+0x19)` | 새 non-self remote만 |

`FUN_00527A70` (239447-239465)은 state/toggle을 `+0x336/+0x33A`에 쓰고 animation table을 사용해 state `0x30`으로 둔다. 그러므로 `0x0A`은 self-update가 아니라 신규 remote 전환값이다.

**VERIFIED — fixed self의 별도 초기화**: `FUN_00614370`의 초기화 단계가 `FUN_006130B0`을 호출하고 (92495-92530), `FUN_006130B0`은 로컬 프로필에서 name/type/appearance를 만든 0x1A 로컬 레코드를 `FUN_00524280`에 준다 (354044-354077). `FUN_00524280`은 fixed self의 id/type/name을 설정한다 (237780-237806).

## A2. 서버 변경과 전송 시점

**구현 보류 (VERIFIED).** self id=1 S2C 0x0066을 보내는 유효 action도, 안전한 전송 시점도 존재하지 않는다. `FUN_0050D790`의 self early-return 때문에 광장 입장 직후 1회와 roster 재갱신 모두 fixed self 복사를 일으키지 않는다.

서버의 `_send_room_roster`는 계속 peer remote actor만 보내도록 명시했고, 이 불변식을 검사하는 회귀 테스트를 추가했다. 이는 self 0x0066을 새 remote처럼 생성하는 회귀를 막는다. 실제 self-name 수정은 `FUN_006130B0`이 읽는 **로컬 프로필의 공급원**을 별도로 추적해야 한다.

**NOT VERIFIED:** `FUN_005286E0`가 읽는 프로필을 어떤 정상 C2S/S2C 계약이 server_state의 캐릭터 이름과 연결하는지. 이것을 확인하기 전에는 서버가 self 이름 패킷을 새로 만들지 않는다.

## A3. 0x0066 레코드 배치

**VERIFIED.** 레코드는 계속 정확히 0x1A다: `+0x01` id, `+0x05` char_type, `+0x07` 이름 13바이트, `+0x14..+0x17` 외형, `+0x18=0xFF` 센티넬. 이 조사에서 배치와 기존 builder는 변경하지 않았다.

## B1. state/toggle 출처와 유효 범위

**VERIFIED — 수신/테이블.** `FUN_00615410` (355258-355283)은 remote actor에만 S2C 0x006C `[state:u8][toggle:u8][actor_id:u32]`를 적용한다. `toggle < 2`이면 state/toggle을 각각 `+0x336/+0x33A`에 저장하고 `FUN_00527760(0x30,0)`으로 진입한다. `toggle >= 2`이면 `FUN_00527720/00527970`으로 둘을 `-1`로 해제한다.

`FUN_00527760`과 `FUN_00527A70`은 `DAT_006D9D48 + state*0x18 + toggle*0x0C`를 사용하며, 한 조합은 3 dword다 (239320-239388, 239447-239465). 원본 PE의 `.data`를 직접 읽은 결과:

| 범위 | 직접 확인한 내용 | 결론 |
|---|---|---|
| `0x006D9D48..0x006D9DD7` | 0x90 bytes, 6행의 비영 3-dword×2 entry | state 0..5, toggle 0..1 초기화됨 |
| `0x006D9DD8..0x006D9E07` | 0x30 bytes 모두 0 | 물리적으로 state 6..7 행은 있으나 reserved/invalid zero 행 |
| `0x006D9E08` 이후 | RTTI 시작 | table 끝 |

따라서 물리 footprint는 8 state × 2 toggle × 3 dword(0xC0)지만, **프로토콜 의미 유효값은 state 0..5와 toggle 0..1**이다. state는 `FUN_00615180`이 `PLAZA_CHAIR_%d.MDL`을 d=0..5로 검사하고 일치 시 C2S 0x0069 1바이트를 보내며 같은 값을 self `+0x336`에 쓰므로 직접 확인된다 (355154-355202, 305567-305578).

**VERIFIED — toggle 수신 경로.** S2C 0x006B의 1바이트는 `FUN_00615340`에서 `<2`일 때 현재 self actor `+0x33A`에 쓰이고, `>=2`면 해제된다 (355216-355244).

**NOT VERIFIED — 원본 서버 정책.** client dump에는 C2S 0x006B builder가 없고, 원본 서버가 0x0069 state를 언제 저장하는지, toggle 0/1을 어느 좌석 점유·해제 규칙으로 결정하는지는 확인되지 않았다. state가 0x0069에서 유래한다는 사실만으로 S2C 0x006C의 두 필드를 완성할 수 없다.

## B2. S2C 0x006C 중계

**구현 보류 (NOT VERIFIED).** state 후보는 C2S 0x0069에서 확인됐지만 toggle 정책이 없다. `(0,0)`이나 마지막 값을 발명하면 actor에 잘못된 table entry와 state 0x30을 강제한다. `azrok_server.py`의 기존 `_relay_community_006c`는 target id만 검증·기록하고 S2C 0x006C을 보내지 않는 상태를 유지한다.

다음 동적 확인은 빈 의자 선택, 점유 의자 선택, 해제/이동 각각에 대해 C2S 0x0069, 해당 세션 S2C 0x006B, 상대 조회 시 S2C 0x006C를 같은 타임라인으로 캡처하는 것이다.

## B3. 커뮤니티 중 이동

**VERIFIED.** `FUN_00615D50`은 remote S2C 0x0068 레코드에 `FUN_00524EB0`을 호출한다 (355557-355584). `FUN_00524EB0` (238159-238198)은 actor state `+0x107 == 0x30`이면 target/deadline을 갱신하지 않고 반환한다. 즉 커뮤니티 state 0x30 중에는 client가 정상 0x0068 이동을 의도적으로 거부한다.

서버는 기존 이동 릴레이와 `visible_remote_actor_ids` gate를 그대로 유지한다. 커뮤니티 상태가 클라이언트에서 해제되어 이동 가능 상태로 돌아오기 전에는 이동이 반영되지 않는 것이 계약에 맞으며, fabricated state나 위치 패킷으로 우회하지 않는다.

## 검증

```text
python -m py_compile azrok_server.py
PYTHONPATH=. python tools/test_server_contract_layers.py
PYTHONPATH=. python tools/test_server_room_mapping.py
PYTHONPATH=. python tools/test_content_builders.py
```

```text
PASS  python -m py_compile azrok_server.py
PASS  PYTHONPATH=. python tools/test_server_contract_layers.py  (107 tests)
PASS  PYTHONPATH=. python tools/test_server_room_mapping.py     (7 tests)
PASS  PYTHONPATH=. python tools/test_content_builders.py        (14 tests)
```
