#!/usr/bin/env python3
"""Read-only admission of exact recorded native-core build/Android artifacts."""
import argparse,hashlib,io,json,struct,subprocess,zipfile
from pathlib import Path,PurePosixPath
PIN='01cbd938463ea8387d02328ebb477db90870c69b'
ARCHIVES={'host':(25233772,'053dec36b34745abfcb152a308b539291dbc3dd40991d9207c473cdcdfcf9bd1'),'android':(3827,'f75bea1bc0684f4eace3e9d20170747352a3ab47b2bf1db6928078afbdcced19')}
def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,why):
 if not ok:raise ValueError(why)
def archive(path,role):
 raw=path.read_bytes();require((len(raw),sha(raw))==ARCHIVES[role],'exact '+role+' archive')
 z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist();require(len(set(names))==len(names) and z.testzip()is None,'unique ZIP domain and CRC')
 for m in z.infolist():
  n=PurePosixPath(m.filename);require(not n.is_absolute()and'..'not in n.parts and'\\'not in m.filename and(m.external_attr>>16)&0o170000!=0o120000,'ZIP path/type')
 return z

def verify_core(root,hostpath,androidpath):
 h=archive(hostpath,'host');a=archive(androidpath,'android');read=lambda z,n:json.loads(z.read(n));q=read(h,'qualification.json');manifest=read(h,'android-execution-manifest.json');android=read(a,'receipt.json');checked={}
 def source(path,want):
  raw=subprocess.check_output(['git','--no-replace-objects','-C',str(root),'show',PIN+':'+path],timeout=30);require(sha(raw)==want,'source Git binding '+path);checked[path]=want;return raw
 require(q['passed']is True and q['errors']=={} and q['sanitizers_requested']is True and q['clean_source_required']is True,'host successful sanitized scope')
 require(q['source_revision']==q['source_revision_end']==PIN and q['source_revision_changed_during_qualification']is False and not q['source_worktree_dirty']and not q['source_git_status_porcelain']and not q['source_git_status_porcelain_end'],'source stable clean both ends')
 source('native-android/engine/session/qualify_live.py',q['driver_sha256'])
 driver=subprocess.check_output(['git','--no-replace-objects','-C',str(root),'show',PIN+':native-android/engine/session/run_live_android.py']);module={'__name__':'checked_actual_android_contract','__file__':'run_live_android.py'};exec(compile(driver,'run_live_android.py','exec'),module);checked['native-android/engine/session/run_live_android.py']=sha(driver)
 require(sha(h.read('android-execution-manifest.json'))==q['android_manifest_sha256']==android['manifest_sha256'],'host/device manifest association')
 require(android['passed']is True and android['android_executed']is True and android['emulator_qualified']is True and android['device_is_emulator']is True and android['abi']=='x86_64'and android['android_sdk']=='33'and android['android_release']=='13','actual Android13 x86_64 emulator')
 scopes=('accepted_apks_rebuilt','actual_server_interoperability_verified','full_live_world_verified','gates25_27_complete','physical_thor_accepted','real_account_login_verified')
 for key in scopes:require(q[key]is False and android[key]is False,'false acceptance boundary '+key)
 require(android['physical_android_executed']is False,'emulator only')
 suites={'crypto','db_wire','db_session','login','mapclient'};require(set(manifest['suites'])==set(android['suites'])==suites,'five suite domain');binaries=[]
 for name,suite in manifest['suites'].items():
  require(set(suite['abis'])=={'arm64-v8a','x86_64'},'both ABIs '+name)
  for abi,row in suite['abis'].items():
   binary=h.read(row['binary']);receipt_raw=h.read(row['receipt']);receipt=json.loads(receipt_raw)
   require(len(binary)==row['bytes']and sha(binary)==row['sha256']and sha(receipt_raw)==row['receipt_sha256'],'actual binary/receipt '+name+abi)
   require(binary[:6]==b'\x7fELF\x02\x01'and struct.unpack_from('<H',binary,18)[0]=={'arm64-v8a':183,'x86_64':62}[abi],'actual ELF ABI '+name+abi)
   kind=suite['receipt_kind']
   if kind=='crypto':
    require(receipt['status']=='PASS'and receipt['abi']==abi and receipt['artifacts_sha256']['test_auth_android']==row['sha256'],'crypto build receipt')
    mapping=receipt['native_source_sha256']
   elif kind=='module':
    require(receipt['passed']is True and receipt['abi']==abi and receipt['binary_sha256']==row['sha256']and receipt['binary']==PurePosixPath(row['binary']).name,'module build receipt')
    mapping=receipt.get('source_sha256',{})
   else:
    values=[r for r in receipt['artifacts']if r['abi']==abi and r['kind']==suite['artifact_kind']and r['file']==PurePosixPath(row['binary']).name];require(len(values)==1 and values[0]['built']is True and values[0]['sha256']==row['sha256'],'DB build receipt');mapping={}
   for path,want in mapping.items():source('native-android/'+path,want)
   binaries.append(dict(suite=name,abi=abi,bytes=len(binary),sha256=sha(binary),receipt_sha256=sha(receipt_raw)))
  actual=android['suites'][name];row=suite['abis']['x86_64'];require(actual['passed']is True and actual['android_executed']is True and actual['binary_sha256']==row['sha256']and actual['build_receipt_sha256']==row['receipt_sha256'],'executed suite identity')
  require(read(a,name+'.json')==actual,'per-suite result receipt');module['check_result'](name,actual['result'],suite['required'])
 for label,prefix in [('combined_host','engine-host'),('combined_arm64','engine-arm64')]:
  build=q['results'][label];require(read(h,prefix+'/build-receipt.json')==build and build['passed']is True,'combined native build')
  for row in build['sources']:source('native-android/'+row['path'],row['sha256'])
  lib=build['library'];raw=h.read(prefix+'/'+lib['name']);require(len(raw)==lib['bytes']and sha(raw)==lib['sha256'],'actual combined native library')
 require(q['results']['combined_arm64']['android_arm64_bionic_cross_compiled']is True,'ARM64 Bionic built')
 for role,prefix in [('mapclient',''),('live_owner',''),('server_oracle','')]:
  result=q['results'][role]
  for field in ('implementation_sha256','source_sha256','native_sources_sha256'):
   for path,want in result.get(field,{}).items():source('native-android/'+path,want)
  for path,want in result.get('adapter_sources_sha256',{}).items():source('native-android/engine/session/server-oracle/'+path,want)
 db=read(h,'android/dbclient/android-build.json');require(sha(h.read('android/dbclient/fixtures.h'))==db['fixture_sha256']==q['results']['dbclient']['android_fixture_sha256'],'DB generated fixture binding')
 mp=q['results']['mapclient'];require(sha(h.read('android/mapclient/fixtures.h'))==mp['android_fixtures_sha256']and sha(h.read('android/mapclient/groups-fixtures.h'))==mp['groups_fixtures_sha256']and sha(h.read('android/mapclient/server-command-fixtures.h'))==mp['server_command_fixtures_sha256'],'retained Map fixture identities')
 return dict(passed=True,run=39011930318,source_revision=PIN,archives=ARCHIVES,manifest_sha256=android['manifest_sha256'],source_sha256_checked=checked,actual_binaries=binaries,actual_android_sdk=33,actual_android_abi='x86_64',suite_results={n:v['result']for n,v in android['suites'].items()},actual_arm64_build=True,actual_x86_64_build=True,owned_temp_removal_command_completed=True,device_temp_absence_separately_verified=False,native_socket_cleanup_checks=True,binaries_reexecuted=False,compiler_reexecuted=False,accepted_apks_rebuilt=False,real_server_accepted=False,live_world=False,physical_thor_accepted=False,later_owned_map_bridge_qualified=False,later_owned_local_qualified=False)

def verify(root,hostpath,androidpath):
 import tempfile
 result=verify_core(root,hostpath,androidpath)
 h=archive(hostpath,'host');a=archive(androidpath,'android');host_raw=h.read('local-owned/host.json');proof=json.loads(host_raw);actual=json.loads(a.read('owned-local.json'))
 def git(path):return subprocess.check_output(['git','--no-replace-objects','-C',str(root),'show',PIN+':'+path],timeout=30)
 names=subprocess.check_output(['git','--no-replace-objects','-C',str(root),'ls-tree','-r','--name-only','-z',PIN],timeout=30).decode().split('\0')
 domain={n for n in names if n.startswith('native-android/')and Path(n).suffix in('.py','.c','.h','.inc')}
 for relative in ('local/source-pins.json','dbclient/source-pins.json','mapclient/source-pins.json','replication/source-pins.json','replication/groups-source-pins.json'):
  path='native-android/engine/'+relative;domain.add(path)
  for name in json.loads(git(path))['sha256_lf']:domain.add(name if name.startswith(('upstream/','android/'))else'upstream/ouroboros/'+name)
 require(domain==set(proof['source_sha256']),'complete historical Git source domain')
 ordered=sorted(domain);queries=''.join(PIN+':'+p+'\n'for p in ordered).encode();data=subprocess.check_output(['git','--no-replace-objects','-C',str(root),'cat-file','--batch'],input=queries,timeout=60);at=0
 for path in ordered:
  end=data.index(b'\n',at);size=int(data[at:end].split()[-1]);at=end+1;body=data[at:at+size];at+=size+1;require(sha(body)==proof['source_sha256'][path],'historical source Git binding '+path)
 tree=subprocess.check_output(['git','--no-replace-objects','-C',str(root),'rev-parse',PIN+'^{tree}']).decode().strip();require(proof['source_revision']==PIN and proof['source_tree']==tree,'historical source identity')
 identity={key:proof[key]for key in('source_revision','source_tree','source_sha256')}
 # Execute only frozen historical pure admission code. Its identity provider is
 # replaced by the independently reconstructed historical Git domain above.
 # This does not reuse the current working-tree HEAD or execute any binary/adb.
 driver_path='native-android/engine/local/run_owned_android.py';driver=git(driver_path);require(sha(driver)==proof['source_sha256'][driver_path],'local driver Git identity');module={'__name__':'checked_historical_local_admission','__file__':str(root/driver_path)};exec(compile(driver,driver_path,'exec'),module);module['source_identity']=lambda ignored:identity
 build=json.loads(h.read('local-owned/android/android-build.json'))
 with tempfile.TemporaryDirectory(prefix='coh-owned-actual-admission-')as tmp:
  directory=Path(tmp);(directory/'android').mkdir();(directory/'host.json').write_bytes(host_raw);(directory/'android/android-build.json').write_bytes(h.read('local-owned/android/android-build.json'))
  for row in build['artifacts']:(directory/'android'/row['file']).write_bytes(h.read('local-owned/android/'+row['file']))
  binary,expected=module['validate'](directory)
  require(sha(binary.read_bytes())==actual['binary_sha256'],'actual local execution binary')
 for key in('passed','android_executed','cleanup_verified'):require(actual[key]is True,'local actual execution '+key)
 require(actual['validation_only']is False and actual['android_sdk']==33 and actual['abi']=='x86_64','actual Android13 local execution')
 for key in('physical_thor_accepted','real_server','encrypted_authentication','actor_identity','world_authority','apk_rebuilt'):require(actual[key]is False,'local scope '+key)
 require(actual['host_sha256']==sha(host_raw)and actual['result']==expected,'local actual result equals source-bound host')
 fixtures=proof['integrated']['fixture_sha256'];files={'fixtures.h':'android/dbclient/fixtures.h','groups-fixtures.h':'android/mapclient/groups-fixtures.h','server-command-fixtures.h':'android/mapclient/server-command-fixtures.h'}
 for name,path in files.items():require(sha(h.read(path))==fixtures[name],'retained generated fixture '+name)
 binaries=[]
 for row in build['artifacts']+build['scripted_ui_peer_artifacts']:
  raw=h.read('local-owned/android/'+row['file']);require(sha(raw)==row['sha256']and raw[:6]==b'\x7fELF\x02\x01'and struct.unpack_from('<H',raw,18)[0]=={'arm64-v8a':183,'x86_64':62}[row['abi']],'local binary ELF/source receipt '+row['file']);binaries.append({'file':row['file'],'abi':row['abi'],'bytes':len(raw),'sha256':sha(raw)})
 result.update(local_host_sha256=sha(host_raw),local_driver_sha256=sha(driver),local_source_files=len(domain),local_source_tree=tree,local_actual_binaries=binaries,local_fixtures=fixtures,local_result=actual['result'],local_cleanup_verified=True,local_checks_both_abis_fixture_bound=True,later_owned_map_bridge_qualified=True,later_owned_local_qualified=True,new_local_scene_observer_qualified=False)
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--host-zip',type=Path,required=True);p.add_argument('--android-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);v=p.parse_args();r=verify(v.source_root,v.host_zip,v.android_zip);v.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'local_sources':r['local_source_files'],'local_checks':r['local_result']['checks'],'local_cleanup':r['local_cleanup_verified']}))
