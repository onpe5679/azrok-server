# 서버·GUI·프로토콜 대개편 런타임 검증 (2026-07-18)

표기: **VERIFIED**=최신 코드 재시작·API·브라우저 UI·파일 해시 직접 확인, **NOT VERIFIED**=후속 원본 UI 상호작용 필요.

## 결론

105 청사진의 P0 관제면과 109 액세서리 exact 계약을 최신 서버 런타임에 올렸습니다. 주 `profile_playable_v2`의 Azrok1을 실제 원본 클라이언트로 다시 선택했고, binding/canonical/economy/accessory/protocol registry가 브라우저 관제 화면에 일관되게 표시됐습니다.

- **VERIFIED runtime** server PID106840, client PID104264, control `127.0.0.1:9300`, TCP9207.
- **VERIFIED identity** entity2 Azrok1, selected/current key `a706c61796572_s0_c417a726f6b31`, canonical exists.
- **VERIFIED state** PatHouse stable, heartbeat recent, persisted evolution1, currency950, unknown C2S 0.
- **VERIFIED safety** 주 프로필 JSON과 196B bin 2개의 SHA-256이 격리 energy 작업 전 기준과 모두 동일합니다.
- **VERIFIED test** py_compile PASS. 111의 self 000C runtime projection, 112/114의 active-entity 분리·0065 reset·0067 remove, OX 운영 패널, cursor API·증분 GUI, unlock authority 회귀 추가 뒤 전체 131 tests PASS.

## 관제 GUI 실사용 검증

실제 렌더된 `Azrok 서버 관제실`을 브라우저에서 확인했습니다.

1. 서버/클라이언트 카드가 `1 client`, `#2 Azrok1`, PatHouse stable을 표시했습니다.
2. 영속성/경제 카드가 profile `playable`, namespace `profile_playable_v2`, BOUND, currency950, canonical path를 표시했습니다.
3. 액세서리 카드가 self 0007의 `FF FF FF FF`, slot별 범위, `stat1=level`, exact 9행 unlock table을 표시했습니다.
4. protocol registry가 C2S0018 exact3 `action0=set/action1=clear`, S2C000C exact7 appearance delta, S2C0007 +1D4와 S2C0066 +14를 모두 VERIFIED로 표시했습니다.
5. live protocol category를 `accessory`로 선택하자 실제 캡처에 0018/000C가 없으므로 `0 / 42`가 표시됐습니다. 이는 허구 행을 만들지 않는 inspector 정책과 일치합니다.
6. 계약 검색에 `0018`을 입력하자 정확히 한 행만 남았고, 필터 초기화 뒤 `46 / 46`과 빈 필터 상태로 복원됐습니다.
7. 브라우저 console error는 0건이었습니다.

## API 계약

`/api/protocol`은 `contracts`, `accessory_slots`, `accessory_policy`를 제공합니다. accessory policy에는 다음이 포함됩니다.

- empty `0xFF`, stat-derived ownership/no inventory
- C2S0018 `0=set,1=clear`
- self restore `0007 +0x1D4`
- remote baseline `0066 +0x14..17`
- remote update `000C` exact7
- stat1=level
- group1..5 stat 범위와 9개 unlock row

## 저장 불변

| 파일 | SHA-256 | 결과 |
|---|---|---|
| `417a726f6b31_c2s0007.bin` | `875390B1...BC817E` | 불변 |
| `506c61796572_c2s0007.bin` | `821D08B9...762940` | 불변 |
| `a706c...Azrok1_state_v1.json` | `D1904562...B0E31F` | 불변 |

server-only 재시작은 메모리 watcher를 붙이지 않으므로 Plaza 전환 매크로의 vtable/phase 안전 조건을 충족하지 않았습니다. 이를 우회해 강제 전환하지 않고 PatHouse stable에서 관제면을 검증했습니다. Plaza/OX 자체의 최신 live 계약은 97의 기존 증거가 권위이며, 이번 실행은 주 저장 복원과 대개편 UI 활성화 증거입니다.

## 111 후속 live 갱신

- **VERIFIED live** 원본 액세서리 UI의 장착/해제 각 1회 `0018→000C` self ACK는 111에서 종결했습니다.
- 관제 self current가 0007 baseline에 머무르던 표시 버그도 actor id1의 000C delta를 순차 적용하도록 수정했습니다.
- **VERIFIED live by 112** 같은 room 두 클라이언트의 000C set/clear remote delta와 원격 화면 효과 생성·소멸을 종결했습니다. 관제는 active entity별로 appearance를 투영하고 0065 reset/0067 remove도 반영합니다.
- **VERIFIED browser/test** OX phase/deadline/participant/answer 표시와 prepare/open/tick/finish(CD/D2/D4) 운영 패널을 추가했습니다. 각 전환은 confirm, 입력검증, 중복실행 방지, 오류 표시를 거칩니다.
- **NOT VERIFIED live** 액세서리 set 상태 재접속 0007 및 이미 set된 actor의 신규 0066 baseline 화면 대조.
- **VERIFIED by 114** P1 cursor packet/event/overview API와 증분 GUI는 구현·runtime probe를 마쳤습니다.
- CAS 관리 도구와 공통 mutation transaction audit는 계속 청사진 단계입니다.

증거: `artifacts/dynamic-analysis/server_gui_overhaul_runtime_evidence_20260718.json`, `captures/packets_20260718_135919.txt`.

Related: 84, 97, 104, 105, 108, 109, 111, 112, 114, INDEX.
