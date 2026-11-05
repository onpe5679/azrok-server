# Azrok Plaza — Reverse Engineering 문서

**현재 확정 사실은 [`INDEX.md`](INDEX.md) 를 볼 것.** 새 조사 전 INDEX 부터 확인해 중복 조사를 피한다.

## 폴더 구조

| 위치 | 내용 |
|---|---|
| `INDEX.md` | **확정 사실 지도 — 무엇이 사실인가** (여기부터) |
| `REGISTRY.md` | **전체 문서 등기부 — 무엇이 어디 있나** (518건, 번호·제목·경로) |
| `00_current_status.md` | 2026-07-18 스냅샷 — **낡음. 현재 상태는 `INDEX.md` §1** |
| `gate1/` `gate2/` `gate5/` `gate6/` `gate7/` | 게이트별 조사 — `gate6/` 는 `perf` / `audio` / `mobile` 로 나뉜다 |
| `webport/` | D3D9→WebGL2 이식 설계·단계 |
| `server/` | 서버 구현·GUI·프로토콜 레지스트리·저널 |
| `protocol/` | opcode·프로토콜 계약 |
| `world/` | Plaza·씬·진화·로컬룸·외출 |
| `multiplayer/` | 로스터·이름·이탈·디스패치 owner |
| `content/` | 스탯·데이터·퀘스트·인벤토리·경제·OX·요리 |
| `tooling/` | frida·x32dbg·엔진 참조·런처·캡처 매니페스트 |
| `archive/` | 낡은/대체된 문서 — 참조용 보존, 삭제 안 함 |

문서 번호는 폴더와 무관하게 고유하다. 문서끼리는 "note NN" 번호로 참조한다.
폴더별 정확한 건수와 파일 목록은 `REGISTRY.md` 첫 표를 볼 것 (2026-07-29 기준 518건).

## 문서 작성·갱신 규칙

`AGENTS.md` 의 `## 문서 규칙` 참조:
- 새 조사 전 INDEX 확인 (중복 방지)
- 새 문서 번호는 INDEX 의 다음 빈 번호 (세션 간 충돌 방지)
- 기존 결론을 뒤집으면 낡은 문서에 `SUPERSEDED by NN` 배너 + `archive/` 이동 (삭제 금지)
- VERIFIED / INFERRED / NOT VERIFIED 구분
- 확정 사실이 바뀌면 즉시 INDEX 갱신

## 알려진 정리 대기 (번호 충돌, 물리 리네임 보류)

전수 검사 결과 충돌은 6건이다. 물리 리네임은 링크 영향 때문에 보류하며, 구분은 `INDEX.md` §4 에서 관리한다:
`32`(world 내부) · `45`(archive/multiplayer) · `57`(content 내부) · `58`(content 내부) · `70`(content/world) · `458`(0바이트 중복본은 archive 로 이동 완료)
