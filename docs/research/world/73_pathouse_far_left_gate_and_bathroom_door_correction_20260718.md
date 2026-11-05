# PatHouse far-left gate and bathroom-door correction (2026-07-18)

이 문서는 사용자의 직접 화면 관찰인 "현재 표적은 욕실문이고 실제 방 밖 문은
훨씬 왼쪽"을 출발점으로 `room.wmb`, 모델 자산, 기존 동적 산출물, Ghidra
디컴파일을 다시 대조한 결과다. 라이브 프로세스 attach, 입력 주입, 실행파일
패치는 하지 않았다.

## 1. 기존 외출문 결론은 틀렸다 (VERIFIED)

기존 63/72는 `dm_door_0003_057`을 외출문으로 단정했다. 그러나 이 레코드는
다음 욕실 오브젝트 군과 같은 공간에 있다.

| WMB name | resource | world `(x,y,z)` |
|---|---|---:|
| `shower_01` | `room_shower_01.MDL` | `(-1393, 34, 7.518)` |
| `boiler_01` | `room_boiler_01.MDL` | `(-1455.5, -95, 1.230)` |
| `bathbox_01` | `room_bathbox_1.MDL` | `(-1077, 288, 11.998)` |
| `bathcase_01` | `room_bathfuni_01.MDL` | `(-886, -395, 1.100)` |
| `dm_door_0003_057` | `dm_door_0003.MDL` | `(-813, -107, 6.70908)` |

- **VERIFIED (사용자 실측):** 반복해서 향한 화면 오른쪽 문은 외출문이 아니라
  욕실문이다.
- **VERIFIED (WMB):** `dm_door_0003_057`은 욕실 오브젝트 군에 붙어 있다.
- **VERIFIED (기존 동적 산출물):** 이 좌표의 투영은 당시 화면
  `x=837..883` 부근, 즉 오른쪽이었다.

따라서 `dm_door_0003_057 = outside exit`은 폐기한다. 이전 수동 외출 성공과
이 레코드의 이름을 시간상 연관 지은 것이 오인의 원인이었다.

## 2. 누락됐던 far-left gate 레코드 (VERIFIED WMB / INFERRED role)

기존 파서는 모델 레코드 크기를 `0x88`/`0x174`만 허용했다. 실제
`room.wmb`의 마지막 레코드는 같은 transform/string prefix를 쓰는 `0x84`
모델 레코드라서 `unknown`으로 버려졌다.

| 항목 | 값 |
|---|---|
| record index | `86` (87개 중 마지막) |
| directory-relative offset | `0x2E2C` |
| file absolute offset | `0x6D1B74` |
| byte size | `0x84` |
| name | `gate_mun_MDL_048` |
| resource | `gate_mun.MDL` |
| world `(x,y,z)` | `(522, 801, 126)` |
| pan/tilt/roll | `(0,0,0)` |
| scale | `(1,1,1)` |

바로 옆에는 다음 프레임 레코드가 있다.

| record | resource | world `(x,y,z)` | distance in XY |
|---|---|---:|---:|
| `gate_mun_MDL_048` | `gate_mun.MDL` | `(522,801,126)` | - |
| `doorframe_01` | `room_doorfr_02.MDL` | `(526,802,-0.38793)` | `4.12` |

- **VERIFIED:** 두 레코드는 사실상 같은 XY에 배치된 gate/frame assembly다.
- **VERIFIED:** `gate_mun.MDL`의 추출 texture는 외부 풍경이 보이는 게이트
  형태이고, `dm_door_0003.MDL`은 작은 내부문/트리거 자산이다.
- **VERIFIED:** 당시 PatHouse camera pan은 `270`이었고, `dm_door`의 실제
  투영은 오른쪽이었다.
- **INFERRED (strong):** world `+X` 쪽의 `gate_mun` assembly가 사용자가
  지적한 화면 far-left 외출문이다. exact screen projection과 실제 클릭은
  주 분석 스레드에서 동적으로 확정해야 한다.

## 3. Ghidra action binding 재감사

`FUN_00557570`과 `FUN_0055AE90`을 Ghidra MCP로 다시 디컴파일했다.

### VERIFIED

- `FUN_00557570`의 PatHouse 이름/type table에는
  `dm_door_0003_057 -> type 0x24`, `doorframe_01 -> type 0x1F`,
  `mirror_01 -> type 0x20`이 있다.
- `FUN_0055AE90`에서 type `0x24`와 `0x1F`는 전용 case가 없어 기본 action
  `0x26`으로 남는다.
- type `0x20`은 `ProtocolState+0x130 != 0`이면 action `0x6F`를 반환한다.
- `Azrok.exe` 문자열 검색 결과 `gate_mun`은 0건이고,
  `dm_door_0003_057 @ 0x006A41DC`, `mirror_01 @ 0x006A40D8`만 존재한다.
- action `0x6F`의 완료 경로는 `FUN_0055BBB0/FUN_0055CBC0 ->
  FUN_00568710 -> FUN_00594820 -> C2S 0x0019`이다.

### NOT VERIFIED

- visible `gate_mun` surface가 왜 `mirror_01`/type `0x20`의 hit identity로
  분류되는지, 또는 게이트 앞 별도 surface/trigger가 type `0x20`을 내는지.
- `gate_mun` 자체는 executable name table에 없으므로 이름만으로 action
  `0x6F`라고 단정할 수 없다.

따라서 "보이는 게이트 = mirror descriptor"도 아직 단정하지 않는다. 다음
동적 확인은 `gate_mun`/`doorframe` 투영점 주변에서 `FUN_0055AE90 == 0x6F`를
직접 측정해야 한다.

## 4. 미니맵 교정 (VERIFIED)

`tools/wmb6_minimap.py`가 `0x84` compact model record를 해석하도록 수정됐다.
분류와 범례도 다음처럼 교정했다.

- 빨강: `gate_mun_MDL_048` outside-gate candidate `(522,801)`
- 청록: colocated `doorframe_01` `(526,802)`
- 파랑: 욕실 내부문 `dm_door_0003_057` `(-813,-107)`
- 주황: wardrobe/mirror `mirror_01` `(-336,1152)`

재생성 산출물:

```text
artifacts/minimap/room_minimap.svg
artifacts/minimap/room_minimap.json
artifacts/minimap/room_minimap.csv
```

`python -m unittest tools.test_wmb6_minimap -v`의 5개 테스트가 통과했다.
SVG/JSON/CSV에는 배치 메타데이터만 있고 원본 mesh/texture는 포함하지 않는다.

## 5. 문서 권위 교정

- 72는 전체 미니맵 결론을 이 문서가 대체하므로 `SUPERSEDED` 처리 후
  `archive/`로 보존한다.
- 63의 Plaza 전환/health 증거는 유효하지만 §6 visible identity만 이 문서가
  대체한다.
- 54/60/62의 `dm_door = visible exit` 보조 문구도 73 기준으로 교정한다.

다음 동적 순서는 `gate_mun` world-to-screen -> 주변 `0x6F` hit-only scan ->
실제 클릭 -> 자연 `C2S 0x0019` 확인이다. `dm_door` 오른쪽 표적은 더 이상
외출 경로로 사용하지 않는다.
