# 553. Wine XIM UTF-8 Unix-locale app A/B (2026-08-08)

## Scope

#552에서 browser commit, synthetic X11, fake XIC, `XmbLookupString`, `XLookupChars` status 2와 UTF-8 6 bytes가 모두 통과했지만 Azrok Edit에는 한글이 나타나지 않았다. Wine 11 원본 소스와 현재 root의 locale payload를 직접 대조하고, 원본 게임/서버/root/runtime/page를 유지한 채 player2~6 launcher의 Unix locale만 바꾸는 immutable app A/B를 만든다.

## VERIFIED — Wine 11 변환 계약

- `dlls/winex11.drv/xim.c::xim_set_result_string()`은 XIM byte를 `ntdll_umbstowcs(str, count, ...)`로 UTF-16 변환한다. `XLocaleOfIM()` 반환 문자열은 이 변환의 codepage 선택에 사용되지 않는다.
- `dlls/ntdll/unix/env.c`의 `unix_cp` 초기값은 `CP_UTF8`이다.
- 초기화는 `setlocale(LC_CTYPE, "")` 뒤 `nl_langinfo(CODESET)`을 읽는다.
- C locale codeset `ANSI_X3.4-1968`은 table에서 codepage 20127로 매핑되며, `c_20127.nls`를 읽으면 `unix_cp`가 ASCII로 바뀐다.
- `ntdll_umbstowcs()`는 `unix_cp != CP_UTF8`이면 그 NLS table의 `cp_mbstowcs()`를 사용한다.

## VERIFIED — 현재 root와 launcher의 불일치

- xim1 root에는 `usr/lib/locale/locale-archive`가 없다.
- `ko_KR/LC_CTYPE` locale object도 없다.
- `opt/wine/share/wine/nls/c_20127.nls`와 `c_949.nls`는 모두 있다.
- 기존 private guest launcher player2~6은 `LANG=ko_KR.EUC-KR`, `LC_ALL=ko_KR.EUC-KR`을 강제한다.
- glibc는 2.38 계열이며 libc 안에 UTF-8 gconv 경로가 있다.

## INFERRED — 현재 실패 원인

존재하지 않는 `ko_KR.EUC-KR`에서 `setlocale()`이 실패하고 C locale이 유지되면 Wine은 `ANSI_X3.4-1968`→20127 NLS를 선택한다. 그 상태에서 fake-XIM의 UTF-8 `한글` 6 bytes를 ASCII converter에 넣으므로 결과 문자열이 유실되는 것이 현재 증상과 일치한다. 이 귀속은 새 launcher의 `WINEUNIXCP` 출력 및 Edit 수용 A/B 전까지 INFERRED다.

## VERIFIED — immutable UTF-8 app candidate

- source: `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1.zip`
- candidate stem: `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime1`
- candidate: 157,274,051 bytes
- SHA-256: `3B5C69FAC8916DC610B57AE341E1A27756E4CA08D1AA6335CC36584FCBAF8DAD`
- 4,268 entry의 이름·순서·ZIP metadata가 source와 동일하다.
- content diff는 다음 5개뿐이다.
  - `run_azrok_multi2.bat`
  - `run_azrok_player3.bat`
  - `run_azrok_player4.bat`
  - `run_azrok_player5.bat`
  - `run_azrok_player6.bat`
- 각 launcher에서 `LANG/LC_ALL`만 `C.UTF-8`로 바꾸고 `D3D9WEB_WINEUNIXCP=%WINEUNIXCP%` 한 줄을 출력한다.
- 원본 EXE, 게임 data, D3D9 payload, peer111/player launcher, root, runtime, server protocol, page는 바꾸지 않았다.
- LAN `<lan-ip>:8765`와 Tailscale `<tailscale-ip>:8765`가 동일 길이·해시를 제공했다.
- focused contract tests 19/19 pass.

## Live A/B 판정

기존 korean5 IME debug runtime과 candidate app을 조합해 player5 Plaza에서 같은 `한글` commit을 반복한다.

- `D3D9WEB_WINEUNIXCP=`가 빈 값이고 Edit에 한글이 들어가면 UTF-8 unix_cp와 원인이 함께 확정된다.
- `D3D9WEB_WINEUNIXCP=20127`이면 `C.UTF-8` locale 선택 자체가 실패한 것이다.
- unix_cp가 UTF-8인데 Edit가 여전히 비면 손실은 `post_ime_update()` 이후 Azrok/IME context 수용으로 내려간다.

## NOT VERIFIED

- candidate app의 실제 `WINEUNIXCP` 출력값.
- candidate app에서 Plaza Edit 한글 수용과 C2S chat byte.
- 성공 전에는 candidate를 production 기본값으로 승격하지 않는다.
