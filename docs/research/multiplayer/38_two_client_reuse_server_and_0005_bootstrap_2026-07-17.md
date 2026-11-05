# Two-client reuse-server run and C→S 0x0005 bootstrap — 2026-07-17

## Result

The second client can now reuse the primary TCP listener instead of starting
an isolated server. `azrok_launcher.py --reuse-server --port 9207` leaves the
existing listener untouched; the elevated on-demand launcher passes this mode
through `tools/run_azrok_instance_elevated.ps1` and
`tools/stop_azrok_elevated.ps1`.

After a clean restart, the first client reached PatHouse through the existing
heartbeat auto-bootstrap. The second client initially remained at the
character-selection screen and emitted the observed one-byte C→S `0x0005`
selector. The server previously ignored this direction-specific packet, so
the client never received a room path. A narrow handler now treats only the
empty/zero selector as the default slot and returns the known-good
`S→C 0x0003 + 0x0007 + 0x0005 + 0x000A + 0x000B` bootstrap bundle. The second
client then emitted C→S `0x0007` and reached the same PatHouse scene.

Evidence from `captures/packets_20260717_093328.txt`:

- first client bootstrap: S→C `0x0003` at line 111;
- second-client selector: C→S `0x0005`, payload `00`, at line 426;
- server response: S→C `0x0003` at line 430, followed by the bundle;
- server control state: two established clients on port 9207, both windows
  responsive.

The second client was then driven through the approved elevated UI action
request. A dialogue advance/floor click changed the camera and local room
contents without any server room packet, matching the static conclusion that
these auxiliary rooms are client-local. The visible Korean hint and furniture
scene are retained as a clean playback artifact at
`artifacts/screens/reuse2_dialog_after.bmp`.

## Important boundaries

- This proves the second client can enter the local scene; it is not yet
  proof of same-room multiplayer because both server metadata entries remain
  `room_kind=null` until a client emits its movement/membership opcodes.
- No speculative ACK was added for C→S `0x0065`. The older human capture has a
  single `0x0065` after a long movement run; the current clean run has not
  produced a second dumbbell-boundary sample.
- The elevated UI path is narrow and marker-based: only click/key/capture/info
  actions are accepted, and capture paths are confined under `artifacts`.

The control-panel metadata path now labels a client that has accepted the
zero selector or sent the 196-byte zone request as `PatHouse (local)` while
keeping `room_kind=null`. This distinguishes a local level load from a
verified server room-membership report. The observed wire kinds `0x15` and
`0x1B` are shown as Gym/Plaza only when they arrive in C→S `0x0065`.

## Next clean-run probe

Use the same-server two-client setup, identify the local room with the sparse
room-init observer, then click the next room door and capture both the image
and any first C→S `0x0065/0x0066/0x0067/0x006C` payload. Only after a real
payload/return pair is observed should the corresponding relay or response be
promoted from logging to protocol behavior.
