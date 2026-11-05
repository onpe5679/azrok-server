# 443. Workload-fingerprint accepted A1 runtime

Date: 2026-07-26  
Status: **VERIFIED accepted diagnostic runtime; fresh-process stability remains open**

The fresh accepted replay (`94/30,550/28,944`) reached registered ABI1,
visible real Present windows, and then sealed the repaired fingerprint with:

```text
version=1 window=13 frames=120 batches=21480 bytes=14158560
hash=2109626789 invalidBatches=0 rejectedBatches=0
```

The command-call and command-byte arrays are retained in the live CDP record;
the corresponding renderer window had 120/120 submitted/reaped Presents,
inflight/max 1/1, ring-full 0, and errors 0. This is a non-FPS diagnostic.

Four seconds later the status had advanced from fingerprint window 13 to 37.
The new sealed window has exactly the same frame/batch/byte totals, all
per-command call/byte arrays, hash `2109626789`, and zero invalid/rejected
batches. Thus the witness is stable across 24 consecutive 120-Present windows
within this one accepted process.

This proves neither room identity nor cross-process stability, and it does
not repair 437 by itself. The next gate is a fresh accepted process with the
same role-neutral diagnostic; only matching clean tuples can authorize a
candidate diagnostic comparison.
