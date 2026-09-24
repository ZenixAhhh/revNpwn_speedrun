// Exports decompiled C pseudocode for all functions to a target directory or file.
//@category Decompilation
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.File;
import java.io.PrintWriter;

public class ExportDecompiledC extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File outFile;
        if (args.length > 0) {
            outFile = new File(args[0]);
        } else {
            outFile = new File(currentProgram.getExecutablePath() + ".decompiled.c");
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);

        try (PrintWriter writer = new PrintWriter(outFile)) {
            writer.println("// Decompiled C source for " + currentProgram.getName());
            writer.println("// Generated via Ghidra Headless Analyzer\n");

            FunctionIterator iter = currentProgram.getFunctionManager().getFunctions(true);
            while (iter.hasNext() && !monitor.isCancelled()) {
                Function func = iter.next();
                DecompileResults results = decompiler.decompileFunction(func, 30, monitor);
                if (results != null && results.decompileCompleted()) {
                    writer.println("// ========================================================");
                    writer.println("// Function: " + func.getName() + " @ " + func.getEntryPoint());
                    writer.println("// ========================================================");
                    writer.println(results.getDecompiledFunction().getC());
                    writer.println("\n");
                }
            }
        }
        println("[+] Successfully exported decompiled C to: " + outFile.getAbsolutePath());
    }
}
