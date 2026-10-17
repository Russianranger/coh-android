"""Original slot/width/count accessors on synthetic storage: not original asset/hash building."""
import ctypes as C,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PATHS=['Common/gameData/costume_data.c','Common/gameData/BodyPart.c','Common/entity/costume.c','Common/entity/costume.h','libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/gameData/BodyPart.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text,name):
 m=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError(name)
 at=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def identity(pins):return sha(''.join(p+'\0'+pins[p]+'\n' for p in sorted(pins)).encode())
def build(root,work):
 texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n') for p in PATHS};pins={p:sha(t.encode()) for p,t in texts.items()}
 expected=json.loads((HERE/'source-pins.json').read_text());assert pins==expected['sha256_lf'];assert identity(pins)==expected['source_id']
 stash=texts[PATHS[4]];functions={}
 def f(name):
  value=extract(stash,name);functions[name]=sha(value.encode());return value
 code='''#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <assert.h>
typedef uint32_t U32;
typedef union{void*pKey;}StashKey;
typedef union{void*pValue;}StashValue;
typedef struct{StashKey key;StashValue value;}StashElementImp;
typedef struct{U32 uiMaxSize,uiValidValues;StashElementImp*pStorage;int eKeyType;}StashTableImp;
#define devassert assert
#define STASH_TABLE_EMPTY_SLOT_KEY NULL
#define STASH_TABLE_DELETED_SLOT_VALUE ((void*)(uintptr_t)0xfffffffeU)
#define StashKeyTypeInts 1
#define PTR_TO_S32(p) ((int32_t)(intptr_t)(p))
'''+''.join(f(n) for n in ['slotEmpty','slotDeleted','stashGetMaxSize','stashGetValidElementCount','stashFindKeyByIndexInternal','stashFindKeyByIndex','stashIntFindKeyByIndex'])
 code+='''int probe(unsigned size,unsigned slot,unsigned kind,int ints,unsigned*out){
 StashElementImp storage[64]={0};StashTableImp t={size,kind<2?0:1,storage,ints};
 void*key=(void*)(uintptr_t)0xff030201U;int value=0;const void*str=0;
 if(kind==1){storage[slot].key.pKey=key;storage[slot].value.pValue=STASH_TABLE_DELETED_SLOT_VALUE;}
 if(kind==2)storage[slot].key.pKey=ints?key:(void*)"";
 if(kind==3)storage[slot].key.pKey=ints?key:(void*)"SM_Chest.geo";
 out[0]=stashGetMaxSize(&t);out[1]=stashGetValidElementCount(&t);
 int found=ints?stashIntFindKeyByIndex(&t,slot,&value):stashFindKeyByIndex(&t,slot,&str);
 out[2]=found;out[3]=ints?(unsigned)value:(str?(unsigned)((const unsigned char*)str)[0]:0u);return found;
}
'''
 color=extract(texts[PATHS[0]],'getRGBAFromVec3');functions['getRGBAFromVec3']=sha(color.encode());code+='typedef float Vec3[3];\n'+color
 body_enum=re.search(r'typedef enum BodyType\b.*?} BodyType;',texts[PATHS[3]],re.S).group()
 body_info=re.search(r'typedef struct BodyTypeInfo\b.*?} BodyTypeInfo;',texts[PATHS[3]],re.S).group()
 body_table=re.search(r'BodyTypeInfo g_BodyTypeInfos\[\]\s*=.*?\n};',texts[PATHS[2]],re.S).group()
 for name,value in [('BodyType',body_enum),('BodyTypeInfo',body_info),('g_BodyTypeInfos',body_table)]:functions[name]=sha(value.encode())
 code+='\n'+body_enum+'\n'+body_info+'\n'+body_table+'\n'+extract(texts[PATHS[2]],'getBodyTypeCount')
 code+='typedef const StashTableImp*cStashTable;\n'+extract(texts[PATHS[6]],'log2i')+extract(texts[PATHS[5]],'defaultBitsPack')+'int width(unsigned n){StashTableImp t={n,0,NULL,0};return defaultBitsPack(&t);}'
 (work/'original.c').write_text(code);subprocess.run(['cc','-std=c99','-O0','-shared','-fPIC','-Wall','-Wextra','-Werror',str(work/'original.c'),'-o',str(work/'original.so')],check=True)
 lib=C.CDLL(str(work/'original.so'));lib.probe.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_int,C.POINTER(C.c_uint)];lib.getRGBAFromVec3.argtypes=[C.POINTER(C.c_float)];lib.getRGBAFromVec3.restype=C.c_uint
 cases=0
 assert lib.getBodyTypeCount()==9;cases+=1
 for n in (2,4,8,16,32,64,128,256,512,1024,2048,4096,8192,16384,32768,65536):
  assert lib.width(n)==n.bit_length()-1;cases+=1
 for size in (2,4,8,16,32,64):
  for slot in (0,size//2,size-1,size):
   for kind in range(4):
    # Out-of-range export must be absent even when other real slots exist.
    for ints in (0,1):
     if slot==size and kind:continue
     out=(C.c_uint*4)();lib.probe(size,slot,kind,ints,out)
     assert list(out)==[size,int(kind>=2),int(kind>=2 and slot<size),0xff030201 if ints and kind>=2 else ord('S') if kind==3 else 0];cases+=1
 for r,g,b in ((0,0,0),(1,2,3),(255,255,255),(127,128,129)):
  assert lib.getRGBAFromVec3((C.c_float*3)(r,g,b))==r+(g<<8)+(b<<16)+0xff000000;cases+=1
 # Pin builder/resize/packet-width inputs even though not executed by this oracle.
 for path,names in {PATHS[0]:['costume_initHashTable','addPaletteToTables'],PATHS[4]:['stashTableResize'],PATHS[5]:['defaultBitsPack','pktSendIndexedString','pktGetIndexedString','pktSendIndexedGeneric','pktGetIndexedGeneric'],PATHS[2]:['getBodyTypeCount'],PATHS[1]:['GetBodyPartCount','ParseBoneNames','bpReadBodyPartFiles']}.items():
  for name in names:functions[path+':'+name]=sha(extract(texts[path],name).encode())
 return {'passed':True,'cases':cases,'source_sha256_lf':pins,'source_id':identity(pins),'function_sha256_lf':functions,'generated_c_sha256':sha(code.encode()),'scope':'Unchanged whole original slot getters, defaultBitsPack/log2i, body type table/count and palette word function executed on synthetic storage. Struct layouts, storage contents, and body/input assets are synthetic. Original hashing, insertion, resize, full costume builder, parser loading and packet sender/consumer functions NOT executed; their source is pinned for schema audit. No captured dictionary or live costume.','original_oracle_sanitized':False}
