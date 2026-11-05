# 283. Gate 6 — sticky GP merge 정확성 기각과 clean-entry read cache

## 결론

- **VERIFIED:** `BOXEDWINE_WASM_JIT_STICKY_GP_MERGE` 계열은 정상 ABI2와 분리되는 startup correctness 회귀를 일으킨다. 성능 A/B 대상으로 보내지 않고 기각한다.
- **VERIFIED:** `EAGER-only`는 로그인과 heartbeat까지 생존했다. 따라서 회귀를 `loadAllGPRegs()` 자체나 선로드만으로 귀속할 수 없다.
- **VERIFIED:** merge-only와 mergefix는 각각 143초, 319초 동안 페이지/JS/WASM/app/root HTTP 200을 받았지만 `WS_ACCEPT`가 한 번도 없었다. 이는 PatHouse 렌더 뒤 문제가 아니라 TCP/WS 로그인 전 startup stall이다.
- **CORRECTED:** 이전에 mergefix에 귀속했던 PatHouse 및 heartbeat #37 로그는 17:01:15 자산 요청으로 시작한 정상 ABI2 fresh 세션이었다. full-sticky에도 해당 서버 로그를 귀속하지 않는다.
- **NOT VERIFIED:** MERGE가 처음 손상시키는 정확한 JIT block, guest register, instruction은 아직 trace로 특정하지 않았다.
- **VERIFIED static/build/runtime/browser:** clean IF 진입에서 `m_gpDirty` 8개가 모두 false일 때만 현재 `m_gpLoaded`를 보존하고, `StartElse`/`EndIf`는 기존 flush/invalidate를 유지하는 제한 후보는 CPU/JIT 회귀와 cache-OFF PatHouse 렌더를 통과했다.
- **VERIFIED performance / REJECTED:** 제한 후보의 A-B-A-B exact-Present 효과 중앙값은 **-2.924%**, 조건 평균은 A `48.9231` 대 B `46.4888 FPS`(**-4.976%**)였다. renderer CPU/Present도 두 B 구간 모두 인접 A보다 높아 성능 후보로 기각한다.

## 동적 세션 상관관계

KST 기준 로그 상관관계는 다음과 같다.

| 런타임 | HTTP 자산 | WS/서버 결과 | 판정 |
|---|---:|---|---|
| ABI2 fresh | 17:01:15 | 17:02:06 WS, 17:03:26 bootstrap, PatHouse/#37 | VERIFIED 정상 |
| eager-only | 17:07:47 | 17:08:27 WS, heartbeat 후 17:09:08 페이지 전환 | VERIFIED startup 생존; PatHouse는 조기 중단으로 미판정 |
| merge-only | 17:09:11 | 143초 동안 WS_ACCEPT 0 | VERIFIED pre-login stall |
| mergefix | 17:11:38 | 319초 동안 WS_ACCEPT 0 | VERIFIED pre-login stall |
| ABI2 restore | 17:17:30 | 17:18:10 WS, 17:19:32 bootstrap, PatHouse 복구 | VERIFIED 정상 |

브라우저 FPS HUD는 DOM/console에만 방출되고 파일 로그로 영속되지 않는다. 따라서 과거 파일만으로 merge의 `Present=0`을 직접 증명하지 않는다.

## 정적 원인 경계

`GpBranchFrame`은 `entryDirty`와 `thenDirty`만 저장한다. 반면 다음 상태는 프레임에 없다.

- arm 진입 당시의 `m_gpLoaded`
- helper 호출 이후의 cache generation
- managed `finishIf()` 밖 raw `m_emitter.emitIf()` 경로

MERGE의 `StartElse()`와 `EndIf()`는 이 불완전한 상태로 `m_gpLoaded.fill(true)`를 수행한다. 파일의 memory fast/slow helper와 bailout 경로는 raw conditional 및 수동 tracker 저장/복원에 의존하므로, 전체 CFG가 관리되지 않는 상태에서 join 뒤 모든 GP local을 유효하다고 승격하는 것은 증명되지 않는다.

## 제한 후보의 불변식

새 `BOXEDWINE_WASM_JIT_IF_READ_CACHE`는 다음만 허용한다.

1. `structuredBranchBoundary()` 진입 시 GP dirty가 하나라도 있으면 기존 `branchBoundary()`를 그대로 실행한다.
2. GP dirty가 전부 false이면 현재 valid read locals만 보존하고 segment cache는 무효화한다.
3. `finishIf()`는 frame/normalize 없이 `emitIf()`만 실행한다.
4. `StartElse()`와 `EndIf()`는 기존 `branchBoundary()`를 유지한다.
5. raw `emitIf`, helper, memory slow path는 변경하지 않는다.

보존 불변식은 `dirty[r] == false && loaded[r] == true`일 때 `local[r] == CPU.reg[r]`이다. arm 종료마다 기존 flush/invalidate가 남으므로 한 arm의 write cache를 다른 arm으로 병합하지 않는다.

## 검증 게이트

- **VERIFIED:** 클린 테스트 빌드 `Build/TestMultiThreadedJitIfReadCache1` 완성.
- **VERIFIED:** 실제 WASM JIT 첫 entry를 거친 DIV/IDIV fault arms, indirect-boundary flags, string 24종, LOOP 6종, DIV16/32, SMC 4종, implicit locked XCHG SMC가 모두 통과했다.
- **VERIFIED:** 전체 `-fast`는 637개 중 628개 통과했다. 실패 9개는 이전과 같은 MT broker Node harness `callHandler` 항목이며 신규 CPU/JIT 실패는 0이다.
- **VERIFIED:** 제품 런타임 `boxedwine.upstreamjit66ifreadcache1`을 cache-OFF로 실행해 선택 화면과 기준 PatHouse를 렌더했다. 벽·카펫·가구·캐릭터·한글 UI가 온전했다.
- **VERIFIED:** 기록 모드는 41,901 blocks / 62,775,596 raw bytes를 저장했다. 기준과 동일한 commonfast64/depth-local/fn6-inline pipeline은 135 groups를 만들었고 `WebAssembly.validate` 135/135를 통과했다.
- **VERIFIED:** A drift가 -4.466%여서 사용자 규칙대로 A-B-A-B로 연장했고, 모든 표본은 `visible`, `hidden=false`였다.

### A-B-A-B 결과

| leg | exact Presents / elapsed | exact FPS | HUD mean | renderer CPU ms/Present | foreground |
|---|---:|---:|---:|---:|---|
| A1 ABI2 | 1,560 / 31.1747s | 50.0406 | 50.4567 | 40.825 | WindowsTerminal 31/31 |
| B1 read-cache | 1,440 / 30.9215s | 46.5696 | 46.7867 | 44.748 | WindowsTerminal 31/31 |
| A2 ABI2 | 1,440 / 30.1220s | 47.8056 | 47.6433 | 43.283 | WindowsTerminal 31/31 |
| B2 read-cache | 1,440 / 31.0291s | 46.4080 | 46.4267 | 44.347 | WindowsTerminal 31/31 |

인접 정규화 효과는 `B1/A1 -6.936%`, `B1/A2 -2.586%`, `B2/A2 -2.924%`; 중앙값은 **-2.924%**다. 두 조건 평균은 A `48.9231`, B `46.4888 FPS`로 B가 **-4.976%**다. 후보 cache가 기준보다 276개 많은 블록을 포함해 잠재적으로 유리한 조건이었는데도 결과가 음수이므로, 동일 블록 집합 재가공 없이 기각할 충분한 직접 증거다.

산출물:

- runtime JS SHA-256: `39FD867C77003040AA9B71CC4363237B32D86DE75A8CB6407D0B9F0AF50DDECD`
- runtime WASM SHA-256: `D48C7E155354C550F285188148AEFE3603240B8EC455DD3694362F39BBFFA4A8`
- candidate cache: `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch-ifreadcache1.zip`
- candidate cache SHA-256: `53FBCD89502A73DD43610075302C4F0ECA0131D9B58945AF4193B7874371F392`
- covariates: `ifreadcache_A1/B1/A2/B2_covariates.json`

## 현재 채택 상태

정상 복구 기준은 계속 `boxedwine.upstreamjit64fn6inlineabi2` + `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2.zip`이다. A1 exact 50.04 FPS 하나만으로 안정 50 FPS를 확정하지 않는다. A2가 47.81 FPS였으므로 전체 안정 50 FPS 게이트는 계속 **NOT VERIFIED**다. full sticky merge와 clean-entry read-cache 모두 기본/채택 경로에 포함하지 않는다.
