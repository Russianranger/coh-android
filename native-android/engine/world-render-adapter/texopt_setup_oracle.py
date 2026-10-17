"""Actual historical cache -> original typed readers -> original CLIENT setupTexOpt producer."""
from pathlib import Path
import re
from texopt_full_oracle import create as wire_create
from check_surface_states import states,oracle as state_oracle

def declarations(root):
 root=Path(root);h=(root/'upstream/ouroboros/Common/seq/tricks.h').read_text();t=(root/'upstream/ouroboros/Game/src/render/texEnums.h').read_text();s=(root/'upstream/ouroboros/Game/src/render/thread/rt_state.h').read_text()
 def decl(text,start,end):a=text.index(start);return text[a:text.index(end,a)+len(end)]
 return '\n'.join(['typedef float F32;typedef uint8_t U8;typedef uint32_t U32;typedef F32 Vec2[2];typedef F32 Vec3[3];',decl(h,'typedef enum ModelFlags','} ModelFlags;'),decl(t,'typedef enum TexOptFlags','} TexOptFlags;'),decl(s,'typedef enum BlendModeShader','} BlendModeShader;'),decl(h,'typedef enum BlendIndex','} BlendIndex;'),decl(h,'typedef enum TexOptScrollType','} TexOptScrollType;'),'typedef struct TexOpt TexOpt;',decl(h,'typedef struct ScrollsScales','} ScrollsScales;'),decl(h,'typedef struct TexOptFallback','} TexOptFallback;'),decl(h,'typedef struct TexOpt\n','} TexOpt;')])
def create(root,extract):
 root=Path(root);code=wire_create(root,extract)
 code=code.replace('typedef uint32_t U32;typedef uint8_t U8;typedef float F32;', '#include <stddef.h>\n#include <stdbool.h>\n'+declarations(root))
 code=code.replace('#define offsetof(s,m) 0\n','')
 for kind in ['U8','INT','F32','FLAGS','STRING']:code=code.replace('#define TOK_'+kind+'(s,m,d) TOK_'+('FLAGS' if kind=='FLAGS' else kind)+'_X,0,d','#define TOK_'+kind+'(s,m,d) TOK_'+('FLAGS' if kind=='FLAGS' else kind)+'_X,offsetof(s,m),d')
 for kind in ['CURRENTFILE','TIMESTAMP']:code=code.replace('#define TOK_'+kind+'(s,m) TOK_'+kind+'_X,0,0','#define TOK_'+kind+'(s,m) TOK_'+kind+'_X,offsetof(s,m),0')
 for n in [2,3]:code=code.replace('#define TOK_VEC'+str(n)+'(s,m) TOK_FIXED_ARRAY|TOK_F32_X,0,'+str(n),'#define TOK_VEC'+str(n)+'(s,m) TOK_FIXED_ARRAY|TOK_F32_X,offsetof(s,m),'+str(n))
 code=code.replace('#define TOK_EMBEDDEDSTRUCT(s,m,t) TOK_STRUCT_X,0,0,t','#define TOK_EMBEDDEDSTRUCT(s,m,t) TOK_STRUCT_X,offsetof(s,m),0,t')
 # Remove observer output; genuine private heap storage reproduces original indirect strings/zero allocation.
 code=re.sub(r'static FILE\*observer;.*?static int SimpleBufRead\(', 'static int SimpleBufRead(',code,flags=re.S)
 a=code.index('static void*TokenStoreAlloc(');b=code.index('int ParserReadBinaryTable(',a)
 code=code[:a]+r'''static void*TokenStoreAlloc(ParseTable*t,int c,void*s,int i,intptr_t p,void*a,void*b){(void)i;(void)p;(void)a;(void)b;return(char*)s+t[c].storeoffset;}
static void TokenStoreSetInt(ParseTable*t,int c,void*s,int i,int v){memcpy((char*)s+t[c].storeoffset+i*4,&v,4);}
static void TokenStoreSetU8(ParseTable*t,int c,void*s,int i,U8 v){memcpy((char*)s+t[c].storeoffset+i,&v,1);}
static void TokenStoreSetF32(ParseTable*t,int c,void*s,int i,F32 v){memcpy((char*)s+t[c].storeoffset+i*4,&v,4);}
static void TokenStoreSetString(ParseTable*t,int c,void*s,int i,char*v,void*a,void*b){(void)i;(void)a;(void)b;char**slot=(char**)((char*)s+t[c].storeoffset);free(*slot);*slot=NULL;if(*v){size_t n=strlen(v);*slot=malloc(n+1);assert(*slot);memcpy(*slot,v,n+1);}}
'''+code[b:]
 code=code[:code.index('int main(int argc')]
 code+=r'''
extern int seqGetStateNumberFromName(const char*);
static TexOpt*original,*raw_original;static unsigned*diagnostics;static TexOpt*stash[32768];
static int fold(int c){return c>='A'&&c<='Z'?c+32:c;}
static int stricmp(const char*a,const char*b){for(;*a&&*b;a++,b++){int d=fold((unsigned char)*a)-fold((unsigned char)*b);if(d)return d;}return(unsigned char)*a-(unsigned char)*b;}
static int strnicmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){int d=fold((unsigned char)a[i])-fold((unsigned char)b[i]);if(d||!a[i]||!b[i])return d;}return 0;}
static const char*strstriConst(const char*s,const char*k){for(;*s;s++)if(!strnicmp(s,k,strlen(k)))return s;return NULL;}
static char*ParserAllocString(const char*s){size_t n=strlen(s);char*p=malloc(n+1);assert(p);memcpy(p,s,n+1);return p;}
static char*allocAddSharedString(const char*s){return ParserAllocString(s);}
static unsigned hashname(const char*s){unsigned h=2166136261u;for(;*s;s++)h=(h^(unsigned)fold((unsigned char)*s))*16777619u;return h&32767;}
static int add_stash(const char*key,TexOpt*value){unsigned h=hashname(key);for(unsigned i=0;i<32768;i++){unsigned k=(h+i)&32767;if(!stash[k]){stash[k]=value;return 1;}if(!stricmp(stash[k]->name,key))return 0;}abort();}
static int find_stash(const char*key,TexOpt**out){unsigned h=hashname(key);for(unsigned i=0;i<32768;i++){unsigned k=(h+i)&32767;if(!stash[k])return 0;if(!stricmp(stash[k]->name,key)){*out=stash[k];return 1;}}abort();}
#define MAX_PATH 260
#define SERVER 0
#define CLIENT 1
#define StructFreeStringConst(s) free((void*)(s))
#define isSharedMemory(s) ((void)(s),false)
#define onlyfulldebugdevassert(s) assert(s)
#define stashAddPointer(table,key,value,overwrite) add_stash(key,value)
#define stashFindPointer(table,key,out) find_stash(key,out)
#define ErrorFilenamef(...) ((void)diagnostics[tex-original]++)
#define Errorf(...) ((void)diagnostics[tex-original]++)
#define ErrorFilenameDup(a,b,c,d) ((void)(a),(void)(b),(void)(c),(void)(d),(void)diagnostics[tex-original]++)
#define setVec3(v,a,b,c) ((v)[0]=(a),(v)[1]=(b),(v)[2]=(c))
#define copyVec3(src,dst) (((dst)[0])=((src)[0]),((dst)[1])=((src)[1]),((dst)[2])=((src)[2]))
#define scaleVec3(v,s,r) ((r)[0]=(v)[0]*(s),(r)[1]=(v)[1]*(s),(r)[2]=(v)[2]*(s))
'''
 src=(root/'upstream/ouroboros/Common/seq/tricks.c').read_text();util=(root/'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils.c').read_text()
 code+='\n'.join([extract(util,'int strStartsWith('),extract(util,'int strEndsWith('),extract(src,'TexOptFlags texOptFlagsFromName('),extract(src,'static bool texOptNeedsMultiTex('),next(x for x in src.splitlines() if x.startswith('#define SAFE_STRUCT_FREE_STRING_CONST')),extract(src,'static void setupTexOpt(')])
 code+=r'''
static void clone_strings(ParseTable*t,void*object){for(unsigned i=0;t[i].type;i++){if(t[i].type&TOK_REDUNDANTNAME)continue;char*base=(char*)object+t[i].storeoffset;unsigned type=TOK_GET_TYPE(t[i].type);if(type==TOK_STRUCT_X)clone_strings(t[i].subtable,base);else if(type==TOK_STRING_X){int earlier=0;for(unsigned j=0;j<i;j++)if(TOK_GET_TYPE(t[j].type)==TOK_STRING_X&&t[j].storeoffset==t[i].storeoffset)earlier=1;if(!earlier){char*s;memcpy(&s,base,sizeof(s));if(s){s=ParserAllocString(s);memcpy(base,&s,sizeof(s));}}}}}
void original_setup_initialize(const unsigned char*body,size_t n){arrays[0].readbin=nonarray_readbin;arrays[1].readbin=fixedarray_readbin;types[1].readbin=u8_readbin;types[2].readbin=int_readbin;types[3].readbin=float_readbin;types[4].readbin=string_readbin;types[5].readbin=struct_readbin;Buffer b={(unsigned char*)body,n,28};U32 list_size,top,count;assert(SimpleBufReadU32(&list_size,&b));SimpleBufSeek(&b,list_size,SEEK_CUR);assert(SimpleBufReadU32(&top,&b)&&top==b.size-b.pos&&SimpleBufReadU32(&count,&b)&&count==14715);original=calloc(count,sizeof(*original));diagnostics=calloc(count,sizeof(*diagnostics));assert(original&&diagnostics);for(U32 i=0;i<count;i++){int sum=0;assert(ParserReadBinaryTable(&b,parse_tex_opt,original+i,&sum));}raw_original=calloc(count,sizeof(*raw_original));assert(raw_original);memcpy(raw_original,original,count*sizeof(*original));for(U32 i=0;i<count;i++)clone_strings(parse_tex_opt,raw_original+i);for(U32 i=count;i>0;i--){TexOpt*t=original+i-1;if(i-1==10499)continue;for(const unsigned char*p=(unsigned char*)t->name;*p;p++)assert(*p>=32&&*p<=126);assert(strlen(t->name)<260);setupTexOpt(t,false);}}
const TexOpt*original_raw_record(unsigned i){assert(i<14715);return raw_original+i;}
const TexOpt*original_setup_record(unsigned i){assert(i<14715);return original+i;}
unsigned original_setup_diagnostics(unsigned i){return diagnostics[i];}
unsigned original_setup_owner(unsigned i){TexOpt*found=NULL;assert(find_stash(original[i].name,&found));return(unsigned)(found-original);}
static int compare_table(ParseTable*t,const void*a,const void*b){for(unsigned i=0;t[i].type;i++){if(t[i].type&TOK_REDUNDANTNAME)continue;const unsigned char*x=(const unsigned char*)a+t[i].storeoffset,*y=(const unsigned char*)b+t[i].storeoffset;unsigned type=TOK_GET_TYPE(t[i].type);size_t n=t[i].type&TOK_FIXED_ARRAY?(size_t)t[i].param:1;if(type==TOK_STRUCT_X){if(!compare_table(t[i].subtable,x,y))return 0;}else if(type==TOK_STRING_X){const char*xs;const char*ys;memcpy(&xs,x,sizeof(xs));memcpy(&ys,y,sizeof(ys));if(!!xs!=!!ys||(xs&&strcmp(xs,ys)))return 0;}else if(memcmp(x,y,n*(type==TOK_U8_X?1:4)))return 0;}return 1;}
int original_setup_compare(unsigned i,const TexOpt*actual){const TexOpt*expected=original+i;if(!compare_table(parse_tex_opt,actual,expected))return 0;const ScrollsScales*a=&actual->scrollsScales,*b=&expected->scrollsScales;return actual->surface==expected->surface&&!memcmp(a->rgba3,b->rgba3,4)&&!memcmp(a->rgba4,b->rgba4,4)&&!memcmp(a->specularRgba1,b->specularRgba1,4)&&!memcmp(a->specularRgba2,b->specularRgba2,4)&&!memcmp(&a->specularExponent1,&b->specularExponent1,4)&&!memcmp(&a->specularExponent2,&b->specularExponent2,4)&&!memcmp(a->diffuseScale,b->diffuseScale,12)&&!memcmp(a->ambientScale,b->ambientScale,12)&&actual->scrollsScales.debug_backpointer==actual;}
static void clear_table(ParseTable*t,void*object){for(unsigned i=0;t[i].type;i++){if(t[i].type&TOK_REDUNDANTNAME)continue;char*base=(char*)object+t[i].storeoffset;unsigned type=TOK_GET_TYPE(t[i].type);if(type==TOK_STRUCT_X)clear_table(t[i].subtable,base);else if(type==TOK_STRING_X){char*str;memcpy(&str,base,sizeof(str));free(str);str=NULL;memcpy(base,&str,sizeof(str));}}}
void original_setup_destroy(void){for(unsigned i=0;i<14715;i++){clear_table(parse_tex_opt,original+i);clear_table(parse_tex_opt,raw_original+i);}free(raw_original);free(original);free(diagnostics);}
'''
 return code
