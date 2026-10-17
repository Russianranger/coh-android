"""Whole original fresh power_Create/LevelFinalize/AddBoostSlot on host fixtures."""
import ctypes as C,hashlib,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/powers.c','Common/entity/character_level.c']
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work):
 previous=module('initial_previous',HERE/'boost_slots_oracle.py');previous.module=module;small=module('initial_extract',HERE/'../costume-inputs/oracle.py');pw=work/'previous';pw.mkdir();_,proof=previous.build(root,pw);code=(pw/'boost-slots.c').read_text();texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};pins={}
 code+='''
/* Explicit fixture storage/clock/MP adapters. CountForLevel was already compiled
 * above with its flat signed-int earray adapter. Here eaiSize only sees the
 * source binary reader's BasePower BoostsAllowed Vec representation. */
typedef SlotCharacter Character;
typedef struct{Character*pcharParent;}PowerSet;
typedef void Boost;
typedef struct Power{const BasePower*ppowBase,*ppowOriginal;int iNumCharges;float fUsageTime;int bDontSetStance,bIgnoreConningRestrictions;unsigned long ulCreationTime;void*chainsIntoPower;Boost**ppBoosts;PowerSet*psetParent;int iNumBoostsBought,iLevelBought;}Power;
#define MP_CREATE(t,n) do{}while(0)
#define MP_ALLOC(t) ((t*)alloc(sizeof(t)))
static unsigned timerSecondsSince2000(void){return 12345;}
#undef eaSize
#undef eaiSize
#define eaSize(pp) (*(pp)?((const Vec*)*(pp))->size:0)
#define eaiSize(pp) eaSize(pp)
static void initial_create(void*pp){*(Vec**)pp=alloc(sizeof(Vec)+8192u*sizeof(void*));}
static int initial_push(void*pp,void*item){Vec*v=*(Vec**)pp;assert(v&&v->size>=0&&v->size<8192);int i=v->size++;v->items[i]=item;return i;}
#define eaCreate(pp) initial_create(pp)
#define eaPush(pp,p) initial_push(pp,p)
#define MIN(a,b) ((a)<(b)?(a):(b))
'''
 for path,name in [(EXTRA[1],'character_GetLevel'),(EXTRA[0],'power_Create'),(EXTRA[0],'power_AddBoostSlot'),(EXTRA[0],'power_LevelFinalize')]:
  body=small.extract(texts[path],name);pins[path+':'+name]=sha(body);code+='\n'+body
 source=(root/'upstream/ouroboros/Common/entity/character_net.c').read_text().replace('\r\n','\n');start=source.index('int iCntAllowed = CountForLevel(');end=source.index('ppow->iNumBoostsBought = 0;',start)+len('ppow->iNumBoostsBought = 0;');block=source[start:end];pins['character_ReceivePowers_boost_slot_slice']=sha(block)
 code+='''
static void initial_read(const unsigned char*bytes,unsigned size,BasePower*base){assert(size<=65536);if(!in){in=calloc(1,sizeof(*in));wr=calloc(1,sizeof(*wr));assert(in&&wr);}reset();memcpy(in->data,bytes,size);in->filesize=size;in->curposition=0;int sum=0;assert(ParserReadBinaryTable(in,ParseBasePower,base,&sum)&&in->curposition==(int)size);}
void original_initial_fields(const unsigned char*bytes,unsigned size,int*out){BasePower base={0};initial_read(bytes,size,&base);out[0]=base.iMaxBoosts;out[1]=eaiSize(&base.pBoostsAllowed);reset();}
void original_initial_power(const unsigned char*bytes,unsigned size,const int*schedule,unsigned count,int level,int bought,int wire,int*out){BasePower base={0};initial_read(bytes,size,&base);int values[4097];assert(count<=4096);values[0]=(int)count;memcpy(values+1,schedule,count*sizeof(int));g_Schedules.aSchedules.piFreeBoostSlotsOnPower=values+1;Character character={level};Character*pchar=&character;PowerSet set={pchar};Power*ppow=power_Create(&base);out[5]=eaSize(&ppow->ppBoosts);assert(!out[5]);ppow->psetParent=&set;int iLevelBought=bought,iCntBoosts=wire;
'''+block+'''
ppow->iLevelBought=iLevelBought;power_LevelFinalize(ppow);out[0]=base.iMaxBoosts;out[1]=eaiSize(&base.pBoostsAllowed);out[2]=ppow->iNumBoostsBought;out[3]=CountForLevel(level-bought,values+1);out[4]=eaSize(&ppow->ppBoosts);out[6]=1;out[7]=MIN(out[2]+out[3],base.iMaxBoosts);for(int i=0;i<out[4];i++)if(((Vec*)ppow->ppBoosts)->items[i])out[6]=0;reset();}
unsigned original_initial_variant(const unsigned char*bytes,unsigned size,int maximum,unsigned allowed,unsigned char*out){BasePower base={0};initial_read(bytes,size,&base);assert(allowed<=256);Vec*v=alloc(sizeof(*v)+allowed*sizeof(void*));v->size=(int)allowed;for(unsigned i=0;i<allowed;i++)v->items[i]=(void*)(uintptr_t)(U32)(i?i-1:UINT32_MAX);base.pBoostsAllowed=(int*)v;base.iMaxBoosts=maximum;wr->curposition=wr->filesize=0;int sum=0;assert(ParserWriteBinaryTable(wr,ParseBasePower,&base,&sum,0,0));unsigned n=wr->filesize;assert(n<=65536);memcpy(out,wr->data,n);reset();return n;}
'''
 (work/'initial-slots.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'initial-slots.c','-lz','-o',work/'initial-slots.so'],check=True);lib=C.CDLL(str(work/'initial-slots.so'));lib.original_initial_fields.argtypes=[C.c_void_p,C.c_uint,C.c_void_p];lib.original_initial_power.argtypes=[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_int,C.c_int,C.c_int,C.c_void_p];lib.original_initial_variant.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_uint,C.c_void_p]
 return lib,{'previous':proof,'unchanged_function_sha256_lf':pins,'generated_c_sha256':sha(code),'explicit_MP_zero_allocation_clock_and_earray_adapters':True,'fresh_slot_container_only':True,'whole_character_ReceivePowers_executed':False,'runtime_generation':False,'actor_authority':False}
