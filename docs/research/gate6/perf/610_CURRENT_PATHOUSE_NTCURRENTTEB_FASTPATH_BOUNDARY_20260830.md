# 610 — Current PatHouse `NtCurrentTeb` fast-path boundary

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED hot chain:** Unix Wine `ntdll.so::NtCurrentTeb()` and its
  `pthread_getspecific(teb_key)` chain execute 283,067 times in the accepted
  20.008940-second / 471-Present game-CPU window: 600.99 calls/Present.
- **REJECTED:** replacing Unix `NtCurrentTeb()` unconditionally with the
  current guest FS base is not safe.  Wine has real thread-initialization and
  signal windows in which the pthread key already contains the correct TEB but
  FS has not yet been installed or has to be repaired.
- **REJECTED:** deriving the value directly from GS would reimplement the
  glibc-version-specific TCB/specific-array/key-generation ABI.
- **INFERRED candidate priority:** first fuse the exact cross-module
  `NtCurrentTeb → PLT → pthread_getspecific → return` region while retaining
  the actual TLS load.  This removes Wasm/dispatcher boundaries without adding
  a new semantic cache.
- **NOT VERIFIED:** the time share of the TLS load versus the entry/dispatcher
  boundaries, and the resulting FPS.  No TEB fast path is admitted before
  current-corpus fixtures and a real-PatHouse A-B-A.

## Verified current implementation

The exact Wine 11 Unix source is
`dlls/ntdll/unix/thread.c:1634–1637`:

```c
TEB * WINAPI NtCurrentTeb(void)
{
    return pthread_getspecific(teb_key);
}
```

The exact release mapping is:

| Stage | ntdll/libc file VMA | Current hits |
|---|---:|---:|
| `NtCurrentTeb` entry | ntdll `0x59184` | 283,067 |
| PIC/GOT continuation | ntdll `0x5918D` | 283,067 |
| `pthread_getspecific@plt` | ntdll `0x7A60` | 283,067 |
| ntdll epilogue | ntdll `0x591A1` | 283,067 |
| libc `pthread_getspecific` chain | libc `0x70DB0..0x70E11` | 283,067 per hot continuation |

The equal counts and direct call/relocation prove one current call chain rather
than unrelated TLS use.

## BoxedWine segment state

- `CPU.seg[FS].address` stores the current emulated FS base.
- `CPU.seg[GS].address` stores the current emulated GS base.
- `set_thread_area → KThread::setTLS` and later segment loads maintain the
  guest descriptor state.
- Under normal initialized Wine i386 Windows execution, Wine installs a TEB
  descriptor and FS resolves to that TEB.
- GS is used by glibc pthread TLS.  BoxedWine's `CLONE_SETTLS` path establishes
  the new thread's GS state.

`KThread` has no separate authoritative named TEB member that can replace the
Wine contract without learning or validating it.

## Why unconditional FS is wrong

The initialization order is decisive:

1. the main thread creates `teb_key` and publishes its value with
   `pthread_setspecific`;
2. later signal/process initialization installs the Windows TEB FS descriptor;
3. child threads likewise call `pthread_setspecific(teb_key, teb)` before
   `server_init_thread → signal_start_thread → init_syscall_frame` installs FS.

Therefore a valid, nonzero pthread value can exist while FS is not yet the
TEB.  Wine's i386 signal handling also anticipates damaged/different segment
state: it derives TEB from the stack mask at handler entry and then restores
FS/GS.  A direct FS return could fail before any guarded fallback is possible.

The PE-facing Wine `NtCurrentTeb` implementation can use `fs:0x18`, but that is
a different execution surface from the Unix `ntdll.so` function measured
here.  Conflating the two implementations is rejected.

## Safest candidate

The first admissible candidate is cross-module region fusion:

```text
NtCurrentTeb entry
  -> ntdll PIC thunk / GOT setup
  -> pthread_getspecific PLT
  -> libc TLS lookup
  -> epilogue / return continuation
```

The region must keep the real TLS loads, key bounds/generation checks, return
EIP, GP registers, flags, and fault behavior.  Only intermediate generated
Wasm function/dispatcher boundaries are removed.  Selection should be based
on resolved control flow and exact function shapes, not hard-coded absolute
guest addresses.

## Conditional learned-cache candidate

Wine 11 creates `teb_key` with no destructor and sets each thread's value only
during main/child initialization.  This makes an exact Wine-only per-KThread
learned cache conceivable, but it remains a second-stage diagnostic candidate.
It must at minimum:

- execute the original path for the first nonzero result;
- publish only per KThread, never process-wide;
- start empty for every clone/fork child;
- invalidate on KThread reset, process exec, and CPU reset;
- remain invalid during first-call signal re-entry;
- guard fast use with `FS base == cached TEB` and preferably
  `TEB+0x18 Self == TEB`;
- fall back to the original TLS path on any mismatch.

Generic `pthread_getspecific` memoization is forbidden because other keys may
change, be deleted/reused, or have destructors.

## Next gate

Finish and measure the lower-risk exact PIC-thunk clone/direct-tail candidate.
If boundary reduction is material but insufficient, extend the same cloning
mechanism into a validated `NtCurrentTeb` cross-module fused region before
considering any learned semantic cache.

## Source witnesses

- `artifacts/wine11_source/wine-11.0/dlls/ntdll/unix/thread.c`
- `artifacts/wine11_source/wine-11.0/dlls/ntdll/unix/virtual.c`
- `artifacts/wine11_source/wine-11.0/dlls/ntdll/unix/server.c`
- `artifacts/wine11_source/wine-11.0/dlls/ntdll/unix/signal_i386.c`
- `artifacts/wine11_source/wine-11.0/dlls/ntdll/signal_i386.c`
- `tools/boxedwine_local/bwujit_threaded_abi/source/kernel/`
- `tools/boxedwine_local/bwujit_threaded_abi/source/emulation/cpu/`
