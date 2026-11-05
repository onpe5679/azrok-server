# 646 — Quest title A4 R/G packing A/B

Date: 2026-09-01 KST

## Evidence

`FUN_00516160` creates a 32-bit GDI DIB, then packs it into the client A4
texture. Its byte-level pack writes source G into the D3D R nibble and source R
into the D3D G nibble. A query-gated host candidate compensated that swap at
A4R4G4B4-to-WebGL RGBA4 conversion.

## Actual result

- **VERIFIED:** the candidate booted through actual server-list-issued account
  and reached PatHouse quest panel.
- **VERIFIED / REJECTED:** upper quest title stayed corrupted.
- **VERIFIED / REJECTED:** unrelated UI colors shifted purple/green, proving
  the candidate changed channel interpretation but not the title defect.
- Production has no `a4SwapRG=1` parameter and remains unchanged.
