"""Original FileListRead NULL-skip/collect leaf; bounded source fixture only."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
SERIAL_C='upstream/ouroboros/libs/UtilitiesLib/src/utils/serialize.c'
SERIAL_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/serialize.h'
PARSER_C='upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c'
PARSER_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h'
INTERNAL_C='upstream/ouroboros/libs/UtilitiesLib/src/utils/structInternals.c'
INTERNAL_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/structInternals.h'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def extract(text,name):
 match=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*)?\s*\{',text,re.M)
 if not match:raise ValueError('missing original dependency-list function '+name)
 at=text.index('{',match.start())+1;depth=1
 while depth:
  if at>=len(text):raise ValueError('unterminated original dependency-list function '+name)
  depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[match.start():at]+'\n'
HEADER=r'''/* Bounded dependency-list source fixture, never runtime catalog provenance. */
#ifndef COH_FILE_LIST_READ_PROVIDER_H
#define COH_FILE_LIST_READ_PROVIDER_H
#include "coh_costume_import.h"
#define FILELIST_STAGE_INPUT 1u
#define FILELIST_STAGE_IDENTITY 2u
#define FILELIST_STAGE_PROFILE 3u
#define FILELIST_STAGE_HEADER 4u
#define FILELIST_STAGE_TYPE_LENGTH 5u
#define FILELIST_STAGE_HEADER_EXTENT 6u
#define FILELIST_STAGE_DEPENDENCY_HEADER 7u
#define FILELIST_STAGE_DEPENDENCY_SIZE 8u
#define FILELIST_STAGE_COUNT 9u
#define FILELIST_STAGE_ROW 10u
#define FILELIST_STAGE_DIGEST 11u
#define FILELIST_STAGE_OPEN 12u
#define FILELIST_STAGE_HEADER_REJECT 13u
#define FILELIST_STAGE_SOURCE_REJECT 14u
#define FILELIST_STAGE_COMPLETE 15u
#define FILELIST_MODE_NULL_SKIP 0u
#define FILELIST_MODE_COLLECT 1u
#define FILELIST_ENTRY_MAX 16u
#define FILELIST_PATH_MAX 260u
#define FILELIST_INPUT_MAX 65536u
#define FILELIST_BUDGET_MAX (1024u*1024u)
#define FILELIST_STACK_RESERVE 16384u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}FileListIdentity;
typedef struct{char path[FILELIST_PATH_MAX];uint32_t date_bits,seen;}FileListEntryResult;
typedef struct{uint32_t header_end,dependency_end,count_observed,count;FileListEntryResult entries[FILELIST_ENTRY_MAX];}FileListResult;
typedef struct{
 uint32_t status,stage,failure_byte,open_calls,read_calls,seek_calls;
 uint32_t source_close_calls,wrapper_close_calls,header_accepted,filelist_calls;
 uint32_t collect_calls,null_skip_calls,allocation_calls,push_calls,warning_calls,source_result;
 uint32_t header_end,dependency_end,source_node_count,fixture_identity_matched,cleanup_complete;
}FileListReceipt;
/* Every caller span/context must be disjoint. Invalid sinks stay unchanged.
 * Safe bounded numeric diagnostics may change on failure; snapshots commit only
 * after source acceptance and owned cleanup. NULL-skip count is unobserved.
 * CRC comparison argument is fixture data, never actual ParseTableCRC/build_id.
 */
CohStatus filelist_apply(CohBytes,const FileListIdentity*,const FileListIdentity*,
 const CohCostumeImportDigest*,uint32_t,uint32_t,uint32_t,
 FileListResult*,FileListReceipt*,size_t,size_t);
int filelist_is_idle(void);
#endif
'''
PREAMBLE=r'''
#include "file-list-read-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint16_t U16;typedef uint32_t U32;typedef int32_t __time32_t;
#define INLINEDBG inline
#define endianSwapIfBig(type,value) (value)
/* Explicit Win32-shaped path-width shell, not a qualified platform ABI. */
#define MAX_PATH 260
typedef char host_int32[(sizeof(int)==4&&sizeof(__time32_t)==4)?1:-1];
'''
ADAPTERS=r'''
typedef struct{
 int active,opened,wrapper_closing;size_t input_size;uint32_t node_count,pushed;
 unsigned char data[FILELIST_INPUT_MAX];SimpleBuffer buffer;
 FileEntry nodes[FILELIST_ENTRY_MAX];FileEntry* pointers[FILELIST_ENTRY_MAX];
 FileListReceipt receipt;
}FileListOwner;
static FileListOwner owner;
static void filelist_wipe(void*p,size_t n){volatile unsigned char*c=p;while(n--)*c++=0;}
static int zeros(const void*p,size_t n){const unsigned char*c=p;for(size_t i=0;i<n;i++)if(c[i])return 0;return 1;}
int filelist_is_idle(void){return zeros(&owner,sizeof(owner));}
int SimpleBufTell(SimpleBufHandle);
static SimpleBufHandle SimpleBufOpenRead(const char*name){
 assert(owner.active&&!owner.opened&&!strcmp(name,"bin/BodyParts.bin"));owner.receipt.open_calls++;
 owner.buffer.data=(char*)owner.data;owner.buffer.filesize=(int)owner.input_size;
 owner.buffer.memsize=(int)sizeof(owner.data);memcpy(owner.buffer.filename,name,sizeof("bin/BodyParts.bin"));
 owner.opened=1;return (SimpleBufHandle)&owner.buffer;
}
static void SimpleBufClose(SimpleBufHandle file){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer&&!owner.buffer.writing);
 if(!owner.receipt.header_accepted)owner.receipt.header_end=(uint32_t)SimpleBufTell(file);
 if(owner.wrapper_closing)owner.receipt.wrapper_close_calls++;else owner.receipt.source_close_calls++;
 owner.opened=0;filelist_wipe(&owner.buffer,sizeof(owner.buffer));filelist_wipe(owner.data,sizeof(owner.data));
}
static void SimpleBufResizeEx(SimpleBufHandle file,int bytes){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer);
 assert(bytes>=0&&bytes<=owner.buffer.filesize&&owner.buffer.memsize==(int)sizeof(owner.data));
}
/* Fixed owned allocation/earray adapters, never general allocator semantics. */
static void*owned_calloc(size_t count,size_t size){
 assert(owner.active&&count==sizeof(FileEntry)&&size==1&&owner.node_count<FILELIST_ENTRY_MAX);
 owner.receipt.allocation_calls++;return &owner.nodes[owner.node_count++];
}
static void owned_eacreate(FileList*list){assert(owner.active&&list&&!*list&&!owner.pushed);*list=owner.pointers;}
static void owned_eapush(FileList*list,FileEntry*node){
 assert(owner.active&&list&&*list==owner.pointers&&owner.pushed<FILELIST_ENTRY_MAX);
 assert(node==&owner.nodes[owner.pushed]&&owner.node_count==owner.pushed+1);
 owner.pointers[owner.pushed++]=node;owner.receipt.push_calls++;
}
#define calloc owned_calloc
#define eaCreate owned_eacreate
#define eaPush owned_eapush
'''
OBSERVERS=r'''
static int observed_read(void*data,int bytes,SimpleBufHandle file){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer&&bytes>=0);
 owner.receipt.read_calls++;return SimpleBufRead(data,bytes,file);
}
static int observed_seek(SimpleBufHandle file,long offset,int origin){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer);
 owner.receipt.seek_calls++;return SimpleBufSeek(file,offset,origin);
}
static int observed_printf(const char*format,...){
 assert(owner.active&&format&&!strcmp(format,"ReadPascalString: string read too long for size\n"));
 owner.receipt.warning_calls++;assert(owner.receipt.warning_calls<=FILELIST_ENTRY_MAX);return 0;
}
#define SimpleBufRead observed_read
#define SimpleBufSeek observed_seek
#define printf observed_printf
'''
WRAPPER=r'''
#undef SimpleBufRead
#undef SimpleBufSeek
#undef printf
#undef calloc
#undef eaCreate
#undef eaPush
typedef struct{const void*p;size_t n;}FileListSpan;
static int valid_span(FileListSpan s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(FileListSpan a,FileListSpan b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static uint32_t read16(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8;}
static uint32_t read32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int32_t signed32(uint32_t word){int32_t value;memcpy(&value,&word,4);return value;}
static int cstring_matches(const uint8_t*p,size_t n,const char*expected){
 size_t used=0;while(used<n&&p[used])used++;
 return used==strlen(expected)&&!memcmp(p,expected,used);
}
static CohStatus framing(CohBytes bytes,uint32_t build_crc,uint32_t ignore_crc,uint32_t mode,FileListReceipt*r){
 r->stage=FILELIST_STAGE_HEADER;
 if(bytes.size<14){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 uint32_t len=read16(bytes.data+12);r->stage=FILELIST_STAGE_TYPE_LENGTH;
 if(len>=MAX_FILETYPE_LEN){r->failure_byte=12;return COH_LIMIT;}
 size_t at=14u+len+(4u-(len+2u)%4u)%4u;r->stage=FILELIST_STAGE_HEADER_EXTENT;
 if(at>bytes.size){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 /* Only scheduling preflight: all acceptance still comes from original calls. */
 if(memcmp(bytes.data,"CrypticS",8)||!cstring_matches(bytes.data+14,len,PARSE_SIG)||(!ignore_crc&&read32(bytes.data+8)!=build_crc))return COH_OK;
 r->stage=FILELIST_STAGE_DEPENDENCY_HEADER;
 if(bytes.size-at<2){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 uint32_t siglen=read16(bytes.data+at);size_t sigat=at+2;
 size_t nameend=sigat+siglen+(4u-(siglen+2u)%4u)%4u;
 if(nameend>bytes.size||bytes.size-nameend<4){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 int32_t declared=signed32(read32(bytes.data+nameend));at=nameend+4;
 if(mode==FILELIST_MODE_NULL_SKIP){
  r->stage=FILELIST_STAGE_DEPENDENCY_SIZE;
  if(declared<0){r->failure_byte=(uint32_t)nameend;return COH_UNSUPPORTED;}
  if((uint32_t)declared>bytes.size-at){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
  return COH_OK;
 }
 if(siglen>=20||!cstring_matches(bytes.data+sigat,siglen,FILELIST_SIG)||declared<=0)return COH_OK;
 r->stage=FILELIST_STAGE_COUNT;
 if(bytes.size-at<4){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 int32_t count=signed32(read32(bytes.data+at));
 if(count>(int32_t)FILELIST_ENTRY_MAX){r->failure_byte=(uint32_t)at;return COH_LIMIT;}
 at+=4;int64_t remaining=(int64_t)declared-4;
 for(int32_t i=0;i<count;i++){
  r->stage=FILELIST_STAGE_ROW;
  if(bytes.size-at<2){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
  uint32_t pathlen=read16(bytes.data+at);size_t amount=2u+pathlen+(4u-(pathlen+2u)%4u)%4u;
  if(amount>bytes.size-at||bytes.size-at-amount<4){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
  at+=amount+4;remaining-=(int64_t)amount+4;
  if(remaining<0)break; /* Original does not enter remaining rows after this. */
 }
 return COH_OK;
}
CohStatus filelist_apply(CohBytes bytes,const FileListIdentity*observed,const FileListIdentity*expected,
 const CohCostumeImportDigest*digest,uint32_t build_crc,uint32_t ignore_crc,uint32_t mode,
 FileListResult*out,FileListReceipt*receipt,size_t budget,size_t retained){
 if(!bytes.data||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 FileListSpan spans[7]={{bytes.data,bytes.size},{observed,sizeof(*observed)},{expected,sizeof(*expected)},
  {digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){
  if(!valid_span(spans[i]))return COH_INVALID;
  for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;
 }
 spans[6]=(FileListSpan){digest->context,digest->context_bytes};
 if(!valid_span(spans[6]))return COH_INVALID;
 for(unsigned j=0;j<6;j++)if(!apart(spans[6],spans[j]))return COH_INVALID;
 FileListReceipt result;memset(&result,0,sizeof(result));result.stage=FILELIST_STAGE_INPUT;
 result.cleanup_complete=(uint32_t)filelist_is_idle();CohStatus status=COH_OK;
 if(!result.cleanup_complete)status=COH_STATE;
 else if(bytes.size>FILELIST_INPUT_MAX||!budget||budget>FILELIST_BUDGET_MAX)status=COH_LIMIT;
 else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+FILELIST_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){
  if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;
 }
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.stage=FILELIST_STAGE_IDENTITY;const unsigned char*labels=(const unsigned char*)expected;
 for(unsigned i=0;i<5;i++)if(zeros(labels+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.fixture_identity_matched=1;result.stage=FILELIST_STAGE_PROFILE;uint16_t host_endian=1;
 if(ignore_crc>1||mode>FILELIST_MODE_COLLECT||*(const unsigned char*)&host_endian!=1){result.status=COH_UNSUPPORTED;*receipt=result;return COH_UNSUPPORTED;}
 status=framing(bytes,build_crc,ignore_crc,mode,&result);
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.stage=FILELIST_STAGE_DIGEST;uint8_t hash[32];memset(hash,0,sizeof(hash));
 status=digest->sha256(digest->context,bytes,hash);
 if(status==COH_OK&&memcmp(hash,expected->input_sha256,32))status=COH_STATE;
 filelist_wipe(hash,sizeof(hash));
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 owner.active=1;owner.input_size=bytes.size;owner.receipt=result;owner.receipt.stage=FILELIST_STAGE_OPEN;owner.receipt.cleanup_complete=0;
 memcpy(owner.data,bytes.data,bytes.size);int compare_build;memcpy(&compare_build,&build_crc,4);
 SimpleBufHandle handle=SerializeReadOpen("bin/BodyParts.bin",PARSE_SIG,compare_build,(int)ignore_crc);
 FileListResult candidate;memset(&candidate,0,sizeof(candidate));FileList list=NULL;
 if(!handle){owner.receipt.stage=FILELIST_STAGE_HEADER_REJECT;status=COH_UNSUPPORTED;}
 else{
  owner.receipt.header_accepted=1;owner.receipt.header_end=(uint32_t)SimpleBufTell(handle);
  candidate.header_end=owner.receipt.header_end;owner.receipt.filelist_calls++;
  int accepted;
  if(mode==FILELIST_MODE_NULL_SKIP){owner.receipt.null_skip_calls++;accepted=FileListRead(NULL,handle);}
  else{owner.receipt.collect_calls++;accepted=FileListRead(&list,handle);}
  owner.receipt.source_result=(uint32_t)accepted;owner.receipt.dependency_end=(uint32_t)SimpleBufTell(handle);
  owner.receipt.source_node_count=owner.pushed;
  if(accepted){
   candidate.dependency_end=owner.receipt.dependency_end;
   if(mode==FILELIST_MODE_COLLECT){
    candidate.count_observed=1;candidate.count=owner.pushed;
    assert(owner.pushed==owner.node_count&&owner.pushed<=FILELIST_ENTRY_MAX);
    if(list)assert(list==owner.pointers);
    for(uint32_t i=0;i<owner.pushed;i++){
     assert(list[i]==&owner.nodes[i]);memcpy(candidate.entries[i].path,list[i]->path,MAX_PATH);
     memcpy(&candidate.entries[i].date_bits,&list[i]->date,4);memcpy(&candidate.entries[i].seen,&list[i]->seen,4);
    }
   }
   owner.receipt.stage=FILELIST_STAGE_COMPLETE;status=COH_OK;
  }else{owner.receipt.stage=FILELIST_STAGE_SOURCE_REJECT;status=COH_UNSUPPORTED;}
  owner.wrapper_closing=1;SimpleBufClose(handle);owner.wrapper_closing=0;
 }
 owner.receipt.status=(uint32_t)status;result=owner.receipt;list=NULL;
 assert(!owner.opened);filelist_wipe(&owner,sizeof(owner));result.cleanup_complete=(uint32_t)filelist_is_idle();
 if(status==COH_OK)*out=candidate;
 *receipt=result;filelist_wipe(&candidate,sizeof(candidate));filelist_wipe(&result,sizeof(result));return status;
}
'''

def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 pin_path=HERE/'file-list-read-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('dependency-list source pin changed: '+name)
  frozen[name]=raw
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()}
 structure=re.search(r'typedef struct SimpleBuffer\s*\{.*?\}\s*SimpleBuffer\s*;',text[SERIAL_C],re.S)[0]
 handle=re.search(r'typedef struct _SimpleBufHandle \*SimpleBufHandle;',text[SERIAL_H])[0]
 entry=re.search(r'typedef struct FileEntry\s*\{.*?\}\s*FileEntry\s*;',text[INTERNAL_H],re.S)[0]
 list_type=re.search(r'^typedef FileEntry\*\* FileList;',text[INTERNAL_H],re.M)[0]
 constants={
  'MAX_FILETYPE_LEN':re.search(r'^#define\s+MAX_FILETYPE_LEN\s+([0-9]+)\s*$',text[SERIAL_H],re.M),
  'cryptic_sig':re.search(r'^static char cryptic_sig\[\]\s*=\s*"CrypticS";\s*$',text[SERIAL_C],re.M),
  'cryptic_sig_len':re.search(r'^#define\s+cryptic_sig_len\s+([0-9]+)\s*$',text[SERIAL_C],re.M),
  'PARSE_SIG':re.search(r'^#define\s+PARSE_SIG\s+"Parse6"[^\n]*$',text[PARSER_H],re.M),
  'FILELIST_SIG':re.search(r'^#define\s+FILELIST_SIG\s+"Files1"[^\n]*$',text[INTERNAL_H],re.M)}
 if not all(constants.values())or int(constants['MAX_FILETYPE_LEN'][1])!=4096 or int(constants['cryptic_sig_len'][1])!=8:raise ValueError('original dependency-list constants changed')
 functions={name:extract(text[path],name)for path,names in((SERIAL_C,('SimpleBufRead','SimpleBufSeek','SimpleBufTell','ReadPascalString','SkipPascalString','SerializeSkipStruct','SerializeReadOpen','SerializeReadHeader','SerializeReadData')),(SERIAL_H,('SimpleBufReadU16','SimpleBufReadU32')),(INTERNAL_C,('FileListCreate','FileListRead')))for name in names}
 callers={name:extract(text[PARSER_C],name)for name in('ParserReadBinaryFile','ParserLoadFiles')}
 binary_call=re.search(r'if\s*\(!FileListRead\(filelist,\s*file\)\)',callers['ParserReadBinaryFile'])
 null_call=re.search(r'ParserReadBinaryFile\(binfile,\s*persistfilepath,\s*pti,\s*structptr,\s*NULL,\s*globaldefines\)',callers['ParserLoadFiles'])
 if not binary_call or not null_call:raise ValueError('original dependency-list caller association changed')
 header=work/'file-list-read-provider.h';header.write_text(HEADER)
 code=PREAMBLE+handle+'\n'+structure+'\n'+entry+'\n'+list_type+'\n'+'\n'.join(value[0]for value in constants.values())+'\n'+ADAPTERS
 code+=functions['SimpleBufRead']+functions['SimpleBufSeek']+functions['SimpleBufTell']+OBSERVERS
 code+=''.join(functions[name]for name in('SimpleBufReadU16','SimpleBufReadU32','ReadPascalString','SkipPascalString','SerializeSkipStruct','SerializeReadOpen','SerializeReadHeader','SerializeReadData','FileListCreate','FileListRead'))+WRAPPER
 provider=work/'file-list-read-provider.c';provider.write_text(code)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('dependency-list source changed during emission')
 proof={'schema':'coh-original-file-list-read-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'source_stable_before_after':True,'whole_function_sha256_lf':{name:sha(value.encode())for name,value in functions.items()},'original_declaration_sha256_lf':{'SimpleBuffer':sha(structure.encode()),'SimpleBufHandle':sha(handle.encode()),'FileEntry':sha(entry.encode()),'FileList':sha(list_type.encode())}|{name:sha(value[0].encode())for name,value in constants.items()},'original_caller_source_audit':{'source_path':PARSER_C,'whole_function_sha256_lf':{name:sha(value.encode())for name,value in callers.items()},'FileListRead_call':binary_call[0],'loader_NULL_call':null_call[0],'compiled':False,'executed':False},'profile':'<=64KiB input, fresh collect list, native positive-count cap16, full entered scalar/name/padding/date preflight; NULL skip requires complete nonnegative extent; no body parsed','NULL_skip_semantics':'Unchanged FileListRead(NULL) calls SerializeSkipStruct and returns1 unconditionally. No Files1/count/path validation or count observation; not equivalent to an empty collected list.','collect_semantics':'Source C-string paths, order, duplicates, separators and raw32 date preserved; seen0 from fixed zeroed nodes. Oversized path>=260 becomes source empty path after safe skip; oversized signature>=20 becomes source empty signature/rejection. No FileListInsert/normalization/filesystem/date freshness.','header_prefix':'Unchanged SerializeReadOpen and dependencies, expected Parse6 from PARSE_SIG. Raw comparison CRC fixture argument, not actual ParseTableCRC or ELF/build_id. Authentic header end20 and dependency end64, before body.','host_adapters':['Exact full SimpleBuffer/handle/FileEntry/FileList declarations with explicit MAX_PATH260 and signed32 time/int little-endian host shell; no Win32/Android ABI claim','Fixed owned64KiB open/close/no-growth adapters; source-header versus wrapper close counters distinct','Fixed owned calloc/FileEntry and eaCreate/eaPush adapters limited16; not original memory allocator/earray implementation','Original fixed oversized-Pascal warning observed as bounded numeric warning_calls; raw printf output suppressed by explicit adapter, all other warning branches excluded by complete preflight','Original Read/Seek/Tell scalar/Pascal/header/data/skip functions unchanged with counting wrappers'],'cleanup':'Every opened accepted-header handle closes through wrapper, original header reject closes through source adapter. Partial original collected nodes remain owned and are wiped on rejection. Volatile arena/nodes/pointers/staging cleanup; safe numeric receipt and atomic output.','original_caller_executed':False,'original_FileListInsert_executed':False,'original_ParserReadBinaryTable_executed':False,'actual_ParseTableCRC_computed':False,'current_Map_runtime_observed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{'file_list_header':str(header),'file_list_provider':str(provider)}}
 return provider,proof
