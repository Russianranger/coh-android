"""Whole original class named-stash finalization and value lookup interfaces."""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','Common/entity/classes.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work):
 classes=module('named_classes',HERE/'classes_oracle.py');classes.module=module;stash=module('named_stash',HERE/'../stash32/oracle.py');small=module('named_extract',HERE/'../costume-inputs/oracle.py');cw=work/'classes';sw=work/'stash';cw.mkdir();sw.mkdir();_,cp=classes.build(root,cw);_,sp=stash.build(root,sw);code=(cw/'original-classes.c').read_text().replace('typedef void*cStashTable;','typedef const struct StashTableImp*cStashTable;');st=(sw/'original.c').read_text().replace('allocations','stash_allocations');src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};functions={}
 def f(path,name):
  body=small.extract(src[path],name);functions[path+':'+name]=sha(body.encode());return body
 code+='\n#undef bool\n'+st+'\n#undef calloc\n';code+='\n'+re.search(r'#define STASH_DEEP_COPY_KEY_NAMES_BIT.*?} StashTableMode;',src[EXTRA[1]],re.S).group()
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
 code+='\n'+''.join(f(EXTRA[0],n)for n in('stashSetMode','getKeyLength','stashTableCreateEx','stashTableCreateWithStringKeysEx','stashAddPointer','stashAddPointerConst','stashFindValueInternal','stashFindPointerConst'))
 code+='''
static StashTable stashTableCreateWithStringKeys(unsigned n,StashTableMode mode){assert(mode==StashDefault);return stashTableCreateWithStringKeysEx(n,mode,"class-named-fixture",0);}
static unsigned duplicate_errors;
#define assertmsg(x,msg) do{if(!(x))duplicate_errors++;}while(0)
typedef struct{unsigned count;float values[];} FloatValues;
#define eafSize(pp) (*(pp)?((FloatValues*)((char*)*(pp)-offsetof(FloatValues,values)))->count:0)
'''
 code+='\n'+f(EXTRA[2],'classes_Finalize')+'\n'+f(EXTRA[2],'class_GetNamedTableValue')
 code+='''
static CharacterClasses loaded;static SimpleBuffer*input;static Vec*rows;
void original_named_close(void){if(rows)for(unsigned i=0;i<(unsigned)rows->size;i++){CharacterClass*c=rows->items[i];StashTable t=(StashTable)c->namedStash;if(t){free(t->pStorage);free(t);}}free(input);input=NULL;rows=NULL;memset(&loaded,0,sizeof(loaded));reset();}
unsigned original_named_open(const unsigned char*bytes,unsigned size,unsigned begin,unsigned*stats){assert(!input&&size<=8388608);input=calloc(1,sizeof(*input));assert(input);reset();memcpy(input->data,bytes,size);input->filesize=size;input->curposition=begin;int sum=0;assert(ParserReadBinaryTable(input,ParseCharacterClasses,&loaded,&sum)&&input->curposition==(int)size);rows=(Vec*)loaded.ppClasses;assert(rows);loaded.ppClasses=(const CharacterClass**)rows->items;for(unsigned i=0;i<(unsigned)rows->size;i++){CharacterClass*c=rows->items[i];Vec*v=(Vec*)c->ppNamedTables;c->ppNamedTables=v?(const NamedTable**)v->items:NULL;for(unsigned j=0;v&&j<(unsigned)v->size;j++){NamedTable*t=v->items[j];Vec*values=(Vec*)t->pfValues;FloatValues*flat=alloc(sizeof(*flat)+(values?values->size:0)*4);flat->count=values?values->size:0;for(unsigned k=0;k<flat->count;k++){U32 w=(U32)(uintptr_t)values->items[k];memcpy(flat->values+k,&w,4);}t->pfValues=flat->values;}}duplicate_errors=0;bool accepted=classes_Finalize(&loaded,false);stats[0]=rows->size;stats[1]=duplicate_errors;stats[2]=stats[3]=stats[4]=0;for(unsigned i=0;i<(unsigned)rows->size;i++){CharacterClass*c=rows->items[i];StashTable t=(StashTable)c->namedStash;stats[2]+=eaSize(&c->ppNamedTables);stats[3]+=t->uiMaxSize;stats[4]+=t->uiValidValues;}return accepted?1:0;}
unsigned original_named_value(unsigned which,const char*name,unsigned index,unsigned*present,unsigned*count){assert(rows&&which<(unsigned)rows->size&&index<=0x7fffffff);CharacterClass*c=rows->items[which];const NamedTable*t=NULL;*present=stashFindPointerConst(c->namedStash,name,&t)?1:0;*count=t?eafSize(&t->pfValues):0;assert(!t||*count);float f=class_GetNamedTableValue(c,name,(int)index);unsigned w;memcpy(&w,&f,4);return w;}
unsigned original_named_variant(const unsigned char*bytes,unsigned size,unsigned begin,unsigned scenario,unsigned char*out){assert(!input&&scenario>=1&&scenario<=6&&size<=8388608);SimpleBuffer*in=calloc(1,sizeof(*in)),*wr=calloc(1,sizeof(*wr));assert(in&&wr);reset();memcpy(in->data,bytes,size);in->filesize=size;in->curposition=begin;CharacterClasses list={0};int sum=0;assert(ParserReadBinaryTable(in,ParseCharacterClasses,&list,&sum)&&in->curposition==(int)size);Vec*v=(Vec*)list.ppClasses;CharacterClass*c=v->items[0];Vec*t=(Vec*)c->ppNamedTables;assert(t&&t->size>1);NamedTable*first=t->items[0],*last=t->items[t->size-1];if(scenario==1)last->pchName=first->pchName;if(scenario==2)first->pfValues=NULL;if(scenario==3)first->pchName="Unknown_Named_Table";if(scenario==4)t->size=0;if(scenario==5)first->pchName="";if(scenario==6){v->size=1;t->size=256;for(unsigned i=0;i<256;i++){NamedTable*n=alloc(sizeof(*n));char*key=alloc(260);memset(key,'x',259);key[256]=(char)('0'+i/100);key[257]=(char)('0'+i/10%10);key[258]=(char)('0'+i%10);key[259]=0;n->pchName=key;n->pfValues=NULL;t->items[i]=n;}}memcpy(wr->data,bytes,begin);wr->curposition=wr->filesize=begin;sum=0;assert(ParserWriteBinaryTable(wr,ParseCharacterClasses,&list,&sum,0,0));unsigned n=wr->filesize;memcpy(out,wr->data,n);reset();free(in);free(wr);return n;}
'''
 for qualified,expected in functions.items():assert sha(small.extract(code,qualified.rsplit(':',1)[1]).encode())==expected
 (work/'named.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'named.c','-lz','-o',work/'named.so'],check=True);lib=C.CDLL(str(work/'named.so'));lib.original_named_open.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p];lib.original_named_value.argtypes=[C.c_uint,C.c_char_p,C.c_uint,C.c_void_p,C.c_void_p];lib.original_named_value.restype=C.c_uint;lib.original_named_variant.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_void_p]
 return lib,{'classes_provider':cp,'stash_provider':sp,'whole_functions_sha256_lf':functions,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'generated_c_sha256':sha(code.encode()),'original_named_finalize_executed':True,'original_named_value_executed':True,'original_empty_value_lookup_executed':False,'runtime_generation':False}
