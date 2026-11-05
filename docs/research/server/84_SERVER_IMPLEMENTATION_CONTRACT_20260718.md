# 서버 구현 계약서 — 방/게임별 서버 책임 (2026-07-18)

> **PARTIALLY SUPERSEDED by 86, 87, 90, 92, 97, 98, 102, 104, 109, 113, 114, 123 and 126.** 구매/로비/질병/퀘스트 방향, 선택 캐릭터 경계, 액세서리, 0007 domain sentinel, 인벤토리·성장·FunCorn wire와 운영 관제까지 후속 문서가 정정·완성했습니다. 101은 126에 의해 archive되었습니다.

**목적**: 지금까지 정적 매핑된 전 콘텐츠/프로토콜을 "서버가 실제로 뭘 구현해야 하나" 관점으로 취합.
분석(무엇이 어떻게 동작하나)에서 **구축(서버 코드로 뭘 만드나)**으로 넘어가는 다리. 상세는 각 권위 문서 참조.

## ★ 핵심 결론: 서버는 얇은 6개 층

게임플레이 계산 **대부분이 클라 로컬**(리워드 공식·레시피·아이템효과·스탯델타 전부 exe 상수/테이블).
서버가 실제 구현할 것은 아래 6개뿐:

| # | 서버 층 | 하는 일 | 권위 문서 |
|---|---|---|---|
| **1** | **연결·로그인 부트스트랩** | TCP accept → 인증 → 부트스트랩 opcode 시퀀스 | protocol/82 |
| **2** | **상태 저장/복원 (0x0007)** | C→S 196B 스탯/진화/mode 저장 + S→C 472B canonical inventory/rows/currency 복원; domain bank empty=`FF` | 57b/49, 86, 113 |
| **3** | **액터 릴레이 (멀티)** | Plaza/Gym 액터 spawn/move/state/text 중계 + 로스터; OX mode-2 로스터/라운드/판정 | protocol/75, 92, mp 51/52/55/67 |
| **4** | **FunCorn/구매** | C→S0013 검증·차감→S→C0005 subtype13; C→S0012+인접0011 reward commit→subtype12 balance ACK | 66, 86, 126 |
| **5** | **채팅·소셜 릴레이** | 0x68→0x6A, 0x6C fail-closed | content/80, 100 |
| **6** | **액세서리 appearance** | 0x18 set/clear→0x000C delta, 0x0007/0x0066 4B 복원, stat/evolution unlock authority | 109, 111, 112, 114 |

## 방/게임별 계약 (로컬 = 서버 무관, 서버 = 서버 구현)

| 방/시스템 | 클라 로컬(서버 무관) | 서버 책임 | 문서 |
|---|---|---|---|
| **PatHouse 케어** | 수면/목욕/청소/용변 스탯델타(sys.tmp) | 결과 스탯 저장(0x0007) | 65/69 |
| **놀이/마술/체육(gym)** | 리워드엔진 FUN_005a1b90(베이스+티어), 스킬 stat31-39 | 스킬 저장(0x0007, 완료시 즉시) | 76/79 |
| **주방(요리)** | 레시피=컨테이너 열거, 요리숙련 stat40-54(domain1) | 인벤토리·숙련 저장 | 77/76 |
| **도서관(독서)** | 공부 action500→지식 stat30(domain0) | 지식 저장 | 76 |
| **상점** | 카트/버리기/되돌리기(전부 로컬·무패킷) | **구매 검증·소지금 차감(서버확정)**, 인벤토리 추가 | 66 |
| **퀘스트** | 평가·행제거·UI 표시 | 10행 발행; C→S0012 amount/channel2 + 인접0011 exact row retire로 FunCorn 원자 지급; kind3은 stage edge/콘0 | 78/123/126 |
| **질병** | 발병/18·36h 진행/치료 전부 로컬 | C→S0007 mode-pair 저장, 재접속 S→C0007 복원 | 83/86 |
| **진화** | 케어로 +0x130 로컬 승격 | 진화값 저장·복원(0x0007 +0x05→+0x02) | 60/62/70 |
| **Plaza/Gym(멀티)** | 렌더/이동/미니게임 계산 | **액터 릴레이·씬 게이트** | 75, mp |
| **OX(멀티)** | 렌더/이동/UI; 정답 side 표시와 CB 결과 적용 | **mode-2 C8..D4 라운드, CE 질문, 위치 마감, CB 패자목록 판정** | 92 |
| **채팅/커뮤니티** | 입력 UI | **메시지 릴레이** | 80 |
| **아이템 사용** | 가구=보관용량·에너지 UI pending. shipped toy/gym 탭은 000D/E producer 없음 | future-compatible 000D/E snapshot 수신, natural 000F atomic consume/0009 ACK | 66/90/98 |

## 1. 연결 부트스트랩 시퀀스 (protocol/82)

```
C→S 0x00 로그인(106B: type1+user13+pass92)
첫 C→S 0x16[00] → S→C 0x16[00] + 0x04[00,time] + 0x00(0x183 로비 SoA)
기존 캐릭터: C→S 0x05[slot] → S→C 0x03 path + 0x07 state + 0x05 post-load + 0x0A/0x0B
Hansol: C→S 0x16[01] 요청에만 S→C 0x04[01,time] 정확히 5회
```
- ★ **같은 opcode가 클라 mode(0핸드셰이크/1게임/2미니게임)별 다른 핸들러** — 서버는 opcode 순서로 진행(mode는 클라 내부).
- 생성 `0004`/선택 `0005` 성공 뒤에만 account+storage slot+character name의 `selected_character_key`를 session에 bind합니다. 같은 socket 재로그인은 이전 name/lobby/authority를 fresh template로 reset합니다.
- 검증된 `0004` transaction을 거치지 않는 rescue-era heartbeat auto-create는 비영속 identity를 만들므로 비활성입니다. (104)

## 2. 상태 저장/복원 = 0x0007 블롭 (서버의 심장)

두 방향은 다른 구조입니다. C→S `0x0007` 저장 196B / S→C `0x0007` 복원 472B:
- C→S: 70개 stat, evolution, mode/date pair
- S→C: 위 필드의 방향별 매핑 + 서버 canonical inventory, runtime rows, currency
- 스탯 70개: 경험치/레벨/봉에너지/스킬31-54/청소도 등
- 진화단계(+0x05→+0x02→logic+0x130)
- 퀘스트 10행의 setup/import(offset 0x134: kind/aux/value)은 S→C0007이며, 런타임 projection export는 파생 `CJSLogic`의 C→S0011 exact80B입니다(123).
- **질병 mode-pair 8개(offset 0x184 상태 / 0x18c 타임스탬프, 그룹5/6/7=질병)**
- 통화는 S→C +0x07과 purchase ACK +0x02에 서버가 채움
→ 서버 = 계정별 펫 상태를 이 블롭 형태로 저장/복원.

영속성 read/write 권한은 로그인 계정만으로 생기지 않습니다. 선택 key가 현재 session identity와 일치할 때만 C→S0007 저장, legacy snapshot import, canonical inventory overlay를 수행합니다. unselected `Player` placeholder는 profile 기본 응답이나 canonical 경로의 권위가 아닙니다. C→S0017 stat authority도 발행 당시 selected key와 함께 저장하고 같은 key의 0007에만 merge합니다. (104)

## 3. 통화 = 서버가 채워야 (content/78, 66)

- **소지금**: `model 0x001911A9 + 0x1F0`, S→C0007 +7/0005 +2가 같은 setter로 들어감. 구매 live에서 1000→950 확정.
- **구매**: C→S0013 45B `[count,total,id×20]` → 서버 카탈로그 검증/atomic commit → S→C0005 `[result,0x13,new_money]`. 성공 직후 0007을 추가 전송하지 않음.
- **구매 identity gate**: 선택/생성 성공으로 bind된 `selected_character_key`가 없거나 현재 account/slot/name과 다르면 canonical을 load하기 전에 status1 ACK로 fail-closed합니다. item-use 000D/E/F도 동일 경계를 사용합니다. (104)
- **퀘스트 FunCorn**: 파생 `CJSLogic::SendQuest`는 C→S0012 exact5 `[amount:u32,channel:u8]`를 보내고, 자연 완료에서 바로 다음 C→S0011이 정확히 한 행을 지웁니다. 서버는 정적 reward table·active generation·인접성을 검증해 FunCorn과 완료키를 한 transaction에 commit한 뒤 S→C0005 subtype12로 새 잔액을 ACK합니다. kind3은 기존 0010/0011+0007 stage edge로 retire하며 통화0입니다(126).

## 4. 서버 구현 전 x32dbg 관문

현재 quest FunCorn 필수 wire 관문은 126에서 닫았습니다. 정적 producer가 없는 toy/gym/006C는 98/100에서 fail-closed이고, 캐릭터 삭제 live는 102에서 격리 종결했습니다. 음식 아이콘 렌더 원인과 새 ACK clean live는 별도 남았습니다.

## 요약

서버가 **게임 로직을 재구현할 필요가 거의 없다** — 미니게임/요리/케어/상점 계산은 전부 클라가 이미 한다.
서버 = **①로그인/계정슬롯+선택 identity bind ②directional 0x0007+canonical 상태 ③액터 릴레이 ④구매/통화 ⑤채팅 릴레이 ⑥액세서리 appearance**.
구매·소지금·로비·질병·0x0007 핵심과 2클라 채팅 live, kind3 행 완료, OX 제출 wire 및 mode-2 판정 계약까지 정적·동적으로 확정됐습니다. 90에서 canonical-first 저장, exclusive character lease, exact 진화 edge와 toy/gym loadout·energy 소비/0009 ACK를 구현했습니다. 93~97에서 exact C8~D4 codec, CA side 판정, 수신자별 actor-id 변환, CD/D2/D4 상호배타 종료, C9→000D→kind1 calibration→0064 Plaza 복귀를 구현했고, 실제 좌측 O active click부터 CB 승자·CD-only·Plaza healthy까지 end-to-end로 검증했습니다.
energy 보유 프로필의 `000F[00]→0009[00 0F]`는 108에서 원본 client sender·server ACK·canonical energy `1→0`까지 live 종결했습니다. 캐릭터 삭제는 102, quest FunCorn은 126, toy/gym producer 부재는 98에서 종결했습니다. 100의 `0018→0069 fail-closed` 결론은 109가 supersede하며, 현행 액세서리 전용 `0018 set/clear→000C delta`와 0007/0066 4B 복원은 111에서 자연 UI self 왕복, 112에서 두 원본 클라이언트의 remote set/clear relay와 화면 생성·소멸까지 live 종결했습니다. OX cutoff/tie-break 원본값은 클라이언트에 없으므로 설정 가능한 fail-closed 서버 정책으로 보존합니다(92~97).

104에서 두 동시 세션의 lease reject 뒤 raw 구매가 `Player` canonical에 귀속되던 결함을 선택 key 기반 경계로 수정했습니다. 113에서 S2C0007 domain bank 40B를 FF sentinel로 바로잡았고, 114에서 액세서리 unlock authority와 cursor/OX/entity별 관제를 구현했습니다. 전체 **131 tests PASS**입니다.

123에서 파생 `CJSLogic` vtable을 직접 확인해 C2S0008/9/A/10/11/14 exact schema를 추가했습니다. 126에서 자연 C2S0012, stale-tail 0011, S2C0005 subtype12 FunCorn ACK와 native symbol metadata를 구현해 현재 전체 **179 tests PASS**입니다.

Related: protocol/75·82, content/65·66·69·71·76·77·78·80·83, world/70, multiplayer/51·52·55·67, archive/101, 104, 109, 113, 114, 123, 126, INDEX(전체 지도).
