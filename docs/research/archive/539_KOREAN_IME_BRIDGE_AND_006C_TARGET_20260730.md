# 539 한글 입력 브리지 + C2S 0x006C 는 "대상" 액터 id 였다 (2026-07-30)

> **PARTIALLY SUPERSEDED by 653.** 이 문서의 2세션 패킷 실측은 유효하지만, §3의 “정보 보기 버튼은 패킷을 만들지 않는다”와 로컬 액터 데이터만으로 정보창을 연다는 해석은 원본 버튼 함수 디컴파일에 의해 뒤집혔습니다. 버튼이 활성화되어 눌리면 별도의 C2S 0x006C가 나갑니다.

날짜: 2026-07-30
선행: #538(이동), #529
근거: 2세션 실측(opcode 히스토그램·이벤트 링) + `plaza_dump.txt` 디컴파일
원본 실행파일·게임 자산 무수정.

---

## 1. 한글 — 렌더는 처음부터 됐다. 안 되는 건 "조합" 뿐 (VERIFIED)

라이브 세션에 EUC-KR S2C `0x006A` 를 직접 주입했다.

```text
S->C 0x006A  kind=0 mode=0 actor=2 name='Player'
             msg='안녕하세요 한글 테스트' (cp949)
```

**말풍선과 채팅 로그 모두 정상 출력.** (`artifacts/audio/korean_chat_test.png`)

즉 폰트·인코딩·렌더 경로에는 아무 문제가 없다.
막힌 곳은 단 하나 — **BoxedWine 안에 IME 가 없어서 게임 입력창이 ASCII 만 받는다.**
브라우저 키 이벤트(`Input.insertText`, `vk=229`, EUC-KR 바이트쌍)가 전부 실패했던 이유가 이것이다.
그 경로들은 전부 "에뮬레이트된 윈도우의 키보드"를 거치는데, 거기엔 한글을 조합해 줄
IME 가 존재하지 않는다.

### 수정 — 호스트 IME 브리지 (적용됨)

브라우저에는 IME 가 있다. 조합이 끝난 문장만 받아서 **평소 채팅과 똑같은 경로**로 내보낸다.

- `azrok_server.py`: `say_as_player(entity_id, message, chat_type, flag)` 신설.
  `_relay_chat_0068` 과 동일한 수신자 선정·id 매핑(`본인=1`, 나머지는 서버 entity id)·
  `_build_state_006A_text_record` 를 그대로 쓴다. cp949 인코딩 불가 문자는 거부.
- `azrok_control.py`: `POST /api/chat/say {entity_id, message}` + 제어판 "한글 채팅" 카드.
  `isComposing` 가드로 **한글 조합 확정 Enter 가 전송으로 새지 않게** 했다.

```text
POST /api/chat/say {"entity_id":2,"message":"한글 입력 브리지 테스트입니다"}
  -> {"ok": true, "message": "delivered to 2 client(s)"}
```

2세션 모두에서 말풍선·로그 정상. (`artifacts/audio/say_A.png`, `say_B.png`) **VERIFIED**

> 한계: 게임 자체 입력창에 글자가 찍히지는 않는다. 그건 IME 없이는 불가능하다.
> 채팅 기능 자체는 완전히 동작한다.

## 2. 캐릭터 클릭이 먹통이던 이유 (VERIFIED)

opcode 히스토그램에서 클라이언트가 **요청을 보내고 있는데 서버가 아무 답도 안 하는** 게 보였다.

```text
eid=2:  C->S 0x006C = 10      S->C 0x006C = (없음)
eid=3:  C->S 0x006C = 7       S->C 0x006C = (없음)
```

이벤트 링이 원인을 정확히 짚어 줬다.

```text
community        eid=2  requested_self_id=1     (자기 캐릭터 클릭)
community_reject eid=2  "0x006C claimed unexpected self id 3"   (상대 클릭)
community_reject eid=3  "0x006C claimed unexpected self id 2"   (상대 클릭)
```

**C2S 0x006C 의 dword 는 "보내는 쪽이 주장하는 자기 id" 가 아니라 "대상 액터 id" 다.**
모든 클라이언트는 자기 자신이 액터 1 이므로,
자기 캐릭터를 클릭하면 1, 상대를 클릭하면 그 상대의 서버 entity id 가 실린다.
서버는 1 이 아닌 값을 전부 **사칭으로 간주해 버렸다** — 그래서 상대 캐릭터를 클릭하는
모든 요청이 통째로 폐기됐다.

### 수정 (적용됨)

`_relay_community_006c` 가 대상 id 를 받아 `self` / `visible_peer` / `unknown` 으로 분류한다.
`unknown`(가시 범위 밖)만 거부. `community_target_actor_id` 로 관측 가능.

> **SUPERSEDED by 653.** Only the information-button/no-server-response conclusion in section 3 is superseded. Original captures and unrelated historical findings are preserved.

## 3. 아직 못 고친 것 — S2C 0x006C 의 state/toggle (NOT VERIFIED)

`FUN_00615410`(S2C 0x6C 핸들러):

```c
if (record.actor_id != my_self_id && lookup(record.actor_id) != 0) {
    if (record.toggle < 2) {
        actor->0x336 = record.state;     // FUN_00615310
        actor->0x33a = record.toggle;    // FUN_006153E0
        FUN_00527760(0x30, 0);           // 상태 0x30 진입
    } else { FUN_00527720(); FUN_00527970(); }
}
```

`FUN_00527760` 은 `DAT_006D9D48 + toggle*0xC + state*0x18` 로 **애니메이션 테이블**을 인덱싱한다.
즉 S2C 0x006C 는 "대상 액터에게 커뮤니티 동작을 재생시켜라" 이고,
`0x30` 은 `thunk_FUN_00524EB0` 이 걷기 갱신을 거부하는 바로 그 상태값이다.

**C2S 는 4바이트(대상 id)뿐인데 S2C 는 state·toggle 2바이트를 더 요구한다.**
그 두 바이트가 어디서 오는지 아직 근거가 없다. 지어내면 모든 액터가 엉뚱한 동작을 한다
(#537 에서 이미 한 번 저지른 실수). 그래서 S2C 중계는 여전히 보류다.

`0x006C` 가 "정보 보기" 창까지 담당하는지도 미확정 — 클릭 종류별 원문 바이트가 필요하다.
그래서 `_capture_c2s_raw` 를 넣어 **0x0016/0x0066/0x0067 을 뺀 모든 C2S 를 hex 로 이벤트 링에 기록**하게 했다.
`/api/events` 에서 `kind='c2s_raw'` 로 조회.

### 측정 결과 (VERIFIED — 2026-07-30)

사용자가 (a) 자기 캐릭터 클릭, (b) 상대 클릭 후 "정보 보기" 클릭 을 수행했다.
`c2s_raw` 전량:

```text
eid=3  0x006C  len=4  hex=01000000     <- 자기 캐릭터 클릭 → 대상 1
eid=3  0x006C  len=4  hex=02000000     <- 상대 캐릭터 클릭 → 대상 2 (peer entity id)
(그 외 0x0000/0x0008/0x0017/0x0064 는 로그인·캐릭터 선택 시퀀스)
```

> **"정보 보기" 버튼 자체는 패킷을 전혀 만들지 않는다.**
> 와이어에 나오는 것은 캐릭터 클릭 1회당 `0x006C` 1개뿐이다.
> 따라서 정보 창은 서버 응답이 아니라 **클라이언트가 이미 갖고 있어야 할 액터 데이터**로 열린다.
> 그리고 대상 id 해석은 위 §2 대로 확정 — 자기=1, 상대=peer entity id.

> **SUPERSEDED by 540 (0x0066-self 송신 해법 부분만).** 0x0066 self-id는 fixed self 이름/외형을 복사하지 않는다. 이 절의 서버 상태/"Guest" 실측과 수동 주입 관찰은 보존하되, 원인과 해결책은 540을 따른다.

## 3.1 닉네임 불일치 — 자기 이름이 클라이언트에 전달되지 않는다 (VERIFIED)

사용자 보고: "서로 보이는 닉네임이 일치하지 않는다".

서버 상태는 자기모순이 없다. `server_state/` 파일명이 hex 로 그대로 말해 준다.

```text
a706c61796572_s0_c417a726f6b31_state_v1.json   account 'player'  -> character 'Azrok1'
a70656572313131_s0_c506c61796572_state_v1.json account 'peer111' -> character 'Player'
overview: eid=2 name='Azrok1' account='player' / eid=3 name='Player' account='peer111'
```

그런데 **두 클라이언트 모두 자기 이름을 "Guest" 로 표시한다.**
`"Guest"` 는 `azrok_server.py` 에도 `server_state/` 에도 **존재하지 않는다** — 클라이언트 기본값이다.

> 원인: 원격 액터 이름은 로스터 `S2C 0x0066` 으로 나가지만(그래서 상대 이름은 맞다),
> **자기 자신(액터 1)의 0x0066 레코드는 아무도 보내지 않는다.**
> `_send_room_roster` 의 `admitted` 목록은 peer 만 담고 self 를 제외한다.
> 그래서 각 클라이언트는 자기 이름만 기본값 "Guest" 로 남는다.

라이브 주입으로 이 채널을 확인했다. 세션 A 에 액터 id 1 짜리 0x0066 을 보냈더니
좌하단 정보판의 `이름:` 이 **Player → Azrok1 로 바뀌었다**.
즉 **자기 이름의 전달 경로는 액터 id 1 의 S2C 0x0066 이 맞다.** (`artifacts/audio/selfname_A.png`)

다만 손으로 만든 레코드(action=0x0A)는 라벨과 액터 구성까지 함께 흔들었다 —
상단 이름칸은 여전히 "Guest" 이고 액터가 하나 더 생긴 것처럼 보였다.
**action 바이트와 나머지 필드를 로스터 경로와 동일하게 맞춰야 한다.**
지어내지 말고 `0x00615B50` / `0x005243E0` 의 action 분기를 먼저 읽을 것 —
#537 에서 필드 의미를 넘겨짚어 회귀시킨 전례가 있다.

**NOT VERIFIED**: self 0x0066 의 올바른 action 값과 전송 시점(입장 직후 1회인지, 로스터마다인지).

## 4. 검증

```text
py_compile azrok_server.py azrok_control.py     PASS
tools/test_server_contract_layers.py            Ran 107  OK
  - test_community_accepts_a_request_aimed_at_a_visible_peer (신규)
  - test_community_rejects_bad_length_and_invisible_target
  - test_community_directional_layout_... (target_kind='self' 확인)
브라우저 2세션: /api/chat/say 한글 전달 2/2, 말풍선·로그 정상        VERIFIED
```
