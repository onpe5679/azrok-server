# 526 OSS 큐 창 확대 시도 — 두 변종 모두 REJECTED, 소스 원복 (2026-07-29)

> # ⚠ 이 카드의 A/B 결과(§4, §4.7)는 **무효**다 — 측정이 오염됐다
>
> T1·T2 는 **같은 Edge 인스턴스에서 leg 를 연달아 돌리며** 측정했고,
> 그 인스턴스의 렌더러 워킹셋이 세션 동안 4.2 GB → **14.5 GB** 로 불어나 있었다.
> 검증은 이렇게 됐다: 나중에 **채택 스템 + 파라미터 없음**(`GOOD_restore`)으로 돌리자
> **fps 3.35 / 무음 75.65%** 로 T2 와 똑같이 무너졌다. 수정이 하나도 없는데도.
>
> | 시각 | leg | fps | 무음 |
> |---|---|---|---|
> | 19:47 | baseline (`storage=memory`) | 36.71 | 2.49% |
> | 20:04 | T1 (창 확대) | 32.28 | 4.12% |
> | 20:10 | T2 (프래그먼트 확대) | 4.21 | 72.64% |
> | 20:54 | **GOOD_restore (수정 없음)** | **3.35** | **75.65%** |
>
> 파라미터와 무관하게 **시간순 단조 감소**다. 따라서
> "창 확대가 악화시켰다"·"프래그먼트 확대가 런타임을 붕괴시켰다" 는 **둘 다 근거 없음**이다.
> 브라우저 인스턴스 수명이 통제되지 않은 축이었고, 그것이 지배 변수였다.
>
> **측정 프로토콜 (강제)**: leg 마다 **새 브라우저 인스턴스**로 시작하고,
> 매 leg 의 `msedge` 워킹셋 합계를 함께 기록할 것. 값이 baseline 대비 크게 올라간
> leg 는 수치를 무효 처리한다. 이 프로젝트에서 "한 탭에 한 leg" 규칙은 있었지만
> **"한 브라우저에 한 leg"** 는 없었다 — 이 카드가 그 대가를 치렀다.
>
> 아래 §1 의 코드 관찰("32 KB 창이 F32 에서 92.9 ms 로 의도의 절반")은 소스와 산술만으로
> 성립하므로 **여전히 VERIFIED** 다. 다만 그것이 잔여 끊김의 원인이라는 주장은
> 이 카드로는 증명되지 않았다. 소스는 전부 원복했고(§4.7), 버퍼 축을 닫는 근거는
> 이 카드가 아니라 **#257 의 통제된 8개 변종 A/B** 뿐이다.


날짜: 2026-07-29
선행: #525 (잔여 끊김이 2.5초 주기 호스트 정지와 1:1 일치함을 확정), #524, #250
원본 실행파일·게임 자산 무수정. 변경은 BoxedWine 런타임 소스에만 있고, **URL 파라미터가
없으면 동작이 이전과 완전히 동일**하도록 게이트했다.

## 1. 결함 (VERIFIED — 코드 + 산술)

`source/kernel/devs/devdsp.cpp` 의 주석이 의도를 명시한다.

```c
// Preserve the approximately 186 ms OSS queue window when the
// browser output ceiling is raised from 11.025 kHz to 44.1 kHz.
// Keeping eight 1 KiB fragments would shrink the window to about
// 46 ms and makes ordinary browser scheduling jitter audible.
this->fragmentCount = DSP_DEFAULT_FRAGMENT_COUNT * dspMaxOutputFreq / 11025;
```

상수는 `DSP_DEFAULT_FRAGMENT_SIZE = 1024`, `DSP_DEFAULT_FRAGMENT_COUNT = 8` 이다.
`dspMaxOutputFreq = 44100` 이면 `fragmentCount = 8 × 4 = 32`, 창은 `1024 × 32 = 32,768` 바이트.
`platform/sdl/kdspaudio.cpp` 의 `DSP_BUFFER_SIZE` 도 정확히 같은 32 KB 다.

**32,768 바이트가 186 ms 가 되려면 초당 176,400 바이트여야 한다 — 즉 44.1 kHz · 2ch · 16bit.**
그런데 이 게임이 실제로 여는 장치는 32비트 float 이다. 게스트 로그가 직접 말한다.

```text
openAudio: freq=44100(got 48000) format=8120(got 8120) channels=2(got 2)
```

`0x8120 = AUDIO_F32LSB`. 따라서 초당 44100 × 2 × **4** = 352,800 바이트이고,

```text
32,768 / 352,800 = 92.9 ms
```

**의도한 186 ms 의 정확히 절반이다.** 주석이 "46 ms 면 브라우저 스케줄링 지터가 들린다" 고
경고한 바로 그 실패 모드가, 절반 크기에서 다시 발생하고 있었다.

## 2. 왜 이것이 잔여 끊김을 설명하는가 (VERIFIED)

#525 에서 실측한 호스트 정지는 **87 ~ 185 ms**(중앙값 129 ms), 60 초에 24 회다.
여유분 93 ms 는 이 정지 대부분보다 짧다. 산술 예측과 실측이 맞는다.

```text
예측 무음 = 24 × (129 - 93) ms = 0.86 s
실측 무음 = 무음 콜백 35 개 × 42.7 ms = 1.5 s     (같은 자릿수)
```

세 개의 상한이 여유분을 결정한다. 가장 작은 것이 구속한다.

| 상한 | 값 | F32 44.1 kHz 기준 |
|---|---|---|
| `getWriteCapacity()` 의 `bytesPerSecond/8` | 1/8 초 | 125 ms |
| `DSP_BUFFER_SIZE` | 32 KB | **92.9 ms** ← 구속 |
| `fragmentSize × fragmentCount` | 32 KB | **92.9 ms** ← 구속 |

## 3. 변경 (구현 완료, 효과는 §4)

여유분을 바이트가 아니라 **시간**으로 표현하고, URL 파라미터 `audioRunwayMs` 로 요청받는다.
파라미터가 없으면 `azrokAudioRunwayMs()` 가 0 을 돌려주고 모든 호출자가 기존 상수 경로를
그대로 탄다 — **채택된 스템의 동작은 바뀌지 않는다.**

- `platform/sdl/kdspaudio.cpp`
  - `azrokAudioRunwayMs()` 추가 (`MAIN_THREAD_EM_ASM_INT` 로 `location.search` 를 읽는다.
    워커의 `location` 은 워커 스크립트 URL 이므로 반드시 메인 스레드에서 읽어야 한다.)
  - `dspWindowBytes()` 추가. 기존 `DSP_BUFFER_SIZE` 사용처 5곳을 이것으로 교체.
  - `getWriteCapacityWant()` 는 런웨이가 요청된 경우 `bytesPerSecond/8` 상한을 우회한다.
  - `DSP_BUFFER_SIZE_MAX (1024*256)` 를 요청값의 천장으로 둔다.
- `source/kernel/devs/devdsp.cpp`
  - `getEffectiveBufferCapacity()` 에서, 런웨이가 요청된 경우 **포맷을 알기 전에 계산된**
    fragment 창이 런웨이를 깎지 못하게 한다.
- `include/kdspaudio.h` — `azrokAudioRunwayMs()` 선언.
- `project/emscripten/makefile` — 채택 타깃과 플래그가 동일하고 출력 디렉터리만 다른
  비공개 타깃 `azrokRunway` (`Build/AzrokRunway1`) 추가. **채택 타깃은 건드리지 않았다.**

공유 헤더 `include/kdspaudio_math.h` 의 `getWriteCapacity()` 는 단위 테스트
(`source/test/devs/testDspAudio.cpp`)가 값을 고정하고 있어 **손대지 않았다.**
우회는 호출부에서만 한다.

빌드: `boxedwine.audiorunway1.wasm` 3,050,357 바이트 / `.js` 327,337 바이트.
(채택 스템은 3,048,524 / 326,898 — 차이는 추가된 코드 분량과 일치한다.)

## 4. 검증 (NOT VERIFIED — 측정 진행 중)

측정 축은 **게스트 탭**이다. 사용자가 브라우저를 음소거한 상태여서 WASAPI 루프백과
원본 상관 대조는 이 구간에서 무효다(#525 §6.5).

기준선 (`storage=memory` leg, 채택 스템, 60 초):

```text
blocks=24  blockMed=129ms  blockMax=184ms  interval=2425ms
callbacks=1407  silent=35  silentPct=2.49  fps=36.71
```

### 결과 — 창만 키우는 것은 **역효과** (VERIFIED)

| 지표 | 기준선 | `audiorunway1` + `audioRunwayMs=320` |
|---|---|---|
| 무음 콜백 | 2.49% | **4.12%** (악화) |
| 정지 횟수 | 24 | 19 |
| 정지 길이 중앙값 | 129 ms | **194 ms** (악화) |
| 정지 최대 | 184 ms | 223 ms |
| 정지 간격 중앙값 | 2,425 ms | 3,103 ms |
| fps | 36.71 | 32.28 |

**정지가 더 드물어지고 더 길어졌다.** 창을 3.4 배로 키웠더니 정지 길이가 1.5 배가 됐다.
분당 총 정지 시간은 3.10 초 → 3.69 초로 비슷하다(둘 다 벽시계의 5~6%).

이 반응 자체가 단서다. 정지 길이가 오디오 버퍼 크기를 따라 움직인다면,
정지는 **오디오/디코드 경로에서 한 번에 처리하는 덩어리 크기**에 비례하는 일일 가능성이 크다.
#525 에서 관측한 "정지 간격이 87~91 프레임으로 거의 일정" 도 이 조건에서 89 → 100 프레임으로
이동했으므로, 순수한 프레임 고정 주기라는 해석은 약해진다.

## 4.5 왜 창만으로는 부족한가 — Wine 쪽 상한 (VERIFIED, 소스)

`artifacts/wine11_source/wine-11.0/dlls/wineoss.drv/oss.c`:

```c
max_period = max(bi.fragsize / stream->fmt->nBlockAlign, stream->period_frames);
...
write_limit = 0;
while(write_limit + in_oss_frames < max_period * 3)
    write_limit += max_period;
```

Wine 의 OSS 드라이버는 **프래그먼트 3개 분량까지만** 앞서 쓴다.
BoxedWine 이 광고하는 `fragsize` 는 `DSP_DEFAULT_FRAGMENT_SIZE = 1024` 바이트(F32 스테레오 128 프레임),
Wine 기본 주기 `def_period = 100000` = 10 ms(44.1 kHz 에서 441 프레임).
`max_period = max(128, 441) = 441` 이므로 선행분은 `3 × 441 = 1323` 프레임 ≈ **30 ms** 에 묶인다.

**총 창을 키워도 Wine 이 그만큼 쓰지 않는다.** 실제 지렛대는 창이 아니라
**광고하는 프래그먼트 크기**다. `getFragmentSize()` 가 런웨이의 1/3 을 돌려주도록 한 변종을
`boxedwine.audiorunway2` 로 빌드했다(3,050,505 바이트).

## 4.6 선행 연구 대조 — 이 파라미터 공간은 이미 훑렸다 (VERIFIED, #257)

`boxedwine.upstreamjit15audiofrag8192` 를 단서로 #257 을 찾았다. 2026-07-22 에
같은 축이 8개 변종으로 이미 A/B 됐고, 결론이 명확히 기록돼 있다.

| 변종 | exact-zero 무음 |
|---|---|
| jit8 real-prebuffer, period4096 | 2.7905% |
| **jit9 period2048** | **2.3047%** ← 채택 |
| jit10 96 ms start queue | 2.6267% |
| jit11 5 ms POLLOUT 타이머 | 3.5216% |
| **jit15 8192 B fragment** | **4.0978%** ← 기각 |

> `jit10~13` 과 `jit15` 는 **REJECTED** 이며 소스는
> `period2048 + 48 ms real prebuffer + 32 KiB/기존 OSS semantics` 기준으로 되돌렸다.

**프래그먼트 확대는 이미 시도됐고 무음을 2.30% → 4.10% 로 악화시켜 기각됐다.**
오늘의 T1(창 확대)이 2.49% → 4.12% 로 악화된 것과 방향·크기가 거의 같다.
현재 값은 임의로 정해진 게 아니라 그때의 최적점이다.

### 그리고 잔여 무음은 새 문제가 아니다

#257 이 채택 시점에 남긴 잔여 무음은 **2.3047%**, 오늘 기준선 측정은 **2.49%** 다.
사실상 같은 값이다. 즉 지금 남은 끊김은 이번에 생긴 회귀가 아니라
**2026-07-22 부터 알려져 있던 바닥값**이다.

#257 은 다음 단계를 이렇게 못박아 두었다.

> **NOT VERIFIED / next:** 게스트 입력 PCM zero-frame 누계와 동일 시각의 host queue
> underflow 를 연결해 남은 2.3% 중 원본/guest silence 와 실제 host starvation 을 분리한다.
> 우선순위/AudioWorklet 측 변경은 이 판별 뒤에만 한다.

**#525 가 그 판별을 끝냈다.** 드롭아웃 7/7 이 호스트 메인 스레드 정지와 일치했고
게스트가 만든 무음이 아니었다. 즉 남은 2.3~2.5% 는 **host starvation** 쪽이며,
#257 이 조건부로 허용한 "우선순위/AudioWorklet 축" 이 이제 열린다.

### 왜 버퍼로는 못 막는가

`boxedwine-multithreaded-audio.js` 는 `SDL2.audio` / `audioContext` 를 건드리는 EM_ASM 을
**메인 스레드로 프록시**한다. 따라서 게스트의 오디오 큐잉 자체가 메인 스레드 작업이다.
메인 스레드가 멈추면 큐를 채울 수도 없다. 큐를 더 깊게 만들려면 프록시 호출당 더 큰
덩어리를 넘겨야 하고, 그러면 메인 스레드 점유가 길어져 정지가 더 길어진다 —
T1 에서 정지 중앙값이 129 ms → 194 ms 로 늘어난 것이 이 되먹임이다.
**버퍼 축은 자기 모순이라 여기서 끝난다.**

## 4.7 프래그먼트 확대 결과 — 런타임 붕괴 (VERIFIED)

`boxedwine.audiorunway2` + `audioRunwayMs=320`, 즉 광고 프래그먼트 ≈ 107 KB:

| 지표 | 기준선 | T1 (창) | **T2 (프래그먼트)** |
|---|---|---|---|
| 무음 콜백 | 2.49% | 4.12% | **72.64%** |
| 정지 횟수 / 60 초 | 24 | 19 | **226** |
| 정지 길이 중앙값 | 129 ms | 194 ms | 235 ms |
| 정지 간격 중앙값 | 2,425 ms | 3,103 ms | **248 ms** |
| fps | 36.71 | 32.28 | **4.21** |

거대한 프래그먼트 때문에 Wine 이 한 번에 엄청난 양을 메인 스레드 프록시로 밀어 넣고,
정지가 사실상 연속(간격 248 ms, 길이 235 ms)이 되어 게임이 4 fps 로 무너졌다.
#257 의 `jit15` 기각을 훨씬 강한 신호로 재현한 셈이다.

### 원복

두 변종 모두 실패했으므로 **공유 트리에 비활성 게이트 코드를 남기지 않고 전부 되돌렸다.**

- `platform/sdl/kdspaudio.cpp` — `azrokAudioRunwayMs()`, `dspWindowBytes()`,
  `getFragmentSize()` 오버라이드, `getWriteCapacityWant()` 분기, `DSP_BUFFER_SIZE_MAX`,
  `<emscripten.h>` 포함 전부 제거. `DSP_BUFFER_SIZE` 사용처 6곳 원상복구.
- `include/kdspaudio.h` — 선언 제거.
- `source/kernel/devs/devdsp.cpp` — `getEffectiveBufferCapacity()` 원상복구.
- `project/emscripten/makefile` — `azrokRunway` 타깃과 `.PHONY` 항목 제거.

원복 후 잔존 참조 0건을 확인했고, 채택 타깃 재빌드로 컴파일도 확인했다.
채택 스템은 처음부터 건드리지 않았다.

## 5. 미결

- 2.4~2.9 초마다 87~185 ms 씩 발생하는 호스트 정지의 정체. `longtask` 0 건,
  LoAF 무귀속, 힙 증가 0 건, `storage=memory` 로도 불변. **프레임 기준 주기가
  87~91 프레임으로 거의 일정**하다는 것이 가장 강한 단서다(#525 §6).
- 브라우저 Present 율 34~37 fps. 목표 50 fps 와의 격차는 별도 축.
- 런웨이를 키우면 효과음 지연도 함께 늘어난다. 청취로 확인할 것.
