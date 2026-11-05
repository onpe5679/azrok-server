import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class ghidra_find_xrefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        // GhidraScript#getScriptArgs() returns one argument per token, not a
        // single semicolon-delimited String.  Headless -postScript passes the
        // address list as individual arguments, so iterate the array directly.
        String[] values = getScriptArgs();
        for (String raw : values) {
            String text = raw.trim();
            if (text.isEmpty()) continue;
            Address target = toAddr(text);
            println("TARGET " + target);
            for (Reference ref : getReferencesTo(target)) {
                Function f = getFunctionContaining(ref.getFromAddress());
                println("  " + ref.getFromAddress() + " " + ref.getReferenceType()
                        + " function=" + (f == null ? "<none>" : f.getEntryPoint() + " " + f.getName()));
            }
        }
    }
}
