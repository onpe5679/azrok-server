# 242 — Gate 2c runtime Stackifier game wiring (2026-07-21)

## Scope

기존 테스트 전용 WebAssembly emitter/Stackifier 골격을 실제 BoxedWine `NormalCPU` 실행 경로에 연결하고, 원본 Azrok PatHouse 장면에서 컴파일·실행·정확성·FPS를 직접 판정합니다.

## 결론

- **VERIFIED (dynamic):** RuntimeJit9/10에서 생성 Wasm이 실제 게임 실행 worker에 설치되고 PatHouse 게스트 명령을 실행했습니다. 이전의 “네이티브 테스트 전용 골격” 상태는 해소됐습니다.
- **VERIFIED (visual):** RuntimeJit10 한 세션에서 정상 카펫 밉맵, 벽, 식탁·의자, 캐릭터, 한글 UI가 기준 화면과 일치했고 fatal/runtime/OOM은 없었습니다.
- **VERIFIED (performance):** 같은 세션의 30.215초 동안 `present_delta=120` 창이 4개 증가해 480 frames, 즉 **15.886 FPS**였습니다.
- **REJECTED:** 기존 DirectDrawUP 기준 22.15 FPS보다 **28.28% 느립니다**. 현재 4~6-op straight-line JIT는 성능 경로로 채택하지 않습니다.
- **VERIFIED (cause at boundary):** 대표 게임 thread telemetry는 `compiled=496`, `executed_blocks=4,194,304`, `executed_ops=18,951,456`, `deopts=2`였습니다. 실행된 JIT block당 평균은 **4.519 ops**입니다. JIT 미실행이 아니라 수백만 번의 너무 짧은 generated-Wasm 호출/모듈 경계 비용이 유효 작업을 압도한 결과입니다.

## 연결 과정과 직접 증거

- **VERIFIED (static):** 초기 `WasmJitEngine::tryRun`의 게임 호출 지점은 0개였고 테스트에서만 사용됐습니다. 이전 emitter/stackifier/memory-tier 테스트 성공은 실게임 가속 증거가 아니었습니다.
- **VERIFIED (dynamic):** entry-only RuntimeJit1과 read-snapshot RuntimeJit2는 PatHouse 실행 중 `WASM_RUNTIME_STACKIFIER` telemetry가 0행이었습니다.
- **VERIFIED (static):** RuntimeJit3는 decode 시 interior opcode에서 4개 이상의 지원 연속 구간을 표시하고 `START_OP`에서 후보만 JIT에 전달했습니다.
- **VERIFIED (dynamic):** RuntimeJit3/4는 수백 Present에도 compile telemetry가 0이었습니다. 이후 candidate mark/hit 계측으로 후보 자체는 수십만 번 도달함을 확인했습니다.
- **VERIFIED (root cause):** `wasmJitForCpu` registry가 `thread_local`인데 engine을 CPU 생성 worker에서 미리 만들고 실제 opcode는 다른 Web Worker에서 실행했습니다. 실행 worker의 lookup은 항상 null이었습니다.
- **VERIFIED (fix):** constructor precreate를 제거하고 `START_OP`에 도달한 현재 실행 worker에서 engine을 lazy-create했습니다. RuntimeJit9에서 즉시 `compiled > 0`, `executed_blocks`/`executed_ops`의 지속 증가가 확인됐습니다.
- **VERIFIED (release measurement):** RuntimeJit10은 warmup 256, candidate trace 비활성, compile telemetry power-of-two 제한 상태로 측정했습니다. 배포 SHA-256은 JS `1B62840D65815AAB72115808147980EB2183292016BCDF858FF811413FCA556E`, WASM `F7D95E315D3D6CCE278D454E53BF5429B55D55F22F4C70464DC71115C463287B`입니다.

## Transaction boundary

- **VERIFIED:** 현재 memory tier는 메모리를 쓰지 않습니다. RAM 32-bit 값을 shadow state로 읽고 generated module은 shadow CPU state만 계산합니다.
- 실행 뒤 값·decoded identity·guest bytes를 다시 검증한 다음 CPU GPR/lazy flags/EIP를 한 번에 commit합니다.
- 따라서 정확한 표현은 “read snapshot 재검증 후 CPU-state commit”이며 “transactional memory commit”은 아닙니다.

## 다음 구현 게이트

현재 tiny-block 경로를 미세 최적화하거나 함수별 AOT 후보를 더 찾지 않습니다. 다음 경로는 호출 경계를 상각하는 **multi-basic-block superblock**입니다.

1. direct unconditional JMP를 따라 여러 decoded block을 하나의 module invocation으로 연결합니다.
2. direct Jcc는 BoxedWine의 lazy-flag 의미를 그대로 사용해 hot successor를 내부화하고 반대편은 정확한 EIP side exit로 둡니다.
3. compile 폭발 방지를 위해 초기 상한을 256 ops / 8 decoded blocks / 제한된 backward edge로 둡니다.
4. 브라우저 실행 전 native tests에서 분기 방향, lazy flags 비변형, side-exit EIP, wraparound, self-modifying-code guard를 검증합니다.
5. 평균 generated invocation 길이가 최소 32 ops 이상임을 telemetry로 확인한 뒤에만 한 개의 PatHouse 브라우저 세션으로 시각·FPS를 재측정합니다.

## 남은 위험

- **VERIFIED (static lifecycle risk):** worker-local TLS registry의 정리는 CPU 파괴 worker에만 의존합니다. CPU가 worker를 이동하면 이전 worker entry가 남을 수 있습니다. guest 오실행은 identity/code guard가 막지만 누수와 pointer-reuse hotness 오염은 남습니다. worker teardown의 `wasmJitForgetAllForWorker()`와 CPU monotonic generation key가 필요합니다.
- write-memory tier, x87/SSE tier, 50 FPS 및 원본 사운드 완전성은 아직 검증되지 않았습니다.
