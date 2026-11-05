# 282 Gate 6 `fn_6` inline fetch ABI2와 PatHouse A-B-A-B (2026-07-23)

## 결론

- **VERIFIED (static/build):** common dispatcher의 hot `helpers.fn_6` 경계를 `CPU::opCache` 10/10/12 lookup으로 대체하는 ABI2 산출물을 만들었습니다. `thread->terminating`, `thread->process`, 16-bit EIP/CS base, cold miss의 원래 `fn_6` 복귀를 상류 `NormalCPU::getOp()` 의미와 대조했습니다.
- **VERIFIED (artifact):** 134/134 그룹이 `WebAssembly.validate`를 통과했고, 41,625 ordinary function과 32,439 기존 patch target은 기준과 동일합니다. 바뀐 것은 134 dispatcher와 manifest뿐이며 ABI2의 process-null guard는 dispatcher당 정확히 8바이트입니다.
- **VERIFIED (browser/render):** 단일 visible 브라우저 탭의 1024x768 CSS 표시에서 PatHouse 3D 부트스트랩 장면을 네 번 재현했습니다. 카펫 반복, 벽 소실, 가구/캐릭터 텍스처 오염, 한글 깨짐은 없었습니다.
- **VERIFIED (performance):** 적응형 A-B-A-B의 30초 exact-Present FPS는 `46.4589 / 46.2416 / 43.1820 / 49.8023`이었습니다. 정상화한 인접 B-A 효과는 `-0.47% / +7.09% / +15.33%`, 중앙값은 **+7.09%**입니다. 재시작 구간 조건 평균은 A `44.8205`, B `48.0220 FPS`, 즉 **+7.14%**입니다.
- **VERIFIED (sustain):** B2를 재시작하지 않고 30초 더 측정한 값은 `48.4485 FPS`; B2 연속 60초 합산은 약 `49.12 FPS`입니다. 이 후보는 채택 가치가 있지만 **안정적 50 FPS는 아직 NOT VERIFIED**입니다.
- **PARTIAL (network-room):** 모든 구간에서 서버 부트스트랩 `0003/0007/0005/000A/000B`와 클라이언트 `0017 x2/0008`, heartbeat는 정상입니다. 그러나 이 측정 세션은 C2S `0x0005` character-select가 없어 서버의 `connection.room_kind/name`은 미확인이었습니다. 따라서 본 문서는 동일한 PatHouse 3D 렌더 워크로드와 성능만 검증하며, 정식 room 진입 증거로 쓰지 않습니다.

## 구현과 정적 계약

### 런타임

- source: `C:\bwujit\source\emulation\cpu\wasm\jitWasmCodeGen.cpp`
- build target: `Build/AzrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbi2`
- deployed stem: `boxedwine.upstreamjit64fn6inlineabi2`
- JS SHA-256: `39FD867C77003040AA9B71CC4363237B32D86DE75A8CB6407D0B9F0AF50DDECD`
- WASM SHA-256: `F1C29C7F2EE8FE7170F54A104F683F1091B0ED22E0A1A5C2384D58487A2FCEF0`

### replay cache

- artifact: `tools/boxedwine_local/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2.zip`
- SHA-256: `48B07223AD07CF963D179597046B3CE99C4D06CBB884306AFB03910B8EA6C676`
- size: 6,714,822 bytes
- groups/entries/patches: `134 / 41,625 / 32,439`
- live ABI: `nextOp740:depth1660:bailout132:pfn12:map12964392:capacity262144`
- inline ABI2: `thread728:terminating72:process36:eip112:cs48:big1632:opCache652`

### 의미 대조

1. `thread->terminating`이면 `nextOp=null`로 종료합니다.
2. `thread->process`의 wasm32 libc++ `shared_ptr` 첫 word가 null이면 종료합니다. 이는 상류 `NormalCPU::getOp()`의 첫 process guard와 같습니다.
3. 주소는 `(big ? eip : eip & 0xffff) + CS.address`입니다.
4. `opCache`는 page index의 10/10/12 계층을 읽습니다.
5. 어느 계층이든 null이면 원래 `helpers.fn_6`으로 fail closed 합니다. decode/mutex slow path를 복제하지 않습니다.
6. profile/record와 replay는 페이지에서 상호 배타이며, getter/manifest가 하나라도 다르면 inline path를 활성화하지 않습니다.

## 동적 측정

| 구간 | runtime/cache | exact FPS | HUD mean | HUD min..max | renderer CPU / 30s | hidden | foreground |
|---|---|---:|---:|---:|---:|---:|---|
| A1 | accepted chain64/depth-local | 46.4589 | 46.2833 | 40.2..50.6 | 61.641s | 0 | ChatGPT |
| B1 | fn6 inline ABI2 | 46.2416 | 46.0933 | 42.4..49.2 | 64.188s | 0 | ChatGPT |
| A2 | accepted chain64/depth-local | 43.1820 | 43.1600 | 39.9..45.7 | 67.281s | 0 | ChatGPT |
| B2 | fn6 inline ABI2 | 49.8023 | 49.8933 | 46.2..52.4 | 62.047s | 0 | ChatGPT |
| B2-cont | 동일 런타임 연속 | 48.4485 | 48.4533 | 46.5..51.8 | 별도 JSON 참조 | 0 | ChatGPT |

공변량 파일:

- `tools/boxedwine_local/profiles/fn6inline_A1_covariates_retry.csv`
- `tools/boxedwine_local/profiles/fn6inline_B1_covariates.csv`
- `tools/boxedwine_local/profiles/fn6inline_A2_covariates.csv`
- `tools/boxedwine_local/profiles/fn6inline_B2_covariates.csv`
- `tools/boxedwine_local/profiles/fn6inline_B2_cont_covariates.csv`

A1/A2 drift는 -7.06%로 3% gate를 넘어서 A-B-A-B로 연장했습니다. foreground와 visibility throttle은 전 구간 같았지만 renderer CPU가 2.055/2.140/2.243/2.068 cores로 흔들렸습니다. 따라서 단일 최고치 49.8023을 50 FPS 달성으로 세지 않고, 인접쌍 중앙값과 B2 연속 구간을 함께 사용했습니다.

## 판정과 다음 gate

- **ACCEPTED:** ABI2 inline fetch runtime/cache를 다음 기준 후보로 올립니다. exact semantic gate, reference render, 중앙 +7.09%, 연속 B2 48.45 FPS가 근거입니다.
- **NOT VERIFIED:** 전체 플레이 세션에서 50 FPS 이상 유지.
- 다음 후보는 275/281의 주 병목인 broad guest-WASM 실행을 더 줄이는 것입니다. 우선순위는 `branchBoundary()`가 매 structured branch에서 GP local을 메모리로 flush/reload하는 비용입니다. helper/fault/SMC/bailout/exit에서만 architectural state를 동기화하고, 순수 Wasm control-flow 내부에서는 GP local을 유지하는 fail-closed spike를 먼저 정적 검증합니다.
