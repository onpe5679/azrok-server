# 214 — x87 outer-loop 네이티브 마이크로벤치

날짜: 2026-07-21  
대상: BoxedWine `Test/x64`, acknex.dll `[0x1004AA80, 0x1004ABE7)`  
분류: **VERIFIED native dynamic / NOT APPLICABLE to current PatHouse FPS**

## 결론

- **VERIFIED:** 독립 벤치마크의 기존 8개 의미론 케이스에서 NormalCPU
  interpreter와 `d3d9WebRunX87OuterLoopTrace()` 결과가 모든 측정 반복마다
  GPR, lazy-flag tuple, EIP, MXCSR, XMM, 전체 x87 상태, 관련 guest memory까지
  bit-exact였다.
- **VERIFIED:** 프로세스 5회, 각 프로세스에서 케이스별 warm-up 17회와
  측정 257회를 실행했다. 따라서 각 경로의 측정 pair는 총
  `5 * 8 * 257 = 10,280`개이다.
- **VERIFIED:** 5개 프로세스의 케이스별 중앙값을 다시 취해 합산하면
  reference는 **33.4 us**, helper는 **2.9 us**, 비율은 **11.517x**였다.
- **VERIFIED:** 각 프로세스의 8-case median-sum 범위는 reference
  **33.4--37.2 us**, helper **2.8--3.7 us**, speedup **10.054--12.000x**였다.
- **중요:** 이것은 Windows 네이티브 `Test/x64`에서 interpreter dispatch와
  한 번의 C++ helper 호출을 비교한 마이크로벤치다. 브라우저 WASM 비용이나
  FPS를 예측하지 않는다.
- **중요:** 문서 212가 현재 고정 PatHouse 세션에서 exact AA80 entry count가
  **0**임을 확인했다. 따라서 이 결과는 helper 설계의 재사용 가능성과
  dispatch 제거 상한을 보여줄 뿐, 현재 PatHouse 성능 향상 근거가 아니다.

## 측정 구현

production 및 기존 `testHotAOTX87.cpp` fixture는 수정하지 않았다. 별도 파일을
추가했다.

- `source/test/cpu/testHotAOTX87Benchmark.cpp`
- `source/test/cpu/testHotAOTX87Benchmark.h`

reference 경로:

1. relocated byte-exact trace의 entry에서 `getNextOp()`까지 준비
2. 타이머 시작
3. `CPU::run()`을 `TestEnd`까지 반복
4. 타이머 종료

helper 경로:

1. 동일 초기 상태를 hot trace entry에 준비
2. 타이머 시작
3. `d3d9WebRunX87OuterLoopTrace(cpu, HOT_ENTRY)` 단 한 번 호출
4. 타이머 종료

다음은 양쪽 모두 타이밍 밖이다.

- guest memory 및 CPU/FPU 상태 초기화
- decoder op-cache clear 및 최초 `getNextOp()`
- 완료 상태 snapshot과 bit-exact 비교
- 결과 출력

helper 타이밍에는 실제 production helper와 동일하게 distributed signature
validation, ordered guest memory operation, 마지막 exit `getNextOp()`이 포함된다.

## 5-process 중앙값

단위는 ns이며, 각 셀은 각 프로세스 내부 257회 중앙값을 5개 프로세스에 걸쳐
다시 취한 값이다.

| case | reference | helper | ratio |
|---|---:|---:|---:|
| one-all-minus1-00-equal-flat | 2,700 | 200 | 13.500x |
| one-all-minus1-10-greater-seg | 3,200 | 300 | 10.667x |
| one-all-minus1-01-less | 2,900 | 300 | 9.667x |
| one-all-minus1-11-qnan | 3,100 | 300 | 10.333x |
| three-all-minus1-negzero | 4,600 | 500 | 9.200x |
| one-one-link-denormal | 5,400 | 400 | 13.500x |
| one-multi-link-infinity | 6,000 | 500 | 12.000x |
| one-out-of-count-link-snan | 5,500 | 400 | 13.750x |
| **median sum** | **33,400** | **2,900** | **11.517x** |

짧은 helper 구간은 이 호스트의 `steady_clock` 출력에서 100ns 단위로 보인다.
단일 표본 대신 257회 중앙값과 5개 독립 프로세스를 사용한 이유다.

## 검증 명령과 결과

MSVC `Test/x64`, `/O2`, 단일 worker로 빌드했다.

```text
MSBuild.exe BoxedWine.vcxproj /p:Configuration=Test /p:Platform=x64 /p:PlatformToolset=v143 /m:1
warning 0, error 0

BoxedWine.exe 8 1 1
Benchmark D3D9Web Hot AOT X87 Outer Loop ... OK
0 tests FAILED
```

독립 벤치 5회 뒤, 새 벤치와 앞선 집중 테스트를 함께 실행했다.

```text
BoxedWine.exe 0 9 1
Test Runtime WASM JIT Guards ... OK
Test WASM Branch Tier ... OK
Test WASM Memory Tier ... OK
Test Runtime WASM Emitter ... OK
Test WASM JIT Stackified Register Block ... OK
Test D3D9Web Hot AOT Transform3x3 ... OK
Test D3D9Web Hot AOT TransformCoord ... OK
Test D3D9Web Hot AOT X87 Outer Loop Fixture ... OK
Benchmark D3D9Web Hot AOT X87 Outer Loop ... OK
0 tests FAILED
```

## 적용 판단

- **VERIFIED reusable mechanism:** 실제로 실행되는 동일 형태의 x87 trace가
  발견되면 whole-loop helper가 decoder/dispatch 비용을 크게 줄일 수 있다.
- **NOT VERIFIED browser:** 네이티브 helper 비율을 WASM 또는 브라우저의
  비율로 환산할 수 없다.
- **NOT APPLICABLE current scene:** 현재 PatHouse에서는 AA80 entry가 0이므로
  이 helper를 더 최적화하거나 기본 활성화해도 현재 scene FPS를 올리지 않는다.
- 다음 구현 대상은 PatHouse에서 entry가 실제로 관측되는 블록이어야 한다.

