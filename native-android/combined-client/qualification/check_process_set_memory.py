#!/usr/bin/env python3
"""Run shipping process-set observer over bounded proc fixtures and real host proc."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,tempfile,time
SOURCE=Path(__file__).resolve().parents[1]/'app/src/main/java/org/coh/nativecombined/ProcessSetMemory.java'
HARNESS=r'''
package org.coh.nativecombined;
import java.nio.file.*;import java.nio.charset.StandardCharsets;import java.util.*;import java.util.concurrent.atomic.AtomicInteger;
public final class ProcessSetMemoryTest {
 static int checks;static void need(boolean b){checks++;if(!b)throw new AssertionError("process memory check "+checks);}
 static void write(Path p,String value)throws Exception{Files.createDirectories(p.getParent());Files.write(p,value.getBytes(StandardCharsets.US_ASCII));}
 static String stat(int pid,long ticks){String[] fields=new String[22];Arrays.fill(fields,"0");fields[0]="S";fields[19]=Long.toString(ticks);return pid+" (name with ) bracket) "+String.join(" ",fields)+"\n";}
 static void process(Path root,int pid,int uid,String name,String cmd,int rss,int pss)throws Exception{
  Path p=root.resolve(""+pid);write(p.resolve("status"),"Name:\t"+name+"\nUid:\t"+uid+"\t"+uid+"\t"+uid+"\t"+uid+"\nVmRSS:\t"+rss+" kB\n");
  write(p.resolve("stat"),stat(pid,1000+pid));write(p.resolve("cmdline"),cmd);write(p.resolve("smaps_rollup"),"Pss:\t"+pss+" kB\n");
 }
 static String escape(Path path){return path.toString().replace("\\","\\134").replace(" ","\\040");}
 static String file(Path path,int cap)throws Exception{return new String(Files.readAllBytes(path),StandardCharsets.US_ASCII);}
 static Map<String,Object> cgroup(Path proc){return AppCgroupMemory.observe(proc,1000,(path,cap)->new String(Files.readAllBytes(path),StandardCharsets.US_ASCII));}
 static void cgroups(Path proc)throws Exception{
  Path cg=proc.getParent().resolve("cg space");Path current=cg.resolve("apps/uid_1000/memory.current");write(current,"4096\n");
  String member="0::/apps/uid_1000/pid_10\n",mount="1 0 0:1 / "+escape(cg)+" rw - cgroup2 cgroup rw\n";
  write(proc.resolve("self/cgroup"),member);write(proc.resolve("self/mountinfo"),mount);
  Map<String,Object> v=cgroup(proc);need("observed".equals(v.get("status"))&&n(v,"charge_bytes")==4096&&Boolean.TRUE.equals(v.get("hierarchical_accounting")));
  need(current.toString().equals(v.get("counter_path"))&&"v2_hierarchical_charge_bytes".equals(v.get("counter_semantics")));
  for(String invalid:new String[]{"max","-1","9223372036854775808","12 kB"}){write(current,invalid);need(cgroup(proc).get("charge_bytes")==null);}
  write(current,"0\n");need(n(cgroup(proc),"charge_bytes")==0);write(current,"4096\n");
  AtomicInteger membershipReads=new AtomicInteger();Map<String,Object> moved=AppCgroupMemory.observe(proc,1000,(path,cap)->{
   if(path.equals(proc.resolve("self/cgroup"))&&membershipReads.incrementAndGet()>1)return "0::/apps/uid_1001/pid_10\n";
   return new String(Files.readAllBytes(path),StandardCharsets.US_ASCII);
  });need("CGROUP_MEMBERSHIP_CHANGED".equals(moved.get("reason"))&&moved.get("charge_bytes")==null);
  AtomicInteger mountReads=new AtomicInteger();Map<String,Object> remounted=AppCgroupMemory.observe(proc,1000,(path,cap)->{
   if(path.equals(proc.resolve("self/mountinfo"))&&mountReads.incrementAndGet()>1)return mount.replace("1 0 0:1","2 0 0:2");
   return new String(Files.readAllBytes(path),StandardCharsets.US_ASCII);
  });need("CGROUP_MOUNT_CHANGED".equals(remounted.get("reason"))&&remounted.get("charge_bytes")==null);
  Files.delete(current);Files.createSymbolicLink(current,cg.resolve("real-counter"));write(cg.resolve("real-counter"),"7000\n");
  need("CGROUP_PATH_ALIAS_OR_LIMIT".equals(cgroup(proc).get("reason"))&&cgroup(proc).get("charge_bytes")==null);Files.delete(current);write(current,"4096\n");
  write(proc.resolve("self/cgroup"),"0::/apps/uid_1001/pid_10\n");need("NO_APP_UID_MEMORY_CGROUP".equals(cgroup(proc).get("reason")));
  write(proc.resolve("self/cgroup"),member);write(proc.resolve("self/mountinfo"),"1 0 0:1 /apps/uid_1000/pid_10 "+escape(cg)+" rw - cgroup2 cgroup rw\n");need(cgroup(proc).get("charge_bytes")==null);
  Path usage=cg.resolve("uid_1000/memory.usage_in_bytes");write(usage,"8192\n");write(cg.resolve("uid_1000/memory.use_hierarchy"),"0\n");
  write(proc.resolve("self/cgroup"),"5:cpu,memory:/apps/uid_1000/pid_10\n");write(proc.resolve("self/mountinfo"),"1 0 0:1 /apps "+escape(cg)+" rw - cgroup memory rw,memory\n");
  v=cgroup(proc);need(n(v,"charge_bytes")==8192&&Boolean.FALSE.equals(v.get("hierarchical_accounting"))&&"v1_approximate_charge_bytes".equals(v.get("counter_semantics")));
  write(cg.resolve("uid_1000/memory.use_hierarchy"),"1\n");need(Boolean.TRUE.equals(cgroup(proc).get("hierarchical_accounting")));
  Map<String,Object> oversized=AppCgroupMemory.observe(proc,1000,(path,cap)->new String(new char[cap+1]));need(oversized.get("charge_bytes")==null);
  AtomicInteger reads=new AtomicInteger();ProcessSetMemory first=new ProcessSetMemory((path,cap)->{
   if(reads.getAndIncrement()==0)need(path.equals(proc.resolve("self/cgroup")));
   return new String(Files.readAllBytes(path),StandardCharsets.US_ASCII);
  });Map<String,Object> measured=sample(first,proc,true);need(n(total(measured),"process_count")==75&&n(measured,"total_pss_bytes")==86016);
 }
 @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(Map<String,Object> v){return (List<Map<String,Object>>)v.get("processes");}
 static long n(Map<String,Object> v,String key){return ((Number)v.get(key)).longValue();}
 @SuppressWarnings("unchecked") static Map<String,Object> aggregate(Map<String,Object> v){return (Map<String,Object>)v.get("aggregation");}
 @SuppressWarnings("unchecked") static Map<String,Object> total(Map<String,Object> v){return (Map<String,Object>)aggregate(v).get("total");}
 static Map<String,Object> sample(ProcessSetMemory observer,Path root,boolean server){observer.sample(root,1000,10,server,()->100L,123456L);return observer.snapshot();}
 @SuppressWarnings("unchecked") static List<List<Object>> identities(Map<String,Object> v){return (List<List<Object>>)v.get("process_identities");}
 static List<Object> identity(Map<String,Object> v,long pid){return identities(v).stream().filter(r->Long.valueOf(pid).equals(r.get(0))).findFirst().get();}
 static String json(Object value){
  if(value==null)return "null";if(value instanceof Number||value instanceof Boolean)return value.toString();
  if(value instanceof Map){StringJoiner out=new StringJoiner(",","{","}");for(Object item:((Map<?,?>)value).entrySet()){Map.Entry<?,?> e=(Map.Entry<?,?>)item;out.add(json(e.getKey())+":"+json(e.getValue()));}return out.toString();}
  if(value instanceof List){StringJoiner out=new StringJoiner(",","[","]");for(Object item:(List<?>)value)out.add(json(item));return out.toString();}
  StringBuilder out=new StringBuilder("\"");for(char c:value.toString().toCharArray()){if(c=='\\'||c=='\"')out.append('\\');if(c<32)out.append(String.format("\\u%04x",(int)c));else out.append(c);}return out.append('"').toString();
 }
 static void executable(Path proc,int pid,String path)throws Exception{Files.createSymbolicLink(proc.resolve(pid+"/exe"),Paths.get(path));}
 static void identities(Path root)throws Exception{
  Path proc=root.resolveSibling("identity-proc");process(proc,10,1000,"coh.nativecombined","app_process",4,2);
  for(int i=100;i<181;i++)process(proc,i,1000,"postgres","postgres",1,1);
  for(int i=200;i<270;i++)process(proc,i,1000,"MapServer.exe","wine\0MapServer.exe",2,1);
  String chain="/runtime/FEXInterpreter\0/opt/wine/bin/wine64\0C:\\coh\\MapServer.exe\0--password=PRIVATE_EQUALS\0--cookie\0PRIVATE_NEXT\0-pPRIVATE_ATTACHED\0/connect:PRIVATE_URI\0--db\0postgresql://user:PRIVATE_URL@host/db\0-c\0echo PRIVATE_SHELL";
  process(proc,9000,1000,"FEXInterpreter",chain,6000,5000);executable(proc,9000,"/runtime/FEXInterpreter");
  process(proc,9001,1000,"DbServer.exe","wine\0DbServer.exe\0-auth\0PRIVATE_AUTH",4000,3000);executable(proc,9001,"/runtime/wine64");
  process(proc,9002,1000,"FEXInterpreter","FEXInterpreter\0wine64\0other.exe",2000000,1785470);executable(proc,9002,"/runtime/FEXInterpreter");
  process(proc,9003,1000,"wineboot.exe","wineboot.exe\0--secret\0PRIVATE_BOOT",2500000,20);executable(proc,9003,"/runtime/wine64");
  ProcessSetMemory observer=new ProcessSetMemory();Map<String,Object> measured=sample(observer,proc,true),exported=observer.exportSnapshot();
  need(n(total(measured),"process_count")==156&&Boolean.TRUE.equals(total(measured).get("pss_complete"))&&n(measured,"process_count")==64);
  need(n(exported,"process_count")==32&&identities(exported).size()==4&&n(exported,"wine_identity_rows_omitted")==70);
  for(long pid:new long[]{9000,9001,9002,9003}){need(rows(measured).stream().anyMatch(r->Long.valueOf(pid).equals(r.get("pid"))));need(identity(exported,pid).get(1).equals(1000L+pid));}
  need(n(exported,"total_pss_bytes")==n(measured,"total_pss_bytes")&&n(exported,"detail_rows_omitted")==124);
  List<Object> map=identity(exported,9000);need(map.get(2).equals("FEXInterpreter")&&map.get(3).equals("/runtime/FEXInterpreter"));
  @SuppressWarnings("unchecked") List<String> argv=(List<String>)map.get(4);
  need(argv.subList(0,3).equals(Arrays.asList("/runtime/FEXInterpreter","/opt/wine/bin/wine64","C:\\coh\\MapServer.exe"))&&argv.contains("--cookie")&&(((Integer)map.get(5))&128)!=0);
  need(!json(exported).contains("PRIVATE_")&&((List<?>)exported.get("process_row_fields")).size()==8);
  // Long original cmdline is a bounded prefix, not a failed/lost executable.
  write(proc.resolve("9000/cmdline"),chain+"\0"+String.join("",Collections.nCopies(5000,"x")));sample(observer,proc,true);map=identity(observer.exportSnapshot(),9000);
  need((((Integer)map.get(5))&4)!=0&&map.get(3).equals("/runtime/FEXInterpreter")&&!json(observer.exportSnapshot()).contains("PRIVATE_"));
  // Worst bounded strings, including JSON escapes, retain the same32 rows.
  for(int pid:new int[]{9000,9001,9002,9003}){
   String state=file(proc.resolve(pid+"/status"),16384);write(proc.resolve(pid+"/status"),"Name:\t"+String.join("",Collections.nCopies(100,"\""))+state.substring(state.indexOf('\n')));
   Files.delete(proc.resolve(pid+"/exe"));executable(proc,pid,"/"+String.join("",Collections.nCopies(220,"\\\"")));
   String program=pid==9000?"MapServer.exe":pid==9001?"DbServer.exe":pid==9002?"other.exe":"wineboot.exe";
   String prefix="/"+String.join("",Collections.nCopies(100,"\\\""));
   write(proc.resolve(pid+"/cmdline"),prefix+"/FEXInterpreter\0"+prefix+"/FEXLoader\0"+prefix+"/wine64\0"+prefix+"/"+program);
  }
  sample(observer,proc,true);Map<String,Object> worst=observer.exportSnapshot();need(identities(worst).size()==4&&n(worst,"total_pss_bytes")==n(measured,"total_pss_bytes"));
  for(List<Object> row:identities(worst)){need(((String)row.get(3)).length()<=192&&(((Integer)row.get(5))&2)!=0);@SuppressWarnings("unchecked") List<String> args=(List<String>)row.get(4);need(args.size()<=16&&args.stream().mapToInt(String::length).sum()<=384);}
  Files.write(root.resolveSibling("identity-export.json"),json(worst).getBytes(StandardCharsets.UTF_8));
  PhaseMemoryDiagnostics phases=new PhaseMemoryDiagnostics();for(PhaseMemoryDiagnostics.Phase p:PhaseMemoryDiagnostics.Phase.values())phases.record(p,Long.MAX_VALUE,Long.MAX_VALUE,
   new ServerMemoryPolicy.Sample(Long.MAX_VALUE,Long.MAX_VALUE,Long.MAX_VALUE/2,false,Long.MAX_VALUE/2,Long.MAX_VALUE),new PhaseMemoryDiagnostics.ProcessSample(Long.MAX_VALUE,Long.MAX_VALUE,"proc_self_smaps_rollup","proc_self_smaps_rollup"));
  Map<String,Object> phase=phases.snapshot();phase.put("same_uid_process_set",worst);phase.put("sampler_failures",Long.MAX_VALUE);phase.put("snapshot_elapsed_ms",Long.MAX_VALUE);phase.put("latest_sample_age_ms",0);
  Files.write(root.resolveSibling("identity-phase.json"),json(phase).getBytes(StandardCharsets.UTF_8));
  // Exercise the production complete-memory emitter, not a hand-trimmed map.
  // The Android JSON formatting shim is independently compared with Python's
  // indent2 writer below; OS/JNI services remain explicit host test doubles.
  java.lang.reflect.Field field=ProcessSetMemory.class.getDeclaredField("latest");field.setAccessible(true);
  @SuppressWarnings("unchecked") Map<String,Object> live=(Map<String,Object>)field.get(observer);
  @SuppressWarnings("unchecked") Map<String,Object> cg=(Map<String,Object>)live.get("app_uid_cgroup");
  String part=String.join("",Collections.nCopies(120,"\\\"")),point="/"+part+"/"+part,sourceRoot="/"+part+"/"+part;
  cg.put("status","observed");cg.put("reason","");cg.put("charge_bytes",Long.MAX_VALUE);cg.put("hierarchical_accounting",true);cg.put("counter","memory.current");
  cg.put("counter_path",point+"/uid_1000/memory.current");cg.put("membership_path",sourceRoot+"/uid_1000/pid_10");cg.put("mount_point",point);cg.put("mount_root",sourceRoot);cg.put("counter_semantics","v2_hierarchical_charge_bytes");
  @SuppressWarnings("unchecked") Map<String,Object> cats=(Map<String,Object>)aggregate(live).get("categories");
  long base=(1L<<50)-1000;
  for(Object raw:cats.values()){@SuppressWarnings("unchecked") Map<String,Object> category=(Map<String,Object>)raw;for(String m:new String[]{"rss","pss"}){category.put(m+"_bytes",n(category,"process_count")*base);category.put("observed_"+m+"_bytes",n(category,"process_count")*base);}}
  for(Map<String,Object> row:rows(live)){
   long pid=n(row,"pid"),pss=pid==9000?(1L<<50)-4:pid==9001?(1L<<50)-5:pid==9002?1L<<50:pid==9003?(1L<<50)-6:base,rss=pid==9003?1L<<50:pid==9002?(1L<<50)-1:base;
   row.put("rss_bytes",rss);row.put("pss_bytes",pss);row.put("start_ticks",1L<<50);
   @SuppressWarnings("unchecked") Map<String,Object> category=(Map<String,Object>)cats.get(row.get("role"));for(String m:new String[]{"rss","pss"}){long delta=n(row,m+"_bytes")-base;category.put(m+"_bytes",n(category,m+"_bytes")+delta);category.put("observed_"+m+"_bytes",n(category,"observed_"+m+"_bytes")+delta);}
  }
  for(String m:new String[]{"rss","pss"}){long bytes=0;for(Object raw:cats.values()){@SuppressWarnings("unchecked") Map<String,Object> category=(Map<String,Object>)raw;bytes+=n(category,m+"_bytes");}total(live).put(m+"_bytes",bytes);total(live).put("observed_"+m+"_bytes",bytes);live.put("total_"+m+"_bytes",bytes);live.put("observed_"+m+"_sum_bytes",bytes);live.put("sampled_peak_total_"+m+"_bytes",bytes);}
  live.put("begin_elapsed_ms",Long.MAX_VALUE);live.put("end_elapsed_ms",Long.MAX_VALUE);live.put("sample_window_ms",0L);live.put("samples",Long.MAX_VALUE);
  Map<String,Object> pressure=new LinkedHashMap<>();pressure.put("source","Android onTrimMemory/onLowMemory callbacks");pressure.put("trim_callbacks",Long.MAX_VALUE);pressure.put("low_memory_callbacks",Long.MAX_VALUE);pressure.put("last_trim_level",100);pressure.put("last_callback_elapsed_ms",Long.MAX_VALUE);pressure.put("callback_is_oom_kill_proof",false);phase.put("android_memory_callbacks",pressure);
  org.json.JSONObject emitted=MemoryTelemetry.boundedSnapshot(phase,observer,Long.MAX_VALUE);String emittedText=emitted.toString(2);
  @SuppressWarnings("unchecked") Map<String,Object> retained=(Map<String,Object>)emitted.toMap().get("same_uid_process_set");
  need(emittedText.getBytes(StandardCharsets.UTF_8).length<24576&&identities(retained).size()==4&&Boolean.TRUE.equals(emitted.toMap().get("process_detail_budget_omission")));
  need(n(total(retained),"process_count")==156&&n(retained,"total_pss_bytes")==n(live,"total_pss_bytes")&&rows(observer.snapshot()).size()==64);
  for(long pid:new long[]{9000,9001,9002,9003})need(identity(retained,pid).get(1).equals(1L<<50));
  Files.write(root.resolveSibling("identity-bounded-phase.json"),emittedText.getBytes(StandardCharsets.UTF_8));
  Path mini=root.resolveSibling("identity-mini");process(mini,10,1000,"app","app_process",4,2);process(mini,20,1000,"MapServer.exe","wine\0MapServer.exe",8,4);process(mini,30,1000,"postgres","postgres",12,6);
  ProcessSetMemory denied=new ProcessSetMemory(new ProcessSetMemory.ProcReader(){
   public String read(Path p,int cap)throws java.io.IOException{if(p.equals(mini.resolve("20/cmdline")))throw new AccessDeniedException(p.toString());return new String(Files.readAllBytes(p),StandardCharsets.US_ASCII);}
   public String link(Path p)throws java.io.IOException{throw new AccessDeniedException(p.toString());}
  });sample(denied,mini,true);Map<String,Object> noAccess=denied.exportSnapshot();List<Object> absent=identity(noAccess,20);
  need(absent.get(3)==null&&absent.get(4)==null&&(((Integer)absent.get(5))&80)==80&&noAccess.get("total_pss_bytes")!=null);
  AtomicInteger links=new AtomicInteger();ProcessSetMemory execChanged=new ProcessSetMemory(new ProcessSetMemory.ProcReader(){
   public String read(Path p,int cap)throws java.io.IOException{return new String(Files.readAllBytes(p),StandardCharsets.US_ASCII);}
   public String link(Path p)throws java.io.IOException{return p.equals(mini.resolve("20/exe"))?(links.incrementAndGet()==1?"/runtime/wine64":"/runtime/replaced"):"/runtime/other";}
  });sample(execChanged,mini,true);List<Object> moved=identity(execChanged.exportSnapshot(),20);need(moved.get(2).equals("")&&moved.get(3)==null&&moved.get(4)==null&&(((Integer)moved.get(5))&1024)!=0);
  AtomicInteger stats=new AtomicInteger();ProcessSetMemory reused=new ProcessSetMemory((p,cap)->p.equals(mini.resolve("20/stat"))&&stats.incrementAndGet()==2?stat(20,99999):new String(Files.readAllBytes(p),StandardCharsets.US_ASCII));
  sample(reused,mini,true);need(identities(reused.exportSnapshot()).isEmpty());
 }
 public static void main(String[] args)throws Exception{
  Path root=Paths.get(args[0]);process(root,10,1000,"coh.nativecombined","app_process",4,2);
  process(root,20,1000,"MapServer.exe","/opt/wine/bin/wine\0MapServer.exe\0--db\0postgres",8,4);
  process(root,30,1000,"FEXInterpreter","/bin/FEXInterpreter\0/opt/coh/pgsql/bin/postgres\0--db",12,6);
  process(root,40,2000,"postgres","postgres",1000,1000);
  ProcessSetMemory observer=new ProcessSetMemory();need(observer.snapshot().get("total_pss_bytes")==null);
  Map<String,Object> first=sample(observer,root,true);need(n(first,"process_count")==3&&n(first,"total_rss_bytes")==24576&&n(first,"total_pss_bytes")==12288);
  need(n(first,"wine_processes")==1&&n(first,"postgresql_processes")==1&&Boolean.TRUE.equals(first.get("expected_roles_observed")));
  need(Boolean.FALSE.equals(first.get("atomic_snapshot"))&&Boolean.TRUE.equals(first.get("rss_sum_includes_repeated_shared_pages")));
  need(rows(first).stream().map(r->r.get("pid")).distinct().count()==3);
  rows(first).get(0).put("pss_bytes",999L);need(n(rows(observer.snapshot()).get(0),"pss_bytes")==2048);
  Files.delete(root.resolve("20/smaps_rollup"));Map<String,Object> partial=sample(observer,root,true);
  need(partial.get("total_pss_bytes")==null&&n(partial,"total_rss_bytes")==24576&&n(partial,"observed_pss_sum_bytes")==8192);
  need(n(partial,"sampled_peak_total_pss_bytes")==12288&&n(partial,"incomplete_process_metrics")==1);
  write(root.resolve("20/smaps_rollup"),"Pss:\t0 kB\n");need(n(sample(observer,root,true),"total_pss_bytes")==8192);
  write(root.resolve("20/smaps_rollup"),"Pss:\t-1 kB\n");need(sample(observer,root,true).get("total_pss_bytes")==null);
  write(root.resolve("20/smaps_rollup"),"Pss:\t999999999999999999999999 kB\n");need(sample(observer,root,true).get("total_pss_bytes")==null);
  write(root.resolve("20/smaps_rollup"),"Pss:\t4 MB\n");need(sample(observer,root,true).get("total_pss_bytes")==null);
  write(root.resolve("20/smaps_rollup"),"Pss:\t4 kB\n");
  // A stable zombie has no address space. This is explicit stat-derived
  // zero, not an invented successful smaps read for an inaccessible live VM.
  process(root,45,1000,"winedevice.exe","",0,0);write(root.resolve("45/status"),"Name:\twinedevice.exe\nUid:\t1000\t1000\t1000\t1000\n");
  write(root.resolve("45/stat"),stat(45,1045).replace(") S ",") Z "));Files.delete(root.resolve("45/smaps_rollup"));
  Map<String,Object> zombie=sample(observer,root,true);Map<String,Object> z=rows(zombie).stream().filter(r->Long.valueOf(45).equals(r.get("pid"))).findFirst().get();
  need(Boolean.TRUE.equals(z.get("zombie_no_address_space"))&&n(z,"rss_bytes")==0&&n(z,"pss_bytes")==0&&n(zombie,"total_pss_bytes")==12288);
  write(root.resolve("45/stat"),stat(45,1045));Map<String,Object> liveUnknown=sample(observer,root,true);Map<String,Object> u=rows(liveUnknown).stream().filter(r->Long.valueOf(45).equals(r.get("pid"))).findFirst().get();
  need(u.get("rss_bytes")==null&&u.get("pss_bytes")==null&&((Integer)u.get("unavailable"))==5&&liveUnknown.get("total_pss_bytes")==null);
  for(Path f:Files.newDirectoryStream(root.resolve("45")))Files.delete(f);Files.delete(root.resolve("45"));
  AtomicInteger statReads=new AtomicInteger();ProcessSetMemory reused=new ProcessSetMemory((path,cap)->{
   if(path.equals(root.resolve("20/stat"))&&statReads.incrementAndGet()==2)return stat(20,99999);
   return new String(Files.readAllBytes(path),StandardCharsets.US_ASCII);
  });Map<String,Object> changed=sample(reused,root,true);need(changed.get("total_rss_bytes")==null&&changed.get("total_pss_bytes")==null);
  need(rows(changed).stream().anyMatch(r->Long.valueOf(20).equals(r.get("pid"))&&Boolean.FALSE.equals(r.get("identity_stable"))));
  ProcessSetMemory cap=new ProcessSetMemory((path,limit)->path.endsWith("smaps_rollup")?new String(new char[limit+1]):new String(Files.readAllBytes(path),StandardCharsets.US_ASCII));
  need(sample(cap,root,true).get("total_pss_bytes")==null);
  write(root.resolve("30/status"),"Name:\tunknown\nUid:\t1000\t1000\t1000\t1000\nVmRSS:\t12 kB\n");write(root.resolve("30/cmdline"),"python\0script.py\0postgres");
  Map<String,Object> noPg=sample(observer,root,true);need(Boolean.FALSE.equals(noPg.get("expected_roles_observed"))&&noPg.get("total_pss_bytes")==null);
  need(sample(observer,root,false).get("total_pss_bytes")!=null);
  write(root.resolve("31/status"),"invalid status");need(Boolean.FALSE.equals(sample(observer,root,false).get("scan_complete")));
  Files.delete(root.resolve("31/status"));Files.delete(root.resolve("31"));
  process(root,30,1000,"postgres","postgres",12,6);
  for(int i=50;i<84;i++)process(root,i,1000,"helper","helper",1,1);
  Map<String,Object> expanded=sample(observer,root,true);need(n(expanded,"process_count")==37&&Boolean.TRUE.equals(expanded.get("scan_complete"))&&expanded.get("total_pss_bytes")!=null);
  for(int i=84;i<122;i++)process(root,i,1000,"helper","helper",1,1);
  process(root,120,1000,"MapServer.exe","wine\0MapServer.exe",2,1);process(root,121,1000,"postgres","postgres",2,1);
  Map<String,Object> bounded=sample(observer,root,true);need(n(bounded,"process_count")==64&&Boolean.TRUE.equals(bounded.get("scan_complete"))&&n(bounded,"total_pss_bytes")==86016);
  need(n(bounded,"omitted_same_uid_processes")>0&&n(bounded,"wine_processes")>=1&&n(bounded,"postgresql_processes")>=1);
  need(rows(bounded).stream().anyMatch(r->Long.valueOf(120).equals(r.get("pid")))&&rows(bounded).stream().anyMatch(r->Long.valueOf(121).equals(r.get("pid"))));
  need(rows(bounded).size()==64&&rows(bounded).get(0).get("pid").equals(10L));
  Map<String,Object> exported=observer.exportSnapshot();need(((List<?>)exported.get("process_row_fields")).size()==8&&((List<?>)exported.get("processes")).size()==32);
  need(((List<?>)((List<?>)exported.get("processes")).get(0)).get(0).equals(10L));
  need(n(total(bounded),"process_count")==75&&n(total(bounded),"rss_bytes")==100352&&Boolean.TRUE.equals(total(bounded).get("rss_complete")));
  need(n(exported,"detail_rows_omitted")==43&&n(exported,"process_count")==32&&n(total(exported),"process_count")==75);
  total(exported).put("rss_bytes",-1L);need(n(total(observer.snapshot()),"rss_bytes")==100352);
  // A lost metric outside the optional detail rows still affects the aggregate.
  Files.delete(root.resolve("119/smaps_rollup"));Map<String,Object> allPartial=sample(observer,root,true);
  need(allPartial.get("total_pss_bytes")==null&&n(allPartial,"total_rss_bytes")==100352&&n(total(allPartial),"missing_pss_processes")==1);
  write(root.resolve("119/smaps_rollup"),"Pss:\t1 kB\n");
  Files.createSymbolicLink(root.resolve("999"),root.resolve("20"));Map<String,Object> alias=sample(observer,root,true);
  need(!Boolean.TRUE.equals(alias.get("scan_complete"))&&alias.get("total_pss_bytes")==null&&n(total(alias),"process_count")==75);Files.delete(root.resolve("999"));
  Files.createDirectory(root.resolve("00020"));need(n(total(sample(observer,root,true)),"process_count")==75);Files.delete(root.resolve("00020"));
  ProcessSetMemory.Aggregate overflow=new ProcessSetMemory.Aggregate();Map<String,Object> huge=new LinkedHashMap<>();huge.put("rss_bytes",1L<<50);huge.put("pss_bytes",1L<<50);huge.put("identity_stable",true);
  for(int i=0;i<8192;i++)overflow.accept(huge);Map<String,Object> sum=overflow.snapshot(true,true,true);
  need(sum.get("rss_bytes")==null&&sum.get("pss_bytes")==null&&(((Integer)sum.get("reason_flags"))&8)!=0);

  AtomicInteger clock=new AtomicInteger();observer.sample(root,1000,10,true,()->clock.getAndAdd(2000),123456L);need(!Boolean.TRUE.equals(observer.snapshot().get("scan_complete")));
  ProcessSetMemory missing=new ProcessSetMemory();Map<String,Object> absent=sample(missing,root.resolve("absent"),true);need(absent.get("total_pss_bytes")==null&&absent.get("total_rss_bytes")==null);
  cgroups(root);
  identities(root);
  // Actual host proc read validates deployed parser/UID handling, not Android visibility.
  String ownStat=new String(Files.readAllBytes(Paths.get("/proc/self/stat")),StandardCharsets.US_ASCII);long pid=Long.parseLong(ownStat.substring(0,ownStat.indexOf(' ')));
  String self=new String(Files.readAllBytes(Paths.get("/proc/self/status")),StandardCharsets.US_ASCII);long uid=-1;for(String line:self.split("\n"))if(line.startsWith("Uid:"))uid=Long.parseLong(line.substring(4).trim().split("\\s+")[0]);
  ProcessSetMemory live=new ProcessSetMemory();live.sample(Paths.get("/proc"),uid,pid,false,()->System.nanoTime()/1000000,System.currentTimeMillis());
  Map<String,Object> liveCgroup=AppCgroupMemory.observe(Paths.get("/proc"),uid,(path,readCap)->new String(Files.readAllBytes(path),StandardCharsets.US_ASCII));
  need("observed".equals(liveCgroup.get("status"))?liveCgroup.get("charge_bytes")!=null:liveCgroup.get("charge_bytes")==null);
  Map<String,Object> actual=live.snapshot();if(!Boolean.TRUE.equals(rows(actual).get(0).get("identity_stable")))throw new AssertionError("host self observation "+pid+" "+rows(actual).get(0));need(rows(actual).stream().anyMatch(r->Long.valueOf(pid).equals(r.get("pid"))&&Boolean.TRUE.equals(r.get("identity_stable"))&&r.get("rss_bytes")!=null));
  if(args.length>1){long zombiePid=Long.parseLong(args[1]);Map<String,Object> realZombie=rows(actual).stream().filter(r->Long.valueOf(zombiePid).equals(r.get("pid"))).findFirst().get();
   need(Boolean.TRUE.equals(realZombie.get("zombie_no_address_space"))&&n(realZombie,"rss_bytes")==0&&n(realZombie,"pss_bytes")==0);}
  need(n(actual,"process_count")<=64);System.out.println("{\"passed\":true,\"checks\":"+checks+",\"process_limit\":64,\"host_proc_observed\":true,\"Android_or_Thor_measured\":false,\"authority\":false}");
 }
}
'''
def main():
 with tempfile.TemporaryDirectory(prefix='coh-process-set-') as tmp:
  out=Path(tmp);test=out/'ProcessSetMemoryTest.java';test.write_text(HARNESS)
  spec=importlib.util.spec_from_file_location('memory_identity_worker_stubs',Path(__file__).with_name('check_memory_worker.py'));worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
  stubs=[]
  for name,text in worker.STUBS.items():
   path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);stubs.append(str(path))
  proc=out/'proc';proc.mkdir()
  build=subprocess.run(['java','com.sun.tools.javac.Main','--release','8','-d',str(out),str(SOURCE),str(SOURCE.with_name('AppCgroupMemory.java')),str(SOURCE.with_name('PhaseMemoryDiagnostics.java')),str(SOURCE.with_name('ServerMemoryPolicy.java')),str(SOURCE.with_name('MemoryTelemetry.java')),str(test),*stubs],capture_output=True,text=True)
  if build.returncode:raise RuntimeError(build.stderr)
  reader,writer=os.pipe();child=os.fork()
  if child==0:
   os.close(reader)
   # /proc may expose outer PID numbers in the build sandbox.
   os.write(writer,Path('/proc/self/stat').read_text().split(' ',1)[0].encode());os.close(writer);os._exit(0)
  os.close(writer)
  try:
   with os.fdopen(reader,'rb') as pipe:zombie=int(pipe.read(64))
   for _ in range(100):
    if Path(f'/proc/{zombie}/stat').read_text().split(') ',1)[1].startswith('Z '):break
    time.sleep(.005)
   else:raise RuntimeError('host zombie observation did not settle')
   run=subprocess.run(['java','-Xmx128m','-cp',str(out),'org.coh.nativecombined.ProcessSetMemoryTest',str(proc),str(zombie)],capture_output=True,text=True,timeout=30)
  finally:os.waitpid(child,0)
  if run.returncode:raise RuntimeError(run.stdout+run.stderr)
  exported=json.loads((out/'identity-export.json').read_text())
  assert len(exported['process_identities'])==4 and len(json.dumps(exported,indent=2).encode())<14*1024
  sys.path.insert(0,str(SOURCE.parents[7]/'tools'))
  from fragment_interop_emulator_check import process_set_snapshot
  process_set_snapshot(exported)
  phase=json.loads((out/'identity-phase.json').read_text());phase_bytes=len(json.dumps(phase,indent=2).encode());assert phase_bytes<24*1024,phase_bytes
  text=(out/'identity-bounded-phase.json').read_text();bounded=json.loads(text);group=bounded['same_uid_process_set'];process_set_snapshot(group)
  assert text==json.dumps(bounded,indent=2) and len(text.encode())<24*1024
  assert bounded['process_detail_budget_omission'] and len(group['process_identities'])==4 and len(group['processes'])>=5
  assert group['detail_rows_omitted']==156-len(group['processes']) and group['total_pss_bytes']==156*((1<<50)-1000)+3985
  receipt=json.loads(run.stdout);receipt.update(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),bounded_identity_rows=4,worst_fixture_phase_bytes=phase_bytes,maximum_metadata_phase_bytes=len(text.encode()),maximum_metadata_detail_rows=len(group['processes']),memory_export_limit=24576,JSON_writer='Android-shaped host shim; indent2 independently checked');print(json.dumps(receipt))
if __name__=='__main__':main()
