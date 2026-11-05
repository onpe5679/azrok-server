# -*- coding: utf-8 -*-
"""
Azrok Plaza - Launcher Emulator

Starts the pristine client and supplies the three launcher values through the
Acknex WDL variables.  A native-command-line mode remains available for
analysis, but is not the default because Acknex 6.40 interprets the final token
as a .WDL filename and aborts with E355.

Usage: python azrok_launcher.py [--species N] [--evolution N] [--port N]
"""
import ctypes
import ctypes.wintypes as wt
import struct
import os
import sys
import time
import argparse
import threading
import webbrowser

from azrok_network import parse_private_ipv4_bind

# ========================================================
#  Configuration
# ========================================================
SERVER_HOST = '127.0.0.1'
DEFAULT_PORT = 9200
USERNAME = 'player'
AUTHKEY = 'localauth'

# Legacy Nexus patch addresses. Normal launches do not touch these addresses;
# --nexus-patches exists only for regression comparison. The two parser sites
# below are the engine's legal ``-NX200`` / ``-NX 200`` assignment branches;
# they are not WDL override sites and must never be NOPed.
ACKNEX_NEXUS_INT_VA = 0x102FC540
ACKNEX_NEXUS_DEFAULT_VA = 0x10017EF6  # MOV [0x102FC540], 0x28 — immediate byte
ACKNEX_NX_COMPACT_ASSIGN_VA = 0x10018414
ACKNEX_NX_SEPARATE_ASSIGN_VA = 0x1001843D

# ========================================================
#  Windows API
# ========================================================
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40
CREATE_SUSPENDED = 0x00000004
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010

# Acknex engine globals populated after engine_open(None, 0).
ENGINE_PTR_ADDR = 0x006E8430
ENGINE_OFFSET_USER = 0x998
ENGINE_OFFSET_SERVER = 0x9A0
ENGINE_OFFSET_AUTH = 0x9AC

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
        ("lpReserved2", ctypes.c_void_p), ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD),
    ]


WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
user32.EnumWindows.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.GetWindow.argtypes = [wt.HWND, wt.UINT]
user32.GetWindow.restype = wt.HWND
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetWindowRect.restype = wt.BOOL
user32.SetWindowPos.argtypes = [
    wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wt.UINT,
]
user32.SetWindowPos.restype = wt.BOOL


def find_process_window(process_id):
    """Return the visible, unowned top-level window for one process."""
    found = []

    @WNDENUMPROC
    def visit(hwnd, _lparam):
        owner_pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
        if (owner_pid.value == process_id and user32.IsWindowVisible(hwnd)
                and not user32.GetWindow(hwnd, 4)):  # GW_OWNER
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else None


def keep_game_window_at_origin(process_id, stop_event):
    """Keep the game frame at screen (0, 0) to avoid its mouse offset bug."""
    announced_hwnd = None
    while not stop_event.wait(0.25):
        hwnd = find_process_window(process_id)
        if not hwnd:
            continue
        rect = wt.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            continue
        if rect.left != 0 or rect.top != 0:
            ok = user32.SetWindowPos(
                hwnd, None, 0, 0, 0, 0,
                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
            )
            if ok and announced_hwnd != hwnd:
                print(f"    [WINDOW] Moved game HWND=0x{hwnd:08X} to screen origin (0, 0)")
                announced_hwnd = hwnd


def read_mem(hProc, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(hProc, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    return buf.raw[:n.value] if ok else None


def write_mem(hProc, addr, data):
    if isinstance(data, bytearray):
        data = bytes(data)
    n = ctypes.c_size_t(0)
    return kernel32.WriteProcessMemory(hProc, ctypes.c_void_p(addr), data, len(data), ctypes.byref(n))


def read_dword(hProc, addr):
    d = read_mem(hProc, addr, 4)
    return struct.unpack('<I', d)[0] if d and len(d) == 4 else 0


def write_dword(hProc, addr, val):
    old_prot = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(addr), 4,
                               PAGE_READWRITE, ctypes.byref(old_prot))
    write_mem(hProc, addr, struct.pack('<I', val))
    kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(addr), 4,
                               old_prot.value, ctypes.byref(old_prot))


def inject_wdl_string(hProc, engine_ptr, engine_offset, value_str):
    """Point one WDL STRING at a private CString-compatible allocation."""
    string_obj = read_dword(hProc, engine_ptr + engine_offset)
    if not string_obj:
        return False

    value_bytes = value_str.encode('ascii') + b'\x00'
    total_size = 16 + len(value_bytes) + 4
    new_buf = kernel32.VirtualAllocEx(
        hProc, None, total_size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
    )
    if not new_buf:
        print("    [WARN] VirtualAllocEx failed")
        return False

    # CStringData: manager, data length, allocation length, refcount.
    header = struct.pack('<IIII', 0, len(value_str), len(value_str) + 1, 1)
    if not write_mem(hProc, new_buf, header + value_bytes):
        return False

    new_data_ptr = new_buf + 16
    old_prot = wt.DWORD(0)
    pointer_addr = string_obj + 12
    if not kernel32.VirtualProtectEx(
        hProc, ctypes.c_void_p(pointer_addr), 4,
        PAGE_READWRITE, ctypes.byref(old_prot)
    ):
        return False
    ok = bool(write_mem(hProc, pointer_addr, struct.pack('<I', new_data_ptr)))
    kernel32.VirtualProtectEx(
        hProc, ctypes.c_void_p(pointer_addr), 4,
        old_prot.value, ctypes.byref(old_prot)
    )
    return ok


def apply_nexus_patches(hProc):
    """Legacy diagnostic writes retained only for historical A/B comparison.

    Supported launches use Acknex's native ``-NX`` command-line option instead.
    """
    old_prot = wt.DWORD(0)

    # Patch engine default: MOV [0x102FC540], 0x28 → change 0x28 to 0xC8
    # This must happen BEFORE engine_open, which calls level_load("pet.wmb")
    orig_nx = read_mem(hProc, ACKNEX_NEXUS_DEFAULT_VA, 1)
    if orig_nx == b'\x28':
        kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(ACKNEX_NEXUS_DEFAULT_VA), 1,
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        write_mem(hProc, ACKNEX_NEXUS_DEFAULT_VA, b'\xc8')
        kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(ACKNEX_NEXUS_DEFAULT_VA), 1,
                                   old_prot.value, ctypes.byref(old_prot))
        print(f"    [PATCH] Nexus default: 40 -> 200 (before engine_open)")
    elif orig_nx == b'\xc8':
        print(f"    [PATCH] Nexus default already 200")
    elif orig_nx is not None:
        print(f"    [WARN] Unexpected nexus default byte: {orig_nx.hex()}")

    # Force nexus value
    cur = read_dword(hProc, ACKNEX_NEXUS_INT_VA)
    ok = kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(ACKNEX_NEXUS_INT_VA), 4,
                               PAGE_READWRITE, ctypes.byref(old_prot))
    if ok:
        write_mem(hProc, ACKNEX_NEXUS_INT_VA, struct.pack('<I', 200))
        kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(ACKNEX_NEXUS_INT_VA), 4,
                                   old_prot.value, ctypes.byref(old_prot))
    new_val = read_dword(hProc, ACKNEX_NEXUS_INT_VA)
    print(f"    [PATCH] Nexus: {cur} -> {new_val}")

    # Calendar/Environment NULL guards REMOVED - fix is protocol-correct:
    # Send S->C 0x0064 during PatHouse entry first (initializes Calendar panels).
    # pan_create panels survive level_load, so they persist into Plaza transition.


def main():
    parser = argparse.ArgumentParser(description='Azrok Plaza Launcher Emulator')
    parser.add_argument('--species', type=int, default=2, help='0=Ark,1=Abo,2=Paz,3=Tero')
    parser.add_argument('--evolution', type=int, default=0,
                        help='Bootstrap evolution stage 0-3 (default: 0; natural care promotes after load)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Server port')
    parser.add_argument(
        '--bind', default=SERVER_HOST,
        help=('Explicit game-server bind/advertise IPv4 (default: 127.0.0.1; '
              'only loopback, RFC1918, or Tailscale 100.64.0.0/10 allowed)'),
    )
    parser.add_argument('--argv0', choices=('basename', 'fullpath'), default='basename',
                        help='argv[0] style used only with --native-cli')
    parser.add_argument('--native-cli', action='store_true',
                        help='analysis mode: pass IP/user/auth on the command line')
    parser.add_argument('--nexus-patches', action='store_true',
                        help='diagnostic only: restore the legacy Nexus=200 writes')
    parser.add_argument('--no-nexus-patches', action='store_true',
                        help=argparse.SUPPRESS)
    parser.add_argument('--nexus', type=int, default=200,
                        help='Acknex native Nexus arena in MiB via -NX (restoration default: 200)')
    parser.add_argument('--control-port', type=int, default=9300,
                        help='Control panel HTTP port (0 to disable)')
    parser.add_argument('--open-control', action='store_true',
                        help='Open the server control panel in the default browser')
    parser.add_argument('--reuse-server', action='store_true',
                        help='Do not start a local server; connect to the existing --port listener')
    parser.add_argument('--username', default=USERNAME,
                        help='Local preservation-server account id (ASCII alnum/underscore, 1..16)')
    args = parser.parse_args()
    if not 1 <= args.nexus <= 2048:
        parser.error('--nexus must be between 1 and 2048 MiB')
    if args.nexus_patches and args.nexus != 40:
        parser.error('--nexus-patches is a legacy A/B path; combine it with explicit --nexus 40')
    if not (1 <= len(args.username) <= 16) or not all(ch.isascii() and (ch.isalnum() or ch == '_') for ch in args.username):
        parser.error('--username must be 1..16 ASCII alphanumeric/underscore characters')
    try:
        bind_host = parse_private_ipv4_bind(args.bind)
    except ValueError as exc:
        parser.error(str(exc))

    port = args.port
    username = args.username
    server_addr = f"{bind_host}:{port}"

    exe_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(exe_dir, 'Azrok.exe')

    print("=" * 60)
    mode_name = 'Native CLI Probe' if args.native_cli else 'WDL Variable Injection'
    print(f"  Azrok Plaza - Launcher Emulator ({mode_name})")
    print(f"  Server: {server_addr}")
    print(f"  Species: {args.species}, Evolution: {min(args.evolution, 3)}")
    print("=" * 60)

    # [1] Start TCP server
    server = None
    if args.reuse_server:
        print("\n[1] Reusing existing TCP server...")
        print(f"    Target listener: {server_addr}")
    else:
        print("\n[1] Starting local TCP server...")
        os.environ['AZROK_SPECIES'] = str(args.species)
        os.environ['AZROK_EVOLUTION'] = str(min(args.evolution, 3))
        sys.path.insert(0, exe_dir)
        import azrok_server
        azrok_server.SERVER_PORT = port
        server = azrok_server.AzrokServer(port, log_dir=exe_dir, bind_host=bind_host)
        server.start()
        time.sleep(0.5)
        print(f"    Listening on {server_addr}")
        print(f"    Capture: {server.capture_path}")

    # [1b] Control panel — observe/drive the server without editing code and restarting.
    control = None
    if args.control_port and server is not None:
        import azrok_control
        control = azrok_control.ControlServer(server, port=args.control_port)
        control.start()
        if args.open_control:
            control_url = f'http://127.0.0.1:{args.control_port}/'
            if webbrowser.open(control_url, new=2):
                print(f"    Control panel opened: {control_url}")
            else:
                print(f"    [WARN] Browser did not accept control panel URL: {control_url}")

    # [2] With no command line Acknex starts its embedded game script. Passing the
    # three values directly makes Acknex treat the auth token as LOCALAUTH.WDL.
    print("\n[2] Launching Azrok.exe (suspended)...")
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()
    command_line = None
    if args.native_cli:
        argv0 = exe_path if args.argv0 == 'fullpath' else 'Azrok.exe'
        nexus_arg = f' -NX{args.nexus}' if args.nexus != 40 else ''
        command_line_text = f'"{argv0}"{nexus_arg} {server_addr} {username} {AUTHKEY}'
        command_line = ctypes.create_unicode_buffer(command_line_text)
        print(f"    CommandLine={command_line_text}")
    elif args.nexus != 40:
        # Acknex parses -NX itself before loading the embedded WDL. Do not put
        # the connection triplet here: bare IP/user/auth tokens are interpreted
        # as a WDL filename and reproduce E355/LOCALAUTH.WDL. Connection values
        # remain on the proven runtime-variable injection path below.
        command_line_text = f'"Azrok.exe" -NX{args.nexus}'
        command_line = ctypes.create_unicode_buffer(command_line_text)
        print(f"    CommandLine={command_line_text} (native Acknex Nexus option)")
    else:
        print("    CommandLine=<none> (embedded WDL startup)")
    ok = kernel32.CreateProcessW(
        exe_path, command_line, None, None, False,
        CREATE_SUSPENDED, None, exe_dir, ctypes.byref(si), ctypes.byref(pi)
    )
    if not ok:
        print(f"    [ERROR] CreateProcess failed: {ctypes.GetLastError()}")
        if server is not None:
            server.stop()
        return
    hProcess = pi.hProcess
    hThread = pi.hThread
    print(f"    PID={pi.dwProcessId}")

    # Acknex's input coordinates become offset when the window starts away from
    # the primary screen origin. Keep it pinned for the lifetime of the client.
    window_stop = threading.Event()
    window_thread = threading.Thread(
        target=keep_game_window_at_origin,
        args=(pi.dwProcessId, window_stop),
        name='azrok-window-origin',
        daemon=True,
    )
    window_thread.start()

    # [3] Resume and optionally wait for ACKNEX.DLL to load.
    print("\n[3] Resuming process...")
    kernel32.ResumeThread(hThread)
    if server is not None:
        server.attach_process(hProcess)

    use_nexus_patches = args.nexus_patches and not args.no_nexus_patches
    if use_nexus_patches:
        print("    Waiting for ACKNEX.DLL load...")
        # Poll until ACKNEX.DLL is loaded (the native -NX parser is readable).
        for i in range(200):  # Up to 10 seconds at 50ms intervals
            time.sleep(0.05)
            test = read_mem(hProcess, ACKNEX_NX_COMPACT_ASSIGN_VA, 6)
            if test is not None and len(test) == 6:
                print(f"    ACKNEX.DLL loaded ({(i+1)*0.05:.2f}s)")
                apply_nexus_patches(hProcess)
                break
        else:
            print("    [WARN] ACKNEX.DLL load not detected, trying nexus patch anyway")
            apply_nexus_patches(hProcess)
    else:
        print("    Nexus patching disabled: no ACKNEX runtime writes")

    if not args.native_cli:
        print("\n[4] Waiting for engine variables...")
        engine_ptr = 0
        for i in range(60):
            time.sleep(0.5)
            engine_ptr = read_dword(hProcess, ENGINE_PTR_ADDR)
            if engine_ptr and read_dword(hProcess, engine_ptr + ENGINE_OFFSET_SERVER):
                print(f"    Engine initialized at 0x{engine_ptr:08X} ({(i + 1) * 0.5:.1f}s)")
                break
        else:
            print("    [ERROR] Engine variables did not initialize in 30 seconds")
            kernel32.TerminateProcess(hProcess, 1)
            if server is not None:
                server.stop()
            return

        print("\n[5] Injecting launcher values...")
        injected = (
            (ENGINE_OFFSET_SERVER, server_addr),
            (ENGINE_OFFSET_USER, username),
            (ENGINE_OFFSET_AUTH, AUTHKEY),
        )
        injection_ok = True
        for offset, value in injected:
            ok = inject_wdl_string(hProcess, engine_ptr, offset, value)
            injection_ok = injection_ok and ok
            print(f"    engine+0x{offset:03x} = '{value}' {'OK' if ok else 'FAIL'}")
        if not injection_ok:
            print("    [ERROR] One or more WDL variables could not be injected")
            kernel32.TerminateProcess(hProcess, 1)
            if server is not None:
                server.stop()
            return

    print("\n" + "=" * 60)
    if args.native_cli:
        print(f"  Native command line passed: {server_addr} {username} {AUTHKEY}")
    else:
        print(f"  Launcher values supplied: {server_addr} {username} {AUTHKEY}")
    print(f"  Game will connect via its native client code")
    print(f"  No IAT hook, no dispatch NOP, no gate NOP!")
    print(f"  Binary patches: {'Nexus=200 (diagnostic)' if use_nexus_patches else 'none'}")
    print(f"  Acknex Nexus: {args.nexus} MiB ({'-NX'+str(args.nexus) if args.nexus != 40 else 'engine default'})")
    if control:
        print(f"  Control panel: http://127.0.0.1:{args.control_port}   (or: python azrok_ctl.py state)")
    print("  Waiting for game...")
    print("=" * 60)

    # [4] Wait for game to exit
    try:
        while True:
            exit_code = wt.DWORD(0)
            kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code))
            if exit_code.value != 0x103:  # STILL_ACTIVE
                print(f"\n[!] Game exited (code: {exit_code.value})")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[!] Stopped by user")
    finally:
        window_stop.set()
        window_thread.join(timeout=1.0)
        kernel32.CloseHandle(hThread)
        kernel32.CloseHandle(hProcess)
        # A primary launcher may host a reused-server secondary client.  Do
        # not tear down the shared TCP/control host merely because this game
        # process exited; otherwise the secondary loses its socket mid-test
        # and the control panel disappears.  Keep the host alive until every
        # connected client has gone away, then close it normally.
        if server is not None:
            # A reused secondary can still be at the character-selection
            # screen and may not have completed its first packet yet.  Its
            # socket can therefore disappear briefly before it has a chance
            # to bootstrap.  Keep the primary-owned host alive for a bounded
            # grace window after the primary exits; this avoids tearing down
            # 9207/9300 in the middle of a real two-client test while still
            # guaranteeing eventual cleanup when no peer remains.
            grace_deadline = time.monotonic() + 180.0
            print("  [SERVER] Keeping host alive for reuse-client grace window (180s)...")
            while server.running and time.monotonic() < grace_deadline:
                if not server.connections:
                    # Give a just-started secondary a short chance to connect
                    # before closing an otherwise idle primary-owned host.
                    time.sleep(2.0)
                    if not server.connections:
                        break
                time.sleep(0.5)
        if control:
            control.stop()
        if server is not None:
            server.stop()


if __name__ == '__main__':
    main()
