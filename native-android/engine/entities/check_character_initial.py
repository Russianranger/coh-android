#!/usr/bin/env python3
"""Composed source first-three character groups; full consumer remains unimplemented."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
import check_teammate_buffs as common
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
EXTRA=['MapServer/src/entity/entserver.c','Game/src/entity/entrecv.c','Common/auth/auth.h','Common/entity/entPlayer.h','Common/entity/gametypes.h','libs/UtilitiesLib/src/utils/structNet.c','libs/UtilitiesLib/src/utils/textparser.c','Common/entity/attrib_net.c']
def oracle(work):
 char=load('character_oracle_composed',HERE/'../character-data/check.py');unused,character=char.oracle(ROOT,work)
 code=(work/'oracle.c').read_text().replace('hasDebugInfo,compress,ordered,ordered_id;', 'hasDebugInfo,compress,ordered,ordered_id,id;');original={p:common.source(p) for p in EXTRA}
 pins={p:sha(s.encode()) for p,s in original.items()}
 if pins!=json.loads((HERE/'character-initial-source-pins.json').read_text()):raise ValueError('original pins differ')
 # Extend explicit fixture owner shells; original function bodies remain exact.
 code=code.replace('typedef struct Entity {int type;Character*pchar;}Entity;', '''typedef struct{U32 auth_user_data[32],playerType,playerSubType,praetorianProgress,pvpSwitch,bIsGanker;char primarySet[256],secondarySet[256];}InitialPlayer;
 typedef struct Entity {int type;Character*pchar,*pcharLast;InitialPlayer*pl;int pvpZoneTimer,pvpClientZoneTimer,pvpUpdateTime;}Entity;''')
 code=code.replace('Entity*entParent;Named*pclass', 'int iAllyID,iGangID,bPvPActive;Entity*entParent;Named*pclass')
 bit=common.source('libs/UtilitiesLib/src/components/BitStream.c')
 code+='\n#define THREADSAFE_STATIC static\n#define THREADSAFE_STATIC_MARK(x)\n'
 code+=''.join(common.extract(bit,n) for n in ['bsWriteBitsArray','bsReadBitsArray','bsReadStringAndLength'])
 code+='''
static void pktSendBitsArray(Packet*p,int n,const void*v){bsWriteBitsArray(&p->stream,n,v);}
static void pktGetBitsArray(Packet*p,int n,void*v){bsReadBitsArray(&p->stream,n,v);}
static char*pktGetString(Packet*p){int n;return bsReadStringAndLength(&p->stream,&n);}
#define STATIC_INFUNC_ASSERT(x)
#define START_BIT_COUNT(p,n)
#define STOP_BIT_COUNT(p)
#define MAX_NAME_LEN 128
'''
 code+=(HERE/'stats_oracle_shim.h').read_text().replace('static int s_inSync,g_bAssertOnBitStreamError;', 'static int s_inSync;')
 structnet=original[EXTRA[5]];textparser=original[EXTRA[6]];schema=original[EXTRA[7]]
 code+=structnet[structnet.index('typedef struct FloatAccuracyTable'):structnet.index('float ParserUnpackFloat')]
 names={}
 def get(text,name):
  body=common.extract(text,name);names[name]=sha(body.encode());return body
 code+=''.join(get(structnet,n) for n in ['ParserUnpackFloat','ParserPackFloat','ParserFloatMinBits'])
 code+=''.join(get(textparser,n) for n in ['int_senddiff','float_senddiff','struct_senddiff','int_recvdiff','float_recvdiff','struct_recvdiff'])
 code+=''.join(get(structnet,n) for n in ['sdPackStruct','ParserSend','sdUnpackStruct','ParserRecv'])
 code+='\n#define Character StatsCharacter\n'+schema[schema.index('TokenizerParseInfo ParseBasicCharacterAttributesLowRes'):schema.index('/* End of File */')]+'\n#undef Character\n'
 sender=common.extract(original[EXTRA[0]],'sendCharacterToClient');send=sender[sender.index('    pktSendBitsPack'):sender.index('    sendTray(')]
 recv=common.extract(original[EXTRA[1]],'receiveCharacterFromServer');account=recv[recv.index('    START_BIT_COUNT'):recv.index('        game_state.skin = UISKIN')]
 post=recv[recv.index('    START_BIT_COUNT(pak, "OriginalPowerSets")'):recv.index('    START_BIT_COUNT(pak, "receiveTray")')]
 code+='''
typedef struct {U32 enableBoostDiminishing,enablePowerDiminishing,no_base_edit,beta_base,base_raid;int skin;} InitialState;
static InitialState server_state,game_state;static StatsCharacter initial_stats,received_stats;
static U32 prefix_end,character_end,stats_begin,names_end;static int RaidIsRunning(void){return server_state.base_raid;}
static int timerCpuTicks(void){return 0;}
static void observed_character_send(Packet*pak,Character*p){prefix_end=bsGetCursorBitPosition(&pak->stream);character_Send(pak,p);character_end=bsGetCursorBitPosition(&pak->stream);}
static void original_stats_send(Packet*pak){stats_begin=bsGetCursorBitPosition(&pak->stream);ParserSend(SendCharacterToSelf,pak,&initial_stats,&initial_stats,true,false,true,0,0);}
#define character_Send observed_character_send
#define sdPackDiff(t,p,a,b,c,d,e,f,g) original_stats_send(p)
static void original_initial_send(Packet*pak,Entity*e){
'''+send+'}\n#undef character_Send\n#undef sdPackDiff\n'
 code+=''.join(get(original[EXTRA[1]],n) for n in ['entReceiveAllyID','entReceivePvP'])
 code+='''
static int observed_ally(Packet*pak,Entity*e,bool stale){names_end=bsGetCursorBitPosition(&pak->stream);return entReceiveAllyID(pak,e,stale);}
#define entReceiveAllyID observed_ally
#define sdUnpackDiff(t,p,c,id,b) assert(ParserRecv(SendCharacterToSelf,p,&received_stats,NULL,true))
static void original_initial_account_receive(Packet*pak,Entity*e){int old_skin;
'''+account+'}\nstatic void original_initial_post_receive(Packet*pak,Entity*e){\n'+post+'''}
#undef sdUnpackDiff
void initial_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*offsets,U32*words,U8*auth,float*stats,int*integers){
 U32 memory[65536]={0};Packet p={0};InitialPlayer pl={0},decoded={0};Character dc={0};Entity d={0};d.pchar=&dc;d.pl=&decoded;
 setup(scenario<6?scenario:1);owner.entity.pl=&pl;owner.ch.playerTypeByLocation=1;
 owner.ch.iAllyID=scenario==8?-1:37;owner.ch.iGangID=scenario==8?-1:71;owner.ch.bPvPActive=scenario%2;
 owner.entity.pvpZoneTimer=scenario==8?-1:65535;pl.pvpSwitch=(scenario/2)%2;pl.bIsGanker=(scenario/3)%2;
 pl.playerType=scenario%2;pl.playerSubType=scenario%4;pl.praetorianProgress=scenario%8;
 strcpy(pl.primarySet,"Unknown_Primary_Set");strcpy(pl.secondarySet,"Unknown_Secondary_Set");
 if(scenario==6||scenario==7){memset(pl.primarySet,'x',scenario==6?127:128);pl.primarySet[scenario==6?127:128]=0;}
 if(scenario==8){owner.class_name.pchName="Unknown_Class";owner.origin_name.pchName="Unknown_Origin";powers_by_crc[2].crcFullName=0xfedcba98;}
 for(unsigned i=0;i<128;i++)((U8*)pl.auth_user_data)[i]=(i*37+scenario)&255;
 server_state=(InitialState){scenario,0xffffffff,16,3,1,0};
 initial_stats=(StatsCharacter){{123.45f,45.5f,91.2f,.753f,300.f,8.75f,-3.3f,.656f},{200.25f,55.5f,100.f,.853f,400.f,9.75f,2.4f,.757f},12,14,123456,-123,1000,7654321};
 stats_ops[1]=(StatsOps){fixture_compare,int_senddiff,int_recvdiff};stats_ops[2]=(StatsOps){fixture_compare,float_senddiff,float_recvdiff};stats_ops[3]=(StatsOps){fixture_compare,struct_senddiff,struct_recvdiff};
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,aligned,0);if(prefix)bsWriteBits(&p.stream,prefix,0);
 original_initial_send(&p,&owner.entity);U32 bits=p.stream.bitLength;memcpy(out,memory,(bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;
 original_initial_account_receive(&p,&d);assert(bsGetCursorBitPosition(&p.stream)==prefix_end);
 /* Original character_Receive/dictionary creation does NOT execute here. The
  * exact complete original character_Send extent is known by construction. */
 p.stream.cursor.byte=character_end/8;p.stream.cursor.bit=character_end%8;
 original_initial_post_receive(&p,&d);assert(bsGetCursorBitPosition(&p.stream)==bits);
 offsets[0]=bits;offsets[1]=prefix_end;offsets[2]=character_end;offsets[3]=stats_begin;offsets[4]=names_end;
 words[0]=game_state.enableBoostDiminishing;words[1]=game_state.enablePowerDiminishing;words[2]=game_state.no_base_edit;words[3]=game_state.beta_base;words[4]=game_state.base_raid;
 words[5]=decoded.playerType;words[6]=decoded.playerSubType;words[7]=decoded.praetorianProgress;words[8]=dc.playerTypeByLocation;
 words[9]=dc.iAllyID;words[10]=dc.iGangID;words[11]=decoded.pvpSwitch;words[12]=dc.bPvPActive;words[13]=d.pvpClientZoneTimer;words[14]=decoded.bIsGanker;
 memcpy(auth,decoded.auth_user_data,128);memcpy(stats,&received_stats.attrCur,16*sizeof(float));memcpy(integers,&received_stats.iLevel,6*sizeof(int));
}
'''
 (work/'initial-oracle.c').write_text(code)
 common.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../character-data'),'-I'+str(ROOT/'native-android/include'),work/'initial-oracle.c','-lm','-Wl,-z,defs','-o',work/'initial-oracle.so'])
 lib=C.CDLL(str(work/'initial-oracle.so'));lib.initial_fixture.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
 return lib,{'character':character,'source_sha256_lf':pins,'functions':names,'sender_block_sha256':sha(send.encode()),'account_receiver_block_sha256':sha(account.encode()),'post_receiver_block_sha256':sha(post.encode()),'generated_oracle_sha256':sha(code.encode()),'whole_sendCharacterToClient_executed':False,'whole_character_Send_executed':True,'whole_character_Receive_executed':False,'consumer_character_extent':'source-produced boundary only; original dictionary/character creation not executed','oracle_sanitized':False}
def fixtures(lib,work):
 lines=[];rows=[]
 for mode in (0,1):
  for prefix in (range(8) if not mode else (0,8)):
   for scenario in range(9):
    data=(C.c_uint8*262144)();offsets=(C.c_uint32*5)();words=(C.c_uint32*15)();auth=(C.c_uint8*128)();stats=(C.c_float*16)();ints=(C.c_int32*6)();lib.initial_fixture(scenario,mode,prefix,data,offsets,words,auth,stats,ints)
    name='initial_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,data[:(offsets[0]+7)//8]))+'};')
    rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,offsets))+','+','.join(map(str,[prefix,mode,scenario]))+',{'+','.join(map(str,words))+'},{'+','.join(map(str,auth))+'},{'+','.join(repr(float(x))+'f' for x in stats)+'},{'+','.join(str(x) for x in ints)+'}}')
 (work/'initial_fixtures.h').write_text('\n'.join(lines)+'\nstatic const InitialFixture initial_fixtures[]={'+',\n'.join(rows)+'};\n')
 return {'count':len(rows),'sha256':sha((work/'initial_fixtures.h').read_bytes())}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);a=ap.parse_args()
 if bool(a.ndk)!=bool(a.android_output):ap.error('both Android paths required')
 if a.output.exists():ap.error('new output path required')
 revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 sources=[HERE/'coh_character_initial.c',HERE/'coh_character_prefix.c',HERE/'../character-data/coh_character_data.c',HERE/'coh_entities.c',HERE/'../replication/coh_replication.c',HERE/'test_character_initial.c']
 inputs=sources+[HERE/n for n in ['coh_character_initial.h','coh_character_prefix.h','coh_entities.h','coh_costume.h','coh_taskforce.h','check_character_initial.py','check_teammate_buffs.py','character-initial-source-pins.json','stats_oracle_shim.h']]+[HERE/'../character-data'/n for n in ['coh_character_data.h','check.py','oracle_shim.h','oracle_fixture.c.inc','source-pins.json']]+[HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py']
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs}
 with tempfile.TemporaryDirectory(prefix='coh-character-initial-') as tmp:
  work=Path(tmp);lib,original=oracle(work);fixture=fixtures(lib,work)
  if a.fixtures_output:a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'initial_fixtures.h',a.fixtures_output)
  checks={};binaries={};stack=[];android={}
  modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else [])
  for mode,flags in modes:
   binary=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-o',binary]);checks[mode]=json.loads(common.run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary.read_bytes())
  stats_calls={'coh_ent_character_stats','character_stats','stats_leaf','pack','read_n','flag','require','signed_bits','check_reader','fail','clear_failure'}
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t');function=location.rsplit(':',1)[-1]
    admitted=any(name+':' in location for name in ['coh_character_initial.c','coh_character_prefix.c','coh_character_data.c']) or ('coh_entities.c:' in location and function in stats_calls) or ('coh_replication.c:' in location and function.split('.')[0] in {'valid','coh_rep_read','coh_rep_pack','coh_rep_string'})
    if admitted:stack.append({'function':function,'bytes':int(size),'bound':bound,'source':location.split(':')[0]})
  if not stack or any(row['bound'] not in {'static','dynamic,bounded'} for row in stack) or sum(row['bytes'] for row in stack)>8192:raise ValueError('Named complete parser stack reserve not justified: '+repr(stack))
  if any(v!=checks['release'] for v in checks.values()):raise ValueError('mode disagreement')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_character_initial.h"\nint main(){return coh_character_initial_read(nullptr,nullptr,0,nullptr,nullptr,0,0,nullptr)==COH_INVALID?0:1;}\n')
  objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if a.ndk:
   a.android_output.mkdir(parents=True,exist_ok=True);shutil.copy2(work/'initial_fixtures.h',a.android_output/'initial_fixtures.h')
   for abi,cc in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
    dest=a.android_output/abi;dest.mkdir(exist_ok=True);binary=dest/'coh_character_initial_test'
    common.run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/cc,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-I'+str(work),*sources,'-lm','-o',binary]);r={'built':True,'executed':False,'binary':binary.name,'binary_sha256':sha(binary.read_bytes()),'fixtures_sha256':fixture['sha256'],'source_sha256':hashes};(dest/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android[abi]=r

  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in inputs} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source changed during qualification')
  result={'schema':'coh-character-initial-prefix-qualification-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'source_stable_before_after':True,'original':original,'fixtures':fixture,'checks':checks,'binary_sha256':binaries,'production_stack_frames':stack,'whole_character_complete':False,'actor_publication':False,'dictionary_authority':False,'acknowledgments_enabled':False,'cpp_link_passed':True,'android':android,'android_built':bool(android),'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'fixtures':fixture}))
if __name__=='__main__':main()
