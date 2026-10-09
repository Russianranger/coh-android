#!/usr/bin/env python3
"""Run the shipped setup memory guard with deterministic host signals and time.

The full production class is compiled, rather than a model of its policy. These
checks do not allocate device-sized payloads or claim Android LMK prevention.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/SetupMemoryGuard.java'
CLASS = 'io.github.russianranger.cohdiagnostic.SetupMemoryGuardHost'

FIXTURE = r'''
package io.github.russianranger.cohdiagnostic;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.util.Map;

public final class SetupMemoryGuardHost {
    static final long MIB=1024L*1024;
    static void need(boolean value,String message) {
        if(!value)throw new AssertionError(message);
    }
    interface Action {void run()throws IOException;}
    interface Samples {SetupMemoryGuard.Sample sample(Environment env)throws IOException;}
    static IOException reject(Action action) {
        try{action.run();throw new AssertionError("Unsafe operation was admitted");}
        catch(IOException expected){return expected;}
    }
    static SetupMemoryGuard.Sample memory(long available,long total,long threshold,
                                          boolean low,long heapUsed,long heapLimit) {
        return new SetupMemoryGuard.Sample(available,total,threshold,low,heapUsed,heapLimit);
    }
    static SetupMemoryGuard.Sample healthy() {
        return memory(2*1024*MIB,4*1024*MIB,128*MIB,false,8*MIB,64*MIB);
    }
    static SetupMemoryGuard.Sample pressure() {
        return memory(500*MIB,4*1024*MIB,128*MIB,true,8*MIB,64*MIB);
    }
    static long number(SetupMemoryGuard guard,String key) {
        Object value=guard.receipt().get(key);
        need(value instanceof Number,"Missing numeric receipt field "+key);
        return ((Number)value).longValue();
    }
    static String status(SetupMemoryGuard guard) {
        return (String)guard.receipt().get("status");
    }
    static final class Environment implements SetupMemoryGuard.Sensor,SetupMemoryGuard.Clock,
            SetupMemoryGuard.Waiter,SetupMemoryGuard.Check,SetupMemoryGuard.Observer {
        long now,waited,maxSleep,extraWaitMillis,cancelAfter=Long.MAX_VALUE;
        int samples,sleeps,checks,io,syncCallbacks,paused,resumed;
        boolean cancelled,interruptWait,stuckClock,expectSyncBeforePressure,failObserver,failWaiter;
        Samples source=env->healthy();
        final InterruptedIOException cancellation=new InterruptedIOException("fixture operation cancelled");
        final IllegalStateException callbackFailure=new IllegalStateException("fixture pressure callback failed");
        final SetupMemoryGuard guard=new SetupMemoryGuard(this,this,this,this,this);
        public SetupMemoryGuard.Sample sample()throws IOException {samples++;return source.sample(this);}
        public long nowMillis(){return now;}
        public void sleep(long millis)throws InterruptedException {
            need(millis>0&&millis<=200,"Wait must use bounded cancellable slices");
            if(expectSyncBeforePressure)need(syncCallbacks==1&&number(guard,"active_dirty_bytes")==0,"Sync precedes pressure and pacing waits");
            sleeps++;maxSleep=Math.max(maxSleep,millis);
            if(failWaiter)throw callbackFailure;
            if(interruptWait)throw new InterruptedException("fixture interrupted");
            long actual=millis+extraWaitMillis;
            waited+=actual;if(!stuckClock)now+=actual;
            if(waited>=cancelAfter)cancelled=true;
        }
        public void check()throws IOException {checks++;if(cancelled)throw cancellation;}
        public void pressure(boolean active){if(active){paused++;if(failObserver)throw callbackFailure;}else resumed++;}
        void input(long bytes)throws IOException {guard.beforeIo();io++;guard.read(bytes);}
        void output(long bytes)throws IOException {guard.beforeIo();io++;guard.written(bytes,()->syncCallbacks++);}
    }
    static void healthyFlow()throws IOException {
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<10;i++){env.input(4096);env.output(4096);}
        env.guard.synced();env.guard.finishWrites();
        need(env.io==20&&env.waited==0,"Healthy streaming should proceed without pauses");
        need(number(env.guard,"read_bytes")==40960&&number(env.guard,"written_bytes")==40960,"Record exact byte totals");
        need(number(env.guard,"pressure_events")==0&&number(env.guard,"file_syncs")==1,"No invented pressure or syncs");
        need(number(env.guard,"samples")==env.samples&&number(env.guard,"checks")==env.checks,"Receipt counts actual callbacks");
        need(status(env.guard).equals("complete"),"Finish must publish complete status");
        need(env.guard.receipt().get("scope").toString().contains("cannot guarantee"),"Receipt must state the physical limitation");
    }
    static void initiallyLow() {
        Environment env=new Environment();env.source=ignored->pressure();
        reject(()->{env.guard.admit();env.input(65536);});
        need(env.io==0&&number(env.guard,"read_bytes")==0,"Initial pressure must prevent payload I/O");
        need(env.waited==15000&&env.maxSleep<=200,"Persistent pressure has a finite cancellable pause");
        need(status(env.guard).equals("memory_pressure_stopped"),"Record protective stop without claiming a kill");
    }
    static void recovers()throws IOException {
        Environment env=new Environment();env.source=e->e.now<600?pressure():healthy();
        env.guard.admit();env.input(65536);
        need(env.waited==600&&env.io==1,"Resume only after memory recovers");
        need(number(env.guard,"pressure_events")==1&&number(env.guard,"pressure_paused_ms")==600,"Record one real pressure pause");
        need(number(env.guard,"minimum_available_bytes")==500*MIB,"Keep the observed low-water mark");
        need(number(env.guard,"last_available_bytes")==2*1024*MIB,"Keep the actual recovery sample");
        need(env.paused==1&&env.resumed==1,"One pause and one actual recovery notification");
    }
    static void hysteresis()throws IOException {
        Environment env=new Environment();
        env.source=e->e.now<200?pressure():memory((e.now<800?703:704)*MIB,
                4*1024*MIB,128*MIB,false,8*MIB,64*MIB);
        env.guard.admit();
        need(env.waited==800,"Recovery must retain 64 MiB of system-memory hysteresis");
    }
    static void heapPressure()throws IOException {
        Environment env=new Environment();
        env.source=e->memory(2*1024*MIB,4*1024*MIB,128*MIB,false,
                (e.now<200?57:e.now<600?55:54)*MIB,64*MIB);
        env.guard.admit();
        need(env.waited==600,"Heap admission and recovery use separate bounded headroom");
        need(number(env.guard,"minimum_java_heap_headroom_bytes")==7*MIB,"Report actual heap pressure");
    }
    static void lowMemorySignal() {
        Environment env=new Environment();
        env.source=e->memory(2*1024*MIB,4*1024*MIB,128*MIB,true,8*MIB,64*MIB);
        reject(env.guard::admit);
        need(env.waited==15000,"Android lowMemory signal must block even with apparent free bytes");
    }
    static void totalPauseLimit()throws IOException {
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<59;i++) {
            final long resume=env.now+1000;
            env.source=e->e.now<resume?pressure():healthy();env.guard.checkpoint();
        }
        need(env.waited==59000,"Fixture creates separate short pressure events");
        env.source=e->pressure();reject(env.guard::checkpoint);
        need(env.waited==60000,"Repeated pressure must stop at the aggregate budget");
        need(number(env.guard,"pressure_events")==60,"Count separate pressure events");
    }
    static void overshootingWait()throws IOException {
        Environment env=new Environment();env.extraWaitMillis=15800;
        env.source=e->e.now==0?pressure():healthy();
        reject(env.guard::admit);
        need(env.waited==16000&&env.samples==1,"An oversleep beyond the episode budget must stop before a recovery probe");
        need(status(env.guard).equals("memory_pressure_stopped"),"Do not claim running after a deadline overrun");

        Environment total=new Environment();total.guard.admit();
        for(int i=0;i<59;i++) {
            final long resume=total.now+1000;
            total.source=e->e.now<resume?pressure():healthy();total.guard.checkpoint();
        }
        int sampled=total.samples;final long resume=total.now+1;
        total.source=e->e.now<resume?pressure():healthy();total.extraWaitMillis=1000;
        reject(total.guard::checkpoint);
        need(total.waited==60200&&total.samples==sampled+1,"An oversleep beyond aggregate budget stops before probing recovery");
        need(number(total.guard,"pressure_paused_ms")==60200,"Record actual elapsed pause rather than requested duration");
    }
    static void invalidSample(String mode) {
        Environment env=new Environment();
        switch(mode) {
            case "unavailable":env.source=e->{throw new IOException("fixture unavailable");};break;
            case "runtime_unavailable":env.source=e->{throw new IllegalStateException("fixture unavailable");};break;
            case "null":env.source=e->null;break;
            case "invalid_total":env.source=e->memory(0,0,0,false,8*MIB,64*MIB);break;
            case "invalid_available":env.source=e->memory(5*1024*MIB,4*1024*MIB,0,false,8*MIB,64*MIB);break;
            case "invalid_threshold":env.source=e->memory(2*1024*MIB,4*1024*MIB,-1,false,8*MIB,64*MIB);break;
            case "invalid_heap":env.source=e->memory(2*1024*MIB,4*1024*MIB,0,false,65*MIB,64*MIB);break;
            default:throw new AssertionError(mode);
        }
        reject(()->{env.guard.admit();env.input(1);});
        need(env.io==0&&env.waited==0,"Unavailable measurements must fail before payload I/O");
        need(status(env.guard).equals("unavailable"),"Receipt must distinguish unavailable data from low memory");
    }
    static void failedPressureCallback(String mode)throws IOException {
        Environment env=new Environment();env.source=e->pressure();
        env.failObserver=mode.equals("observer_failure");env.failWaiter=mode.equals("waiter_failure");
        try {
            env.guard.admit();env.input(65536);env.guard.finishWrites();
            throw new AssertionError("Failed pressure callback admitted payload I/O");
        } catch(IllegalStateException expected) {
            need(expected==env.callbackFailure,"Preserve the actual pressure callback failure");
        }
        need(status(env.guard).equals("paused")&&env.guard.cleanupShouldDefer(),"Failed low-memory callback must defer bulk cleanup");
        need(env.io==0&&number(env.guard,"read_bytes")==0&&number(env.guard,"written_bytes")==0,"Callback failure prevents all payload I/O");
        need(env.paused==1&&env.resumed==0&&env.samples==1,"Failed callback cannot claim recovery or completion");
    }
    static void cancelledBeforeAdmission() {
        Environment env=new Environment();env.cancelled=true;
        need(reject(env.guard::admit)==env.cancellation,"Keep operation cancellation identity");
        need(env.samples==0&&env.waited==0,"Cancellation precedes sampling and waiting");
    }
    static void cancelledDuringPause() {
        Environment env=new Environment();env.source=e->pressure();env.cancelAfter=200;
        need(reject(env.guard::admit)==env.cancellation,"Do not convert cancellation into unavailable memory");
        need(env.waited==200&&env.samples==1,"Cancellation must stop at the next bounded wait slice");
        need(!status(env.guard).equals("unavailable"),"Cancellation is a different outcome");
        need(env.paused==1&&env.resumed==0,"Cancelled pressure must not claim recovery");
    }
    static void interruptedPause() {
        Environment env=new Environment();env.source=e->pressure();env.interruptWait=true;
        need(reject(env.guard::admit) instanceof InterruptedIOException,"Interrupted wait retains cancellation type");
        need(Thread.currentThread().isInterrupted(),"Preserve worker interrupt status");
        Thread.interrupted();
        need(env.samples==1,"No sampling after interrupt");
    }
    static void polling()throws IOException {
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<40;i++)env.guard.beforeIo();
        need(env.samples==1,"Repeated small operations must avoid unbounded memory polls");
        env.guard.read(MIB-1);need(env.samples==1,"Poll byte boundary is exact");
        env.guard.read(1);need(env.samples==2,"One MiB triggers a new memory sample");
        env.now=249;env.guard.beforeIo();need(env.samples==2,"Poll time interval is bounded, not every chunk");
        env.now=250;env.guard.beforeIo();need(env.samples==3,"250 ms triggers a fresh sample");
        need(number(env.guard,"read_bytes")==MIB,"Polling must not inflate source bytes");
    }
    static void ioPressure()throws IOException {
        Environment env=new Environment();env.guard.admit();env.source=e->pressure();env.now=250;
        reject(()->env.input(65536));
        need(env.io==0&&number(env.guard,"read_bytes")==0,"Memory change stops the next input before it is touched");
    }
    static void syncWindow()throws IOException {
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<127;i++)env.output(65536);
        need(!env.guard.syncNeeded(),"Do not sync before the active write window");
        env.output(65536);need(!env.guard.syncNeeded()&&env.syncCallbacks==1,"Sync the active file automatically at eight MiB");
        need(number(env.guard,"maximum_active_dirty_bytes")==8*MIB,"Bound active dirty bytes for actual chunk size");
        need(number(env.guard,"active_dirty_bytes")==0,"Successful sync clears active dirty bytes");
        need(number(env.guard,"file_syncs")==1&&number(env.guard,"paced_write_windows")==1,"Record actual sync and pacing independently");
        need(env.waited==250,"Eight MiB also completes two minimum-duration combined I/O windows");
    }
    static void syncBeforePressure()throws IOException {
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<127;i++)env.output(65536);
        env.expectSyncBeforePressure=true;
        env.source=e->{need(e.syncCallbacks==1,"Active write sync must precede the triggering memory probe");return e.now<200?pressure():healthy();};
        env.output(65536);
        need(env.waited==350&&env.paused==1&&env.resumed==1,"Flush before bounded pressure and retained write pacing waits");
    }
    static void syncFailure()throws IOException {
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<127;i++)env.output(65536);
        IOException failure=new IOException("fixture flush failed");
        need(reject(()->env.guard.written(65536,()->{throw failure;}))==failure,"Keep the actual flush failure");
        need(number(env.guard,"file_syncs")==0&&number(env.guard,"active_dirty_bytes")==8*MIB,"Failed flush cannot claim clean data");
        need(env.waited==125,"Failed flush cannot continue into pacing beyond the preceding completed I/O window");
    }
    static void pacingAcrossFiles()throws IOException {
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<256;i++){env.output(65536);env.guard.synced();}
        need(number(env.guard,"written_bytes")==16*MIB,"Keep global write totals across file closure");
        need(number(env.guard,"file_syncs")==256&&number(env.guard,"paced_write_windows")==2,"Small closed files must still receive global pacing");
        need(number(env.guard,"maximum_active_dirty_bytes")==65536&&env.waited==500,"Closed files do not erase the aggregate I/O pacing window");
    }
    static void cancelledDuringPacing()throws IOException {
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<127;i++)env.output(65536);
        env.cancelAfter=env.waited+25;
        need(reject(()->env.output(65536))==env.cancellation,"Pacing is operation-cancellable");
        need(env.waited==150&&number(env.guard,"paced_write_windows")==1,"Stop after the retained write pacing slice, following one completed aggregate window");
    }
    static void finishRechecks()throws IOException {
        Environment env=new Environment();env.guard.admit();env.source=e->pressure();
        reject(env.guard::finishWrites);
        need(status(env.guard).equals("memory_pressure_stopped"),"Finish cannot publish complete through pressure");
        Environment cancelled=new Environment();cancelled.guard.admit();cancelled.cancelled=true;
        need(reject(cancelled.guard::finishWrites)==cancelled.cancellation,"Finish must retain cancellation");
    }
    static void clocks(String mode)throws IOException {
        Environment env=new Environment();
        if(mode.equals("backward_clock")){env.now=10;env.guard.admit();env.now=9;reject(env.guard::beforeIo);}
        else if(mode.equals("negative_clock")){env.now=-1;reject(env.guard::admit);}
        else{env.stuckClock=true;env.source=e->pressure();reject(env.guard::admit);}
        need(status(env.guard).equals("unavailable"),"Unusable clocks must fail closed");
        need(env.sleeps<=1,"An unmoving clock must not spin forever");
    }
    static void byteLimits()throws Exception {
        Environment env=new Environment();env.guard.admit();
        reject(()->env.guard.read(Long.MAX_VALUE));reject(()->env.guard.written(Long.MAX_VALUE,()->{}));
        need(number(env.guard,"read_bytes")==0&&number(env.guard,"written_bytes")==0&&env.waited==0,"Unbounded callback must fail before counters and pacing loops");
        java.lang.reflect.Field counter=SetupMemoryGuard.class.getDeclaredField("readBytes");counter.setAccessible(true);counter.setLong(env.guard,Long.MAX_VALUE);
        reject(()->env.guard.read(1));
        need(number(env.guard,"read_bytes")==Long.MAX_VALUE,"Byte overflow cannot wrap or erase prior count");
        Environment negative=new Environment();negative.guard.admit();
        reject(()->negative.guard.read(-1));reject(()->negative.guard.written(-1,()->{}));
        need(number(negative.guard,"read_bytes")==0&&number(negative.guard,"written_bytes")==0,"Negative counters cannot authorize streaming");
    }
    static void reservePolicy()throws IOException {
        Environment env=new Environment();env.guard.admit();
        need(number(env.guard,"last_reserve_bytes")==512*MIB,"Small devices retain the reserve floor");
        env.source=e->memory(4*1024*MIB,16*1024*MIB,128*MIB,false,8*MIB,64*MIB);env.guard.checkpoint();
        need(number(env.guard,"last_reserve_bytes")==1024*MIB,"Large devices use a capped proportional reserve");
        env.source=e->memory(4*1024*MIB,64*1024*MIB,128*MIB,false,8*MIB,64*MIB);env.guard.checkpoint();
        need(number(env.guard,"last_reserve_bytes")==1024*MIB,"Reserve must remain capped on larger devices");
        env.source=e->memory(Long.MAX_VALUE,Long.MAX_VALUE,Long.MAX_VALUE,false,8*MIB,64*MIB);
        reject(env.guard::checkpoint);
        need(status(env.guard).equals("memory_pressure_stopped"),"Overflowing required headroom must never admit I/O");
    }
    static void receiptSnapshot()throws IOException {
        Environment env=new Environment();Map<String,Object> early=env.guard.receipt();
        need(early.get("minimum_available_bytes")==null&&early.get("last_available_bytes")==null,"No fabricated measurements before sampling");
        env.guard.admit();Map<String,Object> receipt=env.guard.receipt();receipt.put("status","fixture mutation");
        env.guard.read(1);
        need(status(env.guard).equals("running")&&((Number)early.get("read_bytes")).longValue()==0,"Exported receipts are independent snapshots");
    }
    public static void main(String[] args)throws Exception {
        String mode=args[0];
        switch(mode) {
            case "healthy":healthyFlow();break;
            case "initially_low":initiallyLow();break;
            case "recovers":recovers();break;
            case "hysteresis":hysteresis();break;
            case "heap_pressure":heapPressure();break;
            case "low_memory":lowMemorySignal();break;
            case "total_pause":totalPauseLimit();break;
            case "overshooting_wait":overshootingWait();break;
            case "observer_failure":case "waiter_failure":failedPressureCallback(mode);break;
            case "cancel_before":cancelledBeforeAdmission();break;
            case "cancel_pause":cancelledDuringPause();break;
            case "interrupt_pause":interruptedPause();break;
            case "polling":polling();break;
            case "io_pressure":ioPressure();break;
            case "sync_window":syncWindow();break;
            case "sync_pressure":syncBeforePressure();break;
            case "sync_failure":syncFailure();break;
            case "pacing_files":pacingAcrossFiles();break;
            case "cancel_pacing":cancelledDuringPacing();break;
            case "finish":finishRechecks();break;
            case "backward_clock":case "negative_clock":case "stuck_clock":clocks(mode);break;
            case "byte_limits":byteLimits();break;
            case "reserve":reservePolicy();break;
            case "receipt":receiptSnapshot();break;
            default:invalidSample(mode);
        }
        System.out.println("PASS "+mode);
    }
}
'''


class SetupMemoryGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-setup-memory-guard-')
        cls.directory = Path(cls.temporary.name)
        cls.addClassCleanup(cls.temporary.cleanup)
        fixture = cls.directory / 'SetupMemoryGuardHost.java'
        fixture.write_text(FIXTURE)
        result = subprocess.run(
            ['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
             '-d', str(cls.directory), str(SOURCE), str(fixture)],
            capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def check(self, *scenarios):
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = subprocess.run(
                    ['java', '-Xmx32m', '-cp', str(self.directory), CLASS, scenario],
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertEqual('PASS ' + scenario, result.stdout.strip())

    def test_healthy_streaming_records_actual_counters_without_pressure_pause(self):
        self.check('healthy')

    def test_initial_pressure_prevents_io_and_stops_at_persistent_limit(self):
        self.check('initially_low', 'low_memory')

    def test_recovered_memory_resumes_after_a_bounded_pause(self):
        self.check('recovers')

    def test_system_and_java_heap_recovery_require_hysteresis(self):
        self.check('hysteresis', 'heap_pressure')

    def test_repeated_short_pressure_events_obey_total_pause_limit(self):
        self.check('total_pause')

    def test_waiter_overshoot_stops_before_probing_recovery(self):
        self.check('overshooting_wait')

    def test_unavailable_or_invalid_samples_fail_before_payload_io(self):
        self.check('unavailable', 'runtime_unavailable', 'null', 'invalid_total',
                   'invalid_available', 'invalid_threshold', 'invalid_heap',
                   'observer_failure', 'waiter_failure')

    def test_cancellation_is_checked_before_admission_and_during_pause(self):
        self.check('cancel_before', 'cancel_pause', 'interrupt_pause')

    def test_polling_is_bounded_by_time_and_source_byte_intervals(self):
        self.check('polling', 'io_pressure')

    def test_active_large_file_sync_window_records_dirty_bytes_and_acknowledgment(self):
        self.check('sync_window', 'sync_pressure', 'sync_failure')

    def test_global_write_pacing_survives_small_file_syncs(self):
        self.check('pacing_files', 'cancel_pacing')

    def test_finish_requires_fresh_memory_and_cancellation_checks(self):
        self.check('finish')

    def test_invalid_clocks_cannot_leave_an_unbounded_pause(self):
        self.check('backward_clock', 'negative_clock', 'stuck_clock')

    def test_byte_counters_reject_overflow_and_negative_counts(self):
        self.check('byte_limits')

    def test_memory_reserve_floor_and_cap_do_not_overflow(self):
        self.check('reserve')

    def test_receipts_are_truthful_independent_snapshots(self):
        self.check('receipt')


if __name__ == '__main__':
    unittest.main()
