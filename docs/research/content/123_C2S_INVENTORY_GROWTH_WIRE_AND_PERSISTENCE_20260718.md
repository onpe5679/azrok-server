# C2S 인벤토리·성장 wire와 영속 계약 정정 (2026-07-18)

> **SUPERSEDES archive/120.** 120에서 NOT VERIFIED로 낮춘 `0008/0009/000A/0010/0011`은 파생 `CJSLogic` vtable과 실제 caller를 직접 확인해 exact schema를 복구했습니다.

> **QUEST FOLLOW-UP by 126.** 123의 “kind0/1/2/5 reward provenance 부족” 결론은 자연 C2S0012와 인접 C2S0011 실측으로 폐기되었습니다. 0011 empty는 kindFF만 권위이며 stale aux/value를 허용합니다.

## 결론

- **VERIFIED (static):** `CJSLogic::vftable @006A6478`은 base `CLogicManager`의 no-op callback을 교체합니다. `+0x18=FUN_0059DB40`은 C→S `0011`, `+0x1C=FUN_0059DAD0`은 C→S `0010`을 실제 전송합니다.
- **VERIFIED (static):** 음식/요리 경로는 로컬 inventory 변경 뒤 C→S `0014[item_id:u16]` witness와 C→S `0008` snapshot을 보냅니다. 약 mode6은 C→S `0014` item-id witness로 직접 감소를 증명합니다.
- **VERIFIED (clean live):** 재접속 직후 원본 클라이언트가 C→S `0008` exact 41B를 자연 전송했습니다. 서버는 snapshot을 canonical에 반영하고 재접속 S→C `0007`에서 동일 SHA/센티널/통화/진화를 복원했습니다.
- **VERIFIED (implementation/test):** exact decoder, fail-closed authority, atomic canonical mutation, growth proposal/completion 검증을 구현했습니다. 124의 도구 경로 회귀까지 현재 전체 **177 tests OK**, `py_compile` PASS입니다.

## exact C→S 계약

| opcode | exact length | schema | 서버 권한 |
|---|---:|---|---|
| `0008` | 41B | food 38B = active 33 + zero pad 5, ingredient 3B; 각 값 u8 qty | 선택 key의 food/ingredient snapshot을 원자적으로 교체 |
| `0009` | 10B | toy 10×u8 qty | toy snapshot 교체 |
| `000A` | 8B | gym 8×u8 qty | gym snapshot 교체 |
| `0010` | 2B | `[aux,flag]`, aux 0..6, flag 0=proposal/1=completion candidate | kind3 성장 baseline/후보; 단독 stage 변경 금지 |
| `0011` | 80B | 10×u16 kind + 10×u16 aux + 10×u32 value | runtime-row projection; monotonic `0007` stage edge가 있어야 kind3 completion |
| `0014` | 2B | little-endian `item_id:u16` 한 개; action 의미는 producer 문맥 | food는 후속 0008 상관관계, medicine 4000..4005만 direct -1 |

`0008` sender는 `0059B721`, `0009`는 `0059B35D`, `000A`는 `0059B3FD`, 공통 send는 `00593D10`입니다. `0014`는 vtable slot0 thunk `004DA980→FUN0059DC50`이며 wire에는 item id만 싣습니다. 실제 call은 `00596D5A`, `00596DCE`, `0059B824`입니다.

## 음식·요리·약 producer

- action `D4/DB`: food container 감소 → `0014(food id)` → `0008`.
- action `D1`: ingredient 감소지만 `0014`에는 선택된 원 food id가 실리고 → `0008`이 최종 authoritative snapshot입니다.
- 공통 `FUN005D27C0`의 mode6 약 사용: drug `+0x382` 감소 → `0014`; mode3/5는 같은 handler를 쓰지만 medicine network 감소로 취급하지 않습니다.

서버는 food `1000..1032`의 `0014`만 `witness_pending_0008`로 기록하고 수량을 직접 줄이지 않습니다. medicine `4000..4005`만 직접 `-1`합니다. ingredient/energy/toy/gym/furniture/book/unknown `0014`는 거부합니다.

## 성장/퀘스트 정정

base vtable `006A618C +0x18`의 no-op 자체는 사실이지만, 실제 게임 객체인 파생 `CJSLogic`이 이를 override하므로 “80B row export가 없다”는 일반화는 폐기합니다. `0010`만으로 stage를 올리지 않고, `0011`은 서버가 가진 다음 kind3 행과 일치하며 별도의 C→S `0007` monotonic stage edge가 확인될 때만 완료시킵니다. kind0/1/2/5 reward는 126의 C2S0012 `[amount,channel2]` + 인접 0011 계약을 따릅니다.

## 동적 복원 증거

Clean run `20260718T191339_95676_052fd24d`에서 seq 42가 자연 C→S `0008` exact41입니다. S→C `0007` seq36은 `+0x1AC..0x1D3=FF×40`, `+0x1D4..0x1D7=FF×4`, currency 950, evolution 1, canonical SHA `D190456272D19D182FB9AA69F405373C31C13393F24A706FF190E71B35B0E31F`였습니다.

재접속 run `20260718T193038_95052_55240687`에서도 C→S `0008` seq44가 자연 발생했고, S→C `0007` seq38의 같은 sentinel/currency/evolution 및 같은 canonical SHA를 확인했습니다. 두 S→C0007 472B payload SHA-256은 모두 `fd36bdc6444b420fff168fe04f302a34e798fff8f70740e8ce7eaf6b9824e15e`, 두 C→S0008 payload SHA도 동일합니다. ACK packet은 없습니다.

## 남은 경계

- **NOT VERIFIED:** 실제 음식/요리 1회 전후의 `0014→0008` 수량 edge와 약 `0014` direct decrement를 clean UI로 각각 재현하는 것.
- **NOT VERIFIED:** `0010/0011/0007`의 자연 성장 한 사이클을 새 exact decoder로 재캡처하는 것.
- 서버는 이 live가 끝나기 전에도 exact static schema보다 넓은 의미를 추론하지 않습니다.

관련 권위: 78, 84, 101, 113, 120(archive), INDEX.
