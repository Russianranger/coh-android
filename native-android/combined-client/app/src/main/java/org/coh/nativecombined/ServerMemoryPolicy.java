package org.coh.nativecombined;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Bounded, cooperative startup admission and running memory-pressure policy. */
final class ServerMemoryPolicy {
    static final class Sample {
        final long available, total, threshold, heapUsed, heapLimit;
        final boolean lowMemory;
        Sample(long available, long total, long threshold, boolean lowMemory,
                long heapUsed, long heapLimit) {
            this.available=available; this.total=total; this.threshold=threshold;
            this.lowMemory=lowMemory; this.heapUsed=heapUsed; this.heapLimit=heapLimit;
        }
    }

    private static final long MIB=1024L*1024L;
    private static final long SAMPLE_INTERVAL_MS=1000, PRESSURE_SPAN_MS=3000;
    private static final int REQUIRED_PRESSURE_SAMPLES=3, RETAINED_SAMPLES=64;
    private final ArrayDeque<Map<String,Object>> recent=new ArrayDeque<>();
    private long samples, invalidSamples, started=-1, lastClock=-1;
    private long minimumHeadroom=Long.MAX_VALUE, minimumHeapHeadroom=Long.MAX_VALUE;
    private long pressureStarted=-1, lastPressureCounted=-1, pressureSamples;
    private long admissionReserve, runningReserve, heapReserve;
    private boolean admitted, stopRequested, haveValidSample;
    private String status="not_started", reason="";

    /** Returns true only when this sample permits the guest to start. */
    synchronized boolean admit(Sample sample,long now) {
        boolean valid=record(sample,now);
        if(!valid) return false;
        if(stopRequested) return false;
        if(sample.lowMemory) return block("ANDROID_LOW_MEMORY");
        if(sample.available-sample.threshold<admissionReserve)
            return block("SERVER_START_SYSTEM_MEMORY_PRESSURE");
        if(sample.heapLimit-sample.heapUsed<heapReserve)
            return block("SERVER_START_JAVA_HEAP_PRESSURE");
        admitted=true; status="admitted";
        return true;
    }

    /** Returns a sticky request for the caller to perform its owned cleanup. */
    synchronized boolean observe(Sample sample,long now) {
        if(!record(sample,now)) return true;
        if(stopRequested) return true;
        if(!admitted) {
            stop("SERVER_MEMORY_NOT_ADMITTED");
            return true;
        }
        if(sample.lowMemory) {
            stop("ANDROID_LOW_MEMORY");
            return true;
        }
        boolean pressure=sample.available-sample.threshold<runningReserve
                ||sample.heapLimit-sample.heapUsed<heapReserve;
        if(!pressure) {
            // A healthy sample breaks the consecutive-pressure sequence. The
            // time and sample requirements below debounce isolated dips.
            pressureStarted=-1; lastPressureCounted=-1; pressureSamples=0;
            status="running";
            return false;
        }
        status="pressure_observed";
        if(pressureStarted<0) {
            pressureStarted=now; lastPressureCounted=now; pressureSamples=1;
        } else if(now-lastPressureCounted>=SAMPLE_INTERVAL_MS) {
            lastPressureCounted=now; pressureSamples=increment(pressureSamples);
        }
        if(pressureSamples>=REQUIRED_PRESSURE_SAMPLES
                &&now-pressureStarted>=PRESSURE_SPAN_MS) {
            stop("SERVER_SUSTAINED_MEMORY_PRESSURE");
        }
        return stopRequested;
    }

    private boolean block(String value) {
        stopRequested=true; status="start_blocked"; reason=value;
        return false;
    }

    private void stop(String value) {
        if(stopRequested) return;
        stopRequested=true; status="stop_requested"; reason=value;
    }

    private static long increment(long value) {
        return value==Long.MAX_VALUE?value:value+1;
    }

    private boolean record(Sample sample,long now) {
        samples=increment(samples);
        boolean clockValid=now>=0&&(lastClock<0||now>=lastClock);
        boolean valid=clockValid&&sample!=null&&sample.total>0
                &&sample.available>=0&&sample.available<=sample.total
                &&sample.threshold>=0&&sample.threshold<=sample.total
                &&sample.heapLimit>0&&sample.heapUsed>=0&&sample.heapUsed<=sample.heapLimit;
        Long elapsed=null;
        if(clockValid) {
            if(started<0) started=now;
            lastClock=now;
            // Both operands are nonnegative and now >= started, so this
            // subtraction cannot overflow, even at Long.MAX_VALUE.
            elapsed=now-started;
        }
        Map<String,Object> row=new LinkedHashMap<>();
        row.put("elapsed_ms",elapsed); row.put("valid",valid);
        if(valid) {
            haveValidSample=true;
            admissionReserve=Math.max(512*MIB,Math.min(1024*MIB,sample.total/16));
            runningReserve=Math.max(64*MIB,Math.min(256*MIB,sample.total/64));
            heapReserve=Math.min(16*MIB,Math.max(2*MIB,sample.heapLimit/8));
            long headroom=sample.available-sample.threshold;
            long heapHeadroom=sample.heapLimit-sample.heapUsed;
            minimumHeadroom=Math.min(minimumHeadroom,headroom);
            minimumHeapHeadroom=Math.min(minimumHeapHeadroom,heapHeadroom);
            row.put("available_bytes",sample.available); row.put("total_bytes",sample.total);
            row.put("threshold_bytes",sample.threshold); row.put("low_memory",sample.lowMemory);
            row.put("java_heap_used_bytes",sample.heapUsed); row.put("java_heap_limit_bytes",sample.heapLimit);
            row.put("system_headroom_bytes",headroom); row.put("java_heap_headroom_bytes",heapHeadroom);
        } else {
            invalidSamples=increment(invalidSamples);
            row.put("available_bytes",null); row.put("total_bytes",null);
            row.put("threshold_bytes",null); row.put("low_memory",null);
            row.put("java_heap_used_bytes",null); row.put("java_heap_limit_bytes",null);
            row.put("system_headroom_bytes",null); row.put("java_heap_headroom_bytes",null);
            if(!stopRequested) {
                if(admitted) stop("SERVER_MEMORY_TELEMETRY_UNAVAILABLE");
                else block("SERVER_MEMORY_TELEMETRY_UNAVAILABLE");
            }
        }
        recent.addLast(row);
        while(recent.size()>RETAINED_SAMPLES) recent.removeFirst();
        return valid;
    }

    /** Returns a defensive snapshot containing only bounded maps/lists and primitives. */
    synchronized Map<String,Object> snapshot() {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("format",1); result.put("status",status); result.put("reason",reason);
        result.put("scope","cooperative server admission and pressure observation; cannot guarantee prevention of Android process kills");
        result.put("sample_unavailable_policy","block_start_or_request_owned_cleanup");
        result.put("admitted",admitted); result.put("stop_requested",stopRequested);
        result.put("samples",samples); result.put("invalid_samples",invalidSamples);
        result.put("sample_interval_ms",SAMPLE_INTERVAL_MS);
        result.put("required_pressure_samples",REQUIRED_PRESSURE_SAMPLES);
        result.put("required_pressure_span_ms",PRESSURE_SPAN_MS);
        result.put("retained_sample_limit",RETAINED_SAMPLES);
        result.put("admission_reserve_bytes",haveValidSample?admissionReserve:null);
        result.put("running_reserve_bytes",haveValidSample?runningReserve:null);
        result.put("java_heap_reserve_bytes",haveValidSample?heapReserve:null);
        result.put("minimum_system_headroom_bytes",haveValidSample?minimumHeadroom:null);
        result.put("minimum_java_heap_headroom_bytes",haveValidSample?minimumHeapHeadroom:null);
        result.put("pressure_started_elapsed_ms",pressureStarted<0?null:pressureStarted-started);
        result.put("pressure_samples",pressureSamples);
        result.put("last_elapsed_ms",lastClock<0?null:lastClock-started);
        List<Map<String,Object>> copy=new ArrayList<>();
        for(Map<String,Object> row:recent) copy.add(new LinkedHashMap<>(row));
        result.put("recent_samples",copy);
        return result;
    }
}
