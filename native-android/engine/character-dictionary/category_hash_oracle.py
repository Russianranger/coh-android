"""Whole original category dictionary hash/lookup with explicit unloaded tails."""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','Common/entity/powers.c','Common/entity/powers_load.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work):
 category=module('category_payload',HERE/'power_categories_oracle.py');category.module=module;stash=module('category_stash',HERE/'../stash32/oracle.py');small=module('category_extract',HERE/'../costume-inputs/oracle.py');cw=work/'payload';sw=work/'stash';cw.mkdir();sw.mkdir();_,cp=category.build(root,cw);_,sp=stash.build(root,sw);code=(cw/'categories.c').read_text().replace('typedef void*cStashTable;','typedef const struct StashTableImp*cStashTable;');st=(sw/'original.c').read_text().replace('allocations','stash_allocations');src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};functions={}
 def f(p,n):
  body=small.extract(src[p],n);functions[p+':'+n]=sha(body.encode());return body
 code+='\n#undef bool\n'+st+'\n#undef calloc\n';sh=src[EXTRA[1]];code+='\n'+re.search(r'#define STASH_DEEP_COPY_KEY_NAMES_BIT.*?} StashTableMode;',sh,re.S).group()
 code+='''
typedef StashTableImp*StashTable;typedef const StashElementImp*cStashElement;
#define onlyfulldebugdevassert(x) assert(x)
#define cpp_const_cast(t) (t)
#define S32_TO_PTR(v) ((void*)(uintptr_t)(U32)(v))
#define Indexable 0
#define WideString 1
#define stashOptimalSize(count) ((count * 3 + 1) / 2)
#define stashShared(shared) ((shared)?StashSharedHeap:StashDefault)
static void*createStringTable(void){assert(0);return NULL;}
static void initStringTable(void*p,int n){(void)p;(void)n;assert(0);}
static void strTableSetMode(void*p,int n){(void)p;(void)n;assert(0);}
static int isSharedMemory(const void*p){(void)p;assert(0);return 0;}
'''
 sc=EXTRA[0];code+='\n'+''.join(f(sc,n)for n in('stashSetMode','getKeyLength','stashTableCreateEx','stashTableCreateWithStringKeysEx','stashAddPointer','stashAddPointerConst','stashIntAddPointer','stashIntAddPointerConst','stashFindValueInternal','stashFindPointerConst','stashFindPointerReturnPointer','stashFindPointerReturnPointerConst'))
 code+='''
static StashTable stashTableCreateWithStringKeys(unsigned n,StashTableMode mode){assert(mode==StashDefault);return stashTableCreateWithStringKeysEx(n,mode,"category-fixture",0);}
static StashTable stashTableCreate(unsigned n,StashTableMode mode,StashKeyType type,unsigned bytes){assert(mode==StashDefault&&type==StashKeyTypeInts&&bytes==4);return stashTableCreateEx(n,mode,type,bytes,"category-fixture",0);}
/* Whole hash function's set/power loops are structurally present but not run:
 * loading ParsePowerCatDictionary genuinely leaves those two dictionaries empty.
 * Any accidental call to the absent power serializer is a fixture failure. */
struct BasePowerSet{const char*pchFullName,*pchSourceFile;};
struct BasePower{const char*pchFullName,*pchSourceFile;};
static int powerdict_GetCRCOfBasePower(const BasePower*p){(void)p;assert(0);return 0;}
static unsigned category_errors;
static void ErrorFilenamef(const char*path,const char*fmt,...){(void)path;(void)fmt;category_errors++;}
'''
 code+='\n'+f(EXTRA[3],'powerdict_CreateDictHashes')+'\n'+f(EXTRA[2],'powerdict_GetCategoryByNameEx')+'\n'+f(EXTRA[2],'powerdict_GetCategoryByName')
 code+='''
unsigned original_category_hash(const unsigned char*input,unsigned size,unsigned begin,unsigned*indices,unsigned*stats){SimpleBuffer*in=calloc(1,sizeof(*in));assert(in&&size<=1048576);PowerDictionary raw={0};int sum=0;reset();category_errors=0;memcpy(in->data,input,size);in->filesize=size;in->curposition=begin;assert(ParserReadBinaryTable(in,ParsePowerCatDictionary,&raw,&sum)&&in->curposition==(int)size);Vec*v=(Vec*)raw.ppPowerCategories;PowerDictionary applied=raw;applied.ppPowerCategories=v?(const PowerCategory**)v->items:NULL;assert(!applied.ppPowerSets&&!applied.ppPowers);bool ok=powerdict_CreateDictHashes(&applied,false);stats[0]=v?v->size:0;stats[1]=((StashTable)applied.haCategoryNames)->uiMaxSize;stats[2]=((StashTable)applied.haCategoryNames)->uiValidValues;stats[3]=category_errors;stats[4]=((StashTable)applied.haSetNames)->uiValidValues;stats[5]=((StashTable)applied.haPowerCRCs)->uiValidValues;
 for(unsigned i=0;i<stats[0];i++){PowerCategory*c=v->items[i];const PowerCategory*found=powerdict_GetCategoryByName(&applied,c->pchName);unsigned j=0;while(j<stats[0]&&found!=v->items[j])j++;assert(j<stats[0]);indices[i]=j;char lower[260];unsigned len=strlen(c->pchName);assert(len<260);for(unsigned k=0;k<len;k++){unsigned ch=(unsigned char)c->pchName[k];assert(ch<128);lower[k]=(char)(ch>='A'&&ch<='Z'?ch+32:ch);}lower[len]=0;assert(powerdict_GetCategoryByName(&applied,lower)==found);}
 assert(!powerdict_GetCategoryByNameEx(&applied,"unknown_missing_category",false));free(((StashTable)applied.haCategoryNames)->pStorage);free((void*)applied.haCategoryNames);free(((StashTable)applied.haSetNames)->pStorage);free((void*)applied.haSetNames);free(((StashTable)applied.haPowerCRCs)->pStorage);free((void*)applied.haPowerCRCs);free(in);reset();return ok?1:0;}
'''
 for qualified,expected in functions.items():
  _,name=qualified.rsplit(':',1);assert sha(small.extract(code,name).encode())==expected,(name,'changed')
 (work/'category-hash.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'category-hash.c','-lz','-o',work/'category-hash.so'],check=True);lib=C.CDLL(str(work/'category-hash.so'));lib.original_category_tree.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_uint];lib.original_category_hash.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p]
 return lib,{'payload_provider':cp,'stash_provider':sp,'whole_functions_sha256_lf':functions,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'generated_c_sha256':sha(code.encode()),'source_category_dictionary_only':True,'source_set_power_dictionaries_loaded':False,'runtime_generation':False}
