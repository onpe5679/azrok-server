# 548 — 웹 OX SEH/런처 감사 (2026-08-07)

## 범위

- `#534` 및 그 선행 조사 `#145`를 기준으로 과거의 “예외 무시/계속 실행” 경로가 웹 OX 크래시에도 적용되는지 재검토했다.
- 현재 사설 게스트 `player2`~`player6`가 사용하는 배포 ZIP의 런처를 정적으로 검사했다.
- 실제 게임 조작과 OX 입장 재현은 하지 않았다. 바이너리 패치와 BoxedWine 예외 건너뛰기도 적용하지 않았다.

## VERIFIED

### 1. 과거의 계속 실행 사례는 OX가 아니라 WineGStreamer BGM 장애였다

- `gate6/audio/523_BGM_WG_PARSER_NULL_UNIX_DISPATCH_20260729.md`의 장애는 WineGStreamer PE→Unix dispatch가 null인 상태에서 발생한 Wine unix-call fault였다.
- 당시 `WINEDEBUG=-all,+seh` 실행에서 fault가 로그로 보이고 반복 실행되는 현상이 있었지만, `gate6/audio/524_BGM_PCRE2_SEARCH_PATH_FIX_20260729.md`에서 실제 원인은 guest loader 경로의 `libpcre2-8.so.0` 누락으로 확정되어 라이브러리 배치로 해결됐다.
- 따라서 `+seh` 자체가 일반적인 “예외 무시” 기능이거나 OX 복구 패치였다는 근거는 없다.

### 2. 웹 OX의 최초 fault는 별개의 Acknex invalid-BMAP 역참조다

- `gate5/534_NULL_DISPATCH_ON_SCENE_TRANSITION_20260730.md`와 `gate2/145_GATE2B_VULKAN_OX_C8_GUEST_AV_20260719.md`에서 OX 서버 수락, 카운트다운, 질문 송신 뒤 최초 fault는 `acknex.dll` RVA `0x1DFB8`, `mov ecx,[eax+0x10]`으로 측정됐다.
- panel `+0x24`의 BMAP 포인터는 null이 아니라 읽을 수 없는 주소였다. guarded host 계측에서 draw 진입 전에 이미 unreadable이었고, `unmap`/`mprotect`가 원인인 경우는 배제됐다.
- `WINEDEBUG=-all`과 `WINEDEBUG=-all,+seh` 양쪽에서 OX는 unhandled exception으로 종료됐다. `+seh`는 이 fault를 계속 실행시키지 못했다.
- `#534`의 0x000D 전환 null-vtable fault는 별도 현상이며 OX invalid-BMAP fault와 합쳐서 판단하면 안 된다.

### 3. 현재 player2~6 런처에는 native D3D9와 `+seh`가 이미 들어 있다

검사 대상:

- `tools/boxedwine_local/apps/Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1.zip`
- SHA-256: `D87E4447169BEE588CBD942EB127BF19E9D7433452347BFCCEB4E17B2DDE0DD9`

정적 결과:

| 계정 | 런처 | `d3d9=n` | `WINEDEBUG=-all,+seh` | `acklog_tail.exe` |
|---|---|---:|---:|---:|
| player2 | `run_azrok_multi2.bat` | 예 | 예 | 아니오 |
| player3 | `run_azrok_player3.bat` | 예 | 예 | 예 |
| player4 | `run_azrok_player4.bat` | 예 | 예 | 예 |
| player5 | `run_azrok_player5.bat` | 예 | 예 | 예 |
| player6 | `run_azrok_player6.bat` | 예 | 예 | 예 |

- `tools/test_private_browser_admission.py`에 위 런처 계약을 고정하는 비플레이 회귀 테스트를 추가했다.
- 테스트는 각 런처의 native D3D9, `+seh`, `-NX 200`, 계정명, 로컬 서버 주소와 가짜 `OX_IGNORE` 부재를 검사한다.
- `python -m unittest tools.test_private_browser_admission.PrivateBrowserAdmissionTests.test_guest_launchers_keep_native_d3d9_and_seh_diagnostics -v` 결과는 `Ran 1 test ... OK`였다.
- player2의 `acklog_tail.exe` 부재는 진단 일관성 차이지만, `#534`에서 acklog의 crash-time 버퍼가 남지 않았으므로 이를 추가해도 OX 복구가 되지는 않는다.

## INFERRED

- 최초 fault의 직접 원인은 Acknex panel renderer가 수명이 끝났거나 덮어써진 BMAP 소유권을 계속 참조하는 것이다.
- 단순히 faulting instruction 하나를 건너뛰어도 같은 BMAP의 width/height 및 draw 데이터가 뒤이어 필요하므로 안정적으로 계속 실행될 가능성은 낮다.
- 임의 dummy BMAP 치환은 엔진의 참조 수명과 해제 규약을 바꾸므로, 마지막 writer/owner를 모르는 상태에서는 최소 바이너리 패치 원칙보다 위험하다.

## NOT VERIFIED

- 좌표 `(463,518)`의 fault panel을 생성한 정확한 클라이언트 함수와 panel `+0x24`의 마지막 writer.
- BMAP가 해제된 것인지, 다른 객체로 덮인 것인지, 포인터 필드만 손상된 것인지.
- 앞으로의 수정 뒤 실제 웹 OX가 끝까지 완료되는지. 실제 플레이는 사용자 검증 대기다.

## 결론과 최소 다음 순서

1. `+seh`나 런처 플래그 추가를 OX 해결로 보고하지 않는다. 해당 설정은 player2~6에 이미 있으며 fault를 복구하지 못했다.
2. 사용자 주도 OX 재현 시에만, 이전처럼 exact `acknex.dll` module base + RVA로 한정한 one-shot guarded host 계측을 다시 붙인다.
3. 좌표 `(463,518)` panel의 생성 시점과 `[panel+0x24]` 마지막 write를 먼저 포착한다. 예외 skip/resume이나 전역 low-address write-watch는 사용하지 않는다.
4. writer와 소유권 규약이 확인된 뒤 원본 수명 관리 경로를 최소 수정한다. 그 전에는 안전한 기능 패치가 확정되지 않았다.

## 판정

- **VERIFIED:** 현재 player2~6은 모두 native D3D9와 `+seh` 경로다.
- **VERIFIED:** `+seh`는 웹 OX invalid-BMAP 예외를 무시하고 계속 실행시키는 해결책이 아니다.
- **NOT VERIFIED:** OX 기능 복구. 현재 변경은 런처 상태의 회귀 방지와 잘못된 해결 주장 방지까지다.
