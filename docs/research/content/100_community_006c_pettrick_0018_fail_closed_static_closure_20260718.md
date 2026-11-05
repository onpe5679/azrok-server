# 100 — C2S 006C / 0018 비대칭 변환의 정적 종결과 fail-closed 계약

날짜: 2026-07-18  
대상: 정당하게 취득한 종료 게임 클라이언트 `Azrok_original.exe`의 상호운용성 복원  
방법: 원본 바이너리 Ghidra 디컴파일 + thunk 교차참조 전수 확인 + 서버 계약 테스트

## 1. 결론

- **VERIFIED:** C2S `006C`는 `actor_id:u32` 4바이트만 보냅니다. 원본 클라이언트의 모든 확인된 송신 경로 어디에도 S2C `006C`의 `state/toggle` 생성값이 없습니다.
- **VERIFIED:** C2S `0018`은 `slot:u8, kind:u8, local_id:u8` 3바이트만 보냅니다. 원본 클라이언트의 송신자는 한 함수뿐이며, S2C `0069`의 `arg0/arg1/gate`를 만드는 로컬 변환 경로가 없습니다.
- **VERIFIED:** S2C `006C`의 `state/toggle`과 S2C `0069`의 `arg0/arg1/gate`는 수신 클라이언트에서 실제 actor state 또는 좌표 처리에 사용됩니다. 임의의 `0`도 no-op으로 증명되지 않았습니다.
- **INFERRED:** 누락 필드는 종료된 원본 서버가 권위적으로 결정했던 값입니다.
- **서버 계약:** 대응 값을 꾸며내지 않습니다. 두 요청은 방향별 exact decoder와 세션/actor 검증까지만 수행하고, S2C 패킷은 **0건** 송신하는 fail-closed/deferred 상태를 유지합니다.

## 2. C2S 006C 송신자 전수 확인

### 2.1 wire builder

`FUN_005AB950(actor_id)`:

- 스택 로컬에 `actor_id` dword 하나만 기록합니다.
- `FUN_005AB6A0(0x6C, &local, 4)`를 호출합니다.
- 따라서 exact payload는 `[actor_id:u32]`, 길이는 4바이트입니다.

### 2.2 thunk xref

원본 thunk `004DE33C -> FUN_005AB950`의 코드 xref는 세 곳입니다.

| call site | caller | 직접 확인한 값 |
|---|---|---|
| `005CE949` | `FUN_005CE8E0` | scene `0x6E`이면 self actor id |
| `005CE98B` | `FUN_005CE8E0` | 그 외에는 `0` |
| `005FDB4E` | `FUN_005FDAB0` | button queue case 6에서 얻은 self actor id |

`FUN_005FDAB0`의 case 6도 `FUN_0050D8E0()` 결과를 그대로 `FUN_005AB950`에 넘깁니다. 별도의 `state/toggle` byte를 읽거나 보내지 않습니다.

### 2.3 반대 방향 소비자

S2C `006C` handler `FUN_00615410`은 `[state:u8, toggle:u8, actor_id:u32]`를 소비합니다.

- self actor는 무시합니다.
- remote actor에서 `toggle < 2`이면 actor `+0x336/+0x33A`에 두 값을 write하고 refresh를 호출합니다.
- `toggle >= 2`이면 관련 actor 필드를 reset합니다.

따라서 서버가 `(0, 0)`을 기본값으로 넣는 것도 상태 변경입니다. **VERIFIED static / 원본 서버 값 NOT VERIFIED**입니다.

## 3. C2S 0018 송신자와 S2C 0069 소비자

### 3.1 wire builder와 유일한 producer

`FUN_005AB900(slot, kind, local_id)`은 exact 3바이트를 `opcode 0x18`로 보냅니다.

원본 thunk `004DB97A -> FUN_005AB900`의 코드 xref는 `FUN_005B2970` 내부 `005B2B6D` 한 곳뿐입니다.

`FUN_005B2970(this, slot)`은:

- slot 0이면 `this+0x764/+0x768`, slot 1이면 `this+0x7A8/+0x7AC`에서 kind와 full action id를 읽습니다.
- kind `0..3`에 따라 `10000, 20000, 30000, 40000`을 빼서 1바이트 `local_id`를 만듭니다.
- 최종적으로 `slot/kind/local_id`만 송신합니다.

좌표, actor id, gate 또는 별도 action-state dword는 이 경로에 없습니다.

### 3.2 S2C 0069는 서버 권위 입력

S2C `0069` handler thunk `004E1433`의 xref는 state-1 dispatcher `0061381A` 한 곳뿐입니다. 원본 클라이언트 내부에 C2S `0018`을 S2C `0069` 레코드로 만드는 producer는 확인되지 않습니다.

`FUN_00615E70`은 16바이트 `[actor_id:u32, arg0:u32, arg1:u32, gate:u32]`를 소비합니다.

- self actor에서는 `gate == 0`일 때만 적용되는 분기가 있습니다.
- remote actor에서는 mode에 따라 actor action record 적용, transition reset, pending scene 처리로 이어집니다.
- mode `0x2E/0x2F`에서는 `arg0/arg1`가 `FUN_004DF61F`의 좌표 pair로 들어가 visual sync를 수행합니다.
- `FUN_005250C0`도 `arg0/arg1/gate`를 actor 내부 상태에 기록하거나 동기화합니다.

즉 `arg0/arg1/gate`는 padding이 아니며, C2S 3바이트로부터 직접 변환할 정적 근거가 없습니다. 기존 문서 80의 “0018을 0069로 재브로드캐스트”는 **INFERRED 후보**로만 유지하고 서버 구현 근거로 사용하지 않습니다.

## 4. 서버 반영

`azrok_server.py`의 기존 validate/defer 정책을 다음처럼 보강했습니다.

- `006C`: exact 4바이트, active Plaza, self id 검증 후 `verified_c2s_fields=['actor_id']`와 누락된 `state/toggle`을 기록합니다. emit은 하지 않습니다.
- `0018`: exact 3바이트와 `slot<=1`, `kind<=3` 검증에 더해 active session을 확인합니다.
- `0018` deferred event에는 검증된 `slot/kind/local_id`, 누락된 `arg0/arg1/gate`, relay=false 사유를 명시합니다.
- inactive/위조/잘못된 shape 또는 범위 요청은 reject하고 패킷을 보내지 않습니다.

이것은 기능을 임의로 생략한 것이 아니라, 수신 클라이언트의 상태를 오염시키는 미확정 변환을 금지하는 계약입니다.

## 5. 검증

- `python -m py_compile azrok_server.py`: **PASS**
- `python -m unittest tools.test_server_contract_layers.SocialStateContractTests -v`: **4 PASS**
- `python -m unittest tools.test_server_contract_layers`: **63 PASS**
- `python -m unittest discover -s tools -p 'test_*.py'`: **88 PASS**
- 모든 social-state 계약 테스트에서 `_emit` 결과: **0건**

## 6. 남은 동적 증거

- **NOT VERIFIED:** 원본 서버가 선택한 S2C `006C state/toggle` 실제 값과 UI 의미.
- **NOT VERIFIED:** 원본 서버가 C2S `0018` 이후 선택한 S2C `0069 arg0/arg1/gate` 실제 값.
- 원본 서버는 종료되어 있으므로, 향후 정당한 보존 캡처나 독립된 직접 증거가 나오기 전까지 현재 fail-closed 정책이 권위입니다.

Related: `content/80`, `protocol/75`, `86`, `90`, `84`, `INDEX`.
