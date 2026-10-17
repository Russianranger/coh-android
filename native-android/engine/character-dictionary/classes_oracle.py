"""Original class binary schema prototype; no runtime or global-define CRC claim."""
import ctypes as C,hashlib,importlib.util,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/classes.h','Common/entity/character_attribs.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),"exec"),m.__dict__);return m
def build(root,work):
 origin=module('classes_origin',HERE/'origins_oracle.py');origin.module=module;prior=work/'origin';prior.mkdir();_,proof=origin.build(root,prior);code=(prior/'original-origins.c').read_text();small=module('classes_small',HERE/'../costume-inputs/oracle.py');src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA};tables={}
 # Expand only explicit fixture storage/dispatch adapters, original read/write
 # function bodies remain unchanged. Scalar earrays retain raw words as slots.
 code=code.replace('char data[65536]','char data[8388608]').replace('n<=65536','n<=8388608').replace('allocations[2048]','allocations[262144]').replace('allocation_count<2048','allocation_count<262144').replace('raw_ints[1024]','raw_ints[1048576]').replace('raw_int_count<1024','raw_int_count<1048576')
 for name in('TokenStoreSetInt','TokenStoreGetInt','TokenStoreSetF32','TokenStoreGetF32','TokenStoreSetString','TokenStoreGetString','TokenStoreGetPointer','TokenStoreAlloc'):
  code=code.replace(small.extract(code,name),'')
 code+='\n'
 # Adapter definitions must precede unchanged callers.
 at=code.index('int int_readbin(')
 adapters='''
static void TokenStoreSetInt(ParseTable*t,int c,void*p,int i,int x){if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i<v->size);v->items[i]=(void*)(uintptr_t)(U32)x;}else ((int*)field(t,c,p))[i]=x;}
static int TokenStoreGetInt(ParseTable*t,int c,const void*p,int i){if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i<v->size);return(int)(uintptr_t)v->items[i];}return ((int*)field(t,c,p))[i];}
static void TokenStoreSetF32(ParseTable*t,int c,void*p,int i,F32 x){U32 w;memcpy(&w,&x,4);TokenStoreSetInt(t,c,p,i,(int)w);}
static F32 TokenStoreGetF32(ParseTable*t,int c,const void*p,int i){U32 w=(U32)TokenStoreGetInt(t,c,p,i);F32 x;memcpy(&x,&w,4);return x;}
static void TokenStoreSetString(ParseTable*t,int c,void*p,int i,const char*s,void*a,void*b){(void)a;(void)b;size_t n=strlen(s);assert(n<260);char*d=alloc(n+1);memcpy(d,s,n+1);if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i<v->size);v->items[i]=d;}else *(void**)field(t,c,p)=d;}
static const char*TokenStoreGetString(ParseTable*t,int c,const void*p,int i){if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i<v->size);return v->items[i];}return *(const char**)field(t,c,p);}
static void*TokenStoreGetPointer(ParseTable*t,int c,const void*p,int i){if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i<v->size);return v->items[i];}return *(void**)field(t,c,p);}
static void*TokenStoreAlloc(ParseTable*t,int c,void*p,int i,size_t n,void*a,void*b){(void)a;(void)b;void*x=alloc(n);if(t[c].type&TOK_EARRAY){Vec*v=*(Vec**)field(t,c,p);assert(v&&i<v->size);v->items[i]=x;}else *(void**)field(t,c,p)=x;return x;}
static int*TokenStoreGetCountField(ParseTable*t,int c,void*p){return(int*)((char*)p+t[c].param);}
static void TokenStoreFree(ParseTable*t,int c,void*p,int i){(void)i;*(void**)field(t,c,p)=NULL;}
'''
 code=code[:at]+adapters+code[at:]
 code=code.replace('case TOK_START:case TOK_END:return(Handler)','case TOK_BOOL_X:return(Handler){u8_readbin,u8_writebin};case TOK_POINTER_X:return(Handler){pointer_readbin,pointer_writebin};case TOK_START:case TOK_END:return(Handler)')
 original=(root/'upstream/ouroboros'/small.PATHS[5]).read_text();at=code.index('static Handler typeinfo(U32 t){');code=code[:at]+small.extract(original,'pointer_readbin')+small.extract(original,'pointer_writebin')+code[at:]
 header=src[EXTRA[0]];attrs=src[EXTRA[1]];code+='\n#define bool U8\ntypedef struct PowerCategory PowerCategory;typedef struct PowerDictionary PowerDictionary;typedef void*cStashTable;\n'
 for text,name in [(attrs,'CharacterAttributes'),(attrs,'CharacterAttributesTable'),(header,'NamedTable'),(header,'CharacterClass'),(header,'CharacterClasses')]:
  if name=='CharacterClass':
   for enum in('Category','ClassesDiminish'):code+='\n'+re.search(r'typedef enum '+enum+r'\b.*?} '+enum+';',header,re.S).group()
  code+='\n'+re.search(r'typedef struct '+name+r'\b.*?} '+name+';',text,re.S).group()
 code+='''
#define TOK_STRINGARRAY(s,m) TOK_INDIRECT|TOK_EARRAY|TOK_STRING_X,offsetof(s,m),0
#define TOK_F32ARRAY(s,m) TOK_EARRAY|TOK_F32_X,offsetof(s,m),0
#define TOK_INTARRAY(s,m) TOK_EARRAY|TOK_INT_X,offsetof(s,m),0
#define TOK_AUTOINT(s,m,d) TOK_INT(s,m,d)
#define TOK_F32(s,m,d) TOK_F32_X,offsetof(s,m),((d)==1.0f?0x3f800000:0)
#define TOK_BOOL(s,m,d) TOK_BOOL_X,offsetof(s,m),d
#define TOK_POINTER(s,m,count) TOK_INDIRECT|TOK_POINTER_X,offsetof(s,m),offsetof(s,count)
static ParseTable*ParsePowerDefines[1];static ParseTable*BoolEnum[1];
'''
 for text,name in[(attrs,'ParseCharacterAttributes'),(attrs,'ParseCharacterAttributesTable'),(header,'ParseNamedTable'),(header,'ParseCharacterClass'),(header,'ParseCharacterClasses')]:
  body=re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',text,re.S).group();tables[name]=sha(body.encode());code+='\n'+body
 code+='\nstatic void Errorf(const char*fmt,...){(void)fmt;}\n'
 class_source=(root/'upstream/ouroboros/Common/entity/classes.c').read_text();functions={}
 for name in('classes_GetPtrFromName','classes_GetIndexFromName','classes_GetIndexFromPtr'):
  body=small.extract(class_source,name);functions[name]=sha(body.encode());code+='\n'+body
 code+='''
int original_class_tree(const unsigned char*bytes,unsigned size,unsigned begin,unsigned char*roundtrip,unsigned*counts,unsigned scenario){
 SimpleBuffer*in=calloc(1,sizeof(*in)),*wr=calloc(1,sizeof(*wr));assert(in&&wr&&size<=8388608&&begin<size);CharacterClasses list={0};int sum=0;memcpy(in->data,bytes,size);in->filesize=size;in->curposition=begin;reset();int ok=ParserReadBinaryTable(in,ParseCharacterClasses,&list,&sum);assert(ok&&in->curposition==(int)size);Vec*v=(Vec*)list.ppClasses;assert(v&&v->size<=64);if(scenario){assert(scenario<=3&&v->size);CharacterClass*first=v->items[0];if(scenario==1)first->pchName="Unknown_Class";if(scenario==2&&v->size>1)((CharacterClass*)v->items[v->size-1])->pchName=first->pchName;if(scenario==3)v->size=0;}CharacterClasses lookup={(const CharacterClass**)v->items};counts[0]=v->size;for(int i=0;i<v->size;i++){CharacterClass*d=v->items[i];counts[1+i]=classes_GetIndexFromName(&lookup,d->pchName);assert(counts[1+i]==(U32)classes_GetIndexFromPtr(&lookup,classes_GetPtrFromName(&lookup,d->pchName)));}wr->curposition=begin;wr->filesize=begin;memcpy(wr->data,bytes,begin);sum=0;ok=ParserWriteBinaryTable(wr,ParseCharacterClasses,&list,&sum,0,0);if(ok)memcpy(roundtrip,wr->data,wr->filesize);unsigned result=ok?wr->filesize:0;reset();free(in);free(wr);return result;
}
'''
 for qualified,expected in proof['small_original_provider']['function_sha256_lf'].items():
  _,name=qualified.rsplit(':',1);assert sha(small.extract(code,name).encode())==expected,(name,'changed')
 (work/'original-classes.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'original-classes.c','-lz','-o',work/'original-classes.so'],check=True);lib=C.CDLL(str(work/'original-classes.so'));lib.original_class_tree.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_uint]
 return lib,{'origin_provider':proof,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'tables_sha256_lf':tables,'whole_lookup_functions_sha256_lf':functions,'generated_c_sha256':sha(code.encode()),'global_define_crc_executed':False,'runtime_callbacks_executed':False}
