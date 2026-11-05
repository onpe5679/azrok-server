# Azrok Plaza Reverse Engineering Notes

Short-form, agent-facing split notes now live under:

- `docs/research/README.md`

Historical split notes are archived under:

- `docs/archive/reverse_engineering/README.md`

Date: 2026-03-30
Target: `Azrok.exe`
Status: confirmed findings + current runtime observations

> Note:
> prefer `docs/research/` for the current canonical write-up.
> this file remains the raw chronological log.

## Summary

The earlier assumption that incoming packets were dispatched through `CLogicJSDB::vtable[3]` at `0x5927D0` was incomplete.

`0x5927D0` is indeed a stub, but the final runtime object is not left on the `CLogicJSDB` vtable. The constructor chain upgrades the object to a higher-level class, and packet reactions occur through that final vtable instead.

This explains why the game reacts to some server opcodes even though the originally identified slot looked empty.

## Confirmed Findings

### 1. The stub at `0x5927D0` is real, but not the final active handler

Confirmed in Ghidra:

- `0x5927D0` decompiles to an empty function.
- `0x6A6150` is the `CLogicJSDB::vftable`.
- In that table, slot `+0x0C` points to the thunk for `0x5927D0`.

So this part was correct:

- `CLogicJSDB::vtable[3]` really is a stub.

What was missing:

- the final object is promoted again later.

### 2. The runtime object becomes `CLogicManager`

Confirmed in constructor `0x593F30`.

Constructor flow:

1. `0x593F30` calls `0x593C40` first.
2. `0x593C40` calls the lower constructor chain and installs `CLogicJSDB::vftable`.
3. `0x593F30` then overwrites the main vtable with `CLogicManager::vftable`.

Important addresses:

- `CLogicJSDB::vftable`: `0x6A6150`
- `CLogicManager::vftable`: `0x6A618C`

This means packet processing at runtime should be read from the `CLogicManager` table, not from the earlier `CLogicJSDB` table.

### 3. The packet reaction path is through the final vtable slot, not the stub slot

Confirmed around `0x593E40`.

`0x593E40`:

- dequeues a packet from the ring buffer
- extracts `opcode`, `payload_ptr`, `payload_size`
- calls `(*vtable + 0x0C)`

That call looked like it should hit the stub when the object was assumed to still be `CLogicJSDB`.

But for the final `CLogicManager` vtable, slot `+0x0C` resolves to:

- `0x4D8720` thunk
- which jumps into
- `0x594310`

`0x594310` is the real packet reaction handler currently observed in the live object.

### 4. There is also a lower-level stream parser in `CClientPeer`

Confirmed around `0x61C0E0`.

This code:

- accumulates the TCP stream
- waits until 4 bytes are available
- interprets packet header as:
  - `u16 payload_size`
  - `u16 opcode`
- waits until full payload is available
- then calls `(*vtable + 0x14)` with:
  - opcode
  - payload pointer
  - payload size

So there are two distinct layers:

1. stream framing layer in `CClientPeer`
2. queue/dequeue/game-logic dispatch layer in the higher logic object

The earlier confusion came from following only the queue consumer and reading the wrong class vtable.

## Confirmed Opcode Behavior

### Server -> Client `opcode 0x0001`

Confirmed dangerous.

Observed behavior:

- if the server sends or echoes `0x0001`, the client prints the disconnect message and exits.

Recommendation:

- never send `0x0001` during login/loading experiments.

### Server -> Client `opcode 0x0002`

Confirmed to be an important transition trigger.

Observed runtime behavior:

- after receiving `0x0002`, the client proceeds into the next stage
- then emits:
  - `0x0007`
  - `0x0001`
  - repeated `0x0017`

Relevant handler:

- `0x59DD20` routes opcode `2` to `0x59D150`

What `0x59D150` does:

- kicks internal transition logic
- triggers outgoing client packets through `0x59D760 -> 0x593D10 -> 0x592600`

This matches the live observation that `0x0002` is what pushes the client into loading-related behavior.

### Server -> Client `opcode 0x0003`

Confirmed to be more than a 1-byte ACK.

Important path:

- `0x594310` dispatches by internal state
- when state is `1` and `this+0x163D8 != 0`, the extra path `0x00613740` runs
- in that path, `opcode 3` calls `0x00615610(param_3 + 1)`

What that means:

- byte `0` of the payload looks like a small status/flag
- bytes `1..` are treated as a NUL-terminated C string

Evidence:

- `0x00615610` forwards the pointer to helper routines
- `0x005D4070` copies that string into an object buffer using `strcpy`-like logic (`0x006543B0`)
- then it arms loading-related state/timers/flags

Practical conclusion:

- sending server `0x0003` as just `b"\\x01"` is likely too empty
- a better experimental draft is:
  - `[0x01]["Data\\\\Space\\\\Plaza\\x00"]`

Reason for that candidate string:

- `Data\\\\Space\\\\Plaza` exists as a baked-in game string in the binary
- it matches the loading/space transition context much better than an empty payload

### Server -> Client `opcode 0x0007`

Confirmed to require a large structured payload.

Relevant handler:

- `0x59DD20` routes opcode `7` to `0x59E330`

`0x59E330` reads well beyond a trivial ACK and touches fields out to about `payload + 0x1D4`.

Practical conclusion:

- server reply `opcode 0x0007` cannot be `1 byte`
- minimum meaningful payload is roughly `0x1D8` bytes

That is why the old `0x0007 -> b"\x01"` response could never advance loading.

### Server -> Client `opcode 0x0005`

Confirmed to have a meaningful small structure.

Relevant handler:

- `0x59EBD0`

Observed structure:

- byte `0`: status
- byte `1`: subtype
- bytes `2..5`: little-endian dword

Meaningful subtype branches seen in code:

- `0x00`
- `0x12`
- `0x13`

Practical conclusion:

- `opcode 0x0005` should not be sent as `1 byte`
- a minimum draft should be `6 bytes`

### Client -> Server `opcode 0x0017`

New runtime observation from the latest test:

- after our `0x0007(472B)` + `0x0005(6B)` reply, the client sends many `0x0017` packets
- observed payload pattern:
  - `07 29 29 00 00 00`
  - `07 2A 2A 00 00 00`
  - `07 2B 2B 00 00 00`
  - ...
  - up through at least `07 45 45 00 00 00`

Interpretation:

- this is probably not random noise
- it looks like the client is iterating over IDs, slots, or resource indices during loading
- the payload decodes cleanly as:
  - `kind = 0x07`
  - `stat_id = value`

Observed examples:

- `07 29 29 00 00 00`
- `07 2A 2A 00 00 00`
- ...
- `07 45 45 00 00 00`

Stronger interpretation after the newer log:

- this looks more like a stat/resource sync upload than a request for arbitrary map chunks
- the client is walking a fixed ID range and reporting default/current values equal to the ID itself

At the moment, we do not yet have a confirmed inbound `0x0017` handler that proves the server must answer it directly.
So for now:

- `0x0017` is an important loading-stage symptom
- but not yet a proven server->client requirement

### Server -> Client `opcode 0x0010`

Confirmed to populate grouped stat/resource tables.

Relevant handler:

- `0x59ECA0`

Observed layout:

- `0x16` x `u16` at `+0x00`
- `6` x `u16` at `+0x2C`
- `5` x `u16` at `+0x38`
- `0x20` x `u16` at `+0x42`
- `3` x `u16` at `+0x82`
- `1` x `u16` at `+0x88`
- `6` x `u16` at `+0x8A`

Practical conclusion:

- minimum meaningful payload is about `0x96` bytes
- this looks like a server-driven stat/resource initialization table
- however, the `0x0017` IDs seen at runtime (`0x29..0x45`) are outside the main early `0x0010` group-0 IDs, so `0x0017` is probably tied to a different local stat table
- the binary already contains default/current values for these groups, so sending all-`1` payloads is likely wrong

### Server -> Client `opcode 0x0011`

Confirmed to populate a flat 31-entry table.

Relevant handler:

- `0x59EEE0 -> 0x5A50F0`

Observed layout:

- `31` x `u16`

Practical conclusion:

- minimum meaningful payload is `0x3E` bytes
- the binary already contains a 31-entry default table at `DAT_006E0A88`, so an all-`1` payload is likely wrong here too

## New `0x0007` Layout Corrections

Confirmed from deeper handler reading:

### `0x134` / `0x148` tables use `0x00FF` as the empty sentinel

Relevant function:

- `0x59E330`
- followed by `0x5A5AB0`

Important detail:

- `0x5A5AB0` checks `*(short *)entry == 0x00FF`
- so the empty marker is `0x00FF`, not `0xFFFF`

Practical conclusion:

- the server draft should fill empty slot entries with `0x00FF`

### `0x184` is an 8-byte table, not an 8-dword table

Relevant code:

- `0x59E330` calls `0x5AA6F0(index, param_1[0x184 + index], *(dword *)(param_1 + 0x18C + index*4))`

Important detail:

- the first half is read byte-by-byte
- only the second half at `0x18C` is dword-based

Practical conclusion:

- `0x184..0x18B` should be modeled as 8 small mode values
- `0x18C..0x1AB` remains 8 dwords

### The request dwords at `+0x03` and `+0x07` should be preserved first

Reason:

- the client request already carries non-trivial values in that region
- overwriting them with `1/1` throws away one of the few signals we actually have

Practical conclusion:

- the next draft should preserve the client-provided values there unless we prove they are wrong

### The `0x0B` stat table should default to zeros, not synthetic ascending values

Important discovery:

- `0x5A37A0` initializes the local property table loaded from `lgc.tmp`
- each entry stores:
  - current value
  - minimum
  - maximum
- for the main property IDs, the initializer sets the current value to `0`

Why this matters:

- `0x59E330` feeds the server `0x0007` values into `0x5A4880`
- `0x5A4880` validates them against per-property min/max bounds
- sending `0,1,2,3,...` was a guess and may have created out-of-range or semantically wrong values

Practical conclusion:

- the safest next draft is to zero the full `0x46 * u16` current-value table

### The byte tables behind `0x59BC00` should start empty unless proven otherwise

Important discovery:

- `0x59BC00` copies only non-zero bytes into local item/flag tables
- seeding those regions with `1` creates synthetic entries

Practical conclusion:

- the safer draft keeps those regions all-zero until a required non-zero meaning is identified

## Confirmed Current Runtime Sequence

With the latest server draft:

1. Client connects
2. Client sends `0x0000` hello
3. Client sends heartbeats
4. Server sends fake login packet
5. Client sends `0x0004` character creation
6. Server sends `0x0002 + 0x0003`
7. Client sends `0x0007` with `196B` payload
8. Server sends:
   - `0x0007` with `472B` draft payload
   - `0x0005` with `6B` draft payload
   - `0x0010` with `150B` draft payload
   - `0x0011` with `62B` draft payload
9. Client sends:
   - `0x0001`
   - many `0x0017`
10. Client remains in loading state
11. Eventually connection resets / game exits

Important conclusion:

- the larger `0x0007` reply did not break the client
- but it still was not sufficient to complete loading
- therefore the remaining blocker is now more likely a wrong `0x0007` field layout, a missing follow-up packet, or an unhandled stage transition tied to the repeated `0x0017` burst

## Latest Run Update

Latest reruns with the improved draft still show:

- `0x0003` carrying `01 + "Data\\\\Space\\\\Plaza\\x00"`
- `0x0007` preserving the client's early dwords
- `0x134/0x148` using the correct empty sentinel `0x00FF`
- `0x184` modeled as 8 bytes, not 8 dwords

Observed result:

- the client still enters loading
- no new client opcodes appear after the `0x0017` burst
- the `0x0017` sequence remains the same fixed ID walk:
  - `0x29..0x30`
  - `0x36..0x39`
  - `0x3F..0x45`

Practical conclusion:

- those fixes were structurally correct, but not sufficient
- the current blocker is probably deeper semantic content inside `0x0007`
- alternatively, a later state transition may require one more server-driven event that is not yet identified

## Newer Breakthrough

A later draft changed the client behavior substantially:

- the large `0x0017` burst disappeared
- the client now sends only one packet:
  - `0x0017 payload = 07 01 00 00 00 00`
- after that it only keeps heartbeating

Why this matters:

- this strongly suggests the client accepted much more of the `0x0007` state than before
- it now looks blocked on a single follow-up transition, not on bulk stat initialization

Current interpretation of that lone packet:

- `kind = 0x07`
- `stat_id = 0x01`
- `value = 0`

Best next experiment from this point:

- after the first client `0x0017`, send one extra server `0x0005`
- prefer subtype `0x12` first, because `0x59EBD0` and `0x50CFF0` both contain special handling for subtype `0x12/0x13`
- `0x12` is the more conservative branch compared with `0x13`

Another strong candidate:

- server->client `opcode 100` is intercepted directly by `0x594310`
- it calls `0x594100(1)`, which sets `CLogicManager::state = 1`
- payload is not used

Practical implication:

- this may be the explicit "advance to next logic state" event
- a good experiment is to send `opcode 100` right after the first client `0x0017`
- pairing it with the existing `0x0005 subtype=0x12` follow-up is reasonable

Important correction after runtime crash:

- while `0x594310` itself ignores the payload for the state switch,
  the same packet is then processed by the state-1 extra path
- that reaches `0x00615650(payload)`
- `0x00615650` reads fields out to at least `payload[0x1A]`

Practical conclusion:

- `opcode 100` with an empty payload will crash
- the next valid experiment must use a payload of at least `0x1B` bytes

Deeper correction after inspecting `0x00615650` and `0x0050EE80`:

- `opcode 100` payload bytes `+0x14..+0x1A` are not arbitrary
- they are interpreted as:
  - year (`u16`)
  - month-1 (`u8`)
  - day (`u8`)
  - hour (`u8`)
  - minute (`u8`)
  - second (`u8`)
- those values flow into `0x0050F400`, which validates the date/time fields

Practical conclusion:

- all-zero date/time fields are invalid and can fault the client
- the safer draft should populate `opcode 100` with a real timestamp

## Current Best Server Draft Direction

The best-evidence draft at this point is:

- keep `0x0007` close to local default/current property state
- avoid synthetic non-zero flag tables in `0x0007`
- use binary-default tables for `0x0010`
- use the binary-default 31-entry table for `0x0011`
- optionally try one `0x0005 subtype=0x12` follow-up after the first client `0x0017`

## Current Best Hypothesis

The client is now past the earliest trivial handshake stage.

The infinite loading appears to be caused by one or more of:

1. `0x0003` likely needs a meaningful path/string payload, not a bare `0x01`
2. `0x0007` payload content is structurally valid enough not to crash, but semantically wrong
3. `0x0005` needs a different subtype/value
4. one or more follow-up packets are required after the `0x0017` burst starts
5. the repeated `0x0017` packets correspond to resource/stat uploads or requests that must be acknowledged indirectly

After the latest reruns, item `2` is now the strongest hypothesis.
Item `1` moved down in priority because the more realistic `0x0003` payload did not change the downstream pattern.

## Fields Worth Testing Next

Priority order:

1. `opcode 0x0003` payload string
   - try `Data\\\\Space\\\\Plaza\\x00`
   - if that changes behavior, enumerate other `Data\\\\Space\\\\...` candidates
2. `opcode 0x0007` payload
   - offsets `0x03` and `0x07`
   - the `0x134/0x148/0x15C` tables
   - the `0x184/0x18C` tables
   - keep the `0x0B` property table zero-based first
   - keep `0x97/0xB8/0xC7/0xEA/0x110/0x113/0x11D` byte tables empty first
3. `opcode 0x0005`
   - subtype byte at offset `1`
   - dword at offset `2`
4. repeated `opcode 0x0017`
   - determine whether this is a query sequence that expects per-ID replies

## Files Updated

The current experimental server draft was written into:

- `<home>\Documents\<project-dir>\Azrok_Plaza\azrok_server.py`

The draft currently does this:

- replies to `0x0004` with:
  - `0x0002`
  - `0x0003` carrying `01 + "Data\\\\Space\\\\Plaza\\x00"`
- replies to `0x0007` with:
  - `0x0007` 472-byte draft
  - `0x0005` 6-byte draft
  - `0x0010` 150-byte draft
  - `0x0011` 62-byte draft
- logs `0x0017` but does not answer it yet

## Confidence Labels

High confidence:

- `0x5927D0` is a stub
- final runtime class is `CLogicManager`
- real packet reaction path goes through `0x594310`
- `0x0001` from server kills the client
- `0x0007` inbound handler expects a large structured payload
- `0x0005` inbound handler expects at least a 6-byte structure

Medium confidence:

- the repeated `0x0017` sequence is tied to loading-stage progression
- incorrect `0x0007` semantics are the main reason for current infinite loading

Low confidence:

- exact semantic meaning of each `0x0007` field
- whether `0x0017` requires direct server replies or only accompanies another missing packet

## Crash Root Cause From Windows Error Reporting

Latest confirmed crash:

- time: 2026-03-30 02:05 KST
- exception: `0xC0000005`
- fault offset: `0x0021571E`
- image base: `0x00400000`
- fault VA: `0x0061571E`

This maps directly into `0x00615650`, the state-1 handler for inbound
`opcode 100`.

Important detail:

- the faulting instruction is the write to `local_c + 0x10`
- that means the object pointer returned by the earlier virtual call is null
  or otherwise invalid before any of the later date/time fields matter

Practical conclusion:

- `opcode 100` is still too early / too strong for the current client state
- the crash is not just "bad timestamp data"
- the client is missing a prerequisite current-player / scene object before
  `0x0064` can succeed

## Current Safer Experiment Direction

Because `0x0064` faults inside `0x00615650`, the next server draft avoids it
for now.

The current server now does this after the first client `0x0017`:

- send `opcode 0x0065` with empty payload
- send `opcode 0x0066` with empty payload

Why these two:

- `0x0065 -> 0x00615B20 -> 0x0050D5D0`
  - iterates/finalizes the existing actor list
  - does not touch the null current-player slot that killed `0x0064`
- `0x0066 -> 0x00615B50`
  - processes `0x1A`-byte records
  - with a zero-length payload it safely skips record parsing and still
    executes the trailing finalize call `0x0050DA70`

Working hypothesis:

- state 1 likely expects one or more safe scene/list finalization packets
  before the current-player packet `0x0064`
- if the client reacts differently to `0x0065 + 0x0066`, we can narrow the
  exact prerequisite chain without crashing the game

## Follow-up After Actor Bootstrap Test

Latest result:

- adding a real `0x0066` actor record and then `0x0064(id=1)` still crashes
- the fault offset stayed the same: `0x0021571E`

Practical meaning:

- the actor-list path used by `0x0066` is not enough to satisfy the
  current-player getter used by `0x0064`
- `0x0064` is still premature

Next experiment direction:

- remove `0x0064` again
- keep `0x0065` finalize
- send a single `0x0066` actor record with action byte `0x0A`
  so `0x00615B50` takes its explicit scene-switch branch
- then try `0x006E [00 00]` as a safe state-1 ready/setup event

Why this is a better probe:

- `0x00615B50` handles action bytes `0x0A` / `0x0B` specially
- that branch can move scene/state forward without dereferencing the null
  current-player slot that keeps killing `0x0064`
- `0x006169D0` only takes its heavy setup path when `payload[1] == 0`
- that path sets an internal ready flag at `+0x129B` and does not use the
  null current-player getter that killed `0x0064`

## New Confirmed State-1 Switch Map

`0x00613740` is now effectively dumped.

Confirmed state-1 packet map:

- `0x0003` -> `0x00615610`
- `0x000C` -> `0x006165B0`
- `0x0064` -> `0x00615650`
- `0x0065` -> `0x00615B20`
- `0x0066` -> `0x00615B50`
- `0x0067` -> `0x00615D00`
- `0x0068` -> `0x00615D50`
- `0x0069` -> `0x00615E70`
- `0x006A` -> `0x00615FF0`
- `0x006B` -> `0x00615340`
- `0x006C` -> `0x00615410`
- `0x006D` -> `0x006154E0`
- `0x006E` -> `0x006169D0`
- `0x006F` -> `0x00616B20`
- `0x0070` -> `0x00616860`
- `0x0071` -> `0x00616510`
- `1000` -> `0x006167E0`

Practical conclusion:

- there does not appear to be a hidden extra top-level opcode inside
  `0x594310`
- the missing transition is more likely a specific combination of already
  known state-1 packets, or a wrong scene string in `0x0003`

## New Confirmed State-0 Auxiliary Detail

`0x0050CBC0` still matters during early loading.

Relevant branches:

- `opcode 4`
  - if payload starts with `0xFF`, it sets internal flag `+0x31C71`
  - then copies latency-related values from `+0x9A5` / `+0x9A9`
- `opcode 7`
  - `0x0050D290` picks scene code:
    - `100` if flags `+0x31C72 == 0` and `+0x31C73 == 0`
    - `0x6F` if first is `0`, second is nonzero
    - `0x6E` if first is nonzero

This is one of the strongest remaining hints that the loader still expects a
scene-selection precursor before the final in-world transition.

## New Confirmed Meaning Of `0x0066` And `0x0069`

`0x0066` actor records are now better understood through
`0x00615B50 -> 0x0050D790 -> 0x005243E0`.

Confirmed `0x0066` record fields:

- `+0x00`: action/state byte
- `+0x01`: actor/entity id (`u32`)
- `+0x05`: actor type / species-like byte
- `+0x06`: secondary subtype byte
- `+0x07..+0x13`: short C string
- `+0x14..+0x17`: appearance bytes
- `+0x18..+0x19`: optional pair

Important special case:

- action `0x0A` forces scene code `0x2E`
- action `0x0B` forces scene code `0x2F`

This matters because `0x00615E70` (`opcode 0x0069`) has a special non-current
actor path:

- if the target actor already exists
- and its scene code is `0x2E` or `0x2F`
- then `0x00615E70` calls `0x00524DA0(x, y)`
- that updates the actor position without touching the unsafe current-player
  dereference used by `0x0064`

This is why `0x0069` is now the most grounded next follow-up after the
`0x0066 action 0x0A` bootstrap.

## Current Runtime Status

Latest non-crashing sequence:

- `0x0002`
- `0x0003 = 01 + "Data\\Space\\Plaza\\x00"`
- `0x0007(472B)`
- `0x0005(6B)`
- `0x0010(150B)`
- `0x0011(62B)`
- client sends one `0x0017 = 07 01 00 00 00 00`
- server sends:
  - `0x0066` scene actor (`action 0x0A`)
  - `0x0065` finalize
  - `0x006E [00 00]`

Observed result:

- no immediate crash
- no new client opcode
- only heartbeat continues
- loading screen remains stuck

Practical conclusion:

- `0x0066 + 0x0065 + 0x006E` is safe, but not sufficient
- the client is likely waiting for either:
  - a position/activation follow-up such as `0x0069`
  - or a different `Data\\Space\\...` scene string from `0x0003`

## Practical Next Experiments

### 1. `0x0069` after `0x0066 action 0x0A`

Most grounded next probe:

- create actor with `0x0066 action 0x0A`
- finalize with `0x0065`
- send `0x0069` for the same actor id
- then send `0x006E [00 00]`

Reason:

- `0x0069` can position an actor already placed in scene `0x2E`
  by the `0x0A` bootstrap
- unlike `0x0064`, it does not require the current-player getter to succeed

### 2. Try alternate `0x0003` space strings

Confirmed binary candidates:

- `Data\\Space\\Plaza`
- `Data\\Space\\Lobby`
- `Data\\Space\\SelectPet`
- `Data\\Space\\Pazi`
- `Data\\Space\\OXquiz`
- `Data\\Space\\PopcornGame`
- `Data\\Space\\TeroGym`
- `Data\\Space\\MuryPlay`
- `Data\\Space\\Magic`
- `Data\\Space\\ArimCook`
- `Data\\Space\\ItemShop`
- `Data\\Space\\PatHouse`

Most plausible early candidates:

- `Lobby`
- `SelectPet`
- `Plaza`

The server draft should expose this as a quick toggle instead of hardcoding
only one value.

## Latest Follow-up Adjustment

After testing both:

- `0x0003 = Data\\Space\\Lobby`
- `0x0066 + 0x0065 + 0x0069 + 0x006E`

the observed result stayed the same:

- no crash
- no extra client opcode
- only heartbeat
- infinite loading

This lowers confidence in `0x0069` as the missing final step.

The next stronger follow-up is `0x0068`.

Reason:

- `0x00615D50` consumes `0x18`-byte records for existing non-current actors
- when `record[5] == 0`, it does:
  - `0x00526EC0()`
  - `0x00527A40(1)`
  - `0x00524DA0(record[1], record[2])`

That makes `0x0068` a more complete actor activation / placement path than
`0x0069`, while still avoiding the unsafe current-player dereference inside
`0x0064`.

Additional small improvement:

- the first byte of `0x006E` is now better treated as a slot/index value
- the safest current guess is to reuse the incoming `0x0017 stat_id`
  instead of hardcoding `0`

## Strong New `0x0007` Candidate

`0x0059E330` front-loads the dword at `payload + 0x03` into `0x005A8C90`.

That helper splits the value into decimal groups:

- `YY`
- `MM`
- `DD`
- `HH`

Later in the same handler:

- `0x005A8D40()` recomputes the same 8-digit code
- if the result is `0`, the code falls into `0x005A8790(-1)`

Practical conclusion:

- keeping `0x0007 +0x03 == 0` is likely wrong
- the next best draft should populate it with a real non-zero `YYMMDDHH`
  style value
- using the current local clock is a conservative first probe

## State-1 Gate Insight

The latest decompile of `0x00594310` explains why the earlier
`0x0066` / `0x0068` / `0x006E` follow-ups were likely ineffective.

High-level flow:

- `0x00594310` dispatches opcode `100` first and immediately writes
  `this + 0x163E4 = 1`
- after that, the main dispatch path depends on the current state:
  - state `0` -> `0x0059DD20` + `0x0050CBC0`
  - state `1` -> `0x00613740`
  - state `2` -> `0x00594560` / vtable path

Important consequence:

- opcodes `0x0065`..`0x0071` are only handled by the state-1 dispatcher
  `0x00613740`
- if the client never reaches state `1`, those packets are effectively ignored

That makes `opcode 100` the real state gate.

## Why `opcode 100` Crashed Earlier

`0x00613740` case `100` calls `0x00615650(payload)`.

`0x00615650` does *not* just toggle a flag. It immediately:

- fetches the current-player object
- writes vectors/positions into that object
- parses timestamp bytes at `payload + 0x14..0x1A`

So sending `opcode 100` too early caused the observed crash at
`Azrok.exe+0x0021571E`, because the current-player object was still absent.

## New Experimental Patch

To isolate the state gate from the unsafe body, the runtime patcher now also:

- NOPs the `CALL thunk_FUN_00615650` at `0x006137C1`

This preserves the earlier `0x00594310` state write (`state = 1`) while
turning `opcode 100` into a pure state-switch probe.

Experiment order after the first client `0x0017` is now:

- `0x0064` with empty payload
- `0x0066` scene actor
- `0x0065` finalize
- `0x0068` position
- `0x006E` ready

The purpose of this experiment is to verify whether the client can progress
once those follow-up packets are finally processed under the real state-1
dispatcher instead of being ignored in state 0.

Correction note:

- the first attempt targeted `0x006137CE`, but the jump-table decode showed
  that was the wrong case block
- `0x0061390C` maps opcode `100` to jump-table entry `2`, which lands at
  `0x006137BA -> CALL 0x004DE085 -> thunk_FUN_00615650`
- so the correct callsite to patch is `0x006137C1`

## Crash-Dump Result: `0x006E` Is Still Too Early

Latest dump:

- file: `Azrok.exe(1).94120.dmp`
- exception: `EXCEPTION_ACCESS_VIOLATION`
- address: `0x00616AD2`

That address is inside `0x00616AC0`, which is called by the state-1
`opcode 0x006E` handler `0x006169D0`.

Relevant logic:

- `0x006169D0` only takes the heavy branch when `payload[1] == 0`
- then it calls:
  - `0x00616AC0(slot)`
  - `0x00616AF0(slot)`
- `0x00616AC0` is just:
  - `*(obj + 0x7B) = slot`

Crash implication:

- the target `obj` was still invalid when `0x006E` ran
- so `0x006E` is not safe yet, even after forcing state `1`

Practical follow-up:

- remove `0x006E` from the first state-1 bootstrap
- keep the safer sequence:
  - `0x0064` (state switch only, body skipped by patch)
  - `0x0066`
  - `0x0065`
  - `0x0068`

## State-1 Follow-Up Candidates After Infinite Loading

Recent state-1 handler review tightened the next packet shortlist:

- `0x0066 -> 0x00615B50`
  - consumes `0x1A`-byte actor records
  - `record[0] == 0x0A` drives `0x00527A40(0x2E)`
  - this looks like the safest "scene actor bootstrap" path so far
- `0x0068 -> 0x00615D50`
  - consumes `0x18`-byte movement records
  - for an existing non-current actor with `record[5] == 0`, it reaches
    `0x00524DA0(x, y)` after `0x00526EC0()` and `0x00527A40(1)`
- `0x0069 -> 0x00615E70`
  - is the safest explicit "commit / snap position" follow-up after `0x0068`
- `0x006E`
  - is confirmed too early and crashes if the internal object at
    `0x00616AC0` is still missing

Another high-value finding is that state `1` has its own `opcode 3` handler:

- `0x0003 -> 0x00615610(payload + 1)`
- `0x00615610` calls `0x0050C250(...)` and `0x005D4070(...)`
- `0x005D4070` stores the string and kicks a small timer/setup path

That state-1 `0x0003` replay was tested and is now ruled out:

- latest `Application Error`:
  - exception code `0xc0000005`
  - offset `0x001D407F`
- that is `VA 0x005D407F`, inside `0x005D4070`
- disassembly shows the crash is the very first dereference:
  - `mov ecx, dword ptr [eax + 0x6e]`

So replaying `0x0003("Data\\Space\\Lobby")` after the forced state-1 switch
does not safely advance loading; it dereferences an object graph that is not
ready yet.

The current safer follow-up sequence is therefore:

- `0x0064` (state switch only, body skipped by patch)
- `0x0066`
- `0x0065`
- `0x0068`
- `0x0069`

## Two-Stage `0x0064` Experiment

`0x00615650` is now confirmed as the real loading-close path:

- it accepts entry modes `{0x00, 0x0A, 0x0B, 0x14}`
- it writes the current/self actor id via `0x00615AF0`
- it then dereferences the current actor object and populates position /
  appearance / time-like fields
- it ends with `0x0050A840()`, which is the concrete loading-popup close edge

That creates a useful split:

- if `0x0064` is completely skipped, the client reaches state `1` but can stay
  in infinite loading forever
- if `0x0064` is executed too early, it can crash because the actor object it
  expects does not exist yet

The next practical experiment is therefore:

1. keep the startup patch that turns the *first* `0x0064` into a state-switch
   only packet
2. use that patched `0x0064` to unlock state `1`
3. create/place the actor with:
   - `0x0066`
   - `0x0065`
   - `0x0068`
   - `0x0069`
4. on a later heartbeat, restore the original `0x006137C1` callsite and send
   one structured `0x0064`

This tests whether the missing piece is simply "the real `0x0064` ran before
the actor object existed".
