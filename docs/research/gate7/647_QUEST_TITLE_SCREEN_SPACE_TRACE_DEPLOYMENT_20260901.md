# 647 — Quest-title screen-space trace deployment

Date: 2026-09-01 KST

## Change

- **VERIFIED:** the query-gated `questTitleTrace` path now records each
  eligible A4R4G4B4 DrawPrimitiveUP's decoded screen `min/max` rectangle and
  stage-0 UV `min/max`, in addition to handle, raw-byte FNV and fixed-function
  state.
- **VERIFIED:** positions are decoded from the unmodified original DrawUP
  bytes using the FVF position attribute.  This is diagnostic only: no
  rendering state, resource data, sampler or shader value is changed.
- **VERIFIED:** `node --check` and 44 D3D9Web/homepage contract tests passed.
- **VERIFIED:** local SHA-256 and deployed host SHA-256 both equal
  `5b7c7f016847e1d61c297b4fac08db3770e01b3f9f32667dc8fcb2fa83301b35`.

## Why

The previous A4 trace retained a bounded late draw family but could not prove
which dynamic texture rendered the visibly-corrupted upper quest row.  A
screen-space rectangle lets an actual PatHouse capture select the draw that
intersects the row before any further renderer candidate is changed.

## Boundary

- **NOT VERIFIED:** no account-bound session was issued in this step; the
  actual upper row's handle and source pixels remain unclassified.
- Default production rendering is unchanged unless `questTitleTrace` is
  explicitly present in the launch URL.
