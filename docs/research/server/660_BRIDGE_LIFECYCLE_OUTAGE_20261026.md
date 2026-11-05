# 660 — 게임 접속 종료: WebSocket bridge 중지 누락 (2026-10-26)

## VERIFIED — 직접 확인

사용자 화면은 원본 게임의 “연결이 종료되었습니다.” 팝업입니다.
core/web는 active였지만 azrok-bridge는 inactive였습니다. 홈페이지와
`/api/private-server-status`는 정상 응답했으나 이것은 브리지 가동 증거가
아니었습니다. 최근 core 이벤트에도 새 게임 연결이 없었습니다.

브리지의 InactiveEnterTimestamp는 **2026-10-25 19:38:57 KST**입니다.
따라서 마지막 UI 개편 재시작에서만 발생했다고 단정할 수 없습니다.
당시 성장 복구 작업의 core stop/start 이후 브리지가 빠진 상태가 유지됐고,
후속 UI 배포에서도 core/web만 확인하여 이 누락을 발견하지 못했습니다.

`systemctl --user start azrok-bridge` 후 active를 확인했습니다.
공개 `wss://playazrok.com/azrok-ws`로 인증된 진단 로그인/heartbeat를
보내 응답405B와 opcode0016/0004/0000을 수신했습니다.
`PUBLIC_WSS_OK`는 단순HTTP 가동과 달리 공개 브리지→TCP core→응답 경로를
직접 확인합니다. 진단은 계정/캐릭터를 생성하거나 저장하지 않습니다.

## 수정

- core: `Wants=azrok-bridge.service azrok-web.service`.
- bridge/web: 기존Requires/After를 유지하고 `PartOf=azrok-core.service` 추가.
- 배포 문서에 세 서비스 active 및 공개WSS handshake 필수 확인을 추가.
- 서비스 파일 백업: `rollback/bridge-lifecycle-20261026/`.
- 게임 바이너리·사용자 저장 데이터 변경 없음.

PartOf의 명시적 stop/restart 전파 및 Wants의 기동 의존성은
[systemd 공식 문서](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html#PartOf=)에 정의돼 있습니다.
이를 실제 운영 재시작과 공개WSS 응답으로 별도 확인합니다.

## VERIFIED — 재발 방지 검증

daemon-reload와 systemd-analyze --user verify를 통과한 뒤 core만 restart했습니다.
별도 child start 명령 없이 core/bridge/web가 모두 active로 복귀했습니다.
실행된 core의 Wants/ConsistsOf에 두 서비스가 포함됐고, 재시작 뒤에도
PUBLIC_WSS_OK 405B / 0016,0004,0000 응답을 다시 확인했습니다.
