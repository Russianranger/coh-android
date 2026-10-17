"""Original producer-defined obsolete invention body; original receiver mismatch explicit."""
import ctypes as C,json,re,tempfile,struct
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/Invention.c','Common/entity/Invention.h','Common/entity/Concept.h','Common/entity/character_net.c','Common/entity/RewardSlot.c','Common/entity/RewardSlot.h','Common/entity/RewardItemType.h','Common/entity/boost.h']
def texts():return {p:q.source(p) for p in q.PATHS+EXTRA}
def generate(src):
 code,functions,_=q.generate(src);code=re.sub(r'\bEntity\b','OuterEntity',code)
 for path,name in [(EXTRA[1],'InventionState'),(EXTRA[1],'SlotState'),(EXTRA[6],'RewardItemType')]:code+=re.search(r'typedef enum '+name+r'\s*\{.*?\}\s*'+name+r';',src[path],re.S).group(0)+'\n'
 for path in (EXTRA[0],EXTRA[3],EXTRA[4]):code+=''.join(line+'\n' for line in re.findall(r'^#define (?:INVENTION_\w+|GENERICINV_\w+|REWARDSLOT_\w+)_PACKBITS[^\n]+',src[path],re.M))
 for path in (EXTRA[1],EXTRA[2],EXTRA[7]):code+=''.join(line+'\n' for line in re.findall(r'^#define (?:INVENTION_SLOTS_MAX_COUNT|CONCEPTITEM_MAX_VARS|POWER_VAR_MAX_COUNT|POWERUP_COST_SLOTS_MAX_COUNT)[^\n]+',src[path],re.M))
 code+='''
#define verify(x) (!!(x))
#define CopyStructs(d,s,n) memcpy(d,s,(n)*sizeof(*(d)))
#define TYPE_ARRAY_SIZE(t,f) ARRAY_SIZE(((t*)0)->f)
#define INRANGE0(i,n) ((i)>=0&&(i)<(n))
#define CHAR_BOOST_MAX 1
#define WDW_INVENT 999
#define WINDOW_GROWING 999
#define false 0
#define bool int
typedef struct{RewardItemType type;const char*name;} RewardSlot;
typedef struct{RewardSlot reward;bool filled;} PowerupSlot;
typedef struct{F32 afVars[POWER_VAR_MAX_COUNT];PowerupSlot aPowerupSlots[POWERUP_COST_SLOTS_MAX_COUNT];} Boost;
typedef struct{int id;} RecipeItem;
typedef struct{int id;} ConceptDef;
typedef struct{ConceptDef*def;F32 afVars[CONCEPTITEM_MAX_VARS];} ConceptItem;
typedef struct{SlotState state;ConceptItem**concepts;} InventionSlot;
typedef struct{InventionState state;int boostInvIdx;RecipeItem*recipe;InventionSlot slots[INVENTION_SLOTS_MAX_COUNT];bool statusChange;} Invention;
typedef struct{Invention*invention;Boost*aBoosts[CHAR_BOOST_MAX];} Character;
typedef struct{Character*pchar;} Entity;
static int eaSize(void*p){void**a=*(void***)p;return a?(int)(intptr_t)a[-1]:0;}
static int rewarditemtype_IdFromName(RewardItemType t,const char*n){(void)t;return n?atoi(n):0;}
static unsigned windows;
static void window_setMode(int a,int b){assert(a==WDW_INVENT&&b==WINDOW_GROWING);windows++;}
'''
 for path,names in [(EXTRA[0],['s_validateInventionState','character_IsInventing']),(EXTRA[3],['conceptitem_Send']),(EXTRA[4],['rewardslot_Send']),(EXTRA[0],['invention_Send','invention_Receive','entity_SendInventionUpdate','entity_ReceiveInventionUpdate'])]:
  for n in names:
   body=q.extract(src[path],n);code+=body;functions[n]={'source':path,'sha256_lf':q.sha(body.encode())}
 code+='''
void active_invention_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 U32 memory[4096]={0};Packet p={0};Invention invention={0};Character character={&invention,{0}};Entity e={&character};Boost boost={0};RecipeItem recipe={65537};ConceptItem concepts[2]={0};ConceptDef defs[2]={{123},{300}};ConceptItem*arrays[INVENTION_SLOTS_MAX_COUNT][3];
 invention.statusChange=scenario%3!=0;invention.state=scenario%7;invention.boostInvIdx=scenario%2?0:-1;invention.recipe=&recipe;character.aBoosts[0]=&boost;
 for(int i=0;i<POWER_VAR_MAX_COUNT;i++)boost.afVars[i]=(float)((int)scenario-i)/4.f;
 for(int i=0;i<POWERUP_COST_SLOTS_MAX_COUNT;i++){boost.aPowerupSlots[i].filled=(scenario+i)%2;boost.aPowerupSlots[i].reward.type=(scenario+i)%kRewardItemType_Count;boost.aPowerupSlots[i].reward.name=i%3==0?"300":i%3==1?"127":"128";}
 for(int j=0;j<2;j++){concepts[j].def=(scenario+j)%3?&defs[j]:NULL;for(int i=0;i<CONCEPTITEM_MAX_VARS;i++)concepts[j].afVars[i]=(float)((int)scenario+i+j)/8.f;}
 for(int i=0;i<INVENTION_SLOTS_MAX_COUNT;i++){int count=(scenario+i)%3;arrays[i][0]=(ConceptItem*)(intptr_t)count;arrays[i][1]=&concepts[0];arrays[i][2]=&concepts[1];invention.slots[i].state=(scenario+i)%kSlotState_Count;invention.slots[i].concepts=arrays[i]+1;}
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);entity_SendInventionUpdate(&e,&p);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 observed[0]=invention.statusChange;windows=0;p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;entity_ReceiveInventionUpdate(&e,&p);*end=bsGetCursorBitPosition(&p.stream);observed[1]=windows;
}
'''
 return code,functions

def decode(data,bits,aligned,prefix):
 r=inv.independent.Reader(data,bits,aligned,prefix);status=r.packed(1);result={'status_change':status};consumer_end=r.cursor
 if status:
  state=r.packed(1);result['state']=state
  if state:
   result['recipe']=r.packed(1);result['boost_index']=r.packed(1);result['vars']=[r.scalar(32) for _ in range(4)]
   result['powerups']=[[r.packed(1),r.packed(1),r.packed(1)] for _ in range(10)]
   slots=[]
   for _ in range(10):
    slot={'state':r.packed(1)};count=r.packed(1);slot['concepts']=[[r.packed(5)]+[r.scalar(32) for _ in range(4)] for _ in range(count)];slots.append(slot)
   result['slots']=slots
 if r.cursor!=bits:raise ValueError('source producer cursor mismatch')
 return result,consumer_end

def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'active-invention-source-pins.json').read_text())!=pins:raise ValueError('source pin mismatch')
 code,functions=generate(src);cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-active-invention-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'))
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(42):
     raw=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();obs=(C.c_uint32*2)();lib.active_invention_fixture(scenario,aligned,prefix,raw,C.byref(bits),C.byref(end),obs);data=bytes(raw[:(bits.value+7)//8]);expected,consumer_end=decode(data,bits.value,aligned,prefix)
     assert end.value==consumer_end and obs[0]==0 and expected['status_change']==(scenario%3!=0)
     assert obs[1]==int(expected['status_change'] and scenario%7==1)
     if expected['status_change']:
      assert expected['state']==scenario%7
      if expected['state']:
       assert expected['recipe']==(65537 if expected['state'] in (1,3) or (expected['state'] in (2,4) and scenario%2) else 0)
       fbits=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
       assert expected['boost_index']==(0 if scenario%2 else 0xffffffff)
       assert expected['vars']==([fbits((scenario-i)/4) for i in range(4)] if scenario%2 else [0]*4)
       for i,powerup in enumerate(expected['powerups']):
        rawid=[300,127,128][i%3];narrow=((rawid+128)%256-128)&0xffffffff
        assert powerup==([(scenario+i)%11,narrow,(scenario+i)%2] if scenario%2 else [0,0,0])
       for i,slot in enumerate(expected['slots']):
        assert slot['state']==(scenario+i)%4 and len(slot['concepts'])==(scenario+i)%3
        for j,concept in enumerate(slot['concepts']):
         assert concept==([[123,300][j]]+[fbits((scenario+k+j)/8) for k in range(4)] if (scenario+j)%3 else [0]*5)
     cases.append(dict(scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=bits.value,consumer_end_bit=end.value,wire_hex=data.hex(),expected=expected,consumer_compatible=bits.value==end.value))
 return dict(schema='coh-active-invention-producer-source-oracle-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),cases=cases,cases_count=len(cases),scope='whole unchanged invention sender+validator+consumer; concept/reward senders unchanged, dictionary lookup is numeric fixture callback',source_consumer_body_noop=True,original_consumer_compatible_for_active_status=False,reward_id_char_signedness='host char narrowing observed; not portable Win32 char ABI qualification',dictionary_authority=False,original_oracle_sanitized=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'active-invention-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':result['cases_count']}))
