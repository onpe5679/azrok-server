# -*- coding: utf-8 -*-
"""
Azrok Plaza Debugger - Late Attach Mode
Launches game normally, waits briefly, then attaches debugger.
This avoids interfering with DirectX initialization.
Run: python debug_azrok.py
"""
import ctypes
import ctypes.wintypes as wt
import struct
import os
import sys
import time
import subprocess

# Windows Debug API constants
DEBUG_PROCESS = 0x1
DEBUG_ONLY_THIS_PROCESS = 0x2

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8
RIP_EVENT = 9

DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

EXCEPTION_ACCESS_VIOLATION = 0xC0000005
EXCEPTION_BREAKPOINT = 0x80000003
EXCEPTION_SINGLE_STEP = 0x80000004
STATUS_WX86_BREAKPOINT = 0x4000001F

PROCESS_ALL_ACCESS = 0x001F0FFF
THREAD_GET_CONTEXT = 0x0008
THREAD_QUERY_INFORMATION = 0x0040
CONTEXT_FULL = 0x10007
TH32CS_SNAPTHREAD = 0x00000004

INFINITE = 0xFFFFFFFF

# Structures
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
    _fields_ = [
        ("ExceptionRecord", EXCEPTION_RECORD),
        ("dwFirstChance", wt.DWORD),
    ]

class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hFile", wt.HANDLE),
        ("lpBaseOfDll", ctypes.c_void_p),
        ("dwDebugInfoFileOffset", wt.DWORD),
        ("nDebugInfoSize", wt.DWORD),
        ("lpImageName", ctypes.c_void_p),
        ("fUnicode", wt.WORD),
    ]

class EXIT_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("dwExitCode", wt.DWORD),
    ]

class OUTPUT_DEBUG_STRING_INFO(ctypes.Structure):
    _fields_ = [
        ("lpDebugStringData", ctypes.c_void_p),
        ("fUnicode", wt.WORD),
        ("nDebugStringLength", wt.WORD),
    ]

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
        ("dwDebugEventCode", wt.DWORD),
        ("dwProcessId", wt.DWORD),
        ("dwThreadId", wt.DWORD),
        ("u", DEBUG_EVENT_UNION),
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

class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ThreadID", wt.DWORD),
        ("th32OwnerProcessID", wt.DWORD),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", wt.DWORD),
    ]

kernel32 = ctypes.windll.kernel32
ReadProcessMemory = kernel32.ReadProcessMemory
GetThreadContext = kernel32.GetThreadContext

def read_process_string(hProcess, addr, max_len=260, unicode=False):
    if not addr:
        return None
    buf = ctypes.create_string_buffer(max_len * (2 if unicode else 1))
    read = ctypes.c_size_t(0)
    if ReadProcessMemory(hProcess, ctypes.c_void_p(addr), buf, len(buf), ctypes.byref(read)):
        if unicode:
            return buf.raw[:read.value].decode('utf-16-le', errors='replace').rstrip('\x00')
        return buf.raw[:read.value].decode('ascii', errors='replace').rstrip('\x00')
    return None

def read_process_ptr(hProcess, addr):
    buf = ctypes.c_uint32(0)
    read = ctypes.c_size_t(0)
    if ReadProcessMemory(hProcess, ctypes.c_void_p(addr), ctypes.byref(buf), 4, ctypes.byref(read)):
        return buf.value
    return 0

def read_process_bytes(hProcess, addr, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    if ReadProcessMemory(hProcess, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
        return buf.raw[:read.value]
    return None

def get_thread_context(pid, tid):
    """Get context of a specific thread by ID"""
    hThread = kernel32.OpenThread(THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, False, tid)
    if not hThread:
        return None
    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL
    ok = GetThreadContext(hThread, ctypes.byref(ctx))
    kernel32.CloseHandle(hThread)
    return ctx if ok else None

def dump_stack(hProcess, esp, count=16):
    """Dump stack values"""
    lines = []
    for i in range(count):
        addr = esp + i * 4
        val = read_process_ptr(hProcess, addr)
        lines.append(f"    [ESP+{i*4:02X}] 0x{addr:08X}: 0x{val:08X}")
    return "\n".join(lines)

def main():
    exe_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(exe_dir, "Azrok.exe")
    if not os.path.exists(exe_path):
        print(f"[ERROR] {exe_path} not found!")
        return

    print("=" * 60)
    print("  Azrok Plaza Debugger (Late Attach Mode)")
    print("=" * 60)

    # Step 1: Launch game normally
    print("[1] Launching Azrok.exe normally...")
    proc = subprocess.Popen(
        [exe_path],
        cwd=exe_dir,
        creationflags=0  # Normal launch, no debug
    )
    pid = proc.pid
    print(f"    PID: {pid}")

    # Step 2: Wait briefly for DirectX init
    WAIT_SEC = 1.5
    print(f"[2] Waiting {WAIT_SEC}s for initialization...")
    time.sleep(WAIT_SEC)

    # Check if already dead
    ret = proc.poll()
    if ret is not None:
        print(f"[!] Process already exited with code: {ret} (0x{ret & 0xFFFFFFFF:08X})")
        print("    Game died before we could attach.")
        print("    Try reducing WAIT_SEC or game crashes too fast.")
        input("\nPress Enter to exit...")
        return

    # Step 3: Attach debugger
    print(f"[3] Attaching debugger to PID {pid}...")
    if not kernel32.DebugActiveProcess(pid):
        err = ctypes.GetLastError()
        print(f"[ERROR] DebugActiveProcess failed: {err}")
        proc.kill()
        return
    print("    Attached successfully!")

    # Don't kill process when debugger detaches
    try:
        kernel32.DebugSetProcessKillOnExit(False)
    except:
        pass

    print(f"[4] Monitoring for crashes... (Ctrl+C to stop)")
    print()

    hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    loaded_dlls = {}
    exception_count = 0
    access_violations = []
    all_exceptions = []
    start_time = time.time()
    first_bp_seen = False

    log_lines = []

    try:
        while True:
            de = DEBUG_EVENT()
            if not kernel32.WaitForDebugEvent(ctypes.byref(de), 5000):
                # Check if process still alive
                exit_code = wt.DWORD(0)
                kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code))
                if exit_code.value != 259:  # STILL_ACTIVE
                    print(f"\n[!] Process exited (code: 0x{exit_code.value:08X})")
                    break
                elapsed = time.time() - start_time
                if elapsed > 30:
                    print(f"[TIMEOUT] No crash after {elapsed:.0f}s - game may be running fine!")
                    print("  Detaching debugger...")
                    kernel32.DebugActiveProcessStop(pid)
                    break
                continue

            continue_status = DBG_CONTINUE

            if de.dwDebugEventCode == LOAD_DLL_DEBUG_EVENT:
                info = de.u.LoadDll
                dll_name = "unknown"
                if info.lpImageName:
                    name_ptr = read_process_ptr(hProcess, info.lpImageName)
                    if name_ptr:
                        name = read_process_string(hProcess, name_ptr, unicode=bool(info.fUnicode))
                        if name:
                            dll_name = name
                base = info.lpBaseOfDll if info.lpBaseOfDll else 0
                loaded_dlls[base] = dll_name

            elif de.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
                info = de.u.Exception
                code = info.ExceptionRecord.ExceptionCode
                addr = info.ExceptionRecord.ExceptionAddress or 0
                first = info.dwFirstChance
                tid = de.dwThreadId

                # Find module
                module = "unknown"
                mod_offset = addr
                for base, name in sorted(loaded_dlls.items(), reverse=True):
                    if base and addr >= base:
                        module = os.path.basename(name) if name else "unknown"
                        mod_offset = addr - base
                        break

                # Skip initial breakpoint from attach
                if code in (EXCEPTION_BREAKPOINT, STATUS_WX86_BREAKPOINT) and not first_bp_seen:
                    first_bp_seen = True
                    kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, DBG_CONTINUE)
                    continue

                exception_count += 1
                chance_str = "1st-chance" if first else "2nd-chance (UNHANDLED)"

                if code == EXCEPTION_ACCESS_VIOLATION:
                    rw_val = info.ExceptionRecord.ExceptionInformation[0]
                    rw = "read" if (rw_val is None or rw_val == 0) else "write"
                    target_val = info.ExceptionRecord.ExceptionInformation[1] if info.ExceptionRecord.NumberParameters >= 2 else None
                    target = target_val if target_val is not None else 0

                    msg = f"\n[EXCEPTION #{exception_count}] ACCESS_VIOLATION ({chance_str})"
                    msg += f"\n  Address: 0x{addr:08X} ({module} +0x{mod_offset:X})"
                    msg += f"\n  Type: {rw} at 0x{target:08X}"
                    msg += f"\n  Thread: {tid}"
                    print(msg)
                    log_lines.append(msg)

                    # Get thread context
                    ctx = get_thread_context(pid, tid)
                    if ctx:
                        reg_msg = f"  EAX={ctx.Eax:08X} EBX={ctx.Ebx:08X} ECX={ctx.Ecx:08X} EDX={ctx.Edx:08X}"
                        reg_msg += f"\n  ESI={ctx.Esi:08X} EDI={ctx.Edi:08X} ESP={ctx.Esp:08X} EBP={ctx.Ebp:08X}"
                        reg_msg += f"\n  EIP={ctx.Eip:08X}"
                        print(reg_msg)
                        log_lines.append(reg_msg)

                        # Dump code bytes at crash
                        code_bytes = read_process_bytes(hProcess, addr, 16)
                        if code_bytes:
                            hex_str = ' '.join(f'{b:02X}' for b in code_bytes)
                            code_msg = f"  Code at EIP: {hex_str}"
                            print(code_msg)
                            log_lines.append(code_msg)

                        # Dump stack
                        stack_msg = f"  Stack dump:"
                        print(stack_msg)
                        log_lines.append(stack_msg)
                        stack = dump_stack(hProcess, ctx.Esp)
                        print(stack)
                        log_lines.append(stack)

                    access_violations.append({
                        'addr': addr, 'module': module, 'offset': mod_offset,
                        'rw': rw, 'target': target, 'first': first, 'tid': tid
                    })

                    if not first:
                        print("  >> UNHANDLED - This will crash the program!")

                    continue_status = DBG_EXCEPTION_NOT_HANDLED

                elif code == EXCEPTION_BREAKPOINT or code == STATUS_WX86_BREAKPOINT:
                    continue_status = DBG_EXCEPTION_NOT_HANDLED
                elif code == EXCEPTION_SINGLE_STEP:
                    continue_status = DBG_EXCEPTION_NOT_HANDLED
                else:
                    known = {
                        0xE06D7363: "C++ Exception (throw)",
                        0xC0000096: "Privileged Instruction",
                        0xC00000FD: "Stack Overflow",
                        0xC0000094: "Integer Divide by Zero",
                        0xC000001D: "Illegal Instruction",
                        0x406D1388: "Thread Name Exception",
                        0xC000000D: "STATUS_INVALID_PARAMETER",
                    }
                    code_name = known.get(code, f"0x{code:08X}")
                    msg = f"\n[EXCEPTION #{exception_count}] {code_name} ({chance_str})"
                    msg += f"\n  Address: 0x{addr:08X} ({module} +0x{mod_offset:X})"
                    msg += f"\n  Thread: {tid}"
                    print(msg)
                    log_lines.append(msg)

                    all_exceptions.append({'code': code, 'code_name': code_name,
                        'addr': addr, 'module': module, 'offset': mod_offset, 'first': first})

                    continue_status = DBG_EXCEPTION_NOT_HANDLED

            elif de.dwDebugEventCode == OUTPUT_DEBUG_STRING_EVENT:
                info = de.u.DebugString
                s = read_process_string(hProcess, info.lpDebugStringData,
                                       info.nDebugStringLength, bool(info.fUnicode))
                if s:
                    print(f"[DEBUG] {s.strip()}")

            elif de.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT:
                exit_code = de.u.ExitProcess.dwExitCode
                elapsed = time.time() - start_time
                msg = f"\n{'='*60}"
                msg += f"\n[EXIT] Code: {exit_code} (0x{exit_code:08X})"
                msg += f"\n  Runtime: {elapsed:.1f}s | Exceptions: {exception_count} | AVs: {len(access_violations)}"

                if access_violations:
                    msg += f"\n\n  Access Violation Summary:"
                    for i, av in enumerate(access_violations):
                        fc = "1st" if av['first'] else "2ND"
                        msg += (f"\n    #{i+1}: [{fc}] 0x{av['addr']:08X} ({av['module']}+0x{av['offset']:X}) "
                                f"{av['rw']} @ 0x{av['target']:08X} [thread {av['tid']}]")

                if all_exceptions:
                    msg += f"\n\n  Other Exceptions:"
                    for i, ex in enumerate(all_exceptions):
                        fc = "1st" if ex['first'] else "2ND"
                        msg += f"\n    [{fc}] {ex['code_name']} at 0x{ex['addr']:08X} ({ex['module']}+0x{ex['offset']:X})"

                msg += f"\n{'='*60}"
                print(msg)
                log_lines.append(msg)
                kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, DBG_CONTINUE)
                break

            kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, continue_status)

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Detaching debugger...")
        kernel32.DebugActiveProcessStop(pid)
    finally:
        kernel32.CloseHandle(hProcess)

    # Save log
    log_path = os.path.join(exe_dir, "debug_log.txt")
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("Azrok Plaza Debug Log (Late Attach)\n")
        f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Exceptions: {exception_count}\n")
        f.write(f"Access Violations: {len(access_violations)}\n\n")
        for line in log_lines:
            f.write(line + "\n")
    print(f"\n[SAVED] {log_path}")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
