// Read-only Ghidra helper for locating scalar instruction operands.
// @category Azrok

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.scalar.Scalar;

public class ghidra_search_scalar extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            printerr("usage: ghidra_search_scalar.java <unsigned-value>");
            return;
        }

        long wanted = Long.decode(args[0]);
        int hits = 0;
        for (Instruction instruction : currentProgram.getListing().getInstructions(true)) {
            boolean matched = false;
            for (int operand = 0; operand < instruction.getNumOperands(); operand++) {
                for (Object object : instruction.getOpObjects(operand)) {
                    if (object instanceof Scalar && ((Scalar) object).getUnsignedValue() == wanted) {
                        matched = true;
                    }
                }
            }
            if (!matched) {
                continue;
            }
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            println(instruction.getAddress() + " | "
                + (function == null ? "<no-fn>" : function.getName()) + " | "
                + instruction);
            hits++;
        }
        println("TOTAL=" + hits);
    }
}
