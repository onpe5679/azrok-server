# -*- coding: utf-8 -*-
"""
Azrok Plaza - IAT Hook via Entry Point Stomping
Intercepts connect() to capture server IP:Port and redirect to 127.0.0.1

Technique:
1. CreateProcess with CREATE_SUSPENDED
2. Replace entry point with infinite loop (EB FE)
3. Resume thread -> loader runs, resolves IAT, hits our loop
4. Read resolved IAT entries, patch them with hooks
5. Restore entry point, resume -> game runs with hooks active

No debugger API used - no DirectX interference.

Run: python hook_connect.py
"""
import ctypes
import ctypes.wintypes as wt
import struct
import os
import sys
import time
import socket

# ── Windows Constants ──
CREATE_SUSPENDED     = 0x00000004
PROCESS_ALL_ACCESS   = 0x001F0FFF
THREAD_ALL_ACCESS    = 0x001F03FF
MEM_COMMIT           = 0x1000
MEM_RESERVE          = 0x2000
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE       = 0x04
CONTEXT_FULL         = 0x10001F
INFINITE_WAIT        = 0xFFFFFFFF

kernel32 = ctypes.windll.kernel32

# ── Structures ──
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

def read_mem(hProc, addr, size):
    buf = ctypes.create_string_buffer(size)
    nread = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(hProc, ctypes.c_void_p(addr), buf, size, ctypes.byref(nread))
    return buf.raw[:nread.value] if ok else None

def write_mem(hProc, addr, data_bytes):
    nw = ctypes.c_size_t(0)
    return kernel32.WriteProcessMemory(hProc, ctypes.c_void_p(addr), data_bytes, len(data_bytes), ctypes.byref(nw))

def read_dword(hProc, addr):
    d = read_mem(hProc, addr, 4)
    return struct.unpack('<I', d)[0] if d and len(d) == 4 else 0

def read_string(hProc, addr, max_len=256):
    d = read_mem(hProc, addr, max_len)
    if d:
        null = d.find(b'\x00')
        if null >= 0:
            return d[:null].decode('ascii', errors='replace')
    return None

def build_connect_hook(base):
    """
    x86 shellcode for connect() hook.
    Captures original IP + port from sockaddr_in, replaces IP with 127.0.0.1.
    """
    log_port    = base + 0x100
    log_ip      = base + 0x104
    log_flag    = base + 0x108
    log_count   = base + 0x114
    real_connect = base + 0x080

    c = bytearray()
    c += b'\x55'                                                 # push ebp
    c += b'\x8B\xEC'                                             # mov ebp, esp
    c += b'\x8B\x45\x0C'                                        # mov eax, [ebp+0xC]  ; sockaddr*
    c += b'\x0F\xB7\x48\x02'                                    # movzx ecx, word [eax+2]
    c += b'\x89\x0D' + struct.pack('<I', log_port)               # mov [log_port], ecx
    c += b'\x8B\x50\x04'                                        # mov edx, [eax+4]
    c += b'\x89\x15' + struct.pack('<I', log_ip)                 # mov [log_ip], edx
    c += b'\xC7\x05' + struct.pack('<I', log_flag) + b'\x01\x00\x00\x00'  # mov [log_flag], 1
    c += b'\xFF\x05' + struct.pack('<I', log_count)              # inc [log_count]
    c += b'\xC7\x40\x04' + struct.pack('<I', 0x0100007F)        # mov [eax+4], 127.0.0.1
    c += b'\xFF\x75\x10'                                        # push [ebp+0x10]
    c += b'\xFF\x75\x0C'                                        # push [ebp+0xC]
    c += b'\xFF\x75\x08'                                        # push [ebp+0x08]
    c += b'\xFF\x15' + struct.pack('<I', real_connect)           # call [real_connect]
    c += b'\x5D'                                                 # pop ebp
    c += b'\xC2\x0C\x00'                                        # ret 12
    c += b'\xCC' * (0x40 - len(c))
    return bytes(c)

def build_inet_addr_hook(base):
    """x86 shellcode for inet_addr() hook. Logs the IP string pointer."""
    log_inet    = base + 0x10C
    real_inet   = base + 0x084

    c = bytearray()
    c += b'\x55'                                                 # push ebp
    c += b'\x8B\xEC'                                             # mov ebp, esp
    c += b'\x8B\x45\x08'                                        # mov eax, [ebp+8]
    c += b'\xA3' + struct.pack('<I', log_inet)                   # mov [log_inet], eax
    c += b'\xFF\x75\x08'                                        # push [ebp+8]
    c += b'\xFF\x15' + struct.pack('<I', real_inet)              # call [real_inet_addr]
    c += b'\x5D'                                                 # pop ebp
    c += b'\xC2\x04\x00'                                        # ret 4
    c += b'\xCC' * (0x20 - len(c))
    return bytes(c)

def build_gethostbyname_hook(base):
    """x86 shellcode for gethostbyname() hook. Logs the hostname string pointer."""
    log_host    = base + 0x110
    real_gethbn = base + 0x088

    c = bytearray()
    c += b'\x55'                                                 # push ebp
    c += b'\x8B\xEC'                                             # mov ebp, esp
    c += b'\x8B\x45\x08'                                        # mov eax, [ebp+8]
    c += b'\xA3' + struct.pack('<I', log_host)                   # mov [log_host], eax
    c += b'\xFF\x75\x08'                                        # push [ebp+8]
    c += b'\xFF\x15' + struct.pack('<I', real_gethbn)            # call [real_gethostbyname]
    c += b'\x5D'                                                 # pop ebp
    c += b'\xC2\x04\x00'                                        # ret 4
    c += b'\xCC' * (0x20 - len(c))
    return bytes(c)


def main():
    exe_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(exe_dir, "Azrok.exe")

    print("=" * 60)
    print("  Azrok Plaza - IAT Hook (Entry Point Stomping)")
    print("  Captures server IP:Port, redirects to 127.0.0.1")
    print("=" * 60)
    print()

    if not os.path.exists(exe_path):
        print(f"[ERROR] {exe_path} not found!")
        return

    # ── Fixed Addresses (no ASLR) ──
    ENTRY_POINT        = 0x004DCC4E
    IAT_CONNECT        = 0x006F0A0C
    IAT_INET_ADDR      = 0x006F0A10
    IAT_GETHOSTBYNAME  = 0x006F0A14

    # ── Step 1: Create process SUSPENDED ──
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()

    print("[1] Creating Azrok.exe (SUSPENDED)...")
    ok = kernel32.CreateProcessW(
        exe_path, None, None, None, False,
        CREATE_SUSPENDED, None, exe_dir,
        ctypes.byref(si), ctypes.byref(pi))

    if not ok:
        print(f"[ERROR] CreateProcess failed: {ctypes.GetLastError()}")
        return

    hProcess = pi.hProcess
    hThread  = pi.hThread
    pid      = pi.dwProcessId
    print(f"    PID={pid}")

    try:
        # ── Step 2: Save original entry point bytes ──
        print("[2] Saving entry point bytes...")
        original_ep = read_mem(hProcess, ENTRY_POINT, 2)
        if not original_ep:
            print("[ERROR] Cannot read entry point!")
            kernel32.TerminateProcess(hProcess, 1)
            return
        print(f"    Original EP bytes: {original_ep[0]:02X} {original_ep[1]:02X}")

        # ── Step 3: Write infinite loop at entry point (EB FE = jmp $) ──
        print("[3] Writing infinite loop at entry point...")
        old_protect = wt.DWORD(0)
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ENTRY_POINT), 2,
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect))
        write_mem(hProcess, ENTRY_POINT, b'\xEB\xFE')
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ENTRY_POINT), 2,
                                   old_protect.value, ctypes.byref(old_protect))

        # ── Step 4: Resume thread - loader will run, then hit our loop ──
        print("[4] Resuming thread (loader will execute)...")
        kernel32.ResumeThread(hThread)

        # Wait for the loader to finish (it spins on our infinite loop)
        print("    Waiting for loader to resolve IAT...")
        time.sleep(3)

        # Verify we're at the entry point (thread should be spinning)
        # Check that IAT is now resolved (values should be real addresses)
        test_connect = read_dword(hProcess, IAT_CONNECT)
        test_inet = read_dword(hProcess, IAT_INET_ADDR)
        test_gethbn = read_dword(hProcess, IAT_GETHOSTBYNAME)

        print(f"    IAT connect()       = 0x{test_connect:08X}")
        print(f"    IAT inet_addr()     = 0x{test_inet:08X}")
        print(f"    IAT gethostbyname() = 0x{test_gethbn:08X}")

        # Verify they look like real addresses (should be in DLL range, like 0x7xxx)
        if test_connect < 0x10000 or (test_connect & 0x80000000 and test_connect < 0xC0000000):
            print("[WARNING] IAT may not be resolved yet. Waiting more...")
            time.sleep(3)
            test_connect = read_dword(hProcess, IAT_CONNECT)
            test_inet = read_dword(hProcess, IAT_INET_ADDR)
            test_gethbn = read_dword(hProcess, IAT_GETHOSTBYNAME)
            print(f"    IAT connect()       = 0x{test_connect:08X}")
            print(f"    IAT inet_addr()     = 0x{test_inet:08X}")
            print(f"    IAT gethostbyname() = 0x{test_gethbn:08X}")

        if test_connect < 0x10000000:
            print("[ERROR] IAT still not resolved! Cannot proceed.")
            kernel32.TerminateProcess(hProcess, 1)
            return

        # ── Step 5: Suspend thread for patching ──
        print("[5] Suspending thread for IAT patching...")
        kernel32.SuspendThread(hThread)

        # ── Step 6: Allocate memory for hooks ──
        print("[6] Allocating hook memory...")
        hook_base = kernel32.VirtualAllocEx(
            hProcess, None, 0x1000,
            MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)

        if not hook_base:
            print(f"[ERROR] VirtualAllocEx failed: {ctypes.GetLastError()}")
            kernel32.TerminateProcess(hProcess, 1)
            return
        print(f"    Hook base: 0x{hook_base:08X}")

        # ── Step 7: Build and write hook code ──
        print("[7] Writing hook code...")

        connect_hook = build_connect_hook(hook_base)
        inet_hook = build_inet_addr_hook(hook_base)
        gethbn_hook = build_gethostbyname_hook(hook_base)

        write_mem(hProcess, hook_base + 0x000, connect_hook)
        write_mem(hProcess, hook_base + 0x040, inet_hook)
        write_mem(hProcess, hook_base + 0x060, gethbn_hook)

        # Write real function pointers
        write_mem(hProcess, hook_base + 0x080, struct.pack('<I', test_connect))
        write_mem(hProcess, hook_base + 0x084, struct.pack('<I', test_inet))
        write_mem(hProcess, hook_base + 0x088, struct.pack('<I', test_gethbn))

        # Zero log area
        write_mem(hProcess, hook_base + 0x100, b'\x00' * 32)

        # ── Step 8: Patch IAT entries ──
        print("[8] Patching IAT entries...")
        old_prot = wt.DWORD(0)
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(IAT_CONNECT), 12,
                                   PAGE_READWRITE, ctypes.byref(old_prot))

        write_mem(hProcess, IAT_CONNECT,       struct.pack('<I', hook_base + 0x000))
        write_mem(hProcess, IAT_INET_ADDR,     struct.pack('<I', hook_base + 0x040))
        write_mem(hProcess, IAT_GETHOSTBYNAME, struct.pack('<I', hook_base + 0x060))

        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(IAT_CONNECT), 12,
                                   old_prot.value, ctypes.byref(old_prot))

        # Verify
        v1 = read_dword(hProcess, IAT_CONNECT)
        v2 = read_dword(hProcess, IAT_INET_ADDR)
        v3 = read_dword(hProcess, IAT_GETHOSTBYNAME)
        print(f"    connect       -> 0x{v1:08X} (hook)")
        print(f"    inet_addr     -> 0x{v2:08X} (hook)")
        print(f"    gethostbyname -> 0x{v3:08X} (hook)")

        # ── Step 9: Restore entry point ──
        print("[9] Restoring original entry point...")
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ENTRY_POINT), 2,
                                   PAGE_EXECUTE_READWRITE, ctypes.byref(old_prot))
        write_mem(hProcess, ENTRY_POINT, original_ep)
        kernel32.VirtualProtectEx(hProcess, ctypes.c_void_p(ENTRY_POINT), 2,
                                   old_prot.value, ctypes.byref(old_prot))

        # ── Step 10: Resume - game starts with hooks ──
        print("[10] Resuming game with hooks active!")
        kernel32.ResumeThread(hThread)
        print()

        # ── Step 11: Monitor for connections ──
        print("=" * 60)
        print("  Monitoring connect() calls (60 seconds)...")
        print("  Game should start normally now.")
        print("=" * 60)

        captured_ip = None
        captured_port = None
        start_time = time.time()

        while time.time() - start_time < 60:
            exit_code = wt.DWORD(0)
            kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code))
            if exit_code.value != 259:  # STILL_ACTIVE
                print(f"\n[!] Game exited (code: {exit_code.value})")
                break

            flag = read_dword(hProcess, hook_base + 0x108)
            if flag:
                port_raw = read_dword(hProcess, hook_base + 0x100) & 0xFFFF
                ip_raw = read_dword(hProcess, hook_base + 0x104)
                count = read_dword(hProcess, hook_base + 0x114)

                port = socket.ntohs(port_raw)
                ip_b = struct.pack('<I', ip_raw)
                ip_str = f"{ip_b[0]}.{ip_b[1]}.{ip_b[2]}.{ip_b[3]}"

                if ip_str != captured_ip or port != captured_port:
                    captured_ip = ip_str
                    captured_port = port
                    print(f"\n  *** CAPTURED connect() #{count} ***")
                    print(f"    Original Server IP:   {ip_str}")
                    print(f"    Original Server Port: {port}")
                    print(f"    Redirected to: 127.0.0.1:{port}")

                    inet_ptr = read_dword(hProcess, hook_base + 0x10C)
                    gethbn_ptr = read_dword(hProcess, hook_base + 0x110)
                    if inet_ptr:
                        s = read_string(hProcess, inet_ptr)
                        if s: print(f"    inet_addr(\"{s}\")")
                    if gethbn_ptr:
                        s = read_string(hProcess, gethbn_ptr)
                        if s: print(f"    gethostbyname(\"{s}\")")

            time.sleep(0.3)

        # ── Results ──
        print()
        print("=" * 60)
        print("  RESULTS")
        print("=" * 60)

        if captured_ip and captured_port:
            print(f"  Server IP:   {captured_ip}")
            print(f"  Server Port: {captured_port}")

            inet_ptr = read_dword(hProcess, hook_base + 0x10C)
            gethbn_ptr = read_dword(hProcess, hook_base + 0x110)
            inet_str = read_string(hProcess, inet_ptr) if inet_ptr else None
            host_str = read_string(hProcess, gethbn_ptr) if gethbn_ptr else None

            if inet_str: print(f"  inet_addr argument: \"{inet_str}\"")
            if host_str: print(f"  gethostbyname argument: \"{host_str}\"")

            log_path = os.path.join(exe_dir, "server_info.txt")
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"Azrok Plaza Server Info\n")
                f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Server IP: {captured_ip}\n")
                f.write(f"Server Port: {captured_port}\n")
                if inet_str: f.write(f"inet_addr arg: {inet_str}\n")
                if host_str: f.write(f"gethostbyname arg: {host_str}\n")
            print(f"\n  Saved to: {log_path}")
        else:
            print("  No connect() calls were detected.")
            print("  The game may use a different connection method,")
            print("  or the connection happens after the monitoring period.")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        kernel32.CloseHandle(hThread)
        kernel32.CloseHandle(hProcess)

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
