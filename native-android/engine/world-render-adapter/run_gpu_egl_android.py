#!/usr/bin/env python3
"""Strict source/fixture/ABI admission and owned Android13 standalone EGL execution."""
import argparse,hashlib,json,re,secrets,subprocess
from pathlib import Path
import gpu_egl_contract as contract
HERE=Path(__file__).resolve().parent

def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,timeout=30).strip()
def checked_file(base,name,max_bytes):
 path=base/name
 if path.is_symlink() or not path.is_file() or path.stat().st_size>max_bytes or not path.resolve().is_relative_to(base.resolve()):raise ValueError('Artifact file boundary '+name)
 return path

def admit(root,artifacts):
 root=root.resolve();artifacts=artifacts.resolve()
 if Path(__file__).resolve()!=root/'native-android/engine/world-render-adapter/run_gpu_egl_android.py':raise ValueError('Executing driver must belong to pinned source root')
 if git(root,'status','--porcelain','--untracked-files=no'):raise ValueError('Clean committed source required')
 expected_source=contract.source_hashes(root)
 if set(git(root,'ls-files','--error-unmatch','--',*expected_source).splitlines())!=set(expected_source):raise ValueError('Every consumed source/helper must be committed')
 q=json.loads(checked_file(artifacts,'qualification.json',1024*1024).read_text())
 if q.get('schema')!='coh-standalone-egl-v1' or q.get('passed') is not True or q.get('source_commit')!=git(root,'rev-parse','HEAD') or q.get('source_tree')!=git(root,'rev-parse','HEAD^{tree}') or q.get('source_sha256')!=expected_source:raise ValueError('Exact source commit/tree/own-driver dependency admission')
 if q.get('prior_gpu_model_sha256')!=contract.PRIOR_SHA or q.get('fixture_sha256')!=contract.FIXTURE_SHA or type(q.get('fixture_bytes'))is not int or q['fixture_bytes']!=43990 or q.get('readback_sha256')!=contract.WHOLE_PACKET_SHA or q.get('host_actual_gles') is not True or q.get('android_executed') is not False or any(q.get(k)is not False for k in ('material_authority','world_authority','shipping_renderer_modified')):raise ValueError('Qualification scope or payload binding')
 fixture=checked_file(artifacts,'box-1.texture',43990);raw=fixture.read_bytes();header=checked_file(artifacts,'egl_fixture_digest.h',1024*1024)
 if len(raw)!=43990 or contract.sha(fixture)!=contract.FIXTURE_SHA or header.read_bytes()!=contract.fixture_header(raw) or contract.sha(header)!=q.get('fixture_header_sha256'):raise ValueError('Exact fixture/header regeneration')
 prior=root/'native-android/engine/world-render-adapter/qualification/gpu-texture-model-20261017/host.json'
 if contract.sha(prior)!=contract.PRIOR_SHA:raise ValueError('Prior source proof bytes')
 prior_proof=json.loads(prior.read_text())
 if q.get('pillow')!=prior_proof['texture_oracle']:raise ValueError('Exact independent all-mip oracle proof')
 for name,want in prior_proof['source_sha256'].items():
  if contract.sha(root/name)!=want:raise ValueError('Original model-qualified production source changed')
 if q.get('host_loaded_mapping_verified')is not False or q.get('system_driver_sanitized')is not False or q.get('host_library_files_before')!=q.get('host_library_files_after') or not isinstance(q.get('host_library_files_before'),dict) or len(q['host_library_files_before'])!=2 or any(not re.fullmatch('[0-9a-f]{64}',v) for v in q['host_library_files_before'].values()):raise ValueError('Declared dispatch-file observation boundary')
 if q.get('host_headers')!=json.loads((HERE/'egl-host-header-pins.json').read_text()):raise ValueError('Primary header provenance')
 if not isinstance(q.get('host'),dict) or set(q['host'])!={'release','address','undefined','finite-fixture'}:raise ValueError('Host mode closure')
 for mode,value in q['host'].items():
  contract.native(value.get('native'),'host-linux')
  host_binary=checked_file(artifacts,'host-'+mode,16*1024*1024);host_packet=checked_file(artifacts,mode+'.rgba',3*349524)
  if value.get('binary_sha256')!=contract.sha(host_binary) or host_packet.stat().st_size!=3*349524 or contract.sha(host_packet)!=contract.WHOLE_PACKET_SHA:raise ValueError('Actual host binary/readback binding')
  if value.get('packet_sha256')!=contract.WHOLE_PACKET_SHA:raise ValueError('Host all-stage readback equality')
 ndk=q.get('ndk')
 if not isinstance(ndk,dict) or not re.fullmatch('[0-9a-f]{64}',ndk.get('clang_sha256','')) or ndk.get('revision')!='28.2.13676358' or not re.fullmatch('[0-9a-f]{64}',ndk.get('source_properties_sha256','')) or set(ndk.get('headers_sha256',{}))!=set(q['host_headers']) or any(not re.fullmatch('[0-9a-f]{64}',v) for v in ndk['headers_sha256'].values()):raise ValueError('NDKr28c declaration/header closure')
 if not isinstance(q.get('android'),dict) or set(q['android'])!=set(contract.ABI):raise ValueError('Both ABI receipts required')
 for abi,(_,machine) in contract.ABI.items():
  receipt=q['android'][abi];name=abi+'/coh_gpu_egl_test';path=checked_file(artifacts,name,16*1024*1024)
  if set(receipt)!={'binary','binary_sha256','bytes','elf_machine','compiler_sha256','built','executed'} or receipt['binary']!=name or receipt['built']is not True or receipt['executed']is not False or type(receipt['bytes'])is not int or receipt['bytes']!=path.stat().st_size or type(receipt['elf_machine'])is not int or receipt['elf_machine']!=machine or receipt['binary_sha256']!=contract.sha(path) or not re.fullmatch('[0-9a-f]{64}',receipt['compiler_sha256']):raise ValueError('ABI exact binary receipt')
  contract.elf(path,machine)
 return q

class Adb:
 def __init__(self,path,serial,output):self.path,self.serial,self.output=path,serial,output;self.counter=0
 def run(self,args,timeout=45):
  self.counter+=1;p=subprocess.run([str(self.path),'-s',self.serial,*map(str,args)],capture_output=True,timeout=timeout)
  if len(p.stdout)>2*1024*1024 or len(p.stderr)>1024*1024:raise ValueError('Bounded adb output exceeded')
  with (self.output/f'adb-{self.counter:02}.stdout').open('xb') as stream:stream.write(p.stdout)
  with (self.output/f'adb-{self.counter:02}.stderr').open('xb') as stream:stream.write(p.stderr)
  if p.returncode:raise ValueError('adb operation failed '+str(self.counter))
  return p.stdout.decode('utf-8').strip()
def device_hash(adb,path):
 text=adb.run(['shell','sha256sum',path]);m=re.fullmatch(r'([0-9a-f]{64})\s+\*?'+re.escape(path),text)
 if not m:raise ValueError('Device hash shape')
 return m.group(1)

def execute(q,args,output,adb):
 remote='/data/local/tmp/coh-egl-'+secrets.token_hex(12);made=False
 receipt={'passed':False,'source_commit':q['source_commit'],'source_tree':q['source_tree'],'qualification_sha256':contract.sha(args.artifacts/'qualification.json'),'validated':True,'native_execution_attempted':False,'android_executed':False,'device_cleanup_verified':False,'material_authority':False,'world_authority':False,'abi':args.abi}
 try:
  if adb.run(['shell','getprop','ro.build.version.sdk'])!='33' or adb.run(['shell','getprop','ro.product.cpu.abi'])!=args.abi:raise ValueError('Actual Android13 selected ABI required')
  receipt['platform_loaded_mapping_verified']=False
  receipt['platform_library_files_before']={name:device_hash(adb,name) for name in ('/system/lib64/libEGL.so','/system/lib64/libGLESv3.so','/system/lib64/libz.so')}
  made=True;adb.run(['shell','mkdir',remote]);binary=args.artifacts/args.abi/'coh_gpu_egl_test';fixture=args.artifacts/'box-1.texture'
  for source,name,want in ((binary,'coh_gpu_egl_test',q['android'][args.abi]['binary_sha256']),(fixture,'box-1.texture',contract.FIXTURE_SHA)):
   adb.run(['push',source,remote+'/'+name]);
   if device_hash(adb,remote+'/'+name)!=want:raise ValueError('Transferred exact bytes differ')
  adb.run(['shell','chmod','700',remote+'/coh_gpu_egl_test']);receipt['native_execution_attempted']=True
  text=adb.run(['shell','timeout','-s','KILL','120',remote+'/coh_gpu_egl_test',remote+'/box-1.texture',remote+'/readback.rgba'],timeout=180)
  value=contract.native(json.loads(text),'android');receipt['android_executed']=True;receipt['native']=value
  if adb.run(['shell','stat','-c','%s',remote+'/readback.rgba'])!=str(3*349524) or device_hash(adb,remote+'/readback.rgba')!=contract.WHOLE_PACKET_SHA:raise ValueError('Actual GPU packet size/hash mismatch')
  packet=output/'readback.rgba';adb.run(['pull',remote+'/readback.rgba',packet])
  if packet.stat().st_size!=3*349524 or contract.sha(packet)!=contract.WHOLE_PACKET_SHA:raise ValueError('Pulled actual GPU readback differs')
  receipt['readback_sha256']=contract.WHOLE_PACKET_SHA;receipt['passed']=True
 except Exception as error:receipt['failure']=type(error).__name__+': '+str(error)[:200]
 finally:
  try:
   if 'platform_library_files_before' in receipt:
    receipt['platform_library_files_after']={name:device_hash(adb,name) for name in receipt['platform_library_files_before']}
    if receipt['platform_library_files_after']!=receipt['platform_library_files_before']:raise ValueError('Platform dispatch library files changed')
  except Exception:
   receipt['passed']=False;receipt['platform_library_observation_failure']=True
  try:
   if made:adb.run(['shell','rm','-rf',remote]);adb.run(['shell','test','!','-e',remote])
   receipt['device_cleanup_verified']=True
  except Exception:receipt['cleanup_failure']='owned_device_directory_not_verified_absent'
  receipt['passed']=receipt['passed'] and receipt['device_cleanup_verified']
 return receipt

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source-root','artifacts','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--validate-only',action='store_true');p.add_argument('--adb',type=Path);p.add_argument('--serial');p.add_argument('--abi',choices=tuple(contract.ABI),default='x86_64');a=p.parse_args();a.artifacts=a.artifacts.resolve()
 if a.output.exists() or (a.output.parent.exists() and any(a.output.parent.iterdir())):raise ValueError('Fresh empty evidence directory required')
 q=admit(a.source_root,a.artifacts);initial_qualification_sha=contract.sha(a.artifacts/'qualification.json');a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.validate_only:r={'passed':True,'validated':True,'source_commit':q['source_commit'],'qualification_sha256':contract.sha(a.artifacts/'qualification.json'),'android_executed':False,'material_authority':False,'world_authority':False}
 else:
  if not a.adb or not a.serial:p.error('Explicit adb and serial required')
  adb=Adb(a.adb,a.serial,a.output.parent);r=execute(q,a,a.output.parent,adb)
 try:
  admit(a.source_root,a.artifacts)
  if contract.sha(a.artifacts/'qualification.json')!=initial_qualification_sha:raise ValueError('Qualification changed during execution')
  r['post_admission_verified']=True
 except Exception:
  r['passed']=False;r['post_admission_verified']=False;r['post_admission_failure']='source_or_artifact_changed'
 a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(0 if r['passed'] else 1)
if __name__=='__main__':main()
