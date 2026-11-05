# 153 웹 이식 후보 비교 — 아침 판단용 한 장 요약

Date: 2026-07-19

> **2026-07-19 UPDATE (159-161):** the stale bridge rows below are superseded.
> The full guest PE -> BoxedWine C++ -> JavaScript -> guest EAX round trip is
> VERIFIED by 159. Browser WebGL2 clear/triangle on the existing shared canvas,
> guest `EAX=0x3001`, and exit 0 are VERIFIED by 160. A native-loaded x86
> `d3d9.dll` COM/vtable smoke is VERIFIED by 161. The active next gate is the
> measured Gate 1 method/resource surface, not another transport experiment.
Author: Claude (조사 레인 6개 종합)

> **번호**: 150·151 = Claude 조사 레인, 152 = Codex(2c 스모크). 153 을 잡는다.

Status: **결정 재료.** 경로 선택은 하지 않는다. 사실과 미지수를 나란히 놓는다.

---

## 0. 밤새 바뀐 것 3줄

1. **브라우저 BoxedWine 이 clean named-CLI Azrok 를 실제로 돌린다 — 87~122 MIPS burst.** (157)
2. **PE guest `CD 9A` -> BoxedWine host callback -> EAX 왕복이 성공했다.** (158)
3. **x87 에서 BoxedWine 이 v86 보다 구조적으로 빠르다.** JIT 유무보다 이게 더 크게 작용할 수 있다

---

## 1. 후보 비교표

| 항목 | **BoxedWine (웹)** | **v86** |
|---|---|---|
| 정수 CPU | 순수 인터프리터 (JIT 없음) | **x86→wasm JIT** |
| 정수/기동 실측 | **135 MIPS** (10만회 루프), notepad 91 MIPS, clean Azrok **87~122 MIPS burst** | **수치 없음** (세상에 존재 안 함) |
| **x87 산술** | **인라인 네이티브 `double`** (`useF64=true`) | **전부 SoftFloat 함수 호출** |
| x87 근거 | `ksystem.cpp:70-74` + `emscripten/makefile:110` 에 `BOXEDWINE_X64` 미정의 | `docs/how-it-works.md:80-81` 메인테이너 명시, `softfloat.rs:213-252` 네이티브 폴백 **없음** |
| x87 정확도 | **53비트 고정** (PC 비트 무시) | **80비트 정확** (PC 비트 반영) |
| **정확도 실제 영향** | **없음 — 안전(155)** ⬆ 게임 CRT 가 시작 시 PC 를 **53비트로 낮춘다.** 호스트 네이티브 double 이 실하드웨어와 **비트 동일** | **무의미** — 게임이 53비트로 도는데 80비트 정확도는 값이 없다 |
| 게스트 OS | Wine (진짜 Windows 아님) | **진짜 Win95/98/ME/NT/2000 부팅** |
| 브리지 | **guest PE→host callback+EAX 성공. JS 배선만 남음** ⬆ | **공개 API 존재** |
| 브리지 상세 | 기존 no-op **`INT 0x9A`** 슬롯에 독립 `BOXEDWINE_D3D9WEB` 분기를 추가. native x64 JIT에서 x86 PE의 index/args와 EAX 왕복을 직접 실증(158). **네트워크는 emscripten 에서 명시적 비활성** | `read_memory`/`write_memory`(물리주소) + `net0-send` 초인종. 포크·드라이버 불필요 |
| 브리지 미해결 | host C++ callback→JavaScript copied bytes, 그 다음 WebGL2 | **가상 → 물리 주소 변환** |
| 렌더 결함 | WineD3D GL 경로가 PatHouse 방을 못 그림(139) — **단 A방식이면 우회** | 해당 없음 (Wine 자체를 안 씀) |
| 선례 | Wine 경로는 성숙, 단 3D 미지원 확정 | **우리 같은 시도 전무.** virtio-gpu 요청은 2015년부터 미구현 |
| 이미지 준비 | 기존 하네스 **이미 동작 중** | Windows 이미지를 직접 제작해야 함(공식 배포 없음) |

### 핵심 트레이드오프
**v86 은 정수에서 JIT 로 앞서지만, `acknex.dll` 은 x87 지배적이다**
(`FADDP` 3,693 대 `ADDSS` 43 ≈ 85:1). 그 x87 을 v86 은 SoftFloat 로, BoxedWine 은
네이티브 double 로 처리한다. **어느 쪽이 총합에서 이기는지는 실측 전까지 알 수 없다.**

---

## 2. 우리 백엔드(A방식) 진척 — 호스트와 무관하게 살아남는 자산

| 컴포넌트 | 상태 | 호스트 독립성 |
|---|---|---|
| 셰이더 (D3D9 FF → GLSL ES 3.00) | **실제 드라이버 컴파일·링크 성공** (Chrome/ANGLE/RTX 5090 + SwiftShader). 228 유니폼 / 16 속성 / 5 블록 | 완전 독립 |
| 게스트 `d3d9.dll` (COM/상태/직렬화) | 미착수. 프로브(`d3d9proxy.cpp`)가 vtable 후킹 인프라를 이미 증명 | **완전 독립** |
| 명령 ABI | Codex 설계 중 (문서 147) | 스펙은 독립 |
| 호스트 JS (디코드/FF/WebGL2) | 유니폼 패킹 진행 중 | 브라우저 간 재사용 |
| **브리지** | Phase 0 성공(158); Emscripten→JS 미검증 | **여기만 호스트별 재작성** |

**실측 API 계약**: 호출 56개 / 미호출 80개 / 셰이더 0개 / 렌더타깃 전환 0회 /
프레임당 드로우 55 · 상태변경 560.

### 셰이더에서 실제 드라이버가 잡아준 것 (파서로는 못 잡던 것)
1. `#version 300 es` 가 문자 그대로 첫 줄이어야 함 (ANGLE)
2. `MAX_VERTEX_ATTRIBS` 실측 **16** → 18개에서 축소, 상호배타 쌍 앨리어싱
3. **서로 다른 스테이지의 익명 uniform 블록이 같은 필드명을 못 씀** —
   **Vulkan/SPIR-V 엔 대응물이 없는 오류.** DXVK 는 스테이지를 링크하지 않으므로
   **DXVK 포팅에서 체계적으로 발생한다**
4. varying 에 `layout(location=N)` 금지

---

## 3. 미해결 항목 (전부 NOT VERIFIED)

1. **Azrok 렌더 워크로드의 브라우저 FPS** — clean CLI startup은 87~122 MIPS burst로 VERIFIED지만
   아직 WebGL Present가 없으므로 실제 렌더 프레임 비용은 미측정이다.
2. **BoxedWine host callback→JavaScript 전달** — `INT 0x9A` guest PE→host callback과 EAX는
   end-to-end VERIFIED(158). copied bytes를 Emscripten JS로 넘기는 나머지 절반이 NOT VERIFIED다.
3. **v86 가상→물리 주소 변환** — 후보 3개(E820 예약 / VGA 애퍼처 / 최소 드라이버) 전부 미검증
4. **x87 53비트 고정의 실제 영향** — 3D 변환·조명 연쇄에서 누적될 수 있음.
   `FUCOMPP` 472회의 비교 분기 뒤집힘 가능성. 별도 조사 진행 중
5. **`SetTransform`은 64/64 테이블을 채움** (154). 실제 값은 fixed 2/3과
   world matrix `256..317`로, 최소 62개 world matrix를 쓴다. 64 초과 여부는 아직 미확인이고
   셰이더 `worldViewArray[64]`의 여유가 2칸뿐이라 expanded-cap 재측정 가치가 있다.
6. **P8 / DXT** — 캐릭터 선택 장면에서는 둘 다 **0회**(154). 관측 포맷은
   21/22/23/26뿐이다. 후속 PatHouse/Plaza가 새 포맷을 도입하는지는 NOT VERIFIED다.

---

## 4. 값싼 다음 실험 (비용 오름차순)

| # | 실험 | 답하는 것 | 담당 |
|---|---|---|---|
| 1 | clean named-CLI Azrok MIPS | **완료(157): 87~122 MIPS burst, 흰 화면** | Codex |
| 2 | flushprobe 인자 히스토그램 (Windows 네이티브) | **완료(154): 캐릭터 선택 최소 장면** | Codex |
| 3 | guest x86 PE→`INT 0x9A`→host callback→EAX | **완료(158)** | Codex |
| 4 | host callback→JavaScript copied bytes 1회 | BoxedWine 브리지 남은 절반 | 다음 |
| 5 | `useF64` 를 뒤집은 BoxedWine A/B 빌드 | 네이티브 double vs SoftFloat **순수 효과** | 미배정 (emsdk 필요) |
| 6 | WineD3D `ffp_hlsl=1` 토글 (문서 151) | GL 방 부재의 원인이 FFP 생성기인가 | 미배정 |

**3·4 는 분리 측정한다.** 3은 완료됐고, 4가 다음 단일 게이트다.

---

## 5. 이 문서가 하지 않는 것

**현재 구현 우선순위는 BoxedWine Phase 1이다.** clean Azrok CPU 실행과 guest trap 왕복이 모두
직접 증명됐으므로, 새 인프라나 콘텐츠 QA보다 host callback→JavaScript 한 호출을 먼저 닫는다.
v86은 비교 후보로 남기되 이 단계의 진행을 막지 않는다.

## 6. 근거 문서

- 150 (백엔드 설계·API 계약), 151 (WineD3D GL 방 부재 축소 + `ffp_hlsl` 실험), 152 (2c 스모크·135 MIPS)
- 139 (방 부재 관측), 141 (Vulkan 정상), 147 (마샬링 설계), 148 (프로브 실패)
- `tools/web_backend/shaders/` (이식본 + UNIFORMS.md + PORTING_NOTES.md)
- `tools/d3d9_probe/` (프로브 3종 + README)
- 156 (worldViewArray 256 확장), 157 (clean 2c Azrok MIPS), 158 (`INT 0x9A` Phase 0)
