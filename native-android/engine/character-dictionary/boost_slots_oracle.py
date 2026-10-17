"""Original schedules codec/CountForLevel and ReceivePowers scalar slice.

Explicit host storage and tiny Character/Power fixtures; no whole character,
dictionary-finalization, current-generation or packet application claim.
"""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/power_system.c','Common/entity/power_system.h','Common/entity/character_net.c']
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work):
 record=module('slots_record',HERE/'power_record_oracle.py');record.module=module;small=module('slots_extract',HERE/'../costume-inputs/oracle.py');rw=work/'record';rw.mkdir();_,prior=record.build(root,rw);code=(rw/'power-record.c').read_text();src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};pins={}
 # Only explicit storage adapters change: original struct/int-array/table binary
 # functions execute unchanged. Embedded structs live directly in their parent.
 for name,body in {
  'TokenStoreGetPointer':'static void*TokenStoreGetPointer(ParseTable*t,int c,const void*p,int i){if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i<v->size);return v->items[i];}if(!(t[c].type&TOK_INDIRECT))return field(t,c,p);return *(void**)field(t,c,p);}',
  'TokenStoreAlloc':'static void*TokenStoreAlloc(ParseTable*t,int c,void*p,int i,size_t n,void*a,void*b){(void)a;(void)b;if(!(t[c].type&(TOK_EARRAY|TOK_INDIRECT)))return field(t,c,p);void*x=alloc(n);if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i<v->size);v->items[i]=x;}else *(void**)field(t,c,p)=x;return x;}'
 }.items():code=code.replace(small.extract(code,name),body+"\n")
 for name in ('Schedule','Schedules'):
  body=re.search(r'typedef struct '+name+r'\s*\{.*?} '+name+';',src[EXTRA[1]],re.S).group();pins[name]=sha(body);code+='\n'+body
 code+='\n#define TOK_EMBEDDEDSTRUCT(s,m,t) TOK_STRUCT_X,offsetof(s,m),sizeof(((s*)0)->m),t\n'
 for name in ('ParseSchedule','ParseSchedules'):
  body=re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',src[EXTRA[0]],re.S).group();pins[name]=sha(body);code+='\n'+body
 count=small.extract(src[EXTRA[0]],'CountForLevel');pins['CountForLevel']=sha(count);code+='\n#define eaiSize(pp) (*(pp)?((const int*)*(pp))[-1]:0)\n'+count
 block=re.search(r'int iCntAllowed = CountForLevel\(.*?if\(ppow->iNumBoostsBought<0\) ppow->iNumBoostsBought = 0;',src[EXTRA[2]],re.S).group();assert block.count('\n')==3;pins['character_ReceivePowers_boost_slot_slice']=sha(block)
 code+='''
static Schedules g_Schedules;
typedef struct{int iLevel;}SlotCharacter;
typedef struct{const BasePower*ppowBase;int iNumBoostsBought;}SlotPower;
#define min(a,b) ((a)<(b)?(a):(b))
static unsigned get_schedule(unsigned f,Schedule*s,int*out){const int*values[]={s->piFreeBoostSlotsOnPower,s->piPoolPowerSet,s->piEpicPowerSet,s->piPower,s->piAssignableBoost,s->piInspirationCol,s->piInspirationRow};assert(f<7);Vec*v=(Vec*)values[f];unsigned n=v?v->size:0;assert(n<=4096);for(unsigned i=0;i<n;i++)out[i]=(int)(uintptr_t)v->items[i];return n;}
unsigned original_schedule_count(const int*values,unsigned n,int level){int storage[4097];assert(n<=4096);storage[0]=(int)n;memcpy(storage+1,values,n*sizeof(int));return CountForLevel(level,storage+1);}
int original_slot_arithmetic(const int*values,unsigned n,int level,int bought,int maximum,int wire,int*out){int storage[4097];assert(n<=4096);storage[0]=(int)n;memcpy(storage+1,values,n*sizeof(int));g_Schedules.aSchedules.piFreeBoostSlotsOnPower=storage+1;SlotCharacter character={level};SlotCharacter*pchar=&character;BasePower base={0};base.iMaxBoosts=maximum;SlotPower power={&base,0};SlotPower*ppow=&power;int iLevelBought=bought,iCntBoosts=wire;
'''+block+'''
out[0]=iCntAllowed;out[1]=ppow->iNumBoostsBought;return 1;}
unsigned original_schedules(const unsigned char*bytes,unsigned size,unsigned begin,unsigned char*out,unsigned*words){SimpleBuffer*in=calloc(1,sizeof(*in)),*wr=calloc(1,sizeof(*wr));assert(in&&wr&&size<=65536);Schedules schedules={0};memcpy(in->data,bytes,size);in->filesize=size;in->curposition=begin;reset();int sum=0;assert(ParserReadBinaryTable(in,ParseSchedules,&schedules,&sum)&&in->curposition==(int)size);unsigned at=7;int values[4096];for(unsigned f=0;f<7;f++){unsigned n=get_schedule(f,&schedules.aSchedules,values);words[f]=n;assert(at+n<=4103);for(unsigned i=0;i<n;i++)words[at++]=(unsigned)values[i];}memcpy(wr->data,bytes,begin);wr->curposition=wr->filesize=begin;sum=0;assert(ParserWriteBinaryTable(wr,ParseSchedules,&schedules,&sum,0,0));unsigned n=wr->filesize;memcpy(out,wr->data,n);reset();free(in);free(wr);return n;}
unsigned original_schedules_crc(void){return ParseTableCRC(ParseSchedules,NULL);}
int original_power_maxboosts(const unsigned char*bytes,unsigned size){assert(size<=65536);if(!in){in=calloc(1,sizeof(*in));wr=calloc(1,sizeof(*wr));assert(in&&wr);}reset();memcpy(in->data,bytes,size);in->filesize=size;in->curposition=0;BasePower power={0};int sum=0;assert(ParserReadBinaryTable(in,ParseBasePower,&power,&sum)&&in->curposition==(int)size);int n=power.iMaxBoosts;reset();return n;}
unsigned original_power_maxboosts_variant(const unsigned char*bytes,unsigned size,int maximum,unsigned char*out){assert(size<=65536);if(!in){in=calloc(1,sizeof(*in));wr=calloc(1,sizeof(*wr));assert(in&&wr);}reset();memcpy(in->data,bytes,size);in->filesize=size;in->curposition=0;BasePower power={0};int sum=0;assert(ParserReadBinaryTable(in,ParseBasePower,&power,&sum)&&in->curposition==(int)size);power.iMaxBoosts=maximum;wr->curposition=wr->filesize=0;sum=0;assert(ParserWriteBinaryTable(wr,ParseBasePower,&power,&sum,0,0));unsigned n=wr->filesize;memcpy(out,wr->data,n);reset();return n;}
'''
 (work/'boost-slots.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'boost-slots.c','-lz','-o',work/'boost-slots.so'],check=True);lib=C.CDLL(str(work/'boost-slots.so'))
 lib.original_schedules.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p];lib.original_schedule_count.argtypes=[C.c_void_p,C.c_uint,C.c_int];lib.original_slot_arithmetic.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_int,C.c_int,C.c_int,C.c_void_p];lib.original_power_maxboosts.argtypes=[C.c_void_p,C.c_uint];lib.original_power_maxboosts_variant.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_void_p]
 return lib,{'record_provider':prior,'unchanged_source_sha256_lf':pins,'generated_c_sha256':sha(code),'embedded_struct_storage_adapter':True,'earray_CountForLevel_size_header_adapter':True,'character_fixture_scalar_slice_only':True,'whole_character_ReceivePowers_executed':False,'runtime_generation':False}
