"""Exercise the shipped foreground export owner through interruption/provider failures."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import test_client_sidebar_runtime as sidebar

ROOT=Path(__file__).resolve().parents[3]
JAVA=ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
RECOVERY=ROOT/'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java'

class ClientReportLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='coh-report-lifecycle-');cls.addClassCleanup(cls.tmp.cleanup)
        base=Path(cls.tmp.name)
        uri=base/'android/net/Uri.java';uri.parent.mkdir(parents=True)
        uri.write_text('package android.net; public class Uri { public String getScheme(){return "content";} }')
        cancellation=base/'android/os/CancellationSignal.java';cancellation.parent.mkdir(parents=True)
        cancellation.write_text('package android.os; public class CancellationSignal { public void cancel(){} }')
        descriptor=base/'android/content/res/AssetFileDescriptor.java';descriptor.parent.mkdir(parents=True)
        descriptor.write_text('package android.content.res; import java.io.*; public class AssetFileDescriptor implements Closeable { public static final long UNKNOWN_LENGTH=-1;public long declared=-1;public long getDeclaredLength(){return declared;} OutputStream out; public AssetFileDescriptor(OutputStream o){out=o;android.system.Os.output=o;} public OutputStream createOutputStream(){return out;} public long getStartOffset(){return 0;} public android.os.ParcelFileDescriptor getParcelFileDescriptor(){return new android.os.ParcelFileDescriptor();} public void close()throws IOException{out.close();} }')
        parcel=base/'android/os/ParcelFileDescriptor.java';parcel.write_text('package android.os; public class ParcelFileDescriptor { public java.io.FileDescriptor getFileDescriptor(){return new java.io.FileDescriptor();} }')
        osdir=base/'android/system';osdir.mkdir(parents=True)
        constants=osdir/'OsConstants.java';constants.write_text('package android.system; public class OsConstants { public static final int F_GETFL=1,F_SETFL=2,O_NONBLOCK=4,EAGAIN=11,EINTR=4; }')
        errno=osdir/'ErrnoException.java';errno.write_text('package android.system; public class ErrnoException extends Exception { public int errno;public ErrnoException(int e){errno=e;} }')
        osjava=osdir/'Os.java';osjava.write_text('''package android.system; import java.io.*; public class Os {
          public static OutputStream output;static int flags;public static class WouldBlock extends IOException {}
          public static int fcntlInt(FileDescriptor fd,int cmd,int arg)throws ErrnoException{if(cmd==OsConstants.F_SETFL)flags=arg;return flags;}
          public static int write(FileDescriptor fd,byte[] b,int o,int n)throws ErrnoException,IOException{if((flags&OsConstants.O_NONBLOCK)==0)throw new AssertionError("blocking write");try{output.write(b,o,n);return n;}catch(WouldBlock blocked){throw new ErrnoException(OsConstants.EAGAIN);}}
        }''')
        source=(JAVA/'ClientService.java').read_text()
        methods='\n'.join(sidebar.method(source,x) for x in (
            'public Object beginReportExport(', 'public List<File> retainedReports(', 'private void startReportExport(', 'private android.content.res.AssetFileDescriptor openReportDestination(', 'private java.io.OutputStream boundedReportOutput(', 'private void failedReportDispatch(', 'private void recoverReports('))
        harness=r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;import java.nio.file.*;import java.nio.charset.StandardCharsets;import java.util.*;import java.util.zip.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;
public class ReportLifecycleHost {
 static void need(boolean b){if(!b)throw new AssertionError();}
 static class SystemClock {static long uptimeMillis(){return 5000;}}
 static class ClientRuntime {
  static volatile Object held;static boolean operationActive;static Object setupFinalizationOwner;
  Object context,setupReservation;boolean operationOwned,freshReportRetained;File home,work,operationDir,latestReport;String operation,session,runId;long startedUptime;int checkpointFailure;
  static final String BLOCK_MESSAGE="blocked";
  boolean pointerFails;void write(File path,byte[] data)throws IOException{if(pointerFails)throw new IOException("pointer unwritable");Files.write(path.toPath(),data);}void line(String message){}
  RECORD_METHOD
  ClientRuntime(File root){home=new File(root,"m2");work=new File(root,"client");work.mkdirs();}
  static boolean cleanupBlocked(Object c){return false;}
  void recordLifecycle(String event){if(checkpointFailure==1)throw new IllegalStateException("checkpoint unavailable");if(checkpointFailure==2)throw new OutOfMemoryError("checkpoint memory");}
  static synchronized Object acquireReportExport(Object c)throws IOException{if(held!=null)throw new IOException();return held=new Object();}
  static synchronized void releaseStorage(Object o){if(held==o)held=null;}
  BEGIN_METHOD
 }

 static class Intent {static final int FLAG_GRANT_READ_URI_PERMISSION=1,FLAG_GRANT_WRITE_URI_PERMISSION=2;String source;boolean missingData;android.net.Uri data=new android.net.Uri();Intent(String s){source=s;}Intent(Object c,Class<?> type){}android.net.Uri getData(){return missingData?null:data;}String getStringExtra(String k){return source;}Intent setAction(String action){return this;}Intent setData(android.net.Uri uri){data=uri;return this;}Intent putExtra(String key,String value){source=value;return this;}Intent addFlags(int flags){return this;}}
 static class PowerManager {static final int PARTIAL_WAKE_LOCK=1;WakeLock last;WakeLock newWakeLock(int i,String s){return last=new WakeLock();}static class WakeLock {volatile boolean held;void acquire(long n){held=true;}boolean isHeld(){return held;}void release(){held=false;}}}
 static class Preferences {Map<String,Object> values=new HashMap<>();boolean failCommit;Preferences edit(){return this;}Preferences putBoolean(String k,boolean v){values.put(k,v);return this;}Preferences putString(String k,String v){values.put(k,v);return this;}boolean commit(){if(failCommit)throw new IllegalStateException("preferences unavailable");return true;}}
 static class Main {volatile Runnable delayed;void post(Runnable r){r.run();}void postDelayed(Runnable r,long ms){delayed=r;}void removeCallbacks(Runnable r){if(delayed==r)delayed=null;}}
 static class Resolver {void takePersistableUriPermission(android.net.Uri uri,int flags){}OutputStream output;volatile boolean ignoreOpen;final CountDownLatch entered=new CountDownLatch(1),resume=new CountDownLatch(1);android.content.res.AssetFileDescriptor openAssetFileDescriptor(android.net.Uri uri,String mode,android.os.CancellationSignal signal){if(ignoreOpen){entered.countDown();try{resume.await();}catch(InterruptedException ignored){}}return new android.content.res.AssetFileDescriptor(output);}}
 static class ClientService {
  static final String PREFS="client_ui",POWER_SERVICE="power",EXPORT_REPORT="export";static final int MODE_PRIVATE=0,NOTICE=61,STOP_FOREGROUND_REMOVE=1;
  static final AtomicBoolean reportProviderOpening=new AtomicBoolean();
  volatile boolean destroyed,busy,storageBusy,reportExporting,foreground;boolean foregroundFails;Object exportOwner;File storageReport,root,report;
  String stage,detail;int stopped;PowerManager power=new PowerManager();Preferences prefs=new Preferences();Main main=new Main();Resolver resolver=new Resolver();
  ExecutorService worker=Executors.newSingleThreadExecutor();
  ClientService(File root){this.root=root;}File getFilesDir(){return root;}Object getSystemService(String s){return power;}
  Preferences getSharedPreferences(String s,int i){return prefs;}Resolver getContentResolver(){return resolver;}
  Object notification(){return null;}void startForeground(int n,Object notice){if(foregroundFails)throw new IllegalStateException("foreground rejected");foreground=true;}void stopForeground(int n){foreground=false;}void stopSelf(){stopped++;}void publish(){}
  void idle()throws Exception{worker.submit(()->{}).get(3,TimeUnit.SECONDS);}void close(){worker.shutdownNow();}
 METHODS
 }
 static class PausedOutput extends OutputStream {
  final CountDownLatch entered=new CountDownLatch(1),resume=new CountDownLatch(1);boolean fail;volatile boolean closed;int bytes,peak;
  PausedOutput(boolean fail){this.fail=fail;}
  public void write(int b)throws IOException{throw new AssertionError("unbounded singlebyte copy");}
  public void write(byte[] b,int off,int n)throws IOException{peak=Math.max(peak,n);entered.countDown();if(resume.getCount()>0)throw new android.system.Os.WouldBlock();if(closed||fail)throw new IOException("provider failure");bytes+=n;}
  public void close(){closed=true;resume.countDown();}
 }
 static void scenario(String name)throws Exception {
  File root=Files.createTempDirectory("coh-export-private-").toFile();File run=new File(root,"client/reports/1791679100000-123456abcdef");need(run.mkdirs());
  File report=new File(run,"coh-character-reopen-1791679100000-123456abcdef.zip");byte[] data=new byte[200000];new Random(3).nextBytes(data);try(ZipOutputStream zip=new ZipOutputStream(Files.newOutputStream(report.toPath()))){zip.putNextEntry(new ZipEntry("operation.log"));zip.write(data);zip.closeEntry();}byte[] original=Files.readAllBytes(report.toPath());
  ClientService s=new ClientService(root);PausedOutput out=new PausedOutput(name.equals("provider"));s.resolver.output=out;
  try{
   s.startReportExport(new Intent(report.getPath()));need(out.entered.await(2,TimeUnit.SECONDS));
   need(s.foreground&&s.reportExporting&&s.power.last.isHeld()&&ClientRuntime.held!=null&&Boolean.TRUE.equals(s.prefs.values.get("export_busy")));
   // There is no Activity or bound client in this owner. Repeated start cannot steal it.
   Object owner=s.exportOwner;s.startReportExport(new Intent(report.getPath()));need(owner==s.exportOwner&&s.foreground);
   if(name.equals("timeout")){need(s.main.delayed!=null);s.main.delayed.run();}
   else {if(name.equals("mutated"))Files.write(report.toPath(),new byte[]{1});out.resume.countDown();}
   s.idle();need(!s.foreground&&!s.reportExporting&&!s.power.last.isHeld()&&ClientRuntime.held==null);
   need(Boolean.FALSE.equals(s.prefs.values.get("export_busy"))&&s.stopped==1&&out.closed&&out.peak<=65536);
   if(name.equals("success")){need(s.stage.equals("Report exported")&&out.bytes==original.length);}
   else need(s.stage.equals("Export incomplete"));
   if(!name.equals("mutated"))need(Arrays.equals(original,Files.readAllBytes(report.toPath())));
  }finally{out.close();s.close();}
 }
 static void ignoredOpen()throws Exception{
  ClientService s=new ClientService(Files.createTempDirectory("coh-export-open-").toFile());PausedOutput out=new PausedOutput(false);s.resolver.output=out;s.resolver.ignoreOpen=true;
  try{long start=System.nanoTime();try{s.openReportDestination(new android.net.Uri(),new android.os.CancellationSignal(),new AtomicBoolean(),start+TimeUnit.MILLISECONDS.toNanos(80));throw new AssertionError();}catch(IOException expected){}
   need(System.nanoTime()-start<TimeUnit.SECONDS.toNanos(1));need(ClientService.reportProviderOpening.get());
   s.idle(); // The main service worker remains available while the provider ignores cancellation.
   s.resolver.resume.countDown();for(int i=0;i<100&&!out.closed;i++)Thread.sleep(5);need(out.closed&&!ClientService.reportProviderOpening.get());
  }finally{s.resolver.resume.countDown();s.close();}
 }
 static void finiteDestination()throws Exception{
  ClientService s=new ClientService(Files.createTempDirectory("coh-export-finite-").toFile());PausedOutput output=new PausedOutput(false);
  android.content.res.AssetFileDescriptor asset=new android.content.res.AssetFileDescriptor(output);asset.declared=32;
  try{try{s.boundedReportOutput(asset,new AtomicBoolean(),System.nanoTime()+TimeUnit.SECONDS.toNanos(1));throw new AssertionError();}catch(IOException expected){}need(output.bytes==0);}finally{asset.close();s.close();}
 }
 static void beginFailure(String mode)throws Exception {
  File root=Files.createTempDirectory("coh-begin-owner-").toFile();ClientRuntime runtime=new ClientRuntime(root);
  if(mode.equals("begin_io"))Files.write(new File(runtime.work,"reports").toPath(),new byte[]{1});
  else runtime.checkpointFailure=mode.equals("begin_heap")?2:1;
  try{runtime.begin("character_reopen","1234567890abcdef1234567890abcdef");throw new AssertionError("failure expected");}
  catch(IOException|IllegalStateException|OutOfMemoryError expected){}
  need(!ClientRuntime.operationActive&&!runtime.operationOwned);
  if(mode.equals("begin_io"))Files.delete(new File(runtime.work,"reports").toPath());runtime.checkpointFailure=0;
  runtime.begin("character_reopen","1234567890abcdef1234567890abcdef");need(ClientRuntime.operationActive&&runtime.operationOwned&&runtime.operationDir.isDirectory());
 }
 static class BaseActivity {protected void onActivityResult(int request,int result,Intent data){}}
 static class PickerActivity extends BaseActivity {
  static final int IMPORT=1,EXPORT=2,STORAGE_EXPORT=3,RESULT_OK=4;
  String pendingExport,pendingStorageExport,pendingExportSource;android.net.Uri pendingExportDestination,pendingImport;boolean importWaiting;Object service=new Object();int dispatched;
  Resolver resolver=new Resolver();Resolver getContentResolver(){return resolver;}void dispatchPendingImport(){}void startForegroundService(Intent intent){dispatched++;}
  static class Toast {static final int LENGTH_LONG=1;static Toast makeText(Object activity,String message,int length){return new Toast();}void show(){}}
  PICKER_METHODS
 }
 static void picker(String mode)throws Exception {
  File privateReport=Files.createTempFile("coh-picker-retained-",".zip").toFile();Files.write(privateReport.toPath(),new byte[]{1,2});PickerActivity a=new PickerActivity();a.pendingExport=privateReport.getPath();a.pendingStorageExport=privateReport.getPath();Intent selection=new Intent(privateReport.getPath());
  if(mode.equals("picker_cancel")){a.onActivityResult(PickerActivity.EXPORT,0,selection);need(a.pendingExport==null&&a.dispatched==0&&a.pendingExportSource==null);}
  else if(mode.equals("picker_missing_uri")){selection.missingData=true;a.onActivityResult(PickerActivity.EXPORT,PickerActivity.RESULT_OK,selection);need(a.pendingExport==null&&a.dispatched==0&&a.pendingExportSource==null);}
  else if(mode.equals("picker_storage_cancel")){a.onActivityResult(PickerActivity.STORAGE_EXPORT,0,null);need(a.pendingStorageExport==null&&a.dispatched==0&&a.pendingExportSource==null);}
  else{a.onActivityResult(PickerActivity.EXPORT,PickerActivity.RESULT_OK,selection);need(a.dispatched==1&&a.pendingExport==null&&a.pendingExportSource==null&&a.pendingExportDestination==null);a.onActivityResult(PickerActivity.EXPORT,PickerActivity.RESULT_OK,selection);need(a.dispatched==1);}
  need(privateReport.isFile()&&privateReport.length()==2&&ClientRuntime.held==null);
 }
 static void dispatchFailure(String mode)throws Exception {
  File root=Files.createTempDirectory("coh-report-dispatch-").toFile();File run=new File(root,"client/reports/1791679100000-123456abcdef");need(run.mkdirs());File report=new File(run,"coh-character-reopen-1791679100000-123456abcdef.zip");
  try(ZipOutputStream zip=new ZipOutputStream(Files.newOutputStream(report.toPath()))){zip.putNextEntry(new ZipEntry("operation.log"));zip.write(new byte[]{1});zip.closeEntry();}
  ClientService s=new ClientService(root);s.report=report;
  try {
   if(mode.endsWith("worker"))s.worker.shutdown();else s.foregroundFails=true;
   if(mode.startsWith("recovery"))s.recoverReports();else s.startReportExport(new Intent(report.getPath()));
   need(!s.reportExporting&&!s.foreground&&ClientRuntime.held==null&&s.exportOwner==null&&s.stopped==1);
   need(s.power.last==null||!s.power.last.isHeld());need(s.main.delayed==null&&report.isFile());
  }finally{s.close();}
 }
 static void partialRecovery()throws Exception {
  File root=Files.createTempDirectory("coh-partial-recovery-").toFile();Path reports=Files.createDirectories(root.toPath().resolve("client/reports"));
  Path old=Files.createDirectory(reports.resolve("1791679100000-123456abcdef"));Path latest=Files.createDirectory(reports.resolve("1791679200000-123456abcdef"));
  Path outside=root.toPath().resolve("foreign-checkpoint.json");Files.write(outside,"DO_NOT_EXPORT".getBytes());Files.createSymbolicLink(old.resolve("checkpoint.json"),outside);
  ClientReports.checkpoint(latest.toFile(),"{\"session_id\":\"1234567890abcdef1234567890abcdef\",\"phase\":\"save\"}".getBytes());
  ClientService s=new ClientService(root);
  try{s.recoverReports();s.idle();need(s.stage.equals("Recovery needs attention")&&s.report!=null&&s.report.getParentFile().equals(latest.toFile()));
   need(!s.reportExporting&&ClientRuntime.held==null&&!s.foreground&&!s.power.last.isHeld());need(new String(Files.readAllBytes(outside)).equals("DO_NOT_EXPORT"));
   byte[] retained=Files.readAllBytes(s.report.toPath());s.recoverReports();s.idle();need(ClientReports.reports(root,8).size()==1&&Arrays.equals(retained,Files.readAllBytes(s.report.toPath())));
  }finally{s.close();}
 }
 static void pointerFailure()throws Exception {
  File root=Files.createTempDirectory("coh-report-pointer-").toFile();ClientRuntime r=new ClientRuntime(root);r.pointerFails=true;File committed=new File(root,"complete.zip");Files.write(committed.toPath(),new byte[]{1,2,3});
  r.recordCommittedReport(committed);need(r.freshReportRetained&&r.latestReport.equals(committed)&&committed.length()==3);
 }
 static void retry()throws Exception {
  File root=Files.createTempDirectory("coh-report-retry-").toFile();File run=new File(root,"client/reports/1791679100000-123456abcdef");need(run.mkdirs());File report=new File(run,"coh-character-reopen-1791679100000-123456abcdef.zip");
  try(ZipOutputStream zip=new ZipOutputStream(Files.newOutputStream(report.toPath()))){zip.putNextEntry(new ZipEntry("operation.log"));zip.write(new byte[]{1});zip.closeEntry();}byte[] original=Files.readAllBytes(report.toPath());
  ClientService s=new ClientService(root);
  try{PausedOutput failed=new PausedOutput(true);failed.resume.countDown();s.resolver.output=failed;s.startReportExport(new Intent(report.getPath()));s.idle();need(s.stage.equals("Export incomplete"));
   PausedOutput success=new PausedOutput(false);success.resume.countDown();s.resolver.output=success;s.startReportExport(new Intent(report.getPath()));s.idle();need(s.stage.equals("Report exported")&&success.bytes==original.length);
   need(ClientReports.reports(root,8).size()==1&&Arrays.equals(original,Files.readAllBytes(report.toPath())));
  }finally{s.close();}
 }
 public static void main(String[] args)throws Exception{if(args[0].startsWith("picker_"))picker(args[0]);else if(args[0].contains("_worker")||args[0].contains("_foreground"))dispatchFailure(args[0]);else if(args[0].equals("partial_recovery"))partialRecovery();else if(args[0].equals("pointer_failure"))pointerFailure();else if(args[0].equals("retry"))retry();else if(args[0].startsWith("begin_"))beginFailure(args[0]);else if(args[0].equals("ignored_open"))ignoredOpen();else if(args[0].equals("finite"))finiteDestination();else scenario(args[0]);System.out.println("PASS");}
}
'''.replace(' METHODS',methods).replace('  PICKER_METHODS','\n'.join(sidebar.method((JAVA/'ClientActivity.java').read_text(),sig) for sig in ('@Override protected void onActivityResult(', 'private void dispatchPendingExport('))).replace('  RECORD_METHOD',sidebar.method((JAVA/'ClientRuntime.java').read_text(),'private void recordCommittedReport(')).replace('  BEGIN_METHOD',sidebar.method((JAVA/'ClientRuntime.java').read_text(),'private synchronized void begin('))
        host=base/'ReportLifecycleHost.java';host.write_text(harness)
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(base),str(uri),str(cancellation),str(descriptor),str(parcel),str(constants),str(errno),str(osjava),str(RECOVERY),str(host)],check=True,capture_output=True,text=True,timeout=60)

    def check(self,name):
        result=subprocess.run(['java','-cp',self.tmp.name,'io.github.russianranger.cohclientinteractive.ReportLifecycleHost',name],check=True,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.stdout.strip(),'PASS')
    def test_service_owns_export_with_no_activity(self):self.check('success')
    def test_provider_failure_retains_source_and_releases_owner(self):self.check('provider')
    def test_watchdog_closes_blocked_stream_and_reports_incomplete(self):self.check('timeout')
    def test_changed_source_cannot_be_reported_complete(self):self.check('mutated')
    def test_unresponsive_provider_open_cannot_hold_service_worker(self):self.check('ignored_open')
    def test_finite_destination_cannot_write_outside_its_section(self):self.check('finite')
    def test_report_storage_io_failure_releases_operation_owner(self):self.check('begin_io')
    def test_checkpoint_exception_releases_operation_owner(self):self.check('begin_exception')
    def test_checkpoint_heap_failure_releases_operation_owner(self):self.check('begin_heap')
    def test_cancelled_document_picker_keeps_private_report(self):self.check('picker_cancel')
    def test_missing_document_uri_keeps_private_report(self):self.check('picker_missing_uri')
    def test_cancelled_storage_document_picker_does_not_acquire_owner(self):self.check('picker_storage_cancel')
    def test_duplicate_document_result_cannot_dispatch_duplicate_export(self):self.check('picker_duplicate')
    def test_export_worker_rejection_releases_admission(self):self.check('export_worker')
    def test_export_foreground_failure_releases_admission(self):self.check('export_foreground')
    def test_recovery_worker_rejection_releases_admission(self):self.check('recovery_worker')
    def test_recovery_foreground_failure_releases_admission(self):self.check('recovery_foreground')
    def test_partial_recovery_selects_current_safe_archive_despite_bad_history(self):self.check('partial_recovery')
    def test_unwritable_pointer_cannot_erase_committed_report(self):self.check('pointer_failure')
    def test_failed_export_can_retry_without_duplicate_or_changed_private_report(self):self.check('retry')
    def test_relaunch_preserves_pointer_and_preflights_before_retirement(self):
        source=(JAVA/'ClientRuntime.java').read_text();begin=sidebar.method(source,'private synchronized void begin(')
        self.assertNotIn('latestReport = null',begin);self.assertNotIn('pointer.delete()',begin)
        run=sidebar.method(source,'private Result runCharacter(')
        self.assertLess(run.index('ClientSocketRecovery.prepare('),run.index('removePreviousGuestOutput()'))
        self.assertLess(run.index('ClientReports.preservePrevious('),run.index('removePreviousGuestOutput()'))
        self.assertNotIn('socketDir.getPath(), 0700',run)
        activity=(JAVA/'ClientActivity.java').read_text()
        self.assertNotIn('exporter.execute(',activity)
        self.assertIn('ClientService.EXPORT_REPORT',activity)
        self.assertIn('ClientService.RECOVER_REPORTS',activity)
        self.assertIn('service.retainedReports()',activity)

if __name__=='__main__':unittest.main()
