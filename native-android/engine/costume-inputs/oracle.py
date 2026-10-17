"""Whole original Parse6 table readers/writers; explicit host storage adapters."""
import ctypes as C,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PATHS=['Common/gameData/BodyPart.c','Common/gameData/BodyPart.h','Common/gameData/costume_data.c','Common/gameData/costume_data.h','Common/seq/bones.h','libs/UtilitiesLib/src/utils/textparser.c','libs/UtilitiesLib/src/utils/serialize.c','libs/UtilitiesLib/src/utils/tokenstore.c','libs/UtilitiesLib/src/utils/structInternals.c','libs/UtilitiesLib/include/utilitieslib/utils/textparser.h','libs/UtilitiesLib/include/utilitieslib/utils/tokenstore.h','libs/UtilitiesLib/include/utilitieslib/utils/serialize.h','libs/UtilitiesLib/include/utilitieslib/utils/structTokenizer.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text,name):
 m=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*)?\s*\{',text,re.M)
 if not m:raise ValueError(name)
 at=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def build(root,work):
 texts={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in PATHS};pins={p:sha(t.encode())for p,t in texts.items()};assert pins==json.loads((HERE/'source-pins.json').read_text())
 funcs={};tables={}
 def f(path,name):
  t=extract(texts[path],name);funcs[path+':'+name]=sha(t.encode());return t
 def table(path,name):
  t=re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',texts[path],re.S).group();tables[name]=sha(t.encode());return t+'\n'
 enum=re.search(r'typedef enum\s*\{\s*TOK_IGNORE,.*?} StructTokenType;',texts[PATHS[9]],re.S).group()
 body=re.search(r'typedef struct BodyPart\b.*?} BodyPart;',texts[PATHS[1]],re.S).group()
 color=re.search(r'typedef struct ColorPalette\b.*?}ColorPalette;',texts[PATHS[3]],re.S).group()
 code='''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "coh_costume_inputs.h"
typedef uint32_t U32;typedef uint16_t U16;typedef uint8_t U8;typedef float F32;typedef float Vec3[3];typedef int BoneId;typedef uint32_t StructTypeField;
#define devassert assert
#define INLINEDBG inline
#define endianSwapIfBig(type,v) (v)
#define SAFESTR(x) x,sizeof(x)
#define MAX_STRING_LENGTH (300*40)
#define TOK_TYPE_MASK 255
#define TOK_GET_TYPE(t) ((t)&255)
#define TOK_REDUNDANTNAME (1u<<8)
#define TOK_STRUCTPARAM (1u<<9)
#define TOK_EARRAY (1u<<20)
#define TOK_FIXED_ARRAY (1u<<21)
#define TOK_INDIRECT (1u<<22)
#define TOK_POOL_STRING (1u<<23)
#define TOK_STORAGE_DIRECT_SINGLE 1
#define TOK_STORAGE_DIRECT_FIXEDARRAY 2
#define TOK_STORAGE_DIRECT_EARRAY 4
#define TOK_STORAGE_INDIRECT_SINGLE 8
#define FORALL_PARSEINFO(p,i) for(i=0;(p[i].name&&p[i].name[0])||p[i].type;i++)
'''+enum+'\n'+body+'\n'+color+'''
typedef struct{const BodyPart**bodyParts;}BodyPartList;
typedef struct ParseTable{const char*name;U32 type;size_t offset;intptr_t param;struct ParseTable*subtable;}ParseTable;
typedef ParseTable TokenizerParseInfo;
#define TOK_INT(s,m,d) TOK_INT_X,offsetof(s,m),d
#define TOK_STRING(s,m,d) TOK_INDIRECT|TOK_STRING_X,offsetof(s,m),d
#define TOK_CURRENTFILE(s,m) TOK_INDIRECT|TOK_CURRENTFILE_X,offsetof(s,m),0
#define TOK_BOOLFLAG(s,m,d) TOK_BOOLFLAG_X,offsetof(s,m),d
#define TOK_STRUCT(s,m,t) TOK_INDIRECT|TOK_EARRAY|TOK_STRUCT_X,offsetof(s,m),sizeof(**((s*)0)->m),t
'''+''.join(table(PATHS[0],n)for n in ('ParseBodyPart','ParseBodyPartBegin'))+''.join(table(PATHS[2],n)for n in ('ParseColor','ParseColorPalette'))+'''
typedef struct{char data[65536];int filesize,curposition;}SimpleBuffer;typedef SimpleBuffer*SimpleBufHandle;
static void SimpleBufResizeEx(SimpleBufHandle b,int n){(void)b;assert(n>=0&&n<=65536);}
'''+''.join(f(PATHS[6],n)for n in ('SimpleBufRead','SimpleBufWrite','SimpleBufSeek','SimpleBufTell'))
 for name in ('SimpleBufReadU16','SimpleBufReadU32','SimpleBufReadF32','SimpleBufWriteU16','SimpleBufWriteU32','SimpleBufWriteF32'):code+=f(PATHS[11],name)
 code+=''.join(f(PATHS[6],n)for n in ('ReadPascalString','WritePascalString'))
 code+='''
typedef struct{int size;void*items[256];}Vec;
static unsigned raw_int_count;static U32 raw_ints[1024];static void*allocations[2048];static unsigned allocation_count;
static void*alloc(size_t n){assert(allocation_count<2048);void*p=calloc(1,n);assert(p);allocations[allocation_count++]=p;return p;}
static void reset(void){while(allocation_count)free(allocations[--allocation_count]);raw_int_count=0;}
static void*field(ParseTable*t,int c,const void*p){return (char*)p+t[c].offset;}
static void TokenStoreSetCapacity(ParseTable*t,int c,void*p,int n){assert(n>=0&&n<=256);Vec*v=alloc(sizeof(*v));v->size=n;*(void**)field(t,c,p)=v;}
static void*TokenStoreAlloc(ParseTable*t,int c,void*p,int i,size_t n,void*a,void*b){(void)a;(void)b;Vec*v=*(Vec**)field(t,c,p);assert(v&&i>=0&&i<v->size);v->items[i]=alloc(n);return v->items[i];}
static void*TokenStoreGetPointer(ParseTable*t,int c,const void*p,int i){Vec*v=*(Vec**)field(t,c,p);assert(v&&i>=0&&i<v->size);return v->items[i];}
static int TokenStoreGetNumElems(ParseTable*t,int c,const void*p){Vec*v=*(Vec**)field(t,c,p);return v?v->size:0;}
static void TokenStoreSetInt(ParseTable*t,int c,void*p,int i,int v){assert(raw_int_count<1024);raw_ints[raw_int_count++]=(U32)v;((int*)field(t,c,p))[i]=v;}
static int TokenStoreGetInt(ParseTable*t,int c,const void*p,int i){return ((int*)field(t,c,p))[i];}
static void TokenStoreSetU8(ParseTable*t,int c,void*p,int i,U8 v){((U8*)field(t,c,p))[i]=v;}
static int TokenStoreGetU8(ParseTable*t,int c,const void*p,int i){return ((U8*)field(t,c,p))[i];}
static void TokenStoreSetF32(ParseTable*t,int c,void*p,int i,F32 v){((F32*)field(t,c,p))[i]=v;}
static F32 TokenStoreGetF32(ParseTable*t,int c,const void*p,int i){return ((F32*)field(t,c,p))[i];}
static void TokenStoreSetString(ParseTable*t,int c,void*p,int i,const char*s,void*a,void*b){(void)i;(void)a;(void)b;size_t n=strlen(s);assert(n<260);char*d=alloc(n+1);memcpy(d,s,n+1);*(void**)field(t,c,p)=d;}
static char*TokenStoreGetString(ParseTable*t,int c,const void*p,int i){(void)i;return *(char**)field(t,c,p);}
'''+f(PATHS[7],'TokenStoreGetStorageType')+'''
typedef struct{int(*readbin)(SimpleBufHandle,ParseTable*,int,void*,int,int*);int(*writebin)(SimpleBufHandle,ParseTable*,int,void*,int,int*,StructTypeField,StructTypeField);}Handler;
static Handler typeinfo(U32);static Handler arrayinfo(U32);
#define TYPE_INFO(t) typeinfo(t)
#define TOKARRAY_INFO(t) arrayinfo(t)
int ParserReadBinaryTable(SimpleBufHandle,ParseTable*,void*,int*);
int ParserWriteBinaryTable(SimpleBufHandle,ParseTable*,void*,int*,StructTypeField,StructTypeField);
'''
 for name in ('int_readbin','int_writebin','u8_readbin','u8_writebin','float_readbin','float_writebin','string_readbin','string_writebin','struct_readbin','struct_writebin','nonarray_readbin','nonarray_writebin','fixedarray_readbin','fixedarray_writebin','earray_readbin','earray_writebin','ParserReadBinaryTable','ParserWriteBinaryTable'):code+=f(PATHS[5],name)
 code+='''
static Handler typeinfo(U32 t){switch(TOK_GET_TYPE(t)){case TOK_INT_X:return(Handler){int_readbin,int_writebin};case TOK_BOOLFLAG_X:return(Handler){u8_readbin,u8_writebin};case TOK_F32_X:return(Handler){float_readbin,float_writebin};case TOK_CURRENTFILE_X:case TOK_STRING_X:return(Handler){string_readbin,string_writebin};case TOK_STRUCT_X:return(Handler){struct_readbin,struct_writebin};case TOK_END:return(Handler){0,0};default:assert(0);return(Handler){0,0};}}
static Handler arrayinfo(U32 t){if(t&TOK_FIXED_ARRAY)return(Handler){fixedarray_readbin,fixedarray_writebin};if(t&TOK_EARRAY)return(Handler){earray_readbin,earray_writebin};return(Handler){nonarray_readbin,nonarray_writebin};}
int original_decode(unsigned kind,const unsigned char*bytes,unsigned size,unsigned begin,unsigned scenario,CohCostumeInput*out,unsigned char*roundtrip,unsigned*end){
 SimpleBuffer in={0},wr={0};BodyPartList parts={0};ColorPalette palette={0};int sum=0;unsigned n,k;memset(out,0,sizeof(*out));assert(size<=65536&&begin<size);memcpy(in.data,bytes,size);in.filesize=size;in.curposition=begin;reset();
 ParseTable*t=kind==1?ParseBodyPartBegin:ParseColorPalette;void*p=kind==1?(void*)&parts:(void*)&palette;int ok=ParserReadBinaryTable(&in,t,p,&sum);if(!ok||in.curposition!=(int)size){reset();return 0;}*end=(unsigned)in.curposition;
 out->kind=kind;
 if(scenario&&kind==1){Vec*v=(Vec*)parts.bodyParts;BodyPart*b=v->items[0];b->influenceCost=-12345;b->num_parts=2;b->dont_clear=255;b->bone_num[0]=-1;b->bodyPartIndex=0x7fffffff;b->name=(char*)"RawDiagnosticPart";}
 if(scenario&&kind==2){Vec*v=(Vec*)palette.color;F32*f=v->items[0];f[0]=1.5f;f[1]=254.9f;f[2]=0.99f;palette.name="RawDiagnosticPalette";}

 if(kind==1){Vec*v=(Vec*)parts.bodyParts;out->part_count=v->size;assert(raw_int_count==out->part_count*6);for(n=0;n<out->part_count;n++){BodyPart*b=v->items[n];CohCostumeInputPart*r=&out->parts[n];strcpy(r->name,b->name);strcpy(r->source_file,b->sourceFile);strcpy(r->geometry_name,b->name_geo);strcpy(r->texture_name,b->name_tex);strcpy(r->base_name,b->base_var);r->bone_count_first=raw_ints[n*6];r->influence_cost=(U32)b->influenceCost;r->bone_count_last=(U32)b->num_parts;r->dont_clear_word=b->dont_clear;r->bones[0]=(U32)b->bone_num[0];r->bones[1]=(U32)b->bone_num[1];r->part_index=(U32)b->bodyPartIndex;}}
 else{Vec*v=(Vec*)palette.color;out->color_count=v->size;strcpy(out->palette_name,palette.name);for(n=0;n<out->color_count;n++)for(k=0;k<3;k++)memcpy(&out->colors[n][k],(F32*)v->items[n]+k,4);}
 sum=0;wr.curposition=begin;wr.filesize=begin;memcpy(wr.data,bytes,begin);ok=ParserWriteBinaryTable(&wr,t,p,&sum,0,0);if(ok){if(!scenario)assert(wr.filesize==(int)size);memcpy(roundtrip,wr.data,wr.filesize);}reset();return ok?wr.filesize:0;
}
unsigned original_result_size(void){return sizeof(CohCostumeInput);}
'''
 (work/'original.c').write_text(code);subprocess.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(HERE),str(work/'original.c'),'-o',str(work/'original.so')],check=True)
 return C.CDLL(str(work/'original.so')),{'source_sha256_lf':pins,'function_sha256_lf':funcs,'table_sha256_lf':tables,'generated_c_sha256':sha(code.encode()),'scope':'Unchanged whole original binary table readers/writers, primitive/array/struct handlers, Pascal serialization and exact two schemas execute on real recovered bodies. Host layout/tokenstore/handler dispatch/bounded SimpleBuf allocation adapters explicit; no whole engine ParseTableCRC/callbacks/32bit ABI or stash builder execution.','original_oracle_sanitized':False}
