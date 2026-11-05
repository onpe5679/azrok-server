# 204 Gate 2c dual-SSE AOT browser A/B and worker cleanup

Date: 2026-07-21

## Scope

This gate continues document 203 without repeating the broad CPU profile. It
tests the two already measured pure-SSE kernels in one original `Azrok.exe`
browser session and records an important browser-test isolation failure.

## VERIFIED -- two exact interpreter/AOT oracles

The first AOT covers `FUN_101041d7` (204 bytes). PatHouse actually samples the
adjacent projective-coordinate kernel `FUN_101042a3` (244 bytes), including an
EIP at relocated address `0x7F464393`, so the second function was added too.

Both functions now have a NormalCPU differential oracle. Each runs the exact
guest bytes through the interpreter and the direct AOT under 12 aligned,
unaligned, random, destination/source/matrix alias, and overlap layouts. The
oracle compares 512 bytes of memory, all GPRs, ESP/EIP/EFLAGS, lazy flags, and
XMM0..7 bit-for-bit.

The tests found two real implementation errors before deployment:

- the first AOT reread `source+8` after an aliasing destination store;
- the second AOT reassociated the matrix row additions and differed by 1--2
  ULP.

After snapshotting source Z and restoring original SSE addition order,
`BoxedWine.exe 0 3 1` reports the stackified backend and both AOT tests `OK`,
with zero failures.

## VERIFIED -- browser relocation and live execution

The clean `hotaot5` session resolves the exact SHA's relocated targets as
`0x7F4641D7` and `0x7F4642A3`, then logs both functions enabled. Distributed
byte signatures and default-MXCSR guards remain mandatory; otherwise execution
falls through to the interpreter.

The complete 1024x768 PatHouse screenshot retains the carpet, walls, doorway,
table/stool, character face and shadow, HUD, Korean text, alpha, and corrected
culling. There is no OOM or D3D phase-6 error. Consecutive resource windows
hold `missing=0`, `bound_blocked=0`, and `live=132`; steady windows retire all
120 recurrent resources.

## VERIFIED -- worker isolation was required

Navigating the same browser tab did not reliably terminate the old pthread
worker pool. The new page could show a new canvas while the detached prior game
continued emitting CPU/bridge logs. Those mixed windows are invalid and are
not used here.

The accepted procedure is to close the tab, verify zero browser tabs and zero
established 9201/9200 connections, then open exactly one new tab. The clean
measurement had one tab, one WebSocket bridge connection, one TCP server
connection, and one game session.

## VERIFIED -- A/B result and limit

The first dual-AOT build repeatedly discarded its Acknex address cache when the
worker scheduled Wine helper processes. Four exact PatHouse workload windows
(`2160` uploads, `60440880` upload bytes, `240` direct calls, opcode `12:120`)
averaged **22.973 FPS**.

`hotaot5` pins the resolved Acknex `KMemory` per worker. Other processes now
take one pointer check and cannot trigger mapped-file lookup or cache reset.
Five exact clean-session windows measured 26.09, 27.10, 26.75, 25.29, and
22.46 FPS: mean **25.538 FPS**, an **11.17%** improvement over the faulty
dual-AOT dispatcher. Selection-screen windows also rose into roughly the
84--92 FPS range after warmup, but they are not the target workload.

This is an implementation proof, not the 65-FPS solution. The instrumented
AOT build is not directly comparable to document 202's counter-free 26.78-FPS
release mean, and two functions totaling about 4.05% of measured guest time
cannot close the remaining gap. The next implementation gate is the reusable
hot-block engine plus the measured call-free x87/memory trace.

## NOT VERIFIED

- Runtime-generated WebAssembly and worker-local table installation are not
  implemented yet.
- The current register-only stackified executor covers none of the already
  measured top PatHouse blocks; memory, branch, SSE/x87, and real codegen tiers
  are still required.
- 65 FPS, complete original audio parity, mouse camera attach/detach, and
  two-session multiplayer remain open.
