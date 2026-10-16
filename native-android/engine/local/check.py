#!/usr/bin/env python3
"""Qualify explicit local DB/Map owner against source-layout UDP peers."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, selectors, subprocess, tempfile
HERE=Path(__file__).resolve().parent
PINNED=['upstream/ouroboros/Game/src/clientcomm/authclient.c',
 'upstream/ouroboros/Game/src/clientcomm/dbclient.c',
 'upstream/ouroboros/DBServer/src/clientcomm.c',
 'upstream/ouroboros/Common/comm_backend.h',
 'upstream/ouroboros/Common/ClientLogin/clientcommLogin.c',
 'upstream/ouroboros/libs/UtilitiesLib/src/network/net_version.c',
 'android/native/client-launcher.c','android/guest/game_diagnostic.py',
 'android/guest/client_login_diagnostic.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalized(p):return hashlib.sha256(p.read_text().replace('\r\n','\n').encode()).hexdigest()
def run(cmd,**kwargs):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=120,**kwargs)
 if r.returncode:raise RuntimeError(repr(cmd)+'\n'+r.stdout+r.stderr)
 return r.stdout

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--sanitize',action='store_true');p.add_argument('--ndk',type=Path);p.add_argument('--android-output',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.android_output and not a.ndk:p.error('--android-output requires --ndk')
 repo=a.source_root.resolve();native=repo/'native-android'
 pins={f:normalized(repo/f) for f in PINNED}
 if pins!=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']:raise ValueError('local login source pin mismatch')
 spec=importlib.util.spec_from_file_location('qualified_db_oracle',native/'engine/dbclient/check.py');db=importlib.util.module_from_spec(spec);spec.loader.exec_module(db)
 relative=['engine/dbclient/coh_dbclient.c','engine/dbclient/coh_db_session.c','engine/mapclient/coh_mapclient.c','engine/replication/coh_replication.c','engine/replication/coh_groups.c','engine/network/coh_net.c','engine/network/coh_net_frame.c','engine/network/coh_net_zip.c','engine/network/coh_net_udp.c','engine/auth/coh_auth.c','protocol/coh_protocol.c','src/coh_blowfish.c']
 sources=[HERE/'coh_local.c',*[native/f for f in relative]]
 with tempfile.TemporaryDirectory(prefix='coh-native-local-') as tmp:
  d=Path(tmp);oracle,_=db.oracle(repo,d);fixtures=db.fixtures(oracle,d)
  spec=importlib.util.spec_from_file_location('qualified_map_commands',native/'engine/mapclient/check.py')
  maps=importlib.util.module_from_spec(spec);spec.loader.exec_module(maps);maps.command_fixtures(repo,d);groups_receipt=maps.groups_fixtures(repo,d)
  flags=['-std=c11','-Wall','-Wextra','-Werror','-I'+str(native/'include'),'-I'+str(d)]
  checks={};peer_checks={};modes=[('release',['-O2'])]
  if a.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  for label,options in modes:
   objects=[]
   for i,source in enumerate(sources):
    obj=d/(label+str(i)+'.o');extra=['-O0'] if source.name in ['coh_protocol.c','coh_blowfish.c'] else []
    run(['cc',*flags,*options,*extra,'-c',source,'-o',obj]);objects.append(obj)
   exe=d/label;run(['cc',*flags,*options,HERE/'test_local.c',*objects,'-lz','-lm','-o',exe]);checks[label]=json.loads(run([exe],env=env))
   peer=d/(label+'-ui-peer');client=d/(label+'-ui-peer-client')
   run(['cc',*flags,*options,HERE/'test_ui_peer.c',*objects,'-lz','-lm','-o',peer])
   run(['cc',*flags,*options,HERE/'test_ui_peer_client.c',*objects,'-lz','-lm','-o',client])
   report=d/(label+'-ui-peer.json')
   process=subprocess.Popen([str(peer),'--serve','--report',str(report)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
   try:
    with selectors.DefaultSelector() as ready_selector:
     ready_selector.register(process.stdout,selectors.EVENT_READ)
     if not ready_selector.select(timeout=10):raise TimeoutError('Scripted UI peer readiness timed out')
     ready=json.loads(process.stdout.readline())
    peer_checks[label]=json.loads(run([client,ready['db_port']],env=env))
   finally:
    process.terminate();out,error=process.communicate(timeout=5)
    if process.returncode:raise RuntimeError('Scripted UI peer failed: '+error+out)
   receipt=json.loads(report.read_text())
   if receipt['closed_sockets']!=2 or receipt['source_command_catalogs']!=1 or receipt['scene_prefixes']!=1 or receipt['failed']:raise ValueError('Scripted UI peer lifecycle/catalog did not complete')
   large=groups_receipt['large_fixture'];expected=large['expected'];decoded=(large['payload_bits']+7)//8
   if receipt['scene_decoded_bytes']!=decoded or not 1440<receipt['scene_compressed_bytes']<16384 or receipt['scene_payload_bits']!=large['payload_bits'] or receipt['scene_compressed'] is not True or receipt['scene_ordered'] is not False or receipt['large_body_fixture'] is not True or receipt['scene_tail_parsed'] is not True or receipt['scene_assets_resolved'] is not False or receipt['scene_crc_verified'] is not False or receipt['decoded_budget_bytes']!=4*1024*1024 or receipt['scene_expected_counts']!=expected:raise ValueError('Scripted complete normal GROUPS fixture did not complete')
   peer_checks[label]['peer']=receipt

  android={'arm64_built':False,'executed':False}
  if a.ndk:
   cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang';lib=d/'libcoh_local.so'
   run([cc,*flags,'-O2','-fPIC','-shared',*sources,'-lz','-lm','-Wl,--no-undefined','-o',lib]);android={'arm64_built':True,'executed':False,'library_sha256':sha(lib)}
   if a.android_output:
    a.android_output.mkdir(parents=True,exist_ok=True);artifacts=[];peer_artifacts=[]
    for abi,triple in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
     cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/triple;exe=a.android_output/('coh-local-'+abi)
     run([cc,*flags,'-O2',*sources,HERE/'test_local.c','-lz','-lm','-o',exe]);artifacts.append({'abi':abi,'file':exe.name,'sha256':sha(exe),'built':True,'executed':False})
     peer=a.android_output/('coh-local-peer-'+abi)
     run([cc,*flags,'-O2',*sources,HERE/'test_ui_peer.c','-lz','-lm','-o',peer])
     peer_artifacts.append({'abi':abi,'file':peer.name,'sha256':sha(peer),'built':True,'executed':False,'role':'scripted-ui-peer','real_server_interoperability':False})

    receipt={'schema':1,'module':'local','artifacts':artifacts,'scripted_ui_peer_artifacts':peer_artifacts,'android_execution_qualified':False,'actual_server_interoperability_verified':False}
    (a.android_output/'android-build.json').write_text(json.dumps(receipt,indent=2)+'\n');android['artifacts']=artifacts;android['scripted_ui_peer_artifacts']=peer_artifacts
  proof={'schema':'coh-native-local-owner-v1','passed':True,'checks':checks,'scripted_ui_peer_checks':peer_checks,'source_files':len(pins),'source_sha256_lf':pins,'source_fixture_count':fixtures,'implementation_sha256':{str(v.relative_to(native)):sha(v) for v in [*sources,HERE/'coh_local.h',HERE/'test_local.c',HERE/'test_ui_peer.c',HERE/'test_ui_peer_client.c',HERE/'check.py',native/'engine/dbclient/coh_db_session.h',native/'engine/dbclient/coh_dbclient.h',native/'engine/dbclient/tests/test_db_session.c',native/'engine/mapclient/coh_mapclient.h']},'android':android,'sanitizers':'ASan+UBSan' if a.sanitize else 'not requested','leak_sanitizer_enabled':False,'leak_sanitizer_limitation':'Executor /proc task-walk compatibility; explicit before/after FD checks remain enabled.','actual_server_interoperability_verified':False,'authserver_authenticated_session':False,'native_live_world':False,'physical_thor_accepted':False,'credentials_logged':False}
  proof['implementation_sha256']['engine/mapclient/tests/large_scene_fixture.h']=sha(native/'engine/mapclient/tests/large_scene_fixture.h')
  proof['implementation_sha256']['engine/replication/coh_groups.h']=sha(native/'engine/replication/coh_groups.h')
  proof['server_command_fixtures_sha256']=sha(d/'server-command-fixtures.h')
  proof['groups_producer_oracle']=groups_receipt;proof['groups_fixtures_sha256']=sha(d/'groups-fixtures.h')
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
