"""Execute the shipped Java volume importer against real files, ZIP metadata and inode sharing."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'android/app/src/main/java/io/github/russianranger/cohdiagnostic/AssetPackArchive.java'
GUARD_SOURCE = SOURCE.with_name('SetupMemoryGuard.java')
CLASS = 'io.github.russianranger.cohdiagnostic.AssetPackHost'
HOST = r'''
package io.github.russianranger.cohdiagnostic;
import java.io.*;
import java.nio.file.*;
import java.util.*;
public final class AssetPackHost {
    static void need(boolean value,String message){if(!value)throw new AssertionError(message);}
    public static void main(String[] args)throws Exception {
        File root=new File(args[0]);String mode=args[1];
        Map<String,AssetPackArchive.Pin> pins=new TreeMap<>();Map<String,Set<String>> volumes=new TreeMap<>();
        for(String row:Files.readAllLines(new File(root,"pins.tsv").toPath())) {
            String[] fields=row.split("\\t");pins.put(fields[0],new AssetPackArchive.Pin(Long.parseLong(fields[1]),fields[2]));
            volumes.computeIfAbsent(fields[3],key->new TreeSet<>()).add(fields[0]);
        }
        final long[] read={0},written={0};final int[] checks={0};final boolean[] raced={false};
        AssetPackArchive.Check check=()->{if(mode.equals("cancel")&&++checks[0]>12)throw new InterruptedIOException("cancelled fixture");};
        AssetPackArchive.Io io=new AssetPackArchive.Io(){
            public void before(){}public void read(long n){need(n<=65536,"unbounded read");read[0]+=n;}
            public void written(long n,AssetPackArchive.Sync sync)throws IOException{
                need(n<=65536,"unbounded write");written[0]+=n;sync.sync();
                if(mode.startsWith("race_")&&!raced[0]&&written[0]>new File(root,args[2]).length()) {
                    Path object=new File(root,"store/objects/"+pins.get("atlas/atlas-assets.zip").sha256).toPath();
                    Path replacement=new File(root,"racing-object").toPath();
                    if(mode.equals("race_link"))Files.createSymbolicLink(replacement,new File(root,"outside").toPath());
                    else Files.write(replacement,"racing replacement".getBytes("US-ASCII"));
                    Files.move(replacement,object,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);raced[0]=true;
                }
            }public void synced(){}
        };
        AssetPackArchive pack=new AssetPackArchive(new File(root,"store"),Files.readAllBytes(new File(root,"manifest.json").toPath()),pins,volumes,check,io,(phase,done,total)->{},file->mode.equals("space")?0:100L<<30);
        if(mode.equals("resolve")){System.out.println(pack.resolve("runtime/a.zip"));return;}
        if(mode.equals("missing")){System.out.println(String.join(",",pack.missingVolumes()));return;}
        for(int i=2;i<args.length;i++) {
            boolean acceptedBefore=pack.isAccepted();
            final boolean[] closed={false};final String[] when={null};
            InputStream input=new FilterInputStream(new FileInputStream(new File(root,args[i]))){
                @Override public void close()throws IOException{need(!closed[0],"provider closed twice");closed[0]=true;when[0]=Boolean.toString(pack.isAccepted());super.close();}
            };
            if(mode.startsWith("admission_")) {
                final long[] clock={0};
                SetupMemoryGuard guard=new SetupMemoryGuard(
                    ()->new SetupMemoryGuard.Sample(0,16L<<30,0,true,0,32L<<20),
                    ()->clock[0],millis->clock[0]+=millis,
                    ()->{if(mode.equals("admission_cancel"))throw new InterruptedIOException("cancelled before import");});
                try{pack.importVolume(input,guard::admit);throw new AssertionError("admission unexpectedly succeeded");}
                catch(IOException expected){
                    need(closed[0],"provider leaked when memory admission failed");
                    need("false".equals(when[0])&&!pack.isAccepted(),"admission failure published assets");
                    need(read[0]==0&&written[0]==0,"admission failure performed payload I/O");
                    System.out.println("admission_closed="+guard.receipt().get("status"));return;
                }
            }
            String volume=pack.importVolume(input);need(closed[0],"provider retained");
            if(i==2)need(Boolean.toString(acceptedBefore).equals(when[0]),"published before provider was closed");
            System.out.println("part="+volume+" accepted="+pack.isAccepted()+" missing="+String.join(",",pack.missingVolumes()));
        }
        if(mode.equals("share")) {
            need(pack.isAccepted(),"full pack absent");File source=pack.resolve("runtime/a.zip");Object inode=Files.getAttribute(source.toPath(),"unix:ino");
            for(int i=0;i<5;i++){Path target=new File(root,"runtime-"+i).toPath();Files.createLink(target,source.toPath());need(inode.equals(Files.getAttribute(target,"unix:ino")),"asset bytes duplicated");}
            need(((Number)Files.getAttribute(source.toPath(),"unix:nlink")).longValue()==6,"hardlinks missing");
        }
        System.out.println("io="+read[0]+","+written[0]);
    }
}
'''


class AssetPackImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiled=tempfile.TemporaryDirectory(prefix='coh-pack-classes-'); cls.classes=Path(cls.compiled.name)
        host=cls.classes/'AssetPackHost.java';host.write_text(HOST)
        result=subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(cls.classes),str(host),str(SOURCE),str(GUARD_SOURCE)],capture_output=True,text=True)
        if result.returncode:raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls):cls.compiled.cleanup()

    def setUp(self):
        self.work=tempfile.TemporaryDirectory(prefix='coh-pack-fixture-');self.root=Path(self.work.name)
        self.payloads={'runtime/a.zip':b'old retained asset\n'*5000,'atlas/atlas-assets.zip':b'atlas archive','runtime/zones.zip':b'zones assets'}
        self.volumes={'base':['runtime/a.zip','atlas/atlas-assets.zip'],'zones':['runtime/zones.zip']}
        self.make_contract()
        self.archive('base.zip','base');self.archive('zones.zip','zones')

    def tearDown(self):self.work.cleanup()

    def make_contract(self):
        manifest={'format':1,'id':'coh-assets','version':'1.0.0','files':{key:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for key,raw in self.payloads.items()},'volumes':self.volumes}
        self.raw=json.dumps(manifest,sort_keys=True).encode();(self.root/'manifest.json').write_bytes(self.raw)
        (self.root/'pins.tsv').write_text(''.join(f'{name}\t{len(self.payloads[name])}\t{hashlib.sha256(self.payloads[name]).hexdigest()}\t{volume}\n' for volume,names in self.volumes.items() for name in names))

    def archive(self,filename,volume,*,corrupt=False,symlink=False,extra=None,manifest=None,duplicate=False):
        with zipfile.ZipFile(self.root/filename,'w',compression=zipfile.ZIP_STORED) as out:
            rows=[('asset-pack-manifest.json',self.raw if manifest is None else manifest)]+[('payloads/'+name,self.payloads[name]) for name in sorted(self.volumes[volume])]
            if corrupt:rows[-1]=(rows[-1][0],b'x'*len(rows[-1][1]))
            if extra:rows.append(extra)
            if duplicate:rows.append(rows[-1])
            for i,(name,raw) in enumerate(rows):
                info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=((0o120777 if symlink and i==1 else 0o100644)<<16)
                out.writestr(info,raw)

    def run_host(self,mode,*archives,okay=True):
        result=subprocess.run(['java','-Xmx32m','-cp',str(self.classes),CLASS,str(self.root),mode,*archives],capture_output=True,text=True,timeout=30)
        self.assertEqual(0 if okay else 1,result.returncode,result.stdout+result.stderr)
        return result

    def test_multipart_only_activates_complete_exact_version_and_shares_inodes(self):
        result=self.run_host('share','base.zip','zones.zip')
        self.assertIn('part=base accepted=false missing=zones',result.stdout)
        self.assertIn('part=zones accepted=true missing=',result.stdout)
        self.assertEqual(1,len(list((self.root/'store/accepted').glob('*.json'))))

    def test_reverse_part_order_is_supported(self):
        result=self.run_host('plain','zones.zip','base.zip');self.assertIn('part=zones accepted=false missing=base',result.stdout)

    def test_identical_payloads_have_one_content_object(self):
        self.payloads['runtime/copy.zip']=self.payloads['runtime/a.zip'];self.volumes['base'].append('runtime/copy.zip')
        self.make_contract();self.archive('base.zip','base');self.archive('zones.zip','zones')
        self.run_host('plain','base.zip','zones.zip')
        self.assertEqual(3,len(list((self.root/'store/objects').iterdir())))

    def test_missing_pack_cannot_supply_runtime_payload(self):
        self.run_host('plain','base.zip');result=self.run_host('resolve',okay=False)
        self.assertIn('Import all required asset pack parts',result.stderr)

    def test_corrupt_part_preserves_verified_previous_part_and_cannot_activate(self):
        self.run_host('plain','base.zip');before={p.name:p.read_bytes() for p in (self.root/'store/objects').iterdir()}
        self.archive('bad.zip','zones',corrupt=True);self.run_host('plain','bad.zip',okay=False)
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'store/objects').iterdir()})
        self.assertEqual([],list((self.root/'store/accepted').iterdir()))
        self.run_host('plain','zones.zip')

    def test_bad_update_preserves_accepted_old_pack(self):
        self.run_host('plain','base.zip','zones.zip');old={p.name:p.read_bytes() for p in (self.root/'store/accepted').iterdir()}
        self.payloads['runtime/zones.zip']=b'new zones';self.make_contract();self.archive('bad.zip','zones',corrupt=True)
        self.run_host('plain','bad.zip',okay=False)
        self.assertEqual(old,{p.name:p.read_bytes() for p in (self.root/'store/accepted').iterdir()})

    def test_rejects_symlink_members_unknown_paths_duplicates_and_truncated_central(self):
        for name,kwargs in [('link',{'symlink':True}),('escape',{'extra':('../escape',b'bad')}),('duplicate',{'duplicate':True})]:
            with self.subTest(name=name):self.archive(name+'.zip','base',**kwargs);self.run_host('plain',name+'.zip',okay=False)
        (self.root/'short.zip').write_bytes((self.root/'base.zip').read_bytes()[:-10]);self.run_host('plain','short.zip',okay=False)
        self.assertFalse((self.root.parent/'escape').exists())

    def test_rejects_wrong_manifest_and_central_local_name_mismatch(self):
        self.archive('wrong.zip','base',manifest=b'x'*len(self.raw));self.run_host('plain','wrong.zip',okay=False)
        raw=bytearray((self.root/'base.zip').read_bytes());raw[30]=ord('z');(self.root/'wrong-local.zip').write_bytes(raw)
        self.run_host('plain','wrong-local.zip',okay=False)

    def test_insufficient_space_and_cancel_never_activate_or_leave_partial_stage(self):
        for mode in ('space','cancel'):
            with self.subTest(mode=mode):self.run_host(mode,'base.zip',okay=False);self.assertFalse(list((self.root/'store').glob('.import-*')))
        self.assertFalse(list((self.root/'store/accepted').iterdir()))

    def test_memory_admission_failure_or_cancellation_closes_provider_exactly_once(self):
        for mode,status in [('admission_pressure','memory_pressure_stopped'),('admission_cancel','cancelled')]:
            with self.subTest(mode=mode):
                result=self.run_host(mode,'base.zip')
                self.assertIn('admission_closed='+status,result.stdout)
                self.assertFalse(list((self.root/'store').glob('.import-*')))
                self.assertFalse(list((self.root/'store/accepted').iterdir()))

    def test_unsafe_store_link_is_rejected_without_touching_target(self):
        target=self.root/'outside';target.mkdir();(self.root/'store').symlink_to(target,target_is_directory=True)
        self.run_host('plain','base.zip',okay=False);self.assertFalse(list(target.iterdir()))

    def test_restart_reuses_verified_parts_without_new_objects(self):
        self.run_host('plain','base.zip');before={p.name:p.stat().st_ino for p in (self.root/'store/objects').iterdir()}
        self.run_host('plain','base.zip')
        self.assertEqual(before,{p.name:p.stat().st_ino for p in (self.root/'store/objects').iterdir()})
        result=self.run_host('plain','zones.zip');self.assertIn('accepted=true',result.stdout)

    def test_reimport_repairs_corrupt_object_without_modifying_existing_runtime_hardlink(self):
        self.run_host('plain','base.zip','zones.zip')
        original=self.payloads['runtime/a.zip'];digest=hashlib.sha256(original).hexdigest()
        shared=self.root/'store/objects'/digest;retained=self.root/'old-runtime-archive.zip'
        shared.chmod(0o600);damaged=b'x'*len(original);shared.write_bytes(damaged);os.link(shared,retained)
        previous_inode=shared.stat().st_ino;receipts={p.name:p.read_bytes() for p in (self.root/'store/accepted').iterdir()}
        self.run_host('plain','base.zip')
        self.assertEqual(original,shared.read_bytes());self.assertNotEqual(previous_inode,shared.stat().st_ino)
        self.assertEqual(damaged,retained.read_bytes());self.assertEqual(previous_inode,retained.stat().st_ino)
        self.assertEqual(receipts,{p.name:p.read_bytes() for p in (self.root/'store/accepted').iterdir()})
        self.run_host('resolve')

    def test_corrupt_object_with_multiple_names_is_repaired_once(self):
        self.payloads['runtime/copy.zip']=self.payloads['runtime/a.zip'];self.volumes['base'].append('runtime/copy.zip')
        self.make_contract();self.archive('base.zip','base');self.archive('zones.zip','zones')
        self.run_host('plain','base.zip','zones.zip')
        original=self.payloads['runtime/a.zip'];shared=self.root/'store/objects'/hashlib.sha256(original).hexdigest()
        shared.chmod(0o600);shared.write_bytes(b'wrong length')
        self.run_host('plain','base.zip');self.assertEqual(original,shared.read_bytes())

    def test_repair_refuses_existing_symlink_or_directory_objects(self):
        self.run_host('plain','base.zip')
        shared=self.root/'store/objects'/hashlib.sha256(self.payloads['runtime/a.zip']).hexdigest()
        shared.unlink();outside=self.root/'outside';outside.write_bytes(b'protected external bytes')
        shared.symlink_to(outside)
        self.run_host('plain','base.zip',okay=False);self.assertTrue(shared.is_symlink());self.assertEqual(b'protected external bytes',outside.read_bytes())
        shared.unlink();shared.mkdir()
        self.run_host('plain','base.zip',okay=False);self.assertTrue(shared.is_dir())

    def test_repair_refuses_object_replacement_or_symlink_race(self):
        self.run_host('plain','base.zip')
        original=self.payloads['atlas/atlas-assets.zip'];shared=self.root/'store/objects'/hashlib.sha256(original).hexdigest()
        outside=self.root/'outside';outside.write_bytes(b'protected external bytes')
        for mode in ('race_file','race_link'):
            with self.subTest(mode=mode):
                if shared.is_symlink():shared.unlink()
                if shared.exists():shared.chmod(0o600)
                shared.write_bytes(b'x'*len(original))
                result=self.run_host(mode,'base.zip',okay=False)
                self.assertIn('Asset',result.stderr)
                if mode=='race_file':self.assertEqual(b'racing replacement',shared.read_bytes())
                else:self.assertTrue(shared.is_symlink());self.assertEqual(b'protected external bytes',outside.read_bytes())
                self.assertFalse(list((self.root/'store/accepted').iterdir()))

    def test_failed_repair_part_keeps_other_verified_objects_and_receipt(self):
        self.run_host('plain','base.zip','zones.zip')
        original=self.payloads['runtime/a.zip'];shared=self.root/'store/objects'/hashlib.sha256(original).hexdigest()
        shared.chmod(0o600);shared.write_bytes(b'old damaged bytes')
        before={p.name:p.read_bytes() for p in (self.root/'store/objects').iterdir()}
        receipts={p.name:p.read_bytes() for p in (self.root/'store/accepted').iterdir()}
        self.archive('bad.zip','base',corrupt=True);self.run_host('plain','bad.zip',okay=False)
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'store/objects').iterdir()})
        self.assertEqual(receipts,{p.name:p.read_bytes() for p in (self.root/'store/accepted').iterdir()})
