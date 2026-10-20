#!/usr/bin/env python3
"""Focused offline text projection; original tokenizer/hash execute, no server."""
import io,json,os,sqlite3,subprocess,tempfile,unittest
from pathlib import Path
from unittest import mock
import power_text_map as mapping
import power_text_oracle as oracle

ROOT=Path(__file__).resolve().parents[3]

class PowerTextMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=tempfile.TemporaryDirectory(prefix='coh-power-text-tests-')
        cls.original,cls.provenance,cls.source=oracle.build(ROOT,Path(cls.work.name))
    @classmethod
    def tearDownClass(cls):cls.work.cleanup()
    def text(self,data):
        with tempfile.TemporaryFile() as f:
            f.write(data);f.flush();f.seek(0)
            yield from self.original.tokens(f.fileno())
    def fixture(self,root,files):
        subprocess.run(['git','init','-q',str(root)],check=True)
        for name,data in files.items():
            p=root/mapping.TEXT_ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        subprocess.run(['git','-C',str(root),'add','upstream'],check=True)
        subprocess.run(['git','-C',str(root),'-c','user.name=Offline Test','-c','user.email=offline@example.invalid','commit','-qm','Fixture'],check=True)
    def test_original_hash_normalization_zero_and_bounds(self):
        crc=self.original.crc
        self.assertEqual(crc(b'Incarnate.Data.Rikti_Data'),0xf0840fa4)
        self.assertEqual(crc(b'A\\B.C'),crc(b'a/b.c'))
        self.assertNotEqual(crc(b'Category.Set.One'),crc(b'Category.Set.Two'))
        for invalid in (b'',b'x'*260,b'bad\0name',b'bad\nname',b'\xff'):
            with self.subTest(invalid=invalid[:20]),self.assertRaises(ValueError):crc(invalid)
        self.assertEqual(self.original.lib.ptm_crc(None),0)
    def test_original_comments_strings_and_fullname_parameter(self):
        raw=b'''\xef\xbb\xbf# Power Fake.Comment.Name { }
// Power Fake.Comment.Name { }
pOwEr Cat.Set.Declared
{
 Name UnrelatedShortName
 DisplayName "Power Fake.Name { }"
 Help <<
Power Another.Fake.Name { }\n>>
 Params <&Power Fake.Escape.Name { \\n }&>
 Mod { Nested { Value "}" } }
}
Power "Cat.Set.Quoted" { Name "{" }
'''
        result=list(mapping.definitions(self.text(raw)))
        self.assertEqual([r[0] for r in result],[b'Cat.Set.Declared',b'Cat.Set.Quoted'])
        self.assertGreater(result[1][1],result[0][1])
        self.assertEqual(list(mapping.definitions(self.text(b'Power Cat.Set.First {\n FullName Cat.Set.Replaced\n}\n')))[0][0],b'Cat.Set.Replaced')
    def test_malformed_or_unowned_lexical_inputs_never_emit_a_complete_record(self):
        for raw in (b'Power',b'Power { }',b'Power X Y',b'Power X { Name "unterminated\n}',
                    b'Power X {',b'include missing.powers\n',b'Wrong X {}',b'Power X { Help << unclosed }'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):list(mapping.definitions(self.text(raw)))
    def test_original_tokenizer_refill_is_bounded(self):
        # Cross several24KiB original refills, retaining no record object graph.
        raw=b'#'+b' comment'*2000+b'\n'+b'Power Cat.Set.Refill {\n'+(b' Name x\n'*6000)+b'}\n'
        self.assertEqual([p[0] for p in mapping.definitions(self.text(raw))],[b'Cat.Set.Refill'])
        self.assertLess(self.original.lib.ptm_owner_bytes(),49*1024)
    def test_ordered_first_winner_and_pinned_input_inventory(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo';out=Path(t)/'map.sqlite'
            self.fixture(root,{'z.powers':b'Power cat.set.first { Name Ignored }\nPower Cat.Set.Last { }\n',
                               'a.powers':b'Power Cat.Set.First { Name NoFilenameInference }\n'})
            summary=mapping.build_map(root,out,self.original,self.provenance)
            self.assertEqual((summary['declarations'],summary['unique_crc'],summary['duplicate_crc']),(3,2,1))
            row=mapping.lookup(out,self.original.crc(b'cat.set.first'))
            self.assertEqual(row['full_name'],'Cat.Set.First');self.assertTrue(row['path'].endswith('/a.powers'));self.assertEqual(row['ordinal'],1)
            self.assertIsNone(mapping.lookup(out,0x80443357))
            con=sqlite3.connect(out)
            try:
                self.assertEqual(con.execute('SELECT count(*) FROM inputs WHERE length(sha256)=64').fetchone()[0],2)
                saved=json.loads(con.execute('SELECT value FROM metadata WHERE key="summary"').fetchone()[0])
                self.assertFalse(saved['runtime_dictionary_supplied'])
            finally:con.close()
            with self.assertRaises(ValueError):mapping.build_map(root,out,self.original,self.provenance)
    def test_dirty_alias_truncation_overflow_and_cleanup(self):
        for change in ('dirty','alias','truncated','overflow','churn'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as t:
                root=Path(t)/'repo';out=Path(t)/'map.sqlite';self.fixture(root,{'a.powers':b'Power Cat.Set.First { }\n'})
                path=root/mapping.TEXT_ROOT/'a.powers'
                if change=='dirty':path.write_bytes(b'Power Cat.Set.Other { }\n')
                if change=='alias':
                    donor=Path(t)/'donor';path.rename(donor);path.symlink_to(donor)
                if change=='truncated':
                    path.write_bytes(b'Power Cat.Set.First {\n');subprocess.run(['git','-C',str(root),'add','.'],check=True);subprocess.run(['git','-C',str(root),'-c','user.name=T','-c','user.email=t@example.invalid','commit','-qm','Truncate'],check=True)
                class Changing:
                    lib=self.original.lib;crc=self.original.crc
                    def tokens(_,fd):
                        yield from self.original.tokens(fd)
                        if change=='churn':
                            with path.open('ab') as f:f.write(b' ')
                with mock.patch.object(mapping,'POWER_LIMIT',0 if change=='overflow' else mapping.POWER_LIMIT):
                    with self.assertRaises(ValueError):mapping.build_map(root,out,Changing(),self.provenance)
                self.assertFalse(out.exists());self.assertEqual(list(Path(t).glob('.power-text-*')),[])
    def test_nul_source_and_output_alias_are_not_published(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo';self.fixture(root,{'a.powers':b'Power Cat.Set.First { }\0'})
            out=Path(t)/'map.sqlite'
            with self.assertRaises(ValueError):mapping.build_map(root,out,self.original,self.provenance)
            with self.assertRaises(ValueError):mapping.build_map(root,root/mapping.TEXT_ROOT/'map.sqlite',self.original,self.provenance)
            self.assertFalse(out.exists())
    def test_c_original_bodies_under_release_asan_ubsan(self):
        work=Path(self.work.name);source=self.source.read_text()+r'''
int main(void){
 assert(ptm_crc("A\\B.C")==ptm_crc("a/b.c"));assert(ptm_crc(NULL)==0);
 assert(ptm_crc("Incarnate.Data.Rikti_Data")==0xf0840fa4u);
 char large[261];memset(large,'x',260);large[260]=0;assert(ptm_crc(large)==0);
 for(unsigned i=0;i<100;i++){
  FILE*f=tmpfile();assert(f);const char*s="Power Cat.Set.Real { Name \"}\" }\n";assert(fwrite(s,1,strlen(s),f)==strlen(s));fflush(f);
  void*t=ptm_open(fileno(f));assert(t);char token[12001];int line,quoted,n=0,r;
  while((r=ptm_next(t,token,sizeof(token),&line,&quoted))>0)n++;
  assert(r==0&&n==6);ptm_close(t);fclose(f);
 }
 puts("original tokenizer/hash100 cleanup loops passed");return 0;
}
'''
        harness=work/'original-controls.c';harness.write_text(source)
        for name,flags in (('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])):
            exe=work/('controls-'+name)
            subprocess.run(['flock','/tmp/coh-next-build.lock','cc','-std=gnu99',*flags,str(harness),'-o',str(exe)],check=True,capture_output=True,text=True)
            env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
            result=subprocess.run([str(exe)],check=True,capture_output=True,text=True,env=env)
            self.assertIn('passed',result.stdout)

if __name__=='__main__':unittest.main()
