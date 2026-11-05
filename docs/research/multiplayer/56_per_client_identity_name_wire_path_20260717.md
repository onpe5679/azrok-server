# Per-client identity: where each displayed name comes from (2026-07-17)

Parallel static trace (Ghidra, `Azrok_original.exe`) of the "both players are Azrok1,
self is Guest" problem, done while Codex worked the growth-gate/exit track. No binary
patch, no client-memory write. Every claim below is from a decompiled body; the one
inferred item is marked.

## Summary

There are TWO independent name fields with opposite controllability:

| Name shown | Storage | Set by | Server can change today? |
|---|---|---|---|
| **Own self** (nameplate over your pet) | `localPlayer + 0xC8`, 13-byte string | "Guest" default, or local UI name-entry | **NO** — no S2C opcode carries it |
| **Remote peer** (nameplate over others) | roster record `+7` → `actor + 0x307` | S2C `0x0066` record only | **YES** — fully server-controlled |

So distinct names *between* players are fixable server-side right now; the self-nameplate
reading "Guest" is a client-local artifact and cannot be corrected through any existing
S2C opcode.

## 1. Self name — client-local, hardcoded "Guest", not server-settable

- The string "Guest" appears exactly once in the binary (`0x006A646C`).
- `SetLocalName` = `FUN_00528690`: `strncpy(this + 0xC8, name, 99); (this+299) = 0;`
  → the self name buffer is `localPlayer + 0xC8`. Getter `FUN_005286E0` returns `this + 0xC8`.
- Defaults written by `FUN_005AADC0` (player-info init) and `FUN_0059CE80` (CJSLogic ctor,
  `SetLocalName("Guest")`).
- **`HandleS2C_0064_ApplyAuthoritativeSelf` @ `0x00615650` has NO name field and NO string
  copy** — it writes only self_id (`payload+1`), position (`+6/+10`), selectors (`+0x12/+0x13`),
  room/scene (`+0x14..0x1A`). VERIFIED. This is exactly why self stays "Guest": the authoritative
  self packet never touches `+0xC8`, and the UI name-entry step that would overwrite it is skipped
  in our automated boot.

## 2. Remote name — roster record offset +7, 13 bytes (VERIFIED against live capture)

`RemoteActor_InitFrom0066Record` @ `0x005243E0` field map of the 0x1A-byte record:

```
+0     record_kind            (used by batch handler 0x00615B50)
+1  d  actor_id            -> actor+0x2F8, +0x301
+5  b  model/spawn-variant -> actor+0x9D  (if >0x13: variant flag, then -0x14)
+6  b                      -> actor+0xA1
+7  STRING display name    -> String_CopyZ(actor+0x307, record+7)   [max 13 bytes, 0x07..0x13]
+0x14..0x17  4 bytes       -> actor+0x314..0x317
+0x18/+0x19  pair_left/right
```

`String_CopyZ` @ `0x006543B0` is an unbounded strcpy; the nameplate TextSprite is built right
after, so the rendered remote name = `actor+0x307` = `record+7`.

Live-capture confirmation (`captures/packets_20260717_140843.txt`, seq #0):
```
S->C 0x0066 payload: 0a 03000000 02 00 | 41 7a 72 6f 6b 31 00 00 00 00 00 00 00 | 02000000 | ff 00
                     kind id=3   md    | "Azrok1\0" at +7 (13 bytes)             | +0x14    | pair
```
A second record in the same capture has `id=2` but the SAME name "Azrok1" — proving the server
currently emits one identical name in every roster record. VERIFIED: name is at +7, 13-byte field.

## 3. Login / name source (client side)

- Display name is sourced from a **UI text field** at `uiObj+0x3A` (name-entry input box), submit
  handler `FUN_0050ACB0`. Validation `FUN_00528710`: no spaces, min length 4 (else error 0x10).
  On success it calls `SetLocalName(+0xC8)` and `strncpy(buf, name, 0xD)` — 13-byte wire width,
  same as the roster field.
- `SendC2S_0064_LocalBootstrapStatus` @ `0x006130B0` sends self name to server:
  `strncpy(dst, FUN_005286E0(), 0xD)` (13 bytes from `localPlayer+0xC8`).
- The literal C→S `0x0000` login account name ("player") and auth ("localauth") are a DIFFERENT
  value from the display name (self nameplate shows "Guest", not "player"). They are absent from
  the binary string table because they are runtime-injected — see §5. **The 0x0000 builder is now
  fully traced (VERIFIED):** `FUN_00593d90` @ `0x00593D90`:
  ```
  buf[0]    = 0                       // leading byte
  String_CopyZ(buf+1 , user);         // NAME field, 13 bytes (buf+1..0xD), NUL-terminated, NOT zero-padded
  String_CopyZ(buf+14, auth);         // AUTH field (buf+0xE..)
  send(opcode 0, buf, 0x6A);          // 106-byte payload
  ```
  where `user` = `[[engine+0x998]+0xC]` and `auth` = `[[engine+0x9AC]+0xC]` (double-indirect WDL
  STRING slots), read by `FUN_004EDB10` → `FUN_00508B30` (this=gm; user→gm+0x3179E, auth→gm+0x317BE)
  → `FUN_00594130` → builder.
- **Capture-read correction:** the auth is "localauth", NOT "H0localauth". In
  `00|70 6C 61 79 65 72 00 FF FF FF FF 48 30|6C 6F 63 61 6C 61 75 74 68 00`, the NAME field is the
  13 bytes `buf[1..0xD]` = "player\0" followed by uninitialized STACK GARBAGE (`FF FF FF FF 48 30`)
  because `String_CopyZ` stops at the NUL and does not zero-pad. The real auth begins at buf+0xE =
  "localauth". VERIFIED by byte-match to the live capture.

## 4. The gap — what the server must do

- **Peer names (the "both Azrok1" bug): fix server-side now.** Assign a distinct name per
  connection and write it into `+7` of every `0x0066` record describing that actor to OTHER
  clients. 13-byte NUL-terminated. No client patch. This is the actionable item.
- **Self nameplate ("Guest"): not server-fixable through current protocol.** Options: (i) drive
  the name-entry UI so it calls `SetLocalName` — this is the Blocker A / Frida input lane, not a
  protocol fix; (ii) client patch — out of scope for zero-patch server work.

## 5. Server side — the "player" login value and where the name actually comes from

Confirmed in our own code, not the binary:

- **`azrok_launcher.py`** injects the login identity as engine WDL string variables (NOT the
  command line, in the default mode): `USERNAME = 'player'`, `AUTHKEY = 'localauth'`,
  `ENGINE_OFFSET_USER = 0x998`. This is why "player"/"localauth" are absent from the binary's
  string table (§3) — they are runtime-injected. Matches the live watch:
  `engine_998_string="player"`, `engine_9ac_string="localauth"`, `engine_9a0_string="127.0.0.1:9207"`.
- **`azrok_server.py` never uses the 0x0000 login account name as the display name.** The display
  name in `client_meta['name']` is set from:
  - C→S `0x0005` slot/continue: `meta['name'] = meta.get('name') or 'Azrok1'` (~line 2852) —
    a hardcoded **'Azrok1' default**;
  - C→S `0x0007` bootstrap blob: `meta['name'] = name[:12]` when a name parses, else 'Player'.
- **The roster infrastructure is already per-connection.** `_send_room_roster` (~line 2957) does
  `name_raw = str(meta.get('name') or 'Player')...` and passes it to
  `_build_state_0066_actor_record(entity_id, char_type, name_raw)` → record +7. So each peer's
  name is emitted from ITS OWN `meta['name']`.

**Root cause of "both are Azrok1": not the wire, not the client — the server assigns the same
default name to every connection.** Both clients boot the same way and both land on the 'Azrok1'
default; the server has the plumbing to send distinct +7 names but no distinct SOURCE.

**Fix (server-side, zero client patch):** give each connection a distinct `meta['name']`. Two paths:
- (a) sequential assignment (conn 1 → "Azrok1", conn 2 → "Azrok2", like `next_actor_id`) — simplest,
  self-contained;
- (b) launcher injects a per-client `USERNAME` into engine+0x998, and the server reads the 0x0000
  account name into `meta['name']`. **This is now fully confirmed end-to-end (VERIFIED):**
  `launcher engine+0x998 → C→S 0x0000 NAME field (FUN_00593d90) → server 0x0000 parse → meta['name']
  → S→C 0x0066 +7 → peer nameplate`. Cleaner than (a) because identity anchors to launcher config,
  not connection order. **Server-side 0x0000 parser has two hard constraints:**
  1. Read NAME as a C-string — stop at the first NUL. The 13-byte field is NOT zero-padded; a
     fixed-width read ingests the `FF FF FF FF 48 30` stack garbage (see §3).
  2. Keep injected usernames ≤ 12 chars (13-byte field incl. NUL). "azrok1"/"azrok2" fit.
Either way the self-nameplate "Guest" is unaffected (§4) — that stays a UI-track item.

## Not determined

- The `<len><opcode>` header serializer (`FUN_00592140`) was not separately decompiled to watch it
  stamp `0x0000` — but the 0x0000 builder's payload is byte-identical to the live capture, so the
  opcode identity is direct-by-match, not a gap in the dataflow.
- Whether the launcher writes the STRING pointer vs the char data at the `+0xC` the read lands on.
  Empirically it resolves ("player" reaches the wire), so the current injection is already correct;
  just keep it consistent if the offsets change.
- Whether the self (`+0xC8`) and remote (`+0x307`) nameplates share the same TextSprite draw
  object — each is built from its own field, but the two draw calls were not diffed.

Related: [[project-multiplayer-milestone]], note 40 (roster wire vs client state), note 44
(per-client protocol state).
