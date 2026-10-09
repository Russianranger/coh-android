"""Execute shipped setup ownership, memory recovery and stale-frame release.

Android services/JSON are small host adapters. The production setup boundaries,
durable preferences, report ZIP writes and UI frame-release methods are executed;
this does not qualify Android LMK behavior or device installation.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_storage_ui import production_method

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'

RUNTIME_HOST = r'''
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
class JSONObject {
    static boolean failNext;
    final Map<String,Object> values=new HashMap<>();
    JSONObject(){if(failNext){failNext=false;throw new OutOfMemoryError("fixture report allocation");}}
    JSONObject put(String key,Object value){values.put(key,value);return this;}
}
class SystemClock {static long uptimeMillis(){return 100;}}
class Context {}
class DiagnosticRuntime {
    interface Listener {void onStage(String name,String detail);void onLog(String text);}
    DiagnosticRuntime(Object context,Listener listener){}
    void setupRuntime()throws Exception {
        if(OwnedRuntime.scenario.equals("installer_oom"))throw new OutOfMemoryError("fixture installer");
        if(OwnedRuntime.scenario.equals("installer_exception"))throw new IOException("fixture installer failure");
    }
    JSONObject getSetupReceipt()throws Exception {
        if(OwnedRuntime.scenario.equals("receipt_oom"))throw new OutOfMemoryError("fixture receipt");
        if(OwnedRuntime.scenario.equals("receipt_exception"))throw new IOException("fixture receipt failure");
        return new JSONObject().put("mode","installed");
    }
}
class OwnedRuntime {
    static boolean operationActive;static String scenario;static Object setupFinalizationOwner,storageOwner;
    boolean operationOwned,finished,inputReady=true,cancelled;
    Context context=new Context();Object setupReservation;File work,operationDir,latestReport;
    String operation,session,runId,error;long startedUptime,endedUptime;
    DiagnosticRuntime installer;
    ExecutorService inputWorker=Executors.newSingleThreadExecutor();
    OwnedRuntime(File root){work=new File(root,"client");work.mkdirs();}
    static boolean cleanupBlocked(Object context){return false;}
    static final String BLOCK_MESSAGE="blocked";
    static class Result {
        final boolean passed;final File report;final String summary;
        Result(boolean yes,File report,String text){passed=yes;this.report=report;summary=text;}
    }
    void recordLifecycle(String event) {
        if(scenario.equals("begin_oom"))throw new OutOfMemoryError("fixture begin");
        if(scenario.equals("report_oom"))JSONObject.failNext=true;
    }
    void loadManifest(){}void check(){}void stage(String a,String b){}void line(String text){}
    static String message(Exception failure){return failure.getMessage();}
    static Object characterProfileState(Object context){return "ready";}
    static String profileRecoveryMessage(Object state){return "existing character retained";}
    void publish(JSONObject report,boolean passed,boolean cleanup)throws IOException {
        if(scenario.equals("publish_oom"))throw new OutOfMemoryError("fixture publish");
        if(scenario.equals("publish_exception"))throw new IOException("fixture publish failure");
        latestReport=new File(operationDir,"support.zip");
    }
    RUNTIME_METHODS
}
public class SetupOwnerHost {
    static void need(boolean value,String message){if(!value)throw new AssertionError(message);}
    static byte[] sentinel={7,9,11};
    public static void main(String[] args)throws Exception {
        File root=Files.createTempDirectory("setup-owner-").toFile();
        for(String name:new String[]{"client/state/diagnostic/android-local-login/pgdata/keep","client-import/generation-keep/data/keep","m2/runtime-0000000000000000/rootfs/keep"}) {
            Path path=root.toPath().resolve(name);Files.createDirectories(path.getParent());Files.write(path,sentinel);
        }
        OwnedRuntime runtime=new OwnedRuntime(root);OwnedRuntime.scenario=args[0];
        if(args[0].equals("other_owner"))OwnedRuntime.operationActive=true;
        Object reservation=null;
        if(args[0].equals("reservation_owner")){reservation=OwnedRuntime.acquireSetupReservation(runtime.context);runtime.attachSetupReservation(reservation);}
        if(args[0].equals("pointer_rollback")) {
            Path pointer=runtime.work.toPath().resolve("latest-report.txt");Files.createDirectories(pointer);Files.write(pointer.resolve("keep"),sentinel);
        }
        if(args[0].equals("shutdown_oom"))runtime.inputWorker=new AbstractExecutorService(){
            public void shutdown(){}public List<Runnable> shutdownNow(){throw new OutOfMemoryError("fixture shutdown");}
            public boolean isShutdown(){return false;}public boolean isTerminated(){return false;}
            public boolean awaitTermination(long timeout,TimeUnit unit){return false;}public void execute(Runnable task){}
        };
        boolean failed=false;
        try {
            OwnedRuntime.Result result=runtime.setup();
            need(result.passed!=args[0].equals("installer_exception"),"setup result differs");
        } catch(IOException|OutOfMemoryError expected){failed=true;}
        boolean expectedFailure=args[0].endsWith("oom")||args[0].equals("publish_exception")||args[0].equals("other_owner")||args[0].equals("pointer_rollback");
        need(failed==expectedFailure,"failure did not reach boundary");
        need(OwnedRuntime.operationActive==args[0].equals("other_owner"),"wrong owner lock release");
        need(!runtime.operationOwned&&runtime.installer==null,"setup owner retained");
        if(args[0].equals("reservation_owner")) {
            need(OwnedRuntime.operationInProgress(),"finalization reservation released too early");
            try{new OwnedRuntime(root).setup();throw new AssertionError("new owner admitted during finalization");}catch(IOException expected){}
            try{OwnedRuntime.acquireReportExport(runtime.context);throw new AssertionError("export admitted during finalization");}catch(IOException expected){}
            OwnedRuntime.releaseSetupReservation(new Object());need(OwnedRuntime.setupFinalizationInProgress(),"wrong token released owner");
            OwnedRuntime.releaseSetupReservation(reservation);need(!OwnedRuntime.operationInProgress(),"finalization token retained");
        }
        for(String name:new String[]{"client/state/diagnostic/android-local-login/pgdata/keep","client-import/generation-keep/data/keep","m2/runtime-0000000000000000/rootfs/keep"})
            need(Arrays.equals(sentinel,Files.readAllBytes(root.toPath().resolve(name))),"protected bytes changed");
        System.out.println("PASS "+args[0]);
    }
}
'''

SERVICE_HOST = r'''
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
class JSONObject {
    static final Map<String,JSONObject> encoded=new HashMap<>();static int serial;
    final Map<String,Object> values=new LinkedHashMap<>();
    JSONObject(){}
    JSONObject(String raw)throws IOException {
        if(raw.equals("{}"))return;
        JSONObject original=encoded.get(raw);if(original==null)throw new IOException("invalid fixture JSON");values.putAll(original.values);
    }
    JSONObject put(String key,Object value){values.put(key,value);return this;}
    Object get(String key){return values.get(key);}String optString(String key){Object value=values.get(key);return value==null?"":value.toString();}
    public String toString(){String token="fixture-json-"+(++serial);encoded.put(token,this);return token;}
}
class SharedPreferences {
    final Map<String,Object> values=new HashMap<>();boolean failCommit;int commits;
    String getString(String key,String fallback){return (String)values.getOrDefault(key,fallback);}
    boolean getBoolean(String key,boolean fallback){return (Boolean)values.getOrDefault(key,fallback);}
    Editor edit(){return new Editor();}
    class Editor {
        final Map<String,Object> staged=new HashMap<>();
        Editor putString(String key,String value){staged.put(key,value);return this;}Editor putBoolean(String key,boolean value){staged.put(key,value);return this;}
        boolean commit(){commits++;if(failCommit)return false;values.putAll(staged);return true;}void apply(){commit();}
    }
}
class Context {
    static final int MODE_PRIVATE=0;static final Map<String,SharedPreferences> preferences=new HashMap<>();
    static final String ACTIVITY_SERVICE="activity";
    Object getSystemService(String name){return ActivityManager.missing?null:ActivityManager.manager;}
    SharedPreferences getSharedPreferences(String name,int mode){return preferences.computeIfAbsent(name,key->new SharedPreferences());}
}
class ActivityManager {
    static final ActivityManager manager=new ActivityManager();static boolean unavailable,missing,lowMemory;
    static long availableBytes=4L<<30,totalBytes=16L<<30,thresholdBytes=128L<<20;static int calls;
    static class MemoryInfo {long availMem,totalMem,threshold;boolean lowMemory;}
    void getMemoryInfo(MemoryInfo value){
        calls++;if(unavailable)throw new IllegalStateException("fixture Android memory service unavailable");
        value.availMem=availableBytes;value.totalMem=totalBytes;value.threshold=thresholdBytes;value.lowMemory=lowMemory;
    }
}
class SystemClock {static long now=100;static long uptimeMillis(){return now;}}
class Debug {static long getNativeHeapAllocatedSize(){return 4096;}}
class Build {static class VERSION {static final int SDK_INT=33;}static final String MANUFACTURER="fixture",MODEL="Thor";}
class android {static class os {static class Process {static int myPid(){return 55;}}}}
class PowerManager {static class WakeLock {boolean held=true;int releases;boolean isHeld(){return held;}void release(){held=false;releases++;}}}
class ClientRuntime {
    static boolean operationActive;static Object setupFinalizationOwner,storageOwner;static final String BLOCK_MESSAGE="blocked";
    static boolean cleanupBlocked(Context context){return false;}
    static class Result {final boolean passed;final String summary;File report;Result(boolean yes){passed=yes;summary=yes?"Runtime ready":"Setup stopped";}}
    boolean oom,failure,stopped;int setups;
    JSONObject setupProgress=new JSONObject().put("mode","not_started");
    JSONObject getSetupProgressReceipt()throws IOException{return new JSONObject(setupProgress.toString());}
    Result setup()throws Exception {setups++;if(oom)throw new OutOfMemoryError("fixture heap");if(failure)throw new IOException("fixture IO");return new Result(!stopped);}
    static JSONObject setupProcessExitHistory(Context context){return new JSONObject().put("own_processes_only",true).put("maximum_records",4).put("trace_streams_requested",false);}
    RESERVATION_METHODS
}
class ClientService extends Context {
    static final String SETUP_PREFS="runtime_setup_ui",PREFS="client_ui";static final int MAX_SETUP_EVIDENCE=16384,STOP_FOREGROUND_REMOVE=1;
    byte[] setupRecoveryReserve;boolean setupWorkerOwnsWake,busy=true,inputReady=true,finishing=true,stopping,waitingForSetupFinalization;
    long setupStartedUtc=System.currentTimeMillis(),lastSetupCheckpointUptime;String lastSetupPhase="",stage="",detail="";
    String setupAppVersion="0.13.5",setupAppId="test.coh";
    File setupFailureReport,report;ClientRuntime runtime;int published,stopped;
    final File root;ClientService(File root){this.root=root;}
    File getFilesDir(){return root;}void stopForeground(int flag){}void publish(){published++;}void stopSelf(){stopped++;}
    SERVICE_METHODS
}
public class SetupServiceHost {
    static void need(boolean value,String message){if(!value)throw new AssertionError(message);}
    public static void main(String[] args)throws Exception {
        Path root=Files.createTempDirectory("setup-service-");ClientService service=new ClientService(root.toFile());String scenario=args[0];
        Path profile=root.resolve("client/state/diagnostic/android-local-login/pgdata/keep");Files.createDirectories(profile.getParent());Files.write(profile,new byte[]{7,11});
        SharedPreferences prefs=service.getSharedPreferences(ClientService.SETUP_PREFS,0);
        if(scenario.equals("success")||scenario.equals("stopped")||scenario.equals("oom")||scenario.equals("io_failure")||scenario.equals("checkpoint_failure")) {
            ClientRuntime runtime=new ClientRuntime();runtime.oom=scenario.equals("oom");runtime.failure=scenario.equals("io_failure");runtime.stopped=scenario.equals("stopped");
            if(scenario.equals("checkpoint_failure"))prefs.failCommit=true;
            Object owner=ClientRuntime.acquireSetupReservation(service);
            service.setupWorkerOwnsWake=true;PowerManager.WakeLock wake=new PowerManager.WakeLock();Exception failure=null;
            ClientRuntime.Result result=null;
            try{result=service.executeSetup(runtime);need(result.passed==scenario.equals("success"),"ready result");}
            catch(IOException expected){failure=expected;}
            finally{service.finishSetupWorker(wake,failure,owner,result,null);}
            need(service.setupRecoveryReserve==null&&!service.busy&&!service.setupWorkerOwnsWake&&!wake.held&&wake.releases==1,"setup resources retained");
            need(!service.getSharedPreferences(ClientService.PREFS,0).getBoolean("was_busy",true),"busy preference retained");
            if(scenario.equals("oom")) {
                need(failure!=null&&failure.getMessage().contains("Java memory limit"),"OOM not bounded");
                need(service.setupFailureReport!=null&&service.setupFailureReport.isFile(),"OOM recovery report missing");
                need(ClientService.setupMemoryEvidence(service).optString("status").equals("java_heap_exhausted"),"OOM falsely complete");
            } else if(!scenario.equals("checkpoint_failure"))need(ClientService.setupMemoryEvidence(service).optString("status").equals(scenario.equals("success")?"complete":"stopped"),"terminal status");
            if(scenario.equals("checkpoint_failure"))need(runtime.setups==0,"setup ran without durable checkpoint");
        } else if(scenario.equals("throttle")) {
            service.checkpointSetup("Hashing","first","running",true);int commits=prefs.commits;
            service.checkpointSetup("Hashing",String.join("",Collections.nCopies(1000,"x")),"running",false);need(prefs.commits==commits,"same phase not throttled");
            SystemClock.now+=5000;service.checkpointSetup("Hashing",String.join("",Collections.nCopies(1000,"x")),"running",false);
            JSONObject value=ClientService.setupMemoryEvidence(service);need(value.optString("detail").length()==240,"detail bound");
            service.checkpointSetup(String.join("",Collections.nCopies(200,"p")),"new phase","running",false);need(ClientService.setupMemoryEvidence(service).optString("phase").length()==80,"phase bound");
        } else if(scenario.equals("recover")||scenario.equals("linked_report")) {
            service.checkpointSetup("Unpacking environment","12000 files","running",true);
            Path foreign=null;
            if(scenario.equals("linked_report")){foreign=Files.createTempDirectory("setup-foreign-");Files.createSymbolicLink(root.resolve("client/reports"),foreign);}
            service.recoverSetupOperation();
            if(scenario.equals("recover")) {
                need(service.report!=null&&service.report.isFile(),"recovery report not selectable");
                need(!prefs.getBoolean("was_busy",true),"recovery not acknowledged");
                JSONObject value=ClientService.setupMemoryEvidence(service);need(value.optString("status").equals("interrupted")&&value.optString("phase").equals("Unpacking environment"),"last phase lost");
                need(value.optString("app_version").equals("0.13.5")&&value.optString("application_id").equals("test.coh"),"original failed build lost");
                JSONObject exits=(JSONObject)value.get("android_process_exit_history");need(Boolean.TRUE.equals(exits.get("own_processes_only"))&&Integer.valueOf(4).equals(exits.get("maximum_records")),"unbounded exits");
                try(ZipFile zip=new ZipFile(service.report)){need(zip.size()==2&&zip.getEntry("runtime-setup-service.json")!=null&&zip.getEntry("wrapper.json")!=null,"wrong recovery ZIP");}
                File previous=service.report;service.recoverSetupOperation();need(service.report.equals(previous),"recovery repeated");
            } else {need(service.report==null&&prefs.getBoolean("was_busy",false),"linked report accepted");try(DirectoryStream<Path> entries=Files.newDirectoryStream(foreign)){need(!entries.iterator().hasNext(),"wrote through linked report path");}}
        } else if(scenario.equals("bounded_read")) {
            need(ClientService.setupMemoryEvidence(service).optString("status").equals("not_recorded"),"missing evidence");
            prefs.edit().putString("progress",String.join("",Collections.nCopies(16385,"x"))).commit();need(ClientService.setupMemoryEvidence(service).optString("status").equals("checkpoint_exceeded_bound"),"unbounded read");
            prefs.edit().putString("progress","malformed").commit();need(ClientService.setupMemoryEvidence(service).optString("status").equals("unavailable"),"malformed evidence unsafe");
        } else if(scenario.equals("dispatch_failure")) {
            service.runtime=new ClientRuntime();service.setupWorkerOwnsWake=true;PowerManager.WakeLock wake=new PowerManager.WakeLock();
            Object owner=ClientRuntime.acquireSetupReservation(service);
            service.failedOperationDispatch(true,wake,owner);need(!service.busy&&!wake.held&&!service.setupWorkerOwnsWake&&service.runtime==null&&service.stopped==1,"dispatch resources retained");
            need(!ClientRuntime.operationInProgress(),"dispatch reservation retained");
        } else if(scenario.equals("service_replacement")) {
            Object previous=ClientRuntime.acquireSetupReservation(service);service.setupWorkerOwnsWake=true;
            service.checkpointSetup("Hashing","old worker still finalizing","running",true);
            ClientService replacement=new ClientService(root.toFile());replacement.recoverSetupOperation();
            need(replacement.report==null&&ClientService.setupMemoryEvidence(replacement).optString("status").equals("running")&&prefs.getBoolean("was_busy",false),"live old worker marked interrupted");
            try{ClientRuntime.acquireSetupReservation(replacement);throw new AssertionError("replacement admitted too early");}catch(IOException expected){}
            try{ClientRuntime.acquireReportExport(replacement);throw new AssertionError("replacement export admitted too early");}catch(IOException expected){}
            Path completed=root.resolve("client/reports/finished/support.zip");Files.createDirectories(completed.getParent());Files.write(completed,new byte[]{1,2});
            ClientRuntime.Result finished=new ClientRuntime.Result(true);finished.report=completed.toFile();
            service.finishSetupWorker(new PowerManager.WakeLock(),null,previous,finished,null);
            replacement.refreshFinishedSetup();
            need(replacement.report!=null&&replacement.report.equals(completed.toFile())&&replacement.stage.equals("Runtime ready")&&!replacement.waitingForSetupFinalization,"replacement did not restore terminal report without restart");
            Object current=ClientRuntime.acquireSetupReservation(replacement);replacement.checkpointSetup("Starting","new worker","running",true);
            replacement.getSharedPreferences(ClientService.PREFS,0).edit().putBoolean("was_busy",true).commit();
            service.finishSetupWorker(new PowerManager.WakeLock(),new IOException("late old finalizer"),previous,null,null);
            need(ClientRuntime.ownsSetupReservation(current)&&ClientService.setupMemoryEvidence(replacement).optString("phase").equals("Starting")&&replacement.getSharedPreferences(ClientService.PREFS,0).getBoolean("was_busy",false),"old finalizer stomped new owner");
            ClientRuntime.releaseSetupReservation(current);
        } else throw new AssertionError("unknown scenario");
        need(Arrays.equals(new byte[]{7,11},Files.readAllBytes(profile)),"saved character changed");
        System.out.println("PASS "+scenario);
    }
}
'''

SURFACE_HOST = r'''
import java.util.*;
class Looper {static final Looper UI=new Looper();static Looper current=UI;static Looper myLooper(){return current;}static Looper getMainLooper(){return UI;}}
class SystemClock {static long uptimeMillis(){return 1000L;}}
class Bitmap {boolean recycled;void recycle(){if(Looper.current!=Looper.UI)throw new AssertionError("non UI recycle");recycled=true;}}
class InteractiveRfbClient {static final int MAX_WIDTH=2048,MAX_HEIGHT=2048;}
class SurfaceOwner {
    static class Session {final String id;Session(String id){this.id=id;}}
    static class Frame {final Session session;Frame(Session value,int[] pixels,int width,int height,long sequence){session=value;}}
    static class Main {final List<Runnable> pending=new ArrayList<>();void post(Runnable action){pending.add(action);}void removeCallbacks(Runnable action){pending.remove(action);}void drain(){while(!pending.isEmpty())pending.remove(0).run();}}
    static class CaptureWork {boolean cancelled;long freezeEndedAt;int framesDuringCopy,pendingFramesPeak;}
    boolean capturePending;CaptureWork captureWork;
    final Object pendingLock=new Object();Session session;Frame pending,lastFrame;Bitmap displayed;
    final Main main=new Main();final Runnable captureTimer=()->{};boolean captureTimerPosted;int inputWidth=800,inputHeight=600;float pointerX,pointerY;
    void releaseInput(){}void scheduleRender(){}void scheduleRenderIfPending(){}
    SURFACE_METHODS
}
public class SetupSurfaceHost {
    static void need(boolean value,String message){if(!value)throw new AssertionError(message);}
    public static void main(String[] args) {
        SurfaceOwner surface=new SurfaceOwner();surface.setSession(String.join("",Collections.nCopies(32,"a")));
        surface.setFrame(new int[4],2,2,1);surface.lastFrame=surface.pending;Bitmap old=new Bitmap();surface.displayed=old;surface.captureTimerPosted=true;surface.main.post(surface.captureTimer);
        SurfaceOwner.CaptureWork inFlight=new SurfaceOwner.CaptureWork();surface.captureWork=inFlight;surface.capturePending=true;
        if(args[0].equals("non_ui")) {
            Looper.current=new Looper();try{surface.clearFrames();throw new AssertionError("non UI clear accepted");}catch(IllegalStateException expected){}
            need(!old.recycled&&surface.session!=null&&!inFlight.cancelled&&surface.capturePending,"off-thread clear mutated state");
        } else {
            surface.clearFrames();surface.main.drain();surface.setFrame(new int[4],2,2,2);
            need(inFlight.cancelled&&inFlight.freezeEndedAt==1000L&&!surface.capturePending,"in-flight capture survived clear");
            need(surface.session==null&&surface.pending==null&&surface.lastFrame==null&&surface.displayed==null&&old.recycled&&!surface.captureTimerPosted,"old frame restored");
            if(args[0].equals("new_session")){surface.setSession(String.join("",Collections.nCopies(32,"b")));surface.setFrame(new int[4],2,2,3);surface.main.drain();need(surface.pending!=null&&surface.pending.session==surface.session,"new session blocked");}
        }
        System.out.println("PASS "+args[0]);
    }
}
'''


class SetupServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='coh-setup-service-')
        cls.path = Path(cls.temp.name)
        runtime = (JAVA/'ClientRuntime.java').read_text()
        service = (JAVA/'ClientService.java').read_text()
        surface = (JAVA/'ClientSurface.java').read_text()
        fixtures = {
            'owner': ('SetupOwnerHost', RUNTIME_HOST.replace('RUNTIME_METHODS', '\n'.join(
                production_method(runtime, signature).replace('ClientRuntime.class', 'OwnedRuntime.class')
                for signature in ('private synchronized void begin(', 'private void endOperation(', 'public Result setup(',
                                  'static synchronized Object acquireSetupReservation(', 'static synchronized boolean setupFinalizationInProgress(',
                                  'static synchronized boolean ownsSetupReservation(', 'static synchronized void releaseSetupReservation(',
                                  'void attachSetupReservation(', 'public static synchronized boolean operationInProgress(',
                                  'public static synchronized Object acquireReportExport(', 'private static Object acquireIdleStorage(')))),
            'service': ('SetupServiceHost', SERVICE_HOST.replace('RESERVATION_METHODS', '\n'.join(
                production_method(runtime, signature) for signature in (
                    'static synchronized Object acquireSetupReservation(', 'static synchronized boolean setupFinalizationInProgress(',
                    'static synchronized boolean ownsSetupReservation(', 'static synchronized void releaseSetupReservation(',
                    'public static synchronized boolean operationInProgress(', 'public static synchronized Object acquireReportExport(',
                    'private static Object acquireIdleStorage('))).replace('SERVICE_METHODS', '\n'.join(
                production_method(service, signature).replace('private ', '') for signature in (
                    'public static JSONObject setupMemoryEvidence(', 'private JSONObject setupSystemMemory(', 'private JSONObject setupProcessMemory(', 'private synchronized void checkpointSetup(',
                    'private File writeSetupRecoveryReport(', 'private void recoverSetupOperation(',
                    'private ClientRuntime.Result executeSetup(', 'private void finishSetupWorker(',
                    'private void failedOperationDispatch(', 'private File validSetupReport(', 'private void refreshFinishedSetup(')))),
            'surface': ('SetupSurfaceHost', SURFACE_HOST.replace('SURFACE_METHODS', '\n'.join(
                production_method(surface, signature) for signature in ('public void setSession(', 'public void clearFrames(', 'public void setFrame(', 'private void invalidateCapture(')))),
        }
        cls.fixtures = {}
        for key, (name, contents) in fixtures.items():
            directory = cls.path/key
            directory.mkdir()
            file = directory/(name+'.java')
            file.write_text(contents)
            result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                                     '-d', str(directory), str(file)], capture_output=True, text=True)
            if result.returncode:
                raise AssertionError(result.stderr)
            cls.fixtures[key] = (directory, name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def scenarios(self, fixture, *scenarios):
        directory, name = self.fixtures[fixture]
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = subprocess.run(['java', '-cp', str(directory), name, scenario], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), 'PASS '+scenario)

    def test_setup_releases_its_owner_for_each_heap_failure_boundary(self):
        self.scenarios('owner', 'begin_oom', 'report_oom', 'installer_oom', 'receipt_oom', 'publish_oom', 'shutdown_oom')

    def test_success_optional_telemetry_and_io_failures_release_owner(self):
        self.scenarios('owner', 'success', 'installer_exception', 'receipt_exception', 'publish_exception')

    def test_rejected_begin_preserves_other_owner_and_pointer_rollback_is_closed(self):
        self.scenarios('owner', 'other_owner', 'pointer_rollback', 'reservation_owner')

    def test_service_setup_and_cancellation_record_terminal_status_and_release_resources(self):
        self.scenarios('service', 'success', 'stopped', 'io_failure')

    def test_setup_oom_uses_small_recovery_report_and_releases_resources(self):
        self.scenarios('service', 'oom')

    def test_checkpoint_failure_prevents_installer_start_and_dispatch_failure_releases_resources(self):
        self.scenarios('service', 'checkpoint_failure', 'dispatch_failure')

    def test_checkpoint_detail_phase_reads_and_callback_rate_are_bounded(self):
        self.scenarios('service', 'throttle', 'bounded_read')

    def test_interrupted_launch_preserves_last_phase_and_exports_own_exit_history_once(self):
        self.scenarios('service', 'recover')

    def test_recovery_report_refuses_a_linked_report_directory(self):
        self.scenarios('service', 'linked_report')

    def test_same_process_service_replacement_waits_for_old_finalization_and_rejects_old_token(self):
        self.scenarios('service', 'service_replacement')

    def test_frame_release_recycles_only_on_ui_thread_and_rejects_queued_old_frames(self):
        self.scenarios('surface', 'clear', 'non_ui', 'new_session')

    def test_frame_clear_cancels_inflight_copy_before_new_session(self):
        self.scenarios('surface', 'capture_cancel')

    def test_actual_dispatch_and_support_report_wire_the_setup_boundary(self):
        service = (JAVA/'ClientService.java').read_text()
        dispatch = production_method(service, 'public int onStartCommand(')
        self.assertIn('setup?executeSetup(instance)', dispatch)
        self.assertIn('finally{if(setup)finishSetupWorker(operationWake,failure,setupOwner,result,instance.getLatestReport());}', dispatch)
        self.assertLess(dispatch.index('try {'), dispatch.index('startForeground(NOTICE,notification())'))
        self.assertIn('destroyed||runtime!=instance', dispatch)
        self.assertIn('setup&&setupFailureReport!=null?setupFailureReport', dispatch)
        self.assertIn('recoverSetupOperation();', production_method(service, 'public void onCreate('))
        self.assertIn('!setupWorkerOwnsWake&&wake!=null', production_method(service, 'public void onDestroy('))
        completion = production_method(service, 'private void finishSetupWorker(')
        self.assertLess(completion.index('operationWake.release()'), completion.index('setupWorkerOwnsWake=false'))
        self.assertLess(completion.index('setupWorkerOwnsWake=false'), completion.index('busy=false'))
        runtime = (JAVA/'ClientRuntime.java').read_text()
        publish = production_method(runtime, 'private void publish(')
        self.assertIn('.put("runtime_setup_service",ClientService.setupMemoryEvidence(context))', publish)
        self.assertIn('"runtime-setup-service.json"', publish)
        activity = (JAVA/'ClientActivity.java').read_text()
        self.assertIn('if(next.busy&&next.session.isEmpty())display.clearFrames();', activity)


if __name__ == '__main__':
    unittest.main()
