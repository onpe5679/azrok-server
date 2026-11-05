# 246 Gate 2c call-aware 스택 트랜잭션 기반 (2026-07-21)

## 결론

- **VERIFIED:** Runtime Stackifier가 32비트 near `CALL rel32`의 callee와 plain `RET` 뒤 caller continuation을 하나의 생성 WASM 트랜잭션으로 stitch할 수 있습니다.
- **VERIFIED:** CALL 반환 주소는 x86과 동일하게 CS-relative EIP를 `[SS:ESP-4]`에 기록하며, RET은 그 exact buffered dword를 검사하고 ESP를 복구합니다. CALL/RET 자체는 lazy flags를 변경하지 않습니다.
- **VERIFIED:** exact stack-slot PUSH→POP store-to-load forwarding이 추가됐습니다. unknown/partial/non-stack alias는 계속 보수적으로 거부합니다.
- **VERIFIED:** call-aware backend만 짧은 최초 linear prefix를 넘어 compile 요청을 받을 수 있습니다. 최종 `minimumCompiledOps=32` gate는 그대로이며, 다른 backend의 기존 admission 의미는 바뀌지 않습니다.
- **NOT VERIFIED:** 실제 `acknex+0x49650` 장루프는 아직 생성 WASM으로 설치되지 않습니다. callee의 `LEA`, 변경된 GPR 기반 EA, `CMP [mem],imm`, `JL`, 간접 thunk guard와 동적 출력 쓰기가 남았습니다. 따라서 이번 단계만으로 브라우저 FPS를 다시 재지 않았습니다.

## 정적 분석: transform dispatch의 정확한 대상

대상 `acknex.dll` SHA-256은 `876F6870F6858C3829C0830415BF30CF7DD375590810EEF231A7E6B1A68EEDC6`입니다.

- **VERIFIED:** `0x10252140`과 `0x10252150`은 `.data`의 74-entry 함수 포인터 테이블 index 6/10이며 HIGHLOW relocation 대상입니다.
- **VERIFIED:** raw 초기값은 각각 lazy resolver wrapper `0x10084464`, `0x10084351`입니다.
- **VERIFIED:** direct thunks는 `0x10084477 -> jmp [0x10252140]`, `0x10084364 -> jmp [0x10252150]`입니다.
- **VERIFIED:** `0x100966B9(1)` 초기화는 source table을 복사한 뒤 baseline patch를 적용합니다. 일반 lazy-wrapper 경로의 안정 대상은 `0x100E16D8`(slot 140)과 `0x100875F0`(slot 150)입니다.
- **VERIFIED:** CPU patcher `0x100E0F41/0x100E10B4`는 두 슬롯을 각각 `0x101041D7`, `0x101042A3`로 바꿀 수 있습니다.

## 기존 동적 증거와 대조

- **VERIFIED:** 기존 clean `hotaot5` 로그에서 Acknex base `0x7F360000`과 relocated target `0x7F4641D7`, `0x7F4642A3`의 실제 실행이 확인됐습니다.
- **VERIFIED:** 전자는 translation 없는 3x3 normal transform, 후자는 translation과 W reciprocal을 포함한 coordinate transform입니다. 의미상 각각 `D3DXVec3TransformNormal`, `D3DXVec3TransformCoord` 계열입니다.
- **NOT VERIFIED:** 슬롯 메모리 `0x7F5B2140/150` 자체를 같은 순간 직접 dump한 기존 기록은 없습니다. 정적 patch write와 두 target의 동적 실행은 일치하지만, 향후 indirect guard 계측 때 슬롯 값도 직접 남겨야 합니다.

## 구현

수정 파일:

- `wasmRuntimeEmitter.h/.cpp`: `memorySourceFromWrite`, `ReturnExpected32` 추가
- `wasmJitRuntimeStackified.cpp`: exact stack forwarding, depth 4 bounded direct CALL/RET stitching, CS-relative return guard
- `wasmJitMvp.h/.cpp`: control-flow-aware backend에만 short-prefix compile 요청 허용
- `normalCPU.cpp`: decoder admission에 CPU와 정확한 candidate EIP 전달
- `testWasmJitStackified.cpp`: PUSH→POP differential 및 CALL→callee→RET→continuation 생성 WASM 검증

## 검증

- **VERIFIED:** 깨끗한 Emscripten test ABI 재빌드 후 `node boxedwine.js 7 1 1` — `Test WASM JIT Stackified Register Block ... OK`, 0 failures.
- **VERIFIED:** `node boxedwine.js 15 1 1` — `Test WASM Write32 Tier ... OK`, 0 failures.
- **VERIFIED:** direct CALL/RET fixture는 5 guest ops로 한 module에 compile되고 EAX/EBX, ESP, next EIP, 실제 stack return dword가 interpreter 의미와 일치합니다.
- **VERIFIED:** 멀티스레드 1 GiB 프로덕션 구성 `RuntimeCallAware1`이 링크됐습니다. JS SHA-256 `78E038AF302CE815217F0DBD37361D6D5B11F899504C124A59480606DC585409`, WASM SHA-256 `1C3A41E87CC4BA6440EB3456A8588D1F30A308FF6627607AC1EF5E3354047100`입니다.

## 다음 gate

1. prior transactional stack write와 non-stack read가 실제 주소에서 겹치지 않을 때 허용하는 runtime alias guard
2. MOV/ADD/LEA를 통한 GPR-derived effective-address 전파
3. `CMP [mem],imm`, `JL`의 exact lazy-flag/side-exit 구현
4. `jmp dword ptr [abs]` 슬롯의 entry/commit 이중 target guard
5. 위 기능으로 `+0x49650 -> +0x46760 -> transform thunks`가 실제 32+ op module을 설치한 뒤에만 단일 PatHouse 세션으로 화면/FPS 측정

