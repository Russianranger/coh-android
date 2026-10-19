#!/usr/bin/env python3
"""Bounded phase observations and typed incomplete states, using production Java."""
from pathlib import Path
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'app/src/main/java/org/coh/nativecombined'
HARNESS = r'''
package org.coh.nativecombined;
import java.util.List;
import java.util.Map;
public final class PhaseMemoryTest {
 static int checks;
 static void need(boolean x){checks++;if(!x)throw new AssertionError("phase memory "+checks);}
 static long number(Map<String,Object>x,String k){return ((Number)x.get(k)).longValue();}
 @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(PhaseMemoryDiagnostics p){return (List<Map<String,Object>>)p.snapshot().get("phases");}
 static ServerMemoryPolicy.Sample healthy(){return new ServerMemoryPolicy.Sample(8L<<30,16L<<30,256L<<20,false,32L<<20,256L<<20);}
 static PhaseMemoryDiagnostics.ProcessSample proc(Long r,Long p){return new PhaseMemoryDiagnostics.ProcessSample(r,p,"proc_self_smaps_rollup","proc_self_smaps_rollup");}
 public static void main(String[]args)throws Exception{
  PhaseMemoryDiagnostics p=new PhaseMemoryDiagnostics();need(rows(p).isEmpty());need(p.snapshot().get("sampled_peak_process_rss_bytes")==null);
  need(p.snapshot().get("latest_sample_elapsed_ms")==null);
  p.record(PhaseMemoryDiagnostics.Phase.COLD_STARTUP,0,1,healthy(),proc(0L,0L));
  need(number(rows(p).get(0),"process_rss_bytes")==0);need(number(rows(p).get(0),"process_pss_bytes")==0);
  p.record(PhaseMemoryDiagnostics.Phase.COLD_STARTUP,2,3,null,null);
  Map<String,Object> r=rows(p).get(0);need(r.get("available_bytes")==null);need(r.get("process_pss_bytes")==null);
  need(r.get("memory_state").equals("MEMORY_TELEMETRY_UNAVAILABLE"));need(number(p.snapshot(),"sampled_peak_process_rss_bytes")==0);
  need(number(r,"requested_elapsed_ms")==2&&number(r,"sampled_elapsed_ms")==3);
  p.record(PhaseMemoryDiagnostics.Phase.DIAGNOSTIC,4,5,healthy(),new PhaseMemoryDiagnostics.ProcessSample(99L,88L,"proc_self_status_VmRSS","proc_self_status_VmRSS"));
  r=rows(p).get(1);need(number(r,"process_rss_bytes")==99);need(r.get("process_pss_bytes")==null);
  p.record(PhaseMemoryDiagnostics.Phase.DIAGNOSTIC,6,7,healthy(),proc(-1L,-1L));
  need(rows(p).get(1).get("process_rss_bytes")==null);need(rows(p).get(1).get("process_pss_bytes")==null);
  p.record(PhaseMemoryDiagnostics.Phase.DIAGNOSTIC,8,9,healthy(),new PhaseMemoryDiagnostics.ProcessSample(9L,8L,"forged","forged"));
  need(rows(p).get(1).get("process_rss_bytes")==null);need(rows(p).get(1).get("process_pss_bytes")==null);
  ServerMemoryPolicy.Sample[] bad={null,new ServerMemoryPolicy.Sample(-1,4,0,false,0,1),new ServerMemoryPolicy.Sample(5,4,0,false,0,1),new ServerMemoryPolicy.Sample(4,4,5,false,0,1),new ServerMemoryPolicy.Sample(4,4,0,false,2,1),new ServerMemoryPolicy.Sample(4,4,0,false,0,0)};
  for(int i=0;i<bad.length;i++){p.record(PhaseMemoryDiagnostics.Phase.DIAGNOSTIC,10+i,10+i,bad[i],null);need(rows(p).get(1).get("available_bytes")==null);}
  long before=number(p.snapshot(),"samples");p.record(null,20,20,healthy(),null);p.record(PhaseMemoryDiagnostics.Phase.DIAGNOSTIC,-1,20,healthy(),null);p.record(PhaseMemoryDiagnostics.Phase.DIAGNOSTIC,20,19,healthy(),null);p.record(PhaseMemoryDiagnostics.Phase.DIAGNOSTIC,0,0,healthy(),null);need(number(p.snapshot(),"samples")==before);
  for(int i=0;i<1000;i++)for(PhaseMemoryDiagnostics.Phase phase:PhaseMemoryDiagnostics.Phase.values())p.record(phase,100+i,100+i,healthy(),proc((long)i,(long)i));
  need(rows(p).size()==9);need(number(p.snapshot(),"sampled_peak_process_rss_bytes")==999);
  need(number(p.snapshot(),"sampled_peak_process_pss_bytes")==999);
  List<Map<String,Object>> detached=rows(p);detached.get(0).put("process_rss_bytes",-1);detached.clear();need(rows(p).size()==9);need(number(rows(p).get(0),"process_rss_bytes")==999);
  p.record(PhaseMemoryDiagnostics.Phase.FINAL_CLEANUP,Long.MAX_VALUE,Long.MAX_VALUE,new ServerMemoryPolicy.Sample(Long.MAX_VALUE,Long.MAX_VALUE,0,false,0,Long.MAX_VALUE),proc(Long.MAX_VALUE,Long.MAX_VALUE));
  need(number(p.snapshot(),"latest_sample_elapsed_ms")==Long.MAX_VALUE);need(number(p.snapshot(),"sampled_peak_process_rss_bytes")==Long.MAX_VALUE);
  Map<String,Object>s=PhaseMemoryDiagnostics.states(true,false);need(s.get("catalog").equals("MISSING_CATALOG_GENERATION"));need(s.get("character").equals("INCOMPLETE_CHARACTER_DATA"));need(s.get("world_resource").equals("UNRESOLVED_RESOURCE_IDENTITY"));need(s.get("initial_packet").equals("INITIAL_PACKET_OBSERVED"));need(s.get("world_authority").equals(false));need(s.get("application_ack_permitted").equals(false));
  need(PhaseMemoryDiagnostics.states(false,true).get("memory").equals("MEMORY_PRESSURE_REFUSAL"));
  for(String reason:new String[]{"SERVER_MEMORY_TELEMETRY_UNAVAILABLE","SERVER_MEMORY_NOT_ADMITTED"})need(PhaseMemoryDiagnostics.states(false,reason).get("memory").equals("MEMORY_TELEMETRY_UNAVAILABLE"));
  for(String reason:new String[]{"ANDROID_LOW_MEMORY","SERVER_START_SYSTEM_MEMORY_PRESSURE","SERVER_START_JAVA_HEAP_PRESSURE","SERVER_SUSTAINED_MEMORY_PRESSURE"})need(PhaseMemoryDiagnostics.states(false,reason).get("memory").equals("MEMORY_PRESSURE_REFUSAL"));
  need(p.snapshot().get("owned_guest_process_memory").toString().contains("unavailable"));need(p.snapshot().get("admission_authority").equals(false));need(p.snapshot().get("server_policy_thresholds_changed").equals(false));
  System.out.println("{\"status\":\"passed\",\"checks\":"+checks+",\"retained_phase_limit\":9,\"repeated_records\":9000,\"world_authority\":false}");
 }
}
'''

def main():
    with tempfile.TemporaryDirectory(prefix='coh-phase-memory-') as tmp:
        root = Path(tmp)
        test = root / 'PhaseMemoryTest.java'
        test.write_text(HARNESS)
        subprocess.run(['java', 'com.sun.tools.javac.Main', '-d', str(root), str(SOURCE / 'ServerMemoryPolicy.java'), str(SOURCE / 'PhaseMemoryDiagnostics.java'), str(test)], check=True, capture_output=True, text=True)
        result = subprocess.run(['java', '-cp', str(root), 'org.coh.nativecombined.PhaseMemoryTest'], check=True, capture_output=True, text=True)
        print(json.dumps(json.loads(result.stdout)))

if __name__ == '__main__':
    main()
