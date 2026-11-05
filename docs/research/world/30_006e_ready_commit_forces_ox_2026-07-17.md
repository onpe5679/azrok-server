# Why the successful 0x000D session settles in OX, and the Plaza A/B (2026-07-17)

This note reconciles the clean dynamic success in PID `113980` with the
existing room-loader analysis and the current local server. It is a read-only
interoperability analysis of the original client; no binary or runtime memory
change is proposed.

## Proven session boundary

The clean trace proved that `S->C 0x000D[00]` itself succeeds:

- it stores global room request `0x6E`;
- all four cleanup calls return;
- it sets `gm+0x31C72=1` and resets calibration;
- five request-driven `S->C 0x0004[01]` samples complete;
- the client naturally emits `C->S 0x0064[01]`.

The capture then shows the server sending, in one response:

```text
S->C 0x0064 [entry_kind=0x0A, authoritative self ...]
S->C 0x006E [00 00]
```

The client remains responsive but settles at `scene_opcode=111` and phase 5,
which the live render identifies as OX. There is no second `C->S 0x0007` in
this interval, so the original `0x0007` flag selector is not what performs the
late `0x6E -> 0x6F` overwrite in this session.

## Deterministic 0x006E-to-OX chain

The previously documented `S->C 0x006E` ready flag has a direct downstream
room-selection effect:

1. `HandleS2C_006E_CommitReadyMode @ 0x006169D0` takes the normal path when
   payload byte 1 is zero. It copies payload byte 0 into two mode fields and
   sets its local ready byte at `this+0x129B=1`.
2. On the next `Hansol_PerFrameUpdate @ 0x00613470`, a nonzero `+0x129B`
   selects `FUN_00613A10`, then clears the ready byte again.
3. `FUN_00613A10` calls `FUN_00530FE0(0x0C)`.
4. `FUN_00530FE0` maps local room index `0x0C` to global room code `0x6F` and
   calls `GameManager_EnqueueRoomCode(0x6F)`.
5. The ordinary room dispatcher maps loader code `0x0C` to
   `level_load("OXQuiz.wmb")`, queues post-load code `0x6F`, and the post-load
   initializer sets phase 5.

> **SUPERSEDED (2026-07-17).** The following flow describes the historical
> `AZROK_PLAZA_REPLY_MODE=both` run, where the server deliberately included
> `S->C 0x006E`. It is not the current default and must not be used as the
> Plaza baseline. The `0x006E` ready commit is the deterministic OX selector.

Thus the historical `both` diagnostic flow was:

```text
0x000D -> global room 0x6E -> hansol.wmb / Hansol bootstrap
       -> C->S 0x0064
       -> server S->C 0x0064 + S->C 0x006E[00,00]
       -> ready +0x129B
       -> local selector 0x0C
       -> global room 0x6F
       -> OXQuiz.wmb / phase 5
```

The second byte of `0x006E` is decisive here: zero means successful ready
commit. The first byte is a persistent sub-mode selector, but changing it does
not remove the ready commit or the `0x0C -> 0x6F` per-frame branch.

## Local-server condition

The supported launcher/server default is now `AZROK_PLAZA_REPLY_MODE=0064`, so
the natural `C->S 0x0064` handler sends only the authoritative self reply.
`both` remains an explicit diagnostic mode for reproducing the OX route. The
same code also exposes read-only experiment modes `006e` and `none`; no client
modification is needed to isolate the replies.

The supported default has been independently re-launched and visually
confirmed as outdoor Plaza (`scene=110`, `phase=4`, `self_actor_id=1`) with no
S2C `0x006E`. This default Plaza result supersedes the historical OX wording
above and is the baseline for the next two-client roster test.

The authoritative `0x0064 entry_kind` is not the common OX selector:

- `0x0A` and `0x0B` set actor-local pending codes `0x2E/0x2F`;
- `0x00` and `0x14` do not perform that write;
- controlled fresh sessions with all four accepted kinds nevertheless reached
  the same OX scene when the successful `0x006E` reply was also present.

Likewise, `gm+0x31C73` is not required for this observed route. That flag is
used by the earlier `S->C 0x0007` selector, while controlled OX snapshots show
flags `31C71/72/73 = 0/1/0`.

## Ranked cause conclusion

1. **Directly supported:** successful `S->C 0x006E` ready commit causes the
   Hansol per-frame `0x0C -> room 0x6F` branch. This explains the final OX
   scene under every accepted `0x0064 entry_kind`.
2. **Not the common cause:** `0x0064 entry_kind=0x0A/0x0B` actor-local scene
   writes can affect actor state, but cannot explain the identical `0x00` and
   `0x14` results.
3. **Not this capture's route:** `gm+0x31C73` plus a repeated `0x0007` can also
   request `0x6F`, but neither condition is present in the controlled success.
4. **Superseded interpretation:** `scene_opcode=0x6E` immediately after
   `0x000D` proves only the first room request. In the historical `both`
   diagnostic run it was overwritten by `0x6F` after the deliberate successful
   `S->C 0x006E`; the supported `0064-only` baseline does not take that branch.

## Completed 0x0064-only observation

PID `83304` and the subsequent default session preserved the proven
`0x000D`/five-sample sequence. After natural `C->S 0x0064[01]`, the
`0064`-only reply mode omitted `0x006E`:

- global scene request and active phase immediately before/after `S->C 0x0064`;
- the `0x006E` handler ready byte at `+0x129B`;
- entry to `Hansol_PerFrameUpdate`, `FUN_00613A10`, and
  `FUN_00530FE0` with local index `0x0C`;
- the later `GameManager_EnqueueRoomCode(0x6F)` write;
- loader case `0x0C`, post-load `0x6F`, and final phase 5.

Expected A/B distinction:

| Reply after natural C->S 0x0064 | Expected discriminator |
|---|---|
| explicit `both` | ready byte becomes 1, per-frame `0x0C` branch runs, global room becomes `0x6F`, OX |
| supported default `0064` only | authoritative self is applied, but the `0x006E` ready byte and `0x0C -> 0x6F` branch do not occur; live screen is Plaza |

The live 0064-only result was `scene=110`, `phase=4`, `self_actor_id=1`,
`Responding=true`, with a visible outdoor Plaza and no `S->C 0x006E` in the
capture. The supported default was then re-launched without the one-shot
override and reproduced the same state. Do not test the failure byte of
`0x006E` as a destination selector: nonzero byte 1 deliberately takes the
client's error path and is not a safe Plaza candidate.
