# 325 R2 typed-tail canonical raw recovery audit

## Status

**VERIFIED filesystem/provenance; R2 remains BLOCKED fail-closed.** This is a
recovery audit only. It takes no new browser, FPS, record, replay, or cache
measurement, because 308 already fixed the population required to make such a
measurement meaningful.

## Fixed contract from 308

The R2 typed-tail coverage diagnostic may use only the original corpus with
34,322 JIT modules (34,324 ZIP members including manifest and profile),
50,346,643 archive bytes, and the source population that produces exactly
2,715 admitted tails plus 757 zero-reloc fallbacks. A fresh corpus with a
different population is not an equivalent replacement, even if it reaches the
same PatHouse scene.

## Direct recovery audit

`tools/boxedwine_local/profiles/azrok-jit-record-raw.zip` exists, but it is
not the original corpus. Its SHA-256 exactly equals the current census record:

| file | archive bytes | ZIP members | JIT modules | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `azrok-jit-record-raw.zip` | 50,714,251 | 34,228 | 34,226 | `6BD19F44148B8BE19BA51F6C6AB4CDAB011FF02350A41F478F3221729F304AFF` |
| `azrok-jit-record-r2tailcensus1-20260724-112023.zip` | 50,714,251 | 34,228 | 34,226 | `6BD19F44148B8BE19BA51F6C6AB4CDAB011FF02350A41F478F3221729F304AFF` |

Thus the generic `record-raw` name is a byte-identical alias of the six-entry-
short census input, not a recovered R2 source. The other retained raw-shaped
archives also fail the fixed population: `pre-diag68-backup` has 34,799
modules/46,217,305 bytes/SHA `073405...67C31`; the two parity/ABI2 backups are
byte-identical 41,792-module archives/62,459,642 bytes/SHA
`3C7ED6...AC13E`.

The historical R2 transform evidence is retained separately: its R2 log and
manifest name `azrok-jit-record-raw.zip` as input, record 34,322 modules and
50,346,643 input bytes, and produce the preserved R2 grouped archive
`11E76D21108404C6DEF6510602E14F66B4834FE61393D511C4E8449B2BF64543`.
That output SHA is provenance only. The original raw SHA is not preserved, so
it must not be guessed or inferred from the output.

## Conclusion

**VERIFIED:** no retained profile ZIP is the original 34,322-module,
50,346,643-byte R2 corpus. Reconstructing input from grouped R1/R2 outputs,
relaxing the count, or substituting any newer record would invalidate the
postmortem's numerator/denominator comparison and is prohibited. Do not build
or run the R2 census, replay it, or collect an FPS sample unless the exact
original raw is recovered from an independent archival source with its
provenance preserved under a new immutable name (never by overwriting the
current alias), then passes the unmodified 34,322/2,715/757/21,720 gate.
