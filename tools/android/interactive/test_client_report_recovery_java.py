"""Exercise the actual Android-free diagnostic preservation/export implementation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java'
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;
public class ReportsHost {
 static Path root;
 static String id="1760111000000-0123456789ab";
 static byte[] png={(byte)137,80,78,71,13,10,26,10,0};
 interface Checked { void run() throws Exception; }
 static void need(boolean b){if(!b)throw new AssertionError();}
 static void fails(Checked c)throws Exception {try {c.run();throw new AssertionError("expected IOException");}catch(IOException expected){}}
 static Path run()throws Exception{return Files.createDirectories(root.resolve("client/reports/"+id));}
 static Path state()throws Exception{return Files.createDirectories(root.resolve("client/state"));}
 static Path completed(Path run)throws Exception {Path p=run.resolve("coh-character-reopen-"+run.getFileName()+".zip");Files.write(p,new byte[]{1,2,3});return p;}
 static String read(Path p)throws Exception{return new String(Files.readAllBytes(p),StandardCharsets.UTF_8);}
 static Map<String,byte[]> unzip(File f)throws Exception{
  Map<String,byte[]> result=new LinkedHashMap<>();
  try(ZipInputStream in=new ZipInputStream(new FileInputStream(f))){for(ZipEntry e;(e=in.getNextEntry())!=null;){ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[8192];for(int n;(n=in.read(b))!=-1;)out.write(b,0,n);result.put(e.getName(),out.toByteArray());}}
  return result;
 }
 static void checkpoint()throws Exception{
  Path run=run();ClientReports.checkpoint(run.toFile(),"{\"phase\":\"zoning\"}".getBytes(StandardCharsets.UTF_8));
  ClientReports.png(run.toFile(),"android-zoning/capture-1.png",png);
  need(read(run.resolve("checkpoint.json")).contains("zoning"));
  ClientReports.checkpoint(run.toFile(),"{\"phase\":\"save\"}".getBytes(StandardCharsets.UTF_8));need(read(run.resolve("checkpoint.json")).contains("save"));
  ClientReports.recoverAll(root.toFile());List<File> reports=ClientReports.reports(root.toFile(),8);need(reports.size()==1);
  Map<String,byte[]> zip=unzip(reports.get(0));need(zip.size()==3&&Arrays.equals(zip.get("android-zoning/capture-1.png"),png));
  String manifest=new String(zip.get("recovery-manifest.json"),StandardCharsets.UTF_8);need(manifest.contains("interrupted_unverified")&&manifest.contains("\"passed\":false")&&manifest.contains("\"verified\":false"));
  need(!zip.containsKey("android-client-report.json"));
  ClientReports.recoverAll(root.toFile());need(ClientReports.reports(root.toFile(),8).size()==1);
 }
 static void preserve()throws Exception{
  Path state=state();Files.write(state.resolve("latest-report.json"),"{\"passed\":true}".getBytes(StandardCharsets.UTF_8));Files.write(state.resolve("character-zoning-request.json"),new byte[]{4});Files.write(state.resolve("report.zip"),new byte[]{1,2,3});
  Files.write(state.resolve("secret-profile.json"),"password".getBytes(StandardCharsets.UTF_8));Files.createDirectories(state.resolve("database"));
  File report=ClientReports.preservePrevious(root.toFile());Map<String,byte[]> zip=unzip(report);
  need(zip.size()==4&&zip.containsKey("previous-guest/report.zip")&&!zip.containsKey("secret-profile.json"));
  need(Files.exists(state.resolve("report.zip"))&&read(state.resolve("latest-report.json")).contains("true"));
  need(ClientReports.reports(root.toFile(),8).contains(report));
  for(int n=0;n<10;n++){ClientReports.recoverAll(root.toFile());need(report.equals(ClientReports.preservePrevious(root.toFile())));}
  need(ClientReports.reports(root.toFile(),8).size()==1);
  // Same-size content changes with restored mtime still require new preservation.
  Path raw=state.resolve("report.zip");java.nio.file.attribute.FileTime oldTime=Files.getLastModifiedTime(raw);
  Files.write(raw,new byte[]{3,2,1});Files.setLastModifiedTime(raw,oldTime);
  File changed=ClientReports.preservePrevious(root.toFile());need(!changed.equals(report));
  need(Arrays.equals(unzip(changed).get("previous-guest/report.zip"),new byte[]{3,2,1}));
  need(changed.equals(ClientReports.preservePrevious(root.toFile())));
  // Corruption of the retained archive cannot satisfy the receipt, either.
  byte[] changedArchive=Files.readAllBytes(changed.toPath());java.nio.file.attribute.FileTime zipTime=Files.getLastModifiedTime(changed.toPath());
  changedArchive[0]^=1;Files.write(changed.toPath(),changedArchive);Files.setLastModifiedTime(changed.toPath(),zipTime);
  File repaired=ClientReports.preservePrevious(root.toFile());need(!repaired.equals(changed));
  need(Arrays.equals(unzip(repaired).get("previous-guest/report.zip"),new byte[]{3,2,1}));
 }
 static void empty()throws Exception{need(ClientReports.preservePrevious(root.toFile())==null);need(ClientReports.reports(root.toFile(),8).isEmpty());ClientReports.recoverAll(root.toFile());}
 static void inventory()throws Exception{
  Path a=run();Path b=Files.createDirectories(a.getParent().resolve("1760222000000-0123456789ab"));Path old=completed(a),recent=completed(b);
  Files.write(b.resolve("support.zip.part"),new byte[]{1});Files.write(b.resolve("unrelated.zip"),new byte[]{1});
  Files.write(root.resolve("client/latest-report.txt"),"/untrusted/location.zip".getBytes(StandardCharsets.UTF_8));
  List<File> reports=ClientReports.reports(root.toFile(),1);need(reports.size()==1&&reports.get(0).toPath().equals(recent));
  need(ClientReports.reports(root.toFile(),8).size()==2&&ClientReports.reports(root.toFile(),0).isEmpty());
  fails(()->ClientReports.reports(root.toFile(),51));
 }
 static void export()throws Exception{
  Path f=completed(run());ByteArrayOutputStream out=new ByteArrayOutputStream();need(ClientReports.export(root.toFile(),f.toFile(),out)==3);need(Arrays.equals(out.toByteArray(),new byte[]{1,2,3}));out.write(4);need(out.size()==4);
  fails(()->ClientReports.export(root.toFile(),root.resolve("other.zip").toFile(),out));
  Path outside=Files.createTempFile("coh-recovery-outside", ".zip");try{Files.write(outside,new byte[]{9});Files.delete(f);Files.createSymbolicLink(f,outside);fails(()->ClientReports.export(root.toFile(),f.toFile(),out));need(ClientReports.reports(root.toFile(),8).isEmpty());}finally{Files.deleteIfExists(outside);}
 }
 static void stream()throws Exception{
  Path f=completed(run());byte[] data=new byte[3*1024*1024];new Random(4).nextBytes(data);Files.write(f,data);
  final long[] count={0};OutputStream output=new OutputStream(){public void write(int b){count[0]++;}public void write(byte[] b,int o,int n){need(n<=65536);count[0]+=n;}public void close(){throw new AssertionError("caller owns stream");}};
  need(ClientReports.export(root.toFile(),f.toFile(),output)==data.length&&count[0]==data.length);
 }
 static void changed()throws Exception{
  Path f=completed(run());Files.write(f,new byte[131072]);final boolean[] once={false};
  OutputStream out=new OutputStream(){public void write(int b){}public void write(byte[] b,int o,int n)throws IOException {if(!once[0]){once[0]=true;Files.write(f,new byte[]{5});}}};
  fails(()->ClientReports.export(root.toFile(),f.toFile(),out));
 }
 static void links(String kind)throws Exception{
  Path state=state(),real=root.resolve("source");Files.write(real,new byte[]{1});Path dest=state.resolve("report.zip");
  if(kind.equals("symlink"))Files.createSymbolicLink(dest,real);else if(kind.equals("hardlink"))Files.createLink(dest,real);else if(kind.equals("directory"))Files.createDirectory(dest);else{new ProcessBuilder("mkfifo",dest.toString()).start().waitFor();}
  fails(()->ClientReports.preservePrevious(root.toFile()));need(Files.exists(dest,LinkOption.NOFOLLOW_LINKS));need(ClientReports.reports(root.toFile(),8).isEmpty());
 }
 static void ancestor()throws Exception{
  Path outside=Files.createTempDirectory("coh-recovery-outside");Files.createSymbolicLink(root.resolve("client"),outside);
  try{fails(()->ClientReports.reports(root.toFile(),8));fails(()->ClientReports.preservePrevious(root.toFile()));need(!Files.exists(outside.resolve("reports")));}finally{Files.deleteIfExists(outside);}
 }
 static void pngs()throws Exception{
  Path run=run();for(String invalid:new String[]{"../outside.png","android-zoning/../../outside.png","android-unknown/capture-1.png","android-zoning/capture-0.png","android-zoning/capture-257.png","android-zoning/accepted-capture-1.png"})fails(()->ClientReports.png(run.toFile(),invalid,png));
  fails(()->ClientReports.png(run.toFile(),"android-zoning/capture-1.png",new byte[]{1}));
  byte[] huge=new byte[4*1024*1024+1];System.arraycopy(png,0,huge,0,png.length);fails(()->ClientReports.png(run.toFile(),"android-zoning/capture-1.png",huge));
  ClientReports.png(run.toFile(),"android-task/accepted-capture-1.png",png);ClientReports.png(run.toFile(),"android-task/completed-capture-2.png",png);
  Path outside=Files.createTempDirectory("coh-recovery-outside");Files.createSymbolicLink(run.resolve("android-zoning"),outside);try{fails(()->ClientReports.png(run.toFile(),"android-zoning/capture-1.png",png));need(!Files.exists(outside.resolve("capture-1.png")));}finally{Files.delete(outside);}
 }
 static void bounds()throws Exception{
  Path run=run();ClientReports.checkpoint(run.toFile(),new byte[]{1});fails(()->ClientReports.checkpoint(run.toFile(),new byte[256*1024+1]));need(Files.size(run.resolve("checkpoint.json"))==1);
  Path state=state();try(RandomAccessFile f=new RandomAccessFile(state.resolve("report.zip").toFile(),"rw")){f.setLength(260L*1024*1024+1);}fails(()->ClientReports.preservePrevious(root.toFile()));
  Path report=completed(run);try(RandomAccessFile f=new RandomAccessFile(report.toFile(),"rw")){f.setLength(512L*1024*1024+1);}need(ClientReports.reports(root.toFile(),8).isEmpty());fails(()->ClientReports.export(root.toFile(),report.toFile(),new ByteArrayOutputStream()));
 }
 static void completed()throws Exception{
  Path run=run();ClientReports.checkpoint(run.toFile(),new byte[]{1});Path report=completed(run);ClientReports.recoverAll(root.toFile());List<File> list=ClientReports.reports(root.toFile(),8);need(list.size()==1&&list.get(0).toPath().equals(report));
 }
 static void captureLimit()throws Exception{
  Path run=run();for(int n=1;n<=128;n++)ClientReports.png(run.toFile(),"android-interaction/capture-"+n+".png",png);
  fails(()->ClientReports.png(run.toFile(),"android-interaction/capture-129.png",png));
  ClientReports.png(run.toFile(),"android-interaction/capture-1.png",png);
 }
 static void injected()throws Exception{
  Path report=completed(run());final String[] key={"identity-one"};
  ClientReports.IdentityReader reader=(file)->new ClientReports.FileIdentity(1,key[0]);
  ClientReports.setIdentityReader(reader);ClientReports.setIdentityReader(reader);
  ByteArrayOutputStream out=new ByteArrayOutputStream();need(ClientReports.export(root.toFile(),report.toFile(),out)==3);
  OutputStream changed=new OutputStream(){public void write(int b){}public void write(byte[] b,int o,int n){key[0]="identity-two";}};
  fails(()->ClientReports.export(root.toFile(),report.toFile(),changed));
 }
 static void badIdentity()throws Exception{
  Path report=completed(run());ClientReports.setIdentityReader((file)->new ClientReports.FileIdentity(2,"inode"));
  need(ClientReports.reports(root.toFile(),8).isEmpty());fails(()->ClientReports.export(root.toFile(),report.toFile(),new ByteArrayOutputStream()));
 }
 static void cancelled()throws Exception{
  Path report=completed(run());Thread.currentThread().interrupt();try{fails(()->ClientReports.export(root.toFile(),report.toFile(),new ByteArrayOutputStream()));}finally{Thread.interrupted();}need(Files.size(report)==3);
 }
 static void outputFailure()throws Exception{
  Path report=completed(run());OutputStream broken=new OutputStream(){public void write(int b)throws IOException{throw new IOException("provider closed");}};
  fails(()->ClientReports.export(root.toFile(),report.toFile(),broken));need(Files.size(report)==3);need(ClientReports.reports(root.toFile(),8).size()==1);
 }
 static void captureBytes()throws Exception{
  Path run=run(),dir=Files.createDirectories(run.resolve("android-zoning"));
  for(int n=1;n<=16;n++)try(RandomAccessFile f=new RandomAccessFile(dir.resolve("capture-"+n+".png").toFile(),"rw")){f.setLength(4*1024*1024);}
  fails(()->ClientReports.png(run.toFile(),"android-zoning/capture-17.png",png));need(!Files.exists(dir.resolve("capture-17.png")));
 }
 static void excessiveInventory()throws Exception{
  Path run=run();for(int n=0;n<2049;n++)Files.write(run.resolve("unrelated-"+n),new byte[0]);
  fails(()->ClientReports.reports(root.toFile(),8));
 }
 static void checkpointLink()throws Exception{
  Path run=run(),outside=root.resolve("outside.json");Files.write(outside,new byte[]{9});Files.createSymbolicLink(run.resolve("checkpoint.json"),outside);
  fails(()->ClientReports.checkpoint(run.toFile(),new byte[]{1}));fails(()->ClientReports.recoverAll(root.toFile()));need(Files.readAllBytes(outside)[0]==9);
 }
 public static void main(String[] a)throws Exception {
  root=Paths.get(a[1]);switch(a[0]){case "checkpoint":checkpoint();break;case "preserve":preserve();break;case "empty":empty();break;case "inventory":inventory();break;case "export":export();break;case "stream":stream();break;case "changed":changed();break;case "ancestor":ancestor();break;case "pngs":pngs();break;case "bounds":bounds();break;case "completed":completed();break;case "captureLimit":captureLimit();break;case "checkpointLink":checkpointLink();break;case "injected":injected();break;case "badIdentity":badIdentity();break;case "cancelled":cancelled();break;case "outputFailure":outputFailure();break;case "captureBytes":captureBytes();break;case "excessiveInventory":excessiveInventory();break;default:links(a[0]);}System.out.println("PASS");
 }
}
'''

class ClientReportRecoveryJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=tempfile.TemporaryDirectory(prefix='coh-recovery-java-')
        cls.addClassCleanup(cls.build.cleanup)
        host=Path(cls.build.name)/'ReportsHost.java'
        host.write_text(HARNESS)
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',cls.build.name,str(JAVA),str(host)],check=True,capture_output=True,text=True)

    def scenario(self, name):
        with tempfile.TemporaryDirectory(prefix='coh-report-case-') as case:
            result=subprocess.run(['java','-cp',self.build.name,'io.github.russianranger.cohclientinteractive.ReportsHost',name,case],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('PASS',result.stdout)

for _name in ('checkpoint','preserve','empty','inventory','export','stream','changed','symlink','hardlink','directory','fifo','ancestor','pngs','bounds','completed','captureLimit','checkpointLink','injected','badIdentity','cancelled','outputFailure','captureBytes','excessiveInventory'):
    setattr(ClientReportRecoveryJavaTests,'test_'+_name,lambda self,name=_name:self.scenario(name))

if __name__=='__main__':unittest.main()
