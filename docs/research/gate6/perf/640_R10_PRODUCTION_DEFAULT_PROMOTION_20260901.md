# 640 — r10 production default promotion

Date: 2026-09-01 KST

## Decision and result

- **USER-AUTHORIZED / DEPLOYED:** r10 safe-republish has been promoted from an
  opt-in canary to the production default. This is an explicit user decision;
  it does not rewrite the statistical admission-v1 result in #636/#639.
- **VERIFIED HTTPS:** `index_d3d9web_pathouse.html` defaults to r10,
  `azrok_launch.js` emits r10, and the visible server-list loads
  `azrok_launch.js?v=perf-facewishle-r10`.
- **VERIFIED identity:** both entry paths send the complete r10 identity set:
  `faceWisHle`, `ownerThreadIdentity`, `faceOwnerTrace`,
  `faceOwnerReadwait`, `faceOwnerCausalWis`, `faceRetry`, `faceScopedGen`,
  `faceWarmup`, `faceCwdDiscovery`, and `faceCwdSafe`, all set to `1`.
- **VERIFIED assets:** r10 JS/Wasm/cache are HTTP 200 and byte-identical to the
  recorded r10 build. No service restart was used; `azrok-core`,
  `azrok-bridge`, and `azrok-web` remained active.
- **NOT VERIFIED:** this deployment check intentionally did not press the
  connection button because that sends the browser-bound private-session
  identifier. Therefore remote r10 PatHouse entry and live HLE counters were
  not re-measured in this promotion turn. #639 remains the actual local
  equal-phase PatHouse performance proof.

## Default identity

```text
runtimeStem = boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1r10cwdrepublish1
jitCacheUrl = /profiles/azrok-jit-grouped-multidirectloops1-currentabi1-facewishle1r10cwdrepublish1-map13009736-r1-20260901.zip
```

| object | SHA-256 |
|---|---|
| JS | `35d072b873077702ca2d2d09bfdb78b5b1c8b9608b85d40f67520f4e78cc8be3` |
| Wasm | `02b95215e12232eef772a54c0775cd057b5ea833356862082f10e11aba1ef268` |
| cache | `7fd921fe3fad86ce280360a876a6b946a2fdee718fc51a596119f2dd10ee9878` |
| manifest | `67e2be8547e714fbbf4318fea5a802d770fffc8555cc5a5a052c0453906c9705` |

## Validation

```text
node --check tools/boxedwine_local/azrok_launch.js
node tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-face-r10-cwd-safe-runtime-cache.mjs
node tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-face-cwd-safe-page-contract.mjs
python -m unittest tools.test_d3d9web_page_contract tools.test_azrok_home_contract
```

All checks passed (44 Python contract tests).

## Rollback

Remote production copies and the pre-promotion page/server-list are under:

```text
/home/u32ws/32dev/azroksrv/rollback/r10-production-default-20260901
```

Do not restart services for this static rollback. The pre-promotion page was
byte-verified against its recorded remote SHA. The launch script fallback is
functionally reconstructed from the exact pre-deploy hash boundary because the
first backup command had a shell-quoting failure before the static upload;
the incident is retained here rather than hidden. The current r10 copies are
also retained in that directory.
