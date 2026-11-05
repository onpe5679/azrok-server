# 261 — Gate 6 foreground·bridge·official JIT measurement (2026-07-22)

## 결론

- **VERIFIED:** 안정된 1024×768 PatHouse에서 게스트→호스트 경계는 약 712회/frame이지만, 기존 ordered batch 때문에 실제 main-thread 왕복은 약 5.02–5.10회/frame이고 호스트 응답 대기는 8.29–8.62 ms/frame이다. 따라서 약 30 ms가 동기 경계 왕복에 사라진다는 가설은 기각한다.
- **VERIFIED:** 같은 창에서 BoxedWine `KThread::kernelTime`은 5.26–7.26 ms/frame이었다. bridge 전체 체류 8.64–8.95 ms/frame과 합쳐도 약 13.9–16.2 ms/frame이며, 남은 약 20.7–23.7 ms/frame은 게스트 user-space/JIT 실행과 스케줄링 영역이다.
- **VERIFIED:** 공식 upstream O3 JIT와 no-JIT의 기존 15표본 평균은 각각 32.4667 FPS와 32.2 FPS로 차이가 약 +0.8%뿐이었다. 다만 당시 Windows foreground HWND를 표본 전·후에 기록하지 않았으므로 이 비교는 엄격한 foreground 고정 A/B가 아니다.
- **VERIFIED:** 2026-07-22 14:07:40.489와 14:08:23.804 KST에 foreground HWND가 모두 `0x10A82`, `ChatGPT` PID 15032임을 직접 확인했다. 그 사이 공식 upstream O3 JIT의 15개 1초 HUD 표본은 평균 32.7267 FPS, 최소 27.1, 최대 38.0이었다.
- **INFERRED:** 사용자가 Codex 창을 foreground로 둔 뒤 chain64 표본이 27.8733→32.7333 FPS로 변한 관찰은 Windows/Chromium foreground scheduling 영향의 강한 후보이나, 당시 HWND를 독립 기록하지 않았으므로 +17.4%를 확정 수치로 사용하지 않는다.

## 측정값

### 게스트→호스트 경계

120-Present 안정 창에서:

| 항목 | 측정 범위 |
|---|---:|
| guest bridge calls/frame | 약 712 |
| main-thread round trips/frame | 5.02–5.10 |
| host response wait/frame | 8.29–8.62 ms |
| full bridge residency/frame | 8.64–8.95 ms |
| BoxedWine kernel/syscall time/frame | 5.26–7.26 ms |

`d3d9web.cpp`의 profiler는 `COMMAND.PRESENT`를 프레임 경계로 사용하며, guest call 수와 실제 main-thread 왕복 수를 분리한다. 약 712개의 API 호출이 이미 약 5회의 실제 왕복으로 묶이므로, 무조건적인 추가 command batching만으로 50 FPS에 도달할 수 있다는 가설은 현재 수치와 맞지 않는다.

### 공식 JIT

- **VERIFIED:** JIT 활성 비율은 약 99.99%였고 전체가 interpreter로 되돌아간 상태가 아니다.
- **VERIFIED:** 평균 compiled block 길이는 약 51.8 ops였다.
- **VERIFIED:** O3 JIT/no-JIT 기존 비교는 사실상 동률이었다. 이 결과는 JIT가 켜졌다는 사실과 프레임 이득이 크다는 주장을 구분해야 함을 보여준다.

### frame cap 정정

- **VERIFIED static:** `Sleep(20-delta)`는 PopcornGame room `0x6D` 경로이며 PatHouse가 아니다.
- **VERIFIED static:** PatHouse room code 100의 `FUN_00561050`에는 Sleep/Wait가 없다.
- **VERIFIED static:** Acknex의 별도 cap은 60 FPS이고 현재 31–36 ms 프레임에서는 이미 cap 대기 분기를 타지 않는다.

### x87 FISTP 후보 정정

- **VERIFIED dynamic:** 저오버헤드 opcode 표본의 최상위 FISTP EIP들은 pid 71/75의 `/opt/wine/lib/wine/i386-unix/win32u.so`였고, `0x10438653`은 pid 14 `/opt/wine/bin/wineserver`였다. Acknex 렌더 핫블록이 아니었다.
- **VERIFIED static:** 추출한 win32u.so의 해당 위치는 인접한 `fild m64; fistp m64` 패턴, 즉 산술 없는 64-bit integer x87 왕복이었다.
- **VERIFIED implementation/rejected:** 이 인접 패턴을 exact i64 passthrough로 임시 JIT 처리한 빌드는 시각 회귀는 없었지만 15표본 평균 28.56 FPS로 이득을 보이지 않았다. foreground HWND를 그 표본 전·후에 기록하지 않았으므로 정확한 -12% 수치는 확정 비교로 쓰지 않고, 소스 변경은 전부 되돌렸다.

## 판정 및 다음 측정

1. **REJECTED:** 30 ms 동기 D3D 경계 왕복 병목 가설.
2. **REJECTED:** 짧은 MT chain2/chain64 및 win32u FISTP exact-i64 국소 특수화. 소스는 원복했다.
3. **NOT VERIFIED:** 실제 브라우저 worker가 속한 Windows 프로세스/스레드의 foreground priority, EcoQoS 또는 Chromium background throttling이 남은 약 20–24 ms에 얼마나 기여하는지.
4. 다음 실측은 동일한 한 개 PatHouse 세션에서 OS foreground HWND를 전·후에 기록하고, 관련 프로세스별 CPU delta와 priority/throttling 상태를 동시에 수집한다. 별도 네이티브 게임이나 중복 브라우저 세션은 띄우지 않는다.
