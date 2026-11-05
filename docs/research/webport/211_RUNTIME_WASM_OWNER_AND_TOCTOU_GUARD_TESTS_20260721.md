# 211 — Runtime WASM owner-token 및 TOCTOU 가드 검증 픽스처

날짜: 2026-07-21

## 결론

- **VERIFIED (source):** `RuntimeStackifiedBlock`은 콘텐츠 해시가 아니라 라이브 블록 객체의 wasm32 주소를 `moduleId`로 사용합니다.
- **VERIFIED (source):** 컴파일은 코드 바이트 스냅샷 전후에 `DecodedOp` identity와 전체 바이트를 다시 검사합니다.
- **VERIFIED (source):** 실행은 생성 WASM이 shadow state만 변경하게 한 뒤, guest state 커밋 직전에 identity와 전체 바이트를 다시 검사합니다.
- **VERIFIED (native dynamic):** 통합 MSVC Test/x64 실행에서 `Test Runtime WASM JIT Guards: OK`를 확인했습니다. stale compile identity와 compile/execute 사이 code mutation의 무커밋 폴백이 통과했습니다.
- **NOT VERIFIED (pthread-WASM pending):** owner-token 충돌 A-B-A 실행과 실행 후/커밋 직전 동기 변조 분기는 `__EMSCRIPTEN__` 전용이므로 별도 1 GiB pthread-WASM 테스트 실행이 남았습니다.

## 추가한 독립 테스트

- `source/test/cpu/testWasmJitRuntimeGuards.cpp`
- `source/test/cpu/testWasmJitRuntimeGuards.h`
- `testMain.cpp` 및 MSVC Test 프로젝트에 `Test Runtime WASM JIT Guards` 등록
- production 파일 수정 없음

### 1. 컴파일 identity 가드

두 명령의 지원 블록을 디코드한 뒤 코드 바이트를 `KMemory::writeb`로 변경합니다. 이전 `DecodedOp*`를 담은 compile request가 `nullptr`로 거부되고 GPR, EIP, lazy tuple, `nextOp`가 변하지 않아야 합니다.

### 2. compile/execute 사이 바이트 가드

정상 컴파일 뒤 첫 immediate 바이트를 변경하고 공개 `WasmJitCompiledBlock::execute` 경로를 호출합니다. 결과는 `Fallback`이어야 하며 guest CPU state는 한 필드도 커밋되지 않아야 합니다.

### 3. 실행 후/커밋 직전 바이트 가드

Emscripten 테스트에서 블록 객체 주소로 계산한 실제 production `moduleId`의 worker-cache `run`을 테스트 더블로 바꿉니다. 더블은 shadow GPR/lazy state를 오염시키고 host-translated guest code 한 바이트를 동기 변경한 뒤 성공을 반환합니다. 실행 전 가드는 통과하지만 실행 후 전체 바이트 가드가 변경을 잡아 `Fallback`하고, shadow 변경은 guest CPU에 전혀 게시되지 않아야 합니다.

### 4. 32-bit 콘텐츠 해시 충돌과 owner-token 분리

서로 다른 결과를 내는 두 유효 모듈을 고정했습니다.

- A: `eax=640966b5`, `ecx=b0ce33e7`
- B: `eax=3c076a57`, `ecx=bd6d2b63`
- 두 모듈의 FNV-1a32: `f7483c6f`

테스트는 실제 emitter가 두 서로 다른 바이트열과 동일한 위 해시를 만드는지 먼저 확인합니다. Emscripten에서는 두 라이브 owner 객체 주소를 별도 key로 cold-install하고 A → B → A 순서로 실행하여, 같은 32-bit 콘텐츠 해시여도 두 인스턴스가 동시에 살아 있고 서로 치환되지 않음을 증명합니다.

## 남은 실행 게이트

1. ~~MSVC Test/x64 컴파일 및 `BoxedWine.exe 0 3 1`~~ — **VERIFIED: OK**
2. 1 GiB shared-memory pthread Emscripten Test 빌드
3. Emscripten 실행에서 post-run guard와 owner collision A-B-A 분기 통과 확인

Emscripten 전용 두 분기 실행 전에는 전체 동적 검증 완료로 간주하지 않습니다.
