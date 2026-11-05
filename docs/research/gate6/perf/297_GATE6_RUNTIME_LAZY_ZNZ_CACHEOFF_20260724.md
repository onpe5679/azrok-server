# 297 — runtime-lazy Z/NZ cache-OFF PatHouse integrity gate (2026-07-24)

**VERIFIED browser/cache-OFF integrity; fresh record/replay and performance NOT VERIFIED.**

This gate deploys only the isolated `boxedwine.upstreamjit68runtimeznz1` runtime
after document 296's static, build, fixture, and fail-closed loader checks.  It
does not use a grouped replay cache and makes no FPS claim.

## Direct browser evidence

The single visible PatHouse tab used the candidate stem with `jitCacheUrl=off`
and completed the normal pulse-driven selection into a reference-complete
1024x768 PatHouse: carpet, furniture, `Azrok1`, and the Korean HUD were all
visible.  This is a real guest render rather than a loading or selection
screen.

The candidate script stream continued to report the async-ring main callback
windows with `gaps=0`, `reorders=0`, and `errors=0` (including the live
6001--6120 window).  The candidate-specific script URL emitted no console
error.  The page stayed visible throughout the observation.

## Direct transport evidence

The management API at port 9300 reported the local server running with one
client (`Azrok1`) in local PatHouse, a recent heartbeat, and a healthy,
writable structured capture with zero low-space drops.  Bridge logs recorded
the corresponding accepted WebSocket/TCP session and subsequent five-byte
heartbeat exchanges.  These transport facts are only used to corroborate the
visible guest scene; they are not a performance measurement.

During this check, three accidental HTTP diagnostic requests were sent to raw
game TCP port 9200.  The game server rejected their oversized declared payloads
immediately; they were not candidate traffic, did not crash the service, and
are excluded from this gate.  Subsequent checks use only management port 9300.

## Consequence

The runtime-lazy Z/NZ candidate clears the required cache-OFF real-render
integrity gate.  The next isolated step is a fresh candidate record, grouped
cache generation carrying the exact `runtimeLazyZNZ` manifest contract, and
replay verification (including the `fn_16/fn_17` measurement) before any
30-second A-B-A performance sample.
