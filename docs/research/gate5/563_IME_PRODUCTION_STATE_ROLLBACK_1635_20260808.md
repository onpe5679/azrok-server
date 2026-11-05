# 563. IME production-state rollback to 16:35 (2026-08-08)

## Scope

사용자 요청에 따라 2026-08-08 16:35 이후의 active-preedit 실험을 운영 페이지에서 제거하고, 그 시각에 직접 수락됐던 한글 입력 조합으로 복구합니다.

## VERIFIED

- 첫 cutoff 이후 runtime 산출물 korean7의 파일 시각은 16:47:19이며 korean8은 17:22:19입니다.
- cutoff 이전 수락 조합은 `korean6chat1 + xim25koreanlocale2 + guestprofiles6_rsdefaults1_utf8ime2`입니다.
- #558에서 원본 이름 Edit의 `한글별` 표시와 확인 후 다음 화면 진입이 직접 수락됐습니다.
- 페이지에서 post-cutoff `compositionupdate`, committed-preedit replacement, XIM preedit callback 분기와 korean7/korean8 build routing을 제거했습니다.
- 페이지 입력은 다시 `compositionstart` 동안 보류하고 `compositionend`에서 기존 `send(e.data, true)`만 호출합니다.
- focused 41 tests와 full 248 tests가 통과했습니다.
- live 탭에서 korean6 immutable runtime, JIT 94 groups/30550 blocks, 새 콘솔 오류 0건을 확인했습니다.

## Preservation

- 실패한 korean7/korean8 runtime과 xim30/xim31 root 파일은 삭제하지 않았습니다. 운영 라우팅에서만 제외했으며 기존 archive 문서로 실패 이유를 보존합니다.
- 재도입 방지 대장은 `docs/research/FAILED_EXPERIMENTS.md`입니다. INDEX 상단에서 바로 연결하고, page contract test가 post-16:35 handler 문자열의 부재를 강제합니다.

## NOT VERIFIED

- 이번 재부팅 뒤 사용자가 다시 수행하는 물리 한글 입력. 16:35 이전 수락 증거는 #558에 보존되어 있습니다.
