# 165 D3D9Web Phase 8 — measured mip chain and vertex declaration

Date: 2026-07-19

## Result

**VERIFIED in the local browser:** both real-client blockers identified after
Phase 7 now cross the complete guest COM → `INT 0x9A` → JavaScript → WebGL2
path.

The texture used the directly measured `8x8, levels=4, format=23/R5G6B5,
usage=0, pool=1` shape. Guest `GetLevelDesc` and `LockRect` returned the exact
level chain `8/4/2/1` with pitches `16/8/4/2`; all 170 packed bytes crossed the
bridge and were uploaded to four immutable WebGL mip levels.

The vertex declaration was taken from direct Ghidra MCP and Wine trace evidence
for the real 3D stride-52 path:

```text
POSITION0 FLOAT3 @0
NORMAL0   FLOAT3 @12
TEXCOORD0 FLOAT2 @24
TEXCOORD1 FLOAT2 @32
TEXCOORD2 FLOAT3 @40
stride=52
```

The browser rendered the indexed textured triangle through declaration handle
4 and read back exact quadrant colors:

```text
D3D9WEB_PHASE8_CREATE kind=declaration handle=4 elements=5
D3D9WEB_PHASE7_DRAW indexed=1 layout=decl:4 primitive=4 indices=3 stride=52 texture=1 bgraSwizzle=1
D3D9WEB_PHASE7_PIXELS red=255,0,0,255 green=0,255,0,255 blue=0,0,255,255 white=255,255,255,255 result=PASS
D3D9WEB_PHASE8_RESOURCE tex=23/8x8/levels4/170 pitches=16,8,4,2 mip=PASS vb=156/52 lock=PASS ib=6/index16 lock=PASS decl=5/stride52 result=PASS
D3D9WEB_PHASE8_RESULT=PASS
D3D9WEB_PHASE8_EXITCODE=0
```

No Azrok content was launched.

## Measurement basis

**VERIFIED dynamic:** the latest partial character-select probe contains 100,846
texture creations: 100,817 with one level and 29 with four levels. Levels zero
were not observed. It also records CreateVertexDeclaration 15,
SetVertexDeclaration 1,139,556, and DrawIndexedPrimitive 1,139,556. The clean
full session recorded 55 / 6,776 / 6,776 respectively.

**VERIFIED static:** Ghidra MCP decompilation of `acknex.dll` found device slots
86/87, immediate deep-copy lifetime requirements, the 64-element builder,
`D3DDECL_END`, and Stream 0 FLOAT3 declarations. A Wine trace independently
shows the stride-52 five-element layout above followed by the indexed draw.

## Implementation boundaries

- Texture CPU backing now packs up to 16 level-specific offset/width/height/
  pitch entries and keeps one stable embedded surface object per level.
- `Levels==0` resolves to a full chain although it was not observed in the
  partial scene; measured Levels 1 and 4 are the evidence basis.
- Declaration objects deep-copy up to 64 elements, hold their own COM lifetime,
  and support GetDevice/GetDeclaration even though only Release was measured.
- Host declaration mapping covers the measured FFP usages and ordinary D3D
  declaration scalar/vector types. Packed UDEC3/DEC3N remains demand-driven.
- Static evidence found only Stream 0 in this path, so multi-stream remains
  unsupported rather than speculatively implemented.
- The actual client still requires measured device lifecycle/capability calls,
  material/light state, and complete World/View/Projection composition before a
  bounded PatHouse launch is justified.

## Artifacts

- `tools/boxedwine_local/apps/D3D9Web_phase8.zip` — 75,483 bytes — SHA-256
  `6E970638D08BCF38A39BF092980C3A3B11A2F37A2900031C7BD848860E3AB33A`
- `tools/d3d9_web_backend/phase8_package/d3d9.dll` — 13,312 bytes — SHA-256
  `B33D49884416683BCF315E6C52863A87AA8799A95956D8803A848F9D4603CD49`
- `tools/d3d9_web_backend/phase8_package/bootstrap_client.exe` — 123,392 bytes — SHA-256
  `A9545C3584F9E0B6F35127D9933BECB5C4139B49CDD77BD41D81E6BD02106A63`
- `artifacts/web_backend/20260719_d3d9_mips_decl_phase8/browser_evidence.txt` — SHA-256
  `AF34FE3CBA4C5339FB0A3388B564885748179FCF5FF140572FCB2430868422C1`
- `artifacts/web_backend/20260719_d3d9_mips_decl_phase8/webgl2_mips_decl_indexed.png` —
  33,942 bytes — SHA-256
  `9564E7167B6310B40521A989E10BB81D9AF7D1086EF2E89B1BBC8699A94678A1`

## Next gate

Fill only the remaining methods directly present in Gate 1, then complete
material/light and matrix state. The next content launch is capped at one
PatHouse rendering proof; broad gameplay QA remains out of scope.
