"""Original attribute description sender/consumer in explicit monitor-only profile."""
import ctypes as C,json,re,struct,tempfile
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/attrib_description.c','Common/entity/attrib_description.h','Common/entity/character_attribs.h']
def texts():return {p:q.source(p) for p in q.PATHS+EXTRA}
def generate(src):
 code,functions,_=q.generate(src);code=re.sub(r'\bEntity\b','OuterEntity',code)
 code+=re.search(r'^#define MAX_COMBAT_STATS[^\n]+',src[EXTRA[1]],re.M).group(0)+'\n'
 code+=re.search(r'typedef struct CharacterAttributes\s*\{.*?\}\s*CharacterAttributes;',src[EXTRA[2]],re.S).group(0)+'\n'
 code+='''
#define bool int
#include <stddef.h>
typedef struct{F32 fVal;int buffOrDebuff;void**ppContributers;int key;}AttribDescription;
typedef struct{AttribDescription**ppAttrib;}AttribCategory;
static struct{AttribCategory**ppCategories;}g_AttribCategoryList;
typedef struct{int unused;}Character;
typedef struct{WdwBase*winLocs;struct{int iKey;}combatMonitorStats[MAX_COMBAT_STATS];}AttribPlayer;
typedef struct{AttribPlayer*pl;int newAttribTarget;unsigned attributesTarget,owner;Character*pchar;}Entity;
static Entity*g_pAttribTarget;
static unsigned fixture_scenario,window_calls;static AttribDescription fixture_descriptions[MAX_COMBAT_STATS+1];
static AttribDescription*attribDescriptionGet(int key){for(unsigned i=0;i<MAX_COMBAT_STATS+1;i++)if(fixture_descriptions[i].key&&fixture_descriptions[i].key==key)return &fixture_descriptions[i];return NULL;}
static F32 attrib_GetVal(Character*c,AttribDescription*d,int*buff){(void)c;*buff=(d->key+fixture_scenario)%4;return ((F32)d->key-(F32)fixture_scenario)/16.f;}
static Entity*erGetEnt(unsigned id){(void)id;assert(!"unsupported full attribute fixture");return NULL;}
static Entity*validEntFromId(unsigned id){(void)id;assert(!"unsupported full attribute fixture");return NULL;}
static int eaSize(void*p){(void)p;assert(!"unsupported full attribute dictionary");return 0;}
static void eaClearEx(void*p,void*f){(void)p;(void)f;assert(!"unsupported full attribute fixture");}
static void sendAllMatchingMods(Entity*e,Packet*p){(void)e;(void)p;assert(!"unsupported contributor fixture");}
static void getAllMatchingMods(Entity*e,Packet*p){(void)e;(void)p;assert(!"unsupported contributor fixture");}
static void window_setMode(int a,int b){assert(a==WDW_COMBATNUMBERS&&b==WINDOW_DISPLAYING);window_calls++;}
static void Errorf(const char*format,...){(void)format;assert(!"unexpected missing fixture description");}
'''
 for n in ['sendAttribDescription','receiveAttribDescription']:
  body=q.extract(src[EXTRA[0]],n);code+=body;functions[n]={'path':EXTRA[0],'sha256_lf':q.sha(body.encode())}
 code+='''
void attribute_constants(unsigned*out){out[0]=MAX_COMBAT_STATS;out[1]=offsetof(CharacterAttributes,fDefense);out[2]=sizeof(CharacterAttributes);}
void attribute_fixture(unsigned scenario,unsigned aligned,unsigned prefix,U8*out,unsigned*bits,unsigned*end,unsigned*observed){
 U32 memory[4096]={0};Packet p={0};AttribPlayer player={0};Character character={0};Entity e={&player,scenario%2,0,0,&character};fixture_scenario=scenario;window_calls=0;memset(fixture_descriptions,0,sizeof(fixture_descriptions));
 for(unsigned i=0;i<MAX_COMBAT_STATS;i++){unsigned key=2000+i*4;player.combatMonitorStats[i].iKey=key;if((scenario+i)%3)fixture_descriptions[i].key=key;}if(scenario%2)fixture_descriptions[MAX_COMBAT_STATS].key=offsetof(CharacterAttributes,fDefense);
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);sendAttribDescription(&e,&p,1);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;receiveAttribDescription(&e,&p,1,0);*end=bsGetCursorBitPosition(&p.stream);
 observed[0]=window_calls;observed[1]=e.newAttribTarget;for(unsigned i=0;i<MAX_COMBAT_STATS+1;i++){observed[2+i*3]=fixture_descriptions[i].key;memcpy(observed+3+i*3,&fixture_descriptions[i].fVal,4);observed[4+i*3]=fixture_descriptions[i].buffOrDebuff;}for(unsigned i=0;i<MAX_COMBAT_STATS;i++)observed[35+i]=player.combatMonitorStats[i].iKey;
}
'''
 return code,functions

def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'attribute-monitor-source-pins.json').read_text())!=pins:raise ValueError('source pins changed')
 code,functions=generate(src);cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-attribute-monitor-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'));const=(C.c_uint32*3)();lib.attribute_constants(const);assert const[0]==10;constants={'monitor_slots':const[0],'defense_offset':const[1],'character_attributes_bytes':const[2]}
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(12):
     raw=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();projected=(C.c_uint32*45)();lib.attribute_fixture(scenario,aligned,prefix,raw,C.byref(bits),C.byref(end),projected);data=bytes(raw[:(bits.value+7)//8]);r=inv.independent.Reader(data,bits.value,aligned,prefix);newtarget=r.scalar(1);full=r.scalar(1);assert full==0;rows=[]
     for i in range(11):
      present=r.scalar(1);row={'present':present};key=2000+i*4 if i<10 else const[1];wanted=(scenario+i)%3!=0 if i<10 else bool(scenario%2);assert present==wanted
      if present:
       row.update(key=r.scalar(32),value_word=r.scalar(32),buff=r.scalar(2));bitsf=struct.unpack('<I',struct.pack('<f',(key-scenario)/16))[0];assert [row['key'],row['value_word'],row['buff']]==[key,bitsf,(key+scenario)%4] and list(projected[2+i*3:5+i*3])==[key,bitsf,(key+scenario)%4]
      if i<10:assert projected[35+i]==(key if present else 0)
      rows.append(row)
     assert r.cursor==bits.value==end.value and newtarget==scenario%2 and projected[0]==newtarget and projected[1]==0
     cases.append(dict(scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=end.value,wire_hex=data.hex(),expected={'new_target':newtarget,'full':full,'slots':rows}))
 return dict(schema='coh-attribute-monitor-source-oracle-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),constants=constants,cases=cases,cases_count=len(cases),scope='whole original sender/consumer with winLocsNULL explicit monitor profile; synthetic description/value lookup and UI callbacks; actual CharacterAttributes declaration determines defenseoffset',full_mode_qualified=False,dictionary_authority=False,original_oracle_sanitized=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'attribute-monitor-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 r=qualify();a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'cases':r['cases_count'],'constants':r['constants']}))
