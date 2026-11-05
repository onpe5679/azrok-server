# 653 Plaza 상대 정보창의 이단계 0x006C/0x0070 계약 (2026-09-27)

## 확인된 원인

- **VERIFIED (원본 디컴파일):** `FUN_005CE8E0`은 캐릭터 선택 시 `+0x2b9` latch를 0으로 만들고 C2S `0x006C[target actor id]`를 보냅니다. 원본 `FUN_00616860`은 latch가 0일 때 S2C `0x0070`의 첫 4바이트만 읽어 OX selector pair에 저장하고 latch를 -1로 돌립니다. 따라서 선택 단계에 12바이트 전체 응답을 보내도 정보창 경로에는 도달하지 않습니다.
- **VERIFIED (원본 디컴파일):** `FUN_005FDAB0`의 BtnInfo case 6은 대상 액터의 `+0x2f8` id를 가져와 별도 C2S `0x006C`를 보냅니다. `FUN_00616860`은 latch가 0이 아닌 두 번째 응답의 12바이트를 `FUN_005FDF80`으로 넘겨 정보창을 갱신합니다. #539의 “정보 보기 버튼 자체는 패킷을 만들지 않는다”는 두 번째 버튼 클릭이 실제로 활성화되었는지 확인되지 않은 실측으로, 해당 해석은 뒤집힙니다.
- **VERIFIED (원본 디컴파일):** 전체 응답은 `<u8 displayed level, u8 OX tier, u16 OX points, u32 gauge denominator, u32 gauge numerator>`입니다. `FUN_00616860`은 +8을 numerator, +4를 denominator 인자로 역순 전달합니다. `FUN_005FDF80`은 level을 숫자로 출력하고, tier별 라벨/임계값을 고르며, `points/threshold`와 `numerator/denominator` gauge를 렌더합니다. tier 1은 유효한 최소값입니다. `denominator=0`이면 gauge가 0이 됩니다.
- **VERIFIED (기존 2세션 실측):** 다른 캐릭터 클릭의 C2S `0x006C` dword는 peer 서버 actor id입니다. 이전 서버는 1이 아닌 값을 사칭으로 폐기했습니다. 이 실측 자체는 #539와 일치합니다.

## 구현과 검증

- **VERIFIED (코드):** 서버는 화면에 보이는 Plaza 대상만 허용하고 항상 12바이트 S2C `0x0070`을 보냅니다. 원본 short handler는 패킷 앞 4바이트만 읽고, full handler는 12바이트를 전부 읽으므로 서버가 재선택 여부를 추측할 필요가 없습니다. peer level은 대상 캐릭터의 canonical state에서 읽습니다. 랭킹/대전 기록을 복원한 근거가 없어서 OX 점수·gauge는 0으로 유지합니다. 성장 경험치를 OX 점수로 바꿔 표시하지 않습니다.
- **VERIFIED (로컬):** `tools.test_protocol_registry`와 `tools.test_server_contract_layers.SocialStateContractTests` 통과. 실제 `socketpair`로 연속 12바이트 프레임을 보내고 수신한 바이트를 검증했습니다.
- **VERIFIED (production GUI):** 두 테스트 계정을 실제 Plaza에서 접속한 뒤 상대 선택 → 정보 보기를 실행했습니다. 이름 `sdsd`, level3, OX tier1/0 points 정보창이 표시됩니다. 증거: `artifacts/20260927_plaza_peer_info.png`. 성장단계 문자열은 화면상 블루론이며 캐릭터 선택 화면의 레드론과 달라 별도 미해결 표시 문제로 남깁니다.

원본 확인 함수: `FUN_005CE8E0`, `FUN_005FDAB0`, `FUN_005AB950`, `FUN_00616860`, `FUN_005FDF80` in `docs/research/_salvage/symbols/plaza_dump.txt`.

## 운영 배포

- **VERIFIED:** core and protocol registry deployed, core restarted active. Server SHA256 `4c6e52542d6419e76461570577085e9606f1855661858994e2a4f472e1ae5f18`; registry SHA256 `a461580362729e9a3f1013a0389f33f2c1300f28515c77237186777b60cc4aa6`. Backup `rollback/plaza-info-20260927`. Combined identity/server/registry checks: 142 pass.
- GUI acceptance completed on the two user-confirmed test characters. Existing control S2C000D transition was used solely to reach Plaza for UI verification; this does not prove a natural door click. Both diagnostic sessions and loopback launcher stopped after screenshots.
