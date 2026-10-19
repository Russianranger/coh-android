"""Original FileList lifecycle and selected original EArray destruction closure.
Fixture-owned host allocations are distinct from original engine allocator closure.
"""
from pathlib import Path
import hashlib,json,re
import file_list_ops_provider as accepted
HERE=Path(__file__).resolve().parent
INTERNAL_C=accepted.INTERNAL_C;INTERNAL_H=accepted.INTERNAL_H;UTILS_H=accepted.UTILS_H
EAR_C='upstream/ouroboros/libs/UtilitiesLib/src/components/earray.c'
EAR_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/earray.h'
sha=accepted.sha;extract=accepted.extract
HEADER=r'''/* Fixture only: no filesystem, runtime catalog or freshness authority. */
#ifndef COH_FILE_LIST_LIFECYCLE_PROVIDER_H
#define COH_FILE_LIST_LIFECYCLE_PROVIDER_H
#include "coh_costume_import.h"
#define FLL_OP_MAX 32u
#define FLL_NODE_MAX 16u
#define FLL_PATH_MAX 260u
#define FLL_RAW_MAX 520u
#define FLL_BUDGET_MAX (1024u*1024u)
#define FLL_STACK_RESERVE 16384u
#define FLL_INSERT 1u
#define FLL_FIND 2u
#define FLL_SEARCH 3u
#define FLL_INPUT 1u
#define FLL_IDENTITY 2u
#define FLL_PROFILE 3u
#define FLL_PATH 4u
#define FLL_DATE 5u
#define FLL_DIGEST 6u
#define FLL_CAPACITY 7u
#define FLL_RESERVE 8u
#define FLL_COMPLETE 9u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}FileLifecycleIdentity;
typedef struct{uint32_t kind,length,date_bits;char path[FLL_RAW_MAX];}FileLifecycleOperation;
/* Typed immutable owned fixture request. Modes: 0 ordinary owned array;
 * 1 NULL handle (no operations); 2 append one NULL slot. Modes3..7 describe
 * borrowed node/storage, compressed flags, invalid count/capacity and refuse
 * before original execution. No caller-supplied pointers enter the list.
 * Nonzero INSERT dates exclude filesystem calls. Reservation faults occur
 * before ALL original calls and release every already-reserved host block. */
typedef struct{uint32_t count,directory_length,reserve_fault,fixture_mode;char directory[FLL_PATH_MAX];FileLifecycleOperation operations[FLL_OP_MAX];}FileLifecycleRequest;
typedef struct{char path[FLL_PATH_MAX];uint32_t date_bits;}FileLifecycleEntry;
typedef struct{uint32_t count;FileLifecycleEntry entries[FLL_NODE_MAX];}FileLifecycleResult;
typedef struct{uint32_t status,stage,failed_operation,identity_matched,create_calls,insert_calls,find_calls,search_calls,allocation_calls,earray_insert_calls,directory_calls,normalization_calls,reservation_calls,reserved_nodes,node_count,cleanup_complete,length_calls,destroy_calls,node_free_calls,storage_free_calls,handle_null,slots_cleared,release_order_checked,reservation_releases,fixture_mode;}FileLifecycleReceipt;
/* All arguments and digest context are disjoint spans. Outputs contain owned
 * value copies only and publish after source destruction and owner wipe.
 * No original engine allocator, platform heap, scanning or freshness closure. */
CohStatus filelifecycle_apply(const FileLifecycleRequest*,const FileLifecycleIdentity*,const FileLifecycleIdentity*,const CohCostumeImportDigest*,FileLifecycleResult*,FileLifecycleReceipt*,size_t,size_t);
int filelifecycle_is_idle(void);
size_t filelifecycle_owned_bytes(void);
#endif
'''
PREAMBLE=r'''
#include "file-list-lifecycle-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef int32_t __time32_t;
#define MAX_PATH 260
typedef char host32[(sizeof(int)==4&&sizeof(__time32_t)==4)?1:-1];

#include <stdlib.h>
typedef uint32_t U32;
#define cpp_reinterpret_cast(type) (type)
#define _NORMAL_BLOCK 1
#define devassertmsg(condition,message) assert(condition)
'''
SHELL=r'''
typedef struct{int active;uint32_t allocated,count,last_index,last_found;FileLifecycleRequest request;FileEntry*nodes[FLL_NODE_MAX];FileEntry*order[FLL_NODE_MAX];EArray*storage;uint32_t storage_live;FileLifecycleReceipt receipt;}FileLifecycleOwner;
static FileLifecycleOwner owner;
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static int zero(const void*p,size_t n){const unsigned char*b=p;for(size_t i=0;i<n;i++)if(b[i])return 0;return 1;}
int filelifecycle_is_idle(void){return zero(&owner,sizeof(owner));}
size_t filelifecycle_owned_bytes(void){return sizeof(owner)+EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*)+FLL_NODE_MAX*sizeof(FileEntry);}
/* Explicit ASCII CRT shell, not original platform stricmp implementation. */
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+('a'-'A'):c;}
static int ascii_ncompare(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){unsigned x=lower((unsigned char)a[i]),y=lower((unsigned char)b[i]);if(x!=y)return x<y?-1:1;if(!x)return 0;}return 0;}
static int ascii_compare(const char*a,const char*b){for(;;a++,b++){unsigned x=lower((unsigned char)*a),y=lower((unsigned char)*b);if(x!=y)return x<y?-1:1;if(!x)return 0;}}
#define stricmp ascii_compare
#define strnicmp ascii_ncompare
/* Snapshot has forwardSlashes declaration/calls only. This explicit adapter
 * replaces backslashes only, preserving repeated separators, dots and case. */
static char*forwardSlashes(char*path){assert(owner.active);owner.receipt.normalization_calls++;for(char*p=path;*p;p++)if(*p=='\\')*p='/';return path;}
static char*fileDataDir(void){assert(owner.active);owner.receipt.directory_calls++;return owner.request.directory;}
static __time32_t fileLastChanged(const char*path){(void)path;assert(!"filesystem timestamp branch excluded");return 0;}

static void owned_create(FileList*list){assert(owner.active&&list&&!*list&&!owner.count&&owner.storage_live);*list=(FileList)HandleFromEArray(owner.storage);owner.receipt.create_calls++;}
static void*owned_calloc(size_t n,size_t width){assert(owner.active&&n==sizeof(FileEntry)&&width==1&&owner.allocated<owner.receipt.reserved_nodes&&owner.allocated<FLL_NODE_MAX);owner.receipt.allocation_calls++;return owner.nodes[owner.allocated++];}
static void owned_insert(FileList*list,FileEntry*node,int index){assert(owner.active&&list&&*list==(FileList)HandleFromEArray(owner.storage)&&owner.count<FLL_NODE_MAX&&index>=0&&(unsigned)index<=owner.count&&node==owner.nodes[owner.allocated-1]);EArray*a=EArrayFromHandle(*list);assert(a->count==(int)owner.count);for(uint32_t i=owner.count;i>(unsigned)index;i--)a->structptrs[i]=a->structptrs[i-1];a->structptrs[index]=node;a->count++;owner.count++;owner.receipt.earray_insert_calls++;}
/* Original free(NULL-destructor) call is checked against independently owned
 * reservations and source traversal order, then invokes real host free. */
static void owned_node_free(void*ptr){
 assert(owner.active&&owner.storage_live&&ptr);uint32_t at=owner.receipt.node_free_calls;assert(at<owner.allocated&&ptr==owner.order[at]);
 for(uint32_t i=0;i<at;i++)assert(owner.storage->structptrs[i]==NULL);
 uint32_t i=0;while(i<owner.allocated&&owner.nodes[i]!=ptr)i++;assert(i<owner.allocated);
 wipe(ptr,sizeof(FileEntry));free(ptr);owner.nodes[i]=NULL;owner.order[at]=NULL;owner.receipt.node_free_calls++;owner.receipt.release_order_checked++;
}
static void owned_storage_free(void*ptr,int block){
 assert(owner.active&&block==_NORMAL_BLOCK&&owner.storage_live&&ptr==owner.storage&&owner.storage->flags==0&&owner.storage->count==0&&owner.receipt.node_free_calls==owner.allocated);
 for(uint32_t i=0;i<owner.count;i++)assert(owner.storage->structptrs[i]==NULL);
 owner.receipt.slots_cleared=owner.count;wipe(ptr,EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*));free(ptr);owner.storage=NULL;owner.storage_live=0;owner.receipt.storage_free_calls++;
}
static void reservation_cleanup(void){for(uint32_t i=0;i<FLL_NODE_MAX;i++)if(owner.nodes[i]){wipe(owner.nodes[i],sizeof(FileEntry));free(owner.nodes[i]);owner.nodes[i]=NULL;owner.receipt.reservation_releases++;}if(owner.storage_live){wipe(owner.storage,EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*));free(owner.storage);owner.storage=NULL;owner.storage_live=0;owner.receipt.reservation_releases++;}}
#define eaCreate owned_create
#define eaInsert owned_insert
#define calloc owned_calloc
#define free owned_node_free
#define _free_dbg owned_storage_free
'''
OBSERVER=r'''
static int observed_search(FileList*list,char*path,int*found){owner.receipt.search_calls++;int index=FileListSearch(list,path,found);assert(index>=0&&(unsigned)index<=owner.count);owner.last_index=(uint32_t)index;owner.last_found=(uint32_t)*found;return index;}
#define FileListSearch observed_search
'''
WRAPPER=r'''
#undef FileListSearch
#undef eaCreate
#undef eaInsert
#undef calloc
#undef free
#undef _free_dbg
typedef struct{const void*p;size_t n;}Span;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static int ascii_path(const char*p,size_t n,size_t cap){if(n>=cap||p[n])return 0;for(size_t i=0;i<n;i++)if(!p[i]||(unsigned char)p[i]>127)return 0;return 1;}
CohStatus filelifecycle_apply(const FileLifecycleRequest*request,const FileLifecycleIdentity*observed,const FileLifecycleIdentity*expected,const CohCostumeImportDigest*digest,FileLifecycleResult*out,FileLifecycleReceipt*receipt,size_t budget,size_t retained){
 if(!request||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 Span spans[7]={{request,sizeof(*request)},{observed,sizeof(*observed)},{expected,sizeof(*expected)},{digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(Span){digest->context,digest->context_bytes};if(!valid(spans[6]))return COH_INVALID;for(unsigned i=0;i<6;i++)if(!apart(spans[6],spans[i]))return COH_INVALID;
 FileLifecycleReceipt r;memset(&r,0,sizeof(r));r.stage=FLL_INPUT;r.cleanup_complete=(uint32_t)filelifecycle_is_idle();CohStatus status=COH_OK;uint32_t inserts=0,unique=0;
 char keys[FLL_NODE_MAX][FLL_PATH_MAX];memset(keys,0,sizeof(keys));
 if(!r.cleanup_complete)status=COH_STATE;else if(!budget||budget>FLL_BUDGET_MAX)status=COH_LIMIT;else if(!digest->sha256)status=COH_STATE;
 size_t charge=filelifecycle_owned_bytes()+FLL_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK)goto refused;
 r.stage=FLL_IDENTITY;for(unsigned i=0;i<5;i++)if(zero((const unsigned char*)expected+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK)goto refused;
 r.identity_matched=1;
 r.stage=FLL_PROFILE;if(request->count>FLL_OP_MAX){status=COH_LIMIT;goto refused;}
 r.stage=FLL_PATH;if(!ascii_path(request->directory,request->directory_length,FLL_PATH_MAX)){status=COH_INVALID;goto refused;}
 for(uint32_t i=0;i<request->count;i++){
  const FileLifecycleOperation*op=&request->operations[i];r.failed_operation=i;r.stage=FLL_PROFILE;
  if(op->kind<FLL_INSERT||op->kind>FLL_SEARCH){status=COH_UNSUPPORTED;goto refused;}
  r.stage=FLL_PATH;if(!ascii_path(op->path,op->length,FLL_RAW_MAX)){status=COH_INVALID;goto refused;}
  size_t skip=0;if(op->kind==FLL_INSERT&&!ascii_ncompare(op->path,request->directory,request->directory_length)){skip=request->directory_length;if(op->path[skip]=='/'||op->path[skip]=='\\')skip++;}
  if(op->length-skip>=FLL_PATH_MAX){status=COH_LIMIT;goto refused;}
  if(op->kind==FLL_INSERT){
   r.stage=FLL_DATE;if(!op->date_bits){status=COH_UNSUPPORTED;goto refused;}if(++inserts>FLL_NODE_MAX){status=COH_LIMIT;goto refused;}
   /* Independent bounded capacity admission only, never a replacement source
    * list: linear equality of literal-prefix/slash prepared ASCII keys. */
   char prepared[FLL_PATH_MAX];memset(prepared,0,sizeof(prepared));
   for(size_t j=skip;j<op->length;j++)prepared[j-skip]=op->path[j]=='\\'?'/':op->path[j];
   uint32_t j=0;while(j<unique&&ascii_compare(prepared,keys[j]))j++;
   if(j==unique){memcpy(keys[unique],prepared,sizeof(prepared));unique++;}
   wipe(prepared,sizeof(prepared));
  }
 }
 r.stage=FLL_PROFILE;if(request->reserve_fault>inserts+1u){status=COH_UNSUPPORTED;goto refused;}
 r.stage=FLL_CAPACITY;r.fixture_mode=request->fixture_mode;
 if(request->fixture_mode>2){status=COH_UNSUPPORTED;goto refused;}
 if((request->fixture_mode==1&&request->count)||(request->fixture_mode==2&&unique==FLL_NODE_MAX)){status=COH_LIMIT;goto refused;}
 r.stage=FLL_DIGEST;uint8_t sum[32];memset(sum,0,sizeof(sum));status=digest->sha256(digest->context,(CohBytes){(const uint8_t*)request,sizeof(*request)},sum);if(status==COH_OK&&memcmp(sum,expected->input_sha256,32))status=COH_STATE;wipe(sum,sizeof(sum));if(status!=COH_OK)goto refused;
 r.stage=FLL_RESERVE;owner.active=1;owner.request=*request;owner.receipt=r;owner.receipt.cleanup_complete=0;
 for(uint32_t i=1;i<=inserts+1;i++){
  owner.receipt.reservation_calls++;
  if(request->reserve_fault==i){status=COH_LIMIT;goto reservation_refused;}
  if(request->fixture_mode==1)continue;
  if(i==1){owner.storage=malloc(EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*));if(!owner.storage){status=COH_LIMIT;goto reservation_refused;}owner.storage_live=1;memset(owner.storage,0,EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*));owner.storage->size=FLL_NODE_MAX;}
  else{owner.nodes[i-2]=malloc(sizeof(FileEntry));if(!owner.nodes[i-2]){status=COH_LIMIT;goto reservation_refused;}memset(owner.nodes[i-2],0,sizeof(FileEntry));}
 }
 owner.receipt.reserved_nodes=inserts;wipe(keys,sizeof(keys));FileList list=NULL;if(request->fixture_mode!=1)FileListCreate(&list);
 for(uint32_t i=0;i<request->count;i++){
  FileLifecycleOperation*op=&owner.request.operations[i];
  if(op->kind==FLL_INSERT){__time32_t date;memcpy(&date,&op->date_bits,4);owner.receipt.insert_calls++;FileListInsert(&list,op->path,date);}
  else if(op->kind==FLL_FIND){owner.receipt.find_calls++;(void)FileListFind(&list,op->path);}
  else{int present;(void)observed_search(&list,op->path,&present);}
 }
 assert(owner.count==unique&&owner.allocated==unique);
 FileLifecycleResult candidate;memset(&candidate,0,sizeof(candidate));
 if(request->fixture_mode==2){assert(owner.storage&&owner.count<FLL_NODE_MAX);owner.storage->structptrs[owner.count]=NULL;owner.storage->count++;owner.count++;}
 owner.receipt.length_calls++;candidate.count=(uint32_t)FileListLength(&list);assert(candidate.count==owner.count);
 for(uint32_t i=0;i<unique;i++){FileEntry*node=list[i];owner.order[i]=node;memcpy(candidate.entries[i].path,node->path,MAX_PATH);memcpy(&candidate.entries[i].date_bits,&node->date,4);}
 owner.receipt.node_count=unique;owner.receipt.destroy_calls++;FileListDestroy(&list);assert(!list&&!owner.storage_live);owner.receipt.handle_null=1;
 owner.receipt.length_calls++;assert(FileListLength(&list)==0);owner.receipt.destroy_calls++;FileListDestroy(&list);assert(!list);
 assert(owner.receipt.node_free_calls==unique&&owner.receipt.release_order_checked==unique&&owner.receipt.storage_free_calls==(request->fixture_mode!=1));
 reservation_cleanup();owner.receipt.stage=FLL_COMPLETE;owner.receipt.failed_operation=0;owner.receipt.status=COH_OK;r=owner.receipt;wipe(&owner,sizeof(owner));r.cleanup_complete=(uint32_t)filelifecycle_is_idle();assert(r.cleanup_complete);*out=candidate;*receipt=r;wipe(&candidate,sizeof(candidate));wipe(&r,sizeof(r));return COH_OK;
reservation_refused:reservation_cleanup();r=owner.receipt;wipe(&owner,sizeof(owner));r.cleanup_complete=(uint32_t)filelifecycle_is_idle();assert(r.cleanup_complete);
refused:wipe(keys,sizeof(keys));r.status=(uint32_t)status;*receipt=r;wipe(&r,sizeof(r));return status;
}
'''

def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True);pin_path=HERE/'file-list-lifecycle-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('FileList lifecycle source pin changed: '+name)
  frozen[name]=raw
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()};ec=text[EAR_C];eh=text[EAR_H]
 entry=re.search(r'typedef struct FileEntry\s*\{.*?\}\s*FileEntry\s*;',text[INTERNAL_H],re.S)[0]
 list_type=re.search(r'^typedef FileEntry\*\* FileList;',text[INTERNAL_H],re.M)[0]
 functions={name:extract(text[INTERNAL_C],name)for name in('FileListCreate','FileListSearch','FileListInsert','FileListFind','FileListLength','FileListDestroy')}
 functions.update({name:extract(ec,name)for name in('eaClearExDbg','eaDestroyDbg','eaDestroyExDbg')})
 declarations={'FileEntry':entry,'FileList':list_type,'EArray':re.search(r'typedef struct EArray\s*\{.*?\}\s*EArray;',eh,re.S)[0]}
 for name in('PRIVATE_EARRAY_HEAP','EARRAY_FLAG_CUSTOMALLOC','EARRAY_FLAG_SHAREDMEMORY','EARRAY_HEADER_SIZE','HandleFromEArray','mEACast','eaSize','eaSizeUnsafe','eaClearEx','eaDestroyEx'):
  declarations[name]=re.search(r'^#define '+name+r'\b[^\n]*',eh,re.M)[0]
 declarations['EArrayFromHandle']=re.search(r'^#    define EArrayFromHandle[^\n]*',eh,re.M)[0]
 declarations['EAPtrTest']=re.search(r'^#define EAPtrTest\(ptr\).*?\]\)\)',eh,re.M|re.S)[0]
 declarations['mEArrayHandle']=re.search(r'^typedef void\*\* mEArrayHandle;[^\n]*',eh,re.M)[0]
 declarations['EArrayItemDestructor']=re.search(r'^typedef void \(\*EArrayItemDestructor\)\(void\*\);',eh,re.M)[0]
 header=work/'file-list-lifecycle-provider.h';provider=work/'file-list-lifecycle-provider.c';header.write_text(HEADER)
 definitions='\n'.join(value for key,value in declarations.items())+'\n'
 provider.write_text(PREAMBLE+definitions+SHELL+functions['eaClearExDbg']+functions['eaDestroyDbg']+functions['eaDestroyExDbg']+functions['FileListCreate']+functions['FileListSearch']+OBSERVER+functions['FileListFind']+functions['FileListInsert']+functions['FileListLength']+functions['FileListDestroy']+WRAPPER)
 emitted=provider.read_text()
 for name,body in functions.items():
  if extract(emitted,name)!=body:raise ValueError('Emitted original body changed: '+name)
 for name,body in declarations.items():
  if body not in emitted:raise ValueError('Emitted original declaration changed: '+name)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('Source changed during emission')
 return provider,{'schema':'coh-original-file-list-lifecycle-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'whole_function_sha256_lf':{name:sha(raw.encode())for name,raw in functions.items()},'original_declaration_sha256_lf':{name:sha(raw.encode())for name,raw in declarations.items()},'source_stable_before_after':True,'original_functions_emitted':list(functions),'accepted_ops_provider_reused_as_source_dependency':True,'NULL_destructor_semantics':'Original eaClearExDbg calls free for each non-null element in ascending source array order, nulls slots, count0. Original eaDestroyDbg uses selected PRIVATE_EARRAY_HEAP0 _free_dbg branch, then sets caller handleNULL. Repeated NULL handle destruction safe; handle address NULL excluded.','compile_profile':{'PRIVATE_EARRAY_HEAP':0,'EARRAY_CRAZY_DEBUGGING':False,'CUSTOMALLOC_or_SHARED_flags_admitted':False},'host_adapters':['Pre-reserved host malloc blocks; original calloc returns unique owned node reservation','Checked original free and _free_dbg call adapters invoke actual host free and clear reservation pointers','Fixed eaCreate/eaInsert fixture constructors, exact EArray layout/macros','Accepted ASCII,slash,directory adapters; nonzero signed32 fixture dates; timestamp trap'],'ownership':'No borrowed storage or element pointers; malformed modes refuse before all originals. NULL slots supported. Source node frees/order, count0, slotNULL before header release; nullhandle and second destruction verified. Unused reservations released before owner wipe/atomic pointer-free output.','source_allocator_OOM_recovery_claimed':False,'engine_allocator_closure':False,'standalone_COLLECT_repeated':False,'filesystem_access':False,'freshness_checked':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{'provider':str(provider),'header':str(header)}}
