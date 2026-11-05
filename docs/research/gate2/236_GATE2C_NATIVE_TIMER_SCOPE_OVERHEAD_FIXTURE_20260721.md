# 236 — Gate 2C native timer-scope overhead fixture (2026-07-21)

## 결론

- **VERIFIED (native Test/x64):** production 소스를 바꾸지 않고, 실제 `CPU::run()` 고정 블록에 현재 time-profile 후보와 같은 1/32 선택기와 고해상도 타이머 두 번을 둘러싼 테스트 전용 fixture를 추가했습니다.
- **VERIFIED (native Test/x64):** 2,097,152회 실행, 9개 순서 회전 triplet, triplet별 비율 중앙값 판정에서 독립 프로세스 7/7이 `<5%` gate를 통과했습니다. 프로세스별 총 오버헤드 중앙값은 **1.380%**, 범위는 **-0.833%..2.814%**였습니다. 음수는 가속이 아니라 남은 측정 잡음입니다.
- **VERIFIED:** CPU fixture 0..16 통합 실행도 17/17 통과했고, 그 실행에서 timer-scope 총 오버헤드는 **3.145%**였습니다.
- **NOT VERIFIED (browser):** 이것은 Windows native `std::chrono::steady_clock` fixture입니다. Emscripten의 `emscripten_get_now()`, pthread worker, 브라우저 스케줄러, 실제 PatHouse 프레임 비용은 아직 측정하지 않았습니다. 따라서 브라우저 계측을 켜도 `<5%`라고 단정할 수 없습니다.

## 변경 범위

테스트 전용 파일만 추가/등록했습니다.

- `source/test/cpu/testTimeProfileOverhead.h`
- `source/test/cpu/testTimeProfileOverhead.cpp`
- `source/test/testMain.cpp`의 TestCPU 등록
- `project/msvc/BoxedWine/BoxedWine/BoxedWine.vcxproj`의 테스트 파일 등록

production CPU, D3D9 proxy, WASM, 배포 자산 및 브라우저 세션은 변경하지 않았습니다.

## Fixture 계약

### 실제 실행 블록

게스트 `0x2D000100`에 다음 9바이트를 배치했습니다.

```text
47 3B BE 64 02 00 00 72 F7
INC EDI
CMP EDI,[ESI+264h]
JB  0x2D000100
```

`[ESI+264h] = 0xFFFFFFFF`로 두어 2,097,152번의 `CPU::run()`이 같은 이미 디코드된 블록 한 개를 실행하고 같은 entry로 돌아오게 했습니다. setup, decode priming, fixture 설치는 측정 밖입니다.

### 세 모드

1. `Baseline`: `CPU::run()`만 실행
2. `SelectorOnly`: 매 호출 production 후보와 같은 xorshift 선택기 및 `(selector & 31) == 0` 판정
3. `ScopedTimer`: 선택기 + 선택된 약 1/32 호출 앞뒤의 `steady_clock::now()` 두 번

각 trial에서 세 모드를 연속 실행하되 시작 순서를 회전합니다. 절대시간 세 집합을 따로 중앙값 낸 뒤 빼지 않고, 같은 trial triplet 안에서 먼저 다음 비율을 계산한 뒤 9개 비율의 중앙값을 취합니다.

```text
selector overhead = (selector - baseline) / baseline
timer increment   = (scoped - selector) / baseline
total overhead    = (scoped - baseline) / baseline
```

허용 기준은 `median(total overhead) < 5%`입니다. 선택 표본 수도 1/32 주변 범위인지 별도 검사합니다.

## 측정 설계 교정도 실측 결과다

### 262,144회 / 약 15 ms 모드 — 기각

첫 구현은 모드당 약 15 ms였습니다. 첫 단독 실행은 총 5.939%로 실패했고, 이후 7개 프로세스 중 2개도 8.631%, 나머지는 0.590%..4.530%였습니다. Windows 스케줄러/주파수 잡음이 5% gate와 같은 크기여서 이 측정창은 판정용으로 부적합했습니다.

### 2,097,152회지만 독립 중앙값끼리 비교 — 기각

측정창을 8배로 늘린 뒤에도 `median(scoped) - median(baseline)`처럼 서로 독립인 중앙값을 빼면 7개 프로세스 중 3개가 5.385%, 5.988%, 7.441%로 실패했습니다. 서로 다른 trial의 절대 시간이 짝지어져 호스트 드리프트가 계측 비용으로 섞였습니다.

### 2,097,152회 + order-rotated paired triplet — 채택

동일 trial의 baseline/selector/scoped를 먼저 정규화한 최종 fixture 결과입니다.

| process | selector % | timer increment % | total % | result |
|---:|---:|---:|---:|---|
| 1 | 1.383 | -0.675 | 2.454 | PASS |
| 2 | -0.418 | 4.911 | 1.380 | PASS |
| 3 | 3.488 | -0.464 | 2.814 | PASS |
| 4 | -0.537 | 1.802 | -0.833 | PASS |
| 5 | 0.885 | 0.740 | 1.625 | PASS |
| 6 | 0.088 | 0.258 | 0.114 | PASS |
| 7 | -1.147 | 4.181 | -0.229 | PASS |
| **process median** | **0.088** | **0.740** | **1.380** | **7/7 PASS** |

표본 수는 매 scoped trial에서 65,683/2,097,152 = 3.132%로 예상 1/32에 부합했습니다.

## 재현 명령과 결과

```powershell
& 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe' `
  project\msvc\BoxedWine\BoxedWine\BoxedWine.vcxproj `
  /m:1 /p:Configuration=Test /p:Platform=x64 /p:PlatformToolset=v143 `
  /p:BuildProjectReferences=false /verbosity:minimal

.\project\msvc\BoxedWine\BoxedWine\x64\Test\BoxedWine.exe 16 1 1
.\project\msvc\BoxedWine\BoxedWine\x64\Test\BoxedWine.exe 0 17 1
```

통합 실행의 마지막 결과:

```text
TIME_PROFILE_SCOPE_NATIVE runs=2097152 trials=9 samples=65683
baseline_ns=118694900 selector_ns=120031200 scoped_ns=122636300
selector_overhead_pct=-0.217 timer_increment_pct=2.057
total_overhead_pct=3.145 sample_rate=1/32 acceptance_lt_pct=5
Benchmark Time Profile Scope Overhead ... OK
0 tests FAILED in 4s
```

## 다음 브라우저 gate

이 fixture는 계측 구조의 native 사전 gate일 뿐입니다. 브라우저에서는 같은 PatHouse 고정 장면과 충분히 긴 동일 구간에서 profiler OFF/ON을 교차 실행하고, Present 수/공통 wall time으로 FPS 변화가 5% 미만인지 직접 확인해야 합니다. `emscripten_get_now()` 호출 비용도 별도 카운터로 분리해야 하며, 이 native 결과를 브라우저 수치로 대입하면 안 됩니다.
