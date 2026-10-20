#!/usr/bin/env python3
"""Execute production memory worker with bounded Android/JNI availability stubs."""
from pathlib import Path
import json
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / 'app/src/main/java/org/coh/nativecombined'
STUBS = {
    'android/content/Context.java': '''package android.content;
public class Context {public static final String ACTIVITY_SERVICE="activity";
 public Object getSystemService(String name){return new android.app.ActivityManager();}
 public Context getApplicationContext(){return this;}}
''',
    'android/app/ActivityManager.java': '''package android.app;
public class ActivityManager {public static volatile boolean unavailable=true;
 public static class MemoryInfo {public long availMem,totalMem,threshold;public boolean lowMemory;}
 public void getMemoryInfo(MemoryInfo x){if(unavailable)throw new SecurityException("unavailable fixture");
 x.availMem=8L<<30;x.totalMem=16L<<30;x.threshold=256L<<20;}}
''',
    'android/os/Process.java': 'package android.os; public class Process {public static int myUid(){return 1000;} public static int myPid(){return 1;}}',
    'android/os/SystemClock.java': '''package android.os;
public class SystemClock {private static final long start=System.nanoTime();
 public static final java.util.concurrent.atomic.AtomicBoolean failWorkerOnce=new java.util.concurrent.atomic.AtomicBoolean();
 public static long elapsedRealtime(){if(Thread.currentThread().getName().equals("coh-memory-observer")&&failWorkerOnce.compareAndSet(true,false))throw new IllegalStateException("observation fixture failure");return 1+(System.nanoTime()-start)/1000000L;}}
''',
    'org/json/JSONObject.java': '''package org.json;
public class JSONObject {private java.util.Map<String,Object> value;
 public JSONObject(java.util.Map<String,Object> x){value=x;}
 public JSONObject(String x){throw new IllegalArgumentException("JSON observation unavailable fixture");}
 public java.util.Map<String,Object> toMap(){return value;}
 public int getInt(String x){throw new IllegalArgumentException();}
 public long getLong(String x){throw new IllegalArgumentException();}
 public boolean getBoolean(String x){throw new IllegalArgumentException();}
 public String getString(String x){throw new IllegalArgumentException();}
 public JSONObject getJSONObject(String x){throw new IllegalArgumentException();}}
''',
    'org/coh/nativecombined/LocalNative.java': '''package org.coh.nativecombined;
public class LocalNative {public static volatile int mode,calls;public static volatile boolean wrongThread;
 public static volatile java.util.concurrent.CountDownLatch entered,release;
 public static String processMemory(){calls++;if(!Thread.currentThread().getName().equals("coh-memory-observer"))wrongThread=true;
 java.util.concurrent.CountDownLatch a=entered,b=release;
 if(a!=null){a.countDown();try{if(!b.await(10,java.util.concurrent.TimeUnit.SECONDS))throw new IllegalStateException("fixture timeout");}catch(InterruptedException e){throw new IllegalStateException(e);}entered=null;release=null;}
 if(mode==1)throw new UnsatisfiedLinkError("optional JNI unavailable fixture");
 if(mode==2)return "invalid JSON fixture";return null;}}
'''
}
HARNESS = r'''
package org.coh.nativecombined;
import java.util.*;
import java.util.concurrent.*;
import android.os.SystemClock;
import android.app.ActivityManager;
public final class MemoryWorkerTest {
 static int checks;
 static void need(boolean x){checks++;if(!x)throw new AssertionError("memory worker "+checks);}
 static Object field(String name)throws Exception{java.lang.reflect.Field f=MemoryTelemetry.class.getDeclaredField(name);f.setAccessible(true);return f.get(null);}
 static Map<String,Object> snapshot(){return MemoryTelemetry.snapshot().toMap();}
 static long number(Map<String,Object> x,String key){return ((Number)x.get(key)).longValue();}
 @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(){return (List<Map<String,Object>>)snapshot().get("phases");}
 static void await(java.util.function.BooleanSupplier ready)throws Exception{long stop=System.nanoTime()+TimeUnit.SECONDS.toNanos(10);while(!ready.getAsBoolean()){if(System.nanoTime()>stop)throw new AssertionError("worker did not recover: "+snapshot());Thread.sleep(10);}}
 static boolean idle(){try{synchronized(MemoryTelemetry.class){return !(Boolean)field("scheduled");}}catch(Exception e){throw new IllegalStateException(e);}}
 @SuppressWarnings("unchecked") public static void main(String[] args)throws Exception{
  ScheduledExecutorService worker=(ScheduledExecutorService)field("worker");android.content.Context context=new android.content.Context();
  try {
   // First-ever system and process sources unavailable; no measured-zero seed.
   MemoryTelemetry.request(context,PhaseMemoryDiagnostics.Phase.COLD_STARTUP);
   await(()->number(snapshot(),"samples")==1&&idle());
   need(rows().get(0).get("process_rss_bytes")==null);need(rows().get(0).get("process_pss_bytes")==null);
   need(snapshot().get("sampled_peak_process_rss_bytes")==null);need(snapshot().get("sampled_peak_process_pss_bytes")==null);
   need(rows().get(0).get("available_bytes")==null);need(number(snapshot(),"sampler_failures")==0);

   // Fail a nonfatal observation after its pending phase was drained. Finally
   // must release scheduled so a later request can execute on the same owner.
   SystemClock.failWorkerOnce.set(true);MemoryTelemetry.request(context,PhaseMemoryDiagnostics.Phase.DIAGNOSTIC);
   await(()->number(snapshot(),"sampler_failures")==1&&idle());
   need(number(snapshot(),"samples")==1);
   MemoryTelemetry.request(context,PhaseMemoryDiagnostics.Phase.DIAGNOSTIC);
   await(()->number(snapshot(),"samples")==2&&idle());need(rows().size()==2);

   // Queue every phase while the worker is held, then fail its observation.
   // The finally path must schedule the bounded pending batch without another
   // request, and an optional missing native library must remain unknown.
   LocalNative.entered=new CountDownLatch(1);LocalNative.release=new CountDownLatch(1);
   CountDownLatch entered=LocalNative.entered,release=LocalNative.release;
   MemoryTelemetry.request(context,PhaseMemoryDiagnostics.Phase.RETURN);
   need(entered.await(10,TimeUnit.SECONDS));SystemClock.failWorkerOnce.set(true);LocalNative.mode=1;
   for(int i=0;i<1000;i++)for(PhaseMemoryDiagnostics.Phase phase:PhaseMemoryDiagnostics.Phase.values())MemoryTelemetry.request(context,phase);
   synchronized(MemoryTelemetry.class){need(((Map<?,?>)field("pending")).size()==9);need((Boolean)field("scheduled"));}
   release.countDown();await(()->number(snapshot(),"sampler_failures")==2&&number(snapshot(),"samples")==11&&idle());
   need(rows().size()==9);need(!LocalNative.wrongThread);need(LocalNative.calls<=5);
   for(Map<String,Object> row:rows()){need(row.get("process_rss_bytes")==null);need(row.get("process_pss_bytes")==null);}
   // Invalid optional JSON also cannot wedge later observations.
   ActivityManager.unavailable=false;LocalNative.mode=2;
   MemoryTelemetry.request(context,PhaseMemoryDiagnostics.Phase.RESUME);
   await(()->number(snapshot(),"samples")==12&&idle());
   need(rows().get(PhaseMemoryDiagnostics.Phase.RESUME.ordinal()).get("system_sample_valid").equals(true));
   need(number(snapshot(),"sampler_failures")==2);
   Map<String,Object> pressure=(Map<String,Object>)snapshot().get("android_memory_callbacks");
   need(pressure.get("last_trim_level")==null&&pressure.get("last_callback_elapsed_ms")==null);
   MemoryTelemetry.memoryPressure(context,-2,false);
   need(((Number)((Map<?,?>)snapshot().get("android_memory_callbacks")).get("trim_callbacks")).longValue()==0);
   MemoryTelemetry.memoryPressure(context,80,false);MemoryTelemetry.memoryPressure(context,-1,true);
   await(()->number(snapshot(),"samples")==13&&idle());
   pressure=(Map<String,Object>)snapshot().get("android_memory_callbacks");
   need(((Number)pressure.get("trim_callbacks")).longValue()==1&&((Number)pressure.get("low_memory_callbacks")).longValue()==1);
   need(Integer.valueOf(80).equals(pressure.get("last_trim_level"))&&pressure.get("last_callback_elapsed_ms") instanceof Long);
   need(Boolean.FALSE.equals(pressure.get("callback_is_oom_kill_proof")));
   System.out.println("{\"status\":\"passed\",\"checks\":"+checks+",\"queued_phase_requests\":9000,\"nonfatal_failures_recovered\":2,\"fresh_first_unavailable\":true,\"Android_stubs_only\":true}");
  }finally{worker.shutdownNow();worker.awaitTermination(10,TimeUnit.SECONDS);}
 }
}
'''

def main():
    with tempfile.TemporaryDirectory(prefix='coh-memory-worker-') as tmp:
        root = Path(tmp)
        sources = []
        for name, text in STUBS.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            sources.append(path)
        test = root / 'org/coh/nativecombined/MemoryWorkerTest.java'
        test.write_text(HARNESS)
        sources += [test, *(SOURCE / name for name in ('ServerMemoryPolicy.java', 'PhaseMemoryDiagnostics.java', 'ProcessSetMemory.java', 'AppCgroupMemory.java', 'MemoryTelemetry.java'))]
        build = subprocess.run(['java', 'com.sun.tools.javac.Main', '-d', str(root), *map(str, sources)], capture_output=True, text=True)
        if build.returncode:
            raise RuntimeError(build.stderr)
        result = subprocess.run(['java', '-cp', str(root), 'org.coh.nativecombined.MemoryWorkerTest'], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        print(json.dumps(json.loads(result.stdout)))

if __name__ == '__main__':
    main()
