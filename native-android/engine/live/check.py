#!/usr/bin/env python3
"""Qualify the opt-in integrated owner; no real account/session claim."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kwargs):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,**kwargs)
 if r.returncode:raise RuntimeError(repr(cmd)+'\n'+r.stdout+r.stderr)
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--sanitize',action='store_true');p.add_argument('--ndk',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 native=a.source_root.resolve()/'native-android'
 relative=['engine/login/coh_login.c','engine/dbclient/coh_dbclient.c','engine/dbclient/coh_db_session.c','engine/mapclient/coh_mapclient.c','engine/replication/coh_replication.c','engine/replication/coh_groups.c','engine/network/coh_net.c','engine/network/coh_net_frame.c','engine/network/coh_net_zip.c','engine/network/coh_net_udp.c','engine/session/coh_session_crypto.c','engine/auth/coh_auth.c','engine/auth/coh_auth_openssl.c','protocol/coh_protocol.c','src/coh_blowfish.c']
 dependencies=[native/path for path in relative]
 with tempfile.TemporaryDirectory(prefix='coh-live-owner-') as tmp:
  d=Path(tmp);flags=['-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-I'+str(native/'include')]
  if a.sanitize:flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  result={}
  for name,extra,sources in [('owner_contract',['-DCOH_LIVE_CONTRACT_TEST'],[HERE/'test_live.c',*dependencies]),('actual_tcp_boundary',[],[HERE/'coh_live.c',HERE/'test_live.c',*dependencies])]:
   binary=d/name;run(['cc',*flags,*extra,*sources,'-lcrypto','-lz','-lm','-o',binary]);result[name]=json.loads(run([binary],env=env,timeout=30).stdout)
  android={'built':False,'executed':False}
  if a.ndk:
   cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang';obj=d/'coh_live.o';run([cc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-I'+str(native/'include'),'-c',HERE/'coh_live.c','-o',obj]);android={'built':True,'kind':'owner object only; cross-module Android linkage belongs to aggregate qualification','abi':'arm64-v8a','api':26,'executed':False,'sha256':sha(obj)}
  proof={'schema':'coh-native-integrated-owner-v1','passed':True,**result,'android':android,'sanitizers':'ASan+UBSan; LeakSanitizer disabled' if a.sanitize else 'not requested','source_sha256':{str(path.relative_to(native)):sha(path) for path in [*dependencies,HERE/'coh_live.c',HERE/'coh_live.h',HERE/'test_live.c',HERE/'check.py']},'full_scripted_auth_db_map_socket_chain':False,'real_authenticated_server_session':False,'native_live_world':False,'physical_thor_accepted':False,'credentials_logged':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
