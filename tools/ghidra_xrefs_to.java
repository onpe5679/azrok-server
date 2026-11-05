// Read-only Ghidra helper for locating code references to an address.
// @category Azrok

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class ghidra_xrefs_to extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            printerr("usage: ghidra_xrefs_to.java <address>");
            return;
        }

        Address target = currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(args[0]);
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        int hits = 0;
        while (references.hasNext()) {
            Reference reference = references.next();
            Address from = reference.getFromAddress();
            Function function = currentProgram.getFunctionManager().getFunctionContaining(from);
            Instruction instruction = currentProgram.getListing().getInstructionAt(from);
            println(from + " | " + (function == null ? "<no-fn>" : function.getName())
                + " | " + reference.getReferenceType() + " | "
                + (instruction == null ? "<no-instruction>" : instruction.toString()));
            hits++;
        }
        println("TOTAL=" + hits);
    }
}
