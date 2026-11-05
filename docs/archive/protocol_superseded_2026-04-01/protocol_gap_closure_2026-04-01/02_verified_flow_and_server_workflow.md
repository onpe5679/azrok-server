# Verified Flow And Server Workflow

This is the updated workflow draft after re-verification and gap-closure work.

## 1. Minimum packet-only PatHouse entry

Use the already re-verified state-0 sequence:

1. `C->S 0x0000`
2. `S->C 0x0000`
3. `S->C 0x0003`
4. `S->C 0x0007`
5. `S->C 0x0005`
6. `S->C 0x000A`
7. `S->C 0x000B`
8. keep tolerating `C->S 0x0016`

Still avoid these early:

- `S->C 0x0002`
- `S->C 0x0064`

`S->C 0x0004` remains a binary-faithful readiness side path, but the current PatHouse reproduction is not hard-gated on it.

## 2. Post-entry behavior that is now stronger than before

### `C->S 0x000C`

- This is now strongly tied to a selection/update path, not generic idle telemetry.
- It is emitted only when a cached selection snapshot differs from the active 9-byte stride table.
- Practical server draft:
  - accept it
  - log it
  - do not answer with raw `0x000C`
  - later, answer with authoritative actor slot/equipment updates only after the server understands the decoded meaning

### `C->S 0x0017`

- This is now proven to be a real `<BBI>` sender, not just a log artifact.
- Practical server draft:
  - accept it
  - treat it as late readiness/status
  - do not let first `0x0017` auto-fire early `S->C 0x0064`

### `C->S 0x0064`

- This is a 1-byte bootstrap progress flag from the Hansol path.
- Practical server draft:
  - accept it
  - do not echo it
  - if any follow-up is needed, use safe late-stage state packets, not same-opcode echo

## 3. Updated server workflow draft

### Phase A: login and room bootstrap

- Keep the server extremely conservative.
- Drive only the proven state-0 bootstrap packets.
- Do not inject scene-changing packets that are known to reset or advance the client too early.

### Phase B: steady PatHouse playability

- Heartbeat:
  - tolerate `C->S 0x0016`
- Selection/update packets:
  - tolerate `C->S 0x000C`
  - record payloads and timing
  - do not raw-echo
- Late readiness packets:
  - tolerate `C->S 0x0017`
  - treat as post-load/status, not as a reason to jump directly into authoritative self spawn

### Phase C: later state-1 or Hansol transition

- Only after bootstrap is truly complete should the server consider:
  - authoritative `S->C 0x0064`
  - `0x0065/0x0066/0x0068/0x0069` world actor packets
  - `0x006E` style ready-state packets

## 4. Corrections to current emulator heuristics

The current `azrok_server.py` handlers are still heuristic at these points:

- [azrok_server.py](<home>/Documents/<project-dir>/Azrok_Plaza/azrok_server.py#L2546)
- [azrok_server.py](<home>/Documents/<project-dir>/Azrok_Plaza/azrok_server.py#L2624)

Most important correction:

- `0x0017` should be understood as a proven late `<BBI>` client send, but not yet as a proven mandatory trigger for `S->C 0x006E` or `S->C 0x0064`.
- `0x0064` client-send handling is directionally right in one sense, because it does not echo, but the binary proof is now stronger: the wire payload is only 1 byte.
