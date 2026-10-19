"""Original SerializeReadOpen header leaf, bounded source-fixture profile only."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
SERIAL_C='upstream/ouroboros/libs/UtilitiesLib/src/utils/serialize.c'
SERIAL_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/serialize.h'
PARSER_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h'
PARSER_C='upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def extract(text,name):
 match=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*)?\s*\{',text,re.M)
 if not match:raise ValueError('missing original binary-open function '+name)
 at=text.index('{',match.start())+1;depth=1
 while depth:
  if at>=len(text):raise ValueError('unterminated original binary-open function '+name)
  depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[match.start():at]+'\n'
HEADER=r'''/* Source header-leaf fixture only; no runtime/schema/catalog authority. */
#ifndef COH_BINARY_READ_OPEN_PROVIDER_H
#define COH_BINARY_READ_OPEN_PROVIDER_H
#include "coh_costume_import.h"
#define BINARYOPEN_STAGE_INPUT 1u
#define BINARYOPEN_STAGE_IDENTITY 2u
#define BINARYOPEN_STAGE_PROFILE 3u
#define BINARYOPEN_STAGE_FRAMING 4u
#define BINARYOPEN_STAGE_TYPE_LENGTH 5u
#define BINARYOPEN_STAGE_PAYLOAD 6u
#define BINARYOPEN_STAGE_DIGEST 7u
#define BINARYOPEN_STAGE_OPEN 8u
#define BINARYOPEN_STAGE_SOURCE_REJECT 9u
#define BINARYOPEN_STAGE_COMPLETE 10u
#define BINARYOPEN_FAULT_NONE 0u
#define BINARYOPEN_FAULT_OPEN_REFUSE 1u
#define BINARYOPEN_INPUT_MAX 65536u
#define BINARYOPEN_BUDGET_MAX (1024u*1024u)
#define BINARYOPEN_STACK_RESERVE 16384u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}BinaryOpenIdentity;
typedef struct{uint32_t header_end;}BinaryOpenResult;
typedef struct{
 uint32_t status,stage,failure_byte,open_calls,read_calls,seek_calls;
 uint32_t source_close_calls,wrapper_close_calls,source_accepted,header_end;
 uint32_t fixture_identity_matched,cleanup_complete;
}BinaryOpenReceipt;
/* All spans are disjoint/immutable through digest. Valid numeric diagnostics
 * may change on refusal; aliased/invalid sinks remain unchanged. Result commits
 * only after original acceptance and owned-buffer close/cleanup. build_crc is
 * only the original comparison argument, never actual ParseTableCRC/build_id.
 * ignore_crc0/1 preserves actual source behavior. No NUL/padding strictness is
 * invented: source C string and seek semantics apply after complete framing.
 */
CohStatus binaryopen_apply(CohBytes,const BinaryOpenIdentity*,const BinaryOpenIdentity*,
 const CohCostumeImportDigest*,uint32_t,uint32_t,uint32_t,
 BinaryOpenResult*,BinaryOpenReceipt*,size_t,size_t);
int binaryopen_is_idle(void);
#endif
'''
PREAMBLE=r'''
#include "binary-read-open-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint16_t U16;typedef uint32_t U32;
#define INLINEDBG inline
/* Qualified little-endian host profile; the wrapper checks it before reads. */
#define endianSwapIfBig(type,value) (value)
#define MAX_PATH 260
typedef char host_int32[(sizeof(int)==4&&sizeof(U32)==4)?1:-1];
'''
ADAPTERS=r'''
typedef struct{
 int active,opened,wrapper_closing;uint32_t fault;size_t input_size;
 unsigned char data[BINARYOPEN_INPUT_MAX];SimpleBuffer buffer;
 BinaryOpenReceipt receipt;
}BinaryOwner;
static BinaryOwner owner;
static void binary_wipe(void*p,size_t n){volatile unsigned char*c=p;while(n--)*c++=0;}
static int zeros(const void*p,size_t n){const unsigned char*c=p;for(size_t i=0;i<n;i++)if(c[i])return 0;return 1;}
int binaryopen_is_idle(void){return zeros(&owner,sizeof(owner));}
int SimpleBufTell(SimpleBufHandle);
/* Fixed owned open/close adapters; filesystem/allocation/writing are excluded. */
static SimpleBufHandle SimpleBufOpenRead(const char*name){
 assert(owner.active&&!owner.opened&&!strcmp(name,"bin/BodyParts.bin"));owner.receipt.open_calls++;
 if(owner.fault==BINARYOPEN_FAULT_OPEN_REFUSE)return NULL;
 owner.buffer.data=(char*)owner.data;owner.buffer.filesize=(int)owner.input_size;
 owner.buffer.memsize=(int)sizeof(owner.data);owner.buffer.curposition=0;
 memcpy(owner.buffer.filename,name,sizeof("bin/BodyParts.bin"));owner.opened=1;
 return (SimpleBufHandle)&owner.buffer;
}
static void SimpleBufClose(SimpleBufHandle file){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer&&!owner.buffer.writing);
 owner.receipt.header_end=(uint32_t)SimpleBufTell(file);
 if(owner.wrapper_closing)owner.receipt.wrapper_close_calls++;else owner.receipt.source_close_calls++;
 owner.opened=0;binary_wipe(&owner.buffer,sizeof(owner.buffer));binary_wipe(owner.data,sizeof(owner.data));
}
static void SimpleBufResizeEx(SimpleBufHandle file,int bytes){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer);
 assert(bytes>=0&&bytes<=owner.buffer.filesize&&owner.buffer.memsize==(int)sizeof(owner.data));
 /* Complete framing ensures original read-only seeks need no growth. */
}
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
#define SimpleBufRead observed_read
#define SimpleBufSeek observed_seek
'''
WRAPPER=r'''
#undef SimpleBufRead
#undef SimpleBufSeek
typedef struct{const void*p;size_t n;}BinarySpan;
static int valid_span(BinarySpan s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(BinarySpan a,BinarySpan b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
CohStatus binaryopen_apply(CohBytes bytes,const BinaryOpenIdentity*observed,const BinaryOpenIdentity*expected,
 const CohCostumeImportDigest*digest,uint32_t build_crc,uint32_t ignore_crc,uint32_t fault,
 BinaryOpenResult*out,BinaryOpenReceipt*receipt,size_t budget,size_t retained){
 if(!bytes.data||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 BinarySpan spans[7]={{bytes.data,bytes.size},{observed,sizeof(*observed)},{expected,sizeof(*expected)},
  {digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){
  if(!valid_span(spans[i]))return COH_INVALID;
  for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;
 }
 spans[6]=(BinarySpan){digest->context,digest->context_bytes};
 if(!valid_span(spans[6]))return COH_INVALID;
 for(unsigned j=0;j<6;j++)if(!apart(spans[6],spans[j]))return COH_INVALID;
 BinaryOpenReceipt result;memset(&result,0,sizeof(result));result.stage=BINARYOPEN_STAGE_INPUT;
 result.cleanup_complete=(uint32_t)binaryopen_is_idle();CohStatus status=COH_OK;
 if(!result.cleanup_complete)status=COH_STATE;
 else if(bytes.size>BINARYOPEN_INPUT_MAX||!budget||budget>BINARYOPEN_BUDGET_MAX)status=COH_LIMIT;
 else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+BINARYOPEN_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){
  if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;
 }
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.stage=BINARYOPEN_STAGE_IDENTITY;
 const unsigned char*labels=(const unsigned char*)expected;
 for(unsigned i=0;i<5;i++)if(zeros(labels+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.fixture_identity_matched=1;result.stage=BINARYOPEN_STAGE_PROFILE;
 uint16_t host_endian=1;
 if(ignore_crc>1||fault>BINARYOPEN_FAULT_OPEN_REFUSE||*(const unsigned char*)&host_endian!=1){result.status=COH_UNSUPPORTED;*receipt=result;return COH_UNSUPPORTED;}
 result.stage=BINARYOPEN_STAGE_FRAMING;
 if(bytes.size<14u){result.status=COH_INVALID;result.failure_byte=(uint32_t)bytes.size;*receipt=result;return COH_INVALID;}
 uint32_t type_bytes=(uint32_t)bytes.data[12]|(uint32_t)bytes.data[13]<<8;
 result.stage=BINARYOPEN_STAGE_TYPE_LENGTH;
 if(type_bytes>=MAX_FILETYPE_LEN){result.status=COH_LIMIT;result.failure_byte=12;*receipt=result;return COH_LIMIT;}
 size_t padding=(4u-(type_bytes+2u)%4u)%4u,header_end=14u+type_bytes+padding;
 result.stage=BINARYOPEN_STAGE_PAYLOAD;
 if(header_end>bytes.size){result.status=COH_INVALID;result.failure_byte=(uint32_t)bytes.size;*receipt=result;return COH_INVALID;}
 result.stage=BINARYOPEN_STAGE_DIGEST;uint8_t hash[32];memset(hash,0,sizeof(hash));
 status=digest->sha256(digest->context,bytes,hash);
 if(status==COH_OK&&memcmp(hash,expected->input_sha256,32))status=COH_STATE;
 binary_wipe(hash,sizeof(hash));
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 owner.active=1;owner.fault=fault;owner.input_size=bytes.size;owner.receipt=result;
 owner.receipt.stage=BINARYOPEN_STAGE_OPEN;owner.receipt.cleanup_complete=0;
 memcpy(owner.data,bytes.data,bytes.size);int compare_build;memcpy(&compare_build,&build_crc,4);
 SimpleBufHandle handle=SerializeReadOpen("bin/BodyParts.bin",PARSE_SIG,compare_build,(int)ignore_crc);
 BinaryOpenResult candidate;memset(&candidate,0,sizeof(candidate));
 if(handle){
  owner.receipt.source_accepted=1;candidate.header_end=(uint32_t)SimpleBufTell(handle);
  assert(candidate.header_end==header_end);owner.wrapper_closing=1;SimpleBufClose(handle);owner.wrapper_closing=0;
  owner.receipt.stage=BINARYOPEN_STAGE_COMPLETE;status=COH_OK;
 }else{
  owner.receipt.stage=owner.receipt.open_calls&&!owner.receipt.source_close_calls?BINARYOPEN_STAGE_OPEN:BINARYOPEN_STAGE_SOURCE_REJECT;
  status=COH_UNSUPPORTED;
 }
 owner.receipt.status=(uint32_t)status;result=owner.receipt;
 assert(!owner.opened);binary_wipe(&owner,sizeof(owner));result.cleanup_complete=(uint32_t)binaryopen_is_idle();
 if(status==COH_OK)*out=candidate;
 *receipt=result;binary_wipe(&candidate,sizeof(candidate));binary_wipe(&result,sizeof(result));return status;
}
'''

def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 pin_path=HERE/'binary-read-open-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('binary-open source pin changed: '+name)
  frozen[name]=raw
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()}
 structure=re.search(r'typedef struct SimpleBuffer\s*\{.*?\}\s*SimpleBuffer\s*;',text[SERIAL_C],re.S)[0]
 handle=re.search(r'typedef struct _SimpleBufHandle \*SimpleBufHandle;',text[SERIAL_H])[0]
 limit=re.search(r'^#define\s+MAX_FILETYPE_LEN\s+([0-9]+)\s*$',text[SERIAL_H],re.M)
 signature=re.search(r'^static char cryptic_sig\[\]\s*=\s*"CrypticS";\s*$',text[SERIAL_C],re.M)
 length=re.search(r'^#define\s+cryptic_sig_len\s+([0-9]+)\s*$',text[SERIAL_C],re.M)
 parse_sig=re.search(r'^#define\s+PARSE_SIG\s+"Parse6"[^\n]*$',text[PARSER_H],re.M)
 if not limit or int(limit[1])!=4096 or not signature or not length or int(length[1])!=8 or not parse_sig:raise ValueError('original binary header constants changed')
 functions={name:extract(text[path],name)for path,names in((SERIAL_C,('SimpleBufRead','SimpleBufSeek','SimpleBufTell','ReadPascalString','SerializeReadOpen')),(SERIAL_H,('SimpleBufReadU16','SimpleBufReadU32')))for name in names}
 # Audit the caller association from pinned source; never emit/compile its body.
 caller=extract(text[PARSER_C],'ParserIsPersistNewer')
 crc_call=re.search(r'^\s*crc\s*=\s*ParseTableCRC\(pti,\s*defines\);\s*$',caller,re.M)
 open_call=re.search(r'^\s*binfile\s*=\s*SerializeReadOpen\(persistfile,\s*PARSE_SIG,\s*crc,\s*isProductionMode\(\)\);\s*$',caller,re.M)
 if not crc_call or not open_call:raise ValueError('original binary-open caller association changed')
 caller_audit={'source_path':PARSER_C,'function':'ParserIsPersistNewer','whole_function_sha256_lf':sha(caller.encode()),'crc_assignment':crc_call[0].strip(),'header_open_call':open_call[0].strip(),'compiled':False,'executed':False,'actual_ParseTableCRC_computed':False}
 header=work/'binary-read-open-provider.h';header.write_text(HEADER)
 code=PREAMBLE+handle+'\n'+structure+'\n'+limit[0]+'\n'+signature[0]+'\n'+length[0]+'\n'+parse_sig[0]+'\n'+ADAPTERS
 code+=functions['SimpleBufRead']+functions['SimpleBufSeek']+functions['SimpleBufTell']+OBSERVERS+functions['SimpleBufReadU16']+functions['SimpleBufReadU32']+functions['ReadPascalString']+functions['SerializeReadOpen']+WRAPPER
 provider=work/'binary-read-open-provider.c';provider.write_text(code)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('binary-open source changed during emission')
 proof={'schema':'coh-original-binary-read-open-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'source_stable_before_after':True,'whole_function_sha256_lf':{name:sha(value.encode())for name,value in functions.items()},'original_declaration_sha256_lf':{'SimpleBuffer':sha(structure.encode()),'SimpleBufHandle':sha(handle.encode()),'MAX_FILETYPE_LEN':sha(limit[0].encode()),'cryptic_sig':sha(signature[0].encode()),'cryptic_sig_len':sha(length[0].encode()),'PARSE_SIG':sha(parse_sig[0].encode())},'actual_expected_filetype':'PARSE_SIG from original textparser.h; Parse6','comparison_build_argument_scope':'Caller fixture raw32 comparison argument only; distinct from ELF/build_id and not actual ParseTableCRC or generation. Original production-mode caller supplies ignore_crc_difference1.','profile':'<=64KiB input, declared type length<4096 and complete8+4+2+payload+padding before original read; no ASCII/NUL/padding-content grammar added','header_semantics':'Unchanged source strcmp accepts embedded-NUL Parse6 prefix, ignores skipped padding, ignores CRC differences only when flag1. Successful authentic end20 BEFORE Files1/FileListRead/body parsing.','host_adapters':['Exact full SimpleBuffer/opaque handle declarations; fixed owned64KiB data arena, constant bin/BodyParts.bin path, no filesystem/heap/writing','SimpleBufOpenRead/SimpleBufClose are owned adapters; source-close and wrapper-close classified separately','SimpleBufResizeEx asserts complete-profile read-only seeks need no growth; original resize allocator excluded','Original SimpleBufRead/Seek/Tell and ReadPascalString/U16/U32 run unchanged; explicit observer wrappers count calls','U16/U32/int32 and little-endian host profile checked; endianSwapIfBig identity bridge only for that host profile, no Win32/Android ABI claim'],'cleanup':'Source refusal closes through fixed adapter; accepted source handle is closed by wrapper before result commit. Volatile arena/buffer/owner/staging wipes and idle checks; caller input/identity/result unchanged on refusal except safe bounded numeric receipt.','original_SerializeReadOpen_executed_by_build':False,'original_ParserReadBinaryFile_executed':False,'original_FileListRead_executed':False,'original_full_Parse6_executed':False,'actual_ParseTableCRC_computed':False,'current_Map_runtime_observed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{'binary_header':str(header),'binary_provider':str(provider)}}
 proof['original_caller_source_audit']=caller_audit
 proof['original_ParserIsPersistNewer_executed']=False
 return provider,proof
