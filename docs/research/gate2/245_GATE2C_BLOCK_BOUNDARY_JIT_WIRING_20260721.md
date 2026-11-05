# 245 Gate 2c 블록 경계 JIT 연결과 27 FPS 회복 (2026-07-21)

## 범위

문서 242~244의 Runtime Stackifier를 실제 PatHouse 게임 루프에 연결하되, 짧은 함수 AOT나 추가 정밀 프로파일러로 돌아가지 않고 JIT 디스패치 자체의 실행 경계를 바로잡았습니다. 모든 브라우저 검증은 동시에 한 탭만 사용했고 각 측정 직후 탭을 닫았습니다.

## Superblock1 실측

- **VERIFIED:** 첫 세션은 28.8초에 종료되어 자동 선택 조건인 heartbeat 8회에 도달하지 못했습니다. 서버 로그는 `pre_select=0 -> 1`만 남겼고 `AUTO-SELECT EXISTING` 및 PatHouse 부트스트랩은 없었습니다. 이 검은 화면 표본은 무효입니다.
- **VERIFIED:** 다시 연 단일 세션은 약 110초 뒤 PatHouse에 진입했고, 카펫·벽·가구·캐릭터·한글이 기준 화면과 일치했습니다.
- **VERIFIED:** 유효 PatHouse 구간에서도 `WASM_RUNTIME_STACKIFIER` 설치/실행 로그는 0건이었습니다. 관측된 compile 후보는 4~8 ops였고 모두 32-op gate에서 실패했습니다.
- **VERIFIED:** 120-Present 간격은 9.112/8.211/7.571/7.794초였고, 480프레임/32.688초 = **14.68 FPS**였습니다. 기존 DirectDrawUP 기준 22.15 FPS보다 33.7% 낮습니다.
- **VERIFIED:** 회귀 상태에서는 후보 `START_OP`마다 JIT admission/cache 조회가 실행됐습니다. 즉 생성된 Wasm의 성능이 아니라 설치 0 상태의 정책 오버헤드였습니다.

## 구현: 명령 경계에서 블록 경계로

- **VERIFIED:** `normalCPU.cpp`의 Stackifier 검사를 `START_OP`에서 제거하고 `NormalCPU::run()`의 decoded-block 진입 경계로 옮겼습니다.
- **VERIFIED:** Normal direct dispatch는 한 번의 `run()`에서 branch/call/return까지 블록을 실행하므로, 이 위치는 CALL 의미나 패킷/D3D 경로를 바꾸지 않으면서 한 블록당 한 번만 JIT 정책을 실행합니다.
- **VERIFIED:** mid-block branch target도 `getNextOp()`가 정확한 `DecodedOp`를 `nextOp`로 돌려주므로 다음 `run()`에서 동일 경계를 탑니다.
- **VERIFIED:** 분기 방향 저장은 worker-local 중첩 `unordered_map`에서 고정 크기 4-way set-associative 4096-slot 테이블로 바꿨습니다. 키는 CPU 포인터, branch EIP, decoded identity이며 set overflow는 가장 적게 샘플된 항목만 교체합니다.
- **VERIFIED:** `WASM_RUNTIME_BRANCH_PROFILE` power-of-two 로그는 `BOXEDWINE_WASM_RUNTIME_BRANCH_PROFILE_ONLY` 빌드에서만 방출합니다. 프로덕션 JIT은 내부 방향 카운터를 유지하되 로그를 내지 않습니다.
- **VERIFIED:** 첫 direct-map 시제품은 충돌 때 같은 분기가 256/512/1024를 반복 방출해 로그가 포화됐으므로 FPS 판정을 폐기하고 위 4-way/production-log-off 설계로 교체했습니다.

## 테스트

- **VERIFIED:** 증분 Emscripten 테스트 빌드 후 `node boxedwine.js 7 1 1`은 `Test WASM JIT Stackified Register Block ... OK`, 0 failures였습니다.
- **VERIFIED:** `node boxedwine.js 15 1 1`은 `Test WASM Write32 Tier ... OK`, 0 failures였습니다.
- **VERIFIED:** 배포 산출물 `boxedwine.blockboundary2.js/.wasm` SHA-256은 각각 `9CFD77613B22A7023F0F12CEA952576E5ED6CAD2BEDAFB44D7DA835E74CC000B`, `D8C52F341ABFE9EB2B55A6C8D4A4CF3674AA284CD9B6FCB3A7BC7BA9A50D7748`입니다.

## BlockBoundary2 PatHouse 결과

- **VERIFIED:** 단일 탭 자동 진입 후 기준 PatHouse 화면과 일치했습니다. 카펫 반복, 벽/가구 변형, 캐릭터/한글 회귀가 없었습니다. 잔존 `캐릭터를 생성해주세요` 문구는 사용자 지시에 따라 판정에서 제외했습니다.
- **VERIFIED:** `WASM_RUNTIME_STACKIFIER` 로그는 여전히 0건입니다. compile attempts는 6-op 후보 등에서 실패했으므로 이 결과는 생성 Wasm 실행 가속이 아닙니다.
- **VERIFIED:** 초기 안정 구간은 840프레임/30.779초 = **27.29 FPS**였습니다.
- **VERIFIED:** 후속 구간은 840프레임/31.067초 = **27.04 FPS**였습니다.
- **VERIFIED:** 후속 120-Present 간격은 4.682/4.315/4.547/4.343/4.532/4.371/4.277초입니다.
- **VERIFIED:** 보수적으로 27.04 FPS를 사용하면 DirectDrawUP 22.15 FPS 대비 **+22.1%**, 잘못 연결된 Superblock1 14.68 FPS 대비 **+84.2%**입니다.

## 판정

- **VERIFIED:** 범용 JIT의 올바른 실제 연결점은 per-instruction `START_OP`가 아니라 `NormalCPU::run()` 블록 경계입니다.
- **VERIFIED:** 이번 +22.1%는 JIT-compiled guest code의 이득이 아니라, 설치되지 않는 JIT 정책을 명령마다 호출하던 오버헤드를 제거한 결과입니다. 이를 생성 Wasm 가속으로 표현하면 안 됩니다.
- **VERIFIED:** 그래도 이전 정상 빌드보다 빨라졌으므로 이 경계 변경은 유지할 가치가 있으며, 다음 call-aware tier의 기반으로 채택합니다.

## 다음 gate: CALL-aware 장기 실행 단위

- **VERIFIED:** `acknex+0x4966B`의 taken/fall 합은 정확히 33,554,432이고 taken 99.9491%입니다. 평균 outer-loop 반복은 약 1,964.085회입니다.
- **VERIFIED:** controller는 반복당 9 guest instructions이며 현재 lowering 가능한 scalar는 7개입니다. 단순 손익 gate는 4회 반복 36 guest instructions 또는 5회 반복 35 scalar ops입니다.
- **VERIFIED:** `CALL 0x46760`에서 매번 interpreter로 나가면 2-op/5-op 단편 문제가 그대로 남습니다. 8-op resumable fragment는 의미적으로 안전해도 이미 실패한 짧은 국소 치환 패턴이므로 다음 브라우저 후보로 채택하지 않습니다.
- **INFERRED:** 실제 큰 레버는 outer loop, direct callee `+0x46760`, 그리고 그 안의 안정된 두 indirect transform thunk target을 identity-guard하여 한 generated invocation/chunk 안에서 처리하는 범용 call-aware loop tier입니다.
- **VERIFIED:** 전체 outer-loop controller를 한 경계로 상각하면 tiny 4.519-op/call 방식 대비 module-boundary 수를 이론상 약 99.967% 줄일 수 있습니다. 다만 알려진 transform family의 기존 sampled guest-time 합은 5.844%이므로 wall-FPS 효과는 구현 후 직접 측정해야 합니다.

## 제한

- **NOT VERIFIED:** 27.04 FPS가 장시간 전체 세션에서도 유지되는지는 아직 840프레임 두 구간보다 길게 측정하지 않았습니다.
- **NOT VERIFIED:** call-aware generated callee의 opcode/memory/exception 전체 범위와 실제 FPS 효과는 다음 구현 gate입니다.
- **NOT VERIFIED:** 50 FPS 목표는 아직 달성되지 않았습니다.
