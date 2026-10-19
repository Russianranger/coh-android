#!/usr/bin/env python3
"""Bounded initial self-costume slots against the unchanged original sender."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(raw):return hashlib.sha256(raw).hexdigest()
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
  v&=(1<<n)-1;n=(n+7)&~7 if self.mode else n;self.bits +=[(v>>i)&1 for i in range(n)]
 def pack(self,n,v):
  if self.mode:self.scalar(32,v);return
  while n<32 and v>=(1<<n)-1:self.scalar(n,(1<<n)-1);v-=(1<<n)-1;n=min(n*2,32)
  self.scalar(n,v)
REWARD_ADAPTER=r'''
/* Explicit reward-list leaf adapter. Empty groups only locate the return
 * callsite; retained qualified nonempty lists are composed separately. */
static U32 slots_begin;
static void ent_SendCostumeRewards(Packet*p,Entity*e){(void)e;pktSendBits(p,32,0);pktSendBits(p,32,0);slots_begin=bsGetCursorBitPosition(&p->stream);}
'''
WRAPPER=r'''
void costume_slots_original(unsigned mode,unsigned prefix,const U32*c,U8*out,U32*bits,U32*begin,U32*body){
 assert(mode<=1&&prefix<8&&(!mode||!prefix)&&c[1]<=255&&c[2]<=255&&c[4]<=255);
 U32 memory[16384]={0};Packet p={0};Entity e={0};Player pl={0};Costume bodies[256]={{0}};
 for(unsigned i=0;i<256;i++)pl.costume[i]=bodies+i;
 e.type=ENTTYPE_PLAYER;e.pl=&pl;e.send_all_costume=c[3];pl.pendingCostumeForceTime=c[0]?20:0;pl.current_costume=c[1];pl.num_costume_slots=c[2];pl.num_costumes_stored=c[4];
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;
 slots_begin=observed_boundary=UINT32_MAX;observed_kind=0;watch_variant=1;entSendCostume(&p,&e,&e,1);watch_variant=0;
 assert(!p.stream.errorFlags&&slots_begin!=UINT32_MAX);*bits=p.stream.bitLength;*begin=slots_begin;*body=observed_boundary;memcpy(out,memory,(*bits+7)/8);
}
'''
def oracle(root,work):
 old=module('accepted_costume_prefix_provider',HERE/'check_initial_costume_probe.py');extract=module('slots_extract',root/'native-android/engine/entities/check.py');prepare=module('slots_bits',root/'native-android/tools/protocol_fixture/prepare.py');pins=json.loads((root/'native-android/engine/entities/source-pins.json').read_text())['sha256_lf']
 names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c','Common/comm_game.h','Common/entity/entity_enum.h','Common/entity/entPlayer.h'];texts={n:(root/'upstream/ouroboros'/n).read_text().replace('\r\n','\n')for n in names}
 if any(sha(texts[n].encode())!=pins[n]for n in names):raise ValueError('original costume slot source changed')
 shim=old.SHIM.replace('Costume*costume[16]','Costume*costume[256]');code=prepare.PREAMBLE+''.join(extract.extract(texts[names[0]],n)for n in('initBitStream','bsWriteBits','bsWriteBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'))
 comm=texts['Common/comm_game.h'];at=comm.index('typedef enum',comm.index('// Used by entsend and entrecv.'));code+=comm[at:comm.index('} AppearanceType;',at)+len('} AppearanceType;')]+'\n'+texts['Common/entity/entity_enum.h']+shim+REWARD_ADAPTER
 code+=''.join(extract.extract(texts[names[1]],n)for n in('pktSendIfSetBitsPack','pktSendIfSetString'))+extract.extract(texts['MapServer/src/entity/entsend.c'],'entSendCostume')+WRAPPER
 src=work/'costume-slots-original.c';src.write_text(code);library=work/'original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),src,'-o',library]);lib=C.CDLL(str(library));lib.costume_slots_original.argtypes=[C.c_uint,C.c_uint]+[C.c_void_p]*5
 return lib,{'original_source_sha256_lf':{n:pins[n]for n in names},'whole_producer_sha256_lf':sha(extract.extract(texts['MapServer/src/entity/entsend.c'],'entSendCostume').encode()),'original_consumer_function_sha256_lf':sha(extract.extract(texts['Game/src/entity/entrecv.c'],'entReceiveCostume').encode()),'generated_oracle_sha256':sha(code.encode()),'member_subset_and_opaque_shim_sha256':sha(shim.encode()),'reward_adapter_sha256':sha(REWARD_ADAPTER.encode()),'wrapper_sha256':sha(WRAPPER.encode()),'reward_lists_and_costume_bodies_are_adapters':True,'original_consumer_executed':False,'oracle_sanitized':False}
def retained(root):
 d=HERE/'qualification/initial-reward-list-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('accepted reward-list header changed')
 for n,h in host['source_sha256'].items():
  if sha((root/n).read_bytes())!=h:raise ValueError('accepted reward-list source changed: '+n)
 raw=bytes(map(int,re.search(r'coh_reward_list_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));c={n:int(v)for n,v in re.findall(r'#define COH_REWARD_LIST_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']or c['LIST_END']!=proof['list_end_bit']:raise ValueError('accepted reward-list payload/boundary changed')
 return raw,c,{'host_sha256':sha((d/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'prefix_bits':c['LIST_END'],'source_inputs_verified':len(host['source_sha256']),'old_checker_mains_executed':False,'old_native_suites_executed':False}
def configurations():
 # deferred,current,additional,full-list,source stored count
 return[[1,1,255,1,2],[0,0,0,1,1],[1,9,255,1,10],[0,0,255,1,10],[0,10,0,1,10],[1,255,255,1,10],[0,0,0,0,1],[1,9,255,0,10],[0,0,0,1,0],[1,0,255,1,11],[0,0,0,1,15],[1,2,7,1,2],[0,0,0,1,16],[1,0,255,1,255]]
def projection(mode,start,c):
 w=Writer(mode,start);w.scalar(1,1);w.pack(2,1);w.scalar(1,1);w.scalar(32,0);w.scalar(32,0);begin=len(w.bits);at=[]
 for n,v in zip((1,8,8,1),(c[0]!=0,c[1],c[2],c[3]!=0)):at.append(len(w.bits));w.scalar(n,v)
 if c[3]:at.append(len(w.bits));w.scalar(4,c[4])
 body=len(w.bits)if(not c[3]or c[4])else None
 for _ in range(min(c[4],10)if c[3]else 1):w.scalar(32,0xb0d1b0d1)
 for _ in range(3):w.scalar(1,0)
 return w.bits,begin,body,at
def expected(mode,begin,c):
 d=[0]*6;cursor=begin;d[0]=int(bool(c[0]));cursor+=8 if mode else 1;d[1]=c[1];cursor+=8
 if d[1]>=10:return d,4,3,cursor,0
 d[2]=c[2];cursor+=8;d[3]=int(bool(c[3]));cursor+=8 if mode else 1
 if not d[3]:return d,2,5,cursor,0
 value=c[4]&15;cursor+=8 if mode else 4
 d[4]=value
 if not value or value>10 or d[1]>=value:return d,4,6,cursor,0
 d[5]=1;return d,2,7,cursor,cursor
def fixtures(lib,work,retain,output):
 cfg=configurations();rows=[];manifest=[];comparisons=0
 def append(mode,start,scenario,variant=0,prefix=None):
  nonlocal comparisons
  c=cfg[scenario];seq,begin,body,at=projection(mode,start,c);raw=(C.c_ubyte*65536)();n=C.c_uint();sb=C.c_uint();bb=C.c_uint();lib.costume_slots_original(mode,0 if mode else start,(C.c_uint*5)(*c),raw,C.byref(n),C.byref(sb),C.byref(bb));delta=start if mode else 0;original=[i&1 for i in range(delta)]+bitlist(raw,0,n.value)
  if seq!=original or begin!=sb.value+delta or(body is not None and body!=bb.value+delta):raise ValueError('whole original costume slot framing differs from independent projection: '+repr((mode,start,scenario,len(seq),len(original),begin,sb.value+delta,body,bb.value+delta,next((i for i,(a,b)in enumerate(zip(seq,original))if a!=b),None))))
  comparisons+=1;d,status,stage,stop,end=expected(mode,begin,c)
  if variant==1:seq=seq[:stop];status=1 if stage==7 else status
  elif variant in(2,3,4):
   field={2:0,3:3,4:4}[variant];where=at[field];seq[where:where+8]=[(2 if variant!=4 else 16)>>i&1 for i in range(8)];stop=where+8;status=1;stage={2:2,3:5,4:6}[variant];d=[0]*6 if variant==2 else [int(bool(c[0])),c[1],c[2],0,0,0]if variant==3 else [int(bool(c[0])),c[1],c[2],1,0,0];end=0
  if prefix is not None:
   shift=len(prefix)-begin;seq=prefix+seq[begin:];begin+=shift;stop+=shift;end=end+shift if end else 0;at=[v+shift for v in at]
  packed=packbytes(seq);row=(len(packed),len(seq),mode,variant,scenario,begin,stop,status,stage,*d,end);rows.append((row,packed));manifest.append({'mode':mode,'begin':begin,'scenario':scenario,'variant':variant,'sha256':sha(packed)})
  return row,packed,at
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(len(cfg)):append(mode,start,scenario)
  for scenario in(0,1,2,6,8,11,12):append(mode,0,scenario,1)
  if mode:
   for variant in(2,3,4):append(mode,0,0,variant)
 base,c,_=retain;row,jni,at=append(0,0,0,prefix=bitlist(base,0,c['LIST_END']));proof={'payload_bits':row[1],'payload_sha256':sha(jni),'slots_begin_bit':row[5],'slots_end_bit':row[6],'deferred':1,'current':1,'additional':255,'multiple':1,'body_count':2,'accepted_reward_list_prefix_matched':bitlist(jni,0,c['LIST_END'])==bitlist(base,0,c['LIST_END']),'device_packet':False,'bodies_opaque':True,**{n.lower()+'_bit':c[n]for n in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END','AI_END','NETFX_END','LIST_BEGIN','REWARD_BEGIN','REWARD_END','FIRST_GROUP_END','LATE_REWARD_BEGIN','LIST_END')}}
 if not proof['accepted_reward_list_prefix_matched']:raise ValueError('accepted reward-list prefix changed')
 if output:
  constants=[('BITS',row[1])]+[(n,c[n])for n in('POST_COMMAND','CREATE_END','POSE_END','SEQUENCE_END','TRIGGERED_END','AI_END','NETFX_END','LIST_BEGIN','REWARD_BEGIN','REWARD_END','FIRST_GROUP_END','LATE_REWARD_BEGIN','LIST_END')]+[('SLOTS_BEGIN',row[5]),('CURRENT_BEGIN',at[1]),('ADDITIONAL_BEGIN',at[2]),('MULTIPLE_BEGIN',at[3]),('COUNT_BEGIN',at[4]),('SLOTS_END',row[6])]
  header='/* SOURCE-GENERATED FIXTURE: accepted reward-list prefix, original self/full-list slot framing, OPAQUE costume bodies. No physical packet or dictionary admission. */\nstatic const unsigned char coh_costume_slots_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_COSTUME_SLOTS_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in constants);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,raw in rows:f.write(struct.pack('<16I',*row));f.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'whole_original_projection_checks':comparisons,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'native_body_limit':10,'source_stored_counts':[0,1,2,10,11,15,16,255],'packed_offsets':list(range(8)),'compressed_offsets':[0,8],'original_writer_masks_before_byte_rounding':True,'synthetic_compressed_high_count_bits_refused':True},proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retain=retained(root);sources=[HERE/'coh_initial_costume_slots_probe.c',root/'native-android/engine/replication/coh_replication.c'];inputs=set(sources+[Path(__file__),HERE/'test_initial_costume_slots_probe.c',HERE/'coh_initial_costume_slots_probe.h',HERE/'check_initial_costume_probe.py',root/'native-android/engine/entities/check.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-reward-list-20261019/host.json',HERE/'qualification/initial-reward-list-20261019/jni-fixture.h']);inputs.update(root/'upstream/ouroboros'/n for n in('libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c','Common/comm_game.h','Common/entity/entity_enum.h','Common/entity/entPlayer.h'))
 for s in sources+[HERE/'test_initial_costume_slots_probe.c']:
  deps=run(['cc','-std=c99','-MM',s]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={p.resolve():p.read_bytes()for p in inputs}
 def verify():
  if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed during slot qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-costume-slots-')as temp:
  work=Path(temp);lib,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,work,retain,a.fixture_output)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_costume_slots_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if'coh_initial_costume_slots_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack):raise ValueError('unbounded native stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-costume-slots-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(root)):sha(b)for p,b in sorted(frozen.items())if'upstream/ouroboros'not in str(p)},'original_slot_producer':original,'retained_reward_list':retain[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'native_probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Whole unchanged original entSendCostume executes with explicit member-subset objects, empty reward-list adapter and opaque costume leaves. Only bounded initial self full-list slot framing is compared. Retained source-qualified nonempty reward lists are composed unchanged for JNI. No costume body, dictionary, consumer application or server transaction is qualified.','old_checker_mains_executed':False,'old_native_suites_executed':False,'physical_device_executed':False,'dictionary_admitted':False,'costume_body_parsed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
