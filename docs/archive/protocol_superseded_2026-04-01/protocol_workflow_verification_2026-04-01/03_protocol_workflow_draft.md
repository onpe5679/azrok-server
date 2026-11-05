# Azrok Protocol Communication Workflow Draft

Date: 2026-04-01
Status: draft based on strongest current evidence, with confidence labels

## 1. Workflow rules

This draft separates:

- `Observed-playable`
  - supported by current live log and local runnable setup
- `Binary-faithful target`
  - supported by reverse-engineered handler behavior
- `Excluded for now`
  - should not be in the minimum workflow

## 2. Phase-by-phase workflow

### Phase A: transport and login

Observed-playable:

1. accept TCP connect
2. accept `C->S 0x0000`
3. accept `C->S 0x0016` heartbeat immediately after connect
4. send `S->C 0x0016`
5. send `S->C 0x0000` login sparse-cache blob

Binary-faithful target:

- same as above

Exclude:

- `S->C 0x0002`

Reason:

- it zeroes `gm+0x31946`
- it also triggers a fresh client `0x0007`

### Phase B: readiness / calibration

Observed-playable:

- optional or effectively inert in the current local run
- current live server sends `0x0004` with byte `0x00`, but binary support for that is weak

Binary-faithful target:

1. send `S->C 0x0004`
2. payload:
   - `byte0 = 0x01`
   - `u32 @ +1 = timestamp`
3. repeat 5 times
4. let the client mutate the fifth sample to `0xFF` internally

Exclude:

- treating `0x00 + timestamp` as protocol-faithful

### Phase C: room bootstrap

Observed-playable:

1. send `S->C 0x0003`
   - `byte0 = 0x01`
   - string = `Data\\Space\\PatHouse\\0`
2. send `S->C 0x0007`
3. send `S->C 0x0005`
4. send `S->C 0x000A`
5. send `S->C 0x000B`

Binary-faithful target:

- same packet family
- with stricter field fidelity in `0x0007` and true `0x0004` readiness before it if aiming for full fidelity

Important `0x0007` rules:

- `+0x125..+0x12F`: use `0xFF` as empty/no-op sentinel
- `+0x1D4..+0x1D7`: `0xFF` means clear, `0` is a valid selector
- stat words `57..69`: keep zero

### Phase D: client follow-up after room bootstrap

Observed-playable:

- accept first `C->S 0x0007`
- the current live server re-sends the bundle once here
- later repeated `C->S 0x0007` is ignored

Binary-faithful target:

- be ready for `C->S 0x0007` after `0x0002` or `0x0006`
- for the minimum proactive bootstrap route, repeated `C->S 0x0007` should not create a reload loop

Conservative server rule:

- after bootstrap is already armed, do not keep re-sending full setup bundles on every `C->S 0x0007`

### Phase E: stable in-room operation

Observed-playable:

1. keep answering `C->S 0x0016` with `S->C 0x0016`
2. log `C->S 0x000C`
3. do not blindly answer `0x000C` until its contract is recovered

Binary-faithful target:

- likely add a response or reflected update path for `0x000C`
- exact response family still unresolved

### Phase F: later state-1 expansion

Observed-playable:

- not required for the current minimal room flow

Binary-faithful target:

1. only after state-0 room bootstrap is complete, consider `S->C 0x0064`
2. then bring in:
   - `0x0065` roster flush
   - `0x0066` remote spawn
   - `0x0068` remote state batch
   - `0x0069` action/coord updates
   - `0x006A` text
   - `0x006E` ready commit

Exclude:

- early `S->C 0x0064`

Reason:

- it forces `dispatch_state = 1` before state-0 work is finished

## 3. Include / exclude table

### Include in the minimum current workflow

- `C->S 0x0000`
- `C->S 0x0016`
- `S->C 0x0016`
- `S->C 0x0000`
- `S->C 0x0003`
- `S->C 0x0007`
- `S->C 0x0005`
- `S->C 0x000A`
- `S->C 0x000B`
- repeated heartbeat handling

### Include in the binary-faithful target workflow

- `S->C 0x0004(sample_kind=1) x5`
- possible `S->C 0x0006` if intentionally using the reset/seed path
- later `S->C 0x0064..0x0071` only after state-1 entry is genuinely wanted

### Exclude from the minimum workflow

- `S->C 0x0002`
- early `S->C 0x0064`
- blind echo of `C->S 0x0001`
- blind echo of `C->S 0x000C`
- assuming `C->S 0x0017` is mandatory in the currently reproduced flow

## 4. Highest-priority next verification

1. Recover the producer and field order of `C->S 0x000C`
2. Recover whether the real server answers `0x000C` with `S->C 0x000C`, state packets, or both
3. Close the packet-only Hansol / Plaza transition path without process-memory writes
4. Re-capture a longer live session to see whether `0x0017`, `0x0008`, or `0x0064` ever appear under real interaction

## 5. Draft summary

If the immediate goal is "packet-only normal play" rather than "perfect emulator", the most defensible current workflow is:

```text
login
-> heartbeat
-> login sparse blob
-> room bootstrap bundle
-> stable room
-> keep heartbeat alive
-> investigate and answer C->S 0x000C next
```

If the goal is "binary-faithful emulator", the server must additionally:

```text
implement true 0x0004 readiness
separate state-0 and state-1 carefully
delay 0x0064 until post-bootstrap
close the 0x000C contract
```
