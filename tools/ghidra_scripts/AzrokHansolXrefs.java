import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;

public class AzrokHansolXrefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        long[] addresses = {
            0x006a9068L, 0x006a90acL, 0x006a90d4L,
            0x005ca180L, 0x005ca360L, 0x005cade0L,
            0x004da6f1L, 0x004d9feeL, 0x004e1627L
        };
        ReferenceManager references = currentProgram.getReferenceManager();
        FunctionManager functions = currentProgram.getFunctionManager();
        for (long raw : addresses) {
            Address target = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(raw);
            println("STRING " + target);
            ReferenceIterator iterator = references.getReferencesTo(target);
            while (iterator.hasNext()) {
                Reference reference = iterator.next();
                Address from = reference.getFromAddress();
                Function function = functions.getFunctionContaining(from);
                println("  XREF " + from + " " + reference.getReferenceType() +
                    " FUNC " + (function == null ? "<none>" :
                    function.getName() + "@" + function.getEntryPoint()));
            }
        }
    }
}
