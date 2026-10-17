#!/usr/bin/env python3
"""Pure archived-source and PE-header admission; never run compiler or PE."""
import base64,gzip,hashlib,io,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path,PurePosixPath
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
SOURCE='365bc28e0433112e2292e44f6338da9fbc5c270e'
AUTH='native-android/engine/auth-interop/'
PE='9144727b021526b3777cba53e4935c0ab9c35a76a51d6f00aa50678b7590ea63'
LOCK='a70e878ad1f8872cc876987f6ec644f27bbf7c5ec98db528742f28ed5b098125'
def sha(b):return hashlib.sha256(b).hexdigest()
def verify(root):
 def blob(path):return subprocess.check_output(['git','--no-replace-objects','-C',str(root),'show',SOURCE+':'+path],timeout=30)
 def archive(name,digest):
  raw=(HERE/name).read_bytes();assert sha(raw)==digest
  z=zipfile.ZipFile(io.BytesIO(raw));assert not z.testzip();result={}
  for m in z.infolist():
   n=PurePosixPath(m.filename);assert not n.is_absolute() and '..' not in n.parts and '\\' not in m.filename
   assert (m.external_attr>>16)&0o170000!=0o120000
   assert len(n.parts)==1 and m.file_size<128*1024*1024 and m.filename not in result
   result[m.filename]=z.read(m)
  return result
 controls=archive('controls.zip','c934e2eea66bf701d83c74426c2517253a8a0aec91d5106c0145bbecce5826a4')
 files=archive('compile.zip','641c7f1eb7637c2c81ac0dc8861a5597654ea8bcc17c70f917ac1a79c25b38e9')
 c=json.loads(controls['receipt.json']);q=json.loads(files['receipt.json'])
 assert c['passed'] is True and c['validation_only'] is False and c['tests_run']==15
 assert c['cmake_interpreter_executed'] is True and c['exact_tools_rehashed_before_and_after'] is True
 assert c['source_inputs_unchanged'] is True and c['compiler_executed'] is False and c['service_executed'] is False
 assert c['source_revision']==q['repository_commit']==SOURCE and c['toolchain_lock_sha256']==LOCK
 assert 'Ran 15 tests' in controls['controls.log'].decode() and 'skipped=' not in controls['controls.log'].decode()
 for name,h in c['source_sha256'].items():assert sha(blob(name))==h
 for name,h in q['input_state_before']['helper_inputs'].items():assert sha(blob(AUTH+name))==h
 for name,row in q['files'].items():assert len(files[name])==row['bytes'] and sha(files[name])==row['sha256']
 assert sha(blob(AUTH+'evidence/windows-tool-inventory-39005570623/reviewed-toolchain-lock.json'))==LOCK
 assert files['toolchain-lock.json']==blob(AUTH+'evidence/windows-tool-inventory-39005570623/reviewed-toolchain-lock.json')
 with tempfile.TemporaryDirectory() as td:
  stage=Path(td)/'stage';stage.mkdir();auth=Path(td)/'auth';dep=auth/'deployment';dep.mkdir(parents=True)
  for name,data in files.items():(stage/name).write_bytes(data)
  names=subprocess.check_output(['git','--no-replace-objects','-C',str(root),'ls-tree','--name-only',SOURCE+':'+AUTH+'deployment'],text=True).splitlines()
  for name in names:
   if name.endswith('.py'):(dep/name).write_bytes(blob(AUTH+'deployment/'+name))
  (auth/'source_oracle.py').write_bytes(blob(AUTH+'source_oracle.py'))
  sys.path.insert(0,str(dep));import hosted_manual_atlas_compile as driver
  admitted=driver.admit(stage,sha(files['receipt.json']),PE,LOCK,root)
  assert admitted['admitted'] is True
 maps=json.loads(gzip.decompress(files['all-file-maps.json.gz']))
 assert len(maps['source_before'])==6007
 assert all(row['returncode']==0 for row in q['commands']) and len(q['commands'])==15
 return {'passed':True,'run_id':39008877421,'source_commit':SOURCE,'control_source_inputs_raw_git_verified':len(c['source_sha256']),'compile_helper_raw_git_verified':len(q['input_state_before']['helper_inputs']),'controls':15,'control_skips':0,'source_files':6007,'generated_files':len(maps['generated_source']),'dependencies':3,'successful_commands':15,'compile_receipt_sha256':sha(files['receipt.json']),'controls_receipt_sha256':sha(controls['receipt.json']),'dbserver_pe_sha256':PE,'crashrpt_sha256':sha(files['CrashRpt.dll']),'admission':admitted,'scope':'Exact archived compile-only evidence; no binary/compiler/service execution by this verifier; no persistence/Wine/runtime replacement admission.'}
if __name__=='__main__':print(json.dumps(verify(Path(sys.argv[1]).resolve()),indent=2,sort_keys=True))
