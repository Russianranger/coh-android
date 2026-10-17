#!/usr/bin/env python3
"""Read-only admission of exact recorded native-core build/Android artifacts."""
import argparse,hashlib,io,json,struct,subprocess,zipfile
from pathlib import Path,PurePosixPath
PIN='187c9358bdf198f3d00f22576e140572210b4461'
ARCHIVES={'host':(24786279,'4aa61816f36327f0b73f6e2f62e34abed506fff82d473c23561b340e3703cd68'),'android':(3293,'1bc7d295eea04090f6f893545aa7d8d5448a5b1be9bdbbcbe7cf74b328cf2f78')}
def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,why):
 if not ok:raise ValueError(why)
def archive(path,role):
 raw=path.read_bytes();require((len(raw),sha(raw))==ARCHIVES[role],'exact '+role+' archive')
 z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist();require(len(set(names))==len(names) and z.testzip()is None,'unique ZIP domain and CRC')
 for m in z.infolist():
  n=PurePosixPath(m.filename);require(not n.is_absolute()and'..'not in n.parts and'\\'not in m.filename and(m.external_attr>>16)&0o170000!=0o120000,'ZIP path/type')
 return z

def verify(root,hostpath,androidpath):
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
 return dict(passed=True,run=39009842094,source_revision=PIN,archives=ARCHIVES,manifest_sha256=android['manifest_sha256'],source_sha256_checked=checked,actual_binaries=binaries,actual_android_sdk=33,actual_android_abi='x86_64',suite_results={n:v['result']for n,v in android['suites'].items()},actual_arm64_build=True,actual_x86_64_build=True,owned_temp_removal_command_completed=True,device_temp_absence_separately_verified=False,native_socket_cleanup_checks=True,binaries_reexecuted=False,compiler_reexecuted=False,accepted_apks_rebuilt=False,real_server_accepted=False,live_world=False,physical_thor_accepted=False,later_owned_map_bridge_qualified=False,later_owned_local_qualified=False)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--host-zip',type=Path,required=True);p.add_argument('--android-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=verify(a.source_root,a.host_zip,a.android_zip);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'source_files':len(result['source_sha256_checked']),'binaries':len(result['actual_binaries']),'suites':len(result['suite_results'])}))
