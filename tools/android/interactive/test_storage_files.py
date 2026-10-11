"""Exercise the shipped Android storage adapter and its explicit fd ownership.

The host adapter uses real no-follow FileChannels and /proc descriptor anchors.
It counts Os.open owners independently of JDK stream close: Android's borrowed
FileInputStream(FileDescriptor) does not release that owner, unlike the JDK.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
STUBS = {
    'android/system/ErrnoException.java': '''package android.system; public class ErrnoException extends Exception {public final int errno;public ErrnoException(String operation,int value){super(operation);errno=value;}}''',
    'android/system/StructStat.java': '''package android.system; public class StructStat {public int st_mode;public long st_dev,st_ino,st_nlink,st_size,st_blocks,st_mtime,st_ctime;}''',
    'android/system/OsConstants.java': '''package android.system; public class OsConstants {public static final int O_RDONLY=0,O_WRONLY=1,O_CREAT=64,O_EXCL=128,O_NOFOLLOW=131072,O_CLOEXEC=524288,O_NONBLOCK=2048,ENOENT=2;public static boolean S_ISREG(int n){return (n&0170000)==0100000;}public static boolean S_ISDIR(int n){return (n&0170000)==0040000;}public static boolean S_ISLNK(int n){return (n&0170000)==0120000;}}''',
    'android/system/Os.java': r'''package android.system;
import java.io.*;import java.nio.channels.*;import java.nio.file.*;import java.nio.file.attribute.*;import java.util.*;
public class Os {
 public static final Map<FileDescriptor,FileChannel> owned=new IdentityHashMap<>();
 public static String failOpen,swapOnOpen;public static int failErrno=13,failFstat,peak,opens,closes;public static Path swapTarget;
 static StructStat attributes(Path path,LinkOption... options)throws ErrnoException {
  try{Map<String,Object> a=Files.readAttributes(path,"unix:*",options);StructStat s=new StructStat();
   s.st_mode=((Number)a.get("mode")).intValue();s.st_dev=((Number)a.get("dev")).longValue();s.st_ino=((Number)a.get("ino")).longValue();
   s.st_nlink=((Number)a.get("nlink")).longValue();s.st_size=((Number)a.get("size")).longValue();s.st_blocks=(s.st_size+511)/512;
   s.st_mtime=((FileTime)a.get("lastModifiedTime")).toMillis();s.st_ctime=((FileTime)a.get("ctime")).toMillis();return s;
  }catch(NoSuchFileException e){throw new ErrnoException("stat",2);}catch(IOException e){throw new ErrnoException("stat",13);}
 }
 public static int raw(FileDescriptor descriptor){try{java.lang.reflect.Field f=FileDescriptor.class.getDeclaredField("fd");f.setAccessible(true);return f.getInt(descriptor);}catch(Exception e){throw new AssertionError(e);}}
 public static StructStat lstat(String path)throws ErrnoException{return attributes(Paths.get(path),LinkOption.NOFOLLOW_LINKS);}
 public static StructStat fstat(FileDescriptor descriptor)throws ErrnoException {if(failFstat>0){failFstat--;throw new ErrnoException("fstat",5);}return attributes(Paths.get("/proc/self/fd/"+raw(descriptor)));}
 public static FileDescriptor open(String path,int flags,int mode)throws ErrnoException {
  if(path.equals(failOpen))throw new ErrnoException("open",failErrno);
  try {
   if(path.equals(swapOnOpen)){swapOnOpen=null;Files.delete(Paths.get(path));Files.createSymbolicLink(Paths.get(path),swapTarget);}
   Set<OpenOption> options=new HashSet<>();options.add((flags&OsConstants.O_WRONLY)!=0?StandardOpenOption.WRITE:StandardOpenOption.READ);
   if((flags&OsConstants.O_NOFOLLOW)!=0)options.add(LinkOption.NOFOLLOW_LINKS);
   if((flags&OsConstants.O_CREAT)!=0)options.add((flags&OsConstants.O_EXCL)!=0?StandardOpenOption.CREATE_NEW:StandardOpenOption.CREATE);
   FileChannel channel=FileChannel.open(Paths.get(path),options);
   java.lang.reflect.Field field=channel.getClass().getDeclaredField("fd");field.setAccessible(true);FileDescriptor descriptor=(FileDescriptor)field.get(channel);
   owned.put(descriptor,channel);opens++;peak=Math.max(peak,owned.size());return descriptor;
  }catch(IOException e){throw new ErrnoException("open",40);}catch(ReflectiveOperationException e){throw new AssertionError(e);}
 }
 public static void close(FileDescriptor descriptor)throws ErrnoException {FileChannel channel=owned.remove(descriptor);if(channel==null)throw new ErrnoException("close",9);closes++;try{channel.close();}catch(IOException ignored){}}
 public static String readlink(String path)throws ErrnoException {try{return Files.readSymbolicLink(Paths.get(path)).toString();}catch(IOException e){throw new ErrnoException("readlink",22);}}
 public static String strerror(int errno){return errno==13?"Permission denied":errno==24?"Too many open files":errno==40?"Too many symbolic links":errno==5?"Input/output error":"OS error";}
}''',
    'android/os/ParcelFileDescriptor.java': '''package android.os;import java.io.*;import android.system.*;public class ParcelFileDescriptor implements Closeable {FileDescriptor descriptor;ParcelFileDescriptor(FileDescriptor fd){descriptor=fd;}public static ParcelFileDescriptor dup(FileDescriptor fd)throws IOException {try{return new ParcelFileDescriptor(Os.open("/proc/self/fd/"+Os.raw(fd),OsConstants.O_RDONLY,0));}catch(ErrnoException e){throw new IOException(e);}}public int getFd(){return Os.raw(descriptor);}public void close()throws IOException {try{Os.close(descriptor);}catch(ErrnoException e){throw new IOException(e);}}}''',
    'org/json/JSONObject.java': '''package org.json;import java.util.*;public class JSONObject {public static final Object NULL=new Object();public JSONObject(String text){if(!text.equals("{}"))throw new IllegalArgumentException("invalid JSON fixture");}public Iterator<String> keys(){return Collections.emptyIterator();}public Object get(String key){return null;}}''',
    'org/json/JSONArray.java': '''package org.json;public class JSONArray {public int length(){return 0;}public Object get(int n){return null;}}''',
}
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import android.system.*;import java.io.*;import java.nio.file.*;import java.util.*;import java.util.zip.*;
public class StorageFilesHost {
 interface Work {void run()throws Exception;}
 static void need(boolean value){if(!value)throw new AssertionError();}
 static IOException refuses(Work work)throws Exception {try{work.run();throw new AssertionError("expected refusal");}catch(IOException expected){return expected;}}
 static Path root;static StorageFiles fs;
 static void zip(String name,String member,String text)throws Exception {try(ZipOutputStream out=new ZipOutputStream(Files.newOutputStream(root.resolve(name)))){out.putNextEntry(new ZipEntry(member));out.write(text.getBytes("UTF-8"));out.closeEntry();}}
 static void noOwners(){need(Os.owned.isEmpty()&&Os.opens==Os.closes);}
 static void walk(String path,int depth)throws Exception {
  fs.visitDirectory(path,name->{String child=path.isEmpty()?name:path+"/"+name;StorageAudit.Stat stat=fs.stat(child);if(stat.kind==StorageAudit.Kind.DIRECTORY){try{walk(child,depth+1);}catch(IOException e){throw e;}catch(Exception e){throw new IOException(e);}}});
 }
 public static void main(String[] args)throws Exception {
  Path home=Paths.get(args[1]);root=Files.createDirectory(home.resolve("files"));Files.createDirectory(home.resolve("cache"));fs=new StorageFiles(root.toFile());
  Files.write(root.resolve("identity"),new byte[]{1,2,3});zip("report.zip","android-client-report.json","{}");
  switch(args[0]) {
   case "repeated_reads":
    for(int i=0;i<2048;i++){need(fs.read("identity",20).length==3);need(fs.reportIdentity("report.zip",20).isEmpty());noOwners();}
    need(Os.peak==1);break;
   case "fstat_failure":
    for(int i=0;i<100;i++){Os.failFstat=1;need(refuses(()->fs.read("identity",20)).getMessage().contains("errno=5"));noOwners();Os.failFstat=1;refuses(()->fs.reportIdentity("report.zip",20));noOwners();}break;
   case "malformed_report":
    for(String content:new String[]{"invalid","{}".repeat(100)}) {zip("bad.zip","android-client-report.json",content);for(int i=0;i<100;i++){refuses(()->fs.reportIdentity("bad.zip",20));noOwners();}}
    zip("bad.zip","wrong.json","{}");refuses(()->fs.reportIdentity("bad.zip",20));noOwners();break;
   case "nofollow":
    Files.createSymbolicLink(root.resolve("linked"),root.resolve("identity"));refuses(()->fs.read("linked",20));
    Files.createSymbolicLink(root.resolve("directory-link"),home);refuses(()->fs.list("directory-link"));
    Os.swapOnOpen=root.resolve("identity").toString();Os.swapTarget=root.resolve("report.zip");
    need(refuses(()->fs.read("identity",20)).getMessage().contains("errno=40"));noOwners();break;
   case "directory_errno":
    Files.createDirectories(root.resolve("m2/blocked"));Os.failOpen=root.resolve("m2/blocked").toString();
    for(int errno:new int[]{13,24,40}){Os.failErrno=errno;String error=refuses(()->fs.list("m2/blocked")).getMessage();need(error.contains("errno="+errno)&&error.contains("m2/blocked")&&error.length()<240);noOwners();}break;
   case "deep_directory_failure":
    String path="deep";for(int i=0;i<64;i++){Files.createDirectory(root.resolve(path));path+="/d";}
    Os.failOpen=root.resolve(path.substring(0,path.length()-2)).toString();Os.failErrno=24;
    need(refuses(()->walk("deep",0)).getMessage().contains("errno=24"));noOwners();need(Os.peak<=128);break;
   case "directory_repeated":
    Files.createDirectories(root.resolve("d/e"));for(int i=0;i<1000;i++){walk("d",0);noOwners();}need(Os.peak==4);break;
   default:throw new AssertionError(args[0]);
  }
 }
}
'''


class StorageFilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        sources = []
        for name, text in STUBS.items():
            path = cls.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            sources.append(str(path))
        host = cls.root / 'StorageFilesHost.java'
        host.write_text(HARNESS)
        compiler = [shutil.which('javac')] if shutil.which('javac') else ['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main']
        subprocess.run(compiler + ['-d', str(cls.root), str(JAVA/'StorageAudit.java'), str(JAVA/'StorageFiles.java'), str(host)] + sources, check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def scenario(self, name):
        with tempfile.TemporaryDirectory() as home:
            result = subprocess.run(['java', '--add-opens', 'java.base/sun.nio.ch=ALL-UNNAMED', '--add-opens', 'java.base/java.io=ALL-UNNAMED', '-Xmx48m', '-cp', str(self.root), 'io.github.russianranger.cohclientinteractive.StorageFilesHost', name, home], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


for _name in ('repeated_reads', 'fstat_failure', 'malformed_report', 'nofollow', 'directory_errno', 'deep_directory_failure', 'directory_repeated'):
    setattr(StorageFilesTests, 'test_' + _name, lambda self, name=_name: self.scenario(name))


if __name__ == '__main__':
    unittest.main()
