# 168 Gate 2c original UI render and Present boundary (2026-07-19)

## Scope

웹 이식 우선 원칙에 따라 원본 `Azrok.exe`의 첫 실제 UI 픽셀, 브라우저 프레임 경계,
서버 로그인까지만 측정했다. PatHouse/Plaza/미니게임 콘텐츠 QA는 실행하지 않았다.

## Result summary

| Gate 2c item | Result | Evidence |
|---|---|---|
| (a) 기동 | **VERIFIED** | Wine 11 guest에서 원본 EXE/acknex 적재, `Main loop.........ok` |
| (b) D3D device | **VERIFIED** | `Direct3DCreate9(31)`, 640x480 device, WebGL2 FFP link |
| (c) 화면 출력 | **VERIFIED (first original UI)** | 원본 한솔교육 로고와 게임 키 커서 텍스처가 브라우저에 안정 출력 |
| (d) 프레임 | **VERIFIED, performance incomplete** | 커서 위치와 Present 결과가 갱신되며 steady 9~10 MIPS; 정확한 FPS와 PatHouse 성능은 미측정 |
| (e) 서버 접속 | **VERIFIED** | C2S0000/S2C0004/S2C0000 뒤 C2S/S2C0016 heartbeat 지속 |

캐릭터 선택과 PatHouse 3D는 아직 **NOT VERIFIED**다. 로고 화면에서 서버 heartbeat는
계속되지만 추가 텍스처 생성이 나타나지 않아, 네트워크 정지라고 단정할 수 없다.

## 1. First original-client pixels

**VERIFIED (browser dynamic).** 다음 원본 리소스가 실제로 생성·업로드됐다.

```text
handle=1 format=23 size=8x8      bytes=128     nonzero=128     hash=0x8ED8B345
handle=2 format=23 size=1024x1024 bytes=2097152 nonzero=1570932 hash=0xABDD34A3
handle=3 format=21 size=128x128   bytes=65536   nonzero=23433   hash=0x505D2FA5
```

브라우저 화면에는 흰 바탕 위 원본 한솔교육 로고와 게임 키 커서가 보인다. 이는 단순
WebGL synthetic triangle이 아니라 원본 Acknex 클라이언트가 제출한 텍스처/FVF/state/draw의
최초 픽셀 증명이다.

## 2. Two direct rendering bugs

### DrawPrimitiveUP texture binding

**VERIFIED (source differential + browser dynamic).** host runtime의 indexed draw는 draw 직전
texture/sampler를 bind했지만 `DrawPrimitiveUP`은 하지 않았다. UI draw의 stage state와 texture
handle이 정상이어도 dummy texture가 남는 직접 결함이었다. UP 경로에도
`bindTexturesForDraw()`를 추가했다.

### Lighting on pretransformed vertices

**VERIFIED (Gate 1 state + shader differential + browser dynamic).** 원본은
`FVF 0x2C4 = XYZRHW|DIFFUSE|SPECULAR|TEX2` UI를 그리는 동안 global lighting을 켜 둔다.
기존 shader는 normal이 없는 POSITIONT 정점에도 lighting을 적용해 nonzero diffuse를 검정으로
바꿨다. `vertexHasPositionT()`이면 fixed-function vertex lighting을 건너뛰게 한 뒤 원본 로고가
나타났다.

## 3. Blue/black flicker was a missing backbuffer

**VERIFIED (browser dynamic).** 처음 보인 파랑/검정/로고 반복은 게임이 여러 색을 의도해
깜빡인 것이 아니었다. guest의 `Clear`와 부분 draw가 visible canvas에 즉시 노출되어
`Present` 이전 중간 상태까지 브라우저 compositor가 보여 준 결과다.

host runtime에 RGBA8 texture FBO + DEPTH24_STENCIL8 renderbuffer를 implicit backbuffer로 만들고,
모든 Clear/draw는 FBO에 수행한 뒤 `Present`에서만 default framebuffer로 blit하도록 바꿨다.
첫 blit은 multisampled default framebuffer와 single-sample FBO 조합에서 `0x502`로 실패했다.
WebGL context를 `antialias:false`로 생성한 후 연속 스크린샷에서 동일한 안정 프레임을 확인했다.

## 4. D3D9 semantic corrections before 3D

**VERIFIED (static contract + build/harness).** 다음 직접 불일치를 수정했다.

- `D3DRS_ZFUNC=LESSEQUAL`을 WebGL `LEQUAL`로 전달한다.
- texture `CheckDeviceFormat`이 host가 만들 수 없는 포맷까지 성공시키지 않고 Acknex fallback을
  허용한다.
- shader 최종 clip z를 `2*z-w`로 바꿔 D3D `[0,w]`를 WebGL `[-w,w]`로 변환한다.
- `gl.depthRange(viewport.MinZ, viewport.MaxZ)`를 적용한다.
- `Clear` ABI가 flags/color/z/stencil과 가변 D3DRECT를 전달한다. host는 viewport에 clip한
  scissor 영역만 요청된 target/depth/stencil bit로 지우고 write mask/scissor를 복원한다.

수정 shader는 실제 Chrome WebGL2에서 compile/link와 dummy draw를 다시 통과했다.
diag14 원본 실행도 초기 Clear/device/texture 경로를 에러 없이 통과해 로고를 출력했다.

## 5. Instrumentation removal and performance boundary

**VERIFIED (source/build/browser dynamic).** instrumented WASM은 매 D3D 명령마다 command 판별용
guest soft-MMU read를 중복 수행했고 viewport 뒤 EIP sampler와 128개 syscall 동기 로그를
활성화했다. 브리지의 packet copy/JS dispatch/EAX return은 유지하고 이 진단 전용 경로를
제거했다. 새 WASM 바이너리에서 다음 문자열은 0건이다.

```text
D3D9WEB_VIEWPORT
D3D9WEB_SYSCALL
D3D9WEB_EIP_SAMPLE
```

깨끗한 diag14는 초기 구동 순간 101 MIPS, 렌더 루프에서 steady 9~10 MIPS를 보였다.
steady 수치는 낮지만 client는 서버 heartbeat와 프레임/커서 갱신을 계속한다. 정확한 병목 비율과
FPS는 **NOT VERIFIED**다.

**VERIFIED negative A/B.** 매 command의 C++ `new[]/delete[]`를 성장형 재사용 staging buffer로
바꾼 WASM도 같은 로고 장면에서 9 MIPS였다. per-command host heap allocation은 제거됐지만 현재
steady MIPS의 지배 원인은 아니다. 이 최적화 하나로 character-select 전환이 빨라진다는 가설은
반증됐다.

## 6. Server boundary

**VERIFIED (live API/capture).** 최신 browser 연결은 다음 순서를 완료했다.

```text
C2S 0000 x1
S2C 0004 x1
S2C 0000 x1
C2S/S2C 0016 repeated
```

로고가 유지되는 동안에도 heartbeat가 계속되어 연결·로그인·Wine browser socket bridge 실패는
현재 정지점의 원인이 아니다. character create/select key, zone request, PatHouse scene은 아직
발생하지 않았다.

**VERIFIED packet differential.** 최신 2c의 empty-roster `S2C0000` 387-byte payload는 과거
빈 profile 성공 세션과 바이트 단위로 동일하다(SHA-256
`49A3FDAD26FA8659413036B1FD6252CBEEFA679D04AFB165ECCA4B9409FDD233`). 순서와 wire 길이도
`C2S0000 110 total → C2S/S2C0016 → S2C0004 9 total → S2C0000 391 total`로 같다.
WebSocket-TCP bridge는 첫 서버 응답 405 bytes를 `5+9+391`로 온전히 전달했다. 과거 성공
세션은 이 동일 응답 뒤 C2S0004와 PatHouse까지 갔지만 현재 2c는 heartbeat 외 후속 요청이 없다.
따라서 서버 payload·framing·누락 가설은 배제되며, 다음 정지점은 S2C0000 dispatch 이후 client
UI/timer/main-loop 전환이다.

## 7. Artifacts

- `artifacts/web_backend/20260719_original_client_render/diag14_stable_hansol_logo.png`
  - 87,460 bytes
  - SHA-256 `EB0A4D1DF53E764FB2C86DBBDFDA117068F1FCF24B73363A76EE0EABDD37D681`
- `tools/boxedwine_local/apps/Azrok_D3D9Web_pathouse_diag14.zip`
  - 157,214,819 bytes
  - SHA-256 `93FA2ED29E6D9086BB0D0F4C7B341BFBD570A6925CD027805E8D3465BE1B2C60`
- `tools/d3d9_web_backend/pathouse_package/d3d9.dll`
  - 15,872 bytes
  - SHA-256 `B7BD5B4D8C95F1EEFDEDF76724E61B8F6EC5CE6E6C64075C564B79738BAAB814`
- instrumentation-clean `boxedwine.wasm` (preserved under
  `artifacts/web_backend/20260719_d3d9web_clean_wasm1/`)
  - 2,428,935 bytes
  - SHA-256 `6AB477159536EB10F3435E530857EA54B1E55E77AD2083C7DBF63B2C418EAAF1`
- current reusable-staging `boxedwine.wasm`
  - 2,429,041 bytes
  - SHA-256 `49D9220FABCB1760948A6F842B821781FD3FF10B8733CA710460BCAB354C5A21`

## Next gate

Ghidra MCP로 Hansol/logo 표시 뒤 전환 조건을 추적하고, live capture의 roster 응답을 기존 native
세션과 대조한다. 정지 조건이 특정되기 전에는 프레임이 낮다는 이유만으로 CPU 성능 원인으로
단정하지 않는다. 전환 후 콘텐츠 검증은 캐릭터 선택/생성 → PatHouse 한 장면으로 제한한다.
