# Gate 6 — release JIT 실제 Present 재측정과 73 FPS 주장 폐기

날짜: 2026-07-22 KST

## 결론

- **VERIFIED (dynamic/browser):** `boxedwine.callaudio2` release JIT + `Azrok_D3D9Web_pathouse_stateblock1`의 정상 1024×768 PatHouse는 네 번의 10초 창에서 총 932 D3D9 Presents / 40.008초, **23.295 FPS**였습니다.
- **REJECTED:** 문서 250의 `1,320 Presents / 17.957초 = 73.509 FPS`는 실제 Present 측정이 아니었습니다. `D3D9WEB_HOST_JS_PROFILE batches=120`의 host command batch를 D3D9 Present로 잘못 환산했습니다.
- **VERIFIED:** 진짜 Present 카운터는 host runtime의 `recordDispatch()`가 `COMMAND.PRESENT`에서만 증가시키는 `D3D9WebDebug.presents`입니다. 같은 값이 문서 루트 `data-d3d9web-loop="commands:presents:lastCommand:lastBytes"`에 1024 command마다 게시됩니다.
- **VERIFIED:** 별도의 guest profile `D3D9WEB_GUEST_COPY_SITES presents=120`도 연속 두 보고 사이 5.562초, 즉 21.575 FPS로 같은 저속 범위를 독립 지지합니다.

문서 250의 BGM 자연 루프, Wine seek-flush, upstream 48ms audio pacing A/B 결론은 이번 정정과 무관하며 그대로 유효합니다. 폐기되는 것은 FPS 수치와 그에 따른 50 FPS gate 통과 주장뿐입니다.

## 측정 대상

- browser: Codex in-app browser, 단일 탭
- canvas: 1024×768
- scene: 자연 선택 뒤 정지 PatHouse, 카펫/벽/가구/캐릭터/UI 정상
- runtime: `boxedwine.callaudio2`
- app: `Azrok_D3D9Web_pathouse_stateblock1`
- root: `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3`
- console textarea: hidden

동일 탭 Emscripten pthread 재초기화는 `Module`/WebGL canvas가 생기지 않는 죽은 상태를 만들었으므로, 죽은 탭을 먼저 닫고 깨끗한 탭 정확히 하나에서 release 런타임만 기동했습니다.

## 정확한 Present 근거

`tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`의 `recordDispatch()`는 다음 의미를 가집니다.

```text
command === COMMAND.PRESENT 일 때만 debug.presents += 1
1024 commands마다 document.documentElement.dataset.d3d9webLoop 갱신
형식: commands:presents:lastCommand:lastBytes
```

따라서 sampling 경계의 오차는 최대 1024 host commands에 포함된 소수 프레임이며, 10초 창의 FPS를 3배 이상 부풀릴 수 없습니다.

## 네 번의 10초 결과

| 창 | wall ms | Present delta | FPS |
|---:|---:|---:|---:|
| 1 | 10,004 | 227 | 22.691 |
| 2 | 10,002 | 218 | 21.796 |
| 3 | 10,000 | 244 | 24.400 |
| 4 | 10,002 | 243 | 24.295 |
| 합계 | 40,008 | 932 | **23.295** |

동일 장면의 DrawPrimitiveUP 카운터 측정도 10초에 32,688 calls였습니다. guest profile은 120 Presents에 17,280 DrawUP, 즉 프레임당 144 calls를 보고하므로 `32,688 / 144 / 10 = 22.7 FPS`로 일치합니다.

## 73.509 FPS가 나온 이유

`D3D9WEB_HOST_JS_PROFILE batches=120`은 worker가 host로 보낸 command batch 120개에 대한 JS 실행 비용 창입니다. 한 Present 동안 여러 batch가 발생하므로 이 창의 timestamp 간격을 `120 frames`로 계산하면 FPS가 약 3배 부풀려집니다.

반면 다음 두 값은 진짜 Present입니다.

- `recordDispatch(COMMAND.PRESENT)`의 `D3D9WebDebug.presents`
- guest D3D9 proxy가 Present마다 증가시켜 host에 싣는 `guestProfileLatest.present`

이 둘은 현재 21.6~24.4 FPS 범위에서 일치합니다.

## 판정

- **FAILED:** 현재 release JIT는 1024×768 PatHouse 50 FPS gate를 통과하지 못합니다.
- **FAILED:** 더 엄격한 65 FPS 목표도 통과하지 못합니다.
- **NEXT:** host batch가 아니라 실제 Present를 분모로 고정한 상태에서 guest/runtime의 큰 레버를 다시 측정해야 합니다. 현재 장면은 프레임당 DrawUP 144회, indexed draw 11회이며, 이전의 작은 함수 AOT나 host-only 최적화만으로는 50 FPS에 도달하지 못합니다.

