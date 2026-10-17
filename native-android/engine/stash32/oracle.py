"""Original hash/insertion/resize functions under explicit Win32-width bindings."""
import ctypes as C,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PATHS=['libs/UtilitiesLib/src/components/HashFunctions.c','libs/UtilitiesLib/include/utilitieslib/components/HashFunctions.h','libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','libs/UtilitiesLib/src/utils/mathutil.c','Common/gameData/costume_data.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text,name):
 m=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*\n\s*)*\{',text,re.M)
 if not m:raise ValueError(name)
 at=m.end();depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def build(root,work):
 source={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in PATHS};pins={p:sha(t.encode())for p,t in source.items()};assert pins==json.loads((HERE/'source-pins.json').read_text());functions={}
 def f(path,name):
  text=extract(source[path],name);functions[path+':'+name]=sha(text.encode());return text
 mix=re.search(r'#define mix\(a,b,c\).*?\n}',source[PATHS[0]],re.S).group();functions['mix_macro']=sha(mix.encode())
 code='''#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stddef.h>
#include <stdbool.h>
#include <assert.h>
#include <wchar.h>
#include <stdio.h>
typedef uint32_t U32;typedef uint32_t ub4;typedef unsigned char ub1;
typedef char source_word_must_be32[(sizeof(ub4)==4)?1:-1];
#define DEFAULT_HASH_SEED 0xfacefaceu
#define STASH_HASH_MASK(n) ((n)-1)
#define STASH_TABLE_EMPTY_SLOT_KEY NULL
#define STASH_TABLE_DELETED_SLOT_VALUE ((void*)(uintptr_t)0xfffffffeu)
#define STASH_TABLE_MIN_SIZE 8
#define STASH_TABLE_QUADRATIC_PROBE_COEFFICIENT 1
#define PTR_TO_U32(p) ((uint32_t)(uintptr_t)(p))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define devassert assert
#define devassertmsg(v,m) assert(v)
#define assertmsgf(v,...) assert(v)
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define stricmp strcasecmp
#define _wcsicmp wcscasecmp
#define sharedCalloc calloc
#define sharedFree free
static void strTableLogRemovalRequest(void*a,const char*b){(void)a;(void)b;assert(0);}
static void*strTableAddString(void*a,const void*b){(void)a;(void)b;assert(0);return NULL;}
typedef void*StringTable;typedef unsigned(*ExternalHashFunction)(void*,const void*,int);typedef int(*ExternalCompareFunction)(void*,const void*,const void*);
'''+mix+'\n'+''.join(f(PATHS[0],name)for name in ('burtlehash2','burtlehash3','burtlehash3StashDefault'))
 for name in ('StashKey','StashValue','StashElementImp','StashTableImp'):
  text=re.search(r'typedef (?:union|struct) (?:_)?'+name+r'\b.*?}\s*'+name+r';',source[PATHS[2]],re.S).group();functions[name]=sha(text.encode());code+=text+'\n'
 keyenum=re.search(r'typedef enum\s*\{\s*StashKeyTypeStrings,.*?} StashKeyType;',source[PATHS[3]],re.S).group();code=code.replace('typedef struct StashTableImp',keyenum+'\ntypedef struct StashTableImp',1)
 code+=''.join(f(PATHS[4],n)for n in ('log2i','pow2'))+''.join(f(PATHS[2],n)for n in ('stashMaskTableIndex','slotEmpty','slotDeleted','usesStringKeys','stashFindIndexByKeyInternal'))
 code+='static unsigned allocations;static void*observed_calloc(size_t n,size_t s){assert(n<=65536&&s<=256);void*p=calloc(n,s);assert(p);allocations++;return p;}\n#define calloc observed_calloc\nstatic bool stashAddValueInternal(StashTableImp*,StashKey,U32,StashValue,bool);\n'
 code+=''.join(f(PATHS[2],n)for n in ('stashTableResize','stashAddValueInternal'))
 code+='''
unsigned original_string_hash(const unsigned char*p,unsigned n,unsigned seed){return burtlehash3StashDefault(p,n,seed);}
unsigned original_int_hash(unsigned key,unsigned seed){ub4 k=key;return burtlehash2(&k,1,seed);}
int original_build(const U32*keys,unsigned count,unsigned initial,U32*slots,U32*stats){
 StashTableImp t={0};StashValue v;unsigned n;t.uiMaxSize=initial;t.uiFixedKeyLength=4;t.eKeyType=StashKeyTypeInts;allocations=0;t.pStorage=calloc(initial,sizeof(*t.pStorage));v.pValue=(void*)(uintptr_t)0xabcdef01u;
 unsigned duplicates=0,zeros=0;for(n=0;n<count;n++){if(!keys[n]){zeros++;continue;}StashKey k;k.pKey=(void*)(uintptr_t)keys[n];if(!stashAddValueInternal(&t,k,4,v,false))duplicates++;}
 memset(slots,0,65536*sizeof(*slots));for(n=0;n<t.uiMaxSize;n++)if(!slotEmpty(&t.pStorage[n])&&!slotDeleted(&t.pStorage[n]))slots[n]=(U32)(uintptr_t)t.pStorage[n].key.pKey;
 stats[0]=t.uiMaxSize;stats[1]=t.uiValidValues;stats[2]=allocations-1;stats[3]=duplicates;stats[4]=zeros;free(t.pStorage);return 1;
}
'''
 # Source palette conversion, executed only for finite source RGB0..255 inputs.
 code+='typedef float Vec3[3];\n'+f(PATHS[5],'getRGBAFromVec3')
 (work/'original.c').write_text(code);subprocess.run(['cc','-std=c99','-O0','-shared','-fPIC','-w',str(work/'original.c'),'-o',str(work/'original.so')],check=True)
 lib=C.CDLL(str(work/'original.so'));lib.original_string_hash.argtypes=[C.c_void_p,C.c_uint,C.c_uint];lib.original_string_hash.restype=C.c_uint;lib.original_int_hash.argtypes=[C.c_uint,C.c_uint];lib.original_int_hash.restype=C.c_uint;lib.original_build.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p];lib.getRGBAFromVec3.argtypes=[C.c_void_p];lib.getRGBAFromVec3.restype=C.c_uint
 return lib,{'source_sha256_lf':pins,'functions_sha256_lf':functions,'generated_c_sha256':sha(code.encode()),'source_ub4_binding':'uint32_t models Win32 unsigned-long32; native host unsigned-long64 is deliberately NOT source arithmetic','hash_load_profile':'Unchanged original raw ub4 pointer loads execute in unsanitized x86_64 oracle, including unaligned fixture addresses. Native function uses defined byte loads; no original alignment/aliasing sanitizer closure claimed.','stash_profile':'Whole original find/quadraticprobe/add/resize loops; explicit zeroed shallow int-table constructor/layout/allocation stubs, no deletes/sharedheap/deepstrings. Not whole original Win32 ABI/engine.','original_oracle_sanitized':False}
