#!/usr/bin/env python3
"""Complete original very-rare suffix functions; standalone bounded wire staging."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FILES=['MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c',
 'MapServer/src/storyarc/storySend.c','Game/src/storyarc/contactClient.c',
 'Game/src/storyarc/contactClient.h','Game/src/UI/uiCompass.h',
 'Common/storyarc/contactCommon.h','Common/entity/teamCommon.h',
 'Common/entity/Supergroup.h','Common/entity/gametypes.h','Game/src/entity/entIncludeClient.h',
 'libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c']
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
 if pins!=json.loads((HERE/'very-rare-tail-source-pins.json').read_text())['sha256_lf']:raise ValueError('Original source changed')
 for text,name,value in [(texts[FILES[7]],'MAX_LEVELINGPACT_MEMBERS',2),(texts[FILES[9]],'MAX_NAME_LEN',128),(texts[FILES[9]],'MAX_ZOWIE_TYPE',8),(texts[FILES[9]],'MAX_ZOWIE_NAME',128)]:
  if not re.search(r'#define\s+'+name+r'\s+'+str(value)+r'\b',text):raise ValueError('Original extent changed '+name)
 if 'typedef char MemberName[64];' not in texts[FILES[7]]:raise ValueError('Original member name changed')
 spec=importlib.util.spec_from_file_location('tail_bits',ROOT/'native-android/tools/protocol_fixture/prepare.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',helper.PREAMBLE)
 code+='\n#define THREADSAFE_STATIC static\n#define THREADSAFE_STATIC_MARK(x)\n#define AINRANGE(i,a) ((i)>=0&&(unsigned)(i)<sizeof(a)/sizeof((a)[0]))\n'
 functions={}
 def get(path,name):
  body=extract(texts[path],name);functions[name]={'source':path,'sha256_lf':sha(body.encode())};return body
 code+=''.join(get(FILES[11],n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString','bsReadStringAndLength'])
 code+='''
static void pktSendBits(Packet *p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet *p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet *p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet *p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendString(Packet *p,const char *s){bsWriteString(&p->stream,s);}
static char *pktGetString(Packet *p){int length;return bsReadStringAndLength(&p->stream,&length);}
static void pktSendF32(Packet *p,float f){U32 u;memcpy(&u,&f,4);pktSendBits(p,32,u);}
static float pktGetF32(Packet *p){U32 u=pktGetBits(p,32);float f;memcpy(&f,&u,4);return f;}
static int auto_bins[]={2,10,24,32};
static int g_bAssertOnBitStreamError;
'''
 code+=''.join(get(FILES[12],n) for n in ['pktSendBitsAuto','pktGetBitsAuto','pktSendIfSetBitsPack','pktGetIfSetBitsPack'])
 code+=(HERE/'tail_oracle_shim.h').read_text()
 code+=get(FILES[2],'TaskStatusSend')+get(FILES[3],'TaskStatusReceive')
 senders=['entSendOtherSupergroupInfo','entSendLevelingpactInfo','entSendLogoutUpdate']
 consumers=['entReceiveOtherSupergroupInfo','entReceiveLevelingpactInfo','entReceiveLogoutUpdate']
 code+=''.join(get(FILES[0],n) for n in senders)+''.join(get(FILES[1],n) for n in consumers)
 sender=extract(texts[FILES[0]],'sendEntity');begin=sender.index('        entSendOtherSupergroupInfo(');end=sender.index('\n    }',begin)
 send_order=sender[begin:end]
 receiver=extract(texts[FILES[1]],'entReceive');begin=receiver.index('            START_BIT_COUNT(pak, "entReceiveOtherSupergroupInfo");');end=receiver.index('\n        }',begin)
 recv_order=receiver[begin:end]
 if [send_order.index(n+'(') for n in senders]!=sorted(send_order.index(n+'(') for n in senders):raise ValueError('Sender order changed')
 if [recv_order.index(n+'(') for n in consumers]!=sorted(recv_order.index(n+'(') for n in consumers):raise ValueError('Receiver order changed')
 code+=(HERE/'tail_fixture.c.inc').read_text()
 path=directory/'tail-original.c';path.write_text(code);binary=directory/'tail-original.so'
 run([os.environ.get('CC','cc'),'-std=c99','-O0','-fPIC','-shared','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),path,'-lm','-Wl,-z,defs','-o',binary])
 library=C.CDLL(str(binary));args=[C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p,C.c_void_p]
 library.tail_original.argtypes=args;library.tail_receiver_only.argtypes=args[1:]
 return library,{'source_sha256_lf':pins,'functions':functions,'generated_oracle_sha256':sha(code.encode()),
  'whole_functions_executed':senders+consumers+['TaskStatusSend','TaskStatusReceive'],
  'sender_order_block_sha256_lf':sha(send_order.encode()),'receiver_order_block_sha256_lf':sha(recv_order.encode()),
  'oracle_sanitized':False,'scope':'Whole named source functions with synthetic object/dictionary/location/UI shells; original enclosing sendEntity/entReceive do not execute.',
  'consumer_projection':'Exact byte serialization of numeric/string receiver state. Fixture dictionary behavior is explicit; not original dictionary/gameplay application.'}
def fixtures(library,directory):
 size=library.tail_observation_size();prior_controls=library.tail_prior_controls();lines=[];rows=[];expected={};count=0
 if size!=196612:raise ValueError('Unexpected observation ABI '+str(size))
 def emit(name,data):lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,data))+'};\n')
 for aligned in (0,1):
  for prefix in (range(8) if not aligned else (0,8)):
   for scenario in range(28):
    data=(C.c_uint8*262144)();bits=C.c_uint32();start=C.c_uint32();normal=(C.c_uint8*size)();stale=(C.c_uint8*size)()
    if scenario==25:library.tail_receiver_only(aligned,prefix,data,C.byref(bits),C.byref(start),normal,stale)
    else:library.tail_original(scenario,aligned,prefix,data,C.byref(bits),C.byref(start),normal,stale)
    for tag,value in [('normal',normal),('stale',stale)]:
     used=int.from_bytes(bytes(value[:4]),'little');raw=bytes(value[4:used+4]);key=str(scenario)+'_'+tag
     if key not in expected:expected[key]=raw;emit('expected_'+key,raw or b'\0')
     elif expected[key]!=raw:raise ValueError('Alignment-dependent original receiver state')
    name='tail_packet_'+str(count);emit(name,bytes(data[:(bits.value+7)//8]))
    status='COH_LIMIT' if scenario in (21,22,23) else ('COH_INVALID' if scenario==24 else 'COH_OK')
    rows.append('{%s,sizeof(%s),%d,%d,%d,%d,%s,expected_%d_normal,sizeof(expected_%d_normal),expected_%d_stale,sizeof(expected_%d_stale)}'%(name,name,bits.value,start.value,aligned,scenario,status,scenario,scenario,scenario,scenario));count+=1
 lines.append('static const TailFixture tail_fixtures[]={'+',\n'.join(rows)+'};\n')
 path=directory/'tail_fixtures.h';path.write_text(''.join(lines))
 return {'producer_fixtures':270,'receiver_only_cached_name_fixtures':10,'supported_fixtures':240,'source_valid_local_limit_refusals':30,'source_malformed_null_recipe_refusals':10,'original_prior_state_controls':prior_controls,'stale_pact_cursor_differences':library.tail_stale_pact_differences(),'observation_bytes':size,'sha256':sha(path.read_bytes())}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=ROOT);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if a.source_root.resolve()!=ROOT:ap.error('--source-root must identify this checker checkout')
 if bool(a.ndk)!=bool(a.android_output):ap.error('--ndk and --android-output required together')
 if a.output.exists():ap.error('New output path required')
 revision=run(['git','-C',ROOT,'rev-parse','HEAD']).strip();tree=run(['git','-C',ROOT,'rev-parse','HEAD^{tree}']).strip();clean=not run(['git','-C',ROOT,'status','--porcelain']).strip()
 sources=[HERE/'coh_very_rare_tail.c',HERE/'../replication/coh_replication.c',HERE/'test_very_rare_tail.c']
 paths=[*sources,HERE/'coh_very_rare_tail.h',HERE/'tail_oracle_shim.h',HERE/'tail_fixture.c.inc',HERE/'tail_observation.h',HERE/'very-rare-tail-source-pins.json',HERE/'check_very_rare_tail.py',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py']
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
 original_before={p:sha(source(p).encode()) for p in FILES}
 with tempfile.TemporaryDirectory(prefix='coh-very-rare-tail-') as tmp:
  work=Path(tmp);library,original=oracle(work);fixture=fixtures(library,work)
  if a.fixtures_output:a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'tail_fixtures.h',a.fixtures_output)
  checks={};binaries={};android={};cpp_link=False;stack=[]
  common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE),'-I'+str(work)]
  if not a.prepare_only:
   modes=[('release',['-O2','-fstack-usage'])]
   if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
   env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
   for mode,flags in modes:
    binary=work/mode;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',binary]);checks[mode]=json.loads(run([binary],env=env));binaries[mode]=sha(binary.read_bytes())
   if any(v!=checks['release'] for v in checks.values()):raise ValueError('Qualification modes disagree')
   cpp=work/'link.cpp';cpp.write_text('#include "coh_very_rare_tail.h"\nint main(){return coh_ent_very_rare_tail(nullptr,nullptr,nullptr,0,1)==COH_INVALID?0:1;}\n')
   objects=[]
   for i,path in enumerate(sources[:2]):
    obj=work/(str(i)+'.o');run([os.environ.get('CC','cc'),*common,'-O2','-c',path,'-o',obj]);objects.append(obj)
   run([os.environ.get('CXX','c++'),'-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);run([work/'cpp-link']);cpp_link=True
   for path in work.glob('*.su'):
    for line in path.read_text().splitlines():
     if '/coh_very_rare_tail.c:' in line:
      location,size,bound=line.split('\t');stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
   if not stack or any(row['bound']!='static' for row in stack):raise ValueError('Missing bounded production stack evidence')
   if sum(row['bytes'] for row in stack)>8192:raise ValueError('Named stack reserve insufficient')
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'tail_fixtures.h',a.android_output/'tail_fixtures.h')
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);binary=dest/'coh_very_rare_tail_test'
    run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,*common,'-O2',*sources,'-lm','-o',binary]);r={'built':True,'executed':False,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':fixture['sha256'],'source_sha256':hashes};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths} or original_before!={p:sha(source(p).encode()) for p in FILES} or run(['git','-C',ROOT,'rev-parse','HEAD']).strip()!=revision:raise ValueError('Source changed during qualification')
  result={'schema':'coh-very-rare-tail-qualification-v1','passed':True,'prepare_only':a.prepare_only,'source_revision':revision,'source_tree':tree,'source_worktree_clean':clean,'source_unchanged_before_after':True,'source_sha256':hashes,'original':original,'fixtures':fixture,'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'cpp_link_passed':cpp_link,'android':android,'full_update_complete':False,'stale_state_application_qualified':False,'dictionary_authority':False,'actor_publication':False,'acknowledgments_enabled':False,'real_server_interoperability':False,'thor_accepted':False,'leak_sanitizer':False}
  a.output.parent.mkdir(parents=True,exist_ok=True)
  with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
  print(json.dumps({'passed':True,'fixtures':fixture,'checks':checks,'android_built':list(android),'prepare_only':a.prepare_only}))
if __name__=='__main__':main()
