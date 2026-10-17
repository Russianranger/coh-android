"""Original generic inventory item wire functions with explicit dictionary-free shells."""
from pathlib import Path
import ctypes as C, hashlib, importlib.util, json, re, subprocess, sys, tempfile
HERE=Path(__file__).resolve().parent
PROVIDER=HERE.parent/'character-outer-20261017'
sys.path.insert(0,str(PROVIDER))
import qualify_outer as q
import independent
EXTRA=['Common/entity/character_net.c','Common/entity/character_inventory.h','Common/entity/Concept.h']
def texts():return {p:q.source(p) for p in q.PATHS+EXTRA}
def generate(src):
 code,funcs,_=q.generate(src)
 h=src[EXTRA[1]]
 code+=re.search(r'typedef enum InventoryType\s*\{.*?\}\s*InventoryType;',h,re.S).group(0)+'\n'
 code+=re.search(r'#define CONCEPTITEM_MAX_VARS[^\n]+',src[EXTRA[2]]).group(0)+'\n'
 code+=''.join(x+'\n' for x in re.findall(r'^#define GENERICINV_(?:TYPE|ID|IDX|AMOUNT)_PACKBITS[^\n]+',src[EXTRA[0]],re.M))
 code+='''
#define verify(x) (!!(x))
#define CopyStructs(d,s,n) memcpy(d,s,(n)*sizeof(*(d)))
#define TYPE_ARRAY_SIZE(t,f) ARRAY_SIZE(((t*)0)->f)
#define EAINRANGE(i,a) ((i)>=0&&(i)<1&&(a))
typedef struct{int id;} ConceptDef;
typedef struct{ConceptDef*def;F32 afVars[CONCEPTITEM_MAX_VARS];} ConceptItem;
typedef struct{ConceptItem*concept;} ConceptInventoryItem;
typedef struct{ConceptInventoryItem**conceptInv;int id,amount;U32 observed[8];} Character;
static void character_GetInvInfo(Character*p,int*id,int*amount,void*unused,InventoryType type,int idx){(void)unused;(void)type;(void)idx;*id=p->id;*amount=p->amount;}
static void character_SetConcept(Character*p,int id,F32*vars,int idx,int amount){p->observed[0]=kInventoryType_Concept;p->observed[1]=idx;p->observed[2]=amount;p->observed[3]=id;memcpy(p->observed+4,vars,4*sizeof(F32));}
static void character_SetInventory(Character*p,int type,int id,int idx,int amount,const char*fn){(void)fn;p->observed[0]=type;p->observed[1]=idx;p->observed[2]=amount;p->observed[3]=id;}
'''
 for n in ['conceptitem_Send','character_inventory_Send','character_inventory_Receive']:
  body=q.extract(src[EXTRA[0]],n);funcs[n]={'source':EXTRA[0],'sha256_lf':q.sha(body.encode())};code+=body
 code+='''
void inventory_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 U32 memory[4096]={0};Packet p={0};Character source={0},dest={0};ConceptDef def={0};ConceptItem concept={0};ConceptInventoryItem item={&concept};ConceptInventoryItem*items[]={&item};
 U32 type=scenario%7;int idx=type==kInventoryType_Concept?0:(int)(scenario*33u);source.id=(int)(scenario*65537u);source.amount=(int)(scenario*129u);source.conceptInv=items;def.id=source.id;concept.def=scenario%3?&def:NULL;
 for(int i=0;i<CONCEPTITEM_MAX_VARS;i++)concept.afVars[i]=(float)((int)scenario-i*3)/4.f;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;
 if(prefix)bsWriteBits(&p.stream,prefix,0);character_inventory_Send(&source,&p,type,idx);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;
 character_inventory_Receive(&dest,&p);*end=bsGetCursorBitPosition(&p.stream);memcpy(observed,dest.observed,sizeof(dest.observed));
}
'''
 return code,funcs

def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()};pinpath=HERE/'inventory-source-pins.json'
 if not pinpath.exists() or json.loads(pinpath.read_text())!=pins:raise ValueError('inventory source pin absent or changed')
 code,funcs=generate(src);cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-inventory-oracle-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'))
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(70):
     raw=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();obs=(C.c_uint32*8)();lib.inventory_fixture(scenario,aligned,prefix,raw,C.byref(bits),C.byref(end),obs)
     data=bytes(raw[:(bits.value+7)//8]);r=independent.Reader(data,bits.value,aligned,prefix)
     values=[r.packed(5) for _ in range(4)]
     if values[0]==1:values += [r.scalar(32) for _ in range(4)]
     else:values += [0]*4
     if r.cursor!=bits.value or end.value!=bits.value or values!=list(obs):raise ValueError('original/model field or cursor mismatch')
     cases.append(dict(scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=end.value,wire_hex=data.hex(),expected=values))
 if texts()!=src:raise ValueError('source changed during run')
 return dict(schema='coh-inventory-item-source-oracle-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=funcs,generated_source_sha256=q.sha(code.encode()),cases=cases,cases_count=len(cases),scope='raw item grammar; dictionary setters and inventory lookup are explicit fixture callbacks',auction_inventory_qualified=False,complete_inventory_update=False,original_oracle_sanitized=False,android_executed=False,actor_publication=False,acknowledgments_enabled=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'inventory-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':result['cases_count']}))
