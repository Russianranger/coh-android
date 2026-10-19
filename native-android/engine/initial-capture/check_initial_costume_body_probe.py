#!/usr/bin/env python3
"""First costume's optional cached-string prefix from unchanged original producers."""
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
  v&=(1<<n)-1;n=(n+7)&~7 if self.mode else n;self.bits +=[(v>>i)&1 for i in range(n)]
 def pack(self,n,v):
  if self.mode:self.scalar(32,v);return
  while n<32 and v>=(1<<n)-1:self.scalar(n,(1<<n)-1);v-=(1<<n)-1;n=min(n*2,32)
  self.scalar(n,v)
SHIM=r'''
#include <strings.h>
typedef float F32;typedef int bool;
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define stricmp strcasecmp
#define NUM_SG_COLOR_SLOTS 6
#define MAX_BODY_SCALES 30
typedef struct {U32 integer;} Color;
typedef struct {U32 SGBitSetLow,SGBitSetHigh;} SGColorBits;
typedef struct {const char *entTypeFile,*costumeFilePrefix;int bodytype,convertedScale,currentSuperColorSet,iNumParts;Color colorSkin;F32 fScales[30];SGColorBits superColorsPrimaryU[6],superColorsSecondaryU[6],superColorsPrimary2U[6],superColorsSecondary2U[6],superColorsTertiaryU[6],superColorsQuaternaryU[6];} Appearance;
typedef struct {const char *pchGeom,*pchTex1,*pchTex2,*pchFxName,*regionName,*bodySetName;Color color[4];} CostumePart;
typedef struct {Appearance appearance;CostumePart *parts[30];} Costume;
/* Explicit stash adapter, fixed throughout each producer transaction. */
typedef struct {unsigned capacity;} FixtureStash;typedef const FixtureStash*cStashTable;
static FixtureStash fixture_stash={8};static cStashTable costume_HashTable=&fixture_stash,costume_HashTableExtraInfo=&fixture_stash;
static unsigned stashGetMaxSize(cStashTable t){return t->capacity;}
static int stashFindIndexByKey(cStashTable t,const char*s,int*out){int hit=!strcasecmp(s,"Index");if(hit)*out=t->capacity-1;return hit;}
static unsigned bodytype_begin,indexed_depth;
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){if(n==6&&!indexed_depth&&bodytype_begin==UINT32_MAX)bodytype_begin=bsGetCursorBitPosition(&p->stream);bsWriteBitsPack(&p->stream,n,v);}
static void pktSendString(Packet*p,const char*s){bsWriteString(&p->stream,s);}
static void pktSendF32(Packet*p,F32 v){U32 bits;memcpy(&bits,&v,4);pktSendBits(p,32,bits);}
/* Unexecuted body-tail adapters: this focused fixture has send_names1 and0parts. */
static void pktSendF(Packet*p,int n,F32 lo,F32 hi,F32 v){(void)p;(void)n;(void)lo;(void)hi;(void)v;assert(0);}
static void sendCachedIndexedColor(Packet*p,int v){(void)p;(void)v;assert(0);}
static int GetBodyPartCount(void){return 4;}
static int isNullOrNone(const char*s){return!s||!strcasecmp(s,"None");}
static int num_colors_inv_lookup[]={-1,-1,0,-1,1};
static const char*stringcache[120];static int stringcachecount,stringcacheorder;
static int colorcachecount,colorcacheorder;
'''
OBSERVER=r'''
static void observed_indexed_string(Packet*p,const char*s,cStashTable t){indexed_depth++;pktSendIndexedString(p,s,t);indexed_depth--;}
#define pktSendIndexedString observed_indexed_string
'''
WRAPPER=r'''
#undef pktSendIndexedString
void costume_body_original(unsigned mode,unsigned prefix,unsigned first,unsigned second,unsigned capacity,U8*out,U32*bits,U32*body){
 assert(mode<=1&&prefix<8&&(!mode||!prefix)&&capacity>=2&&capacity<=16&&first<=10&&second<=10);
 U32 memory[32768]={0};Packet p={0};Costume c={0};char a259[260],b260[261],b259[260],high[]={-128,-1,'A',0};
 memset(a259,'A',259);a259[259]=0;memset(b260,'B',260);b260[260]=0;memset(b259,'B',259);b259[259]=0;
 const char*values[]={NULL,"FixtureEntity","fixtureentity","",a259,b260,"Index","Other",high,"None",b259};
 c.appearance.entTypeFile=values[first];c.appearance.costumeFilePrefix=values[second];c.appearance.bodytype=1;fixture_stash.capacity=capacity;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;p.hasDebugInfo=0;
 bodytype_begin=UINT32_MAX;indexed_depth=0;costume_send(&p,&c,1);assert(!p.stream.errorFlags&&bodytype_begin!=UINT32_MAX);*bits=p.stream.bitLength;*body=bodytype_begin;memcpy(out,memory,(*bits+7)/8);
}
'''
def oracle(root,work):
 e=root/'native-android/engine/entities';extract=module('body_extract',e/'costume_oracle.py');prepare=module('body_bits',root/'native-android/tools/protocol_fixture/prepare.py');pins=json.loads((e/'source-pins.json').read_text())['sha256_lf'];names=['libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c','Common/entity/costume.h'];texts={n:(root/'upstream/ouroboros'/n).read_text().replace('\r\n','\n')for n in names}
 if any(sha(texts[n].encode())!=pins[n]for n in names):raise ValueError('original costume body source changed')
 if 'stringcache[30*4]'not in texts[names[3]]or not re.search(r'#define\s+NUM_SG_COLOR_SLOTS\s+\(6\)',texts[names[4]]):raise ValueError('source cache/body constants changed')
 code=prepare.PREAMBLE+''.join(extract.extract(texts[names[0]],n)for n in('initBitStream','bsWriteBits','bsWriteBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'))+SHIM
 functions=[(names[2],'log2i'),(names[1],'defaultBitsPack'),(names[1],'pktSendIndexedString')];code+=''.join(extract.extract(texts[p],n)for p,n in functions)+OBSERVER;functions +=[(names[3],'sendCachedIndexedString'),(names[3],'costume_send')];code+=''.join(extract.extract(texts[p],n)for p,n in functions[-2:])+WRAPPER
 src=work/'costume-body-original.c';src.write_text(code);library=work/'original.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),src,'-o',library]);lib=C.CDLL(str(library));lib.costume_body_original.argtypes=[C.c_uint]*5+[C.c_void_p]*3
 return lib,{'original_source_sha256_lf':{n:pins[n]for n in names},'whole_functions_sha256_lf':{n:sha(extract.extract(texts[p],n).encode())for p,n in functions},'consumer_source_functions_sha256_lf':{n:sha(extract.extract(texts[p],n).encode())for p,n in[(names[3],'getCachedIndexedString'),(names[3],'costume_receive'),(names[1],'pktGetIndexedString')]},'generated_oracle_sha256':sha(code.encode()),'shim_sha256':sha(SHIM.encode()),'observer_sha256':sha(OBSERVER.encode()),'wrapper_sha256':sha(WRAPPER.encode()),'fixture_stash_capacities':[2,3,8,16],'stash_and_member_subset_are_fixture_adapters':True,'cache_reset_original_per_body':True,'original_consumer_executed':False,'packet_debug_profile':0,'oracle_sanitized':False}
def retained(root):
 d=HERE/'qualification/initial-costume-slots-20261019';host=json.loads((d/'host.json').read_text());header=(d/'jni-fixture.h').read_text();proof=host['source_generated_jni_fixture']
 if sha(header.encode())!=proof['header_sha256']:raise ValueError('accepted slots header changed')
 for n,h in host['source_sha256'].items():
  if sha((root/n).read_bytes())!=h:raise ValueError('accepted slots source changed: '+n)
 raw=bytes(map(int,re.search(r'coh_costume_slots_jni_fixture\[\]=\{([\d,]+)\}',header)[1].split(',')));c={n:int(v)for n,v in re.findall(r'#define COH_COSTUME_SLOTS_JNI_FIXTURE_(\w+) (\d+)u',header)}
 if sha(raw)!=proof['payload_sha256']or c['SLOTS_END']!=proof['slots_end_bit']:raise ValueError('accepted slots payload/boundary changed')
 return raw,c,{'host_sha256':sha((d/'host.json').read_bytes()),'header_sha256':proof['header_sha256'],'payload_sha256':proof['payload_sha256'],'prefix_bits':c['SLOTS_END'],'source_inputs_verified':len(host['source_sha256']),'old_checker_mains_executed':False,'old_native_suites_executed':False}
def text(k):return{1:b'FixtureEntity',2:b'fixtureentity',3:b'',4:b'A'*259,5:b'B'*260,6:b'Index',7:b'Other',8:bytes((128,255,65)),9:b'None',10:b'B'*259}[k]
def specifications():return[(0,0),(1,0),(0,1),(1,2),(1,7),(3,3),(0,3),(4,0),(0,4),(5,0),(1,5),(6,0),(0,6),(1,6),(8,7),(0,9),(3,7),(4,4),(4,7),(4,10)]
def projection(mode,start,kinds,capacity):
 w=Writer(mode,start);records=[];cache=[]
 for field,k in enumerate(kinds):
  rec={'field':field+1,'kind':k,'flag':len(w.bits)};w.scalar(1,bool(k));rec['flag_end']=len(w.bits)
  if k:
   value=text(k);cached=value.lower()in cache;rec['cached']=cached;rec['cache']=len(w.bits);w.scalar(1,cached);rec['cache_end']=len(w.bits)
   if not cached:
    rec['presence']=len(w.bits);w.scalar(1,1);rec['storage']=len(w.bits);w.scalar(1,k==6);rec['text']=len(w.bits)
    if k==6:w.pack((capacity-1).bit_length(),capacity-1)
    else:
     for v in value+b'\0':w.scalar(8,v)
    cache.append(value.lower())
  rec['end']=len(w.bits);records.append(rec)
 bodytype=len(w.bits);w.pack(6,1);w.scalar(32,0);w.scalar(1,0);w.scalar(3,0);w.scalar(1,1)
 for _ in range(72+30):w.scalar(32,0)
 w.scalar(1,1);w.pack(4,0)
 return w.bits,records,bodytype
def expected(mode,records):
 # field,compressed,seen,present,complete,cached,cache_count,literals,bytes,validated
 d=[0,mode,0,0,0,0,0,0,0,0]
 for rec in records:
  d[0]=rec['field'];mask=1<<(rec['field']-1);d[2]|=mask;k=rec['kind']
  if not k:d[4]|=mask;continue
  d[3]|=mask
  if rec['cached']:d[5]|=mask
  elif k==6:return d,2,7,rec['text'],0
  elif k==5:return d,4,6,rec['text']+260*8,0
  else:d[6]+=1;d[7]+=1;d[8]+=len(text(k))
  d[4]|=mask
 d[9]=1;return d,2,8,records[-1]['end'],records[-1]['end']
def fixtures(lib,work,retain,output):
 specs=specifications();rows=[];manifest=[];comparisons=0
 def append(mode,start,scenario,variant=0,capacity=8,prefix=None):
  nonlocal comparisons
  kinds=specs[scenario];seq,recs,body=projection(mode,start,kinds,capacity);raw=(C.c_ubyte*131072)();n=C.c_uint();bb=C.c_uint();lib.costume_body_original(mode,0 if mode else start,*kinds,capacity,raw,C.byref(n),C.byref(bb));delta=start if mode else 0;original=[i&1 for i in range(delta)]+bitlist(raw,0,n.value)
  if seq!=original or body!=bb.value+delta:raise ValueError('whole original costume prefix differs from independent projection: '+repr((mode,start,scenario,capacity)))
  comparisons+=1;d,status,stage,stop,end=expected(mode,recs)
  if variant==1:seq=seq[:stop];status=1 if stage in(7,8)else status
  elif variant==2:
   stop=recs[0]['end'];seq=seq[:stop];d=[2,mode,1,1,1,0,1,1,len(text(kinds[0])),0];status=1;stage=2;end=0
  elif variant>=10:
   ordinal=1 if variant in(20,21,22,23,31,33)else 0;rec=recs[ordinal];field=variant%10 if variant<30 else 1 if variant in(30,31)else 2;key=('flag','cache','presence','storage')[field];where=rec[key];value=2 if variant<30 else 1 if variant in(30,31)else 0;width=8 if mode else 1;seq[where:where+width]=[(value>>i)&1 for i in range(width)];stop=where+width;status=1;stage=(2,3,4,5)[field];end=0
   d=[ordinal+1,mode,0,0,0,0,0,0,0,0]
   if ordinal and kinds[0]:d[2]=d[3]=d[4]=1;d[6]=d[7]=1;d[8]=len(text(kinds[0]))
   elif ordinal:d[2]=d[4]=1
   mask=1<<ordinal
   if field>=1:d[2]|=mask;d[3]|=mask
   if variant in(30,31):d[5]|=mask
  if prefix is not None:
   shift=len(prefix)-start;seq=prefix+seq[start:];start+=shift;stop+=shift;end=end+shift if end else 0;recs=[{key:value+shift if key in('flag','flag_end','cache','cache_end','presence','storage','text','end')else value for key,value in rec.items()}for rec in recs];body+=shift
  packed=packbytes(seq);row=(len(packed),len(seq),mode,variant,scenario,start,stop,status,stage,*d,end);rows.append((row,packed));manifest.append({'mode':mode,'begin':start,'scenario':scenario,'variant':variant,'capacity':capacity,'sha256':sha(packed)})
  return row,packed,recs,body
 for mode in(0,1):
  for start in(range(8)if not mode else(0,8)):
   for scenario in range(len(specs)):append(mode,start,scenario)
  for scenario in range(len(specs)):append(mode,0,scenario,1)
  append(mode,0,3,2)
  for capacity in(2,3,16):
   for scenario in(11,12,13):append(mode,0,scenario,capacity=capacity)
  for scenario,variant in((1,30),(2,31),(1,32),(4,33)):append(mode,0,scenario,variant)
  if mode:
   for variant in(10,11,12,13,20,21,22,23):append(mode,0,4,variant)
 base,c,_=retain;row,jni,recs,body=append(0,0,3,prefix=bitlist(base,0,c['SLOTS_END']));proof={'payload_bits':row[1],'payload_sha256':sha(jni),'body_begin_bit':row[5],'bodytype_begin_bit':body,'prefix_end_bit':row[6],'accepted_slots_prefix_matched':bitlist(jni,0,c['SLOTS_END'])==bitlist(base,0,c['SLOTS_END']),'literal_count':1,'literal_bytes':13,'cached_mask':2,'second_cache_index_bits':0,'device_packet':False,'costume_body_accepted':False,**{n.lower()+'_bit':v for n,v in c.items()if n!='BITS'}}
 if not proof['accepted_slots_prefix_matched']:raise ValueError('accepted slots prefix changed')
 if output:
  constants=[('BITS',row[1])]+[(n,v)for n,v in c.items()if n!='BITS']+[('BODY_BEGIN',row[5]),('FIRST_FLAG_BEGIN',recs[0]['flag']),('FIRST_CACHE_BEGIN',recs[0]['cache']),('FIRST_PRESENCE_BEGIN',recs[0]['presence']),('FIRST_STORAGE_BEGIN',recs[0]['storage']),('FIRST_TEXT_BEGIN',recs[0]['text']),('PREFIX_FLAG_BEGIN',recs[1]['flag']),('PREFIX_CACHE_BEGIN',recs[1]['cache']),('BODYTYPE_BEGIN',body),('PREFIX_END',row[6])]
  header='/* SOURCE-GENERATED FIXTURE: unchanged accepted slots prefix, original costume_send/cached/indexed-string producer; first literal plus case-fold cache reuse. Body suffix is source-produced but UNACCEPTED. No dictionary identity or physical body. */\nstatic const unsigned char coh_costume_body_jni_fixture[]={'+','.join(map(str,jni))+'};\n'+''.join('#define COH_COSTUME_BODY_JNI_FIXTURE_'+n+' '+str(v)+'u\n'for n,v in constants);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(header);proof['header_sha256']=sha(header.encode())
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(rows)))
  for row,raw in rows:f.write(struct.pack('<20I',*row));f.write(raw)
 return path,{'count':len(rows),'sha256':sha(path.read_bytes()),'whole_original_projection_checks':comparisons,'case_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'literal_lengths':[0,3,4,5,13,259,260],'packed_offsets':list(range(8)),'compressed_offsets':[0,8],'maximum_prefix_bits':[4168,4224],'bodytype_pack_consumed':False},proof
def main():
 if not __debug__:raise ValueError('Python assertions required')
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if a.output.exists():raise ValueError('fresh evidence output required')
 retain=retained(root);sources=[HERE/'coh_initial_costume_body_probe.c',HERE/'coh_initial_reward_probe.c',root/'native-android/engine/replication/coh_replication.c'];inputs=set(sources+[Path(__file__),HERE/'test_initial_costume_body_probe.c',HERE/'coh_initial_costume_body_probe.h',HERE/'coh_initial_reward_probe.h',root/'native-android/engine/entities/costume_oracle.py',root/'native-android/engine/entities/source-pins.json',root/'native-android/tools/protocol_fixture/prepare.py',HERE/'qualification/initial-costume-slots-20261019/host.json',HERE/'qualification/initial-costume-slots-20261019/jni-fixture.h']);inputs.update(root/'upstream/ouroboros'/n for n in('libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/costume.c','Common/entity/costume.h'))
 for s in sources+[HERE/'test_initial_costume_body_probe.c']:
  deps=run(['cc','-std=c99','-MM',s]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={p.resolve():p.read_bytes()for p in inputs}
 def verify():
  if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed during body prefix qualification')
 modes=[('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]);checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-costume-body-')as temp:
  work=Path(temp);lib,original=oracle(root,work);verify();wire,fixture,jni=fixtures(lib,work,retain,a.fixture_output)
  for mode,flags in modes:
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_initial_costume_body_probe.c','-o',exe]);checks[mode]=json.loads(run([exe,wire],env=env));binaries[mode]=sha(exe.read_bytes());verify()
  if any(v!=checks['release']for v in checks.values()):raise ValueError('mode results differ')
  stack=[]
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t')
    if'coh_initial_costume_body_probe.c:'in location or'coh_initial_reward_probe.c:'in location:stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(x['bound']not in('static','dynamic,bounded')for x in stack):raise ValueError('unbounded native stack')
 verify();a.output.parent.mkdir(parents=True,exist_ok=True);result={'schema':'coh-initial-costume-body-prefix-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(root)):sha(b)for p,b in sorted(frozen.items())if'upstream/ouroboros'not in str(p)},'original_prefix_producers':original,'retained_costume_slots':retain[2],'fixtures':fixture,'source_generated_jni_fixture':jni,'checks':checks,'binary_sha256':binaries,'native_probe_stack_frames':stack,'source_stable_before_after':True,'scope':'Whole unchanged original costume_send, sendCachedIndexedString, pktSendIndexedString, defaultBitsPack and log2i with original bit writers and explicit member-subset/stash adapters. Native accepts only two optional string fields; bodytype and the rest of the source-produced costume are unread. No dictionary identity, complete costume, original consumer application or server transaction qualified.','old_checker_mains_executed':False,'old_native_suites_executed':False,'physical_device_executed':False,'dictionary_admitted':False,'bodytype_pack_consumed':False,'complete_costume':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False};a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'jni':jni}))
if __name__=='__main__':main()
