#!/usr/bin/env python3
"""Run shipping process-set observer over bounded proc fixtures and real host proc."""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile,time
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
 @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(Map<String,Object> v){return (List<Map<String,Object>>)v.get("processes");}
 static long n(Map<String,Object> v,String key){return ((Number)v.get(key)).longValue();}
 static Map<String,Object> sample(ProcessSetMemory observer,Path root,boolean server){observer.sample(root,1000,10,server,()->100L,123456L);return observer.snapshot();}
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
  Map<String,Object> bounded=sample(observer,root,true);need(n(bounded,"process_count")==64&&!Boolean.TRUE.equals(bounded.get("scan_complete"))&&bounded.get("total_pss_bytes")==null);
  need(n(bounded,"omitted_same_uid_processes")>0&&n(bounded,"wine_processes")>=1&&n(bounded,"postgresql_processes")>=1);
  need(rows(bounded).stream().anyMatch(r->Long.valueOf(120).equals(r.get("pid")))&&rows(bounded).stream().anyMatch(r->Long.valueOf(121).equals(r.get("pid"))));
  need(rows(bounded).size()==64&&rows(bounded).get(0).get("pid").equals(10L));
  Map<String,Object> exported=observer.exportSnapshot();need(((List<?>)exported.get("process_row_fields")).size()==8&&((List<?>)exported.get("processes")).size()==64);
  need(((List<?>)((List<?>)exported.get("processes")).get(0)).get(0).equals(10L));
  AtomicInteger clock=new AtomicInteger();observer.sample(root,1000,10,true,()->clock.getAndAdd(2000),123456L);need(!Boolean.TRUE.equals(observer.snapshot().get("scan_complete")));
  ProcessSetMemory missing=new ProcessSetMemory();Map<String,Object> absent=sample(missing,root.resolve("absent"),true);need(absent.get("total_pss_bytes")==null&&absent.get("total_rss_bytes")==null);
  // Actual host proc read validates deployed parser/UID handling, not Android visibility.
  String ownStat=new String(Files.readAllBytes(Paths.get("/proc/self/stat")),StandardCharsets.US_ASCII);long pid=Long.parseLong(ownStat.substring(0,ownStat.indexOf(' ')));
  String self=new String(Files.readAllBytes(Paths.get("/proc/self/status")),StandardCharsets.US_ASCII);long uid=-1;for(String line:self.split("\n"))if(line.startsWith("Uid:"))uid=Long.parseLong(line.substring(4).trim().split("\\s+")[0]);
  ProcessSetMemory live=new ProcessSetMemory();live.sample(Paths.get("/proc"),uid,pid,false,()->System.nanoTime()/1000000,System.currentTimeMillis());
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
  proc=out/'proc';proc.mkdir()
  build=subprocess.run(['java','com.sun.tools.javac.Main','--release','8','-d',str(out),str(SOURCE),str(test)],capture_output=True,text=True)
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
  receipt=json.loads(run.stdout);receipt['source_sha256']=hashlib.sha256(SOURCE.read_bytes()).hexdigest();print(json.dumps(receipt))
if __name__=='__main__':main()
