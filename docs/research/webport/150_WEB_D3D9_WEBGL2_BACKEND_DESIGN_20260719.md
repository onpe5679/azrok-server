# 150 웹 이식: d3d9 → WebGL2 백엔드 설계

Date: 2026-07-19

> **2026-07-19 UPDATE (159-161):** the guest PE -> BoxedWine C++ -> JavaScript
> -> guest EAX transport is VERIFIED by 159. Document 160 additionally verifies
> WebGL2 clear/triangle on the existing single 800x600 canvas, `EAX=0x3001`, and
> exit 0. Document 161 verifies a native-loaded x86 `d3d9.dll` COM/vtable smoke
> through `Present`. The active next gate is measured method/resource expansion.
> The stale canvas/transport NOT VERIFIED wording below is superseded.
Author: Claude (게이트 1 실측 기반)

> **번호 주의**: 145 다음이지만 Codex 가 OX 결론 문서를 146~149 로 쓰고 있을 수 있어
> 충돌 회피로 150 을 잡았다. INDEX 등록 시 확인할 것.

Status: **설계 문서.** 구현 전. 사실 표기는 VERIFIED / INFERRED / NOT VERIFIED 로 구분한다.

---

## 1. 왜 이 문서가 필요한가 — 기성품 경로가 없다 (VERIFIED)

BoxedWine 브라우저(WASM/emscripten) 빌드는 **3D 를 지원하지 않는다.** 추정이 아니라 확인이다.

메인테이너 danoon2 본인:
> "The web version **definitely does not support 3d graphics.** So far we haven't found a way
> to map OpenGL to WebGL and Wine converts Direct3D to OpenGL." (2024-05-28, issue #94)
> "3D graphics are not supported in the web/emscripten build." (2025-01-06, 같은 이슈 최종 코멘트)

로컬 소스 스냅샷(26R1)도 일치:

| 사실 | 근거 |
|---|---|
| `BOXEDWINE_VULKAN` 이 emscripten makefile 에 **없음** (msvc/xcode 에만 정의) | `project\emscripten\makefile:110` / `project\msvc\...\BoxedWine.vcxproj:337,441,728` |
| → `source/vulkan/*` 전부 빈 껍데기로 컴파일. **브라우저에서 Vulkan/DXVK 불가** | `source\vulkan\vulkancommon.cpp:20` 등 `#ifdef BOXEDWINE_VULKAN` 가드 |
| `BOXEDWINE_OPENGL_SDL` 도 emscripten makefile 에 **없음** (linux makefile 엔 있음) | `project\linux\makefile:108` vs `project\emscripten\makefile:110` |
| → **게스트 3D 패스스루가 아예 컴파일되지 않는다** | `platform\sdl\knativesystem.cpp:100-116` |
| `WebGPU` — 코드베이스 전체 **0건** | 전수 검색 |
| emscripten 일 때 `SDL_RENDERER_SOFTWARE` 강제 | `platform\sdl\knativescreenSDL.cpp:755` |
| gl4es 실험 브랜치는 참여자 본인이 "dead-end and very out-of-date" 로 종결 | issue #94, kevodwyer 2024-06-10 |

**결론: 백엔드를 직접 만드는 것이 유일한 길이다.**

---

## 2. 두 가지 결정과 근거

### 2-1. A 방식 — 게스트 안 `d3d9.dll` 교체

| | 위치 | CheerpX 등으로 이전 시 |
|---|---|---|
| **A. 게스트 `d3d9.dll` 교체** | Windows 게스트 | **번역 로직 재사용.** 마샬링 채널만 재작성 |
| B. BoxedWine GL 패스스루 수정 | 에뮬레이터 내부 | 통째로 폐기 |

사용자 확정 로드맵이 `① 백엔드 → ② BoxedWine WASM 성능 실측 → ③ 느리면 CheerpX 이전` 이므로
**③ 이 가능하려면 반드시 A** 여야 한다.

**출발점이 이미 있다: `tools/d3d9_probe/d3d9proxy.cpp`.** 드롭인 `d3d9.dll` 형태가 정확히 A 다.
`acknex.dll` 은 `d3d9.dll` 에서 **`Direct3DCreate9` 하나만** 정적 임포트하고 이후는 전부
COM vtable 호출이므로(VERIFIED, 임포트 1건), 이 진입점 하나만 우리가 제공하면 렌더링 전체를 갖는다.

> 과거 "Wine 에서 프록시 체이닝 불가"(문서 139) 한계는 **여기 해당 없음.**
> 그건 진짜 d3d9 로 *넘겨주려* 했기 때문이다. 백엔드는 넘기지 않고 자기가 구현한다.

### 2-2. WebGL2 (WebGPU 아님)

- **셰이더 0개**(VERIFIED, 아래 §3). 순수 고정기능 → **WebGL 도 WebGPU 도 FF 가 없으므로
  양쪽 다 셰이더로 흉내내야 한다. 작업량 동일** → 이 항목은 결정 근거가 못 된다
- **상태 변경이 프레임당 약 560회**(§4). FF 에뮬레이션에선 상태 조합마다 셰이더 순열이 생긴다.
  **WebGPU 는 조합마다 파이프라인 객체가 필요해 파이프라인 폭발**이 난다.
  WebGL2 는 유니폼 분기가 가능해 이 형태에 유리하다 ← **결정적 근거**
- **드로우가 프레임당 55개뿐** → WebGPU 의 낮은 호출 오버헤드 이점이 무의미
- 호환성: WebGL2 는 사실상 전 브라우저. WebGPU 는 Safari 도입이 최근

---

## 3. 측정된 API 계약 (VERIFIED — 게이트 1 전체 세션 1회 정상 종료)

출처: `artifacts/d3d9_probe/20260719_gate1/d3d9_probe_full_session.log`
세션 범위: 로그인 → PatHouse → Plaza → 자연 OX 1회전 → 요리학원 오븐 결과

**호출된 고유 메서드 56개 / 총 1,891,345회 / 미호출 80개**

### 3-1. 반드시 구현 (핵심 렌더)
```
Present 2,095          BeginScene 2,094      EndScene 2,093     Clear 3,282
DrawPrimitiveUP 109,176                      DrawIndexedPrimitive 6,776
SetStreamSource 6,776  SetIndices 6,776      SetVertexDeclaration 6,776
SetFVF 119,628         CreateVertexDeclaration 55
CreateTexture 731      CreateVertexBuffer 54 CreateIndexBuffer 54
SetTexture 94,844      SetTextureStageState 322,815   SetSamplerState 144,678
SetRenderState 389,932 SetTransform 21,808   SetViewport 10,735  GetViewport 2,092
SetMaterial 70,045     SetLight 6,415        LightEnable 4,072
SetScissorRect 4,184   GetScissorRect 2,092  SetPaletteEntries 6
```

### 3-2. 디바이스/열거 (간단, 값만 반환하면 됨)
```
Direct3DCreate9 → CreateDevice 1회
GetAdapterCount 6 / GetAdapterIdentifier 5 / GetAdapterModeCount 16 / EnumAdapterModes 1,610
GetAdapterDisplayMode 2 / CheckDeviceType 295 / CheckDeviceFormat 367,297
CheckDeviceMultiSampleType 2,813 / CheckDepthStencilMatch 17,697 / GetDeviceCaps 14+1,519
GetAdapterMonitor 1 / GetAvailableTextureMem 2,091 / GetDisplayMode 731 / GetDirect3D 839
TestCooperativeLevel 2 / Reset 2 / ValidateDevice 2 / ShowCursor 7,652 / GetBackBuffer 3
BeginStateBlock 1 / CreateQuery 2
```
> `CheckDeviceFormat` 이 367,297회다. **반환값 캐시 필수**(INFERRED — 성능상).

### 3-3. COM 수명주기
`IDirect3D9` AddRef 70,917 / Release 70,873, `IDirect3DDevice9` AddRef 3,547 / Release 3,321.
**정확한 참조계수 구현 필요.** 프록시가 아니라 진짜 객체를 제공하므로 여기서 새면 바로 누수다.

### 3-4. 구현 불필요 — 미호출 80개 중 표면을 크게 줄이는 것들 (VERIFIED)
```
SetRenderTarget / GetRenderTarget / CreateRenderTarget
SetDepthStencilSurface / GetDepthStencilSurface / CreateDepthStencilSurface
CreateAdditionalSwapChain / GetSwapChain / GetNumberOfSwapChains
StretchRect / ColorFill / UpdateSurface / UpdateTexture / GetRenderTargetData / GetFrontBufferData
CreateCubeTexture / CreateVolumeTexture / CreateOffscreenPlainSurface
SetGammaRamp / GetGammaRamp / SetClipPlane / GetClipPlane
SetVertexShader / SetPixelShader 및 모든 셰이더 상수 API   ← 전부 0회
DrawRectPatch / DrawTriPatch / DeletePatch / EvictManagedResources / SetCursorProperties
```
**의미**: 렌더 타깃 전환 없음. 큐브/볼륨 텍스처 없음. 셰이더 없음. **암시적 백버퍼에만 그린다.**
문서 139 가 열어뒀던 "render-target/viewport" 가설이 폐기된 근거도 이것이다.

---

## 4. 프레임당 부하 (VERIFIED, Present 2,095 기준 세션 평균)

| 항목 | 프레임당 |
|---|---:|
| `DrawPrimitiveUP` (UI/2D) | 52.1 |
| `DrawIndexedPrimitive` (3D 모델) | 3.2 |
| `SetRenderState` | 186.1 |
| `SetTextureStageState` | 154.1 |
| `SetSamplerState` | 69.1 |
| `SetFVF` | 57.1 |
| `SetTexture` | 45.3 |
| `SetMaterial` | 33.4 |
| `SetTransform` | 10.4 |
| `SetViewport` | 5.1 |
| `SetLight` / `LightEnable` | 3.1 / 1.9 |
| **드로우 합계** | **≈ 55** |
| **상태 변경 합계** | **≈ 560** |

**해석**: 드로우 55개는 현대 기준 극히 가볍다. 병목은 그래픽이 아니라 **x86 CPU 에뮬레이션**일
가능성이 높다(INFERRED). 상태 변경 560회는 FF 순열 관리 설계를 좌우한다 → §2-2 의 WebGL2 근거.

---

## 5. 아키텍처

```
┌─ 게스트 (WASM 안 Windows/Wine) ────────────────────┐
│  Azrok.exe → acknex.dll                            │
│      └─ d3d9.dll  ← 우리가 만드는 것 (A 방식)       │
│           · COM 객체/vtable 제공                    │
│           · 상태 추적 + 명령 배치                    │
└──────────────────┬─────────────────────────────────┘
                   │  ★ 마샬링 채널 (이식성 경계)
┌──────────────────▼─────────────────────────────────┐
│  호스트 (브라우저 JS)                                │
│   · 명령 디코드                                      │
│   · FF 상태 → GLSL ES 3.00 유니폼 상태               │
│   · WebGL2 호출                                     │
└────────────────────────────────────────────────────┘
```

**마샬링 채널이 유일한 의도된 이식성 경계다.** CheerpX 에서 같은 ABI 를 재사용하는 것은
설계 목표이며 **NOT VERIFIED**다. 실제 CheerpX guest→JS 채널은 아직 실측되지 않았다.
→ **구현 착수 전에 이 경계의 계약부터 합의할 것.**

설계 지침(INFERRED):
- 기본 Emscripten release 는 싱글스레드다. 실제 어댑터가 같은 스레드/콜스택 직접 호출을
  제공한다면 **호출별 전달부터 시작할 수 있다.** 이 직접 전달 경로 자체는 NOT VERIFIED다.
- 프레임 배치와 공유 메모리 링은 worker/main-thread 프록시 비용이 실측될 때 추가할
  최적화이며 초기 ABI 요구사항이 아니다.
- 상태는 게스트 쪽에서 추적하고 **변경분만** 전송할 수 있지만, 현재 560회 중 실제
  중복률은 NOT VERIFIED다. 인자 히스토그램 측정 뒤 결정한다.

---

## 6. 고정기능 → GLSL 매핑 (구현 계획)

| D3D9 FF | 호출량 | WebGL2 구현 |
|---|---:|---|
| `SetTransform` (World/View/Proj) | 10.4/f | 유니폼 행렬 |
| `SetMaterial` | 33.4/f | 유니폼 (ambient/diffuse/specular/emissive/power) |
| `SetLight` + `LightEnable` | 3.1 / 1.9 /f | 유니폼 배열 + 활성 마스크. 광원 타입별 분기 |
| `SetTextureStageState` (COLOROP/ALPHAOP/ARG) | 154.1/f | **텍스처 스테이지 결합기.** 순열 핵심 |
| `SetSamplerState` (필터/주소) | 69.1/f | `texParameteri` + 샘플러 객체 |
| `SetRenderState` (알파테스트/블렌드/컬링/Z) | 186.1/f | 상당수는 GL 상태 직결. **알파테스트는 셰이더 discard** |
| `SetFVF` | 57.1/f | 정점 포맷 → `vertexAttribPointer` 레이아웃 |

**핵심 난이도는 `SetTextureStageState` 결합기다.** D3D9 의 스테이지 연산(MODULATE/ADD/
BLENDTEXTUREALPHA 등)과 인자(TEXTURE/DIFFUSE/CURRENT/TFACTOR)를 GLSL 로 재현해야 한다.
초기 전략은 런타임 순열 폭발이 아니라 **우버 셰이더 또는 소수의 정적 셰이더 + 유니폼
비트필드 분기**다. 정확한 연산 집합은 인자 히스토그램으로 확정한다.

**어두운 화면 참고**: Vulkan 경로에서 관측된 어두움(문서 141+)은 FF 조명 변환 문제로 보인다.
우리 백엔드는 **밝기 정답을 Windows 네이티브와 대조**해야 한다 — WineD3D/DXVK 를 기준으로 삼지 말 것.

---

## 7. 알려진 구현 항목 (근본 장벽 아님, 작업량임)

1. **8비트 팔레트 텍스처 후보** — `SetPaletteEntries` 6회는 VERIFIED지만 실제
   `D3DFMT_P8` 생성은 NOT VERIFIED다. `CreateTexture` 포맷 히스토그램에서 P8이 나오면
   WebGL2 업로드 시 RGBA 또는 인덱스+팔레트 텍스처로 확장한다.
2. **컬러키 투명** — D3D9 시대 관용. 셰이더 `discard`
3. **`DrawPrimitiveUP`** — 정점 버퍼 없이 사용자 메모리에서 그림. 스트리밍 버퍼 + orphaning
4. **`CheckDeviceFormat` 367,297회** — 캐시 없으면 경계 왕복만으로 죽는다
5. **COM 참조계수** — §3-3

## 8. GL 근본 한계 가설은 배제된다 (근거)

WineD3D 가 방을 못 그린 것(문서 139)이 "GL 로는 표현 불가" 를 뜻하지 않는다:
- OpenGL 자체가 FF 파이프라인을 가졌고 D3D9 FF 와 기능 대등하다
- FF 는 셰이더의 부분집합이다. 표현 불가가 성립하기 어렵다
- WineD3D 로 FF 시대 게임 다수가 정상 동작한다
- 실패 신호가 능력 부족이 아닌 자원 처리 오류 모양이다 — `D3DERR_*` **0건**,
  "invalid zero-width map" **816건**(문서 139)
- 실패 지점이 정통 Wine 이 아니라 **BoxedWine 자체 GL 계층**일 수 있다 — 미분리(NOT VERIFIED)

그리고 **A 방식은 d3d9 에서 가로채므로 WineD3D 를 통과하지 않고 대체한다.** 그 버그를 물려받을
경로 자체가 없다.

## 9. 미해결 (NOT VERIFIED — 다음 확인 대상)

1. **Azrok 브라우저 렌더 성능** — 문서 157에서 프로브 없는 명명 CLI Azrok가
   87~122 MIPS로 여러 초 실행되고 유휴 뒤 다시 120/114 MIPS로 재개하는 것은 확인했다.
   그러나 WebGL Present가 아직 없으므로 렌더 프레임 성능은 미측정이다.
2. **CheerpX** — guest→JS 채널과 Wine/Azrok 실제 실행을 포함해 전부 NOT VERIFIED다.
3. **상태 변경 560회 중 실제 변경 비율** — 중복 설정이면 전송량이 크게 줄어든다
4. **WebGL2 canvas 경로** — 문서 159에서 x86 PE의 stack index/args가 Emscripten
   callback과 JavaScript에 정확히 도달하고 JS 반환값이 guest EAX로 왕복하는 것까지
   VERIFIED다. 전송 채널은 더 이상 미지수가 아니다. 다음은 기존 canvas에서 WebGL2
   clear/triangle를 직접 그리는 것이다. `INT 0x99`와 generic `/dev`는 fallback이다.

## 9-1. 콘텐츠 검증 상한 (사용자 결정)

웹 이식 게이트의 게임 실행은 렌더링 증명만 한다. PatHouse, Plaza, 대표 미니게임 1곳 중
현재 질문에 필요한 1~2곳만 사용한다. 요리·도서관·퀘스트·사운드·세부 게임플레이 QA는
웹 백엔드 진행을 막지 않으며 별도 요청 없이는 반복하지 않는다.

## 10. 근거 파일

- `artifacts/d3d9_probe/20260719_gate1/d3d9_probe_full_session.log` — API 표면 실측
- `tools/d3d9_probe/d3d9proxy.cpp` / `README.md` — A 방식 출발점, Wine 한계 기록
- 문서 134 (게이트 1 표면), 139 (WineD3D 방 부재), 141 (Vulkan 렌더), 145 (OX AV)
- BoxedWine issue #94, 릴리스노트 26R1.0, 로컬 소스 26R1 스냅샷
- 문서 154 (최소 인자 히스토그램), 156 (행렬 256 확장), 157 (clean 2c MIPS), 158 (INT 0x9A Phase 0), 159 (browser round trip)
