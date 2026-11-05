# Quest FunCorn 0x0012, S2C 0x0005 subtype 0x12 ACK, 원본 심볼

Date: 2026-07-18

## 결론

- **VERIFIED (natural live):** food1001 퀘스트 완료는 C2S `0012 [amount:u32=40][reward_channel:u8=2]`를 보냅니다. 바로 다음 C2S `0011`이 완료 행을 제거합니다.
- **VERIFIED (static, current Plaza binary):** `HandleS2C_0005_PostLoadState @ 0x0059EBD0`에는 subtype `0x12` 성공 분기가 있으며 payload `+2`의 u32를 S2C0007 `+7`과 같은 setter로 씁니다. 퀘스트 성공 ACK 계약은 S2C `0005 [status=0][subtype=0x12][new_funcorn:u32]`입니다.
- **VERIFIED (original ILK symbols):** FunCorn은 `CJSUser::{Add,Get,Set}FunCorn`을 가진 유일 잔액입니다. `G2C_PRICE_ACK`는 `CJSShop::{ShopSet,ShopGet,ShopReset}Price`와 가격 전역 배열에 연결된 가격 카탈로그입니다. 별도 money 잔액을 만들지 않습니다.
- **VERIFIED (server implementation/test):** 0012는 정확한 정적 reward와 active row를 arm하고, 인접 0011의 정확히 한 행 retire와 함께 FunCorn·완료키를 atomic commit합니다. 이후 S2C0005 subtype12 ACK를 보냅니다. duplicate credit은 거부합니다. 전체 180 tests OK입니다.
- **VERIFIED (captured-profile recovery):** 구 서버가 food만 소비하고 놓친 최초 보상은 exact SHA/revision/semantic preimage를 확인한 1회성 recovery로 revision `3 -> 4`, FunCorn `950 -> 990`, row1 `kind0/aux1001 -> FF/FF/0`, durable tx5로 보정했습니다.
- **VERIFIED (clean live + restart):** 두 격리 namespace에서 실제 consumer 1회와 사용자 자연 클릭 1회를 각각 재현했습니다. 둘 다 `0014 -> 0008 -> 0012 -> 0011 -> 0007`, S2C0005 subtype12/990, UI990이었습니다. 첫 namespace는 서버·클라이언트를 모두 재기동해 S2C0007/0005 990, food0, normalized row, duplicate credit 없음까지 확인했습니다. 상세는 127입니다.

## 1. 자연 패킷 증거

run `20260718T200538_52232_e3b06bea`:

| seq | 방향/opcode | payload/의미 |
|---:|---|---|
| 339 | C2S 0014 | `e903`, food1001 action witness |
| 340 | C2S 0008 | food1001 `1 -> 0` |
| 341 | C2S 0012 | `2800000002`, amount40/channel2 |
| 342 | C2S 0011 | 완료 row kind `0x00FF`; aux1001/value26073020 stale |
| 343 | C2S 0007 | 후속 character snapshot |

클라이언트의 빈 행 권위는 kind `0x00FF` 하나입니다. aux/value stale tail은 decoder에서 `FF/FF/0`으로 정규화한 뒤 비교·저장합니다.

## 2. FunCorn과 Price 구분

원본 Naver `Azrok.ilk` 심볼의 직접 근거:

- `CJSLogic::AckFunCorn(G2C_FUNCORN_ACK*)`
- `CGameManager::OnFunCornAck(G2C_FUNCORN_ACK*)`
- `CJSUser::AddFunCorn/GetFunCorn/SetFunCorn`
- `CJSLogic::AckPrice(G2C_PRICE_ACK*)`
- `CJSShop::ShopSetPrice/ShopGetPrice/ShopResetPrice`
- `g_PriceBook` .. `g_PricePlay`, `g_nPriceBook` .. `g_nPricePlay`

따라서 UI의 `소지금`은 별도 통화명이 아니라 보유 FunCorn 표시입니다. canonical schema의 기존 `currency` 키는 호환성을 위해 유지하지만 의미는 FunCorn 하나입니다. 0012의 마지막 byte는 통화 selector가 아니라 현재 확인된 quest reward channel입니다. 세 reward producer가 모두 literal 2를 사용하므로 서버는 channel2만 fail-closed 수용합니다.

## 3. 즉시 ACK 계약

현재 Plaza binary의 `HandleS2C_0005_PostLoadState`:

- subtype `0x12`, status0: payload `+2` u32를 FunCorn setter에 기록
- subtype `0x13`, status0: pending shop inventory replay 후 같은 FunCorn setter 기록
- subtype `0x13`, failure: shop lock/error path
- subtype `0x00`, status0: bootstrap FunCorn 기록

서버는 reward+row commit이 durable하게 끝난 뒤에만 다음 프레임을 보냅니다.

`S2C 0005 00 12 <new_funcorn:u32 little-endian>`

이 ACK가 실패한 persistence보다 먼저 나가면 클라이언트와 canonical이 갈라지므로, 0012 수신 시점이 아니라 인접 0011 atomic commit 뒤에 생성합니다.

## 4. 원본 프로토콜 심볼 23종과 레지스트리

레지스트리는 wire stable ID를 원본 이름으로 덮어쓰지 않습니다. 대신 다음을 분리했습니다.

- `native_symbols`: ILK에서 복구된 C2G 9 / G2C 7 / S2C 7 식별자
- `native_links`: 현재 opcode와 직접 연결한 evidence-rated 링크
- `metadata_spec_id`: wire `spec_id`와 독립적인 native metadata hash

22개는 함수 인수 `PAU<TYPE>`로 직접 확인한 record type입니다. 23번째 `S2C_PLAZAENTER_ACK`는 raw ILK 문자열 식별자이므로 `kind=string_identifier`로 구분합니다. 숫자가 아직 없는 ACK는 symbol catalog에만 있고 wire link를 만들지 않습니다.

핵심 ABI도 보존합니다.

- `CClientPeer::Protocol(int, void*, int)`
- `CGamePeer::Protocol(int, void*, int)`
- `CGamePeer::AddPacket(int, void*, int)`
- `CPacket::MakePacket(void*, int, void*, int)`

## 5. 추가 원본 빌드 증거

- Naver `Azrok.bat`: `Azrok -nwnd -nx 100 -pl naver -dir 1234567890 -ip 127.0.0.1:3000` — 해당 배포판 기본 NX100은 VERIFIED. 현 안정 운영 NX200을 자동 변경할 근거는 아닙니다.
- `sys.tmp`: Plaza/Naver 4,268B SHA 완전 동일.
- `lgc.tmp`: 정확히 2바이트만 다름. `지식경험,0,0,450`(Plaza) vs `...,600`(Naver).

## 6. 구현 및 검증

- `decode_c2s_quest_reward_0012`: exact5, positive amount, channel2
- `decode_c2s_runtime_rows_0011`: kindFF empty authority + stale tail canonicalization
- `_process_quest_reward_0012`: exact reward candidate arm
- `_process_runtime_rows_0011`: adjacent one-row retire, idempotency key, FunCorn atomic credit, S2C0005 subtype12 ACK
- protocol registry: 68 wire specs + 23 native symbols + native links + independent metadata hash
- capture inspector/semantics: subtype12를 `G2C_FUNCORN_ACK`, balance를 `funcorn`으로 표시 (`currency` compatibility alias 유지)
- py_compile 성공, 전체 **180 tests OK**

복구 transaction:

- before SHA: `44e472bbf1d6a402dbb36bb6fef57498292134e089f56c58ab72595c9415a75f`
- after SHA: `f677d3f42849be23387102d97b13c100c46f3170bdb8d27e600834f8f45d0de7`
- receipt: `tx-00000005`, journal `durable`

## live gate 종결

위 live gate 1~4는 127에서 종결했습니다. 빈 슬롯 아이콘은 별도 표시-only 결함이며 protocol gap이 아닙니다. 원본 서비스 환경 재현이 없으므로 현대 렌더 호환성 문제인지 원본 클라이언트 고유 버그인지는 NOT VERIFIED입니다.
