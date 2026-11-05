# 581 — 서버 선택 헤더 제목/NPC 순서 교체

날짜: 2026-08-27

## 변경 및 확인

- **VERIFIED:** `azrok_server_list.html` 헤더의 DOM 순서를 아즈로크 로고 → 제목/안내문 → 꿀벌 NPC로 변경했습니다.
- **VERIFIED:** NPC의 기존 오른쪽 여백을 제거하고 제목과 NPC 사이 왼쪽 여백 18px을 적용했습니다.
- **VERIFIED:** 실제 브라우저에서 자식 순서가 `server-logo-image`, `DIV`, `server-npc-image`임을 확인하고 화면 캡처로 배치를 확인했습니다.
- **VERIFIED:** 홈페이지 contract test 10/10 통과.

## 경계

- 서버 선택 동작, 계정/티켓 API, BoxedWine 및 D3D9Web 런타임은 변경하지 않았습니다.
