import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class AzrokXrefDump extends GhidraScript {
    @Override
    public void run() throws Exception {
        FunctionManager functions = currentProgram.getFunctionManager();
        String[] targets = getScriptArgs();
        for (String target : targets) {
            Address address = toAddr(target);
            Function function = functions.getFunctionAt(address);
            println("TARGET " + address + " " + function);
            ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(address);
            while (refs.hasNext()) {
                Reference ref = refs.next();
                Address from = ref.getFromAddress();
                Function owner = functions.getFunctionContaining(from);
                println("REF " + from + " " + owner + " " + ref.getReferenceType());
            }
        }
    }
}
