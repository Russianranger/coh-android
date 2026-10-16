#!/usr/bin/env python3
"""Original GROUPS producer bytes plus unchanged local-owner diagnostic capture.

No real server/account is started. UDP peer and character identity are synthetic.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, selectors, shutil, subprocess, tempfile
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
 return p.stdout

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=REPO);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output',type=Path,required=True);ap.add_argument('--build-output',type=Path);ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if a.android_output and not a.ndk:ap.error('--android-output requires --ndk')
 repo=a.source_root.resolve();native=repo/'native-android';checks={};peer_checks={}
 revision=run(['git','-C',repo,'rev-parse','HEAD']).strip();tree=run(['git','-C',repo,'rev-parse','HEAD^{tree}']).strip()
 clean_before=not run(['git','-C',repo,'status','--porcelain']).strip()
 relative=['engine/local/coh_local.c','engine/dbclient/coh_dbclient.c','engine/dbclient/coh_db_session.c','engine/mapclient/coh_mapclient.c','engine/replication/coh_replication.c','engine/replication/coh_groups.c','engine/network/coh_net.c','engine/network/coh_net_frame.c','engine/network/coh_net_zip.c','engine/network/coh_net_udp.c','engine/auth/coh_auth.c','protocol/coh_protocol.c','src/coh_blowfish.c']
 crypto=[native/'engine/auth/coh_auth_openssl.c',native/'engine/session/coh_session_crypto.c']
 sources=[native/f for f in relative]
 owned=[p for p in HERE.iterdir() if p.suffix in ['.c','.h','.py','.md']]
 headers=sorted({native/'engine/coh_contracts.h',*(native/'include').glob('*.h'),*[h for p in [*sources,*crypto] for h in p.parent.glob('*.h')]})
 implementation_paths=[*owned,*sources,*crypto,*headers,native/'engine/local/test_ui_peer.c']
 implementation_sha256={str(p.relative_to(native)):sha(p) for p in implementation_paths}
 with tempfile.TemporaryDirectory(prefix='coh-world-capture-') as tmp:
  d=Path(tmp);g=load(native/'engine/replication/groups_oracle.py','capture_original_groups');gdir=d/'original';gdir.mkdir();fixtures,groups=g.produce_fixtures(repo,gdir)
  lines=['typedef struct {const unsigned char *data;size_t bytes;uint32_t bits,legacy,aligned,admit,files,roots,defs_crc,refs_crc;} CaptureFixture;']
  for i,f in enumerate(fixtures):lines.append('static const unsigned char fixture%d[]={%s};'%(i,','.join(str(v) for v in bytes.fromhex(f['payload_hex']))))
  lines.append('static const CaptureFixture capture_fixtures[]={')
  for i,f in enumerate(fixtures):
   e=f['expected'];admit=f['expected_status']==0 and e.get('new_world')==1
   values=[f['payload_bytes'],f['payload_bits'],f['legacy_commands'],int(f['representation']=='byte_aligned'),int(admit),e.get('footer_file_count',0),e.get('footer_active_roots',0),e.get('footer_defs_crc',0),e.get('footer_refs_crc',0)]
   lines.append('{fixture%d,%s},'%(i,','.join(str(v)+'u' for v in values)))
  lines.append('};');(d/'capture_fixtures.h').write_text('\n'.join(lines)+'\n')
  db=load(native/'engine/dbclient/check.py','capture_original_db')
  maps=load(native/'engine/mapclient/check.py','capture_original_map')
  # Older accepted oracle helpers require physical source paths. Stage exact git
  # blobs in a disposable mirror without expanding/modifying this worktree.
  replication=load(native/'engine/replication/check.py','capture_replication_sources')
  mirror=d/'source-mirror';mirror.mkdir();(mirror/'native-android').symlink_to(native,target_is_directory=True)
  for name in sorted(set(replication.FILES+db.FILES+maps.FILES)):
   rel='upstream/ouroboros/'+name;target=mirror/rel;target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(subprocess.check_output(['git','show','HEAD:'+rel],cwd=repo))
  oracle,dbpins=db.oracle(mirror,d);db.fixtures(oracle,d)
  maps.command_fixtures(mirror,d);maps.groups_fixtures(repo,d)
  flags=['-std=c11','-Wall','-Wextra','-Werror','-I'+str(native/'include'),'-I'+str(d)]
  modes=[('release',['-O2'])]
  if a.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  large=next(f for f in fixtures if f['name']=='large_world_byte_aligned');expected=large['expected']
  probe_build=None
  for label,options in modes:
   objects=[]
   for i,source in enumerate(sources):
    obj=d/(label+str(i)+'.o');extra=['-O0'] if source.name in ['coh_protocol.c','coh_blowfish.c'] else []
    run(['cc',*flags,*options,*extra,'-c',source,'-o',obj]);objects.append(obj)
   exe=d/(label+'-unit');run(['cc',*flags,*options,HERE/'coh_world_capture.c',HERE/'test_capture.c',*objects,'-lz','-lm','-o',exe]);checks[label]=json.loads(run([exe],env=env))
   peer=d/(label+'-peer');probe=d/(label+'-probe')
   run(['cc',*flags,*options,native/'engine/local/test_ui_peer.c',*objects,'-lz','-lm','-o',peer])
   run(['cc',*flags,*options,HERE/'coh_world_capture.c',HERE/'capture_hooks.c',HERE/'probe.c',*crypto,*objects,'-Wl,--wrap=coh_net_udp_create,--wrap=coh_net_udp_queue,--wrap=coh_net_udp_next_owned','-lz','-lm','-lcrypto','-o',probe])
   cases={}
   for case in ['success','wrong_footer','wrong_character','wrong_endpoint','wrong_map','existing_output']:
    report=d/(label+'-'+case+'-peer.json');packet=d/(label+'-'+case+'.groups')
    if case=='existing_output':packet.write_bytes(b'preserved')
    process=subprocess.Popen([str(peer),'--serve','--report',str(report)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
     with selectors.DefaultSelector() as selector:
      selector.register(process.stdout,selectors.EVENT_READ)
      if not selector.select(timeout=10):raise TimeoutError('Scripted peer readiness')
      ready=json.loads(process.stdout.readline())
     mapport=ready['map_port'] if case!='wrong_endpoint' else (ready['map_port']%65535+1)
     args=[ready['db_port'],mapport,0,721,6 if case=='wrong_map' else 5,1,1,expected['footer_file_count'],expected['footer_active_roots'],expected['footer_defs_crc']^(case=='wrong_footer'),expected['footer_refs_crc'],10000,1048577,*[str(i)*64 for i in range(1,6)],packet]
     result=subprocess.run([str(probe),*map(str,args)],input='Fixture\n'+('Wrong Character' if case=='wrong_character' else 'Native Fixture')+'\n',capture_output=True,text=True,env=env,timeout=15)
     if result.returncode not in [0,1]:raise RuntimeError(result.stdout+result.stderr)
     receipt=json.loads(result.stdout)
     if receipt['captured']!=(case=='success') or bool(result.returncode)!=(case!='success'):raise ValueError(case+' capture result '+str(receipt))
     if case=='success':
      if packet.read_bytes()!=bytes.fromhex(large['payload_hex']) or packet.stat().st_mode&0o777!=0o600:raise ValueError('capture byte/mode mismatch')
      for key,value in {'payload_bits':large['payload_bits'],'payload_bytes':large['payload_bytes'],'map_commands':3,'groups_seen':1,'blocked_commands':0,'blocked_endpoints':0,'opened_sockets':2,'closed_sockets':2,'character_identity_verified':False,'wire_selected_dbid':0,'world_ready':False}.items():
       if receipt[key]!=value:raise ValueError(key+' receipt mismatch')
      receipt['payload_sha256']=sha(packet)
     elif case=='existing_output':
      if packet.read_bytes()!=b'preserved':raise ValueError('preexisting output overwritten')
     elif packet.exists():raise ValueError('failed capture published bytes')
     if 'Fixture' in result.stdout+result.stderr:raise ValueError('private name logged')
     cases[case]=receipt
    finally:
     process.terminate();out,error=process.communicate(timeout=5)
     if process.returncode:raise RuntimeError('peer failed '+out+error)
    peer_receipt=json.loads(report.read_text())
    if peer_receipt['closed_sockets']!=2 or peer_receipt['failed']:raise ValueError('peer cleanup failure')
    cases[case]['scripted_peer']=peer_receipt
   peer_checks[label]=cases
   if label=='release' and a.build_output:
    a.build_output.mkdir(parents=True,exist_ok=True);target=a.build_output/'coh-world-capture-probe';shutil.copy2(probe,target);probe_build={'file':target.name,'sha256':sha(target),'host_built':True,'real_server_executed':False}
  android={'arm64_built':False,'executed':False,'scope':'core staging test only; host probe uses OpenSSL provider'}
  if a.ndk:
   artifacts=[];outdir=a.android_output or d/'android';outdir.mkdir(parents=True,exist_ok=True)
   for abi,triple in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/triple;target=outdir/('coh-world-capture-'+abi)
    core=[HERE/'coh_world_capture.c',HERE/'test_capture.c',native/'engine/replication/coh_replication.c',native/'engine/replication/coh_groups.c',native/'protocol/coh_protocol.c',native/'src/coh_blowfish.c']
    run([cc,*flags,'-O2',*core,'-lz','-lm','-o',target]);artifacts.append({'abi':abi,'file':target.name,'sha256':sha(target),'built':True,'executed':False})
   android.update(arm64_built=True,artifacts=artifacts)
   if a.android_output:shutil.copy2(d/'capture_fixtures.h',outdir/'capture_fixtures.h')
  if implementation_sha256!={str(p.relative_to(native)):sha(p) for p in implementation_paths}:raise ValueError('source changed during qualification')
  proof={'schema':1,'passed':True,'source_revision':revision,'source_tree':tree,'source_worktree_clean_before':clean_before,'source_worktree_clean_after':not run(['git','-C',repo,'status','--porcelain']).strip(),'source_kind':'unchanged original GROUPS producer fixture + synthetic UDP peer','checks':checks,'scripted_peer_checks':peer_checks,'groups_oracle':groups,'db_source_sha256_lf':dbpins,'fixtures_sha256':sha(d/'capture_fixtures.h'),'implementation_sha256':implementation_sha256,'source_unchanged_during_qualification':True,'probe_build':probe_build,'android':android,'authentic_server_capture':False,'selected_dbid_verified':False,'actor_identity_verified':False,'full_update_ack_enabled':False,'native_live_world':False,'physical_thor_accepted':False,'leak_sanitizer_enabled':False,'leak_sanitizer_limitation':'Executor compatibility; explicit complete socket cleanup checked.'}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'peer_cases':list(peer_checks),'android':android}))
if __name__=='__main__':main()
