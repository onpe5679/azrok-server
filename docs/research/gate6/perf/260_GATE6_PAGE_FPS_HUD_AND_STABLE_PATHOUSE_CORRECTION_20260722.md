# 260 Gate 6 page FPS HUD and stable PatHouse correction (2026-07-22)

## 결론

- **VERIFIED (implementation):** 브라우저 페이지 헤더 우측에 `FPS N.N` 실시간 배지를 추가했습니다.
- **VERIFIED (low-overhead design):** 렌더 루프, BoxedWine worker, D3D 프록시, 게스트에는 계측 코드를 추가하지 않았습니다. 호스트가 이미 `COMMAND.PRESENT`마다 증가시키는 `globalThis.D3D9WebDebug.presents`를 메인 페이지의 1초 `setInterval`이 한 번 읽고, 실제 경과시간으로 차분합니다.
- **VERIFIED (dynamic/browser):** 로딩 전에는 `FPS --`, 렌더 중에는 숫자, 숨겨진 탭에서는 다시 `FPS --`가 됩니다. 50 FPS 이상은 녹색, 0보다 크고 50 미만은 주황색입니다.
- **CORRECTED:** 실제 1024×768 PatHouse 안정 체류는 HUD에서 약 22~31 FPS였고, exact cross-check는 **266 Presents / 10.036 s = 26.5046 FPS**였습니다.
- **REJECTED:** 문서 259의 release17 **97.1043 FPS**를 안정 PatHouse 결과로 본 판정은 틀렸습니다.

## 구현

파일: `tools/boxedwine_local/index_d3d9web_pathouse.html`

헤더에 캔버스를 가리지 않는 고정 폭 배지를 추가했습니다. 계산은 다음 기존 누적값만 사용합니다.

```text
D3D9WebDebug.presents
  = d3d9web-runtime.js recordDispatch(COMMAND.PRESENT)에서만 증가
```

1초마다 다음을 계산합니다.

```text
fps = (currentPresents - previousPresents) * 1000
      / (currentPerformanceNow - previousPerformanceNow)
```

`data-d3d9web-loop`는 1024 host commands마다만 게시되므로 HUD 원본으로 사용하지 않았고 독립 cross-check에만 사용합니다.

## 동적 확인

한 브라우저 탭만 reload했습니다. 페이지 내부에서 다음 상태를 직접 확인했습니다.

1. 시작 전: `FPS --`
2. 선택/전환 렌더 중: `FPS 80~90대`
3. 정적인 선택 화면에서 Present가 멈춘 순간: `FPS 0.0`
4. 기존 입력 펄스로 PatHouse 진입 후 안정 체류: `FPS 22~31`

PatHouse 안정 체류 exact 구간:

| 시작 | 종료 | wall | Present delta | FPS | memory title |
|---:|---:|---:|---:|---:|---:|
| 8,693 Presents | 8,959 Presents | 10.036 s | 266 | **26.5046** | 470→471 MB |

이는 사용자가 화면에서 본 약 28 FPS와 일치합니다.

## 성능 비용 판정

HUD 자체는 초당 한 번의 `performance.now()`, 숫자 읽기, DOM text/dataset 갱신만 수행합니다. hot render path에는 새 분기나 시계 호출이 없습니다. 따라서 기존 per-frame profiler처럼 프레임당 수십만 번 타이머를 호출하는 오버헤드 구조가 아닙니다.

동일 세션에서 HUD OFF/ON을 반복하려면 게임을 다시 띄워야 하므로 사용자의 중복 실행 최소화 요구에 따라 별도 A/B는 하지 않았습니다. 현재 26.5 FPS는 HUD 추가 전 초기 측정의 약 27 FPS 범위와도 일치하지만, 이는 정밀 matched A/B 주장은 아닙니다.

## 다음 판정

- **VERIFIED (phase classification):** 97 FPS 구간은 선택/전환의 가벼운 렌더 phase였습니다. 당시 120-Present 보고는 `DrawUP 299`, transform 744, upload 33~120 수준이었습니다. 실제 PatHouse 안정 체류는 120 Presents마다 `DrawUP 23,880`, transform 8,880, upload 1,920, DrawUP payload 약 28.38 MB입니다. 프레임당으로는 각각 약 199 DrawUP, 74 transforms, 16 uploads입니다.
- **VERIFIED:** 안정 PatHouse의 독립 `present_delta=120` timestamp 간격은 약 4.34~4.93초, 즉 24.3~27.6 FPS로 HUD와 exact 10초 차분에 일치합니다.
- 따라서 333→470 MB 증가만으로 장시간 JIT 성능 저하라고 단정하지 않습니다. 직접 확인된 주된 차이는 장면의 렌더 제출량입니다.
- 이후 성능 gate는 반드시 화면 phase를 먼저 확정하고, PatHouse에서 최소 10초 체류 후 HUD와 exact 10초 Present 차분을 동시에 기록합니다.
