// @category COH.NativeInvestigation
// Static, targeted continuation of the saved partial project; never executes Game.
import ghidra.app.util.headless.HeadlessScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.Address;
import com.google.gson.GsonBuilder;
import java.nio.file.*;
import java.util.*;
public class CoHPhase2Seams extends HeadlessScript {
  public void run() throws Exception {
    String pin="5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b";
    if(!pin.equals(currentProgram.getExecutableSHA256()))throw new IllegalStateException("Wrong Game producer");
    Map<String,Object> out=new LinkedHashMap<>();out.put("producer","direct supervised Ghidra; reused partial project, no whole-program analysis");
    out.put("sha256",pin);out.put("target_executed",false);out.put("matching_pdb",false);
    String[] targets={"0062e640","005ff490","008f6790","0067bc40"};
    List<Map<String,Object>> results=new ArrayList<>();DecompInterface decompiler=new DecompInterface();decompiler.openProgram(currentProgram);
    try { for(String target:targets){
      monitor.checkCancelled();Address a=toAddr(target);Function f=currentProgram.getFunctionManager().getFunctionAt(a);
      boolean created=false;
      if(f==null){disassemble(a);f=createFunction(a,null);created=f!=null;}
      Map<String,Object> item=new LinkedHashMap<>();item.put("requested_entry",target);item.put("created_analysis_only",created);
      if(f==null){item.put("unresolved",true);results.add(item);continue;}
      item.put("name",f.getName());item.put("entry",f.getEntryPoint().toString());item.put("body_bytes",f.getBody().getNumAddresses());
      DecompileResults d=decompiler.decompileFunction(f,10,monitor);item.put("decompile_completed",d.decompileCompleted());item.put("error",d.getErrorMessage());
      item.put("pseudocode",d.getDecompiledFunction()==null?null:d.getDecompiledFunction().getC());
      List<Map<String,String>> instructions=new ArrayList<>();InstructionIterator iterator=currentProgram.getListing().getInstructions(f.getBody(),true);
      int n=0;while(iterator.hasNext() && n++<1200){Instruction i=iterator.next();Map<String,String> row=new LinkedHashMap<>();row.put("address",i.getAddress().toString());row.put("instruction",i.toString());instructions.add(row);}
      item.put("instructions",instructions);item.put("instructions_truncated",iterator.hasNext());
      List<Map<String,String>> callees=new ArrayList<>();for(Function callee:f.getCalledFunctions(monitor)){Map<String,String> row=new LinkedHashMap<>();row.put("entry",callee.getEntryPoint().toString());row.put("name",callee.getName(true));callees.add(row);}item.put("callees",callees);
      results.add(item);
    }}finally{decompiler.dispose();}
    out.put("functions",results);out.put("limits","Partial coverage. Recovered prototypes/control flow and source-name correspondence remain inferences; no runtime workload/Thor test.");
    Files.writeString(Path.of(getScriptArgs()[0]),new GsonBuilder().setPrettyPrinting().create().toJson(out));
  }
}
