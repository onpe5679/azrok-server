# Launcher and Connection Architecture

**STATUS: RESEARCH (2026-04-01)**

This document covers the Azrok game launcher (open.exe) architecture and the full connection chain from launcher web login through to the game client's TCP socket, plus the root cause of the IAT hook failure mode and the clean fix via engine variable injection.

---

## Launcher Architecture (open.exe)

### Executables

| File | Size | Role |
|------|------|------|
| open.exe | 741 KB | Real launcher |
| starmaru.exe | 524 KB | Updater only |

### autoLauncher.dll

- COM ActiveX component
- CLSID: `{63875209-13A5-4586-8756-74FB690099CA}`
- Registered via `regsvr32` by `starmaru.exe` on first run

**Two commands exposed to JavaScript:**

| Command | Behavior |
|---------|----------|
| `"run"` | Reads exe path and working directory from registry, calls `ShellExecuteA` with args passed directly from JavaScript |
| `"send"` | Creates 512B shared memory named `"mooondal"`, copies 256B into it, then `FindWindowA` + `SendMessageA(0xBBB, 0x13F)` |

**Registry key for `"run"`:**
`HKLM\SOFTWARE\<key>\autoLauncher` — REG_BINARY format: `workdir\0exepath\0`

The `"run"` command passes its JavaScript argument string directly as the
`lpParameters` to `ShellExecuteA`. This is how `Azrok.exe` receives its
`"IP:PORT user auth"` command-line arguments from the web login flow.

**Role clarification:**
- `open.exe` is a **separate mooondal-engine game client**, not a thin launcher wrapper. It runs its own game loop and renders the home/lobby UI.
- `starmaru.exe` is the **patcher**: handles `regsvr32`, reads `version.dat`, downloads patches. Runs first in the chain.
- The actual launch of `Azrok.exe` is triggered by JavaScript inside `open.exe`'s embedded IE WebBrowser control calling `autoLauncher.dll`'s `"run"` command.

### Web Integration

The launcher embeds an IE WebBrowser control and navigates to web endpoints for login and home:

- **Login URL**: `https://member.funitto.com/member/login/app/app_login_do.jsp`
- **Home URL**: `http://starmaru.funitto.com/star/maru.azrok.screen`

### Server Endpoints

| Role | Host | Path |
|------|------|------|
| Notify server | file.funitto.com | starmaru/azrok/app |
| Chatting server | starmaru.funitto.com | hompy/common/app |

### Login Parameters

After successful web login, the launcher receives and passes these parameters to the game:

| Parameter | Description |
|-----------|-------------|
| `p_target_id` | homeID |
| `p_mbr_id` | loginID |
| `p_mbr_auth_key` | loginKey |

### Config Keys

After web login, the launcher dynamically sets:

- `gameServer` — IP address of the game server
- `gameServerPort` — Port of the game server

These are the values the WDL engine variables ultimately hold when the game is launched through the normal launcher flow.

### Window Layout

The launcher window is 948x693 pixels. Within it:

| Panel | Size | Offset |
|-------|------|--------|
| Game window | 601x500 | (98, 106) |
| Chatting window | 150x50 | (20, 430) |

### UI Framework

The launcher uses the `mooondal` JavaScript/web namespace with these components:

- `c_dividedPanel`
- `c_scrollBar`
- `c_chattingBalloon`
- `c_popupMenu`
- `c_tileTerrainManager`

---

## Connection Chain (Azrok.exe)

The connection sequence spans several functions. The entry point reads WDL engine variables, parses them, then drives the socket connection.

### Step 1: FUN_004edb10 — Read WDL Engine Variables

Reads three string variables from the WDL engine struct:

| Offset | Content |
|--------|---------|
| `engine+0x9a0 (+0x0c)` | `"IP:PORT"` combined string |
| `engine+0x998 (+0x0c)` | username string |
| `engine+0x9ac (+0x0c)` | authkey string |

The `+0x0c` dereference is the string data pointer inside the WDL string struct.

### Step 2: FUN_00508b30 — Parse and Store

Parses the combined string and stores fields into the global game struct (`gm`):

```
strtok(param2, ":")  →  IP   stored at gm+0x31822
atol(port_str)       →  PORT stored at gm+0x31842
username             →  gm+0x3179e
authkey              →  gm+0x317be
```

### Step 3: Connection Call Chain

```
FUN_00594130
  └─ FUN_005941c0
       └─ FUN_00592920  (ConnectToServer)
            └─ CConnection::Connect  (FUN_0061E340)
```

### Step 4: CConnection::Connect (FUN_0061E340)

Full socket establishment sequence:

1. `gethostbyname` / `inet_addr` on the stored IP
2. `socket()` — create TCP socket
3. `connect()` — initiate connection
4. `WSAEventSelect(FD_CONNECT)` + `WSAWaitForMultipleEvents` — async wait
5. On success: set `vtable[1] = CClientPeer::OnConnect` (FUN_00591CD0)

### Step 5: CClientPeer::OnConnect (FUN_00591CD0)

- Sets dispatch flag: `this+0x4076 = 1`
- Starts the send thread

The dispatch flag at `this+0x4076` is the gate that allows the client to send packets. If it stays 0, no outbound traffic is possible.

---

## Why the IAT Hook Breaks Things

The IAT hook approach replaces `connect()` to redirect the destination from `<lan-ip>:0` to `127.0.0.1:9200`.

### Root Cause

Without the launcher, the WDL engine variables are never populated. `FUN_004edb10` reads empty strings, so `FUN_00508b30` produces:

- IP = `<lan-ip>` (VMware NIC default)
- PORT = `0` (uninitialized / `atol("")` = 0)

The hook makes `connect()` succeed synchronously on the redirected address.

### The Domino Effect

```
IAT hook makes connect() return success synchronously
  → WSAEventSelect FD_CONNECT event never fires
  → WSAWaitForMultipleEvents never signals connection
  → CClientPeer::OnConnect (FUN_00591CD0) never called
  → dispatch flag (this+0x4076) stays 0
  → client cannot send packets
  → NOP patch needed on dispatch check
  → 0x0002 restore needed
  → gate NOP needed
```

Each patch is a symptom of the one above it. The chain originates entirely from the empty WDL engine variables.

---

## Solution: Engine Variable Injection

Instead of hooking the socket layer, inject the correct values directly into the WDL engine variables before `FUN_004edb10` runs. The game's own code then handles the rest without modification.

### Injection Targets

| Variable | Address | Value to Write |
|----------|---------|----------------|
| IP:PORT string | `engine+0x9a0 (+0x0c)` | `"127.0.0.1:9200"` |
| username string | `engine+0x998 (+0x0c)` | any dummy value (e.g. `"player"`) |
| authkey string | `engine+0x9ac (+0x0c)` | any dummy value (e.g. `"authkey"`) |

### Result

```
WDL variables populated with 127.0.0.1:9200
  → FUN_004edb10 reads correct IP:PORT
  → FUN_00508b30 stores 127.0.0.1 + 9200 into gm struct
  → connect() called with correct target
  → WSAEventSelect FD_CONNECT fires normally
  → CClientPeer::OnConnect called
  → dispatch flag (this+0x4076) = 1
  → client sends packets normally
```

### Patches Eliminated

By using engine variable injection, the following patches become unnecessary:

- IAT hook on `connect()`
- NOP patch on dispatch flag check
- 0x0002 restore patch
- Gate NOP patch

The game's own WDL connection code path executes unmodified from end to end.
