# 244 Gate 2c reachable trace 장벽과 최소 33-op 확장 (2026-07-21)

## 범위

243의 JZ/JNZ superblock은 정확성 테스트를 통과했지만 원본 Azrok/acknex의 재귀 도달 코드에서 32-op 실행 gate를 통과하는 후보가 0개였습니다. 이 문서는 실제 도달 가능한 명령만 대상으로 trace 종료 장벽을 다시 측정하고, 최소 opcode 확장과 가장 뜨거운 실게임 분기의 관계를 기록합니다.

## 정적 측정

- **VERIFIED:** 현재 subset+JZ/JNZ의 최대는 `acknex.dll` 23 ops, `Azrok.exe` 17 ops이며 32+ 후보는 0개입니다.
- **VERIFIED:** `acknex.dll`에 `OTHER_JCC`만 더하면 최대 31, shift만으로는 32에 도달하지 않습니다.
- **VERIFIED:** `SHIFT + OTHER_JCC` 조합은 `acknex.dll RVA 0x0001E054`에 33-op 후보 1개를 만듭니다. 필요한 concrete form은 `JLE rel8/rel32`, `JGE rel8/rel32`, `SHL r32,imm8`뿐입니다.
- **VERIFIED:** 해당 경로에는 `+0x1E05F JLE`, `+0x1E078 JGE`, `+0x1E088/+0x1E08C JLE`, `+0x1E094/+0x1E097/+0x1E09A/+0x1E09F SHL reg,0x0A`가 있습니다.
- **VERIFIED:** Azrok.exe의 상위 연속 stack-local store 경로는 opcode보다 16-write 제한에 먼저 막힙니다. 장기적으로 write-tier 확대/store forwarding도 필요합니다.

## 동적 branch profile 주소 대응

- **VERIFIED:** `0x7F3A966B`는 브라우저 acknex base `0x7F360000` 기준 `acknex.dll+0x4966B`입니다. 프로파일 값은 taken 33,537,348 / fall 17,084(99.949%)였습니다.
- **VERIFIED:** 이 주소는 outer object loop의 `JL +0x49650` latch입니다. 본문은 `+0x49654 CALL` 앞 2 scalar op, call 뒤 `MOV/ADD/ADD/ADD/CMP` 5 scalar op로 갈라집니다. 현재 acyclic JZ/JNZ/JLE/JGE superblock은 이 가장 뜨거운 루프를 아직 연결하지 못합니다.
- **VERIFIED:** `0x7F3963D6=acknex+0x363D6`, `0x00660E5B=Azrok+0x260E5B`, `0x006630E1=Azrok+0x2630E1`입니다.
- **VERIFIED:** `0x7BDD2F73/0x7BDD2D6D`는 프로젝트 proxy `d3d9.dll`, `0x1072D03C`는 기존 동일 로드맵 기준 Wine ntdll 영역입니다.
- **VERIFIED (coarse):** `0x1065BCF3` 계열은 Azrok/acknex/proxy 범위 밖의 Wine 런타임 영역입니다. branchprofile 세션에 exact Unix DSO base/name을 남기지 않아 세부 모듈명은 확정하지 않습니다.

## 구현

- **VERIFIED (dynamic differential):** Runtime emitter/Stackifier에 `SHL r32,imm8`, `JumpLE`, `JumpNL`(x86 JGE)를 추가했고 Emscripten `Test WASM JIT Stackified Register Block`가 단독 실행에서 0 failures로 통과했습니다.
- **VERIFIED:** SHL은 WebAssembly `i32.shl` 결과만 쓰는 것이 아니라 BoxedWine와 동일하게 `dst=원값`, `src=masked count`, `result`, `FLAGS_SHL32` lazy tuple을 남깁니다.
- **VERIFIED:** JLE/JGE는 trace 내부의 마지막 `ADD32`, `SUB32/CMP32`, `XOR32/TEST32` producer가 지배할 때만 연결합니다. ADD/SUB/logic별 OF 계산과 `ZF || SF != OF`, `SF == OF`를 generated module 안에서 평가합니다. producer가 없거나 SHL 등 아직 지원하지 않는 OF 유형이면 연결하지 않습니다.
- **VERIFIED:** 선호 방향이 fallthrough이면 조건을 반전하며 cold exit는 이미 실행된 prefix의 EIP/op/write count만 publish합니다.
- **VERIFIED:** SHL `0x81234567 << 4 = 0x12345670`에서 raw lazy dst/src/result/`FLAGS_SHL32`와 이후 인터프리터의 `CF/PF/AF/ZF/SF/OF` 읽기가 oracle과 일치했습니다.
- **VERIFIED:** JLE는 SUB taken-hot과 logic fall-hot, JGE는 CMP taken-hot과 logic fall-hot을 각각 hot/cold 양쪽으로 실행했습니다. hot은 9 ops, cold prefix는 5 ops이며 전체 GPR/lazy tuple/materialized flags/EIP가 interpreter oracle과 일치했습니다.

## 다음 단계

1. 실제 33-op 후보가 모든 분기에서 255 samples/90% 편향 gate를 만족하는지 단일 PatHouse 세션에서 compile/executed-op telemetry로 측정합니다.
2. 33-op 후보의 실게임 비중이 작으면 다음 큰 레버는 `acknex+0x4966B`의 `CALL+JL` outer loop를 generated module 내부 call/loop로 연결하는 call-aware tier입니다.

## 한계

- **NOT VERIFIED:** 33-op 후보의 실제 PatHouse 실행 빈도와 분기 편향은 아직 브라우저에서 측정하지 않았습니다.
- **NOT VERIFIED:** 가장 뜨거운 outer loop의 call target을 범용 JIT 내부 함수로 컴파일하는 설계, x87 포함 callee 범위, 성능 이득은 다음 gate입니다.
