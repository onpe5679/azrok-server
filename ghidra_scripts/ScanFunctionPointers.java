import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

/** Read-only raw-memory scan for data pointers to a function. */
public class ScanFunctionPointers extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args == null || args.length == 0) {
            println("usage: ScanFunctionPointers <hex_function> [hex_function ...]");
            return;
        }
        Memory memory = currentProgram.getMemory();
        for (String raw : args) {
            String text = raw.trim();
            if (text.startsWith("0x") || text.startsWith("0X")) text = text.substring(2);
            int target = (int)Long.parseLong(text, 16);
            println("== raw pointer hits for 0x" + text.toUpperCase() + " ==");
            int hits = 0;
            for (MemoryBlock block : memory.getBlocks()) {
                if (!block.isInitialized() || !block.isRead()) continue;
                long length = block.getSize();
                Address base = block.getStart();
                for (long off = 0; off + 4 <= length; off += 4) {
                    Address at = base.add(off);
                    int value;
                    try { value = memory.getInt(at); }
                    catch (Exception e) { continue; }
                    if (value != target) continue;
                    println(at + " block=" + block.getName());
                    for (int n = -4; n <= 20; n += 4) {
                        if (off + n < 0 || off + n + 4 > length) continue;
                        Address probe = base.add(off + n);
                        try { println("  " + probe + " = 0x" + String.format("%08X", memory.getInt(probe))); }
                        catch (Exception e) { }
                    }
                    hits++;
                    if (hits >= 200) break;
                }
                if (hits >= 200) break;
            }
            println("hits=" + hits);
        }
    }
}
