import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class ShowXrefs extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args == null || args.length == 0) {
            println("usage: ShowXrefs <hex_address> [hex_address ...]");
            return;
        }

        for (String rawArg : args) {
            String raw = rawArg.trim();
            if (raw.startsWith("0x") || raw.startsWith("0X")) {
                raw = raw.substring(2);
            }
            Address addr = toAddr(raw);
            println("== xrefs to " + addr + " ==");
            int count = 0;
            for (Reference ref : getReferencesTo(addr)) {
                Address from = ref.getFromAddress();
                Function fn = getFunctionContaining(from);
                String fnName = (fn == null) ? "<no function>" : fn.getName();
                println(from + "  " + ref.getReferenceType() + "  " + fnName);
                count++;
            }
            if (count == 0) {
                println("<none>");
            }
        }
    }
}
