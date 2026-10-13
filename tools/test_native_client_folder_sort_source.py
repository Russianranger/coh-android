"""Execute extracted stock insertion/constructor parity on controlled metadata.

The OS enumeration and allocation fault inputs are fixtures. A passing test does
not assert actual Game, Wine, file-provider or AYN Thor performance qualification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import map_startup_namespace_certificate as namespace
import prepare_native_client_folder_sort_source as candidate


def harness():
    stock = candidate.source_bytes().decode()
    node_source = candidate.bytes_lf(candidate.ROOT / 'upstream/ouroboros' / candidate.NODE_SOURCE).decode()
    header_source = candidate.bytes_lf(candidate.ROOT / 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/FolderCache.h').decode()
    node_struct = header_source.split('typedef struct FolderNode {', 1)[1].split('} FolderNode;', 1)[0]
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
#else
#include <strings.h>
#define native_stricmp strcasecmp
#define MAX_PATH 260
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
    prefix += 'typedef struct FolderNode {' + node_struct + '} FolderNode;\n'
    prefix += r'''
typedef void (*NodeCallback)(FolderCache *,FolderNode *);
struct FolderCache { FolderNode *root,*root_tail; NodeCallback nodeCreateCallback; };
static FolderCache *folder_cache;
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
static int alloc_calls,alloc_fail_at,active_buffers,max_buffers;
static size_t peak_bytes;
static const char *fixture_environment="1";
static const char *fixture_getenv(const char *key) {assert(!strcmp(key,"COH_CLIENT_FOLDER_METADATA_SORT"));return fixture_environment;}
static void *fixture_realloc(void *old,size_t bytes) {
 void *ret;++alloc_calls;if(alloc_calls==alloc_fail_at)return NULL;
 ret=realloc(old,bytes);if(ret&&!old){++active_buffers;if(active_buffers>max_buffers)max_buffers=active_buffers;}
 if(ret&&bytes>peak_bytes)peak_bytes=bytes;return ret;
}
static void fixture_free(void *p) {assert(p&&active_buffers>0);--active_buffers;free(p);}
#define COH_FOLDER_METADATA_REALLOC fixture_realloc
#define COH_FOLDER_METADATA_FREE fixture_free
#define COH_FOLDER_METADATA_ENV fixture_getenv
#include "coh_folder_metadata_sort.h"
static int fwFindFirstFile(U32 *handle,const char *search,WIN32_FIND_DATAA *row) {
 int i,j;char path[1024];size_t n=strlen(search);++find_first_calls;assert(n>2&&!strcmp(search+n-2,"/*"));
 assert(n-2<sizeof(path));memcpy(path,search,n-2);path[n-2]=0;
 /* Every parent metadata buffer must be freed before recursive enumeration. */
 assert(active_buffers==0);
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
 int n;(void)fc;assert(active_buffers==0);++callback_calls;
 n=snprintf(callback_trace+callback_used,sizeof(callback_trace)-callback_used,"%s:%d:%lu:%d;",node->name,node->virtual_location,(unsigned long)node->size,(int)node->timestamp);
 assert(n>0&&(size_t)n<sizeof(callback_trace)-callback_used);callback_used+=(size_t)n;
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
 callback_calls=0;callback_used=0;callback_trace[0]=0;alloc_calls=active_buffers=max_buffers=0;peak_bytes=0;current_comparisons=0;
 root_constructor_order=1469598103934665603ull;
 memset(fixture_handles,0,sizeof(fixture_handles));
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
 unsigned int i;char name[80];directory_count=2;fixture_aliases=aliases;memset(fixture_dirs,0,sizeof(fixture_dirs));
 strcpy(fixture_dirs[0].path,"fixture");fixture_dirs[0].count=n+3;
 fixture_dirs[0].rows=(WIN32_FIND_DATAA*)calloc(n+3,sizeof(WIN32_FIND_DATAA));assert(fixture_dirs[0].rows);
 for(i=0;i<n;i++){snprintf(name,sizeof(name),"k%05u.fx",n-1-i);fixture_dirs[0].rows[i]=entry(name,(i%8)&7u,10000+i%3*3600,100+i);}
 fixture_dirs[0].rows[n]=entry("subdir",FILE_ATTRIBUTE_DIRECTORY,555,0);
 fixture_dirs[0].rows[n+1]=entry(".ignored",0,666,123);
 fixture_dirs[0].rows[n+2]=entry(aliases?"K00005.FX":"zzzz.fx",FILE_ATTRIBUTE_HIDDEN,26000,999);
 strcpy(fixture_dirs[1].path,"fixture/subdir");fixture_dirs[1].count=4;
 fixture_dirs[1].rows=(WIN32_FIND_DATAA*)calloc(4,sizeof(WIN32_FIND_DATAA));assert(fixture_dirs[1].rows);
 fixture_dirs[1].rows[0]=entry("z.anim",FILE_ATTRIBUTE_READONLY,2500,7);
 fixture_dirs[1].rows[1]=entry("a.anim",FILE_ATTRIBUTE_SYSTEM,2501,8);
 fixture_dirs[1].rows[2]=entry("m.anim",FILE_ATTRIBUTE_HIDDEN,2502,9);
 fixture_dirs[1].rows[3]=entry(".hidden",0,0,0);
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
static void run_case(int callbacks,int fail,const char *env,int providers,int pigs) {
 FolderCache stock={0},changed={0};int p;
 if(callbacks)stock.nodeCreateCallback=changed.nodeCreateCallback=callback;
 if(pigs){preseed_pigs(&stock);preseed_pigs(&changed);}
 if(pigs==2){preseed_conflicts(&stock);preseed_conflicts(&changed);}
 for(p=0;p<providers;p++) {
  int old_first,old_next,old_close,old_files,old_folders,old_discard,old_update,old_callbacks,was_populated=changed.root!=NULL;
  unsigned long long old_order;
  char old_callback_trace[65536];
  alloc_fail_at=fail;fixture_environment=env;reset_observations();count_comparisons=1;
  folder_cache=use_global_owner?&stock:NULL;
  stockConstructor(&stock,&stock.root,&stock.root_tail,NULL,"fixture",p);
  if(p==0)first_stock_comparisons=current_comparisons;last_stock_comparisons=current_comparisons;
  stock_comparisons+=current_comparisons;old_first=find_first_calls;old_next=find_next_calls;old_close=find_close_calls;
  old_files=count_file;old_folders=count_folder;old_discard=discard_count;old_update=update_count;
  old_callbacks=callback_calls;strcpy(old_callback_trace,callback_trace);
  old_order=root_constructor_order;
  reset_observations();
  folder_cache=use_global_owner?&changed:NULL;
  FolderCacheAddFolderToNode(&changed,&changed.root,&changed.root_tail,NULL,"fixture",p);
  if(p==0)first_candidate_comparisons=current_comparisons;last_candidate_comparisons=current_comparisons;
  sorted_comparisons+=current_comparisons;
  assert(active_buffers==0&&max_buffers<=1&&peak_bytes<=(size_t)COH_FOLDER_METADATA_LIMIT*sizeof(CohFolderMetadataRow));
  assert(old_first==find_first_calls&&old_next==find_next_calls&&old_close==find_close_calls);
  assert(old_files==count_file&&old_folders==count_folder&&old_discard==discard_count&&old_update==update_count);
  assert(old_callbacks==callback_calls&&!strcmp(old_callback_trace,callback_trace));
  if(callbacks||strcmp(env,"1")||fail||fixture_aliases||!use_global_owner||was_populated||fixture_dirs[0].count>COH_FOLDER_METADATA_LIMIT)
   assert(old_order==root_constructor_order);
  if(callbacks||strcmp(env,"1")||!use_global_owner)assert(alloc_calls==0);
  assert_equal_nodes(stock.root,changed.root,NULL,NULL,stock.root_tail,changed.root_tail);
  assert(provider_digest(stock.root,"")==provider_digest(changed.root,""));
 }
 destroy_nodes(stock.root);destroy_nodes(changed.root);folder_cache=NULL;count_comparisons=0;
}
int main(void) {
 int seed,cases=0;unsigned int i;
 for(seed=0;seed<64;seed++) {
  state=(unsigned int)seed+17u;make_inputs(300,0);shuffle_inputs();run_case(0,0,"1",3,0);++cases;
  run_case(1,0,"1",3,1);++cases;run_case(0,0,"0",2,1);++cases;
  run_case(0,1,"1",2,0);++cases;run_case(0,2,"1",2,0);++cases;
  clear_inputs();make_inputs(300,1);shuffle_inputs();run_case(0,0,"1",3,0);++cases;clear_inputs();
 }
 make_inputs(17000,0);run_case(0,0,"1",1,0);++cases;clear_inputs();
 make_inputs(300,0);
 for(i=0;i<4;i++){static const char *env[]={"","true","01"," 1"};run_case(0,0,env[i],1,0);++cases;}
 folder_cache_exclusion_folder="subdir";
 folder_cache_exclusion=FOLDER_CACHE_EXCLUDE_FOLDER;run_case(0,0,"1",1,0);++cases;
 folder_cache_exclusion=FOLDER_CACHE_ONLY_FOLDER;run_case(0,0,"1",1,0);++cases;
 folder_cache_exclusion=FOLDER_CACHE_ALL_FOLDERS;folder_cache_exclusion_folder=NULL;
 ban_all_overrides=true;using_dev_data=0;run_case(0,0,"1",1,0);++cases;
 ban_all_overrides=false;using_dev_data=1;clear_inputs();
 make_inputs(300,0);shuffle_inputs();run_case(0,0,"1",3,2);++cases;
 use_global_owner=0;run_case(0,0,"1",1,0);++cases;use_global_owner=1;clear_inputs();
 make_inputs(0,0);fixture_dirs[0].count=0;run_case(0,0,"1",1,0);++cases;clear_inputs();
 make_inputs(4096,0);shuffle_inputs();
 run_case(0,0,"1",1,0);++cases;
 printf("COH_CLIENT_FOLDER_METADATA_COMPARISON_V1 mode=empty first_stock=%llu first_candidate=%llu last_stock=%llu last_candidate=%llu\n",
  first_stock_comparisons,first_candidate_comparisons,last_stock_comparisons,last_candidate_comparisons);
 run_case(0,0,"1",1,1);++cases;
 printf("COH_CLIENT_FOLDER_METADATA_COMPARISON_V1 mode=mixed_pig first_stock=%llu first_candidate=%llu last_stock=%llu last_candidate=%llu\n",
  first_stock_comparisons,first_candidate_comparisons,last_stock_comparisons,last_candidate_comparisons);
 run_case(0,0,"1",2,0);++cases;
 printf("COH_CLIENT_FOLDER_METADATA_COMPARISON_V1 mode=previous_gdd first_stock=%llu first_candidate=%llu last_stock=%llu last_candidate=%llu\n",
  first_stock_comparisons,first_candidate_comparisons,last_stock_comparisons,last_candidate_comparisons);
 clear_inputs();
 printf("COH_CLIENT_FOLDER_METADATA_PARITY_PASS cases=%d providers=3 stock_comparisons=%llu candidate_comparisons=%llu native_wfd_bytes=%lu row_bytes=%lu bound_bytes=%lu\n",
  cases,stock_comparisons,sorted_comparisons,(unsigned long)sizeof(WIN32_FIND_DATAA),(unsigned long)sizeof(CohFolderMetadataRow),
  (unsigned long)((size_t)COH_FOLDER_METADATA_LIMIT*sizeof(CohFolderMetadataRow)));
 return 0;
}
'''
    return prefix + '\n' + slash + '\n' + insertion + '\n' + instrument + '\n' + stock_function.replace('FolderCacheAddFolderToNode(', 'stockConstructor(') + '\n' + helper + '\n' + patched_function + tail


def execute(output=None, windows=False):
    namespace.require(not windows or os.name == 'nt', 'Actual Windows fixture execution required')
    compiler = shutil.which('cl' if windows else 'cc')
    namespace.require(compiler is not None, 'C compiler required')
    with tempfile.TemporaryDirectory(prefix='coh-client-folder-sort-') as temporary:
        root = Path(temporary)
        code = harness()
        (root / 'fixture.c').write_text(code)
        (root / candidate.HEADER).write_bytes(candidate.bytes_lf(candidate.ROOT / candidate.OVERLAY))
        binary = root / ('fixture.exe' if windows else 'fixture')
        command = ([compiler, '/nologo', '/O2', '/TC', '/MT', 'fixture.c', '/Fe:' + str(binary)] if windows else
                   [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-I', str(root), 'fixture.c', '-o', str(binary)])
        build = subprocess.run(command, cwd=root, capture_output=True, text=True)
        namespace.require(build.returncode == 0, 'Folder-sort fixture compile failed: ' + build.stdout + build.stderr)
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=90)
        namespace.require(run.returncode == 0 and 'COH_CLIENT_FOLDER_METADATA_PARITY_PASS' in run.stdout,
                          'Folder-sort fixture execution failed: ' + run.stdout + run.stderr)
        summary = run.stdout.strip().splitlines()[-1]
        fields = dict(re.findall(r'(\w+)=(\d+)', summary))
        receipt = {
            'format': 1, 'status': 'passed', 'role': 'actual_extracted_folder_constructor_and_node_insert_parity',
            'cases': int(fields['cases']), 'controlled_enumeration': True,
            'native_windows_executed': windows, 'native_game_executed': False,
            'native_wine_executed': False, 'physical_device_executed': False,
            'portable_windows_types_are_adapters': not windows,
            'callback_trace_exact_in_fallback': True, 'provider_metadata_and_all_links_equal': True,
            'root_per_entry_constructor_order_exact_in_every_fallback': True,
            'same_FindFirst_FindNext_FindClose_counts': True, 'enumerations_restarted': False,
            'one_temporary_batch_maximum': True, 'temporary_buffers_released_before_recursion': True,
            'tested_allocation_failures': [1, 2], 'tested_entry_limit': 16384,
            'controlled_insertion_comparison_cases': [dict(re.findall(r'(\w+)=([\w]+)', row))
                for row in run.stdout.splitlines() if row.startswith('COH_CLIENT_FOLDER_METADATA_COMPARISON_V1')],
            'observed_native_WFD_bytes': int(fields['native_wfd_bytes']),
            'observed_row_bytes': int(fields['row_bytes']), 'maximum_retained_batch_payload_bytes': int(fields['bound_bytes']),
            'possible_realloc_payload_overlap_bytes_before_allocator_overhead': int(fields['row_bytes']) * 24576,
            'aggregate_comparisons_include_sort_alias_checks_and_fallbacks': {
                'stock': int(fields['stock_comparisons']), 'candidate': int(fields['candidate_comparisons'])},
            'source': candidate.expected_receipt(), 'publication_allowed': False,
            'harness_sha256': hashlib.sha256(code.encode()).hexdigest(),
            'fixture_binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'output': summary,
        }
        if output:
            output = Path(output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(receipt, indent=2) + '\n')
            shutil.copyfile(binary, output.with_suffix('.exe' if windows else '.bin'))
        return receipt


class NativeClientFolderSortTests(unittest.TestCase):
    def test_actual_stock_constructor_insert_provider_and_fault_parity(self):
        self.assertEqual(execute()['cases'], 398)

    def test_per_entry_helper_preserves_literal_stock_body(self):
        stock = candidate.per_entry_body(candidate.source_bytes())
        helper = namespace.function(candidate.patch_source(candidate.source_bytes()).decode(), candidate.HELPER)
        self.assertIn(stock.replace('continue;', 'return;'), helper)
        for anchor in ('node2->writeable =', 'node2->hidden =', 'node2->system =', 'count_file++;', 'count_folder++;'):
            self.assertIn(anchor, helper)

    def test_insert_provider_function_is_not_modified(self):
        receipt = candidate.expected_receipt()
        source = candidate.bytes_lf(candidate.ROOT / 'upstream/ouroboros' / candidate.NODE_SOURCE)
        self.assertEqual(receipt['source_sha256'][candidate.NODE_SOURCE], hashlib.sha256(source).hexdigest())
        self.assertNotIn(candidate.NODE_SOURCE, receipt['patched_sha256'])

    def test_sort_is_disabled_without_exact_one_and_callback_absent(self):
        patched = candidate.patch_source(candidate.source_bytes()).decode()
        self.assertIn('cohFolderMetadataEnabled() && fc == folder_cache && *node == NULL && *tail == NULL && fc->nodeCreateCallback == NULL', patched)
        header = candidate.bytes_lf(candidate.ROOT / candidate.OVERLAY).decode()
        self.assertIn('value && !strcmp(value, "1")', header)

    def test_changed_constructor_anchor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'enumeration anchors differ'):
            candidate.patch_source(candidate.source_bytes().replace(b'    do {\n', b'    for (;;) {\n', 1))

    def test_receipt_does_not_qualify_game_device_or_publication(self):
        receipt = candidate.expected_receipt()
        for key in ('native_windows_executed', 'native_game_executed', 'physical_device_executed', 'publication_allowed', 'default_enabled'):
            self.assertFalse(receipt[key])
        self.assertEqual(receipt['maximum_directory_entries'], 16384)
        self.assertTrue(receipt['fallback_preserves_original_arrival_order'])

    def test_staging_refuses_immutable_root_before_any_validator(self):
        for target in (candidate.ROOT, candidate.ROOT / 'upstream/ouroboros', candidate.ROOT.parent):
            with self.assertRaisesRegex(ValueError, 'Repository or immutable'):
                candidate.stage(target)

    def test_staging_refuses_symlink_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            (temp / 'real').mkdir()
            (temp / 'link').symlink_to(temp / 'real', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Linked folder-sort'):
                candidate.stage(temp / 'link')

    def test_new_callback_assignment_fails_closed_source_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            upstream = root / 'upstream/ouroboros'
            for name in (candidate.SOURCE, 'libs/UtilitiesLib/src/utils/file.c'):
                target = upstream / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(candidate.bytes_lf(candidate.ROOT / 'upstream/ouroboros' / name))
            self.assertEqual(candidate.callback_source_audit(root)['callback_assignments_found'], 0)
            (upstream / 'new_callback.c').write_text('void new_callback(void) { fc->nodeCreateCallback = hook; }\n')
            with self.assertRaisesRegex(ValueError, 'assigns a node-create callback'):
                candidate.callback_source_audit(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--windows-qualify', action='store_true')
    parser.add_argument('--output', type=Path)
    args, rest = parser.parse_known_args()
    if args.windows_qualify:
        namespace.require(args.output is not None, 'Windows evidence output required')
        print(json.dumps(execute(args.output, windows=True)))
    else:
        unittest.main(argv=[__file__, *rest])
