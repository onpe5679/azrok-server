// Export analyzed function body ranges for offline profiler aggregation.
//@category Azrok

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressRange;
import ghidra.program.model.address.AddressRangeIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;

public class ExportFunctionRanges extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException("usage: ExportFunctionRanges <output.csv>");
        }
        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) parent.mkdirs();
        Address imageBase = currentProgram.getImageBase();
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(output))) {
            writer.write("# program=" + currentProgram.getName());
            writer.newLine();
            writer.write("# sha256=" + currentProgram.getExecutableSHA256());
            writer.newLine();
            writer.write("# image_base=" + imageBase.toString());
            writer.newLine();
            writer.write("entry_rva,range_start_rva,range_end_exclusive_rva,name");
            writer.newLine();
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function function = functions.next();
                long entryRva = function.getEntryPoint().subtract(imageBase);
                String name = function.getName().replace('"', '_');
                AddressRangeIterator ranges = function.getBody().getAddressRanges();
                while (ranges.hasNext()) {
                    AddressRange range = ranges.next();
                    long startRva = range.getMinAddress().subtract(imageBase);
                    long endExclusiveRva = range.getMaxAddress().subtract(imageBase) + 1L;
                    writer.write(String.format("0x%X,0x%X,0x%X,\"%s\"",
                        entryRva, startRva, endExclusiveRva, name));
                    writer.newLine();
                }
            }
        }
        println("Exported function ranges to " + output.getAbsolutePath());
    }
}
