import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class DecompileAddresses extends GhidraScript {
    @Override
    protected void run() throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String raw : getScriptArgs()) {
            String text = raw.toLowerCase().startsWith("0x") ? raw.substring(2) : raw;
            Address address = toAddr(text);
            Function function = getFunctionContaining(address);
            println("== " + address + " " + (function == null ? "<none>" : function.getName()) + " ==");
            if (function == null) {
                continue;
            }
            DecompileResults results = decompiler.decompileFunction(function, 60, monitor);
            if (!results.decompileCompleted()) {
                println("DECOMPILE FAILED: " + results.getErrorMessage());
                continue;
            }
            println(results.getDecompiledFunction().getC());
        }
        decompiler.dispose();
    }
}
