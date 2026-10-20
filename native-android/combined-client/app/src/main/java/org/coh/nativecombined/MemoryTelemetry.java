package org.coh.nativecombined;

import android.app.ActivityManager;
import android.content.Context;
import android.os.SystemClock;
import java.util.EnumMap;
import java.util.Map;
import java.util.LinkedHashMap;
import java.nio.file.Paths;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;

/** One bounded process-lifetime control sampler; never executes on a render/network owner. */
final class MemoryTelemetry {
    private static final PhaseMemoryDiagnostics observations=new PhaseMemoryDiagnostics();
    private static final ScheduledExecutorService worker=Executors.newSingleThreadScheduledExecutor(r->new Thread(r,"coh-memory-observer"));
    private static final EnumMap<PhaseMemoryDiagnostics.Phase,Long> pending=new EnumMap<>(PhaseMemoryDiagnostics.Phase.class);
    private static boolean scheduled;
    private static final ProcessSetMemory processSet=new ProcessSetMemory();
    private static boolean processSetPending,serverProcessExpected;
    private static long nextProcessSet;
    private static long nextSample, sampleFailures;
    private static long trimCallbacks, lowMemoryCallbacks;
    private static Integer lastTrimLevel;
    private static Long lastPressureElapsed;
    private MemoryTelemetry() { }

    static ServerMemoryPolicy.Sample systemSample(Context context) {
        try {
            ActivityManager manager=(ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE);
            ActivityManager.MemoryInfo info=new ActivityManager.MemoryInfo();manager.getMemoryInfo(info);
            Runtime java=Runtime.getRuntime();
            return new ServerMemoryPolicy.Sample(info.availMem,info.totalMem,info.threshold,info.lowMemory,
                    java.totalMemory()-java.freeMemory(),java.maxMemory());
        }catch(RuntimeException unavailable){return null;}
    }
    static synchronized void request(Context context,PhaseMemoryDiagnostics.Phase phase) {
        if(phase==null)return;
        try {
            long now=SystemClock.elapsedRealtime();
            pending.put(phase,now);
            if(now>=nextProcessSet)processSetPending=true;
            if(scheduled)return;
            schedule(context.getApplicationContext());
        }catch(RuntimeException unavailable){failed();}
    }
    /** Reuses the same observer worker; never forks another guest or changes admission. */
    static synchronized void requestProcessSet(Context context,boolean serverExpected) {
        boolean changed=serverProcessExpected!=serverExpected;serverProcessExpected=serverExpected;
        if(!changed&&SystemClock.elapsedRealtime()<nextProcessSet)return;
        processSetPending=true;
        if(!scheduled)try{schedule(context.getApplicationContext());}catch(RuntimeException unavailable){failed();}
    }
    private static void failed(){if(sampleFailures<Long.MAX_VALUE)sampleFailures++;}
    /** Caller holds the class monitor. Refusal must never leave a phantom queued task. */
    private static void schedule(Context context){
        long delay=Math.max(0,nextSample-SystemClock.elapsedRealtime());
        scheduled=true;
        try{worker.schedule(()->sample(context),delay,TimeUnit.MILLISECONDS);}
        catch(RuntimeException unavailable){scheduled=false;failed();}
    }
    private static void sample(Context context) {
        try {
            EnumMap<PhaseMemoryDiagnostics.Phase,Long> requested;boolean collectProcessSet,expectServer;
            synchronized(MemoryTelemetry.class){requested=new EnumMap<>(pending);pending.clear();collectProcessSet=processSetPending;processSetPending=false;expectServer=serverProcessExpected;}
            ServerMemoryPolicy.Sample system=systemSample(context);
            PhaseMemoryDiagnostics.ProcessSample process=null;
            try {
                String raw=LocalNative.processMemory();
                if(raw!=null&&raw.length()<=1024){JSONObject value=new JSONObject(raw);
                    if(value.getInt("schema")!=1||!"process_memory_sample".equals(value.getString("scope"))||!"bytes".equals(value.getString("unit")))throw new IllegalStateException("Unexpected observer schema");
                    JSONObject rss=value.getJSONObject("rss"),pss=value.getJSONObject("pss");
                    process=new PhaseMemoryDiagnostics.ProcessSample(rss.getBoolean("known")?rss.getLong("bytes"):null,
                            pss.getBoolean("known")?pss.getLong("bytes"):null,rss.getString("source"),pss.getString("source"));}
            }catch(Exception|LinkageError unavailable){/* Optional /proc observation never weakens server admission. */}
            if(collectProcessSet) {
                processSet.sample(Paths.get("/proc"),android.os.Process.myUid(),android.os.Process.myPid(),expectServer,
                        SystemClock::elapsedRealtime,System.currentTimeMillis());
                synchronized(MemoryTelemetry.class){long now=SystemClock.elapsedRealtime();nextProcessSet=now>Long.MAX_VALUE-ProcessSetMemory.INTERVAL_MS?Long.MAX_VALUE:now+ProcessSetMemory.INTERVAL_MS;}
            }
            long sampled=SystemClock.elapsedRealtime();
            for(Map.Entry<PhaseMemoryDiagnostics.Phase,Long> row:requested.entrySet())
                observations.record(row.getKey(),row.getValue(),sampled,system,process);
        }catch(RuntimeException unavailable){synchronized(MemoryTelemetry.class){failed();}}
        finally {
            synchronized(MemoryTelemetry.class){
                scheduled=false;
                try {
                    long now=SystemClock.elapsedRealtime();
                    nextSample=now>Long.MAX_VALUE-1000?Long.MAX_VALUE:now+1000;
                    if(!pending.isEmpty()||processSetPending)schedule(context);
                }catch(RuntimeException unavailable){failed();}
            }
        }
    }
    static synchronized void memoryPressure(Context context,int level,boolean lowMemory) {
        if(lowMemory){if(lowMemoryCallbacks<Long.MAX_VALUE)lowMemoryCallbacks++;}
        else if(level>=0&&level<=100){if(trimCallbacks<Long.MAX_VALUE)trimCallbacks++;lastTrimLevel=level;}
        else return;
        lastPressureElapsed=SystemClock.elapsedRealtime();
        request(context,PhaseMemoryDiagnostics.Phase.DIAGNOSTIC);
    }
    private static synchronized Map<String,Object> pressureSnapshot(){
        Map<String,Object> row=new LinkedHashMap<>();
        row.put("source","Android onTrimMemory/onLowMemory callbacks");row.put("trim_callbacks",trimCallbacks);
        row.put("low_memory_callbacks",lowMemoryCallbacks);row.put("last_trim_level",lastTrimLevel);
        row.put("last_callback_elapsed_ms",lastPressureElapsed);row.put("callback_is_oom_kill_proof",false);return row;
    }
    static JSONObject snapshot(){
        Map<String,Object> snapshot=observations.snapshot();long now=SystemClock.elapsedRealtime();
        Long latest=(Long)snapshot.get("latest_sample_elapsed_ms");
        snapshot.put("snapshot_elapsed_ms",now);snapshot.put("latest_sample_age_ms",latest==null||latest>now?null:now-latest);
        synchronized(MemoryTelemetry.class){snapshot.put("sampler_failures",sampleFailures);}
        snapshot.put("android_memory_callbacks",pressureSnapshot());
        return boundedSnapshot(snapshot,processSet,now);
    }
    /** Only optional numeric detail shrinks. Every scanned-process aggregate,
     * all phase slots and four PID/start_ticks identity joins remain present.
     * At most six bounded candidates are encoded; no proc rescan occurs. */
    static JSONObject boundedSnapshot(Map<String,Object> snapshot,ProcessSetMemory observer,long now){
        JSONObject encoded=null;
        for(int limit:new int[]{32,24,16,8,5,0}){
            Map<String,Object> group=observer.exportSnapshot(limit==0?5:limit,limit==0);Object end=group.get("end_elapsed_ms");
            group.put("snapshot_age_ms",end instanceof Long&&((Long)end)<=now?now-((Long)end):null);
            snapshot.put("same_uid_process_set",group);snapshot.put("process_detail_budget_omission",limit<32);
            encoded=new JSONObject(snapshot);
            try{if(encoded.toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8).length<24*1024)return encoded;}
            catch(org.json.JSONException unavailable){/* All candidate values are bounded observation scalars. */}
        }
        // The minimum candidate includes the app and every priority identity.
        // Its complete emitter bound is exercised with maximum source paths,
        // JSON escapes, counters and all nine phase records by the host check.
        return encoded;
    }
}
