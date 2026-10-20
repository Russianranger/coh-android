#!/usr/bin/env python3
"""Nonshipping stage41 gate: source consumer, synthetic qualified-query branch."""
import argparse,ctypes as C,hashlib,json,os,re,shlex,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def run(a,**kw):
 p=subprocess.run(list(map(str,a)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(repr(a)+'\n'+p.stdout+p.stderr)
 return p.stdout
def extract(text,name):
 m=re.search(r'^int\s+'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError('missing original '+name)
 at=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
ORACLE=r'''
#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define SERVER 0
#define NUM_SG_COLOR_SLOTS 6
#define MAX_BODY_SCALES 30
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
typedef int bool;typedef uint32_t U32;typedef float F32;
typedef struct{const unsigned char*data;size_t bits,cursor;unsigned aligned;}Packet;
static uint32_t pktGetBits(Packet*p,unsigned n){uint32_t v=0;if(p->aligned)n=(n+7)&~7u;assert(n<=32&&p->cursor+n<=p->bits);for(unsigned i=0;i<n;i++)v|=(uint32_t)((p->data[(p->cursor+i)/8]>>((p->cursor+i)%8))&1)<<i;p->cursor+=n;return v;}
static uint32_t pktGetBitsPack(Packet*p,unsigned n){if(p->aligned)return pktGetBits(p,32);uint32_t sum=0;for(;;){uint32_t v=pktGetBits(p,n);if(n==32||v!=(UINT32_C(1)<<n)-1)return sum+v;sum+=v;n=n*2>32?32:n*2;}}
static F32 pktGetF32(Packet*p){uint32_t v=pktGetBits(p,32);F32 f;memcpy(&f,&v,4);return f;}
static F32 pktGetF(Packet*p,int n,int a,int b){(void)p;(void)n;(void)a;(void)b;assert(0);return 0;}
typedef struct{U32 integer;}Color;
typedef struct{U32 SGBitSetLow,SGBitSetHigh;}SGColorBits;
typedef struct{const char*entTypeFile,*costumeFilePrefix;int bodytype,convertedScale,currentSuperColorSet,iNumParts;Color colorSkin;float fScales[30];SGColorBits superColorsPrimaryU[6],superColorsSecondaryU[6],superColorsPrimary2U[6],superColorsSecondary2U[6],superColorsTertiaryU[6],superColorsQuaternaryU[6];}Appearance;
typedef struct{const char*pchGeom,*pchTex1,*pchTex2,*pchFxName,*displayName,*regionName,*bodySetName;Color color[4];}CostumePart;
typedef struct{Appearance appearance;CostumePart*parts[30];}Costume;
#define StructInitFields(fn,p) memset(&(p)->appearance,0,sizeof((p)->appearance))
static int colorcachecount,colorcacheorder,stringcachecount,stringcacheorder;
static int num_colors_lookup[]={2,4},costume_HashTableExtraInfo;
static jmp_buf part_boundary;
static const char*getCachedIndexedString(Packet*p){(void)p;longjmp(part_boundary,1);return 0;}
static U32 getCachedIndexedColor(Packet*p){(void)p;assert(0);return 0;}
static const char*pktGetIndexedString(Packet*p,int t){(void)p;(void)t;assert(0);return 0;}
static struct{void**bodyParts;}bodyPartList;static unsigned fixture_count;
#define eaSize(p) ((void)(p),(int)fixture_count)
typedef struct{int type;const char*name,*seq;}BodyTypeInfo;
'''
WRAPPER=r'''
int original_boundary(const unsigned char*data,size_t bytes,size_t bits,unsigned mode,unsigned count,size_t*out){
 static Packet p;static Costume c;static CostumePart parts[30];memset(&c,0,sizeof(c));memset(parts,0,sizeof(parts));for(unsigned i=0;i<30;i++)c.parts[i]=&parts[i];assert(bits<=bytes*8);p=(Packet){data,bits,0,mode};fixture_count=count;
 int result;if(setjmp(part_boundary))result=2;else result=costume_receive(&p,&c);
 out[0]=p.cursor;out[1]=(unsigned)c.appearance.iNumParts;out[2]=(unsigned)getBodyTypeCount();return result;
}
'''
def source_oracle(root,work):
 names=['Common/entity/costume.c','Common/entity/costume.h','Common/gameData/BodyPart.c']
 pins=json.loads((root/'native-android/engine/entities/source-pins.json').read_text())['sha256_lf']
 texts={n:run(['git','-C',root,'show','HEAD:upstream/ouroboros/'+n]).replace('\r\n','\n')for n in names}
 if any(sha(texts[n].encode())!=pins[n]for n in names):raise ValueError('original source changed')
 costume=texts[names[0]];header=texts[names[1]]
 enum=re.search(r'typedef enum BodyType\s*\{.*?\}\s*BodyType;',header,re.S)[0]
 table=re.search(r'BodyTypeInfo g_BodyTypeInfos\[\]\s*=\s*\{.*?\n\};',costume,re.S)[0]
 functions={'GetBodyPartCount':extract(texts[names[2]],'GetBodyPartCount'),'getBodyTypeCount':extract(costume,'getBodyTypeCount'),'costume_receive':extract(costume,'costume_receive')}
 generated=ORACLE+enum+'\n'+table+'\n'+''.join(functions.values())+WRAPPER
 path=work/'original-boundary.c';path.write_text(generated);libpath=work/'original.so';run(['cc','-std=c99','-O0','-w','-shared','-fPIC',path,'-o',libpath]);lib=C.CDLL(str(libpath));lib.original_boundary.argtypes=[C.c_void_p,C.c_size_t,C.c_size_t,C.c_uint,C.c_uint,C.c_void_p]
 cases=0
 for mode in(0,1):
  for parts in(1,2,27,28,29,30):
   for bodytype in(0,8,9,63,64,0x7fffffff):
    for explicit in(0,1):
     for count in(0,1,parts,parts+1,30):
      seq=[]
      def bits(n,v):
       if mode:n=(n+7)&~7
       seq.extend((v>>i)&1 for i in range(n))
      def pack(n,v):
       if mode:bits(32,v);return
       while n<32:
        m=(1<<n)-1
        if v<m:bits(n,v);return
        bits(n,m);v-=m;n=min(n*2,32)
       bits(32,v)
      bits(1,0);bits(1,0);pack(6,bodytype);bits(32,0);bits(1,1);bits(3,0);bits(1,1)
      for _ in range(72+30):bits(32,0)
      bits(1,explicit)
      if explicit:pack(4,count)
      raw=bytearray((len(seq)+7)//8)
      for i,v in enumerate(seq):raw[i//8]|=v<<(i%8)
      data=(C.c_ubyte*len(raw)).from_buffer_copy(raw);observed=(C.c_size_t*3)();got=lib.original_boundary(data,len(raw),len(seq),mode,parts,observed)
      chosen=count if explicit else parts;want=0 if bodytype>=9 or chosen>parts else 1 if not chosen else 2
      if got!=want or tuple(observed)!=(len(seq),chosen,9):raise ValueError('unchanged consumer boundary differs')
      cases+=1
 return {'cases':cases,'whole_unchanged_function_sha256_lf':{k:sha(v.encode())for k,v in functions.items()},'original_source_sha256_lf':{n:pins[n]for n in names},'bodytype_enum_sha256_lf':sha(enum.encode()),'bodytype_table_sha256_lf':sha(table.encode()),'generated_oracle_sha256':sha(generated.encode()),'original_bodytype_rows':9,'original_consumer_executed':True,'actual_runtime_catalog_executed':False,'packet_helpers':'Independent bounded fixture Bits/Pack/F32 adapters; unchanged whole original receiver and getters. Positive source counts are synthetic earray adapters, not current catalog. Stops before first part/cache read.','compiled_oracle_sanitized':False}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path);a=p.parse_args();root=a.source_root.resolve()
 sources=[HERE/'coh_initial_partcount_admission.c',HERE/'coh_initial_partcount_probe.c',HERE/'coh_initial_scales_probe.c',HERE/'coh_initial_sgcolors_probe.c',HERE/'coh_initial_appearance_probe.c',root/'native-android/engine/replication/coh_replication.c'];test=HERE/'test_initial_partcount_admission.c'
 composition=HERE/'partcount_owner_composition.inc';composition_sources=sources+[root/'native-android/engine/character-dictionary/coh_costume_owner.c',root/'native-android/engine/costume-import/coh_costume_import.c',root/'native-android/engine/entities/coh_costume.c']
 inputs=set(composition_sources+[test,composition,Path(__file__),root/'native-android/engine/entities/source-pins.json'])
 for s in composition_sources+[test,composition]:
  deps=run(['cc','-std=c99','-x','c','-MM',s]).replace('\\\n',' ').split(':',1)[1];inputs.update(Path(n).resolve()for n in shlex.split(deps))
 frozen={p.resolve():p.read_bytes()for p in inputs};checks={};binaries={};frames=[];composed={};composed_binaries={};composed_frames=[]
 def verify():
  if any(p.read_bytes()!=b for p,b in frozen.items()):raise ValueError('source changed while qualifying')
 env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='coh-count-admission-')as temporary:
  work=a.work or Path(temporary)
  if a.work:work.mkdir(parents=True,exist_ok=False)
  original=source_oracle(root,work);verify()
  for mode,flags in [('release',['-O2','-fstack-usage']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,test,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free','-o',binary]);checks[mode]=json.loads(run([binary],env=env));binaries[mode]=sha(binary.read_bytes());verify()
   combined=work/('composed-'+mode);run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*composition_sources,'-x','c',composition,'-x','none','-Wl,--wrap=calloc,--wrap=free','-lcrypto','-lm','-o',combined]);composed[mode]=json.loads(run([combined],env=env));composed_binaries[mode]=sha(combined.read_bytes());verify()
  for f in work.glob('*.su'):
   for line in f.read_text().splitlines():
    location,size,bound=line.split('\t')
    if f.name.startswith('release-') and '/test_'not in location:frames.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
    if f.name.startswith('composed-release-') and 'coh_costume_owner.c:'in location:composed_frames.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not frames or any(x['bound']not in('static','dynamic,bounded')for x in frames):raise ValueError('unbounded stack')
  if sum(x['bytes']for x in frames)>16384:raise ValueError('16KiB call reserve exceeded')
  if not composed_frames or any(x['bound']not in('static','dynamic,bounded')for x in composed_frames):raise ValueError('unbounded owner stack')
  if sum(x['bytes']for x in frames+composed_frames)>16384:raise ValueError('composed16KiB query-call reserve exceeded')
 if len({json.dumps(x,sort_keys=True)for x in composed.values()})!=1:raise ValueError('composed mode checks differ')
 if len({json.dumps(x,sort_keys=True)for x in checks.values()})!=1:raise ValueError('mode checks differ')
 verify();result={'schema':'coh-initial-partcount-admission-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(root)):sha(b)for p,b in sorted(frozen.items())},'checks':checks,'binary_sha256':binaries,'actual_owner_composition':{'checks':composed,'binary_sha256':composed_binaries,'owner_native_frames':composed_frames,'conservative_admission_and_all_owner_frame_sum':sum(x['bytes']for x in frames+composed_frames),'external_crypto_sanitizer_stack_closure':False,'old_owner_suite_executed':False,'production_query_admitted':False},'original_consumer':original,'native_stack_frames':frames,'conservative_all_emitted_frame_sum':sum(x['bytes']for x in frames),'call_stack_reserve':16384,'new_heap_bytes':0,'persistent_owner_bytes':0,'packet_borrow_max':4*1024*1024,'source_stable_before_after':True,'positive_owner_query':'Explicit test-only link replacement; never compiled into production owner','production_query_admitted':False,'runtime_catalog_admitted':False,'live_stage41_progressed':False,'parts_read':0,'complete_costume':False,'actor':False,'application_ack':False,'world_authority':False,'scope':'Bounded source-framing/default/count admission consumer. Actual source/run/generation owner remains unavailable. No shipping callsite or cap changes.'};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'actual_owner_composition_checks':composed,'original_consumer_cases':original['cases'],'stack_frame_sum':result['conservative_all_emitted_frame_sum']}))
if __name__=='__main__':main()
