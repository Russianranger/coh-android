"""Whole original FileListForEach with private bounded fixture-owned recorder.

Accepted operations supply the exact original list constructor functions and
explicit ASCII/slash/earray shells. No prior checker main is invoked.
"""
from pathlib import Path
import hashlib,json,re
import file_list_ops_provider as accepted
HERE=Path(__file__).resolve().parent
INTERNAL_C=accepted.INTERNAL_C
INTERNAL_H=accepted.INTERNAL_H
UTILS_H=accepted.UTILS_H
sha=accepted.sha
extract=accepted.extract
HEADER=r'''/* Fixture only: no filesystem, runtime catalog or freshness authority. */
#ifndef COH_FILE_LIST_FOREACH_PROVIDER_H
#define COH_FILE_LIST_FOREACH_PROVIDER_H
#include "coh_costume_import.h"
#define FFE_OP_MAX 32u
#define FFE_NODE_MAX 16u
#define FFE_PATH_MAX 260u
#define FFE_RAW_MAX 520u
#define FFE_BUDGET_MAX (1024u*1024u)
#define FFE_STACK_RESERVE 16384u
#define FFE_INSERT 1u
#define FFE_FIND 2u
#define FFE_SEARCH 3u
#define FFE_INPUT 1u
#define FFE_IDENTITY 2u
#define FFE_PROFILE 3u
#define FFE_PATH 4u
#define FFE_DATE 5u
#define FFE_DIGEST 6u
#define FFE_CAPACITY 7u
#define FFE_RESERVE 8u
#define FFE_COMPLETE 9u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}FileForEachIdentity;
typedef struct{uint32_t kind,length,date_bits;char path[FFE_RAW_MAX];}FileForEachOperation;
/* Entire fixed typed request is immutable and hashed, including unused bytes.
 * INSERT strips the literal case-insensitive raw prefix before normalizing.
 * FIND normalizes only; SEARCH uses the supplied path literally. Zero INSERT
 * dates refuse even for duplicates, before all original functions execute.
 * reserve_fault 0 succeeds; 1..1+INSERT count refuses owned reservation before
 * source entry. It is not source allocator OOM recovery. callback_capacity is
 * 0..16 and must hold the exact independently preflighted unique stored list.
 * Capacity refusal precedes ALL original calls, including list construction.
 * There is no external callback selector or function-pointer argument. */
typedef struct{uint32_t count,directory_length,reserve_fault,callback_capacity;char directory[FFE_PATH_MAX];FileForEachOperation operations[FFE_OP_MAX];}FileForEachRequest;
/* Callback trace contains owned bytes and signed32 date bits only. */
typedef struct{char path[FFE_PATH_MAX];uint32_t date_bits;}FileForEachEntry;
typedef struct{uint32_t count;FileForEachEntry entries[FFE_NODE_MAX];}FileForEachResult;
typedef struct{uint32_t status,stage,failed_operation,identity_matched,create_calls,insert_calls,find_calls,search_calls,allocation_calls,earray_insert_calls,directory_calls,normalization_calls,reservation_calls,reserved_nodes,node_count,cleanup_complete,foreach_calls,callback_calls,node_addresses_checked,list_unchanged,context_closed,required_callbacks,callback_capacity;}FileForEachReceipt;
/* All request, labels, digest, digest context, output and receipt spans must be
 * valid and disjoint. Invalid sinks stay unchanged. Output commits atomically
 * after source completion and volatile cleanup; only safe numeric diagnostics
 * may change on refusal. No original heap/earray/platform closure is claimed. */
CohStatus fileforeach_apply(const FileForEachRequest*,const FileForEachIdentity*,const FileForEachIdentity*,const CohCostumeImportDigest*,FileForEachResult*,FileForEachReceipt*,size_t,size_t);
int fileforeach_is_idle(void);
size_t fileforeach_owned_bytes(void);
#endif
'''
PREAMBLE=accepted.PREAMBLE.replace("file-list-ops-provider.h","file-list-foreach-provider.h")
SHELL=r'''
typedef struct{int active;uint32_t allocated,count,last_index,last_found;FileForEachRequest request;FileEntry nodes[FFE_NODE_MAX];FileEntry*pointers[FFE_NODE_MAX];FileForEachReceipt receipt;int callback_active;FileEntry snapshot_nodes[FFE_NODE_MAX];FileEntry*snapshot_pointers[FFE_NODE_MAX];FileForEachResult trace;}FileForEachOwner;
static FileForEachOwner owner;
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static int zero(const void*p,size_t n){const unsigned char*b=p;for(size_t i=0;i<n;i++)if(b[i])return 0;return 1;}
int fileforeach_is_idle(void){return zero(&owner,sizeof(owner));}
size_t fileforeach_owned_bytes(void){return sizeof(owner);}
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
static void owned_create(FileList*list){assert(owner.active&&list&&!*list&&!owner.count);*list=owner.pointers;owner.receipt.create_calls++;}
static int owned_size(FileList*list){assert(owner.active&&list&&*list==owner.pointers);return(int)owner.count;}
static void*owned_calloc(size_t n,size_t width){assert(owner.active&&n==sizeof(FileEntry)&&width==1&&owner.allocated<owner.receipt.reserved_nodes&&owner.allocated<FFE_NODE_MAX);owner.receipt.allocation_calls++;return &owner.nodes[owner.allocated++];}
static void owned_insert(FileList*list,FileEntry*node,int index){assert(owner.active&&list&&*list==owner.pointers&&owner.count<FFE_NODE_MAX&&index>=0&&(unsigned)index<=owner.count&&node==&owner.nodes[owner.allocated-1]);for(uint32_t i=owner.count;i>(unsigned)index;i--)owner.pointers[i]=owner.pointers[i-1];owner.pointers[index]=node;owner.count++;owner.receipt.earray_insert_calls++;}
#define eaCreate owned_create
#define eaSize owned_size
#define eaInsert owned_insert
#define calloc owned_calloc
'''
OBSERVER=accepted.OBSERVER
CALLBACK=r'''
/* Fixed private callback: source has mutable char*, but this callback never
 * changes nodes/list or retains a pointer. Only copied path/date bytes survive
 * until wrapper cleanup. No caller-supplied executable callback is admitted. */
static void owned_callback(char*path,__time32_t date){
 assert(owner.active&&owner.callback_active==1);
 uint32_t i=owner.receipt.callback_calls;
 assert(i<owner.count&&i<owner.request.callback_capacity&&i<FFE_NODE_MAX);
 FileEntry*node=owner.snapshot_pointers[i];uintptr_t start=(uintptr_t)owner.nodes,at=(uintptr_t)node;
 assert(at>=start&&at-start<sizeof(owner.nodes)&&(at-start)%sizeof(FileEntry)==0);
 assert(path==node->path&&path==owner.pointers[i]->path);
 uint32_t date_bits;memcpy(&date_bits,&date,4);
 assert(!memcmp(&date_bits,&node->date,4));
 owner.receipt.node_addresses_checked++;
 memcpy(owner.trace.entries[i].path,path,MAX_PATH);
 memcpy(&owner.trace.entries[i].date_bits,&date,4);
 owner.receipt.callback_calls++;owner.trace.count++;
}
'''
WRAPPER=r'''
#undef FileListSearch
#undef eaCreate
#undef eaSize
#undef eaInsert
#undef calloc
typedef struct{const void*p;size_t n;}Span;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static int ascii_path(const char*p,size_t n,size_t cap){if(n>=cap||p[n])return 0;for(size_t i=0;i<n;i++)if(!p[i]||(unsigned char)p[i]>127)return 0;return 1;}
CohStatus fileforeach_apply(const FileForEachRequest*request,const FileForEachIdentity*observed,const FileForEachIdentity*expected,const CohCostumeImportDigest*digest,FileForEachResult*out,FileForEachReceipt*receipt,size_t budget,size_t retained){
 if(!request||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 Span spans[7]={{request,sizeof(*request)},{observed,sizeof(*observed)},{expected,sizeof(*expected)},{digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(Span){digest->context,digest->context_bytes};if(!valid(spans[6]))return COH_INVALID;for(unsigned i=0;i<6;i++)if(!apart(spans[6],spans[i]))return COH_INVALID;
 FileForEachReceipt r;memset(&r,0,sizeof(r));r.stage=FFE_INPUT;r.cleanup_complete=(uint32_t)fileforeach_is_idle();CohStatus status=COH_OK;uint32_t inserts=0,unique=0;
 char keys[FFE_NODE_MAX][FFE_PATH_MAX];memset(keys,0,sizeof(keys));
 if(!r.cleanup_complete)status=COH_STATE;else if(!budget||budget>FFE_BUDGET_MAX)status=COH_LIMIT;else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+FFE_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK)goto refused;
 r.stage=FFE_IDENTITY;for(unsigned i=0;i<5;i++)if(zero((const unsigned char*)expected+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK)goto refused;
 r.identity_matched=1;
 r.stage=FFE_PROFILE;if(request->count>FFE_OP_MAX){status=COH_LIMIT;goto refused;}
 r.stage=FFE_PATH;if(!ascii_path(request->directory,request->directory_length,FFE_PATH_MAX)){status=COH_INVALID;goto refused;}
 for(uint32_t i=0;i<request->count;i++){
  const FileForEachOperation*op=&request->operations[i];r.failed_operation=i;r.stage=FFE_PROFILE;
  if(op->kind<FFE_INSERT||op->kind>FFE_SEARCH){status=COH_UNSUPPORTED;goto refused;}
  r.stage=FFE_PATH;if(!ascii_path(op->path,op->length,FFE_RAW_MAX)){status=COH_INVALID;goto refused;}
  size_t skip=0;if(op->kind==FFE_INSERT&&!ascii_ncompare(op->path,request->directory,request->directory_length)){skip=request->directory_length;if(op->path[skip]=='/'||op->path[skip]=='\\')skip++;}
  if(op->length-skip>=FFE_PATH_MAX){status=COH_LIMIT;goto refused;}
  if(op->kind==FFE_INSERT){
   r.stage=FFE_DATE;if(!op->date_bits){status=COH_UNSUPPORTED;goto refused;}if(++inserts>FFE_NODE_MAX){status=COH_LIMIT;goto refused;}
   /* Independent bounded capacity admission only, never a replacement source
    * list: linear equality of literal-prefix/slash prepared ASCII keys. */
   char prepared[FFE_PATH_MAX];memset(prepared,0,sizeof(prepared));
   for(size_t j=skip;j<op->length;j++)prepared[j-skip]=op->path[j]=='\\'?'/':op->path[j];
   uint32_t j=0;while(j<unique&&ascii_compare(prepared,keys[j]))j++;
   if(j==unique){memcpy(keys[unique],prepared,sizeof(prepared));unique++;}
   wipe(prepared,sizeof(prepared));
  }
 }
 r.stage=FFE_PROFILE;if(request->reserve_fault>inserts+1u){status=COH_UNSUPPORTED;goto refused;}
 r.stage=FFE_CAPACITY;r.required_callbacks=unique;r.callback_capacity=request->callback_capacity;
 if(request->callback_capacity>FFE_NODE_MAX){status=COH_UNSUPPORTED;goto refused;}
 if(request->callback_capacity<unique){status=COH_LIMIT;goto refused;}
 r.stage=FFE_DIGEST;uint8_t sum[32];memset(sum,0,sizeof(sum));status=digest->sha256(digest->context,(CohBytes){(const uint8_t*)request,sizeof(*request)},sum);if(status==COH_OK&&memcmp(sum,expected->input_sha256,32))status=COH_STATE;wipe(sum,sizeof(sum));if(status!=COH_OK)goto refused;
 r.stage=FFE_RESERVE;for(uint32_t i=1;i<=inserts+1;i++){r.reservation_calls++;if(request->reserve_fault==i){status=COH_LIMIT;goto refused;}}r.reserved_nodes=inserts;
 wipe(keys,sizeof(keys));
 owner.active=1;owner.request=*request;owner.receipt=r;owner.receipt.cleanup_complete=0;FileList list=NULL;FileListCreate(&list);
 for(uint32_t i=0;i<request->count;i++){
  FileForEachOperation*op=&owner.request.operations[i];
  if(op->kind==FFE_INSERT){__time32_t date;memcpy(&date,&op->date_bits,4);owner.receipt.insert_calls++;FileListInsert(&list,op->path,date);}
  else if(op->kind==FFE_FIND){owner.receipt.find_calls++;(void)FileListFind(&list,op->path);}
  else{int present;(void)observed_search(&list,op->path,&present);}
 }
 assert(owner.count==unique&&!owner.callback_active&&!owner.trace.count);
 memcpy(owner.snapshot_nodes,owner.nodes,sizeof(owner.nodes));memcpy(owner.snapshot_pointers,owner.pointers,sizeof(owner.pointers));
 owner.receipt.foreach_calls++;owner.callback_active=1;
 FileListForEach(&list,owned_callback);
 owner.callback_active=0;owner.receipt.context_closed=1;
 assert(owner.trace.count==unique&&owner.receipt.callback_calls==unique&&owner.receipt.node_addresses_checked==unique);
 assert(list==owner.pointers&&!memcmp(owner.nodes,owner.snapshot_nodes,sizeof(owner.nodes))&&!memcmp(owner.pointers,owner.snapshot_pointers,sizeof(owner.pointers)));
 owner.receipt.list_unchanged=1;owner.receipt.node_count=owner.count;owner.receipt.stage=FFE_COMPLETE;owner.receipt.failed_operation=0;owner.receipt.status=COH_OK;
 FileForEachResult candidate=owner.trace;r=owner.receipt;list=NULL;wipe(&owner,sizeof(owner));r.cleanup_complete=(uint32_t)fileforeach_is_idle();assert(r.cleanup_complete);*out=candidate;*receipt=r;wipe(&candidate,sizeof(candidate));wipe(&r,sizeof(r));return COH_OK;
refused:wipe(keys,sizeof(keys));r.status=(uint32_t)status;*receipt=r;wipe(&r,sizeof(r));return status;
}
'''
def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True);pin_path=HERE/'file-list-foreach-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('FileListForEach source pin changed: '+name)
  frozen[name]=raw
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()}
 entry=re.search(r'typedef struct FileEntry\s*\{.*?\}\s*FileEntry\s*;',text[INTERNAL_H],re.S)[0]
 list_type=re.search(r'^typedef FileEntry\*\* FileList;',text[INTERNAL_H],re.M)[0]
 callback_type=re.search(r'^typedef void \(\*FileListCallback\)\(char\* path, __time32_t date\);',text[INTERNAL_H],re.M)[0]
 functions={name:extract(text[INTERNAL_C],name)for name in('FileListCreate','FileListSearch','FileListInsert','FileListFind','FileListForEach')}
 declaration=re.search(r'^char \*forwardSlashes\(char \*path\);',text[UTILS_H],re.M)[0]
 provider=work/'file-list-foreach-provider.c';header=work/'file-list-foreach-provider.h';header.write_text(HEADER)
 provider.write_text(PREAMBLE+entry+'\n'+list_type+'\n'+callback_type+'\n'+SHELL+functions['FileListCreate']+functions['FileListSearch']+OBSERVER+functions['FileListFind']+functions['FileListInsert']+functions['FileListForEach']+CALLBACK+WRAPPER)
 emitted=provider.read_text()
 for name,body in functions.items():
  if extract(emitted,name)!=body:raise ValueError('Emitted original body changed: '+name)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('Source changed during emission')
 proof={'schema':'coh-original-file-list-foreach-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'whole_function_sha256_lf':{name:sha(raw.encode())for name,raw in functions.items()},'original_declaration_sha256_lf':{'FileEntry':sha(entry.encode()),'FileList':sha(list_type.encode()),'FileListCallback':sha(callback_type.encode()),'forwardSlashes_declaration_only':sha(declaration.encode())},'source_stable_before_after':True,'original_functions_emitted':list(functions),'accepted_ops_provider_reused_as_source_dependency':True,'callback':'Private fixed owned recorder only; exact owned node.path address/order/date checks, copies bytes only. Full node and pointer snapshots unchanged; active context restricted to source traversal, cleared and wiped before atomic output. No borrowed pointer escape.','capacity':'Independently preflight exact unique normalized INSERT keys before any original call; callback_capacity0..16 and >=unique. No partial acceptance.','host_adapters':['Accepted explicit ASCII stricmp/strnicmp and backslash-to-slash adapter; original helper implementation absent','Owned fixed earray/calloc, directory, callback; fileLastChanged trap; nonzero signed32 fixture dates only','Reservation refusal BEFORE all originals, no unchecked source calloc NULL recovery claim','Host int32/MAX_PATH260 shell, no original ABI/allocator/earray closure'],'profile':'32 operations,16 INSERT calls including duplicates,16 unique nodes; raw path519/directory259/post-strip-or-lookup259; exact source literal prefix/case/slash semantics','FileListLength_or_Destroy_executed':False,'standalone_COLLECT_repeated':False,'filesystem_access':False,'freshness_checked':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{'provider':str(provider),'header':str(header)}}
 return provider,proof
