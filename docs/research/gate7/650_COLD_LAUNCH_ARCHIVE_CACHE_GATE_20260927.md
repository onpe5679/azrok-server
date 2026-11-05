# 650 — Cold-launch archive cache gate

Date: 2026-09-27 KST

## VERIFIED — source and executed behavior

The server-list launcher started three large archive fetch/cache.put operations
on page load and awaited all of them after private admission. There was no timeout
or progress indicator. A pending cache operation or body therefore prevented
navigation indefinitely. Existing public-browser storage completed here; this
is not proof that the reporter had exactly the same storage/network failure.

Removed speculative pre-cache and its admission gate. The game shell already
loads app/root archives itself; the JIT loader independently fetches its archive.
The validated admission and all pinned app/root/runtime/bridge parameters remain.

The shell now treats Cache Storage as optional: open/match has a1.5s budget,
exceptions fall back to network, and cache writes never gate execution. Streaming
app/root download reports received/total MB, resets its60s idle budget per chunk,
and reports HTTP/network/idle failures visibly with refresh instructions.
The non-streaming legacy Response fallback is not the modern Chrome/Edge path;
a hung cached arrayBuffer on that fallback has not been verified.

## VERIFIED — validation and deployment

- Actual launcher VM behavior:11 cases.
- Actual shell loadFile VM behavior:15 cases, including stalled network/cache body.
- Page/home contracts:44 passed; shell syntax passed.
- Static backup: production rollback/coldload-20260927.
- Both script references use coldload2-20260927 to bypass immutable old scripts.
- Public downloaded launcher SHA256 matches local:
  1900e86c4a0c93bd2d0d433ad687910667470a87d68f5291e38890451fd0a85b
- Public downloaded shell SHA256 matches local:
  367acef8e840171bc416550da2ffa73703298c418e41697d9f2927ff30c65b37
- No core/bridge restart or game binary changes.

## Runtime acceptance

Unused isolated origin localhost18801 proxies production files and connects to
production WSS. Only the launcher host adaptation and diagnostic UI parameters
are changed by the pre-existing proxy. This avoids existing account/prefix/cache
without clearing user storage; it is not a separate physical computer.
Server selection navigated into the runtime without archive pre-cache waiting;
app/root download completed and Wine client boot began. VERIFIED: the original
purple character creation screen rendered with all four character choices.
The saved screenshot shows 174.2 FPS; this is visibility evidence, not a benchmark.
Evidence: artifacts/20260927_cold_launch_verified.png.
