# 598 — fresh prefix D3D9 registry와 fastboot4 복구 (2026-08-28)

## 증상

다른 컴퓨터의 `playazrok.com` 실행 로그는 current app/root/JIT를 모두 정상
받고 94 group·30,550 entry replay까지 등록했지만 다음에서 중단됐다.

```text
Uknown int 99 call: 2897
worker sent an error ... Uncaught ReferenceError: alert is not defined
```

같은 계정 `aeRVSOfRNIRtM`에 대한 u32ws bridge/core 로그에는 WS accept나 login이
한 건도 없었다. 따라서 Cloudflare, WSS 또는 서버 프로토콜 문제가 아니라 원본
클라이언트의 첫 네트워크 이전 guest 렌더 초기화 실패다. 선택적인
`fastboot3-jit-modules.zip` 404는 persistence loader의 허용된 fallback이며 원인이
아니다.

## VERIFIED — 원인

`#596`의 A/B는 빈 `localhost` origin에서 기존 launcher를 먼저 실행한 다음 같은
origin으로 fastboot1/2/3을 순서대로 실행했다. 첫 baseline의

```bat
reg add "HKCU\Software\Wine\DllOverrides" /v d3d9 /d native /f
```

가 IndexedDB Wine prefix에 남았으므로 뒤 후보에서 이 줄을 제거해도 native D3D9가
계속 선택됐다. 완전히 새 컴퓨터/prefix에는 그 registry가 없고, D3D9 override가
적용되기 전에 Wine OpenGL INT 0x99 index 2897로 진입했다. D3D9Web build의
`callOpenGL`은 그 callback을 지원하지 않아 `kpanic`의 worker-side `alert()`까지
도달했고 `alert`가 없는 worker에서 ReferenceError가 발생했다.

즉 `WINEDLLOVERRIDES=d3d9=n`만으로 fresh browser가 보장된다는 #596의 결론은
기각됐다. 기존 prefix 값이 가린 A/B 오염이었다.

## 수정

새 immutable `fastboot4`는 idempotent D3D9 `reg add`만 복구한다. 다음 진단성
지연 제거는 유지한다.

- `acklog_tail.exe` 미실행
- Acknex `-diag` 제거
- `WINEDEBUG=-all` 유지, `+seh` 제거
- 원본 `Azrok.exe`, app 콘텐츠, root, JIT, 계정/서버 인자 불변

배포 자산:

- `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1_fastboot4.zip`
- 157,274,465 bytes
- SHA-256 `2EBDDA97C7159C9B7A59AD05F33AE490EA7C03077F24BC39028D461E292CB1DB`

홈페이지/서버 선택 route는 `restore9` + `fastboot4`로 갱신했다. 이미 주소창에
`app=...fastboot3`가 남은 사용자를 위해 실행 페이지도 load 시 query와 내부
app stem을 `fastboot4`로 자동 승격한다.

## VERIFIED — 공개 fresh-origin 수용

- 새 Chrome `https://playazrok.com` origin에서 homepage → server list를 열었다.
- 계정을 새로 만들지 않는 직접 probe로 fastboot4를 처음 mount했다.
- 약 60초 안에 boot overlay가 해제되고 FPS가 16.2로 갱신되어 첫 drawn Present를
  확인했다.
- console error/warning은 0건이며 `Unknown int 99`, `alert is not defined`가
  재발하지 않았다.
- 무티켓 probe의 WSS 종료 뒤 서버 선택 화면으로 정상 복귀했다.
- 구 fastboot3 URL을 다시 열자 주소가 즉시 fastboot4로 replace됐다.
- u32ws public app HEAD는 200, Content-Length 157,274,465와 immutable header를
  반환했다.
- 전체 suite: **293 tests PASS**.

## NOT VERIFIED

- 문제를 제보한 정확한 물리 PC에서 브라우저 캐시를 유지한 채 새로고침 후 최종
  character selector/PatHouse까지의 사용자 수용. 실행 페이지 migration 때문에
  구 URL 새로고침도 fastboot4를 선택해야 한다.

