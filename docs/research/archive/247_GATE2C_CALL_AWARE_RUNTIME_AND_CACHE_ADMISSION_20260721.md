> **SUPERSEDED by 259.** CallAware4의 95.1518 FPS 주장은 2026-07-22 동일 아티팩트의 exact `COMMAND.PRESENT` 재측정에서 19.5355 FPS로 기각되었습니다. 아래 기록은 당시 오판 경위를 보존하기 위해 남깁니다.

# 247 Gate 2c call-aware runtime validation and cache admission (2026-07-21)

## 결론

- **VERIFIED (browser):** `RuntimeCallAware2` 단일 탭 PatHouse 실행은 기준 화면의 카펫, 벽, 식탁·의자, 캐릭터, 한글 UI를 그대로 유지했습니다.
- **VERIFIED (browser):** 안정 구간 840 Present가 11.365초였으며 `73.8526 FPS`였습니다. 인접 840-frame 창도 약 73.7~74.0 FPS였습니다. 따라서 1024x768 PatHouse의 50 FPS 목표는 화면 기준으로 처음 통과했습니다.
- **VERIFIED (telemetry):** 주 게임 스레드 `pid=71 tid=72`에서 generated-Wasm `executed_blocks=2256`, `executed_ops=76806`을 직접 확인했습니다. `pid=71`의 Acknex 매핑은 `0x7F360000..0x7F6DC000`입니다.
- **REJECTED AS LONG-RUN BUILD:** 같은 실행에서 aggregate compile attempts가 `1,048,576`까지 증가했습니다. 화면/FPS 통과만으로 장기 실행을 승인하지 않으며, 재컴파일 cache thrash를 제거한 후 재검증합니다.

## Call-aware 범위 확장

- **VERIFIED:** exact stack store-to-load forwarding, direct CALL/RET, `LEA`, derived effective-address chain, `CMP [mem],imm`, `JL`, absolute `JMP [disp32]` target guard가 Emscripten differential test를 통과했습니다.
- **VERIFIED:** 간접 thunk slot은 module entry와 commit 직전에 값과 decoded target identity를 다시 검사합니다. 슬롯 변화는 guest state를 commit하지 않는 `Fallback`입니다.
- **VERIFIED (static):** live CPU-patched transform 경로의 첫 미지원 명령은 `0x101042A9 AND ESP,0xfffffff0`이었습니다. outer `acknex+0x49650` trace는 이 한 명령을 포함하면 정확히 32 ops에 도달합니다.
- **VERIFIED (test):** `AndR32I32` lowering은 interpreter와 GPR/EIP/lazy destination/source/result/type가 일치하며 `FLAGS_AND32`를 보존합니다.

## 재컴파일 폭증 원인과 수정

- **VERIFIED (code review):** 256 compiled cap에서 새 후보가 기존 LRU block을 compile 성공 전에 제거했습니다. compile 실패 시 정상 block만 잃을 수 있었습니다.
- **VERIFIED (code review):** C++ block reset이 worker-local JS module Map을 제거하지 않아 두 LRU가 서로 다른 live set을 가질 수 있었습니다.
- **VERIFIED (code review):** 257개 이상의 활성 후보가 순환하면 evicted block이 짧은 cooldown 뒤 다시 compile되어 ping-pong할 수 있었습니다.
- **IMPLEMENTED / TESTED:** 후보 캐시 2048와 compiled cap 256을 분리하고, 후보 방문 빈도가 최저 빈도 compiled block보다 높을 때만 교체합니다. 거절 후보는 방문 수를 계속 축적하되 4096-hit cooldown을 갖습니다.
- **IMPLEMENTED / TESTED:** generated module 설치를 첫 execute까지 지연하고, compiled block destructor가 동일 `moduleId`를 worker-local JS Map에서도 제거합니다.
- **IMPLEMENTED / TESTED:** candidate-cache 축출은 미컴파일 entry를 우선하며, zero-op prefix는 identity-bound permanent reject로 기록합니다. 성공한 compile은 failure/backoff 상태를 초기화합니다.
- **VERIFIED (tests):** `node boxedwine.js 7 1 1`과 `node boxedwine.js 15 1 1` 모두 0 failures입니다. 1-slot resident/candidate fixture는 cold displacement와 immediate ping-pong을 막고, 더 뜨거워진 후보만 교체합니다.

## 증거 보존 경계

- 두 번째 유효 `callaware2_valid2` WebSocket 세션은 213.391초였고, PatHouse bootstrap 뒤 131.320초 유지됐습니다.
- 브라우저 콘솔 본문은 파일로 저장되지 않았습니다. 위 FPS/Stackifier 수치는 해당 단일 세션의 직접 관찰값이지만 재산출 가능한 raw console artifact는 아닙니다.
- 다음 `RuntimeCallAware3` 검증에서는 화면, Present timestamp, compile-attempt/Stackifier telemetry를 파일에도 저장해야 합니다.

## RuntimeCallAware3 재검증

- **VERIFIED (browser):** 정확히 한 탭으로 자동 PatHouse에 진입했고 카펫·벽·가구·캐릭터·한글이 기준 화면과 일치했습니다. fatal/OOM/console error는 없었습니다.
- **VERIFIED (browser):** 마지막 8개 120-Present timestamp `12:00:37.570Z .. 12:00:50.831Z`는 840 frames / 13.261 s = **63.3436 FPS**입니다.
- **VERIFIED (telemetry):** `pid=71 tid=72`는 `executed_blocks=131072`, `executed_ops=4581188`까지 증가했습니다. generated Wasm이 실제 Acknex 주 스레드 실행을 담당했습니다.
- **REJECTED AS LONG-RUN BUILD:** compile attempt/failure가 여전히 `65536`까지 증가했고, 누적 `compiled=1352`, `deopts=1349`였습니다. 1,048,576회에서 크게 줄었지만 cache admission만으로는 retry storm을 제거하지 못했습니다.
- **VERIFIED (root cause):** backend `compile()`의 `nullptr`가 immutable opcode/resource barrier와 아직 덜 쌓인 branch profile을 구분하지 않았습니다. 또한 transactional first-execute Fallback을 같은 identity에서 다시 compile했습니다.
- **IMPLEMENTED / TESTED:** generator가 마지막 실패의 transient 여부를 보고합니다. profile/indirect-target/race만 8192-hit부터 지수 backoff로 재시도하고 immutable failure는 즉시 identity-bound negative cache로 전환합니다. compiled block의 transactional Fallback도 동일 identity에서 재컴파일하지 않습니다. 깨끗한 전체 Emscripten test ABI에서 tests 7/15가 다시 0 failures입니다.

## 다음 gate

1. fresh `RuntimeCallAware4` 단일 탭으로 자동 PatHouse 진입
2. 동일 기준 화면 유지 확인
3. stable 840-frame FPS와 final compile attempts 저장
4. 50 FPS 이상이며 compile-attempt 폭증이 재현되지 않을 때만 장기 실행 후보로 승인
5. 이후 사운드 전체 경로와 장시간/OOM 안정성 검증

## RuntimeCallAware4 최종 결과

- **VERIFIED (clean build/tests):** 가상 backend ABI 변경 뒤 테스트 빌드를 완전히 새로 만들었으며 `node boxedwine.js 7 1 1`, `node boxedwine.js 15 1 1`이 각각 0 failures입니다.
- **VERIFIED (artifact):** 배포 `boxedwine.callaware4.js` SHA-256은 `2E70E65370EFCED74BC0F32C900746FF052AEE30A4ECAE0DF8EC6168B1773834`, `.wasm`은 `80947097869F059EF44B46BADBEF87A92310AAEB2CC65BDE9656D515EB381F50`입니다.
- **VERIFIED (single visible browser session):** 탭 0개에서 정확히 한 탭만 열고 사용자에게 브라우저를 표시했습니다. 도움말 중간 화면을 건드리지 않고 자동 PatHouse 진입했으며 카펫·벽·가구·캐릭터·한글은 기준 화면과 일치했습니다.
- **VERIFIED (FPS):** 안정 마지막 8개 120-Present timestamp는 `12:22:27.118, 28.418, 29.667, 30.954, 32.169, 33.392, 34.692, 35.946Z`입니다. 840 frames / 8.828 s = **95.1518 FPS**입니다.
- **VERIFIED (generated Wasm):** 초기 주 스레드 로그는 `pid=71 tid=72 compiled=8 executed_blocks=2447 executed_ops=83198 deopts=6 evictions=203 cache=2048`이었습니다. 실제 generated-Wasm 실행이 유지됐습니다.
- **VERIFIED (retry bounded in this session):** 주 스레드는 `12:19:31.435Z failures=2048` 이후 세션 종료 `12:22:35.946Z`까지 power-of-two `4096` 로그가 나오지 않았습니다. CallAware3의 같은 세션 내 65536, CallAware2의 1048576 증가가 재현되지 않았습니다.
- **VERIFIED:** browser error-level 로그는 0개였고 측정 직후 탭을 닫았습니다.
- **ACCEPTED for the 1024x768 PatHouse 50-FPS visual gate.** 아직 사운드 전체 경로, 장시간 OOM, 카메라 pointer-lock, 다중 브라우저 멀티플레이는 별도 gate입니다.
