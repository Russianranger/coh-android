"""Exercise the shipped storage policy on the JVM, including hostile/stale plans."""
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/StorageAudit.java'
FIXTURE = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
public final class StorageAuditHost {
  static Map<String,Object> map(Object... values){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<values.length;i+=2)m.put((String)values[i],values[i+1]);return m;}
  static void need(boolean value){if(!value)throw new AssertionError();}
  static String parent(String path){int i=path.lastIndexOf('/');return i<0?"":path.substring(0,i);}
  static String hash(byte[] bytes){try{StringBuilder s=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(bytes))s.append(String.format("%02x",b&255));return s.toString();}catch(Exception e){throw new AssertionError(e);}}
  static class Entry {
    StorageAudit.Kind kind;long ino,links=1,size,blocks,modified=1,changed=1;byte[] bytes=new byte[0];String target;
    Entry(StorageAudit.Kind k,long ino,long size,long blocks){kind=k;this.ino=ino;this.size=size;this.blocks=blocks;if(k==StorageAudit.Kind.DIRECTORY)links=2;}
    StorageAudit.Stat stat(){return new StorageAudit.Stat(kind,5,ino,links,size,blocks,modified,changed);}
  }
  static class Fs implements StorageAudit.Fs {
    final TreeMap<String,Entry> files=new TreeMap<>();final Map<String,Map<String,Object>> json=new HashMap<>();
    final Map<String,Map<String,Object>> reports=new HashMap<>();long ino=100,time=1791040000000L;int removed=0;String failDelete,failStat,mutateOnList;List<String> aliases=Arrays.asList("/private","/android-alias/private");
    Fs(){dir("");dir("m2");dir("client");dir("client/state");dir("client-import");}
    void dir(String path){if(files.containsKey(path))return;if(!path.isEmpty())dir(parent(path));files.put(path,new Entry(StorageAudit.Kind.DIRECTORY,ino++,128,1));}
    Entry file(String path,long size,long blocks){dir(parent(path));Entry e=new Entry(StorageAudit.Kind.FILE,ino++,size,blocks);files.put(path,e);return e;}
    Entry bytes(String path,byte[] value){Entry e=file(path,value.length,1);e.bytes=value;return e;}
    void link(String path,String target){Entry e=file(path,target.length(),0);e.kind=StorageAudit.Kind.SYMLINK;e.target=target;}
    void hardlink(String source,String target){dir(parent(target));Entry e=files.get(source);e.links++;files.put(target,e);}
    String runtime(String version,boolean executable) {
      byte[] manifest=("{\"format\":1,\"files\":{\""+version+".zip\":{\"bytes\":100,\"sha256\":\""+"f".repeat(64)+"\"}}}").getBytes(StandardCharsets.UTF_8);
      String digest=hash(manifest),path="m2/runtime-"+digest.substring(0,16);dir(path);
      for(String member:Arrays.asList("assets","rootfs","wine","pg","dbserver"))dir(path+"/"+member);
      bytes(path+"/assets/runtime-manifest.json",manifest);file(path+"/assets/"+version+".zip",100,1);
      json.put(new String(manifest,StandardCharsets.UTF_8),map("format",1,"files",map(version+".zip",map("bytes",100,"sha256","f".repeat(64)))));
      byte[] ready=("ready:"+digest).getBytes(StandardCharsets.UTF_8);bytes(path+"/ready.json",ready);json.put(new String(ready,StandardCharsets.UTF_8),map("manifest_sha256",digest));
      if(executable)for(String name:Arrays.asList("rootfs/usr/bin/python3","rootfs/usr/bin/Xtigervnc","wine/bin/wine","wine/bin/wineserver","pg/opt/coh/pgsql/bin/postgres","pg/opt/coh/pgsql/bin/initdb"))file(path+"/"+name,4000,2);
      return path;
    }
    String report(int number) {
      String run=String.format("17910300000%02d-0123456789ab",number),dir="client/reports/"+run;dir(dir);
      String archive=dir+"/coh-character-reopen-"+run+".zip";file(archive,20000,4);
      reports.put(archive,map("format",1,"run_id",run,"status","passed"));return dir;
    }
    @Override public StorageAudit.Stat stat(String path)throws IOException{if(path.equals(failStat))throw new IOException("stat denied");Entry e=files.get(path);return e==null?null:e.stat();}
    @Override public String rootPath(){return "/private";}
    @Override public List<String> rootAliases(){return aliases;}
    @Override public String readLink(String path)throws IOException{Entry e=files.get(path);if(e==null||e.kind!=StorageAudit.Kind.SYMLINK)throw new IOException("not a link");return e.target;}
    @Override public List<String> list(String path)throws IOException {
      Entry e=files.get(path);if(e==null||e.kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("not a directory");
      List<String> result=new ArrayList<>();for(String name:files.keySet())if(!name.isEmpty()&&parent(name).equals(path))result.add(name.substring(path.isEmpty()?0:path.length()+1));
      if(path.equals(mutateOnList)){mutateOnList=null;file(path+"/new",12,1);e.modified++;}return result;
    }
    @Override public byte[] read(String path,int limit)throws IOException{Entry e=files.get(path);if(e==null||e.kind!=StorageAudit.Kind.FILE||e.bytes.length>limit)throw new IOException("read denied");return e.bytes.clone();}
    @Override public Map<String,Object> json(byte[] bytes)throws IOException{Map<String,Object> m=json.get(new String(bytes,StandardCharsets.UTF_8));if(m==null)throw new IOException("invalid JSON");return m;}
    @Override public Map<String,Object> reportIdentity(String path,int limit)throws IOException{Map<String,Object> m=reports.get(path);if(m==null)throw new IOException("invalid ZIP");return m;}
    void delete(String path)throws IOException {
      if(path.equals(failDelete))throw new IOException("delete denied");Entry e=files.remove(path);if(e==null)throw new IOException("missing");removed++;
      if(e.kind!=StorageAudit.Kind.DIRECTORY){e.links--;e.changed++;}
      Entry p=files.get(parent(path));if(p!=null)p.modified++;
    }
    @Override public void unlink(String path)throws IOException{if(files.get(path).kind==StorageAudit.Kind.DIRECTORY)throw new IOException("directory");delete(path);}
    @Override public void rmdir(String path)throws IOException{for(String name:files.keySet())if(!name.equals(path)&&parent(name).equals(path))throw new IOException("not empty");delete(path);}
    @Override public long nowMillis(){return time;}
  }
  static class Fixture {
    Fs fs=new Fs();String current=fs.runtime("current",true),old=fs.runtime("old",false);
    String digest=new String(fs.files.get(current+"/ready.json").bytes,StandardCharsets.UTF_8).substring(6);
    StorageAudit.Plan scan(){return StorageAudit.scan(fs,digest,StorageAudit.Limits.defaults());}
    StorageAudit.CleanupResult clean(StorageAudit.Plan p,String... ids){return StorageAudit.cleanup(fs,p,new HashSet<>(Arrays.asList(ids)),StorageAudit.Limits.defaults());}
  }
  static StorageAudit.Category category(StorageAudit.Plan p,String id){for(StorageAudit.Category c:p.categories)if(c.id.equals(id))return c;throw new AssertionError();}
  static StorageAudit.Candidate candidate(StorageAudit.Plan p,String path){for(StorageAudit.Candidate c:p.candidates)if(c.path.equals(path))return c;return null;}
  public static void main(String[] args)throws Exception {
    Fixture f=new Fixture();
    switch(args[0]) {
    case "classify": {
      f.fs.file("client/state/server-profile/database.dat",1000000000L,2000);f.fs.file("client-import/inactive/data/maps/x",2000000000L,3000);
      StorageAudit.Plan p=f.scan();need(p.complete&&p.currentRuntimeVerified&&p.cleanupAllowed);need(candidate(p,f.old)!=null);need(candidate(p,f.current)==null);
      need(category(p,"client_state").apparentBytes>=1000000000L);need(category(p,"client_import").apparentBytes>=2000000000L);need(!category(p,"client_state").removable);break;
    }
    case "read_only":{int count=f.fs.files.size();f.scan();need(f.fs.files.size()==count&&f.fs.removed==0);break;}
    case "allocated":{f.fs.file(f.old+"/rootfs/sparse",10000000000L,2);StorageAudit.Plan p=f.scan();need(p.apparentBytes>10000000000L&&p.allocatedBytes<100000);need(candidate(p,f.old).reclaimableBytes<10000);break;}
    case "hardlink_dedup":{f.fs.file(f.old+"/rootfs/a",6000,12);f.fs.hardlink(f.old+"/rootfs/a",f.old+"/rootfs/b");StorageAudit.Plan p=f.scan();need(candidate(p,f.old).apparentBytes>12000);long expected=candidate(p,f.old).reclaimableBytes;StorageAudit.CleanupResult r=f.clean(p,"old_runtime");need(r.completed&&r.reclaimedBytes==expected&&!f.fs.files.containsKey(f.old));break;}
    case "hardlink_protected":{long baseline=candidate(f.scan(),f.old).reclaimableBytes;Entry a=f.fs.file(f.old+"/rootfs/a",6000,12);f.fs.hardlink(f.old+"/rootfs/a","client/state/keep");StorageAudit.Plan p=f.scan();need(candidate(p,f.old).reclaimableBytes==baseline);StorageAudit.CleanupResult r=f.clean(p,"old_runtime");need(r.completed&&f.fs.files.containsKey("client/state/keep")&&f.fs.files.get("client/state/keep").links==1);break;}
    case "hardlink_external":{Entry a=f.fs.file(f.old+"/rootfs/a",6000,12);a.links=2;StorageAudit.Plan p=f.scan();need(candidate(p,f.old).reclaimableBytes<candidate(p,f.old).allocatedBytes);StorageAudit.CleanupResult r=f.clean(p,"old_runtime");need(r.completed&&r.reclaimedBytes==candidate(p,f.old).reclaimableBytes);break;}
    case "download_names":{for(String prefix:Arrays.asList("base","wine","database environment","Windows runtime"))for(String suffix:Arrays.asList(".tar.gz",".tar.gz.part"))f.fs.file("m2/downloads/"+prefix+"-"+"a".repeat(64)+suffix,1000,2);f.fs.file("m2/downloads/user-backup.zip",1000,2);StorageAudit.Plan p=f.scan();need(category(p,"downloads").candidateCount==8);StorageAudit.CleanupResult r=f.clean(p,"downloads");need(r.completed&&f.fs.files.containsKey("m2/downloads/user-backup.zip")&&f.fs.files.containsKey(f.old));break;}
    case "current_missing":{f.fs.files.remove(f.current+"/ready.json");StorageAudit.Plan p=f.scan();need(p.complete&&!p.currentRuntimeVerified&&!p.cleanupAllowed);need(f.clean(p,"old_runtime").deletedCount==0);break;}
    case "current_payload_missing":{f.fs.files.remove(f.current+"/assets/current.zip");need(!f.scan().cleanupAllowed);break;}
    case "current_payload_size":{f.fs.files.get(f.current+"/assets/current.zip").size++;need(!f.scan().cleanupAllowed);break;}
    case "current_symlink_executable":{f.fs.file(f.current+"/rootfs/usr/bin/python3.12",4000,2);f.fs.link(f.current+"/rootfs/usr/bin/python3","python3.12");need(f.scan().currentRuntimeVerified);f.fs.link(f.current+"/rootfs/usr/bin/python3","/outside/python");need(!f.scan().cleanupAllowed);break;}
    case "old_bad_identity":{f.fs.bytes(f.old+"/assets/runtime-manifest.json","tampered".getBytes(StandardCharsets.UTF_8));StorageAudit.Plan p=f.scan();need(p.complete&&p.cleanupAllowed&&candidate(p,f.old)==null);break;}
    case "old_extra_root":{f.fs.dir(f.old+"/unrecognized-user-data");need(candidate(f.scan(),f.old)==null);break;}
    case "staging_protected":{f.fs.file(f.old+".staging/assets/anything",100000,100);need(candidate(f.scan(),f.old+".staging")==null);break;}
    case "reports_retention":{List<String> dirs=new ArrayList<>();for(int i=1;i<=6;i++)dirs.add(f.fs.report(i));String kept=dirs.get(0);String archive=f.fs.reports.keySet().stream().filter(p->p.startsWith(kept+"/")).findFirst().get();f.fs.bytes("client/latest-report.txt",("/private/"+archive).getBytes(StandardCharsets.UTF_8));StorageAudit.Plan p=f.scan();need(category(p,"old_reports").candidateCount==2);need(candidate(p,dirs.get(0))==null&&candidate(p,dirs.get(3))==null);StorageAudit.CleanupResult r=f.clean(p,"old_reports");need(r.completed&&f.fs.files.containsKey(archive)&&f.fs.files.containsKey(dirs.get(5)));break;}
    case "reports_incomplete":{for(int i=1;i<=5;i++)f.fs.report(i);String path=f.fs.report(1);f.fs.file(path+"/support.zip.part",2000,4);need(candidate(f.scan(),path)==null);break;}
    case "pointer_invalid":{f.fs.bytes("client/latest-report.txt","/shared/user.zip".getBytes(StandardCharsets.UTF_8));need(!f.scan().cleanupAllowed);break;}
    case "symlink_unlink_only":{f.fs.link(f.old+"/rootfs/shared","/outside/private-data");StorageAudit.Plan p=f.scan();need(p.complete&&p.cleanupAllowed);need(f.clean(p,"old_runtime").completed);break;}
    case "protected_relative_reference":{f.fs.link("client/state/wine/dosdevices/runtime","../../../../"+f.old+"/wine");StorageAudit.Plan p=f.scan();need(p.complete&&candidate(p,f.old)==null);need(f.clean(p,"old_runtime").completed&&f.fs.files.containsKey(f.old));break;}
    case "protected_absolute_reference":{f.fs.link("client/state/cache","/private/"+f.old+"/assets");need(candidate(f.scan(),f.old)==null);break;}
    case "protected_alias_reference":{f.fs.link("client/state/cache","/android-alias/private/"+f.old+"/assets");need(candidate(f.scan(),f.old)==null);break;}
    case "symlink_same_stat_mutation":{String path=f.old+"/wine/link";f.fs.link(path,"/outside/first");StorageAudit.Plan p=f.scan();f.fs.files.get(path).target="/outside/other";StorageAudit.CleanupResult r=f.clean(p,"old_runtime");need(r.stalePlan&&r.deletedCount==0);break;}
    case "link_read_failure":{f.fs.link(f.old+"/wine/link","/outside/first");f.fs.files.get(f.old+"/wine/link").target=null;StorageAudit.Plan p=f.scan();need(!p.complete&&!p.cleanupAllowed);break;}
    case "cancelled_scan":{Thread.currentThread().interrupt();StorageAudit.Plan p=f.scan();Thread.interrupted();need(!p.complete&&!p.cleanupAllowed);break;}
    case "cross_candidate_reference":{String second=f.fs.runtime("older",false);f.fs.link(f.old+"/wine/keep","/private/"+second+"/wine");StorageAudit.Plan p=f.scan();need(candidate(p,f.old)!=null&&candidate(p,second)==null);break;}
    case "scan_error":{f.fs.failStat="client/state";StorageAudit.Plan p=f.scan();need(!p.complete&&!p.cleanupAllowed&&p.reclaimableBytes==0);need(f.clean(p,"old_runtime").deletedCount==0);break;}
    case "entry_limit":{StorageAudit.Plan p=StorageAudit.scan(f.fs,f.digest,new StorageAudit.Limits(5,128,600000));need(!p.complete&&!p.cleanupAllowed&&p.entryCount<=5);break;}
    case "changed_during_scan":{f.fs.mutateOnList=f.old+"/rootfs";need(!f.scan().cleanupAllowed);break;}
    case "stale_file":{StorageAudit.Plan p=f.scan();f.fs.files.get(f.old+"/assets/old.zip").modified++;StorageAudit.CleanupResult r=f.clean(p,"old_runtime");need(r.stalePlan&&r.deletedCount==0&&f.fs.files.containsKey(f.old));break;}
    case "stale_pointer":{for(int i=1;i<=5;i++)f.fs.report(i);StorageAudit.Plan p=f.scan();String archive=f.fs.reports.keySet().iterator().next();f.fs.bytes("client/latest-report.txt",("/private/"+archive).getBytes(StandardCharsets.UTF_8));need(f.clean(p,"old_runtime").stalePlan);break;}
    case "new_reference_after_scan":{StorageAudit.Plan p=f.scan();f.fs.link("client/state/new-reference","/private/"+f.old);need(f.clean(p,"old_runtime").deletedCount==0);break;}
    case "protected_selection":{StorageAudit.Plan p=f.scan();StorageAudit.CleanupResult r=f.clean(p,"client_state");need(!r.completed&&r.deletedCount==0&&!r.errors.isEmpty());break;}
    case "partial_failure":{StorageAudit.Plan p=f.scan();f.fs.failDelete=f.old+"/assets/old.zip";StorageAudit.CleanupResult r=f.clean(p,"old_runtime");need(!r.completed&&r.skippedCount==1&&!r.errors.isEmpty()&&f.fs.files.containsKey(f.old));need(r.reclaimedBytes<=candidate(p,f.old).reclaimableBytes);break;}
    case "protected_socket":{Entry e=f.fs.file("client/state/unused.sock",0,0);e.kind=StorageAudit.Kind.OTHER;StorageAudit.Plan p=f.scan();need(p.complete&&p.cleanupAllowed);e=f.fs.file(f.old+"/rootfs/socket",0,0);e.kind=StorageAudit.Kind.OTHER;need(candidate(f.scan(),f.old)==null);break;}
    case "report_json_bounded":{for(int i=0;i<300;i++)f.fs.file("m2/downloads/base-"+String.format("%064x",i)+".tar.gz",100,1);StorageAudit.Plan p=f.scan();String json=p.toJson();need(json.startsWith("{")&&json.contains("\"candidate_details_truncated\":true")&&json.length()<150000);break;}
    case "large_tree":{for(int i=0;i<15000;i++)f.fs.file(f.old+"/rootfs/files/f"+i,100,1);StorageAudit.Plan p=f.scan();need(p.complete&&p.entryCount>15000);StorageAudit.CleanupResult r=f.clean(p,"old_runtime");need(r.completed&&r.deletedCount>15000);break;}
    default:throw new AssertionError(args[0]);
    }
  }
}
'''


class StorageAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        host = cls.root / 'StorageAuditHost.java'
        host.write_text(FIXTURE)
        compiler = [shutil.which('javac')] if shutil.which('javac') else ['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main']
        subprocess.run(compiler + ['-encoding', 'UTF-8', '-d', str(cls.root), str(SOURCE), str(host)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def scenario(self, name):
        result = subprocess.run(['java', '-Xmx128m', '-cp', str(self.root), 'io.github.russianranger.cohclientinteractive.StorageAuditHost', name], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


SCENARIOS = [
    'classify', 'read_only', 'allocated', 'hardlink_dedup', 'hardlink_protected',
    'hardlink_external', 'download_names', 'current_missing', 'current_payload_missing',
    'current_payload_size', 'current_symlink_executable', 'old_bad_identity', 'old_extra_root',
    'staging_protected', 'reports_retention', 'reports_incomplete', 'pointer_invalid',
    'symlink_unlink_only', 'protected_relative_reference', 'protected_absolute_reference',
    'protected_alias_reference', 'symlink_same_stat_mutation', 'link_read_failure', 'cancelled_scan',
    'cross_candidate_reference', 'scan_error', 'entry_limit', 'changed_during_scan',
    'stale_file', 'stale_pointer', 'new_reference_after_scan', 'protected_selection',
    'partial_failure', 'protected_socket', 'report_json_bounded', 'large_tree',
]
for _scenario in SCENARIOS:
    setattr(StorageAuditTests, 'test_' + _scenario, lambda self, name=_scenario: self.scenario(name))

if __name__ == '__main__':
    unittest.main()
