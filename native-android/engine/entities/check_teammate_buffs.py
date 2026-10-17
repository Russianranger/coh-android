#!/usr/bin/env python3
"""Complete original very-rare suffix functions; standalone bounded wire staging."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FILES=['MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c','MapServer/src/entity/character_net_server.c','Game/src/entity/character_net_client.c','Common/entity/character_net.c','libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','Common/comm_game.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def run(command,**kw):
 p=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(repr(command)+'\n'+p.stdout+p.stderr)
 return p.stdout

def source(name):
 p=ROOT/'upstream/ouroboros'/name
 return (p.read_bytes() if p.is_file() else subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:upstream/ouroboros/'+name])).decode().replace('\r\n','\n')
def extract(text,name):
 m=re.search(r'^[^\n{};]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError('missing original function '+name)
 at=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def oracle(directory):
 texts={p:source(p) for p in FILES};pins={p:sha(s.encode()) for p,s in texts.items()}
 if pins!=json.loads((HERE/'teammate-buffs-source-pins.json').read_text())['sha256_lf']:raise ValueError('Original source changed')
 spec=importlib.util.spec_from_file_location('buff_bits',ROOT/'native-android/tools/protocol_fixture/prepare.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',helper.PREAMBLE)
 code+='\n#define AINRANGE(i,a) ((i)>=0&&(unsigned)(i)<sizeof(a)/sizeof((a)[0]))\n'
 functions={}
 def get(path,name):
  body=extract(texts[path],name);functions[name]={'source':path,'sha256_lf':sha(body.encode())};return body
 code+=''.join(get(FILES[5],n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition'])
 code+="""
static void pktSendBits(Packet *p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet *p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet *p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet *p,int n){return bsReadBitsPack(&p->stream,n);}
static int auto_bins[]={2,10,24,32}; static int g_bAssertOnBitStreamError;
"""
 code+=''.join(get(FILES[6],n) for n in ['pktSendBitsAuto','pktGetBitsAuto'])
 enum=re.search(r'typedef enum BuffSettings\s*\{.*?\}BuffSettings;',texts[FILES[7]],re.S).group(0)
 code+=(HERE/'buffs_oracle_shim.h').read_text().replace('BUFF_SETTINGS_FROM_SOURCE',enum)
 names=[(4,'basepower_Send'),(4,'basepower_Receive'),(2,'character_SendBuffs'),(3,'character_ReceiveBuffs'),(0,'appendTeammatePacket'),(1,'entReceiveBuffs')]
 code+=''.join(get(FILES[i],n) for i,n in names)
 code+=(HERE/'buffs_fixture.c.inc').read_text()
 path=directory/'buffs-original.c';path.write_text(code);binary=directory/'buffs-original.so'
 run([os.environ.get('CC','cc'),'-std=c99','-O0','-fPIC','-shared','-w','-I'+str(ROOT/'native-android/include'),path,'-lm','-Wl,-z,defs','-o',binary])
 library=C.CDLL(str(binary));library.buffs_original.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p,C.POINTER(C.c_uint32)]
 return library,{'source_sha256_lf':pins,'functions':functions,'generated_oracle_sha256':sha(code.encode()),'whole_functions_executed':[n for i,n in names],'oracle_sanitized':False,'scope':'Original complete standalone producer/consumer functions with explicit synthetic entity, stash, dictionary and UI shells. No enclosing entity or live packet.'}
def fixtures(library,directory):
 lines=[];rows=[];count=0
 def emit(name,data,kind='unsigned char'):
  lines.append('static const '+kind+' '+name+'[]={'+','.join(map(str,data or [0]))+'};\n')
 for aligned in (0,1):
  for prefix in (range(8) if not aligned else (0,8)):
   for scenario in range(28):
    data=(C.c_uint8*1048576)();bits=C.c_uint32();start=C.c_uint32();normal=(C.c_uint32*32768)();stale=(C.c_uint32*32768)();nc=C.c_uint32();sc=C.c_uint32()
    library.buffs_original(scenario,aligned,prefix,data,C.byref(bits),C.byref(start),normal,C.byref(nc),stale,C.byref(sc))
    name='buffs_packet_'+str(count);emit(name,list(data[:(bits.value+7)//8]));emit(name+'_normal',list(normal[:nc.value]),'uint32_t');emit(name+'_stale',list(stale[:sc.value]),'uint32_t')
    status='COH_LIMIT' if scenario in (15,17,18) else 'COH_OK'
    rows.append('{%s,sizeof(%s),%d,%d,%d,%d,%s,%s_normal,%d,%s_stale,%d}'%(name,name,bits.value,start.value,aligned,scenario,status,name,nc.value,name,sc.value));count+=1
 lines.append('static const BuffFixture buffs_fixtures[]={'+',\n'.join(rows)+'};\n')
 path=directory/'buffs_fixtures.h';path.write_text(''.join(lines))
 return {'fixtures':count,'sha256':sha(path.read_bytes())}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=ROOT);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if a.source_root.resolve()!=ROOT:ap.error('--source-root must identify this checker checkout')
 if bool(a.ndk)!=bool(a.android_output):ap.error('--ndk and --android-output required together')
 if a.output.exists():ap.error('New output path required')
 revision=run(['git','-C',ROOT,'rev-parse','HEAD']).strip();tree=run(['git','-C',ROOT,'rev-parse','HEAD^{tree}']).strip();clean=not run(['git','-C',ROOT,'status','--porcelain']).strip()
 sources=[HERE/'coh_teammate_buffs.c',HERE/'../replication/coh_replication.c',HERE/'test_teammate_buffs.c']
 paths=[*sources,HERE/'coh_teammate_buffs.h',HERE/'buffs_oracle_shim.h',HERE/'buffs_fixture.c.inc',HERE/'teammate-buffs-source-pins.json',HERE/'check_teammate_buffs.py',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py']
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
 original_before={p:sha(source(p).encode()) for p in FILES}
 with tempfile.TemporaryDirectory(prefix='coh-teammate-buffs-') as tmp:
  work=Path(tmp);library,original=oracle(work);fixture=fixtures(library,work)
  if a.fixtures_output:a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'buffs_fixtures.h',a.fixtures_output)
  checks={};binaries={};android={};cpp_link=False;stack=[]
  common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE),'-I'+str(work)]
  if not a.prepare_only:
   modes=[('release',['-O2','-fstack-usage'])]
   if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
   env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
   for mode,flags in modes:
    binary=work/mode;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',binary]);checks[mode]=json.loads(run([binary],env=env));binaries[mode]=sha(binary.read_bytes())
   if any(v!=checks['release'] for v in checks.values()):raise ValueError('Qualification modes disagree')
   cpp=work/'link.cpp';cpp.write_text('#include "coh_teammate_buffs.h"\nint main(){return coh_ent_teammate_buffs(nullptr,nullptr,nullptr,0,1)==COH_INVALID?0:1;}\n')
   objects=[]
   for i,path in enumerate(sources[:2]):
    obj=work/(str(i)+'.o');run([os.environ.get('CC','cc'),*common,'-O2','-c',path,'-o',obj]);objects.append(obj)
   run([os.environ.get('CXX','c++'),'-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);run([work/'cpp-link']);cpp_link=True
   for path in work.glob('*.su'):
    for line in path.read_text().splitlines():
     if '/coh_teammate_buffs.c:' in line:
      location,size,bound=line.split('\t');stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
   if not stack or any(row['bound']!='static' for row in stack):raise ValueError('Missing bounded production stack evidence')
   if sum(row['bytes'] for row in stack)>4096:raise ValueError('Named stack reserve insufficient')
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'buffs_fixtures.h',a.android_output/'buffs_fixtures.h')
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);binary=dest/'coh_teammate_buffs_test'
    run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,*common,'-O2',*sources,'-lm','-o',binary]);r={'built':True,'executed':False,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':fixture['sha256'],'source_sha256':hashes};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths} or original_before!={p:sha(source(p).encode()) for p in FILES} or run(['git','-C',ROOT,'rev-parse','HEAD']).strip()!=revision:raise ValueError('Source changed during qualification')
  result={'schema':'coh-teammate-buffs-qualification-v1','passed':True,'prepare_only':a.prepare_only,'source_revision':revision,'source_tree':tree,'source_worktree_clean':clean,'source_unchanged_before_after':True,'source_sha256':hashes,'original':original,'fixtures':fixture,'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'cpp_link_passed':cpp_link,'android':android,'full_update_complete':False,'stale_state_application_qualified':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False,'real_server_interoperability':False,'thor_accepted':False,'leak_sanitizer':False}
  a.output.parent.mkdir(parents=True,exist_ok=True)
  with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
  print(json.dumps({'passed':True,'fixtures':fixture,'checks':checks,'android_built':list(android),'prepare_only':a.prepare_only}))
if __name__=='__main__':main()
