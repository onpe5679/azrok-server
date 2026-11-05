// Ghidra headless script - deeper analysis of open.exe
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.app.decompiler.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class AnalyzeLauncher2 extends GhidraScript {

    @Override
    public void run() throws Exception {
        println("=== DEEPER ANALYSIS ===");

        // 1. Search for ALL strings containing .exe, file mapping names, shared memory
        println("\n=== EXE AND FILE MAPPING STRINGS ===");
        Data data = getFirstData();
        while (data != null) {
            if (data.hasStringValue()) {
                String val = data.getDefaultValueRepresentation();
                if (val != null) {
                    String lower = val.toLowerCase();
                    if (lower.contains(".exe") || lower.contains("filemap") ||
                        lower.contains("shared") || lower.contains("mutex") ||
                        lower.contains("starmaru") || lower.contains("pipe") ||
                        lower.contains("event") || lower.contains("ipc") ||
                        lower.contains("javascript") || lower.contains("navigate") ||
                        lower.contains("invoke") || lower.contains("call") ||
                        lower.contains("external") || lower.contains("querystring") ||
                        lower.contains("p_target_id") || lower.contains("p_mbr") ||
                        lower.contains("init.csv") || lower.contains("lgc.tmp") ||
                        lower.contains("config") || lower.contains(".ini") ||
                        lower.contains(".cfg") || lower.contains(".dat") ||
                        lower.contains("maru") || lower.contains("open") ||
                        lower.contains("start") || lower.contains("exec") ||
                        lower.contains("spawn") || lower.contains("run") ||
                        lower.contains("launch") || lower.contains("game") ||
                        lower.contains("connect") || lower.contains("socket") ||
                        lower.contains("findwindow") || lower.contains("sendmessage") ||
                        lower.contains("wm_") || lower.contains("copydata")) {
                        println("  " + data.getAddress() + ": " + val);
                    }
                }
            }
            data = getDataAfter(data);
        }

        // 2. Find and decompile functions that use CreateFileMappingA, MapViewOfFile, OpenFileMappingA
        println("\n=== FUNCTIONS USING FILE MAPPING (SHARED MEMORY IPC) ===");
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        String[] apiNames = {"CreateFileMappingA", "MapViewOfFile", "OpenFileMappingA",
                            "FindWindowA", "SendMessageA", "socket", "connect"};

        SymbolTable symTable = currentProgram.getSymbolTable();
        Set<Function> decompiled = new HashSet<>();

        for (String apiName : apiNames) {
            SymbolIterator syms = symTable.getSymbols(apiName);
            while (syms.hasNext()) {
                Symbol sym = syms.next();
                Reference[] refs = getReferencesTo(sym.getAddress());
                for (Reference ref : refs) {
                    Function func = getFunctionContaining(ref.getFromAddress());
                    if (func != null && !decompiled.contains(func)) {
                        decompiled.add(func);
                        println("\n--- " + func.getName() + " @ " + func.getEntryPoint() +
                                " (calls " + apiName + ") ---");
                        DecompileResults res = decomp.decompileFunction(func, 30, new ConsoleTaskMonitor());
                        if (res.decompileCompleted()) {
                            println(res.getDecompiledFunction().getC());
                        }
                    }
                }
            }
        }

        // 3. Decompile FUN_0042d310 which is called with gameServer and gameServerPort
        println("\n=== FUN_0042d310 (called with gameServer, gameServerPort) ===");
        Function f = getFunctionAt(toAddr(0x0042d310));
        if (f != null && !decompiled.contains(f)) {
            DecompileResults res = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
            if (res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            }
        }

        // 4. Decompile FUN_00401fa0 and FUN_00402000 (called with parsed args)
        println("\n=== FUN_00401fa0 (stores first arg from sscanf) ===");
        f = getFunctionAt(toAddr(0x00401fa0));
        if (f != null) {
            DecompileResults res = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
            if (res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            }
        }

        println("\n=== FUN_00402000 (stores third arg from sscanf) ===");
        f = getFunctionAt(toAddr(0x00402000));
        if (f != null) {
            DecompileResults res = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
            if (res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            }
        }

        // 5. Decompile FUN_00402040 (called in login handler with password)
        println("\n=== FUN_00402040 (login handler - stores auth key) ===");
        f = getFunctionAt(toAddr(0x00402040));
        if (f != null) {
            DecompileResults res = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
            if (res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            }
        }

        // 6. Decompile FUN_0040a0e0 - called during init
        println("\n=== FUN_0040a0e0 (called during init) ===");
        f = getFunctionAt(toAddr(0x0040a0e0));
        if (f != null) {
            DecompileResults res = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
            if (res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            }
        }

        // 7. Look at FUN_0040a840 which is passed as callback
        println("\n=== FUN_0040a840 (timer/callback function) ===");
        f = getFunctionAt(toAddr(0x0040a840));
        if (f != null) {
            DecompileResults res = decomp.decompileFunction(f, 30, new ConsoleTaskMonitor());
            if (res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            }
        }

        decomp.dispose();
        println("\n=== DEEPER ANALYSIS COMPLETE ===");
    }
}
