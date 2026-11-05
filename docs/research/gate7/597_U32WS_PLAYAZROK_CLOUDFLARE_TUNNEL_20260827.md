# 597 — u32ws playazrok.com Cloudflare Tunnel 배포 (2026-08-27)

## 범위

현행 Windows 보존 서버를 삭제하거나 교체하지 않고, Tailscale 장치
`u32ws` (`<tailscale-ip>`, Ubuntu)에 별도 운영본을 배치했다. 공개 진입점은
`https://playazrok.com`, 내부 원본은 모두 loopback으로 유지했다.

## VERIFIED — 서버 배치

- 배치 루트: `/home/u32ws/32dev/azroksrv` (`X:\home\u32ws\32dev\azroksrv`).
- user systemd + linger로 다음 네 서비스가 모두 `active`이다.
  - `azrok-core`: `127.0.0.1:9200`, control `127.0.0.1:9300`
  - `azrok-web`: `127.0.0.1:8765`
  - `azrok-bridge`: `127.0.0.1:9201`
  - `azrok-cloudflared`: outbound QUIC tunnel
- `cloudflared` 2026.8.2가 사용자 소유 `bin/`에 설치됐으며 인바운드 방화벽
  포트는 열지 않았다.
- 동기화 도구 `deploy/u32ws/sync_to_u32ws.ps1`는 운영에 필요한 immutable
  app/root/JIT와 웹 자산만 전송한다. 최초 `-InitializeState` 이후에는 계정
  registry, 복구 비밀, 캐릭터 상태를 덮어쓰지 않는다. 같은 해시의 큰 ZIP도
  다시 전송하지 않는다.

## VERIFIED — Linux 코어 경계

첫 Linux import는 `azrok_server.py`가 선택적인 Windows 네이티브 클라이언트
도우미용 `ctypes.windll`을 모듈 import 때 무조건 초기화해 실패했다. `os.name ==
'nt'`에서만 `kernel32/user32` handle을 만들도록 가드했다. 프로토콜, 패킷,
콘텐츠 서버 경로는 변경하지 않았다. 수정 뒤 Linux 실제 프로세스가 9200/9300에
리슨하고 `/api/private-server-status`가 HTTP 200을 반환했다.

## VERIFIED — Cloudflare와 공개 경로

- tunnel name: `playazrok`
- tunnel ID: `<cloudflare-tunnel-id>`
- DNS: apex `playazrok.com` CNAME → 위 tunnel, proxied/automatic TTL
- ingress rule 0: `playazrok.com` + `^/azrok-ws$` → `http://127.0.0.1:9201`
- ingress rule 1: 나머지 `playazrok.com` → `http://127.0.0.1:8765`
- 네 개 ICN01/ICN06 QUIC connector와 Cloudflare connectivity precheck가 PASS했다.

서버의 기존 `<other-domain>` 단일-zone origin certificate로 CLI DNS route를 처음
시도했을 때 `playazrok.com.<other-domain>`가 생성됐다. Cloudflare 대시보드에서 그
레코드를 삭제하고, `playazrok.com` zone에 올바른 apex CNAME을 생성했다.
공용 1.1.1.1 조회는 `104.21.35.220`, `172.67.180.59`를 반환한다.

## VERIFIED — 외부 수용 시험

- HTTPS `/`: 200, 홈페이지 97,817 bytes, COOP/COEP/CORP 보존.
- `/api/private-server-status`: 200, valid JSON.
- immutable app Range `0-1023`: 206, 정확한 `Content-Range
  bytes 0-1023/157274401`, `Accept-Ranges`, immutable cache header.
- 공개 `wss://playazrok.com/azrok-ws`에 5분 서명 ticket과 원본 형식
  C2S `0x0000` 로그인/`0x0016` heartbeat를 보냈다. bridge가 loopback 9200
  코어로 연결했고 405-byte S2C `0x0016`, `0x0004`, `0x0000`을 반환했다.
- 로컬 전체 도구 suite: **292 tests PASS**.

## NOT VERIFIED / 운영 선택

- 배포 직전 로컬 재귀 DNS가 기존 NXDOMAIN을 캐시해 Chrome/인앱 브라우저의
  픽셀 수용 시험은 즉시 수행하지 못했다. 공용 DNS, HTTPS, WSS/TCP는 직접
  검증됐으며 로컬 DNS cache 만료 뒤 시각 수용을 별도로 수행한다.
- Cloudflare Access는 아직 켜지 않았다. 현재 도메인은 공개 상태이고 접속
  계정은 브라우저별로 자동 발급된다. 공개 범위를 어떻게 둘지는 사용자 운영
  정책 결정이 필요하다. (운영 세부는 공개본에서 뺐다)

