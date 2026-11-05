> **SUPERSEDED by 598.** 기존 origin의 D3D9 registry를 물려받은 오염된 A/B였으며 fresh prefix에는 `reg add`가 필수다.

# 596 — 브라우저 콜드 부팅 운영 진단 제거 (2026-08-27)

## 범위

서버 선택 화면의 실제 버튼에서 수정하지 않은 `Azrok.exe`가 첫 D3D draw를
표시할 때까지를 Codex 인앱 브라우저로 직접 측정했다. 서버/프로토콜, D3D9Web
페이지와 런타임은 변경하지 않았고, 앱 ZIP의 동적 계정 런처 한 파일만 바꿨다.

## VERIFIED — 기존 병목 경계

- 빈 `localhost:8765` origin의 기존 `startersplash1` 실행에서 runtime ready 뒤
  app/root 생성과 94 JIT group·30,550 entry 등록은 약 1.3초에 끝났다.
- 부팅 오버레이는 그 뒤에도 유지됐고 첫 실제 draw는 실행 버튼 뒤 약 52초,
  WSS 수락/TCP 연결은 runtime ready 뒤 약 54초에 나타났다.
- 따라서 이번 실측의 주 병목은 314.62 MiB archive 전송이나 JIT 등록이 아니라
  Wine/Azrok guest 기동부터 첫 draw 직전까지였다.

## VERIFIED — 정적 근거와 최소 변경

기존 `run_azrok_account.bat`는 원본 클라이언트보다 먼저 `reg.exe`와
`acklog_tail.exe`를 별도 Wine 프로세스로 실행했다. 같은 런처의
`WINEDLLOVERRIDES=d3d9=n`이 이미 자식 프로세스에 적용되므로 매 실행의
`reg add`는 중복이었다.

선행 조사 #167의 Ghidra 결과대로 Acknex `-diag`는 `acklog.txt`를 열고 매 쓰기마다
flush한다. #548에서 `WINEDEBUG=+seh`는 알려진 OX invalid-BMAP 예외를 복구하지
못하는 진단 채널로 확정됐다. 운영 실행에 두 진단 스트림을 소비하는 경로도 없다.

새 빌더 `tools/build_fastboot_account_app.py`는 원본 immutable ZIP에서 정확히
`run_azrok_account.bat` 하나만 바꾸며 다음만 제거한다.

1. 매 부팅의 `reg add ... DllOverrides`
2. 진단 helper `start /b acklog_tail.exe`
3. Acknex `-diag`
4. Wine `+seh` 채널 (`WINEDEBUG=-all`은 유지)

원본 `Azrok.exe`, 콘텐츠, native D3D9 override, locale, 계정·서버 인자는 그대로다.

## VERIFIED — 브라우저 A/B

같은 Codex 인앱 브라우저와 `localhost:8765` 버튼 경로에서 단일 실행씩 비교했다.
각 후보 앱 ZIP은 별도 immutable URL로 실제 HTTP 200 전달됐다.

| 실행 앱 | 변경 누적 | 첫 draw |
|---|---|---:|
| 기존 `startersplash1` | 없음 | 약 52.0초 |
| `fastboot1` | `reg.exe`, `acklog_tail.exe` 제거 | 약 49.2초 |
| `fastboot2` | 위 + Acknex `-diag` 제거 | 약 45.0초 |
| `fastboot3` | 위 + Wine `+seh` 제거 | **약 38.7초** |

최종 후보는 기존 대비 약 13.3초, 약 25.6% 단축됐다. 첫 draw 뒤 실제 아즈로크
화면을 스크린샷으로 확인했고 FPS 표시는 180.9까지 갱신됐으며 private status API는
연결된 세션을 보고했다. 이 수치는 단일 브라우저 실측이므로 통계적 benchmark로
일반화하지 않는다. 다만 baseline의 archive/JIT가 1.3초에 완료됐으므로 13.3초 감소를
캐시 차이만으로 설명할 수는 없다.

## 배포 자산과 회귀

- 앱: `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1_fastboot3.zip`
- 크기: 157,274,401 bytes
- SHA-256: `A46A51540CB9177594637D3855875DAD0CA61847F9B0F4697C95A2DBF60B1E2B`
- 홈페이지 fallback과 `azrok_launch.js`를 `fastboot3`로 통일하고 cache-buster를
  `restore7`로 올렸다.
- `python -m unittest discover -s tools -p 'test_*.py'`: **291 tests PASS**.
- 빌더 회귀는 ZIP 4,269개 member 순서/내용을 비교해 런처 한 파일만 달라짐을 고정한다.

## NOT VERIFIED

- 물리 모바일/LAN/Tailscale 장치의 완전한 빈 캐시에서 반복 측정한 분포.
- 남은 약 39초의 세부 guest 함수별 비중. 더 줄이려면 추정 플래그 삭제가 아니라
  첫 process start부터 첫 Present까지 파일/함수 경계를 새로 계측해야 한다.
