# Gate 6 MOVSD warmed SMC DF1 closure (2026-07-25)

Status: **VERIFIED direct browser DF0/DF1 differential; helper-fallback row remains**

The private fixture now warms each direction from ECX=0 before its active-code
write. It directly asserts the relevant `FMASK_ALL` flags rather than relying
only on printed output; unrelated persistent CPU flags are deliberately not
part of the assertion.

With cache disabled, the sole CDP page ran MRGN4 then MRGF4 at entry `391`.
Both rows reported `0 tests FAILED`. MRGF4 logged its first JIT block,
direct-chain ABI, and for **each** DF direction `generated checked-write=1`
and `bailout-taken=1`.

Scripted exact MRGN4-vs-MRGF4 comparison passed both post-write and final
snapshots (all eight GP registers, flags, EIP, next opcode identity, seven
code bytes, and source dword). The new DF1 row directly proves:

```
post-write ESI=F000017C EDI=CFFFFFFF ECX=0 EIP=3 FLAGS=00000CD7
final      EAX=10203041 EIP=4 with the same DF1 ESI/EDI/flags
```

DF0 remains identical to 343. This closes the direct scalar SMC commit in
both directions. The required nonzero-live-DS fallback row is still pending:
it must warm with zero DS, then switch DS base nonzero while preserving the
same linear source, and prove generated checked-write=0 with exact
NormalCPU parity. Publication, MRG2, cache/replay, and FPS remain closed.
