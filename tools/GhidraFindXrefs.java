// Ghidra script: print code references to one address and their containing functions.
// @category Azrok
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class GhidraFindXrefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            printerr("usage: GhidraFindXrefs <address>");
            return;
        }
        Address target = toAddr(args[0]);
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(target);
        while (refs.hasNext()) {
            Reference ref = refs.next();
            Function function = getFunctionContaining(ref.getFromAddress());
            println(ref.getFromAddress() + " " + ref.getReferenceType() + " " +
                (function == null ? "<none>" : function.getName() + " " + function.getEntryPoint()));
        }
    }
}
