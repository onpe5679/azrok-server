# 아이템 사용 producer 도달성·S2C 0007 effect-byte 경계 (2026-07-18)

> **SUPERSEDES 84/90/91의 “toy/gym 실제 인벤토리 UI live 미검증” 가정.**
> shipped 클라이언트의 `내 인벤토리` toy/gym 탭에는 C2S `000D/000E` producer가 없습니다. UI 조작을 더 찾는 문제가 아니라 정적 callgraph상 도달 불가능한 경로입니다.

원본 `Azrok_original.exe`를 Ghidra MCP로 직접 디컴파일하고, 최신 Plaza 클라이언트의 비파괴 UI/wire 실측과 대조했습니다. VERIFIED는 디컴파일 또는 wire 실측, INFERRED는 보존 서버 정책, NOT VERIFIED는 별도 disposable ABI 실측이 필요한 항목입니다.

## 1. 핵심 정정

- **VERIFIED:** `DomainCode_EmitLocalEffect@0059A6E0`의 인자는 domain 번호가 아니라 **absolute item ID**입니다.
- **VERIFIED:** 함수는 먼저 `DomainCode_ClassifyBucket(item_id)@0059A460`를 호출한 뒤 그 반환값을 switch합니다.
  - classifier `case 0`: furniture item ID `0..32`
  - `case 1`: toy `2000..2009` → C2S `000D`
  - `case 2`: gym `2500..2507` → C2S `000E`
  - `case 7`: energy `5000..5002` → C2S `000F`
- 따라서 effect byte 값 `1`, `2`, `7`은 toy/gym/energy domain 번호가 아닙니다. 이 값들이 item ID 인자로 들어가면 모두 furniture `case 0`입니다.

이 구분이 `S2C 0007 +0x125`를 toy/gym loadout 복원 필드로 잘못 쓰는 것을 막습니다.

## 2. `S2C 0007 +0x125..+0x12F` exact 계약

`HandleS2C_0007_LoadSetupBlob@0059E330`은 다음 루프를 실행합니다.

```text
for i = 0..10:
    DomainCode_EmitLocalEffect(zero_extend_u8(payload[0x125+i]))
```

- **VERIFIED:** 정확히 **11행 × u8**입니다.
- **VERIFIED:** 행 위치는 별도 인자로 전달되지 않습니다. 각 바이트는 독립적인 absolute item-ID command이며 row index 자체의 소비 의미는 없습니다.
- **VERIFIED:** 표현 가능한 live item ID는 `0..255`뿐입니다. 현재 카탈로그에서 이는 furniture `0..32`뿐입니다.
- **VERIFIED:** `0xFF`는 classifier가 `-1`을 반환하여 아무 효과·송신도 만들지 않는 안전 nop입니다.
- **VERIFIED:** toy `2000+`, gym `2500+`, energy `5000+`는 이 필드에 절대 표현할 수 없습니다. 하위 8비트으로 잘라 쓰면 전혀 다른 furniture ID가 됩니다.

별도 furniture UI 테이블 `DAT_006DA248`은 11개 logical group을 다음처럼 묶습니다.

| group | UI button pair | furniture IDs |
|---:|---:|---:|
| 0 | `EE/EF` | `0,1,2` |
| 1 | `F0/F1` | `3,4,5` |
| ... | ... | ... |
| 10 | `102/103` | `30,31,32` |

이 표와 effect-byte 수가 모두 11인 것은 furniture 활성 상태와 구조적으로 수렴합니다. 다만 loader는 row index를 사용하지 않으므로 “wire row N은 반드시 furniture group N”이라는 더 강한 순서 규칙은 **INFERRED**로만 둡니다.

## 3. direct caller/xref 전수 결과

구현 본체 `0059A6E0`은 thunk `004D746A` 하나로 들어갑니다. thunk의 direct xref를 전수하면 다음 네 callsite뿐입니다.

| caller | 전달 가능한 item ID | 결과 |
|---|---|---|
| `HandleS2C_0007_LoadSetupBlob@0059E330` | u8 `0..255` | furniture 또는 nop만 도달 |
| `FUN_005BBC00` callsite 2개 | furniture container `model+0x334`에서 열거한 `0..32` | furniture만 도달 |
| `FUN_005BC970` | energy list `model+0x2E4`, `5000..5002` | `000F` 도달 |

간접 data-reference나 다른 full-width UI caller는 없습니다. 구현 본체에 대한 유일한 xref도 thunk입니다.

### 3.1 상위 UI gate `FUN_005BAF60`

- `FUN_005B0100()!=0`: UI/button queue가 활성 상태여야 합니다.
- `ButtonQueue_Pop`이 button ID와 event type을 꺼냅니다.
- global/modal gate `FUN_005BB5A0()==0`이어야 commit callback을 호출합니다.
- event type `2`에서:
  - `EE..103` → `FUN_005BBC00` (furniture)
  - `104..107` → `FUN_005BC970(...,2)` (energy use)
- 함수 본문에 scene/room 번호 검사는 없습니다. 실제 Plaza에서 같은 `내 인벤토리` 패널이 열렸으므로 PatHouse 복귀는 필요하지 않습니다.

### 3.2 `FUN_005BBC00`은 toy/gym handler가 아님

`FUN_0059AF50/0059AF90`은 `model+0x334` furniture container만 열거합니다. `DAT_006DA248`도 item ID `0..32`만 가집니다. 따라서 기존 content/66의 “인벤토리 슬롯핸들러”라는 넓은 이름은 맞지만, 이를 toy/gym producer로 읽으면 안 됩니다.

### 3.3 `FUN_005BC970`은 natural energy UI

- `model+0x2E4` 목록을 최대 4개씩 표시합니다.
- `FUN_005BC6F0`은 ID `5000/5001/5002`만 해당 icon을 enable합니다.
- pending item이 없어야 하고(`model energy subobject +0x25 == -1`), 소유 수량이 양수여야 합니다.
- `this+0x46D==0`과 게임시간 비율 gate를 통과한 뒤에만 `DomainCode_EmitLocalEffect(full_item_id)`를 호출합니다.
- 현재 canonical energy 수량은 모두 0이므로 `000F`를 자연 발생시킬 수 없습니다.

## 4. C2S payload 생성 규칙

### C2S `000D` toy — sender body VERIFIED, shipped producer unreachable

1. full-width toy ID `2000..2009`가 `0059A6E0`에 들어옵니다.
2. `model+0x3D4` container vfunc `+4(item_id,1)`이 소유/활성 설정에 성공해야 합니다.
3. `FUN_0059C790`이 active flag `1`인 entry를 container 순서대로 순회합니다.
4. 각 byte는 `item_id - container_base(2000)`, 즉 local index `0..9`입니다.
5. sender는 serializer 반환 count를 무시하고 stack buffer 앞 **4바이트를 고정 송신**합니다.

기본 활성은 local `1,4,7` 세 개이므로 네 번째 바이트는 네 번째 활성 아이템이 없을 때 미초기화 residue입니다. 서버가 앞 세 개를 권위로 검증하고 네 번째는 ordered/owned일 때만 받는 현행 정책이 맞습니다.

### C2S `000E` gym — sender body VERIFIED, shipped producer unreachable

1. full-width gym ID `2500..2507`가 들어와 `model+0x426` 활성 vfunc가 성공해야 합니다.
2. 같은 serializer가 `item_id-2500` local index를 ascending entry order로 씁니다.
3. 앞 **3바이트를 고정 송신**합니다.

기본 활성 local `0,3,6`과 exact 3B가 일치합니다.

### C2S `000F` energy — natural UI reachable

1. full-width energy ID `5000..5002`가 들어오고 기존 pending이 없어야 합니다.
2. 소유 수량이 양수이면 `FUN_0059BFC0(0,item_id)`이 pending ID만 설정합니다.
3. `item_id-5000` local index 1B를 송신합니다.
4. 클라이언트는 S2C `0009[00 0F]` 성공 ACK 전에는 수량을 줄이지 않습니다.

## 5. 동적 수렴

- **VERIFIED live:** 최신 Plaza healthy 클라이언트에서 `내 인벤토리` toy 탭의 기본 소유 슬롯을 선택하고 패널을 닫은 이전 실행에서 C2S `000D/000E/000F`는 0건이었습니다(91).
- **VERIFIED live follow-up:** UI 입력을 중단한 뒤 seq `254..323`은 C2S/S2C heartbeat `0016` 각 35건뿐이었고, C2S `000D/E/F`, S2C `0009`, non-heartbeat는 모두 0건이었습니다. canonical SHA, 파일 크기, currency 950, energy all-zero, Plaza healthy가 불변이었습니다.
- 이는 “commit gesture를 아직 못 찾음”이 아니라, shipped toy/gym UI producer 부재라는 static callgraph와 수렴합니다.

## 6. 서버 계약 리뷰·수정

현행 `azrok_server.py`의 C2S decoder/handler는 다음 면에서 맞습니다.

- **VERIFIED contract:** `000D=4B`, `000E=3B`, `000F=1B` exact length/range 검증.
- **VERIFIED contract:** toy/gym은 quantity 소비 없이 active snapshot만 canonical 저장.
- **VERIFIED contract:** energy만 copy-on-write 감소 → atomic JSON 성공 뒤 `S2C 0009[00 0F]`.
- **VERIFIED contract:** 실패 status wire가 없으므로 forged/stale request에 ACK를 만들지 않는 fail-closed 정책.
- **VERIFIED contract:** toy 네 번째 residue를 owned/ascending일 때만 채택.

수정 사항:

- decoder와 builder 주석에 toy/gym sender body와 shipped UI reachability를 분리했습니다.
- S2C builder가 canonical `active_loadouts.toy/gym`을 `+0x125`로 truncate하지 못하도록 FF×11 규칙을 명문화했습니다.
- nondefault toy/gym loadout이 있어도 `+0x125..12F == FF×11`이고 ownership quantity arrays만 정상 복원되는 회귀 테스트를 추가했습니다.

검증:

- `python -m py_compile azrok_server.py`: PASS
- `python -m unittest tools.test_server_contract_layers -q`: **63 PASS**
- `python -m unittest discover -s tools -p 'test_*.py' -q`: **88 PASS**

toy/gym `000D/E` decoder는 protocol compatibility를 위해 유지합니다. 아직 발견되지 않은 서버 이벤트/다른 빌드가 이 exact sender body에 full-width ID를 줄 가능성은 있으나, 현재 shipped UI가 이를 생성한다고 주장하지 않습니다.

## 7. 후속 동적 절차

### 비파괴 reconnect 음성 대조 — 권장

1. 현재 canonical SHA/size/currency/inventory를 checkpoint합니다.
2. 정상 fresh reconnect에서 S2C `0007`을 한 번만 수신합니다.
3. payload `+0x125..12F == FF×11`, toy/gym quantity arrays가 canonical과 일치하는지 캡처합니다.
4. setup 직후 C2S `000D/E`가 0건인지 확인합니다.
5. Plaza healthy와 canonical checkpoint 불변을 확인합니다.

이 결과의 기대값은 **000D/E 무발생**입니다. FF effect-byte setup을 “natural roundtrip이 실패했다”고 오판하면 안 됩니다.

### sender body ABI 양성 대조 — disposable profile만

정말 `0059A6E0`의 dormant toy/gym branch를 live 확인하려면 disposable client/profile에서 ownership을 먼저 검증하고 함수에 full-width `2001` 또는 `2500`을 직접 한 번 호출해 C2S payload를 관찰해야 합니다. 이는 원본 UI 경로가 아니며 메인 사용자 저장에서는 수행하지 않습니다. 동적 확인 전 **NOT VERIFIED**입니다.

## 결론

`000D/000E`는 exact sender와 wire 형식은 존재하지만 shipped `내 인벤토리` UI에서 도달하지 않습니다. `000F`만 energy UI에서 자연 도달 가능하며 보유량/시간/pending gate가 있습니다. `S2C 0007 +0x125`는 11×u8 furniture command list이지 toy/gym loadout 복원 필드가 아닙니다. 서버는 effect bytes를 FF로 유지하고 toy/gym decoder를 future-compatible 수신 경계로만 보존해야 합니다.

Related: 84, 90, 91, content/57, content/66, content/71, protocol/49, INDEX.
