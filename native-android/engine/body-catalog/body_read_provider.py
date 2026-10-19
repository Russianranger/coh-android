"""Bounded original ParserReadBinaryFile body composition, fixture only."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
BASE='upstream/ouroboros/'
SERIAL_C=BASE+'libs/UtilitiesLib/src/utils/serialize.c'
SERIAL_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/serialize.h'
PARSER_C=BASE+'libs/UtilitiesLib/src/utils/textparser.c'
PARSER_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/textparser.h'
INTERNAL_C=BASE+'libs/UtilitiesLib/src/utils/structInternals.c'
INTERNAL_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/structInternals.h'
BODY_C=BASE+'Common/gameData/BodyPart.c'
BODY_H=BASE+'Common/gameData/BodyPart.h'
TOKEN_C=BASE+'libs/UtilitiesLib/src/utils/tokenstore.c'
TOKEN_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/tokenstore.h'
TYPES_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/textparser_types.h'
STD_H=BASE+'libs/UtilitiesLib/include/utilitieslib/stdtypes.h'
LEX_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/structTokenizer.h'
OLD_H=BASE+'libs/UtilitiesLib/include/utilitieslib/utils/structoldnames.h'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def extract(text,name):
 match=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*)?\s*\{',text,re.M)
 if not match:raise ValueError('missing original body-read function '+name)
 at=text.index('{',match.start())+1;depth=1
 while depth:
  if at>=len(text):raise ValueError('unterminated original body-read function '+name)
  depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[match.start():at]+'\n'
HEADER=r'''/* Original source fixture only; no runtime/catalog/generation/authority. */
#ifndef COH_BODY_READ_PROVIDER_H
#define COH_BODY_READ_PROVIDER_H
#include "coh_costume_import.h"
#define BODYREAD_STAGE_INPUT 1u
#define BODYREAD_STAGE_IDENTITY 2u
#define BODYREAD_STAGE_PROFILE 3u
#define BODYREAD_STAGE_HEADER 4u
#define BODYREAD_STAGE_TYPE_LENGTH 5u
#define BODYREAD_STAGE_HEADER_EXTENT 6u
#define BODYREAD_STAGE_DEPENDENCY_HEADER 7u
#define BODYREAD_STAGE_DEPENDENCY_SIZE 8u
#define BODYREAD_STAGE_BODY_LENGTH 9u
#define BODYREAD_STAGE_COUNT 10u
#define BODYREAD_STAGE_ROW_LENGTH 11u
#define BODYREAD_STAGE_STRING 12u
#define BODYREAD_STAGE_SCALAR 13u
#define BODYREAD_STAGE_DIGEST 14u
#define BODYREAD_STAGE_HEADER_REJECT 15u
#define BODYREAD_STAGE_SOURCE_REJECT 16u
#define BODYREAD_STAGE_COMPLETE 17u
#define BODYREAD_PART_MAX 30u
#define BODYREAD_STRING_MAX 260u
#define BODYREAD_INPUT_MAX 65536u
#define BODYREAD_BUDGET_MAX (1024u*1024u)
#define BODYREAD_STACK_RESERVE 98304u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}BodyReadIdentity;
typedef struct{
 char name[260],source_file[260],geometry_name[260],texture_name[260],base_name[260];
 uint32_t raw[7]; /* first BoneCount,influence,last BoneCount,DontClear,bones2,index */
 uint32_t final_num_parts,final_influence_cost,final_dont_clear,final_bones[2],final_index,string_null_mask;
}BodyReadPart;
typedef struct{
 uint32_t header_end,dependency_end,body_end,part_count,raw_array_count,body_declared_size;
 BodyReadPart parts[BODYREAD_PART_MAX];
}BodyReadResult;
typedef struct{
 uint32_t status,stage,failure_byte,open_calls,read_calls,seek_calls;
 uint32_t source_close_calls,wrapper_close_calls,header_accepted,filelist_calls;
 uint32_t table_calls,capacity_calls,allocation_calls,string_calls,int_calls,u8_calls;
 uint32_t warning_calls,source_result,header_end,dependency_end,body_end;
 uint32_t source_node_count,raw_array_count,body_declared_size,fixture_identity_matched,cleanup_complete;
}BodyReadReceipt;
/* All spans/digest context disjoint. Invalid sinks unchanged. Safe numeric
 * diagnostics may change on refusal; result commits only after source success
 * and owned cleanup. Raw CRC argument is fixturedata, not actual ParseTableCRC.
 */
CohStatus bodyread_apply(CohBytes,const BodyReadIdentity*,const BodyReadIdentity*,
 const CohCostumeImportDigest*,uint32_t,uint32_t,
 BodyReadResult*,BodyReadReceipt*,size_t,size_t);
int bodyread_is_idle(void);
#endif
'''
PREAMBLE=r'''
#include "body-read-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t U32;typedef uint16_t U16;typedef uint8_t U8;typedef int BoneId;typedef int32_t __time32_t;
#define INLINEDBG inline
#define endianSwapIfBig(type,value) (value)
#define devassert assert
#define SAFESTR(x) x,sizeof(x)
#define MAX_PATH 260
typedef char host32[(sizeof(int)==4&&sizeof(BoneId)==4&&sizeof(__time32_t)==4)?1:-1];
'''
ADAPTERS=r'''
typedef int(*readbin_f)(SimpleBufHandle,ParseTable*,int,void*,int,int*);
/* Explicit readbin-only holders; not original complete engine handler ABI. */
typedef struct{readbin_f readbin;}BodyHandler;
static const BodyHandler g_arraytable[3],g_tokentable[NUM_TOK_TYPE_TOKENS];
typedef struct{
 int active,opened;size_t input_size;uint32_t capacity,nodes,strings;
 unsigned char data[BODYREAD_INPUT_MAX];SimpleBuffer buffer;BodyPartList root;
 BodyPart parts[BODYREAD_PART_MAX];const BodyPart*pointers[BODYREAD_PART_MAX];
 char text[BODYREAD_PART_MAX][5][BODYREAD_STRING_MAX];uint32_t raw[BODYREAD_PART_MAX][7];
 uint32_t raw_written[BODYREAD_PART_MAX],string_written[BODYREAD_PART_MAX];
 uint32_t body_start;BodyReadReceipt receipt;
}BodyOwner;
static BodyOwner owner;
static char*parser_relpath;
static void body_wipe(void*p,size_t n){volatile unsigned char*c=p;while(n--)*c++=0;}
static int zeros(const void*p,size_t n){const unsigned char*c=p;for(size_t i=0;i<n;i++)if(c[i])return 0;return 1;}
int bodyread_is_idle(void){return !parser_relpath&&zeros(&owner,sizeof(owner));}
int SimpleBufTell(SimpleBufHandle);
int ParserReadBinaryTable(SimpleBufHandle,ParseTable*,void*,int*);
static int observed_table(SimpleBufHandle,ParseTable*,void*,int*);
static SimpleBufHandle SimpleBufOpenRead(const char*name){
 assert(owner.active&&!owner.opened&&!strcmp(name,"bin/BodyParts.bin"));owner.receipt.open_calls++;
 owner.buffer.data=(char*)owner.data;owner.buffer.filesize=(int)owner.input_size;
 owner.buffer.memsize=(int)sizeof(owner.data);memcpy(owner.buffer.filename,name,sizeof("bin/BodyParts.bin"));
 owner.opened=1;return(SimpleBufHandle)&owner.buffer;
}
static void SimpleBufClose(SimpleBufHandle file){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer);
 owner.receipt.source_close_calls++;if(!owner.receipt.header_accepted)owner.receipt.header_end=(uint32_t)SimpleBufTell(file);
 owner.opened=0;body_wipe(&owner.buffer,sizeof(owner.buffer));body_wipe(owner.data,sizeof(owner.data));
}
static void SimpleBufResizeEx(SimpleBufHandle file,int bytes){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer&&bytes>=0&&bytes<=owner.buffer.filesize);
}
/* FileListRead(NULL) must not enter its collect allocators. */
static void*unqualified_calloc(size_t a,size_t b){(void)a;(void)b;assert(!"unqualified collected FileList allocation");return NULL;}
static void unqualified_eacreate(FileList*p){(void)p;assert(!"unqualified collected FileList creation");}
static void unqualified_eapush(FileList*p,FileEntry*n){(void)p;(void)n;assert(!"unqualified collected FileList push");}
#define calloc unqualified_calloc
#define eaCreate unqualified_eacreate
#define eaPush unqualified_eapush
static uint32_t part_index(void*p){
 for(uint32_t i=0;i<owner.nodes;i++)if(p==&owner.parts[i])return i;
 assert(!"unowned original BodyPart");return 0;
}
static void TokenStoreSetCapacity(ParseTable*t,int c,void*p,int n){
 assert(owner.active&&t==ParseBodyPartBegin&&c==0&&p==&owner.root&&n>0&&n<=(int)BODYREAD_PART_MAX&&!owner.capacity);
 owner.capacity=(uint32_t)n;owner.root.bodyParts=owner.pointers;owner.receipt.capacity_calls++;
}
static void*TokenStoreAlloc(ParseTable*t,int c,void*p,int index,U32 size,void*a,void*b){
 assert(owner.active&&t==ParseBodyPartBegin&&c==0&&p==&owner.root&&index==(int)owner.nodes&&owner.nodes<owner.capacity&&size==sizeof(BodyPart)&&!a&&!b);
 BodyPart*part=&owner.parts[owner.nodes];owner.pointers[owner.nodes++]=part;owner.receipt.allocation_calls++;return part;
}
static void TokenStoreSetInt(ParseTable*t,int c,void*p,int index,int value){
 assert(owner.active&&t==ParseBodyPart&&index==0&&(c==2||c==3||c==7||c==9||c==10||c==11));
 uint32_t n=part_index(p),slot=c==2?0:c==3?1:c==7?2:(uint32_t)c-5;
 assert(!(owner.raw_written[n]&(1u<<slot)));owner.raw_written[n]|=1u<<slot;
 memcpy(&owner.raw[n][slot],&value,4);memcpy((char*)p+t[c].storeoffset,&value,4);owner.receipt.int_calls++;
}
static void TokenStoreSetU8(ParseTable*t,int c,void*p,int index,U8 value){
 assert(owner.active&&t==ParseBodyPart&&c==8&&index==0);uint32_t n=part_index(p);
 assert(owner.raw_written[n]&(1u<<3));*((U8*)p+t[c].storeoffset)=value;owner.receipt.u8_calls++;
}
static char*TokenStoreSetString(ParseTable*t,int c,void*p,int index,const char*s,void*a,void*b){
 assert(owner.active&&t==ParseBodyPart&&index==0&&!a&&!b&&(c==0||c==1||c==4||c==5||c==6));
 uint32_t n=part_index(p),slot=c<2?(uint32_t)c:(uint32_t)c-2;size_t len=strlen(s);assert(len<BODYREAD_STRING_MAX);
 assert(!(owner.string_written[n]&(1u<<slot)));owner.string_written[n]|=1u<<slot;owner.receipt.string_calls++;
 char*value=NULL;if(len){memcpy(owner.text[n][slot],s,len+1);value=owner.text[n][slot];owner.strings++;}
 memcpy((char*)p+t[c].storeoffset,&value,sizeof(value));return value;
}
static int ParseTableCRC(ParseTable*t,void*d){(void)t;(void)d;assert(!"actual ParseTableCRC unavailable");return 0;}
static int isProductionMode(void){assert(!"unopened ParserReadBinaryFile route unavailable");return 0;}
typedef void DefineContext;
static char*allocAddString(const char*s){assert(owner.active&&!strcmp(s,"bin/BodyParts.bin"));return owner.buffer.filename;}
'''
OBSERVERS=r'''
static int observed_read(void*data,int bytes,SimpleBufHandle file){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer&&bytes>=0);
 int at=SimpleBufTell(file);owner.receipt.read_calls++;int result=SimpleBufRead(data,bytes,file);
 if(owner.body_start&&bytes==4&&result==4){
  if(at==(int)owner.body_start)memcpy(&owner.receipt.body_declared_size,data,4);
  if(at==(int)owner.body_start+4)memcpy(&owner.receipt.raw_array_count,data,4);
 }
 /* Source u8_readbin reads raw32 before narrowing at its setter. */
 if(bytes==4&&result==4&&owner.nodes&&owner.string_written[owner.nodes-1]==31u&&owner.raw_written[owner.nodes-1]==7u){
  memcpy(&owner.raw[owner.nodes-1][3],data,4);owner.raw_written[owner.nodes-1]|=8u;
 }
 return result;
}
static int observed_seek(SimpleBufHandle file,long offset,int origin){
 assert(owner.active&&owner.opened&&file==(SimpleBufHandle)&owner.buffer);owner.receipt.seek_calls++;
 if(origin==SEEK_END)owner.receipt.body_end=(uint32_t)SimpleBufTell(file);
 return SimpleBufSeek(file,offset,origin);
}
static int observed_printf(const char*format,...){
 assert(owner.active&&format&&(!strcmp(format,"ParserReadBinaryTable: unexpected end of file\n")||!strcmp(format,"ParserReadBinaryTable: datasum length not correct\n")||!strcmp(format,"ParserReadBinaryFile: unexpected end of file\n")));
 owner.receipt.warning_calls++;assert(owner.receipt.warning_calls<=4);return 0;
}
#define SimpleBufRead observed_read
#define SimpleBufSeek observed_seek
#define printf observed_printf
'''
LINKS=r'''
static int observed_table(SimpleBufHandle file,ParseTable*t,void*p,int*sum){
 assert(owner.active&&owner.opened&&((t==ParseBodyPartBegin&&p==&owner.root)||(t==ParseBodyPart&&owner.nodes&&p==&owner.parts[owner.nodes-1])));
 if(t==ParseBodyPartBegin){assert(!owner.body_start);owner.body_start=(uint32_t)SimpleBufTell(file);}
 owner.receipt.table_calls++;return ParserReadBinaryTable(file,t,p,sum);
}
static int observed_filelist(FileList*list,SimpleBufHandle file){
 assert(owner.active&&!list);owner.receipt.filelist_calls++;int result=FileListRead(list,file);
 owner.receipt.dependency_end=(uint32_t)SimpleBufTell(file);return result;
}
#define FileListRead observed_filelist
#define ParserReadBinaryTable observed_table
'''
WRAPPER=r'''
#undef FileListRead
#undef ParserReadBinaryTable
#undef SimpleBufRead
#undef SimpleBufSeek
#undef printf
#undef calloc
#undef eaCreate
#undef eaPush
typedef struct{const void*p;size_t n;}BodySpan;
static int valid_span(BodySpan s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(BodySpan a,BodySpan b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static uint32_t read16(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8;}
static uint32_t read32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int32_t signed32(uint32_t word){int32_t value;memcpy(&value,&word,4);return value;}
static int cstring_matches(const uint8_t*p,size_t n,const char*expected){size_t used=0;while(used<n&&p[used])used++;return used==strlen(expected)&&!memcmp(p,expected,used);}
static CohStatus framing(CohBytes bytes,uint32_t build_crc,uint32_t ignore_crc,BodyReadReceipt*r){
 r->stage=BODYREAD_STAGE_HEADER;
 if(bytes.size<14){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 uint32_t len=read16(bytes.data+12);r->stage=BODYREAD_STAGE_TYPE_LENGTH;
 if(len>=MAX_FILETYPE_LEN){r->failure_byte=12;return COH_LIMIT;}
 size_t at=14u+len+(4u-(len+2u)%4u)%4u;r->stage=BODYREAD_STAGE_HEADER_EXTENT;
 if(at>bytes.size){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 if(memcmp(bytes.data,"CrypticS",8)||!cstring_matches(bytes.data+14,len,PARSE_SIG)||(!ignore_crc&&read32(bytes.data+8)!=build_crc))return COH_OK;
 r->stage=BODYREAD_STAGE_DEPENDENCY_HEADER;
 if(bytes.size-at<2){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 uint32_t siglen=read16(bytes.data+at);size_t end=at+2u+siglen+(4u-(siglen+2u)%4u)%4u;
 if(end>bytes.size||bytes.size-end<4){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 int32_t skip=signed32(read32(bytes.data+end));at=end+4;r->stage=BODYREAD_STAGE_DEPENDENCY_SIZE;
 if(skip<0){r->failure_byte=(uint32_t)end;return COH_UNSUPPORTED;}
 if((uint32_t)skip>bytes.size-at){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}at+=(uint32_t)skip;
 r->stage=BODYREAD_STAGE_BODY_LENGTH;
 if(bytes.size-at<4){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}at+=4;
 r->stage=BODYREAD_STAGE_COUNT;
 if(bytes.size-at<4){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
 int32_t count=signed32(read32(bytes.data+at));
 if(count>(int32_t)BODYREAD_PART_MAX){r->failure_byte=(uint32_t)at;return COH_LIMIT;}at+=4;
 for(int32_t n=0;n<count;n++){
  r->stage=BODYREAD_STAGE_ROW_LENGTH;
  if(bytes.size-at<4){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
  int32_t declared=signed32(read32(bytes.data+at));at+=4;size_t begin=at;int c;
  FORALL_PARSEINFO(ParseBodyPart,c){
   int type=TOK_GET_TYPE(ParseBodyPart[c].type);
   if(type==TOK_CURRENTFILE_X||type==TOK_STRING_X){
    r->stage=BODYREAD_STAGE_STRING;
    if(bytes.size-at<2){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}
    uint32_t stringlen=read16(bytes.data+at);
    if(stringlen>=BODYREAD_STRING_MAX){r->failure_byte=(uint32_t)at;return COH_LIMIT;}
    size_t amount=2u+stringlen+(4u-(stringlen+2u)%4u)%4u;
    if(amount>bytes.size-at){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}at+=amount;
   }else if(type==TOK_INT_X||type==TOK_BOOLFLAG_X){
    r->stage=BODYREAD_STAGE_SCALAR;
    if(bytes.size-at<4){r->failure_byte=(uint32_t)bytes.size;return COH_INVALID;}at+=4;
   }else assert(type==TOK_END);
  }
  if((int64_t)(at-begin)!=(int64_t)declared)break; /* Source short-circuits later rows. */
 }
 return COH_OK;
}
static void copy_part(BodyReadPart*out,const BodyPart*part,uint32_t n){
 const char*strings[5]={part->name,part->sourceFile,part->name_geo,part->name_tex,part->base_var};
 char*dest[5]={out->name,out->source_file,out->geometry_name,out->texture_name,out->base_name};
 for(unsigned k=0;k<5;k++){if(strings[k]){size_t len=strlen(strings[k]);assert(len<BODYREAD_STRING_MAX);memcpy(dest[k],strings[k],len+1);}else out->string_null_mask|=1u<<k;}
 assert(owner.raw_written[n]==127u&&owner.string_written[n]==31u);memcpy(out->raw,owner.raw[n],sizeof(out->raw));
 memcpy(&out->final_num_parts,&part->num_parts,4);memcpy(&out->final_influence_cost,&part->influenceCost,4);
 out->final_dont_clear=part->dont_clear;memcpy(out->final_bones,part->bone_num,8);memcpy(&out->final_index,&part->bodyPartIndex,4);
}
CohStatus bodyread_apply(CohBytes bytes,const BodyReadIdentity*observed,const BodyReadIdentity*expected,
 const CohCostumeImportDigest*digest,uint32_t build_crc,uint32_t ignore_crc,
 BodyReadResult*out,BodyReadReceipt*receipt,size_t budget,size_t retained){
 if(!bytes.data||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 BodySpan spans[7]={{bytes.data,bytes.size},{observed,sizeof(*observed)},{expected,sizeof(*expected)},
  {digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid_span(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(BodySpan){digest->context,digest->context_bytes};if(!valid_span(spans[6]))return COH_INVALID;
 for(unsigned j=0;j<6;j++)if(!apart(spans[6],spans[j]))return COH_INVALID;
 BodyReadReceipt result;memset(&result,0,sizeof(result));result.stage=BODYREAD_STAGE_INPUT;result.cleanup_complete=(uint32_t)bodyread_is_idle();CohStatus status=COH_OK;
 if(!result.cleanup_complete)status=COH_STATE;
 else if(bytes.size>BODYREAD_INPUT_MAX||!budget||budget>BODYREAD_BUDGET_MAX)status=COH_LIMIT;
 else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+BODYREAD_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.stage=BODYREAD_STAGE_IDENTITY;const unsigned char*labels=(const unsigned char*)expected;
 for(unsigned i=0;i<5;i++)if(zeros(labels+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.fixture_identity_matched=1;result.stage=BODYREAD_STAGE_PROFILE;uint16_t host_endian=1;
 if(ignore_crc>1||*(const unsigned char*)&host_endian!=1){result.status=COH_UNSUPPORTED;*receipt=result;return COH_UNSUPPORTED;}
 status=framing(bytes,build_crc,ignore_crc,&result);
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.stage=BODYREAD_STAGE_DIGEST;uint8_t hash[32];memset(hash,0,sizeof(hash));status=digest->sha256(digest->context,bytes,hash);
 if(status==COH_OK&&memcmp(hash,expected->input_sha256,32))status=COH_STATE;
 body_wipe(hash,sizeof(hash));
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 owner.active=1;owner.input_size=bytes.size;owner.receipt=result;owner.receipt.cleanup_complete=0;memcpy(owner.data,bytes.data,bytes.size);
 int compare_build;memcpy(&compare_build,&build_crc,4);SimpleBufHandle handle=SerializeReadOpen("bin/BodyParts.bin",PARSE_SIG,compare_build,(int)ignore_crc);
 BodyReadResult candidate;memset(&candidate,0,sizeof(candidate));
 if(!handle){owner.receipt.stage=BODYREAD_STAGE_HEADER_REJECT;status=COH_UNSUPPORTED;}
 else{
  owner.receipt.header_accepted=1;owner.receipt.header_end=(uint32_t)SimpleBufTell(handle);
  int accepted=ParserReadBinaryFile(handle,"bin/BodyParts.bin",ParseBodyPartBegin,&owner.root,NULL,NULL);
  owner.receipt.source_result=(uint32_t)accepted;owner.receipt.source_node_count=owner.nodes;
  if(accepted){
   candidate.header_end=owner.receipt.header_end;candidate.dependency_end=owner.receipt.dependency_end;candidate.body_end=owner.receipt.body_end;
   candidate.part_count=owner.nodes;candidate.raw_array_count=owner.receipt.raw_array_count;candidate.body_declared_size=owner.receipt.body_declared_size;
   assert(owner.nodes==owner.capacity);for(uint32_t n=0;n<owner.nodes;n++){assert(owner.root.bodyParts[n]==&owner.parts[n]);copy_part(&candidate.parts[n],owner.root.bodyParts[n],n);}
   owner.receipt.stage=BODYREAD_STAGE_COMPLETE;status=COH_OK;
  }else{owner.receipt.stage=BODYREAD_STAGE_SOURCE_REJECT;status=COH_UNSUPPORTED;}
 }
 owner.receipt.status=(uint32_t)status;result=owner.receipt;assert(!owner.opened&&!parser_relpath);body_wipe(&owner,sizeof(owner));result.cleanup_complete=(uint32_t)bodyread_is_idle();
 if(status==COH_OK)*out=candidate;
 *receipt=result;body_wipe(&candidate,sizeof(candidate));body_wipe(&result,sizeof(result));return status;
}
'''

def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 pin_path=HERE/'body-read-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('body-read source pin changed: '+name)
  frozen[name]=raw
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()}
 def pattern(path,expression):
  match=re.search(expression,text[path],re.M|re.S)
  if not match:raise ValueError('missing body source declaration '+expression)
  return match[0]
 declarations={
  'SimpleBuffer':pattern(SERIAL_C,r'typedef struct SimpleBuffer\s*\{.*?\}\s*SimpleBuffer\s*;'),
  'SimpleBufHandle':pattern(SERIAL_H,r'typedef struct _SimpleBufHandle \*SimpleBufHandle;'),
  'FileEntry':pattern(INTERNAL_H,r'typedef struct FileEntry\s*\{.*?\}\s*FileEntry\s*;'),
  'FileList':pattern(INTERNAL_H,r'typedef FileEntry\*\* FileList;'),
  'BodyPart':pattern(BODY_H,r'typedef struct BodyPart\b.*?\}\s*BodyPart;'),
  'BodyPartList':pattern(BODY_H,r'typedef struct\s*\{\s*const BodyPart\*\* bodyParts;\s*\}\s*BodyPartList;'),
  'ParseTable':pattern(TYPES_H,r'typedef struct ParseTable\s*\{.*?\}\s*ParseTable;'),
  'StructTypeField':pattern(TYPES_H,r'typedef U32 StructTypeField;'),
  'StructFormatField':pattern(TYPES_H,r'typedef U32 StructFormatField;'),
  'StructTokenType':pattern(PARSER_H,r'typedef enum\s*\{\s*TOK_IGNORE,.*?\} StructTokenType;')}
 def macro(path,name):
  match=re.search(r'^#define\s+'+re.escape(name)+r'(?=[ \t(])(?:\([^\n]*?\))?[^\n]*$',text[path],re.M)
  if not match:raise ValueError('missing original body macro '+name)
  return match[0]
 macro_inputs=[(STD_H,n)for n in('SIZEOF2','SIZEOF2_DEREF','SIZEOF2_DEREF2')]
 macro_inputs +=[(PARSER_H,n)for n in('TOK_INT','TOK_STRING','TOK_CURRENTFILE','TOK_BOOLFLAG','TOK_STRUCT','TOK_TYPE_MASK','TOK_GET_TYPE','TOK_REDUNDANTNAME','TOK_EARRAY','TOK_FIXED_ARRAY','TOK_INDIRECT','FORALL_PARSETABLE','PARSE_SIG')]
 macro_inputs +=[(TOKEN_H,n)for n in('TOK_STORAGE_DIRECT_SINGLE','TOK_STORAGE_DIRECT_FIXEDARRAY','TOK_STORAGE_DIRECT_EARRAY','TOK_STORAGE_INDIRECT_SINGLE')]
 macro_inputs +=[(OLD_H,'FORALL_PARSEINFO'),(TYPES_H,'TokenizerParseInfo'),(LEX_H,'MAX_TOKEN_LENGTH'),(LEX_H,'MAX_STRING_LENGTH'),(INTERNAL_H,'TOKARRAY_INFO'),(INTERNAL_H,'TYPE_INFO'),(INTERNAL_H,'FILELIST_SIG'),(SERIAL_H,'MAX_FILETYPE_LEN'),(SERIAL_C,'cryptic_sig_len')]
 macros={name:macro(path,name)for path,name in macro_inputs}
 signature=pattern(SERIAL_C,r'^static char cryptic_sig\[\]\s*=\s*"CrypticS";[^\n]*$')
 tables={name:pattern(BODY_C,r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};')for name in('ParseBodyPart','ParseBodyPartBegin')}
 paths={SERIAL_C:('SimpleBufRead','SimpleBufSeek','SimpleBufTell','ReadPascalString','SkipPascalString','SerializeSkipStruct','SerializeReadOpen','SerializeReadHeader','SerializeReadData','SerializeClose'),SERIAL_H:('SimpleBufReadU16','SimpleBufReadU32'),INTERNAL_C:('FileListCreate','FileListRead'),TOKEN_C:('TokenStoreGetStorageType',),PARSER_C:('u8_readbin','int_readbin','string_readbin','struct_readbin','nonarray_readbin','earray_readbin','ParserReadBinaryTable','ParserReadBinaryFile')}
 functions={name:extract(text[path],name)for path,names in paths.items()for name in names}
 # Retain source dispatch identities while emitting explicit readbin-only holders.
 token_table=pattern(INTERNAL_C,r'TokenTypeInfo g_tokentable\[\]\s*=\s*\{.*?^};')
 array_table=pattern(INTERNAL_C,r'TokenArrayInfo g_arraytable\[3\]\s*=\s*\{.*?^};')
 mappings={}
 for token,expected in(('TOK_END','0'),('TOK_INT_X','int_readbin'),('TOK_STRING_X','string_readbin'),('TOK_CURRENTFILE_X','string_readbin'),('TOK_BOOLFLAG_X','u8_readbin'),('TOK_STRUCT_X','struct_readbin')):
  row=re.search(r'\{\s*'+token+r',.*?^\s*},',token_table,re.M|re.S)
  fields=re.sub(r'//[^\n]*','',row[0][1:]).split(',')if row else []
  if len(fields)<16 or fields[15].strip()!=expected:raise ValueError('original body token dispatch changed '+token)
  mappings[token]=fields[15].strip()
 array_rows=re.findall(r'\{\s*([^{}]+)\}',array_table)
 array_mappings=[row.split(',')[5].strip()for row in array_rows]
 if array_mappings!=['nonarray_readbin','fixedarray_readbin','earray_readbin']:raise ValueError('original body array dispatch changed')
 dispatch='static const BodyHandler g_arraytable[3]={{nonarray_readbin},{NULL},{earray_readbin}};\nstatic const BodyHandler g_tokentable[NUM_TOK_TYPE_TOKENS]={'+','.join('['+name+']={'+('NULL'if value=='0'else value)+'}'for name,value in mappings.items())+'};\n'
 loader=extract(text[PARSER_C],'ParserLoadFiles');call=re.search(r'ParserReadBinaryFile\(binfile,\s*persistfilepath,\s*pti,\s*structptr,\s*NULL,\s*globaldefines\)',loader)
 setter=extract(text[TOKEN_C],'TokenStoreSetString')
 if not call or not re.search(r'if\s*\(str && !str\[0\]\) str = NULL;',setter):raise ValueError('original body loader/string association changed')
 header=work/'body-read-provider.h';header.write_text(HEADER)
 code=PREAMBLE+'\n'.join(declarations[n]for n in('SimpleBufHandle','SimpleBuffer','FileEntry','FileList','BodyPart','BodyPartList','StructTypeField','StructFormatField','ParseTable','StructTokenType'))+'\n'+'\n'.join(macros.values())+'\n'+signature+'\n'+'\n'.join(tables.values())+'\n'+ADAPTERS
 code+=''.join(functions[n]for n in('SimpleBufRead','SimpleBufSeek','SimpleBufTell'))+OBSERVERS
 code+=''.join(functions[n]for n in('SimpleBufReadU16','SimpleBufReadU32','ReadPascalString','SkipPascalString','SerializeSkipStruct','SerializeReadOpen','SerializeReadHeader','SerializeReadData','SerializeClose','FileListCreate','FileListRead','TokenStoreGetStorageType'))
 code+='#define ParserReadBinaryTable observed_table\n'+''.join(functions[n]for n in('u8_readbin','int_readbin','string_readbin','struct_readbin','nonarray_readbin','earray_readbin'))+'#undef ParserReadBinaryTable\n'+functions['ParserReadBinaryTable']+dispatch+LINKS+functions['ParserReadBinaryFile']+WRAPPER
 provider=work/'body-read-provider.c';provider.write_text(code)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('body-read sources changed during emission')
 proof={'schema':'coh-original-body-read-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'source_stable_before_after':True,'whole_function_sha256_lf':{name:sha(value.encode())for name,value in functions.items()},'original_declaration_sha256_lf':{name:sha(value.encode())for name,value in declarations.items()},'original_macro_sha256_lf':{name:sha(value.encode())for name,value in macros.items()},'original_table_sha256_lf':{name:sha(value.encode())for name,value in tables.items()},'dispatch_source_audit':{'g_tokentable_sha256_lf':sha(token_table.encode()),'g_arraytable_sha256_lf':sha(array_table.encode()),'readbin_tokens':mappings,'readbin_array_order':array_mappings,'emitted_holders':'Explicit immutable readbin-only member holders; original TYPE_INFO/TOKARRAY_INFO selectors execute. No complete handler-table ABI or other engine operation claimed.'},'original_unexecuted_source_audits':{'ParserLoadFiles_sha256_lf':sha(loader.encode()),'loader_NULL_call':call[0],'TokenStoreSetString_sha256_lf':sha(setter.encode()),'empty_indirect_string_becomes_NULL':True,'functions_executed':False},'profile':'<=64KiB, positive part-count cap30, declared per-string length<=259, source-entered schema preflight with late accounting short-circuit; native policy only. Negative signed array count retains source zero-iteration behavior and raw word.','original_composition':'Whole original SerializeReadOpen -> ParserReadBinaryFile(supplied owned handle) -> FileListRead(NULL) -> ParserReadBinaryTable and original array/struct/string/int/U8 handlers -> original file-end accounting/SerializeClose. No old checker/main or native full-body decoder.','raw_loaded_fields':'All five C-string prefixes/NULL masks, seven raw numeric words, last BoneCount overwrite, raw cached bone/index words and source low8 U8 truncation retained. No ParseBoneNames/recalculation.','host_adapters':['Fixed owned open/close/no-growth input64KiB; FileList collect/allocation branches guarded and unexecuted','Exact full six-field ParseTable, original two macro schemas and full BodyPart/List declarations; U32/U16/U8/int32/BoneId shell and native little-endian host only, no Win32/Android ABI claim','Fresh fixed owned TokenStore capacity/row/string/int/U8 storage adapters; indirect empty strings ->NULL source rule audited. Not whole original allocator/storage implementation','Read/seek/table/FileList observers retain bounded counters/cursors; fixed original accounting warnings become numeric counts','Source ParserReadBinaryFile receives opened handle; unopened/ParseTableCRC/profile selection traps unexecuted'],'cleanup':'Original header or file close always closes owned buffer; source parser_relpath resets. Partial rows/strings remain owned and volatile-wiped, candidate commits atomically only after original success; bounded safe numeric diagnostics.','stack_reserve_bytes':98304,'actual_ParseTableCRC_computed':False,'original_ParseBoneNames_executed':False,'original_ParserLoadFiles_executed':False,'current_Map_runtime_observed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{'body_read_header':str(header),'body_read_provider':str(provider)}}
 return provider,proof
