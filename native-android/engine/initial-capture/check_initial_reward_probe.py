#!/usr/bin/env python3
"""One original indexed-string leaf; no dictionary admission or reward-loop continuation."""
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
def bits(raw,a,b):return[(raw[i//8]>>(i%8))&1 for i in range(a,b)]
def packbytes(seq):
 raw=bytearray((len(seq)+7)//8)
 for i,v in enumerate(seq):raw[i//8]|=v<<(i%8)
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
typedef struct {unsigned capacity,hit,index;} FixtureStash;
typedef const FixtureStash*cStashTable;
static unsigned stashGetMaxSize(cStashTable t){return t->capacity;}
static int stashFindIndexByKey(cStashTable t,const char*s,int*out){assert(s);if(t->hit)*out=t->index;return t->hit;}
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static void pktSendString(Packet*p,const char*s){bsWriteString(&p->stream,s);}
'''
WRAPPER=r'''
/* Fixture stash hit/capacity observations are not source runtime dictionaries. */
void reward_original(unsigned mode,unsigned prefix,unsigned scenario,U8*out,U32*length,U32*begin,U32*index_width){
 assert(mode<=1&&prefix<8&&(!mode||!prefix)&&scenario<11);
 U32 memory[8192]={0};Packet p={0};char text[261],high[]={-128,-1,'A',0};const char*s="RewardLiteral";
 FixtureStash t={8,0,0};
 if(scenario==0)s="";
 if(scenario==2||scenario==3){unsigned n=scenario==2?259:260;memset(text,'A',n);text[n]=0;s=text;}
 if(scenario==4)s=high;
 if(scenario==5)s=NULL;
 if(scenario>=6){const unsigned capacity[]={2,3,8,16,65536};t.capacity=capacity[scenario-6];t.hit=1;t.index=t.capacity-1;}
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;p.hasDebugInfo=0;*begin=bsGetCursorBitPosition(&p.stream);
 *index_width=defaultBitsPack(&t);pktSendIndexedString(&p,s,&t);assert(!p.stream.errorFlags);*length=p.stream.bitLength;memcpy(out,memory,(*length+7)/8);
}
'''
def oracle(root,work):
 e=root/'native-android/engine/entities';extract=module('reward_source_extract',e/'check.py');prepare=module('reward_bits_prepare',root/'native-android/tools/protocol_fixture/prepare.py');pins=json.loads((e/'source-pins.json').read_text())['sha256_lf'];names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c'];text={n:(root/'upstream/ouroboros'/n).read_text().replace('\r\n','\n')for n in names}
 if any(sha(text[n].encode())!=pins[n]for n in names):raise ValueError('original reward source changed')
 code=prepare.PREAMBLE+''.join(extract.extract(text[names[0]],n)for n in('initBitStream','bsWriteBits','bsWriteBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'))+SHIM
 code+=extract.extract(text[names[2]],'log2i')+extract.extract(text[names[1]],'defaultBitsPack')+extract.extract(text[names[1]],'pktSendIndexedString')+WRAPPER
 source=work/'reward-original.c';source.write_text(code);library=work/'reward-original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),source,'-o',library]);lib=C.CDLL(str(library));lib.reward_original.argtypes=[C.c_uint]*3+[C.c_void_p]*4
 return lib,{'original_source_sha256_lf':{n:pins[n]for n in names},'whole_functions_sha256_lf':{n:sha(extract.extract(text[p],n).encode())for p,n in[(names[2],'log2i'),(names[1],'defaultBitsPack'),(names[1],'pktSendIndexedString')]},'generated_oracle_sha256':sha(code.encode()),'shim_sha256':sha(SHIM.encode()),'wrapper_sha256':sha(WRAPPER.encode()),'stash_capacity_cases':[2,3,8,16,65536],'stash_is_explicit_fixture_only':True,'packet_debug_profile':0,'original_consumer_executed':False,'oracle_sanitized':False}
def retained_prefix(root):
 d=HERE/'qualification/initial-costume-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('accepted prefix header changed')
 for p,h in host['source_sha256'].items():
  if sha((root/p).read_bytes())!=h:raise ValueError('accepted prefix input changed: '+p)
 raw=bytes(map(int,re.search(r'coh_costume_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));constants={n:int(v)for n,v in re.findall(r'#define COH_COSTUME_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']:raise ValueError('accepted prefix bytes changed')
 return raw,constants,{'host_sha256':sha((d/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'source_inputs_verified':len(host['source_sha256']),'old_checker_main_executed':False,'old_native_suites_executed':False}
def fixtures(lib,work,retained,output,root):
 rows=[];manifest=[];checks=0;index_proofs=[]
 def original(mode,start,scenario):
  nonlocal checks
  raw=(C.c_ubyte*32768)();length=C.c_uint();begin=C.c_uint();width=C.c_uint();lib.reward_original(mode,0 if mode else start,scenario,raw,C.byref(length),C.byref(begin),C.byref(width));w=Writer(mode,start);present=scenario!=5;hit=scenario>=6;w.scalar(1,present)
  if present:
   w.scalar(1,hit)
   if hit:
    cap=[2,3,8,16,65536][scenario-6];expected_width=(cap-1).bit_length()
    if width.value!=expected_width:raise ValueError('original capacity-to-width differs')
    w.pack(expected_width,cap-1);index_proofs.append((mode,cap,expected_width))
   else:
    text=b''if scenario==0 else b'A'*259 if scenario==2 else b'A'*260 if scenario==3 else bytes((128,255,65))if scenario==4 else b'RewardLiteral'
    for v in text+b'\0':w.scalar(8,v)
  produced=[i&1 for i in range(start)]+bits(raw,begin.value,length.value)
  if produced!=w.bits:raise ValueError('whole original indexed string differs from independent projection')
  checks+=1;return produced
 def append(mode,start,scenario,variant=0,prefix=None):
  seq=original(mode,start,scenario);present=scenario!=5;hit=scenario>=6;bytes_count=0 if hit or not present or scenario==0 else 259 if scenario==2 else 260 if scenario==3 else 3 if scenario==4 else 13
  stage=2 if not present else 5 if hit else 4 if scenario==3 else 6;status=1 if not present else 4 if scenario==3 else 2;valid=int(stage==6)
  stop=start+(8 if mode else 1)if not present else start+2*(8 if mode else 1)if hit else start+2*(8 if mode else 1)+260*8 if scenario==3 else len(seq)
  end=stop if stage==6 else 0
  if variant==1:seq=seq[:stop];status=1 if stage in(5,6)else status
  elif variant==2:seq=seq[:-8];stop=len(seq);stage=4;status=1;valid=0;end=0
  else:seq +=[1]+[(0xdeadbeef>>i)&1 for i in range(32)]
  if variant in(3,4):
   at=start+(8 if variant==4 else 0);seq[at:at+8]=[(2>>i)&1 for i in range(8)];stop=at+8;stage=2 if variant==3 else 3;status=1;present=variant==4;hit=False;bytes_count=valid=end=0
  if prefix is not None:
   delta=len(prefix)-start;seq=prefix+seq[start:];start+=delta;stop+=delta;end=end+delta if end else 0
  raw=packbytes(seq);row=(len(raw),len(seq),mode,variant,scenario,start,stop,status,stage,int(present),int(hit),bytes_count,valid,end);rows.append((row,raw));manifest.append({'mode':mode,'scenario':scenario,'variant':variant,'start':start,'sha256':sha(raw)});return row,raw
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(11):append(mode,start,scenario)
  for scenario in(0,1,2,6,10):append(mode,0,scenario,1)
  append(mode,0,1,2)
  if mode:
   append(mode,0,1,3);append(mode,0,1,4)
 # One accepted prefix source transaction reaches its exact present-reward
 # callsite. Never call the old checker main or use its opaque nested bytes.
 old=module('accepted_costume_prefix_provider',HERE/'check_initial_costume_probe.py');oldwork=work/'prefix';oldwork.mkdir();oldlib,oldproof=old.oracle(root,oldwork);raw=(C.c_ubyte*65536)();length=C.c_uint();begin=C.c_uint();boundary=C.c_uint();kind=C.c_uint();cfg=(C.c_uint*11)(1,1,2,3,0,0,0,0,1,1,0);oldlib.costume_prefix_original(0,0,cfg,raw,C.byref(length),C.byref(begin),C.byref(boundary),C.byref(kind))
 if kind.value!=1 or boundary.value!=37:raise ValueError('source present-reward callsite changed')
 base,const,_=retained;prefix=bits(base,0,const['NETFX_END'])+bits(raw,0,boundary.value);row,jni=append(0,len(prefix)%8,1,prefix=prefix)
 jni_proof={'payload_bits':row[1],'payload_sha256':sha(jni),'reward_begin_bit':row[5],'reward_end_bit':row[6],'present_reward_source_callsite_bit':boundary.value,'one_accepted_prefix_producer_case_executed':True,'accepted_prefix_oracle_sha256':oldproof['generated_oracle_sha256'],'device_packet':False,**{n.lower()+'_bit':const[n]for n in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END','AI_END','NETFX_END')}}
 if output:
  header='/* SOURCE-GENERATED FIXTURE: accepted prefix through first present-reward callsite, whole original literal indexed-string leaf, OPAQUE reward continuation witness. No dictionary or physical packet. */\nstatic const unsigned char coh_reward_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_REWARD_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in[('BITS',row[1])]+[(n,const[n])for n in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END','AI_END','NETFX_END')]+[('PREFIX_END',row[5]),('REWARD_BEGIN',row[5]),('REWARD_END',row[6])]);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);jni_proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,raw in rows:f.write(struct.pack('<14I',*row));f.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'original_projection_checks':checks,'index_capacity_width_cases':sorted(set(index_proofs)),'literal_lengths':[0,3,13,259,260],'cap_including_nul':260,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode())},jni_proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retained=retained_prefix(root);sources=[HERE/'coh_initial_reward_probe.c',root/'native-android/engine/replication/coh_replication.c'];providers=[Path(__file__),HERE/'test_initial_reward_probe.c',HERE/'coh_initial_reward_probe.h',HERE/'check_initial_costume_probe.py',root/'native-android/engine/entities/check.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-costume-20261019/host.json',HERE/'qualification/initial-costume-20261019/jni-fixture.h'];inputs=set(sources+providers)
 original_names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','MapServer/src/entity/entsend.c','Common/entity/costume.c','Common/comm_game.h','Common/entity/entity_enum.h','Common/entity/entPlayer.h'];inputs.update(root/'upstream/ouroboros'/n for n in original_names)
 for source in sources+[HERE/'test_initial_reward_probe.c']:
  deps=run(['cc','-std=c99','-MM',source]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={path.resolve():path.read_bytes()for path in inputs}
 def verify():
  if any(path.read_bytes()!=raw for path,raw in frozen.items()):raise ValueError('source changed during reward qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-reward-leaf-')as temp:
  work=Path(temp);lib,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,work,retained,a.fixture_output,root)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_reward_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if 'coh_initial_reward_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(v['bound']not in('static','dynamic,bounded')for v in stack):raise ValueError('unbounded reward stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-reward-string-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(frozen.items())if'upstream/ouroboros'not in str(path)},'original_reward_producer':original,'retained_costume_prefix':retained[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Exactly one original pktSendIndexedString leaf under explicit fixture stash/capacity adapters and debug0. Literal text is discarded; indexed profile stops before its pack. One existing prefix producer case supplies JNI callsite. Opaque continuation is not remaining reward framing or a costume body.','old_native_suites_executed':False,'physical_device_executed':False,'dictionary_admitted':False,'remaining_reward_loop_parsed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
