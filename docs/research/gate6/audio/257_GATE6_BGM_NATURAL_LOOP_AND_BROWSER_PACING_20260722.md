# Gate 6 — BGM 자연 루프와 브라우저 오디오 페이싱 실측 (2026-07-22)

> **FOLLOW-UP: 258에서 Wine DirectSound의 실제 생산 수위를 32 ms에서 80 ms로 늘린 근본 수정을 채택했다.** 이 문서의 자연 루프 결론은 유지되며, `jit9`를 최선으로 본 페이싱 결론만 258로 갱신된다.

## 자연 루프

- **VERIFIED (100 s WASAPI loopback):** `evidence/upstreamjit7_bgmloop_100s_20260722.wav`는 48 kHz stereo 100.000 s이며 원본 `Data/Sound/PetHouse.mp3`의 spectral fingerprint와 안정 구간 상관 `0.931~0.950`으로 일치한다.
- **VERIFIED:** 캡처 `17.5 s -> source 83.65 s`, `20.0 s -> source 0.85 s`로 tail-to-head wrap이 일어났다. `18.802146~19.105687 s`의 루프 경계 뒤 두 번째 cycle PCM이 90초 지점까지 계속되었다.
- **VERIFIED:** BGM이 한 번만 재생되고 멈추는 문제는 Wine seek-flush 수정과 현재 root에서 해소되었다. 효과음과 BGM은 같은 브라우저 세션에서 함께 출력된다.

## 느림/끊김의 직접 측정

초기 100초 캡처의 source 진행률은 wall time의 약 `0.970~0.971`이었고 exact-zero는 `3.34994%`였다. 원본 MP3 정상 decode의 exact-zero는 `0.07385%`뿐이다. 44.1->48 kHz 변환 비율은 동적 누계에서 `1.088244`, 이론 `1.088435`와 일치하므로 sample-rate 오해가 아니다.

`topUpSilence()`가 real PCM 뒤에 합성 무음을 큐잉하던 경로를 제거하고, real PCM만으로 시작 임계치를 채우는 prebuffer로 바꿨다. Emscripten SDL period를 `4096 -> 2048 frames`로 줄인 빌드가 현재 A/B 중 가장 낮은 무음을 냈다.

| 빌드 / 30 s | exact-zero | >=5 ms | >=20 ms | 최장 |
|---|---:|---:|---:|---:|
| jit8 real-prebuffer, period4096 | 2.7905% | 40 / 0.6257 s | 9 / 0.2822 s | 38.917 ms |
| **jit9 period2048** | **2.3047%** | **40 / 0.5108 s** | **6 / 0.1615 s** | **31.063 ms** |
| jit10 96 ms start queue | 2.6267% | 42 / 0.5552 s | 7 / 0.2210 s | 58.729 ms |
| jit11 5 ms POLLOUT timer | 3.5216% | 64 / 0.8140 s | 6 / 0.1967 s | 73.729 ms |
| jit12 nominal 64 KiB | 5.9006% | 103 / 1.5150 s | 13 / 0.4661 s | 59.083 ms |
| jit13 true 186 ms GETOSPACE cap | 12.6752% | 199 / 3.4551 s | 34 / 1.5319 s | 407.667 ms |
| jit15 8192 B fragment | 4.0978% | 83 / 1.0216 s | 7 / 0.2017 s | 35.167 ms |

`jit10~13`과 `jit15`는 **REJECTED**이며 소스는 `period2048 + 48 ms real prebuffer + 32 KiB/기존 OSS semantics` 기준으로 되돌렸다.

## 깨우기 판정

- **VERIFIED (static path):** Wine 11 `wineoss` BGM writer는 `poll(POLLOUT)`을 사용하지 않는다. `audio_client_timer`가 기본 10 ms마다 `NtDelayExecution` 후 `SNDCTL_DSP_GETOSPACE`와 nonblocking `write()`를 직접 호출한다.
- **VERIFIED (static path):** 이 대기는 BoxedWine `select(nfds=0)` -> `KThread::sleep` -> Emscripten dummy futex timeout이다. 별도 condition signal 발신자는 없다. 따라서 `SDL_AddTimer(5)`/`BoxedWineCondition` missed-wake는 이 실행 경로의 원인이 아니다.
- **VERIFIED (dynamic):** 5 ms POLLOUT timer A/B가 무음을 줄이지 않았다. 실제 1초 창의 guest/device 생산은 각각 기대치의 약 `95.3%`였고 변환 비율은 정상이었다. write gap은 보통 `20~47 ms`, 관측 최대 `77 ms`였다.
- **INFERRED:** 남은 짧은 underflow의 주원인은 브라우저 Web Worker timed-wait oversleep/재스케줄 지연이다. Wine이 요청한 TIME_CRITICAL 우선순위는 BoxedWine `setpriority`에서 적용되지 않는다.

## 현재 상태와 다음 검증

- **ACCEPTED CURRENT:** `boxedwine.upstreamjit14audiobest`와 동일한 period2048/48 ms real-PCM prebuffer 기준. 자연 루프는 완료됐고, A/B 중 무음 지표가 가장 낮다.
- **NOT VERIFIED / next:** 게스트 입력 PCM zero-frame 누계와 동일 시각의 host queue underflow를 연결해 남은 2.3% 중 원본/guest silence와 실제 host starvation을 분리한다. 우선순위/AudioWorklet 측 변경은 이 판별 뒤에만 한다.

## 증거

- `docs/research/evidence/upstreamjit7_bgmloop_100s_20260722.wav`
- `docs/research/evidence/upstreamjit8_audioprebuffer_30s_20260722.wav`
- `docs/research/evidence/upstreamjit9_period2048_30s_20260722.wav`
- `docs/research/evidence/upstreamjit10_queue96_30s_20260722.wav`
- `docs/research/evidence/upstreamjit11_wake5_30s_20260722.wav`
- `docs/research/evidence/upstreamjit12_audio64k_30s_20260722.wav`
- `docs/research/evidence/upstreamjit13_formatcap_30s_20260722.wav`
- `docs/research/evidence/upstreamjit15_frag8192_30s_20260722.wav`
