"""Unchanged original TexWord readers, cold dictionary, locale and lookup.

Only bounded Buffer/TokenStore/stash/namespace/empty-Basic/UI/platform adapters
are supplied. Layout fixups/composition/OS watches and current CLIENT state are
not qualified. The original readers see complete trusted padded inputs only.
"""
from pathlib import Path
import re
import hashlib

FUNCTIONS = {
 'Game/src/render/texWords.c': ['texWordsNameCmp','texWordFind','texWordsLoadInfo','texWordsLoad'],
 'Game/src/render/tex.c': ['texFixName','texFind'],
 'libs/UtilitiesLib/src/utils/textparser.c': ['u8_readbin','int_readbin','float_readbin',
  'string_readbin','struct_readbin','nonarray_readbin','fixedarray_readbin','earray_readbin','ParserReadBinaryTable'],
 'libs/UtilitiesLib/src/utils/serialize.c': ['ReadPascalString'],
 'libs/UtilitiesLib/src/utils/utils.c': ['strStartsWith'],
 'libs/UtilitiesLib/src/utils/utils_opt.c': ['getFileName'],
}


def extract(text, name):
 match=re.search(r'^[\w \t*]+\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*\n\s*)?\{',text,re.M)
 if not match:raise ValueError('original TexWord function '+name)
 at=text.index('{',match.start());depth=0;mode='code'
 while at<len(text):
  char=text[at];pair=text[at:at+2]
  if mode=='code':
   if pair=='//':mode='line';at+=2;continue
   if pair=='/*':mode='comment';at+=2;continue
   if char in ('"',"'"):mode=char
   elif char=='{':depth+=1
   elif char=='}':
    depth-=1
    if not depth:return text[match.start():at+1]+'\n'
  elif mode=='line':
   if char=='\n':mode='code'
  elif mode=='comment':
   if pair=='*/':mode='code';at+=2;continue
  elif char=='\\':at+=2;continue
  elif char==mode:mode='code'
  at+=1
 raise ValueError('unclosed original TexWord function')


def create(root):
 root=Path(root)
 sources={p:(root/'upstream/ouroboros'/p).read_bytes().replace(b'\r\n',b'\n').decode() for p in FUNCTIONS}
 bodies={n:extract(sources[p],n) for p,names in FUNCTIONS.items() for n in names}
 source=sources['Game/src/render/texWords.c']
 start=source.index('TokenizerParseInfo ParseDropShadow[] =')
 end=source.index('TokenizerParseInfo ParseTexWordFiles[] =',start);end=source.index('\n};',end)+3
 tables=source[start:end]+'\n'
 code=r'''
#include "tests/texwords_fixture.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdbool.h>
typedef uint8_t U8;typedef uint32_t U32;typedef float F32;
typedef struct{unsigned char*b;size_t size,pos;}Buffer;typedef Buffer*SimpleBufHandle;
static int SimpleBufRead(void*out,size_t n,SimpleBufHandle f){if(n>f->size-f->pos)return 0;memcpy(out,f->b+f->pos,n);f->pos+=n;return(int)n;}
static int SimpleBufReadU16(unsigned short*out,SimpleBufHandle f){U8 b[2];if(!SimpleBufRead(b,2,f))return 0;*out=(unsigned short)(b[0]|b[1]<<8);return 2;}
static int SimpleBufReadU32(U32*out,SimpleBufHandle f){U8 b[4];if(!SimpleBufRead(b,4,f))return 0;*out=(U32)b[0]|(U32)b[1]<<8|(U32)b[2]<<16|(U32)b[3]<<24;return 4;}
static int SimpleBufReadF32(F32*out,SimpleBufHandle f){U32 v;if(!SimpleBufReadU32(&v,f))return 0;memcpy(out,&v,4);return 4;}
static long SimpleBufTell(SimpleBufHandle f){return(long)f->pos;}
static int SimpleBufSeek(SimpleBufHandle f,long offset,int origin){assert(origin==SEEK_CUR&&offset>=0&&(size_t)offset<=f->size-f->pos);f->pos+=(size_t)offset;return 0;}
'''+bodies['ReadPascalString']+r'''
#define TOK_U8_X 1
#define TOK_INT_X 2
#define TOK_F32_X 3
#define TOK_STRING_X 4
#define TOK_STRUCT_X 5
#define TOK_MATPYR_X 6
#define TOK_FUNCTIONCALL_X 6
#define TOK_FIXED_ARRAY 256
#define TOK_EARRAY 2048
#define TOK_REDUNDANTNAME 512
#define TOK_STRUCTPARAM 1024
#define TOK_END 0
#define TOK_IGNORE 0
#define TOK_GET_TYPE(t) ((t)&255)
#define TOK_STORAGE_INDIRECT_SINGLE 99
#define TOK_U8(s,m,d) TOK_U8_X,0,d
#define TOK_BOOLFLAG(s,m,d) TOK_U8_X,0,d
#define TOK_INT(s,m,d) TOK_INT_X,0,d
#define TOK_F32(s,m,d) TOK_F32_X,0,d
#define TOK_STRING(s,m,d) TOK_STRING_X,0,d
#define TOK_CURRENTFILE(s,m) TOK_STRING_X,0,0
#define TOK_VEC2(s,m) TOK_FIXED_ARRAY|TOK_F32_X,0,2
#define TOK_INTARRAY(s,m) TOK_EARRAY|TOK_INT_X,0,0
#define TOK_STRUCT(s,m,t) TOK_EARRAY|TOK_STRUCT_X,0,0,t
#define TOK_EMBEDDEDSTRUCT(s,m,t) TOK_STRUCT_X,0,0,t
#define TOK_NULLSTRUCT(t) TOK_STRUCT_X,0,0,t
typedef struct ParseTable{const char*name;int type;int storeoffset;intptr_t param;void*subtable;}ParseTable,TokenizerParseInfo;
static int ParseTexWordLayerType[]={0},ParseTexWordLayerStretch[]={0},ParseTexWordFilterType[]={0},ParseTexWordBlendType[]={0};
'''+tables+r'''
typedef struct TexWord{char*name;uint32_t ordinal,offset,bytes;}TexWord;
typedef struct TexWordList{TexWord**texWords;}TexWordList;
typedef struct BasicTexture{int unused;}BasicTexture;
static TexWordList texWords_list;static TexWord**fixture_words;static uint32_t fixture_count;
static TexWordsOracleStats fixture_stats;
static int dummy_object;
typedef int(*ReadBin)(SimpleBufHandle,ParseTable*,int,void*,int,int*);
typedef struct{ReadBin readbin;}TypeInfo;
static TypeInfo types[7],arrays[3];
#define TYPE_INFO(t) types[TOK_GET_TYPE(t)]
#define TOKARRAY_INFO(t) arrays[((t)&TOK_EARRAY)?2:!!((t)&TOK_FIXED_ARRAY)]
#define FORALL_PARSEINFO(t,i) for((i)=0;(t)[i].name&&((t)[i].type||(t)[i].name[0]);(i)++)
#define MAX_STRING_LENGTH 12000
#define SAFESTR(s) s,sizeof(s)
static U32 TokenStoreGetStorageType(int t){(void)t;return 0;}
static void TokenStoreSetCapacity(ParseTable*t,int column,void*object,int n){
 (void)column;(void)object;assert(n>0&&n<=4096);
 if(t==ParseTexWordFiles){assert(!fixture_words);fixture_count=(uint32_t)n;fixture_words=calloc((size_t)n,sizeof(*fixture_words));assert(fixture_words);}
}
static void*TokenStoreAlloc(ParseTable*t,int column,void*object,int i,intptr_t size,void*a,void*b){
 (void)column;(void)object;(void)size;(void)a;(void)b;
 if(t==ParseTexWordFiles){assert(i>=0&&(uint32_t)i<fixture_count&&!fixture_words[i]);TexWord*w=calloc(1,sizeof(*w));assert(w);w->ordinal=(uint32_t)i;fixture_words[i]=w;return w;}
 return &dummy_object;
}
static void TokenStoreSetInt(ParseTable*t,int c,void*s,int i,int v){(void)t;(void)c;(void)s;(void)i;(void)v;}
static void TokenStoreSetU8(ParseTable*t,int c,void*s,int i,U8 v){(void)t;(void)c;(void)s;(void)i;(void)v;}
static void TokenStoreSetF32(ParseTable*t,int c,void*s,int i,F32 v){(void)t;(void)c;(void)s;(void)i;(void)v;}
static void TokenStoreSetString(ParseTable*t,int column,void*object,int i,char*value,void*a,void*b){
 (void)i;(void)a;(void)b;if(t==ParseTexWord&&column==1){TexWord*w=object;size_t n=strlen(value);assert(!w->name);w->name=malloc(n+1);assert(w->name);memcpy(w->name,value,n+1);}
}
int ParserReadBinaryTable(SimpleBufHandle,ParseTable*,void*,int*);
'''
 for name in ['u8_readbin','int_readbin','float_readbin','string_readbin','struct_readbin','nonarray_readbin','fixedarray_readbin','earray_readbin']:
  code+=bodies[name]
 code+='#define ParserReadBinaryTable original_table_read\n'+bodies['ParserReadBinaryTable']+'#undef ParserReadBinaryTable\n'
 code+=r'''
int ParserReadBinaryTable(SimpleBufHandle file,ParseTable*t,void*object,int*sum){
 fixture_stats.nodes++;for(unsigned i=0;t[i].type||t[i].name[0];i++)if(TOK_GET_TYPE(t[i].type))fixture_stats.fields++;
 unsigned offset=(unsigned)file->pos;int before=*sum;int ok=original_table_read(file,t,object,sum);
 if(t==ParseTexWord){TexWord*w=object;w->offset=offset+4;w->bytes=(unsigned)(*sum-before)-4;}
 return ok;
}
static int fold(int x){return x>='A'&&x<='Z'?x+32:x;}
static int stricmp(const char*a,const char*b){for(;*a&&*b;a++,b++){int d=fold((unsigned char)*a)-fold((unsigned char)*b);if(d)return d;}return(unsigned char)*a-(unsigned char)*b;}
static int strnicmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){int d=fold((unsigned char)a[i])-fold((unsigned char)b[i]);if(d||!a[i]||!b[i])return d;}return 0;}
static void forwardSlashes(char*s){for(;*s;s++)if(*s=='\\')*s='/';}
'''+bodies['strStartsWith']+bodies['getFileName']+r'''
#define MAX_PATH 260
#define Strncpyt(dst,src) strncpyt((dst),(src),sizeof(dst))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof(*(a)))
static void strncpyt(char*dst,const char*src,size_t n){assert(n);size_t count=strlen(src);if(count>=n)count=n-1;memcpy(dst,src,count);dst[count]=0;}
typedef struct Entry{char key[260];TexWord*word;int live;}Entry;
typedef Entry*StashElement;
typedef struct Dictionary{Entry entries[4096];unsigned count;}Dictionary;
static Dictionary *htTexWords;
static void *g_basicTextures_ht=(void*)1;static BasicTexture**g_basicTextures;
static const CohWrTexNamespace *query_namespace;static uint32_t namespace_queries;
static BasicTexture presence;
static Dictionary*stashTableCreateWithStringKeys(int n,int mode){assert(n==16&&mode==1);Dictionary*d=calloc(1,sizeof(*d));assert(d);return d;}
static void stashTableDestroy(Dictionary*d){free(d);}
static int stashFindElement(Dictionary*d,const char*key,StashElement*out){*out=NULL;for(unsigned i=0;i<d->count;i++)if(d->entries[i].live&&!stricmp(d->entries[i].key,key)){*out=d->entries+i;return 1;}return 0;}
static void*stashElementGetPointer(StashElement e){assert(e&&e->live);return e->word;}
static int stashRemovePointer(Dictionary*d,const char*key,void*out){assert(!out);StashElement e;int found=stashFindElement(d,key,&e);if(found)e->live=0;return found;}
static int stashAddPointer(Dictionary*d,const char*key,TexWord*w,int overwrite){StashElement e;if(stashFindElement(d,key,&e)){if(overwrite)e->word=w;return overwrite;}assert(d->count<4096&&strlen(key)<260);e=d->entries+d->count++;strcpy(e->key,key);e->word=w;e->live=1;return 1;}
static int find_pointer(void*table,const char*key,void*out){
 if(table==g_basicTextures_ht){assert(query_namespace);namespace_queries++;CohWrTexNamespaceBasic b;CohStatus status=coh_wr_tex_namespace_find(query_namespace,key,&b);assert(status==COH_OK||status==COH_NOT_FOUND);*(BasicTexture**)out=status==COH_OK?&presence:NULL;return status==COH_OK;}
 StashElement e;int found=stashFindElement(table,key,&e);*(TexWord**)out=found?e->word:NULL;return found;
}
#define stashFindPointer(table,key,out) find_pointer((table),(key),(out))
#define StashDeepCopyKeys 1
#define TEX_TGA 32
#define TEX_JPEG 8192
#define TEX_DDS 64
'''+bodies['texFixName']+bodies['texFind']+r'''
static struct{int texWordEdit,texWordVerbose;}game_state;
static char texWordsLocale[MAX_PATH],texWordsLocale2[MAX_PATH],fixture_search[80];
static int production,region,g_allow_loading=1,numTexWordsInThread,texWordsNeedsReload,texWord_doNotYield,yield_amount;
#define REGION_EU 1
#define INIT_YIELD_AMOUNT 1
#define OUTPUT_VERBOSE 1
#define FOLDER_CACHE_CALLBACK_UPDATE 1
static int isProductionMode(void){return production;}
static int getCurrentRegion(void){return region;}
static int getNumRealCpus(void){return 1;}
static int getNumVirtualCpus(void){return 1;}
static void texSetSearchPath(char*s){assert(strlen(s)<sizeof(fixture_search));strcpy(fixture_search,s);}
static void texCheckSwapList(void){}
static void texWordsEdit_reloadCallback(void){}
static void reloadTexWordCallback(void){}
static void FolderCacheSetCallback(int mode,const char*pattern,void(*fn)(void)){assert(mode==1&&!strcmp(pattern,"texts/*.texword")&&fn==reloadTexWordCallback);}
static void writeConsole(int mode,const char*format,...){(void)mode;(void)format;}
static void fixture_error(void){}
#define Errorf(...) fixture_error()
static int eaSize(void*slot){if(slot==&texWords_list.texWords)return(int)fixture_count;assert(slot==&g_basicTextures);return 0;}
static void ParserDestroyStruct(ParseTable*t,void*object){assert(t==ParseTexWordFiles&&object==&texWords_list);texWords_list.texWords=NULL;}
static int texWordsPreprocessor(ParseTable*t,void*object){(void)t;(void)object;abort();return 0;}
static void fixture_load(ParseTable*t,void*object,const char*cache){assert(t==ParseTexWordFiles&&object==&texWords_list&&cache&&!strcmp(cache,"texWords.bin"));texWords_list.texWords=fixture_words;}
#define ParserLoadFiles(folder,extension,cache,flags,table,object,a,b,preprocessor) fixture_load((table),(object),(cache))
static void texFree(BasicTexture*b,int type){(void)b;(void)type;abort();}
'''
 # The original cold Basic loop must compile unchanged, but cannot execute:
 # the fixture has no previous Basic table or GPU resources to reload.
 code=code.replace('typedef struct BasicTexture{int unused;}BasicTexture;',
  'typedef struct BasicTexture{struct{char*layoutName;}*texWordParams;TexWord*texWord;char*name;int hasBeenComposited;}BasicTexture;')
 for name in ['texWordsNameCmp','texWordFind','texWordsLoadInfo','texWordsLoad']:
  code+=bodies[name]
 code+=r'''
void original_texwords_initialize(CohBytes bytes){
 assert(!fixture_words&&!htTexWords&&bytes.size>=36);memset(&fixture_stats,0,sizeof(fixture_stats));
 types[1].readbin=u8_readbin;types[2].readbin=int_readbin;types[3].readbin=float_readbin;types[4].readbin=string_readbin;types[5].readbin=struct_readbin;
 arrays[0].readbin=nonarray_readbin;arrays[1].readbin=fixedarray_readbin;arrays[2].readbin=earray_readbin;
 Buffer b={(unsigned char*)(uintptr_t)bytes.data,bytes.size,28};U32 files;assert(SimpleBufReadU32(&files,&b)&&files<=b.size-b.pos);b.pos+=files;
 int sum=0;assert(ParserReadBinaryTable(&b,ParseTexWordFiles,&dummy_object,&sum)&&b.pos==b.size);fixture_stats.records=fixture_count;
}
void original_texwords_configure(const char*locale,uint32_t eu,uint32_t edit,uint32_t prod,uint32_t verbose){
 assert(locale&&strlen(locale)<32&&eu<=1&&edit<=1&&prod<=1&&verbose<=1&&!(edit&&prod));
 production=(int)prod;region=(int)eu;game_state.texWordEdit=(int)edit;game_state.texWordVerbose=(int)verbose;
 texWords_list.texWords=NULL;texWordsLoad((char*)locale);
}
uint32_t original_texwords_find(const CohWrTexNamespace*ns,const char*name,int search,uint32_t*queries){
 query_namespace=ns;namespace_queries=0;TexWord*w=texWordFind(name,search);*queries=namespace_queries;return w?w->ordinal:UINT32_MAX;
}
void original_texwords_record(uint32_t index,TexWordOracleRecord*out){
 assert(index<fixture_count);TexWord*w=NULL;for(uint32_t i=0;i<fixture_count;i++)if(fixture_words[i]->ordinal==index)w=fixture_words[i];assert(w);
 *out=(TexWordOracleRecord){{(const uint8_t*)w->name,strlen(w->name)},w->offset,w->bytes};
}
void original_texwords_configuration(char a[32],char b[32],char s[80]){assert(strlen(texWordsLocale)<32&&strlen(texWordsLocale2)<32);strcpy(a,texWordsLocale);strcpy(b,texWordsLocale2);strcpy(s,fixture_search);}
TexWordsOracleStats original_texwords_stats(void){return fixture_stats;}
size_t original_texwords_workspace(void){size_t n=sizeof(Dictionary)+(size_t)fixture_count*(sizeof(TexWord*)+sizeof(TexWord));for(uint32_t i=0;i<fixture_count;i++)n+=strlen(fixture_words[i]->name)+1;return n;}
void original_texwords_destroy(void){
 if(htTexWords){stashTableDestroy(htTexWords);htTexWords=NULL;}
 for(uint32_t i=0;i<fixture_count;i++){free(fixture_words[i]->name);free(fixture_words[i]);}
 free(fixture_words);fixture_words=NULL;fixture_count=0;texWords_list.texWords=NULL;
}
'''
 return code,bodies,{'tables_sha256_lf':hashlib.sha256(tables.encode()).hexdigest(),
  'whole_original_token_readers':True,'whole_original_texWordsLoad_LoadInfo_Find':True,
  'source_layout_preprocessor_executed':False,'original_parser_storage_adapters':True,
  'cold_empty_previous_Basic_table':True,'actual_namespace_presence_queries':True,
  'layout_font_image_composition_UI_OS_callbacks_executed':False}
