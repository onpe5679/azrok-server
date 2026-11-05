# -*- coding: utf-8 -*-
"""
Azrok Plaza - Connect() Capture
Hooks the connect() call to see which IP:Port the game tries to reach.
Uses hardware breakpoint on connect IAT entry.
Run: python capture_connect.py
"""
import ctypes
import ctypes.wintypes as wt
import struct
import os
import sys
import time
import subprocess

DEBUG_ONLY_THIS_PROCESS = 0x2
EXCEPTION_DEBUG_EVENT = 1
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
OUTPUT_DEBUG_STRING_EVENT = 8
EXCEPTION_BREAKPOINT = 0x80000003
EXCEPTION_SINGLE_STEP = 0x80000004
STATUS_WX86_BREAKPOINT = 0x4000001F
EXCEPTION_ACCESS_VIOLATION = 0xC0000005
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
PROCESS_ALL_ACCESS = 0x001F0FFF
THREAD_ALL_ACCESS = 0x001F03FF
CONTEXT_FULL = 0x10007
CONTEXT_DEBUG_REGISTERS = 0x10010
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

class EXCEPTION_RECORD(ctypes.Structure):
    pass
EXCEPTION_RECORD._fields_ = [
    ("ExceptionCode", wt.DWORD),
    ("ExceptionFlags", wt.DWORD),
    ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
    ("ExceptionAddress", ctypes.c_void_p),
    ("NumberParameters", wt.DWORD),
    ("ExceptionInformation", ctypes.c_void_p * 15),
]

class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD), ("dwFirstChance", wt.DWORD)]

class EXIT_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("dwExitCode", wt.DWORD)]

class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hFile", wt.HANDLE), ("lpBaseOfDll", ctypes.c_void_p),
        ("dwDebugInfoFileOffset", wt.DWORD), ("nDebugInfoSize", wt.DWORD),
        ("lpImageName", ctypes.c_void_p), ("fUnicode", wt.WORD),
    ]

class OUTPUT_DEBUG_STRING_INFO(ctypes.Structure):
    _fields_ = [("lpDebugStringData", ctypes.c_void_p), ("fUnicode", wt.WORD), ("nDebugStringLength", wt.WORD)]

class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("Exception", EXCEPTION_DEBUG_INFO),
        ("LoadDll", LOAD_DLL_DEBUG_INFO),
        ("ExitProcess", EXIT_PROCESS_DEBUG_INFO),
        ("DebugString", OUTPUT_DEBUG_STRING_INFO),
        ("_padding", ctypes.c_byte * 160),
    ]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", wt.DWORD), ("dwProcessId", wt.DWORD),
        ("dwThreadId", wt.DWORD), ("u", DEBUG_EVENT_UNION),
    ]

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

class CONTEXT(ctypes.Structure):
    _fields_ = [
        ("ContextFlags", wt.DWORD),
        ("Dr0", wt.DWORD), ("Dr1", wt.DWORD), ("Dr2", wt.DWORD),
        ("Dr3", wt.DWORD), ("Dr6", wt.DWORD), ("Dr7", wt.DWORD),
        ("_FloatSave", ctypes.c_byte * 112),
        ("SegGs", wt.DWORD), ("SegFs", wt.DWORD),
        ("SegEs", wt.DWORD), ("SegDs", wt.DWORD),
        ("Edi", wt.DWORD), ("Esi", wt.DWORD),
        ("Ebx", wt.DWORD), ("Edx", wt.DWORD),
        ("Ecx", wt.DWORD), ("Eax", wt.DWORD),
        ("Ebp", wt.DWORD), ("Eip", wt.DWORD),
        ("SegCs", wt.DWORD), ("EFlags", wt.DWORD),
        ("Esp", wt.DWORD), ("SegSs", wt.DWORD),
        ("_ExtendedRegisters", ctypes.c_byte * 512),
    ]

kernel32 = ctypes.windll.kernel32

def read_mem(hProc, addr, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    if kernel32.ReadProcessMemory(hProc, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
        return buf.raw[:read.value]
    return None

def write_mem(hProc, addr, data_bytes):
    written = ctypes.c_size_t(0)
    old_protect = wt.DWORD(0)
    kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(addr), len(data_bytes), PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect))
    result = kernel32.WriteProcessMemory(hProc, ctypes.c_void_p(addr), data_bytes, len(data_bytes), ctypes.byref(written))
    kernel32.VirtualProtectEx(hProc, ctypes.c_void_p(addr), len(data_bytes), old_protect.value, ctypes.byref(old_protect))
    return result

def read_ptr(hProc, addr):
    data = read_mem(hProc, addr, 4)
    if data and len(data) == 4:
        return struct.unpack('<I', data)[0]
    return 0

def read_string(hProc, addr, max_len=256):
    data = read_mem(hProc, addr, max_len)
    if data:
        null = data.find(b'\x00')
        if null >= 0:
            return data[:null].decode('ascii', errors='replace')
    return None

def main():
    exe_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(exe_dir, "Azrok.exe")

    print("=" * 60)
    print("  Azrok Plaza - Connect() Capture")
    print("=" * 60)

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()

    ok = kernel32.CreateProcessW(
        exe_path, None, None, None, False,
        DEBUG_ONLY_THIS_PROCESS, None, exe_dir,
        ctypes.byref(si), ctypes.byref(pi))

    if not ok:
        print(f"[ERROR] CreateProcess failed: {ctypes.GetLastError()}")
        return

    hProcess = pi.hProcess
    print(f"[OK] PID: {pi.dwProcessId}")

    # Known IAT addresses for ws2_32 functions (from PE analysis)
    # These are in .idata section and will be filled by the loader
    IAT_CONNECT = 0x6F0A0C      # connect()
    IAT_INET_ADDR = 0x6F0A10    # inet_addr()
    IAT_GETHOSTBYNAME = 0x6F0A14  # gethostbyname()
    IAT_HTONS = 0x6F0A00        # htons()

    # We'll set INT3 (0xCC) breakpoints at the CALL sites
    # connect() is called at VA 0x501600 and 0x61E428
    # inet_addr() is called at VA 0x501570, 0x61E023, 0x61E381, 0x61E3BF

    # Breakpoints: set INT3 at the call instruction locations
    # call [connect] = FF 15 0C 0A 6F 00 (6 bytes)
    # We'll breakpoint on the PUSH before connect to read params

    # Actually, let's breakpoint on the call [inet_addr] sites to capture the IP string
    # and on call [htons] sites to capture the port

    bp_sites = {
        # inet_addr calls (push [ebp+8]; call [inet_addr])
        # VA: file  - the push before inet_addr
        0x50156E: {'name': 'inet_addr_1', 'type': 'inet_addr', 'orig': None},
        0x61E01F: {'name': 'inet_addr_2', 'type': 'inet_addr', 'orig': None},
        0x61E38B: {'name': 'inet_addr_3', 'type': 'inet_addr', 'orig': None},
        0x61E3C9: {'name': 'inet_addr_4', 'type': 'inet_addr', 'orig': None},
        # connect calls
        0x5015FE: {'name': 'connect_1', 'type': 'connect', 'orig': None},
        0x61E426: {'name': 'connect_2', 'type': 'connect', 'orig': None},
        # htons calls (for port)
        0x50157B: {'name': 'htons_1', 'type': 'htons', 'orig': None},
        0x61DFFF: {'name': 'htons_2', 'type': 'htons', 'orig': None},
    }

    first_bp = True
    captures = []
    start_time = time.time()

    try:
        while True:
            de = DEBUG_EVENT()
            if not kernel32.WaitForDebugEvent(ctypes.byref(de), 10000):
                elapsed = time.time() - start_time
                if elapsed > 30:
                    print(f"\n[TIMEOUT] No events for 10s after {elapsed:.0f}s")
                    break
                continue

            cont_status = DBG_CONTINUE

            if de.dwDebugEventCode == LOAD_DLL_DEBUG_EVENT:
                pass  # DLL loads

            elif de.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
                info = de.u.Exception
                code = info.ExceptionRecord.ExceptionCode
                addr = info.ExceptionRecord.ExceptionAddress or 0

                if code in (EXCEPTION_BREAKPOINT, STATUS_WX86_BREAKPOINT):
                    if first_bp:
                        first_bp = False
                        # Set our breakpoints now that the process is loaded
                        print("[*] Setting breakpoints on socket calls...")
                        for va, bp in bp_sites.items():
                            orig = read_mem(hProcess, va, 1)
                            if orig:
                                bp['orig'] = orig[0]
                                write_mem(hProcess, va, b'\xCC')
                                print(f"    BP at 0x{va:08X} ({bp['name']})")
                        print("[*] Breakpoints set. Resuming game...")
                        print()
                    elif addr in bp_sites:
                        bp = bp_sites[addr]
                        print(f"\n[HIT] {bp['name']} at 0x{addr:08X}")

                        # Restore original byte
                        write_mem(hProcess, addr, bytes([bp['orig']]))

                        # Get thread context
                        hThread = kernel32.OpenThread(THREAD_ALL_ACCESS, False, de.dwThreadId)
                        ctx = CONTEXT()
                        ctx.ContextFlags = CONTEXT_FULL
                        kernel32.GetThreadContext(hThread, ctypes.byref(ctx))

                        if bp['type'] == 'inet_addr':
                            # The IP string pointer should be on stack (already pushed or about to be)
                            # At inet_addr call site: push [ebp+8]; call [inet_addr]
                            # EBP points to stack frame, [ebp+8] is the IP string param
                            ip_ptr = read_ptr(hProcess, ctx.Ebp + 8)
                            if ip_ptr:
                                ip_str = read_string(hProcess, ip_ptr)
                                print(f"  IP string: {ip_str}")
                                captures.append(('inet_addr', ip_str))
                            else:
                                # Try reading from stack (ESP might have pushed value)
                                sp_val = read_ptr(hProcess, ctx.Esp)
                                ip_str = read_string(hProcess, sp_val) if sp_val else None
                                print(f"  IP string (from stack): {ip_str}")
                                captures.append(('inet_addr', ip_str))

                        elif bp['type'] == 'htons':
                            # Port value in [ebp+8] or [ebp+0xC]
                            port1 = read_ptr(hProcess, ctx.Ebp + 8) & 0xFFFF
                            port2 = read_ptr(hProcess, ctx.Ebp + 0xC) & 0xFFFF
                            print(f"  Port candidates: [ebp+8]={port1}, [ebp+0xC]={port2}")
                            # Also check what's about to be pushed (the instruction before call)
                            # Read word from EAX (often the port is in AX)
                            print(f"  EAX={ctx.Eax:08X} ECX={ctx.Ecx:08X}")
                            captures.append(('htons', port1, port2))

                        elif bp['type'] == 'connect':
                            # sockaddr_in is on stack: [esp+4] = pointer to sockaddr
                            # Or read from ebp-based frame
                            print(f"  ESP=0x{ctx.Esp:08X} EBP=0x{ctx.Ebp:08X}")
                            # Read sockaddr from various likely locations
                            for label, sa_addr in [('[ebp-0x24]', ctx.Ebp - 0x24),
                                                    ('[ebp-0x28]', ctx.Ebp - 0x28),
                                                    ('[ebp-0x1C]', ctx.Ebp - 0x1C)]:
                                sa = read_mem(hProcess, sa_addr, 16)
                                if sa and len(sa) >= 8:
                                    family = struct.unpack_from('<H', sa, 0)[0]
                                    port = struct.unpack_from('>H', sa, 2)[0]  # network byte order
                                    ip = f"{sa[4]}.{sa[5]}.{sa[6]}.{sa[7]}"
                                    if family == 2:  # AF_INET
                                        print(f"  sockaddr_in {label}: {ip}:{port}")
                                        captures.append(('connect', ip, port))

                        # Set EIP back to the breakpoint address (re-execute the original instruction)
                        ctx.Eip = addr
                        kernel32.SetThreadContext(hThread, ctypes.byref(ctx))
                        kernel32.CloseHandle(hThread)

                        # Set single-step to re-enable breakpoint after one instruction
                        # (For now, just leave the breakpoint removed to avoid infinite loop)
                    else:
                        cont_status = DBG_EXCEPTION_NOT_HANDLED

                elif code == EXCEPTION_ACCESS_VIOLATION:
                    print(f"\n[AV] at 0x{addr:08X}")
                    cont_status = DBG_EXCEPTION_NOT_HANDLED
                elif code == EXCEPTION_SINGLE_STEP:
                    pass
                else:
                    cont_status = DBG_EXCEPTION_NOT_HANDLED

            elif de.dwDebugEventCode == OUTPUT_DEBUG_STRING_EVENT:
                pass

            elif de.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT:
                exit_code = de.u.ExitProcess.dwExitCode
                print(f"\n[EXIT] Code: {exit_code} (0x{exit_code:08X})")
                kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, DBG_CONTINUE)
                break

            kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, cont_status)

    except KeyboardInterrupt:
        print("\n[STOP]")
        kernel32.TerminateProcess(hProcess, 1)
    finally:
        kernel32.CloseHandle(hProcess)
        kernel32.CloseHandle(pi.hThread)

    # Print summary
    print("\n" + "=" * 60)
    print("  CAPTURED CONNECTIONS")
    print("=" * 60)
    for cap in captures:
        if cap[0] == 'inet_addr':
            print(f"  inet_addr(\"{cap[1]}\")")
        elif cap[0] == 'htons':
            print(f"  htons({cap[1]} or {cap[2]})")
        elif cap[0] == 'connect':
            print(f"  connect({cap[1]}:{cap[2]})")

    # Save to file
    log_path = os.path.join(exe_dir, "connect_log.txt")
    with open(log_path, 'w') as f:
        f.write("Azrok Plaza - Connection Capture\n")
        f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for cap in captures:
            f.write(f"{cap}\n")
    print(f"\n[SAVED] {log_path}")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
