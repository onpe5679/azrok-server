import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.scalar.Scalar;

public class FindOpcodeImmediates extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args == null || args.length == 0) {
            println("usage: FindOpcodeImmediates <hex-value> ...");
            return;
        }
        for (String raw : args) {
            String valueText = raw.toLowerCase().startsWith("0x") ? raw.substring(2) : raw;
            long target = Long.parseUnsignedLong(valueText, 16);
            println("== scalar immediate 0x" + Long.toHexString(target).toUpperCase() + " ==");
            int count = 0;
            int instructionCount = 0;
            for (Instruction instruction : currentProgram.getListing().getInstructions(true)) {
                instructionCount++;
                boolean matched = false;
                for (int operand = 0; operand < instruction.getNumOperands() && !matched; operand++) {
                    for (Object object : instruction.getOpObjects(operand)) {
                        if (object instanceof Scalar) {
                            Scalar scalar = (Scalar)object;
                            if (scalar.getUnsignedValue() == target) {
                                matched = true;
                                break;
                            }
                        }
                    }
                }
                if (matched) {
                    Function function = getFunctionContaining(instruction.getAddress());
                    String functionName = function == null ? "<no function>" : function.getName();
                    println(instruction.getAddress() + "  " + functionName + "  " + instruction);
                    count++;
                }
            }
            println("TOTAL " + count + " OF_INSTRUCTIONS " + instructionCount);
        }
    }
}
