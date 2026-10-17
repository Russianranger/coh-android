"""Original table+token-reader observer harness, not original runtime storage/schema CRC."""
from pathlib import Path
TABLES=('Vec2Default1','Vec3Default1','RGBDefault255','parse_rgb3','parse_tex_opt_fallback','parse_tex_opt')
def create(root,extract):
 root=Path(root);source=(root/'upstream/ouroboros/Common/seq/tricks.c').read_text();util=root/'upstream/ouroboros/libs/UtilitiesLib/src/utils';reader=(util/'textparser.c').read_text();serialize=(util/'serialize.c').read_text()
 code=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
typedef uint32_t U32;typedef uint8_t U8;typedef float F32;
typedef struct{unsigned char*b;size_t size,pos;}Buffer;typedef Buffer*SimpleBufHandle;
static FILE*observer;
static void put32(U32 n){unsigned char b[4]={(U8)n,(U8)(n>>8),(U8)(n>>16),(U8)(n>>24)};assert(fwrite(b,1,4,observer)==4);}
static int SimpleBufRead(void*out,size_t n,SimpleBufHandle f){if(n>f->size-f->pos)return 0;memcpy(out,f->b+f->pos,n);f->pos+=n;return(int)n;}
static int SimpleBufReadU16(unsigned short*out,SimpleBufHandle f){U8 b[2];if(!SimpleBufRead(b,2,f))return 0;*out=(unsigned short)(b[0]|b[1]<<8);return 2;}
static int SimpleBufReadU32(U32*out,SimpleBufHandle f){U8 b[4];if(!SimpleBufRead(b,4,f))return 0;*out=(U32)b[0]|(U32)b[1]<<8|(U32)b[2]<<16|(U32)b[3]<<24;return 4;}
static int SimpleBufReadF32(F32*out,SimpleBufHandle f){U32 u;if(!SimpleBufReadU32(&u,f))return 0;memcpy(out,&u,4);return 4;}
static void SimpleBufSeek(SimpleBufHandle f,long n,int origin){assert(origin==SEEK_CUR&&n>=0&&(size_t)n<=f->size-f->pos);f->pos+=(size_t)n;}
static long SimpleBufTell(SimpleBufHandle f){return(long)f->pos;}
'''+extract(serialize,'int ReadPascalString(')+r'''
#define TOK_U8_X 1
#define TOK_INT_X 2
#define TOK_F32_X 3
#define TOK_STRING_X 4
#define TOK_CURRENTFILE_X 4
#define TOK_TIMESTAMP_X 2
#define TOK_FLAGS_X 2
#define TOK_STRUCT_X 5
#define TOK_MATPYR_X 6
#define TOK_FIXED_ARRAY 256
#define TOK_REDUNDANTNAME 512
#define TOK_STRUCTPARAM 1024
#define TOK_END 0
#define TOK_INDIRECT 0
#define TOK_GET_TYPE(t) ((t)&255)
#define TOK_STORAGE_INDIRECT_SINGLE 99
#define TOK_U8(s,m,d) TOK_U8_X,0,d
#define TOK_INT(s,m,d) TOK_INT_X,0,d
#define TOK_F32(s,m,d) TOK_F32_X,0,d
#define TOK_FLAGS(s,m,d) TOK_FLAGS_X,0,d
#define TOK_STRING(s,m,d) TOK_STRING_X,0,d
#define TOK_CURRENTFILE(s,m) TOK_CURRENTFILE_X,0,0
#define TOK_TIMESTAMP(s,m) TOK_TIMESTAMP_X,0,0
#define TOK_VEC2(s,m) TOK_FIXED_ARRAY|TOK_F32_X,0,2
#define TOK_VEC3(s,m) TOK_FIXED_ARRAY|TOK_F32_X,0,3
#define TOK_EMBEDDEDSTRUCT(s,m,t) TOK_STRUCT_X,0,0,t
#define TOK_NULLSTRUCT(t) TOK_STRUCT_X,0,0,t
#define offsetof(s,m) 0
#define TEXOPTSCROLL_NORMAL 0
typedef struct ParseTable{const char*name;int type;int storeoffset;intptr_t param;void*subtable;}ParseTable,TokenizerParseInfo;
static int texblend_flags[]={0},tex_flags[]={0},model_flags[]={0},parse_texopt_scroll_type[]={0};
'''
 for name in TABLES:
  start=source.index('TokenizerParseInfo '+name+'[]');end=source.index('\n};',start)+3;code+=source[start:end]+'\n'
 code+=r'''
typedef int(*ReadBin)(SimpleBufHandle,ParseTable*,int,void*,int,int*);
typedef struct{ReadBin readbin;}TypeInfo;
static TypeInfo types[7],arrays[2];
#define TYPE_INFO(t) types[TOK_GET_TYPE(t)]
#define TOKARRAY_INFO(t) arrays[!!((t)&TOK_FIXED_ARRAY)]
#define FORALL_PARSEINFO(t,i) for((i)=0;(t)[i].name&&(t)[i].type;(i)++)
#define MAX_STRING_LENGTH 12288
#define SAFESTR(s) s,sizeof(s)
static U32 TokenStoreGetStorageType(int type){(void)type;return 0;}
static void*TokenStoreAlloc(ParseTable*t,int c,void*s,int i,intptr_t p,void*a,void*b){(void)t;(void)c;(void)i;(void)p;(void)a;(void)b;return s;}
static void TokenStoreSetInt(ParseTable*t,int c,void*s,int i,int v){(void)t;(void)c;(void)s;(void)i;put32((U32)v);}
static void TokenStoreSetU8(ParseTable*t,int c,void*s,int i,U8 v){(void)t;(void)c;(void)s;(void)i;put32(v);}
static void TokenStoreSetF32(ParseTable*t,int c,void*s,int i,F32 v){U32 n;(void)t;(void)c;(void)s;(void)i;memcpy(&n,&v,4);put32(n);}
static void TokenStoreSetString(ParseTable*t,int c,void*s,int i,char*v,void*a,void*b){(void)t;(void)c;(void)s;(void)i;(void)a;(void)b;put32((U32)strlen(v));assert(fwrite(v,1,strlen(v),observer)==strlen(v));}
int ParserReadBinaryTable(SimpleBufHandle,ParseTable*,void*,int*);
'''
 for name in ['u8_readbin','int_readbin','float_readbin','string_readbin','struct_readbin','nonarray_readbin','fixedarray_readbin']:
  code+=extract(reader,'int '+name+'(')+'\n'
 code+=extract(reader,'int ParserReadBinaryTable(')+r'''
int main(int argc,char**argv){assert(argc==3);types[1].readbin=u8_readbin;types[2].readbin=int_readbin;types[3].readbin=float_readbin;types[4].readbin=string_readbin;types[5].readbin=struct_readbin;arrays[0].readbin=nonarray_readbin;arrays[1].readbin=fixedarray_readbin;FILE*f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0&&n<16*1024*1024);rewind(f);Buffer b={malloc((size_t)n),(size_t)n,28};assert(b.b&&fread(b.b,1,b.size,f)==b.size);fclose(f);U32 list_size;assert(SimpleBufReadU32(&list_size,&b));SimpleBufSeek(&b,list_size,SEEK_CUR);U32 top,count;assert(SimpleBufReadU32(&top,&b)&&top==b.size-b.pos);assert(SimpleBufReadU32(&count,&b)&&count==14715);observer=fopen(argv[2],"wb");assert(observer);put32(count);for(U32 i=0;i<count;i++){int sum=0,dummy=1;put32(i);put32((U32)b.pos);assert(ParserReadBinaryTable(&b,parse_tex_opt,&dummy,&sum));put32((U32)sum);}assert(!fclose(observer));free(b.b);return 0;}
'''
 return code
