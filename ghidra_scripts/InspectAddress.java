import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.listing.Data;
import ghidra.program.model.symbol.Reference;

public class InspectAddress extends GhidraScript {
    @Override
    protected void run() throws Exception {
        for (String raw : getScriptArgs()) {
            String text = raw.trim();
            if (text.startsWith("0x") || text.startsWith("0X")) text = text.substring(2);
            Address a = toAddr(text);
            MemoryBlock b = currentProgram.getMemory().getBlock(a);
            println("== " + a + " ==");
            if (b != null) {
                println("block=" + b.getName() + " start=" + b.getStart() + " end=" + b.getEnd()
                    + " init=" + b.isInitialized() + " read=" + b.isRead()
                    + " write=" + b.isWrite() + " execute=" + b.isExecute()
                    + " source=" + b.getSourceName());
            } else println("block=<none>");
            Data d = currentProgram.getListing().getDataContaining(a);
            if (d != null) println("data=" + d.getDataType() + " len=" + d.getLength() + " value=" + d.getValue());
            for (Reference ref : getReferencesTo(a)) println("xref=" + ref.getFromAddress() + " " + ref.getReferenceType());
            for (int i = 0; i < 12; i++) {
                Address p = a.add(i * 4);
                try { println("  " + p + " = 0x" + String.format("%08X", currentProgram.getMemory().getInt(p))); }
                catch (Exception e) { break; }
            }
        }
    }
}
