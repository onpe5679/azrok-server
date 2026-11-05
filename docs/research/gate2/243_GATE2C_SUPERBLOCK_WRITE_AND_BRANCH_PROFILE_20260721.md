# 243 Gate 2c superblock write tier와 실게임 branch profile (2026-07-21)

## 범위

tiny-block Runtime Stackifier가 PatHouse에서 실제 실행됐지만 4.519 ops/call에 그쳐 15.886 FPS로 회귀한 뒤, 호출 경계를 줄이기 위한 multi-basic-block superblock의 선행 조건을 측정했습니다. 이 문서는 direct JMP, transactional dword write/PUSH/POP, 그리고 Jcc hot-edge 선택용 브라우저 실게임 분기 계측 결과를 기록합니다.

## 결론

- **VERIFIED (dynamic):** `branchprofile1` 프로파일 전용 빌드로 원본 Azrok가 자동 선택 경로를 통해 PatHouse에 진입했습니다. 카펫, 벽, 식탁/의자, 캐릭터, 한글 UI가 기준 화면과 같은 정상 형상으로 렌더됐습니다.
- **VERIFIED (isolation):** 프로파일 전용 빌드는 JIT hot threshold를 `0xffffffff`로 두었고, 세션 콘솔의 `WASM_RUNTIME_STACKIFIER` 행은 0개였습니다. 따라서 아래 분기 수치는 generated-Wasm 실행의 영향을 받지 않습니다.
- **VERIFIED (dynamic):** 주 게임 프로세스 `pid=71, tid=72`에서 매우 강하게 편향된 분기가 반복됐습니다. 대표값은 `eip=0x7f3a966b` taken 33,537,348 / fall 17,084, 즉 taken 99.949%입니다. 그 밖에 2,097,152회 중 fall 2,097,150회인 `0x1065bcf3`, 1,048,576회 전부 fall인 `0x7bdd2f73`/`0x7bdd2d6d`, 1,048,576회 중 taken 1,048,441회인 `0x7f3963d6`가 확인됐습니다.
- **VERIFIED (performance direction):** tiny-JIT 회귀는 17.802 ms/frame, 8,738.1 generated-block calls/frame였습니다. 컴파일 비용을 0으로 두는 상한 계산에서 호출당 순회귀는 최대 2.037 us입니다. 전체 프레임이 eligible interpreter 비용이라는 불가능한 최선에서도 break-even은 7 ops 이상이며, 실제 안전 실행 gate는 평균 32 ops/call 이상으로 유지합니다.
- **VERIFIED (static, corrected):** PE entry/export에서 direct call/jump/Jcc로 재귀 도달 가능한 실제 명령만 다시 스캔하면, 현재 구현 subset+JZ/JNZ의 최대는 `acknex.dll` 23 ops, `Azrok.exe` 17 ops이며 32 ops 이상 후보는 둘 다 0개입니다. 이전 선형 스윕의 32+ 후보 4개/최대 55는 `.text` 안의 데이터를 명령으로 오인한 거짓 양성이므로 폐기합니다.

## 실측 분기 표본

아래 값은 각 CPU별 최신 power-of-two 방출값입니다. 동일 EIP라도 worker가 다르면 별도 행이며, 주 게임 스레드의 큰 표본을 우선합니다.

| pid/tid | EIP | taken | fall | taken 비율 |
|---|---:|---:|---:|---:|
| 71/72 | `0x7f3a966b` | 33,537,348 | 17,084 | 99.949% |
| 71/72 | `0x10636016` | 1,573,129 | 524,023 | 75.013% |
| 71/72 | `0x1065bcf3` | 2 | 2,097,150 | 0.000095% |
| 71/72 | `0x7bdd2f73` | 0 | 1,048,576 | 0% |
| 71/72 | `0x7bdd2d6d` | 0 | 1,048,576 | 0% |
| 71/72 | `0x7f3963d6` | 1,048,441 | 135 | 99.987% |
| 71/72 | `0x10635fa8` | 0 | 524,288 | 0% |
| 71/72 | `0x00660e5b` | 524,288 | 0 | 100% |
| 71/72 | `0x006630e1` | 524,288 | 0 | 100% |
| 71/72 | `0x1072d03c` | 88,726 | 173,418 | 33.846% |

`0x10636016`처럼 75%인 분기는 계측 helper의 기존 70% preference gate는 통과하지만 초기 superblock 연결 대상으로는 사용하지 않습니다. 첫 구현은 표본 256 이상 및 dominant 90% 이상만 연결합니다.

## 계측 사각지대

- **VERIFIED (static):** 이 프로파일은 모든 Jcc를 계수하지 않습니다. 후보 straight-line 구간에 지원 명령이 최소 4개 있어야 terminal Jcc에 profile flag가 붙습니다.
- **VERIFIED (static):** 총 실행 256회 이상이며 합계가 2의 거듭제곱일 때만 로그가 방출됩니다. 종료 시 최종 table dump는 없습니다.
- **INFERRED:** 로그에 없는 Jcc는 미실행 또는 저가치라고 판정할 수 없습니다. 기존 정적 최고 후보 `0x10046780`의 entry `JL`, 이어지는 `TEST; JZ`, `CMP; JNZ`는 0~1-op prefix라 현재 계측에서 빠질 수 있습니다.
- **VERIFIED (static):** 카운터 키는 CPU별 physical branch EIP이며 decoded identity가 바뀌면 reset됩니다. 여러 worker의 같은 EIP를 단순한 단일 시간축으로 합산하지 않습니다.

## 정적 후보 정정

- **VERIFIED:** `Azrok.exe` SHA-256은 `39680da744df27cf13eae03f675d91c301b3ca9332f6979ca4447fba9908caba`, `acknex.dll`은 `876f6870f6858c3829c0830415bf30cf7dd375590810eef231a7e6b1a68eedc6`입니다.
- **VERIFIED:** 현재 제약(최대 8 segment/256 ops, cycle 금지, read-after-write/address-register guard)과 JZ/JNZ 두 방향 중 긴 쪽을 택한 upper bound에서도 `acknex.dll` 최대 23, `Azrok.exe` 최대 17입니다. Jcc 사이 0-scalar를 허용해도 값은 변하지 않았습니다.
- **VERIFIED:** `minimumCompiledOps=32`를 유지한 현재 production 구성은 원본 두 바이너리에서 설치 가능한 후보가 0개입니다. 그러므로 이 상태의 브라우저 FPS 실행은 JIT 효과를 측정하지 못하며 생략합니다.
- **NOT VERIFIED:** export/direct-flow에서 발견되지 않고 간접 호출로만 도달하는 함수의 완전성은 동적 decoded-address 수집 또는 Ghidra 함수 경계 전수 대조가 필요합니다.

## write/PUSH/POP 구현

- **VERIFIED (native tests):** `wasmMemoryCommitWrite32Batch`는 모든 plan을 먼저 재검증한 뒤 한 lock 구간에서 guest 순서로 commit합니다. 두 번째 plan이 stale이면 첫 번째 sentinel도 바뀌지 않으며, 같은 주소 두 번 쓰기는 마지막 값이 남습니다.
- **VERIFIED (emitter probe):** generated module에서 POP snapshot, MOV store 두 개, PUSH register/immediate가 실행됐고 ESP와 write 값이 interpreter 의미와 일치했습니다. PUSH ESP는 감소 전 값을 저장하고, POP ESP는 popped value가 최종 ESP가 됩니다.
- **VERIFIED (admission):** 16-bit stack mode, write 뒤 read forwarding이 필요한 trace, 변경된 address register를 후속 memory EA가 사용하는 trace, POP ESP 뒤 후속 stack op는 현재 tier에서 거부합니다.
- **VERIFIED (Emscripten differential):** `Test WASM JIT Stackified Register Block`는 PUSH ESP, POP ESP, exact/partial alias, valid+invalid multiwrite, `0xFFC/0xFFD` page boundary, COW, 16-bit stack gate와 JZ hot/cold side exit를 포함해 통과했습니다. `Test WASM Write32 Tier`도 별도 단독 실행에서 통과했습니다.
- **VERIFIED (generated module probe):** 고정 1GiB shared-memory Emscripten probe에서 `ContinueIfZero`와 `ContinueIfNotZero`의 hot/cold 네 경우가 모두 정확한 EIP와 executed-op count를 반환했습니다.
- **NOT VERIFIED:** batch validation/commit은 실패 시 무부분커밋을 보장하지만 다른 guest worker 전체에 대한 다중 위치 원자성을 뜻하지 않습니다. code post-guard와 batch commit 사이 TOCTOU, observer의 명령별 정확한 EIP attribution은 남은 제한입니다.

## Jcc superblock 구현 계약

1. 첫 조건은 `JZ/JNZ`이며 lazy producer를 `ADD32/SUB32/XOR32/CMP32/TEST32` exact type으로 guard합니다. ZF는 `result == 0`으로 계산하고 lazy tuple을 materialize하거나 변경하지 않습니다.
2. 내부 producer가 Jcc를 지배하는 경우와 trace 진입 전 외부 producer가 남은 경우를 모두 지원해야 합니다. 후자는 위 5종 exact lazy type mismatch 시 guest state 변경 전 fallback합니다.
3. cold side exit는 prefix가 이미 실행됐으므로 fallback이 아니라 completed exit입니다. generated state가 동적 `nextEip`, `executedOpCount`, `executedWriteCount`를 반환해야 하며 C++는 실제 실행된 prefix write만 commit해야 합니다.
4. 첫 브라우저 후보는 최대 256 ops/8 segments, compile 시 완료 표본 255 이상/dominant 90% 이상, backward cycle 금지, 최종 정적 길이 32 ops 이상으로 제한합니다. `START_OP` 컴파일은 terminal Jcc의 256번째 실행 직전이므로 이때 정확히 255개가 쌓이는 경계 조건을 반영합니다. 프로파일 로그 방출 기준은 기존대로 256 이상입니다.
5. 네이티브 차등 테스트에서 hot/cold 방향, lazy tuple 불변, cold exit EIP, cold 뒤 미실행 write 무커밋, wraparound/SMC guard를 통과하기 전에는 브라우저 빌드를 만들지 않습니다.

## 다음 게이트

- JZ/JNZ hot-edge와 동적 side-exit 결과 ABI는 구현 및 Emscripten 차등 테스트를 통과했습니다.
- 상위 23-op trace를 끊는 unsupported opcode를 집계하고, 최소 opcode 확장으로 재귀 도달 코드에서 실제 32-op 이상 후보를 먼저 증명합니다.
- 그 뒤에만 단일 PatHouse 브라우저 세션을 열어 정상 화면, fatal/OOM 부재, 평균 ops/call, FPS를 함께 측정하고 즉시 닫습니다.
