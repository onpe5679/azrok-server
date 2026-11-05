# 403 -- Runtime logical-composite census source audit

Date: 2026-07-25  
Status: **VERIFIED static source audit; private diagnostic implementation PARTIAL; no build/browser result**.

The private source skeleton adds no generated inline condition and changes no
helper result.  At the unchanged BE/NBE/L/NL/LE/NLE helper boundary it records
the raw `lazyFlagType`, an invalid-type bucket, and potential b8/b32 logical
helper coverage.  Its ABI is six condition rows × (53 current-type buckets +
53 CFOF-predecessor buckets + two potential-width counters) = 5,184 bytes.

Static review caught two P1 defects before any build: CFOF alone cannot prove
its predecessor class, and a helper-boundary logical count is not an actual
direct admission.  The source now records `lazyFlagTypePrev` only when current
type is CFOF, and names the b8/b32 values `eligibleHelperByWidth`; it makes no
claim that a direct path ran.  The exact direct candidate remains closed until
a later implementation can prove its own admitted-versus-helper split.

The six target helpers, macro scope and invalid type bucket were audited.  The
remaining work is a distinct private Make/page/URL/loader route, compile and
Wasm export audit, then cache-OFF visible census.  No accepted asset, cache,
browser process, replay or FPS data changed.
