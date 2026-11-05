# 458 - INT9A B1 WebGL context admission failure

> Status: **VERIFIED failure before FPS; no candidate performance result.**

Fresh private INT9A B1 registered the exact replay identity (`154/48902/41721`)
but never reached a Present. The visible page textarea directly reports
`D3D9WEB_PHASE6_ERROR Error: WebGL2 context unavailable` from renderer creation.

No clean workload fingerprint, rate preflight or FPS row exists. This is not a
candidate performance result. Fresh B1 retry is next; no source/cache/asset changed.
