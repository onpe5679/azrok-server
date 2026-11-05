> **SUPERSEDED by 562.** Depth guard 이후에도 물리 조합에서 동일 stack overflow가 재현됐고 FIFO depth가 29까지 증가했습니다. callback 방식 전체를 기본 경로에서 철회했습니다.

# 561. Wine XIM preedit callback reentry guard (2026-08-08)

## VERIFIED - failure boundary

- 사용자 물리 한글 입력 순간 화면에 `Exception thrown, see JavaScript console`이 표시되었습니다.
- 같은 시각 worker 콘솔은 `Uncaught RangeError: Maximum call stack size exceeded`였습니다.
- 따라서 #560의 첫 물리 수락은 실패했으며 정적 callback 계약 통과만으로 성공을 주장할 수 없습니다.

## VERIFIED - correction

- Wine preedit callback은 메시지를 동기 처리하면서 같은 synthetic key의 `XmbLookupString`으로 재진입할 수 있습니다.
- guest libX11에 callback depth를 두고, callback 내부 nested lookup이 private action `0x7101..0x7104`를 다시 만나면 callback을 호출하지 않고 `XLookupNone`으로 반환하도록 했습니다.
- 바깥 lookup만 start/draw/done action을 소유합니다.
- 새 libX11 SHA-256은 `65CC717A5F4A7943BAC157DE6694662076E55FDED705A1249A5A1B6882A776DF`입니다.
- 새 immutable root는 `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim31preeditreentry1.zip`, SHA-256은 `128BE4E769EBB5FD23A4E167EF7E3BF1B4728FF2167FC522CFBE970697D4209B`입니다.
- LAN HTTPS HEAD 200, packaged lib hash 일치, focused 42 tests 통과, 새 부팅에서 JIT 94 groups/30550 blocks 등록까지 확인했습니다.

## NOT VERIFIED

- 수정 후 사용자 물리 키보드 `안녕`의 자연스러운 `ㅇ → 아 → 안` preedit 표시와 최종 확정.
- 수정 후 첫 composition update에서 새 시각의 worker exception이 발생하지 않는지 최종 사용자 수락.
