// Read-only Ghidra headless helper: resolve addresses captured from x32dbg.
// @category Azrok

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

public class PrintContainingFunctions extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String raw : getScriptArgs()) {
            Address address = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(raw);
            Function function = getFunctionContaining(address);
            Instruction instruction = getInstructionAt(address);
            println(raw + "\tfunction=" + (function == null ? "<none>" : function.getName())
                + "\tentry=" + (function == null ? "<none>" : function.getEntryPoint())
                + "\tinstruction=" + (instruction == null ? "<none>" : instruction.toString()));
        }
    }
}
