# S->C 0x0003 -> 0x000D path and vtable preconditions (2026-07-17)

This note separates the client-protocol state that must be reached without the
current `C->S 0x0019` memory shortcut from the independent embedded-object
lifetime precondition of the packet-only `S->C 0x000D` candidate. It is based
on read-only analysis of `/New Traces/Azrok_original.exe`; no executable or
runtime memory was modified.

## 1. Dispatch mode is the first protocol precondition

`DispatchInbound_ByClientMode @ 0x00594310` selects the inbound dispatcher
from its mode field at `transport+0x163E4`:

- mode `0` calls `DispatchState0Specific_S2C` and then
  `DispatchState0Common_S2C @ 0x0050CBC0`;
- mode `1` calls `DispatchState1_S2C @ 0x00613740` instead;
- mode `2` takes a third virtual-dispatch path.

The two `S->C 0x0003` handlers do not have the same payload contract:

| Client mode | Handler | Payload interpretation |
|---:|---|---|
| `0` | `0x0050D200` | `[u8 flag][NUL-terminated path]`; stores the flag and passes `payload+1` onward |
| `1` | `0x00615610` | treats `payload` itself as the string/value; it does not skip a flag byte |

`S->C 0x000D` is case `0x0D` of the mode-0 common dispatcher at
`0x0050CD01`. There is no `0x000D` case in the known state-1 switch. Therefore
the proposed `[01] + "Data\\Space\\Plaza\\0"` followed by `0x000D [00]` is a
mode-0 contract. Sending that state-0 `0x0003` layout after the client has
already changed to mode 1 would feed the leading `0x01` to the state-1 string
handler and would not reach the mode-0 `0x000D` transition.

**Evidence strength: direct control flow and instruction-level payload use.**

## 2. Exact mode-0 0x0003 effects

`DispatchState0Common_S2C` reaches the handler through
`0x0050CC45..0x0050CC4C`. `HandleS2C_0003_StoreSpacePath @ 0x0050D200` then:

1. reads `payload[0]` at `0x0050D20F` and writes it as a dword to
   `gm+0x31C63` at `0x0050D215`;
2. advances the payload pointer by one at `0x0050D21E`;
3. obtains the embedded UI root at `gm+0x4A78F`, then calls accessor
   `FUN_0050C250`, which returns `ui_root+0x989`;
4. passes the still-stacked `payload+1` string to
   `FUN_005D4070(ui_root+0x989, path)`.

This corrects the older shorthand that `FUN_0050C250` copies the path to
`gm+0x989`. It is only an address accessor. The actual object and destination
are:

```text
ui_root       = gm + 0x4A78F
notice_popup  = ui_root + 0x989 = gm + 0x4B118
path buffer   = notice_popup + 0xDB = gm + 0x4B1F3
```

`FUN_005D4070` is a `CPopupNotice` operation. It returns without copying or
arming anything when the current scene/state query is `0x6B` or `0x6C`.
Otherwise it:

- optionally performs an existing-popup cleanup;
- copies the NUL-terminated path to `notice_popup+0xDB` at `0x005D4104`;
- creates the transition notice/effect;
- sets popup bytes `+0xD0=1` and `+0xD1=1`;
- stores `GetTickCount()` at `+0xCC`;
- stores countdown `10` at `+0xD7`.

The constructor `FUN_005D3AF0` gives this object vptr `0x006A9E18`.

The current-scene query in this operation is also exact. `notice_popup+0x6E`
points back to `ui_root`; dereferencing the first dword of that root recovers
`gm`, and `FUN_004ED750` reads `gm+0x31796`. This is the field tested at
`0x005D408E` and again at `0x005D40A5`. It is not the later scene-request
field `gm+0x31AAD`.

The early-return branches are ordered as follows:

1. if the first `read32(gm+0x31796)` is `0x6B`, return at
   `0x005D4091 -> 0x005D40AA`;
2. otherwise query the field again, and if the second value is `0x6C`, return
   at `0x005D40A5..0x005D40AA`;
3. only after both checks pass does execution reach the copy at `0x005D4104`.

For a stable experiment, the preflight requirement is therefore
`read32(gm+0x31796) not in {0x6B, 0x6C}`. The handler has no lock around its
two reads, so the observer should also record the scene immediately after the
call rather than assume the pre-call sample remained constant.

### 0x0003-only read-only postcondition table

The exact fields to snapshot before and after a successful mode-0
`0x0003 [01] + path` experiment are:

| Meaning | Address | Width | Successful post-value |
|---|---:|---:|---|
| packet flag | `gm+0x31C63` | dword | zero-extended `payload[0]`, normally `1` |
| notice render tick | `gm+0x4B1E0` (`notice+0xC8`) | dword | a fresh `GetTickCount()` written inside `FUN_005D42C0` |
| notice main tick | `gm+0x4B1E4` (`notice+0xCC`) | dword | a fresh `GetTickCount()` written at `0x005D4138..41` |
| armed D0 | `gm+0x4B1E8` (`notice+0xD0`) | byte | `1` |
| armed D1 | `gm+0x4B1E9` (`notice+0xD1`) | byte | `1` |
| countdown | `gm+0x4B1EF` (`notice+0xD7`) | dword | `10` |
| staged path | `gm+0x4B1F3` (`notice+0xDB`) | byte string | exact payload path followed by NUL |
| current scene used by guard | `gm+0x31796` | dword | recorded value should remain outside `0x6B/0x6C` |

The flag write occurs before either scene guard, so `gm+0x31C63 == 1` alone
does not prove the path arm succeeded. Conversely, the early return performs
no path, D0/D1, tick, or countdown write: those locations retain their prior
contents and must be compared with the pre-snapshot. For the ticks, the robust
test is unsigned modulo-32-bit proximity to the observer's `GetTickCount()`
window, not merely `!= 0`.

`thunk_String_CopyZ @ 0x004D90DA -> 0x006543B0` is an unbounded `strcpy`-style
loop; the packet supplies no destination length. The notice object begins at
`ui_root+0x989`, and the next embedded object is constructed at
`ui_root+0xB61`, establishing a packed object span of `0x1D8` bytes. The path
starts at notice offset `0xDB`, leaving exactly `0xFD` bytes through the end of
that span. Thus the strongest structural ceiling supported by this binary is:

```text
path bytes excluding NUL <= 0xFC (252)
total copied bytes including NUL <= 0xFD (253)
```

This is an overwrite-prevention ceiling, not a recommendation to send paths
near that size. There is no bounded-copy enforcement, and a missing NUL or a
253-byte non-NUL path begins overwriting the next embedded object at
`ui_root+0xB61`. The known `"Data\\Space\\Plaza"` path is 16 bytes plus its
terminator and is well inside the structural bound. A read-only observer
should likewise cap its path read at `0xFD`, so a corrupt or unterminated path
cannot make the diagnostic cross into the following object.

Thus a packet-level path-arm success requires more than seeing opcode 0x0003
on the wire: the client must be in mode 0, must not be in scene `0x6B/0x6C`,
and must return past `0x005D4070` with the path and popup state committed.
These effects should be allowed to complete before sending `0x000D`; separate
packets/ticks preserve that boundary.

**Evidence strength: direct disassembly for all listed writes. The later
engine-level use of the staged path remains an inference; `0x000D` itself does
not read this buffer.**

## 3. Exact mode-0 0x000D order

At `0x0050CD01`, the common dispatcher reads `payload[0]`:

- zero: obtains the transition object through `gm+0xE4A`, then calls
  `Plaza_TransitionFromRoom @ 0x00568770`;
- nonzero: takes error route `0x1C` and never calls the transition.

There is no object-validity guard before `Plaza_TransitionFromRoom`. Its exact
high-level order is:

1. `0x0056877C..0x0056878B`: enqueue scene request `0x6E`, which stores
   `gm+0x31AAD=0x6E` and opens the loading request;
2. run one direct transition cleanup chain;
3. invoke vtable slot `+0x0C` on `ui_root+0x716`;
4. invoke vtable slot `+0x0C` on `ui_root+0x004`;
5. invoke vtable slot `+0x0C` on `ui_root+0x641` at
   `0x0056881A..0x00568822`;
6. run two direct operations on `ui_root+0x1A0`;
7. invoke vtable slot `+0x0C` on `ui_root+0x45E`;
8. close/reset the `ui_root+0x989` notice popup;
9. set `gm+0x31C72=1` at the call beginning `0x005688AD`;
10. reset the calibration accumulator by calling
    `HandleS2C_0004_CalibrationSample(NULL)` at `0x005688D0`.

The order matters diagnostically. Scene request `0x6E` is stored before any
of the risky virtual calls, while the Hansol flag and calibration reset occur
after all of them. A crash can therefore leave `scene_opcode=110` while the
actual transition contract is incomplete. Such a process is contaminated and
must not be reused as a successful baseline.

**Evidence strength: direct disassembly.**

## 4. Shared embedded-object lifetime precondition

The four unconditional virtual calls can be checked read-only before an
experiment. The expected original-image values are:

| Object | Absolute offset from `gm` | Expected vptr | Expected vtable `+0x0C` target | Slot behavior |
|---|---:|---:|---:|---|
| `CPopupStatus` (`ui_root+0x716`) | `gm+0x4AEA5` | `0x006ADA34` | `0x004D7C4E` -> `0x005F0540` | removes owned panels, returns `1` |
| `CPopupAzronInfo` (`ui_root+0x004`) | `gm+0x4A793` | `0x006AE3C4` | `0x004DCF7D` -> `0x005FBCD0` | removes owned panels, returns `1` |
| `CPopupCalendar` (`ui_root+0x641`) | `gm+0x4ADD0` | `0x006A7D6C` | `0x004DDA86` -> `0x005B5EE0` | removes owned panels, returns `1` |
| `CPopupStateList` (`ui_root+0x45E`) | `gm+0x4ABED` | `0x006AD970` | `0x004DA0BB` -> `0x005EF3F0` | removes owned panels and clears slots, returns `1` |

All four slot implementations finish with success, but they are not trivial
returns: they purge/remove owned panel handles and zero the corresponding
object fields. Their virtual dispatch is unconditional, so a null or damaged
vptr faults before this cleanup can complete.

The object lifecycle is rooted in `GameManager` construction:

- `FUN_00507DF0` calls `FUN_005110E0(gm+0x4A78F)` at `0x00507FA0`;
- that constructor creates `+0x004`, `+0x1A0`, `+0x45E`, `+0x641`, `+0x716`,
  and later popup objects in order;
- `CPopupCalendar` is constructed by `FUN_005B57A0` at `0x00511144..4A`,
  then receives its owner/root pointer through `FUN_00511730` at
  `0x005112BD..C3`;
- direct xrefs to vptr constant `0x006A7D6C` exist only at the calendar
  constructor (`0x005B57B7`) and destructor (`0x005B598F`). Both write the
  expected vptr; there is no normal setter that writes null.

This makes the lifecycle precondition distinct from server protocol state.
No recovered S->C packet field constructs or repairs these vptrs. If the
read-only preflight finds a mismatch, the cause class is partial/bypassed
construction, teardown, or memory corruption/overwrite; sending more packets
is not a justified repair.

The historical `0x00614865` stage-6 fault is the same calendar-object failure
at an earlier vtable slot: it loads `ui_root+0x641` and attempts vtable slot
`+0x04`. This shared identity is strong, but the later controlled entry-kind
matrix proves it is not caused by `entry_kind=0x0B`.

**Evidence strength: direct constructors, xrefs, vtable contents, and both
fault-site access chains. The historical source of the corruption remains
unresolved.**

## 5. Protocol state versus lifecycle state

The memory shortcut currently conflates two categories. A packet-faithful
replacement must induce the left column through client protocol while merely
verifying, not synthesizing, the right column:

| Must be induced by client protocol | Must already be valid as object lifetime |
|---|---|
| inbound dispatch mode `0` for this `0x0003/0x000D` contract | `ui_root=gm+0x4A78F` fully constructed |
| mode-0 `0x0003 [flag]+path` accepted outside `0x6B/0x6C` | all four vptrs above match valid image vtables |
| zero-payload `0x000D` reaches `0x00568770` | vtable `+0x0C` entries point to executable image thunks |
| client stores request `0x6E` and sets `gm+0x31C72` after cleanup | no destructor/overwrite occurs between preflight and call |
| transition resets calibration, then five `0x0004 [01]` samples set `gm+0x31C71` | calendar vptr remains valid through later Hansol stage 6 |

The two packets also have no proven direct data dependency inside
`Plaza_TransitionFromRoom`: `0x000D` does not read `gm+0x31C63` or the path at
`gm+0x4B1F3`. The required order is still justified because `0x0003` arms the
notice/path state used by the broader loader before `0x000D` enqueues request
`0x6E`, not because `0x000D` consumes the path as an argument.

## 6. Controlled-experiment handoff

Before any packet-only `0x000D` run, a read-only observer should establish:

1. fresh PatHouse baseline and inbound dispatch mode `0`;
2. current scene is neither `0x6B` nor `0x6C`;
3. all four vptr/value pairs in section 4 match;
4. send `0x0003 [01] + "Data\\Space\\Plaza\\0"` alone and confirm the client
   survives past `0x005D4070`;
5. re-check the four vptrs, then only in a separately recorded step send
   `0x000D [00]`;
6. distinguish the early `gm+0x31AAD=0x6E` write from later proof that
   `gm+0x31C72=1` and calibration reset completed.

This design is read-only apart from the intended protocol packets. A failed
vptr preflight is a stop condition, not permission to write the missing value.

## 7. Live GhydraMCP cross-check: exact runtime owner/root chain

An independent pass against the currently open GhydraMCP instance
(`Azrok_original.exe`, image base `0x00400000`) reproduced the constructor,
accessor, and xref evidence above. This instance describes the loaded program
database, not a live process memory snapshot; the runtime values below must
still be obtained with read-only `ReadProcessMemory`.

The complete chain used by `Plaza_TransitionFromRoom` is:

```text
controller  = gm + 0xE4A
transition  = controller + 0x23       = gm + 0xE6D
[transition + 4]                      = controller
[controller + 4]                      = gm
ui_root_by_accessor = gm + 0x4A78F
[controller + 0x30873]                = ui_root_by_accessor
```

The last stored pointer is therefore available at the absolute GameManager
offset `gm+0x316BD`. It provides an independent read-only cross-check of the
root computed by the accessors:

```text
read32(gm + 0x316BD) == gm + 0x4A78F
```

The construction evidence is exact:

- `FUN_00507DF0` constructs `gm+0x4A78F` at
  `0x00507F97..0x00507FA0`;
- it then calls `FUN_005302C0(gm+0xE4A, gm, gm+0x4A78F)` at
  `0x00507FCB..0x00507FE1`;
- `FUN_005302C0` stores its second argument at `controller+4` and its
  third at `controller+0x30873`;
- the controller constructor constructs `controller+0x23` at
  `0x0052F952..0x0052F958`, then binds the parent at
  `0x0052FAEC..0x0052FAF6`; the callee stores that parent at
  `transition+4`.

At `0x00568770`, each of the four virtual-call paths independently repeats
`[transition+4] -> [controller+4] -> gm+0x4A78F`, then uses one of the
following accessors:

| Accessor | Returned object |
|---|---|
| `FUN_0050C1C0` | `ui_root+0x716` |
| `FUN_0050C110` | `ui_root+0x004` |
| `FUN_0050C190` | `ui_root+0x641` |
| `FUN_0050C160` | `ui_root+0x45E` |

The live database xref query also returns exactly two references to the
calendar vptr `0x006A7D6C`: the constructor write at `0x005B57B7` and the
destructor write at `0x005B598F`. Its first 24 vtable bytes decode as six
little-endian pointers:

```text
0x004DF25A  0x004DFABB  0x004DE8E6
0x004DDA86  0x004D8A81  0x004DB4E3
```

This independently confirms the required slot `+0x0C = 0x004DDA86`.

### Read-only runtime preflight

A fail-closed observer can validate the chain before permitting the packet:

```text
assert read32(gm) == 0x0069D0A4
controller = gm + 0xE4A
transition = controller + 0x23
assert read32(transition + 4) == controller
assert read32(controller + 4) == gm
root = read32(controller + 0x30873)
assert root == gm + 0x4A78F
assert read32(root + 0x716) == 0x006ADA34
assert read32(root + 0x004) == 0x006AE3C4
assert read32(root + 0x641) == 0x006A7D6C
assert read32(root + 0x45E) == 0x006AD970
```

The `gm` base itself must come from a validated hook capture or a validated
stack scan for GameManager vptr `0x0069D0A4`. It is not the value stored at
`0x006E8430`: `FUN_004ECAB0` stores the Acknex `engine_open` result at that
global (`0x004ECAD8`), while the actual GameManager is a stack-local object at
`EBP-0x4CC5C`, constructed at `0x004ECB27..0x004ECB2D`. Consequently, any
observer fallback that treats `[0x006E8430]` as `gm` can manufacture a false
root and must be disabled or made fail-closed before its result is trusted.

**Evidence strength: independent live GhydraMCP decompilation, disassembly,
xrefs, and program-memory reads. Runtime-value validation remains pending a
fresh client process and must be performed read-only.**

## 8. Exact 0x000D completion and calibration handoff

The final part of `Plaza_TransitionFromRoom @ 0x00568770` establishes a useful
ordered completion boundary:

1. `0x0056877C..0x0056878B` calls `GameManager_EnqueueRoomCode(0x6E)`, which
   writes dword `gm+0x31AAD=0x6E` before invoking the two engine/post-load
   request functions;
2. direct transition cleanup runs;
3. the `CPopupStatus`, `CPopupAzronInfo`, and `CPopupCalendar` vtable `+0x0C`
   cleanup calls run in that order;
4. the two direct `ui_root+0x1A0` cleanup operations run, followed by the
   `CPopupStateList` virtual cleanup and the notice-popup close;
5. `0x005688AD..0x005688BC` writes byte `gm+0x31C72=1`;
6. `0x005688C1..0x005688D0` obtains calibration object `gm+0x15989` and calls
   `HandleS2C_0004_CalibrationSample(NULL)`;
7. only after the null reset and its initial client send return does
   `Plaza_TransitionFromRoom` return at `0x005688DB`.

The flag and calibration reset are after all four virtual calls. Therefore a
read-only observation of both `gm+0x31C72==1` and the new calibration-reset
state is stronger completion evidence than `gm+0x31AAD==0x6E`, which is
written before the risky calls.

The virtual methods also have real cleanup effects. Every panel pointer they
test is zero when the method returns: a null pointer is already zero, while a
non-null pointer is removed by `FUN_005AE340` and then explicitly zeroed. The
state-list method additionally zeros its second 8-by-5 slot matrix. These
large field sets can be watched when diagnosing an individual cleanup, but
the later Hansol flag/reset boundary is the smaller aggregate proof that all
four calls returned normally.

The exact child-handle fields passed to `FUN_005AE340` are:

| Object base | Object-relative child fields | Exact `gm`-relative fields |
|---|---|---|
| `status=gm+0x4AEA5` | `+0x74`; `+0x78+4*i` and `+0x90+4*i`, `i=0..5` | `+0x4AF19`; `+0x4AF1D..+0x4AF31` step 4; `+0x4AF35..+0x4AF49` step 4 |
| `azron=gm+0x4A793` | `+0x73,+0x77,+0x7B,+0x7F,+0x83,+0x87,+0x8B`; `+0x8F+4*i`, `i=0..9`; `+0xDF,+0xE3` | `+0x4A806..+0x4A81E` step 4; `+0x4A822..+0x4A846` step 4; `+0x4A872,+0x4A876` |
| `calendar=gm+0x4ADD0` | `+0xB2,+0xB6,+0xBA,+0xBE,+0xC2` | `+0x4AE82,+0x4AE86,+0x4AE8A,+0x4AE8E,+0x4AE92` |
| `state_list=gm+0x4ABED` | `+0x73`; `+0x77+0x14*r+4*c`, `r=0..7,c=0..4` | `+0x4AC60`; eight five-dword rows beginning `+0x4AC64,+0x4AC78,+0x4AC8C,+0x4ACA0,+0x4ACB4,+0x4ACC8,+0x4ACDC,+0x4ACF0` |

A valid object vptr is therefore necessary but not sufficient for a fault-free
cleanup. Every non-null child handle above must still be a valid engine panel:
`FUN_005AE340` dereferences `handle+0x24`, optionally purges that bitmap, and
calls `pan_remove(handle)`. A dangling non-null handle is a separate crash
class. A zero child field is explicitly valid: `FUN_005AE340` returns without
dereferencing it. For a nonzero value, a minimum read-only screen should
require committed readable memory through at least `handle+0x27` (and
practically through `+0x2F`, covering observed PANEL fields at
`+0x1C,+0x24,+0x28,+0x2C`). A nonzero `read32(handle+0x24)` bitmap pointer must also point
to committed readable memory.

This is only a memory-safety plausibility screen. `bmap_purge` and `pan_remove`
are imported from `ACKNEX.DLL`; the EXE exposes no verified PANEL magic,
vtable, or imported validity predicate that proves type/lifetime from pointer
shape alone. Strong acceptance of a nonzero handle therefore requires runtime
provenance such as a recorded `pan_create` return or membership in an engine
allocation registry. Accepting every readable pointer would let dangling or
wrong-type objects through. Diagnostics must not replace or zero any handle to
force the transition.

#### Clean-bootstrap `pan_create` occupancy fingerprint

The common creator `FUN_004FCCB0` directly invokes imported `pan_create` at
`0x004FCD0E` (through thunk `0x004D83AB`). On success it initializes PANEL
fields `+0x14,+0x18,+0x1C`, optionally assigns the requested bitmap at `+0x24`,
and returns the original `pan_create` value. Each popup setup below stores that
return value directly into its cleanup field:

These are also the setup methods paired with the cleanup slot in the same
vtable: status vtable `+0x04=0x004DD2FC -> 0x005F01E0`, Azron
`+0x04=0x004DD7ED -> 0x005FB540`, calendar
`+0x04=0x004DFABB -> 0x005B59B0`, and StateList
`+0x04=0x004D8CC0 -> 0x005EECF0`. The cleanup under investigation is each
same vtable's `+0x0C` slot.

| Popup setup | Direct `pan_create`-return coverage | Representative call VAs | Created / cleanup fields |
|---|---|---|---:|
| `CPopupStatus @ 0x005F01E0` | `+0x74`; `+0x78+4*i`, `i=0..5`; `+0x90+4*i`, `i=2..5` | `0x005F0245`, loop calls `0x005F0384` and `0x005F035A` | 11 / 13 |
| `CPopupAzronInfo @ 0x005FB540` | `+0x73,+0x77,+0x7B,+0x7F,+0x83,+0x87,+0x8B`; `+0x8F+4*i`, `i=0..9`; `+0xDF+4*i`, `i=0..1` | `0x005FB59F..0x005FB81D`, loops `0x005FB89D`, `0x005FB970` | 19 / 19 |
| `CPopupCalendar @ 0x005B59B0` | `+0xBA,+0xBE,+0xC2,+0xB2,+0xB6` | `0x005B5B8D`, `0x005B5C04`, `0x005B5C5A`, `0x005B5CB0`, `0x005B5D06` | 5 / 5 |
| `CPopupStateList @ 0x005EECF0` | main `+0x73`; matrix `+0x77+0x14*r+4*c`, with per-row counts `[3,3,3,3,3,2,2,2]` | main `0x005EF1CD`; matrix loop `0x005EEFB0` | 22 / 41 |

The status constructor leaves `+0x90,+0x94` zero. The StateList constructor at
`0x005EEB60` zeros all 40 matrix fields; setup creates only 21 of them, namely:

```text
r0: +0x077,+0x07B,+0x07F       r1: +0x08B,+0x08F,+0x093
r2: +0x09F,+0x0A3,+0x0A7       r3: +0x0B3,+0x0B7,+0x0BB
r4: +0x0C7,+0x0CB,+0x0CF       r5: +0x0DB,+0x0DF
r6: +0x0EF,+0x0F3              r7: +0x103,+0x107
```

Therefore the clean setup creates exactly `11+19+5+22 = 57` child PANELs out
of the 78 cleanup fields, while the other 21 fields remain zero. A runtime
snapshot with those exact 57 positions nonzero and exactly those 21 positions
zero is a strong clean-bootstrap occupancy fingerprint: all 57 nonzero
*field roles* have a direct `pan_create` provenance in the binary.

There are two normal null-safe occupancy states, not only one:

1. **constructor-initial state:** all 78 child fields are zero. Every cleanup
   call passes zero to `FUN_005AE340`, which returns without dereferencing;
2. **stable setup-complete state:** the exact 57 `pan_create` positions above
   are nonzero and the exact remaining 21 positions are zero.

Both states are allowed by the read-only cleanup gate. The mismatch condition
is a partial or mixed occupancy that matches neither complete shape: for
example, only part of a setup loop populated, an expected setup field missing,
or a field that is constructor-zero/setup-zero unexpectedly nonzero. This
correction matters because an all-zero object is not a dangling-PANEL risk;
requiring 57 live panels would incorrectly reject the valid pre-setup cleanup
case.

This fingerprint does not by itself prove that each current pointer value is
still the same live allocation returned earlier. An external removal, heap
reuse, or overwrite can preserve the nonzero occupancy shape. The macro gate
should therefore accept either complete occupancy state, and for the 57/21
state combine exact occupancy with readable PANEL/BMAP screening and, when
available, runtime `pan_create` return provenance. Partial occupancy or an
unreadable nonzero value is fail-closed; matching 57/21 occupancy is strong
evidence but not permission to skip the lifetime checks.

#### Minimal x32dbg observation order

For a single controlled `0x000D` run, the debugger needs only the following
ordered milestones:

1. enter `Plaza_TransitionFromRoom` from the mode-0 `0x000D[00]` dispatcher;
2. observe the scene-request write of `0x6E`, but do not treat this early write
   as complete transition success;
3. observe matching call and return events for cleanup in order: Status,
   AzronInfo, Calendar, then StateList. A call without its matching return
   localizes the failure to that cleanup and child PANEL set;
4. observe `gm+0x31C72=1`. Reaching this write proves all four virtual
   cleanups and the intervening direct cleanups returned;
5. observe `HandleS2C_0004_CalibrationSample(NULL)` enter and reset the count,
   arrays, and reset tick;
6. observe the first client `C->S 0x0016[01]` calibration request emitted by
   the null-reset call itself;
7. observe the reset call and `Plaza_TransitionFromRoom` return.

Stop on an exception, a cleanup call without its matching return, an
unexpected virtual target, a missing/wrong flag write, a non-null reset
argument, or a missing/malformed first calibration request. Seeing only
`scene_opcode=0x6E` is explicitly an incomplete transition, not success.

#### Debugger lifecycle at the transition-return breakpoint

The transition-return breakpoint is an observation pause, not the end of the
experiment. By the time it is reached the null reset has emitted the first
client calibration request, but the client still needs its message loop to run
to receive and dispatch the five server `0x0004[01]` samples.

After capturing the return-state snapshot:

1. disable/remove the one-shot return breakpoint as appropriate;
2. **resume the client from the breakpoint** and confirm it is running;
3. only then detach the debugger, if detachment is desired;
4. let the request-driven five-sample handshake proceed and observe the later
   client `C->S 0x0064` separately.

Detaching or otherwise ending debugger control while the debuggee remains
suspended prevents the Windows message/network dispatch loop from processing
the inbound calibration samples. That produces an artificial stall after a
successful `0x000D` and must not be diagnosed as a protocol or calibration
failure. Likewise, sending all five samples while the client is still paused
only queues traffic; it does not prove that any sample handler ran. The clean
session lifecycle is therefore **break -> snapshot -> resume -> optional
detach -> calibration handshake**, not break -> detach while paused.

### Immediate read-only postconditions

The calibration base and exact reset fields are:

```text
calibration = gm + 0x15989
read32(gm + 0x1632E) == 0                  # captured/final value
read32(gm + 0x16338 + 4*i) == 0, i=0..4   # sample delta array
read32(gm + 0x1634C + 4*i) == 0, i=0..4   # inter-sample delta array
read32(gm + 0x16360) ~= reset GetTickCount()
read32(gm + 0x16364) == 0                  # accepted sample count
```

Thus a paused `0x000D`-only observation, before the server sends any
`0x0004[01]`, should establish all of the following:

| Postcondition | Meaning |
|---|---|
| `read32(gm+0x31AAD)==0x6E` | the scene request was stored |
| four vptrs still match section 4 | no object teardown/vptr corruption occurred during cleanup |
| `read8(gm+0x31C72)==1` | execution passed all cleanup calls and reached the Hansol flag setter |
| reset fields above match | the final null-reset call executed |
| client emitted `C->S 0x0016 [01]` | the reset call continued through its count-less-than-five branch and reached the transport sender |

`FUN_005D49C0`, called during step 4, clears notice fields C8, CC, D0, D1,
D2, D6, and D7. It does not clear the path at `gm+0x4B1F3`. Consequently the
armed D0/D1/tick/countdown values are specifically `0x0003`-only
postconditions and are expected to be zero again after a completed `0x000D`.

The null reset does **not** clear readiness latch `gm+0x31C71`. A clean
transition experiment must prove that latch is zero before `0x000D`; otherwise
the room dispatcher can consume stale readiness without the five new samples.

### Packet-faithful calibration timing

The null reset itself starts calibration. After zeroing the state,
`HandleS2C_0004_CalibrationSample` sees count 0, constructs a one-byte value
`01`, and synchronously calls the generic sender with opcode `0x0016` and
length 1 at `0x0059DFDE..0x0059DFED`. The request/response progression is:

```text
0x000D null reset -> client C->S 0x0016 [01]
server S->C 0x0004 [01 + timestamp] #1 -> count 1 -> client C->S 0x0016 [01]
server S->C 0x0004 [01 + timestamp] #2 -> count 2 -> client C->S 0x0016 [01]
server S->C 0x0004 [01 + timestamp] #3 -> count 3 -> client C->S 0x0016 [01]
server S->C 0x0004 [01 + timestamp] #4 -> count 4 -> client C->S 0x0016 [01]
server S->C 0x0004 [01 + timestamp] #5 -> count 5, inbound byte mutates to FF
common dispatcher sees FF -> gm+0x31C71=1
room 0x0B consumes readiness -> hansol.wmb -> room 0x6E
Hansol stage 0 -> client C->S 0x0064 [one-byte local status]
```

There are five client `0x0016[01]` requests in this handshake: one emitted by
the null reset and one after each of samples 1 through 4. The fifth sample
does not emit another request. A normal `S->C 0x0016[00]` heartbeat reply may
be interleaved on the wire, but it is not a calibration sample and must not be
counted as one. After the fifth sample, `gm+0x31C71=1` can be transient because
the room dispatcher clears it after passing the Hansol load gate; observing
the fifth-buffer mutation/common-dispatch write is more reliable than slow
polling for the latch.

### 0x0003 to 0x000D delay and stop conditions

No binary-enforced wall-clock minimum was found. The mode-0 `0x0003` handler
is synchronous: it copies the path and completes the popup writes before it
returns to the dispatcher. `0x000D` neither tests the notice ticks nor waits
for a popup update frame; it immediately closes that popup during its own
cleanup. Therefore the static minimum is one completed handler boundary, not
a fixed millisecond or render-tick delay. In a controlled run, gate `0x000D`
on the read-only `0x0003` postcondition table in section 2. Once that snapshot
passes, no additional sleep is justified by the binary. If the packets are
sent back-to-back without an observation gate, the experiment loses proof of
the intermediate state even though sequential dispatch can still be valid.

Stop and discard the process as a clean baseline if any of these occur:

- any of the four vptr preconditions fails, or the process faults in a cleanup;
- `gm+0x31C71` is already 1 or `gm+0x16364` is nonzero before `0x000D`;
- `0x0003` path/armed postconditions cannot be observed before `0x000D`;
- before any new sample, the `0x000D`-only scene, flag, reset fields, or initial
  `C->S 0x0016[01]` request do not match the table above;
- samples 1 through 4 do not advance count by exactly one and each produce the
  next `C->S 0x0016[01]` request;
- `C->S 0x0064`, a readiness latch, or Hansol room work appears before sample
  5, indicating stale state or interleaving;
- sample 5 does not leave count 5 and take the client-mutated `FF` common
  dispatch path, or the client changes out of mode 0 before calibration ends.

These are fail-closed diagnostic conditions. They do not authorize repairing
any client field or vptr in memory.
