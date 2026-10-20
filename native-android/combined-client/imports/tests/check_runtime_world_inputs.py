#!/usr/bin/env python3
"""Run the shipped world resolver with real files and explicit Android stubs.

Native dup/pread/GLES qualification is in check_live_world.py. No APK, imported
archive download or server is needed; small archive bytes here are format fixtures.
"""
from pathlib import Path
import argparse, importlib.util, json, subprocess, tempfile
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[2];JAVA=NATIVE/'combined-client/app/src/main/java/org/coh/nativecombined'
HOST=r'''
package org.coh.nativecombined;
import android.content.Context;import android.system.Os;import io.github.russianranger.cohdiagnostic.AssetPackStore;import org.json.JSONObject;import java.io.*;import java.nio.file.*;import java.util.*;
public class RuntimeWorldInputsHost {
 static int checks;static void need(boolean b){checks++;if(!b)throw new AssertionError("control "+checks);}
 interface Work{void run()throws Exception;}static void fail(Work w)throws Exception{boolean failed=false;try{w.run();}catch(Exception|OutOfMemoryError expected){failed=true;}need(failed);need(Os.openHandles()==0);}
 static byte[] bytes(String s)throws Exception{return s.getBytes("UTF-8");}
 static JSONObject pin(byte[] b){return new JSONObject().put("bytes",b.length).put("sha256",ImportContract.hex(ImportContract.hash().digest(b)));}
 static void write(File p,byte[] b)throws Exception{if(p.exists())Os.chmod(p.toString(),0600);Files.write(p.toPath(),b);Os.chmod(p.toString(),0444);}
 public static void main(String[] args)throws Exception{
  File root=new File(args[0]);root.mkdirs();Context c=new Context(root);byte[] index=new byte[64];System.arraycopy(bytes("COHLIVE1"),0,index,0,8);byte[] atlas=new byte[128],client=new byte[96],donor=bytes("donor");Arrays.fill(atlas,(byte)3);Arrays.fill(client,(byte)7);
  JSONObject manifest=new JSONObject().put("format",1).put("files",new JSONObject().put("atlas-world-supplement.zip",pin(atlas)).put("client-visual-assets.zip",pin(client)));
  c.assets.put("runtime/runtime-manifest.json",bytes(manifest.toString()));c.assets.put("runtime/runtime-lock.json",bytes(new JSONObject().put("base",pin(donor)).put("wine",pin(donor)).toString()));
  c.assets.put("combined/import-contract.json",bytes(new JSONObject().put("format",1).put("donor_apk",pin(donor).put("name","donor.apk")).put("donor_files",new JSONObject().put("assets/runtime/test.bin",pin(donor))).put("bundled_files",new JSONObject()).toString()));
  File apk=new File(root,"index.apk"),a=new File(root,"atlas.zip"),b=new File(root,"client.zip");byte[] envelope=new byte[index.length+74];System.arraycopy(index,0,envelope,37,index.length);write(apk,envelope);write(a,atlas);write(b,client);c.assets.put("live-world.bin",index);c.assetFiles.put("live-world.bin",apk);
  AssetPackStore.objects.put("runtime/atlas-world-supplement.zip",a);AssetPackStore.objects.put("runtime/client-visual-assets.zip",b);AssetPackStore.accepted=true;ImportStore store=new ImportStore(c,null);ImportContract.Control control=new ImportContract.Control();
  RuntimeWorldInputs input=RuntimeWorldInputs.open(c,store,pin(index),control);need(Os.openHandles()==3);need(input.fds[0]>=0&&input.fds[1]>=0&&input.fds[2]>=0);need(input.offsets[0]==37&&input.offsets[1]==0&&input.lengths[0]==64&&input.lengths[1]==128&&input.lengths[2]==96);need(input.stagingPayloadBytes()==16444);input.close();input.close();need(Os.openHandles()==0&&input.fds[0]==-1&&input.stagingPayloadBytes()==0);
  fail(()->RuntimeWorldInputs.open(c,store,new JSONObject().put("bytes",63).put("sha256",pin(index).getString("sha256")),control));
  fail(()->RuntimeWorldInputs.open(c,store,new JSONObject().put("bytes",64).put("sha256",String.join("",Collections.nCopies(64,"0"))),control));
  fail(()->RuntimeWorldInputs.open(c,store,new JSONObject().put("bytes",64L+65536L*96L+1).put("sha256",pin(index).getString("sha256")),control));
  AssetPackStore.accepted=false;fail(()->RuntimeWorldInputs.open(c,store,pin(index),control));AssetPackStore.accepted=true;
  AssetPackStore.objects.remove("runtime/client-visual-assets.zip");fail(()->RuntimeWorldInputs.open(c,store,pin(index),control));AssetPackStore.objects.put("runtime/client-visual-assets.zip",b);
  Os.chmod(b.toString(),0600);fail(()->RuntimeWorldInputs.open(c,store,pin(index),control));Os.chmod(b.toString(),0444);
  File link=new File(root,"client-link.zip");Files.deleteIfExists(link.toPath());Files.createSymbolicLink(link.toPath(),b.toPath());AssetPackStore.objects.put("runtime/client-visual-assets.zip",link);fail(()->RuntimeWorldInputs.open(c,store,pin(index),control));AssetPackStore.objects.put("runtime/client-visual-assets.zip",b);
  write(b,new byte[95]);fail(()->RuntimeWorldInputs.open(c,store,pin(index),control));write(b,client);
  ImportContract.Control cancelled=new ImportContract.Control();cancelled.cancel();fail(()->RuntimeWorldInputs.open(c,store,pin(index),cancelled));
  ImportContract.Control mid=new ImportContract.Control();Os.afterRead=()->mid.cancel();fail(()->RuntimeWorldInputs.open(c,store,pin(index),mid));Os.afterRead=null;
  Os.afterRead=()->{throw new OutOfMemoryError("injected after descriptor open");};fail(()->RuntimeWorldInputs.open(c,store,pin(index),control));Os.afterRead=null;
  Os.failClosePath=a.getPath();fail(()->RuntimeWorldInputs.open(c,store,pin(index),control));Os.failClosePath=null;
  for(int i=0;i<64;i++){try(RuntimeWorldInputs next=RuntimeWorldInputs.open(c,store,pin(index),control)){need(Os.openHandles()==3);}}need(Os.openHandles()==0);
  System.out.println("{\"passed\":true,\"controls\":"+checks+",\"repeat_open_close\":64,\"live_descriptors\":0,\"verification_payload_bytes\":16444,\"scope\":\"real shipped resolver; explicit Android/import stubs, not Android execution\"}");
 }
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
 spec=importlib.util.spec_from_file_location('world_existing_import_stubs',HERE/'check_imports.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base);stubs=dict(base.STUBS)
 stubs['android/content/Context.java']=stubs['android/content/Context.java'].replace('public final File files;', 'public final Map<String,File> assetFiles=new HashMap<>();public final File files;').replace('public class Assets {','public class Assets {public android.content.res.AssetFileDescriptor openFd(String name)throws IOException{return new android.content.res.AssetFileDescriptor(assetFiles.get(name),37,assets.get(name).length);}')
 os_stub=stubs['android/system/Os.java'].replace('static final Map<FileDescriptor,String> paths=', 'public static final Map<FileDescriptor,String> paths=')
 os_stub=os_stub.replace('public static void close(FileDescriptor fd)throws ErrnoException{try{inputs.remove(fd).close();paths.remove(fd);cloexec.remove(fd);}', 'public static void close(FileDescriptor fd)throws ErrnoException{try{String name=paths.get(fd);inputs.remove(fd).close();paths.remove(fd);cloexec.remove(fd);if(name!=null&&name.equals(failClosePath)){failClosePath=null;throw new IOException("injected close failure");}}')
 os_stub=os_stub.replace('public static int openHandles()', 'public static Runnable afterRead;public static String failClosePath;public static FileDescriptor duplicate(FileDescriptor fd)throws ErrnoException{return open(paths.get(fd),0x80001,0);}public static int pread(FileDescriptor fd,byte[] b,int off,int count,long position)throws ErrnoException{try{int n=inputs.get(fd).getChannel().read(java.nio.ByteBuffer.wrap(b,off,count),position);if(afterRead!=null)afterRead.run();return n<0?0:n;}catch(IOException e){throw new ErrnoException(e);}}public static int openHandles()')
 stubs['android/system/Os.java']=os_stub
 stubs['android/os/ParcelFileDescriptor.java']='''package android.os;import android.system.*;import java.io.*;public class ParcelFileDescriptor implements AutoCloseable {private FileDescriptor fd;private static int next=10;private final int id=next++;public ParcelFileDescriptor(FileDescriptor fd){this.fd=fd;}public static ParcelFileDescriptor dup(FileDescriptor fd)throws IOException{try{return new ParcelFileDescriptor(Os.duplicate(fd));}catch(Exception e){throw new IOException(e);}}public int getFd(){return id;}public FileDescriptor getFileDescriptor(){return fd;}public void close()throws IOException{if(fd!=null){FileDescriptor old=fd;fd=null;try{Os.close(old);}catch(Exception e){throw new IOException(e);}}}}'''
 stubs['android/content/res/AssetFileDescriptor.java']='''package android.content.res;import android.os.*;import android.system.*;import java.io.*;public class AssetFileDescriptor implements AutoCloseable {private final ParcelFileDescriptor fd;private final long offset,length;public AssetFileDescriptor(File file,long offset,long length)throws IOException{try{if(file==null)throw new IOException("missing asset");fd=new ParcelFileDescriptor(Os.open(file.getPath(),0x80001,0));this.offset=offset;this.length=length;}catch(Exception e){throw new IOException(e);}}public long getStartOffset(){return offset;}public long getDeclaredLength(){return length;}public FileDescriptor getFileDescriptor(){return fd.getFileDescriptor();}public ParcelFileDescriptor getParcelFileDescriptor(){return fd;}public void close()throws IOException{fd.close();}}'''
 pack=stubs['io/github/russianranger/cohdiagnostic/AssetPackStore.java'];pack=pack.replace('public class AssetPackStore {','public class AssetPackStore {public static final java.util.Map<String,File> objects=new java.util.HashMap<>();');pack=pack.replace('public File resolve(String p)throws IOException{throw new FileNotFoundException(p);}', 'public File resolve(String p)throws IOException{File f=objects.get(p);if(!accepted||f==null)throw new FileNotFoundException(p);return f;}');stubs['io/github/russianranger/cohdiagnostic/AssetPackStore.java']=pack
 files=[]
 for name,content in stubs.items():
  path=a.work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content);files.append(path)
 host=a.work/'org/coh/nativecombined/RuntimeWorldInputsHost.java';host.parent.mkdir(parents=True,exist_ok=True);host.write_text(HOST);files.append(host)
 files += [JAVA/name for name in ('ImportContract.java','ImportStore.java','RuntimeWorldInputs.java')]
 classes=a.work/'classes';classes.mkdir(exist_ok=True);subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(classes),*map(str,files)],check=True)
 result=subprocess.run(['java','-ea','-cp',str(classes),'org.coh.nativecombined.RuntimeWorldInputsHost',str(a.work/'inputs')],capture_output=True,text=True);
 if result.returncode: raise RuntimeError(result.stdout+result.stderr)
 report=json.loads(result.stdout);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
