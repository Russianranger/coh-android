"""Original source-schema checksum with bounded owned fixture mutations."""
from pathlib import Path
import hashlib,importlib.util,json,re
HERE=Path(__file__).resolve().parent
BASE='upstream/ouroboros/'
PARSER_C=BASE+'libs/UtilitiesLib/src/utils/textparser.c'
PARSER_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/textparser.h'
INTERNAL_C=BASE+'libs/UtilitiesLib/src/utils/structInternals.c'
INTERNAL_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/structInternals.h'
BODY_C=BASE+'Common/gameData/BodyPart.c'
BODY_H=BASE+'Common/gameData/BodyPart.h'
TYPES_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/textparser_types.h'
STD_H=BASE+'libs/UtilitiesLib/include/utilitieslib/stdtypes.h'
OLD_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/structoldnames.h'
CRYPT_C=BASE+'libs/UtilitiesLib/src/network/crypt.cpp'
CRYPT_H=BASE+'libs/UtilitiesLib/include/utilitieslib/network/crypt.h'
CRYPTO_CMAKE=BASE+'cmake/dependencies/CryptoPP.cmake'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def extract(text,name):
 match=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*)?\s*\{',text,re.M)
 if not match:raise ValueError('missing original schema-crc function '+name)
 at=text.index('{',match.start())+1;depth=1
 while depth:
  if at>=len(text):raise ValueError('unterminated original schema-crc function '+name)
  depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[match.start():at]+'\n'
HEADER=r'''/* Controlled source-schema fixture only; never catalog/generation authority. */
#ifndef COH_SCHEMA_CRC_PROVIDER_H
#define COH_SCHEMA_CRC_PROVIDER_H
#include "coh_costume_import.h"
#define SCHEMA_CRC_STAGE_INPUT 1u
#define SCHEMA_CRC_STAGE_IDENTITY 2u
#define SCHEMA_CRC_STAGE_PROFILE 3u
#define SCHEMA_CRC_STAGE_WIRE 4u
#define SCHEMA_CRC_STAGE_MUTATION 5u
#define SCHEMA_CRC_STAGE_DIGEST 6u
#define SCHEMA_CRC_STAGE_SOURCE 7u
#define SCHEMA_CRC_STAGE_COMPLETE 8u
#define SCHEMA_CRC_FIELD_NAME 1u
#define SCHEMA_CRC_FIELD_TYPE_FLAGS 2u
#define SCHEMA_CRC_FIELD_PARAM 3u
#define SCHEMA_CRC_FIELD_OFFSET 4u
#define SCHEMA_CRC_FIELD_FORMAT 5u
#define SCHEMA_CRC_FIELD_DEFAULT_STRING 6u
#define SCHEMA_CRC_MUTATION_MAX 4u
#define SCHEMA_CRC_TEXT_MAX 63u
#define SCHEMA_CRC_WIRE_MAX 356u
#define SCHEMA_CRC_TRACE_MAX 512u
#define SCHEMA_CRC_UPDATE_MAX 64u
#define SCHEMA_CRC_BUDGET_MAX (1024u*1024u)
#define SCHEMA_CRC_STACK_RESERVE 16384u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}SchemaCrcIdentity;
typedef struct{
 uint32_t crc,stream_bytes,update_calls,visited_fields,interpret_calls;
 uint32_t update_lengths[SCHEMA_CRC_UPDATE_MAX];uint8_t stream[SCHEMA_CRC_TRACE_MAX];
}SchemaCrcResult;
typedef struct{
 uint32_t status,stage,failure_byte,mutation_count,source_calls,update_calls;
 uint32_t stream_bytes,visited_fields,interpret_calls,crypto_cleanup_complete;
 uint32_t fixture_identity_matched,cleanup_complete;
}SchemaCrcReceipt;
/* Canonical wire: 'SCR1',LE32 count<=4; each record LE32 table,row,field,
 * LE64 value,LE32 text length,then<=63 textbytes; no padding/trailing bytes.
 * Table0=root row0; table1=child rows0..12. Fixed acyclic links; defines=NULL.
 * NAME/DEFAULT_STRING require value0; other fields require text length0.
 * TYPE_FLAGS permits REDUNDANTNAME/STRUCTPARAM only, OR onto exact base type.
 * PARAM string/currentfile only0; DEFAULT_STRING supplies owned C-string.
 * Every caller span/context disjoint. Atomic result, safe numeric diagnostics.
 */
CohStatus schema_crc_apply(CohBytes,const SchemaCrcIdentity*,const SchemaCrcIdentity*,
 const CohCostumeImportDigest*,SchemaCrcResult*,SchemaCrcReceipt*,size_t,size_t);
int schema_crc_is_idle(void);
#endif
'''
PREAMBLE=r'''
#include "schema-crc-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint32_t U32;typedef uint8_t U8;typedef int BoneId;
#define devassert assert
typedef char schema_host[(sizeof(int)==4&&sizeof(intptr_t)==8&&sizeof(size_t)==8)?1:-1];
void cryptAdler32Init(void);void cryptAdler32Update(const U8*,int);U32 cryptAdler32Final(void);
int schema_adler_is_idle(void);void schema_adler_cleanup(void);size_t schema_adler_object_bytes(void);
'''
ADAPTERS=r'''
typedef ParseInfoFieldUsage(*interpretfield_f)(ParseTable*,int,ParseInfoField);
/* Explicit interpretfield-only holders; not complete original table ABI. */
typedef struct{interpretfield_f interpretfield;}SchemaHandler;
static const SchemaHandler g_tokentable[NUM_TOK_TYPE_TOKENS];
typedef void DefineContext;
static void UpdateCrcFromDefineList(DefineContext*p){(void)p;assert(!"unqualified dynamic defines");}
static void UpdateCrcFromStaticDefines(void*p){(void)p;assert(!"unqualified static defines");}
typedef struct{
 int active;ParseTable root[2],parts[14];char text[SCHEMA_CRC_MUTATION_MAX][SCHEMA_CRC_TEXT_MAX+1];
 SchemaCrcResult candidate;SchemaCrcReceipt receipt;
}SchemaOwner;
static SchemaOwner owner;
static void schema_wipe(void*p,size_t n){volatile unsigned char*c=p;while(n--)*c++=0;}
static int zeros(const void*p,size_t n){const unsigned char*c=p;for(size_t i=0;i<n;i++)if(c[i])return 0;return 1;}
int schema_crc_is_idle(void){return zeros(&owner,sizeof(owner))&&schema_adler_is_idle();}
static void observed_update(const U8*data,int len){
 assert(owner.active&&len>=0&&(data||!len));SchemaCrcResult*r=&owner.candidate;
 assert(r->update_calls<SCHEMA_CRC_UPDATE_MAX&&(uint32_t)len<=SCHEMA_CRC_TRACE_MAX-r->stream_bytes);
 r->update_lengths[r->update_calls++]=(uint32_t)len;
 if(len)memcpy(r->stream+r->stream_bytes,data,(size_t)len);
 r->stream_bytes+=(uint32_t)len;
 if(len==4){
  for(unsigned i=0;i<1;i++)if(data==(const U8*)&owner.root[i].type)r->visited_fields++;
  for(unsigned i=0;i<13;i++)if(data==(const U8*)&owner.parts[i].type)r->visited_fields++;
 }
 cryptAdler32Update(data,len);
}
#define cryptAdler32Update observed_update
'''
WRAPPER=r'''
#undef cryptAdler32Update
typedef struct{const void*p;size_t n;}SchemaSpan;
typedef struct{uint32_t table,row,field,length;uint64_t value;const uint8_t*text;}SchemaMutation;
static int valid_span(SchemaSpan s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(SchemaSpan a,SchemaSpan b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static uint32_t read32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t read64(const uint8_t*p){return(uint64_t)read32(p)|(uint64_t)read32(p+4)<<32;}
static CohStatus preflight(CohBytes bytes,SchemaMutation*m,uint32_t*count,SchemaCrcReceipt*r){
 r->stage=SCHEMA_CRC_STAGE_WIRE;
 if(bytes.size<8){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 if(memcmp(bytes.data,"SCR1",4)){r->failure_byte=0;return COH_INVALID;}
 *count=read32(bytes.data+4);
 if(*count>SCHEMA_CRC_MUTATION_MAX){r->failure_byte=4;return COH_LIMIT;}
 size_t at=8;
 for(uint32_t n=0;n<*count;n++){
  r->stage=SCHEMA_CRC_STAGE_WIRE;
  if(bytes.size-at<24){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
  size_t start=at;SchemaMutation*p=&m[n];p->table=read32(bytes.data+at);p->row=read32(bytes.data+at+4);p->field=read32(bytes.data+at+8);
  p->value=read64(bytes.data+at+12);p->length=read32(bytes.data+at+20);at+=24;
  if(p->length>SCHEMA_CRC_TEXT_MAX){r->failure_byte=(uint32_t)start+20;return COH_LIMIT;}
  if(p->length>bytes.size-at){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
  p->text=bytes.data+at;at+=p->length;r->stage=SCHEMA_CRC_STAGE_MUTATION;
  if(p->table>1){r->failure_byte=(uint32_t)start;return COH_UNSUPPORTED;}
  if(p->row>=(p->table?13u:1u)){r->failure_byte=(uint32_t)start+4;return COH_UNSUPPORTED;}
  if(p->field<SCHEMA_CRC_FIELD_NAME||p->field>SCHEMA_CRC_FIELD_DEFAULT_STRING){r->failure_byte=(uint32_t)start+8;return COH_UNSUPPORTED;}
  int type=TOK_GET_TYPE((p->table?ParseBodyPart:ParseBodyPartBegin)[p->row].type);
  if(p->field==SCHEMA_CRC_FIELD_NAME||p->field==SCHEMA_CRC_FIELD_DEFAULT_STRING){
   if(p->value){r->failure_byte=(uint32_t)start+12;return COH_INVALID;}
   if(p->field==SCHEMA_CRC_FIELD_DEFAULT_STRING&&type!=TOK_STRING_X&&type!=TOK_CURRENTFILE_X){r->failure_byte=(uint32_t)start+8;return COH_UNSUPPORTED;}
  }else{
   if(p->length){r->failure_byte=(uint32_t)start+20;return COH_INVALID;}
   if(p->field==SCHEMA_CRC_FIELD_TYPE_FLAGS&&(p->value&~(uint64_t)(TOK_REDUNDANTNAME|TOK_STRUCTPARAM))){r->failure_byte=(uint32_t)start+12;return COH_UNSUPPORTED;}
   if(p->field==SCHEMA_CRC_FIELD_PARAM&&(type==TOK_STRING_X||type==TOK_CURRENTFILE_X)&&p->value){r->failure_byte=(uint32_t)start+12;return COH_UNSUPPORTED;}
   if(p->field==SCHEMA_CRC_FIELD_FORMAT&&p->value>UINT32_MAX){r->failure_byte=(uint32_t)start+12;return COH_LIMIT;}
  }
 }
 if(at!=bytes.size){r->stage=SCHEMA_CRC_STAGE_WIRE;r->failure_byte=(uint32_t)at;return COH_INVALID;}
 return COH_OK;
}
static void mutate(const SchemaMutation*m,uint32_t count){
 memcpy(owner.root,ParseBodyPartBegin,sizeof(owner.root));memcpy(owner.parts,ParseBodyPart,sizeof(owner.parts));owner.root[0].subtable=owner.parts;
 for(uint32_t n=0;n<count;n++){
  const SchemaMutation*p=&m[n];ParseTable*t=(p->table?owner.parts:owner.root)+p->row;
  const ParseTable*base=(p->table?ParseBodyPart:ParseBodyPartBegin)+p->row;
  if(p->length)memcpy(owner.text[n],p->text,p->length);
  switch(p->field){
  case SCHEMA_CRC_FIELD_NAME:t->name=owner.text[n];break;
  case SCHEMA_CRC_FIELD_TYPE_FLAGS:t->type=base->type|(uint32_t)p->value;break;
  case SCHEMA_CRC_FIELD_PARAM:memcpy(&t->param,&p->value,8);break;
  case SCHEMA_CRC_FIELD_OFFSET:t->storeoffset=(size_t)p->value;break;
  case SCHEMA_CRC_FIELD_FORMAT:t->format=(uint32_t)p->value;break;
  case SCHEMA_CRC_FIELD_DEFAULT_STRING:{const char*value=owner.text[n];memcpy(&t->param,&value,sizeof(value));break;}
  default:assert(!"unqualified schema mutation");
  }
 }
}
CohStatus schema_crc_apply(CohBytes bytes,const SchemaCrcIdentity*observed,const SchemaCrcIdentity*expected,
 const CohCostumeImportDigest*digest,SchemaCrcResult*out,SchemaCrcReceipt*receipt,size_t budget,size_t retained){
 if(!bytes.data||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 SchemaSpan spans[7]={{bytes.data,bytes.size},{observed,sizeof(*observed)},{expected,sizeof(*expected)},{digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid_span(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(SchemaSpan){digest->context,digest->context_bytes};if(!valid_span(spans[6]))return COH_INVALID;
 for(unsigned j=0;j<6;j++)if(!apart(spans[6],spans[j]))return COH_INVALID;
 SchemaCrcReceipt result;memset(&result,0,sizeof(result));result.stage=SCHEMA_CRC_STAGE_INPUT;result.cleanup_complete=(uint32_t)schema_crc_is_idle();result.crypto_cleanup_complete=(uint32_t)schema_adler_is_idle();CohStatus status=COH_OK;
 if(!result.cleanup_complete)status=COH_STATE;
 else if(bytes.size>SCHEMA_CRC_WIRE_MAX||!budget||budget>SCHEMA_CRC_BUDGET_MAX)status=COH_LIMIT;
 else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+SCHEMA_CRC_STACK_RESERVE+schema_adler_object_bytes();
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.stage=SCHEMA_CRC_STAGE_IDENTITY;const uint8_t*labels=(const uint8_t*)expected;
 for(unsigned i=0;i<5;i++)if(zeros(labels+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.fixture_identity_matched=1;result.stage=SCHEMA_CRC_STAGE_PROFILE;uint16_t endian=1;
 if(*(const uint8_t*)&endian!=1){result.status=COH_UNSUPPORTED;*receipt=result;return COH_UNSUPPORTED;}
 SchemaMutation mutations[SCHEMA_CRC_MUTATION_MAX];memset(mutations,0,sizeof(mutations));uint32_t count=0;
 status=preflight(bytes,mutations,&count,&result);
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;schema_wipe(mutations,sizeof(mutations));return status;}
 result.mutation_count=count;result.stage=SCHEMA_CRC_STAGE_DIGEST;uint8_t hash[32];memset(hash,0,sizeof(hash));status=digest->sha256(digest->context,bytes,hash);
 if(status==COH_OK&&memcmp(hash,expected->input_sha256,32))status=COH_STATE;
 schema_wipe(hash,sizeof(hash));
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;schema_wipe(mutations,sizeof(mutations));return status;}
 owner.active=1;owner.receipt=result;owner.receipt.cleanup_complete=0;owner.receipt.crypto_cleanup_complete=0;owner.receipt.stage=SCHEMA_CRC_STAGE_SOURCE;
 mutate(mutations,count);schema_wipe(mutations,sizeof(mutations));owner.receipt.source_calls++;
 int crc=ParseTableCRC(owner.root,NULL);memcpy(&owner.candidate.crc,&crc,4);
 schema_adler_cleanup();owner.receipt.crypto_cleanup_complete=(uint32_t)schema_adler_is_idle();
 owner.receipt.update_calls=owner.candidate.update_calls;owner.receipt.stream_bytes=owner.candidate.stream_bytes;
 owner.receipt.visited_fields=owner.candidate.visited_fields;owner.receipt.interpret_calls=owner.candidate.interpret_calls;
 owner.receipt.status=COH_OK;owner.receipt.stage=SCHEMA_CRC_STAGE_COMPLETE;SchemaCrcResult candidate=owner.candidate;result=owner.receipt;
 schema_wipe(&owner,sizeof(owner));result.cleanup_complete=(uint32_t)schema_crc_is_idle();assert(result.cleanup_complete);
 *out=candidate;*receipt=result;schema_wipe(&candidate,sizeof(candidate));schema_wipe(&result,sizeof(result));return COH_OK;
}
'''

def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 pin_path=HERE/'schema-crc-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('schema-crc source pin changed: '+name)
  frozen[name]=raw
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()}
 def pattern(path,expression):
  match=re.search(expression,text[path],re.M|re.S)
  if not match:raise ValueError('missing schema-crc declaration '+expression)
  return match[0]
 def macro(path,name):
  match=re.search(r'^#define\s+'+re.escape(name)+r'(?=[ \t(])(?:\([^\n]*?\))?[^\n]*$',text[path],re.M)
  if not match:raise ValueError('missing original schema macro '+name)
  return match[0]
 declarations={
  'StructTypeField':pattern(TYPES_H,r'typedef U32 StructTypeField;'),
  'StructFormatField':pattern(TYPES_H,r'typedef U32 StructFormatField;'),
  'ParseTable':pattern(TYPES_H,r'typedef struct ParseTable\s*\{.*?\}\s*ParseTable;'),
  'BodyPart':pattern(BODY_H,r'typedef struct BodyPart\b.*?\}\s*BodyPart;'),
  'BodyPartList':pattern(BODY_H,r'typedef struct\s*\{\s*const BodyPart\*\* bodyParts;\s*\}\s*BodyPartList;'),
  'StructTokenType':pattern(PARSER_H,r'typedef enum\s*\{\s*TOK_IGNORE,.*?\} StructTokenType;'),
  'ParseInfoField':pattern(INTERNAL_H,r'typedef enum ParseInfoField\s*\{.*?\}\s*ParseInfoField;'),
  'ParseInfoFieldUsage':pattern(INTERNAL_H,r'typedef enum ParseInfoFieldUsage\s*\{.*?\}\s*ParseInfoFieldUsage;')}
 macro_inputs=[(STD_H,n)for n in('SIZEOF2','SIZEOF2_DEREF','SIZEOF2_DEREF2')]+[(PARSER_H,n)for n in('TOK_INT','TOK_STRING','TOK_CURRENTFILE','TOK_BOOLFLAG','TOK_STRUCT','TOK_TYPE_MASK','TOK_GET_TYPE','TOK_REDUNDANTNAME','TOK_STRUCTPARAM','TOK_EARRAY','TOK_FIXED_ARRAY','TOK_INDIRECT','FORALL_PARSETABLE')]+[(OLD_H,'FORALL_PARSEINFO'),(TYPES_H,'TokenizerParseInfo'),(INTERNAL_H,'TYPE_INFO')]
 macros={name:macro(path,name)for path,name in macro_inputs}
 tables={name:pattern(BODY_C,r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};')for name in('ParseBodyPart','ParseBodyPartBegin')}
 functions={name:extract(text[PARSER_C],name)for name in('ignore_interpretfield','number_interpretfield','string_interpretfield','struct_interpretfield','UpdateCRCFromParseInfo','ParseTableCRC')}
 token_table=pattern(INTERNAL_C,r'TokenTypeInfo g_tokentable\[\]\s*=\s*\{.*?^};');mappings={}
 for token,expected in(('TOK_END','ignore_interpretfield'),('TOK_INT_X','number_interpretfield'),('TOK_STRING_X','string_interpretfield'),('TOK_CURRENTFILE_X','string_interpretfield'),('TOK_BOOLFLAG_X','number_interpretfield'),('TOK_STRUCT_X','struct_interpretfield')):
  row=re.search(r'\{\s*'+token+r',.*?^\s*},',token_table,re.M|re.S)
  fields=re.sub(r'//[^\n]*','',row[0][1:]).split(',')if row else []
  if len(fields)<9 or fields[8].strip()!=expected:raise ValueError('original schema interpretfield dispatch changed '+token)
  mappings[token]=fields[8].strip()
 observers=''
 for name in('ignore_interpretfield','number_interpretfield','string_interpretfield','struct_interpretfield'):
  observers+='static ParseInfoFieldUsage observed_'+name+'(ParseTable*t,int c,ParseInfoField f){assert(owner.active);owner.candidate.interpret_calls++;return '+name+'(t,c,f);}\n'
 dispatch='static const SchemaHandler g_tokentable[NUM_TOK_TYPE_TOKENS]={'+','.join('['+token+']={observed_'+name+'}'for token,name in mappings.items())+'};\n'
 header=work/'schema-crc-provider.h';header.write_text(HEADER)
 table_bounds='typedef char root_table_count[(sizeof(ParseBodyPartBegin)/sizeof(ParseTable)==2)?1:-1];\ntypedef char child_table_count[(sizeof(ParseBodyPart)/sizeof(ParseTable)==14)?1:-1];\n'
 code=PREAMBLE+'\n'.join(declarations.values())+'\n'+'\n'.join(macros.values())+'\n'+'\n'.join(tables.values())+'\n'+table_bounds+ADAPTERS
 code+=''.join(functions[name]for name in('ignore_interpretfield','number_interpretfield','string_interpretfield','struct_interpretfield'))+observers+dispatch+functions['UpdateCRCFromParseInfo']+functions['ParseTableCRC']+WRAPPER
 provider=work/'schema-crc-provider.c';provider.write_text(code)
 crypt_functions={name:extract(text[CRYPT_C],name)for name in('cryptAdler32Init','cryptAdler32Update','cryptAdler32Final')}
 crypt_global=pattern(CRYPT_C,r'^THREADSAFE_STATIC Adler32 \*adler32 = NULL;[^\n]*$')
 thread_macro=macro(STD_H,'THREADSAFE_STATIC')
 adler_code='''#include <adler32.h>
#include <cstddef>
#include <cstdint>
using namespace CryptoPP;
typedef std::uint32_t U32;typedef std::uint8_t U8;
/* Explicit C++11 native thread-local/little-endian shell. */
#define COH_THREAD_LOCAL thread_local
#define endianSwapIfBig(type,value) (value)
'''+thread_macro+'\nextern "C" {\n'+crypt_global+'\n'+''.join(crypt_functions.values())+'''
int schema_adler_is_idle(void){return adler32==NULL;}
std::size_t schema_adler_object_bytes(void){return sizeof(Adler32);}
void schema_adler_cleanup(void){delete adler32;adler32=NULL;}
}
'''
 adler_cpp=work/'schema-crc-adler.cpp';adler_cpp.write_text(adler_code)
 dependency_module_path=HERE/'cryptopp_adler_source.py'
 spec=importlib.util.spec_from_file_location('coh_schema_cryptopp_dependency',dependency_module_path)
 dependency_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(dependency_module)
 dependency=dependency_module.prepare(root,work)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('schema-crc sources changed during emission')
 proof={'schema':'coh-original-schema-crc-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'source_stable_before_after':True,'whole_function_sha256_lf':{name:sha(value.encode())for name,value in functions.items()}|{name:sha(value.encode())for name,value in crypt_functions.items()},'original_declaration_sha256_lf':{name:sha(value.encode())for name,value in declarations.items()}|{'adler32_global':sha(crypt_global.encode())},'original_macro_sha256_lf':{name:sha(value.encode())for name,value in macros.items()}|{'THREADSAFE_STATIC':sha(thread_macro.encode())},'original_table_sha256_lf':{name:sha(value.encode())for name,value in tables.items()},'dispatch_source_audit':{'g_tokentable_sha256_lf':sha(token_table.encode()),'interpretfield_tokens':mappings,'holder_scope':'Immutable interpretfield-only holder with counting wrappers invoking exact source handlers; no complete handler-table ABI.'},'profile':'Exact fixed acyclic BodyPart root+child tables; definesNULL and no static defines. <=4 canonical owned mutations, text<=63B, wire<=356B, stream<=512B/64updates. Native int32/intptr64/size64 little-endian only; no engine/device ABI claim.','source_semantics':'Source names/types/int32 default bytes/default C-string bytes CRC; offsets/format/substruct sizeof ignored. Redundant fields skipped. Actual CryptoPP Final digest bytes returned through unchanged original little-endian U32 wrapper, never forced to retained header.','excluded_profiles':'External schema/subtable/define pointers, dynamic/static define CRC, recursion/reentrant schema graphs, primitive-type changes, alternate hash backend and cache-selection remain unqualified/guarded.','cleanup':'Owned schema/text/trace/staging volatile-wiped. Actual CryptoPP context is deleted and source TLS pointer reset; allocator zeroization/RSS/heap-failure closure not claimed. Result atomic and bounded numeric first failure safe. sizeof actual Adler32 charged with16KiB own stack and caller spans.','retained_CLIENT_crc_argument_used':False,'body_or_loader_or_cache_selection_executed':False,'current_Map_runtime_observed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'adler_cpp_path':str(adler_cpp),'crypto_dependency_expected_revision':'b5242667a24e3db8e4600e77b2e502ef204e5280','evidence_paths':{'schema_crc_header':str(header),'schema_crc_provider':str(provider),'schema_crc_adler_cpp':str(adler_cpp)}}
 proof['crypto_dependency']=dependency
 for path in dependency['repository_input_paths']:
  input_path=Path(path).resolve();proof['source_sha256'][str(input_path.relative_to(root))]=sha(input_path.read_bytes())
 return provider,proof
