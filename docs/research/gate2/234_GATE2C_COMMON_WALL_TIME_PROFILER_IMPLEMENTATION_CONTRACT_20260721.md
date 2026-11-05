# 234 Gate 2c common wall-time profiler implementation contract

Date: 2026-07-21

## Status and scope

- **VERIFIED (source):** the insertion points, nesting relationships, current
  Emscripten clock implementation, and browser-served runtime path below were
  read from the current tree.
- **INFERRED (design):** the proposed profiler should produce a closed
  Present-to-Present partition while keeping every nested region exclusive.
- **NOT VERIFIED:** no profiler source, browser asset, build, or runtime result
  was produced by this document.

This is an implementation contract, not a claim that the historical
instruction samples or independently-reset timers can already explain one
frame. Document 235 remains the boundary on all retained measurements.

## Required clock and frame boundary

The only accepted C++ clock in the Emscripten build is:

```cpp
static inline uint64_t wallNowNs() {
    return static_cast<uint64_t>(emscripten_get_now() * 1000000.0);
}
```

The local Emscripten 6.0.3 implementation in `src/lib/libcore.js` defines
`emscripten_get_now` as `performance.timeOrigin + performance.now()`. Main JS
absolute timestamps must therefore use the same expression, not bare
`performance.now()`:

```js
const wallNowNs = () => Math.round(
  (performance.timeOrigin + performance.now()) * 1000000);
```

Bare `performance.now()` remains valid for a duration wholly measured on the
main thread, but it cannot be compared with a worker absolute timestamp.

The frame boundary is the completion of opcode 11 `Present`, after the
synchronous `flushBatchedCommands()` has returned in
`source/opengl/d3d9web.cpp:785-787`. The interval from Present completion N to
Present completion N+1 is one frame. A report window is exactly 120 such
intervals after the accepted PatHouse scene is stable.

## Minimal file and API structure

Add one profiler interface and one implementation only:

```text
include/d3d9WebWallProfile.h
source/emulation/cpu/common/d3d9WebWallProfile.cpp
```

The Emscripten makefile already includes every `source/emulation/**/*.cpp`.
The header must be a compile-time no-op unless
`BOXEDWINE_D3D9WEB_WALL_PROFILE` is defined, so ordinary release code and the
hot inline soft-MMU path remain unchanged.

The following is the minimum compile-shaped public interface. Exact names may
change, but ownership and call direction must not.

```cpp
#pragma once
#include <cstdint>

class CPU;

enum class D3D9WebWallCategory : uint8_t {
    OutsideCpuRun,
    CpuRunResidual,
    HotAot,
    GuestAcknex,
    GuestD3D9,
    GuestOther,
    GetOp,
    DecodeMiss,
    SoftMmu,
    D3D9Bridge,
    D3D9GuestCopy,
    D3D9BatchCopy,
    ProxyWorkerTotal,
    Count
};

struct D3D9WebMainInterval {
    uint64_t startNs = 0;
    uint64_t endNs = 0;
};

#if defined(BOXEDWINE_D3D9WEB_WALL_PROFILE)
class D3D9WebWallScope {
public:
    explicit D3D9WebWallScope(D3D9WebWallCategory category);
    ~D3D9WebWallScope();
    D3D9WebWallScope(const D3D9WebWallScope&) = delete;
    D3D9WebWallScope& operator=(const D3D9WebWallScope&) = delete;
private:
    uint32_t token = 0;
};

D3D9WebWallCategory d3d9WebWallGuestCategory(CPU* cpu,
                                              uint32_t physicalEip);
void d3d9WebWallRecordMainInterval(const D3D9WebMainInterval& interval);
void d3d9WebWallPresentComplete(CPU* cpu);
#else
class D3D9WebWallScope {
public:
    explicit constexpr D3D9WebWallScope(D3D9WebWallCategory) {}
};
inline D3D9WebWallCategory d3d9WebWallGuestCategory(CPU*, uint32_t) {
    return D3D9WebWallCategory::GuestOther;
}
inline void d3d9WebWallRecordMainInterval(const D3D9WebMainInterval&) {}
inline void d3d9WebWallPresentComplete(CPU*) {}
#endif
```

`D3D9WebWallScope` must be declared as a normal local variable. Do not place
it inside opcode handlers or the `NEXT()` macro: those paths depend on
`MUSTTAIL`, and an outstanding C++ destructor can invalidate a required tail
call. A scope around `normalDispatch()` in its caller is safe because it is
destroyed only after the complete tail-called decoded block returns.

## Exact insertion points

### 1. CPU run root

In `normalPlatformMultiThreaded.cpp:265-280`, put the root scope inside the
`try` so exceptions still unwind it:

```cpp
try {
    D3D9WebWallScope cpuRun(D3D9WebWallCategory::CpuRunResidual);
    cpu->run();
} catch (...) {
    // existing recovery unchanged
}
```

The profiler's TLS root is `OutsideCpuRun`; therefore the time between calls is
not silently attributed to guest execution. Do not add another whole-function
scope to `NormalCPU::run`, because it would describe the same interval.

### 2. Hot-AOT and normal dispatch

In `NormalCPU::run`:

- wrap only `d3d9WebTryHotAOT(this)` at `normalCPU.cpp:950-953` with `HotAot`;
- wrap the selected call at `:955-968` with the cached guest-module category.

```cpp
bool handled;
{
    D3D9WebWallScope hot(D3D9WebWallCategory::HotAot);
    handled = d3d9WebTryHotAOT(this);
}
if (handled) return;

const auto guestCategory =
    d3d9WebWallGuestCategory(this, getEipAddress());
D3D9WebWallScope guest(guestCategory);
normalDispatch(this, nextOp); // or the existing pfn path
```

Module classification must not call `getModuleName()` on every block. Use a
fixed thread-local cache keyed by at least `(KProcess*, DecodedOp*, physical
EIP)` and resolve only misses to `acknex.dll`, the private `d3d9.dll`, or
other. The physical EIP prevents a recycled `DecodedOp*` from inheriting a
stale class.

### 3. getOp and decoder miss

Wrap all of `NormalCPU::getOp` (`normalCPU.cpp:891-933`) with `GetOp`. Add one
child `DecodeMiss` scope only around the miss work at `:897-925`, including
`decodeBlock`, pfn assignment, dynamic-address checks, and `addCode_nolock`.
Do not time the trivial `CPU::getNextOp` wrapper at `cpu.cpp:1213-1215`; it
would duplicate `getOp` and add another hot clock read.

With the stack rule below, a `getOp` reached from a terminating decoded block
is removed from that block's guest-module exclusive time and appears exactly
once as `GetOp`/`DecodeMiss`.

### 4. soft-MMU

The deep profiler must cover the public scalar gates in
`kernel/kmemory.cpp:836-930`, the direct dword gates in
`emulation/softmmu/kmemory_soft.h:79-109`, and the three bulk copies in
`kernel/kmemory.cpp:356-390`.

All of these use `SoftMmu`. Same-category recursion is collapsed by depth, so
cross-page `readd -> readb` does not read the clock again or double count.
When `SoftMmu` is entered under `D3D9GuestCopy`, it is suppressed: the bulk
guest-to-host copy remains one leaf category rather than being reported once
as copy and again as MMU.

This hot instrumentation is allowed only during selected complete deep-profile
frames. In a disabled build the header must compile away entirely.

### 5. D3D command and proxy boundaries

Wrap `callD3D9Web` (`source/opengl/d3d9web.cpp:443+`) with `D3D9Bridge`.
Add child scopes at:

| Category | Current source locations |
|---|---|
| `D3D9GuestCopy` | direct upload `:563`; direct DrawUP `:668-669`; generic command copy `:696` |
| `D3D9BatchCopy` | upload batch `:585-588`; generic batch `:781-784` |
| `ProxyWorkerTotal` | every `d3d9webDispatch*OnRuntimeThread` call, including `:569-570`, `:651-652`, `:743-744`, and `:767` |

The remaining exclusive time in the function is `D3D9Bridge`: descriptor
reads, validation, allocation/growth, state profiling, and control flow.
Guest-side packet construction before INT 0x9A is not inside this function; it
is retained in the enclosing `GuestD3D9` residual.

### 6. main JS interval

The page actually serves
`tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`. It is not
identical to `tools/web_backend/host/d3d9web-runtime.js`; do not edit or copy
the older file over the served file during this measurement.

For each synchronous proxy call, pass a pointer to a stack-local
`D3D9WebMainInterval` into `MAIN_THREAD_EM_ASM_INT`. Main JS writes
`startNs/endNs` around the complete `runtime.dispatch` or
`runtime.dispatchBatch`. The C++ worker consumes it before the synchronous
call returns. Writing a JS number as `uint64_t` requires explicit low/high
words in shared `HEAPU32`; do not cast a value above 32 bits with `>>> 0`.

The first 32 calls must verify:

```text
workerProxyStart <= mainStart <= mainEnd <= workerProxyEnd
```

Any violation invalidates cross-thread subtraction for that session.

The existing `hostBatchStart = performance.now()` at runtime lines
2203-2255 measures a separately-reset duration. It is useful as a diagnostic
cross-check, but it is not the frame-joined interval required here.

## Nesting-safe exclusive accounting

Each guest worker owns one TLS stack. At every real category transition:

```text
now = wallNowNs()
exclusive[top] += now - lastNow
push or pop category
lastNow = now
```

Rules:

1. Entering the same category as the current top increments a recursion depth
   and does not read the clock.
2. `SoftMmu` below `D3D9GuestCopy` is a suppressed token and does not change
   the stack.
3. Tokens carry a profile generation, so a scope created before a sampled
   frame cannot pop a stack created after activation.
4. Exceptions use RAII to restore the stack. A mismatched token increments an
   error counter and invalidates the window; it must never be guessed away.
5. `inclusive` values may be recorded for diagnostics, but only exclusive leaf
   values enter percentages.

The natural nesting is:

```text
OutsideCpuRun
  CpuRunResidual
    HotAot
      SoftMmu
    GuestAcknex | GuestD3D9 | GuestOther
      GetOp
        DecodeMiss
      SoftMmu
      D3D9Bridge
        D3D9GuestCopy
        D3D9BatchCopy
        ProxyWorkerTotal
```

`CpuRunResidual` and guest-module time therefore do not overlap. `GetOp` is a
child of whichever execution path requested the next block, and D3D copy/proxy
time is removed from `GuestD3D9` and `D3D9Bridge` residuals automatically.

## Proxy/main-thread overlap rule

`ProxyWorkerTotal` already includes main-thread work because the guest worker
waits synchronously. Main JS must not be added on top of it. For every joined
interval:

```text
mainJsNs = mainEnd - mainStart
proxyWaitNs = max(0, proxyWorkerTotalNs - mainJsNs)
```

The additive frame partition replaces `ProxyWorkerTotal` with
`proxyWaitNs + mainJsNs`, whose sum is exactly the original worker interval.
Main JS is a cross-thread subinterval, not a second CPU percentage. GPU timer
queries are asynchronous supporting evidence and never enter this CPU/wall
sum.

## Deep-frame activation and boundary residual

Always-on scalar-MMU timers would perturb the interpreter more than the work
being measured. Keep only Present timestamps always active. Select deep frames
deterministically after the stable-scene gate, for example eight of a
120-frame window with a fixed pseudo-random seed.

Activation occurs at the first `cpu->run()` entry after the selected Present
boundary. The short interval from Present completion to that entry is left in
`OutsideCpuRun/unclassified`; it is not reassigned to guest work. The selected
frame closes exactly at its next Present completion. This avoids maintaining
a hot logical stack while deep timing is disabled and preserves a closed wall
partition through an explicit residual.

## Multi-thread aggregation

The `pid,tid` that emits opcode 11 is the render critical thread. Its exclusive
categories use `frameWallNs` as a 100-percent denominator.

Other guest threads use a shared `(windowGeneration, T0, T1)` and clip TLS
intervals to those absolute timestamps. They are reported separately as:

```text
otherThreadsCoreX100 = sum(otherThreadExclusiveNs) * 100 / frameWallNs
```

This value may exceed 100 because threads overlap. It is parallel core demand,
not a render-frame percentage, and must not be added to the critical-thread
partition. Window publication needs an acknowledgement from every live
profiled thread; a terminated, silent, or generation-mismatched thread marks
the aggregate incomplete.

## Overhead and rejection rules

Each worker calibrates at least 8,192 clock reads. Every report includes raw
exclusive times, timer-read count, calibrated timer cost, category transition
counts, stack errors, main/worker ordering failures, and the explicit
unclassified residual.

Run three otherwise identical assets/scenes:

1. instrumentation off;
2. Present-only coarse profiler;
3. selected-frame deep profiler.

Reject the deep result if estimated timer overhead exceeds five percent of
the sampled-frame wall time, sampled frames are more than five percent slower
than adjacent unsampled frames, the exclusive partition error exceeds the
calibrated timer bound, or any join/stack/window completeness check fails.
Do not silently subtract timer cost into a negative category.

## Required report invariant

For the render critical thread:

```text
frameWallNs
  = sum(worker exclusive leaves excluding ProxyWorkerTotal)
  + proxyWaitNs
  + mainJsNs
  + OutsideCpuRun/unclassified
  +/- calibrated timer and timestamp quantization error
```

The output must contain `frames`, `wall_us`, `fps`, `deep_frames`, each
exclusive category in microseconds and percent, `proxy_total_us`,
`main_js_us`, `proxy_wait_us`, `other_threads_core_x100`, `timer_reads`,
`timer_overhead_us`, `sum_error_us`, and `incomplete`. A line with
`incomplete != 0` is diagnostic only and cannot guide optimization.

