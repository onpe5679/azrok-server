# 151 WineD3D/OpenGL PatHouse 방 부재 — 후보 축소와 결정적 실험 2개

Date: 2026-07-19
Author: Claude (조사 레인)

> **번호 주의**: Codex 가 146~148 을 썼고 149 를 쓰고 있을 수 있다. 충돌 회피로 151 을 잡았다.
> (150 = 웹 백엔드 설계, 같은 조사 레인)

Status: **원인 미확정.** 후보 하나를 배제했고, 그것을 가르는 실험 2개를 확보했다.
**이 문서는 실행하지 않은 조사 결과다.** 실측은 아직 없다.

---

## 1. 문서 139 의 "invalid zero-width map 816건" — 배제 (INFERRED, 확신 높음)

내가 "가장 구체적인 신호" 라고 지목했던 단서인데, **노이즈로 보인다.**

**실제 로그 원문** (문서 139 의 요약 표현이 부정확했다):
```
0024:warn:d3d:wined3d_resource_check_box_dimensions Box (0, 0, 0)-(0, 1, 1) is invalid.
0024:warn:d3d:wined3d_device_context_map Map box is invalid.
```
근거: `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_d3d_scene_0431_stdout.log:552145-552146`

**세 카운트가 정확히 일치한다 (VERIFIED)**:
| 항목 | 건수 |
|---|---:|
| `Map box is invalid` | 816 |
| `Box (0, 0, 0)-(0, 1, 1) is invalid` | 816 |
| `d3d9_*buffer_Lock` 의 `offset 0, size 0` 호출 | 816 (인덱스 141 + 버텍스 675) |

**정체**: D3D9 관례상 `Lock(0, 0, ...)` 은 **"버퍼 전체를 잠근다"** 는 뜻이다.
그런데 Wine 의 `dlls/d3d9/buffer.c` 는 이 관례를 특별 처리하지 않고 그대로
`wined3d_box_set(&box, 0, 0, 0, 1, 0, 1)` 을 만들어, `dlls/wined3d/resource.c` 의
`wined3d_resource_check_box_dimensions` 가 폭 0 짜리 퇴화 박스로 보고 WARN 을 찍는다.

**왜 무해한가**:
1. 로그상 이 WARN 뒤에도 map 이 **중단되지 않고 정상 완료**된다 —
   `buffer_resource_sub_resource_map Returning memory at 08441F10` (유효 포인터 반환)
2. 실제 GPU 업로드 경로인 `dlls/wined3d/buffer.c` 의 `buffer_invalidate_bo_range()` 에는
   이 관례를 아는 분기가 있다:
   `if (!offset && (!size || size == buffer->resource.size)) goto invalidate_all;`
   → 버퍼 전체를 dirty 처리해 다음 draw 전에 재업로드한다.

**즉 박스 검증 계층만 관례를 모르고, 실제 데이터 경로는 올바르다.**
완전 배제는 아니다(맵 전후 바이트를 직접 덤프해 확증하지 않았다). **"유력하게 배제"** 로 표기한다.

---

## 2. 새로 확인된 구조적 사실 (VERIFIED)

**Wine 9.9(2024-05)에서 GLSL 이외의 고정기능 경로가 전부 제거됐다.**
GL FFP vertex/fragment pipeline, NV_register_combiners, ATI_fragment_shader,
ARB_fragment_program 블리터, ARB 셰이더 백엔드 — 전부 삭제.

→ **Wine 11 의 OpenGL 렌더러에는 고정기능 구현이 `glsl_shader.c` 의 GLSL 생성 방식 단 하나뿐이다.**
   "arb vs glsl 백엔드를 바꿔보라" 는 옛 조언은 이 버전에 적용되지 않는다.

---

## 3. ★ 레버리지 — `ffp_hlsl` (VERIFIED, 커밋 확인)

커밋 `ff43072` (2024-11-19) — *"wined3d: Allow using the HLSL FFP replacement with GL"*

**같은 GL 렌더러 안에 완전히 독립적인 두 번째 고정기능 구현체가 있다.**
HLSL 로 FFP 를 기술해 SM2 바이트코드로 컴파일한 뒤 일반 셰이더처럼 처리하는 방식이다.
**기본값 비활성, GL 렌더러에서만 의미 있음.**

→ **레지스트리 값 하나로 FFP 셰이더 생성기를 통째로 갈아끼워 비교할 수 있다.**

---

## 4. BoxedWine 계층 (VERIFIED)

- BoxedWine 은 **순정 업스트림 Wine 을 쓴다.** `tools/buildWine/wine_builds.json` 이
  `wine-mirror/wine.git` 을 가리키고, `source/` 안에 `wined3d`/`d3d9` 코드가 **0건**,
  8개 패치 중 렌더링 로직에 손댄 것도 **없다**
- 그러나 **BoxedWine 자체 GL 마샬링 계층은 경로에 실제로 관여한다** —
  TinyCore 게스트 안에서 호스트의 진짜 `NVIDIA GeForce RTX 5090` 문자열이 나온 것이
  직접 증거다(문서 139)

→ 따라서 "실패가 wined3d 가 아니라 그 아래 BoxedWine GL 패스스루" 라는 가설의 **전제는 성립한다.**
   다만 그 계층에 이 실패와 연결되는 버그가 있다는 직접 증거는 **못 찾았다.**

---

## 5. 남은 후보 3개 (전부 NOT VERIFIED)

1. `glsl_shader.c` 의 FFP 생성기가 **이 워크로드**(`SetMaterial` 70,045 / `SetLight` 6,415 /
   `LightEnable` 4,072 / `SetTextureStageState` 51,187 = 극단적으로 무거운 레거시 조명·텍스처스테이지)
   에서 갖는 특정 버그
2. BoxedWine 자체 GL 마샬링 계층의 결함
3. 호스트 NVIDIA GL 드라이버와 이 FFP 셰이더 조합의 상호작용

**이 셋을 가르는 알려진 버그 리포트는 웹 조사로 찾지 못했다(NOT FOUND).**
WineHQ bugzilla 전체 검색, freedesktop bugzilla, FreeBSD 포럼 — 일부는 403/로그인 요구로
본문 접근 불가라 완전 배제는 아니다.

**DXVK 와의 알려진 차이점** (VERIFIED, 부분): 알파 테스트(DXVK 가 NVIDIA 동작에 맞춰 변경한 이력),
컬러키 투명(D7VK 1.4 가 "주요 그래픽 버그 수정" 명시). 깊이 NDC 규약 차이는 이론적으론 유명하나
**wined3d 가 수천 개 D3D9 게임에서 이미 올바르게 변환해 왔으므로 이 실패의 원인일 개연성은 낮다**(INFERRED).

---

## 6. 다음 실험 — 실행 환경 가진 쪽(Codex)에 넘길 것

### 실험 A (최우선, 가장 쌈) — `ffp_hlsl` 토글
같은 하네스, `renderer=gl` 유지, 레지스트리 값 하나 추가:
```
HKCU\Software\Wine\Direct3D
    renderer   REG_SZ    gl
    ffp_hlsl   REG_DWORD 1
```
```
Azrok.exe -NX 200 -NWND -PL d3d_scene_ffphlsl -DIR localauth -IP 127.0.0.1:9200
```
**관찰**: PatHouse 진입 시 방이 보이는가?
- **보이면** → 원인이 기본 GLSL FFP 생성기로 좁혀진다.
  그리고 **우리 WebGL2 백엔드 설계에 직접적인 교훈**이 된다 —
  "조명/머티리얼 상태 조합에서 같은 실수를 하지 마라"
- **안 보이면** → 원인이 FFP 생성기보다 아래(공통 버퍼/텍스처 업로드, 드라이버, BoxedWine 마샬링)

### 실험 B (두 번째, 가장 결정적) — 실패한 드로우의 GLSL 소스를 직접 읽기
```
WINEDEBUG=+d3d9,+d3d,+d3d_shader
```
`shader_glsl_dump_program_source` 가 `d3d_shader` 채널에서 활성화되어,
**wined3d 가 그 순간 실제로 컴파일한 FFP 셰이더 소스 전문을 로그에 덤프한다**(VERIFIED, 함수 존재 확인).

**관찰**: 573회 `DrawIndexedPrimitive` 중 **2,068 삼각형 드로우**(stage-0 텍스처 non-null,
`ZENABLE`=1) 직전에 생성된 프래그먼트 셰이더를 찾아, 텍스처 유닛 바인딩 / 라이트 개수 클램프 /
알파테스트·컬러키 분기 / 조기 discard 가 잘못돼 있는지 **코드를 눈으로 확인**.

추론이 아니라 **실제 실행되는 셰이더 코드를 직접 보는 방법**이라 가장 결정적이다.

### 실험 C — 드라이버 배제
`MaxVersionGL` REG_DWORD 를 낮춰(예: `30`) 재실행. 동일하게 안 보이면 GL 버전/확장 의존 버그 배제.

### 실험 D — BoxedWine 계층 분리 (비쌈, A/B 후에만)
동일 게스트 FS + 동일 레지스트리를 **BoxedWine 이 아닌 일반 리눅스 네이티브 Wine 11** 로 옮겨 실행.
안 보이면 순수 wined3d/드라이버, 보이면 BoxedWine GL 패스스루가 원인.

---

## 7. 이 결과가 웹 이식 판단에 갖는 의미

- **우리 백엔드(A방식)로 가면** 이 원인은 **"우리가 피해야 할 것"** 의 목록이다. 실험 A/B 가
  그 목록을 구체화해준다. 특히 B 는 실패한 셰이더를 직접 보여주므로 값이 크다
- **BoxedWine GL 채널을 여는 싼 경로로 가면** 이건 **반드시 고쳐야 할 차단 요인**이다.
  브라우저엔 Vulkan 이 없어 이 경로 외에 대안이 없기 때문이다
- 어느 쪽이든 **실험 A 와 B 는 값이 있다.** 다만 지금은 사용자 지시("웹 이식 최우선,
  콘텐츠 QA 최소화")에 따라 Codex 가 웹 트랙에 있으므로, **이 실험들은 큐에 둔다.**

## 8. 근거 파일

- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_d3d_scene_0431_stdout.log` (816건 근거, 552139-552154)
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/tools/buildWine/wine_builds.json`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/source/opengl/` (glMarshal.cpp, glcommon.cpp)
- Wine 소스(웹): `dlls/d3d9/buffer.c`, `dlls/wined3d/resource.c`, `dlls/wined3d/buffer.c`,
  `dlls/wined3d/wined3d_main.c`, Wine 9.9 changelog, 커밋 `ff43072`
- 관련 문서: 139(방 부재 관측), 141(Vulkan 정상 렌더), 143, 150(웹 백엔드 설계)
