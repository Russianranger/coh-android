"""Bounded original ParseBoneNames execution with the accepted enum provider.

This is a source callback qualification fixture, not a runtime body catalog.
The caller supplies individually qualified input rows; no Parse6 loader or
MapServer runtime/generation is admitted by this provider.
"""
from pathlib import Path
import hashlib,importlib.util,json,re

HERE=Path(__file__).resolve().parent
BODY_C='upstream/ouroboros/Common/gameData/BodyPart.c'
BODY_H='upstream/ouroboros/Common/gameData/BodyPart.h'
COSTUME_H='upstream/ouroboros/Common/entity/costume.h'
PART_MAX=29
SINGLE_NAME_MAX=259
PAIRED_NAME_MAX=126

def sha(value):return hashlib.sha256(value).hexdigest()

HEADER=r'''/* Bounded source callback fixture API; no runtime catalog or authority. */
#ifndef COH_PARSE_BONE_NAMES_PROVIDER_H
#define COH_PARSE_BONE_NAMES_PROVIDER_H
#include <stddef.h>
#include <stdint.h>
#define SOURCEPARTS_OK 0
#define SOURCEPARTS_INVALID 1
#define SOURCEPARTS_LIMIT 3
#define SOURCEPARTS_STATE 4
#define SOURCEPARTS_PART_MAX 29u
#define SOURCEPARTS_SINGLE_NAME_MAX 259u
#define SOURCEPARTS_PAIRED_NAME_MAX 126u
typedef struct {
 const unsigned char *name_geo;size_t name_bytes;
 int32_t num_parts,bone_num[2],part_index;
} SourcePartInput;
typedef struct {int32_t bone_num[2],part_index;} SourcePartOutput;
typedef struct {
 /* source_count is original GetBodyPartCount over owned fixture rows only;
  * it is never a genuine current MapServer/default catalog count. */
 uint32_t callback_executed,callback_return,count,lookup_calls,source_count;
} SourcePartsReceipt;
/* Fixed source qualification profile: non-NULL inputs/output even for count0;
 * all row/name and output/receipt spans disjoint; association must1. Preflight
 * completes before ANY original mutation; refusal changes no caller storage.
 * Unknown/sentinel bone results are retained exactly, never validity filtered.
 */
int sourceparts_apply(const SourcePartInput *,size_t,uint32_t,
 SourcePartOutput *,SourcePartsReceipt *);
int sourceparts_is_idle(void);
#endif
'''

GLUE_BEFORE=r'''
/* Explicit host adapters, not the original earray allocation/Win32 ABI. */
typedef unsigned char U8;
typedef int bool;
typedef void ParseTable;
#define cpp_const_cast(type) (type)
'''

ADAPTER=r'''
BodyPartList bodyPartList;
static const BodyPart **sourceparts_active_rows;
static size_t sourceparts_active_count;
static uint32_t sourceparts_lookup_calls;
static int sourceparts_ea_size(const void *address){
 assert(address==(const void*)&bodyPartList.bodyParts);
 assert(bodyPartList.bodyParts==sourceparts_active_rows);
 assert(sourceparts_active_count<=SOURCEPARTS_PART_MAX);
 return (int)sourceparts_active_count;
}
#define eaSize(address) sourceparts_ea_size((const void*)(address))
static BoneId sourceparts_observed_lookup(const char *name){
 assert(sourceparts_active_rows&&sourceparts_lookup_calls<2u*SOURCEPARTS_PART_MAX);
 sourceparts_lookup_calls++;return bone_IdFromName(name);
}
#define bone_IdFromName sourceparts_observed_lookup
'''

WRAPPER=r'''
#undef bone_IdFromName
static void sourceparts_wipe(void*storage,size_t bytes){
 volatile unsigned char*cursor=(volatile unsigned char*)storage;
 while(bytes--)*cursor++=0;
}
static int sourceparts_overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
int sourceparts_is_idle(void){
 return !bodyPartList.bodyParts&&!sourceparts_active_rows&&
  !sourceparts_active_count&&!sourceparts_lookup_calls;
}
int sourceparts_apply(const SourcePartInput*input,size_t count,uint32_t association,
 SourcePartOutput*out,SourcePartsReceipt*receipt){
 if(!input||!out||!receipt)return SOURCEPARTS_INVALID;
 if(count>SOURCEPARTS_PART_MAX)return SOURCEPARTS_LIMIT;
 size_t input_bytes=count*sizeof(*input),output_bytes=count*sizeof(*out);
 if(sourceparts_overlap(input,input_bytes,out,output_bytes)||
    sourceparts_overlap(input,input_bytes,receipt,sizeof(*receipt))||
    sourceparts_overlap(out,output_bytes,receipt,sizeof(*receipt)))return SOURCEPARTS_INVALID;
 if(association!=1||!sourceparts_is_idle())return SOURCEPARTS_STATE;
 for(size_t i=0;i<count;i++){
  const SourcePartInput*p=input+i;
  if(p->num_parts!=1&&p->num_parts!=2)return SOURCEPARTS_INVALID;
  size_t maximum=p->num_parts==2?SOURCEPARTS_PAIRED_NAME_MAX:SOURCEPARTS_SINGLE_NAME_MAX;
  if(p->name_bytes>maximum)return SOURCEPARTS_LIMIT;
  if(!p->name_geo||sourceparts_overlap(p->name_geo,p->name_bytes,input,input_bytes)||
     sourceparts_overlap(p->name_geo,p->name_bytes,out,output_bytes)||
     sourceparts_overlap(p->name_geo,p->name_bytes,receipt,sizeof(*receipt)))return SOURCEPARTS_INVALID;
  for(size_t j=0;j<p->name_bytes;j++)if(!p->name_geo[j]||p->name_geo[j]>127)return SOURCEPARTS_INVALID;
 }
 /* Full source structs are owned here; no input alias or original heap escapes.
  * These fixed arrays are the explicit replacement for original earray storage.
  */
 BodyPart owned[SOURCEPARTS_PART_MAX];const BodyPart*rows[SOURCEPARTS_PART_MAX];
 char names[SOURCEPARTS_PART_MAX][SOURCEPARTS_SINGLE_NAME_MAX+1u];
 SourcePartOutput candidate[SOURCEPARTS_PART_MAX];SourcePartsReceipt result;
 memset(owned,0,sizeof(owned));memset(rows,0,sizeof(rows));memset(names,0,sizeof(names));
 memset(candidate,0,sizeof(candidate));memset(&result,0,sizeof(result));
 for(size_t i=0;i<count;i++){
  memcpy(names[i],input[i].name_geo,input[i].name_bytes);
  owned[i].name=names[i];owned[i].name_geo=names[i];owned[i].num_parts=input[i].num_parts;
  owned[i].bone_num[0]=(BoneId)input[i].bone_num[0];owned[i].bone_num[1]=(BoneId)input[i].bone_num[1];
  owned[i].bodyPartIndex=input[i].part_index;rows[i]=owned+i;
 }
 sourceparts_active_rows=rows;sourceparts_active_count=count;sourceparts_lookup_calls=0;
 bodyPartList.bodyParts=rows;
 int value=ParseBoneNames(NULL,&bodyPartList);
 result.callback_executed=1;result.callback_return=(uint32_t)value;result.count=(uint32_t)count;
 result.lookup_calls=sourceparts_lookup_calls;result.source_count=(uint32_t)GetBodyPartCount();
 for(size_t i=0;i<count;i++){
  candidate[i].bone_num[0]=(int32_t)owned[i].bone_num[0];
  candidate[i].bone_num[1]=(int32_t)owned[i].bone_num[1];
  candidate[i].part_index=owned[i].bodyPartIndex;
 }
 bodyPartList.bodyParts=NULL;sourceparts_active_rows=NULL;sourceparts_active_count=0;sourceparts_lookup_calls=0;
 sourceparts_wipe(owned,sizeof(owned));sourceparts_wipe(rows,sizeof(rows));sourceparts_wipe(names,sizeof(names));
 memcpy(out,candidate,output_bytes);*receipt=result;
 sourceparts_wipe(candidate,sizeof(candidate));sourceparts_wipe(&result,sizeof(result));
 return SOURCEPARTS_OK;
}
'''

def build(root,work):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    pins_path=HERE/'parse-bone-names-source-pins.json';pins=json.loads(pins_path.read_text());frozen={}
    for name,pin in pins['files'].items():
        raw=(root/name).read_bytes()
        if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('callback prerequisite pin changed: '+name)
        frozen[name]=raw
    def verify():
        if any((root/name).read_bytes()!=raw for name,raw in frozen.items()):raise ValueError('callback source changed during generation')
    accepted_path=HERE/'bone_enum_provider.py';spec=importlib.util.spec_from_file_location('accepted_bone_enum_dependency',accepted_path);accepted=importlib.util.module_from_spec(spec);spec.loader.exec_module(accepted)
    enum_c,enum_proof,reference=accepted.build(root,work/'enum-provider');verify()
    texts={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()}
    body=re.search(r'typedef struct BodyPart\s*\{.*?\}\s*BodyPart\s*;',texts[BODY_H],re.S)
    listing=re.search(r'typedef struct\s*\{\s*const BodyPart\*\* bodyParts;\s*\}\s*BodyPartList\s*;',texts[BODY_H],re.S)
    maximum=re.search(r'^#define\s+MAX_COSTUME_PARTS\s+([0-9]+)\s*$',texts[COSTUME_H],re.M)
    alias=re.search(r'^#define\s+MAX_BODYPARTS\s+MAX_COSTUME_PARTS\s*$',texts[BODY_H],re.M)
    if not body or not listing or not maximum or not alias:raise ValueError('original callback declarations/constants changed')
    if PART_MAX>=int(maximum[1]):raise ValueError('callback profile exceeds original source count bound')
    callback=accepted.extract(texts[BODY_C],'ParseBoneNames');getter=accepted.extract(texts[BODY_C],'GetBodyPartCount')
    if 'char tmp[128]'not in callback or callback.count('bone_IdFromName(')!=3:raise ValueError('original callback lookup/buffer profile changed')
    header=work/'parse-bone-names-provider.h';header.write_text(HEADER)
    code=Path(enum_c).read_text()+'\n#include "parse-bone-names-provider.h"\n'+GLUE_BEFORE+'\n'+maximum[0]+'\n'+alias[0]+'\n'+body[0]+'\n'+listing[0]+'\n'+ADAPTER+callback+getter+WRAPPER
    provider=work/'parse-bone-names-provider.c';provider.write_text(code);verify()
    source_hashes={**enum_proof['source_sha256'],**{name:sha(raw)for name,raw in frozen.items()}}
    proof={'schema':'coh-original-parse-bone-names-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':source_hashes,'source_pins_sha256':sha(pins_path.read_bytes()),'source_stable_before_after':True,'accepted_enum_provider':enum_proof,'original_declaration_sha256_lf':{'BodyPart':sha(body[0].encode()),'BodyPartList':sha(listing[0].encode()),'MAX_BODYPARTS_alias':sha(alias[0].encode()),'MAX_COSTUME_PARTS':sha(maximum[0].encode())},'whole_function_sha256_lf':{'ParseBoneNames':sha(callback.encode()),'GetBodyPartCount':sha(getter.encode())},'original_callback_source_count_max_exclusive':int(maximum[1]),'wrapper_part_max_policy':PART_MAX,'paired_name_max':PAIRED_NAME_MAX,'paired_buffer_arithmetic':'126 bytes + R/L suffix1 + NUL1 = original tmp128;127 bytes refuses before original callback','single_name_max_policy':SINGLE_NAME_MAX,'source_unknown_minus_one_and_sentinels_preserved':True,'single_part_second_bone_preserved':True,'full_original_BodyPart_and_BodyPartList_declarations':True,'host_adapters':['U8=unsigned char; bool=int; opaque unused ParseTable; cpp_const_cast C cast','Fixed29 owned full BodyPart rows, pointer array and 260-byte name buffers replace original earray allocation; eaSize checks global/argument ownership metadata','Observed lookup wrapper calls unchanged actual bone_IdFromName once; callback source text unchanged','Original source MAX_BODYPARTS=MAX_COSTUME_PARTS60;29 is only this qualification/native profile limit','Original fatal branches unreachable after complete bounded preflight; source bone-validity checks are commented out, so no new validity filter','Accepted enum provider three-field aliasing/platform adapters and -fno-strict-aliasing remain required'],'original_callback_executed_by_provider_build':False,'original_full_parser_executed':False,'current_Map_runtime_observed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{**{'enum_'+name:path for name,path in enum_proof['evidence_paths'].items()},'callback_header':str(header),'callback_provider':str(provider)}}
    proof['source_count_scope']='Original GetBodyPartCount executes over adapter-owned callback rows only; this is not a genuine current MapServer or costume default part count.'
    proof['neutral_owned_field_profile']='Exact full BodyPart declarations are retained, but input carries only callback-relevant fields. Unused owned fields remain neutral zero; diagnostic name aliases the owned geometry name. No full-record roundtrip or original ABI is claimed.'
    proof['cleanup']='Original global/list metadata reset before output commit; owned row/pointer/name/candidate/receipt staging is cleared through volatile byte stores. No input pointer survives.'
    return provider,proof,reference
