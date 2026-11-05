# 547. Original fresh bootstrap and natural growth packet order (2026-08-07)

> **LIVE ACCEPTANCE UPDATE by 585.** `playable` 신규 캐릭터의 date=0 원본
> 부트스트랩을 복구한 뒤 수정하지 않은 클라이언트가 PatHouse 3D, HUD, 퀘스트
> UI까지 실제 렌더한 것을 확인했다. 전체 튜토리얼 완주는 여전히 미검증이다.

## Scope

Replace the high-level demo bootstrap with the original new-character path and
make the server accept the packet order emitted by the unmodified client.
This change does not patch `Azrok.exe` and does not manufacture a completed
tutorial or evolution state.

## VERIFIED — why the old `playable` profile was not original progression

- The prior profile sent the shipped level-25/EXP-33000 values and immediately
  seeded a kind-3 growth row.  A fresh account therefore bypassed the original
  baby tutorial rather than beginning at Azron stage 1.
- A live unmodified client emitted the natural growth order
  `0010 completion -> 0011 row removal -> 0007 evolution edge ->
  0010 proposal -> 0011 proposal`.  The server previously rejected the first
  0011 for arriving before 0007, then injected its own aux value and rejected
  the client's next proposal.

## VERIFIED — native fresh-character path

Ghidra decompilation of the current client established the following call
chain and data contracts:

- `HandleS2C_0007_LoadSetupBlob` imports the 472-byte restore payload, builds
  the packed date, and calls `FUN_005A8790(-1)` when that date is zero.
- `FUN_005A8790(-1)` creates the first local tutorial runtime row
  `kind=5, aux=212` for a stage-0 Azron.  The client then owns the original
  tutorial chain instead of the server pre-completing it.
- `Stats_ApplyLocalArchetypeSeed@005A3020` resets the fresh stat table, applies
  fixed values and species-specific stat 10..17 baselines, and selects IQ and
  hygiene inside species-specific native ranges.
- The original local seed leaves stat 56 at zero for every species.  Therefore
  the earlier header-species/stat56 mismatch is not proven to be the PatHouse
  3D sufficient cause and is not used as the original-profile fix.

## Implementation

- `playable` now builds the native fresh stat layout instead of reusing the
  shipped level-25 table.  Fixed values and both random ranges mirror the
  decompiled routine.
- Native C `rand()` process state is not reproducible across interrupted
  browser sessions.  The preservation server deterministically selects values
  inside the exact native ranges from private account/slot/name identity.  This
  RNG source is a server persistence policy; it is not claimed to reproduce a
  particular original `rand()` sequence.
- A truly fresh 0007 uses packed date zero and empty runtime rows.  This lets
  the unmodified client seed kind-5/212.  Once an authoritative snapshot is
  restored, the server sends a valid date so reconnect does not reseed it.
- The old pristine playable kind-3/aux-0 demo seed is migrated away only when
  there is no authoritative snapshot or completion history.
- A natural 0011 row removal may now be buffered until the following monotonic
  0007 evolution edge.  The server correlates and durably commits that pair,
  does not invent the next kind-3 row, and preserves the client's subsequent
  aux proposal.

## Verification

- Fresh types 0..3, 472-byte payload layout, date-zero tutorial trigger,
  all-empty runtime rows, reconnect date/snapshot authority, and shipped
  compatibility have focused contracts.
- The observed natural `0010 -> 0011 -> 0007 -> 0010 -> 0011` ordering and
  client aux preservation have transaction-layer contracts.
- Full tool test discovery: **216 passed**.
- The loopback core/GUI was restarted with `--content-profile playable`; live
  API reports PID 116420, `clients=0`, and `127.0.0.1:9200` only.  LAN and
  Tailscale asset/bridge listeners were not restarted or broadened.

## NOT VERIFIED

- The user's reported new-character PatHouse 3D visibility has not yet been
  visually retested.  Admission assets/JIT/D3D package parity is verified, but
  the visual symptom must not be declared fixed from server-state evidence.
- The complete five-step tutorial, every stage transition, Plaza entry, and
  late-game progression still require natural user-driven end-to-end captures.
  The server no longer skips their original starting path; full completion is
  not yet proven.
