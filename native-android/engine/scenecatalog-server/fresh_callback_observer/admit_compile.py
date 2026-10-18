#!/usr/bin/env python3
"""Record/admit only the separately identified fresh callback-sealed PE role."""
import argparse,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
try:from . import stage
except ImportError:import stage
sys.path.insert(0,str(HERE.parent))
import delivery as d
SCHEMA='coh-fresh-groups-observer-compile-v1'
RECEIPT='compile-only-receipt.json'

def names(root):
 return {'MapServer.exe','CMakeCache.txt',stage.RECEIPT,stage.old.RECEIPT,stage.old.PRIOR,
 'map-startup-inputs.json',*('source/'+n for n in (*stage.PATCHED,*{**stage.old.overlays(root),**stage.overlays(root)}))}

def validators(root):
 directory=root/'native-android/engine/scenecatalog-qualification'
 sys.path.insert(0,str(directory))
 try:
  spec=importlib.util.spec_from_file_location('coh_fresh_compile_checks',directory/'record_export_compile.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  d.require(Path(module.__file__).resolve()==directory/'record_export_compile.py'
   and Path(sys.modules['common'].__file__).resolve()==directory/'common.py','FRESH_PE_HELPER_CHECKOUT')
  return module
 finally:sys.path.pop(0)


def inspect(source,root,receipt_sha256):
 source=d.path(source);root=d.path(root);d.sha(receipt_sha256);closure=stage.checkout_closure(root)
 before=d.hash_file(source/RECEIPT,8*1024**2)
 d.require(before[1]==receipt_sha256,'FRESH_COMPILE_PIN')
 receipt=d.json_object(d.read(source/RECEIPT,8*1024**2))
 d.require(receipt.get('schema')==SCHEMA and receipt.get('passed') is True and receipt.get('build_role')==stage.ROLE
 and receipt.get('source_git_status_porcelain')==[] and receipt.get('compile_only') is True
 and receipt.get('runtime_executed') is False and receipt.get('source_stage_verified') is True
 and receipt.get('inherited_source_closure_reverified') is True
 and receipt.get('external_input_archive_verification_claimed') is False and receipt.get('platform')=='Win32'
 and receipt.get('pe_machine')=='i386' and receipt.get('configuration')=='OptDebug' and receipt.get('generator')=='Visual Studio 18 2026'
 and receipt.get('accepted_observer_equivalence') is False,'FRESH_COMPILE_SCOPE')
 d.require(type(receipt.get('source_revision')) is str and len(receipt['source_revision'])==40 and all(c in '0123456789abcdef' for c in receipt['source_revision']),'FRESH_REVISION')
 expected=names(root);d.require(type(receipt.get('artifacts')) is dict and set(receipt['artifacts'])==expected,'FRESH_ARTIFACTS')
 for n,v in receipt['artifacts'].items():
  size,digest=d.hash_file(source/n,16*1024**2);d.require(v=={'bytes':size,'sha256':digest},'FRESH_ARTIFACT_HASH')
 checks=validators(root);checks.pe32_identity(source/'MapServer.exe')
 staged=receipt.get('staged_source_root');d.require(type(staged) is str and re.fullmatch(r'[A-Za-z]:/[^\\\r\n]+',staged) is not None,'FRESH_RETAINED_STAGE_ROOT')
 checks.cmake_identity(source/'CMakeCache.txt',Path(staged))
 declared=stage.verify_bytes(root,lambda n:d.read(source/(n if n in (stage.RECEIPT,stage.old.RECEIPT,stage.old.PRIOR) else 'source/'+n),16*1024**2))
 d.require(d.hash_file(source/RECEIPT,8*1024**2)==before,'FRESH_COMPILE_CHANGED')
 for n,v in receipt['artifacts'].items():
  size,digest=d.hash_file(source/n,16*1024**2);d.require(v=={'bytes':size,'sha256':digest},'FRESH_ARTIFACT_CHANGED')
 stage.unchanged_checkout(root,closure)
 return receipt,declared

def record(root,staged,binary,cache,output):
 root=d.path(root);staged=d.path(staged);binary=d.path(binary);cache=d.path(cache);output=d.path(output);closure=stage.checkout_closure(root)
 # This command only copies an already-built PE. It never invokes a compiler,
 # installs/deploys a PE or starts any original source process.
 declared=stage.verify_staged(root,staged)
 revision=subprocess.run(['git','rev-parse','HEAD'],cwd=root,check=True,capture_output=True,text=True).stdout.strip()
 status=subprocess.run(['git','status','--porcelain'],cwd=root,check=True,capture_output=True,text=True).stdout.splitlines()
 d.require(status==[],'FRESH_SOURCE_DIRTY');d.require(not output.exists(),'FRESH_OUTPUT_EXISTS')
 d.require(binary==staged/'out/build/vs2026/bin/OptDebug/MapServer.exe' and cache==staged/'out/build/vs2026/CMakeCache.txt','FRESH_BUILD_PATHS')
 checks=validators(root);checks.pe32_identity(binary);checks.cmake_identity(cache,staged)
 output.mkdir(mode=0o700);created=[]
 try:
  sources={'MapServer.exe':binary,'CMakeCache.txt':cache,
   **{n:staged/n for n in (stage.RECEIPT,stage.old.RECEIPT,stage.old.PRIOR,'map-startup-inputs.json')},
   **{'source/'+n:staged/n for n in (*stage.PATCHED,*{**stage.old.overlays(root),**stage.overlays(root)})}}
  artifacts={}
  for n,src in sources.items():
   target=output/n;target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as stream:
    created.append(target);stream.write(d.read(src,16*1024**2));stream.flush();os.fsync(stream.fileno())
   size,digest=d.hash_file(target,16*1024**2);d.require((size,digest)==d.hash_file(src,16*1024**2),'FRESH_COPY_CHANGED');artifacts[n]={'bytes':size,'sha256':digest}
  # Revalidate actual staged sources after all copies and before final receipt.
  d.require(stage.base.json_equal(stage.verify_staged(root,staged),declared),'FRESH_STAGE_CHANGED')
  d.require(subprocess.run(['git','rev-parse','HEAD'],cwd=root,check=True,capture_output=True,text=True).stdout.strip()==revision
   and subprocess.run(['git','status','--porcelain'],cwd=root,check=True,capture_output=True,text=True).stdout.splitlines()==[],'FRESH_SOURCE_CHANGED')
  receipt={'schema':SCHEMA,'passed':True,'build_role':stage.ROLE,'source_revision':revision,
   'source_git_status_porcelain':[],'compile_only':True,'runtime_executed':False,
   'source_stage_verified':True,'inherited_source_closure_reverified':True,
   'external_input_archive_verification_claimed':False,'platform':'Win32','pe_machine':'i386',
   'accepted_observer_equivalence':False,'configuration':'OptDebug','generator':'Visual Studio 18 2026',
   'staged_source_root':staged.as_posix(),'artifacts':artifacts}
  stage.unchanged_checkout(root,closure)
  with (output/RECEIPT).open('xb') as stream:
   created.append(output/RECEIPT);stream.write((json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode('utf-8'));stream.flush();os.fsync(stream.fileno())
  inspect(output,root,d.hash_file(output/RECEIPT,8*1024**2)[1])
  stage.unchanged_checkout(root,closure)
  return receipt
 except BaseException:
  for target in reversed(created):
   try:target.unlink()
   except OSError:pass
  raise

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--compile-directory',type=Path);p.add_argument('--compile-receipt-sha256')
 p.add_argument('--record',action='store_true');p.add_argument('--already-staged',type=Path);p.add_argument('--binary',type=Path);p.add_argument('--cmake-cache',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.record:
  d.require(all((a.already_staged,a.binary,a.cmake_cache,a.output)) and not a.compile_directory and not a.compile_receipt_sha256,'FRESH_RECORD_ARGS')
  receipt=record(a.source_root,a.already_staged,a.binary,a.cmake_cache,a.output)
 else:
  d.require(a.compile_directory and a.compile_receipt_sha256 and not any((a.already_staged,a.binary,a.cmake_cache,a.output)),'FRESH_ADMIT_ARGS')
  receipt,_=inspect(a.compile_directory,a.source_root,a.compile_receipt_sha256)
 print(json.dumps({'passed':True,'build_role':stage.ROLE,'source_revision':receipt['source_revision'],'binary':receipt['artifacts']['MapServer.exe'],'runtime_executed':False}))
if __name__=='__main__':main()
