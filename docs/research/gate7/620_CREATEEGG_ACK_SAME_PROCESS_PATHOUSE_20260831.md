# 620 — CreateEgg ACK와 같은 프로세스 PatHouse 직접 진입 (2026-08-31)

## 결론

- **VERIFIED (Ghidra):** 생성 성공 응답은 S2C `0x0006 [result=0, fresh/status=0]`이다. mode 0에서는 `CJSLogic::AckCreateEgg` 계열이 seed/state를 초기화하고 자연 C2S `0x0007`을 내보내며, `CGameManager::OnCreatEggAck -> CPopupSelectEgg::CreatEggResult` 계열이 SelectEgg UI와 엔티티를 purge/remove한다.
- **VERIFIED (production live):** C2S `0x0004`에 S2C `0x0006`만 즉시 응답한 뒤, 클라이언트의 자연 C2S `0x0007`을 받은 별도 응답으로 `0x0003/0x0007/0x0005/0x000A/0x000B`를 보냈다.
- **VERIFIED (visual):** 재부팅, 별도 접속 버튼, C2S `0x0005` 재선택, 게임 바이너리 패치 없이 같은 URL/프로세스에서 SelectEgg가 사라지고 카펫·가구·캐릭터·HUD·퀘스트 패널이 모두 보이는 PatHouse 3D에 진입했다.
- **SUPERSEDES #619:** #619의 원격 runtime/cache 배포와 INIT reset 배포 사실은 역사적으로 유효하지만, host INIT reset이 신규 생성 직행 실패의 해결 원인이라는 귀속은 기각한다. 저장 캐릭터 재선택 성공은 생성 popup을 정상 종료시키는 CreateEgg ACK 누락을 증명하거나 해결하지 못했다.

## 정적 근거

Ghidra read-only 재검증 경로:

1. `0x594310` mode dispatch → `0x59DD20` case 6 → `0x59E1F0` (`CJSLogic::AckCreateEgg`).
2. `payload[0] == 0`이면 `payload[1]`을 fresh/status 필드에 저장하고 clock/state/archetype seed를 초기화한 뒤 `0x5A4770(0,1,7)`로 자연 C2S `0x0007`을 방출한다.
3. common case 6은 `0x50D250` (`CGameManager::OnCreatEggAck`) → `0x5E8B90` → `0x5E7F50` → `0x5E7CD0`으로 이어진다.
4. 마지막 함수는 SelectEgg 자식 UI를 비활성화하고 네 entity를 purge/remove하며 관련 panel을 숨긴다.
5. `payload[1]`은 생성 슬롯이 아니다. S2C `0x0007` byte 0과 같은 fresh/status selector이며, 생성 슬롯은 C2S `0x0004` byte 14에 별도로 존재한다. 따라서 어느 슬롯이든 fresh 성공 ACK는 `[00,00]`이다.

S2C `0x0002`는 create ACK가 아니다. transition/logout 계열을 타고 `gm+0x31946=0`을 만들며 SelectEgg cleanup을 호출하지 않는다.

## 운영 wire 수락

계정 `aJYwo_vovUZVk`, 2026-08-31 KST:

| 시각 | 방향/opcode | 관찰 |
|---|---|---|
| 02:10:22.969538 | C2S `0004` | 15B 생성 요청, type 0 |
| 02:10:22.975079 | S2C `0006` | 2B `00 00`, C2S0004 후 5.541ms |
| 02:10:23.074551 | C2S `0007` | 196B 자연 후속, ACK 후 99.472ms |
| 02:10:23.077450 | S2C `0003` | 21B, `Data\\Space\\PatHouse\0` |
| 02:10:23.079717 | S2C `0007` | 472B fresh canonical restore |
| 02:10:23.082171 | S2C `0005` | 6B, state 0 |
| 02:10:23.084391 | S2C `000A` | 150B item registry |
| 02:10:23.086847 | S2C `000B` | 62B stat table |
| 02:10:23.740023 | C2S `0011` | 80B runtime/tutorial rows |

- **VERIFIED:** bridge의 두 왕복은 `19B -> 6B`, `200B -> 731B`로 분리됐다. 731B는 다섯 wire frame 크기의 정확한 합이다.
- **VERIFIED:** 중간 S2C `0002`, C2S `0005`, 재접속, client disconnect가 없었다.
- **VERIFIED:** 이후 C2S/S2C `0016` heartbeat가 10초 간격으로 지속됐다.

## 실제 화면 수락

- **VERIFIED:** 같은 launch URL과 같은 프로세스를 유지한 채 SelectEgg 화면이 사라졌다.
- **VERIFIED:** PatHouse 카펫, 책상/벽면 가구, 창밖 배경, 생성 캐릭터, 좌상단 프로필/경험치/상태 HUD, 우측 퀘스트 패널, 하단 메뉴가 동시에 렌더됐다.
- **VERIFIED:** 확인 시 host FPS 표시는 약 39.7이었고 브라우저 warning/error는 0건이었다.
- **VERIFIED (user acceptance):** 사용자가 동일 화면에서 생성 직행과 PatHouse 3D 진입 성공을 직접 확인했다.

## 구현과 검증

- 서버는 캐릭터 canonical 저장 성공 뒤 S2C `0006 [00,00]`만 C2S `0004` 응답으로 반환한다.
- `fresh_create_ack_sent`가 설정된 상태에서 자연 C2S `0007`이 오면 fresh legacy import를 억제하고 S2C `0003`을 room bundle 앞에 붙인다.
- `0006`과 room bundle을 같은 서버 응답에 합치지 않는다. 과거 동적 실험에서 이 조합은 `0xC0000005`를 일으켰다.
- **VERIFIED:** targeted server/registry 138 tests가 로컬 소스와 원격-baseline 최소 후보 양쪽에서 통과했다.
- **VERIFIED:** 전체 `tools/test_*.py` 307 tests가 통과했다.
- **VERIFIED:** 운영 server SHA-256은 `1aec22ecb9e473cda272590f75f4d5e832bf789470615bf5fe4c649e26bd25f8`, registry SHA-256은 `f025504c30794fcd6550b275ff78a6f64f2309a3cb51c9a758a3439dfa387737`이다.

## 접속 경계

- **VERIFIED:** 최초 재실행 때 로컬 `127.0.0.1:9201` SSH forward가 내려가 웹은 열리지만 게임 소켓이 원격 bridge에 도달하지 않았다.
- **VERIFIED:** `9201 -> u32ws:9201` forward를 복구하고 같은 launch URL을 reload하자 WebSocket/TCP/login/heartbeat가 정상화됐다. 이 reload는 캐릭터 생성 전에 수행했으며 create→PatHouse 직접 전환에는 재부팅이나 재접속이 개입하지 않았다.

## 남은 경계

- **NOT VERIFIED:** 물리 모바일에서 같은 fresh-create 직접 진입.
- **NOT VERIFIED:** 논리 슬롯 1~3의 실제 UI 생성 수락. `[00,00]`이 슬롯과 무관하다는 정적 계약과 합성 테스트는 확인했다.

