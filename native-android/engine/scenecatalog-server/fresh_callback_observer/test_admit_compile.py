"""New compile-role shape/byte controls; no compiler or server execution."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import admit_compile as a

class Controls(unittest.TestCase):
 def fixture(self,root):
  # A DOS/PE-shaped byte fixture is explicitly synthetic and not executable.
  pe=bytearray(1024);pe[:2]=b'MZ';pe[60:64]=(128).to_bytes(4,'little');pe[128:132]=b'PE\0\0';pe[132:134]=(0x14c).to_bytes(2,'little');pe[134:136]=(1).to_bytes(2,'little');pe[148:150]=(96).to_bytes(2,'little');pe[150:152]=(2).to_bytes(2,'little');pe[152:154]=(0x10b).to_bytes(2,'little');pe[168:172]=(1).to_bytes(4,'little')
  (root/'MapServer.exe').write_bytes(pe)
  (root/'CMakeCache.txt').write_text('CMAKE_GENERATOR:INTERNAL=Visual Studio 18 2026\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\nCMAKE_CONFIGURATION_TYPES:STRING=OptDebug;Release\nCMAKE_HOME_DIRECTORY:INTERNAL=D:/private/staged\n')
  receipt={'schema':a.SCHEMA,'passed':True,'build_role':a.stage.ROLE,'source_revision':'a'*40,
   'source_git_status_porcelain':[],'compile_only':True,'runtime_executed':False,
   'source_stage_verified':True,'inherited_source_closure_reverified':True,
   'external_input_archive_verification_claimed':False,'platform':'Win32','pe_machine':'i386',
   'accepted_observer_equivalence':False,'configuration':'OptDebug','generator':'Visual Studio 18 2026','staged_source_root':'D:/private/staged','artifacts':{'MapServer.exe':{'bytes':len(pe),'sha256':a.d.digest(pe)},'CMakeCache.txt':{'bytes':(root/'CMakeCache.txt').stat().st_size,'sha256':a.d.digest((root/'CMakeCache.txt').read_bytes())}}}
  return receipt
 def write(self,root,value):
  raw=(json.dumps(value)+'\n').encode();(root/a.RECEIPT).write_bytes(raw);return a.d.digest(raw)
 def test_new_role_scope_strict_and_old_role_refused(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);receipt=self.fixture(root)
   with patch.object(a.stage,'checkout_closure',return_value={}),patch.object(a.stage,'unchanged_checkout',return_value=None),patch.object(a,'names',return_value={'MapServer.exe','CMakeCache.txt'}),patch.object(a.stage,'verify_bytes',return_value={'synthetic':True}):
    a.inspect(root,HERE.parents[3],self.write(root,receipt))
    for key,value in (('schema','coh-groups-transaction-compile-v1'),('build_role',a.stage.old.ROLE),('passed',1),('compile_only',1),('source_stage_verified',False),('runtime_executed',True),('accepted_observer_equivalence',True),('inherited_source_closure_reverified',False),('external_input_archive_verification_claimed',True),('source_revision','arbitrary-private-text')):
     changed=copy.deepcopy(receipt);changed[key]=value
     with self.subTest(key=key),self.assertRaises(ValueError):a.inspect(root,HERE.parents[3],self.write(root,changed))
 def test_binary_shape_hash_names_and_late_bytes(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);receipt=self.fixture(root)
   with patch.object(a.stage,'checkout_closure',return_value={}),patch.object(a.stage,'unchanged_checkout',return_value=None),patch.object(a,'names',return_value={'MapServer.exe','CMakeCache.txt'}),patch.object(a.stage,'verify_bytes',return_value={}):
    pin=self.write(root,receipt)
    with self.assertRaises(ValueError):a.inspect(root,HERE.parents[3],'0'*64)
    pe=(root/'MapServer.exe').read_bytes();(root/'MapServer.exe').write_bytes(pe+b'changed')
    with self.assertRaises(ValueError):a.inspect(root,HERE.parents[3],pin)
    (root/'MapServer.exe').write_bytes(pe)
    def mutate(*args,**kwargs):(root/'MapServer.exe').write_bytes(pe+b'late');return {}
    with patch.object(a.stage,'verify_bytes',side_effect=mutate),self.assertRaises(ValueError):a.inspect(root,HERE.parents[3],pin)
   for value in (b'',b'MZ'+bytes(254),bytes(512)):
    with tempfile.TemporaryDirectory() as bad:
     path=Path(bad)/'bad.exe';path.write_bytes(value)
     with self.assertRaises(ValueError):a.validators(HERE.parents[3]).pe32_identity(path)
 def test_strict_existing_pe_and_cmake_identity_controls(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);self.fixture(root);checks=a.validators(HERE.parents[3]);checks.pe32_identity(root/'MapServer.exe');checks.cmake_identity(root/'CMakeCache.txt',Path('D:/private/staged'))
   raw=(root/'MapServer.exe').read_bytes()
   for offset,value in ((152,(0x20b).to_bytes(2,'little')),(150,(0x2002).to_bytes(2,'little')),(168,bytes(4)),(134,bytes(2))):
    changed=bytearray(raw);changed[offset:offset+len(value)]=value;(root/'MapServer.exe').write_bytes(changed)
    with self.subTest(offset=offset),self.assertRaises(ValueError):checks.pe32_identity(root/'MapServer.exe')
   cache=(root/'CMakeCache.txt').read_text()
   for before,after in (('Win32','x64'),('OptDebug;Release','Release'),('Visual Studio 18 2026','other'),('D:/private/staged','D:/other')):
    (root/'CMakeCache.txt').write_text(cache.replace(before,after))
    with self.subTest(before=before),self.assertRaises(ValueError):checks.cmake_identity(root/'CMakeCache.txt',Path('D:/private/staged'))

 def test_receipt_encoding_is_lf_bytes(self):
  source=(HERE/'admit_compile.py').read_text()
  self.assertIn("(output/RECEIPT).open('xb')",source)
  self.assertIn("(stage/RECEIPT).open('xb')",(HERE/'stage.py').read_text())

if __name__=='__main__':unittest.main()
