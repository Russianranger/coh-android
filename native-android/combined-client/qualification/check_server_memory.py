#!/usr/bin/env python3
"""Exercise the production, Android-independent server memory policy."""
from pathlib import Path
import json
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / 'app/src/main/java/org/coh/nativecombined/ServerMemoryPolicy.java'
HARNESS = r'''
package org.coh.nativecombined;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

public final class ServerMemoryTest {
 static final long M=1024L*1024L,G=1024L*M;
 static int checks;
 static void need(boolean value){checks++;if(!value)throw new AssertionError("server memory "+checks);}
 static ServerMemoryPolicy.Sample sample(long available,long total,long threshold,boolean low,long used,long limit){
  return new ServerMemoryPolicy.Sample(available,total,threshold,low,used,limit);
 }
 static ServerMemoryPolicy.Sample healthy(){return sample(8*G,16*G,256*M,false,32*M,256*M);}
 static ServerMemoryPolicy.Sample pressure(){return sample(511*M,16*G,256*M,false,32*M,256*M);}
 static long number(Map<String,Object> map,String key){return ((Number)map.get(key)).longValue();}
 static String reason(ServerMemoryPolicy value){return (String)value.snapshot().get("reason");}
 static ServerMemoryPolicy admitted(){ServerMemoryPolicy p=new ServerMemoryPolicy();need(p.admit(healthy(),0));return p;}
 @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(ServerMemoryPolicy p){return (List<Map<String,Object>>)p.snapshot().get("recent_samples");}
 static void primitives(Object value){
  if(value==null||value instanceof Boolean||value instanceof String||value instanceof Number){checks++;return;}
  if(value instanceof Map){for(Object entry:((Map<?,?>)value).entrySet()){Map.Entry<?,?> e=(Map.Entry<?,?>)entry;need(e.getKey() instanceof String);primitives(e.getValue());}return;}
  if(value instanceof List){for(Object item:(List<?>)value)primitives(item);return;}
  need(false);
 }
 public static void main(String[] args)throws Exception{
  ServerMemoryPolicy p=new ServerMemoryPolicy();Map<String,Object> s=p.snapshot();
  need(number(s,"format")==1);need(number(s,"samples")==0);need(rows(p).isEmpty());
  need(s.get("status").equals("not_started"));need(s.get("minimum_system_headroom_bytes")==null);
  need(s.get("last_elapsed_ms")==null);need(!(Boolean)s.get("admitted"));need(!(Boolean)s.get("stop_requested"));
  need(p.admit(healthy(),1000));need(p.admit(healthy(),2000));
  s=p.snapshot();need(number(s,"samples")==2);need(number(s,"last_elapsed_ms")==1000);
  need(number(s,"admission_reserve_bytes")==G);need(number(s,"running_reserve_bytes")==256*M);
  need(number(s,"java_heap_reserve_bytes")==16*M);need(s.get("scope").toString().contains("cannot guarantee"));

  // Admission includes Android's own threshold, plus the bounded system reserve.
  for(long total:new long[]{G,8*G,16*G,32*G,Long.MAX_VALUE}){
   long reserve=Math.max(512*M,Math.min(G,total/16));long threshold=16*M;
   p=new ServerMemoryPolicy();need(p.admit(sample(threshold+reserve,total,threshold,false,32*M,256*M),0));
   need(number(p.snapshot(),"admission_reserve_bytes")==reserve);
   p=new ServerMemoryPolicy();need(!p.admit(sample(threshold+reserve-M,total,threshold,false,32*M,256*M),0));
   need(reason(p).equals("SERVER_START_SYSTEM_MEMORY_PRESSURE"));
   p=new ServerMemoryPolicy();need(!p.admit(sample(threshold+reserve-1,total,threshold,false,32*M,256*M),0));
  }
  p=new ServerMemoryPolicy();need(!p.admit(sample(256*M,16*G,256*M,false,32*M,256*M),0));
  p=new ServerMemoryPolicy();need(!p.admit(sample(255*M,16*G,256*M,false,32*M,256*M),0));
  need(number(p.snapshot(),"minimum_system_headroom_bytes")==-M);
  for(long heap:new long[]{M,16*M,64*M,128*M,256*M,Long.MAX_VALUE}){
   long reserve=Math.min(16*M,Math.max(2*M,heap/8));
   p=new ServerMemoryPolicy();boolean expected=heap>=reserve;
   need(p.admit(sample(8*G,16*G,0,false,Math.max(0,heap-reserve),heap),0)==expected);
   if(expected){
    need(number(p.snapshot(),"java_heap_reserve_bytes")==reserve);
    p=new ServerMemoryPolicy();need(!p.admit(sample(8*G,16*G,0,false,heap-reserve+1,heap),0));
    need(reason(p).equals("SERVER_START_JAVA_HEAP_PRESSURE"));
   }
  }
  p=new ServerMemoryPolicy();need(!p.admit(sample(8*G,16*G,0,true,32*M,256*M),0));
  need(reason(p).equals("ANDROID_LOW_MEMORY"));need(!p.admit(healthy(),1));

  // Invalid or absent telemetry cannot authorize a guest. No invalid raw values leak.
  ServerMemoryPolicy.Sample[] invalid={null,sample(-1,G,0,false,0,M),sample(G+1,G,0,false,0,M),
   sample(0,0,0,false,0,M),sample(0,-1,0,false,0,M),sample(G,G,-1,false,0,M),
   sample(G,G,G+1,false,0,M),sample(G,G,0,false,-1,M),sample(G,G,0,false,M+1,M),
   sample(G,G,0,false,0,0),sample(G,G,0,false,0,-1)};
  for(ServerMemoryPolicy.Sample bad:invalid){
   p=new ServerMemoryPolicy();need(!p.admit(bad,0));need(reason(p).equals("SERVER_MEMORY_TELEMETRY_UNAVAILABLE"));
   need(number(p.snapshot(),"invalid_samples")==1);need(rows(p).get(0).get("available_bytes")==null);
   need(p.snapshot().get("minimum_system_headroom_bytes")==null);
   need(p.observe(healthy(),1000));need(reason(p).equals("SERVER_MEMORY_TELEMETRY_UNAVAILABLE"));
   p=admitted();need(p.observe(bad,1000));need(reason(p).equals("SERVER_MEMORY_TELEMETRY_UNAVAILABLE"));
  }
  p=new ServerMemoryPolicy();need(p.observe(healthy(),0));need(reason(p).equals("SERVER_MEMORY_NOT_ADMITTED"));

  // Three spaced samples alone are insufficient until their span reaches 3 s.
  p=admitted();need(!p.observe(pressure(),1000));need(!p.observe(pressure(),2000));
  need(!p.observe(pressure(),3000));need(number(p.snapshot(),"pressure_samples")==3);
  need(!p.observe(pressure(),3999));need(p.observe(pressure(),4000));
  need(reason(p).equals("SERVER_SUSTAINED_MEMORY_PRESSURE"));
  need(number(p.snapshot(),"pressure_started_elapsed_ms")==1000);
  need(p.observe(healthy(),5000));need(reason(p).equals("SERVER_SUSTAINED_MEMORY_PRESSURE"));
  p=admitted();need(!p.observe(pressure(),1000));need(!p.observe(pressure(),2500));need(p.observe(pressure(),4000));
  // Rapid callbacks never accelerate the counted 1-second sampling window.
  p=admitted();for(int i=0;i<1000;i++)need(!p.observe(pressure(),i));
  need(number(p.snapshot(),"pressure_samples")==1);
  need(!p.observe(healthy(),1000));need(number(p.snapshot(),"pressure_samples")==0);
  need(p.snapshot().get("pressure_started_elapsed_ms")==null);
  need(!p.observe(pressure(),2000));need(!p.observe(pressure(),3000));
  need(!p.observe(pressure(),4000));need(p.observe(pressure(),5000));

  // Recovery breaks the sequence, including a sample exactly at either reserve.
  p=admitted();need(!p.observe(pressure(),1000));need(!p.observe(pressure(),2000));
  need(!p.observe(sample(512*M,16*G,256*M,false,240*M,256*M),3000));
  need(number(p.snapshot(),"pressure_samples")==0);need(!p.observe(pressure(),4000));
  need(!p.observe(pressure(),5000));need(!p.observe(pressure(),6000));need(p.observe(pressure(),7000));
  p=admitted();need(!p.observe(sample(8*G,16*G,0,false,241*M,256*M),1000));
  need(!p.observe(sample(8*G,16*G,0,false,241*M,256*M),2000));
  need(!p.observe(sample(8*G,16*G,0,false,241*M,256*M),3000));
  need(p.observe(sample(8*G,16*G,0,false,241*M,256*M),4000));
  p=admitted();need(p.observe(sample(8*G,16*G,0,true,32*M,256*M),1));need(reason(p).equals("ANDROID_LOW_MEMORY"));
  for(long total:new long[]{G,8*G,16*G,32*G,Long.MAX_VALUE}){
   long reserve=Math.max(64*M,Math.min(256*M,total/64));
   p=new ServerMemoryPolicy();need(p.admit(sample(Math.min(total,2*G),total,0,false,32*M,256*M),0));
   need(!p.observe(sample(reserve,total,0,false,32*M,256*M),1000));
   need(number(p.snapshot(),"running_reserve_bytes")==reserve);need(number(p.snapshot(),"pressure_samples")==0);
   need(!p.observe(sample(reserve-M,total,0,false,32*M,256*M),2000));
   need(!p.observe(sample(reserve-M,total,0,false,32*M,256*M),3000));
   need(!p.observe(sample(reserve-M,total,0,false,32*M,256*M),4000));
   need(p.observe(sample(reserve-M,total,0,false,32*M,256*M),5000));
  }

  // Invalid time is fail closed; huge valid clocks and capacities never wrap.
  p=new ServerMemoryPolicy();need(!p.admit(healthy(),-1));need(rows(p).get(0).get("elapsed_ms")==null);
  p=new ServerMemoryPolicy();need(p.admit(healthy(),100));need(p.observe(healthy(),99));
  need(reason(p).equals("SERVER_MEMORY_TELEMETRY_UNAVAILABLE"));need(number(p.snapshot(),"last_elapsed_ms")==0);
  p=admitted();need(!p.observe(pressure(),Long.MAX_VALUE-3000));
  need(!p.observe(pressure(),Long.MAX_VALUE-2000));need(p.observe(pressure(),Long.MAX_VALUE));
  need(number(p.snapshot(),"last_elapsed_ms")==Long.MAX_VALUE);
  p=new ServerMemoryPolicy();need(p.admit(sample(Long.MAX_VALUE,Long.MAX_VALUE,0,false,0,Long.MAX_VALUE),0));
  need(number(p.snapshot(),"minimum_system_headroom_bytes")==Long.MAX_VALUE);
  need(number(p.snapshot(),"minimum_java_heap_headroom_bytes")==Long.MAX_VALUE);

  // Snapshot contents are bounded, private, defensive, and synchronized.
  p=admitted();for(int i=1;i<=100;i++)need(!p.observe(healthy(),i*1000));
  s=p.snapshot();need(number(s,"samples")==101);need(rows(p).size()==64);
  need(number(rows(p).get(0),"elapsed_ms")==37000);need(number(rows(p).get(63),"elapsed_ms")==100000);
  List<Map<String,Object>> snapshotRows=rows(p);snapshotRows.get(0).put("available_bytes",-1L);snapshotRows.clear();
  need(rows(p).size()==64);need(number(rows(p).get(0),"available_bytes")==8*G);
  primitives(s);
  final ServerMemoryPolicy shared=admitted();final AtomicBoolean failed=new AtomicBoolean();
  Thread[] threads=new Thread[4];
  for(int t=0;t<threads.length;t++){threads[t]=new Thread(()->{
   try {for(int i=0;i<100;i++){if(shared.observe(healthy(),1000))failed.set(true);shared.snapshot();}}
   catch(Throwable failure){failed.set(true);}
  });threads[t].start();}
  for(Thread thread:threads)thread.join();need(!failed.get());need(number(shared.snapshot(),"samples")==401);
  need(rows(shared).size()==64);need(number(shared.snapshot(),"invalid_samples")==0);
  System.out.println("{\"status\":\"passed\",\"checks\":"+checks+",\"retained_samples\":64,\"cooperative_only\":true,\"actual_server_interoperability_verified\":false}");
 }
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix='coh-server-memory-') as tmp:
        root = Path(tmp)
        test = root / 'ServerMemoryTest.java'
        test.write_text(HARNESS)
        subprocess.run(['java', 'com.sun.tools.javac.Main', '-d', str(root), str(SOURCE), str(test)],
                       check=True, capture_output=True, text=True)
        result = subprocess.run(['java', '-cp', str(root), 'org.coh.nativecombined.ServerMemoryTest'],
                                check=True, capture_output=True, text=True)
        print(json.dumps(json.loads(result.stdout)))


if __name__ == '__main__':
    main()
