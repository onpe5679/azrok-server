# -*- coding: utf-8 -*-
"""
Attach to an already-running Azrok.exe process and log debug exceptions.
Useful when azrok_server.py launches the game and we want exact crash EIP/EAX...

Example:
  python tools\\attach_azrok_debugger.py --pid 180276 --log artifacts\\ui-probes\\attach_debug.log
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time


EXCEPTION_DEBUG_EVENT = 1
LOAD_DLL_DEBUG_EVENT = 6
EXIT_PROCESS_DEBUG_EVENT = 5
OUTPUT_DEBUG_STRING_EVENT = 8

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
STILL_ACTIVE = 259


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
    _fields_ = [("dwExitCode", wt.DWORD)]


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


kernel32 = ctypes.windll.kernel32
ReadProcessMemory = kernel32.ReadProcessMemory
GetThreadContext = kernel32.GetThreadContext
Wow64GetThreadContext = getattr(kernel32, "Wow64GetThreadContext", None)


def read_process_string(h_process, addr, max_len=260, unicode=False):
    if not addr:
        return None
    buf = ctypes.create_string_buffer(max_len * (2 if unicode else 1))
    read = ctypes.c_size_t(0)
    if ReadProcessMemory(h_process, ctypes.c_void_p(addr), buf, len(buf), ctypes.byref(read)):
        if unicode:
            return buf.raw[:read.value].decode("utf-16-le", errors="replace").rstrip("\x00")
        return buf.raw[:read.value].decode("ascii", errors="replace").rstrip("\x00")
    return None


def read_process_ptr(h_process, addr):
    buf = ctypes.c_uint32(0)
    read = ctypes.c_size_t(0)
    if ReadProcessMemory(h_process, ctypes.c_void_p(addr), ctypes.byref(buf), 4, ctypes.byref(read)):
        return buf.value
    return 0


def read_process_bytes(h_process, addr, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    if ReadProcessMemory(h_process, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
        return buf.raw[:read.value]
    return None


def get_thread_context(tid):
    h_thread = kernel32.OpenThread(THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, False, tid)
    if not h_thread:
        return None
    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL
    ok = False
    if Wow64GetThreadContext is not None:
        try:
            ok = bool(Wow64GetThreadContext(h_thread, ctypes.byref(ctx)))
        except Exception:
            ok = False
    if not ok:
        ok = bool(GetThreadContext(h_thread, ctypes.byref(ctx)))
    kernel32.CloseHandle(h_thread)
    return ctx if ok else None


def dump_stack(h_process, esp, count=16):
    lines = []
    for i in range(count):
        addr = esp + i * 4
        val = read_process_ptr(h_process, addr)
        lines.append(f"    [ESP+{i*4:02X}] 0x{addr:08X}: 0x{val:08X}")
    return "\n".join(lines)


def dump_dwords(h_process, addr, count=8):
    if not addr:
        return "    <null>"
    lines = []
    for i in range(count):
        cur = addr + i * 4
        val = read_process_ptr(h_process, cur)
        lines.append(f"    [0x{cur:08X}] = 0x{val:08X}")
    return "\n".join(lines)


def dump_ptr_chain(h_process, addr, depth=4):
    if not addr:
        return "0x00000000"
    parts = [f"0x{addr:08X}"]
    cur = addr
    for _ in range(depth):
        nxt = read_process_ptr(h_process, cur)
        parts.append(f"0x{nxt:08X}")
        if nxt == 0 or nxt == cur:
            break
        cur = nxt
    return " -> ".join(parts)


def resolve_module(loaded_dlls, addr):
    module = "unknown"
    mod_offset = addr
    for base, name in sorted(loaded_dlls.items(), reverse=True):
        if base and addr >= base:
            module = os.path.basename(name) if name else "unknown"
            mod_offset = addr - base
            break
    return module, mod_offset


def main():
    parser = argparse.ArgumentParser(description="Attach debugger to a running Azrok.exe process")
    parser.add_argument("--pid", type=int, required=True, help="Target Azrok.exe PID")
    parser.add_argument("--timeout", type=float, default=30.0, help="Detach after this many seconds without exit")
    parser.add_argument("--log", default="", help="Optional output log file")
    args = parser.parse_args()

    pid = args.pid
    print(f"[attach] target pid={pid}")
    if not kernel32.DebugActiveProcess(pid):
        err = ctypes.get_last_error()
        raise SystemExit(f"DebugActiveProcess failed: {err}")

    try:
        kernel32.DebugSetProcessKillOnExit(False)
    except Exception:
        pass

    h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not h_process:
        raise SystemExit("OpenProcess failed")

    loaded_dlls = {}
    first_bp_seen = False
    exception_count = 0
    access_violations = []
    other_exceptions = []
    start = time.time()
    log_lines = []

    def emit(text):
        try:
            print(text)
        except UnicodeEncodeError:
            safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
                sys.stdout.encoding or "utf-8", errors="replace"
            )
            print(safe)
        log_lines.append(text)

    try:
        while True:
            de = DEBUG_EVENT()
            if not kernel32.WaitForDebugEvent(ctypes.byref(de), 1000):
                exit_code = wt.DWORD(0)
                kernel32.GetExitCodeProcess(h_process, ctypes.byref(exit_code))
                if exit_code.value != STILL_ACTIVE:
                    emit(f"[exit-check] process exited code=0x{exit_code.value:08X}")
                    break
                if time.time() - start > args.timeout:
                    emit(f"[timeout] no terminal exit after {args.timeout:.1f}s, detaching")
                    kernel32.DebugActiveProcessStop(pid)
                    break
                continue

            continue_status = DBG_CONTINUE

            if de.dwDebugEventCode == LOAD_DLL_DEBUG_EVENT:
                info = de.u.LoadDll
                dll_name = "unknown"
                if info.lpImageName:
                    name_ptr = read_process_ptr(h_process, info.lpImageName)
                    if name_ptr:
                        name = read_process_string(h_process, name_ptr, unicode=bool(info.fUnicode))
                        if name:
                            dll_name = name
                base = info.lpBaseOfDll if info.lpBaseOfDll else 0
                loaded_dlls[base] = dll_name

            elif de.dwDebugEventCode == OUTPUT_DEBUG_STRING_EVENT:
                info = de.u.DebugString
                s = read_process_string(
                    h_process, info.lpDebugStringData, info.nDebugStringLength, bool(info.fUnicode)
                )
                if s:
                    emit(f"[debug] {s.strip()}")

            elif de.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
                info = de.u.Exception
                code = info.ExceptionRecord.ExceptionCode
                addr = info.ExceptionRecord.ExceptionAddress or 0
                first = info.dwFirstChance
                tid = de.dwThreadId
                module, mod_offset = resolve_module(loaded_dlls, addr)

                if code in (EXCEPTION_BREAKPOINT, STATUS_WX86_BREAKPOINT) and not first_bp_seen:
                    first_bp_seen = True
                    kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, DBG_CONTINUE)
                    continue

                exception_count += 1
                chance = "1st" if first else "2nd"

                if code == EXCEPTION_ACCESS_VIOLATION:
                    rw_val = info.ExceptionRecord.ExceptionInformation[0]
                    rw = "read" if (rw_val is None or rw_val == 0) else "write"
                    target_val = (
                        info.ExceptionRecord.ExceptionInformation[1]
                        if info.ExceptionRecord.NumberParameters >= 2 else None
                    )
                    target = target_val if target_val is not None else 0
                    emit(
                        f"[av #{exception_count}] {chance} addr=0x{addr:08X} "
                        f"({module}+0x{mod_offset:X}) {rw}@0x{target:08X} tid={tid}"
                    )
                    ctx = get_thread_context(tid)
                    if ctx:
                        emit(
                            f"  EAX={ctx.Eax:08X} EBX={ctx.Ebx:08X} ECX={ctx.Ecx:08X} "
                            f"EDX={ctx.Edx:08X}"
                        )
                        emit(
                            f"  ESI={ctx.Esi:08X} EDI={ctx.Edi:08X} ESP={ctx.Esp:08X} "
                            f"EBP={ctx.Ebp:08X} EIP={ctx.Eip:08X}"
                        )
                        code_bytes = read_process_bytes(h_process, addr, 16)
                        if code_bytes:
                            emit("  CODE=" + " ".join(f"{b:02X}" for b in code_bytes))
                        for reg_name, reg_val in (
                            ("EAX", ctx.Eax),
                            ("EBX", ctx.Ebx),
                            ("ECX", ctx.Ecx),
                            ("EDX", ctx.Edx),
                            ("ESP", ctx.Esp),
                            ("EBP", ctx.Ebp),
                        ):
                            emit(f"  {reg_name}_CHAIN={dump_ptr_chain(h_process, reg_val)}")
                            if reg_val >= 0x10000:
                                emit(f"  {reg_name}_MEM:")
                                emit(dump_dwords(h_process, reg_val))
                        emit("  STACK:")
                        emit(dump_stack(h_process, ctx.Esp))
                    access_violations.append((addr, module, mod_offset, rw, target, tid, first))
                    continue_status = DBG_EXCEPTION_NOT_HANDLED

                elif code not in (EXCEPTION_BREAKPOINT, EXCEPTION_SINGLE_STEP, STATUS_WX86_BREAKPOINT):
                    known = {
                        0xE06D7363: "C++ Exception",
                        0xC0000096: "Privileged Instruction",
                        0xC00000FD: "Stack Overflow",
                        0xC0000094: "Divide by Zero",
                        0xC000001D: "Illegal Instruction",
                        0x406D1388: "Thread Name Exception",
                        0xC000000D: "STATUS_INVALID_PARAMETER",
                    }
                    name = known.get(code, f"0x{code:08X}")
                    emit(
                        f"[ex #{exception_count}] {chance} {name} at 0x{addr:08X} "
                        f"({module}+0x{mod_offset:X}) tid={tid}"
                    )
                    other_exceptions.append((code, addr, module, mod_offset, tid, first))
                    continue_status = DBG_EXCEPTION_NOT_HANDLED

            elif de.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT:
                exit_code = de.u.ExitProcess.dwExitCode
                emit(
                    f"[exit] code=0x{exit_code:08X} runtime={time.time() - start:.1f}s "
                    f"exceptions={exception_count} avs={len(access_violations)}"
                )
                kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, DBG_CONTINUE)
                break

            kernel32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, continue_status)

    finally:
        kernel32.CloseHandle(h_process)
        if args.log:
            log_path = os.path.abspath(args.log)
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines) + "\n")
            print(f"[saved] {log_path}")


if __name__ == "__main__":
    main()
