"""Qualify the original obsolete-invention sender/consumer boundary mismatch."""
import ctypes as C, json, re, tempfile
from pathlib import Path
import inventory_oracle as inv
q=inv.q
HERE=Path(__file__).resolve().parent
PATH='Common/entity/Invention.c';HEADER='Common/entity/Invention.h'
def qualify():
 src={p:q.source(p) for p in q.PATHS+[PATH,HEADER]};pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'invention-source-pins.json').read_text())!=pins:raise ValueError('invention source pins changed')
 code,functions,_=q.generate(src)
 # q's Player/Entity fixture does not own a Character; rename its fixture types.
 code=re.sub(r'\bEntity\b','OuterEntity',code)
 code+=re.search(r'typedef enum InventionState\s*\{.*?\}\s*InventionState;',src[HEADER],re.S).group(0)+'\n'
 code+=re.search(r'typedef enum SlotState\s*\{.*?\}\s*SlotState;',src[HEADER],re.S).group(0)+'\n'
 code+=''.join(line+'\n' for line in re.findall(r'^#define INVENTION_\w+_PACKBITS[^\n]+',src[PATH],re.M))
 code+='''
#define verify(x) (!!(x))
#define TYPE_ARRAY_SIZE(t,f) (sizeof(((t*)0)->f)/sizeof(((t*)0)->f[0]))
#define CopyStructs(d,s,n) memcpy(d,s,(n)*sizeof(*(d)))
#define INRANGE0(i,n) ((i)>=0&&(i)<(n))
#define CHAR_BOOST_MAX 1
#define WDW_INVENT 999
#define WINDOW_GROWING 999
#define false 0
#define bool int
typedef struct{int reward,filled;} PowerupSlot;
typedef struct{F32 afVars[4];PowerupSlot aPowerupSlots[1];} Boost;
typedef struct{int id;} RecipeItem;
typedef struct{int state;void**concepts;} InventionSlot;
typedef struct{InventionState state;int boostInvIdx;RecipeItem*recipe;InventionSlot slots[10];int statusChange;} Invention;
typedef struct{Invention*invention;Boost*aBoosts[1];} Character;
typedef struct{Character*pchar;} Entity;
static int character_IsInventing(const Character*p){(void)p;assert(!"unsupported active invention fixture");return 0;}
static int eaSize(void*p){(void)p;assert(!"unsupported invention slots fixture");return 0;}
static void rewardslot_Send(void*r,Packet*p){(void)r;(void)p;assert(!"unsupported invention reward fixture");}
static void conceptitem_Send(void*c,Packet*p){(void)c;(void)p;assert(!"unsupported invention concept fixture");}
static void window_setMode(int a,int b){(void)a;(void)b;assert(!"unsupported invention UI fixture");}
'''
 for name in ['invention_Send','invention_Receive','entity_SendInventionUpdate','entity_ReceiveInventionUpdate']:
  body=q.extract(src[PATH],name);code+=body;functions[name]={'source':PATH,'sha256_lf':q.sha(body.encode())}
 code+='''
void invention_fixture(U32 status,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 U32 memory[4096]={0};Packet p={0};Invention invention={0};Character character={&invention,{0}};Entity e={&character};invention.statusChange=status;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;
 if(prefix)bsWriteBits(&p.stream,prefix,0);entity_SendInventionUpdate(&e,&p);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);observed[0]=invention.statusChange;
 /* Null consumer Character suppresses UI-only callbacks after original no-op reader. */
 e.pchar=NULL;p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;
 entity_ReceiveInventionUpdate(&e,&p);*end=bsGetCursorBitPosition(&p.stream);
 observed[1]=*bits-*end;
 /* Execute unchanged invention_Receive directly too; it must read no wire. */
 U32 before=bsGetCursorBitPosition(&p.stream);invention_Receive(&character,&p);observed[2]=bsGetCursorBitPosition(&p.stream)-before;
}
'''
 cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-invention-oracle-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'))
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for status in (0,1):
     raw=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();obs=(C.c_uint32*3)();lib.invention_fixture(status,aligned,prefix,raw,C.byref(bits),C.byref(end),obs)
     r=inv.independent.Reader(bytes(raw),bits.value,aligned,prefix);assert r.packed(1)==status;consumer_end=r.cursor
     if status:assert r.packed(1)==0
     assert r.cursor==bits.value and consumer_end==end.value and obs[0]==0 and obs[2]==0 and obs[1]==(32 if aligned else 1)*status
     cases.append(dict(status=status,aligned=aligned,begin_bit=prefix,sender_end_bit=bits.value,consumer_end_bit=end.value,wire_hex=bytes(raw[:(bits.value+7)//8]).hex(),observed=list(obs)))
 return dict(schema='coh-invention-source-boundary-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),cases=cases,cases_count=len(cases),active_nonzero_state_qualified=False,source_consumer_body_noop=True,status_change_true_sender_consumer_match=False,scope='status false and status true/state None only; active invention helpers assert rather than fabricate',original_oracle_sanitized=False,android_executed=False,actor_publication=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'invention-source-pins.json').write_text(json.dumps({p:q.sha(q.source(p).encode()) for p in q.PATHS+[PATH,HEADER]},indent=2)+'\n')
 r=qualify();a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'cases':r['cases_count'],'source_boundary_mismatch_proven':True}))
