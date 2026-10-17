#!/usr/bin/env python3
"""Complete pinned original power-range producer/consumer, bounded raw staging."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shutil,tempfile
from pathlib import Path
import check_teammate_buffs as common
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
FILES=['Common/entity/PowerInfo.c','Common/entity/character_net.c','libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);args=ap.parse_args()
 if bool(args.ndk)!=bool(args.android_output):ap.error('--ndk and --android-output required together')
 if args.android_output and args.android_output.exists():ap.error('new Android output directory required')
 if args.android_output and args.fixtures_output and (args.fixtures_output.resolve()==args.android_output.resolve() or args.android_output.resolve() in args.fixtures_output.resolve().parents):ap.error('explicit fixture output must be outside Android output; range_fixtures.h is retained there')
 if args.ndk:
  toolchain=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'
  android_compilers=[('arm64-v8a',toolchain/'aarch64-linux-android26-clang'),('x86_64',toolchain/'x86_64-linux-android26-clang')]
  if any(not p.is_file() for _,p in android_compilers):ap.error('both NDK Linux ABI compiler drivers required')
 if args.output.exists() or (args.fixtures_output and args.fixtures_output.exists()):ap.error('new output paths required')
 if args.fixtures_output and args.fixtures_output.resolve()==args.output.resolve():ap.error('fixture/receipt paths must differ')
 revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 tree=common.run(['git','-C',ROOT,'rev-parse','HEAD^{tree}']).strip()
 paths=[HERE/n for n in ['coh_power_ranges.c','coh_power_ranges.h','test_power_ranges.c','check_power_ranges.py','power-ranges-source-pins.json','power_ranges_oracle.c.inc','power_ranges_fixture.c.inc','check_teammate_buffs.py']]+[HERE/'../replication/coh_replication.c',HERE/'../replication/coh_replication.h',HERE/'../character-data/coh_character_data.h',HERE/'../character-data/coh_character_data.c',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py',HERE/'run_wire_android.py',HERE/'test_run_wire_android.py',HERE/'../continuation/run_adapter_android.py',HERE/'../scenecatalog-qualification/common.py']
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
 texts={p:common.source(p) for p in FILES};pins={p:sha(s.encode()) for p,s in texts.items()}
 if pins!=json.loads((HERE/'power-ranges-source-pins.json').read_text()):raise ValueError('source pins changed')
 spec=importlib.util.spec_from_file_location('range_bits',ROOT/'native-android/tools/protocol_fixture/prepare.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',helper.PREAMBLE)
 functions={}
 def get(path,name):
  body=common.extract(texts[path],name);functions[name]={'source':path,'sha256_lf':sha(body.encode())};return body
 code+=''.join(get(FILES[2],n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteF32','bsReadF32'])
 code+='''
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static U32 pktGetBits(Packet*p,int n){return bsReadBits(&p->stream,n);}
static void pktSendF32(Packet*p,float v){bsWriteF32(&p->stream,v);}
static int auto_bins[]={2,10,24,32},g_bAssertOnBitStreamError;
#define AINRANGE(i,a) ((i)>=0&&(unsigned)(i)<sizeof(a)/sizeof((a)[0]))
'''
 code+=''.join(get(FILES[3],n) for n in ['pktSendBitsAuto','pktGetBitsAuto'])
 code+=(HERE/'power_ranges_oracle.c.inc').read_text()
 code+=''.join(get(FILES[1],n) for n in ['basepower_Send','basepower_Receive'])
 code+=''.join(get(FILES[0],n) for n in ['character_SendPowerRanges','character_ReceivePowerRanges'])
 send=common.extract(texts[FILES[0]],'entity_SendPowerInfoUpdate');send=send[send.index('{')+1:send.index('    pktSendBits(pak, 4, e->pchar->iCurBuild)')]
 receive=common.extract(texts[FILES[0]],'entity_ReceivePowerInfoUpdate');receive=receive[receive.index('{')+1:receive.index('    iCurBuild = pktGetBits(pak, 4)')]
 code+='static void original_nochange_send(Entity*e,Packet*pak){'+send+'assert(0);}\n'
 code+='static void original_nochange_receive(Entity*e,Packet*pak){'+receive+'assert(0);}\n'
 code+=(HERE/'power_ranges_fixture.c.inc').read_text()
 with tempfile.TemporaryDirectory(prefix='coh-power-ranges-') as tmp:
  work=Path(tmp);(work/'oracle.c').write_text(code)
  common.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),work/'oracle.c','-o',work/'oracle.so'])
  lib=C.CDLL(str(work/'oracle.so'));lib.fixture.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p,C.POINTER(C.c_uint32)]
  rows=[];lines=[]
  for mode in (0,1):
   for prefix in (range(8) if not mode else (0,8)):
    for outer in (0,1):
     for scenario in range(12):
      if scenario>=10 and prefix:continue
      data=(C.c_uint8*262144)();bits=C.c_uint32();end=C.c_uint32();observed=(C.c_uint32*4096)();count=C.c_uint32()
      lib.fixture(scenario,mode,prefix,outer,data,C.byref(bits),C.byref(end),observed,C.byref(count))
      if bits.value!=end.value:raise ValueError('original producer/consumer disagree')
      name='ranges_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data[:(bits.value+7)//8]))+'};')
      lines.append('static const CohPowerRange '+name+'_expected[]={'+','.join('{%d,%d}'%(observed[2*i],observed[2*i+1]) for i in range(count.value))+'};' if count.value else 'static const CohPowerRange '+name+'_expected[]={{0,0}};')
      rows.append('{'+name+','+str(bits.value)+','+str(prefix)+','+str(mode)+','+str(outer)+','+str(count.value)+','+name+'_expected}')
  fixture='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n';(work/'range_fixtures.h').write_text(fixture)
  if args.fixtures_output:args.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'range_fixtures.h',args.fixtures_output)
  wire_controls=json.loads(common.run(['python3',HERE/'test_run_wire_android.py']))
  if wire_controls.get('passed') is not True:raise ValueError('wire runner controls failed')
  checks={};stack=[];android={}
  sources=[HERE/'coh_power_ranges.c',HERE/'../replication/coh_replication.c',HERE/'test_power_ranges.c']
  for mode,flags in [('release',['-O2','-fstack-usage']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-o',binary]);checks[mode]=json.loads(common.run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  for path in work.glob('*.su'):stack.extend(line for line in path.read_text().splitlines() if '/coh_power_ranges.c:' in line)
  if not stack or any(line.split('\t')[-1]!='static' for line in stack) or sum(int(line.split('\t')[-2]) for line in stack)>4096:raise ValueError('production stack reserve insufficient')
  cpp=work/'link.cpp';cpp.write_text('#include \"coh_power_ranges.h\"\nint main(){return coh_power_ranges(nullptr,nullptr,nullptr,0,1)==COH_INVALID && coh_power_info_no_changes(nullptr,nullptr,nullptr,0,1)==COH_INVALID ? 0:1;}\n')
  objects=[]
  for i,path in enumerate(sources[:2]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if args.ndk:
   args.android_output.mkdir(parents=True);shutil.copy2(work/'range_fixtures.h',args.android_output/'range_fixtures.h')
   for abi,compiler in android_compilers:
    dest=args.android_output/abi;dest.mkdir();binary=dest/'coh_power_ranges_test'
    common.run([compiler,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),*sources,'-lm','-o',binary])
    receipt={'built':True,'executed':False,'abi':abi,'api_level':26,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':sha(fixture.encode()),'source_revision':revision,'source_tree':tree,'expected_native_result':checks['release'],'source_sha256':hashes,'original_sha256_lf':pins,'full_power_info_update':False,'actor_publication':False,'acknowledgments_enabled':False}
    (dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android[abi]=receipt
  if any(v!=checks['release'] for v in checks.values()):raise ValueError('modes disagree')
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in paths} or pins!={p:sha(common.source(p).encode()) for p in FILES} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source changed during qualification')
  result={'wire_runner_host_controls':wire_controls,'passed':True,'schema':'coh-power-range-qualification-v1','source_revision':revision,'source_tree':tree,'source_unchanged_before_after':True,'source_sha256':hashes,'original_sha256_lf':pins,'original_function_sha256':functions,'original_nochange_prefix_sha256_lf':{'producer':sha(send.encode()),'consumer':sha(receive.encode())},'original_generated_oracle_sha256':sha(code.encode()),'fixtures_sha256':sha(fixture.encode()),'checks':checks,'production_stack':stack,'cpp_link_passed':True,'original_oracle_sanitized':False,'source_scope':'whole original range producer/consumer and basepower functions, plus exact unchanged false-branch original PowerInfoUpdate prefixes with synthetic gameplay/dictionary shell','dictionary_authority':False,'full_power_info_update':False,'actor_publication':False,'acknowledgments_enabled':False,'android':android,'android_built':list(android),'android_executed':False,'thor_accepted':False}
  args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()
