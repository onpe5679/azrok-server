# 528 부팅 300초와 주기적 정지의 공통 원인 — 매 세션 반복되는 프리픽스 업데이트 (2026-07-29)

날짜: 2026-07-29
선행: #527(무효 배너 참조), #525, #526
**원본 실행파일·게임 자산·런타임 바이너리 무수정. 변경은 root 안의 텍스트 파일 1개, 8바이트.**

## 1. 한 줄

`home/username/.wine/.update-timestamp` 를 `disable` 로 바꾸자
**부팅 330초 → 60초 미만**, **주기적 정지 17~24회/분 → 0회**.

## 2. 사슬 (VERIFIED — Wine 소스 + 게스트 로그)

게스트 로그의 결정적 한 줄:

```text
0024:err:environ:run_wineboot boot event wait timed out
[?25lreg: The operation completed successfully
```

`reg` 는 런처 bat 의 첫 줄이다. 즉 **bat 이 실행되기까지 걸린 시간이 곧 wineboot 대기 시간**이다.

1. `dlls/ntdll/unix/env.c: build_initial_params()` 가 **부모 없는 프로세스에서 무조건**
   `run_wineboot()` 을 호출한다. BoxedWine 은 세션마다 wineserver 를 새로 띄우므로
   **매 부팅이 첫 부팅**이다.
2. `run_wineboot()` 의 대기 타임아웃이 소스에 박혀 있다.

   ```c
   timeout.QuadPart = (ULONGLONG)5 * 60 * 1000 * -10000;   /* 정확히 300초 */
   if (NtWaitForMultipleObjects( count, handles, WaitAny, FALSE, &timeout ) == WAIT_TIMEOUT)
       ERR( "boot event wait timed out\n" );
   ```

   `WaitAny` 로 **이벤트 신호 또는 wineboot 종료** 를 기다린다. 300초를 다 채웠다는 것은
   wineboot 이 신호도 안 하고 끝나지도 않았다는 뜻이다.
3. `programs/wineboot/wineboot.c` 에서 `SetEvent(event)` 는 **main 의 맨 마지막 줄**이다.
   그 앞의 `update_wineprefix()` 안에는 rundll32 설치를 `INFINITE` 로 기다리는 루프와
   `install_root_pnp_devices()` 가 있다. 로그의 마지막 줄이 정확히 그 wineusb 설치였다.

   ```text
   0108:err:setupapi:SetupDefaultQueueCallbackW copy error 1812 ... wineusb.sys -> wineusb.inf
   ```
4. 그 블록 전체를 거르는 조건은 단 한 줄이다.

   ```c
   if (update_timestamp( config_dir, st.st_mtime ) || force) { ... }
   ```

   `update_timestamp()` 는 프리픽스의 `.update-timestamp` 를 읽어
   **`"disable"` 로 시작하면 무조건**, 혹은 값이 `wine.inf` 의 mtime 과 같으면 갱신을 건너뛴다.
5. 실제 값이 어긋나 있었다.

   | 항목 | 값 |
   |---|---|
   | `.update-timestamp` | `1776473242` |
   | `wine.inf` mtime (2026-04-18 08:47:20 UTC) | 약 `1776502040` |
   | 차이 | 약 **-28,798초 (≈ 8시간)** |

   타임존/mtime 변환 차이로 보인다. 어긋나므로 **매 부팅 전체 재설치**가 돌았다.

## 3. 정지까지 같이 사라진 이유 (INFERRED — 강한 정황)

`run_wineboot()` 은 타임아웃 후 **기다리기를 포기할 뿐 wineboot 을 죽이지 않는다.**
핸들만 닫고 돌아간다(`while (count) NtClose( handles[--count] );`).
따라서 wineboot 과 그 안의 rundll32 설치 프로세스는 **게임이 도는 내내 살아서 계속 돈다.**
이것이 #525 에서 관측한 2.4~2.9초 주기 정지의 정체로 보인다.

이 해석은 #525 의 관측들과 모순이 없다.

- 정지 중 Present 도 0 → 게스트 전체가 멈춤 (다른 게스트 프로세스가 CPU 를 가져감)
- 메인 스레드는 막힌 게 아니라 `(program)` 90% 로 **바빴다** → 워커를 기다리는 스핀
- `longtask` 0건, LoAF 무귀속 → 메인 스레드 JS 가 아님
- 셰이더/wasm컴파일/IndexedDB/힙증가 전부 배제됨

**NOT VERIFIED**: 게스트 프로세스 목록으로 wineboot/rundll32 잔존을 직접 확인하지는 않았다.
정지가 사라진 것은 실측이지만, 그 원인이 잔존 프로세스라는 것은 아직 정황이다.

## 4. 수정과 검증

```text
home/username/.wine/.update-timestamp :  "1776473242\r\n"  ->  "disable\n"
새 root: TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1.zip
원본 root 무수정. 다른 파일 8,659개는 바이트 그대로 복사.
```

단독 부팅 검증 (`debugConsole=1&lean=0`, 즉 불리한 조건):

| t | canvas | audio |
|---|---|---|
| 30s | 1024x768 | false |
| **60s** | **640x480** | **true** |

같은 세션 60초 측정:

```text
blocks=0  callbacks=1407  silent=8 (0.57%)  fps=37.28
```

프로덕션 설정 확인 (`lean=1`, 진단 파라미터 없음, 새 브라우저, `E_noprefixupd_prod`):

```text
audio node after 40s
blocks=0  callbacks=1406  silent=0  silentPct=0  fps=40.6
```

| 지표 | 기존 root | noprefixupd1 (진단설정) | **noprefixupd1 (프로덕션)** |
|---|---|---|---|
| 오디오 노드까지 | 325~330초 | 60초 미만 | **40초** |
| 정지 횟수/60초 | 17~24 | 0 | **0** |
| 무음 콜백 | 0.21~2.49% | 0.57% | **0.00%** |
| fps | 34~41 | 37.28 | **40.6** |

**무음 0건.** 1,406회 콜백 중 무음 0. #257 이 2026-07-22 에 남긴 바닥값 2.30% 와
#525 의 0.21% 를 모두 밑돈다. 게스트 BGM 이 드롭아웃 없이 재생된다.

## 5. 부수 소득 — 게스트 자체 FPS 카운터로 135fps 이상치 확정

게스트 로그에 게임 자신의 카운터가 있다.

```text
D3D9WEB_FPS_SAMPLE presents=11281 delta=120 elapsed_ms=3449.905   -> 34.8 fps
                                            3381.575              -> 35.5 fps
                                            3330.710              -> 36.0 fps
                                            3052.300              -> 39.3 fps
                                            2984.065              -> 40.2 fps
```

**34~40 fps.** 외부 측정(34.2 / 36.1 / 37.3 / 41.1)과 일치한다.
#527 이 근거로 삼았던 **135.64 fps 는 이상치로 확정**이며, "JIT 캐시가 fps 를 4배로 만든다" 는
주장은 폐기한다. `D3D9WEB_FPS_SAMPLE` 은 계측 방식과 독립적인 축이므로 앞으로 이것을 우선한다.

## 5.5 게스트 MP3 디코딩의 fps 비용 = 사실상 0 (VERIFIED)

"#520 의 70 fps 는 브라우저 대행 재생이라 게스트가 디코딩하지 않았기 때문" 이라는 가설을
통제 A/B 로 검정했다. leg 마다 새 브라우저, 다른 인스턴스 0개, `bringToFront` 없음,
page 타깃에서 `devtools://` 제외, 나머지 조건 동일.

| leg | `webBgmFallback` | fps | 무음 | 정지 |
|---|---|---|---|---|
| G1 게스트 디코딩 | 0 | **39.16** | 0.43% | 0 |
| G2 브라우저 재생 | 1 | **40.83** | 0.36% | 0 |

차이 **1.67 fps** — 이날 관측된 편차(34~46)를 훨씬 밑돈다. **가설 기각.**
원본 실행파일이 MP3 를 직접 디코딩해도 fps 비용은 사실상 없다.
따라서 "게스트 재생" 과 "50 fps" 는 **상충하지 않는다.**

### #520 의 70 fps 는 이 카드로 재현되지 않았다 (NOT VERIFIED)

오늘의 통제 측정은 36.8 / 39.2 / 40.6 / 40.8 fps 에 모인다. #520 의 67.9~72.0 은
재현되지 않았고, 원인도 아직 모른다. **#520 은 root·app·runtimeStem·씬을 기록하지 않았다** —
"기존에 떠 있던 격리 데스크톱 Edge 게임 탭" 이라고만 적혀 있어 문서만으로는 재현이 불가능하다.
남은 후보는 그때의 씬(PatHouse 캐릭터·UI 유무), 해상도 구성, 그 시점의 root/스템이다.

**교훈**: 성능 카드는 반드시 root / app / runtimeStem / 씬 / 브라우저 인스턴스 상태를
함께 적을 것. 적지 않으면 다음 사람이 그 숫자를 쫓을 수 없다.

## 6. 방법론

nomono root(#526 계열)를 **단독 검증 없이 통제 A/B 양쪽에 바로 투입**해 20분을 날렸다.
새 변수는 A/B 에 넣기 전에 **단독 부팅부터 확인**한다. 이 카드의 root 는 그 순서를 지켰다.

또한 "180초에 멈춘 것처럼 보인다" 를 근거로 nomono 가 깨졌다고 의심했으나,
원본 root 로 같은 진단을 돌리자 **체크포인트가 전부 동일**했다. 조용한 프리픽스 초기화
구간이라 그렇게 보였을 뿐이다. **대조 없이 단독 관측으로 판단하지 말 것.**

## 7. 미결

- 잔존 wineboot/rundll32 프로세스를 게스트 쪽에서 직접 확인(§3).
- `silent 0.57%` 의 잔여분 — 정지가 0인데도 남는 이유.
- 프리픽스 업데이트를 건너뛰어 잃는 기능이 있는지(프리픽스는 root 에 완비돼 있어
  이론상 없지만, 장시간·다른 씬에서 확인 필요).
- nomono root(`mscoree`/`mshtml` 비활성)는 이 카드와 무관하며 **효과가 없었다**.
  Mono 프롬프트는 `update_wineprefix()` 안에서 일어나므로 이 수정으로 함께 사라진다.
