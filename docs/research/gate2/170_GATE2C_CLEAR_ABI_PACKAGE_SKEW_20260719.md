# Gate 2c: Clear ABI package skew

Status: VERIFIED

## Direct observation

The clean browser run reached the real D3D9Web fixed-function renderer but
repeatedly reported:

```text
D3D9WEB_PHASE6_ERROR Error: bad Clear size 8
```

The host implementation requires the packed `CommandClear` command:

```text
u32 command, count, flags, color, float z, u32 stencil
```

which is 24 bytes before any `D3DRECT` payload. The current guest source
constructs exactly that structure and sends `sizeof(CommandClear)`.

## Cause

The application ZIP used by the local browser page contained an older guest
`d3d9.dll`, not the current `tools/d3d9_web_backend/d3d9_web.dll`:

```text
ZIP before replacement: 4acb9fa82975745c298e3218ab8a34e2c03e468b7093bc208a0e0ff34fde7d4c
current guest DLL:      b7bd5b4d8c95f1eefdedf76724e61b8f6ec5ce6e6c64075c564b79738baab814
```

The 8-byte command observed by the host is therefore a package/version skew,
not an EIP-sampling effect, browser-control failure, or server failure.

## Repair and live verification

The original client was not modified. The local browser ZIP's replacement
`d3d9.dll` was updated from the current project build, then re-opened and
hash-verified against the build artifact. A separately named ZIP
(`Azrok_D3D9Web_pathouse_clearabi.zip`) forced a fresh browser mount.

The new live run has no `bad Clear size` error and directly rendered the
original Hansol Education logo plus the animated key cursor. It continued from
the 8x8 initialization texture to real 1024x1024 and 128x128 game textures:

```text
D3D9WEB_PHASE6_FFP_INIT webgl2=1 shader=driver-linked blocks=5 canvas=overlay
D3D9WEB_PHASE7_CREATE kind=texture handle=2 format=23 size=1024x1024
D3D9WEB_PHASE7_CREATE kind=texture handle=3 format=21 size=128x128
```

## Consequence

The Gate 2c renderer baseline is restored. The next blocker remains the
already-isolated Wine `WSAEventSelect` readiness-to-Windows-event handoff
(document 169); do not interpret this package repair as a server or gameplay
completion claim.
