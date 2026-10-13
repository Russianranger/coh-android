// @category COH.NativeInvestigation
// Read-only targeted discovery in recovered project; no import/autoanalysis/target execution.
import ghidra.app.util.headless.HeadlessScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import com.google.gson.GsonBuilder;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
public class CoHPhase8CharacterSeams extends HeadlessScript {
 private LinkedHashMap<String,Function> selected=new LinkedHashMap<>();
 private List<Map<String,Object>> refs(Address address,int depth) throws Exception {
  List<Map<String,Object>> result=new ArrayList<>();ReferenceIterator it=currentProgram.getReferenceManager().getReferencesTo(address);int count=0;
  while(it.hasNext()&&count++<100){monitor.checkCancelled();Reference ref=it.next();Map<String,Object> r=new LinkedHashMap<>();r.put("from",ref.getFromAddress().toString());r.put("to",ref.getToAddress().toString());r.put("type",ref.getReferenceType().toString());
   Instruction i=currentProgram.getListing().getInstructionAt(ref.getFromAddress());if(i!=null)r.put("instruction",i.toString());Function f=currentProgram.getFunctionManager().getFunctionContaining(ref.getFromAddress());
   if(f!=null){r.put("function",f.getName(true));r.put("entry",f.getEntryPoint().toString());r.put("thunk",f.isThunk());
    if(!f.isExternal()&&!f.isThunk()&&selected.size()<3)selected.put(f.getEntryPoint().toString(),f);
   }
   if(depth>0)r.put("incoming_to_reference",refs(ref.getFromAddress(),depth-1));result.add(r);
  }return result;
 }
 public void run() throws Exception {
  String pin="5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b";if(!pin.equals(currentProgram.getExecutableSHA256()))throw new IllegalStateException("Wrong reference Game");
  Map<String,Object> out=new LinkedHashMap<>();out.put("producer","Direct supervised Ghidra12.1.4 using recovered REA-assisted partial project");out.put("target_sha256",pin);out.put("target_executed",false);out.put("autoanalysis",false);out.put("database_modified",false);out.put("whole_program_coverage","partial inherited checkpoint; no PDB");
  List<Map<String,Object>> symbols=new ArrayList<>();SymbolIterator sit=currentProgram.getSymbolTable().getAllSymbols(true);
  while(sit.hasNext()){Symbol s=sit.next();String n=s.getName(true);if(false){
   Map<String,Object> r=new LinkedHashMap<>();r.put("name",n);r.put("address",s.getAddress().toString());r.put("references",refs(s.getAddress(),2));symbols.add(r);
  }}out.put("retained_imports_unused",symbols);
  List<Map<String,Object>> anchors=new ArrayList<>();String[] patterns={"costume_client.c","seqgraphics.c","seqskeleton.c","seqanimate.c","model.c","rt_tricks.c","rt_model.c","rt_boned.c","GEO_Head_Wretch","GEO_Hair_Jack","Collar2x"};
  for(String p:patterns){Map<String,Object> r=new LinkedHashMap<>();r.put("pattern",p);List<Map<String,Object>> hits=new ArrayList<>();byte[] pattern=p.getBytes(StandardCharsets.US_ASCII);
   for(MemoryBlock block:currentProgram.getMemory().getBlocks()){if(!block.isInitialized())continue;Address start=block.getStart();int count=0;
    while(start.compareTo(block.getEnd())<=0&&count++<10){Address a=currentProgram.getMemory().findBytes(start,block.getEnd(),pattern,null,true,monitor);if(a==null)break;
     Map<String,Object> hit=new LinkedHashMap<>();hit.put("address",a.toString());hit.put("memory_block",block.getName());hit.put("references",refs(a,0));hits.add(hit);start=a.add(1);
    }
   }r.put("hits",hits);anchors.add(r);
  }out.put("character_anchors",anchors);
  DecompInterface dec=new DecompInterface();dec.openProgram(currentProgram);List<Map<String,Object>> functions=new ArrayList<>();
  try{for(Function f:selected.values()){monitor.checkCancelled();Map<String,Object> r=new LinkedHashMap<>();r.put("entry",f.getEntryPoint().toString());r.put("name",f.getName(true));r.put("body_bytes",f.getBody().getNumAddresses());DecompileResults d=dec.decompileFunction(f,10,monitor);r.put("decompile_completed",d.decompileCompleted());r.put("decompile_error",d.getErrorMessage());r.put("pseudocode",d.getDecompiledFunction()==null?null:d.getDecompiledFunction().getC());
   List<Map<String,Object>> instructions=new ArrayList<>();InstructionIterator ii=currentProgram.getListing().getInstructions(f.getBody(),true);int n=0;while(ii.hasNext()&&n++<800){Instruction ins=ii.next();Map<String,Object> row=new LinkedHashMap<>();row.put("address",ins.getAddress().toString());row.put("instruction",ins.toString());instructions.add(row);}r.put("instructions",instructions);r.put("instructions_truncated",ii.hasNext());functions.add(r);
  }}finally{dec.dispose();}out.put("selected_functions",functions);out.put("limitations",List.of("Raw character-related anchors identify candidates only; no source function identity is assigned.","No source-function name is assigned without corroboration.","References depend on inherited partial database; empty search results do not establish absence of behavior.","Maximum3 non-thunk functions,10s per decompilation,800 retained instructions each; external process deadline90s."));
  Files.writeString(Path.of(getScriptArgs()[0]),new GsonBuilder().setPrettyPrinting().serializeNulls().create().toJson(out));println("Saved read-only Phase8 character seam discovery");
 }
}
