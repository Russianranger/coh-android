"""Unchanged original tree, traversal and whole cached-header consumer functions.

Storage/file/stash/Win32 wire observers are explicit. The caller supplies an
already ordered immutable provider snapshot, not an observed original CLIENT.
"""
def create(root,extract):
 from pathlib import Path
 root=Path(root);base=root/'upstream/ouroboros'
 node=(base/'libs/UtilitiesLib/src/utils/FolderCacheNode.c').read_text()
 cache=(base/'libs/UtilitiesLib/src/utils/FolderCache.c').read_text()
 files=(base/'libs/UtilitiesLib/src/utils/fileutil.c').read_text()
 tex=(base/'Game/src/render/tex.c').read_text();header=(base/'Game/src/render/tex.h').read_text();enums=(base/'Game/src/render/texEnums.h').read_text()
 signatures=[('FolderNodeAdd',node,'FolderNode *FolderNodeAdd('),('FolderNodeFind',node,'FolderNode *FolderNodeFind('),('FolderNodeRecurseEx',node,'int FolderNodeRecurseEx('),('FolderCacheMatchesIgnorePrefixAnywhere',cache,'bool FolderCacheMatchesIgnorePrefixAnywhere('),('fileScanAllDataDirsHelper',files,'static int fileScanAllDataDirsHelper('),('texFixName',tex,'static int texFixName('),('texFillInBind',tex,'int texFillInBind('),('texLoadHeaderProcessor',tex,'static FileScanAction texLoadHeaderProcessor(')]
 functions={name:extract(source,sig) for name,source,sig in signatures}
 a=header.index('typedef enum TexFlags');flags=header[a:header.index('} TexFlags;',a)+len('} TexFlags;')]
 a=enums.index('typedef enum TexOptFlags');flags+='\n'+enums[a:enums.index('} TexOptFlags;',a)+len('} TexOptFlags;')]
 a=header.index('typedef struct {');wire=header[a:header.index('} TextureFileHeader;',a)+len('} TextureFileHeader;')]
 code=r'''#include "tests/tex_namespace_fixture.h"
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#define FINAL 1
#define MAX_PATH 260
#define MAX_TEX_SIZE 1024
#define _A_SUBDIR 16
#define _A_NORMAL 0
#define FSA_NO_EXPLORE_DIRECTORY 0
#define FSA_EXPLORE_DIRECTORY 1
#define LWC_STAGE_1 1
typedef int FileScanAction;
typedef uint8_t U8;typedef float F32;
'''+flags+'\n'+wire+r'''
_Static_assert(sizeof(TextureFileHeader)==32,"original Win32 cached header wire observer");
struct _finddata32_t{unsigned attrib;char name[260];int size;int32_t time_access,time_create,time_write;};
typedef FileScanAction(*FileScanProcessor)(char*,struct _finddata32_t*);
typedef struct FolderNode FolderNode;
struct FolderNode{FolderNode*next,*prev;int32_t virtual_location;unsigned is_dir,seen_in_fs;int file_index;FolderNode*contents,*contents_tail,*parent;char*name;size_t size;int32_t timestamp;uint32_t oracle_record;};
typedef int(*FolderNodeOpEx)(const char*,FolderNode*,void*);
static FolderNode*tree,*tail;static int folder_cache_debug,update_count,discard_count;
static FolderNode*nodes[262144];static uint32_t node_count;
static char*strings[262144];static uint32_t string_count;
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int stricmp(const char*a,const char*b){while(*a&&*b){int d=(int)fold((unsigned char)*a++)-(int)fold((unsigned char)*b++);if(d)return d;}return(unsigned char)*a-(unsigned char)*b;}
static int strnicmp(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){int d=(int)fold((unsigned char)a[i])-(int)fold((unsigned char)b[i]);if(d||!a[i]||!b[i])return d;}return 0;}
static char*strstri(const char*s,const char*k){for(;*s;s++)if(!strnicmp(s,k,strlen(k)))return(char*)s;return NULL;}
#define strstriConst strstri
static char*allocAddString(const char*s){size_t n=strlen(s)+1;assert(string_count<262144);char*p=malloc(n);assert(p);memcpy(p,s,n);strings[string_count++]=p;return p;}
static FolderNode*FolderNodeCreate(void){assert(node_count<262144);FolderNode*n=calloc(1,sizeof(*n));assert(n);nodes[node_count++]=n;return n;}
static char*firstSlash(char*s){for(;*s;s++)if(*s=='/'||*s=='\\')return s;return NULL;}
static void strcpy_s(char*d,size_t n,const char*s){assert(strlen(s)<n);strcpy(d,s);}
#define ARRAY_SIZE_CHECKED(x) sizeof(x)
typedef int32_t __time32_t;
'''+functions['FolderNodeAdd']+'\n'+functions['FolderNodeFind']+'\n'+functions['FolderNodeRecurseEx']+r'''
static char*ignorePrefixArray[50];static int numIgnorePrefixes;
static void _strlwr_s(char*s,size_t n){assert(strlen(s)<n);for(;*s;s++)*s=(char)fold((unsigned char)*s);}
static void _strupr_s(char*s,size_t n){assert(strlen(s)<n);for(;*s;s++)if(*s>='a'&&*s<='z')*s=(char)(*s-32);}
#define STR_COMBINE_SS(out,a,b) do{assert(strlen(a)+strlen(b)<sizeof(out));strcpy(out,a);strcat(out,b);}while(0)
#define STR_COMBINE_SSS(out,a,b,c) do{assert(strlen(a)+strlen(b)+strlen(c)<sizeof(out));strcpy(out,a);strcat(out,b);strcat(out,c);}while(0)
'''+functions['FolderCacheMatchesIgnorePrefixAnywhere']+r'''
static int devel_dynamic;
static char*getFileName(char*s){char*p=strrchr(s,'/');return p?p+1:s;}
static char*getDirectoryName(char*s){char*p=strrchr(s,'/');assert(p);*p=0;return s;}
'''+functions['fileScanAllDataDirsHelper']+r'''
typedef struct{const char*name,*dirname;uint32_t flags,texopt_flags,texopt_surface;int file_pos,file_bytes,height,width,realHeight,realWidth;char*mipdata;int mipsize,mipid;uint32_t oracle_record;}BasicTexture;
typedef struct{const char*key;BasicTexture*value;}Element;
typedef Element*StashElement;
static Element elements[65536];static uint32_t element_count,element_hash[131072],element_slots[65536];
static uint32_t*element_slot(const char*key){uint32_t h=2166136261u;for(const char*s=key;*s;s++)h=(h^fold((unsigned char)*s))*16777619u;h&=131071u;while(element_hash[h]&&stricmp(elements[element_hash[h]-1].key,key))h=(h+1)&131071u;return element_hash+h;}
static BasicTexture*allocated[65536],*g_basicTextures[65536];static uint32_t allocated_count,basic_count;
static int g_basicTextures_ht;
static int stashFindElement(int unused,const char*key,StashElement*out){(void)unused;uint32_t*slot=element_slot(key);if(!*slot)return 0;*out=elements+*slot-1;return 1;}
static void stashAddPointerAndGetElement(int unused,const char*key,BasicTexture*b,int replace,StashElement*out){(void)unused;assert(!replace&&element_count<65536);uint32_t*slot=element_slot(key);assert(!*slot);element_slots[element_count]=(uint32_t)(slot-element_hash);elements[element_count]=(Element){allocAddString(key),b};*out=elements+element_count;*slot=++element_count;}
static const char*stashElementGetStringKey(StashElement e){return e->key;}
static int stashFindPointer(int unused,const char*key,BasicTexture**out){StashElement e;if(stashFindElement(unused,key,&e)){*out=e->value;return 1;}return 0;}
static BasicTexture*allocate_basic(void){assert(allocated_count<65536);BasicTexture*b=calloc(1,sizeof(*b));assert(b);allocated[allocated_count++]=b;return b;}
#define MP_CREATE(type,n) ((void)0)
#define MP_ALLOC(type) allocate_basic()
static void push_basic(BasicTexture*b){assert(basic_count<65536);g_basicTextures[basic_count++]=b;}
#define eaPush(array,b) push_basic(b)
static int lwc_active,lwc_stage,tex_load_header_count;
static const char*basefolder="texture_library";
static const NamespaceOracleFile*input;static uint32_t input_count,opened_record;
static int LWC_IsActive(void){return lwc_active;}
static int LWC_GetLastCompletedDataStage(void){return lwc_stage;}
static int fileSetLogging(int n){(void)n;return 0;}
static FILE*fileOpen(const char*name,const char*mode){assert(!strcmp(mode,"rbR"));FolderNode*n=FolderNodeFind(tree,name);assert(n&&!n->is_dir&&n->oracle_record<input_count);uint32_t i=n->oracle_record;assert(!stricmp(input[i].path,name)&&input[i].location==n->virtual_location&&input[i].timestamp==n->timestamp&&input[i].file_index==n->file_index);FILE*f=tmpfile();assert(f&&fwrite(input[i].body.data,1,input[i].body.size,f)==input[i].body.size);rewind(f);opened_record=i;assert(allocated_count);allocated[allocated_count-1]->oracle_record=i;return f;}
static void strncpyt(char*d,const char*s,int n){assert(n>0&&strlen(s)<(unsigned)n);strcpy(d,s);}
static void Errorf(const char*fmt,...){(void)fmt;abort();}
static void ErrorFilenamef(const char*file,const char*fmt,...){(void)file;(void)fmt;abort();}
static void FatalErrorFilenamef(const char*file,const char*fmt,...){(void)file;(void)fmt;abort();}
static void FatalErrorf(const char*fmt,...){(void)fmt;abort();}
static int log2i(int n){int power=0,value=1;while(value<n){assert(value<=1073741824);value*=2;power++;}return power;}
typedef struct{uint32_t surface;}TexOpt;
static TexOpt*trickFromTextureDirName(const char*d,const char*n,uint32_t*flags){(void)d;(void)n;*flags=0;return NULL;}
'''+functions['texFixName']+'\n'+functions['texFillInBind']+'\n'+functions['texLoadHeaderProcessor']+r'''
static void add(const NamespaceOracleFile*f){int created=0;char path[260];assert(strlen(f->path)<259);strcpy(path,f->path);if(f->directory)strcat(path,"/");FolderNode*n=FolderNodeAdd(&tree,&tail,NULL,path,f->timestamp,f->body.size,f->location,f->file_index,&created);if(n){n->oracle_record=(uint32_t)(f-input);if(f->directory)n->is_dir=1;}}
void original_namespace(const NamespaceOracleFile*files,uint32_t count,uint32_t mode,uint32_t quickload,const char*const*prefixes,uint32_t prefix_count,uint32_t active,uint32_t stage,const NamespaceOracleBasic*prior,uint32_t prior_count,NamespaceOracleBasic*out,uint32_t*out_count){
 assert(!tree&&!tail&&!node_count&&!string_count&&!allocated_count&&!basic_count&&!element_count&&prefix_count<=50);input=files;input_count=count;lwc_active=(int)active;lwc_stage=(int)stage;numIgnorePrefixes=(int)prefix_count;
 for(uint32_t i=0;i<prefix_count;i++)ignorePrefixArray[i]=allocAddString(prefixes[i]);
 for(unsigned phase=0;phase<2;phase++)for(uint32_t i=0;i<count;i++){
  int fs=files[i].location>=0,want_fs=mode==1?phase==1:phase==0;if(fs!=want_fs)continue;
  if(fs&&(mode==3||(mode==1&&(quickload||strnicmp(files[i].path,"texture_library/",16)))))continue;
  if(!fs&&mode==0&&(FolderCacheMatchesIgnorePrefixAnywhere(files[i].path)||!FolderNodeFind(tree,files[i].path)))continue;
  add(files+i);
 }
 for(uint32_t i=0;i<prior_count;i++){BasicTexture*b=allocate_basic();b->name=allocAddString(prior[i].key);b->dirname=allocAddString(prior[i].directory);StashElement element;if(!stashFindElement(0,b->name,&element))stashAddPointerAndGetElement(0,b->name,b,0,&element);b->name=stashElementGetStringKey(element);push_basic(b);}
 devel_dynamic=mode==1&&!quickload;FolderNode*start=FolderNodeFind(tree,"texture_library");if(start&&start->contents)FolderNodeRecurseEx(start->contents,fileScanAllDataDirsHelper,(void*)texLoadHeaderProcessor,"texture_library");
 for(uint32_t i=0;i<basic_count;i++){
  NamespaceOracleBasic*v=out+i;memset(v,0,sizeof(*v));BasicTexture*b=g_basicTextures[i];strcpy(v->key,b->name);strcpy(v->directory,b->dirname);
  for(uint32_t k=0;k<i;k++)if(!stricmp(out[k].key,v->key)){v->first=k;goto found;}
  v->first=i;
found:
  if(i<prior_count){uint32_t first=v->first;*v=prior[i];v->first=first;continue;}
  const NamespaceOracleFile*f=files+b->oracle_record;FolderNode*n=FolderNodeFind(tree,f->path);assert(n);
  assert(f->body.size>=33);strcpy(v->original,(const char*)f->body.data+32);v->width=(uint32_t)b->width;v->height=(uint32_t)b->height;v->flags=b->flags;v->offset=(uint32_t)b->file_pos;v->bytes=(uint32_t)b->file_bytes;v->location=n->virtual_location;v->timestamp=n->timestamp;v->file_index=n->file_index;v->mip_bytes=(uint32_t)b->mipsize;if(b->mipsize)memcpy(v->mips,b->mipdata,(size_t)b->mipsize);
 }
 *out_count=basic_count;
 for(uint32_t i=0;i<allocated_count;i++){free(allocated[i]->mipdata);free(allocated[i]);}for(uint32_t i=0;i<node_count;i++)free(nodes[i]);for(uint32_t i=0;i<string_count;i++)free(strings[i]);
 for(uint32_t i=0;i<element_count;i++)element_hash[element_slots[i]]=0;
 tree=tail=NULL;node_count=string_count=allocated_count=basic_count=element_count=0;numIgnorePrefixes=devel_dynamic=0;input=NULL;input_count=opened_record=0;
}
'''
 return code,functions,flags,wire
