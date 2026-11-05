# 564. Character logout and roster-return opcode 0x0002 (2026-08-26)

> **PARTIALLY SUPERSEDED by 585.** 정적 `0002 ACK -> 0007 -> 0001`
> 흐름과 상태 보존 결론은 유효하지만, 같은 프로세스에서 4슬롯 로비가 다시
> 그려진다는 가정은 라이브 실측으로 기각됐다. 최신 브라우저 복귀 계약은 #585를 따른다.

## Scope

원본 클라이언트에서 같은 계정의 다른 캐릭터로 전환하려고 로그아웃했을 때 관측된
`C2S 0x0002`의 의미와 서버 계약을 확정하고, 해당 계약을 서버에 최소
구현한다.

## VERIFIED — original client static contract

- MainMenu 버튼 `0x1B1`은 LogOut, 확인 버튼 `0x1B2`의 소비자는
  `FUN_005CC5C0` (`0x005CC5C0`)이다.
- Yes 분기는 `0x005CCC26`에서 시작해 로컬 씬 정리 후
  `FUN_005CE680`을 호출한다.
- `FUN_005CE680`은 메뉴 mode별 정리를 마치고 모든 분기에서
  `FUN_0059D150(this, 0)`을 호출한다.
- `FUN_0059D150`은 현재 캐릭터 상태를 직렬화하고 먼저 `C2S 0x0007`을
  보낸 다음, false 경로에서 `FUN_0059D760(2, 0, 0)`으로
  `C2S 0x0002` 0바이트를 보낸다. 따라서 이 패킷은 캐릭터 로그아웃 및
  캐릭터 선택 화면 복귀 요청이다.
- mode-0 수신 dispatcher `FUN_0059DD20`의 case 2는
  `FUN_0059D150(this, 1)`을 호출한다. 따라서 서버 ACK는 `S2C 0x0002`이다.
- 해당 handler는 payload를 읽지 않으므로 최소 안전 ACK payload는 0바이트다.
- ACK 이후 true 경로는 다시 `C2S 0x0007`을 보낸 뒤
  `FUN_0059D760(1, 0, 0)`으로 `C2S 0x0001` 0바이트를 보낸다.
  이 흐름의 `C2S 0x0001`은 단순 disconnect echo가 아니라 logout completion이다.

## VERIFIED — pre-fix live failure evidence

- `logs/browser_server_9200.out.log`의 현재 세션에서 `C2S 0x0007` 196바이트
  상태 저장 직후 `C2S 0x0002` 0바이트가 관측됐다.
- 구현 전 `azrok_server.py`에는 C2S 0x0002 handler가 없어 이를 `NEW opcode`로
  기록하고 무응답 처리했다. 이후 client heartbeat만 계속되어 캐릭터 선택 화면
  복귀가 진행되지 않았다. 현재 구현 상태는 아래 섹션을 따른다.

## Conservative implementation contract

구현 시 다음 순서를 지켜야 한다.

1. `C2S 0x0002`는 payload가 정확히 0바이트일 때만 받는다.
2. 직전 `0x0007` canonical 저장 결과를 보존한다.
3. 선택 캐릭터 lease와 active actor/room 상태만 해제한다.
4. 브라우저 바인딩, 원본 account identity, 계정의 4개 캐릭터 roster는 유지한다.
5. `S2C 0x0002` 0바이트 하나만 응답한다.
6. 자연 후속 `C2S 0x0007`, `C2S 0x0001`을 completion으로 처리한다.
7. **#585 정정:** `S2C 0x0000` roster 재전송은 로딩 화면을 끝내지 못한다.
   completion에는 원본 종료 handler를 타는 `S2C 0x0001[00]`을 응답하고 웹
   실행기가 서버 선택 화면으로 복귀시킨다.
8. 현재 브라우저 서버의 `--auto-select-existing` 보조 기능은 명시적 로그아웃 뒤에는
   반드시 억제한다. 그렇지 않으면 4슬롯 로비에 복귀한 뒤 슬롯 0이 다시 자동 선택되어
   사용자가 다른 캐릭터를 고를 수 없다.

## VERIFIED — server implementation and automated contract (2026-08-26)

- `azrok_server.py` 가 정확히 0바이트인 C2S `0x0002`만 선택된 캐릭터
  lease 상태에서 수락하고 S2C `0x0002[0B]`를 응답한다.
- 로그아웃 처리는 `account_raw`, `account_name`, `lobby_slots`,
  `account_has_characters`, 기존 canonical 저장 파일을 보존한다.
- 선택 key/lease와 Plaza 원격 액터, OX 참여, room/position 메타데이터만
  해제한다. Plaza peer에게는 기존 검증된 S2C `0x0067` 단일 액터 제거를
  사용하며 OX mode-2 처리를 state-1 relay와 섞지 않는다.
- ACK 후 자연 후속 C2S `0x0007[196B+]` 및 `0x0001[0B]`를 completion으로
  수락하되, 해제된 placeholder identity로 다시 저장하거나 lease를 복구하지
  않는다.
- `explicit_character_logout` 상태와 `auto_select_existing_sent`를 동시에 사용해
  명시적 로그아웃 뒤 슬롯 0 자동 선택을 억제하고, 사용자의 성공한 C2S
  `0x0004`/`0x0005` 생성·선택에서만 해제한다.
- protocol registry에 C2S/S2C `0x0002` 양방향 exact-0B 계약을 등록해 더 이상
  unknown opcode로 분류하지 않는다.
- 자동 계약 시험은 malformed `0x0002` 거부, 기존 canonical 바이트 보존,
  2슬롯 roster 보존, Plaza peer `0x0067`, completion `0x0007/0x0001`, 다른
  슬롯 재선택을 검증했다. `test_server_contract_layers` 110개와 room/content/registry를
  포함한 150개 집중 시험이 통과했다.

## SUPERSEDED live acceptance result

- 실제 원본 화면은 빈 `S2C 0x0002` 뒤 같은 프로세스의 4슬롯 UI로 복귀하지
  않았고, 후속 heartbeat의 `S2C 0x0000` 재전송 뒤에도 로딩 화면에 머물렀다.
  상세 라이브 증거와 수정은 #585에 있다.

## NOT VERIFIED

- 원본 서버가 `S2C 0x0002`에 정확히 0바이트를 썼는지. 클라이언트 handler가
  payload를 읽지 않으므로 0바이트가 최소·충분하다는 것까지만 확정됐다.
- 웹 서버 선택 화면 복귀 뒤 다른 슬롯 선택→PatHouse/Plaza 재진입의 전체 동적 수락.
