# 535 파란 화면 — 해결. 프록시가 D3D9 기본값을 0 으로 캡처했다 (2026-07-30)

> ## ✅ 해결됨 (VERIFIED)
>
> **근본 원인**: `d3d9_web.cpp` 의 device 상태 캐시는 `ByteZero` 로 0 초기화되는데
> `D3DRS_COLORWRITEENABLE`(168) 의 D3D9 기본값은 **`0x0000000F`** 다.
> `StateBlock_Capture`(:2682) 는 device 쪽 `render_state_set[]` 를 확인하지 않고
> `device->render_states[state]` 를 그대로 복사한다. 게임이 한 번도 쓴 적 없는 168 이
> **0 으로 캡처**되고, `StateBlock_Apply` 가 그 0 을 호스트에 밀어 넣는다.
>
> **수정**: `D3D9_CreateDevice` 에서 `SeedDefaultRenderStates()` 로 D3D9 문서상의
> 기본값을 심는다(47개, 168 포함). `render_state_set` 는 FALSE 로 두므로 첫 실제
> `SetRenderState` 는 그대로 호스트로 전달되고, 심은 값들은 호스트 런타임이 이미 쓰던
> `?? 기본값` 과 동일해 **양쪽이 우연이 아니라 구성으로 일치**하게 된다.
>
> ```text
> 수정 전 : values {0:199, 15:199}   픽셀 0,0,128,0 ×3        (전체 남색)
> 수정 후 : values {15:2}            픽셀 199,130,135,255 / 235,234,217,255 / 34,0,68,255
> ```
>
> `0` 이 **한 번도 나가지 않는다.** Enter 를 눌러도 장면이 유지되고 **채팅 입력창이 정상 표시**된다
> (`artifacts/audio/blue_FIXED_after_enter.png`, FPS 42.3).
> 원본 실행파일·게임 자산 무수정. 빌드: `build_guest_texture_recycle.bat`,
> 패키지 `apps/Azrok_D3D9Web_pathouse_guesttexrecycle4_rsdefaults1.zip`.
>
> 아래 §1~§5 는 그 원인에 도달한 경로다. §4.5 의 `case 168` 추가는 별개의 정당한
> 누락 보완으로 유지한다(그것만으로는 증상이 풀리지 않았다).

---

# (조사 경과) 컬러 쓰기 마스크가 꺼진 채 고착된다

날짜: 2026-07-30
선행: **#530**(GL 파이프라인 실측, 크기 단서는 이 카드로 기각), **#532**(Codex 정적 분석 — 후보 1 적중), #252(D3D9 StateBlock)
원본 실행파일·게임 자산 무수정. 브라우저 실측.

---

## 1. 결정적 재현이 확보됐다 (VERIFIED)

CDP 키 이벤트 **한 번**으로 재현된다. 사람 손이 필요 없다.

```powershell
Input.dispatchKeyEvent  type=keyDown  windowsVirtualKeyCode=13 key=Enter text="`r"
Input.dispatchKeyEvent  type=keyUp    windowsVirtualKeyCode=13 key=Enter
```

첫 시도가 실패했던 이유는 `rawKeyDown` + `char` 조합을 썼기 때문이다.
`keyDown` 에 `text`/`unmodifiedText` 를 실어야 게스트에 닿는다.
도달은 페이지 리스너로 확인했다 — `["keydown:Enter:13","keypress:Enter:13","keyup:Enter:13"]`.

```text
Enter 직전 : 148,88,51,255 / 235,234,217,255 / 34,170,1,254 / 245,232,209,255
Enter 직후 : 0,0,128,0  ×5      (전 지점 동일)
presents    : 14645 -> 14732 -> 14838   (계속 돈다)
```

프로세스는 살아 있고 FPS 31.3 이 표시된다. `artifacts/audio/enter_try1.png` 가 사용자가 본 그 화면이다.

---

## 2. 원인 — `gl.colorMask(false,false,false,false)` (VERIFIED)

파란 상태에서 WebGL 프로토타입을 후킹해 **실제 draw 시점의 상태**를 찍었다. 2 초 창:

```json
{ "draws": 11796, "clears": 282,
  "clearColors": { "0,0,128,0": 282 },
  "clearMasks": { "256": 188, "16640": 94 } }
```

샘플 12 건 **전부** 동일했다:

```json
"colorMask":   [false, false, false, false],     <-- 원인
"scissorTest": false, "scissor": [0,0,1024,768],
"viewport":    [0,0,1024,768],
"clearColor":  [0, 0, 0.5019, 0],
"db": "1024x768", "drawFB": "[object WebGLFramebuffer]"
```

2 초에 **11,796 번 그리는데 한 픽셀도 나가지 않는다.** 마스크가 전 채널 차단이다.
scissor·viewport·cull 은 전부 정상이므로 #532 의 다른 후보들은 배제된다.

`glClear` 도 같은 마스크를 받는다. 그래서 남색은 **마스크가 꺼지기 직전 마지막 clear 가 남긴 잔상이 얼어붙은 것**이다.
clear 색 `0,0,128,0` 은 알파 0 — `D3DCOLOR_ARGB(0,0,0,128)` 이다.

### 기능 검증 — 마스크만 켜면 그림이 돌아온다 (VERIFIED)

파란 세션을 그대로 두고 `gl.colorMask` 를 감싸 **all-false 호출만 거부**했다.

```javascript
P.colorMask = function (r,g,b,a) {
  if (!r && !g && !b && !a) { blocked++; return o.call(this, true,true,true,true); }
  return o.call(this, r,g,b,a);
};
```

```text
차단 전 : 0,0,128,0 ×4
차단 후 : 148,88,51,255 / 235,234,217,255 / 34,170,1,254 / 245,232,209,255
3 초간 차단된 all-false 호출 : 318 회
```

Enter 이전 값과 정확히 같은 픽셀로 복귀했다. **다른 요인은 없다.**
(이것은 진단이지 수정이 아니다 — 마스크를 무조건 켜면 정당한 컬러 마스킹 효과가 깨진다.)

---

## 3. 마스크는 어디서 오는가 (VERIFIED)

`web_backend/host/d3d9web-runtime.js` 에서 `gl.colorMask` 를 부르는 곳은 **`clearBackbuffer` 하나뿐**이다.

```javascript
// :1877-1881  clear 를 위해 강제로 켠다
if (flags & 1) {
  gl.clearColor(...);
  gl.colorMask(true, true, true, true);
  mask |= gl.COLOR_BUFFER_BIT;
}
...
// :1921-1923  clear 뒤 게스트 상태로 되돌린다
const colorWrite = renderStates.get(168) ?? 0x0f;
gl.colorMask(Boolean(colorWrite & 1), Boolean(colorWrite & 2),
             Boolean(colorWrite & 4), Boolean(colorWrite & 8));
```

즉 매 프레임이 이렇게 흐른다: **남색 clear 는 통과 → 마스크 0 으로 복귀 → 이후 draw 전부 차단 → present.**
관측된 모든 수치와 일치한다.

### 런타임의 별개 결함 — `applyRenderState` 에 `case 168` 이 없다 (VERIFIED)

`applyRenderState`(:2105-2193) 는 `renderStates.set(id, normalized)` 로 값을 저장하지만
**168 에 대한 `case` 가 없어서 `gl.colorMask` 를 부르지 않는다**.
7·14·22·23·27·174 등은 즉시 GL 에 반영되는데 168 만 빠져 있다.

결과적으로 `D3DRS_COLORWRITEENABLE` 은 **다음 Clear 까지 GL 에 반영되지 않는다.**
Clear 가 매 프레임 오므로 정상 흐름에서는 티가 안 나지만, 상태 추적으로서는 구멍이다.

---

## 4. 게스트 명령 스트림 실측 — 원인 확정 (VERIFIED)

`D3D9WebRuntime.dispatch`/`dispatchBatch` 를 감싸 `SET_RENDER_STATE(=5)` + `state==168` 을
스캔했다(`scratchpad/rs168_trace.ps1`).

```text
Enter 이전 3 초 : total=0                       <-- 168 명령이 아예 없다
Enter 이후 6 초 : total=176   seen={ "15": 88, "0": 88 }
이력           : t=3343 v=15 / t=3344 v=0 / t=3375 v=15 / t=3377 v=0 / ...
                 항상 15 -> 0 순서, 프레임마다(약 29ms) 반복, 마지막 이벤트는 v=0
```

평소 광장에서 **168 명령이 0 건**이라는 것이 결정적이다. 그래서 `?? 0x0f` 기본값이 살아 있고
화면이 정상이다. 채팅 UI 가 열릴 때만 이 상태를 쓴다.

### 프레임 흐름 — 왜 아무것도 안 그려지는가

| # | 일어나는 일 | GL 마스크 |
|---|---|---|
| 1 | `Clear` : 강제로 켜고 navy clear → `renderStates.get(168)`(=0) 로 복귀 | **false** |
| 2 | 게스트 `SetRenderState(168, 15)` → `renderStates` 에 저장만. **`case 168` 이 없어 `gl.colorMask` 미호출** | **false** (그대로) |
| 3 | 게스트 draw (UI) | 전부 차단 |
| 4 | 게스트 `SetRenderState(168, 0)` → 저장 | false |
| 5 | 다음 프레임 1 번으로 | false |

**즉 누락된 `case 168` 이 원인 그 자체다.** 실제 D3D9 라면 2 번에서 쓰기가 켜져 그림이 나온다.
우리 런타임은 다음 `Clear` 까지 반영하지 않는데, 그때는 이미 게스트가 0 으로 되돌린 뒤다.

프록시·StateBlock 은 **무관하다**. 앞서 의심했던 아래 항목들은 원인이 아니다
(사실 자체는 맞지만 이 결함과 인과관계가 없다).

| 확인한 사실 | 판정 | 이 결함과의 관계 |
|---|---|---|
| `Device_SetRenderState`(:2351) 는 값이 같으면 호스트로 안 보낸다(:2361) | VERIFIED | 무관 — 15/0 이 교대하므로 매번 전송된다 |
| `StateBlock_Capture`(:2674) 는 `render_state_set[]` 를 존중한다 | VERIFIED | 무관 |
| `Device_CreateStateBlock` 이 프록시에 없다 | VERIFIED | 별개 과제 |

---

## 4.5. 수정 (적용됨)

`web_backend/host/d3d9web-runtime.js` `applyRenderState` 에 `case 168` 추가.
비트 순서는 `clearBackbuffer` 가 이미 쓰던 D3D9 계약 그대로(RED=1, GREEN=2, BLUE=4, ALPHA=8).

```javascript
case 168:
  gl.colorMask(Boolean(value & 1), Boolean(value & 2),
    Boolean(value & 4), Boolean(value & 8));
  break;
```

호스트 JS 파일이라 **재빌드가 필요 없다** — 페이지 새로고침으로 반영된다.
원본 실행파일·게임 자산·프록시 DLL 은 건드리지 않았다.

### 그러나 이 수정만으로는 증상이 풀리지 않는다 (VERIFIED)

수정을 넣고 새 세션에서 다시 재현했다. **여전히 남색이다.**
`case 168` 이 실제로 발화하는 것은 확인했다 — `gl.colorMask` 호출수가 clear 수를 넘어섰다
(3 초에 호출 398 / clear 240, 값 분포 `{"1111":119, "0000":279}`).

`colorMask`·`clear`·draw 를 하나의 순서 로그로 찍자 프레임 구조가 드러났다.

```text
M1  C  M0  d×102    C M0 d×17    C M0 d×6    M1 d M0 d
↑   ↑   ↑    ↑
│   │   │    └─ 장면 draw 102 개 — 전부 마스크된 채로 난다
│   │   └─ clear 뒤 renderStates.get(168)=0 으로 복원
│   └─ navy color clear
└─ clearBackbuffer 가 강제로 켠 것

마스크가 열린 채 그려진 draw : 8,472 중 30 개
```

즉 **게스트가 프레임 내내 `COLORWRITEENABLE=0` 을 유지한 채 장면 전체를 그린다.**
실제 D3D9 하드웨어에서도 그렇게 그리면 아무것도 안 나온다. 따라서

> **게스트의 실제 의도와 호스트가 받는 값이 다르다. 갈라지는 지점은 프록시(C++)다.**

`case 168` 추가는 유지한다 — 런타임이 게스트 상태를 정확히 추종하게 만드는 정당한 누락 보완이고,
장면 draw 는 이미 clear 복원 때문에 마스크돼 있었으므로 회귀가 아니다.
다만 **이것은 증상의 수정이 아니다.** 프록시 조사는 별도로 진행 중이다.

### 프록시 dedup 가설은 기각됐다 (VERIFIED — 호스트 데이터만으로)

`Device_SetRenderState`(:2361)의 중복 억제가 복원값 `15` 를 삼킨다는 가설을 세웠었다.
그렇다면 호스트가 받는 `15` 의 수가 `0` 보다 **적어야** 한다.

```text
Enter 이후 8 초: { "15": 268, "0": 268 }     <-- 정확히 균형
```

**삼켜진 것이 없다.** 재빌드 없이 기각된다.
아울러 실패 경로(`SendCommand` → `FlushGuestBatch` 실패)는 전부
`InvalidateDeviceHostStateCaches()` 로 캐시를 무효화하므로(:631-647, :712-741),
캐시가 호스트보다 앞서 나가는 구조도 아니다.

### 호출 지점 실측 — 게임이 아니라 프록시였다 (VERIFIED)

진단 프록시가 모든 `SetRenderState(168, v)` 앞에 `{SET_RENDER_STATE, 0x9168, _ReturnAddress()}`
마커를 실어 보내게 하고 Enter 전후를 찍었다.

```text
Enter 이전 : sites {}          values {}
Enter 이후 : sites { "7bdd90f8": 398 }   values { "0":199, "15":199 }
순서       : @7bdd90f8 =15 @7bdd90f8 =0 @7bdd90f8 =15 @7bdd90f8 =0 ...
```

**호출 지점이 단 하나이고, `0x7BDD90F8` 은 d3d9.dll(base `0x7BDD0000`) 안이다** — RVA `0x90F8`.
즉 `SetRenderState(168, …)` 을 부르는 것은 **게임이 아니라 우리 프록시 자신**,
`StateBlock_Apply`(:2786) 다.

같은 빌드에서 널 vtable 슬롯 스텁도 함께 넣었는데 `slots hit: {}` — 이 경로에서는
널 슬롯 호출이 없었다(별개 결함인 `0x000D` 크래시와는 무관하다는 뜻).

이 한 줄로 앞선 모든 가설이 정리된다: 게임은 168 을 쓰지 않는다. 프록시가 쓴다.
그리고 프록시가 쓰는 값의 출처는 `StateBlock_Capture` 가 복사한 **0 으로 초기화된 device 캐시**다.

### 남은 사실과 다음 실험

게스트는 프레임당 정확히 `15 → 0` **한 쌍**을 보내고, 그 쌍은 **프레임 끝**에 있다.
장면 draw 125 개는 그 앞, 즉 **이전 프레임이 남긴 0** 상태에서 난다.
그리고 Enter 이전에는 168 명령이 아예 없다.

따라서 남은 질문은 하나다 — **누가 168 을 쓰는가.**
프록시에 진단 매크로 `D3D9WEB_TRACE_COLORWRITE` 를 넣어
모든 `SetRenderState(168, v)` 앞에 `{SET_RENDER_STATE, 0x9168, _ReturnAddress()}`
마커를 실어 보내게 했다(`build_colorwrite_trace.bat`,
`apps/Azrok_D3D9Web_pathouse_guesttexrecycle4_cwtrace1.zip`).
`0x9168` 은 실제 렌더 스테이트가 아니라 호스트의 `default:` 로 빠져 부작용이 없다.

호출 주소가 Azrok.exe(0x400000~) 인지 acknex(0x7F360000~) 인지에 따라
게임 로직인지 엔진인지가 갈린다. 계측 스크립트는 `scratchpad/cw_trace.ps1`.

### 반증된 것 (VERIFIED)

- "호스트가 168 을 GL 에 반영하지 않아서" 만으로는 설명되지 않는다 — 반영해도 남색이다.
- "clear 색이 잘못됐다" 가 아니다 — clear 는 정상 동작하고, 문제는 그 뒤 draw 가 안 덮는 것이다.
- #530 의 크기 불일치는 §5 에서 이미 기각됐다.

---

## 5. #530 의 크기 단서는 기각됐다 (VERIFIED)

같은 시점에 두 캔버스를 함께 찍었다.

| 요소 | attr(백킹) | CSS | 위치 |
|---|---|---|---|
| `#canvas` (SDL source) | 640x480 | 1024x768 | 429,232 |
| `#d3d9web-canvas` (D3D output) | 1024x768 | 1024x768 | 429,232 |

#532 가 정적으로 예고한 오버레이 계약과 정확히 일치한다.
#530 은 source 캔버스를 재면서 WebGL 컨텍스트는 output 것으로 봤다.
**크기를 강제로 맞추는 수정은 금지** — 입력 640→1024 변환 계약이 깨진다.

---

## 6. 다음

1. `rs168_trace.ps1` 로 Enter 전후 `SET_RENDER_STATE(168, v)` 이력 확보 → 고착 원인 확정.
2. 확정 뒤 수정 지점 선택:
   - 게스트가 복원을 보내는데 프록시가 삼킨다 → 프록시 수정(재빌드 필요)
   - 게스트가 복원을 안 보낸다 → `CreateStateBlock`(슬롯 60) 구현 여부부터 확인
3. 어느 쪽이든 `applyRenderState` 의 `case 168` 누락은 **별도로** 메울 것.
