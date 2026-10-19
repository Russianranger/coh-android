package org.coh.nativecombined;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Observation only. Fixed phase slots do not retain events, assets or owners. */
final class PhaseMemoryDiagnostics {
    enum Phase { COLD_STARTUP, SERVER_READY, NATIVE_CONNECTION, DIAGNOSTIC, RETURN,
        PAUSE, RESUME, FINAL_CLEANUP, SERVER_STOPPED }
    enum State { MISSING_CATALOG_GENERATION, UNRESOLVED_RESOURCE_IDENTITY,
        INCOMPLETE_CHARACTER_DATA, INITIAL_PACKET_OBSERVED, MEMORY_PRESSURE_REFUSAL,
        MEMORY_TELEMETRY_UNAVAILABLE, OBSERVATION_ONLY }
    static final class ProcessSample {
        final Long rss, pss;
        final String rssSource, pssSource;
        ProcessSample(Long rss, Long pss, String rssSource, String pssSource) {
            this.rss=rss; this.pss=pss; this.rssSource=rssSource; this.pssSource=pssSource;
        }
    }
    private final EnumMap<Phase,Map<String,Object>> phases=new EnumMap<>(Phase.class);
    private long samples;
    private Long peakRss, peakPss, minimumSystem, minimumHeap;
    private long lastSample=-1;

    static Map<String,Object> states(boolean initialObserved, boolean pressureRefusal) {
        Map<String,Object> out=new LinkedHashMap<>();
        out.put("catalog",State.MISSING_CATALOG_GENERATION.name());
        out.put("world_resource",State.UNRESOLVED_RESOURCE_IDENTITY.name());
        out.put("character",State.INCOMPLETE_CHARACTER_DATA.name());
        out.put("initial_packet",initialObserved?State.INITIAL_PACKET_OBSERVED.name():"NOT_OBSERVED");
        out.put("memory",pressureRefusal?State.MEMORY_PRESSURE_REFUSAL.name():State.OBSERVATION_ONLY.name());
        out.put("world_authority",false); out.put("application_ack_permitted",false);
        return out;
    }
    static Map<String,Object> states(boolean initialObserved,String memoryReason) {
        boolean pressure="ANDROID_LOW_MEMORY".equals(memoryReason)||"SERVER_START_SYSTEM_MEMORY_PRESSURE".equals(memoryReason)
                ||"SERVER_START_JAVA_HEAP_PRESSURE".equals(memoryReason)||"SERVER_SUSTAINED_MEMORY_PRESSURE".equals(memoryReason);
        Map<String,Object> out=states(initialObserved,pressure);
        if("SERVER_MEMORY_TELEMETRY_UNAVAILABLE".equals(memoryReason)||"SERVER_MEMORY_NOT_ADMITTED".equals(memoryReason))
            out.put("memory",State.MEMORY_TELEMETRY_UNAVAILABLE.name());
        return out;
    }
    private static Long known(Long value) { return value!=null&&value>=0?value:null; }
    private static boolean validSystem(ServerMemoryPolicy.Sample sample) {
        return sample!=null&&sample.total>0&&sample.available>=0&&sample.available<=sample.total
                &&sample.threshold>=0&&sample.threshold<=sample.total&&sample.heapLimit>0
                &&sample.heapUsed>=0&&sample.heapUsed<=sample.heapLimit;
    }
    private static Long maximum(Long a,Long b) {
        if(a==null)return b;
        if(b==null)return a;
        return Long.valueOf(Math.max(a.longValue(),b.longValue()));
    }
    private static Long minimum(Long a,long b) { return a==null?b:Math.min(a,b); }
    private static String source(Long value,String source) {
        return value==null?"unavailable":"proc_self_smaps_rollup".equals(source)
                ||"proc_self_status_VmRSS".equals(source)?source:"unavailable";
    }
    /** The observer timestamps requested phase and later control-thread sample separately. */
    synchronized void record(Phase phase,long requested,long sampled,ServerMemoryPolicy.Sample system,
            ProcessSample process) {
        if(phase==null||requested<0||sampled<requested||sampled<lastSample)return;
        lastSample=sampled; if(samples<Long.MAX_VALUE)samples++;
        boolean valid=validSystem(system);
        Long rss=process==null?null:known(process.rss),pss=process==null?null:known(process.pss);
        String rssSource=source(rss,process==null?null:process.rssSource);
        String pssSource=source(pss,process==null?null:process.pssSource);
        if("unavailable".equals(rssSource))rss=null;
        if(!"proc_self_smaps_rollup".equals(pssSource)){pss=null;pssSource="unavailable";}
        Map<String,Object> row=new LinkedHashMap<>();
        row.put("phase",phase.name());row.put("requested_elapsed_ms",requested);row.put("sampled_elapsed_ms",sampled);
        row.put("sequence",samples);row.put("system_sample_valid",valid);
        row.put("available_bytes",valid?system.available:null);row.put("total_bytes",valid?system.total:null);
        row.put("threshold_bytes",valid?system.threshold:null);row.put("android_low_memory",valid?system.lowMemory:null);
        row.put("java_heap_used_bytes",valid?system.heapUsed:null);row.put("java_heap_limit_bytes",valid?system.heapLimit:null);
        row.put("system_headroom_bytes",valid?system.available-system.threshold:null);
        row.put("java_heap_headroom_bytes",valid?system.heapLimit-system.heapUsed:null);
        row.put("process_rss_bytes",rss);row.put("process_pss_bytes",pss);
        row.put("process_rss_source",rssSource);row.put("process_pss_source",pssSource);
        row.put("process_observer_status",process==null?"unavailable":"native_observer_returned");
        row.put("memory_state",valid?State.OBSERVATION_ONLY.name():State.MEMORY_TELEMETRY_UNAVAILABLE.name());
        phases.put(phase,row);peakRss=maximum(peakRss,rss);peakPss=maximum(peakPss,pss);
        if(valid){minimumSystem=minimum(minimumSystem,system.available-system.threshold);
            minimumHeap=minimum(minimumHeap,system.heapLimit-system.heapUsed);}
    }
    synchronized Map<String,Object> snapshot() {
        Map<String,Object> out=new LinkedHashMap<>();
        out.put("schema","coh-combined-phase-memory-v1");out.put("scope","current Android app process lifetime; bounded phase observations, not total device or guest memory");
        out.put("phase_limit",Phase.values().length);out.put("samples",samples);
        out.put("sample_interval_ms",1000);out.put("latest_sample_elapsed_ms",lastSample<0?null:lastSample);
        out.put("sampled_peak_process_rss_bytes",peakRss);out.put("sampled_peak_process_pss_bytes",peakPss);
        out.put("minimum_observed_system_headroom_bytes",minimumSystem);out.put("minimum_observed_java_heap_headroom_bytes",minimumHeap);
        out.put("owned_guest_process_memory","unavailable: no installed verified process-owner adapter; shared RSS is never summed");
        out.put("native_owner_memory","unavailable as an aggregate; existing native module ownership receipts remain separate");
        out.put("graphics_memory","unavailable as a process total; accepted renderer allocation estimates remain in native snapshot");
        out.put("admission_authority",false);out.put("server_policy_thresholds_changed",false);
        List<Map<String,Object>> rows=new ArrayList<>();
        for(Map<String,Object> row:phases.values())rows.add(new LinkedHashMap<>(row));
        out.put("phases",rows);return out;
    }
}
