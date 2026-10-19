"""Bounded unchanged ParserIsPersistNewer production call, exact source dependencies."""
from pathlib import Path
import hashlib,importlib.util,json,re
HERE=Path(__file__).resolve().parent
PARSER_C='upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c'
INTERNAL_H='upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/structInternals.h'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def module(name):
 spec=importlib.util.spec_from_file_location('coh_persist_'+name,HERE/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
HEADER=r'''/* Production cache-header fixture only; no freshness/Map/catalog authority. */
#ifndef COH_PERSIST_NEWER_PROVIDER_H
#define COH_PERSIST_NEWER_PROVIDER_H
#include "coh_costume_import.h"
#define PERSIST_NEWER_STAGE_INPUT 1u
#define PERSIST_NEWER_STAGE_IDENTITY 2u
#define PERSIST_NEWER_STAGE_PROFILE 3u
#define PERSIST_NEWER_STAGE_FRAMING 4u
#define PERSIST_NEWER_STAGE_TYPE_LENGTH 5u
#define PERSIST_NEWER_STAGE_OPEN 6u
#define PERSIST_NEWER_STAGE_SOURCE_REJECT 7u
#define PERSIST_NEWER_STAGE_COMPLETE 8u
#define PERSIST_NEWER_STAGE_DIGEST 9u
#define PERSIST_NEWER_ROUTE_CALLER 0u
#define PERSIST_NEWER_ROUTE_STRICT_HEADER 1u
#define PERSIST_NEWER_INPUT_MAX 65536u
#define PERSIST_NEWER_BUDGET_MAX (1024u*1024u)
#define PERSIST_NEWER_STACK_RESERVE 16384u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}PersistNewerIdentity;
typedef struct{uint32_t source_crc,header_end;}PersistNewerResult;
typedef struct{
 uint32_t status,stage,failure_byte,source_calls,crc_calls,mode_calls;
 uint32_t open_calls,read_calls,seek_calls,source_close_calls,wrapper_close_calls;
 uint32_t source_accepted,header_end,update_calls,stream_bytes,visited_fields,interpret_calls;
 uint32_t failure_diagnostics,fixture_identity_matched,crypto_cleanup_complete,cleanup_complete;
}PersistNewerReceipt;
/* route0 requires production1 and executes whole original caller. route1 requires
 * mode0: dependency-only strictCRC0 negative control, never caller/development.
 * fault0 normal,1 owned open refusal. Input is complete CrypticS/Parse6 framing;
 * no grammar is invented for C-string suffix, skipped padding, or body suffix.
 * All spans/context disjoint. Atomic output after close+volatile owned cleanup.
 */
CohStatus persist_newer_apply(CohBytes,const PersistNewerIdentity*,const PersistNewerIdentity*,
 const CohCostumeImportDigest*,uint32_t,uint32_t,uint32_t,
 PersistNewerResult*,PersistNewerReceipt*,size_t,size_t);
int persist_newer_is_idle(void);
size_t persist_newer_owner_bytes(void);
size_t persist_newer_crypto_object_bytes(void);
#endif
'''
CALLER_ADAPTERS=r'''
#include "persist-newer-provider.h"
#include <stdarg.h>
typedef int32_t __time32_t;
'''
CALLER_BRIDGES=r'''
static PersistNewerReceipt persist_receipt;
static FileList lf_filedates;
static const char *g_StdAdditionalFilePrefixes[]={""};
static int persist_production_mode(void){assert(owner.active);persist_receipt.mode_calls++;return 1;}
/* Explicit immutable fixture mode. Original production helper is not qualified. */
#define isProductionMode persist_production_mode
static void verbose_printf(const char*format,...){
 assert(owner.active&&!strcmp(format,"bin file %s is incorrect version\n"));
 va_list arguments;va_start(arguments,format);const char*name=va_arg(arguments,const char*);
 assert(name&&!strcmp(name,"bin/BodyParts.bin"));va_end(arguments);persist_receipt.failure_diagnostics++;
}
/* Development/date/filesystem helpers remain unqualified, and cannot execute. */
static void forbidden_development(void){assert(!"unqualified development/date/filesystem branch");}
static int FileListRead(FileList*list,SimpleBufHandle file){(void)list;(void)file;forbidden_development();return 0;}
static void FileListCreate(FileList*list){(void)list;forbidden_development();}
static void FileListDestroy(FileList*list){(void)list;forbidden_development();}
static void FileListInsert(FileList*list,const char*name,__time32_t date){(void)list;(void)name;(void)date;forbidden_development();}
static FileEntry*FileListFind(FileList*list,const char*name){(void)list;(void)name;forbidden_development();return NULL;}
static void DateCheckCallback(void){forbidden_development();}
static void fileScanAllDataDirs(const char*dir,void(*callback)(void)){(void)dir;(void)callback;forbidden_development();}
static char*addFilePrefix(const char*name,const char*prefix){(void)name;(void)prefix;forbidden_development();return NULL;}
static int eaSize(FileList*list){(void)list;forbidden_development();return 0;}
static int fileDatesEqual(__time32_t a,__time32_t b,int normalize){(void)a;(void)b;(void)normalize;forbidden_development();return 0;}
static __time32_t fileLastChanged(const char*name){(void)name;forbidden_development();return 0;}
static int fileExists(const char*name){(void)name;forbidden_development();return 0;}
static void SerializeClose(SimpleBufHandle file){(void)file;forbidden_development();}
#define true 1
static int persist_original_crc(ParseTable*table,DefineContext*defines){
 assert(owner.active&&table==owner.root&&!defines);persist_receipt.crc_calls++;
 int crc=ParseTableCRC(table,defines);memcpy(&owner.candidate.crc,&crc,4);return crc;
}
#define ParseTableCRC persist_original_crc
'''
WRAPPER=r'''
#undef ParseTableCRC
#undef isProductionMode
#undef true
#undef SimpleBufRead
#undef SimpleBufSeek
typedef struct{const void*p;size_t n;}PersistSpan;
static int valid_span(PersistSpan s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(PersistSpan a,PersistSpan b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
int persist_newer_is_idle(void){return schema_crc_is_idle()&&binaryopen_is_idle()&&zeros(&persist_receipt,sizeof(persist_receipt))&&lf_filedates==NULL;}
size_t persist_newer_owner_bytes(void){return sizeof(owner)+sizeof(binary_owner)+sizeof(persist_receipt)+sizeof(lf_filedates)+sizeof(g_StdAdditionalFilePrefixes);}
size_t persist_newer_crypto_object_bytes(void){return schema_adler_object_bytes();}
CohStatus persist_newer_apply(CohBytes bytes,const PersistNewerIdentity*observed,const PersistNewerIdentity*expected,
 const CohCostumeImportDigest*digest,uint32_t route,uint32_t production_mode,uint32_t fault,
 PersistNewerResult*out,PersistNewerReceipt*receipt,size_t budget,size_t retained){
 if(!bytes.data||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 PersistSpan spans[7]={{bytes.data,bytes.size},{observed,sizeof(*observed)},{expected,sizeof(*expected)},
  {digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid_span(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(PersistSpan){digest->context,digest->context_bytes};if(!valid_span(spans[6]))return COH_INVALID;
 for(unsigned j=0;j<6;j++)if(!apart(spans[6],spans[j]))return COH_INVALID;
 PersistNewerReceipt result;memset(&result,0,sizeof(result));result.stage=PERSIST_NEWER_STAGE_INPUT;
 result.cleanup_complete=(uint32_t)persist_newer_is_idle();result.crypto_cleanup_complete=(uint32_t)schema_adler_is_idle();CohStatus status=COH_OK;
 if(!result.cleanup_complete)status=COH_STATE;
 else if(bytes.size>PERSIST_NEWER_INPUT_MAX||!budget||budget>PERSIST_NEWER_BUDGET_MAX)status=COH_LIMIT;
 else if(!digest->sha256)status=COH_STATE;
 size_t charge=persist_newer_owner_bytes()+PERSIST_NEWER_STACK_RESERVE+schema_adler_object_bytes();
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.stage=PERSIST_NEWER_STAGE_IDENTITY;const unsigned char*labels=(const unsigned char*)expected;
 for(unsigned i=0;i<5;i++)if(zeros(labels+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.fixture_identity_matched=1;result.stage=PERSIST_NEWER_STAGE_PROFILE;uint16_t endian=1;
 if(route>PERSIST_NEWER_ROUTE_STRICT_HEADER||production_mode!=(route==PERSIST_NEWER_ROUTE_CALLER?1u:0u)||fault>1||*(const uint8_t*)&endian!=1){result.status=COH_UNSUPPORTED;*receipt=result;return COH_UNSUPPORTED;}
 result.stage=PERSIST_NEWER_STAGE_FRAMING;
 if(bytes.size<14){result.status=COH_INVALID;result.failure_byte=(uint32_t)bytes.size;*receipt=result;return COH_INVALID;}
 uint32_t type_bytes=(uint32_t)bytes.data[12]|(uint32_t)bytes.data[13]<<8;result.stage=PERSIST_NEWER_STAGE_TYPE_LENGTH;
 if(type_bytes>=MAX_FILETYPE_LEN){result.status=COH_LIMIT;result.failure_byte=12;*receipt=result;return COH_LIMIT;}
 size_t padding=(4u-(type_bytes+2u)%4u)%4u,header_end=14u+type_bytes+padding;result.stage=PERSIST_NEWER_STAGE_FRAMING;
 if(header_end>bytes.size){result.status=COH_INVALID;result.failure_byte=(uint32_t)bytes.size;*receipt=result;return COH_INVALID;}
 result.stage=PERSIST_NEWER_STAGE_DIGEST;uint8_t hash[32];memset(hash,0,sizeof(hash));status=digest->sha256(digest->context,bytes,hash);
 if(status==COH_OK&&memcmp(hash,expected->input_sha256,32))status=COH_STATE;
 schema_wipe(hash,sizeof(hash));
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 owner.active=1;memcpy(owner.root,ParseBodyPartBegin,sizeof(owner.root));memcpy(owner.parts,ParseBodyPart,sizeof(owner.parts));owner.root[0].subtable=owner.parts;
 binary_owner.active=1;binary_owner.fault=fault;binary_owner.input_size=bytes.size;memcpy(binary_owner.data,bytes.data,bytes.size);
 persist_receipt=result;persist_receipt.cleanup_complete=0;persist_receipt.crypto_cleanup_complete=0;persist_receipt.stage=PERSIST_NEWER_STAGE_OPEN;
 SimpleBufHandle handle;
 if(route==PERSIST_NEWER_ROUTE_CALLER){persist_receipt.source_calls++;handle=ParserIsPersistNewer(NULL,NULL,"bin/BodyParts.bin",owner.root,NULL);}
 else{int crc=persist_original_crc(owner.root,NULL);handle=SerializeReadOpen("bin/BodyParts.bin",PARSE_SIG,crc,0);}
 PersistNewerResult candidate;memset(&candidate,0,sizeof(candidate));candidate.source_crc=owner.candidate.crc;
 if(handle){persist_receipt.source_accepted=1;candidate.header_end=(uint32_t)SimpleBufTell(handle);assert(candidate.header_end==header_end);binary_owner.wrapper_closing=1;SimpleBufClose(handle);binary_owner.wrapper_closing=0;persist_receipt.stage=PERSIST_NEWER_STAGE_COMPLETE;status=COH_OK;}
 else{persist_receipt.stage=binary_owner.receipt.source_close_calls?PERSIST_NEWER_STAGE_SOURCE_REJECT:PERSIST_NEWER_STAGE_OPEN;status=COH_UNSUPPORTED;}
 persist_receipt.open_calls=binary_owner.receipt.open_calls;persist_receipt.read_calls=binary_owner.receipt.read_calls;persist_receipt.seek_calls=binary_owner.receipt.seek_calls;
 persist_receipt.source_close_calls=binary_owner.receipt.source_close_calls;persist_receipt.wrapper_close_calls=binary_owner.receipt.wrapper_close_calls;persist_receipt.header_end=binary_owner.receipt.header_end;
 persist_receipt.update_calls=owner.candidate.update_calls;persist_receipt.stream_bytes=owner.candidate.stream_bytes;persist_receipt.visited_fields=owner.candidate.visited_fields;persist_receipt.interpret_calls=owner.candidate.interpret_calls;
 schema_adler_cleanup();persist_receipt.crypto_cleanup_complete=(uint32_t)schema_adler_is_idle();persist_receipt.status=(uint32_t)status;result=persist_receipt;
 assert(!binary_owner.opened&&!lf_filedates);schema_wipe(&owner,sizeof(owner));binary_wipe(&binary_owner,sizeof(binary_owner));schema_wipe(&persist_receipt,sizeof(persist_receipt));
 result.cleanup_complete=(uint32_t)persist_newer_is_idle();assert(result.cleanup_complete);if(status==COH_OK)*out=candidate;*receipt=result;
 schema_wipe(&candidate,sizeof(candidate));schema_wipe(&result,sizeof(result));return status;
}
'''
def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 pin_path=HERE/'persist-newer-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('persist-newer source pin changed: '+name)
  frozen[name]=raw
 schema=module('schema_crc_provider');binary=module('binary_read_open_provider')
 schema_path,schema_proof=schema.build(root,work);binary_path,binary_proof=binary.build(root,work)
 schema_code=Path(schema_path).read_text()
 if not schema_code.endswith(schema.WRAPPER):raise ValueError('schema composition boundary changed')
 schema_code=schema_code[:-len(schema.WRAPPER)]
 binary_code=Path(binary_path).read_text()
 if not binary_code.startswith(binary.PREAMBLE)or not binary_code.endswith(binary.WRAPPER):raise ValueError('binary composition boundary changed')
 binary_code=binary_code[len(binary.PREAMBLE):-len(binary.WRAPPER)]
 # Only explicit adapter variables are renamed. All original function text remains exact.
 original_functions={name:binary.extract(frozen[path].decode().replace('\r\n','\n'),name)for path,names in((binary.SERIAL_C,('SimpleBufRead','SimpleBufSeek','SimpleBufTell','ReadPascalString','SerializeReadOpen')),(binary.SERIAL_H,('SimpleBufReadU16','SimpleBufReadU32')))for name in names}
 for block in(binary.ADAPTERS,binary.OBSERVERS):
  if binary_code.count(block)!=1:raise ValueError('binary adapter boundary changed')
  binary_code=binary_code.replace(block,re.sub(r'\bowner\b','binary_owner',block).replace('static int zeros(', 'static int binary_zeros(').replace('return zeros(&binary_owner', 'return binary_zeros(&binary_owner'),1)
 text=frozen[PARSER_C].decode().replace('\r\n','\n');caller=schema.extract(text,'ParserIsPersistNewer')
 internal=frozen[INTERNAL_H].decode().replace('\r\n','\n');entry=re.search(r'typedef struct FileEntry\s*\{.*?\}\s*FileEntry;',internal,re.S)
 if not entry:raise ValueError('original FileEntry declaration missing')
 (work/'persist-newer-provider.h').write_text(HEADER)
 code=schema_code+'\n#include <stdio.h>\n#include \"binary-read-open-provider.h\"\ntypedef uint16_t U16;\n#define INLINEDBG inline\n#define endianSwapIfBig(type,value) (value)\n#define MAX_PATH 260\n'+binary_code+CALLER_ADAPTERS+entry[0]+'\ntypedef FileEntry** FileList;\n'+CALLER_BRIDGES+caller+WRAPPER
 for name,body in original_functions.items():
  if code.count(body)!=1:raise ValueError('emitted original binary function changed '+name)
 if code.count(caller)!=1:raise ValueError('emitted original caller changed')
 for name in('ignore_interpretfield','number_interpretfield','string_interpretfield','struct_interpretfield','UpdateCRCFromParseInfo','ParseTableCRC'):
  body=schema.extract(text,name)
  if code.count(body)!=1:raise ValueError('emitted original schema function changed '+name)
 provider=work/'persist-newer-provider.c';provider.write_text(code)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('persist-newer inputs changed during emission')
 proof={'schema':'coh-original-persist-newer-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'source_stable_before_after':True,'whole_function_sha256_lf':schema_proof['whole_function_sha256_lf']|binary_proof['whole_function_sha256_lf']|{'ParserIsPersistNewer':sha(caller.encode())},'original_declaration_sha256_lf':{'FileEntry':sha(entry[0].encode())},'schema_crc_composition':schema_proof,'binary_open_composition':binary_proof,'profile':'Exact owned BodyPart schemas, definesNULL; unchanged whole original ParserIsPersistNewer in immutable production1 fixture; actual source CRC; original SerializeReadOpen ignoreCRC1. StrictCRC0 dependency-only route explicitly separate. <=64KiB complete header input, native little-endian int32/intptr64/size64. No shared-memory loader executes.','mode_shell':'Immutable isProductionMode adapter1 counts calls. Production helper itself, development/date/filesystem helpers not qualified. All unexecuted development helpers trap.','semantics':'CRC computed before open on every source-entered route, including open refusal. Production accepts CRC mismatch due original ignoreCRC1. Exact C-string/padding/body-suffix behavior of original header source retained.','cleanup':'Owned schema/trace/header buffer/receipt staging volatile-wiped; actual CryptoPP delete and TLS reset; caller spans/context disjoint; budget charges owner+16KiB stack+actual Adler32 object+caller/digest reserves; result atomic after cleanup. External allocator/RSS/stack closure unqualified.','original_ParserIsPersistNewer_executed_by_build':False,'development_or_filesystem_freshness_qualified':False,'current_Map_runtime_observed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'adler_cpp_path':schema_proof['adler_cpp_path'],'crypto_dependency':schema_proof['crypto_dependency'],'evidence_paths':{'persist_header':str(work/'persist-newer-provider.h'),'persist_provider':str(provider)}}
 proof['source_sha256'].update(schema_proof['source_sha256']);return provider,proof
