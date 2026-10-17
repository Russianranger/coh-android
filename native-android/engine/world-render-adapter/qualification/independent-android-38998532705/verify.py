#!/usr/bin/env python3
"""Read-only verification of retained standalone Android artifact; never executes it."""
import argparse, hashlib, json, struct, subprocess, zipfile
from pathlib import Path
HEAD='c21f2c059c0045aedfd9693ff076391598b33163'
ZIP_SHA='84916be2a7827aac487aae7677557afb79874240aca29f5ccad7300be231b4bb'
PACKET='261155800f81fbd7645e9e34a7b4c4ed9b453e1596fe3e947162df24bf29e45c'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify(archive,repo):
 raw=archive.read_bytes();assert len(raw)==2948433 and sha(raw)==ZIP_SHA
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  files={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
 read=lambda n:json.loads(files[n])
 q=read('egl/qualification.json');e=read('egl-execution/receipt.json');p=read('suffix/package.json');h=read('suffix/host.json');s=read('suffix-execution/receipt.json')
 assert q['source_commit']==p['source_revision']==h['source_revision']==e['source_commit']==HEAD
 assert q['source_tree']==e['source_tree']==subprocess.check_output(['git','-C',str(repo),'rev-parse',HEAD+'^{tree}'],text=True).strip()
 bound={}
 for table in [q['source_sha256'],p['source_sha256']]:
  for name,want in table.items():
   assert sha(subprocess.check_output(['git','-C',str(repo),'show',HEAD+':'+name]))==want,name
   if name in bound:assert bound[name]==want
   bound[name]=want
 assert sha(files['egl/qualification.json'])==e['qualification_sha256']
 assert sha(files['suffix/host.json'])==p['host_sha256']
 assert sha(files['suffix/fixtures.h'])==p['fixture_sha256']==h['fixtures_sha256']
 abi={}
 for name,machine in [('arm64-v8a',183),('x86_64',62)]:
  er=q['android'][name];sr=p['builds'][name];raw=files['egl/'+er['binary']];suffix=files['suffix/'+name+'/coh_initial_suffix_test']
  assert sha(raw)==er['binary_sha256'] and sha(suffix)==sr['binary_sha256']
  assert read('suffix/'+name+'/build.json')==sr
  assert er['built'] is True and er['executed'] is False and sr['built'] is True and sr['executed'] is False
  for payload in [raw,suffix]:assert payload[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',payload,18)[0]==machine
  abi[name]={'elf_machine':machine,'egl_sha256':sha(raw),'suffix_sha256':sha(suffix),'built':True,'executed':name=='x86_64'}
 assert set(q['host'])=={'release','address','undefined','finite-fixture'}
 for mode,value in q['host'].items():
  assert value['native']['passed'] is True and value['native']['checks']==183
  assert sha(files['egl/host-'+mode])==value['binary_sha256']
  assert sha(files['egl/'+mode+'.rgba'])==PACKET==value['packet_sha256']
 assert q['pillow']['pillow_all_mips_equal'] is True
 assert e['passed'] is e['android_executed'] is e['device_cleanup_verified'] is e['post_admission_verified'] is True
 n=e['native'];assert n==read('egl-execution/adb-12.stdout')
 assert n['checks']==183 and n['contexts_created']==n['contexts_destroyed']==2 and n['surfaces_created']==n['surfaces_destroyed']==3 and n['readbacks']==27 and n['levels_per_upload']==9 and n['cleanup_verified'] is True
 assert files['egl-execution/adb-08.stdout'].split()[0].decode()==q['android']['x86_64']['binary_sha256']
 assert files['egl-execution/adb-10.stdout'].split()[0].decode()==q['fixture_sha256']
 assert files['suffix-execution/6.log'].split()[0].decode()==p['builds']['x86_64']['binary_sha256']
 assert files['egl-execution/adb-01.stdout'].strip()==b'33' and files['egl-execution/adb-02.stdout'].strip()==b'x86_64'
 assert n['platform']=='android' and 'SwiftShader' in n['gl_renderer']
 assert len(files['egl-execution/readback.rgba'])==1048572 and sha(files['egl-execution/readback.rgba'])==PACKET==e['readback_sha256']
 assert e['platform_library_files_before']==e['platform_library_files_after'] and e['platform_loaded_mapping_verified'] is False
 assert files['egl-execution/adb-19.stdout']==files['egl-execution/adb-20.stdout']==b''
 assert s['passed'] is s['artifact_admitted'] is s['android_executed'] is s['temporary_files_removed'] is True
 assert s['observed']==h['checks']['release']==h['checks']['asan']==h['checks']['ubsan']==read('suffix-execution/9.log')
 assert s['observed']['checks']==9991 and s['observed']['scratch_acquires']==s['observed']['scratch_releases']==2390
 assert [files['suffix-execution/'+str(i)+'.log'].strip() for i in [1,2,3]]==[b'33',b'x86_64',b'1']
 assert files['suffix-execution/11.log']==files['suffix-execution/12.log']==b''
 assert s['observed_platform_zlib_file']['before_sha256']==s['observed_platform_zlib_file']['after_sha256']==e['platform_library_files_before']['/system/lib64/libz.so']
 for key in ['whole_initial_update_complete','actor_publication','acknowledgments_enabled','live_server','physical_thor','external_dependency_stack_and_sanitizer_closure']:assert s[key] is False
 for key in ['material_authority','world_authority']:assert e[key] is n[key] is False
 return {'schema':'coh-independent-actual-android-review-v1','passed':True,'run_id':38998532705,'artifact_id':12088426347,'artifact_sha256':ZIP_SHA,'artifact_bytes':2948433,'source_commit':HEAD,'source_tree':q['source_tree'],'bound_source_inputs':len(bound),'both_abis':abi,'egl_native':n,'egl_packet_sha256':PACKET,'suffix_native':s['observed'],'android_sdk':33,'device_abi':'x86_64','cleanup_verified':True,'platform_library_file_observations':e['platform_library_files_before'],'loaded_mapping_verified':False,'transitive_system_dependency_sanitizer_stack_closure':False,'physical_thor':False,'whole_initial_update_complete':False,'material_authority':False,'world_authority':False,'actor_publication':False,'ack_permitted':False,'file_sha256':{name:sha(data) for name,data in sorted(files.items())}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();proof=verify(a.archive,a.repo);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k not in ['file_sha256','egl_native','suffix_native']}))
