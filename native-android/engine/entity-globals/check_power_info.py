#!/usr/bin/env python3
"""Complete original PowerInfo producer; bounded raw native staging, no actor."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FILES=['Common/entity/PowerInfo.c','Common/entity/PowerInfo.h','Common/entity/character_net.c',
 'MapServer/src/entity/character_net_server.c','Game/src/entity/character_net_client.c',
 'Common/entity/character_base.h','Common/entity/boost.h','Common/entity/powers.h',
 'Common/entity/RewardItemType.h','libs/UtilitiesLib/src/components/BitStream.c',
 'libs/UtilitiesLib/src/network/net_packetutil.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def run(command,**kw):
 p=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(repr(command)+'\n'+p.stdout+p.stderr)
 return p.stdout
def source(root,name):
 p=root/'upstream/ouroboros'/name
 return (p.read_bytes() if p.is_file() else subprocess.check_output(['git','-C',str(root),'show','HEAD:upstream/ouroboros/'+name])).decode().replace('\r\n','\n')
def extract(text,name):
 m=re.search(r'^(?:static\s+)?[^\n{};]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError('Missing original '+name)
 at=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def oracle(root,directory):
 texts={n:source(root,n) for n in FILES};pins={n:sha(t.encode()) for n,t in texts.items()}
 if pins!=json.loads((HERE/'power-info-source-pins.json').read_text())['sha256_lf']:raise ValueError('Original source pins differ')
 spec=importlib.util.spec_from_file_location('power_bits',root/'native-android/tools/protocol_fixture/prepare.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',helper.PREAMBLE)
 functions={}
 def get(index,name):
  body=extract(texts[FILES[index]],name);functions[name]={'file':FILES[index],'sha256_lf':sha(body.encode())};return body
 code+=''.join(get(9,n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteF32','bsReadF32'])
 code+='''
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet*p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet*p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendF32(Packet*p,float v){bsWriteF32(&p->stream,v);}
static float pktGetF32(Packet*p){return bsReadF32(&p->stream);}
static int auto_bins[]={2,10,24,32},g_bAssertOnBitStreamError;
#define AINRANGE(i,a) ((i)>=0&&(unsigned)(i)<sizeof(a)/sizeof((a)[0]))
'''
 code+=''.join(get(10,n) for n in ['pktSendBitsAuto','pktGetBitsAuto'])
 code+=(HERE/'power_info_oracle_shim.h').read_text()
 code+=''.join(get(2,n) for n in ['basepower_Send','character_SendPowerBoost','boost_Send','powerRef_Send','powerRef_Receive'])
 code+=get(3,'inspiration_Send')
 code+=''.join(get(0,n) for n in ['powerActivation_Send','powerActivation_Receive','powerEnabledStatus_Send','powerEnabledStatus_Receive','powerRechargeTimer_Send','powerRechargeTimer_Receive','character_SendPowerRanges','powerRef_DestroyAdapter','entity_SendPowerInfoUpdate'])
 code+=(HERE/'power_info_fixture.c.inc').read_text()
 p=directory/'oracle.c';p.write_text(code);libpath=directory/'oracle.so'
 run([os.environ.get('CC','cc'),'-std=c99','-O0','-w','-shared','-fPIC','-I'+str(HERE),'-I'+str(root/'native-android/include'),p,'-lm','-Wl,-z,defs','-o',libpath])
 lib=C.CDLL(str(libpath));lib.original_power_info.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.POINTER(C.c_uint32)];lib.original_power_info.restype=C.c_uint64;lib.original_power_components.argtypes=[C.c_uint]
 return lib,{'source_sha256_lf':pins,'functions':functions,'generated_oracle_sha256':sha(code.encode()),'whole_entity_SendPowerInfoUpdate_executed':True,'whole_entity_ReceivePowerInfoUpdate_executed':False,'consumer_scope':'Complete original powerRef/activation/enabled/recharge subconsumers; no whole gameplay update consumer or dictionary application.','oracle_sanitized':False}
def fixtures(lib,directory):
 text=[];rows=[];n=0;comparisons=0
 for aligned in (0,1):
  assert lib.original_power_components(aligned)==1;comparisons+=1
  for scenario in range(7):
   for prefix in (range(8) if not aligned else (0,8)):
    data=(C.c_ubyte*65536)();bits=C.c_uint32();expected=lib.original_power_info(scenario,aligned,prefix,data,C.byref(bits))
    text.append('static const unsigned char wire_%d[]={%s};\n'%(n,','.join(map(str,data[:(bits.value+7)//8]))))
    rows.append('{wire_%d,sizeof(wire_%d),%d,%d,%d,%d,UINT64_C(%d)}'%(n,n,bits.value,aligned,prefix,scenario,expected));n+=1
 text.append('static const Fixture fixtures[]={'+',\n'.join(rows)+'};\n')
 p=directory/'power_info_fixtures.h';p.write_text(''.join(text));return {'count':n,'original_subconsumer_roundtrips':comparisons,'sha256':sha(p.read_bytes())}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-root',type=Path,default=ROOT);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);ap.add_argument('--fixtures-output',type=Path);a=ap.parse_args()
 if bool(a.ndk)!=bool(a.android_output):ap.error('Both Android paths required')
 root=a.source_root.resolve();sources=[HERE/'coh_power_info.c',HERE/'../replication/coh_replication.c',HERE/'test_power_info.c']
 inputs=[*sources,HERE/'coh_power_info.h',HERE/'power_info_oracle_shim.h',HERE/'power_info_fixture.c.inc',HERE/'power-info-source-pins.json',Path(__file__),HERE/'../character-data/coh_character_data.h',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',root/'native-android/tools/protocol_fixture/prepare.py',root/'native-android/include/coh_native_core.h']
 inputs.append(HERE/'../entities/run_character_android.py')
 hashes={str(p.resolve().relative_to(root)):sha(p.read_bytes()) for p in inputs}
 with tempfile.TemporaryDirectory(prefix='coh-power-info-') as tmp:
  d=Path(tmp);lib,original=oracle(root,d);fixture=fixtures(lib,d)
  if a.fixtures_output:a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(d/'power_info_fixtures.h',a.fixtures_output)
  common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE),'-I'+str(d)];checks={};android={}
  modes=[('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else [])
  for mode,flags in modes:
   binary=d/mode;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',binary]);checks[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  run([os.environ.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-x','c++','-c','-o',d/'header.o','-'],input='#include "'+str(HERE/'coh_power_info.h')+'"\nint main(){return 0;}\n')
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(d/'power_info_fixtures.h',a.android_output/'power_info_fixtures.h')
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    p=a.android_output/abi;p.mkdir(exist_ok=True);binary=p/'coh_power_info_test';run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,*common,'-O2',*sources,'-lm','-o',binary]);proof={'built':True,'executed':False,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':{'power_info_fixtures.h':fixture['sha256']},'source_sha256':hashes,'expected':checks['release']};(p/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n');android[abi]=proof
  if any(sha(p.read_bytes())!=hashes[str(p.resolve().relative_to(root))] for p in inputs):raise ValueError('Source changed during qualification')
  if any(v!=checks['release'] for v in checks.values()):raise ValueError('Sanitizer result differs')
  proof={'schema':'coh-power-info-qualification-v1','passed':True,'source_sha256':hashes,'source_unchanged_before_after':True,'original':original,'fixtures':fixture,'checks':checks,'android':android,'cpp_header_passed':True,'leak_sanitizer':False,'dictionary_authority':False,'whole_initial_update':False,'actor_publication':False,'acknowledgments_enabled':False,'live_service_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'fixtures':fixture,'checks':checks,'android_built':list(android)}))
if __name__=='__main__':main()
