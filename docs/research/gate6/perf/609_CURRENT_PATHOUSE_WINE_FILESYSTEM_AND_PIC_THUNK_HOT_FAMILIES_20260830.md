# 609 — Current PatHouse Wine filesystem and PIC-thunk hot families

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED module/source:** current PatHouse ranks 1 and 3 are not an
  unidentified renderer or codec.  They are loops inside Wine 11
  `hash_short_file_name()` in `dlls/ntdll/unix/file.c`: the case-insensitive
  8.3-name hash loop and the last-dot/extension scan.
- **VERIFIED dynamic:** the function-entry block ran 32,126 times in the
  accepted 20.008940-second / 471-Present owner-CPU window.  Its main hash-loop
  block ran 439,255 times and its extension-scan block 407,129 times.
- **VERIFIED libc:** other leading paths are glibc 2.38 `pthread_getspecific`,
  `strlen`, `readdir64`, and mutex lock/unlock, plus four exact 4-byte i386 PIC
  thunks of the form `mov reg,[esp]; ret`.
- **VERIFIED dynamic:** `readdir64` entered 64,756 times, with 63,296 successful
  dirent-update paths.  `pthread_mutex_lock` and the paired hidden unlock path
  each ran 61,070 times.
- **VERIFIED generic overhead surface:** the five active libc PIC-thunk
  instances account for 614,292 separate activations, while all exact
  BX/DX/AX/DI/SI/CX thunk byte hashes across the current corpus account for
  1,209,674 activations: 60,457/s, 2,568.31/Present, and 5.9759% of all
  20,242,521 owner-CPU generated entries.  The
  `pthread_getspecific` body/continuations plus its BX thunk alone form about
  1.415 million sequential entries, 6.99% of the total.
- **INFERRED priority:** a fail-closed clone/direct-tail optimization for exact
  tiny PIC thunks is more reusable than substituting this particular libc or
  Wine function.  It can benefit many 32-bit ELF PIC workloads.
- **NOT VERIFIED:** generated-entry percentage is not CPU-time percentage.
  Neither a PIC-thunk candidate nor directory-enumeration cache is accepted
  without an immutable, current-corpus, visually gated PatHouse A-B-A.

## Exact ELF identity

### Wine ntdll

```text
file   artifacts/performance/ntdll_current_wine11.so
bytes  578920
SHA256 3a03b005d9311f521ee26c49dd395850f9a379ba0d0195559bb383309eec88b7
ELF    32-bit i386 ET_DYN, build-id 71e7ba5b1150ae7099731c9c46eb158351f7fa1f
RX     file offset 0x7000 == VMA 0x7000
```

The executable segment has equal file offset and VMA, so the resolver's
`ModuleEip` values in this range are also their disassembly VMAs.

### libc

```text
file   artifacts/performance/libc_current.so.6
bytes  1655568
SHA256 141319771edb3c2ffbd91d7617dc133bc70eafa3bf718defa60d11ba5a729d7d
ELF    32-bit i386 ET_DYN, GNU libc 2.38, GCC 13.2.0
RX     file offset 0x22000 == VMA 0x22000, size 0xFF8B5
```

All mapped hot libc offsets lie in that equal-offset executable segment.

## Wine `hash_short_file_name`

The stripped ntdll has no local symbol table, so the containing function was
identified by exact disassembly/source equivalence rather than by assigning
the preceding exported ELF symbol.

Function start:

```text
file/VMA 0x15EB0
guest EIP 0x10635EB0
source dlls/ntdll/unix/file.c:1381
static ULONG hash_short_file_name(const WCHAR *name, int length, LPWSTR buffer)
```

The two current leaders map exactly:

| Guest EIP | File/VMA | Hits | Wine source operation |
|---|---:|---:|---|
| `10635F1F` | `0x15F1F` | 439,255 | lines 1395–1397, `0xbeef` case-folded rolling hash loop |
| `10635FAA` | `0x15FAA` | 407,129 | lines 1406–1409, scan for the last dot/extension |

The disassembly at `0x15F14` loads the exact initial hash `0xFFFFBEEF`.
At `0x15F1F` it performs `(hash << 3) ^ (hash >> 5)` and two lower-case table
lookups, matching the source loop.  At `0x15FAA` it compares successive UTF-16
characters with `'.'`, matching the last-extension scan.  The later code copies
four valid DOS characters, inserts `~` plus three hash characters, and copies
up to three extension characters as documented by the same source function.

The accepted census provides:

| Block | Hits | Hits/Present |
|---|---:|---:|
| function entry `10635EB0` | 32,126 | 68.21 |
| hash loop `10635F1F` | 439,255 | 932.60 |
| extension scan `10635FAA` | 407,129 | 864.39 |

These are generated-block entries, not source calls or elapsed time.  The
entry count nevertheless proves repeated per-frame 8.3-name work on the
owner CPU.

Two sibling ntdll filesystem functions were resolved with the same standard:
FDE boundaries, exact release disassembly, a symbolized Wine-11 sibling,
source control flow, and the exact number of direct call sites all agree.

| Release file/VMA | Function | Wine source | Entry hits | Hot inner block |
|---:|---|---|---:|---:|
| `0x155C4..0x1568B` | `is_legal_8dot3_name` | `unix/file.c:1556–1580` | 43,199 | invalid-char/dot loop `0x155F9..0x15633` |
| `0x18C97..0x199CB` | `lookup_unix_name` | `unix/file.c`, call sites 3773/3827/4133 | 887 | invalid-NT-char table scan `0x18D58/60`: 221,680/193,970 |

The high `0x18D58/60` totals are inner-loop entries, not 221,680 complete
path lookups: `lookup_unix_name` itself entered only 887 times, about 1.88 per
Present.  This distinction prevents a loop count from being mislabeled as a
filesystem-call rate.

## Wine `NtCurrentTeb` / libc TLS chain

`ntdll.so` dynamic symbol `NtCurrentTeb` is exactly `0x59184..0x591A5` and
matches `dlls/ntdll/unix/thread.c:1634–1637`:

```c
TEB * WINAPI NtCurrentTeb(void)
{
    return pthread_getspecific(teb_key);
}
```

Its entry and continuations `0x59184/18D/1A1`, ntdll
`pthread_getspecific@plt` at `0x7A60`, and the leading libc TLS path all have
283,067 hits, or 600.99 calls/Present.  This exact equal-count chain proves
that a material part of the leading libc traffic is Wine's current-TEB lookup,
not an unrelated application TLS consumer.  It also makes cross-entry/PIC
boundary fusion more broadly useful than a `hash_short_file_name`-only patch.

## libc mapping

The dynamic symbol table and exact disassembly establish:

| File/VMA range | Exact function/role | Accepted hits |
|---|---|---:|
| `0x70DB0..0x70E16` | `pthread_getspecific` | 283,067 at each hot continuation |
| `0x82710..0x827BE` | scalar i386 `strlen` | 67,296 entry; 63–67k inner continuations |
| `0x9F885..0x9F940` | `readdir64` | 64,756 entry; 63,296 successful update |
| `0x721F5..` | `pthread_mutex_lock` | 61,070 |
| `0x7369E..0x737B3` | hidden mutex-unlock implementation | 61,070 |

The exact internal unlock symbol is stripped.  Its independent FDE,
type-dispatch disassembly, paired count, and glibc wrapper structure verify
the role; the conventional local name `__pthread_mutex_unlock_usercnt` remains
**INFERRED** rather than exported-symbol fact.

## Exact i386 PIC thunks

The six libc blocks are independent 4-byte FDEs:

| File/VMA | Bytes | Effect | Hits |
|---:|---|---|---:|
| `0x11200C` | `8B 1C 24 C3` | return EIP to EBX | 286,960 |
| `0x112010` | `8B 14 24 C3` | return EIP to EDX | 106,955 |
| `0x112014` | `8B 04 24 C3` | return EIP to EAX | 66,156 |
| `0x112018` | `8B 3C 24 C3` | return EIP to EDI | 39,193 |
| `0x11201C` | `8B 34 24 C3` | return EIP to ESI | 115,028 |
| `0x112020` | `8B 0C 24 C3` | return EIP to ECX | 0 |

Wine ntdll also contains exact instances: BX `0x7B70` ran 425,011 times, SI
`0xBAF1` ran 108,215, DI `0x1471B` ran 33,082, AX `0xC888` ran 28,064, CX
`0x25F2E` ran 611, and DX `0x7C65` ran 397.  Two additional byte-identical
thunks in another mapped module ran once each.  Across the full 30,550-entry
corpus, 174 blocks have one of the six exact block hashes and 13 are nonzero
in this window; their total is 1,209,674.
The semantic operation is directly verified; the familiar local symbol
spelling `__x86.get_pc_thunk.{bx,dx,ax,di,si,cx}` is **INFERRED** because the local
symbols are stripped.

The current grouped cache places widely shared thunks in one group while many
callers live in other groups.  Cross-group calls therefore enter the generic
dispatcher and a separate generated Wasm function for two guest operations.
This is the bounded optimization surface: clone only an exact, relocation-free
4-byte thunk as an internal non-exported group function, then admit the already
known static caller edge as a direct tail.  The original exported entry and
loader identity must remain unique.

## Why directory-result caching is not implemented yet

The count chain strongly indicates repeated directory enumeration:

```text
readdir64 -> strlen/Unicode conversion -> optional 8.3 hash -> mutex/TLS paths
```

However, a reusable cache must preserve directory mutation, seek/tell/rewind,
file-creation visibility, case-sensitivity, and per-handle enumeration state.
The top-entry census does not establish an invalidation contract.  A cache
that merely remembers filenames could silently hide live filesystem changes.
It is therefore a second-stage candidate after caller/handle tracing, not an
admitted shortcut.

## Candidate order

1. Rebuild the already semantically admitted INT 0x9A direct helper against
   the exact current 94-group corpus and perform real-PatHouse visual A-B-A.
2. Build an opt-in exact tiny-PIC-thunk clone/direct-tail cache while keeping
   30,550 exported entries and the runtime ABI fixed; validate every module and
   relocation patch, then perform the same A-B-A.
3. Trace the repeated `readdir64` caller and directory-handle lifecycle before
   designing a mutation-aware directory-result cache.

The first candidate targets the D3D9Web bridge and is broadly reusable within
this renderer.  The second is architecture-level and can apply to unrelated
32-bit PIC programs.  Their effects must be measured separately before any
combined build.

## Artifacts

- `artifacts/performance/regional_anchored_full_entry_actual_pathouse_20260830.raw.json`
- `artifacts/performance/regional_anchored_full_entry_actual_pathouse_20260830.top.csv`
- `artifacts/performance/regional_anchored_map_actual_pathouse_20260830.json`
- `artifacts/performance/ntdll_current_wine11.so`
- `artifacts/performance/libc_current.so.6`
- `artifacts/wine11_source/wine-11.0/dlls/ntdll/unix/file.c`
