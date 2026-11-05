# 435. INT9A private record route: live-handler audit

Date: 2026-07-26  
Status: **VERIFIED safety hold; no private record POST was sent**

## Independent live and source evidence

Two independent audits agree on the record boundary.

* The current sole browser page remains the private cache-OFF URL, visible and
  focused with a CSS 1024x768 canvas. It directly reports ABI `1`, error-free
  asynchronous 120/120 submitted/reaped windows, and specialized
  `direct/fallback/fault=4,033,002/0/0` at the audit point. This confirms that
  434's rebuilt helper is live; it is not a record or replay result.
* 8765 is Python PID 66804, child of PID 67404, started at
  `2026-07-24 21:03:15Z` (local display: 2026-07-25 06:03:15 KST).
  `tools/boxedwine_local/server.py` containing the private route was modified
  at `2026-07-25 20:48:42Z`, about 23 h 45 m after that process started.
  A Python process cannot load that later source without a reload.
* The source handler at `tools/boxedwine_local/server.py:26-73` checks content
  length before accepting only `azrok-jit-record-raw` and
  `azrok-jit-record-int9aspecialized1`; the latter is atomically written to
  `profiles/azrok-jit-record-int9aspecialized1.zip`. This is the required
  identity separation but is **not** proof of the old live handler.

## Why a harmless HTTP version probe does not exist

`jit-record=true` necessarily submits a nonempty ZIP. The earlier handler can
accept that same request and atomically overwrite the generic raw path, while
the new handler would honor the private header. Invalid/zero-length or wrong
path requests are rejected before the identity decision in both versions and
therefore cannot distinguish them. A live POST would consequently risk the
accepted/generic raw artifact and is prohibited.

## Static record/replay contract

The page permits record only with the exact private stems,
`int9aSpecialized=1`, `jit-record=true`, and `jitCacheUrl=off`; it writes the
three-field private raw manifest identity and private upload header. The
transform pipeline requires the exact stem and a 64-character SHA-256 of the
uncompressed `boxedwine-jit-manifest.json` ZIP entry, not the archive SHA. It
rejects MRG/parity/logical identity mixing and emits ABI-1
`azrok-int9a-specialized-v1`. Replay keeps all three pins deliberately null,
so it fails closed before any fresh record/transform.

## Resume protocol

After a human-owned service-loop reload produces and verifies a new 8765
listener PID/start time, the only authorized sequence is:

1. fresh private `jit-record=true&jitCacheUrl=off` run;
2. verify the private response path and that generic raw remains unchanged;
3. derive the raw manifest-entry SHA, transform the private artifact, and
   pin raw/archive/grouped-manifest hashes;
4. static mutation rejection, fresh private replay-render integrity, then
   fresh-process 30-second Present A-B-A(B).

No candidate rejection, cache generation, replay, or FPS decision is implied
by this hold.
