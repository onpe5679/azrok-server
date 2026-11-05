// Ghidra headless helper: print decompiler text, instructions, and basic-block
// successors for one or more hexadecimal virtual addresses.
// @category Azrok

import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.block.BasicBlockModel;
import ghidra.program.model.block.CodeBlock;
import ghidra.program.model.block.CodeBlockIterator;
import ghidra.program.model.block.CodeBlockReference;
import ghidra.program.model.block.CodeBlockReferenceIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class ExportFunctionContract extends GhidraScript {
    @Override
    protected void run() throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        BasicBlockModel blocks = new BasicBlockModel(currentProgram);
        println("PROGRAM " + currentProgram.getName() + " BASE=" + currentProgram.getImageBase() +
            " MIN=" + currentProgram.getMinAddress() + " MAX=" + currentProgram.getMaxAddress());

        for (String argument : getScriptArgs()) {
            Address address = toAddr(argument.replace("0x", ""));
            Function function = getFunctionContaining(address);
            if (function == null) {
                println("NO_FUNCTION " + address);
                continue;
            }

            println("=== FUNCTION " + function.getName() + " " + function.getEntryPoint() +
                " BODY=" + function.getBody() + " ===");
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            println("--- DECOMPILE ---");
            println(result.decompileCompleted() ? result.getDecompiledFunction().getC() :
                "DECOMPILE_FAILED " + result.getErrorMessage());

            println("--- INSTRUCTIONS ---");
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            int count = 0;
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                println(instruction.getAddress() + "\t" + instruction.toString());
                count++;
            }
            println("INSTRUCTION_COUNT=" + count);

            println("--- CFG ---");
            CodeBlockIterator iterator = blocks.getCodeBlocksContaining(function.getBody(), monitor);
            while (iterator.hasNext()) {
                CodeBlock block = iterator.next();
                List<String> destinations = new ArrayList<>();
                CodeBlockReferenceIterator references = block.getDestinations(monitor);
                while (references.hasNext()) {
                    CodeBlockReference reference = references.next();
                    destinations.add(reference.getDestinationAddress() + ":" + reference.getFlowType());
                }
                println("BLOCK " + block.getFirstStartAddress() + ".." + block.getMaxAddress() +
                    " -> " + String.join(",", destinations));
            }
        }
        decompiler.dispose();
    }
}
