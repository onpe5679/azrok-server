# 580 — 계정별 안정 복구 코드, 금색 타이틀, 게임 프레임 정렬

날짜: 2026-08-27

## 복구 코드

- **VERIFIED:** `PrivateAccountRegistry` schema v3는 계정마다 `recovery_revision`만 저장합니다. 복구 코드는 private access secret에 `account_id`와 revision을 HMAC-SHA256하여 계산하므로 평문은 registry JSON에 저장되지 않습니다.
- **VERIFIED:** `export_recovery_code(browser_id, rotate=False)`를 연속 호출하면 같은 계정에서 같은 `azr1-...` 코드가 반환됩니다. 실제 8765 API도 비회전 요청 2회의 형식과 동일성을 확인했습니다. 코드 자체는 기록하지 않았습니다.
- **VERIFIED:** UI의 `복구 코드 표시`는 `rotate:false`로 조회만 합니다. 별도 `복구 코드 재생성` 버튼은 확인창 뒤 `rotate:true`를 보내며 그때만 revision을 증가시켜 이전 코드를 폐기합니다.
- **VERIFIED:** 현재 코드는 가져오기 후 소비되지 않으며 여러 새 브라우저를 같은 계정에 연결할 수 있습니다. 명시적 재생성 뒤에는 직전 코드가 거부됩니다.
- **VERIFIED:** v1/v2 registry는 시작 시 v3로 이행합니다. 이전 one-time digest는 새 안정 코드로 바뀌므로 구 코드가 계속 유효하다고 주장하지 않습니다.

## 메인 타이틀

- **VERIFIED:** `아즈로크 복원 프로젝트`를 밝은 금색 채움, 검정 다중 외곽선, 주황/갈색 하단 extrusion으로 바꿨습니다. 반투명 청록 명판은 제거했습니다.
- **VERIFIED:** 실제 브라우저 캡처에서 제목은 404×59px로 렌더링되고 배너 중앙에서 원본 로고와 분리되어 판독됩니다.

## 게임 화면 정렬

- **VERIFIED:** 기존 `left:-1px; top:-1px` 추정 보정은 제거했습니다.
- **VERIFIED:** 라이브 DOM 측정에서 source canvas와 D3D overlay는 모두 1024×768, 좌표 차이 `(0,0)`, 크기 차이 `(0,0)`였습니다.
- **VERIFIED:** 어긋남의 실제 원인은 전역 `box-sizing:border-box` 때문에 런타임이 `#dropzone`에 설정한 1024×768 안에서 7px 테두리가 콘텐츠를 잠식한 것입니다. 그 결과 화면이 오른쪽과 아래로 각각 7px 넘쳤습니다.
- **VERIFIED:** `#dropzone{box-sizing:content-box}` 적용 뒤 외곽 프레임은 1038×782가 되었고, 화면 기준 네 변 inset은 모두 정확히 7px였습니다. 실제 원본 클라이언트 화면과 FPS 출력도 다시 확인했습니다.

## 검증과 경계

- focused unit/contract tests: 62/62 통과. 전체 `tools/test_*.py`: 271/271 통과.
- **VERIFIED:** 8765 asset server와 9200/9300 core/control을 동일 access secret 인자로 재시작했습니다. 라이브 registry는 version 3, 계정 필드는 `created_at`, `legacy`, `recovery_revision`이며 `recovery_digest`는 없습니다. 재시작 뒤 원본 화면 FPS 185.5, source/overlay delta 0, 네 변 7px inset을 다시 확인했습니다.
- D3D9Web 렌더러, Wine/BoxedWine 바이너리, launcher와 app ZIP은 변경하지 않았습니다.
- 실계정 복구 코드는 검사 출력과 문서에 남기지 않았고, 라이브 검증에서는 회전 요청을 보내지 않았습니다.
