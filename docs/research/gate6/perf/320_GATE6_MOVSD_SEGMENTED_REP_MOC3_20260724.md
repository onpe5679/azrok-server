# 320 MOC3 exact segmented-REP census

Status: **VERIFIED static/build/browser cache-OFF MOC3; guarded flat-path audit opened**

## Scope

319 requires an exact B5-only diagnostic before any Movsd candidate. MOC3 is a
private cache-OFF diagnostic with an independent stem and no record/replay or
Present path. It records only pre-interpreter state at the existing fn_8 entry;
it is neither a generated-Wasm optimization nor an FPS candidate.

## Exact layout and invariants

The snapshot is 335 little-endian U64 (2,680 bytes):

```
fn8Total, otherOpcode, invalidTag, nonB5Movsd, invalidMetadata,
b5Context[6][3][4], ecxBins[256], ecxOverflowCalls, ecxOverflowDwords
```

b5Context axes are source segment ES..GS, codegen-time cause
{ES-only, source-only, both}, and live helper-entry zero-base pair
{ES.address==0, source.address==0}. ECX is an EA32 pre-call requested dword
count; 0..255 get exact bins and larger values get both overflow calls and
requested-dword sum. It is never described as completed copy work.

The reader rejects invalid metadata and requires:

```
fn8Total = otherOpcode + invalidTag + nonB5Movsd + invalidMetadata + sum(b5Context)
sum(b5Context) = sum(ecxBins) + ecxOverflowCalls
invalidMetadata = 0
```

## Fail-closed loader and implementation

The MOC3 macro is MT-only and mutually excludes EOC, MOC2 and profile. It tags
tmpReg, preserves the existing three-bit memHelperValue shape, and stores
codegen-time {base, hasSetES, hasSetSource} in memHelperAddr only for static
B5. The helper reads live segment addresses before interpretation. This
preserves the distinction between selection-time hasSetSeg and runtime base
value. The dedicated page gate requires exactly movsdSegmentedRepCensus=1,
jitCacheUrl=off, its distinct runtime stem, and the absence (by key) of record,
capture and all other census keys. It exposes a pre-existing visible refresh
control only after ABI=1, 335 words and 2,680-byte layout validation.

Build/MOC3 completed at one low-priority compiler job with only the pre-existing
compiler warnings. Its private assets are JS SHA
7053AD8247B7436EBF2DDBD764AAF2E4FFD47D990B12AB0993D1234791E1ECF4 and Wasm
SHA E8BB5F10AE7D30DCF12A6CF659A0D9E3BA7A50545A132463EC7DA8A6B0C44C52. The
58 Wasm exports are the accepted 54 plus exactly the four MOC3 APIs; glue maps
all four and no dual-entry binding is present.

## Browser result

The private URL used the distinct stem, exactly MOC3=1 and cache-OFF; it
contained no record, replay, capture or other census key. The loader published
ABI 1 and word count 335 before guest start. A fresh tab reached the complete
visible 1024x768 PatHouse scene, and the visible refresh button produced two
snapshots around a nominal 25-second visible-room interval with no console
warning/error.

The exact delta has:

    fn8Total=7,181,476
    otherOpcode=4,762,346
    invalidTag=0
    nonB5Movsd=8,440
    invalidMetadata=0
    valid B5 context=2,410,690

Both reader invariants held exactly. The sole nonzero B5 joint cell was
source=DS, cause=source-only, ES.address==0 and DS.address==0, with all
2,410,690 calls. Thus B5 is 99.651% of the observed Movsd fallback
(2,410,690 / (2,410,690 + 8,440)), and this interval directly proves both the
source/destination runtime bases are zero for this bucket. The result does not
prove that every future workload has zero bases.

The exact ECX partition has 2,409,395 calls in bins 0..255 and 1,295 overflow
calls. Binned requested dwords are 71,622,529 and overflow requested dwords
are 36,080,246, for 107,702,775 total pre-call requested dwords. The largest
exact finite bins are ECX 30: 955,847; 1: 666,168; 16: 323,884; 128: 281,091;
2: 84,391; and 3: 45,033. No requested/completed or time/FPS equivalence is
claimed.

This opens only a separate static audit of a runtime-guarded flat REP path:
when both live bases are zero, retain existing movsr semantics; otherwise
emulate. The broader segmented generated loop remains separate. No cache,
replay or FPS result is allowed for MOC3 itself.
