# 229 Gate 2c production Write32Plan native fixture

Date: 2026-07-21

## Scope

This fixture tests the production `WasmMemoryWrite32Plan` contract introduced
for the future `0x1008E05E` helper. It exercises
`wasmMemoryPrepareWrite32`, `wasmMemoryValidateWrite32`, and
`wasmMemoryCommitWrite32` directly against the real soft-MMU page table.

This is native Test/x64 evidence for the reusable write primitive only. The
primitive is not yet connected to the production `0x1008E05E` dispatcher, no
browser asset changed, and no browser session was opened.

## VERIFIED -- resident writable Ram and same-page boundary

A materialized writable `PageType::Ram` page accepts dword writes at offsets:

- `0x000`, aligned;
- `0x001`, unaligned but wholly inside the page;
- `0xFFC`, the last wholly same-page dword.

For every accepted case, Prepare returns a ready plan, Validate accepts its
captured page identity, and Commit changes exactly the requested guest dword.

Offsets `0xFFD`, `0xFFE`, and `0xFFF` are rejected by Prepare because the
dword would cross the page boundary. An unready rejected plan is also rejected
by Validate and Commit.

## VERIFIED -- page-class and permission rejection

Prepare/Validate/Commit reject each of the following without committing the
requested value:

- writable anonymous lazy-zero Ram with `ramIndex == 0`;
- materialized read-only Ram;
- `PageType::CopyOnWrite`;
- `PageType::Code`;
- an invalid/unmapped page.

The lazy-zero case additionally verifies that Prepare does not materialize a
backing RamPage. These classes must continue through ordinary soft-MMU write
semantics rather than the direct prepared-write path.

## VERIFIED -- stale-plan fail-closed behavior

Three plans are prepared from valid resident writable Ram, then invalidated
before Validate/Commit:

1. the page permission changes to read-only;
2. the page type changes to CopyOnWrite;
3. the original page is unmapped and remapped with a different RamPage
   identity.

Validate rejects all three stale plans. Commit takes `KMemory::mutex`, repeats
the same validation, rejects all three, and leaves each sentinel dword
unchanged. Thus the captured flags, type, `ramIndex`, and RamPage base are not
treated as durable authority after Prepare.

Successful Commit deliberately calls `KMemory::writed` while holding the
memory mutex rather than directly storing through the captured host pointer.
This preserves the existing guest-write observer path.

## Verification

```text
MSBuild BoxedWine.vcxproj /m:1 /p:Configuration=Test /p:Platform=x64
BoxedWine.vcxproj -> ...\x64\Test\BoxedWine.exe

BoxedWine.exe 14 1 1
Test WASM Write32 Tier ... OK
0 tests FAILED

BoxedWine.exe 13 1 1
Test D3D9Web Hot AOT Scan Body Fixture ... OK
0 tests FAILED

BoxedWine.exe 0 15 1
...
Test D3D9Web Hot AOT Scan Body Fixture ... OK
Test WASM Write32 Tier ... OK
0 tests FAILED
```

## Status

- **VERIFIED native dynamic/static:** production Prepare/Validate/Commit API,
  same-page aligned and unaligned Ram writes, page-end rejection, page-class
  rejection, and permission/type/remap stale-plan no-commit behavior.
- **NOT VERIFIED multi-host-thread race:** Commit serializes validation and
  write with `KMemory::mutex`, but this fixture changes mappings sequentially.
- **NOT SUPPORTED by this fast tier:** dwords crossing a guest-page boundary;
  callers must replay them through ordinary memory semantics.
- **NOT VERIFIED production integration/browser:** the full `0x1008E05E`
  helper still needs to consume this plan transactionally and pass native
  differential plus browser release validation.

