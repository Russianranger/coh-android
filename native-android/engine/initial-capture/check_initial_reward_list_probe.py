#!/usr/bin/env python3
"""Bounded two-group reward syntax against whole original source producers."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(repr(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def bitlist(b,a,z):return[(b[i//8]>>(i%8))&1 for i in range(a,z)]
def packbytes(seq):
 b=bytearray((len(seq)+7)//8)
 for i,v in enumerate(seq):b[i//8]|=v<<(i%8)
 return b
class Writer:
 def __init__(self,mode,start=0):self.mode=mode;self.bits=[i&1 for i in range(start)]
 def scalar(self,n,v):
  n=(n+7)&~7 if self.mode else n;self.bits +=[(v>>i)&1 for i in range(n)]
 def pack(self,n,v):
  if self.mode:self.scalar(32,v);return
  while n<32 and v>=(1<<n)-1:self.scalar(n,(1<<n)-1);v-=(1<<n)-1;n=min(n*2,32)
  self.scalar(n,v)
SHIM=r'''
typedef struct {unsigned capacity;} FixtureStash;
typedef const FixtureStash*cStashTable;
static const char filtered[]="Filtered";
static unsigned stashGetMaxSize(cStashTable t){return t->capacity;}
static int stashFindIndexByKey(cStashTable t,const char*s,int*out){assert(s);int hit=!strcmp(s,"Index");if(hit)*out=t->capacity-1;return hit;}
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static void pktSendString(Packet*p,const char*s){bsWriteString(&p->stream,s);}
typedef struct {const char*reward;} RewardToken;
typedef struct {RewardToken**rewardTokens,**ArchitectRewardTokens;} Player;
typedef struct {Player*pl;} Entity;
static RewardToken*groups[2][257];static unsigned counts[2];
static int fixture_ea_size(void*p){if(p==groups[0])return counts[0];assert(p==groups[1]);return counts[1];}
#define eaSize(p) fixture_ea_size(*(p))
/* Explicit eligibility adapter; no real reward membership is admitted. */
static int costume_isReward(const char*s){return s!=filtered;}
static FixtureStash fixture_stash={8};static cStashTable costume_HashTable=&fixture_stash;
'''
OBSERVE=r'''
static U32 first_begin,first_end,present_calls;
static void observed_indexed_string(Packet*p,const char*s,cStashTable t){
 U32 begin=bsGetCursorBitPosition(&p->stream);pktSendIndexedString(p,s,t);
 if(!present_calls){first_begin=begin;first_end=bsGetCursorBitPosition(&p->stream);}present_calls++;
}
#define pktSendIndexedString observed_indexed_string
'''
WRAPPER=r'''
#undef pktSendIndexedString
void reward_lists_original(unsigned mode,unsigned prefix,unsigned n0,unsigned n1,const U32*kinds,U8*out,U32*length,U32*begin,U32*end,U32*first,U32*after){
 assert(mode<=1&&prefix<8&&(!mode||!prefix)&&n0<=257&&n1<=257);
 U32 memory[16384]={0};Packet p={0};Entity e={0};Player pl={0};RewardToken tokens[2][257];char long259[260],long260[261],high[]={-128,-1,'A',0};
 memset(long259,'A',259);long259[259]=0;memset(long260,'A',260);long260[260]=0;counts[0]=n0;counts[1]=n1;
 for(unsigned g=0;g<2;g++)for(unsigned i=0;i<counts[g];i++){
  unsigned k=kinds[g*257+i];const char*s=k==0?filtered:k==1?"RewardLiteral":k==2?"":k==3?long259:k==4?long260:k==5?"Index":k==6?NULL:k==7?high:"Second";
  tokens[g][i].reward=s;groups[g][i]=&tokens[g][i];
 }
 pl.rewardTokens=groups[0];pl.ArchitectRewardTokens=groups[1];e.pl=&pl;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;p.hasDebugInfo=0;*begin=bsGetCursorBitPosition(&p.stream);
 first_begin=first_end=UINT32_MAX;present_calls=0;ent_SendCostumeRewards(&p,&e);*end=bsGetCursorBitPosition(&p.stream);assert(!p.stream.errorFlags);
 *length=p.stream.bitLength;*first=first_begin;*after=first_end;memcpy(out,memory,(*length+7)/8);
}
'''
def oracle(root,work):
 e=root/'native-android/engine/entities';extract=module('reward_list_extract',e/'check.py');prepare=module('reward_list_bits',root/'native-android/tools/protocol_fixture/prepare.py');pins=json.loads((e/'source-pins.json').read_text())['sha256_lf'];names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c'];texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in names}
 if any(sha(texts[n].encode())!=pins[n]for n in names):raise ValueError('original reward producer changed')
 code=prepare.PREAMBLE+''.join(extract.extract(texts[names[0]],n)for n in('initBitStream','bsWriteBits','bsWriteBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'))+SHIM
 code+=extract.extract(texts[names[2]],'log2i')+extract.extract(texts[names[1]],'defaultBitsPack')+extract.extract(texts[names[1]],'pktSendIndexedString')+OBSERVE+extract.extract(texts[names[3]],'ent_SendCostumeRewards')+WRAPPER
 source=work/'reward-lists-original.c';source.write_text(code);library=work/'original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),source,'-o',library]);lib=C.CDLL(str(library));lib.reward_lists_original.argtypes=[C.c_uint]*4+[C.c_void_p]*7
 return lib,{'original_source_sha256_lf':{n:pins[n]for n in names},'whole_functions_sha256_lf':{n:sha(extract.extract(texts[p],n).encode())for p,n in[(names[2],'log2i'),(names[1],'defaultBitsPack'),(names[1],'pktSendIndexedString'),(names[3],'ent_SendCostumeRewards')]},'generated_oracle_sha256':sha(code.encode()),'shim_sha256':sha(SHIM.encode()),'observer_sha256':sha(OBSERVE.encode()),'wrapper_sha256':sha(WRAPPER.encode()),'fixed_fixture_stash_capacity':8,'predicate_and_stash_are_fixture_adapters':True,'original_consumer_executed':False,'packet_debug_profile':0,'oracle_sanitized':False}
def retained(root):
 d=HERE/'qualification/initial-reward-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('accepted reward header changed')
 for p,h in host['source_sha256'].items():
  if sha((root/p).read_bytes())!=h:raise ValueError('accepted reward input changed: '+p)
 raw=bytes(map(int,re.search(r'coh_reward_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));c={n:int(v)for n,v in re.findall(r'#define COH_REWARD_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']:raise ValueError('accepted reward bytes changed')
 return raw,c,{'host_sha256':sha((d/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'source_inputs_verified':len(host['source_sha256']),'old_checker_mains_executed':False,'old_native_suites_executed':False}
def specifications():
 mixed0=[0]*256;mixed1=[0]*256
 for a in(mixed0,mixed1):a[0]=2;a[128]=1;a[255]=8
 return[([],[]),([1,0],[8,0,2]),([0,0],[1]),([2,7],[0]),([3],[]),([4],[]),([6],[]),([1,5],[8]),([1,0],[8,5]),(mixed0,mixed1),([2]*256,[2]*256),([0]*257,[]),([1],[0]*257),([0],[5]),([],[2]),([1,0,1],[0,8,0])]
def text(k):return b''if k==2 else b'A'*259 if k==3 else b'A'*260 if k==4 else bytes((128,255,65))if k==7 else b'Second'if k==8 else b'RewardLiteral'
def projection(mode,start,groups):
 w=Writer(mode,start);records=[];first=None;count_starts=[]
 for g,items in enumerate(groups):
  count_starts.append(len(w.bits));w.scalar(32,len(items))
  for i,k in enumerate(items):
   flag=len(w.bits);w.scalar(1,k!=0);begin=len(w.bits);storage=None
   if k:
    w.scalar(1,k!=6)
    if k!=6:
     storage=len(w.bits);w.scalar(1,k==5)
     if k==5:w.pack(3,7)
     else:
      for v in text(k)+b'\0':w.scalar(8,v)
    if first is None:first=(begin,len(w.bits))
   records.append({'group':g,'index':i,'kind':k,'flag':flag,'begin':begin,'storage':storage,'end':len(w.bits)})
 return w.bits,records,count_starts,first
def expected(mode,start,groups,records,count_starts,variant):
 d=[1,0,0,0,0,0,0,0,0,0];stage=6;status=2;stop=0
 # d: group,index,count0,count1,entry0,entry1,literals,literalbytes,complete,leafstage
 by={(r['group'],r['index']):r for r in records}
 for g,items in enumerate(groups):
  d[0]=g+1;d[1]=0;d[2+g]=len(items);stop=count_starts[g]+32
  if len(items)>256:return d,4,2,stop,0
  for i,k in enumerate(items):
   d[1]=i;r=by[g,i];stop=r['flag']+(8 if mode else 1)
   if k:
    if k==6:d[9]=2;return d,1,4,r['begin']+(8 if mode else 1),0
    if k==5:d[9]=5;return d,2,5,r['storage']+(8 if mode else 1),0
    if k==4:d[9]=4;return d,4,4,r['storage']+(8 if mode else 1)+260*8,0
    d[6]+=1;d[7]+=len(text(k));stop=r['end']
   d[4+g]+=1
 d[8]=1;return d,1 if variant==1 else 2,6,stop if records else count_starts[1]+32,stop if records else count_starts[1]+32
def fixtures(lib,work,retain,output):
 specs=specifications();rows=[];manifest=[];comparisons=0
 def append(mode,start,scenario,variant=0,prefix=None):
  nonlocal comparisons
  groups=specs[scenario];seq,records,count_starts,first=projection(mode,start,groups);kinds=(C.c_uint*514)()
  for g,items in enumerate(groups):
   for i,k in enumerate(items):kinds[g*257+i]=k
  raw=(C.c_ubyte*65536)();n=C.c_uint();begin=C.c_uint();end=C.c_uint();fb=C.c_uint();fe=C.c_uint();lib.reward_lists_original(mode,0 if mode else start,len(groups[0]),len(groups[1]),kinds,raw,C.byref(n),C.byref(begin),C.byref(end),C.byref(fb),C.byref(fe))
  original=[i&1 for i in range(start)]+bitlist(raw,begin.value,n.value)
  if original!=seq:raise ValueError('whole original reward lists differ from independent wire projection')
  if first and(first!=(fb.value+start-begin.value,fe.value+start-begin.value)):raise ValueError('original first literal callsite differs')
  comparisons+=1;d,status,stage,stop,validated_end=expected(mode,start,groups,records,count_starts,variant);list_end=len(seq)
  if variant==1:seq=seq[:list_end]
  elif variant in(2,3,4):
   rec=records[0];at=rec['flag']if variant==2 else rec['begin']if variant==3 else rec['storage'];seq[at:at+8]=[(2>>i)&1 for i in range(8)];stop=at+8;status=1;stage=3 if variant==2 else 4;d=[1,0,len(groups[0]),0,0,0,0,0,0,0 if variant==2 else 2 if variant==3 else 3];validated_end=0
  elif variant==5:
   # A complete first-group literal with missing second count must be counted,
   # then fail at COUNT2 rather than propagate its leaf's exact-end status.
   seq=seq[:records[0]['end']];stop=len(seq);status=1;stage=2;d=[2,0,1,0,1,0,1,13,0,0];validated_end=0
  elif variant==6:
   seq=seq[:records[0]['end']];stop=len(seq);status=1;stage=3;d=[1,1,2,0,1,0,1,13,0,0];validated_end=0
  else:seq +=[1]+[(0xdeadbeef>>i)&1 for i in range(32)]
  if variant==1 and stage==5:stop0=stop;seq=seq[:stop0];status=1
  if prefix is not None:
   delta=len(prefix)-start;seq=prefix+seq[start:];start+=delta;stop+=delta;validated_end=validated_end+delta if validated_end else 0;list_end+=delta
  packed=packbytes(seq);row=(len(packed),len(seq),mode,variant,scenario,start,stop,status,stage,*d,validated_end);rows.append((row,packed));manifest.append({'mode':mode,'start':start,'scenario':scenario,'variant':variant,'sha256':sha(packed)})
  return row,packed,seq,first,list_end
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in(0,1,2,3,4,5,6,7,8,13,14,15):append(mode,start,scenario)
  for scenario in(9,10,11,12):append(mode,0,scenario)
  for scenario in(0,1,4,7,14):append(mode,0,scenario,1)
  # Independent exact-end continuation controls.
  saved=specs[15];specs[15]=([1],[]);append(mode,0,15,5);specs[15]=([1,0],[]);append(mode,0,15,6);specs[15]=saved
  if mode:
   for variant in(2,3,4):append(mode,0,1,variant)
 base,c,_=retain;list_begin=c['NETFX_END']+4;local_start=list_begin%8;seq,recs,count_starts,first=projection(0,local_start,specs[1]);delta=list_begin-local_start
 first_group_end=count_starts[1]+delta;late_reward_begin=next(r['begin']+delta for r in recs if r['group']==1 and r['kind'])
 prefix=bitlist(base,0,list_begin)
 if bitlist(base,list_begin,c['REWARD_END'])!=seq[local_start:first[1]]:raise ValueError('whole producer firstcount/firstliteral does not match accepted JNI bytes')
 row,jni,_,_,list_end=append(0,local_start,1,prefix=prefix)
 jni_proof={'payload_bits':row[1],'payload_sha256':sha(jni),'list_begin_bit':list_begin,'reward_begin_bit':c['REWARD_BEGIN'],'reward_end_bit':c['REWARD_END'],'first_group_end_bit':first_group_end,'late_reward_begin_bit':late_reward_begin,'list_end_bit':list_end,'accepted_first_literal_bytes_matched':True,'counts':[2,3],'entries':[2,3],'literals':3,'literal_bytes':19,'device_packet':False,**{n.lower()+'_bit':c[n]for n in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END','AI_END','NETFX_END')}}
 if output:
  header='/* SOURCE-GENERATED FIXTURE: exact accepted prefix and first literal, complete original reward groups, OPAQUE deferred/slot witness. No source dictionary or physical packet. */\nstatic const unsigned char coh_reward_list_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_REWARD_LIST_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in[('BITS',row[1])]+[(n,c[n])for n in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END','AI_END','NETFX_END')]+[('LIST_BEGIN',list_begin),('REWARD_BEGIN',c['REWARD_BEGIN']),('REWARD_END',c['REWARD_END']),('FIRST_GROUP_END',first_group_end),('LATE_REWARD_BEGIN',late_reward_begin),('LIST_END',list_end)]);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);jni_proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,packed in rows:f.write(struct.pack('<20I',*row));f.write(packed)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'whole_original_projection_checks':comparisons,'max_source_counts':[256,257],'literal_lengths':[0,3,6,13,259,260],'max_complete_entries':512,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode())},jni_proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retain=retained(root);sources=[HERE/'coh_initial_reward_list_probe.c',HERE/'coh_initial_reward_probe.c',root/'native-android/engine/replication/coh_replication.c'];inputs=set(sources+[Path(__file__),HERE/'test_initial_reward_list_probe.c',HERE/'coh_initial_reward_list_probe.h',HERE/'coh_initial_reward_probe.h',root/'native-android/engine/entities/check.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-reward-20261019/host.json',HERE/'qualification/initial-reward-20261019/jni-fixture.h']);inputs.update(root/'upstream/ouroboros'/n for n in('libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c'))
 for s in sources+[HERE/'test_initial_reward_list_probe.c']:
  deps=run(['cc','-std=c99','-MM',s]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={p.resolve():p.read_bytes()for p in inputs}
 def verify():
  if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed during reward-list qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-reward-lists-')as temp:
  work=Path(temp);lib,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,work,retain,a.fixture_output)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_reward_list_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if'coh_initial_reward_list_probe.c:'in location or'coh_initial_reward_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack):raise ValueError('unbounded native stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-reward-list-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(root)):sha(b)for p,b in sorted(frozen.items())if'upstream/ouroboros'not in str(p)},'original_producers':original,'retained_reward_leaf':retain[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'native_probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Whole unchanged original two-group reward and indexed-string producers under explicit eligibility/stash/member-subset fixtures. No dictionary, consumer gameplay or complete original entity transaction. Lists stop before deferred/slot framing.','old_checker_mains_executed':False,'old_native_suites_executed':False,'physical_device_executed':False,'dictionary_admitted':False,'slot_framing_parsed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
