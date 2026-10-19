"""Original BodyPart destruction over bounded owned reader arenas.

The accepted loader is immutable. This emitter replaces its safe clear shell
only in a new independently qualified composition; allocator ABI is a shell.
"""
from pathlib import Path
import hashlib,json,re
import cache_hit_loader_provider as accepted
HERE=Path(__file__).resolve().parent
sha=accepted.sha
once=accepted.once

DECLARATIONS=r'''
typedef void(*destroy_f)(ParseTable*,int,void*,int);
void StructClear(ParseTable*,void*);
void string_destroystruct(ParseTable*,int,void*,int);
void struct_destroystruct(ParseTable*,int,void*,int);
void nonarray_destroystruct(ParseTable*,int,void*,int);
void earray_destroystruct(ParseTable*,int,void*,int);
const void*TokenStoreGetPointerConst(ParseTable*,int,const void*,int);
void*TokenStoreGetPointer(ParseTable*,int,void*,int);
void TokenStoreFreeString(ParseTable*,int,void*,int);
void TokenStoreFree(ParseTable*,int,void*,int);
void TokenStoreDestroyEArray(ParseTable*,int,void*);
int TokenStoreGetNumElems(ParseTable*,int,const void*);
'''
EXTRA_HEADER=r'''
/* No pointer-bearing request or borrowed storage is admitted. present=0 keeps
 * a partial earray slot NULL; string_mask chooses the five original strings.
 * Every selected string is owned even when its length is zero. pool/borrowed
 * and unsupported storage modes refuse before any original code executes. */
typedef struct{uint32_t present,string_mask,length[5];}StructClearRow;
typedef struct{uint32_t count,array_present,reserve_fault,borrowed;StructClearRow rows[30];}StructClearRequest;
typedef struct{uint32_t rows,strings,arrays,order_count,order[30],numeric_preserved,root_null,repeat_no_releases;}StructClearFixtureResult;
CohStatus struct_clear_fixture(const StructClearRequest*,const StructClearIdentity*,const StructClearIdentity*,const CohCostumeImportDigest*,StructClearFixtureResult*,StructClearReceipt*,size_t,size_t);
'''
SHELL=r'''
/* These releases retire only exact registered owned arena slots. They do not
 * invoke or qualify engine StructFree/StringFree, heap ownership or ea ABI. */
typedef struct{uint32_t nodes,strings,arrays,order_count,order[30],numeric_preserved,root_null,repeat_no_releases,node_mask,string_mask[30];}ClearState;
static ClearState clear_state;
static int clear_idle(void){return zeros(&clear_state,sizeof(clear_state));}
static int clear_easize(const void*p){
 assert(owner.active&&p==(const void*)&owner.root.bodyParts);
 assert(!owner.root.bodyParts||owner.root.bodyParts==owner.pointers);
 return owner.root.bodyParts?(int)owner.nodes:0;
}
#define eaSizeUnsafe(p) clear_easize((const void*)(p))
static int clear_ea32size(const void*p){(void)p;assert(!"BodyPart has no direct32 earray");return 0;}
#define ea32Size(p) clear_ea32size((const void*)(p))
static void StructFreeString(char*p){
 assert(owner.active&&p);int found=0;
 for(uint32_t n=0;n<owner.nodes;n++)for(uint32_t k=0;k<5;k++)if(p==owner.text[n][k]){
  for(uint32_t later=n+1;later<owner.nodes;later++)assert(!owner.pointers[later]);
  BodyPart*row=&owner.parts[n];char*fields[5]={row->name,row->sourceFile,row->name_geo,row->name_tex,row->base_var};
  for(uint32_t earlier=0;earlier<k;earlier++)assert(!fields[earlier]);
  assert(!(clear_state.string_mask[n]&(1u<<k)));clear_state.string_mask[n]|=1u<<k;
  clear_state.strings++;body_wipe(owner.text[n][k],sizeof(owner.text[n][k]));found++;
 }
 assert(found==1);
}
static void StructFree(void*p){
 assert(owner.active&&p);uint32_t n=part_index(p);assert(!(clear_state.node_mask&(1u<<n)));
 for(uint32_t later=n+1;later<owner.nodes;later++)assert(!owner.pointers[later]);
 BodyPart*row=p;assert(!row->name&&!row->sourceFile&&!row->name_geo&&!row->name_tex&&!row->base_var);
 uint32_t words[6];memcpy(words,&row->num_parts,4);memcpy(words+1,&row->influenceCost,4);memcpy(words+2,row->bone_num,8);memcpy(words+4,&row->bodyPartIndex,4);words[5]=row->dont_clear;
 assert(words[0]==owner.raw[n][2]&&words[1]==owner.raw[n][1]&&words[2]==owner.raw[n][4]&&words[3]==owner.raw[n][5]&&words[4]==owner.raw[n][6]&&words[5]==(owner.raw[n][3]&255u));
 clear_state.numeric_preserved++;clear_state.node_mask|=1u<<n;clear_state.order[clear_state.order_count++]=n;clear_state.nodes++;
 body_wipe(p,sizeof(BodyPart));body_wipe(words,sizeof(words));
}
static void clear_eadestroy(void*p){
 assert(owner.active&&p==(void*)&owner.root.bodyParts);
 if(owner.root.bodyParts){assert(owner.root.bodyParts==owner.pointers);for(uint32_t i=0;i<owner.nodes;i++)assert(!owner.pointers[i]);clear_state.arrays++;}
 body_wipe(owner.pointers,sizeof(owner.pointers));owner.root.bodyParts=NULL;clear_state.root_null=1;
}
#define eaDestroy(p) clear_eadestroy((void*)(p))
static void clear_ea32destroy(void*p){(void)p;assert(!"BodyPart has no direct32 earray");}
#define ea32Destroy(p) clear_ea32destroy((void*)(p))
static void clear_receipt(void){
 owner.receipt.clear_nodes=clear_state.nodes;owner.receipt.clear_strings=clear_state.strings;owner.receipt.clear_arrays=clear_state.arrays;
 owner.receipt.clear_order_count=clear_state.order_count;memcpy(owner.receipt.clear_order,clear_state.order,sizeof(clear_state.order));
 owner.receipt.clear_numeric_preserved=clear_state.numeric_preserved;owner.receipt.clear_root_null=clear_state.root_null;
}
static void observed_StructClear(ParseTable*t,void*r){
 assert(owner.active&&!owner.opened&&!parser_relpath&&t==ParseBodyPartBegin&&r==&owner.root);
 loader_trace(13);owner.receipt.struct_clear_calls++;StructClear(t,r);
}
'''
FIXTURE=r'''
CohStatus struct_clear_fixture(const StructClearRequest*request,const StructClearIdentity*observed,const StructClearIdentity*expected,const CohCostumeImportDigest*digest,StructClearFixtureResult*out,StructClearReceipt*receipt,size_t budget,size_t retained){
 if(!request||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 BodySpan spans[7]={{request,sizeof(*request)},{observed,sizeof(*observed)},{expected,sizeof(*expected)},{digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid_span(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(BodySpan){digest->context,digest->context_bytes};if(!valid_span(spans[6]))return COH_INVALID;
 for(unsigned j=0;j<6;j++)if(!apart(spans[6],spans[j]))return COH_INVALID;
 StructClearReceipt r;memset(&r,0,sizeof(r));r.stage=1;r.cleanup_complete=(uint32_t)struct_clear_is_idle();CohStatus status=COH_OK;
 if(!r.cleanup_complete)status=COH_STATE;else if(!budget||budget>1048576u)status=COH_LIMIT;else if(!digest->sha256)status=COH_STATE;
 size_t charge=struct_clear_owner_bytes()+98304u;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK)goto refused;
 r.stage=2;for(unsigned i=0;i<5;i++)if(zeros((const unsigned char*)expected+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK)goto refused;
 r.fixture_identity_matched=1;
 r.stage=3;if(request->count>30){status=COH_LIMIT;goto refused;}
 if(request->array_present>1||request->borrowed||request->reserve_fault>1||(!request->array_present&&request->count)){status=COH_UNSUPPORTED;goto refused;}
 for(uint32_t i=0;i<request->count;i++){
  const StructClearRow*row=&request->rows[i];if(row->present>1||row->string_mask>31){status=COH_UNSUPPORTED;goto refused;}
  for(unsigned k=0;k<5;k++)if(row->length[k]>=260){status=COH_LIMIT;goto refused;}
 }
 r.stage=14;uint8_t hash[32];memset(hash,0,sizeof(hash));status=digest->sha256(digest->context,(CohBytes){(const unsigned char*)request,sizeof(*request)},hash);
 if(status==COH_OK&&memcmp(hash,expected->input_sha256,32))status=COH_STATE;
 body_wipe(hash,sizeof(hash));if(status!=COH_OK)goto refused;
 if(request->reserve_fault){r.stage=17;status=COH_LIMIT;goto refused;}
 owner.active=1;owner.nodes=request->count;owner.capacity=request->count;owner.root.bodyParts=request->array_present?owner.pointers:NULL;
 for(uint32_t n=0;n<request->count;n++)if(request->rows[n].present){
  BodyPart*row=&owner.parts[n];owner.pointers[n]=row;const StructClearRow*input=&request->rows[n];
  char**fields[5]={&row->name,&row->sourceFile,&row->name_geo,&row->name_tex,&row->base_var};
  for(unsigned k=0;k<5;k++)if(input->string_mask&(1u<<k)){memset(owner.text[n][k],(int)('A'+n%26),input->length[k]);*fields[k]=owner.text[n][k];}
  for(unsigned k=0;k<7;k++)owner.raw[n][k]=0x80000000u+n*17u+k;
  row->num_parts=(int)owner.raw[n][2];row->influenceCost=(int)owner.raw[n][1];memcpy(row->bone_num,owner.raw[n]+4,8);memcpy(&row->bodyPartIndex,owner.raw[n]+6,4);row->dont_clear=(U8)owner.raw[n][3];
 }
 StructClear(ParseBodyPartBegin,&owner.root);ClearState first=clear_state;StructClear(ParseBodyPartBegin,&owner.root);
 clear_state.repeat_no_releases=(uint32_t)!memcmp(&first,&clear_state,sizeof(first));body_wipe(&first,sizeof(first));
 StructClearFixtureResult candidate;memset(&candidate,0,sizeof(candidate));candidate.rows=clear_state.nodes;candidate.strings=clear_state.strings;candidate.arrays=clear_state.arrays;candidate.order_count=clear_state.order_count;memcpy(candidate.order,clear_state.order,sizeof(candidate.order));candidate.numeric_preserved=clear_state.numeric_preserved;candidate.root_null=clear_state.root_null;candidate.repeat_no_releases=clear_state.repeat_no_releases;
 clear_receipt();r=owner.receipt;r.status=COH_OK;r.stage=18;r.fixture_identity_matched=1;body_wipe(&owner,sizeof(owner));body_wipe(&clear_state,sizeof(clear_state));r.cleanup_complete=(uint32_t)struct_clear_is_idle();r.crypto_cleanup_complete=1;
 assert(r.cleanup_complete);*out=candidate;*receipt=r;body_wipe(&candidate,sizeof(candidate));body_wipe(&r,sizeof(r));return COH_OK;
refused:r.status=(uint32_t)status;r.crypto_cleanup_complete=1;r.cleanup_complete=(uint32_t)struct_clear_is_idle();*receipt=r;body_wipe(&r,sizeof(r));return status;
}
'''

def build(root,work):
 root,work=Path(root).resolve(),Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 pins_path=HERE/'struct-clear-source-pins.json';pins=json.loads(pins_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('StructClear source pin changed '+name)
  frozen[name]=raw
 body=accepted.module('body_read_provider');path,proof=accepted.build(root,work);code=path.read_text();header=(work/'cache-hit-loader-provider.h').read_text()
 text={n:v.decode().replace('\r\n','\n')for n,v in frozen.items()}
 functions={n:body.extract(text[p],n)for p,ns in((body.PARSER_C,('StructClear','string_destroystruct','struct_destroystruct','nonarray_destroystruct','earray_destroystruct')),(body.TOKEN_C,('TokenStoreFreeString','TokenStoreFree','TokenStoreGetPointerConst','TokenStoreGetPointer','TokenStoreDestroyEArray','TokenStoreGetNumElems')))for n in ns}
 code=once(code,'typedef struct{readbin_f readbin;interpretfield_f interpretfield;}BodyHandler;',DECLARATIONS+'typedef struct{readbin_f readbin;interpretfield_f interpretfield;destroy_f destroystruct;}BodyHandler;')
 code=once(code,'static const BodyHandler g_arraytable[3]={{nonarray_readbin},{NULL},{earray_readbin}};','static const BodyHandler g_arraytable[3]={{nonarray_readbin,NULL,nonarray_destroystruct},{NULL,NULL,NULL},{earray_readbin,NULL,earray_destroystruct}};')
 table=re.search(r'TokenTypeInfo g_tokentable\[\]\s*=\s*\{.*?^};',text[body.INTERNAL_C],re.S|re.M)[0]
 mappings={}
 for token,want in(('TOK_END','0'),('TOK_INT_X','0'),('TOK_STRING_X','string_destroystruct'),('TOK_CURRENTFILE_X','string_destroystruct'),('TOK_BOOLFLAG_X','0'),('TOK_STRUCT_X','struct_destroystruct')):
  row=re.search(r'\{\s*'+token+r',.*?^\s*},',table,re.S|re.M)[0];fields=re.sub(r'//[^\n]*','',row[1:]).split(',');actual=fields[10].strip()
  if actual!=want:raise ValueError('Original destructor dispatch changed '+token)
  mappings[token]=actual
  code=re.sub(r'(\['+token+r'\]=\{[^{}]*)\}',lambda m:m[1]+','+('NULL'if actual=='0'else actual)+'}',code,count=1)
 array_table=re.search(r'TokenArrayInfo g_arraytable\[3\]\s*=\s*\{.*?^};',text[body.INTERNAL_C],re.S|re.M)[0]
 rows=re.findall(r'\{\s*([^{}]+)\}',array_table);array_mapping=[row.split(',')[1].strip()for row in rows]
 if array_mapping!=['nonarray_destroystruct','fixedarray_destroystruct','earray_destroystruct']:raise ValueError('Array destructor dispatch changed')
 extra=[]
 for n in('TOK_STORAGE_INDIRECT_FIXEDARRAY','TOK_STORAGE_INDIRECT_EARRAY','TokenStoreIsCompatible'):
  extra.append(re.search(r'^#define\s+'+n+r'(?=[\s(])[^\n]*',text[body.TOKEN_H],re.M)[0])
 extra.append(re.search(r'^#define\s+TOK_POOL_STRING[^\n]*',text[body.PARSER_H],re.M)[0]);extra.append(re.search(r'^#define\s+TS_REQUIRE[^\n]*',text[body.TOKEN_C],re.M)[0])
 old=re.search(r'static void StructClear\(ParseTable\*t,void\*r\)\{[^\n]*\}',code)[0]
 # The original functions are emitted without edits. Only leaf engine memory
 # operations and handler holder ABI are supported owned fixture adapters.
 code=once(code,old,'\n'.join(extra)+'\n'+SHELL+'\n'+''.join(functions.values()))
 code=once(code,'#define free loader_free\n#define strdup loader_strdup\n','#define free loader_free\n#define strdup loader_strdup\n#define StructClear observed_StructClear\n')
 original_loader=body.extract(text[body.PARSER_C],'ParserLoadFiles');code=once(code,original_loader,original_loader+'#undef StructClear\n')
 code=once(code,'static int loader_globals_idle(void);','static int clear_idle(void);\nstatic int loader_globals_idle(void);')
 code=once(code,'&&loader_globals_idle();','&&loader_globals_idle()&&clear_idle();')
 code=once(code,'return sizeof(owner)+sizeof(crc_owner)', 'return sizeof(clear_state)+sizeof(owner)+sizeof(crc_owner)')
 code=once(code,'owner.receipt.status=(uint32_t)status;result=owner.receipt;', 'if(owner.root.bodyParts)StructClear(ParseBodyPartBegin,&owner.root);clear_receipt();\n owner.receipt.status=(uint32_t)status;result=owner.receipt;')
 code=once(code,'loader_globals_cleanup();body_wipe(&owner','loader_globals_cleanup();body_wipe(&clear_state,sizeof(clear_state));body_wipe(&owner')
 header=once(header,'uint32_t entry_calls,','uint32_t clear_nodes,clear_strings,clear_arrays,clear_order_count,clear_order[30],clear_numeric_preserved,clear_root_null;\n uint32_t entry_calls,')
 for a,b in(('CacheHitLoader','StructClear'),('CACHE_HIT_LOADER','STRUCT_CLEAR'),('cache_hit_loader','struct_clear'),('cache-hit-loader','struct-clear')):code=code.replace(a,b);header=header.replace(a,b)
 header=once(header,'#endif',EXTRA_HEADER+'#endif');code+=FIXTURE
 for n,value in functions.items():
  if code.count(value)!=1:raise ValueError('Original destructor changed or duplicated '+n)
 if any((root/n).read_bytes()!=raw for n,raw in frozen.items()):raise ValueError('Source changed during composition')
 (work/'struct-clear-provider.h').write_text(header);output=work/'struct-clear-provider.c';output.write_text(code)
 return output,proof|{'schema':'coh-original-struct-clear-provider-v1','source_pins_sha256':sha(pins_path.read_bytes()),'whole_function_sha256_lf':proof['whole_function_sha256_lf']|{n:sha(v.encode())for n,v in functions.items()},'destructor_dispatch':{'g_tokentable_sha256_lf':sha(table.encode()),'g_arraytable_sha256_lf':sha(array_table.encode()),'token_destroystruct':mappings,'array_destroystruct':array_mapping,'holder_ABI':'Explicit readbin+destroystruct members only; selectors and supported mappings exact, complete engine handler ABI not claimed'},'composition':'Original StructClear -> exact TOKARRAY_INFO/nonarray/earray -> source struct/string destroystruct -> source TokenStore GetStorageType/GetPointer(Const)/GetNumElems/FreeString/Free/DestroyEArray. New loader composition replaces safe failure shell; originals and accepted providers unchanged. Successful source-owned arena is also destroyed after copying pointer-free candidate.','ownership':'Fixed owned row/string/earray release adapters validate exact slots, one release, string-before-row, reverse source earray row order, numeric non-destruction, root NULL and repeated clear. They retire/wipe arena slots; no original allocator/engine heap/libc free/earray header ABI closure. Borrowed descriptors and invalid string masks preflight refuse. Exact schemas never select pooled, direct-string, fixed-array or direct32-array storage; those engine semantics are excluded.','safe_shell_comparison':'Old shell only nulled root; new source destroys original supported owned strings then rows in reverse earray order and owned array. Same source loader status, call order and atomic pointer-free output retained.','integration':'New independently qualified provider only; accepted cache_hit_loader_provider remains immutable. Runtime catalog remains unadmitted.','engine_allocator_closure':False}
