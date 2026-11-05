import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;

public class DisassembleRange extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) { println("usage: DisassembleRange <start> <end>"); return; }
        Address a = toAddr(args[0].replaceFirst("(?i)^0x", ""));
        Address end = toAddr(args[1].replaceFirst("(?i)^0x", ""));
        while (a.compareTo(end) <= 0) {
            Instruction i = currentProgram.getListing().getInstructionAt(a);
            if (i == null) { a = a.add(1); continue; }
            println(i.getAddress() + "  " + i);
            a = i.getMaxAddress().add(1);
        }
    }
}
