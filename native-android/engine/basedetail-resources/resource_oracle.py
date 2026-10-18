"""Complete original BIN table grammar + copied persisted resource projection.
No prior qualifier entrypoints, text preprocessing, gameplay or resource load.
"""
import ctypes as C,hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def build(work):
 manifest=json.loads((HERE/'source-pins.json').read_bytes())
 for p,h in manifest['source_sha256_raw'].items():
  if sha((ROOT/p).read_bytes())!=h:raise ValueError('original/helper pin mismatch '+p)
 path=HERE/'../character-dictionary/salvage_oracle.py';spec=importlib.util.spec_from_file_location('bd_resource_prior',path);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
 inherited=work/'provider';inherited.mkdir();_,base=prior.build(ROOT,inherited);code=(inherited/'original-salvage.c').read_text()
 capabilities=('CLIENT_chareval_body_executed_as_noop','ordinary_source_getters_executed','serialized_workshop_text_observed_at_original_link_ReadPascalString_boundary')
 base['compiled_provider_capabilities_NOT_executed_here']={k:base.pop(k)for k in capabilities}
 base['prior_original_salvage_wrapper_executed']=False
 # Existing reader provider was not a resource finalizer: it allocated "" even
 # for indirect-single strings. This new local adapter follows the ORIGINAL
 # TokenStoreSetString empty/NULL rule for the copied cache projection.
 old='size_t n=strlen(s);assert(n<12000);char*q=alloc(n+1);memcpy(q,s,n+1);TokenStoreSetPointer(t,c,p,i,q);'
 new='size_t n=strlen(s);assert(n<12000);char*q=NULL;if(n||(t[c].type&TOK_EARRAY)){q=alloc(n+1);memcpy(q,s,n+1);}TokenStoreSetPointer(t,c,p,i,q);'
 if code.count(old)!=1:raise ValueError('setter adapter shape')
 code=code.replace(old,new)
 source=(ROOT/'upstream/ouroboros/Common/bases/basedata.c').read_text();parser=(ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c').read_text()
 witnesses={n:prior.extract(parser if n.startswith('Parser')else source,n)for n in('ParserLoadFiles','ParserLoadFilesShared','ParserReadBinaryFile','basedata_Load')}
 load=witnesses['ParserLoadFiles'];hit=load.index('if (ParserReadBinaryFile(');ret=load.index('return 1;',hit);pre=load.index('// run the preprocessor');write=load.index('ParserWriteBinaryFile(',pre)
 if not(hit<ret<pre<write):raise ValueError('original BIN branch no longer bypasses text preprocessing')
 code+='\n#include "coh_bd_resources.h"\n'
 code+='''
static CohBdResourceText resources_copy(CohBdResources*out,const char*s){CohBdResourceText t={0,0};if(!s||!*s)return t;unsigned n=strlen(s);assert(n<1024&&n+1<=COH_BD_RESOURCE_TEXT_MAX-out->text_bytes);t=(CohBdResourceText){out->text_bytes,n};memcpy(out->text+t.offset,s,n+1);out->text_bytes+=n+1;return t;}
int original_resources(const unsigned char*bytes,unsigned n,unsigned begin,CohBdResources*out){
 reset();memset(&g_DetailDict,0,sizeof(g_DetailDict));memset(out,0,sizeof(*out));SimpleBuffer*in=alloc(sizeof(*in));assert(n<=1048576);memcpy(in->data,bytes,n);in->filesize=n;in->curposition=begin;int sum=0;assert(ParserReadBinaryTable(in,ParseDetailDict,&g_DetailDict,&sum)&&in->curposition==(int)n);Vec*v=(Vec*)g_DetailDict.ppDetails;if(!v)v=vector(0,0);g_DetailDict.ppDetails=(const Detail**)v->items;out->count=v->size;
 for(unsigned i=0;i<out->count;i++){Detail*d=v->items[i];CohBdResourceRow*r=&out->rows[i];r->name=resources_copy(out,d->pchName);r->groups[0]=resources_copy(out,d->pchGroupName);r->groups[1]=resources_copy(out,d->pchGroupNameUnpowered);r->groups[2]=resources_copy(out,d->pchGroupNameDestroyed);r->groups[3]=resources_copy(out,d->pchGroupNameMount);r->groups[4]=resources_copy(out,d->pchGroupNameUnpoweredMount);r->groups[5]=resources_copy(out,d->pchGroupNameBaseEdit);r->surface=d->eSurface;r->mounted=d->bMounted;r->animated=d->bAnimatedEnt;}
 reset();memset(&g_DetailDict,0,sizeof(g_DetailDict));return 1;}
size_t resources_sizeof(void){return sizeof(CohBdResources);}
'''
 output=work/'original-resources.c';output.write_text(code);so=work/'original-resources.so';subprocess.run(['cc','-std=gnu11','-w','-shared','-fPIC','-I'+str(HERE),'-I'+str(HERE/'../character-dictionary'),'-I'+str(HERE/'../costume-inputs'),output,'-lz','-o',so],check=True)
 lib=C.CDLL(str(so));lib.original_resources.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p];lib.original_resources.restype=C.c_int;lib.resources_sizeof.restype=C.c_size_t
 return lib,{'provider':base,'generated_source_sha256':sha(code.encode()),'unexecuted_whole_consumer_source_witnesses_sha256_lf':{n:sha(b.encode())for n,b in witnesses.items()},'original_BIN_cache_hit_bypasses_text_preprocessor_source_guard':True,'indirect_empty_string_source_policy':True,'CLIENT_unused_field_pruning_executed':False,'Details_preprocessing_executed':False,'original_geometry_loader_executed':False,'prior_qualifier_entrypoints_executed':False}
