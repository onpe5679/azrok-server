# Non-purchase inventory persistence gap (2026-07-18)

> **SUPERSEDED by 123.** 파생 `CJSLogic` vtable과 실제 sender를 직접 확인해 C→S0008/9/A/10/11/14의 exact schema와 인벤토리·성장 영속 경로를 복구했습니다. 이 문서는 당시 P0 갭을 발견한 역사 증거로만 보존합니다.

> **이 문서는 content/77의 `0x0007/0x000A` inventory 동기화 결론을 부분 정정합니다.**

## P0 결론

- **VERIFIED (static/code):** 현재 canonical inventory를 변경하는 서버 경로는 구매 C→S `0013`의 `+1`, energy C→S `000F`의 `-1`, toy/gym loadout뿐입니다.
- **VERIFIED (static):** 음식 먹이기와 요리는 클라이언트 로컬 컨테이너를 변경한 뒤 확인된 저장 wire로 C→S `0007` 196B만 보냅니다. 이 blob에는 inventory가 없습니다.
- **VERIFIED (server):** C→S `0007` commit은 기존 canonical inventory를 그대로 복사하므로, 재접속하면 먹은 음식/소비한 재료가 부활하고 새로 만든 음식은 사라질 구조입니다.
- **VERIFIED / NOT VERIFIED split:** 약은 로컬 질병 mode-pair를 바꾸는 것이 확인됐지만 실제 약 수량 감소 primitive 적중은 아직 live 미확정입니다. 감소한다면 현재 서버에서는 재접속 후 부활합니다.
- **VERIFIED correction:** S→C `000A`는 75-u16 item registry입니다. C→S inventory export의 증거가 아닙니다.

## 프로토콜 fail-closed 정정

C→S `0008`, `0009`, `000A`, `0010`, `0011`은 문서 82의 이름만으로 payload와 authority가 증명되지 않았습니다. typed registry에서 모두 `NOT VERIFIED`, `implementation=not_verified`, `risk=unknown`, `observe only; do not infer inventory`로 낮췄습니다. 자연 액션 capture 전에는 stat 변화나 opaque frame을 근거로 item id/수량을 추측하지 않습니다.

## 최소 동적 캡처

1. 음식 1개: `00596690`(D4/DB, food id), `0059BE80`(container/baseId/return), `005A4770`(send), 전후 container/canonical/reconnect `0007 +0xEA`.
2. 요리 1회: `005D27C0`, `00596690`, `0059B7F0`, `0059BE80`, `005A1B90`, `005A4770`; ingredient `+0x110`, food `+0xEA`, stat40..54 전후 비교.
3. 약 1개: `00596690`(D5, id4000..4005), `005AA6F0`(질병 pair), `0059BE80`, `005A4770`; drug `+0xB8`와 reconnect 비교.

각 시나리오는 알려진 opcode만 필터하지 말고 전체 C→S를 구조화 capture해야 합니다. 같은 프로세스에 x32dbg와 Frida를 동시에 붙이지 않습니다.

## 구현 판단 경계

별도 inventory wire가 실측되면 그 exact schema로 canonical mutation을 구현합니다. wire가 없다면 원본 클라이언트만으로 서버가 소비 item id를 알 수 없으므로, stat delta 추측 대신 보존용 최소 interoperability shim을 별도 설계해야 합니다. 이 결정은 동적 부정증거 전에는 하지 않습니다.
