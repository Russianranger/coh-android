#!/usr/bin/env python3
"""Focused original costume/reward prefix with explicit opaque nested leaves."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kw)
 if p.returncode:raise RuntimeError(repr(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def bitlist(raw,a,b):return[(raw[i//8]>>(i%8))&1 for i in range(a,b)]
def packbytes(bits):
 raw=bytearray((len(bits)+7)//8)
 for i,v in enumerate(bits):raw[i//8]|=v<<(i%8)
 return raw
class Writer:
 def __init__(self,mode,start=0):self.mode=mode;self.bits=[i&1 for i in range(start)]
 def scalar(self,n,v):
  n=(n+7)&~7 if self.mode else n;self.bits +=[(v>>i)&1 for i in range(n)]
 def pack(self,n,v):
  if self.mode:self.scalar(32,v);return
  while n<32 and v>=(1<<n)-1:self.scalar(n,(1<<n)-1);v-=(1<<n)-1;n=min(32,n*2)
  self.scalar(n,v)
SHIM=r'''
#define INLINEDBG
#define CONFUSED_COSTUMES 0
#define MAX_COSTUMES 10
#define ENTTYPE(e) ((e)->type)
typedef struct {unsigned fixture;} Costume;
typedef struct {const char*reward;} RewardToken;
typedef struct {int pendingCostumeForceTime,current_costume,num_costume_slots,num_costumes_stored,supergroup_mode,hide_supergroup_emblem,npc_costume;Costume*costume[16];RewardToken**rewardTokens,**ArchitectRewardTokens;char costumeFxSpecial[260];} Player;
typedef struct {struct {const char*name;}*type;} SeqInst;
typedef struct {int type,npcIndex,costumeIndex,send_all_costume,supergroup_id;Player*pl;Costume*ownedCostume;SeqInst*seq;void*customNPC_costume;const char*costumeWorldGroup;} Entity;
static RewardToken*groups[2][257];static unsigned group_counts[2];
static int fixture_ea_size(void*p){if(p==groups[0])return group_counts[0];assert(p==groups[1]);return group_counts[1];}
#define eaSize(p) fixture_ea_size(*(p))
static int costume_isReward(const char*s){return *s=='R';}
static void*costume_HashTable;
static unsigned observed_boundary,observed_kind,watch_variant;
static void observe(Packet*p,unsigned kind){if(observed_boundary==UINT32_MAX){observed_boundary=bsGetCursorBitPosition(&p->stream);observed_kind=kind;}}
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){if(watch_variant==3&&n==12)observe(p,3);bsWriteBitsPack(&p->stream,n,v);}
static void pktSendString(Packet*p,const char*s){if(watch_variant==4)observe(p,4);bsWriteString(&p->stream,s?s:"");}
/* These nested serializers are deliberately OPAQUE witnesses. No indexed
 * string/costume bytes, source dictionary or resource generation are proved. */
static void pktSendIndexedString(Packet*p,const char*s,void*t){(void)s;(void)t;observe(p,1);pktSendBits(p,32,0xc0deface);}
static void costume_send(Packet*p,Costume*c,int names){(void)c;(void)names;observe(p,2);pktSendBits(p,32,0xb0d1b0d1);}
static void NPCcostume_send(Packet*p,void*c){(void)c;assert(0);(void)p;}
static Costume*costume_current(Entity*e){return e->pl->costume[e->pl->current_costume];}
static Costume*costume_makeSupergroup(Entity*e){return e->pl->costume[0];}
static int timerSecondsSince2000(void){return 10;}
'''
WRAPPER=r'''
void costume_prefix_original(unsigned aligned,unsigned prefix,const U32*c,U8*out,U32*bits,U32*begin,U32*boundary,U32*kind){
 assert(aligned<=1&&prefix<8&&(!aligned||!prefix)&&c[2]<=257&&c[3]<=257);
 U32 memory[16384]={0};Packet p={0};Entity e={0};Player pl={0};Costume bodies[16]={{0}};RewardToken tokens[2][257];
 struct {const char*name;} st={"OpaqueSequence"};SeqInst seq={(void*)&st};
 for(unsigned i=0;i<16;i++)pl.costume[i]=bodies+i;
 for(unsigned g=0;g<2;g++){group_counts[g]=c[2+g];for(unsigned i=0;i<group_counts[g];i++){tokens[g][i].reward=c[4]==g&&c[5]==i?"Reward":"Filtered";groups[g][i]=&tokens[g][i];}}
 pl.rewardTokens=groups[0];pl.ArchitectRewardTokens=groups[1];pl.current_costume=c[6];pl.num_costume_slots=c[7];pl.num_costumes_stored=c[9];pl.pendingCostumeForceTime=c[10]?20:0;
 e.type=c[0]==2?ENTTYPE_CRITTER:c[0]==3?ENTTYPE_NPC:c[0]==4?ENTTYPE_MISSION_ITEM:ENTTYPE_PLAYER;e.pl=c[0]<=1?&pl:NULL;e.ownedCostume=c[0]==2?bodies:NULL;e.send_all_costume=c[8];e.seq=&seq;e.npcIndex=123;e.costumeIndex=2;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=aligned;*begin=bsGetCursorBitPosition(&p.stream);
 observed_boundary=UINT32_MAX;observed_kind=0;watch_variant=c[0];entSendCostume(&p,&e,c[1]?&e:NULL,c[0]!=0);watch_variant=0;
 if(observed_boundary==UINT32_MAX)observed_boundary=bsGetCursorBitPosition(&p.stream);
 assert(!p.stream.errorFlags);*bits=p.stream.bitLength;*boundary=observed_boundary;*kind=observed_kind;memcpy(out,memory,(*bits+7)/8);
}
'''
def oracle(root,work):
 e=root/'native-android/engine/entities';helper=module('costume_prefix_extract',e/'check.py');bits=module('costume_prefix_bits',root/'native-android/tools/protocol_fixture/prepare.py');pins=json.loads((e/'source-pins.json').read_text())['sha256_lf']
 names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','MapServer/src/entity/entsend.c','Common/entity/costume.c','Common/comm_game.h','Common/entity/entity_enum.h','Common/entity/entPlayer.h'];texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in names}
 if any(sha(texts[p].encode())!=pins[p]for p in names):raise ValueError('original costume prefix source changed')
 code=bits.PREAMBLE;bit=texts[names[0]]
 code+=''.join(helper.extract(bit,n)for n in('initBitStream','bsWriteBits','bsWriteBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'))
 comm=texts['Common/comm_game.h'];at=comm.index('typedef enum',comm.index('// Used by entsend and entrecv.'));code+=comm[at:comm.index('} AppearanceType;',at)+len('} AppearanceType;')]+'\n'+texts['Common/entity/entity_enum.h']+SHIM
 code+=''.join(helper.extract(texts[names[1]],n)for n in('pktSendIfSetBitsPack','pktSendIfSetString'))
 code+=helper.extract(texts['Common/entity/costume.c'],'ent_SendCostumeRewards')+helper.extract(texts['MapServer/src/entity/entsend.c'],'entSendCostume')+WRAPPER
 src=work/'original.c';src.write_text(code);lib=work/'original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),src,'-o',lib]);dll=C.CDLL(str(lib));dll.costume_prefix_original.argtypes=[C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
 return dll,{'original_source_sha256_lf':{p:pins[p]for p in names},'whole_functions':{n:sha(helper.extract(texts[p],n).encode())for p,n in[('MapServer/src/entity/entsend.c','entSendCostume'),('Common/entity/costume.c','ent_SendCostumeRewards')]},'generated_oracle_sha256':sha(code.encode()),'shim_sha256':sha(SHIM.encode()),'wrapper_sha256':sha(WRAPPER.encode()),'nested_costume_and_indexed_string_serializers_opaque':True,'original_consumer_executed':False,'oracle_sanitized':False}
def retained_netfx(root):
 d=HERE/'qualification/initial-netfx-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('retained NetFX header changed')
 for p,h in host['source_sha256'].items():
  if sha((root/p).read_bytes())!=h:raise ValueError('retained NetFX source changed: '+p)
 raw=bytes(map(int,re.search(r'coh_netfx_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));constants={n:int(v)for n,v in re.findall(r'#define COH_NETFX_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']or constants['NETFX_END']!=proof['netfx_end_bit']:raise ValueError('retained NetFX boundaries changed')
 return raw,constants,{'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'host_sha256':sha((d/'host.json').read_bytes()),'accepted_prefix_end':constants['NETFX_END'],'old_suites_reexecuted':False}
def configurations():
 # type,self,group0,group1,presentgroup,presentindex,current,additional,multiple,bodies,deferred
 cfg=[[1,1,0,0,99,0,0,0,0,1,0],[1,1,2,3,99,0,1,3,1,2,1],[1,1,2,3,0,0,0,0,0,1,0],[1,1,2,3,1,2,0,0,0,1,0],[1,0,0,0,99,0,0,0,0,1,1],[2,0,0,0,99,0,0,0,0,1,0],[3,0,0,0,99,0,0,0,0,1,0],[4,0,0,0,99,0,0,0,0,1,0],[0,1,0,0,99,0,0,0,0,1,0],[1,1,256,256,99,0,0,255,0,1,0],[1,1,257,0,99,0,0,0,0,1,0],[1,1,0,257,99,0,0,0,0,1,0],[1,1,0,0,99,0,9,255,1,10,0],[1,1,0,0,99,0,10,0,0,1,0],[1,1,0,0,99,0,0,0,1,0,0],[1,1,0,0,99,0,0,0,1,11,0],[1,1,0,0,99,0,2,0,1,2,0]]
 cfg[0][8]=1;cfg[9][8]=1
 cfg.append([1,1,0,0,99,0,0,0,0,1,0]) # noninitial single-self profile
 return cfg
def model(mode,start,c,create):
 w=Writer(mode,start);type_,self_,n0,n1,pgroup,pindex,current,additional,multiple,count,deferred=c;w.scalar(1,bool(type_))
 if type_:w.pack(2,type_)
 selector=len(w.bits);d=[type_,int(1<=type_<=4),0,0,0,0,0,0,0,0,0,0];stage=3;status=2;bound=False
 def done(s=2,st=None,b=False):return w.bits,d,s,stage if st is None else st,selector if d[1]else 0,len(w.bits)if b else 0
 if not 1<=type_<=4:return done()
 if type_ in(3,4):return done(st=12 if type_==3 else 13,b=True)
 if type_==2:d[10]=1;d[11]=1;return done(st=11,b=True)
 w.scalar(1,self_);d[2]=1
 if self_!=create:return done(7,4)
 d[3]=1
 if self_:
  for g,n in enumerate((n0,n1)):
   d[4]=g+1;d[5]=0;w.scalar(32,n);d[6+g]=n
   if n>256:return done(4,5)
   for j in range(n):
    d[5]=j;present=pgroup==g and pindex==j;w.scalar(1,present)
    if present:return done(st=10,b=True)
    d[8+g]+=1
 w.scalar(1,deferred)
 if self_:
  w.scalar(8,current);w.scalar(8,additional)
  if current>=10:return done(4,7)
 w.scalar(1,multiple if self_ else 0)
 if self_ and not multiple:return done(2,8)
 d[10]=1
 if self_ and multiple:
  w.scalar(4,count);d[10]=count
  if not count or count>10 or current>=count:return done(4,9)
 d[11]=1;return done(st=11,b=True)
def fixtures(lib,work,retained,output):
 rows=[];manifest=[];comparisons=0;cfgs=configurations()
 def append(mode,start,scenario,variant=0,prefix=None):
  nonlocal comparisons
  c=cfgs[scenario];create=c[1]if variant not in(2,3)else 1-c[1]
  prefix_bits,d,status,stage,selector,end=model(mode,start,c,create);stop=len(prefix_bits)
  raw=(C.c_ubyte*65536)();length=C.c_uint();begin=C.c_uint();boundary=C.c_uint();kind=C.c_uint();lib.costume_prefix_original(mode,0 if mode else start,(C.c_uint*len(c))(*c),raw,C.byref(length),C.byref(begin),C.byref(boundary),C.byref(kind));source=[i&1 for i in range(start)]+bitlist(raw,begin.value,length.value)
  if source[:stop]!=prefix_bits:raise ValueError('whole original costume prefix differs from independent projection: '+str((mode,start,scenario,variant)))
  if end and boundary.value+start-begin.value!=end:raise ValueError('nested callsite receipt differs from prefix end')
  comparisons+=1;bits=source
  if variant==1:bits=bits[:stop];status=1
  if variant>=4:
   # Rounded-byte corruptions and unsupported numeric controls are synthetic.
   if variant==4:at=start;value=2;stage=2;d=[0]*12;selector=end=0
   elif variant==5:at=selector;value=2;stage=4;d[2]=d[3]=0;d[4:]=[0]*8;end=0
   elif variant==6:at=selector+8+64;value=2;stage=7;d[10]=d[11]=0;end=0
   elif variant==7:at=selector+8+64+8+16;value=2;stage=8;d[10]=d[11]=0;end=0
   elif variant==8:at=selector+8+32;value=2;stage=6;d[4]=1;d[5]=0;d[6]=2;d[7]=d[8]=d[9]=d[10]=d[11]=0;end=0
   elif variant==9:
    w=Writer(mode,start);w.scalar(1,1);w.pack(2,5);bits=w.bits+[0]*32;stop=len(w.bits);d=[5]+[0]*11;status=2;stage=3;selector=end=0;at=None
   elif variant==10:
    w=Writer(mode,start);w.scalar(1,1);w.pack(2,1);w.scalar(1,0);w.scalar(1,0);w.scalar(1,1);bits=w.bits+[0]*32;stop=len(w.bits);d=[1,1,1,1,0,0,0,0,0,0,0,0];status=1;stage=8;selector=(start+40 if mode else start+3);end=0;at=None
   if variant not in(9,10):bits[at:at+8]=[(value>>i)&1 for i in range(8)];stop=at+8;status=1
  if prefix is not None:
   delta=len(prefix)-start;bits=prefix+bits[start:];start+=delta;stop+=delta;selector+=delta;end+=delta
  raw=packbytes(bits);row=(len(raw),len(bits),mode,variant,scenario,start,stop,status,stage,create,*d,selector,end);rows.append((row,raw));manifest.append({'mode':mode,'start':start,'scenario':scenario,'variant':variant,'sha256':sha(raw)})
  return row,raw
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(len(cfgs)):append(mode,start,scenario)
  for scenario in(0,2,3,4,5,6,7):append(mode,0,scenario,1)
  append(mode,0,0,2);append(mode,0,4,3);append(mode,0,0,9);append(mode,0,4,10)
  if mode:
   for variant,scenario in((4,0),(5,0),(6,0),(7,0),(8,2)):append(mode,0,scenario,variant)
 raw,const,_=retained;prefix=bitlist(raw,0,const['NETFX_END']);row,jni=append(0,const['NETFX_END']%8,0,prefix=prefix)
 proof={'payload_bits':row[1],'payload_sha256':sha(jni),'prefix_end_bit':row[6],'device_packet':False,'framing_only':True,**{n.lower()+'_bit':const[n]for n in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END','AI_END','NETFX_END')}}
 if output:
  header='/* SOURCE-GENERATED FIXTURE: retained NetFX prefix plus original costume/reward framing and OPAQUE nested costume witness. No real dictionary or device packet. */\nstatic const unsigned char coh_costume_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_COSTUME_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in[('BITS',row[1])]+[(n,const[n])for n in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END','AI_END','NETFX_END')]+[('PREFIX_END',row[6])]);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,raw in rows:f.write(struct.pack('<24I',*row));f.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'source_prefix_comparisons':comparisons,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'source_reward_counts':[0,2,3,256,257],'native_reward_limit':256,'packed_offsets':list(range(8)),'compressed_offsets':[0,8],'nested_body_or_dictionary_produced':False},proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retained=retained_netfx(root);sources=[HERE/'coh_initial_costume_probe.c',root/'native-android/engine/replication/coh_replication.c'];providers=[Path(__file__),HERE/'test_initial_costume_probe.c',HERE/'coh_initial_costume_probe.h',root/'native-android/engine/entities/check.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-netfx-20261019/host.json',HERE/'qualification/initial-netfx-20261019/jni-fixture.h'];inputs=set(sources+providers)
 original_names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','MapServer/src/entity/entsend.c','Common/entity/costume.c','Common/comm_game.h','Common/entity/entity_enum.h','Common/entity/entPlayer.h'];inputs.update(root/'upstream/ouroboros'/n for n in original_names)
 for source in sources+[HERE/'test_initial_costume_probe.c']:
  deps=run(['cc','-std=c99','-MM',source]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={path.resolve():path.read_bytes()for path in inputs}
 def verify():
  if any(path.read_bytes()!=raw for path,raw in frozen.items()):raise ValueError('source changed during focused qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-costume-prefix-')as temp:
  work=Path(temp);lib,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,work,retained,a.fixture_output)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_costume_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('qualification modes differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if 'coh_initial_costume_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(v['bound']not in('static','dynamic,bounded')for v in stack):raise ValueError('unbounded prefix stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-costume-prefix-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())if'upstream/ouroboros'not in str(path)},'original_prefix_producers':original,'retained_netfx_prefix':retained[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Whole original costume and reward framing executes with synthetic engine objects and opaque nested indexed-string/costume adapters; only bounded prefix compared. Original nested bodies, dictionaries, consumer, complete record and server transaction are not qualified.','old_suites_reexecuted':False,'physical_device_executed':False,'dictionary_captured':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
