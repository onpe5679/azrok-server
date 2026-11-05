# 635 — r10 safe-republish static-only remote canary deployment

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED DEPLOYED CANARY:** r10 safe-republish is available on
  `playazrok.com` only through the explicit `faceCwdSafe=1` route layered on
  the prior nine diagnostic flags. It is not the homepage/server-list/default
  runtime.
- **VERIFIED PRODUCTION UNCHANGED:** the remote production FACE r5 JS, Wasm,
  and grouped cache remain byte-exact. The pathouse page still sets FACE r5
  when `runtimeStem` is absent, and `azrok_server_list.html` contains no r10
  stem.
- **VERIFIED HTTPS DELIVERY:** the r10 JS/Wasm/cache returned HTTP 200 with the
  exact local byte counts and SHA-256 values below. The HTTPS page contains
  both the r10 opt-in identity and the FACE r5 default.
- **VERIFIED PARTIAL REMOTE SMOKE:** a fresh remote browser loaded the signed
  canary URL and registered `143 groups / 44,395 blocks / 33,912 patches` with
  the r10 ABI/base. The original character-selection connection was reached.
- **NOT VERIFIED REMOTELY:** remote PatHouse entry and active FACE-HLE counters
  were not admitted. No UI workaround or forced remote character action was
  used. Local UI-less exact `player/Azrok1` C2S `0x0005` activation remains the
  evidence in #634, not evidence for the remote canary.

## Exact immutable identities

| object | bytes | SHA-256 |
|---|---:|---|
| r10 JS | 338,487 | `35d072b873077702ca2d2d09bfdb78b5b1c8b9608b85d40f67520f4e78cc8be3` |
| r10 Wasm | 3,171,343 | `02b95215e12232eef772a54c0775cd057b5ea833356862082f10e11aba1ef268` |
| r10 grouped cache | 7,150,020 | `7fd921fe3fad86ce280360a876a6b946a2fdee718fc51a596119f2dd10ee9878` |
| r10 manifest | 18,090,152 | `67e2be8547e714fbbf4318fea5a802d770fffc8555cc5a5a052c0453906c9705` |
| production FACE r5 JS | 332,064 | `b6cf4b8a386e5cd8417d93a247ed6eff31b0e03742a3e55e1a295cdbb6bc1220` |
| production FACE r5 Wasm | 3,094,493 | `68d7c2139293934a9b320b37f430220385c917ba10b6942d1aace39601c122d4` |
| production FACE r5 cache | 7,435,146 | `b66eb03460d1d4197ace6baaf41dd26cbbb922759ee991ce54bd869e755d5582` |

The runtime uses reloc-map base `13009736`, owner word `13009720`, stamp word
`13009724`, FACE helper `36`, and CWD ABI `1 / 7 counters / 56 bytes`.

## HTTPS and default-route verification

- `index_d3d9web_pathouse.html?canary=r10safe-20260901`: HTTP 200, r10 identity
  present, FACE r5 default present.
- r10 JS/Wasm/cache: HTTP 200 and exact hashes above.
- production r5 JS/Wasm/cache: HTTP 200 and exact hashes above.
- `azrok_server_list.html?canary=r10safe-20260901`: HTTP 200 and r10 stem absent.
- Remote origin page raw bytes are 284,971/SHA
  `2b8296a54ef66f62ffb8d31c162cc7fe100b9da189bd400b091c793c95a7bd4f`.
  The Cloudflare-delivered HTML is 285,330/SHA
  `fc12797ed05c83580282bac59f209d80d637555a6e34e077b30d3c080df4f8cb`;
  therefore page acceptance used exact identity/default strings plus immutable
  asset hashes rather than falsely claiming edge HTML byte identity.

## Canary URL contract

The signed canary URL uses:

```text
runtimeStem = boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1r10cwdrepublish1
jitCacheUrl = /profiles/azrok-jit-grouped-multidirectloops1-currentabi1-facewishle1r10cwdrepublish1-map13009736-r1-20260901.zip
flags       = faceWisHle, ownerThreadIdentity, faceOwnerTrace,
              faceOwnerReadwait, faceOwnerCausalWis, faceRetry,
              faceScopedGen, faceWarmup, faceCwdDiscovery, faceCwdSafe
ws          = wss://playazrok.com/azrok-ws
```

The issued ticket was valid for 12 hours. Its signed tail is intentionally not
persisted in this document; issue a fresh same-account ticket before later use.

## Restart incident and rollback state

- **VERIFIED INCIDENT:** `azrok-core` was restarted once after the static
  upload and before the instruction prohibiting restart was received. This
  restart was unnecessary and may have disconnected active sessions.
- Immediately after the prohibition, no second restart was performed.
- All four user services reported `active` after the incident.
- The on-disk server files were restored from the pre-canary rollback copy:
  - `azrok_server.py` SHA `1aec22ecb9e473cda272590f75f4d5e832bf789470615bf5fe4c649e26bd25f8`
  - `tools/run_server_only.py` SHA `4d528589515b10acb1a4a93c1fda4f876c61102ade9a9db96f26463068cffe6a`
- Because there was deliberately no second restart, the already-running core
  retains the loaded post-upload Python code until its next ordinary restart;
  its default auto-select threshold remains 8. The next ordinary restart will
  load the restored pre-canary files.

Rollback directory:

```text
/home/u32ws/32dev/azroksrv/rollback/r10-canary-pre-20260901
```

Rollback procedure, only if the canary static route must be removed:

1. Restore `tools/boxedwine_local/index_d3d9web_pathouse.html` from that
   directory.
2. Remove only the three new r10 immutable JS/Wasm/cache files.
3. Re-check the production FACE r5 hashes and default/server-list assertions.
4. Do not restart `azrok-core`, `azrok-bridge`, or `azrok-web` for this static
   rollback.

## Evidence

- `artifacts/performance/face_r10_cwd_safe_player_pathouse_20260901.json`
- `artifacts/performance/face_r8_vs_r10_safe_fresh_ab_20260901.json`
- `artifacts/performance/face_r8_vs_r10_safe_fresh_ab_run2_20260901.json`
- `artifacts/performance/face_r8_vs_r10_safe_fresh_ab_pooled_20260901.json`
- `artifacts/performance/r10_remote_canary_deploy_rollback_20260901.json`
- `tools/browser_diagnostics/verify_remote_r10_canary.py`

