import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;

public class XrefsAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        ReferenceManager references = currentProgram.getReferenceManager();
        FunctionManager functions = currentProgram.getFunctionManager();
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("usage: XrefsAt.java ADDRESS [ADDRESS ...]");
            return;
        }

        for (String value : args) {
            Address target = toAddr(value);
            println("=== XREFS TO " + target + " ===");
            ReferenceIterator iterator = references.getReferencesTo(target);
            while (iterator.hasNext()) {
                Reference reference = iterator.next();
                Address from = reference.getFromAddress();
                Function function = functions.getFunctionContaining(from);
                String owner = function == null
                    ? "<no-function>"
                    : function.getName() + "@" + function.getEntryPoint();
                println(from + " " + reference.getReferenceType() + " " + owner);
            }
        }
    }
}
