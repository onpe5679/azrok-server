import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.Symbol;

public class ListSymbolsRange extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) { println("usage: ListSymbolsRange <start> <end>"); return; }
        Address start = toAddr(args[0].replaceFirst("(?i)^0x", ""));
        Address end = toAddr(args[1].replaceFirst("(?i)^0x", ""));
        for (Symbol s : currentProgram.getSymbolTable().getAllSymbols(true)) {
            Address a = s.getAddress();
            if (a.compareTo(start) >= 0 && a.compareTo(end) <= 0) {
                println(a + " " + s.getSymbolType() + " " + s.getName() + " primary=" + s.isPrimary());
            }
        }
    }
}
