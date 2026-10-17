#!/usr/bin/env python3
"""Pinned original pre-character statement blocks, not whole character functions."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
import check_teammate_buffs as common
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PATHS=['MapServer/src/entity/entserver.c','Game/src/entity/entrecv.c','Common/auth/auth.h','Common/entity/entPlayer.h','libs/UtilitiesLib/src/components/BitStream.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);args=ap.parse_args()
 if bool(args.ndk)!=bool(args.android_output):ap.error('--ndk and --android-output required together')
 if args.output.exists():ap.error('new output required')
 if args.fixtures_output and args.fixtures_output.exists():ap.error('new fixtures output path required')
 if args.fixtures_output and args.fixtures_output.resolve()==args.output.resolve():ap.error('fixture and receipt paths must differ')
 if args.android_output and args.android_output.exists():ap.error('new Android output directory required')
 if args.android_output and args.fixtures_output and (args.fixtures_output.resolve()==args.android_output.resolve() or args.android_output.resolve() in args.fixtures_output.resolve().parents):ap.error('explicit fixtures output must be outside Android output directory; Android output already includes prefix_fixtures.h')
 if args.ndk:
  toolchain=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'
  android_compilers=[('arm64-v8a',toolchain/'aarch64-linux-android26-clang'),('x86_64',toolchain/'x86_64-linux-android26-clang')]
  if any(not path.is_file() for _,path in android_compilers):ap.error('NDK must provide both Linux ARM64 and x86_64 API 26 compiler drivers')
 revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 tree=common.run(['git','-C',ROOT,'rev-parse','HEAD^{tree}']).strip()
 production=[HERE/n for n in ['coh_character_prefix.c','coh_character_prefix.h','test_character_prefix.c','check_character_prefix.py','character-prefix-source-pins.json']]+[HERE/'../replication/coh_replication.c',HERE/'../replication/coh_replication.h',HERE/'check_teammate_buffs.py',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py',HERE/'run_wire_android.py',HERE/'test_run_wire_android.py',HERE/'../continuation/run_adapter_android.py',HERE/'../scenecatalog-qualification/common.py']
 production_pins={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in production}
 texts={p:common.source(p) for p in PATHS};pins={p:sha(s.encode()) for p,s in texts.items()}
 if pins!=json.loads((HERE/'character-prefix-source-pins.json').read_text()):raise ValueError('original source changed')
 if not re.search(r'#define\s+AUTH_BYTES\s+128\b',texts[PATHS[2]]) or not re.search(r'U32\s+auth_user_data\s*\[AUTH_DWORDS\]' ,texts[PATHS[3]]):raise ValueError('auth array contract changed')
 send=common.extract(texts[PATHS[0]],'sendCharacterToClient');send=send[send.index('    pktSendBitsPack'):send.index('    character_Send(')]
 recv=common.extract(texts[PATHS[1]],'receiveCharacterFromServer');recv=recv[recv.index('    START_BIT_COUNT'):recv.index('        game_state.skin = UISKIN')]
 spec=importlib.util.spec_from_file_location('bits',ROOT/'native-android/tools/protocol_fixture/prepare.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 code=helper.PREAMBLE
 code+=''.join(common.extract(texts[PATHS[4]],n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsWriteBitsArray','bsReadBitsArray','bsGetCursorBitPosition'])
 code+='''
#define STATIC_INFUNC_ASSERT(x)
#define START_BIT_COUNT(p,n)
#define STOP_BIT_COUNT(p)
#define kPlayerType_Count 2
#define kPlayerSubType_Count 4
#define kPraetorianProgress_Count 8
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet*p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet*p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendBitsArray(Packet*p,int n,const void*v){bsWriteBitsArray(&p->stream,n,v);}
static void pktGetBitsArray(Packet*p,int n,void*v){bsReadBitsArray(&p->stream,n,v);}
typedef struct{U32 enableBoostDiminishing,enablePowerDiminishing,no_base_edit,beta_base,base_raid;int skin;} State;
static State server_state,game_state;
static U32 RaidIsRunning(void){return server_state.base_raid;}
typedef struct{U32 auth_user_data[32];U32 playerType,playerSubType,praetorianProgress;} Player;
typedef struct{U32 playerTypeByLocation;} Character;
typedef struct{Player*pl;Character*pchar;} Entity;
static void original_send(Packet*pak,Entity*e){
'''+send+'}\nstatic void original_receive(Packet*pak,Entity*e){int old_skin;\n'+recv+'''}
void fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*words,U8*auth){
 U32 memory[4096]={0};Packet p={0};Player pl={0},decoded={0};Character ch={0},dc={0};Entity e={&pl,&ch},d={&decoded,&dc};
 U32 values[]={0,1,2,3,7,15,16,254,255,256,65535,65536,0x7fffffff,0xffffffff};
 server_state=(State){values[scenario%14],values[(scenario+1)%14],values[(scenario+2)%14],values[(scenario+3)%14],values[(scenario+4)%14],0};
 pl.playerType=scenario%2;pl.playerSubType=scenario%4;pl.praetorianProgress=scenario%8;ch.playerTypeByLocation=(scenario/2)%2;
 for(int i=0;i<128;i++)((U8*)pl.auth_user_data)[i]=(i*37+scenario)&255;
 initBitStream(&p.stream,memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;
 if(prefix)bsWriteBits(&p.stream,prefix,0);original_send(&p,&e);
 *bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;original_receive(&p,&d);
 *end=p.stream.cursor.byte*8+p.stream.cursor.bit;
 words[0]=game_state.enableBoostDiminishing;words[1]=game_state.enablePowerDiminishing;words[2]=game_state.no_base_edit;words[3]=game_state.beta_base;words[4]=game_state.base_raid;words[5]=decoded.playerType;words[6]=decoded.playerSubType;words[7]=decoded.praetorianProgress;words[8]=dc.playerTypeByLocation;memcpy(auth,decoded.auth_user_data,128);
}
'''
 with tempfile.TemporaryDirectory(prefix='coh-character-prefix-') as tmp:
  work=Path(tmp);(work/'oracle.c').write_text(code)
  common.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),work/'oracle.c','-o',work/'oracle.so'])
  lib=C.CDLL(str(work/'oracle.so'));lib.fixture.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p,C.c_void_p];lines=[];rows=[]
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(28):
     data=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();words=(C.c_uint32*9)();auth=(C.c_uint8*128)()
     lib.fixture(scenario,aligned,prefix,data,C.byref(bits),C.byref(end),words,auth)
     if end.value!=bits.value:raise ValueError('original producer/consumer cursor mismatch')
     index=len(rows);name='prefix_'+str(index)
     lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data[:(bits.value+7)//8]))+'};')
     rows.append('{'+name+','+str(bits.value)+','+str(prefix)+','+str(aligned)+',{'+','.join(map(str,words))+'},{'+','.join(map(str,auth))+'}}')
  fixture='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n';(work/'prefix_fixtures.h').write_text(fixture)
  if args.fixtures_output:
   args.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'prefix_fixtures.h',args.fixtures_output)
  wire_controls=json.loads(common.run(['python3',HERE/'test_run_wire_android.py']))
  if wire_controls.get('passed') is not True:raise ValueError('wire runner controls failed')
  checks={};binary_sha={};stack=[];android={}
  for mode,flags in [('release',['-O2','-fstack-usage']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),HERE/'coh_character_prefix.c',HERE/'../replication/coh_replication.c',HERE/'test_character_prefix.c','-lm','-o',binary]);checks[mode]=json.loads(common.run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binary_sha[mode]=sha(binary.read_bytes())
  for path in work.glob('*.su'):
   stack.extend(line for line in path.read_text().splitlines() if 'coh_character_prefix.c:' in line)
  cpp=work/'link.cpp';cpp.write_text('#include \"coh_character_prefix.h\"\nint main(){return coh_character_prefix(nullptr,nullptr)==COH_INVALID?0:1;}\n')
  objects=[]
  for i,path in enumerate([HERE/'coh_character_prefix.c',HERE/'../replication/coh_replication.c']):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if any(v!=checks['release'] for v in checks.values()):raise ValueError('modes disagree')
  if args.ndk:
   args.android_output.mkdir(parents=True);shutil.copy2(work/'prefix_fixtures.h',args.android_output/'prefix_fixtures.h')
   for abi,compiler in android_compilers:
    dest=args.android_output/abi;dest.mkdir();binary=dest/'coh_character_prefix_test'
    common.run([compiler,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),HERE/'coh_character_prefix.c',HERE/'../replication/coh_replication.c',HERE/'test_character_prefix.c','-lm','-o',binary])
    receipt={'built':True,'executed':False,'abi':abi,'api_level':26,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':sha(fixture.encode()),'source_revision':revision,'source_tree':tree,'expected_native_result':checks['release'],'source_sha256':production_pins,'original_source_sha256_lf':pins,'thor_accepted':False,'whole_character_complete':False,'actor_publication':False,'acknowledgments_enabled':False}
    (dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android[abi]=receipt
  if production_pins!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in production} or pins!={p:sha(common.source(p).encode()) for p in PATHS} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source changed during qualification')
  result={'wire_runner_host_controls':wire_controls,'source_unchanged_before_after':True,'production_source_sha256':production_pins,'passed':True,'schema':'coh-character-prefix-v1','source_revision':revision,'source_tree':tree,'source_sha256_lf':pins,'original_statement_blocks_sha256_lf':{'send':sha(send.encode()),'receive':sha(recv.encode())},'original_generated_oracle_sha256':sha(code.encode()),'fixture_sha256':sha(fixture.encode()),'checks':checks,'binary_sha256':binary_sha,'production_stack':stack,'cpp_link_passed':True,'original_oracle_sanitized':False,'scope':'exact pre-character original statement blocks with synthetic state; bit and byte-array writer/readers are original full functions','android':android,'android_built':list(android),'android_executed':False,'thor_accepted':False,'whole_character_complete':False,'actor_publication':False,'acknowledgments_enabled':False}
  args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'android_built':list(android)}))
if __name__=='__main__':main()
