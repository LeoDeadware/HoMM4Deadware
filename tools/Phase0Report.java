// Ghidra headless script: summary of heroes4.exe for phase 0 (imports, functions, sizes, RTTI classes)
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.mem.*;
import java.util.*;
import java.io.*;

public class Phase0Report extends GhidraScript {
    @Override
    public void run() throws Exception {
        String out = getScriptArgs().length > 0 ? getScriptArgs()[0] : "phase0.txt";
        PrintWriter w = new PrintWriter(new FileWriter(out));

        w.println("== Memory blocks");
        for (MemoryBlock b : currentProgram.getMemory().getBlocks())
            w.printf("%-10s %s size=%d exec=%b%n", b.getName(), b.getStart(), b.getSize(), b.isExecute());

        w.println("== Imports per DLL");
        Map<String, List<String>> imports = new TreeMap<>();
        for (Symbol s : currentProgram.getSymbolTable().getExternalSymbols()) {
            String lib = s.getParentNamespace().getName();
            imports.computeIfAbsent(lib, k -> new ArrayList<>()).add(s.getName());
        }
        for (Map.Entry<String, List<String>> e : imports.entrySet()) {
            w.printf("%s (%d): %s%n", e.getKey(), e.getValue().size(), String.join(" ", e.getValue()));
        }

        w.println("== Functions");
        FunctionManager fm = currentProgram.getFunctionManager();
        int n = 0, thunks = 0;
        long total = 0;
        int[] buckets = new int[6]; // <32, <128, <512, <2048, <8192, >=8192 bytes
        for (Function f : fm.getFunctions(true)) {
            if (f.isThunk()) { thunks++; continue; }
            n++;
            long sz = f.getBody().getNumAddresses();
            total += sz;
            int i = sz < 32 ? 0 : sz < 128 ? 1 : sz < 512 ? 2 : sz < 2048 ? 3 : sz < 8192 ? 4 : 5;
            buckets[i]++;
        }
        w.printf("functions=%d thunks=%d code_bytes=%d%n", n, thunks, total);
        w.printf("size buckets <32:%d <128:%d <512:%d <2K:%d <8K:%d >=8K:%d%n",
            buckets[0], buckets[1], buckets[2], buckets[3], buckets[4], buckets[5]);

        w.println("== RTTI / class names");
        Set<String> classes = new TreeSet<>();
        SymbolIterator it = currentProgram.getSymbolTable().getAllSymbols(true);
        while (it.hasNext()) {
            Symbol s = it.next();
            if (s.getName().startsWith("RTTI_Type_Descriptor") || s.getName().equals("vftable"))
                classes.add(s.getParentNamespace().getName(true));
        }
        w.printf("classes=%d%n", classes.size());
        for (String c : classes) w.println(c);
        w.close();
    }
}
