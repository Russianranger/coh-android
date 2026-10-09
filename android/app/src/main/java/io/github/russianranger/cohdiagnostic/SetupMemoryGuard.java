package io.github.russianranger.cohdiagnostic;

import java.io.IOException;
import java.io.InterruptedIOException;
import java.util.LinkedHashMap;
import java.util.Map;

/** One setup operation's bounded, cooperative I/O and memory admission control. */
final class SetupMemoryGuard {
    interface Sensor { Sample sample() throws IOException; }
    interface Clock { long nowMillis(); }
    interface Waiter { void sleep(long millis) throws InterruptedException; }
    interface Check { void check() throws IOException; }
    interface Observer { void pressure(boolean paused); }
    interface Sync { void sync() throws IOException; }
    static final class Sample {
        final long available,total,threshold,heapUsed,heapLimit;
        final boolean lowMemory;
        Sample(long available,long total,long threshold,boolean lowMemory,long heapUsed,long heapLimit) {
            this.available=available;this.total=total;this.threshold=threshold;
            this.lowMemory=lowMemory;this.heapUsed=heapUsed;this.heapLimit=heapLimit;
        }
    }
    private static final long MIB=1024L*1024, POLL_BYTES=MIB, POLL_MS=250;
    private static final long WRITE_WINDOW=8*MIB, PACE_MS=25, PAUSE_SLICE_MS=200;
    private static final long IO_WINDOW=4*MIB, IO_HEALTHY_MS=125, IO_PRESSURE_MS=500, MAX_IO_CALLBACK_BYTES=64*MIB;
    private static final long MAX_PRESSURE_PAUSE_MS=15000, MAX_TOTAL_PAUSE_MS=60000;
    private final Sensor sensor;
    private final Clock clock;
    private final Waiter waiter;
    private final Check check;
    private final Observer observer;
    private long readBytes,writtenBytes,sinceSample,dirtyBytes,maxDirtyBytes,writeWindowBytes;
    private long samples,checks,syncs,paceWindows,pressureEvents,pressureSamples,pausedMillis;
    private long lastSampleTime=-1,lastClock=-1,minAvailable=Long.MAX_VALUE,minHeapHeadroom=Long.MAX_VALUE;
    private long available,total,threshold,reserve,heapUsed,heapLimit;
    private boolean lowMemory;
    private long ioWindowBytes,ioWindowStarted=-1,ioPacedWindows,ioPacedMillis;
    private String status="not_started";

    SetupMemoryGuard(Sensor sensor,Clock clock,Waiter waiter,Check check) {
        this(sensor,clock,waiter,check,paused->{});
    }
    SetupMemoryGuard(Sensor sensor,Clock clock,Waiter waiter,Check check,Observer observer) {
        if(sensor==null||clock==null||waiter==null||check==null||observer==null)throw new IllegalArgumentException("Missing setup memory control");
        this.sensor=sensor;this.clock=clock;this.waiter=waiter;this.check=check;this.observer=observer;
    }
    private void cancellation() throws IOException {
        checks++;
        try {check.check();}
        catch(IOException failure){status=failure instanceof InterruptedIOException?"cancelled":"stopped";throw failure;}
    }
    private long now() throws IOException {
        long value=clock.nowMillis();
        if(value<0||value<lastClock){status="unavailable";throw new IOException("Setup memory clock is unavailable");}
        lastClock=value;return value;
    }
    private Sample sample() throws IOException {
        cancellation();
        Sample value;
        try { value=sensor.sample(); }
        catch(IOException|RuntimeException failure) {status="unavailable";throw new IOException("Setup memory information is unavailable; setup stopped safely",failure);}
        if(value==null||value.total<=0||value.available<0||value.available>value.total
                ||value.threshold<0||value.threshold>value.total||value.heapLimit<=0
                ||value.heapUsed<0||value.heapUsed>value.heapLimit) {
            status="unavailable";throw new IOException("Setup memory information is unavailable; setup stopped safely");
        }
        samples++;available=value.available;total=value.total;threshold=value.threshold;
        lowMemory=value.lowMemory;
        heapUsed=value.heapUsed;heapLimit=value.heapLimit;
        reserve=Math.max(512*MIB,Math.min(1024*MIB,total/16));
        minAvailable=Math.min(minAvailable,available);minHeapHeadroom=Math.min(minHeapHeadroom,heapLimit-heapUsed);
        lastSampleTime=now();sinceSample=0;return value;
    }
    private boolean healthy(Sample value,boolean resuming) {
        long extra=resuming?64*MIB:0;
        long heapReserve=Math.max(2*MIB,Math.min(16*MIB,heapLimit/8));
        if(resuming)heapReserve=Math.min(heapLimit,heapReserve+2*MIB);
        return !value.lowMemory&&available>=threshold&&available-threshold>=reserve+extra
                &&heapLimit-heapUsed>=heapReserve;
    }
    private void pause(long millis) throws IOException {
        cancellation();
        try {waiter.sleep(millis);}
        catch(InterruptedException failure) {Thread.currentThread().interrupt();throw new InterruptedIOException("Runtime setup cancelled");}
        cancellation();
    }
    void admit() throws IOException { checkpoint(); }
    void checkpoint() throws IOException {
        Sample value=sample();
        if(healthy(value,false)){status="running";return;}
        status="paused";pressureEvents++;observer.pressure(true);
        long started=now();
        while(true) {
            pressureSamples++;
            long elapsed=now()-started;
            if(elapsed>=MAX_PRESSURE_PAUSE_MS||pausedMillis>=MAX_TOTAL_PAUSE_MS) {
                status="memory_pressure_stopped";
                throw new IOException("Runtime setup stopped safely because memory remained low; the previous runtime and saved profile are preserved");
            }
            long slice=Math.min(PAUSE_SLICE_MS,Math.min(MAX_PRESSURE_PAUSE_MS-elapsed,MAX_TOTAL_PAUSE_MS-pausedMillis));
            long before=now();pause(slice);long after=now();
            // A waiter must advance its monotonic clock; otherwise it could
            // spin forever while reporting a falsely bounded pressure pause.
            if(after<=before){status="unavailable";throw new IOException("Setup memory wait clock is unavailable");}
            pausedMillis=add(pausedMillis,after-before);
            if(after-started>=MAX_PRESSURE_PAUSE_MS||pausedMillis>=MAX_TOTAL_PAUSE_MS) {
                status="memory_pressure_stopped";
                throw new IOException("Runtime setup stopped safely because memory remained low; the previous runtime and saved profile are preserved");
            }
            value=sample();
            if(healthy(value,true)){status="running";observer.pressure(false);return;}
        }
    }
    void beforeIo() throws IOException {
        cancellation();long value=now();
        if(lastSampleTime<0||sinceSample>=POLL_BYTES||value-lastSampleTime>=POLL_MS)checkpoint();
        if(ioWindowStarted<0)ioWindowStarted=now();
    }
    private long add(long current,long amount) throws IOException {
        if(amount<0||current>Long.MAX_VALUE-amount)throw new IOException("Runtime setup byte counter exceeds limits");
        return current+amount;
    }
    void read(long bytes) throws IOException {
        boundedIo(bytes);readBytes=add(readBytes,bytes);sinceSample=add(sinceSample,bytes);beforeIo();paceIo(bytes);
    }
    void written(long bytes,Sync sync) throws IOException {
        boundedIo(bytes);
        writtenBytes=add(writtenBytes,bytes);sinceSample=add(sinceSample,bytes);
        dirtyBytes=add(dirtyBytes,bytes);maxDirtyBytes=Math.max(maxDirtyBytes,dirtyBytes);
        writeWindowBytes=add(writeWindowBytes,bytes);
        // Flush an active large file before any pressure wait or abort. Small
        // files are additionally synced on close by each streaming caller.
        if(syncNeeded()) {
            if(sync==null)throw new IOException("Missing runtime setup file sync control");
            sync.sync();synced();
        }
        beforeIo();
        while(writeWindowBytes>=WRITE_WINDOW) {
            writeWindowBytes-=WRITE_WINDOW;paceWindows++;pause(PACE_MS);beforeIo();
        }
        paceIo(bytes);
    }
    private void boundedIo(long bytes) throws IOException {
        if(bytes<0||bytes>MAX_IO_CALLBACK_BYTES)throw new IOException("Runtime setup I/O callback exceeds its bound");
    }
    private void paceIo(long bytes) throws IOException {
        long time=now();
        if(ioWindowStarted<0)ioWindowStarted=time;
        ioWindowBytes=add(ioWindowBytes,bytes);
        while(ioWindowBytes>=IO_WINDOW) {
            long interval=available-threshold<2*reserve?IO_PRESSURE_MS:IO_HEALTHY_MS;
            long elapsed=now()-ioWindowStarted;
            while(elapsed<interval) {
                long before=now();pause(Math.min(PAUSE_SLICE_MS,interval-elapsed));
                long after=now();
                if(after<=before){status="unavailable";throw new IOException("Setup I/O wait clock is unavailable");}
                ioPacedMillis=add(ioPacedMillis,after-before);beforeIo();
                elapsed=now()-ioWindowStarted;
                interval=available-threshold<2*reserve?IO_PRESSURE_MS:IO_HEALTHY_MS;
            }
            ioWindowBytes-=IO_WINDOW;ioPacedWindows++;ioWindowStarted=now();
        }
    }
    boolean syncNeeded() {return dirtyBytes>=WRITE_WINDOW;}
    boolean cleanupShouldDefer() {return status.equals("paused")||status.equals("memory_pressure_stopped")||status.equals("unavailable");}
    void synced() {dirtyBytes=0;syncs++;}
    void finishWrites() throws IOException {checkpoint();status="complete";}
    Map<String,Object> receipt() {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("format",1);result.put("status",status);
        result.put("scope","cooperative setup-only polling and paced streaming; cannot guarantee prevention of Android process kills");
        result.put("sample_unavailable_policy","stop_before_more_setup_io");
        result.put("poll_bytes",POLL_BYTES);result.put("poll_interval_ms",POLL_MS);
        result.put("persistent_pressure_limit_ms",MAX_PRESSURE_PAUSE_MS);result.put("total_pressure_pause_limit_ms",MAX_TOTAL_PAUSE_MS);
        result.put("resume_hysteresis_bytes",64*MIB);result.put("write_window_bytes",WRITE_WINDOW);
        result.put("write_window_pace_ms",PACE_MS);result.put("file_sync_policy","each closed regular file; active large file at write window");
        result.put("combined_io_window_bytes",IO_WINDOW);result.put("maximum_io_callback_bytes",MAX_IO_CALLBACK_BYTES);
        result.put("healthy_combined_io_bytes_per_second",32*MIB);result.put("pressure_combined_io_bytes_per_second",8*MIB);
        result.put("combined_io_paced_windows",ioPacedWindows);result.put("combined_io_paced_ms",ioPacedMillis);
        result.put("checks",checks);result.put("samples",samples);result.put("read_bytes",readBytes);
        result.put("read_bytes_scope","aggregate guarded input bytes, including compressed source and decoded archive reads; not unique storage bytes");
        result.put("written_bytes",writtenBytes);result.put("file_syncs",syncs);result.put("paced_write_windows",paceWindows);
        result.put("active_dirty_bytes",dirtyBytes);result.put("maximum_active_dirty_bytes",maxDirtyBytes);
        result.put("pressure_events",pressureEvents);result.put("pressure_samples",pressureSamples);result.put("pressure_paused_ms",pausedMillis);
        result.put("minimum_available_bytes",minAvailable==Long.MAX_VALUE?null:minAvailable);
        result.put("minimum_java_heap_headroom_bytes",minHeapHeadroom==Long.MAX_VALUE?null:minHeapHeadroom);
        result.put("last_available_bytes",samples==0?null:available);result.put("last_total_bytes",samples==0?null:total);
        result.put("last_threshold_bytes",samples==0?null:threshold);result.put("last_reserve_bytes",samples==0?null:reserve);
        result.put("last_low_memory",samples==0?null:lowMemory);
        result.put("last_java_heap_used_bytes",samples==0?null:heapUsed);result.put("last_java_heap_limit_bytes",samples==0?null:heapLimit);
        return result;
    }
}
