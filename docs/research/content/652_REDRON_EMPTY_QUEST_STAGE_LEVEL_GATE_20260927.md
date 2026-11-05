# 652 — 레드론 직후 빈 퀘스트 창: 성장 레벨 게이트와 일반 퀘스트 주기 (2026-09-27)

## 결론

- **VERIFIED (원본 디컴파일):** 진화 직후 레벨 3에서는 다음 성장 퀘스트(kind 3)가 곧바로 발행되지 않습니다. `FUN_005A7C90`은 진화 단계 1에서 레벨이 **10 이상**일 때만 aux 1·2·3 중 하나를 무작위 선택하고, 이미 kind 3 행이 있으면 발행하지 않습니다. 이 함수의 반환값은 `FUN_005A6300(1, ...)`을 통해 kind 3 행으로 등록됩니다.
- **VERIFIED (원본 디컴파일):** 매 게임 루프에서 호출되는 `FUN_005A6580`은 빈 성장 경로일 때 일반 퀘스트를 별도로 시도합니다. 진화 단계가 0이 아니고 `currentPackedDate >= logic+0x7FC`인 경우 다음 날짜를 `PackedDate_AddDeltaWithCarry(current, 200)`으로 기록한 뒤 `rand()%100 < 0x3D`(61%)이면 `FUN_005A6300(0, ...)`으로 kind 0·1·2 후보를 만듭니다. 그 외에는 이번 틱에서 행을 만들지 않습니다. 날짜 `200`의 실제 시간 단위와 브라우저 런타임 주기 수용은 **NOT VERIFIED**입니다.
- **VERIFIED (운영 저장/수신):** 2026-09-27의 서로 다른 두 테스트 캐릭터는 모두 stage 1, level 3, kind 3 aux 0 완료 이력 1건, 활성 퀘스트 0행이었습니다(저장 시각 03:46:09 및 03:54:53 KST). 최신 세션에서 `0010[00,01] → 0011` 행 제거 → `0007` stage 1 저장은 수락됐고, 그 뒤 구역 이탈 전 다음 성장 제안 `0010[aux,00]`은 없었습니다. **레벨 3이므로 이 부재는 원본 성장 게이트와 일치합니다.** 계정명·원본 snapshot 내용은 이 문서에 기록하지 않습니다.
- **INFERRED:** 사용자께서 본 진화 직후의 빈 퀘스트 창은 이 단계에서 가능한 정상적인 일시 상태입니다. 이후 일반 퀘스트가 언제 뜨는지, 영구적으로 빈 상태가 되는지는 별도 실제 플레이 관찰이 필요합니다. 서버가 임의로 aux 1을 즉시 발행하면 원본의 레벨 게이트와 무작위 분기 모두 깨집니다.

## 이전 aux 2·3 제안 표본과의 차이

- **VERIFIED (기존 실측 로그):** `artifacts/boxedwine/20260719_gate2b_native/server_9200_wine10_stdout.log`에는 stage 0→1 저장 뒤 클라이언트 `0010[02,00] → 0011[kind3/aux2]`가 있습니다. `server_9200_hoststack_full_stdout.log`에는 같은 순서로 aux 3이 있습니다. 두 표본의 성장 직전 snapshot은 level 25, 성장 직후 level 26으로 출력되어 `FUN_005A7C90`의 stage 1 level≥10 게이트를 충족합니다. aux 2와 aux 3이 갈라지므로 기존 서버 설정의 고정 aux 1을 원본의 결정적 선택으로 볼 수 없습니다.
- **VERIFIED (출처 구분):** #547의 “원본 클라이언트가 다음 aux를 제안한다”는 표본은 실제 클라이언트 wire에 근거합니다. 다만 높은 레벨로 시작한 구형 프로필의 조건에서 관측된 것이며, level 3 신규 캐릭터에 무조건 적용된다는 결론은 성립하지 않습니다.
- **VERIFIED (원본 디컴파일):** `FUN_005A8070`은 활성 kind 3 첫 행을 **읽어 완료 조건만** 검사합니다. `FUN_005A7E40`은 stage를 올리고 생리/스탯을 조정하지만 다음 퀘스트 행을 만들지 않습니다. 실제 발행 경로는 `FUN_005A6300`이며, 성장 후보 `FUN_005A7C90`의 레벨 게이트를 통과해야 합니다.

## 서버 경계와 조치

- **VERIFIED (코드/집중 테스트):** 서버는 성장 완료를 원자 저장한 뒤 클라이언트의 선택적 다음 `0010/0011`을 받을 수 있습니다. 레벨 3에서 이를 받지 않은 상태는 퀘스트 10행이 FF인 채 유지됩니다. 이 동작만으로 서버 결함을 확정할 수 없습니다.
- **VERIFIED (변경 상태):** 조사 중 만들었던 구역 진입 시 kind3/aux1 자동 발행안은 근거 부족으로 전부 되돌렸고 운영에 배포하지 않았습니다. 현재 코드 변경은 없습니다.
- **NOT VERIFIED:** 일반 퀘스트의 실제 첫 발행 시각과 `logic+0x7FC` 날짜 초기화/복원, RNG 표본, GUI에 행이 표시되는 시점. 원본 클라이언트 동적 계측과 운영 패킷·UI 동시 캡처로 확인해야 합니다. 현재 Ghidra MCP GUI 인스턴스와 x32dbg 연결은 없어 기존 분석 프로젝트의 headless 디컴파일 및 운영 수신/저장 실측을 결합했습니다.

## 재현 근거와 검증

- Ghidra headless 기존 분석 프로젝트 `/Azrok_analyzed.exe`에서 `DecompileAddresses.java`로 `005A6580`, `005A6300`, `005A7C90`, `005A8070`, `005A7E40`, `005A7F30`, `005AA680`의 함수 본문을 직접 확인했습니다. `QuestIssueXrefs.java`는 `FUN_005A6580`의 호출자 `FUN_00561050`(메인 루프)과 발행기 `FUN_005A6300`의 호출 위치를 확인했습니다. `Data/Interface/Quest`는 UI 이미지(.tga)만 포함하며 퀘스트 발행 규칙 파일은 확인되지 않았습니다.
- 운영 canonical 두 건은 원본을 수정하지 않고 읽기만 했습니다. 각 문서는 revision 24, stage 1, level 3, `g1:r0:k3:a0:e1` 완료, 활성 행 0개였습니다. 둘째 세션의 control event ring에는 `growth_route_edge aux=0 completion_candidate`, `runtime_row_snapshot pending_0007`, `runtime_row_complete`가 차례로 기록됐습니다. 이어 구역 이탈까지 다음 `growth_route_edge proposal`이 없었습니다.
- 집중 회귀: `python -m unittest tools.test_server_contract_layers.CanonicalStateContractTests.test_natural_growth_order_buffers_removal_then_accepts_client_next_route tools.test_server_contract_layers.CanonicalStateContractTests.test_kind3_row_retires_once_on_proven_evolution_edge_without_currency -q` → 2 tests OK. 합성 aux 2 제안 테스트는 높은 레벨 실측을 검증하는 계약이며, level 3 신규 사용자의 발행을 예측하지 않습니다.

## 남은 직접 확인

1. stage 1 level 3 상태에서 `logic+0x7FC`와 packed date를 x32dbg로 계측하고, 일반 퀘스트가 실제 `0010/0011`과 GUI에 언제 등록되는지 확인합니다.
2. level 10 도달 시 `FUN_005A7C90` 진입과 aux 1..3 제안을 기록합니다. 고정 aux를 서버에서 먼저 발행하지 않습니다.
3. 만약 충분한 날짜/플레이 틱 이후에도 일반 퀘스트가 영구히 비면 그때 호출/저장 누락을 별도 결함으로 조사합니다.

관련: #106(튜토리얼 단계 0), #123(0010/0011 wire), #547(고레벨 성장 표본), #602(자연 표본 경계), #87(호환 aux 기본값은 INFERRED).
