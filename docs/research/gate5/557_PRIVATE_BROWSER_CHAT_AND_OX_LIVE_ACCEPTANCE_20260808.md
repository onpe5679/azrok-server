# 557. Private browser Hangul chat and OX live acceptance (2026-08-08)

> **IME 부분은 558에서 PARTIALLY SUPERSEDED되었습니다.** 이 문서의 Plaza
> 브라우저 채팅 릴레이와 OX 수락 결과는 유효하지만, 원본 ANSI 입력 컨트롤의
> 공통 원인은 558의 BoxedWine 환경 인자 따옴표 오류와 Wine ACP 949 복구입니다.

## Scope

Finish Plaza Hangul chat without patching `Azrok.exe`, preserve the original
client's receive/render behavior, remove the long blank cold-boot interval, and
re-run the supported OX lifecycle instead of hiding or resuming exceptions.

## VERIFIED - actual Hangul loss boundary

- Browser composition, BoxedWine's UTF-8 FIFO, fake XIC, `XmbLookupString`,
  `XLookupChars`, and Wine UTF-8-to-Unicode conversion all ran successfully in
  the earlier probes. The remaining failure was the original game's ANSI Edit
  control: XIM/VK_PACKET/`EM_REPLACESEL` variants either produced lossy text,
  literal physical-layout keys such as `l4j10`, or no accepted text.
- The production chat text owner is now the browser input shown over the bottom
  of the game canvas after Enter. Printable key events and Backspace do not
  leak into SDL while that input is open. The next Enter closes the host input,
  sends the original guest Enter control key, and submits the finished string.
- Before opening the overlay, `GET /api/private-chat-state` authenticates the
  private-session ticket, resolves its durable account binding, and requires
  that account's latest connected player to be in Plaza (`room_kind == 27`).
  A final character-select check returned `data-private-chat-ready=0`, kept the
  input at `opacity:0`/`pointer-events:none`, and preserved the original Enter.
- `POST /api/private-chat-say` accepts only a valid HMAC private-session ticket
  from loopback/RFC1918/Tailscale clients. It resolves the durable browser-to-
  account binding, requires a connected player for that account, rejects
  controls/non-CP949 text and messages over 120 CP949 bytes, then calls the
  loopback control API `/api/chat/say`.
- The core uses the ordinary S2C `0x006A` chat packet. The original client still
  owns chat decoding, the Plaza log, and the speech-bubble renderer; only the
  browser-to-guest ANSI Edit step is bypassed.

## VERIFIED - live browser acceptance

- A private HTTPS browser session loaded the production
  `boxedwine.upstreamjit64fn6inlineabi2korean6chat1` runtime and
  `...acp949-xim3cp949input1.zip` root, selected persisted character `Azrok1`,
  and rendered PatHouse 3D followed by Plaza 3D.
- In Plaza, the host input visibly held `한글 입력 성공`. On Enter,
  `#runtime-status` reported `data-private-chat=sent` and entity `43`.
- The original client visibly rendered `한글 입력 성공` both in the actor's
  speech bubble and in its lower-left Plaza chat log. This is direct visual
  acceptance, not a static-build or packet-only claim.
- The final Plaza-gated build was re-accepted on entity `44`: the overlay
  visibly held `최종 한글 채팅`; after Enter, `data-private-chat=sent`, entity
  `44`, and an empty error attribute were recorded. The original client then
  displayed that exact Korean string in both its speech bubble and chat log,
  with no physical-layout text such as `l4j10` leaking into the game.

## VERIFIED - cold-boot progress and asset streaming

- The earlier blank/stalled boot was reproduced as a Python asset-server
  `MemoryError` while copying the 157 MB app ZIP. Full responses previously
  delegated to the generic copy helper; range responses alone were bounded.
- Full and range responses now both stream in at most 1 MiB chunks. The two
  private 8765 listeners were restarted without restarting the shared 9200
  core or 9201 bridges.
- A fresh browser then downloaded the app/root/JIT assets, showed the elapsed
  `Azrok 시작 중` overlay, reached the Hansol logo, and entered the game. No new
  `MemoryError` appeared; each asset listener remained near 29 MB working set.

## VERIFIED - OX lifecycle, no exception ignore

- Starting from that same rendered Plaza client, `/api/ox/enter` sent the
  supported portal control reply and waited for the client's natural C2S
  `0x00C8` admission. The client rendered OX Quiz mode 2 and the server entered
  the `question` phase for `1 + 1 = 2`.
- With no answer, the server made the player a loser, completed the round, and
  the client returned naturally to the rendered Plaza through C2S/S2C `0x0064`.
  Entity `43` stayed connected and its room returned to `plaza (0064-only)`.
- The browser console gained no `Unhandled exception`, page fault, SEH crash,
  or runtime abort during entry, question, exit, and eight seconds of stable
  post-return rendering. The old acknex invalid-BMAP fault from #534/#548 was
  not reproduced on this supported handshake.
- No `OX_IGNORE`, blanket SEH continuation, dummy BMAP, or original-binary
  patch was introduced. If a future natural sign-click reproduces a fault, the
  exact failing asset lookup still must be captured rather than skipped.
- The complete lifecycle was repeated after the Plaza-only chat gate on entity
  `44`. The client rendered `[OX] 1 + 1 = 2`; the server recorded entity `44`
  as the loser, returned it to `room_kind=27`, and kept it connected. The full
  browser-output delta through ten seconds of post-return Plaza rendering had
  no match for unhandled exception, page fault, `err:seh`, runtime abort, or
  crash, and the OX scheduler reported no automatic error.

## Package identity and regression checks

- Chat runtime JS SHA-256:
  `7F8BA53B8A6D422D24AE3AF49B168D2D9CCC7BA04010EC25E3C074764C9AF38D`
- Chat runtime WASM SHA-256:
  `3A1A903245430B029C0FC19CC46C27F53DB238A923CF422C8B69A7E3E3515467`
- Focused private-admission/page/XIM tests: **44/44 passed**.
- Full `tools/test_*.py` discovery: **240/240 passed**.

## Remaining separate finding

- **NOT FIXED in this change:** Korean names in the character-creation Edit
  control still use the original ANSI input path. The browser overlay is
  deliberately Plaza-only; character select/create Enter was checked only to
  ensure the overlay stays hidden and does not steal the original control.
- **VERIFIED reproduction, NOT FIXED here:** a newly created stage-0 `player2`
  character completed C2S `0x0004` and received the 472-byte S2C `0x0007`, but
  displayed the lobby background under the in-game HUD instead of PatHouse 3D.
  This is distinct from Hangul chat and the now-passing persisted-character OX
  route. Its captured entity-42 packet sequence must be used for the next
  fresh-bootstrap differential; do not attribute it to JIT/package download.
