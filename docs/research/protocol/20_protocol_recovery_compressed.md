# Azrok Protocol Recovery 04-07 압축 요약

Date: 2026-03-31  
Source:
- `04_readme_delta_stat_registry_keyspace.md`
- `05_readme_delta_schema_file_crosswalk.md`
- `06_readme_delta_hidden_outbound_channels.md`
- `07_readme_delta_bootstrap_and_orphaned_pass.md`

목적:
- 4번부터 7번까지의 핵심 정보를 한 문서에 압축 정리
- 수치, 범위, 함수, 패킷 의미는 최대한 유지
- 반복되는 "Server implication" 문장은 항목별 핵심 결론으로 통합

---

## 1. Stat/Schema Keyspace 정리

### 1.1 `0x000A`는 평면 stat dump가 아니라 그룹형 registry update

근거 함수:
- `StatRegistry_WriteGroupedKeyValue`

고정 그룹 크기:
- group0=`33`
- group1=`10`
- group2=`8`
- group3=`33`
- group4=`3`
- group5=`1`
- group6=`6`

내장 키/기본값:
- group0: ids `0..32`, 반복값 `0 / 1000 / 2000`
- group1: ids `2000..2009`, 반복값 `0 / 200 / 500`
- group2: ids `2500..2507`, 반복값 `0 / 200 / 500`
- group3:
  - `1001..1003 -> 30`
  - `1004..1005 -> 40`
  - `1006..1014 -> 100`
  - `1015..1023 -> 200`
  - `1024..1032 -> 300`
  - `1500 -> 100`
- group4:
  - `1500 -> 100`
  - `1501 -> 200`
  - `1502 -> 300`
- group5: `3000 -> 200`
- group6:
  - `4000/4002/4004 -> 100`
  - `4001/4003/4005 -> 500`

압축 결론:
- `0x000A`는 내부 다중 family id-space를 가진 grouped registry 갱신이다.
- `1500`은 둘 이상의 group에 의도적으로 중복 배치되어 있다.

### 1.2 stat/domain 코드는 8개 category로 공식 분류됨

근거 함수:
- `DomainCode_ClassifyBucket`

분류:
- category `0`: `0..32`
- category `1`: `2000..2009`
- category `2`: `2500..2507`
- category `3`: `1000..1032`
- category `4`: `1500..1502`
- category `5`: `3000`
- category `6`: `4000..4005`
- category `7`: `5000..5002`

압축 결론:
- 이 숫자들은 ad hoc magic number가 아니라 typed keyspace다.

### 1.3 schema row 중 일부는 일반 numeric stat row가 아님

근거 함수:
- `StatSchema_LoadFallbackAndMapNames`
- `StatSchema_LookupIdByName`

핵심:
- fallback schema는 총 `57` rows
- 이 중 `0x43/0x44/0x45/0x46`은 일반 stat slot이 아닌 synthetic ids
- 특수 처리:
  - `0x45` -> object offset `+0x6BC`에 pointer-like data 기록
  - `0x46` -> object offset `+0x6C0`에 pointer-like data 기록
  - `0x43` -> `ProtocolState_SetField130Value(0xFF)` 호출
  - `0x44` -> normal triple-slot stat storage에서 제외

압축 결론:
- schema universe 전체를 단순 numeric row 집합으로 보면 오해가 생긴다.

### 1.4 stat slot `9`는 stage 의존 max를 가짐

근거 함수:
- `FUN_005A4A50`

매핑:
- stage `0x1E -> max 500`
- stage `0x1F -> max 600`
- stage `0x20 -> max 700`

압축 결론:
- slot `9`는 고정 cap으로 처리하면 native behavior와 어긋난다.

---

## 2. 파일 기반 schema와 실제 런타임 모델의 차이

### 2.1 `lgc.tmp`만이 schema authority가 아님

근거 함수:
- `StatSchema_LoadFallbackAndMapNames`
- `StatSchema_LookupIdByName`

핵심:
- 클라이언트는 코드 내부에 full fallback schema를 내장
- fallback row 수는 `57`
- file-backed schema와 같은 stat-engine object model로 적용

압축 결론:
- 서버 검증은 file-only authority를 가정하면 안 된다.

### 2.2 `init.csv`만으로 startup visible value가 결정되지 않음

근거 함수:
- `FUN_005A3020`
- `FUN_005A1B90`

런타임 동작:
- 전체 `0x47` stat slots를 기본값으로 초기화
- archetype-specific override 적용
- 최소 stat `0`, stat `4`에 random seed 주입

관찰된 random window:
- archetype `0`: stat `4 = 0x3C..0x4F`, stat `0 = 0x14..0x59`
- archetype `1`: stat `4 = 0x28..0x3B`, stat `0 = 0x1E..0x59`
- archetype `2`: stat `4 = 0x14..0x27`, stat `0 = 0x28..0x59`
- archetype `3`: stat `4 = 0x28..0x3B`, stat `0 = 0x14..0x59`

압축 결론:
- 사람이 읽는 seed source로는 `init.csv`가 유용하지만, packet-faithful startup은 archetype/random layer까지 반영해야 한다.

### 2.3 imported `0x0007` stats는 client schema 기준으로 clamp됨

근거 함수:
- `Stats_StoreClampedValue`

동작:
- client-side min/max schema로 검사
- 범위 내 값은 수용
- 범위 밖 값은 clamp
- 단, callback `7`은 원래의 out-of-range value를 들고 발생

압축 결론:
- 서버가 "조금 벗어난 값"을 보내도 부작용이 없다고 볼 수 없다.

### 2.4 progression/evolution gate는 visible stat 외 hidden requirement를 섞어 씀

근거 함수:
- `FUN_005A82B0`

핵심:
- 일부 gate는 고정 상수 대신 current max와 비교
- 한 case는 `FUN_0059AF20` 기반 possession/presence check 필요
- 다른 case는 세 내부 offset의 aggregate sum threshold 필요

압축 결론:
- progression 모델은 단순 CSV stat row 비교가 아니다.

---

## 3. Hidden Outbound / Local Effect 채널

### 3.1 `0x0007 + 0x125..0x12F`는 passive flag가 아님

근거 함수:
- `DomainCode_ClassifyBucket`
- `DomainCode_EmitLocalEffect`

핵심:
- 이 코드들도 formal category에 편입됨
- 일부 category는 즉시 local send/event family를 구동
  - category `1 -> 0x000D`
  - category `2 -> 0x000E`
  - category `7 -> 0x000F`

압축 결론:
- `0x0007` capability block은 숨은 outbound/local emit 채널 역할을 한다.

### 3.2 category `0` code는 하드코딩된 local effect family를 직접 탄다

근거 함수:
- `DomainCode_EmitLocalEffect`

확인된 매핑:
- `0 -> 5,5`
- `1 -> 10,10`
- `2 -> 15,15`
- `0x12 -> 4,3`
- `0x13 -> 7,6`
- `0x14 -> 8,7`
- `0x15 -> 5`
- `0x16 -> 10`
- `0x17 -> 15`

압축 결론:
- 코드 변경은 UI flag 수준이 아니라 local emit/effect 경로 자체를 바꿀 수 있다.

### 3.3 `0x006F`는 소형 setter 성격이 강함

근거 함수:
- `HandleS2C_006F_SetSelectorPair`

핵심:
- `FUN_006108F0(payload[0], payload[1])` 호출
- 사실상 compact two-byte write path

압축 결론:
- 초기 에뮬레이션에서는 복합 scene packet보다 small slot/value update로 보는 쪽이 맞다.

### 3.4 `0x0071`은 early emulation에서 우선순위가 낮을 가능성

근거 함수:
- `FUN_00616510`

핵심:
- `payload[0] == 0`일 때만 동작
- `FUN_00606970(...)`, `FUN_00520320(...)`를 통해 local `0xFE` path를 합성

압축 결론:
- 1차 서버 bring-up 단계에서는 low-priority stub 후보에 가깝다.

---

## 4. Bootstrap / Late-Sync / Handler Coverage

### 4.1 orphaned-code scan 결과, 숨은 미발견 handler는 못 찾음

스캔 구간:
- `0x0050C000-0x0050D400`
- `0x0059C000-0x005A6000`
- `0x00612000-0x00617000`

관찰된 island:
- `0x0050CD6E`
- `0x0059DDDD`
- `0x006138C6`
- `0x00614586`

압축 결론:
- 이들은 standalone protocol handler가 아니라 table/padding island로 보는 편이 맞다.
- 현재 정확도 gap은 "누락 handler"보다 "기존 handler 내부 field fidelity" 쪽에 있다.

### 4.2 `S->C 0x0000`은 hello stub가 아니라 persistent bootstrap cache

근거 함수:
- `Lobby_CopyBootstrapBlob_0183`
- `HandleS2C_0000_LoadLobbySparseCache`
- `LobbySparseRecordTable_Reset`
- `LobbySparseRecordTable_InsertIfNonzero`

구조:
- blob size=`0x183`
- lobby/object offset `+0xBF4`에 복사
- `payload[0x56]`는 count byte
- tail은 sparse pair-table
  - `u16[]` at `+0x57`
  - `u32[]` at `+0xBB`
- zero value row는 active insertion에서 제외

state 분기:
- `payload[0] == 0 && payload[1] == 0 -> local state 0x6C`
- `payload[0] == 0 && payload[1] != 0 -> local state 0x6B`

압축 결론:
- `0x0000`은 구조화된 캐시 쓰기로 구현해야 한다.

### 4.3 `S->C 0x0064`, `0x006E`는 여러 내부 object를 직접 갱신

근거 함수:
- `HandleS2C_0064_ApplyAuthoritativeSelf`
- `FUN_0050EE80`
- `FUN_0050C190`
- `FUN_005B61F0`
- `FUN_00614D40`
- `HandleS2C_006E_CommitReadyMode`
- `FUN_00616AC0`
- `FUN_00616AF0`

핵심:
- `0x0064 + 0x1A`로 `this + 0x641` 기반 sub-object 선택
- 그 sub-object의 `+0xCB`, `+0xCF`, `+0xD4`에 timer/state 기록
- `0x0064`는 `+0x35C0F..+0x35C1F`에 packed descriptor block도 밀어 넣음
- `0x006E`는 ready flag 이전에 `byte0`를 두 곳에 복사
  - `this + 0x1889` rooted field offset `+0x7B`
  - `this + 0x22C4` rooted field offset `+0x16B`

압축 결론:
- 둘 다 scene-entry ack/filler가 아니라 내부 object programming packet에 가깝다.

### 4.4 state-1 late-sync family는 self-bootstrap 축보다 넓음

새로 핀된 dispatch member:
- `0x0065`
- `0x0067`
- `0x006A`
- `0x006B`
- `0x006C`
- `0x006D`
- `0x0070`
- `0x0071`

실무상 포인트:
- `0x0065`: tracked entities flush
- `0x0066`: batched remote-actor spawn/state
- `0x0067`: targeted removal/detachment
- `0x0068`: batched movement/state update
- `0x0069`: targeted actor action/state update
- `0x0070`: client latch에 따라 wire shape 2종

압축 결론:
- self-bootstrap 이후 월드 sync는 이 wider band를 포함해 봐야 한다.

### 4.5 `S->C 0x0004`, `0x0006`은 예상보다 강한 bootstrap path

근거 함수:
- `HandleS2C_0004_CalibrationSample`
- `DispatchState0Common_S2C`
- `HandleS2C_0006_ResetLocalClockAndSeed`

핵심:
- `0x0004`: multi-sample calibration path, payload state를 변형하고 readiness 관련 latch에 연결
- `0x0006`: `payload[0] == 0`일 때 archetype/state helper를 포함한 full local reseed 수행

압축 결론:
- 둘 다 filler/ack-only로 취급하면 bootstrap fidelity가 크게 떨어질 수 있다.

---

## 5. 최종 요약

- stat 쪽은 flat table보다 `typed keyspace + grouped registry + special synthetic rows + stage/archetype dependent behavior` 모델이 더 정확하다.
- schema authority는 파일 단독이 아니라 code fallback까지 포함한다.
- `0x0007` 관련 일부 값은 hidden outbound/local effect channel로 작동한다.
- bootstrap/sync 쪽은 `0x0000`, `0x0004`, `0x0006`, `0x0064`, `0x006E` 및 state-1 late-sync family를 우선적으로 정밀 구현해야 한다.
- 현재 남은 공백은 "숨은 새 handler"보다는 "이미 찾은 handler 내부 필드 충실도"에 가깝다.
