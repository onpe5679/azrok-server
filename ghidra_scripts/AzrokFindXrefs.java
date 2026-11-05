import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

/** Read-only xref dump with a project-unique class name. */
public class AzrokFindXrefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String raw : getScriptArgs()) {
            String text = raw.trim();
            if (text.isEmpty()) continue;
            Address target = toAddr(text.startsWith("0x") ? text.substring(2) : text);
            println("TARGET " + target);
            for (Reference ref : getReferencesTo(target)) {
                Function f = getFunctionContaining(ref.getFromAddress());
                println("  " + ref.getFromAddress() + " " + ref.getReferenceType()
                        + " function=" + (f == null ? "<none>"
                        : f.getEntryPoint() + " " + f.getName()));
            }
        }
    }
}
