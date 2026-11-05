# 서버 5층 구현 — 구매·로비·상태·질병 계약 수렴 (2026-07-18)

> **PARTIALLY SUPERSEDED by 87, 90, 92 and 104.** kind3 안전 완료/중복방지, 실제 두 클라이언트 채팅, OX mode-2 `C8..D4`에 더해 선택 캐릭터 key 없는 구매/상태 mutation의 fail-closed 경계가 추가 확정됐습니다.

정적 분석과 실제 클라이언트 실측을 `azrok_server.py` 구현으로 수렴시킨 기록입니다.
VERIFIED=디컴파일 또는 실제 wire/UI/재접속 확인, INFERRED=서버 정책, NOT VERIFIED=후속 동적 확인 필요.

## 1. 상점 구매 왕복 (VERIFIED)

- 구매 C→S opcode는 `0x0013`, payload는 정확히 45B:
  `[count:u8][claimed_total:u32 LE][item_id:u16 × 20]`.
- 실제 햄버거 1개 구매에서 `count=1`, `total=50`, `item=1001`을 수신했습니다. count 뒤의 미초기화 tail은 해석하지 않습니다.
- 성공 응답은 S→C `0x0005`, 6B `[result=0][subtype=0x13][new_money:u32]`입니다.
  실측 응답 `00 13 B6 03 00 00`은 950입니다. 실패도 동일 형식에서 result≠0으로 응답해 클라이언트 구매 락을 해제해야 합니다.
- 성공 직후 S→C `0x0007`을 또 보내면 클라이언트가 이중 적용할 수 있으므로 보내지 않습니다.
- 클라이언트 money model은 `0x001911A9`, vtable `0x006A6478`, 소지금은 `model+0x1F0`입니다.
  실측에서 서버 시작값 1000, 결제 후 화면 950, canonical JSON `currency=950`, `food[1]=1`이 일치했습니다.
- 카탈로그는 정당 취득한 로컬 `Azrok.dat`를 서버 시작 때 읽으며, 정확히 97개 레코드/8188B입니다. 서버에는 원본 자산이 아니라 id/domain/price만 유지합니다.

근거 아티팩트:
- `artifacts/dynamic-analysis/frida_prepare_shop_live_server_20260718.txt`
- `artifacts/dynamic-analysis/shop_purchase_commit_server_20260718.txt`
- 당시 packet ring seq 203/204: C→S 0013 45B, S→C 0005 `0013b6030000`

## 2. 재접속 로비 슬롯 계약 (VERIFIED)

S→C `0x0000` 387B의 앞부분은 SoA입니다.

- `+0x00`: result
- `+0x01`: occupied character count 0..4
- slot `i`: species `+0x02+i`, level `+0x06+i`, model stage `+0x0A+i`
- slot name: `+0x0E + 13*i`, CP949 C string 최대 12B+NUL
- `+0x42+i`: route flag. 값 3은 Hansol 강제 경로이며 정상 재접속은 0
- `+0x56`: sparse count
- 빈 슬롯 species/level은 `0xFF`. `count=1`인데 species가 모두 FF인 이전 blob은 모순된 상태였습니다.

현재 계정의 canonical 파일 이름에서 `Azrok1`을 복원하고, snapshot에서 level26/model stage1을 복원했습니다.
라이브 화면에 `이름: Azrok1 / 레벨: 26 / 단계: 레드론`이 표시됐습니다.

- 선택 C→S: `0x0005`, 정확히 `[slot:u8]`; 라이브 slot0 `00` 확인.
- 생성 C→S: `0x0004`, 정확히 `[species:u8][name:13][slot:u8]`. 이전 구현의 name14 해석은 마지막 slot을 이름에 섞는 오류였습니다.
- 삭제 C→S: `0x0006 [slot]`, 응답 S→C `0x0008 [slot,result]`, result0 성공. 102에서 격리 `profile_minimal`의 disposable `Del102`를 live 삭제해 `0008 00 00`, 보존 archive, 재접속 roster0을 확인했습니다. 실제 `Azrok1`은 삭제하지 않았고 주 프로필 SHA 3개가 모두 불변입니다.
- C→S `0x0008` 41B는 삭제가 아니라 별도 property sync입니다.

계정+slot+캐릭터명 canonical key를 로비에서 먼저 복원하므로 `char_name_raw=Player` 초기값 때문에 저장을 놓치지 않습니다.

## 3. 0x0007 방향별 상태 계약 (VERIFIED)

- C→S `0x0007`은 196B, S→C `0x0007`은 472B로 서로 다른 구조입니다.
- C→S는 70개 stat과 8개 mode/date pair를 담지만, S→C 전용 inventory/quest/currency 행을 다시 올리지 않습니다.
- 서버 canonical JSON이 inventory/runtime rows/currency를 소유하고, C→S snapshot은 stat/evolution/mode pair만 merge합니다.
- 재접속 실측 S→C 0007: `currency=950`, `food[1]=1`, evolution1, mode states `0×8`, dates `0×8`.
- 신규 mode pair에서 `0xFF`는 sentinel이 아닙니다. `ModePairWriter_Import@005AA6F0`은 이를 실제 상태로 쓰므로 fresh는 state/date 모두 0이어야 합니다.
- 과거 오염 signature `state2×8 + date0×8`은 fresh 0으로 migration합니다. 질병 group5..7은 state0..3만 허용하고 state1..3에는 유효 `YYMMDDHH`가 필요합니다.

## 4. 질병 — 서버 판정이 아니라 로컬 진행 결과 저장 (VERIFIED, content/83 정정)

`FUN_005AA850`이 mode0 per-frame에서 로컬로 발병/진행합니다.

- group5: `stat4 위생 < stat12 사회적지능 - 40`
- group6: `stat7 스트레스 > 80`
- group7: `stat29 인스턴트 > 90`
- 조건 활성 시 state1, 게임시간 18h 후 state2, 36h 후 state3. 게임시계는 20초마다 1h 전진합니다.
- 아기(evolution0)는 group5..7 로컬 진행을 건너뜁니다.
- 약 치료 action0xD5도 로컬이며 결과 C→S 0007을 서버가 저장합니다. 질병 전용 opcode/약 ID wire는 없습니다.

따라서 서버가 wall clock으로 독자 발병시키면 클라이언트 게임시계와 어긋납니다. 서버 역할은 결과 snapshot 저장/복원이며 즉시 0007 echo를 보내지 않습니다.

## 5. 퀘스트/콘의 관측 한계 (VERIFIED, content/78 정정)

- 퀘스트 10행은 S→C 0007 `+0x134/+0x148/+0x15C`로만 import됩니다.
- C→S 0007 196B 범위는 `logic+0x5F8..+0x6BC`; 퀘스트는 `logic+0x70C`이므로 포함되지 않습니다.
- 완료 뒤 80B 테이블 export 시도는 vtable callback `00594980`이 순수 no-op이며 네트워크로 가지 않습니다.
- 완료 UI event queue도 로컬 UI에서만 소비됩니다. universal quest-complete C→S opcode는 없습니다.

따라서 모든 C→S 0007 수신에 콘을 지급하면 안 됩니다. kind3은 서버 발행 generation/행 index/발행 당시
진화값과 정확한 목표 단계 상승 및 보이는 임계값을 결합해 가장 앞 행 하나만 retire하도록 구현했습니다.
kind3에는 통화 callback이 없어 콘은 지급하지 않으며 replay/reconnect echo는 완료로 인정하지 않습니다.
kind1은 일반 행동도 같은 stat을 올리고 보너스가 clamp/gate로 사라질 수 있어 stat delta만으로 판정하지 않습니다.
kind0/2/5의 범용 정확 판정도 NOT VERIFIED입니다. 상세는 87입니다.

## 6. OX 정정 (VERIFIED/NOT VERIFIED)

> **PARTIALLY SUPERSEDED by 92.** 아래 위치 제출 결론은 유지됩니다. 92가 mode-2 전용 S→C 프로토콜과 서버 판정 경계를 추가 확정했습니다.

- `FUN_006133B0`은 답안 setter가 아니라 일반 outbound opcode latch입니다. 답안 BP로 쓰지 않습니다.
- C→S `0x0069`는 `PLAZA_CHAIR_%d.MDL` 의자 선택 경로이며 OX 답안이 아닙니다.
- OX 질문/결과 popup에는 송신이 없고 답안은 전용 opcode가 아니라 일반 이동을 재사용합니다.
- C→S `0066` 22B의 byte0는 current cell이며 current/destination/duration/pathFlag를 담고,
  C→S `0067` 15B는 arrival/current-position commit입니다. destination cell은 좌표에서 서버가 별도 계산합니다.
  cell 공식은 `((y+9000)/3000)+((x+9000)/3000)*6`입니다.
- 최종 판정 timestamp와 O/X side→cell mapping만 동적 A/B가 남았습니다. 상세는 87입니다.

## 7. 구현/테스트 상태

`azrok_server.py` 구현:

- Layer1: heartbeat-paced login, 계정/slot/character 로비 복원, 선택/생성
- Layer2: versioned canonical state, atomic save, C2S/S2C 0007 directional merge, mode-pair sanitation
- Layer3: actor roster/state relay
- Layer4: exact 0013 purchase validation/commit + 0005 subtype13 ACK
- Layer5: public/whisper 0068→006A relay. C→S 006C는 exact 4B/self-id/Plaza 조건까지 검증하지만,
  S→C 006C의 `state/toggle`은 실제 actor state를 바꾸며 `0/0`도 no-op으로 증명되지 않았으므로
  90에서 relay를 fail-closed/deferred로 정정했습니다.
- C→S 0018(3B `slot/kind/localId`)은 검증하되, S→C 0069에 필요한 `arg0/arg1/gate` 매핑이
  INFERRED이므로 패킷을 꾸며내지 않고 `pet_trick_deferred` 이벤트로 기록합니다.
- 실제 두 클라이언트 Plaza에서 UI 입력 `L5CHAT84A`를 보내 C→S0068 1건→양쪽 S→C006A 2건과
  양쪽 화면 렌더를 확인했습니다. peer 이름이 `Player`로 보이던 문제도 canonical 캐릭터명 relay metadata 동기화로 수정했습니다.

현행 저장 무결성·item-use 추가 계약은 90을 따르며, 101/102 반영 후 전체 **91 tests PASS**입니다.

남은 항목:

- NOT VERIFIED: OX 원본 서버 cutoff/tie-break(클라이언트에는 없음), 활성 라운드 `0=O/1=X` 글자라벨 및 기본 cell 후보 `{20,21}/{14,15}` live A-B (mode-2 wire/CE side/CB 패자목록은 92에서 VERIFIED)
- NOT VERIFIED: S→C 006C의 실제 state/toggle 값과 C→S 0018→S→C 0069의 arg0/arg1/gate 매핑
- NOT VERIFIED: 퀘스트 kind0/1/2/5의 정확한 서버-visible action evidence
- VERIFIED (102): 격리 disposable 캐릭터 생성→원본 UI roster→C2S0006/S2C0008→archive→재접속 빈 로비와 주 프로필 SHA 불변
