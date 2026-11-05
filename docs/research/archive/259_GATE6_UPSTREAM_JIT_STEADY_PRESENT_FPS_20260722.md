> **SUPERSEDED by 260.** 97.1043 FPS 구간을 PatHouse 안정 체류로 잘못 판정했습니다. 실제 PatHouse 체류 중 페이지 HUD와 exact Present 재측정은 26.5046 FPS였습니다. 아래 기록은 오판 경위를 보존합니다.

# 259 Gate 6 official upstream JIT steady Present FPS (2026-07-22)

## 결론

- **VERIFIED (dynamic/browser):** 현재 배포 후보 `boxedwine.upstreamjit17release`는 1024×768 PatHouse에서 로딩과 JIT 워밍업 이후 exact `COMMAND.PRESENT` 기준 **97.1043 FPS**를 기록했습니다.
- **VERIFIED (dynamic/browser):** 사용자가 기억한 “PatHouse 90 FPS 초과”는 맞습니다. 다만 그 성능의 주체는 과거 custom `boxedwine.callaware4`가 아니라 현재 official-upstream-JIT release17입니다.
- **REJECTED:** 문서 247의 CallAware4 **95.1518 FPS** 주장은 같은 아티팩트의 exact Present 재측정에서 **19.5355 FPS**로 기각됐습니다.
- **CORRECTED:** release17을 **27.31 FPS**로 본 직전 판정은 게임 로딩과 JIT 워밍업이 섞인 초기 구간을 steady state로 잘못 취급한 값이었습니다.
- **VERIFIED (visual/audio):** 한 탭만 사용했고, 최종 release17 PatHouse의 벽·카펫·가구·캐릭터·한글 UI가 유지됐습니다. 사용자는 같은 빌드의 BGM 자연 루프가 정상적으로 들린다고 확인했습니다.

## 측정 계약

호스트의 `D3D9WebDebug.presents`는 `recordDispatch(COMMAND.PRESENT)`에서만 증가합니다. 페이지의 `data-d3d9web-loop` 형식은 다음과 같습니다.

```text
commands:presents:lastCommand:lastBytes
```

따라서 아래 결과는 `D3D9WEB_HOST_JS_PROFILE batches`나 명령 배치 수가 아니라 실제 D3D9 Present 누적 차이입니다. 각각 10초 벽시계 구간 두 번을 썼으며, 브라우저 탭은 하나만 유지했습니다.

## CallAware4 재측정

- runtime: `boxedwine.callaware4`
- app: `Azrok_D3D9Web_pathouse_stateblock1`
- root: `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1`
- 장면: intact 1024×768 PatHouse

| 구간 | wall | Present delta | FPS |
|---:|---:|---:|---:|
| 1 | 10.034 s | 199 | 19.8326 |
| 2 | 10.032 s | 193 | 19.2384 |
| 합계 | 20.066 s | 392 | **19.5355** |

독립 guest profile의 `present_delta=120` 로그 간격도 약 6.012, 6.020, 6.368, 6.451, 6.366초였으므로 약 18.6~20.0 FPS 범위로 일치합니다. generated Wasm 실행 자체는 관찰됐지만 50-FPS gate에는 실패합니다.

## official upstream JIT release17 재측정

- runtime: `boxedwine.upstreamjit17release`
- app: `Azrok_D3D9Web_pathouse_stateblock1`
- root: `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1`
- 장면: intact 1024×768 PatHouse

| 구간 | wall | Present delta | FPS |
|---:|---:|---:|---:|
| 1 | 10.036 s | 969 | 96.5524 |
| 2 | 10.035 s | 980 | 97.6582 |
| 합계 | 20.071 s | 1,949 | **97.1043** |

독립 guest `D3D9WEB_GUEST_PROFILE present_delta=120` 로그도 후반부에서 약 1.171~1.375초마다 나와 같은 약 87~102 FPS 범위를 지지합니다.

## 판정

- 최종 목표인 1024×768 PatHouse 평균 50 FPS는 현재 steady-state에서 **통과**합니다.
- 초기 로딩/컴파일 구간과 steady state를 분리해 보고해야 합니다. 이후 성능 회귀 판정은 PatHouse 장면 확인 후 최소 10초 워밍업을 버리고, exact Present 10초 구간 두 개 이상으로 고정합니다.
- custom CallAware4 전체를 다시 채택하지 않습니다. official upstream JIT를 기준으로 유지하며, 정적 비교에서 확인되는 게임별 최소 차이만 별도 검토합니다.
- 아직 별도 gate인 초기 로딩 시간, 장시간 OOM, 포인터 잠금 카메라, 여러 브라우저 세션 멀티플레이는 이 측정으로 완료되지 않습니다.

## BGM 루프 관련 병행 판정

사용자 청감상 현재 루프는 정상입니다. 별도 동적 trace에서는 남은 약 300ms 경계 무음이 BoxedWine wake 실패가 아니라 Wine Quartz `dsoundrender.c`의 EOS 전체 secondary-buffer 무음 덮기 뒤 `EC_COMPLETE`를 보내는 순서로 좁혀졌습니다. 기능상 현재 허용되므로 이 문서에서는 수정하지 않고 원인만 보존합니다.
