# Gate 1: D3D9 API surface full-session probe (2026-07-19)

## Scope

This is the measurement-first gate for the Azrok browser-port feasibility
study. The shipped 32-bit `tools/d3d9_probe/d3d9.dll` was placed beside the
unmodified `Azrok.exe`; no game binary or packet-path patch was used.

## Result

**VERIFIED (live, one PID, normal detach):**

- Session: 2026-07-19 01:12:53 through 01:20:26 KST.
- Probe SHA-256:
  `804F4E7C7E3C7E104BC5F16F27018D483E45F249D8EAFF0110B40661C167C379`.
- Both tracked vtables report `hooked=1`.
- Observed unique methods: **56** of the probe's 136 tracked slots.
  - `IDirect3D9`: 15 of 17.
  - `IDirect3DDevice9`: 41 of 119.
- Aggregate calls: **1,891,345**.
- The required exported entrypoint `Direct3DCreate9` is not counted by the
  log. Therefore the directly measured implementation lower bound is
  **57 entrypoints**: the 56 observed COM methods plus `Direct3DCreate9`.
- Check: 56 called rows + 80 uncalled rows = 136 tracked slots.

Evidence:

- `artifacts/d3d9_probe/20260719_gate1/d3d9_probe_full_session.log`
- `artifacts/d3d9_probe/20260719_gate1/D3D9.probe.deployed.dll`
- `captures/packets_20260719_011252.txt`
- structured run `20260719T011252_121560_52b962c7`

## Prescribed gameplay coverage

**VERIFIED (dynamic):** the same client process covered the requested route.

1. Existing-character login and PatHouse bootstrap completed through the
   standard launcher/server path.
2. Plaza rendered and remained healthy.
3. The real brown OX door was clicked. The session emitted natural
   `006B -> 006E -> 00C8`, displayed `1 + 1 = 2`, completed the scheduler
   round through `00CE/00CA/00CB`, emitted natural `00C9`, and returned through
   `000D` to Plaza healthy.
4. The client naturally entered cooking academy (`room=7`), interacted with
   the oven, and displayed the cooking result panel with a positive
   `요리경험` change.
5. The user exited the game normally. `DLL_PROCESS_DETACH` wrote the log at
   01:20:26 KST; no forced process termination was used for the measurement.

The system D3D9 path produced a real device, full scene output, and 2,095
`Present` calls during the measured session.

## Important measurement boundary

**VERIFIED (probe source):** the current probe only patches
`IDirect3D9` and `IDirect3DDevice9`. It does not patch returned resource
interfaces such as textures, surfaces, vertex/index buffers, swap chains,
state blocks, shaders, or queries. Resource-object `Lock/Unlock/Release` and
similar calls are therefore outside this measurement.

Consequently:

- **56** is the exact answer produced by the prescribed probe for its two
  tracked interfaces.
- **57** is the exact directly measured lower bound when the required export
  is included.
- A complete drop-in D3D9 implementation count is **NOT VERIFIED** until a
  second probe covers returned COM object vtables.
- The log label `미호출(구현 불필요)` is too strong. Those 80 slots are only
  unobserved in this route; device-loss, display-mode, and other paths may use
  more.

## Renderer-path note

**VERIFIED:** before the run, the root `D3D9.dll` was dgVoodoo2 2.86.5 x86,
SHA-256
`B7401378B2B8E8C18C88A033E77C3EE99F4C7D2AC8CFCC949D79C1DD7FA99767`.
The probe loads `%SystemRoot%\\System32\\d3d9.dll` directly and does not chain
to dgVoodoo. Thus this run measured Azrok on native Windows system D3D9, not
the usual dgVoodoo path. Native system D3D9 nevertheless created a device and
rendered the full route successfully.

After evidence capture, the root dgVoodoo DLL was restored and its SHA-256
matched the pre-run value. `Azrok.exe` and listeners 9207/9300 were absent.

## Incidental server finding

**VERIFIED (dynamic, repeated twice):** leaving library (`room=10`) and
leaving cooking academy (`room=7`) each left the client at
`scene=110 / phase=2 / dispatch_mode=0` while heartbeats continued. The
server did not automatically send the verified Plaza-return command
`S2C 0x000D[00]`. Sending that exact command manually restored
`scene=110 / phase=4 / dispatch_mode=1 / self=1 / room=27` both times.

This is a preservation-server generic facility-exit response gap, not a D3D
probe failure. Automatic handling remains **NOT IMPLEMENTED** in this record.

## Gate disposition

Gate 1 is complete for the supplied probe: **56 observed methods; 57 directly
measured minimum entrypoints including the export**. Gate 2 may proceed, but
Gate 3 must treat the full resource-interface surface as NOT VERIFIED rather
than equating 56 with a complete replacement-DLL surface.
