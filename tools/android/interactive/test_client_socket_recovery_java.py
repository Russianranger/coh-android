"""Execute the shipped socket recovery decision and bounded process ownership gate."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientSocketRecovery.java'
STUBS = {
'android/content/Context.java': '''package android.content; import java.io.*; public class Context {public File getFilesDir(){return new File("/unused");}}''',
'android/net/LocalSocketAddress.java': '''package android.net; public class LocalSocketAddress {public enum Namespace {FILESYSTEM}; public LocalSocketAddress(String name,Namespace space){}}''',
'android/net/LocalSocket.java': '''package android.net; import java.io.*; public class LocalSocket implements Closeable {public OutputStream getOutputStream()throws IOException{return new ByteArrayOutputStream();} public FileDescriptor getFileDescriptor(){return new FileDescriptor();} public void connect(LocalSocketAddress a)throws IOException{} public void close()throws IOException{}}''',
'android/os/Process.java': '''package android.os; public class Process {public static int myUid(){return 10001;} public static int myPid(){return 73;}}''',
'android/os/ParcelFileDescriptor.java': '''package android.os; import java.io.*; public class ParcelFileDescriptor implements Closeable {public static ParcelFileDescriptor dup(FileDescriptor d)throws IOException{return new ParcelFileDescriptor();} public FileDescriptor getFileDescriptor(){return new FileDescriptor();}public int getFd(){return 5;}public void close()throws IOException{}}''',
'android/system/ErrnoException.java': '''package android.system; public class ErrnoException extends Exception {public final int errno;public ErrnoException(String function,int errno){this.errno=errno;}}''',
'android/system/StructStat.java': '''package android.system; public class StructStat {public int st_mode,st_uid,st_gid;public long st_dev,st_ino,st_nlink;}''',
'android/system/OsConstants.java': '''package android.system; public class OsConstants {public static final int O_RDONLY=0,O_NOFOLLOW=2,O_CLOEXEC=4,O_NONBLOCK=8,ENOENT=2,ECONNREFUSED=111,F_GETFL=3,F_SETFL=4;public static boolean S_ISREG(int n){return n==3;}public static boolean S_ISDIR(int n){return n==1;}public static boolean S_ISSOCK(int n){return n==2;}}''',
'android/system/Os.java': '''package android.system; import java.io.*; public class Os {public static StructStat lstat(String p)throws ErrnoException{return new StructStat();}public static StructStat fstat(FileDescriptor d)throws ErrnoException{return new StructStat();}public static FileDescriptor open(String p,int f,int m)throws ErrnoException{return new FileDescriptor();}public static void close(FileDescriptor d)throws ErrnoException{}public static void mkdir(String p,int mode)throws ErrnoException{}public static String strerror(int errno){return errno==111?"Connection refused":"other error";}public static int fcntlInt(FileDescriptor d,int command,int arg)throws ErrnoException{return 0;}}''',
}
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.util.*;
import java.nio.file.*;
import android.system.*;
public final class SocketRecoveryHost {
 static final int UID=10001;
 static ClientSocketRecovery.Identity identity(int kind,int uid,int mode,long ino,long links){return new ClientSocketRecovery.Identity(kind,uid,mode,4,ino,links);}
 static ClientSocketRecovery.Identity directory(long ino){return identity(ClientSocketRecovery.DIRECTORY,UID,0700,ino,2);}
 static ClientSocketRecovery.Identity socket(long ino){return identity(ClientSocketRecovery.SOCKET,UID,0700,ino,1);}
 static void need(boolean value){if(!value)throw new AssertionError();}
 interface Checked {void run()throws Exception;}
 static void refuses(Checked work)throws Exception {try{work.run();throw new AssertionError("recovery should refuse");}catch(IOException expected){}}
 static class Probe implements ClientSocketRecovery.Probe {
  ClientSocketRecovery.Identity root=SocketRecoveryHost.directory(1),dir=SocketRecoveryHost.directory(2),sock=SocketRecoveryHost.socket(3);
  String fault="";int rootReads,dirReads,sockReads,scans,connects,unlinks;boolean refused=true;
  public int uid(){return UID;}
  public ClientSocketRecovery.Identity root(){rootReads++;return fault.equals("root_changed")&&rootReads==2?SocketRecoveryHost.directory(9):root;}
  public ClientSocketRecovery.Identity directory(){dirReads++;return fault.equals("dir_changed")&&dirReads==2?SocketRecoveryHost.directory(9):dir;}
  public ClientSocketRecovery.Identity socket(){sockReads++;if(sockReads==2&&fault.equals("gone"))return null;return sockReads==2&&fault.equals("socket_changed")?SocketRecoveryHost.socket(9):sock;}
  public void requireNoOtherAppProcess()throws IOException {scans++;if(fault.equals("owner")||fault.equals("scan_unreadable")||(fault.equals("new_owner")&&scans==2))throw new IOException("ownership blocked");}
  public boolean connectionRefused()throws IOException {need(scans==1);connects++;if(fault.equals("connect_unreadable"))throw new IOException("ambiguous");return refused;}
  public void unlink(ClientSocketRecovery.Identity expected)throws IOException {need(scans==2&&connects==1&&expected.same(sock));if(fault.equals("unlink_race"))throw new IOException("inode changed in anchored adapter");unlinks++;}
  public void close(){}
 }
 static void stale()throws Exception {Probe p=new Probe();need(ClientSocketRecovery.prepare(p));need(p.unlinks==1&&p.scans==2&&p.connects==1);}
 static void missing()throws Exception {for(String target:new String[]{"socket","dir"}){Probe p=new Probe();if(target.equals("socket"))p.sock=null;else p.dir=null;need(!ClientSocketRecovery.prepare(p));need(p.unlinks==0&&p.scans==0&&p.connects==0);}}
 static void mutation(String fault)throws Exception {Probe p=new Probe();p.fault=fault;refuses(()->ClientSocketRecovery.prepare(p));need(p.unlinks==0);if(fault.equals("owner")||fault.equals("scan_unreadable"))need(p.connects==0);}
 static void gone()throws Exception {Probe p=new Probe();p.fault="gone";need(!ClientSocketRecovery.prepare(p));need(p.unlinks==0&&p.scans==2);}
 static void live()throws Exception {Probe p=new Probe();p.refused=false;refuses(()->ClientSocketRecovery.prepare(p));need(p.unlinks==0&&p.scans==1);}
 static void rootGroup()throws Exception {
  Probe owned=new Probe();owned.root=new ClientSocketRecovery.Identity(ClientSocketRecovery.DIRECTORY,UID,UID,0771,4,1,2);need(ClientSocketRecovery.prepare(owned));need(owned.unlinks==1);
  Probe foreign=new Probe();foreign.root=new ClientSocketRecovery.Identity(ClientSocketRecovery.DIRECTORY,UID,99,0771,4,1,2);refuses(()->ClientSocketRecovery.prepare(foreign));need(foreign.unlinks==0&&foreign.scans==0);
  for(int mode:new int[]{0711,0755,0770,0771}){Probe nonprivate=new Probe();nonprivate.dir=identity(ClientSocketRecovery.DIRECTORY,UID,mode,2,2);refuses(()->ClientSocketRecovery.prepare(nonprivate));need(nonprivate.unlinks==0&&nonprivate.scans==0);}
 }
 static void foreign()throws Exception {
  for(int which=0;which<3;which++)for(String fault:new String[]{"uid","kind","mode","links"}){
   if(which==2&&fault.equals("mode")||which!=2&&fault.equals("links"))continue;
   Probe p=new Probe();int kind=which==2?ClientSocketRecovery.SOCKET:ClientSocketRecovery.DIRECTORY;
   ClientSocketRecovery.Identity invalid=identity(fault.equals("kind")?ClientSocketRecovery.OTHER:kind,
    fault.equals("uid")?UID+1:UID,fault.equals("mode")?0777:0700,which+1,fault.equals("links")?2:which==2?1:2);
   if(which==0)p.root=invalid;else if(which==1)p.dir=invalid;else p.sock=invalid;
   refuses(()->ClientSocketRecovery.prepare(p));need(p.unlinks==0&&p.connects==0&&p.scans==0);
  }
 }
 static void errno()throws Exception {
  need(ClientSocketRecovery.explicitlyRefused(new IOException(new ErrnoException("connect",OsConstants.ECONNREFUSED))));
  need(ClientSocketRecovery.explicitlyRefused(new IOException(new IOException(new ErrnoException("connect",OsConstants.ECONNREFUSED)))));
  for(IOException e:new IOException[]{new IOException("Connection refused: additional context"),new IOException(new ErrnoException("connect",13)),new IOException(new ErrnoException("connect",OsConstants.ENOENT)),new IOException("ECONNREFUSED")})need(!ClientSocketRecovery.explicitlyRefused(e));
  need(ClientSocketRecovery.explicitlyRefused(new IOException(Os.strerror(OsConstants.ECONNREFUSED))));
  need(!ClientSocketRecovery.explicitlyRefused(new java.net.SocketTimeoutException(Os.strerror(OsConstants.ECONNREFUSED))));
  need(!ClientSocketRecovery.explicitlyRefused(new IOException(new IOException(Os.strerror(OsConstants.ECONNREFUSED)))));
  Throwable nested=new ErrnoException("connect",OsConstants.ECONNREFUSED);for(int n=0;n<9;n++)nested=new IOException(nested);need(!ClientSocketRecovery.explicitlyRefused((IOException)nested));
 }
 static void status()throws Exception {
  String valid="Name:\tproot\nPid:\t74\nUid:\t10001\t10001\t10001\t10001\n";
  need(ClientSocketRecovery.processOwner(valid.getBytes("US-ASCII"),74,UID)==UID);
  need(ClientSocketRecovery.processOwner(valid.replace("10001","0").getBytes("US-ASCII"),74,UID)==-1);
  need(ClientSocketRecovery.processOwner(valid.replace("Uid:\t10001\t10001\t10001\t10001","Uid:\t0\t0\t10001\t0").getBytes("US-ASCII"),74,UID)==UID);
  for(String broken:new String[]{"",valid.replace("74","75"),valid+"Uid:\t0\t0\t0\t0\n",valid.replace("Uid:","Wrong:"),valid.replace("10001","4294967295"),valid.replace("10001\t10001\t10001\t10001","10001"),valid+"Pid:\t74\n"})refuses(()->ClientSocketRecovery.processOwner(broken.getBytes("US-ASCII"),74,UID));
  refuses(()->ClientSocketRecovery.processOwner(new byte[ClientSocketRecovery.MAX_PROCESS_STATUS+1],74,UID));
 }
 static void processes()throws Exception {
  List<Path> paths=Arrays.asList(Paths.get("/proc/self"),Paths.get("/proc/73"),Paths.get("/proc/74"));
  ClientSocketRecovery.ProcessStat otherUid=p->p.toString().endsWith("73")?directory(73):identity(ClientSocketRecovery.DIRECTORY,99,0500,74,2);
  ClientSocketRecovery.requireNoOtherAppProcess(paths,otherUid,UID,73);
  ClientSocketRecovery.requireNoOtherAppProcess(paths,p->p.toString().endsWith("73")?directory(73):null,UID,73);
  refuses(()->ClientSocketRecovery.requireNoOtherAppProcess(paths,p->directory(73),UID,73));
  refuses(()->ClientSocketRecovery.requireNoOtherAppProcess(paths,p->{if(p.toString().endsWith("74"))throw new IOException("EACCES");return directory(73);},UID,73));
  refuses(()->ClientSocketRecovery.requireNoOtherAppProcess(paths,p->null,UID,73));
  refuses(()->ClientSocketRecovery.requireNoOtherAppProcess(paths,p->identity(ClientSocketRecovery.DIRECTORY,99,0500,74,2),UID,73));
  refuses(()->ClientSocketRecovery.requireNoOtherAppProcess(paths,p->socket(73),UID,73));
  List<Path> bounded=new ArrayList<>();bounded.add(Paths.get("/proc/73"));for(int i=0;i<ClientSocketRecovery.MAX_PROC_ENTRIES;i++)bounded.add(Paths.get("/proc/non_pid"));
  refuses(()->ClientSocketRecovery.requireNoOtherAppProcess(bounded,otherUid,UID,73));
 }
 public static void main(String[] args)throws Exception {
  switch(args[0]){case "stale":stale();break;case "missing":missing();break;case "live":live();break;case "foreign":foreign();break;case "rootGroup":rootGroup();break;case "errno":errno();break;case "processes":processes();break;case "status":status();break;case "gone":gone();break;default:mutation(args[0]);}
  System.out.println("PASS");
 }
}
'''

class ClientSocketRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='coh-socket-recovery-java-')
        cls.addClassCleanup(cls.tmp.cleanup)
        temp=Path(cls.tmp.name)
        sources=[]
        for relative,contents in STUBS.items():
            path=temp/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(contents);sources.append(path)
        host=temp/'SocketRecoveryHost.java';host.write_text(HARNESS)
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(temp),*map(str,sources),str(JAVA),str(host)],check=True,capture_output=True,text=True,timeout=60)
    def run_host(self,mode):
        result=subprocess.run(['java','-cp',self.tmp.name,'io.github.russianranger.cohclientinteractive.SocketRecoveryHost',mode],check=True,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.stdout.strip(),'PASS')
    def test_dead_owned_unchanged_socket_recovered_only_after_two_process_scans(self):self.run_host('stale')
    def test_missing_socket_or_directory_does_not_probe_or_mutate(self):self.run_host('missing')
    def test_live_listener_refuses_deletion(self):self.run_host('live')
    def test_socket_disappearing_after_probe_needs_no_deletion(self):self.run_host('gone')
    def test_android_app_group_root_allowed_but_display_directory_exactly_private(self):self.run_host('rootGroup')
    def test_wrong_owner_link_type_permissions_and_hardlink_refuse(self):self.run_host('foreign')
    def test_numeric_errno_or_exact_platform_exception_only_and_bounded_chain(self):self.run_host('errno')
    def test_kernel_uid_status_detects_non_dumpable_and_mixed_uid_owner(self):self.run_host('status')
    def test_process_ownership_requires_self_no_other_app_and_complete_bounded_inventory(self):self.run_host('processes')
    def test_ownership_uncertainty_and_all_inode_races_leave_socket_untouched(self):
        for fault in ('owner','scan_unreadable','new_owner','connect_unreadable','root_changed','dir_changed','socket_changed','unlink_race'):
            with self.subTest(fault=fault):self.run_host(fault)
    def test_android_adapter_anchors_fixed_path_and_never_kills_or_unlinks_runtime_data(self):
        source=JAVA.read_text()
        self.assertIn('OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK',source)
        self.assertIn('new File("/proc/self/fd/"+directoryFd.getFd(),"view.sock")',source)
        self.assertEqual(source.count('Files.delete('),1)
        self.assertIn('Files.delete(socketPath.toPath())',source)
        self.assertIn('Os.mkdir(directoryPath.getPath(),0700)',source)
        self.assertIn('(value.mode&0777)!=0700',source)
        self.assertIn('flags|OsConstants.O_NONBLOCK',source)
        self.assertNotIn('ProcessBuilder',source)
        self.assertNotIn('killProcess',source)
        self.assertNotIn('destroy(',source)
        self.assertNotIn('.delete()',source)

if __name__=='__main__':unittest.main()
