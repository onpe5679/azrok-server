> **SUPERSEDED by 502.**

# 501 Gate 6 host upBatch compatibility rejection (2026-07-28)

## Superseded finding

The initial black-output observation was later shown to have inherited a
previous render-scale module cache. It must not be used to claim that
`upBatch` is incompatible.

## Preserved initial observation

- An initial `upBatch=1` launch showed a black 640x480 output. This was not
  a controlled result because the same browser tab had previously loaded the
  failed scaled-output runtime.
