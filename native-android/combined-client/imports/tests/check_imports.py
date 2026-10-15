#!/usr/bin/env python3
"""Execute shipped import methods with real files/ZIPs; Android adapters are explicit stubs.

This does not run Android, Linux/Wine, PostgreSQL or a game server. Existing asset
and tar suites test the reused production archive engines separately.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import tarfile
import io

ROOT=Path(__file__).resolve().parents[4]
JAVA=ROOT/'combined-client/app/src/main/java/org/coh/nativecombined'
REPO=ROOT.parents[0]
STUBS={
'android/content/Context.java':'''package android.content;import java.io.*;import java.util.*;public class Context {public static final String ACTIVITY_SERVICE="activity"; public final Map<String,byte[]> assets=new HashMap<>();public final File files;public Context(File files){this.files=files;}public Context getApplicationContext(){return this;}public File getFilesDir(){return files;}public Object getSystemService(String name){return new android.app.ActivityManager();}public Assets getAssets(){return new Assets();}public class Assets {public InputStream open(String name)throws IOException{byte[] value=assets.get(name);if(value==null)throw new FileNotFoundException(name);return new ByteArrayInputStream(value);}}}''',
'android/app/ActivityManager.java':'''package android.app;public class ActivityManager {public static class MemoryInfo {public long availMem=16L<<30,totalMem=16L<<30,threshold=0;public boolean lowMemory;}public void getMemoryInfo(MemoryInfo m){}}''',
'android/os/Build.java':'''package android.os;public class Build {public static String[] SUPPORTED_ABIS={"arm64-v8a"};}''',
'android/os/SystemClock.java':'''package android.os;public class SystemClock {public static long uptimeMillis(){return System.nanoTime()/1000000;}}''',
'android/system/Os.java':'''package android.system;import java.nio.file.*;public class Os {public static void chmod(String name,int mode){}public static void symlink(String target,String name)throws Exception{Files.createSymbolicLink(Paths.get(name),Paths.get(target));}}''',
'org/json/JSONObject.java':'''package org.json;import java.util.*;public class JSONObject {static final Map<String,JSONObject> encoded=new HashMap<>();private final Map<String,Object> values=new LinkedHashMap<>();public JSONObject(){}public JSONObject(String text){JSONObject known=encoded.get(text);if(known==null)throw new IllegalArgumentException("Invalid fixture JSON");values.putAll(known.values);}public JSONObject put(String n,Object v){values.put(n,v);return this;}public int getInt(String n){return ((Number)values.get(n)).intValue();}public long getLong(String n){return ((Number)values.get(n)).longValue();}public String getString(String n){return (String)values.get(n);}public JSONObject getJSONObject(String n){return (JSONObject)values.get(n);}public boolean has(String n){return values.containsKey(n);}public Iterator<String> keys(){return values.keySet().iterator();}public String toString(){String key="fixture-json-"+encoded.size();encoded.put(key,this);return key;}}''',
'io/github/russianranger/cohdiagnostic/AssetPackStore.java':'''package io.github.russianranger.cohdiagnostic;import java.io.*;import android.content.Context;import org.json.JSONObject;public class AssetPackStore {public static boolean accepted;public interface Check {void check()throws IOException;}public interface Progress {void update(String n,long a,long b);}public AssetPackStore(Context c,JSONObject m,Check k,Progress p){}public String status(){return "fixture assets pending";}public boolean isAccepted(){return accepted;}public String importVolume(InputStream i)throws IOException{i.close();return "fixture";}public boolean contains(String p){return false;}public InputStream open(String p)throws IOException{throw new FileNotFoundException(p);}public File resolve(String p)throws IOException{throw new FileNotFoundException(p);}}''',
'io/github/russianranger/cohatlas/AtlasAssetImporter.java':'''package io.github.russianranger.cohatlas;import java.io.*;public class AtlasAssetImporter {public static File fixtureData;public interface Assets {InputStream open(String n)throws IOException;}public interface Progress {void update(String n,long a,long b,long c,long d);}public static class Control {public boolean requestCancel(){return true;}}public static class Summary {public File dataDirectory;}public AtlasAssetImporter(File f,Assets a){}public Summary inspect(){if(fixtureData==null)return null;Summary s=new Summary();s.dataDirectory=fixtureData;return s;}public Summary importArchive(InputStream i,Progress p,Control c){return null;}}''',
}
HOST=r'''
package org.coh.nativecombined;
import android.content.Context;import org.json.JSONObject;import java.io.*;import java.nio.file.*;import java.security.*;import java.util.*;import java.util.zip.*;
public final class ImportsHost {
 static int checks;static void need(boolean b,String m){checks++;if(!b)throw new AssertionError(m);}
 interface Work {void run()throws Exception;}
 static void fail(Work w)throws Exception {boolean failed=false;try{w.run();}catch(Exception e){failed=true;}need(failed,"invalid import was accepted");}
 static JSONObject pin(byte[] b){return new JSONObject().put("bytes",b.length).put("sha256",ImportContract.hex(ImportContract.hash().digest(b)));}
 static byte[] bytes(String s)throws Exception{return s.getBytes("UTF-8");}
 static byte[] zip(String name,byte[] body)throws Exception {ByteArrayOutputStream out=new ByteArrayOutputStream();try(ZipOutputStream z=new ZipOutputStream(out)){z.putNextEntry(new ZipEntry(name));z.write(body);z.closeEntry();}return out.toByteArray();}
 static Context context(File files,byte[] apk,byte[] body)throws Exception {
  files.mkdirs();Context c=new Context(files);
  JSONObject contract=new JSONObject().put("format",1).put("donor_apk",pin(apk).put("name","COH-Atlas-Gameplay-0.13.36.apk"))
    .put("donor_files",new JSONObject().put("assets/runtime/test.bin",pin(body))).put("bundled_files",new JSONObject());
  c.assets.put("combined/import-contract.json",bytes(contract.toString()));
  c.assets.put("runtime/runtime-manifest.json",bytes(new JSONObject().put("format",1).put("files",new JSONObject().put("test.bin",pin(body))).toString()));
  c.assets.put("runtime/runtime-lock.json",bytes(new JSONObject().put("base",pin(bytes("base"))).put("wine",pin(bytes("wine"))).toString()));return c;
 }
 static InputStream owned(byte[] data,int[] close){return new ByteArrayInputStream(data){@Override public void close(){close[0]++;need(close[0]==1,"provider closed twice");}};}
 public static void main(String[] args)throws Exception {
  File root=new File(args[0]);byte[] body=bytes("verified payload"),apk=zip("assets/runtime/test.bin",body);Context c=context(new File(root,"main"),apk,body);
  ImportStore store=new ImportStore(c,(p,d,t)->{});need(!store.donorReady(),"fresh donor ready");int[] closed={0};store.importDonorApk(owned(apk,closed),new ImportContract.Control());need(closed[0]==1&&store.donorReady(),"donor not atomically accepted");
  File member=new File(store.runtimePayloadDirectory(),"test.bin");need(Arrays.equals(body,Files.readAllBytes(member.toPath())),"wrong donor bytes");
  byte[] before=Files.readAllBytes(member.toPath());byte[] wrong=apk.clone();wrong[wrong.length/2]^=1;closed[0]=0;final int[] badClose=closed;fail(()->store.importDonorApk(owned(wrong,badClose),new ImportContract.Control()));need(closed[0]==1&&store.donorReady()&&Arrays.equals(before,Files.readAllBytes(member.toPath())),"failed donor replaced accepted data");
  ImportContract.Control cancelled=new ImportContract.Control();cancelled.cancel();closed[0]=0;final int[] cancelClose=closed;fail(()->store.importDonorApk(owned(apk,cancelClose),cancelled));need(closed[0]==1&&store.donorReady(),"cancel changed donor");
  closed[0]=0;store.importDonorApk(owned(apk,closed),new ImportContract.Control());need(closed[0]==1&&store.donorReady(),"repeat donor not reused");
  ImportContract.Control later=new ImportContract.Control();InputStream during=new ByteArrayInputStream(apk){@Override public synchronized int read(byte[] b,int o,int n){int r=super.read(b,o,n);later.cancel();return r;}};fail(()->store.importDonorApk(during,later));need(store.donorReady(),"during-copy cancellation changed donor");
  byte[] missing=zip("assets/runtime/other.bin",body);ImportStore absent=new ImportStore(context(new File(root,"absent"),missing,body),null);fail(()->absent.importDonorApk(new ByteArrayInputStream(missing),new ImportContract.Control()));need(!absent.donorReady(),"missing member published");
  Path outside=new File(root,"outside").toPath();Files.write(outside,bytes("outside"));Path link=new File(root,"output-link").toPath();Files.createSymbolicLink(link,outside);fail(()->ImportStore.copy(new ByteArrayInputStream(body),link,new ImportContract.Pin(body.length,ImportContract.hex(ImportContract.hash().digest(body))),new ImportContract.Control(),(p,d,t)->{},"fixture"));need(new String(Files.readAllBytes(outside),"UTF-8").equals("outside"),"link target changed");
  closed[0]=0;File profile=store.importProfileDump(owned(bytes("PGDMPfixture-data"),closed),new ImportContract.Control());need(closed[0]==1&&profile.equals(store.profileDump()),"logical profile not stored");byte[] saved=Files.readAllBytes(profile.toPath());
  fail(()->store.importProfileDump(new ByteArrayInputStream(bytes("not-a-logical-dump")),new ImportContract.Control()));need(Arrays.equals(saved,Files.readAllBytes(profile.toPath())),"bad logical dump overwrote profile");
  fail(()->store.importProfileDump(new ByteArrayInputStream(bytes("PGD")),new ImportContract.Control()));need(Arrays.equals(saved,Files.readAllBytes(profile.toPath())),"truncated header overwrote profile");
  fail(()->store.importProfileDump(new ByteArrayInputStream(bytes("PGDMPcancelled")),cancelled));need(Arrays.equals(saved,Files.readAllBytes(profile.toPath())),"cancelled dump overwrote profile");
  closed[0]=0;File base=store.importRuntimeArchive("base",owned(bytes("base"),closed),new ImportContract.Control());need(closed[0]==1&&base.isFile(),"runtime archive absent");
  fail(()->store.importRuntimeArchive("base",new ByteArrayInputStream(bytes("wrong")),new ImportContract.Control()));need(new String(Files.readAllBytes(base.toPath()),"UTF-8").equals("base"),"bad runtime replaced old input");
  fail(()->store.importRuntimeArchive("arbitrary",new ByteArrayInputStream(body),new ImportContract.Control()));
  fail(()->new ImportContract.Pin(-1,"0"));fail(()->ImportContract.safeLeaf("../escape"));fail(()->ImportContract.safeLeaf("/absolute"));fail(()->ImportContract.safeLeaf("a/b"));
  RuntimeSetup setup=new RuntimeSetup(c,store);need(!setup.ready(),"unconfigured runtime ready");fail(()->setup.setup(new ImportContract.Control(),null));need(!setup.ready(),"missing game assets activated runtime");
  boolean[] hook={false};ImportContract.Control hooked=new ImportContract.Control();hooked.whenCancelled(()->hook[0]=true);hooked.cancel();need(hook[0],"cancellation not propagated");
  byte[] baseArchive=Files.readAllBytes(new File(args[1],"base.tar.gz").toPath()),wineArchive=Files.readAllBytes(new File(args[1],"wine.tar.gz").toPath()),pgArchive=Files.readAllBytes(new File(args[1],"pg.tar.gz").toPath());
  ByteArrayOutputStream both=new ByteArrayOutputStream();try(ZipOutputStream z=new ZipOutputStream(both)){for(String name:new String[]{"test.bin","postgresql-runtime.tar.gz"}){z.putNextEntry(new ZipEntry("assets/runtime/"+name));z.write(name.equals("test.bin")?body:pgArchive);z.closeEntry();}}
  byte[] full=both.toByteArray();Context setupContext=context(new File(root,"setup"),full,body);
  JSONObject completeContract=new JSONObject().put("format",1).put("donor_apk",pin(full).put("name","COH-Atlas-Gameplay-0.13.36.apk")).put("donor_files",new JSONObject().put("assets/runtime/test.bin",pin(body)).put("assets/runtime/postgresql-runtime.tar.gz",pin(pgArchive))).put("bundled_files",new JSONObject());
  setupContext.assets.put("combined/import-contract.json",bytes(completeContract.toString()));setupContext.assets.put("runtime/runtime-manifest.json",bytes(new JSONObject().put("format",1).put("files",new JSONObject().put("test.bin",pin(body)).put("postgresql-runtime.tar.gz",pin(pgArchive))).toString()));
  JSONObject winePin=pin(wineArchive).put("manifest_sha256",ImportContract.hex(ImportContract.hash().digest(bytes("wine-manifest"))));
  setupContext.assets.put("runtime/runtime-lock.json",bytes(new JSONObject().put("base",pin(baseArchive)).put("wine",winePin).toString()));
  ImportStore setupImports=new ImportStore(setupContext,null);setupImports.importDonorApk(new ByteArrayInputStream(full),new ImportContract.Control());setupImports.importRuntimeArchive("base",new ByteArrayInputStream(baseArchive),new ImportContract.Control());setupImports.importRuntimeArchive("wine",new ByteArrayInputStream(wineArchive),new ImportContract.Control());
  io.github.russianranger.cohdiagnostic.AssetPackStore.accepted=true;io.github.russianranger.cohatlas.AtlasAssetImporter.fixtureData=new File(root,"fake-game/data");
  RuntimeSetup actual=new RuntimeSetup(setupContext,setupImports);File installed=actual.setup(new ImportContract.Control(),null);need(actual.ready(),"real small tar setup not activated");need(new File(installed,"rootfs/usr/bin/python3").isFile()&&new File(installed,"pg/opt/coh/pgsql/bin/postgres").isFile(),"runtime files not extracted");
  Object importedInode=Files.getAttribute(new File(setupImports.runtimePayloadDirectory(),"test.bin").toPath(),"unix:ino"),stagedInode=Files.getAttribute(new File(installed,"assets/test.bin").toPath(),"unix:ino");need(importedInode.equals(stagedInode),"runtime generation copied immutable asset bytes");
  need(actual.setup(new ImportContract.Control(),null).equals(installed),"repeat setup changed generation");fail(()->actual.setup(cancelled,null));need(actual.ready(),"cancelled repeat setup discarded ready generation");
  Files.delete(new File(installed,"assets/test.bin").toPath());Files.write(new File(installed,"assets/test.bin").toPath(),bytes("damaged"));fail(()->actual.setup(new ImportContract.Control(),null));need(actual.ready(),"failed verification removed previous receipt");need(Arrays.equals(body,Files.readAllBytes(new File(setupImports.runtimePayloadDirectory(),"test.bin").toPath())),"runtime damage changed immutable donor inode");
  System.out.println("combined import controls passed: "+checks);
 }
}
'''

CANONICAL_HOST=r'''
package org.coh.nativecombined;
import android.content.Context;import org.json.JSONObject;import java.io.*;import java.nio.file.*;
public final class CanonicalPathsHost {
 static int checks;static void need(boolean b,String m){checks++;if(!b)throw new AssertionError(m);}
 static byte[] bytes(String s)throws Exception{return s.getBytes("UTF-8");}
 static JSONObject pin(byte[] b){return new JSONObject().put("bytes",b.length).put("sha256",ImportContract.hex(ImportContract.hash().digest(b)));}
 public static void main(String[] args)throws Exception {
  Path root=Paths.get(args[0]),actual=root.resolve("actual"),alias=root.resolve("android-user-zero");Files.createDirectories(actual.resolve("files"));Files.createSymbolicLink(alias,actual);
  Context c=new Context(alias.resolve("files").toFile());
  JSONObject contract=new JSONObject().put("format",1).put("donor_apk",pin(bytes("APK")).put("name","COH-Atlas-Gameplay-0.13.36.apk"))
    .put("donor_files",new JSONObject().put("assets/runtime/test.bin",pin(bytes("payload")))).put("bundled_files",new JSONObject());
  c.assets.put("combined/import-contract.json",bytes(contract.toString()));c.assets.put("runtime/runtime-manifest.json",bytes(new JSONObject().put("format",1).put("files",new JSONObject()).toString()));
  c.assets.put("runtime/runtime-lock.json",bytes(new JSONObject().put("base",pin(bytes("base"))).put("wine",pin(bytes("wine"))).toString()));
  c.assets.put("atlas/atlas-import.properties",Files.readAllBytes(Paths.get(args[1])));
  ImportStore store=new ImportStore(c,null);String status=store.status();need(status.contains("import COH-Atlas-Gameplay-0.13.36.apk"),"fresh status failed to report missing donor");need(status.contains("Game files: import all four asset parts"),"fresh status failed to report missing assets");
  need(store.gameDataDirectory()==null,"fresh game import incorrectly ready");Path game=actual.resolve("files/combined-game-import");need(Files.isDirectory(game,LinkOption.NOFOLLOW_LINKS),"canonical private game store not created");
  ImportStore.remove(game);Path outside=root.resolve("outside");Files.createDirectory(outside);Path sentinel=outside.resolve("sentinel");Files.write(sentinel,bytes("preserve"));Files.createSymbolicLink(game,outside);
  boolean rejected=false;try{store.status();}catch(IOException expected){rejected=true;}need(rejected,"actual game directory symlink was followed");need(new String(Files.readAllBytes(sentinel),"UTF-8").equals("preserve"),"outside path modified");
  System.out.println("canonical Android private path controls passed: "+checks);
 }
}
'''

def main():
    root=Path(__file__).resolve().parents[2]
    repo=root.parents[1]
    source=root/'app/src/main/java/org/coh/nativecombined'
    with tempfile.TemporaryDirectory(prefix='coh-combined-import-') as tmp:
        temp=Path(tmp); files=[]
        for name,content in STUBS.items():
            path=temp/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content);files.append(path)
        host=temp/'org/coh/nativecombined/ImportsHost.java';host.parent.mkdir(parents=True,exist_ok=True);host.write_text(HOST);files.append(host)
        files += [source/name for name in ('ImportContract.java','ImportStore.java','RuntimeSetup.java')]
        files += [root/'imports/src/org/coh/nativecombined/RuntimeTarExtractor.java',root/'imports/src/org/coh/nativecombined/RuntimeMemoryGuard.java']
        classes=temp/'classes';classes.mkdir()
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(classes),*(str(f) for f in files)],check=True)
        fixtures=temp/'fixtures';fixtures.mkdir()
        for name,entries in {'base':{'usr/bin/python3':b'python-fixture'},'wine':{'bin/wine':b'wine-fixture','bin/wineserver':b'wineserver-fixture','lsb-fex.json':b'wine-manifest'},'pg':{'opt/coh/pgsql/bin/postgres':b'postgres-fixture','opt/coh/pgsql/bin/initdb':b'initdb-fixture'}}.items():
            with tarfile.open(fixtures/(name+'.tar.gz'),'w:gz',format=tarfile.USTAR_FORMAT) as archive:
                for path,data in entries.items():
                    item=tarfile.TarInfo(path);item.size=len(data);item.mode=0o755;archive.addfile(item,io.BytesIO(data))
        subprocess.run(['java','-cp',str(classes),'org.coh.nativecombined.ImportsHost',str(temp/'files'),str(fixtures)],check=True)
        # Compile a separate regression with the actual AtlasAssetImporter, not the
        # readiness adapter used by the synthetic runtime setup fixture above.
        canonical=temp/'canonical-classes';canonical.mkdir()
        canonical_host=temp/'org/coh/nativecombined/CanonicalPathsHost.java';canonical_host.write_text(CANONICAL_HOST)
        actual_importer=repo/'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java'
        canonical_files=[f for f in files if f.name not in ('ImportsHost.java','AtlasAssetImporter.java')]+[canonical_host,actual_importer]
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(canonical),*(str(f) for f in canonical_files)],check=True)
        properties={'format':'1','source.commit':'1'*40,'data.commit':'2'*40,'repository.commit':'3'*40,
            'asset.archive.sha256':'a'*64,'text.archive.sha256':'b'*64,'asset.manifest.sha256':'c'*64,'asset.index.sha256':'d'*64,'text.index.sha256':'e'*64,
            'asset.archive.bytes':'1','text.archive.bytes':'1','asset.manifest.bytes':'1','asset.index.bytes':'1','text.index.bytes':'1',
            'asset.count':'1','text.count':'1','total.count':'2','asset.bytes':'1','text.bytes':'1','total.bytes':'2',
            'storage.reserve.bytes':str(256*1024*1024),'storage.per.file.bytes':'4096'}
        atlas_properties=temp/'atlas-import.properties';atlas_properties.write_text(''.join(f'{k}={v}\n' for k,v in properties.items()).replace('\\n','\n'))
        subprocess.run(['java','-cp',str(canonical),'org.coh.nativecombined.CanonicalPathsHost',str(temp/'canonical-files'),str(atlas_properties)],check=True)
        original=(repo/'android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java').read_text()
        adapted=(root/'imports/src/org/coh/nativecombined/RuntimeTarExtractor.java').read_text()
        expected=original.replace('package io.github.russianranger.cohdiagnostic;','package org.coh.nativecombined;\n').replace('final class TarExtractor {','final class RuntimeTarExtractor {').replace('SetupMemoryGuard','RuntimeMemoryGuard')
        assert adapted==expected,'Accepted runtime extractor changed beyond package/class adapter'
        guard=(repo/'android/app/src/main/java/io/github/russianranger/cohdiagnostic/SetupMemoryGuard.java').read_text()
        copied=(root/'imports/src/org/coh/nativecombined/RuntimeMemoryGuard.java').read_text()
        assert copied==guard.replace('package io.github.russianranger.cohdiagnostic;','package org.coh.nativecombined;').replace('SetupMemoryGuard','RuntimeMemoryGuard')
        print('Accepted tar extractor and memory guard source identity: verified')
if __name__=='__main__':main()
