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
class Context {}
class ClientRuntime {
    static boolean operationActive, blocked;
    static Object storageOwner;
    static final String BLOCK_MESSAGE="blocked";
    static boolean cleanupBlocked(Context context){return blocked;}
    RUNTIME_METHODS
}
class Intent {
    Map<String,Object> extras=new HashMap<>();
    String[] getStringArrayExtra(String name){return (String[])extras.get(name);}
    String getStringExtra(String name){return (String)extras.get(name);}
    Intent put(String key,Object value){extras.put(key,value);return this;}
}
class PowerManager {
    static final int PARTIAL_WAKE_LOCK=1;
    static class WakeLock {boolean held;void acquire(long bound){held=true;}boolean isHeld(){return held;}void release(){held=false;}}
    WakeLock newWakeLock(int kind,String name){return new WakeLock();}
}
class StorageFiles {StorageFiles(File root){}}
class StorageAudit {
    static int scans,cleanups;static boolean fail,stale,partial;static Set<String> selected;
    static class Limits {static Limits defaults(){return new Limits();}}
    static class Plan {boolean complete=true,cleanupAllowed=true;String snapshotId="reviewed";String toJson(){return "{}";}}
    static class CleanupResult {Plan afterPlan=new Plan();boolean stalePlan,completed=true;int deletedCount=3;String toJson(){return "{}";}}
    static Plan scan(StorageFiles fs,String sha,Limits limits)throws IOException{scans++;if(fail)throw new IOException("scan failed");return new Plan();}
    static CleanupResult cleanup(StorageFiles fs,Plan plan,Set<String> ids,Limits limits)throws IOException{cleanups++;selected=new LinkedHashSet<>(ids);if(fail)throw new IOException("cleanup failed");CleanupResult result=new CleanupResult();result.stalePlan=stale;result.completed=!partial&&!stale;return result;}
}
class HostService extends Context {
    static final int NOTICE=61,STOP_FOREGROUND_REMOVE=1;
    static final String POWER_SERVICE="power";
    boolean destroyed,busy,storageBusy,reportExporting,foregroundFails;
    Object exportOwner;StorageAudit.Plan storagePlan;String storageStatus="ready";File storageReport,report;
    String session="preserved-session";long inputSent=81,inputFailed=2;int certified=12;
    final File root;int foreground,published;List<String> preferences=new ArrayList<>();
    static class Main {void post(Runnable runnable){runnable.run();}}
    static class Worker {boolean rejects;List<Runnable> pending=new ArrayList<>();void execute(Runnable runnable){if(rejects)throw new RuntimeException("worker closed");pending.add(runnable);}void drain(){while(!pending.isEmpty())pending.remove(0).run();}}
    final Main main=new Main();final Worker worker=new Worker();
    HostService(File root)throws IOException{this.root=root;root.mkdirs();report=new File(root,"latest.zip");Files.write(report.toPath(),new byte[]{1});}
    File getFilesDir(){return root;}File getCacheDir(){File cache=new File(root.getParentFile(),root.getName()+"-cache");cache.mkdirs();return cache;}Object getSystemService(String name){return new PowerManager();}
    static class Assets {InputStream open(String path){return new ByteArrayInputStream("manifest".getBytes(StandardCharsets.UTF_8));}}
    Assets getAssets(){return new Assets();}
    static class Prefs {Prefs edit(){return this;}Prefs putString(String key,String value){return this;}void apply(){}}
    Prefs getSharedPreferences(String name,int mode){preferences.add(name);return new Prefs();}
    static final int MODE_PRIVATE=0;
    void publish(){published++;}Object notification(){return new Object();}void startForeground(int id,Object value){if(foregroundFails)throw new RuntimeException("foreground rejected");foreground++;}void stopForeground(int kind){}void stopSelf(){}
    void storage(Intent intent,boolean cleaning){startStorage(intent,cleaning);}
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
            'private void startStorage(')]
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


if __name__ == '__main__': unittest.main()
