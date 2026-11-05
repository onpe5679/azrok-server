# 582 — 서버 NPC 우측 끝 배치와 실시간 접속 인원

날짜: 2026-08-27

## 변경

- **VERIFIED:** 꿀벌 NPC에 `margin-left:auto`를 적용해 서버 선택 헤더의 맨 오른쪽에 배치했습니다. 실제 720px 창에서 헤더 오른쪽 padding 22px을 남기고 정렬됩니다.
- **VERIFIED:** 8765에 읽기 전용 `GET /api/private-server-status`를 추가했습니다. 사설 네트워크 요청만 받고, 9300 `/api/overview`의 `server.players` 중 `connected is True`인 레코드만 집계합니다.
- **VERIFIED:** 서버 목록은 최초 로드 즉시, 이후 10초 간격으로 `현재 N명 접속`을 갱신합니다. 제어 서버가 응답하지 않거나 형식이 잘못되면 `접속 인원 확인 불가`로 표시합니다.

## 실측 및 테스트

- **VERIFIED:** 라이브 8765 API 응답은 `ok=true`, 정수형 `online=0`이었습니다.
- **VERIFIED:** 실제 브라우저에서 `· 현재 0명 접속` 표시와 NPC 우측 여백 22px을 확인했습니다.
- **VERIFIED:** focused 24/24, 전체 `tools/test_*.py` 271/271 통과했습니다.

## 경계

- 접속 인원은 등록 계정 수나 누적 방문자가 아니라 현재 core가 `connected`로 보고하는 원본 클라이언트 수입니다.
- 9200/9300 core, 계정/티켓 정책, BoxedWine/D3D9Web 런타임은 변경하지 않았습니다.
