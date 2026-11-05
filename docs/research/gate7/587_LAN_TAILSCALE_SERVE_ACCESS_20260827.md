# 587 — LAN/Tailscale HTTPS·WSS 접속 경로

> **PARTIALLY SUPERSEDED by 589.** Tailscale의 별도 `:9201` WSS는 IPv4 직접 자체서명 리스너와 충돌했다. 현재 신뢰 경로는 동일 TLS 443의 `/azrok-ws`이다.

날짜: 2026-08-27

## 결론

- **VERIFIED:** LAN `<lan-ip>`와 Tailscale IP `<tailscale-ip>`에 HTTP 8765 및 WSS 9201 전용 프로세스가 리슨한다.
- **VERIFIED:** 두 IP의 홈페이지는 HTTPS 200을 반환하고, 9201은 WebSocket Upgrade에 `101 Switching Protocols`를 반환한다. 인증 없는 시험 요청은 의도대로 private browser admission 오류로 종료된다.
- **VERIFIED:** Tailscale Serve를 `443 -> http://127.0.0.1:8765`, `9201 -> http://127.0.0.1:9201`로 구성했다.
- **VERIFIED:** `https://<tailnet-host>/`은 200, `wss://<tailnet-host>:9201`은 101을 반환했다.

## 사용자 접속 주소

- 같은 로컬망: `https://<lan-ip>:8765/`
- 같은 Tailnet: `https://<tailnet-host>/`

LAN IP 주소는 자체 인증서 경고가 생길 수 있다. MagicDNS Serve 주소는 Tailscale이 제공하는 HTTPS 경로다.

## 운영 경계

- **VERIFIED:** 기존 활성 게임 세션을 끊지 않고 웹 프런트엔드만 최신 코드로 교체했다.
- **VERIFIED:** Windows 방화벽의 새 Tailscale 전용 규칙 추가는 현재 비관리자 셸에서 거부됐다. Tailscale Serve 경로는 별도 관리자 작업 없이 활성화됐다.
