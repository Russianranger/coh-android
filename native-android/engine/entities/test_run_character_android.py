import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('rawdriver',HERE/'run_character_android.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class Admission(unittest.TestCase):
 def fixture(self,root,kind='creation'):
  repo=root/'repo';art=root/'art';repo.mkdir();art.mkdir()
  schema,binary,checks=d.SPECS[kind];runner='native-android/engine/entities/run_character_android.py';source='native-android/engine/entities/coh_character_creation.c' if kind=='creation' else 'native-android/engine/entity-globals/coh_power_info.c'
  sources={}
  for name in d.REQUIRED[kind]:
   data=Path(d.__file__).read_bytes() if name==runner else b'qualified fixture source'
   p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);sources[name]=d.digest(p)
  expected=dict(passed=True,checks=checks,actor_publication=False)
  expected[{'creation':'whole_character_complete','outer':'whole_initial_update_complete','power-info':'whole_initial_update'}[kind]]=False
  proof=dict(schema=schema,passed=True,actor_publication=False,acknowledgments_enabled=False,source_sha256=sources,checks={m:copy.deepcopy(expected) for m in ('release','asan','ubsan')},android={})
  proof[{'creation':'whole_character_complete','outer':'whole_initial_update_complete','power-info':'whole_initial_update'}[kind]]=False
  fixtures={'initial_fixtures.h':b'initial','ui_fixtures.h':b'ui'} if kind=='creation' else {'power_info_fixtures.h':b'power'}
  if kind=='outer':fixtures={'initial_fixtures.h':b'initial','ui_fixtures.h':b'ui','tail_fixtures.h':b'tail'}
  (art/'android').mkdir()
  for name,data in fixtures.items():(art/'android'/name).write_bytes(data)
  if kind in ('creation','outer'):proof.update(fixture_initial={'sha256':d.digest(art/'android/initial_fixtures.h')},ui_fixtures_sha256=d.digest(art/'android/ui_fixtures.h'))
  if kind=='outer':proof.update(outer_character_wire_grammar_complete=True,fixtures_sha256={n:d.digest(art/'android'/n) for n in fixtures},tail_fixtures_sha256=d.digest(art/'android/tail_fixtures.h'))
  if kind=='power-info':proof['fixtures']={'sha256':d.digest(art/'android/power_info_fixtures.h')}
  for abi,machine in [('arm64-v8a',183),('x86_64',62)]:
   out=art/'android'/abi;out.mkdir();raw=bytearray(64);raw[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',raw,18,machine);(out/binary).write_bytes(raw)
   receipt=dict(built=True,executed=False,binary=binary,binary_sha256=d.digest(out/binary),source_sha256=sources,fixtures_sha256={n:d.digest(art/'android'/n) for n in fixtures});proof['android'][abi]=receipt;(out/'receipt.json').write_text(json.dumps(receipt))
  (art/'host.json').write_text(json.dumps(proof));return repo,art,proof
 def test_valid_both_modules(self):
  for kind in d.SPECS:
   with tempfile.TemporaryDirectory() as tmp:
    repo,art,_=self.fixture(Path(tmp),kind);d.admit(kind,art,repo)
 def test_refusal_matrix(self):
  mutations=[lambda p:p.update(provider_sha256={next(iter(p['source_sha256'])):'0'*64}),lambda p:p['source_sha256'].pop('native-android/engine/replication/coh_replication.c'),lambda p:p['android']['x86_64'].pop('fixtures_sha256'),lambda p:p.update(passed=False),lambda p:p.update(actor_publication=True),lambda p:p.update(acknowledgments_enabled=True),lambda p:p.update(schema='other'),lambda p:p['checks']['asan'].update(checks=0),lambda p:p['checks']['release'].update(checks=True),lambda p:p['android'].pop('arm64-v8a'),lambda p:p['source_sha256'].pop('native-android/engine/entities/run_character_android.py')]
  for mutate in mutations:
   with tempfile.TemporaryDirectory() as tmp:
    repo,art,p=self.fixture(Path(tmp));mutate(p);(art/'host.json').write_text(json.dumps(p))
    with self.assertRaises(ValueError):d.admit('creation',art,repo)
 def test_mutated_sources_fixtures_binaries_receipts(self):
  names=['repo/native-android/engine/entities/coh_character_creation.c','art/android/initial_fixtures.h','art/android/x86_64/coh_character_creation_test','art/android/arm64-v8a/receipt.json']
  for name in names:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);repo,art,_=self.fixture(root);p=root/name;p.write_bytes(p.read_bytes()+b'changed')
    with self.assertRaises((ValueError,json.JSONDecodeError)):d.admit('creation',art,repo)
 def test_symlinks_and_escape(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);repo,art,_=self.fixture(root);p=art/'android/x86_64/coh_character_creation_test';data=p.read_bytes();p.unlink();(root/'external').write_bytes(data);p.symlink_to(root/'external')
   with self.assertRaises(ValueError):d.admit('creation',art,repo)
   for name in ['../escape','/absolute','dir\\escape']:
    with self.assertRaises(ValueError):d.child(root,name)
 def test_device_attempt_and_cleanup(self):
  for fail in (False,True):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);repo,art,proof=self.fixture(root,'outer');output=root/'execution/receipt.json';calls=[]
    def execute(argv,log,timeout=60):
     args=list(map(str,argv))[3:];calls.append(args)
     if args[:2]==['shell','getprop']:return {'ro.build.version.sdk':'33','ro.product.cpu.abi':'x86_64','ro.kernel.qemu':'1'}[args[2]]
     if args[:2]==['shell','sha256sum']:return proof['android']['x86_64']['binary_sha256']+'  binary'
     if args[:2]==['shell','timeout']:
      self.assertEqual(args[2:5],['-s','KILL','90'])
      if fail:raise ValueError('simulated native timeout/launch refusal')
      return json.dumps(proof['checks']['release'])
     return ''
    argv=['driver','--kind','outer','--artifacts',str(art),'--source-root',str(repo),'--adb','/fixture/adb','--serial','emulator-5554','--output',str(output)]
    with mock.patch('sys.argv',argv),mock.patch.object(d,'command',side_effect=execute):code=d.main()
    receipt=json.loads(output.read_text());self.assertEqual(code,1 if fail else 0);self.assertEqual(receipt['android_executed'],not fail);self.assertTrue(receipt['native_execution_attempted']);self.assertTrue(receipt['temporary_files_removed']);self.assertTrue(any(a[:3]==['shell','rm','-rf'] for a in calls))
if __name__=='__main__':unittest.main()
