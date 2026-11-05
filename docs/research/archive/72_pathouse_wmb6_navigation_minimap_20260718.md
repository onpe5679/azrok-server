# PatHouse WMB6 navigation minimap (2026-07-18)

> **SUPERSEDED by 73.** 이 문서는 `0x84` 크기의 마지막 WMB 모델 레코드를
> 해석하지 못해 실제 외출 게이트 `gate_mun_MDL_048`을 지도에서 누락했고,
> 욕실 내부문 `dm_door_0003_057`을 외출문으로 잘못 단정했다. 당시 오인의
> 원인과 증거를 보존하기 위해 본문은 수정하지 않고 보관한다.

사용자가 화면상 실제 출구가 훨씬 왼쪽에 있다고 교정하고 미니맵 기반
판단을 제안했다. 이 문서는 원본 자산을 복제하지 않고 `room.wmb`의 배치
메타데이터만 추출해 이동용 도식을 만든 결과다.

## 1. WMB6 엔티티 디렉터리 (VERIFIED)

`Data/Space/PatHouse/room.wmb`를 직접 읽었다.

| 항목 | 값 |
|---|---:|
| magic | `WMB6` |
| 엔티티 디렉터리 헤더 필드 | `file+0x7C` |
| 엔티티 디렉터리 파일 오프셋 | `0x6CED44` |
| 디렉터리 길이 | `0x2EB4` (11,956 bytes) |
| 레코드 수 | 87 |
| 모델 엔티티 레코드 | 48 |
| 라이트 레코드 | 37 |
| 아직 해석하지 않은 레코드 | 2 |

이 파일에서 엔티티 오프셋 테이블은 디렉터리의 4바이트 count 다음을
기준으로 한 상대 오프셋이다. `0x88`/`0x174` 크기 레코드의 처음 9개
float는 `x,y,z / pan,tilt,roll / scale x,y,z`, 이후 영역은 이름·리소스·
WMB action 문자열이다. `0x24` 크기 37개는 위치·RGB·범위를 가진 라이트
레코드다. 이 레이아웃은 **이 PatHouse 파일에서 직접 검증**했으며 다른
WMB6 변형 전체에 대한 일반화는 아직 하지 않는다.

WMB 헤더 `+0x9C`의 6개 float도 직접 읽었다:

```text
min = (-3362, -2640, -261)
max = ( 2937,  3684,   45)
```

이는 컴파일된 월드 bounds 값이다. **walkable/collision polygon이라고
확정할 수 없다.** 따라서 SVG의 원형 footprint는 길 찾기용 추론 도식이며
JSON에도 `NOT VERIFIED collision geometry`로 명시했다.

## 2. 문과 랜드마크 좌표 (VERIFIED)

| 역할 | WMB name / resource | 월드 좌표 `(x,y,z)` | 비고 |
|---|---|---:|---|
| 실제 외부 문 mesh | `dm_door_0003_057` / `dm_door_0003.MDL` | `(-813, -107, 6.70908)` | 화면 기준 훨씬 왼쪽이라는 사용자 관찰과 일치 |
| 내부 문틀 | `doorframe_01` / `room_doorfr_02.MDL` | `(526, 802, -0.38793)` | 외출 요청 문이 아님 |
| 옷장/거울 | `mirror_01` / `room_mirr_01.MDL` | `(-336, 1152, 44.615)` | visible identity는 63에서 교정됨 |

기존 정적 타입 메타데이터도 JSON/CSV에 별도 열로 합쳤다:

- `dm_door_0003_057`: type `0x24`, static default action `0x26`.
  그러나 이 visible mesh의 실제 수동 클릭에서 자연 `C2S 0x0019`가 나간
  사실도 VERIFIED이며, 두 descriptor 사이의 정확한 provenance는 계속
  NOT VERIFIED다.
- `doorframe_01`: type `0x1F`, default action `0x26`.
- `mirror_01`: static descriptor type `0x20`, gated action `0x6F`.
  visible 외부 문과 이 descriptor의 정확한 binding은 NOT VERIFIED다.

미니맵에서는 이 셋을 각각 빨강 별, 청록 마름모, 주황 표식으로 분리한다.
월드 XY 기준 실제 외부 문은 내부 문틀보다 `x=-1339`, `y=-909`만큼
왼쪽·아래에 있다. 화면을 조금 왼쪽으로 찍는 수준이 아니라, 방 중앙 가구
군집에서 **서쪽(음의 X)으로 크게 이동**해야 한다는 판단 근거다.

## 3. 생성 도구와 산출물 (VERIFIED)

도구:

```text
tools/wmb6_minimap.py
tools/test_wmb6_minimap.py
```

생성 명령:

```powershell
python tools\wmb6_minimap.py Data\Space\PatHouse\room.wmb `
  --output-dir artifacts\minimap
```

산출물:

```text
artifacts/minimap/room_minimap.svg
artifacts/minimap/room_minimap.json
artifacts/minimap/room_minimap.csv
```

- SVG는 모델/문/케어 후보를 월드 XY에 배치한 메타데이터 도식이다.
- JSON은 87개 레코드와 증거 등급, WMB header bounds, 런타임 annotation을
  보존한다.
- CSV는 동일 레코드를 디버거/스프레드시트에서 빠르게 검색하기 위한
  평면 테이블이다.
- 어느 산출물에도 원본 texture/mesh/base64 자산을 넣지 않았다.

선택적 현재 위치 overlay도 지원한다:

```json
{
  "player": {"x": -500, "y": 100, "z": 5},
  "camera": {"x": -300, "y": 300, "z": 200}
}
```

```powershell
python tools\wmb6_minimap.py Data\Space\PatHouse\room.wmb `
  --output-dir artifacts\minimap --overlay current_position.json
```

따라서 Frida/x32dbg의 read-only 좌표를 위 JSON으로 저장하면 같은 지도에
PLAYER/CAMERA 표식을 즉시 겹칠 수 있다. 입력을 넣지 않을 때는 정적 지도만
생성된다.

## 4. 검증 (VERIFIED)

```powershell
python -m unittest tools.test_wmb6_minimap -v
```

5개 테스트가 통과했다:

1. magic, 디렉터리 offset/count, header bounds;
2. 외부 문 name/resource/좌표/type/action;
3. 내부 문틀과 mirror 좌표·identity 분리;
4. SVG/JSON/CSV 생성과 SVG 내 embedded asset 부재;
5. player/camera overlay 생성.

SVG는 XML 파싱에 성공했고 `1280x960 viewBox`, 169개 도식 요소와 56개
텍스트 요소를 갖는다. 오른쪽 내부 문틀 label은 범례와 겹치지 않도록
왼쪽 정렬로 교정했다.

## 5. 다음 동적 사용

1. 현재 player/camera world 좌표를 read-only로 취득한다.
2. overlay JSON으로 지도를 재생성한다.
3. player→`(-813,-107)`의 월드 방향을 정하고 실제 이동 입력을 준다.
4. 도착 후 visible door click에서 `action 0x6F`와 자연 `C2S 0x0019`를
   함께 관측한다.

이 지도는 화면 hit-test를 대체하는 **방향 판단 도구**다. 정확한 walkable
경로/장애물 회피를 주장하려면 WMB BSP collision lump를 추가 파싱하거나
런타임 trace로 바닥 이동 가능 영역을 직접 샘플링해야 한다.
