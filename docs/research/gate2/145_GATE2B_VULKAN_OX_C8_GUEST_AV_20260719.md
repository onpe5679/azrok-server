# 145 Gate 2b: reproducible Vulkan OX C8 guest access violation

Date: 2026-07-19

Status: **VERIFIED** client-side crash boundary, faulting module/RVA, fault
instruction and render-loop caller; root ownership defect is **NOT VERIFIED**.

## Reproduction without D3D trace

To eliminate the prior frame-rate instrumentation effect, the same native
BoxedWine/Wine 11 Vulkan prefix was rerun with `WINEDEBUG=-all`. The natural
path again reached:

```text
C2S 006B -> S2C 006E -> C2S C8 -> S2C C8 (14 bytes) -> client disconnect
```

The server had no exception and the BoxedWine stdout ended only with
`Boxedwine shutdown`. This reproduces the termination without `+d3d9,+d3d`.

## SEH confirmation

The next otherwise-equivalent run used `WINEDEBUG=+seh,+tid`, avoiding the
per-frame D3D trace. It reached the same natural C8 boundary and emitted:

```text
0024:trace:seh:dispatch_exception code=c0000005
    (EXCEPTION_ACCESS_VIOLATION) addr=7F3BDFB8
...
0024:trace:seh:dispatch_exception code=c0000005 addr=00000000
0024:err:seh:NtRaiseException Unhandled exception code c0000005 flags 0 addr (nil)
Boxedwine shutdown
```

The server had already sent the exact 14-byte S2C `0x00C8` when the client
reset the TCP connection. No server-side exception or Windows Application
Error event attributable to Azrok/BoxedWine was recorded.

## Fault module and instruction

The subsequent narrow `+seh,+unwind,+loaddll,+module` run mapped native
`acknex.dll` at guest `0x7F3A0000`. Its first fatal instruction was
`0x7F3BDFB8`; a direct PE image-base check gives preferred VA
`0x1001DFB8` / RVA `0x1DFB8`.

**VERIFIED (bytes directly decoded):** the containing code begins at
`acknex.dll!0x1001DF90` and calculates panel dimensions. When a panel has a
non-null background-BMAP at `[ebx+0x24]`, it executes:

```text
1001DFB8  mov ecx, dword ptr [eax+0x10]   ; BMAP height
1001DFBB  shl ecx, 0x0a
1001DFBE  mov dword ptr [ebx+0x40], ecx
1001DFC1  mov edx, dword ptr [eax+0x0c]   ; BMAP width
```

The SEH register record at this instruction has `eax=0x00001800`, making the
failing read exactly `0x00001810`. The preceding `cmp eax,0` / `jz` null
branch was not taken. This is a non-null invalid BMAP pointer, not a null
pointer.

Windows-native OX completed with the same all-zero 14-byte S2C C8. The new
`WINEDEBUG=+file` reproduction opened `Data\MultiGame\OXGame\OXbasePan.wis`,
`bolrok.wis`, `Data\Space\OXquiz\black_3.MDL`, OX UI WIS files, and
`Data\sound\OXquiz_back.mp3` successfully; no OX-entry `NtCreateFile` failure
or case mismatch was observed. Thus C8 fields and Win32 asset-open failure are
excluded. A WIS/BMAP decode-path partial initialization or BMAP lifetime error
remains **NOT VERIFIED**.

## Static MCP correlation

**VERIFIED (Ghidra MCP):** `Azrok.exe!FUN_00606B90` calls OX setup
`FUN_005F7DF0`; it assigns an OX state `+0x8e` time-digit BMAP array into two
panel `+0x24` fields. The array is loaded by `FUN_005F6F60` from
`Data\\MultiGame\\OXGame\\Time%d.wis`. The asset-open trace proves the Wine
filesystem case-folds these requests and reads `time0.wis` through `time9.wis`
successfully, so this establishes a direct C8-to-panel path, not a filename
failure.

Acknex direct call sites for `FUN_1001DF90` are `0x10010952`, `0x1001E0C6`,
`0x1001E1DD`, and `0x1001F001`. At `0x1001E1C1..0x1001E1E1`, code calls the
BMAP loader, stores EAX to `[panel+0x24]`, then immediately calls panel
auto-size. The expected fault-return address for this writer is `0x1001E1E2`.
The BMAP loader chain can return a non-null allocated/reused BMAP shell even
when its inner population routine reports failure, so partial initialisation
remains a direct static candidate. This is **not** a claim that a loader error
returns uninitialised EAX: its ordinary error result is verified as zero.

The invalid value is not a fixed sentinel: one SEH run had EAX `0x33006D00`,
another EAX `0x00001800`, both at the same panel auto-size read. That supports
an ownership/initialisation defect over a packet field.

## OX countdown lifetime check

**VERIFIED (Ghidra MCP):** the tempting “reload and free a digit every
second” explanation is false. `FUN_005F6F60` loads all ten
`Time0.wis` through `Time9.wis` once into the OX state `+0x8e` array. On a
countdown update, `FUN_005F7DF0` only selects two already-loaded entries and
writes their addresses to the two digit panels' `+0x24`; it contains no BMAP
allocation or release. The timer tick itself is therefore not the direct
freeing operation. The remaining branches are a later overwrite of the panel
field/state array, or object/panel lifetime/reuse elsewhere.

## Guarded host-side exception measurement

The rejected guest debugger was replaced with the BoxedWine-recommended host
exception boundary, `KThread::runSignal`. A one-shot condition on
`SIGSEGV && EIP==0x7F3BDFB8` was built into the local BoxedWine executable.
Every guest dereference in the logger is guarded by `KMemory::canRead`; this
does not inject a debugger or modify the game/Wine code path.

The identical Vulkan/Wine 11 OX route then produced:

```text
AZROK_OX_BMAP_AV eip=7F3BDFB8 fault=33006D10 eax=33006D00
                  ebx=06AF4B78 esp=7F1C31A0 bmap_readable=0
AZROK_OX_BMAP_STACK 00000001 00000000 7F3B0957 06AF4B78 ...
AZROK_OX_BMAP_PANEL panel_bmap=33006D00
```

**VERIFIED:** `EAX` and the panel's stored `[EBX+0x24]` agree, and that BMAP
address is no longer readable when the draw occurs. `ACK_PanelAutoSize` saves
ECX and EBX before the fault, making `[ESP+8]` the return address:
`0x7F3B0957` rebases to `acknex!0x10010957`.

Ghidra MCP directly decompiles that caller (`FUN_10010940`) as the generic
panel-render path: it calls auto-size only when panel width/height is zero,
then uses the same `[panel+0x24]` BMAP for rendering. This is not the
immediate OX BMAP setter at `0x1001E1E2`; the pointer was already stale before
the renderer reached it.

**VERIFIED static consequence:** the normal BMAP allocation path
`FUN_10011CC0` zero-initialises a 0x64-byte BMAP shell and returns that shell
even when its inner bitmap population routine fails. A standalone decode
failure therefore leaves a readable object with zero dimensions; it does not
by itself explain the unmapped `0x33006D00`. Lifetime/ownership or a later
pointer overwrite is now the stronger hypothesis, still **NOT VERIFIED**
until the free/write source is measured.

Two additional guarded host runs tested whether the recurrent unreadable
`0x33006D00` becomes invalid through BoxedWine's normal virtual-memory paths.
Neither `KMemory::unmap` nor `KMemory::mprotect` received a range containing
that address before the identical OX AV. Thus ordinary page release and read
permission removal are **excluded** for this value. It was either assigned as
an invalid value at source, or overwritten through a raw write that does not
change the page mapping.

**VERIFIED (Ghidra MCP):** the game-specific `Time%d.wis` loader
`FUN_00502C70` first calls Acknex `bmap_createblack`, stores its return in the
resource, then fills BMAP `+0x1c` pixel memory and `+0x0c/+0x10` dimensions
from the WIS stream. `bmap_createblack` delegates to Acknex
`FUN_10011CC0`. This makes an invalid source value from the OX WIS/BMAP
creation path a live branch alongside a later raw overwrite; it is not yet a
dynamic attribution of `0x33006D00` to that return.

## Rejected debugger method

A one-hit hardware-breakpoint guest launcher using `DEBUG_ONLY_THIS_PROCESS`
was built to stop at `acknex+0x1DFB8`. It exited before Acknex loaded
(`child_exit=0xC0000005`, `bmap_hit=0`), so it is a BoxedWine guest-debugger
compatibility failure and supplies no OX evidence. It must not be reused for
this path.

An attempted host CodePage write watch based only on the panel's repeating
low-address offset also exited during Wine bootstrap: the offset collides with
unrelated Wine pages before OX has allocated its panel. It is rejected as an
unsafe addressing method and supplies no OX evidence. The code was removed
before the subsequent `mprotect` run.

## Conclusions

- The OX exit is reproducible without full D3D logging, so trace-induced frame
  rate is **excluded** as its cause.
- The direct failure boundary is an Acknex panel-background BMAP dereference
  during BoxedWine/Wine handling of S2C C8, not a missing server response.
- The recurrent unreadable BMAP did not reach that state through BoxedWine
  `unmap` or `mprotect`; source creation or a raw overwrite remains.
- 144 remains valid only for its narrow negative result: no D3D9
  `Reset`/device-loss event occurs at OX entry. Its former suggestion that the
  exit was non-deterministic is superseded by this reproduction.

## Next measurement

Trace the actual source assignment, not a guessed heap address: capture the
return of Acknex `bmap_createblack`/`FUN_10011CC0` and the OX resource-array
write, then compare it with the panel setter. Any next dynamic hook must arm
from that function/event; the guest `DEBUG_ONLY_THIS_PROCESS` launcher and
low-address CodePage watch are rejected above.

## Count-array OOB check (revised)

**VERIFIED (Ghidra MCP):** the two-digit selector `FUN_005F7DF0` has no
bounds check: it writes `state[0x72 / 10]` and `state[0x72 % 10]` from the
ten-entry `Time0..9` BMAP array. In isolation, a negative value or a value
over 99 would be unsafe.

The condition is **not yet dynamically excluded for the observed C8 crash**.
The packet dispatcher `FUN_00605EE0` maps S2C `0x00C8` to `FUN_00606B90`,
`0x00C9` to `FUN_00606EF0`, `0x00CA` to `FUN_005F80F0`, and `0x00CD` to
`FUN_00607530`. C8 and C9 can increment `+0x72` conditionally; CA decrements
it; CD directly sets it to `ceil(payload_length / 4)`. The captured route has
no CD before the AV, but the C8 increment is guarded by a virtual-call result,
so `count=1` has not been measured. This is an OX participant/result counter,
not a locally decreasing timer: a slow-emulation negative-timer explanation
is excluded, while packet/order-driven OOB remains **NOT VERIFIED** until the
crash-time count and array are dumped.

The next dynamic sample must record state `+0x72`, its ten `+0x8e` BMAP slots,
and the two selected panel fields at the AV. It will distinguish in-range bad
array contents from a true OOB selection without changing the protocol.

## Reverse-linked AV snapshot (corrected)

> **SUPERSEDED within this section by the vtable-validated result below.**
> The first reverse-link pass accepted a structurally similar false positive
> (`0x7F20F5BD`, `count=-1`) because it checked only two panel offsets. It is
> not evidence about the actual faulting panel or OX count.

**VERIFIED (vtable filter result):** `FUN_005F6C00` writes `0x006AE124` as
the first word of the same complete panel layout initialized by
`FUN_005F6F60`: its constructor zeroes all twelve panel fields and both Time/
QNumber arrays. A follow-up AV scan required that vtable and searched every
one of those twelve panel slots. It found zero matches for fault panel
`0x06AF4B78` (five raw literal occurrences, zero valid OX owners).

The earlier `state+0x7a`/`count=-1` structure is therefore a false positive,
not evidence of negative-count OOB. The unbounded selector remains a static
robustness concern but is not dynamically tied to this AV. Separately,
`FUN_004FCCB0` is verified to call `pan_create` and, when its BMAP argument
is NULL, leave `PANEL+0x24` unwritten itself. That is **not** sufficient to
prove an uninitialised field: Acknex `FUN_1001E0E0` copies a 30-dword parsed
panel description into the created panel and immediately calls auto-size; a
garbage BMAP would be expected to fault during creation. The stronger branch
remains a later bad assignment or raw overwrite. Live ownership and the last
writer of the fault panel remain **NOT VERIFIED** until coordinate/creation
route capture.

## Fault-panel coordinates

**VERIFIED (guarded host AV log):** a subsequent identical C8 crash recorded
the faulting panel's fixed-point fields directly before the unreadable BMAP
dereference:

```text
AZROK_OX_BMAP_PANEL panel_bmap=33006D00 x=00073C00 y=00081800 flags=00004000
```

`x=0x73c00 / 1024 = 463` and `y=0x81800 / 1024 = 518`. These do not match the
known twelve `CPopupOXResult` panel creation coordinates (Time, QNumber, result,
or auxiliary panels). Together with the vtable-validated zero-owner scan, this
directly excludes treating that twelve-slot layout as the owner of the AV panel.
The next attribution must instead identify the panel creation route at screen
coordinate `(463, 518)` before making any count-array or Time-WIS claim.

## Evidence

- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_no_trace_ox_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_seh_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_stack_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_file_0517_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_bmap_watch_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_host_bmap_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_bmap_unmap_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_bmap_mprotect_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_panel_watch_stdout.log` (rejected)
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_panel_coords_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/server_9200_wine11_vulkan_seeded_stdout.log`
