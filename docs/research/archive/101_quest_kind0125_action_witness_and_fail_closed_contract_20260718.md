> **SUPERSEDED by 126.** 자연 C2S0012와 인접 C2S0011이 kind0 완료·FunCorn 지급의 server-visible evidence임이 실측되어, 이 문서의 no-signal/fail-closed 핵심 결론은 폐기되었습니다. 정적 reward 표와 과거 판단 근거만 보존합니다.

# 101 — 퀘스트 kind 0/1/2/5 action witness와 fail-closed 서버 계약

> **PARTIALLY SUPERSEDED by 123.** base `CLogicManager` vtable `+0x18` no-op 자체는 맞지만 실제 파생 `CJSLogic`은 이를 C→S0011 80B sender로 override합니다. 따라서 “runtime-row export wire 없음” 일반화는 폐기합니다. kind0/1/2/5 보상 provenance 부족과 fail-closed 정책은 유지됩니다.

날짜: 2026-07-18  
대상: 정당하게 취득한 종료 게임 클라이언트 `Azrok_original.exe`의 상호운용성 복원  
방법: 기존 INDEX/78/83/84/86/87/98~100 검토 후 Ghidra 분석 프로젝트를 headless read-only로 열어 평가기·생산자·콜백 xref와 디컴파일 본문 전수 확인

## 1. 결론

- **VERIFIED:** 퀘스트 완료 평가기 `FUN_005A6910`의 실제 진입자는 일반 액션 `FUN_00596690`, 그 내부 action 분류기 `FUN_005A67A0`, 미니게임 보상기 `FUN_005A1B90`뿐입니다. 별도 universal C→S 완료 sender는 없습니다.
- **VERIFIED:** kind 0/1/2/5는 각각 로컬 action/item/stat을 근거로 행을 제거하지만, action id와 제거된 10행 테이블은 C→S wire에 실리지 않습니다.
- **VERIFIED / CORRECTED by 123:** base `CLogicManager`의 `+0x18/+0x20/+0x28`은 no-op이지만 실제 파생 `CJSLogic +0x18`은 C→S0011 sender입니다. 콘/일반 callback no-op과 kind0/1/2/5 provenance 부족은 유지됩니다.
- **VERIFIED:** C→S `0007`에서 관측 가능한 것은 최종 stat/stage/mode-date뿐입니다. kind0/2의 stat7, kind1의 skill stat, kind5의 stat2는 퀘스트 외 로컬 경로도 바꾸므로 완료 provenance가 아닙니다.
- **서버 계약:** 자동 retire 가능한 kind는 **3 하나뿐**입니다. kind0/1/2/5는 표시·복원은 하되 retire/콘 지급은 0건으로 fail-closed합니다. 모든 `0007` 수신에 보상하는 방식은 금지합니다.

| kind | 실제 의미 / 로컬 witness | C→S에서 보이는 결과 | 서버 판정 |
|---:|---|---|---|
| 0 | 음식 갈망. action `D4/DB`와 exact food id | stat7 최종값뿐 | **fail-closed** |
| 1 | 미니게임·훈련. resolved skill stat `31..62` | 해당 skill stat 최종값뿐 | **fail-closed** |
| 2 | 급식·운동·요리/행동. action 또는 food id | stat7 최종값뿐 | **fail-closed** |
| 3 | 성장 조건 충족 후 진화 stage commit | exact stage edge + branch threshold stats | **자동 retire, 콘 0** |
| 5 | stage0 튜토리얼 action chain | stat2(EXP) 최종값뿐 | **fail-closed** |

## 2. 평가기 실제 producer 전수

`FUN_005A6910`의 thunk `004D7A50` 실제 call site는 다음뿐입니다.

| call site | caller | 의미 |
|---|---|---|
| `00596E7E` | `FUN_00596690` | 매 일반 액션 뒤 kind3 성장 평가 |
| `005A67D3/6822/6841/6861/6880` | `FUN_005A67A0` | stage와 action code에 따라 kind0/2/5 평가 |
| `005A20C1` | `FUN_005A1B90` | domain1..4 미니게임 뒤 kind1 평가 |

평가기 본문은 앞에서부터 10행을 스캔해 일치 행 하나만 처리합니다. kind0/1/2/3은 보상 함수 뒤 `FUN_005A6160(...,2)`와 `FUN_005A5EC0(row)`을 호출하고 즉시 반환합니다. kind5는 자체 함수가 같은 제거와 다음 튜토리얼 행 발행까지 담당합니다. 이 경로 안에는 network builder/sender 호출이 없습니다.

## 3. kind별 정확한 클라이언트 동작

### kind0 — 음식 갈망

`FUN_005A67A0`은 진화 stage가 0이 아닐 때 action `0xD4/0xDB`의 `param_4` item id로 `QuestEval(kind=0,item_id)`을 호출합니다. aux exact match 뒤 `FUN_005A6CE0`이 food `1001..1028`의 정의된 부분집합에 대해 stat7을 `-10..-30` 변경하고 콘 `38..48`을 vtable `+0x20`에 넘깁니다.

- **VERIFIED:** action code와 item id는 평가 순간 로컬 인자입니다.
- **VERIFIED:** C→S `0007`에는 stat7 결과만 있고 action/item id와 제거행은 없습니다.
- **VERIFIED:** 콘 callback은 no-op입니다.
- **판정:** 동일 stat7을 다른 케어/action도 바꾸며, 클라이언트 소비 인벤토리도 C→S `0007`에 없습니다. stat7 감소나 서버 canonical 보유량만으로 완료를 증명할 수 없습니다.

### kind1 — 미니게임·훈련

`FUN_005A1B90`은 domain `1..4`의 로컬 보상을 적용한 뒤 리매퍼가 고른 skill stat으로 `QuestEval(kind=1,resolved_stat)`을 호출합니다. aux exact match 뒤 `FUN_005A7240`이 stat31..39에 `+16`, stat40..44에 `+15`, stat49..53에 `+17`, stat58..62에 `+19`를 시도하고 콘 `19..24`를 no-op callback에 넘깁니다.

- **VERIFIED:** 같은 `FUN_005A1B90`이 퀘스트 전 기본 미니게임 보상도 같은 stat에 먼저 씁니다.
- **VERIFIED:** C→S `0007`은 둘이 합쳐진/clamp된 최종 stat만 보냅니다.
- **판정:** delta 크기는 기본 보상·티어·상한·봉에너지 gate와 섞이므로 어떤 크기도 완료 provenance가 아닙니다.

### kind2 — 급식·운동·행동

진화 stage가 0이 아닐 때 `FUN_005A67A0`의 분기는 다음과 같습니다.

- action `CF`, `DC..E2` → action 자체를 aux 후보로 사용
- action `D1` → `param_4` item/food id를 aux 후보로 사용
- action `E4..EC` → `FUN_005A78C0`에서 공통 aux `0x102`로 정규화

일치하면 `FUN_005A7910`이 stat7을 `-10/-13/-17/-20` 변경하고, 정의된 food aux에는 콘 `24/29/35`를 no-op callback에 넘깁니다.

- **VERIFIED:** action/food aux는 로컬 함수 인자일 뿐 C→S `0007` 필드가 아닙니다.
- **판정:** kind0과 같은 stat7 결과만 보이며 원인 action을 구분할 수 없으므로 fail-closed입니다.

### kind5 — stage0 튜토리얼 체인

진화 stage가 0이면 `FUN_005A67A0`은 일반 action code를 `QuestEval(kind=5,action)`에 넘깁니다. `FUN_005A8790`은 현재 kind5 aux와 action이 맞으면 행을 제거하고 `DAT_006E0D80` 체인(문서78의 `212→202→203→227→201`)에 따라 stat2 EXP `+40..80`, 콘 callback, 다음 로컬 행 발행을 수행합니다. setup 시 stage0이고 행이 없으면 `HandleS2C_0007_LoadSetupBlob`도 `FUN_005A8790(-1)`을 호출해 첫 행을 로컬 생성할 수 있습니다.

- **VERIFIED:** action code, 제거행, 다음행은 C→S로 export되지 않습니다.
- **VERIFIED:** C→S `0007`의 stat2는 일반 경험치 누적과 동일 필드입니다.
- **판정:** EXP 증가와 stage0 상태만으로 튜토리얼 완료/현재 체인을 증명할 수 없습니다.

## 4. callback과 wire 경계

Ghidra에서 `CLogicManager` vtable `006A618C`를 직접 읽고 각 함수를 디컴파일했습니다.

| vtable offset | 함수 | 결과 |
|---:|---|---|
| `+0x18` | `FUN_00594980` | `return 0` — 80B runtime-row export no-op |
| `+0x20` | `FUN_005949C0` | `return 0` — 콘 credit no-op |
| `+0x28` | `FUN_00594A00` | `return 0` — 일반 save/update callback no-op |

파생 `CJSLogic`의 C→S0011 80B runtime-row projection은 123에서 확인됐습니다. 다만 콘 N 자체와 kind0/1/2/5의 로컬 action witness를 증명하지 않으므로 이 네 kind의 자동 credit 금지 결론은 유지합니다. C→S `0007` 196B에 runtime row 영역이 없다는 사실도 유지됩니다.

## 5. 서버 구현

`azrok_server.py`에 `RUNTIME_ROW_SERVER_POLICIES`를 추가해 kind0/1/2/3/5의 의미·로컬 효과·fail-closed 이유를 실행 계약으로 고정했습니다.

- `_complete_runtime_row_from_snapshot`은 active fail-closed kind를 진단 상태에 기록합니다.
- 실제 completion dispatcher는 기존 kind3 exact evolution edge만 호출합니다.
- kind0/1/2/5의 실제 로컬 effect와 같은 synthetic `0007` stat 변화가 와도 행, completed key, currency를 바꾸지 않습니다.
- row import/display는 계속 허용하므로 호환 UI를 제거하지 않습니다.

## 6. 검증

- `python -m py_compile azrok_server.py tools/test_server_contract_layers.py`: **PASS**
- 새 정책/음성 회귀 2개: **PASS**
- kind0 stat7 `50→40`, kind1 stat32 `0→16`, kind2 stat7 `50→40`, kind5 stat2 `0→40` 각각에서 row 유지·completed 0·currency 불변을 확인했습니다.
- Ghidra 원문: `ghidra_temp/quest_evidence_audit3_20260718.log` (read-only 분석)

## 7. 남은 한계

- **NOT VERIFIED:** 종료된 원본 서버가 별도 세션 문맥이나 미보존 서버 내부 이벤트로 kind0/1/2/5를 판정했는지 여부.
- 그 값은 클라이언트 바이너리와 현재 wire에서 복원할 수 없습니다. 독립된 원본 캡처가 나오기 전까지 fail-closed가 보존 서버의 권위 계약입니다.

Related: `content/78`, `84`, `86`, `87`, `98`, `99`, `100`, `INDEX`.
