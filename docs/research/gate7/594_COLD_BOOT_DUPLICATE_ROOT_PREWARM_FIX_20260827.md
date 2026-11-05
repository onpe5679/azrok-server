# 594. Cold boot duplicate-root prewarm fix (2026-08-27)

## Scope

새 브라우저/origin의 첫 실행이 비정상적으로 오래 걸리는 현재 배포 경로를 다시 감사하고,
서버 선택 화면의 선행 캐시와 실제 BoxedWine 실행 페이지가 동일한 불변 자산을 사용하게 한다.

## VERIFIED — 회귀 원인

- `index_d3d9web_pathouse.html`의 현재 기본 root는
  `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim25koreanlocale2`
  이며 ZIP 실물은 167,825,891 B이다.
- 수정 전 `azrok_launch.js`는 위 root가 아니라
  `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1` ZIP 167,172,869 B를
  Cache Storage에 미리 넣고 있었다. 실행 페이지는 이 파일을 사용하지 않으므로 빈 origin에서는
  앱 157,274,502 B + 잘못된 root 167,172,869 B + 실제 root 167,825,891 B + JIT
  4,804,035 B의 최대 497,077,297 B(474.05 MiB) 경로가 된다.
- 이는 #586의 설계 결론이 틀린 것이 아니라 이후 `azrok_launch.js`가 구 root로 회귀한 것이다.

## VERIFIED — 수정

- 앱, root, runtime stem을 각각 단일 상수로 고정했다. 서버 선택 화면의 선행 캐시와 생성되는
  실행 URL이 같은 앱과 `xim25koreanlocale2` root를 사용한다.
- 실행 URL에 `root=...xim25koreanlocale2`와
  `runtimeStem=boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch1`을 명시해 실행 페이지의
  기본값이 앞으로 변해도 선행 캐시와 실행 자산이 조용히 갈라지지 않게 했다.
- 앱/root/JIT 선행 캐시는 순차 `for/await` 대신 `Promise.all`로 준비한다. HTTP 프런트는
  `ThreadingHTTPServer`이므로 세 독립 요청을 동시에 처리할 수 있다.
- 수정 후 첫 origin의 필수 archive 합계는 329,904,428 B(314.62 MiB)이며, 잘못된 root
  167,172,869 B(159.43 MiB, 종전 최대 경로의 약 33.6%)를 제거한다.
- 캐시가 강한 `azrok_launch.js`의 쿼리 버전을 `restore4`로 올렸다.

## VERIFIED — 실제 전달과 회귀 검사

- 전용 빈 origin에서 2026-08-27 12:53:00에 `restore4` 스크립트와 앱/root/JIT 세 요청이
  같은 초에 시작됐다. 요청된 root는 정확히 `xim25koreanlocale2`였고 구 root 요청은 없었다.
- 이어 발급된 실행 URL에는 새 앱, 정확한 root, `korean6chat1touch1` runtime stem이 모두
  명시됐다. 실행 페이지 단계에서는 앱/root의 잘못된 두 번째 경로가 관측되지 않았다.
- 8765 HEAD 실측에서 서버 목록 HTML은 `no-store`, `restore4` JS와 root ZIP은
  `public, max-age=31536000, immutable`; root `Content-Length`는 167,825,891 B였다.
- `node --check tools/boxedwine_local/azrok_launch.js`와 전체 `tools/test_*.py` 288개가 통과했다.

## NOT VERIFIED / remaining boundary

- 수정 후 완전히 새 물리 브라우저에서 서버 선택 클릭부터 첫 실제 D3D draw까지의 최종 시간은
  아직 재측정하지 않았다. 기존 origin의 캐시를 지우는 파괴적 검증은 수행하지 않았다.
- 이번 수정은 불필요한 159.43 MiB 수신과 순차 대기를 제거한다. 남은 314.62 MiB 최초 수신,
  약 540 MiB raw 앱 해제, 약 619 MiB raw root 해제, grouped JIT replay, Wine/Acknex 초기화는
  계속 필요하다. 이 잔여 시간을 더 줄이려면 검증된 slim app/root 또는 추출 파일시스템 영속화가
  별도 단계로 필요하다.
- 이미 열려 있던 과거 `dynamicaccounts2` 실행 URL은 불변 URL 자체가 자동 교체되지 않는다.
  서버 선택 화면에서 새로 접속해야 `startersplash1 + xim25 + korean6chat1touch1` 조합을 받는다.
