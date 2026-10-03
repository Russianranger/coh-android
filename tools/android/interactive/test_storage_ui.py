"""Execute shipped storage ownership and service routes against bounded host adapters."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'


def production_method(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth, quote, escaped, line_comment, block_comment = 0, None, False, False, False
    i = opening
    while i < len(text):
        ch, nxt = text[i], text[i:i + 2]
        if line_comment:
            if ch == '\n': line_comment = False
        elif block_comment:
            if nxt == '*/': block_comment = False; i += 1
        elif quote:
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == quote: quote = None
        elif nxt == '//': line_comment = True; i += 1
        elif nxt == '/*': block_comment = True; i += 1
        elif ch in ('"', "'"): quote = ch
        elif ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0: return text[start:i + 1]
        i += 1
    raise AssertionError('Unterminated production method')


HOST = r'''
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
class Context {public void onDestroy(){}}
class ClientActivity {}class ClientService {}
class android {static class R {static class drawable {static final int ic_menu_view=1;}}}
class PendingIntent {
    static final int FLAG_UPDATE_CURRENT=1,FLAG_IMMUTABLE=2;final Intent intent;
    PendingIntent(Intent value){intent=value;}
    static PendingIntent getActivity(Context owner,int code,Intent value,int flags){return new PendingIntent(value);}
    static PendingIntent getService(Context owner,int code,Intent value,int flags){return new PendingIntent(value);}
}
class Notification {
    String title,text;boolean ongoing;List<Action> actions=new ArrayList<>();
    static class Action {
        String label;PendingIntent intent;
        static class Builder {final Action action=new Action();Builder(Object icon,String label,PendingIntent intent){action.label=label;action.intent=intent;}Action build(){return action;}}
    }
    static class Builder {
        final Notification result=new Notification();Builder(Context owner,String channel){}
        Builder setSmallIcon(int icon){return this;}Builder setContentTitle(String title){result.title=title;return this;}Builder setContentText(String text){result.text=text;return this;}
        Builder setContentIntent(PendingIntent intent){return this;}Builder setOngoing(boolean value){result.ongoing=value;return this;}Builder setOnlyAlertOnce(boolean value){return this;}
        Builder addAction(Action action){result.actions.add(action);return this;}Notification build(){return result;}
    }
}
class NotificationManager {int updates;Notification last;void notify(int id,Notification value){updates++;last=value;}}
class ClientRuntime {
    enum ProfileState {ABSENT,READY,PRESERVE}
    static boolean operationActive, blocked;
    static Object storageOwner;
    static ProfileState profile=ProfileState.ABSENT;
    static final String BLOCK_MESSAGE="blocked";
    static boolean cleanupBlocked(Context context){return blocked;}
    static ProfileState characterProfileState(Context context){return profile;}
    static String profileRecoveryMessage(ProfileState value){return value.name();}
    int stopCalls;boolean requestStop(){stopCalls++;return true;}
    RUNTIME_METHODS
}
class Intent {
    Map<String,Object> extras=new HashMap<>();
    Intent(){}Intent(Context owner,Class<?> type){}Intent setAction(String value){action=value;return this;}
    String action;String getAction(){return action;}Intent action(String value){action=value;return this;}
    String[] getStringArrayExtra(String name){return (String[])extras.get(name);}
    String getStringExtra(String name){return (String)extras.get(name);}
    Intent put(String key,Object value){extras.put(key,value);return this;}
}
class PowerManager {
    static final int PARTIAL_WAKE_LOCK=1;
    static WakeLock latest;
    static class WakeLock {boolean held;void acquire(long bound){held=true;}boolean isHeld(){return held;}void release(){held=false;}}
    WakeLock newWakeLock(int kind,String name){latest=new WakeLock();return latest;}
}
class StorageFiles {StorageFiles(File root){}StorageFiles(File root,File cache){}}
class JSONObject {
    static Map<String,Map<String,Object>> encoded=new HashMap<>();
    final Map<String,Object> values=new LinkedHashMap<>();
    JSONObject(){}JSONObject(String json){if(!json.equals("{}")){Map<String,Object> record=encoded.get(json);if(record==null)throw new IllegalArgumentException("bad JSON");values.putAll(record);}}
    JSONObject put(String key,Object value){values.put(key,value);return this;}
    public String toString(){String text=values.toString();encoded.put(text,new LinkedHashMap<>(values));return text;}
}
class JSONArray {List<Object> values=new ArrayList<>();JSONArray put(Object value){values.add(value);return this;}public String toString(){return values.toString();}}
class SharedPreferences {
    Map<String,Object> values=new HashMap<>();boolean failCommit,terminalCommitted,terminalOwned;
    SharedPreferences edit(){return this;}SharedPreferences putString(String key,String value){values.put(key,value);return this;}SharedPreferences putBoolean(String key,boolean value){values.put(key,value);return this;}
    String getString(String key,String fallback){return (String)values.getOrDefault(key,fallback);}boolean getBoolean(String key,boolean fallback){return (Boolean)values.getOrDefault(key,fallback);}
    boolean commit(){if(values.containsKey("was_busy")&&!getBoolean("was_busy",false)){terminalCommitted=true;terminalOwned=ClientRuntime.operationInProgress();}return !failCommit;}void apply(){}
}
class Build {static class VERSION {static int SDK_INT=33;}}
class Debug {static long getNativeHeapAllocatedSize(){return 4096;}}
class ApplicationExitInfo {
    long getTimestamp(){return 123;}int getPid(){return 45;}int getReason(){return 3;}int getStatus(){return 0;}int getImportance(){return 100;}long getPss(){return 20;}long getRss(){return 30;}String getDescription(){return String.join("",Collections.nCopies(300,"x"));}
}
class ActivityManager {
    String packageName;int pid,maximum;
    List<ApplicationExitInfo> getHistoricalProcessExitReasons(String name,int process,int limit){packageName=name;pid=process;maximum=limit;return Arrays.asList(new ApplicationExitInfo());}
}
class StorageAudit {
    static int scans,cleanups;static boolean fail,stale,partial,oom;static Set<String> selected;
    interface ProgressListener {void update(String phase,int entries,String path,long elapsed)throws IOException;}
    static class Limits {static Limits defaults(){return new Limits();}}
    static class Plan {boolean complete=true,cleanupAllowed=true;String snapshotId="reviewed";String toJson(){return "{}";}}
    static class CleanupResult {Plan afterPlan=new Plan();boolean stalePlan,completed=true;int deletedCount=3;String toJson(){return "{}";}}
    static Plan scan(StorageFiles fs,String sha,Limits limits)throws IOException{scans++;if(fail)throw new IOException("scan failed");return new Plan();}
    static CleanupResult cleanup(StorageFiles fs,Plan plan,Set<String> ids,Limits limits)throws IOException{cleanups++;selected=new LinkedHashSet<>(ids);if(fail)throw new IOException("cleanup failed");CleanupResult result=new CleanupResult();result.stalePlan=stale;result.completed=!partial&&!stale;return result;}
    static Plan scan(StorageFiles fs,String sha,Limits limits,ProgressListener progress)throws IOException{if(oom)throw new OutOfMemoryError();progress.update("scanning files",245,"client-import/generation-current",5000);return scan(fs,sha,limits);}
    static CleanupResult cleanup(StorageFiles fs,Plan plan,Set<String> ids,Limits limits,ProgressListener progress)throws IOException{progress.update("removing reviewed files",3,"m2/downloads/old",5000);return cleanup(fs,plan,ids,limits);}
}
class HostService extends Context {
    static final int NOTICE=61,STOP_FOREGROUND_REMOVE=1,START_NOT_STICKY=2;
    static final String POWER_SERVICE="power",ACTIVITY_SERVICE="activity",NOTIFICATION_SERVICE="notice",CHANNEL="client";
    static final String SETUP="setup",IMPORT="import",RUN="run",CREATE="create",STOP="stop",FINISH="finish",STORAGE_SCAN="scan",STORAGE_CLEAN="clean";
    boolean destroyed,busy,storageBusy,reportExporting,foregroundFails,stopping,inputReady,characterSaved;
    PowerManager.WakeLock wake;final Runnable sessionDeadlineTick=()->{};final Object screenReceiver=new Object();final List<Object> listeners=new ArrayList<>();
    final AtomicBoolean storageStopRequested=new AtomicBoolean();byte[] storageRecoveryReserve;
    ClientRuntime runtime;ClientRuntime.ProfileState profileState=ClientRuntime.ProfileState.ABSENT;String profileNote="",stage="",detail="";boolean blocked;
    Object exportOwner;StorageAudit.Plan storagePlan;String storageStatus="ready";File storageReport,report;
    String session="preserved-session";long inputSent=81,inputFailed=2;int certified=12;
    final File root;int foreground,published;List<String> preferences=new ArrayList<>();
    static class Main {void post(Runnable runnable){runnable.run();}void removeCallbacks(Runnable runnable){}}
    static class Worker {boolean rejects,closed;List<Runnable> pending=new ArrayList<>();void execute(Runnable runnable){if(rejects)throw new RuntimeException("worker closed");pending.add(runnable);}void drain(){while(!pending.isEmpty())pending.remove(0).run();}void shutdown(){closed=true;rejects=true;}}
    final Main main=new Main();final Worker worker=new Worker();final SharedPreferences prefs=new SharedPreferences();final ActivityManager exitManager=new ActivityManager();final NotificationManager noticeManager=new NotificationManager();
    HostService(File root)throws IOException{this.root=root;root.mkdirs();report=new File(root,"latest.zip");Files.write(report.toPath(),new byte[]{1});}
    File getFilesDir(){return root;}File getCacheDir(){File cache=new File(root.getParentFile(),root.getName()+"-cache");cache.mkdirs();return cache;}Object getSystemService(String name){return name.equals(ACTIVITY_SERVICE)?exitManager:name.equals(NOTIFICATION_SERVICE)?noticeManager:new PowerManager();}String getPackageName(){return "test.coh";}
    static class Assets {InputStream open(String path){return new ByteArrayInputStream("manifest".getBytes(StandardCharsets.UTF_8));}}
    Assets getAssets(){return new Assets();}
    SharedPreferences getSharedPreferences(String name,int mode){preferences.add(name);return prefs;}
    static final int MODE_PRIVATE=0;
    void publish(){published++;}boolean requestFinish(){return true;}void startForeground(int id,Object value){if(foregroundFails)throw new RuntimeException("foreground rejected");foreground++;}void stopForeground(int kind){}void stopSelf(){}void unregisterReceiver(Object receiver){}
    void storage(Intent intent,boolean cleaning){startStorage(intent,cleaning);}
    void checkpoint(String mode,String phase,int entries,String path,long elapsed)throws IOException{checkpointStorage(mode,phase,entries,path,elapsed);}
    void recover(){recoverStorageOperation(prefs);}JSONObject exits(){return storageProcessExits();}
    void updateNotice(){notifyStatus();}Notification currentNotice(){return notification();}
    SERVICE_METHODS
}
public class StorageUiHost {
    static void need(boolean condition){if(!condition)throw new AssertionError();}
    interface Action {void run()throws Exception;}
    static void reject(Action action)throws Exception{try{action.run();throw new AssertionError("operation accepted");}catch(IOException expected){}}
    static void preserved(HostService service,File report){need(service.report.equals(report));need(service.session.equals("preserved-session"));need(service.inputSent==81&&service.inputFailed==2&&service.certified==12);need(service.preferences.stream().allMatch("storage_ui"::equals));}
    public static void main(String[] args)throws Exception{
        File root=Files.createTempDirectory("storage-ui-service-").toFile();HostService service=new HostService(root);File original=service.report;
        switch(args[0]){
        case "live":service.busy=true;service.storage(new Intent(),false);need(!service.storageBusy&&service.worker.pending.isEmpty()&&service.foreground==0);preserved(service,original);break;
        case "blocked":ClientRuntime.blocked=true;service.storage(new Intent(),false);need(service.worker.pending.isEmpty());reject(()->ClientRuntime.acquireStorage(service));Object e=service.beginReportExport(original);need(service.reportExporting);service.endReportExport(e);need(!ClientRuntime.operationInProgress());preserved(service,original);break;
        case "scan":service.storage(new Intent(),false);need(service.storageBusy&&ClientRuntime.operationInProgress());reject(()->service.beginReportExport(original));reject(()->ClientRuntime.acquireStorage(service));service.worker.drain();need(!service.storageBusy&&!ClientRuntime.operationInProgress());need(service.storagePlan!=null&&service.storageReport.isFile()&&StorageAudit.scans==1);need(!service.storageReport.toPath().startsWith(root.toPath()));preserved(service,original);break;
        case "stale":service.storagePlan=new StorageAudit.Plan();service.storage(new Intent().put("storage_snapshot","older").put("storage_categories",new String[]{"old_runtime"}),true);need(service.worker.pending.isEmpty()&&StorageAudit.cleanups==0);preserved(service,original);break;
        case "category":service.storagePlan=new StorageAudit.Plan();for(String[] ids:new String[][]{null,new String[]{},new String[]{"client_state"},new String[]{"old_runtime","downloads","old_reports","other"}}){service.storage(new Intent().put("storage_snapshot","reviewed").put("storage_categories",ids),true);}need(service.worker.pending.isEmpty()&&StorageAudit.cleanups==0);preserved(service,original);break;
        case "clean":service.storagePlan=new StorageAudit.Plan();service.storage(new Intent().put("storage_snapshot","reviewed").put("storage_categories",new String[]{"old_runtime","downloads"}),true);need(StorageAudit.cleanups==0);service.worker.drain();need(StorageAudit.cleanups==1&&StorageAudit.selected.equals(new LinkedHashSet<>(Arrays.asList("old_runtime","downloads"))));need(!ClientRuntime.operationInProgress()&&service.storageReport.isFile());preserved(service,original);break;
        case "failure":StorageAudit.fail=true;service.storage(new Intent(),false);service.worker.drain();need(!ClientRuntime.operationInProgress()&&!service.storageBusy&&service.storagePlan==null);need(service.storageStatus.contains("scan failed"));preserved(service,original);break;
        case "owner":Object owner=ClientRuntime.acquireStorage(service);ClientRuntime.releaseStorage(new Object());ClientRuntime.releaseStorage(null);need(ClientRuntime.operationInProgress());reject(()->ClientRuntime.acquireReportExport(service));ClientRuntime.releaseStorage(owner);need(!ClientRuntime.operationInProgress());Object second=ClientRuntime.acquireStorage(service);ClientRuntime.releaseStorage(owner);need(ClientRuntime.operationInProgress());ClientRuntime.releaseStorage(second);break;
        case "export":File foreign=new File(root,"foreign.zip");Files.write(foreign.toPath(),new byte[]{2});reject(()->service.beginReportExport(foreign));Object exporter=service.beginReportExport(original);service.storage(new Intent(),false);need(service.worker.pending.isEmpty());service.endReportExport(new Object());need(ClientRuntime.operationInProgress());service.endReportExport(exporter);need(!ClientRuntime.operationInProgress()&&!service.reportExporting);preserved(service,original);break;
        case "linked_report":File other=Files.createTempDirectory("storage-ui-external-").toFile();Files.createSymbolicLink(new File(service.getCacheDir(),"storage-tools").toPath(),other.toPath());service.storage(new Intent(),false);service.worker.drain();need(!ClientRuntime.operationInProgress()&&other.list().length==0&&service.storageReport==null);preserved(service,original);break;
        case "foreground_failure":service.foregroundFails=true;service.storage(new Intent(),false);need(!ClientRuntime.operationInProgress()&&!service.storageBusy&&service.worker.pending.isEmpty());preserved(service,original);break;
        case "worker_failure":service.worker.rejects=true;service.storage(new Intent(),false);need(!ClientRuntime.operationInProgress()&&!service.storageBusy&&service.worker.pending.isEmpty());preserved(service,original);break;
        case "stale_result":StorageAudit.stale=true;service.storagePlan=new StorageAudit.Plan();service.storage(new Intent().put("storage_snapshot","reviewed").put("storage_categories",new String[]{"old_runtime"}),true);service.worker.drain();need(service.storageStatus.contains("No cleanup was started"));preserved(service,original);break;
        case "partial_result":StorageAudit.partial=true;service.storagePlan=new StorageAudit.Plan();service.storage(new Intent().put("storage_snapshot","reviewed").put("storage_categories",new String[]{"old_runtime"}),true);service.worker.drain();need(service.storageStatus.contains("stopped before all"));preserved(service,original);break;
        case "retention":for(int i=0;i<5;i++){service.storage(new Intent(),false);service.worker.drain();}need(service.storageReport.getParentFile().list().length==3&&service.storageReport.isFile());preserved(service,original);break;
        case "checkpoint":service.storage(new Intent(),false);service.worker.drain();JSONObject checkpoint=new JSONObject(service.prefs.getString("progress","{}"));need(checkpoint.values.get("entries").equals(245)&&checkpoint.values.get("phase").equals("scanning files"));need(checkpoint.values.get("cleanup_allowed").equals(false));need(service.prefs.terminalCommitted&&service.prefs.terminalOwned&&!service.prefs.getBoolean("was_busy",true));preserved(service,original);break;
        case "bounded_path":service.checkpoint("scan","files",7,String.join("",Collections.nCopies(10000,"z")),1000);JSONObject path=new JSONObject(service.prefs.getString("progress","{}"));need(((String)path.values.get("last_relative_path")).length()==2048);need(path.values.get("java_heap_limit_bytes") instanceof Long&&path.values.get("native_heap_allocated_bytes").equals(4096L));preserved(service,original);break;
        case "checkpoint_failure":service.prefs.failCommit=true;service.storage(new Intent(),false);service.worker.drain();need(StorageAudit.scans==0&&service.storagePlan==null&&!ClientRuntime.operationInProgress());need(service.storageReport.isFile()&&service.storageStatus.contains("checkpoint could not be saved"));preserved(service,original);break;
        case "cancel":service.storage(new Intent(),false);service.runtime=new ClientRuntime();service.onStartCommand(new Intent().action(HostService.STOP),0,0);need(service.storageStopRequested.get()&&service.runtime.stopCalls==0&&ClientRuntime.operationInProgress());service.worker.drain();need(StorageAudit.scans==0&&!service.storageBusy&&!ClientRuntime.operationInProgress()&&service.storageReport.isFile());need(service.storageStatus.contains("cancelled"));preserved(service,original);break;
        case "oom":StorageAudit.oom=true;service.storage(new Intent(),false);service.worker.drain();need(service.storageReport.isFile()&&service.storagePlan==null&&service.storageRecoveryReserve==null&&!ClientRuntime.operationInProgress());need(service.storageStatus.contains("memory limit"));preserved(service,original);break;
        case "interrupted":service.checkpoint("scan","files",17,"m2/runtime-old",12000);service.storagePlan=new StorageAudit.Plan();service.recover();need(service.storagePlan==null&&!service.storageBusy&&service.storageReport.isFile());need(service.storageStatus.contains("interrupted")&&!service.prefs.getBoolean("was_busy",true));JSONObject recovered=new JSONObject(new String(Files.readAllBytes(service.storageReport.toPath()),StandardCharsets.UTF_8));need(recovered.values.get("status").equals("interrupted")&&recovered.values.get("entries").equals(17)&&recovered.values.get("cleanup_allowed").equals(false));need(recovered.values.containsKey("android_process_exit_history"));preserved(service,original);break;
        case "exit_scope":JSONObject exits=service.exits();need(service.exitManager.packageName.equals("test.coh")&&service.exitManager.pid==0&&service.exitManager.maximum==4);need(exits.values.get("own_processes_only").equals(true)&&exits.values.get("trace_streams_requested").equals(false));JSONArray records=(JSONArray)exits.values.get("records");need(((String)((JSONObject)records.values.get(0)).values.get("description")).length()==240);preserved(service,original);break;
        case "unsupported_exits":Build.VERSION.SDK_INT=29;JSONObject unsupported=service.exits();need(unsupported.values.get("status").equals("unsupported_api")&&service.exitManager.packageName==null);preserved(service,original);break;
        case "missing_reopen":service.onStartCommand(new Intent().action(HostService.RUN),0,0);need(service.stage.equals("Saved profile missing")&&service.foreground==0&&service.worker.pending.isEmpty()&&!service.busy);preserved(service,original);break;
        case "preserved_create":ClientRuntime.profile=ClientRuntime.ProfileState.PRESERVE;service.onStartCommand(new Intent().action(HostService.CREATE),0,0);need(service.stage.equals("Saved profile needs attention")&&service.foreground==0&&service.worker.pending.isEmpty()&&!service.busy);preserved(service,original);break;
        case "ready_create":ClientRuntime.profile=ClientRuntime.ProfileState.READY;service.onStartCommand(new Intent().action(HostService.CREATE),0,0);need(service.stage.equals("Saved profile needs attention")&&service.foreground==0&&service.worker.pending.isEmpty()&&!service.busy);preserved(service,original);break;
        case "destroyed_terminal":service.storage(new Intent(),false);service.destroyed=true;service.worker.drain();need(service.prefs.terminalCommitted&&service.prefs.terminalOwned&&!ClientRuntime.operationInProgress());need(new File(service.prefs.getString("report","")).isFile()&&!service.prefs.getBoolean("was_busy",true));preserved(service,original);break;
        case "stale_cancel":service.storageStopRequested.set(true);service.storage(new Intent(),false);need(!service.storageStopRequested.get());service.worker.drain();need(StorageAudit.scans==1&&service.storagePlan!=null&&!ClientRuntime.operationInProgress());preserved(service,original);break;
        case "storage_notice":service.storageBusy=true;service.storageStatus="scanning files · 500 entries";service.updateNotice();need(service.noticeManager.updates==1&&service.noticeManager.last.text.equals(service.storageStatus)&&service.noticeManager.last.title.equals("COH storage")&&service.noticeManager.last.ongoing);preserved(service,original);break;
        case "idle_notice":service.updateNotice();need(service.noticeManager.updates==0);preserved(service,original);break;
        case "storage_notice_cancel":service.storageBusy=true;Notification notice=service.currentNotice();need(notice.actions.size()==1&&notice.actions.get(0).label.equals("Cancel storage work")&&notice.actions.get(0).intent.intent.getAction().equals(HostService.STOP));preserved(service,original);break;
        case "guest_notice":service.busy=true;service.stage="Playing";service.inputReady=true;service.characterSaved=true;service.updateNotice();Notification playing=service.noticeManager.last;need(service.noticeManager.updates==1&&playing.actions.size()==2&&playing.actions.get(0).label.equals("Finish")&&playing.actions.get(1).label.equals("Stop"));preserved(service,original);break;
        case "destroy_cancel":service.storage(new Intent(),false);PowerManager.WakeLock held=PowerManager.latest;service.onDestroy();need(service.storageStopRequested.get()&&service.worker.closed&&service.worker.pending.size()==1&&ClientRuntime.operationInProgress()&&held.isHeld());service.worker.drain();need(StorageAudit.scans==0&&!ClientRuntime.operationInProgress()&&!held.isHeld());need(service.prefs.terminalCommitted&&service.prefs.terminalOwned&&!service.prefs.getBoolean("was_busy",true)&&new File(service.prefs.getString("report","")).isFile());preserved(service,original);break;
        case "unwritable_after_report":service.storage(new Intent(),false);service.worker.drain();File oldStorage=service.storageReport,tools=oldStorage.getParentFile(),kept=new File(tools.getParentFile(),"storage-tools-kept"),external=Files.createTempDirectory("storage-ui-denied-").toFile();Files.move(tools.toPath(),kept.toPath());Files.createSymbolicLink(tools.toPath(),external.toPath());StorageAudit.fail=true;service.storage(new Intent(),false);service.worker.drain();need(service.storagePlan==null&&service.storageReport==null&&!ClientRuntime.operationInProgress()&&service.prefs.getBoolean("was_busy",false));need(service.prefs.getString("report","unexpected")==null&&service.prefs.getString("progress","").contains("scanning files"));need(external.list().length==0&&new File(kept,oldStorage.getName()).isFile());Files.delete(tools.toPath());Files.move(kept.toPath(),tools.toPath());service.recover();need(service.storageReport.isFile()&&service.storageStatus.contains("interrupted")&&!service.prefs.getBoolean("was_busy",true));preserved(service,original);break;
        default:throw new AssertionError("unknown scenario");
        }
    }
}
'''


class StorageUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        service = (JAVA / 'ClientService.java').read_text()
        methods = [production_method(runtime, signature) for signature in (
            'public static synchronized Object acquireStorage(',
            'public static synchronized Object acquireReportExport(',
            'private static Object acquireIdleStorage(',
            'public static synchronized void releaseStorage(',
            'public static synchronized boolean operationInProgress(')]
        service_methods = [production_method(service, signature) for signature in (
            'public Object beginReportExport(', 'public void endReportExport(',
            'private String currentManifestSha(', 'private File writeStorageReport(',
            'private JSONObject storageProcessExits(', 'private void recoverStorageOperation(',
            'private void checkpointStorage(', 'private File storageFailureReport(',
            'private void refreshProfileState(', 'private void startStorage(',
            'private Notification notification(', 'private void notifyStatus(',
            'public void onDestroy(')]
        # Run the actual service dispatch prefix through its authoritative profile guard.
        # The guest-operation tail is not needed for refusal/cancellation scenarios.
        dispatch = production_method(service, 'public int onStartCommand(')
        service_methods.append(dispatch[:dispatch.index('        final android.net.Uri importUri=')]
                               + '        return START_NOT_STICKY;\n    }')
        cls.folder = tempfile.TemporaryDirectory(prefix='coh-storage-ui-')
        cls.path = Path(cls.folder.name)
        host = cls.path / 'StorageUiHost.java'
        host.write_text(HOST.replace('RUNTIME_METHODS', '\n'.join(methods)).replace('SERVICE_METHODS', '\n'.join(service_methods)))
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-d', str(cls.path), str(host)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls): cls.folder.cleanup()

    def scenario(self, name):
        subprocess.run(['java', '-cp', str(self.path), 'StorageUiHost', name], check=True, capture_output=True, text=True)

    def test_live_gameplay_rejects_storage_without_state_changes(self): self.scenario('live')
    def test_cleanup_block_preserves_failure_report_export(self): self.scenario('blocked')
    def test_scan_reserves_shared_owner_and_keeps_latest_gameplay_report(self): self.scenario('scan')
    def test_stale_review_cannot_start_cleanup(self): self.scenario('stale')
    def test_protected_unknown_empty_and_oversized_selections_are_rejected(self): self.scenario('category')
    def test_only_reviewed_selected_categories_reach_cleanup(self): self.scenario('clean')
    def test_storage_failure_releases_owner_without_overwriting_gameplay(self): self.scenario('failure')
    def test_foreign_or_stale_release_cannot_unlock_an_operation(self): self.scenario('owner')
    def test_saf_export_blocks_cleanup_and_rejects_foreign_report_paths(self): self.scenario('export')
    def test_linked_storage_report_directory_never_writes_outside_private_storage(self): self.scenario('linked_report')
    def test_foreground_start_failure_releases_reserved_owner(self): self.scenario('foreground_failure')
    def test_rejected_worker_releases_reserved_owner(self): self.scenario('worker_failure')
    def test_stale_plan_status_does_not_claim_deletion(self): self.scenario('stale_result')
    def test_partial_cleanup_status_does_not_claim_completion(self): self.scenario('partial_result')
    def test_audit_report_retention_is_bounded_outside_gameplay_files(self): self.scenario('retention')
    def test_progress_checkpoint_survives_outside_inventory_and_finishes(self): self.scenario('checkpoint')
    def test_progress_paths_and_memory_metadata_are_bounded(self): self.scenario('bounded_path')
    def test_unpersistable_checkpoint_stops_before_inventory(self): self.scenario('checkpoint_failure')
    def test_cancel_waits_for_storage_owner_without_stopping_guest_runtime(self): self.scenario('cancel')
    def test_memory_limit_leaves_small_failure_report_and_releases_owner(self): self.scenario('oom')
    def test_interrupted_scan_restores_progress_and_disables_cleanup(self): self.scenario('interrupted')
    def test_exit_diagnostic_reads_only_own_bounded_records_without_trace_stream(self): self.scenario('exit_scope')
    def test_older_android_records_unsupported_exit_history(self): self.scenario('unsupported_exits')
    def test_service_refuses_missing_profile_reopen_before_mutating_report(self): self.scenario('missing_reopen')
    def test_service_refuses_incomplete_profile_creation_before_mutating_report(self): self.scenario('preserved_create')
    def test_service_refuses_creation_over_existing_profile_before_mutating_report(self): self.scenario('ready_create')
    def test_destroyed_service_commits_terminal_report_before_releasing_owner(self): self.scenario('destroyed_terminal')
    def test_new_scan_clears_only_previous_storage_cancellation(self): self.scenario('stale_cancel')
    def test_storage_progress_updates_foreground_notification(self): self.scenario('storage_notice')
    def test_idle_service_does_not_refresh_foreground_notification(self): self.scenario('idle_notice')
    def test_storage_notification_cancellation_uses_owned_stop_route(self): self.scenario('storage_notice_cancel')
    def test_guest_notification_retains_saved_character_finish_and_stop(self): self.scenario('guest_notice')
    def test_service_destruction_cancels_storage_but_holds_lock_and_wake_until_worker_finishes(self): self.scenario('destroy_cancel')
    def test_failure_without_report_keeps_checkpoint_and_never_exposes_stale_report(self): self.scenario('unwritable_after_report')


if __name__ == '__main__': unittest.main()
