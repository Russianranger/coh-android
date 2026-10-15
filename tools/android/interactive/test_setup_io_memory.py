#!/usr/bin/env python3
"""Execute shipped setup I/O throttling against deterministic host signals.

The complete Java guard is compiled and exercised. Host timing and fake Android
signals verify policy and evidence, not physical LMK prevention or throughput.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_storage_ui import production_method
from test_setup_service import SERVICE_HOST


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/SetupMemoryGuard.java'
CLASS = 'io.github.russianranger.cohdiagnostic.SetupIoMemoryHost'
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'


GUARD_HOST = r'''
package io.github.russianranger.cohdiagnostic;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;

class JSONObject {
    static final Map<String,Map<String,Object>> encoded=new LinkedHashMap<>();static int serial;
    final Map<String,Object> values=new LinkedHashMap<>();
    JSONObject(){}
    JSONObject(Map<String,Object> map){values.putAll(map);}
    JSONObject(String raw){Map<String,Object> source=encoded.get(raw);if(source==null)throw new IllegalArgumentException("invalid fixture JSON");values.putAll(source);}
    JSONObject put(String key,Object value){values.put(key,value);return this;}
    Object get(String key){return values.get(key);}
    public String toString(){String key="fixture-json-"+(++serial);encoded.put(key,new LinkedHashMap<>(values));return key;}
}
class DiagnosticRuntime {
    JSONObject setupReceipt;SetupMemoryGuard setupControl;
    GETTER_METHODS
}
class RuntimeProgress {
    DiagnosticRuntime installer;
    BRIDGE_METHOD
}

public final class SetupIoMemoryHost {
    static final long MIB=1024L*1024,CHUNK=65536;
    static void need(boolean value,String message){if(!value)throw new AssertionError(message);}
    interface Action {void run()throws IOException;}
    interface Signal {SetupMemoryGuard.Sample get(Environment value)throws IOException;}
    static IOException reject(Action action){
        try{action.run();throw new AssertionError("Unsafe operation accepted");}
        catch(IOException failure){return failure;}
    }
    static long number(SetupMemoryGuard guard,String key){
        Object value=guard.receipt().get(key);
        need(value instanceof Number,"Missing numeric receipt field: "+key);
        return ((Number)value).longValue();
    }
    static String status(SetupMemoryGuard guard){return (String)guard.receipt().get("status");}
    static SetupMemoryGuard.Sample memory(long available,boolean low){
        return new SetupMemoryGuard.Sample(available,16*1024*MIB,128*MIB,low,64*MIB,256*MIB);
    }
    static SetupMemoryGuard.Sample healthy(){return memory(4*1024*MIB,false);}
    static SetupMemoryGuard.Sample adaptive(){return memory(1536*MIB,false);}
    static SetupMemoryGuard.Sample low(){return memory(512*MIB,true);}
    static final class Environment implements SetupMemoryGuard.Sensor,SetupMemoryGuard.Clock,
            SetupMemoryGuard.Waiter,SetupMemoryGuard.Check,SetupMemoryGuard.Observer {
        long now,waited,cancelAt=Long.MAX_VALUE,oversleep;
        int checks,samples,syncs,paused,resumed,io;
        boolean stuck,interrupted,requireSynced;
        final List<Long> waits=new ArrayList<>();
        Signal signal=value->healthy();
        final InterruptedIOException stop=new InterruptedIOException("fixture Stop request");
        final SetupMemoryGuard guard=new SetupMemoryGuard(this,this,this,this,this);
        public SetupMemoryGuard.Sample sample()throws IOException{samples++;return signal.get(this);}
        public long nowMillis(){return now;}
        public void sleep(long millis)throws InterruptedException{
            need(millis>0&&millis<=200,"Setup waits must remain cancellable every 200 ms");
            if(requireSynced)need(syncs==1&&number(guard,"active_dirty_bytes")==0,"Active large file must sync before pause");
            if(interrupted)throw new InterruptedException("fixture worker interrupt");
            waits.add(millis);long actual=millis+oversleep;waited+=actual;if(!stuck)now+=actual;
        }
        public void check()throws IOException{checks++;if(waited>=cancelAt)throw stop;}
        public void pressure(boolean value){if(value)paused++;else resumed++;}
        void input(long bytes)throws IOException{guard.beforeIo();io++;guard.read(bytes);}
        void output(long bytes)throws IOException{guard.beforeIo();io++;guard.written(bytes,()->syncs++);}
        void reads(long bytes)throws IOException{
            while(bytes>0){long part=Math.min(CHUNK,bytes);input(part);bytes-=part;}
        }
        void writes(long bytes)throws IOException{
            while(bytes>0){long part=Math.min(CHUNK,bytes);output(part);bytes-=part;}
        }
    }
    static void readsOnly()throws IOException{
        Environment env=new Environment();env.guard.admit();env.reads(4*MIB);
        need(env.now==125&&env.waited==125,"Four MiB guarded reads need a 125 ms window");
        need(env.syncs==0&&number(env.guard,"written_bytes")==0,"Read pacing cannot invent writes or file syncs");
        need(number(env.guard,"read_bytes")==4*MIB,"Read accounting is byte exact");
        need(number(env.guard,"pressure_events")==0,"Healthy I/O pacing is not a pressure event");
    }
    static void mixed()throws IOException{
        Environment env=new Environment();env.guard.admit();env.reads(2*MIB);env.writes(2*MIB);
        need(env.now==125,"Reads and writes share one aggregate four MiB budget");
        need(number(env.guard,"read_bytes")==2*MIB&&number(env.guard,"written_bytes")==2*MIB,"Mixed bytes retain their separate totals");
        need(env.syncs==0&&number(env.guard,"active_dirty_bytes")==2*MIB,"Combined pacing preserves the eight MiB sync window");
    }
    static void partial()throws IOException{
        Environment env=new Environment();env.guard.admit();env.reads(2*MIB);env.writes(2*MIB-1);
        need(env.waited==0,"A partial four MiB window cannot invent completed work");
        env.output(1);need(env.waited==125,"The last byte completes the shared window");
    }
    static void elapsedWork()throws IOException{
        Environment env=new Environment();env.guard.admit();env.guard.beforeIo();env.now=100;env.guard.read(4*MIB);
        need(env.now==125&&env.waited==25,"Only the unspent part of the healthy window is slept");
        env.now+=1000;env.reads(4*MIB);
        need(env.now==1125&&env.waited==25,"Slow storage already satisfies pacing; no additional sleep");
        env.reads(4*MIB);need(env.now==1250&&env.waited==150,"Idle time cannot authorize the following fast window");
    }
    static void writesAndSync()throws IOException{
        Environment env=new Environment();env.guard.admit();env.writes(8*MIB-CHUNK);
        need(env.syncs==0&&number(env.guard,"active_dirty_bytes")==8*MIB-CHUNK,"Do not sync before the active eight MiB boundary");
        env.requireSynced=true;env.output(CHUNK);
        need(env.syncs==1&&number(env.guard,"active_dirty_bytes")==0,"Flush the actual active file at eight MiB");
        need(number(env.guard,"file_syncs")==1&&number(env.guard,"paced_write_windows")==1,"Legacy sync and write pacing remain explicit");
        need(env.now>=250&&env.now<=275,"Combined and retained write pacing impose bounded elapsed time");
        need(number(env.guard,"maximum_active_dirty_bytes")==8*MIB,"Chunked dirty writes retain their existing upper bound");
    }
    static void closedFiles()throws IOException{
        Environment env=new Environment();env.guard.admit();
        for(int i=0;i<256;i++){env.output(CHUNK);env.guard.synced();}
        need(env.now>=500&&env.now<=550,"Closing small files must not reset global aggregate pacing");
        need(number(env.guard,"written_bytes")==16*MIB&&number(env.guard,"file_syncs")==256,"Closed file receipts remain actual counts");
        need(number(env.guard,"maximum_active_dirty_bytes")==CHUNK&&number(env.guard,"paced_write_windows")==2,"Dirty accounting and old pacing survive small file closure");
    }
    static void adaptiveRate()throws IOException{
        Environment env=new Environment();env.signal=value->adaptive();env.guard.admit();env.reads(4*MIB);
        need(env.now==500&&env.waits.size()==3,"Admitted marginal headroom uses a 500 ms aggregate window");
        need(env.waits.get(0)==200&&env.waits.get(1)==200&&env.waits.get(2)==100,"Adaptive waits use bounded cancellation slices");
        need(number(env.guard,"pressure_events")==0&&status(env.guard).equals("running"),"Adaptive throttling is admitted work, not a low-memory stop");
    }
    static void adaptiveBoundary()throws IOException{
        Environment normal=new Environment();normal.signal=value->memory(128*MIB+2048*MIB,false);normal.guard.admit();normal.reads(4*MIB);
        need(normal.now==125,"Exactly twice the system reserve retains normal pacing");
        Environment marginal=new Environment();marginal.signal=value->memory(128*MIB+2048*MIB-1,false);marginal.guard.admit();marginal.reads(4*MIB);
        need(marginal.now==500,"Below twice the reserve selects marginal-headroom pacing");
    }
    static void adaptiveRechecks()throws IOException{
        Environment env=new Environment();env.signal=value->value.now<500?adaptive():healthy();env.guard.admit();env.reads(4*MIB);
        need(env.now==500,"Initial adaptive window must complete");env.reads(4*MIB);
        need(env.now==625,"Fresh healthy memory resumes the normal window");
        need(number(env.guard,"minimum_available_bytes")==1536*MIB&&number(env.guard,"last_available_bytes")==4*1024*MIB,"Retain sampled low-water and recovery evidence");
    }
    static void cancellation()throws IOException{
        Environment env=new Environment();env.signal=value->adaptive();env.guard.admit();env.cancelAt=200;
        IOException failure=reject(()->{env.reads(4*MIB);env.input(CHUNK);});
        need(failure==env.stop&&env.waited==200,"Stop request interrupts an adaptive wait at its next slice");
        need(number(env.guard,"read_bytes")==4*MIB&&env.io==64,"No following I/O after cancellation");
        need(status(env.guard).equals("cancelled"),"Receipt distinguishes cancellation from memory pressure");
    }
    static void pressureRecovery()throws IOException{
        Environment env=new Environment();env.signal=value->value.now<600?low():adaptive();env.guard.admit();env.reads(4*MIB);
        need(env.paused==1&&env.resumed==1&&number(env.guard,"pressure_paused_ms")==600,"Existing pressure pause and recovery remain unchanged");
        need(env.now>=600&&env.now<=1100,"Recovered adaptive work is bounded without duplicating pressure elapsed time");
        need(number(env.guard,"read_bytes")==4*MIB&&status(env.guard).equals("running"),"Only admitted recovered I/O is counted");
        need(Boolean.FALSE.equals(env.guard.receipt().get("last_low_memory")),"Recovery exports the actual last Android lowMemory signal");
    }
    static void persistentPressure()throws IOException{
        Environment env=new Environment();env.signal=value->low();
        reject(()->{env.guard.admit();env.reads(4*MIB);});
        need(env.now==15000&&env.io==0,"Persistent unhealthy memory retains the existing finite stop before I/O");
        need(number(env.guard,"read_bytes")==0&&status(env.guard).equals("memory_pressure_stopped"),"No aggregate pacing can bypass pressure admission");
        need(Boolean.TRUE.equals(env.guard.receipt().get("last_low_memory")),"Protective stop retains the actual Android lowMemory signal");
    }
    static void oversleep()throws IOException{
        Environment env=new Environment();env.guard.admit();env.oversleep=1000;env.reads(4*MIB);
        need(env.waits.size()==1&&env.now==1125,"A delayed scheduler must not repeatedly sleep the same completed window");
        need(number(env.guard,"pressure_paused_ms")==0,"Scheduler oversleep is not fabricated pressure evidence");
    }
    static void stuckClock()throws IOException{
        Environment env=new Environment();env.guard.admit();env.stuck=true;
        reject(()->env.reads(4*MIB));
        need(env.waits.size()==1&&status(env.guard).equals("unavailable"),"An unmoving pacing clock must stop rather than spin");
    }
    static void callbackBound()throws IOException{
        Environment env=new Environment();env.guard.admit();
        need(number(env.guard,"maximum_io_callback_bytes")==64*MIB,"Callback accounting has an explicit finite byte bound");
        reject(()->env.guard.read(64*MIB+1));reject(()->env.guard.written(64*MIB+1,()->{}));
        need(number(env.guard,"read_bytes")==0&&number(env.guard,"written_bytes")==0&&env.waited==0,"Oversized callback is rejected before counters or pacing loops");
        env.guard.read(64*MIB);need(env.now==2000&&number(env.guard,"combined_io_paced_windows")==16,"Maximum healthy callback has finitely bounded paced windows");
        Environment marginal=new Environment();marginal.signal=value->adaptive();marginal.guard.admit();marginal.guard.read(64*MIB);
        need(marginal.now==8000&&number(marginal.guard,"combined_io_paced_windows")==16,"Maximum adaptive callback has finitely bounded paced windows");
    }
    static void receipts()throws IOException{
        Environment env=new Environment();Map<String,Object> before=env.guard.receipt();env.guard.admit();env.reads(4*MIB);env.writes(4*MIB);env.guard.synced();env.guard.finishWrites();
        Map<String,Object> receipt=env.guard.receipt();
        need(number(env.guard,"read_bytes")+number(env.guard,"written_bytes")==8*MIB,"Combined guarded work retains actual read plus write byte totals");
        need(number(env.guard,"combined_io_window_bytes")==4*MIB,"Export the actual aggregate policy window");
        need(number(env.guard,"healthy_combined_io_bytes_per_second")==32*MIB&&number(env.guard,"pressure_combined_io_bytes_per_second")==8*MIB,"Export both configured aggregate rates");
        need(number(env.guard,"combined_io_paced_windows")==2,"Record actual completed aggregate windows");
        need(number(env.guard,"combined_io_paced_ms")==env.waited,"Pacing receipt records actual elapsed waiting");
        need(((Number)before.get("read_bytes")).longValue()==0&&status(env.guard).equals("complete"),"Earlier receipts cannot mutate and finish remains explicit");
        need(receipt.get("scope").toString().contains("cannot guarantee"),"Host policy must retain its physical limitation");
    }
    static void liveReceipt()throws Exception{
        DiagnosticRuntime owner=new DiagnosticRuntime();RuntimeProgress bridge=new RuntimeProgress();
        need(bridge.getSetupProgressReceipt()==null&&owner.getSetupProgressReceipt()==null,"No fabricated progress without installer ownership");bridge.installer=owner;
        owner.setupReceipt=new JSONObject().put("mode","checking").put("current_asset","server-animations.pigg").put("current_asset_copied_bytes",3*MIB);
        JSONObject initial=owner.getSetupProgressReceipt();need(initial.get("setup_memory_control")==null,"No fabricated guard samples before guard ownership");
        Environment env=new Environment();owner.setupControl=env.guard;env.guard.admit();env.reads(4*MIB);
        JSONObject captured=bridge.getSetupProgressReceipt();JSONObject metrics=(JSONObject)captured.get("setup_memory_control");
        need(((Number)metrics.get("read_bytes")).longValue()==4*MIB&&((Number)metrics.get("combined_io_paced_windows")).longValue()==1,"Live getter exports the owned guard's actual counters");
        need(captured.get("current_asset").equals("server-animations.pigg")&&((Number)captured.get("current_asset_copied_bytes")).longValue()==3*MIB,"Current asset progress survives the guard snapshot");
        captured.put("mode","fixture mutation");env.reads(4*MIB);
        need(owner.setupReceipt.get("mode").equals("checking")&&((Number)metrics.get("read_bytes")).longValue()==4*MIB,"Exported progress must not alias mutable installer or guard state");
        JSONObject later=(JSONObject)owner.getSetupProgressReceipt().get("setup_memory_control");
        need(((Number)later.get("read_bytes")).longValue()==8*MIB,"A later checkpoint reflects newly completed work");
    }
    public static void main(String[] args)throws Exception{
        switch(args[0]){
            case "reads":readsOnly();break;case "mixed":mixed();break;case "partial":partial();break;
            case "elapsed":elapsedWork();break;case "sync":writesAndSync();break;case "closed":closedFiles();break;
            case "adaptive":adaptiveRate();break;case "boundary":adaptiveBoundary();break;case "recheck":adaptiveRechecks();break;
            case "cancel":cancellation();break;case "recover":pressureRecovery();break;case "pressure":persistentPressure();break;
            case "oversleep":oversleep();break;case "stuck":stuckClock();break;case "receipts":receipts();break;
            case "live_receipt":liveReceipt();break;
            case "callback_bound":callbackBound();break;
            default:throw new AssertionError("Unknown fixture scenario");
        }
        System.out.println("PASS "+args[0]);
    }
}
'''

CHECKPOINT_HOST = r'''
public class SetupIoCheckpointHost {
    static final long MIB=1024L*1024;
    static void need(boolean value,String text){if(!value)throw new AssertionError(text);}
    static long number(JSONObject value,String key){Object field=value.get(key);need(field instanceof Number,"Missing numeric checkpoint field: "+key);return ((Number)field).longValue();}
    static void checkCaptured(JSONObject value){
        JSONObject system=(JSONObject)value.get("system_memory");need(system!=null&&Boolean.TRUE.equals(system.get("available")),"Actual memory sample is present");
        need(number(system,"available_bytes")==4*1024*MIB&&number(system,"total_bytes")==16*1024*MIB&&number(system,"threshold_bytes")==128*MIB,"Durable checkpoint preserves sampled system values");
        need(Boolean.FALSE.equals(system.get("low_memory")),"Durable checkpoint preserves sampled lowMemory flag");
        JSONObject process=(JSONObject)value.get("process_memory");
        need(process!=null&&Boolean.TRUE.equals(process.get("available"))&&process.get("source").equals("bounded_proc_self_status"),"Actual bounded Linux process memory sample is present");
        need(number(process,"maximum_source_bytes")==32768&&number(process,"rss_bytes")>0,"Process memory input bound and typed RSS are preserved");
        JSONObject progress=(JSONObject)value.get("runtime_setup_progress");need(progress!=null,"Owned installer progress is present");
        need(progress.get("current_asset").equals("server-animations.pigg")&&number(progress,"current_asset_expected_bytes")==8*MIB&&number(progress,"current_asset_copied_bytes")==3*MIB,"Current asset copy progress survives durable publication");
        need(progress.get("current_asset_source").equals("asset_fd")&&number(progress,"runtime_payload_verified_bytes")==12*MIB,"Progress identifies source and independently verified prior bytes");
        JSONObject guard=(JSONObject)progress.get("setup_memory_control");
        need(number(guard,"read_bytes")==6*MIB&&number(guard,"written_bytes")==3*MIB&&number(guard,"combined_io_paced_windows")==2&&number(guard,"combined_io_paced_ms")==250,"Checkpoint carries actual owned guard pacing counters");
        need(Boolean.FALSE.equals(value.get("game_execution_requested"))&&Boolean.FALSE.equals(value.get("runtime_cleanup_requested")),"Checkpoint cannot claim game execution or profile cleanup");
    }
    public static void main(String[] args)throws Exception{
        Path root=Files.createTempDirectory("setup-io-checkpoint-");ClientService service=new ClientService(root.toFile());
        Path character=root.resolve("client/state/diagnostic/android-local-login/pgdata/keep");Files.createDirectories(character.getParent());Files.write(character,new byte[]{7,11});
        String mode=args[0];
        if(mode.equals("memory_unavailable"))ActivityManager.unavailable=true;
        if(mode.equals("memory_missing"))ActivityManager.missing=true;
        if(!mode.equals("no_runtime")){
            service.runtime=new ClientRuntime();service.runtime.setupProgress=new JSONObject().put("current_asset","server-animations.pigg")
                .put("current_asset_expected_bytes",8*MIB).put("current_asset_copied_bytes",3*MIB).put("current_asset_source","asset_fd")
                .put("runtime_payload_verified_bytes",12*MIB).put("runtime_payload_files_copied",2).put("runtime_payload_files_reused",1)
                .put("runtime_payload_bytes_copied",8*MIB).put("runtime_payload_bytes_reused",4*MIB)
                .put("setup_memory_control",new JSONObject().put("read_bytes",6*MIB).put("written_bytes",3*MIB)
                    .put("combined_io_paced_windows",2).put("combined_io_paced_ms",250));
        }
        service.checkpointSetup("Copying runtime assets","server-animations.pigg: 3 / 8 MiB copied","running",true);
        JSONObject durable=ClientService.setupMemoryEvidence(service);
        long capturedRss=number((JSONObject)durable.get("process_memory"),"rss_bytes");
        if(mode.equals("capture")||mode.equals("recovery")){
            checkCaptured(durable);need(ActivityManager.calls==1,"One memory sample per actual durable checkpoint");
            if(mode.equals("recovery")){
                ActivityManager.availableBytes=2*1024*MIB;ActivityManager.lowMemory=true;service.runtime=null;
                ClientService replacement=new ClientService(root.toFile());replacement.recoverSetupOperation();
                JSONObject recovered=ClientService.setupMemoryEvidence(replacement);checkCaptured(recovered);
                need(number((JSONObject)recovered.get("process_memory"),"rss_bytes")==capturedRss,"Recovery preserves the prior process memory sample");
                need(recovered.optString("status").equals("interrupted")&&ActivityManager.calls==1,"Recovery retains last observed system state instead of substituting later memory");
                need(replacement.report!=null&&replacement.report.isFile(),"Interrupted setup publishes a selectable report");
                try(ZipFile zip=new ZipFile(replacement.report)){need(zip.size()==2&&zip.getEntry("runtime-setup-service.json")!=null&&zip.getEntry("wrapper.json")!=null,"Recovery ZIP contains compact setup evidence");}
            }
        } else if(mode.equals("memory_unavailable")||mode.equals("memory_missing")){
            JSONObject memory=(JSONObject)durable.get("system_memory");need(Boolean.FALSE.equals(memory.get("available")),"Unavailable Android memory service is explicit");
            need(memory.get("available_bytes")==null&&memory.get("total_bytes")==null&&memory.get("low_memory")==null,"Unavailable sample cannot invent healthy measurements");
            need(mode.equals("memory_missing")||memory.optString("error").equals("IllegalStateException"),"Failure evidence is a bounded class, not an arbitrary message");
            need(durable.get("runtime_setup_progress")!=null,"Optional Android observation failure does not erase available installer evidence");
        } else if(mode.equals("no_runtime")){
            need(durable.get("runtime_setup_progress")==null&&ActivityManager.calls==1,"No invented installer progress before runtime ownership");
        } else throw new AssertionError("Unknown scenario");
        need(Arrays.equals(new byte[]{7,11},Files.readAllBytes(character)),"Setup checkpoint or recovery changed saved character bytes");
        System.out.println("PASS "+mode);
    }
}
'''


class SetupIoMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-setup-io-memory-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.directory = Path(cls.temporary.name)
        fixture = cls.directory / 'SetupIoMemoryHost.java'
        diagnostic = SOURCE.with_name('DiagnosticRuntime.java').read_text()
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        getter_methods = '\n'.join(production_method(diagnostic, signature) for signature in (
            'public JSONObject getSetupReceipt(', 'public JSONObject getSetupProgressReceipt('))
        fixture.write_text(GUARD_HOST.replace('GETTER_METHODS', getter_methods).replace(
            'BRIDGE_METHOD', production_method(runtime, 'public JSONObject getSetupProgressReceipt(')))
        result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
            '-d', str(cls.directory), str(SOURCE), str(fixture)], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        service = (JAVA / 'ClientService.java').read_text()
        checkpoint_adapter = SERVICE_HOST.split('public class SetupServiceHost {', 1)[0]
        checkpoint_adapter = checkpoint_adapter.replace('RESERVATION_METHODS', '\n'.join(
            production_method(runtime, signature) for signature in (
                'static synchronized Object acquireSetupReservation(', 'static synchronized boolean setupFinalizationInProgress(',
                'static synchronized boolean ownsSetupReservation(', 'static synchronized void releaseSetupReservation(',
                'public static synchronized boolean operationInProgress(', 'public static synchronized Object acquireReportExport(',
                'private static Object acquireIdleStorage(')))
        checkpoint_adapter = checkpoint_adapter.replace('SERVICE_METHODS', '\n'.join(
            production_method(service, signature).replace('private ', '') for signature in (
                'public static JSONObject setupMemoryEvidence(', 'private JSONObject setupSystemMemory(',
                'private JSONObject setupProcessMemory(', 'private synchronized void checkpointSetup(', 'private File writeSetupRecoveryReport(',
                'private void recoverSetupOperation(')))
        checkpoint = cls.directory / 'SetupIoCheckpointHost.java'
        checkpoint.write_text(checkpoint_adapter + CHECKPOINT_HOST)
        result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
            '-d', str(cls.directory), str(checkpoint)], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def check(self, *scenarios, fixture=CLASS):
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = subprocess.run(['java', '-Xmx32m', '-cp', str(self.directory), fixture, scenario],
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertEqual('PASS ' + scenario, result.stdout.strip())

    def test_guarded_reads_receive_aggregate_pacing_without_invented_writes(self):
        self.check('reads')

    def test_read_and_write_bytes_share_one_aggregate_window(self):
        self.check('mixed', 'partial')

    def test_elapsed_io_work_reduces_wait_and_idle_time_cannot_authorize_future_burst(self):
        self.check('elapsed')

    def test_eight_mib_sync_and_existing_write_pacing_are_preserved(self):
        self.check('sync', 'closed')

    def test_marginal_but_admitted_headroom_uses_bounded_adaptive_pacing(self):
        self.check('adaptive', 'boundary')

    def test_fresh_memory_signal_restores_normal_pacing_and_preserves_low_water(self):
        self.check('recheck')

    def test_stop_request_interrupts_adaptive_window_before_further_io(self):
        self.check('cancel')

    def test_pressure_recovery_and_existing_finite_admission_stop_are_preserved(self):
        self.check('recover', 'pressure')

    def test_scheduler_oversleep_does_not_duplicate_wait_and_stuck_clock_stops(self):
        self.check('oversleep', 'stuck')

    def test_receipts_record_actual_aggregate_bytes_windows_time_and_scope(self):
        self.check('receipts')

    def test_live_installer_receipt_captures_guard_and_asset_progress_without_aliasing(self):
        self.check('live_receipt')

    def test_single_callback_has_finite_paced_work_and_rejects_excess_before_accounting(self):
        self.check('callback_bound')

    def test_durable_checkpoint_records_current_asset_system_memory_and_owned_guard_counters(self):
        self.check('capture', fixture='SetupIoCheckpointHost')

    def test_setup_recovery_retains_last_observed_memory_and_partial_asset_progress(self):
        self.check('recovery', fixture='SetupIoCheckpointHost')

    def test_unavailable_memory_or_absent_installer_are_explicit_without_fabricated_measurements(self):
        self.check('memory_unavailable', 'memory_missing', 'no_runtime', fixture='SetupIoCheckpointHost')


if __name__ == '__main__':
    unittest.main()
