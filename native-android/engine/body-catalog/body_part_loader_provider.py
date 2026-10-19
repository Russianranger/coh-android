"""Original body-part loader, fixture-scoped nonshared exact cache-hit profile.

No full original binary reader/CRC, text parser, shared generation, current Map
runtime, catalog/default or dictionary generation is admitted by this provider.
"""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
PREFIX='upstream/ouroboros/'
BODY_C=PREFIX+'Common/gameData/BodyPart.c'
BODY_H=PREFIX+'Common/gameData/BodyPart.h'
COSTUME_H=PREFIX+'Common/entity/costume.h'
BONES_H=PREFIX+'Common/seq/bones.h'
PARSER_C=PREFIX+'libs/UtilitiesLib/src/utils/textparser.c'
PARSER_H=PREFIX+'libs/UtilitiesLib/include/utilitieslib/utils/textparser.h'
SHARED_H=PREFIX+'libs/UtilitiesLib/include/utilitieslib/components/SharedMemory.h'
STDTYPES_H=PREFIX+'libs/UtilitiesLib/include/utilitieslib/stdtypes.h'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def extract(text,name):
 match=re.search(r'^[^\n{};=()]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*)?\s*\{',text,re.M)
 if not match:raise ValueError('missing original loader function '+name)
 at=text.index('{',match.start())+1;depth=1
 while depth:
  if at>=len(text):raise ValueError('unterminated original loader function '+name)
  depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[match.start():at]+'\n'
HEADER=r'''/* Fixture source-loader API: no current Map/runtime/catalog authority. */
#ifndef COH_BODY_PART_LOADER_PROVIDER_H
#define COH_BODY_PART_LOADER_PROVIDER_H
#include "coh_costume_inputs.h"
#define BODYLOADER_STAGE_INPUT 1u
#define BODYLOADER_STAGE_IDENTITY 2u
#define BODYLOADER_STAGE_PROFILE 3u
#define BODYLOADER_STAGE_ENTRY 4u
#define BODYLOADER_STAGE_SHARED 5u
#define BODYLOADER_STAGE_ACQUIRE 6u
#define BODYLOADER_STAGE_LOAD 7u
#define BODYLOADER_STAGE_LOCATE 8u
#define BODYLOADER_STAGE_PERSIST 9u
#define BODYLOADER_STAGE_BINARY 10u
#define BODYLOADER_STAGE_DECODE 11u
#define BODYLOADER_STAGE_LOADED 12u
#define BODYLOADER_STAGE_COMPLETE 13u
#define BODYLOADER_FAULT_NONE 0u
#define BODYLOADER_FAULT_MISSING_CACHE 1u
#define BODYLOADER_FAULT_PERSIST_REFUSE 2u
#define BODYLOADER_FAULT_BINARY_REFUSE 3u
typedef struct {
 uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];
} BodyLoaderIdentity;
typedef struct {
 uint32_t status,stage,entry_calls,shared_calls,acquire_calls,load_calls;
 uint32_t locate_calls,persist_calls,binary_calls,callback_calls,getter_count;
 uint32_t cache_hit,source_return,fixture_identity_matched,loaded_fields_verified;
 uint32_t struct_clear_calls,cleanup_complete;
} BodyLoaderReceipt;
/* Expected fixture labels must be independently measured by the qualifier;
 * matching these labels does not authenticate their runtime origin. All spans
 * are disjoint and stable through the digest. Snapshot commits only on complete
 * cache-hit execution/loaded-field comparison. A safe numeric receipt may change
 * on failure; invalid/aliased diagnostic storage remains unchanged.
 */
CohStatus sourceloader_apply(CohBytes,const BodyLoaderIdentity*,const BodyLoaderIdentity*,
 const CohCostumeImportDigest*,uint32_t,CohCostumeInput*,BodyLoaderReceipt*,size_t,size_t);
int sourceloader_is_idle(void);
#endif
'''
PREAMBLE=r'''
/* Exact source loader control flow; explicit fixture binary/platform bridges. */
#include "body-part-loader-provider.h"
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t U32;typedef uint8_t U8;typedef int bool;
#define false 0
#define true 1
typedef uint32_t StructTypeField;
typedef struct {int fixture_identity;} ParseTable;
typedef void DefineContext;
typedef void* FileList;
typedef struct {int updated;} ParserLoadInfo;
typedef int (*ParserLoadPreProcessFunc)(ParseTable*,void*);
typedef int (*ParserLoadPostProcessFunc)(ParseTable*,void*);
typedef int (*ParserLoadFinalProcessFunc)(ParseTable*,void*,bool);
typedef struct SharedMemoryHandle {int fixture_unused;} SharedMemoryHandle;
#define SHARED_MEMORY_PARAM
#define MAX_PATH 260
#define TOK_SERVER_ONLY 1u
#define TOK_CLIENT_ONLY 2u
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define PERFINFO_AUTO_STOP_START(a,b) ((void)0)
#define OUTPUT_DEBUG 0
#define OUTPUT_VERBOSE 1
#define TODO() ((void)0)
'''
GLOBALS=r'''
static ParseTable ParseBodyPartBegin[1]; /* Token/schema identity shell only. */
BodyPartList bodyPartList;
static char*lf_filemasks[16];static ParseTable*lf_pti;static void*lf_structptr;
static DefineContext*lf_globaldefines;static int lf_loadedok,lf_ignoreempty;
static int lf_loadedonefile,lf_forcebincreate;static FileList g_parselist;
static const char*parser_relpath;
static const char*g_StdAdditionalFilePrefixes[]={""};
static char oldmask_arena[MAX_PATH];
typedef struct{int fixture_token;}FixtureBin;
typedef FixtureBin*SimpleBufHandle;
typedef struct{
 int active;uint32_t fault,loaded_count;
 CohBytes bytes;const CohCostumeImportDigest*digest;BodyLoaderIdentity expected;
 size_t budget,retained;
 CohCostumeInputWorkspace workspace;CohCostumeInput cached;
 BodyPart parts[COH_COSTUME_INPUT_PART_MAX];
 const BodyPart*rows[COH_COSTUME_INPUT_PART_MAX];
 FixtureBin token;BodyLoaderReceipt receipt;
}LoaderState;
static LoaderState owner;
static void loader_wipe(void*p,size_t n){volatile unsigned char*c=p;while(n--)*c++=0;}
static void loader_step(uint32_t stage){if(owner.receipt.status==COH_OK)owner.receipt.stage=stage;}
static void loader_fail(CohStatus status,uint32_t stage){
 if(owner.receipt.status==COH_OK){owner.receipt.status=(uint32_t)status;owner.receipt.stage=stage;}
}
static void loader_unqualified(void){assert(!"unqualified source loader branch");abort();}
static int same(const char*a,const char*b){return a&&b&&!strcmp(a,b);}
static int scalar32(const void*p){int value;memcpy(&value,p,4);return value;}
static uint32_t raw32(const void*p){uint32_t value;memcpy(&value,p,4);return value;}
typedef char host_int32[(sizeof(int)==4)?1:-1];
typedef char host_bone32[(sizeof(BoneId)==4)?1:-1];
typedef char host_u8[(sizeof(U8)==1)?1:-1];
static int loader_ea_size(const void*where){
 assert(owner.active&&where==(const void*)&bodyPartList.bodyParts);
 assert(!owner.loaded_count||bodyPartList.bodyParts==owner.rows);
 return (int)owner.loaded_count;
}
#define eaSize(p) loader_ea_size((const void*)(p))
/* Source bp entry must pass this guarded preprocessor symbol in argument11.
 * The actual original ParseBoneNames is NOT executed on this cache-hit route. */
static bool ParseBoneNames(ParseTable*table,void*root){
 (void)table;(void)root;owner.receipt.callback_calls++;loader_unqualified();return 0;
}
static void loader_table(ParseTable*t){assert(t==ParseBodyPartBegin);}
#define TEST_PARSE_TABLE(p) loader_table(p)
static int isProductionMode(void){assert(owner.active);return 1;}
static void writeConsole(int level,const char*format,...){(void)level;(void)format;}
static void verbose_printf(const char*format,...){(void)format;}
static void Errorf(const char*format,...){(void)format;loader_unqualified();}
static void FatalErrorf(const char*format,...){(void)format;loader_unqualified();}
/* Original function-static old_filemask always refers to this permanent owned
 * arena. Its bytes are wiped at transaction end; no borrowed pointer escapes. */
static void loader_free(void*p){assert(!p||p==oldmask_arena);loader_wipe(oldmask_arena,sizeof(oldmask_arena));}
static char*loader_strdup(const char*s){assert(same(s,".bp"));memcpy(oldmask_arena,s,4);return oldmask_arena;}
static char*strtok_quoted(char*s,const char*a,const char*b){
 assert(same(a,";")&&same(b,";"));if(s){assert(s==oldmask_arena&&same(s,".bp"));return s;}return NULL;
}
static SM_AcquireResult sharedMemoryAcquire(SharedMemoryHandle**handle,const char*name){
 loader_step(BODYLOADER_STAGE_ACQUIRE);owner.receipt.acquire_calls++;
 assert(same(name,"SM_BodyParts.bin"));*handle=NULL;return SMAR_Error;
}
static char*fileLocateRead(const char*name,char*buffer){
 loader_step(BODYLOADER_STAGE_LOCATE);owner.receipt.locate_calls++;
 assert(same(name,"bin/BodyParts.bin"));
 if(owner.fault==BODYLOADER_FAULT_MISSING_CACHE){loader_fail(COH_UNSUPPORTED,BODYLOADER_STAGE_LOCATE);return NULL;}
 memcpy(buffer,name,18);return buffer;
}
static SimpleBufHandle ParserIsPersistNewer(const char*dir,const char*mask,const char*path,ParseTable*t,DefineContext*d){
 loader_step(BODYLOADER_STAGE_PERSIST);owner.receipt.persist_calls++;
 assert(same(dir,"Defs\\UI")&&same(mask,".bp")&&same(path,"bin/BodyParts.bin")&&t==ParseBodyPartBegin&&!d);
 if(owner.fault==BODYLOADER_FAULT_PERSIST_REFUSE){loader_fail(COH_UNSUPPORTED,BODYLOADER_STAGE_PERSIST);return NULL;}
 return &owner.token;
}
static int ParserReadBinaryFile(SimpleBufHandle file,char*name,ParseTable*t,void*root,FileList*list,DefineContext*d){
 loader_step(BODYLOADER_STAGE_BINARY);owner.receipt.binary_calls++;
 assert(file==&owner.token&&same(name,"bin/BodyParts.bin")&&t==ParseBodyPartBegin&&root==&bodyPartList&&!list&&!d);
 if(owner.fault==BODYLOADER_FAULT_BINARY_REFUSE){loader_fail(COH_UNSUPPORTED,BODYLOADER_STAGE_BINARY);return 0;}
 loader_step(BODYLOADER_STAGE_DECODE);
 CohStatus status=coh_costume_input_read(owner.bytes,COH_COSTUME_INPUT_BODY_PARTS,owner.expected.input_sha256,
  owner.digest,&owner.workspace,&owner.cached,owner.budget,owner.retained+sizeof(owner));
 if(status!=COH_OK){loader_fail(status,BODYLOADER_STAGE_DECODE);return 0;}
 /* Conservative fixture object profile: preserve every supported serialized
  * U8 exactly. The original full binary reader/BOOLFLAG narrowing is not here. */
 for(uint32_t i=0;i<owner.cached.part_count;i++)if(owner.cached.parts[i].dont_clear_word>255u){loader_fail(COH_LIMIT,BODYLOADER_STAGE_LOADED);return 0;}
 owner.loaded_count=owner.cached.part_count;
 for(uint32_t i=0;i<owner.loaded_count;i++){
  CohCostumeInputPart*in=owner.cached.parts+i;BodyPart*out=owner.parts+i;
  out->name=in->name;out->sourceFile=in->source_file;out->name_geo=in->geometry_name;
  out->name_tex=in->texture_name;out->base_var=in->base_name;
  out->num_parts=scalar32(&in->bone_count_last);out->influenceCost=scalar32(&in->influence_cost);
  memcpy(out->bone_num,&in->bones,sizeof(in->bones));out->bodyPartIndex=scalar32(&in->part_index);
  out->dont_clear=(U8)in->dont_clear_word;owner.rows[i]=out;
 }
 bodyPartList.bodyParts=owner.rows;owner.receipt.cache_hit=1;return 1;
}
static void StructClear(ParseTable*t,void*p){
 assert(t==ParseBodyPartBegin&&p==&bodyPartList);owner.receipt.struct_clear_calls++;
 bodyPartList.bodyParts=NULL;owner.loaded_count=0;
}
/* All following functions belong to excluded text/shared-generation profiles.
 * Their declarations only let the unchanged complete loader functions compile. */
static void FileListCreate(FileList*p){(void)p;loader_unqualified();}
static void FileListDestroy(FileList*p){(void)p;loader_unqualified();}
static int ParserLoadFile(const char*p,int empty){(void)p;(void)empty;loader_unqualified();return 0;}
static const char*allocAddString(const char*p){(void)p;loader_unqualified();return NULL;}
static char*addFilePrefix(const char*p,const char*s){(void)p;(void)s;loader_unqualified();return NULL;}
static int fileExists(const char*p){(void)p;loader_unqualified();return 0;}
static int ParserLoadCallback(char*p,void*data){(void)p;(void)data;loader_unqualified();return 0;}
static void fileScanAllDataDirs(const char*p,int(*callback)(char*,void*)){(void)p;(void)callback;loader_unqualified();}
static char*fileLocateWrite(const char*p,char*b){(void)p;(void)b;loader_unqualified();return NULL;}
static void mkdirtree(const char*p){(void)p;loader_unqualified();}
static int ParserWriteBinaryFile(const char*p,ParseTable*t,void*r,FileList*l,DefineContext*d,int v,StructTypeField flags){(void)p;(void)t;(void)r;(void)l;(void)d;(void)v;(void)flags;loader_unqualified();return 0;}
static void*sharedMemoryGetDataPtr(SharedMemoryHandle*h){(void)h;loader_unqualified();return NULL;}
static int ParseTableCRC(ParseTable*t,DefineContext*d){(void)t;(void)d;loader_unqualified();return 0;}
static void sharedMemorySetMode(SharedMemoryMode m){(void)m;loader_unqualified();}
static size_t StructGetMemoryUsage(ParseTable*t,void*p,size_t size){(void)t;(void)p;(void)size;loader_unqualified();return 0;}
static void sharedMemorySetSize(SharedMemoryHandle*h,size_t n){(void)h;(void)n;loader_unqualified();}
static void*sharedMemoryAlloc(SharedMemoryHandle*h,size_t n){(void)h;(void)n;loader_unqualified();return NULL;}
static void*StructCompress(ParseTable*t,void*p,size_t n,void*a,void*(*alloc)(void*,size_t),void*h){(void)t;(void)p;(void)n;(void)a;(void)alloc;(void)h;loader_unqualified();return NULL;}
static void sharedMemoryCommit(SharedMemoryHandle*h){(void)h;loader_unqualified();}
static void sharedMemoryUnlock(SharedMemoryHandle*h){(void)h;loader_unqualified();}
static void sharedHeapMemoryManagerLock(void){loader_unqualified();}
static void sharedHeapMemoryManagerUnlock(void){loader_unqualified();}
'''
OBSERVE_LOAD=r'''
#undef free
#undef strdup
static bool observed_ParserLoadFiles(const char*dir,const char*mask,const char*persist,int flags,
 ParseTable*t,void*root,DefineContext*d,ParserLoadInfo*info,ParserLoadPreProcessFunc pre){
 loader_step(BODYLOADER_STAGE_LOAD);owner.receipt.load_calls++;
 assert(same(dir,"Defs\\UI")&&same(mask,".bp")&&same(persist,"BodyParts.bin")&&!flags&&
  t==ParseBodyPartBegin&&root==&bodyPartList&&!d&&!info&&pre==ParseBoneNames);
 return ParserLoadFiles(dir,mask,persist,flags,t,root,d,info,pre);
}
#define ParserLoadFiles observed_ParserLoadFiles
'''
OBSERVE_SHARED=r'''
#undef ParserLoadFiles
static bool observed_ParserLoadFilesShared(const char*shared,const char*dir,const char*mask,const char*persist,int flags,
 ParseTable*t,void*root,size_t size,DefineContext*d,ParserLoadInfo*info,ParserLoadPreProcessFunc pre,
 ParserLoadPostProcessFunc post,ParserLoadFinalProcessFunc final){
 loader_step(BODYLOADER_STAGE_SHARED);owner.receipt.shared_calls++;
 assert(same(shared,"SM_BodyParts.bin")&&same(dir,"Defs\\UI")&&same(mask,".bp")&&same(persist,"BodyParts.bin")&&!flags&&
  t==ParseBodyPartBegin&&root==&bodyPartList&&size==sizeof(BodyPartList)&&!d&&!info&&pre==ParseBoneNames&&!post&&!final);
 int result=ParserLoadFilesShared(shared,dir,mask,persist,flags,t,root,size,d,info,pre,post,final);
 owner.receipt.source_return=(uint32_t)result;return result;
}
#define ParserLoadFilesShared observed_ParserLoadFilesShared
'''
WRAPPER=r'''
#undef ParserLoadFilesShared
typedef struct{const void*p;size_t n;}LoaderSpan;
static int valid_span(LoaderSpan s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(LoaderSpan a,LoaderSpan b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static int all_zero(const void*p,size_t n){const unsigned char*c=p;for(size_t i=0;i<n;i++)if(c[i])return 0;return 1;}
int sourceloader_is_idle(void){
 if(!all_zero(&owner,sizeof(owner))||bodyPartList.bodyParts||lf_pti||lf_structptr||lf_globaldefines||lf_loadedok||lf_ignoreempty||lf_loadedonefile||lf_forcebincreate||g_parselist||parser_relpath)return 0;
 return all_zero(lf_filemasks,sizeof(lf_filemasks))&&all_zero(oldmask_arena,sizeof(oldmask_arena));
}
static void finish_cleanup(void){
 bodyPartList.bodyParts=NULL;lf_pti=NULL;lf_structptr=NULL;lf_globaldefines=NULL;
 lf_loadedok=lf_ignoreempty=lf_loadedonefile=lf_forcebincreate=0;g_parselist=NULL;parser_relpath=NULL;
 loader_wipe(lf_filemasks,sizeof(lf_filemasks));loader_wipe(oldmask_arena,sizeof(oldmask_arena));loader_wipe(&owner,sizeof(owner));
}
static int loaded_fields(void){
 if(bodyPartList.bodyParts!=owner.rows||GetBodyPartCount()!=(int)owner.cached.part_count)return 0;
 owner.receipt.getter_count=(uint32_t)GetBodyPartCount();
 for(uint32_t i=0;i<owner.loaded_count;i++){
  const BodyPart*p=bodyPartList.bodyParts[i];const CohCostumeInputPart*q=owner.cached.parts+i;
  if(p!=owner.parts+i||!same(p->name,q->name)||!same(p->sourceFile,q->source_file)||
     !same(p->name_geo,q->geometry_name)||!same(p->name_tex,q->texture_name)||!same(p->base_var,q->base_name)||
     raw32(&p->num_parts)!=q->bone_count_last||raw32(&p->influenceCost)!=q->influence_cost||
     raw32(&p->bone_num[0])!=q->bones[0]||raw32(&p->bone_num[1])!=q->bones[1]||
     raw32(&p->bodyPartIndex)!=q->part_index||p->dont_clear!=q->dont_clear_word)return 0;
  owner.receipt.loaded_fields_verified++;
 }
 return 1;
}
CohStatus sourceloader_apply(CohBytes bytes,const BodyLoaderIdentity*observed,const BodyLoaderIdentity*expected,
 const CohCostumeImportDigest*digest,uint32_t fault,CohCostumeInput*out,BodyLoaderReceipt*receipt,size_t budget,size_t retained){
 if(!bytes.data||!bytes.size||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 LoaderSpan span[7]={{bytes.data,bytes.size},{observed,sizeof(*observed)},{expected,sizeof(*expected)},
  {digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid_span(span[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(span[i],span[j]))return COH_INVALID;}
 span[6]=(LoaderSpan){digest->context,digest->context_bytes};
 if(!valid_span(span[6]))return COH_INVALID;
 for(unsigned j=0;j<6;j++)if(!apart(span[6],span[j]))return COH_INVALID;
 BodyLoaderReceipt result;memset(&result,0,sizeof(result));result.stage=BODYLOADER_STAGE_INPUT;result.cleanup_complete=(uint32_t)sourceloader_is_idle();
 CohStatus status=COH_OK;
 if(!result.cleanup_complete)status=COH_STATE;
 else if(bytes.size>COH_COSTUME_INPUT_BYTES_MAX||!budget||budget>COH_COSTUME_INPUT_BUDGET_MAX)status=COH_LIMIT;
 else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+COH_COSTUME_INPUT_STACK_RESERVE;
 if(status==COH_OK){for(unsigned i=0;i<7;i++){if(span[i].n>budget||charge>budget-span[i].n){status=COH_LIMIT;break;}charge+=span[i].n;}}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.stage=BODYLOADER_STAGE_IDENTITY;
 const unsigned char*ids=(const unsigned char*)expected;
 for(unsigned i=0;i<5;i++)if(all_zero(ids+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK){result.status=(uint32_t)status;*receipt=result;return status;}
 result.fixture_identity_matched=1;result.stage=BODYLOADER_STAGE_PROFILE;
 if(fault>BODYLOADER_FAULT_BINARY_REFUSE){result.status=COH_UNSUPPORTED;*receipt=result;return COH_UNSUPPORTED;}
 owner.active=1;owner.fault=fault;owner.bytes=bytes;owner.digest=digest;owner.expected=*expected;
 owner.budget=budget;owner.retained=retained;owner.receipt=result;owner.receipt.cleanup_complete=0;
 loader_step(BODYLOADER_STAGE_ENTRY);owner.receipt.entry_calls++;
 bpReadBodyPartFiles();
 if(owner.receipt.status==COH_OK){
  if(!owner.receipt.source_return||!owner.receipt.cache_hit){loader_fail(COH_UNSUPPORTED,BODYLOADER_STAGE_LOADED);}
  else {loader_step(BODYLOADER_STAGE_LOADED);if(!loaded_fields())loader_fail(COH_STATE,BODYLOADER_STAGE_LOADED);}
 }
 if(owner.receipt.status==COH_OK)loader_step(BODYLOADER_STAGE_COMPLETE);
 result=owner.receipt;status=(CohStatus)result.status;
 if(status==COH_OK)*out=owner.cached;
 finish_cleanup();result.cleanup_complete=(uint32_t)sourceloader_is_idle();*receipt=result;loader_wipe(&result,sizeof(result));
 return status;
}
'''

def build(root,work):
 root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 pin_path=HERE/'body-part-loader-source-pins.json';pins=json.loads(pin_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('body loader source pin changed: '+name)
  frozen[name]=raw
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()}
 enum=re.search(r'typedef\s+enum\s+BoneId\s*\{.*?\}\s*BoneId\s*;',text[BONES_H],re.S)[0]
 body=re.search(r'typedef struct BodyPart\s*\{.*?\}\s*BodyPart\s*;',text[BODY_H],re.S)[0]
 listing=re.search(r'typedef struct\s*\{\s*const BodyPart\*\* bodyParts;\s*\}\s*BodyPartList\s*;',text[BODY_H],re.S)[0]
 shared_enum=re.search(r'typedef enum SM_AcquireResult\s*\{.*?\}\s*SM_AcquireResult\s*;',text[SHARED_H],re.S)[0]
 mode_enum=re.search(r'typedef enum SharedMemoryMode\s*\{.*?\}\s*SharedMemoryMode\s*;',text[SHARED_H],re.S)[0]
 xcase=re.search(r'^#define\s+xcase\s+break;case\s*$',text[STDTYPES_H],re.M)
 if not xcase:raise ValueError('original xcase control-flow macro changed')
 plfs=re.search(r'typedef struct PLFSHeader\s*\{.*?\}\s*PLFSHeader\s*;',text[PARSER_C],re.S)[0]
 flags='\n'.join(line for line in text[PARSER_H].splitlines()if re.match(r'#define\s+PARSER_[A-Z]+\s',line))
 functions={name:extract(text[path],name)for path,names in((BODY_C,('bpReadBodyPartFiles','GetBodyPartCount')),(PARSER_C,('ParserLoadFiles','ParserLoadFilesShared','sharedMemoryAllocAdapter')))for name in names}
 callback=extract(text[BODY_C],'ParseBoneNames')
 header=work/'body-part-loader-provider.h';header.write_text(HEADER)
 code=PREAMBLE+xcase[0]+'\n'+enum+'\n'+body+'\n'+listing+'\n'+shared_enum+'\n'+mode_enum+'\n'+plfs+'\n'+flags+'\n'+GLOBALS
 code+='\n#define free loader_free\n#define strdup loader_strdup\n'+functions['ParserLoadFiles']+OBSERVE_LOAD+functions['sharedMemoryAllocAdapter']+functions['ParserLoadFilesShared']+OBSERVE_SHARED+functions['bpReadBodyPartFiles']+'\n#undef ParserLoadFilesShared\n'+functions['GetBodyPartCount']+WRAPPER
 generated=work/'body-part-loader-provider.c';generated.write_text(code)
 if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('original loader sources changed during emission')
 proof={'schema':'coh-original-body-part-loader-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':{name:sha(raw)for name,raw in frozen.items()},'source_pins_sha256':sha(pin_path.read_bytes()),'source_stable_before_after':True,'whole_function_sha256_lf':{name:sha(value.encode())for name,value in functions.items()},'unexecuted_actual_ParseBoneNames_sha256_lf':sha(callback.encode()),'source_entry_tuple':['SM_BodyParts.bin','Defs\\UI','.bp','BodyParts.bin',0,'ParseBodyPartBegin','&bodyPartList','sizeof(BodyPartList)','NULL','NULL','ParseBoneNames','NULL','NULL'],'controlled_shared_branch':'SMAR_Error only; explicit sharedMemoryAcquire adapter, never current Map selection','controlled_cache_branch':'production mode, forcebincreate0, valid persist path -> native binary bridge returns1; original source returns before text/preprocessor','native_binary_bridge':'Unchanged coh_costume_input_read verifies complete exact bytes/header/digest into owned DTO; NOT original ParserReadBinaryFile/ParserIsPersistNewer/ParseTableCRC/Serialize or full engine loader','full_original_BodyPart_declarations':True,'loaded_field_profile':'All5strings/finalBoneCount/influence/rawbones/index/order copied to full source fields and compared. First duplicate BoneCount remains DTO-only. U8 dont_clear requires raw<=255; wider words explicitly refuse profile, not source grammar. Signed32 fields use bitcopy with host int/BoneId size assertions.','callback_symbol_adapter':'Guarded ParseBoneNames symbol validates entry tuple identity and traps if invoked; actual callback/generation not required on exact hit and not executed','source_static_lifetime':'Original old_filemask pointer persists to permanent fixture-owned arena; bytes/global borrowed metadata are wiped after each normal return. No heap allocation/borrowed pointer retained. Original recursive_call reset is exercised through normal source hit/failure returns, never longjmp.','unqualified_profiles':'Shared first/data reuse/CRC/StructCompress and text/fallback/writing trap; wrong requested profile refuses before source entry. Production cache miss/read refusal executes original StructClear/failure return.','budget':'Existing <=1MiB input-reader aggregate budget covers fixed owner, caller spans, stack16KiB, digest scratch/context and retained bytes; underlying reader conservatively also charges owner bytes. No original global/device/compiler RSS bound.','fixture_identity_scope':'Source/input/build/profile/run labels must be independently measured by qualifier; equality and input digest bind only this fixture transaction, not current server consumption or generation.','original_binary_reader_executed':False,'original_preprocessor_executed':False,'current_Map_runtime_observed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{'loader_header':str(header),'loader_provider':str(generated)}}
 proof['original_xcase_control_flow']={'path':STDTYPES_H,'macro_sha256_lf':sha(xcase[0].encode()),'exact_semantics':'break;case','source_macro_extracted_unchanged':True}
 return generated,proof
