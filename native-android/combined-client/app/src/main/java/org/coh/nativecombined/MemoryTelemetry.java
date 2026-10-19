package org.coh.nativecombined;

import android.app.ActivityManager;
import android.content.Context;
import android.os.SystemClock;
import java.util.EnumMap;
import java.util.Map;
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
    private static long nextSample;
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
        pending.put(phase,SystemClock.elapsedRealtime());
        if(scheduled)return;
        scheduled=true;
        final Context application=context.getApplicationContext();
        worker.schedule(()->sample(application),Math.max(0,nextSample-SystemClock.elapsedRealtime()),TimeUnit.MILLISECONDS);
    }
    private static void sample(Context context) {
        EnumMap<PhaseMemoryDiagnostics.Phase,Long> requested;
        synchronized(MemoryTelemetry.class){requested=new EnumMap<>(pending);pending.clear();}
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
        long sampled=SystemClock.elapsedRealtime();
        for(Map.Entry<PhaseMemoryDiagnostics.Phase,Long> row:requested.entrySet())
            observations.record(row.getKey(),row.getValue(),sampled,system,process);
        synchronized(MemoryTelemetry.class){
            nextSample=sampled>Long.MAX_VALUE-1000?Long.MAX_VALUE:sampled+1000;scheduled=false;
            if(!pending.isEmpty()){
                scheduled=true;worker.schedule(()->sample(context),Math.max(0,nextSample-SystemClock.elapsedRealtime()),TimeUnit.MILLISECONDS);
            }
        }
    }
    static JSONObject snapshot(){
        Map<String,Object> snapshot=observations.snapshot();long now=SystemClock.elapsedRealtime();
        Long latest=(Long)snapshot.get("latest_sample_elapsed_ms");
        snapshot.put("snapshot_elapsed_ms",now);snapshot.put("latest_sample_age_ms",latest==null||latest>now?null:now-latest);
        return new JSONObject(snapshot);
    }
}
