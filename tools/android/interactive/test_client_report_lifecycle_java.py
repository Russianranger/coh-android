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
            'public Object beginReportExport(', 'public List<File> retainedReports(', 'private void startReportExport(', 'private android.content.res.AssetFileDescriptor openReportDestination(', 'private java.io.OutputStream boundedReportOutput('))
        harness=r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;import java.nio.file.*;import java.util.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;
public class ReportLifecycleHost {
 static void need(boolean b){if(!b)throw new AssertionError();}
 static class ClientRuntime {static volatile Object held;static synchronized Object acquireReportExport(Object c)throws IOException{if(held!=null)throw new IOException();return held=new Object();}static synchronized void releaseStorage(Object o){if(held==o)held=null;}}
 static class Intent {String source;Intent(String s){source=s;}android.net.Uri getData(){return new android.net.Uri();}String getStringExtra(String k){return source;}}
 static class PowerManager {static final int PARTIAL_WAKE_LOCK=1;WakeLock last;WakeLock newWakeLock(int i,String s){return last=new WakeLock();}static class WakeLock {volatile boolean held;void acquire(long n){held=true;}boolean isHeld(){return held;}void release(){held=false;}}}
 static class Preferences {Map<String,Boolean> values=new HashMap<>();Preferences edit(){return this;}Preferences putBoolean(String k,boolean v){values.put(k,v);return this;}boolean commit(){return true;}}
 static class Main {volatile Runnable delayed;void post(Runnable r){r.run();}void postDelayed(Runnable r,long ms){delayed=r;}void removeCallbacks(Runnable r){if(delayed==r)delayed=null;}}
 static class Resolver {OutputStream output;volatile boolean ignoreOpen;final CountDownLatch entered=new CountDownLatch(1),resume=new CountDownLatch(1);android.content.res.AssetFileDescriptor openAssetFileDescriptor(android.net.Uri uri,String mode,android.os.CancellationSignal signal){if(ignoreOpen){entered.countDown();try{resume.await();}catch(InterruptedException ignored){}}return new android.content.res.AssetFileDescriptor(output);}}
 static class ClientService {
  static final String PREFS="client_ui",POWER_SERVICE="power";static final int MODE_PRIVATE=0,NOTICE=61,STOP_FOREGROUND_REMOVE=1;
  static final AtomicBoolean reportProviderOpening=new AtomicBoolean();
  volatile boolean destroyed,busy,storageBusy,reportExporting,foreground;Object exportOwner;File storageReport,root;
  String stage,detail;int stopped;PowerManager power=new PowerManager();Preferences prefs=new Preferences();Main main=new Main();Resolver resolver=new Resolver();
  ExecutorService worker=Executors.newSingleThreadExecutor();
  ClientService(File root){this.root=root;}File getFilesDir(){return root;}Object getSystemService(String s){return power;}
  Preferences getSharedPreferences(String s,int i){return prefs;}Resolver getContentResolver(){return resolver;}
  Object notification(){return null;}void startForeground(int n,Object notice){foreground=true;}void stopForeground(int n){foreground=false;}void stopSelf(){stopped++;}void publish(){}
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
  File report=new File(run,"coh-character-reopen-1791679100000-123456abcdef.zip");byte[] original=new byte[200000];Arrays.fill(original,(byte)3);Files.write(report.toPath(),original);
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
 public static void main(String[] args)throws Exception{if(args[0].equals("ignored_open"))ignoredOpen();else if(args[0].equals("finite"))finiteDestination();else scenario(args[0]);System.out.println("PASS");}
}
'''.replace(' METHODS',methods)
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
