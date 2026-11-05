# 532 D3D9Web 광장 Enter 남색 고정 — 렌더러 정적 코드 분석 (2026-07-30)

범위: 브라우저·게임을 실행하지 않고 JavaScript/HTML만 읽었다. #530의 실측은 전제로 사용했으며 재현하지 않았다. 원본 실행 파일과 게임 자산은 읽거나 수정하지 않았다.

분석 대상의 실제 로드 경로는 `tools/boxedwine_local/index_d3d9web_pathouse.html:1136-1140`이다. 이 페이지는 `web_backend/host/d3d9web-runtime.js`와 그 FFP shader를 import한다. 질문에 적힌 `assets_d3d9web/d3d9web-runtime.js`/`pack-ffp.js`는 이 checkout에 없으므로, 아래 줄 번호는 실제 import 대상 `web_backend/host/`를 사용한다. Emscripten 입력 로더만 `assets_d3d9web/boxedwine.upstreamjit64fn6inlineabi2.js`이다.

## 결론

### 우선 0 — 640x480 / 1024x768 값은 단독으로 원인이 아니다

**VERIFIED (높음)**: WebGL2를 원본 SDL `#canvas`에서 얻지 못하면 `createRenderer()`는 별도 `#d3d9web-canvas`를 만들고(`d3d9web-runtime.js:598-630`), 원본 canvas의 현재 속성/CSS 크기를 한 번 복제한다(`:620-623`). 이어 `ensureRenderer()`는 내부 `canvas` 변수를 renderer 소유 output canvas로 교체한다(`:1060-1065`). 오버레이 모드에서는 SDL source의 640x480 backing store와 D3D output의 1024x768을 **분리하고**, 두 요소의 CSS 크기만 D3D output 크기로 맞추도록 명시돼 있다(`:1070-1095`).

따라서 #530의 `canvas.width=640x480`이 `sourceCanvas`/`Module.canvas`이고 `gl.drawingBuffer=1024x768`이 `#d3d9web-canvas`의 WebGL context라면, 이는 코드와 정확히 일치하는 정상 오버레이 계약이다. 두 값을 같은 canvas 객체의 값으로 다시 계측하기 전에는 이를 리사이즈 결함으로 단정할 수 없다. source와 output의 backing size를 강제로 같게 만드는 수정은 입력의 640→1024 단일 변환 계약을 망가뜨릴 수 있으므로 제안하지 않는다.

## 1. 렌더 타깃/캔버스 크기를 바꾸는 전체 정적 지점

| 지점 | 조건과 효과 | 판정 |
|---|---|---|
| `assets_d3d9web/boxedwine-shell.js:1192-1219` | Emscripten `Module.canvas`를 얻은 뒤 시작 기본값으로 `800x600`을 대입한다. `MutationObserver`는 frame CSS 변수만 갱신한다. | VERIFIED |
| `assets_d3d9web/boxedwine.upstreamjit64fn6inlineabi2.js:1` (minified offsets 164051, 168790, 169586) | Emscripten Browser/SDL glue의 fullscreen/`setCanvasSize()`/`updateCanvasDimensions()`가 source canvas의 backing width/height 또는 CSS width/height를 바꾼다. fullscreen의 `resizeCanvas` 여부와 native window size가 조건이다. 이 경로는 renderer overlay가 아니라 source `Module.canvas`를 대상으로 한다. | VERIFIED |
| `d3d9web-runtime.js:598-630` | source canvas의 `getContext('webgl2')` 실패 시 overlay canvas를 생성한다. overlay 속성 width/height는 source의 현재 속성값, CSS는 source `clientWidth/clientHeight`에서 초기화한다. | VERIFIED |
| `d3d9web-runtime.js:674`, `:678-702` | renderer 생성 및 필요 시 `resizeBackbuffer()`가 offscreen color texture/depth-stencil renderbuffer/FBO(fb1)를 전달된 width/height로 재할당한다. | VERIFIED |
| `d3d9web-runtime.js:1053-1065` | `ensureRenderer(width,height)`는 renderer 생성 전의 closure canvas, 생성 뒤에는 renderer-owned canvas의 `width/height`를 요청 크기와 다를 때만 바꾼다. 주석대로 대입은 WebGL drawing buffer를 reset한다. | VERIFIED |
| `d3d9web-runtime.js:1101-1105` | fb1은 `canvas.width*renderScale` 크기로만 재할당되고 fb1에 bind된다. output canvas 자체의 크기를 renderScale로 줄이지 않는다. | VERIFIED |
| `d3d9web-runtime.js:1113-1118` | Present는 fb1을 READ, 기본 framebuffer를 DRAW로 bind하여 `fb1 size → canvas.width/height` blit한 뒤 fb1을 다시 bind한다. | VERIFIED |
| `d3d9web-runtime.js:2972-2979`, `:2992-3001` | guest `COMMAND.INIT` 및 `COMMAND.SET_VIEWPORT`가 `viewport.width/height`를 갱신하고 `ensureRenderer()`/`applyViewport()`를 호출한다. 이 두 command만 이 host runtime에서 D3D geometry를 canvas resize 요청으로 연결한다. | VERIFIED |
| `assets_d3d9web/boxedwine.upstreamjit64fn6inlineabi2.js:1` (minified offset 196411) | Emscripten `setCanvasElementSizeCallingThread()`는 target canvas의 `width/height`를 대입하고, 종전 viewport가 canvas 전체였을 때만 GL viewport도 바꾼다. | VERIFIED |
| 같은 파일 `:1` (offset 247863) | Emscripten CSS-size API는 `target.style.width/height`만 대입한다. | VERIFIED |

`pack-ffp.js`는 std140 UBO packer이며 canvas, resize, input, blit 코드를 갖지 않는다(`pack-ffp.js:1-14`, `:132-237`, `:312-387`).

## 2. blit 직전 마지막 약 8 draw의 정체

**VERIFIED**: renderer에는 별도의 full-screen composite quad/shader pass가 없다. `presentBackbuffer()`는 guest가 이미 만든 fb1을 `gl.blitFramebuffer`로 기본 framebuffer에 복사할 뿐이다(`d3d9web-runtime.js:1108-1118`). 따라서 #530에서 blit 직전 관측된 8회 draw는 renderer의 합성 패스가 아니라 guest D3D 명령이다.

각 draw는 `COMMAND.DRAW_PRIMITIVE_UP` 또는 `COMMAND.DRAW_INDEXED`로 들어와 각각 `gl.drawArrays`/`gl.drawElements`가 된다(`d3d9web-runtime.js:2291-2301`, `:2469-2536`, `:2651-2672`, `:2744-2759`, `:2833-2842`). 둘 다 renderer 생성 시 link한 하나의 fixed-function uber program(`d3d9_ffp.vert`/`.frag`)을 `useProgram`하며(`d3d9web-runtime.js:633-651`, `:2485-2493`, `:2750-2759`), dirty state이면 다섯 UBO block을 새 ArrayBuffer로 채워 upload한다(`:704-718`; `pack-ffp.js:132-237`, `:312-387`).

**NOT VERIFIED**: 해당 8회가 UP/Indexed 중 어느 쪽인지, FVF/vertex declaration·정점·texture·render state가 무엇인지, 그리고 screen-space `XYZRHW` full-screen quad인지 여부는 #530의 카운터만으로 식별할 수 없다. `XYZRHW`라면 vertex shader가 viewport inverse 값으로 screen space를 만들 수는 있다(`d3d9_ffp.vert:633-642`), 그러나 마지막 8 draw가 그 layout이었다는 정적 근거는 없다.

Fragment shader는 `v_Color0`(diffuse)에서 시작해 texture stage 0~7을 실행하고(`d3d9_ffp.frag:810-843`), alpha test 실패 시 discard한다(`:845-851`). null/미구현 3D texture는 `vec4(0)` fallback이지만(`:492-530`), host의 missing handle은 opaque white dummy 2D texture로 bind된다(`d3d9web-runtime.js:2556-2575`). 이들 경로에 RGB(0,0,128)를 상수로 출력하는 shader/UBO 기본값은 없다.

## 3. 원인 후보 순위

### 1) navy COLOR clear가 남고, 이후 draw가 전체 fb1을 덮지 못함 — INFERRED, 높음

코드는 D3D CLEAR packet의 ARGB를 그대로 `gl.clearColor(r,g,b,a)`로 변환한다. 특히 B=`color & 255`, R=`(color >>> 16) & 255`이다(`d3d9web-runtime.js:1861-1882`). clear 영역은 viewport/region을 scale하여 scissor로 clear한다(`:1895-1919`). 그러므로 guest가 color `0xFF000080`으로 전체 viewport COLOR clear를 냈고 뒤 draw가 pixel을 통과/coverage하지 못하면, #530의 fb1 전면 `(0,0,128)` 및 정상 Present/blit와 정확히 양립한다.

후속 draw가 덮지 못하는 정적 조건은 depth test/write, alpha test/discard, cull, blend, color write mask, scissor이다. 이 state들은 `SET_RENDER_STATE`가 유지·적용한다(`d3d9web-runtime.js:2105-2192`), fragment alpha test는 실제 discard를 실행한다(`d3d9_ffp.frag:845-851`). Enter 뒤 실제 `CLEAR` 색과 마지막 draw coverage는 실행 계측이 필요하므로 아직 원인 확정은 아니다.

### 2) Enter 뒤 guest가 보낸 FFP state/geometry가 stale 또는 부정합이라 draw가 reject/clip/discard됨 — INFERRED, 중간

renderer는 transform/material/light/texture-stage/render state를 command 단위로 shadow state에 보존하고 dirty일 때 UBO를 다시 upload한다(`d3d9web-runtime.js:1952-2015`, `:2021-2080`, `:2105-2231`, `:2485-2493`). viewport도 output/backbuffer 비율로 적용한다(`:1825-1859`). 따라서 Enter 이후 guest command stream이 특정 state를 바꾼 뒤 필요한 복원 command를 보내지 않으면, last draw가 화면을 쓰지 못할 수 있다. 그러나 어떤 state가 실제로 바뀌었는지는 정적으로 알 수 없다.

### 3) source 640x480 / overlay 1024x768 불일치가 blue screen의 직접 원인 — NOT VERIFIED이며 현재는 낮음

앞서 본 오버레이 설계 자체가 이 값 쌍을 의도한다(`d3d9web-runtime.js:598-630`, `:1070-1095`). 같은 object의 attr/drawingBuffer를 계측하지 않은 현재 증거로는 원인 후보가 아니라 우선 배제해야 할 혼동이다. 실제 output canvas가 아닌 source canvas를 census한 것이 확인되면 이 후보는 **기각**된다.

### 4) missing texture fallback이 navy를 직접 출력 — INFERRED, 낮음

null texture shader fallback은 zero vector이고(`d3d9_ffp.frag:492-530`), missing handle은 white dummy texture다(`d3d9web-runtime.js:2556-2575`). texture-stage 조합에 따라 black/transparent/discard를 유발할 가능성은 있으나, 정확한 navy 자체는 만들지 않는다. navy clear를 노출시키는 간접 요인일 수만 있다.

## 4. Enter 입력 경로

페이지 레벨에서 `keydown`을 직접 듣는 코드는 BGM gesture arm뿐이며 renderer/canvas/viewport를 바꾸지 않는다(`index_d3d9web_pathouse.html:184-186`). renderer module에는 key listener가 없다. Emscripten loader는 keydown/keypress/keyup을 keyCode·key·code와 함께 guest callback으로 전달한다(`assets_d3d9web/boxedwine.upstreamjit64fn6inlineabi2.js:1`, minified offset 252497; callback 등록 API offsets 253926 onward). 이어 guest/WASM bridge가 D3D command packet을 `D3D9WebRuntime.dispatch`/`dispatchBatch`로 넘긴다(같은 파일 `:1`; host dispatcher `d3d9web-runtime.js:2955-3055`).

**NOT VERIFIED**: Enter가 guest 내부에서 어떤 native handler를 거쳐 `INIT`, `SET_VIEWPORT`, `CLEAR`, draw, 혹은 render state command를 발생시키는지는 JS만으로 추적할 수 없다. JS에는 `Enter`, `keyCode===13`, `VK_RETURN`에 따른 renderer 상태 변경 분기가 없다.

## 5. 최소 수정안 (소스에는 적용하지 않음)

첫 수정은 크기 강제 동기화가 아니라 frame-local 원인 판별 telemetry여야 한다. `d3d9web-runtime.js`에 아래처럼 diagnostics-gated 기록을 추가한다.

```diff
@@ function presentBackbuffer() {
+ if (runtimeDiagnosticsEnabled) report(
+   `D3D9WEB_PRESENT_TARGET mode=${current.canvasMode}` +
+   ` source=${current.sourceCanvas.width}x${current.sourceCanvas.height}` +
+   ` output=${current.canvas.width}x${current.canvas.height}` +
+   ` db=${gl.drawingBufferWidth}x${gl.drawingBufferHeight}` +
+   ` fb=${current.backbufferWidth}x${current.backbufferHeight}` +
+   ` vp=${viewport.x},${viewport.y},${viewport.width},${viewport.height}`);
 }

@@ function clearBackbuffer(view, bytes) {
+ if (runtimeDiagnosticsEnabled && (flags & 1)) report(
+   `D3D9WEB_CLEAR color=0x${color.toString(16).padStart(8, '0')}` +
+   ` regions=${count || 1} vp=${viewport.width}x${viewport.height}`);
 }
```

그리고 기존 DPUP capture가 이미 가진 마지막 draw record(`d3d9web-runtime.js:2416-2455`)에 `frameDrawCalls`, draw kind와 clear serial을 붙여 final 8 records를 식별한다. 그러면 큰 로그 없이 해당 frame의 primitive/FVF/vertices/textures/TSS/sampler/render state를 보존할 수 있다. `canvas.width`를 source/output 사이에서 복사하는 패치는 이 확인 전에는 금지한다.

## 6. Claude 후속 브라우저 검증 절차

1. 기존 #530 WebGL census에 **두 canvas object의 id, attr width/height, `drawingBufferWidth/Height`, renderer `canvasMode`**를 같은 시점에 기록한다. `source=640x480`, `output/db=1024x768`, `mode=overlay`면 크기 불일치 가설을 기각한다.
2. Enter 직전/직후 각각 한 complete frame에 `D3D9WEB_CLEAR`의 flags/color/region 및 `D3D9WEB_PRESENT_TARGET`을 기록한다. 직후 clear가 `0xFF000080`이고 fb1이 navy이면 후보 1의 clear 절반은 VERIFIED가 된다.
3. 그 clear 뒤 마지막 8 draw의 DPUP/Indexed kind, FVF/declaration, viewport, TSS/sampler/render state와 각 draw 뒤 fb1 sample 변화를 기록한다. sample이 한 번도 바뀌지 않거나 전면을 덮지 못하면 depth/alpha/scissor/cull/geometry를 해당 record로 판별한다.
4. 같은 capture에서 source/output/fb size가 바뀌지 않았는데 navy clear와 no-coverage가 재현되면, resize 계열 수정은 배제하고 candidate 1/2만 수정한다. 반대로 actual output canvas와 db가 갈라지면 그 object를 대상으로만 resize owner를 추적한다.
