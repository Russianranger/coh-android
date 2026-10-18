#!/usr/bin/env python3
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,subprocess,tempfile
from pathlib import Path
import oracle
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def run(cmd,**kw):
 r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True,**kw)
 if r.returncode:raise RuntimeError(str(cmd)+'\n'+r.stdout+r.stderr)
 return r.stdout

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-db-identity-')as tmp:
  w=Path(tmp);lib,source=oracle.build(ROOT,w);lib.original_db_handoff.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p]
  def fixture(dbid,cookie,profile,route):
   data=(C.c_ubyte*65536)();bits=C.c_uint();words=(C.c_uint*7)();assert lib.original_db_handoff(dbid,cookie,profile,route,data,C.byref(bits),words)==1
   assert list(words)==[dbid,1,0x0100000a if route&2 else 0x0100007f,0x0100000a if route&2 else 0x0100007f,7002,7003,cookie]
   return bytes(data[:(bits.value+7)//8]),bits.value,list(words)
  rows=[];lines=['typedef struct{const unsigned char*data;unsigned bytes,bits,aligned,legacy,words[7];}Fixture;'];cases=[]
  for dbid in(0,1,2,17,4242,0x7fffffff,0x80000000,0xffffffff):
   for cookie in(2,123456,0xffffffff):
    for profile in range(4):
     for route in range(4):
      raw,bits,words=fixture(dbid,cookie,profile,route);n=len(rows);lines.append('static const unsigned char wire_'+str(n)+'[]={'+','.join(map(str,raw))+'};');rows.append('{wire_'+str(n)+',sizeof(wire_'+str(n)+'),'+','.join(map(str,(bits,profile&1,profile>>1)))+',{'+','.join(map(str,words))+'}}');cases.append({'dbid':dbid,'cookie':cookie,'profile':profile,'route':route,'bits':bits,'wire_sha256':oracle.sha(raw),'wire_hex':raw.hex()})
  lines.append('static const Fixture fixtures[]={'+','.join(rows)+'};');full='\n'.join(lines)+'\n';(w/'source_fixtures.h').write_text(full)
  # Existing opaque session/socket suite gets whole actual source MAP_CONNECT
  # bytes in place of earlier synthetic seven-field fixtures. Other accepted
  # parser/source-layout fixtures are reused unchanged.
  db=oracle.module('existing_db_check',HERE/'../dbclient/check.py');base=w/'native-base';base.mkdir();blib,_=db.oracle(ROOT,base);db.fixtures(blib,w);header=(w/'fixtures.h').read_text()
  for label,profile in [('map0',0),('map1',1),('map_old0',2),('map_old1',3)]:
   raw,bits,_=fixture(17,123456,profile,profile&1)
   replacement='static const unsigned char '+label+'[]={'+','.join(map(str,raw))+'};\n#define '+label+'_bits '+str(bits)+'u'
   header,n=re.subn(r'static const unsigned char '+label+r'\[\]=\{[^}]*\};\s*#define '+label+r'_bits \d+u',replacement,header);assert n==1
  for label,dbid in [('identity_zero',0),('identity_high',0x80000000),('identity_one',1),('identity_max',0x7fffffff)]:
   raw,bits,_=fixture(dbid,123456,0,1);header+='static const unsigned char '+label+'[]={'+','.join(map(str,raw))+'};\n#define '+label+'_bits '+str(bits)+'u\n'
  (w/'fixtures.h').write_text(header)
  common=[HERE/'../dbclient/coh_dbclient.c',ROOT/'native-android/protocol/coh_protocol.c',ROOT/'native-android/src/coh_blowfish.c',HERE/'../auth/coh_auth.c'];sessions=[HERE/'../dbclient/coh_db_session.c',HERE/'../dbclient/coh_db_account_controls.c']+[HERE/'../network'/f for f in('coh_net.c','coh_net_frame.c','coh_net_udp.c','coh_net_zip.c')];checks={}
  for mode,options in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   flags=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(w),'-I'+str(ROOT/'native-android/include'),*options];objects=[]
   for path in common[1:]:
    obj=w/(mode+'-'+path.stem+'.o');run(['cc',*flags,'-O0','-c',path,'-o',obj]);objects.append(obj)
   env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');checks[mode]={}
   for label,paths,test in [('wire',[common[0],*objects],HERE/'test_handoff.c'),('owner',[common[0],*objects,*sessions],HERE/'test_identity.c')]:
    binary=w/(mode+'-'+label);run(['cc',*flags,*paths,test,'-lz','-lm','-o',binary]);result=run([binary],env=env);checks[mode][label]=json.loads(result.splitlines()[-1]);checks[mode][label]['binary_sha256']=oracle.sha(binary.read_bytes())
  inputs=list(HERE.glob('*.py'))+list(HERE.glob('*.h'))+list(HERE.glob('*.c'))+[HERE/'source-pins.json',HERE/'CONTRACT.md',HERE/'../dbclient/check.py',HERE/'../dbclient/source-pins.json',ROOT/'native-android/tools/protocol_fixture/prepare.py',HERE/'../costume-tree/tree_oracle.py',*common,*sessions,HERE/'../dbclient/coh_db_session.h',HERE/'../dbclient/tests/test_db_session.c']
  # Capture every non-system compile dependency, including the included
  # original socket regression C file and frozen scalar/crypto headers.
  for path in common+sessions+[HERE/'test_handoff.c',HERE/'test_identity.c']:
   deps=run(['cc','-std=c99','-I'+str(w),'-I'+str(ROOT/'native-android/include'),'-MM',path]).replace('\\\n',' ')
   for name in deps.split(':',1)[1].split():
    dep=Path(name)
    if dep.exists() and not dep.is_relative_to(w):inputs.append(dep)
  inputs=list(dict.fromkeys(inputs))
  receipt={'schema':1,'passed':True,'source_head':run(['git','rev-parse','HEAD'],cwd=ROOT).strip(),'source_oracle':source,'source_sha256':{os.path.relpath(p,HERE):oracle.sha(p.read_bytes())for p in inputs},'whole_producer_queue_cases':len(cases),'source_cases':cases,'source_fixtures_sha256':oracle.sha(full.encode()),'owner_fixtures_sha256':oracle.sha(header.encode()),'native':checks,'scope':{'exact_MAP_CONNECT_opaque_owner_DBID':True,'generic_link_id_reinterpreted':False,'DB_list_contains_DBID':False,'original_host_oracle_sanitized':False,'local_auth_promoted_to_encrypted_auth':False,'complete_entity_actor_or_ACK':False,'real_DB_Map_Auth_run':False,'android_built':False,'Win32_ABI':False,'leak_sanitizer':False}}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'original_cases':len(cases),'native':checks,'output':str(a.output)}))
if __name__=='__main__':main()
