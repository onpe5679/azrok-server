// Ghidra headless script to analyze open.exe launcher
// @category Analysis

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.*;
import ghidra.program.model.data.*;
import ghidra.program.model.mem.*;
import ghidra.app.decompiler.*;
import ghidra.util.task.ConsoleTaskMonitor;
import java.util.*;

public class AnalyzeLauncher extends GhidraScript {

    @Override
    public void run() throws Exception {
        println("=== LAUNCHER ANALYSIS START ===");

        // 1. Search for key strings
        println("\n=== KEY STRINGS ===");
        String[] searchTerms = {
            "gameServer", "gameServerPort", "Azrok", "CreateProcess",
            "%s %s %s", "%s %s", "<data>", "</data>", "login",
            "http", "https", ".exe", "command", "cmd", "launch",
            "ShellExecute", "WinExec", "server", "port", "address",
            "ip", "auth", "token", "key", "session", "user", "pass",
            "xml", "HTML", "POST", "GET"
        };

        Data data = getFirstData();
        Map<String, List<String>> foundStrings = new LinkedHashMap<>();

        while (data != null) {
            if (data.hasStringValue()) {
                String val = data.getDefaultValueRepresentation();
                if (val != null) {
                    String lower = val.toLowerCase();
                    for (String term : searchTerms) {
                        if (lower.contains(term.toLowerCase())) {
                            List<String> list = foundStrings.computeIfAbsent(term, k -> new ArrayList<>());
                            list.add(data.getAddress() + ": " + val);
                        }
                    }
                }
            }
            data = getDataAfter(data);
        }

        for (Map.Entry<String, List<String>> entry : foundStrings.entrySet()) {
            println("--- Matches for '" + entry.getKey() + "' ---");
            for (String s : entry.getValue()) {
                println("  " + s);
            }
        }

        // 2. List imports
        println("\n=== IMPORTS (Process/Shell related) ===");
        SymbolTable symTable = currentProgram.getSymbolTable();
        SymbolIterator symIter = symTable.getExternalSymbols();
        while (symIter.hasNext()) {
            Symbol sym = symIter.next();
            String name = sym.getName();
            String lower = name.toLowerCase();
            if (lower.contains("process") || lower.contains("shell") || lower.contains("exec") ||
                lower.contains("create") || lower.contains("internet") || lower.contains("http") ||
                lower.contains("url") || lower.contains("open") || lower.contains("write") ||
                lower.contains("file") || lower.contains("registry") || lower.contains("reg") ||
                lower.contains("memory") || lower.contains("map") || lower.contains("pipe") ||
                lower.contains("socket") || lower.contains("connect") || lower.contains("send") ||
                lower.contains("recv")) {
                println("  " + name + " @ " + sym.getAddress());
            }
        }

        // 3. List ALL imports for completeness
        println("\n=== ALL IMPORTS ===");
        symIter = symTable.getExternalSymbols();
        while (symIter.hasNext()) {
            Symbol sym = symIter.next();
            println("  " + sym.getName() + " @ " + sym.getAddress());
        }

        // 4. Decompile functions that reference key strings
        println("\n=== DECOMPILING FUNCTIONS WITH XREFS TO KEY STRINGS ===");
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        // Find addresses of interesting strings and decompile their referencing functions
        Set<Function> decompiled = new HashSet<>();
        data = getFirstData();
        while (data != null) {
            if (data.hasStringValue()) {
                String val = data.getDefaultValueRepresentation();
                if (val != null) {
                    String lower = val.toLowerCase();
                    boolean interesting = lower.contains("gameserver") || lower.contains("azrok") ||
                        lower.contains("%s %s") || lower.contains("createprocess") ||
                        lower.contains("shellexecute") || lower.contains(".exe") ||
                        lower.contains("<data>") || lower.contains("server") ||
                        lower.contains("port") || lower.contains("login") ||
                        lower.contains("launch");
                    if (interesting) {
                        Reference[] refs = getReferencesTo(data.getAddress());
                        for (Reference ref : refs) {
                            Function func = getFunctionContaining(ref.getFromAddress());
                            if (func != null && !decompiled.contains(func)) {
                                decompiled.add(func);
                                println("\n--- Decompiling " + func.getName() + " @ " + func.getEntryPoint() + " ---");
                                println("  (references string: " + val + ")");
                                DecompileResults res = decomp.decompileFunction(func, 30, new ConsoleTaskMonitor());
                                if (res.decompileCompleted()) {
                                    println(res.getDecompiledFunction().getC());
                                } else {
                                    println("  [decompilation failed]");
                                }
                            }
                        }
                    }
                }
            }
            data = getDataAfter(data);
        }

        decomp.dispose();

        // 5. Entry points
        println("\n=== ENTRY POINTS ===");
        SymbolIterator entries = symTable.getSymbols("entry");
        while (entries.hasNext()) {
            Symbol entry = entries.next();
            println("  " + entry.getName() + " @ " + entry.getAddress());
        }

        println("\n=== LAUNCHER ANALYSIS COMPLETE ===");
    }
}
