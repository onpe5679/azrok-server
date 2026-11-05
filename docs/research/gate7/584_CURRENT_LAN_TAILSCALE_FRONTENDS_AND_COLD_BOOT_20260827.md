# 584 — 최신 로컬/LAN/Tailscale 프런트엔드와 콜드 부팅 확인

> **PARTIALLY SUPERSEDED by 589.** 당시 NOT VERIFIED였던 모바일 종료 원인은 MagicDNS와 직접 자체서명 IPv4 `:9201`의 TLS hostname 충돌로 확인됐고, 동일 443 `/azrok-ws` 경로로 교체됐다.

## 판정

- **VERIFIED — 현재 서버 세대:** 코어는 현재 워킹트리의 `azrok_server.py`보다 뒤에 시작됐고 `127.0.0.1:9200/9300`에만 바인딩되어 있다. 홈페이지는 최신 `dynamicaccounts2_startersplash1` 앱을 선택한다. 해당 불변 앱은 157,274,502 bytes, SHA-256 `171CAD7371967E7FA35462957CD4A3AC4D1D471CF07E66333A1C1F0873205F61`이다.
- **VERIFIED — 불일치 한 건과 조치:** 기존 loopback WSS 브리지는 00:53에 시작되어 07:19 인증 모듈 수정 전 프로세스였다. 코어·저장 데이터는 유지한 채 `127.0.0.1:9201` 브리지만 현재 코드로 재시작했다.
- **VERIFIED — 제한된 바인딩:** HTTP/WSS 프런트엔드는 `127.0.0.1:8765/9201`, LAN `<lan-ip>:8765/9201`, Tailscale `<tailscale-ip>:8765/9201`에만 떠 있다. 코어/GUI는 계속 loopback-only `127.0.0.1:9200/9300`이며 wildcard/public listener는 없다.
- **VERIFIED — 세 경로의 인증 왕복:** loopback HTTP/WS, LAN HTTPS/WSS, Tailscale HTTPS/WSS에서 브라우저 티켓을 발급하고 원본 `C2S 0x0000` 로그인 + `0x0016` heartbeat를 보냈다. 세 경로 모두 코어에서 405-byte 첫 응답을 받았다. 외부 두 HTTPS 루트는 200, 157MB 앱의 1-byte Range 요청은 206이었다.
- **VERIFIED — 실제 LAN 브라우저 부팅:** `https://<lan-ip>:8765/`의 보존 홈페이지에서 게임 시작 → 서버 선택 → 접속 버튼을 실제로 눌렀다. `dynamicaccounts2_startersplash1`, `autorun=1`으로 실행되어 콜드 캐시에서 약 43.0초 뒤 첫 실제 D3D 렌더(한솔교육 화면)로 전환됐다. 코어에서 `player` 연결과 `0x0016` heartbeat가 49.3초 이상 유지됐고 즉시 종료는 재현되지 않았다.

## 콜드 부팅 비용

- 앱 ZIP: 149.99 MiB
- Wine filesystem root: 160.05 MiB
- 공통 JIT profile: 4.58 MiB
- 첫 브라우저/새 origin은 합계 약 314.62 MiB를 내려받고 압축 해제·Wine/JIT 준비를 해야 한다. 같은 브라우저와 origin의 후속 실행은 캐시를 재사용할 수 있지만, 다른 브라우저나 LAN/Tailscale처럼 origin이 바뀌면 별도 콜드 캐시다.

## 네트워크와 인증서

- Tailscale 서비스는 Running/Automatic이며 현재 IPv4는 `<tailscale-ip>`이다.
- LAN 8765/9201 Windows Firewall 규칙은 `<lan-ip>`, 원격 `<lan-ip>/24`, 정확한 Python 실행 파일에만 허용되어 있다.
- LAN 인증서는 `<lan-ip>`, Tailscale 인증서는 `<tailscale-ip>` SAN을 가지며 2028-10-30까지 유효하다.
- 이 호스트의 CurrentUser 저장소에는 LAN 사설 CA만 신뢰되어 있다. 다른 PC/휴대폰은 해당 경로의 CA를 직접 신뢰해야 하며, Tailscale 실제 원격 기기에서의 브라우저 부팅은 **NOT VERIFIED**다.

## 종료 증상 경계

- **VERIFIED:** 관측된 서버 쪽 연결은 정상 heartbeat 뒤 클라이언트 소켓이 닫힌 기록이며 강제 차단·티켓 거절·서버 예외는 없었다.
- **INFERRED:** 사용자가 본 장시간 로딩은 새 브라우저/origin의 314.62 MiB 콜드 부팅과 일치한다.
- **NOT VERIFIED:** 사용자 측 브라우저가 종료된 정확한 원인은 해당 브라우저의 WebSocket close code/콘솔 없이 특정할 수 없다. 최신 브리지 재시작 후 실제 LAN 시험에서는 즉시 종료가 재현되지 않았다.
