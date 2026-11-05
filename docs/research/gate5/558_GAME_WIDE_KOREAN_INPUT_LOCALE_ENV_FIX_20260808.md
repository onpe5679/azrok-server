# 558. Game-wide Korean input by restoring the Wine locale environment (2026-08-08)

## Scope

캐릭터 생성 이름이나 Plaza 채팅 한 곳만 우회하지 않고, 게임 바이너리
`Azrok.exe`를 수정하지 않은 채 원본 클라이언트의 모든 일반 ANSI 입력 컨트롤이
공유하는 경로를 복구한다.

`browser IME -> BoxedWine fake XIM -> Wine Unicode/ANSI conversion -> original control`

## VERIFIED - root cause

- `boxedwine-shell.js`의 `Module.arguments`는 이미 argv 배열이다. 그런데 기존
  `parseEnvProp()`과 Azrok 기본 환경은 값에 셸용 큰따옴표를 다시 포함시켰다.
- 수정 전 브라우저 실측 argv는
  `-env "\"LANG=ko_KR.EUC-KR\"" -env "\"LC_ALL=ko_KR.EUC-KR\""`였다.
  따옴표가 구문이 아니라 인자 본문이므로 BoxedWine은 이름이 `"LANG`인 변수를
  만들었고 libc/Wine은 실제 `LANG`과 `LC_ALL`을 보지 못했다.
- 같은 root를 native BoxedWine에서 실행하면 `locale charmap=EUC-KR`, Windows
  probe `GetACP()=949`였지만, 수정 전 웹 no-manifest probe는 `GetACP()=1252`였다.
- `parseEnvProp()`과 Azrok 기본값을 raw `KEY=VALUE`로 바꾼 뒤 웹 argv는
  `-env "LANG=ko_KR.EUC-KR" -env "LC_ALL=ko_KR.EUC-KR"`가 되었고 같은 웹
  Windows probe가 `D3D9WEB_GETACP=949`를 출력했다.

## VERIFIED - original client acceptance

- clean `storage=memory` 세션에서 표준 fake-XIM root
  `...acp949-xim25koreanlocale2`, app `...guestprofiles6_rsdefaults1_utf8ime2`,
  production runtime `...korean6chat1`을 사용했다. 실험적인 xim28/xim29 Wine
  패치는 사용하지 않았다.
- 원본 캐릭터 생성 화면에서 브라우저 IME로 `한글별`을 조합했다. 문자열은 host
  overlay가 아니라 원본 게임 이름 입력칸에 정확히 표시되었다.
- 원본 확인 버튼을 누르자 다음 튜토리얼 도움말 화면으로 진행했다. 따라서
  브라우저 조합, XIM commit, Wine ACP 949 변환, 원본 컨트롤 수락이 한 경로로
  직접 확인되었다.
- 일반 URL도 다시 실행해 기본 선택이 `xim25koreanlocale2` + `utf8ime2`이고,
  argv의 두 locale 변수가 raw 값인 것을 브라우저 로그에서 확인했다.
- base app과 utf8ime2 app의 `Azrok.exe` SHA-256은 모두
  `39680DA744DF27CF13EAE03F675D91C301B3CA9332F6979CA4447FBA9908CABA`다.
  게임 실행 파일은 패치하지 않았다.

## Production route

- `index.html`: 사설 세션 admission 후 `...utf8ime2` app을 선택한다.
- `index_d3d9web_pathouse.html`: base guestprofiles6 요청도 `...utf8ime2`로
  승격하고 root 기본값을 `...xim25koreanlocale2`로 선택한다.
- `boxedwine-shell.js?v=imeenv949fix3`: `LANG`/`LC_ALL`을 raw argv 값으로 전달한다.
- 예전 XIM/root와 명시적 URL override는 진단/rollback용으로 보존한다.

## Rejected hypotheses

- XIM FIFO/XIC가 commit을 못 한다는 가설: 이전 runtime probe에서 UTF-8 6 bytes,
  `XLookupChars` status 2까지 이미 통과했다.
- user32/imm32에 ACP 949를 강제하거나 `WM_IME_COMPOSITION`을 Unicode
  DefWindowProc로 우회하는 실험: 원본 입력칸은 계속 `?`였고 production에
  승격하지 않았다.
- 외부 `Azrok.exe.manifest`: 실행 파일에 embedded manifest가 있어 외부 manifest를
  원본 전체 해법으로 사용할 수 없다.
- 개별 Edit에 `EM_REPLACESEL` 또는 클립보드/Ctrl+V를 보내는 방식: 입력 위치별
  예외처리이며 game-wide 계약이 아니므로 기본 해법에서 제외했다.

## INFERRED

- 동일한 Wine 프로세스, XIM commit, ACP 949 변환을 사용하는 다른 원본 ANSI
  입력 컨트롤도 캐릭터 이름과 같은 공통 경로의 수혜를 받는다. 입력칸별 host
  패치가 아니라 프로세스 문자 환경을 복구했기 때문이다.
- 별도 custom text widget이 자체 디코더를 구현한 경우에는 독립 검증이 필요할 수
  있지만, 그런 위젯이 있다는 증거는 현재 없다.

## NOT VERIFIED

- 게임 안의 모든 입력 화면을 하나씩 열어 문자열을 제출하는 전수 수락 시험.
- 이번 캐릭터 생성 실측에서 새 이름의 durable 서버 저장 완료 패킷. 원본 확인 후
  다음 화면 진입은 확인했지만 해당 계정의 신규 서버 mutation은 확인하지 못했다.
- 이 leg에서 Plaza의 원본 ANSI Edit 자체를 다시 입력한 결과. #557의 browser-owned
  Plaza relay 수락 결과는 별도로 유효하다.

## Artifacts and verification

- locale root SHA-256:
  `AE1959C214A5BFF5AFE22E300E554525C586AE93D4E90AF6545D14B89894D3AF`
- utf8ime2 app SHA-256:
  `3B5C69FAC8916DC610B57AE341E1A27756E4CA08D1AA6335CC36584FCBAF8DAD`
- shell SHA-256:
  `F277F2CB86EC24D3F1B0BB85747F2E072E22D5DACB8D26B8697B2EF62DBFB909`
- game page SHA-256:
  `A4EC767E087EBFC5E45C8B1D6C64B0489F07E397F142FE22485BE5C0AC828EEF`
- focused page/private-admission tests: 30 passed.
- XIM/page focused tests after production-root contract update: 36 passed.
- full `tools/test_*.py` discovery: 243 passed.
