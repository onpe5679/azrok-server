//Decompile the function containing each address passed as a script argument.
//Addresses are given as plain hex in the program's own address space, e.g.
//1001DFB8 for acknex.dll RVA 0x1DFB8 when the image base is 0x10000000.
//@category Azrok
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

public class DecompileAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("DECOMPILE_AT: no addresses given");
            return;
        }
        println("DECOMPILE_AT image_base=" + currentProgram.getImageBase());
        DecompInterface d = new DecompInterface();
        d.openProgram(currentProgram);
        for (String a : args) {
            Address addr;
            try {
                addr = currentProgram.getAddressFactory().getDefaultAddressSpace()
                        .getAddress(Long.parseUnsignedLong(a.replace("0x", ""), 16));
            } catch (Exception e) {
                println("DECOMPILE_AT bad address " + a + ": " + e);
                continue;
            }
            println("===== DECOMPILE_AT " + a + " -> " + addr + " =====");
            Function f = getFunctionContaining(addr);
            if (f == null) {
                println("no function contains it; raw disassembly around the address:");
                Address s = addr.subtract(0x40);
                Instruction i = getInstructionAt(s);
                if (i == null) i = getInstructionAfter(s);
                for (int n = 0; i != null && n < 60; n++) {
                    println(String.format("%s%s  %s", i.getAddress().equals(addr) ? ">>> " : "    ",
                            i.getAddress(), i.toString()));
                    i = i.getNext();
                }
                continue;
            }
            println("function " + f.getName() + " @ " + f.getEntryPoint()
                    + "  size=" + f.getBody().getNumAddresses());
            // The faulting instruction itself, plus a little context, anchors the
            // decompiled body to the exact EIP.
            Instruction fault = getInstructionAt(addr);
            if (fault != null) println("FAULT INSTRUCTION: " + addr + "  " + fault.toString());
            Instruction i = getInstructionAt(f.getEntryPoint());
            int shown = 0;
            println("--- disassembly (fault marked) ---");
            while (i != null && f.getBody().contains(i.getAddress()) && shown < 400) {
                println(String.format("%s%s  %s", i.getAddress().equals(addr) ? ">>> " : "    ",
                        i.getAddress(), i.toString()));
                i = i.getNext();
                shown++;
            }
            println("--- decompiled ---");
            DecompileResults r = d.decompileFunction(f, 90, monitor);
            if (r != null && r.decompileCompleted() && r.getDecompiledFunction() != null) {
                println(r.getDecompiledFunction().getC());
            } else {
                println("decompile failed: " + (r == null ? "null" : r.getErrorMessage()));
            }
            println("--- callers ---");
            for (Function c : f.getCallingFunctions(monitor)) {
                println("  " + c.getName() + " @ " + c.getEntryPoint());
            }
        }
        d.dispose();
        println("DECOMPILE_AT done");
    }
}
