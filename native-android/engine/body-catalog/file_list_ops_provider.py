"""Unchanged original FileList operations in an explicit owned fixture shell."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
INTERNAL_C='upstream/ouroboros/libs/UtilitiesLib/src/utils/structInternals.c'
INTERNAL_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/structInternals.h'
UTILS_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/utils.h'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def extract(text,name):
 match=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*)?\s*\{',text,re.M)
 if not match:raise ValueError('missing original FileList operation '+name)
 at=text.index('{',match.start())+1;depth=1
 while depth:
  if at>=len(text):raise ValueError('unterminated original function '+name)
  depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[match.start():at]+'\n'
HEADER=r'''/* Fixture only: no filesystem, runtime catalog or freshness authority. */
#ifndef COH_FILE_LIST_OPS_PROVIDER_H
#define COH_FILE_LIST_OPS_PROVIDER_H
#include "coh_costume_import.h"
#define FLO_OP_MAX 32u
#define FLO_NODE_MAX 16u
#define FLO_PATH_MAX 260u
#define FLO_RAW_MAX 520u
#define FLO_BUDGET_MAX (1024u*1024u)
#define FLO_STACK_RESERVE 16384u
#define FLO_INSERT 1u
#define FLO_FIND 2u
#define FLO_SEARCH 3u
#define FLO_INPUT 1u
#define FLO_IDENTITY 2u
#define FLO_PROFILE 3u
#define FLO_PATH 4u
#define FLO_DATE 5u
#define FLO_DIGEST 6u
#define FLO_RESERVE 7u
#define FLO_COMPLETE 8u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}FileOpsIdentity;
typedef struct{uint32_t kind,length,date_bits;char path[FLO_RAW_MAX];}FileOpsOperation;
/* Entire fixed typed request is immutable and hashed, including unused bytes.
 * INSERT strips the literal case-insensitive raw prefix before normalizing.
 * FIND normalizes only; SEARCH uses the supplied path literally. Zero INSERT
 * dates refuse even for duplicates, before all original functions execute.
 * reserve_fault 0 succeeds; 1..1+INSERT count refuses owned reservation before
 * source entry. It is not source allocator OOM recovery. */
typedef struct{uint32_t count,directory_length,reserve_fault;char directory[FLO_PATH_MAX];FileOpsOperation operations[FLO_OP_MAX];}FileOpsRequest;
typedef struct{char path[FLO_PATH_MAX];uint32_t date_bits,seen;}FileOpsEntry;
typedef struct{uint32_t found,index,count_after,inserted,date_bits;}FileOpsOperationResult;
typedef struct{uint32_t count;FileOpsEntry entries[FLO_NODE_MAX];FileOpsOperationResult operations[FLO_OP_MAX];}FileOpsResult;
typedef struct{uint32_t status,stage,failed_operation,identity_matched,create_calls,insert_calls,find_calls,search_calls,allocation_calls,earray_insert_calls,directory_calls,normalization_calls,reservation_calls,reserved_nodes,node_count,cleanup_complete;}FileOpsReceipt;
/* All request, labels, digest, digest context, output and receipt spans must be
 * valid and disjoint. Invalid sinks stay unchanged. Output commits atomically
 * after source completion and volatile cleanup; only safe numeric diagnostics
 * may change on refusal. No original heap/earray/platform closure is claimed. */
CohStatus fileops_apply(const FileOpsRequest*,const FileOpsIdentity*,const FileOpsIdentity*,const CohCostumeImportDigest*,FileOpsResult*,FileOpsReceipt*,size_t,size_t);
int fileops_is_idle(void);
size_t fileops_owned_bytes(void);
#endif
'''
PREAMBLE=r'''
#include "file-list-ops-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef int32_t __time32_t;
#define MAX_PATH 260
typedef char host32[(sizeof(int)==4&&sizeof(__time32_t)==4)?1:-1];
'''
SHELL=r'''
typedef struct{int active;uint32_t allocated,count,last_index,last_found;FileOpsRequest request;FileEntry nodes[FLO_NODE_MAX];FileEntry*pointers[FLO_NODE_MAX];FileOpsReceipt receipt;}FileOpsOwner;
static FileOpsOwner owner;
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static int zero(const void*p,size_t n){const unsigned char*b=p;for(size_t i=0;i<n;i++)if(b[i])return 0;return 1;}
int fileops_is_idle(void){return zero(&owner,sizeof(owner));}
size_t fileops_owned_bytes(void){return sizeof(owner);}
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
static void*owned_calloc(size_t n,size_t width){assert(owner.active&&n==sizeof(FileEntry)&&width==1&&owner.allocated<owner.receipt.reserved_nodes&&owner.allocated<FLO_NODE_MAX);owner.receipt.allocation_calls++;return &owner.nodes[owner.allocated++];}
static void owned_insert(FileList*list,FileEntry*node,int index){assert(owner.active&&list&&*list==owner.pointers&&owner.count<FLO_NODE_MAX&&index>=0&&(unsigned)index<=owner.count&&node==&owner.nodes[owner.allocated-1]);for(uint32_t i=owner.count;i>(unsigned)index;i--)owner.pointers[i]=owner.pointers[i-1];owner.pointers[index]=node;owner.count++;owner.receipt.earray_insert_calls++;}
#define eaCreate owned_create
#define eaSize owned_size
#define eaInsert owned_insert
#define calloc owned_calloc
'''
OBSERVER=r'''
static int observed_search(FileList*list,char*path,int*found){owner.receipt.search_calls++;int index=FileListSearch(list,path,found);assert(index>=0&&(unsigned)index<=owner.count);owner.last_index=(uint32_t)index;owner.last_found=(uint32_t)*found;return index;}
#define FileListSearch observed_search
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
CohStatus fileops_apply(const FileOpsRequest*request,const FileOpsIdentity*observed,const FileOpsIdentity*expected,const CohCostumeImportDigest*digest,FileOpsResult*out,FileOpsReceipt*receipt,size_t budget,size_t retained){
 if(!request||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 Span spans[7]={{request,sizeof(*request)},{observed,sizeof(*observed)},{expected,sizeof(*expected)},{digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(Span){digest->context,digest->context_bytes};if(!valid(spans[6]))return COH_INVALID;for(unsigned i=0;i<6;i++)if(!apart(spans[6],spans[i]))return COH_INVALID;
 FileOpsReceipt r;memset(&r,0,sizeof(r));r.stage=FLO_INPUT;r.cleanup_complete=(uint32_t)fileops_is_idle();CohStatus status=COH_OK;uint32_t inserts=0;
 if(!r.cleanup_complete)status=COH_STATE;else if(!budget||budget>FLO_BUDGET_MAX)status=COH_LIMIT;else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+FLO_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK)goto refused;
 r.stage=FLO_IDENTITY;for(unsigned i=0;i<5;i++)if(zero((const unsigned char*)expected+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK)goto refused;
 r.identity_matched=1;
 r.stage=FLO_PROFILE;if(request->count>FLO_OP_MAX){status=COH_LIMIT;goto refused;}
 r.stage=FLO_PATH;if(!ascii_path(request->directory,request->directory_length,FLO_PATH_MAX)){status=COH_INVALID;goto refused;}
 for(uint32_t i=0;i<request->count;i++){
  const FileOpsOperation*op=&request->operations[i];r.failed_operation=i;r.stage=FLO_PROFILE;
  if(op->kind<FLO_INSERT||op->kind>FLO_SEARCH){status=COH_UNSUPPORTED;goto refused;}
  r.stage=FLO_PATH;if(!ascii_path(op->path,op->length,FLO_RAW_MAX)){status=COH_INVALID;goto refused;}
  size_t skip=0;if(op->kind==FLO_INSERT&&!ascii_ncompare(op->path,request->directory,request->directory_length)){skip=request->directory_length;if(op->path[skip]=='/'||op->path[skip]=='\\')skip++;}
  if(op->length-skip>=FLO_PATH_MAX){status=COH_LIMIT;goto refused;}
  if(op->kind==FLO_INSERT){r.stage=FLO_DATE;if(!op->date_bits){status=COH_UNSUPPORTED;goto refused;}if(++inserts>FLO_NODE_MAX){status=COH_LIMIT;goto refused;}}
 }
 r.stage=FLO_PROFILE;if(request->reserve_fault>inserts+1u){status=COH_UNSUPPORTED;goto refused;}
 r.stage=FLO_DIGEST;uint8_t sum[32];memset(sum,0,sizeof(sum));status=digest->sha256(digest->context,(CohBytes){(const uint8_t*)request,sizeof(*request)},sum);if(status==COH_OK&&memcmp(sum,expected->input_sha256,32))status=COH_STATE;wipe(sum,sizeof(sum));if(status!=COH_OK)goto refused;
 r.stage=FLO_RESERVE;for(uint32_t i=1;i<=inserts+1;i++){r.reservation_calls++;if(request->reserve_fault==i){status=COH_LIMIT;goto refused;}}r.reserved_nodes=inserts;
 owner.active=1;owner.request=*request;owner.receipt=r;owner.receipt.cleanup_complete=0;FileList list=NULL;FileListCreate(&list);FileOpsResult candidate;memset(&candidate,0,sizeof(candidate));
 for(uint32_t i=0;i<request->count;i++){
  FileOpsOperation*op=&owner.request.operations[i];FileOpsOperationResult*answer=&candidate.operations[i];FileEntry*found=NULL;answer->index=UINT32_MAX;
  if(op->kind==FLO_INSERT){__time32_t date;memcpy(&date,&op->date_bits,4);uint32_t before=owner.count;owner.receipt.insert_calls++;FileListInsert(&list,op->path,date);answer->found=owner.last_found;answer->index=owner.last_index;answer->inserted=owner.count-before;found=list[answer->index];}
  else if(op->kind==FLO_FIND){owner.receipt.find_calls++;found=FileListFind(&list,op->path);answer->found=(uint32_t)(found!=NULL);if(found)for(uint32_t j=0;j<owner.count;j++)if(list[j]==found)answer->index=j;}
  else{int present;answer->index=(uint32_t)observed_search(&list,op->path,&present);answer->found=(uint32_t)present;if(present)found=list[answer->index];}
  answer->count_after=owner.count;if(found)memcpy(&answer->date_bits,&found->date,4);
 }
 candidate.count=owner.count;for(uint32_t i=0;i<owner.count;i++){assert(list[i]>=owner.nodes&&list[i]<owner.nodes+FLO_NODE_MAX);memcpy(candidate.entries[i].path,list[i]->path,MAX_PATH);memcpy(&candidate.entries[i].date_bits,&list[i]->date,4);memcpy(&candidate.entries[i].seen,&list[i]->seen,4);}
 owner.receipt.node_count=owner.count;owner.receipt.stage=FLO_COMPLETE;owner.receipt.failed_operation=0;owner.receipt.status=COH_OK;r=owner.receipt;list=NULL;wipe(&owner,sizeof(owner));r.cleanup_complete=(uint32_t)fileops_is_idle();*out=candidate;*receipt=r;wipe(&candidate,sizeof(candidate));wipe(&r,sizeof(r));return COH_OK;
refused:r.status=(uint32_t)status;*receipt=r;wipe(&r,sizeof(r));return status;
}
'''
def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True);pin_path=HERE/'file-list-ops-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('FileList ops pin changed: '+name)
  frozen[name]=raw
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()};entry=re.search(r'typedef struct FileEntry\s*\{.*?\}\s*FileEntry\s*;',text[INTERNAL_H],re.S)[0];list_type=re.search(r'^typedef FileEntry\*\* FileList;',text[INTERNAL_H],re.M)[0]
 functions={name:extract(text[INTERNAL_C],name)for name in('FileListCreate','FileListSearch','FileListInsert','FileListFind')}
 declaration=re.search(r'^char \*forwardSlashes\(char \*path\);',text[UTILS_H],re.M)[0]
 header=work/'file-list-ops-provider.h';header.write_text(HEADER);provider=work/'file-list-ops-provider.c';provider.write_text(PREAMBLE+entry+'\n'+list_type+'\n'+SHELL+functions['FileListCreate']+functions['FileListSearch']+OBSERVER+functions['FileListFind']+functions['FileListInsert']+WRAPPER)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('Source changed during emission')
 proof={'schema':'coh-original-file-list-ops-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'whole_function_sha256_lf':{name:sha(raw.encode())for name,raw in functions.items()},'original_declaration_sha256_lf':{'FileEntry':sha(entry.encode()),'FileList':sha(list_type.encode()),'forwardSlashes_declaration_only':sha(declaration.encode())},'source_stable_before_after':True,'host_adapters':['Explicit ASCII stricmp/strnicmp comparisons; no platform CRT ABI claim','forwardSlashes is an explicit backslash-to-slash adapter; pinned source snapshot contains declaration/calls only, not its implementation','Fixed fixture-owned fileDataDir string; real fileLastChanged is an assertion trap, zero dates refuse before source entry','Fixed zeroed FileEntry calloc and eaCreate/eaSize/eaInsert shells; not original allocator/earray closure','Owned reservation fault refusal BEFORE FileListCreate; source calloc never receives injected NULL and source OOM recovery is NOT claimed','Exact original signed32 time/FileEntry/FileList declarations under explicit MAX_PATH260/int32 host shell; original Win32/Android ABI unqualified'],'semantics':'Exact original binary search, literal case-insensitive raw data-directory prefix removal without component boundary, one leading separator removal after prefix, then slash adapter; Find normalizes without prefix removal, Search receives literal path; duplicates retain original spelling/date; source insertion positions preserved. No canonicalization of dots/repeated separators.','profile':'32 ops; at most16 INSERT calls, including duplicates; raw paths<=519, fixture directory<=259; post-strip INSERT path<=259, FIND/SEARCH supplied path<=259; non-NUL ASCII; nonzero date bits only','allocation_failure_scope':'Wrapper reservation only; no claim original unchecked calloc survives OOM','original_functions_emitted':list(functions),'original_forwardSlashes_implementation_executed':False,'source_earray_or_allocator_executed':False,'filesystem_access':False,'freshness_checked':False,'current_Map_runtime_executed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{'provider':str(provider),'header':str(header)}}
 return provider,proof
