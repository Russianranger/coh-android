"""Portable extracted-stock constructor parity for a closed metadata prototype.

Enumeration/provider/lease inputs are controlled fixtures, not real Wine or Thor.
The production Game source never registers this census context.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import map_startup_namespace_certificate as namespace
import prepare_native_client_metadata_census_source as candidate


def harness(native_enabled=True):
    stock = candidate.source_bytes().decode()
    node_source = candidate.bytes_lf(candidate.ROOT / 'upstream/ouroboros' / candidate.NODE_SOURCE).decode()
    header = candidate.bytes_lf(candidate.ROOT / 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/FolderCache.h').decode()
    node_struct = header.split('typedef struct FolderNode {', 1)[1].split('} FolderNode;', 1)[0]
    insertion = namespace.function(node_source, 'FolderNode *FolderNodeAdd(')
    slash = namespace.function(node_source, 'static char *firstSlash(')
    stock_function = namespace.function(stock, candidate.SIGNATURE)
    patched = candidate.patch_source(stock.encode()).decode()
    helper = namespace.function(patched, candidate.HELPER)
    patched_function = namespace.function(patched, candidate.SIGNATURE)
    prefix = r'''

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#ifdef _WIN32
#include <windows.h>
#define native_stricmp _stricmp
#define COH_CLIENT_METADATA_CENSUS_PROTOTYPE 1
#else
#include <strings.h>
#define native_stricmp strcasecmp
#define MAX_PATH 260
#define COH_CLIENT_METADATA_CENSUS_PROTOTYPE 1
#define FALSE 0
#define FILE_ATTRIBUTE_READONLY 1u
#define FILE_ATTRIBUTE_HIDDEN 2u
#define FILE_ATTRIBUTE_SYSTEM 4u
#define FILE_ATTRIBUTE_DIRECTORY 16u
typedef struct { uint32_t dwLowDateTime, dwHighDateTime; } FILETIME;
typedef struct {
 uint32_t dwFileAttributes; FILETIME ftCreationTime,ftLastAccessTime,ftLastWriteTime;
 uint32_t nFileSizeHigh,nFileSizeLow,dwReserved0,dwReserved1;
 char cFileName[260],cAlternateFileName[14];
} WIN32_FIND_DATAA;
#endif
typedef uint32_t U32;
typedef int32_t S32;
#ifndef _WIN32
typedef int32_t __time32_t;
#endif
typedef struct FolderNode FolderNode;
typedef struct FolderCache FolderCache;

'''
    prefix += "typedef struct FolderNode {" + node_struct + "} FolderNode;\n"
    prefix += r'''

typedef void (*NodeCallback)(FolderCache *,FolderNode *);
struct FolderCache { FolderNode *root,*root_tail; NodeCallback nodeCreateCallback,nodeDeleteCallback; };
static FolderCache *folder_cache;
static int folder_cache_update_enable,fixture_gdd_count=1,fixture_pig_count;
static uint32_t fixture_thread=1;
static uint32_t GetCurrentThreadId(void) {return fixture_thread;}
static int callback_clears;
static int fixture_dynamic=1;
static int FolderCacheGetMode(void) {return fixture_dynamic?1:0;}
#define FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC 1
static int FolderCache_GetNumGDDs(FolderCache *fc) {(void)fc;return fixture_gdd_count;}
static int FolderCache_GetNumPiggs(FolderCache *fc) {(void)fc;return fixture_pig_count;}
static char *FolderCache_GetFromVirtualLocation(FolderCache *fc,int i) {(void)fc;assert(i==0);return "fixture";}
static int use_global_owner=1;
typedef enum {FOLDER_CACHE_EXCLUDE_FOLDER,FOLDER_CACHE_ONLY_FOLDER,FOLDER_CACHE_ALL_FOLDERS} FolderCacheExclusion;
static int folder_cache_debug,discard_count,update_count,count_file,count_folder;
static FolderCacheExclusion folder_cache_exclusion=FOLDER_CACHE_ALL_FOLDERS;
static char *folder_cache_exclusion_folder;
static bool ban_all_overrides;
static char *banned_overrides[]={"/scenes","/ent_types","/object_library","/geobin"};
static int banned_overrides_len[4];
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define xcase break;case
#define xdefault break;default
#define STR_COMBINE_SS(out,a,b) snprintf((out),sizeof(out),"%s%s",(a),(b))
#define STR_COMBINE_SSS(out,a,b,c) snprintf((out),sizeof(out),"%s%s%s",(a),(b),(c))
static unsigned long long stock_comparisons,sorted_comparisons,current_comparisons;
static int count_comparisons;
static int compare_names(const char *a,const char *b) {
 if(count_comparisons) ++current_comparisons;
 return native_stricmp(a,b);
}
#define stricmp compare_names
static char *allocAddString(const char *value) {
 size_t n=strlen(value)+1;char *ret=(char*)malloc(n);assert(ret);memcpy(ret,value,n);return ret;
}
static FolderNode *FolderNodeCreate(void) {FolderNode *ret=(FolderNode*)calloc(1,sizeof(*ret));assert(ret);return ret;}
static void _FileTimeToUnixTime(const FILETIME *time,__time32_t *ret,int unused) {(void)unused;*ret=(__time32_t)time->dwLowDateTime;}
static int using_dev_data=1;
static int fileIsUsingDevData(void) {return using_dev_data;}
typedef struct FixtureDirectory {char path[1024];WIN32_FIND_DATAA *rows;unsigned int count;} FixtureDirectory;
typedef struct FixtureHandle {FixtureDirectory *directory;unsigned int index;int open;} FixtureHandle;
static FixtureDirectory fixture_dirs[8];
static FixtureHandle fixture_handles[8];
static int directory_count,find_first_calls,find_next_calls,find_close_calls,fixture_aliases;
static unsigned long long root_constructor_order;
static unsigned long long first_stock_comparisons,first_candidate_comparisons,last_stock_comparisons,last_candidate_comparisons;
static char callback_trace[65536];
static size_t callback_used;
static int callback_calls;
#include "coh_folder_census_adapter.h"
static int fwFindFirstFile(U32 *handle,const char *search,WIN32_FIND_DATAA *row) {
 int i,j;char path[1024];size_t n=strlen(search);++find_first_calls;assert(n>2&&!strcmp(search+n-2,"/*"));
 assert(n-2<sizeof(path));memcpy(path,search,n-2);path[n-2]=0;
 /* Every parent metadata buffer must be freed before recursive enumeration. */

 for(i=0;i<directory_count;i++) if(!strcmp(path,fixture_dirs[i].path)&&fixture_dirs[i].count) {
  for(j=0;j<8;j++) if(!fixture_handles[j].open) {
   fixture_handles[j].directory=&fixture_dirs[i];fixture_handles[j].index=0;fixture_handles[j].open=1;
   *handle=(U32)(j+1);*row=fixture_dirs[i].rows[0];return 1;
  }
  assert(0);
 }
 return 0;
}
static int fwFindNextFile(U32 handle,WIN32_FIND_DATAA *row) {
 FixtureHandle *h;assert(handle>0&&handle<=8);h=&fixture_handles[handle-1];assert(h->open);++find_next_calls;
 if(++h->index>=h->directory->count)return 0;*row=h->directory->rows[h->index];return 1;
}
static void fwFindClose(U32 handle) {assert(handle>0&&handle<=8&&fixture_handles[handle-1].open);fixture_handles[handle-1].open=0;++find_close_calls;}
static void callback(FolderCache *fc,FolderNode *node) {
 int n;(void)fc;++callback_calls;
 n=snprintf(callback_trace+callback_used,sizeof(callback_trace)-callback_used,"%s:%d:%lu:%d;",node->name,node->virtual_location,(unsigned long)node->size,(int)node->timestamp);
 assert(n>0&&(size_t)n<sizeof(callback_trace)-callback_used);callback_used+=(size_t)n;
 if(callback_clears)fc->nodeCreateCallback=NULL;
}

'''
    instrument = r'''

static FolderNode *observedFolderNodeAdd(FolderNode **head,FolderNode **tail,FolderNode *parent,
    const char *name,__time32_t time,size_t bytes,int provider,int file_index,int *created) {
 const unsigned char *p;
 if(parent==NULL) {
  for(p=(const unsigned char*)name;*p;p++)root_constructor_order=(root_constructor_order^*p)*1099511628211ull;
  root_constructor_order=(root_constructor_order^(unsigned int)time)*1099511628211ull;
  root_constructor_order=(root_constructor_order^(unsigned long long)bytes)*1099511628211ull;
  root_constructor_order=(root_constructor_order^(unsigned int)provider)*1099511628211ull;
 }
 return FolderNodeAdd(head,tail,parent,name,time,bytes,provider,file_index,created);
}
#define FolderNodeAdd observedFolderNodeAdd

'''
    tail = r'''

static unsigned int state=17;
static unsigned int random_value(void) {state=state*1664525u+1013904223u;return state;}
static void reset_observations(void) {
 find_first_calls=find_next_calls=find_close_calls=count_file=count_folder=discard_count=update_count=0;
 callback_calls=0;callback_used=0;callback_trace[0]=0;current_comparisons=0;
 root_constructor_order=1469598103934665603ull;memset(fixture_handles,0,sizeof(fixture_handles));
}
static void destroy_nodes(FolderNode *node) {
 while(node) {FolderNode *next=node->next;destroy_nodes(node->contents);free(node->name);free(node);node=next;}
}
static void assert_equal_nodes(FolderNode *a,FolderNode *b,FolderNode *ap,FolderNode *bp,FolderNode *at,FolderNode *bt) {
 FolderNode *last_a=NULL,*last_b=NULL;
 while(a&&b) {
  assert(a->parent==ap&&b->parent==bp&&a->prev==last_a&&b->prev==last_b);
  assert(!strcmp(a->name,b->name));assert(a->virtual_location==b->virtual_location&&a->is_dir==b->is_dir);
  assert(a->writeable==b->writeable&&a->hidden==b->hidden&&a->system==b->system&&a->seen_in_fs==b->seen_in_fs);
  assert(a->in_hash_table==b->in_hash_table&&a->delete_if_absent==b->delete_if_absent);
  assert(a->timestamp==b->timestamp&&a->size==b->size&&a->file_index==b->file_index);
  assert_equal_nodes(a->contents,b->contents,a,b,a->contents_tail,b->contents_tail);
  last_a=a;last_b=b;a=a->next;b=b->next;
 }
 assert(!a&&!b&&last_a==at&&last_b==bt);
}
/* Traversal simulates the unchanged stock final hash-table membership, recording
 * each exact relative path and metadata; pointer values are not compared. */
static unsigned long long provider_digest(FolderNode *node,const char *prefix) {
 unsigned long long hash=1469598103934665603ull;char path[1024];
 for(;node;node=node->next) {
  const unsigned char *p;snprintf(path,sizeof(path),"%s/%s",prefix,node->name);
  for(p=(const unsigned char*)path;*p;p++)hash=(hash^*p)*1099511628211ull;
  hash=(hash^(unsigned long long)(unsigned int)node->timestamp)*1099511628211ull;
  hash=(hash^(unsigned long long)node->size)*1099511628211ull;
  hash^=provider_digest(node->contents,path);
 }
 return hash;
}
static WIN32_FIND_DATAA entry(const char *name,unsigned int attrs,unsigned int time,unsigned int bytes) {
 WIN32_FIND_DATAA row;memset(&row,0,sizeof(row));strcpy(row.cFileName,name);row.dwFileAttributes=attrs;
 row.ftLastWriteTime.dwLowDateTime=time;row.nFileSizeLow=bytes;row.nFileSizeHigh=7;return row;
}
static void make_inputs(unsigned int n,int aliases) {
 unsigned int i;char name[80];directory_count=3;fixture_aliases=aliases;memset(fixture_dirs,0,sizeof(fixture_dirs));
 strcpy(fixture_dirs[0].path,"fixture/fx");fixture_dirs[0].count=n+4;
 fixture_dirs[0].rows=(WIN32_FIND_DATAA*)calloc(n+4,sizeof(WIN32_FIND_DATAA));assert(fixture_dirs[0].rows);
 for(i=0;i<n;i++){snprintf(name,sizeof(name),"k%05u.fx",n-1-i);fixture_dirs[0].rows[i]=entry(name,(i%8)&7u,10000+i%3*3600,100+i);}
 fixture_dirs[0].rows[n]=entry("subdir",FILE_ATTRIBUTE_DIRECTORY,555,0);
 fixture_dirs[0].rows[n+1]=entry(".ignored",0,666,123);
 fixture_dirs[0].rows[n+2]=entry(aliases?"K00005.FX":"zzzz.fx",FILE_ATTRIBUTE_HIDDEN,26000,999);
 fixture_dirs[0].rows[n+3]=entry("empty",FILE_ATTRIBUTE_DIRECTORY,333,0);
 strcpy(fixture_dirs[1].path,"fixture/fx/subdir");fixture_dirs[1].count=4;
 fixture_dirs[1].rows=(WIN32_FIND_DATAA*)calloc(4,sizeof(WIN32_FIND_DATAA));assert(fixture_dirs[1].rows);
 fixture_dirs[1].rows[0]=entry("z.anim",FILE_ATTRIBUTE_READONLY,2500,7);
 fixture_dirs[1].rows[1]=entry("a.anim",FILE_ATTRIBUTE_SYSTEM,2501,8);
 fixture_dirs[1].rows[2]=entry("m.anim",FILE_ATTRIBUTE_HIDDEN,2502,9);
 fixture_dirs[1].rows[3]=entry(".hidden",0,0,0);
 strcpy(fixture_dirs[2].path,"fixture/fx/empty");fixture_dirs[2].rows=NULL;fixture_dirs[2].count=0;
}
static void clear_inputs(void) {int i;for(i=0;i<directory_count;i++)free(fixture_dirs[i].rows);directory_count=0;}
static void shuffle_inputs(void) {
 unsigned int i;for(i=fixture_dirs[0].count-1;i>0;i--){unsigned int j=random_value()%(i+1);WIN32_FIND_DATAA t=fixture_dirs[0].rows[i];fixture_dirs[0].rows[i]=fixture_dirs[0].rows[j];fixture_dirs[0].rows[j]=t;}
}
static void preseed_pigs(FolderCache *fc) {
 int created;FolderNode *n;
 n=FolderNodeAdd(&fc->root,&fc->root_tail,NULL,"k00005.fx",10000,25,-1,17,&created);assert(created&&n);
 n=FolderNodeAdd(&fc->root,&fc->root_tail,NULL,"k00009.fx",13600,31,-2,23,&created);assert(created&&n);
 n=FolderNodeAdd(&fc->root,&fc->root_tail,NULL,"only_pig.fx",777,17,-3,47,&created);assert(created&&n);
}
static void preseed_conflicts(FolderCache *fc) {
 int created;FolderNode *n;
 n=FolderNodeAdd(&fc->root,&fc->root_tail,NULL,"subdir",10000,27,-1,29,&created);assert(created&&n);
 n=FolderNodeAdd(&fc->root,&fc->root_tail,NULL,"k00005.fx/old_pig_child.anim",10000,29,-2,31,&created);assert(created&&n);
}

'''
    tail += CENSUS_FIXTURE
    if not native_enabled:
        prefix = prefix.replace('#define COH_CLIENT_METADATA_CENSUS_PROTOTYPE 1', '')
    return prefix + "\n" + slash + "\n" + insertion + "\n" + instrument + "\n" + stock_function.replace("FolderCacheAddFolderToNode(", "stockConstructor(") + "\n" + helper + "\n" + patched_function + tail


CENSUS_FIXTURE = r'''
#if defined(COH_CLIENT_METADATA_CENSUS_PROTOTYPE)
static const int fixture_compiled_census=1;
#else
static const int fixture_compiled_census=0;
#endif
static int lease_current=1,lease_calls;
static unsigned char generation_token[32];
static int fixture_lease(void *owner,const char *root,const char *relative,const unsigned char token[32]) {
 (void)owner;assert(!strcmp(root,"fixture"));assert(!memcmp(token,generation_token,32));
 assert(!*relative||!strncmp(relative,"fx",2));++lease_calls;return lease_current;
}
static void put32(unsigned char *p,uint32_t n) {p[0]=(unsigned char)n;p[1]=(unsigned char)(n>>8);p[2]=(unsigned char)(n>>16);p[3]=(unsigned char)(n>>24);}
static void put16(unsigned char *p,uint16_t n) {p[0]=(unsigned char)n;p[1]=(unsigned char)(n>>8);}
static unsigned char *make_blob(size_t *bytes) {
 static const char *paths[]={"","fx","fx/empty","fx/subdir"};
 unsigned int counts[4]={1,0,0,0},first=0,d,j;size_t record_offset=64,offset;
 unsigned char *blob;WIN32_FIND_DATAA root_entry=entry("fx",FILE_ATTRIBUTE_DIRECTORY,123,0);
 counts[1]=fixture_dirs[0].count;counts[3]=fixture_dirs[1].count;
 for(d=0;d<4;d++)record_offset+=(16+strlen(paths[d])+3)&~(size_t)3;
 *bytes=record_offset+(size_t)(1+counts[1]+counts[3])*328;
 blob=(unsigned char*)calloc(1,*bytes);assert(blob);memcpy(blob,"COHCNS1\0",8);
 put32(blob+8,1);put32(blob+12,(uint32_t)*bytes);put32(blob+16,4);
 put32(blob+20,1+counts[1]+counts[3]);put32(blob+24,(uint32_t)record_offset);
 memcpy(blob+32,generation_token,32);offset=64;
 for(d=0;d<4;d++) {
  size_t n=strlen(paths[d]);put16(blob+offset,(uint16_t)n);put32(blob+offset+4,first);
  put32(blob+offset+8,counts[d]);put32(blob+offset+12,d);memcpy(blob+offset+16,paths[d],n);
  for(j=0;j<counts[d];j++) {
   WIN32_FIND_DATAA *row=d==0?&root_entry:d==1?&fixture_dirs[0].rows[j]:&fixture_dirs[1].rows[j];
   unsigned char *record=blob+record_offset+(size_t)(first+j)*328;
   put32(record,d);put32(record+4,j);memcpy(record+8,row,320);
  }
  first+=counts[d];offset+=(16+n+3)&~(size_t)3;
 }
 return blob;
}
static unsigned char *make_child_only_blob(size_t *bytes) {
 const char *path="fx/subdir";size_t n=strlen(path),record_offset=64+((16+n+3)&~(size_t)3);
 unsigned int j;unsigned char *blob;
 *bytes=record_offset+(size_t)fixture_dirs[1].count*328;blob=(unsigned char*)calloc(1,*bytes);assert(blob);
 memcpy(blob,"COHCNS1\0",8);put32(blob+8,1);put32(blob+12,(uint32_t)*bytes);put32(blob+16,1);
 put32(blob+20,fixture_dirs[1].count);put32(blob+24,(uint32_t)record_offset);memcpy(blob+32,generation_token,32);
 put16(blob+64,(uint16_t)n);put32(blob+72,fixture_dirs[1].count);memcpy(blob+80,path,n);
 for(j=0;j<fixture_dirs[1].count;j++){unsigned char *row=blob+record_offset+(size_t)j*328;put32(row+4,j);memcpy(row+8,&fixture_dirs[1].rows[j],320);}
 return blob;
}
static void run_case(int scenario) {
 FolderCache stock={0},changed={0};unsigned char *blob,token[32];size_t bytes;
 int old_first,old_next,old_close,old_files,old_folders,old_discard,old_update,old_callbacks,registered;
 unsigned long long old_order;char old_trace[65536];
 fixture_gdd_count=1;fixture_pig_count=0;fixture_dynamic=1;folder_cache_update_enable=0;fixture_thread=1;callback_clears=0;
 folder_cache_exclusion=FOLDER_CACHE_ALL_FOLDERS;folder_cache_exclusion_folder=NULL;
 using_dev_data=1;ban_all_overrides=false;use_global_owner=1;
 if(scenario==5)stock.nodeCreateCallback=changed.nodeCreateCallback=callback;
 if(scenario==19){stock.nodeCreateCallback=changed.nodeCreateCallback=callback;callback_clears=1;}
 if(scenario==17)stock.nodeDeleteCallback=changed.nodeDeleteCallback=callback;
 if(scenario==7||scenario==8){preseed_pigs(&stock);preseed_pigs(&changed);}
 if(scenario==8){preseed_conflicts(&stock);preseed_conflicts(&changed);}
 if(scenario==9)folder_cache_update_enable=1;
 if(scenario==10)fixture_dynamic=0;
 if(scenario==11)fixture_gdd_count=2;
 if(scenario==12)fixture_pig_count=1;
 if(scenario==13){using_dev_data=0;ban_all_overrides=true;}
 if(scenario==14){folder_cache_exclusion=FOLDER_CACHE_EXCLUDE_FOLDER;folder_cache_exclusion_folder="subdir";}
 if(scenario==15){folder_cache_exclusion=FOLDER_CACHE_ONLY_FOLDER;folder_cache_exclusion_folder="subdir";}
 if(scenario==6)use_global_owner=0;
 reset_observations();folder_cache=use_global_owner?&stock:NULL;
 stockConstructor(&stock,&stock.root,&stock.root_tail,NULL,"fixture/fx",scenario==16?1:0);
 old_first=find_first_calls;old_next=find_next_calls;old_close=find_close_calls;
 old_files=count_file;old_folders=count_folder;old_discard=discard_count;old_update=update_count;
 old_callbacks=callback_calls;strcpy(old_trace,callback_trace);old_order=root_constructor_order;
 reset_observations();folder_cache=use_global_owner?&changed:NULL;
 lease_calls=0;lease_current=1;memcpy(token,generation_token,32);blob=scenario==20?make_child_only_blob(&bytes):make_blob(&bytes);
 cohFolderCensusClearContext(&coh_folder_census_context);
 if(scenario==3)token[0]^=1;
 if(scenario==4)blob[bytes-1]=1; /* Whole-blob preflight must fail before any row is exposed. */
 registered=scenario==1?0:cohFolderCensusRegister(&coh_folder_census_context,blob,bytes,
    "fixture",token,&changed,0,fixture_lease,NULL);
 assert(registered==(scenario!=1&&scenario!=3&&scenario!=4));
 if(scenario==2)lease_current=0;
 if(scenario==18)fixture_thread=2;
 FolderCacheAddFolderToNode(&changed,&changed.root,&changed.root_tail,NULL,"fixture/fx",scenario==16?1:0);
 assert(old_files==count_file&&old_folders==count_folder&&old_discard==discard_count&&old_update==update_count);
 assert(old_callbacks==callback_calls&&!strcmp(old_trace,callback_trace));assert(old_order==root_constructor_order);
 assert_equal_nodes(stock.root,changed.root,NULL,NULL,stock.root_tail,changed.root_tail);
 assert(provider_digest(stock.root,"")==provider_digest(changed.root,""));
 if(scenario==0&&fixture_compiled_census) {assert(old_first==3&&old_close==2);assert(find_first_calls==0&&find_next_calls==0&&find_close_calls==0);assert(lease_calls==4);}
 else {assert(old_first==find_first_calls&&old_next==find_next_calls&&old_close==find_close_calls);}
 cohFolderCensusClearContext(&coh_folder_census_context);free(blob);
 destroy_nodes(stock.root);destroy_nodes(changed.root);folder_cache=NULL;
}
static void api_guards(void) {
 static CohFolderCensusContext copy,snapshot;
 FolderCache owner={0};unsigned char *blob;size_t bytes;CohFolderCensusDirectory directory;
 fixture_thread=1;lease_current=1;make_inputs(8,0);blob=make_blob(&bytes);
 assert(cohFolderCensusRegister(&coh_folder_census_context,blob,bytes,"fixture",generation_token,&owner,0,fixture_lease,NULL));
 copy=coh_folder_census_context;
 assert(!cohFolderCensusAcquireDirectory(&copy,&owner,&owner,"fixture/fx","fixture",1,0,0,1,1,1,1,1,1,&directory));
 assert(!copy.registered&&coh_folder_census_context.registered);
 snapshot=coh_folder_census_context;
 assert(!cohFolderCensusRegister(&coh_folder_census_context,blob,bytes,"fixture",coh_folder_census_context.generation_token,&owner,0,fixture_lease,NULL));
 assert(!memcmp(&snapshot,&coh_folder_census_context,sizeof(snapshot)));
 assert(!cohFolderCensusRegister(&coh_folder_census_context,blob,bytes,coh_folder_census_context.native_root,generation_token,&owner,0,fixture_lease,NULL));
 assert(!memcmp(&snapshot,&coh_folder_census_context,sizeof(snapshot)));
 assert(!cohFolderCensusRegister(&coh_folder_census_context,(const unsigned char*)&coh_folder_census_context,sizeof(coh_folder_census_context),"fixture",generation_token,&owner,0,fixture_lease,NULL));
 assert(!memcmp(&snapshot,&coh_folder_census_context,sizeof(snapshot)));
 cohFolderCensusClearContext(&coh_folder_census_context);free(blob);clear_inputs();
}
int main(void) {
 int seed,scenario,cases=0;unsigned int i;
 assert(sizeof(WIN32_FIND_DATAA)==320);for(i=0;i<32;i++)generation_token[i]=(unsigned char)(i+1);
 for(seed=0;seed<32;seed++) {
  state=(unsigned int)seed+17;make_inputs(300,0);shuffle_inputs();
  for(scenario=0;scenario<21;scenario++){run_case(scenario);++cases;}clear_inputs();
  make_inputs(300,1);shuffle_inputs();run_case(0);++cases;clear_inputs();
 }
 make_inputs(0,0);run_case(0);++cases;clear_inputs();
 make_inputs(4096,0);shuffle_inputs();run_case(0);++cases;run_case(7);++cases;clear_inputs();
 api_guards();
 printf("COH_CLIENT_METADATA_CENSUS_PARITY_PASS cases=%d native_wfd_bytes=%lu context_bytes=%lu removed_fixture_enum_calls=3 api_guard_cases=4\n",
  cases,(unsigned long)sizeof(WIN32_FIND_DATAA),(unsigned long)sizeof(CohFolderCensusContext));return 0;
}
'''


def execute(output=None, native_enabled=True):
    compiler = shutil.which('cc')
    namespace.require(compiler is not None, 'Portable C compiler required')
    with tempfile.TemporaryDirectory(prefix='coh-client-census-constructor-') as temporary:
        root = Path(temporary)
        code = harness(native_enabled)
        (root / 'fixture.c').write_text(code)
        for name in candidate.HEADERS:
            (root / name).write_bytes(candidate.bytes_lf(candidate.ROOT / 'database/client-metadata-census/overlay' / name))
        binary = root / 'fixture'
        build = subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-I', str(root),
            'fixture.c', '-o', str(binary)], cwd=root, capture_output=True, text=True)
        namespace.require(build.returncode == 0, 'Census constructor fixture compile failed: ' + build.stdout + build.stderr)
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=90)
        namespace.require(run.returncode == 0 and 'COH_CLIENT_METADATA_CENSUS_PARITY_PASS' in run.stdout,
            'Census constructor fixture failed: ' + run.stdout + run.stderr)
        fields = dict(re.findall(r'(\w+)=(\d+)', run.stdout.strip().splitlines()[-1]))
        receipt = {'format': 1, 'role': 'portable_extracted_stock_constructor_census_parity',
            'status': 'passed', 'controlled_native_metadata_rows': True, 'controlled_provider_lease': True,
            'prototype_compile_gate_enabled': native_enabled,
            'cases': int(fields['cases']), 'observed_adapter_WFD_bytes': int(fields['native_wfd_bytes']),
            'observed_portable_context_bytes': int(fields['context_bytes']),
            'fixture_removed_enumeration_calls_per_complete_branch': int(fields['removed_fixture_enum_calls']),
            'api_guard_cases': int(fields['api_guard_cases']),
            'copied_context_and_context_input_aliases_refused': True, 'owned_registration_thread_bound': True,
            'exact_arrival_and_node_attributes': True, 'exact_all_tree_links_and_provider_counters': True,
            'actual_hash_table_implementation_executed': False, 'hash_membership_compared_by_complete_tree_digest': True,
            'all_admission_failures_preserve_stock_enumeration': True,
            'native_windows_executed': False, 'native_wine_executed': False, 'native_game_executed': False,
            'physical_device_executed': False, 'production_generation_authority_present': False,
            'publication_allowed': False, 'source': candidate.expected_receipt(),
            'harness_sha256': hashlib.sha256(code.encode()).hexdigest(),
            'fixture_binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'output': run.stdout}
        if output:
            Path(output).write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
        return receipt


class MetadataCensusConstructorTests(unittest.TestCase):
    def test_actual_extracted_stock_constructor_parity(self):
        self.assertEqual(execute()['cases'], 707)

    def test_absent_dedicated_build_macro_retains_every_stock_enumeration(self):
        self.assertEqual(execute(native_enabled=False)['cases'], 707)

    def test_stock_body_and_node_insertion_retained(self):
        stock = candidate.source_bytes()
        helper = namespace.function(candidate.patch_source(stock).decode(), candidate.HELPER)
        self.assertIn(candidate.per_entry_body(stock).replace('continue;', 'return;'), helper)
        self.assertNotIn(candidate.NODE_SOURCE, candidate.expected_receipt()['patched_sha256'])

    def test_current_prototype_has_no_production_registration(self):
        patched = candidate.patch_source(candidate.source_bytes()).decode()
        self.assertNotIn('cohFolderCensusRegister(', patched)
        receipt = candidate.expected_receipt()
        for key in ('production_registration_present', 'production_activation_available',
                    'native_game_executed', 'native_wine_executed', 'physical_device_executed', 'publication_allowed'):
            self.assertFalse(receipt[key])

    def test_hash_query_and_request_tree_bodies_unchanged(self):
        stock = candidate.source_bytes().decode()
        patched = candidate.patch_source(candidate.source_bytes()).decode()
        for signature in ('void FolderCacheBuildHashTable(', 'void FolderCacheRequestTree(', 'FolderNode *FolderCacheQuery('):
            self.assertEqual(namespace.function(stock, signature), namespace.function(patched, signature))
        begin, end = 'FolderNode *FolderCacheFileSystemOverride(', 'static char *ignorePrefixArray'
        self.assertEqual(stock.split(begin, 1)[1].split(end, 1)[0], patched.split(begin, 1)[1].split(end, 1)[0])

    def test_changed_enumeration_anchor_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'enumeration differs'):
            candidate.patch_source(candidate.source_bytes().replace(b'    do {\n', b'    for (;;) {\n', 1))

    def test_staging_refuses_repo_and_immutable_root(self):
        for path in (candidate.ROOT, candidate.ROOT.parent, candidate.ROOT / 'upstream/ouroboros'):
            with self.assertRaisesRegex(ValueError, 'Repository or immutable'):
                candidate.stage(path)


if __name__ == '__main__':
    unittest.main()

