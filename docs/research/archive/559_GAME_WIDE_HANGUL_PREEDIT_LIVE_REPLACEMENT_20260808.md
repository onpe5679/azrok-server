> **SUPERSEDED by 560.** `compositionupdate`를 확정 문자로 넣고 synthetic Backspace로 교체하는 방식은 물리 입력 `안녕 -> ㅇ안` 회귀로 기각됐다.

# 559. Game-wide Hangul preedit live replacement (2026-08-08)

## Scope

#558의 game-wide XIM/ACP 949 경로는 조합이 끝난 한글을 원본 Edit에 넣지만,
페이지가 `compositionend`만 전달해서 마지막 조합 글자가 Space/ASCII 전까지 보이지
않는 지연을 없앤다. `Azrok.exe`와 게임 데이터는 수정하지 않는다.

## VERIFIED - root cause

- 기존 페이지는 `compositionstart`에서 플래그만 세우고 `compositionupdate`를 게스트에
  보내지 않았다. `compositionend`에서만 `boxedwine_inject_text_utf8()`를 호출했다.
- 따라서 브라우저가 `ㄱ -> 가 -> 간`을 조합하는 동안 원본 Edit에는 직전 commit까지만
  보이고, 마지막 음절은 조합 종료를 유발하는 Space/ASCII 뒤에야 나타났다.
- 페이지에서 Backspace를 SDL 이벤트로 큐잉하고 새 문자열을 XServer에 즉시 넣는 방식은
  삭제보다 삽입이 먼저 실행될 수 있어 안전하지 않다.

## VERIFIED - implementation

- 새 host export `boxedwine_replace_preedit_utf8(text, eraseCharacters)`가 하나의 동기
  XServer transaction 안에서 이전 미리보기 scalar 수만큼 Backspace press/release를
  보낸 뒤 새 UTF-8 scalar들을 기존 fake-XIM FIFO/key 경로로 넣는다.
- 페이지는 non-chat 원본 입력 컨트롤에서 각 `compositionupdate`를 이 export로 교체하고,
  `compositionend` 값이 마지막 미리보기와 같으면 중복 삽입하지 않는다. 취소/변경된
  end 값만 마지막으로 원자 교체한다.
- Plaza의 browser-owned chat input은 브라우저 자체 preedit UI를 이미 사용하므로 기존
  chat 경로를 유지한다.
- 새 immutable runtime은
  `boxedwine.upstreamjit64fn6inlineabi2korean7preedit1`; build id는
  `ime-preedit-atomic-v1-20260808`이다. 이전 korean6 runtime은 rollback용으로 보존한다.

## VERIFIED - build, serve, and boot

- JS SHA-256: `6DFE15D11FE05ABFAC6A2D4A67B63DB77C304F6BC2F6BD8A0B1B17F1028157F3`
- WASM SHA-256: `B68BA1D9296ABCA9D5B677A99DA29B3AE72C57FE3A204AEC9BA266D03E724521`
- WASM public export가 minified raw export `Fe`에 연결되고 함수임을 Node instantiate로
  확인했다.
- 같은 instance에서 currentabi1 map/capacity가 `12968408/262144`임을 확인했다.
- LAN HTTPS에서 받은 JS/WASM의 크기와 해시가 디스크와 일치했다.
- 사용자 LAN 탭에서 korean7/build id가 실제 로드되고, JIT 94 groups/30,550 blocks를
  등록한 뒤 원본 클라이언트가 3D PatHouse까지 정상 렌더링했다. ABI mismatch는 없었다.
- focused XIM/page tests 39개와 전체 `tools/test_*.py` 246개가 통과했다.

## NOT VERIFIED

- 자동 브라우저 입력은 Windows의 실제 한글 keyboard-layout composition을 만들지 못한다.
  완성형 `간`의 guest FIFO 전달/소비는 확인했지만, 사람 키보드로 누른 `ㄱ -> 가 -> 간`
  세 화면의 즉시 갱신은 사용자 수락 입력을 기다린다.
- 게임 안의 모든 custom text widget 전수 시험. 일반 원본 ANSI Edit는 공통 page/XIM
  경로를 사용하지만 자체 디코더를 가진 별도 위젯은 독립 확인이 필요하다.

## Acceptance

1. 캐릭터 생성 이름 Edit 또는 다른 원본 Edit에 포커스를 둔다.
2. 한글 자판으로 `ㄱ`, `ㅏ`, `ㄴ`을 차례로 누른다.
3. 원본 Edit가 다른 commit 키 없이 `ㄱ -> 가 -> 간`으로 즉시 바뀌어야 한다.
4. Space/ASCII 뒤에 중복 음절이 생기지 않아야 하며 Backspace/취소도 잔상을 남기지
   않아야 한다.
