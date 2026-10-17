#include "../coh_wr_tex_seed.c"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include "tex-seed-fixtures.h"
typedef struct{unsigned classification,queries,slots[16],ordinals[16],flags[16];char keys[16][128];}SeedOracle;
extern void original_seed_headers(unsigned,const char*const*);
extern int original_seed(const CohWrTexOptView*,unsigned,SeedOracle*);
static unsigned checks,comparisons,allocations,polls,cancel_at;
static unsigned actual_class[3],actual_unknown,actual_unsafe,actual_candidates,controlled_class[3],controlled_unknown,controlled_unsafe;
static unsigned actual_policy[2][5],retirement_phase;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"texseed line%d %s\n",__LINE__,#x);abort();}}while(0)
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);
void*__wrap_malloc(size_t n){allocations++;return __real_malloc(n);}
void*__wrap_calloc(size_t n,size_t z){allocations++;return __real_calloc(n,z);}
typedef struct{uint8_t*data;size_t size;}Source;
static Source load(const char*name){FILE*f=fopen(name,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<16*1024*1024);rewind(f);Source s={malloc((size_t)n),(size_t)n};CHECK(s.data&&fread(s.data,1,s.size,f)==s.size&&!fclose(f));return s;}
static CohStatus readat(void*v,uint64_t offset,void*out,size_t n){Source*s=v;if(offset>s->size||n>s->size-offset)return COH_IO;memcpy(out,s->data+(size_t)offset,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t hash[32]){(void)v;SHA256(b.data,b.size,hash);return COH_OK;}
static int cancelled(void*v){(void)v;polls++;return cancel_at&&polls==cancel_at;}
static CohStatus compare(const CohWrTexOptRecord*record,const CohWrTexOptView*v,const CohWrTexInputs*inputs,CohWrTexSeedLimits limits,int controlled){
 SeedOracle oracle;CohStatus expected=(CohStatus)original_seed(v,limits.guarded_short_key_policy,&oracle);
 CohWrTexSeed out,saved;memset(&out,0x55,sizeof(out));saved=out;unsigned before=allocations;
 CohStatus status=controlled?project(v,v,sizeof(*v),inputs,&limits,(CohCancel){0},&out):coh_wr_tex_seed(record,inputs,&limits,(CohCancel){0},&out);
 CHECK(allocations==before&&status==expected);comparisons++;
 if(status!=COH_OK){CHECK(!memcmp(&out,&saved,sizeof(out)));CHECK(status==COH_NOT_FOUND||status==COH_UNSUPPORTED);if(status==COH_NOT_FOUND){if(controlled)controlled_unknown++;else{actual_unknown++;actual_policy[limits.guarded_short_key_policy][3]++;}}else{if(controlled)controlled_unsafe++;else{actual_unsafe++;actual_policy[limits.guarded_short_key_policy][4]++;}}return status;}
 CHECK(out.classification==oracle.classification&&out.query_count==oracle.queries&&out.query_count<=16);
 CHECK(out.source_ordinal==v->source_ordinal&&out.table_owner_ordinal==v->table_owner_ordinal&&out.historical_input_generation==17&&out.guarded_short_key_policy==limits.guarded_short_key_policy&&!memcmp(out.cache_sha256,v->cache_sha256,32));
 CHECK(out.aggregate_reserved_bytes==limits.external_bytes+OWN_RESERVE+BASIC_RESERVE);
 for(unsigned i=0;i<out.query_count;i++){const CohWrTexSeedDependency*d=out.dependencies+i;CohWrTexHeaderInput h;CHECK(d->source_slot==oracle.slots[i]&&d->header_ordinal==oracle.ordinals[i]&&d->format_flags==oracle.flags[i]&&!strcmp(d->key,oracle.keys[i]));CHECK(coh_wr_tex_inputs_header(inputs,d->header_ordinal,&h)==COH_OK&&!memcmp(d->header_sha256,h.sha256,32));}
 if(controlled)controlled_class[out.classification]++;else if(!retirement_phase){actual_class[out.classification]++;actual_policy[limits.guarded_short_key_policy][out.classification]++;if(out.classification==2)actual_candidates++;}return status;
}
static void refusal_controls(const CohWrTexOptRecord*r,const CohWrTexOptView*v,const CohWrTexInputs*i,CohWrTexSeedLimits limits,const CohWrTexHeaderInput*h){
 CohWrTexSeed out,saved;memset(&out,0xa5,sizeof(out));saved=out;CohWrTexSeedLimits bad=limits;
 unsigned before=allocations;polls=0;bad.aggregate_limit=bad.external_bytes+OWN_RESERVE+BASIC_RESERVE-1;
 CHECK(coh_wr_tex_seed(r,i,&bad,(CohCancel){cancelled,NULL},&out)==COH_LIMIT&&!polls&&allocations==before&&!memcmp(&out,&saved,sizeof(out)));
 bad=limits;bad.external_bytes=1;CHECK(coh_wr_tex_seed(r,i,&bad,(CohCancel){cancelled,NULL},&out)==COH_LIMIT&&!polls&&!memcmp(&out,&saved,sizeof(out)));
 CohWrTexInputsReport ir;CHECK(coh_wr_tex_inputs_report(i,&ir)==COH_OK);bad=limits;bad.external_bytes=v->owned_bytes+ir.owned_bytes+ir.loader_reservation+16384;bad.aggregate_limit=bad.external_bytes+OWN_RESERVE+BASIC_RESERVE;
 CHECK(coh_wr_tex_seed(r,i,&bad,(CohCancel){0},&out)==COH_OK&&out.aggregate_reserved_bytes==bad.aggregate_limit);out=saved;bad.external_bytes--;CHECK(coh_wr_tex_seed(r,i,&bad,(CohCancel){cancelled,NULL},&out)==COH_LIMIT&&!polls&&!memcmp(&out,&saved,sizeof(out)));
 bad=limits;bad.external_bytes=SIZE_MAX;CHECK(coh_wr_tex_seed(r,i,&bad,(CohCancel){cancelled,NULL},&out)==COH_LIMIT&&!polls&&!memcmp(&out,&saved,sizeof(out)));
 bad=limits;bad.guarded_short_key_policy=2;CHECK(coh_wr_tex_seed(r,i,&bad,(CohCancel){0},&out)==COH_UNSUPPORTED&&!memcmp(&out,&saved,sizeof(out)));
 CHECK(coh_wr_tex_seed(r,i,&limits,(CohCancel){0},(CohWrTexSeed*)r)==COH_INVALID);
 CHECK(coh_wr_tex_seed(r,i,&limits,(CohCancel){0},(CohWrTexSeed*)i)==COH_INVALID);
 CHECK(coh_wr_tex_seed(r,i,&limits,(CohCancel){0},(CohWrTexSeed*)(void*)h->original_name)==COH_INVALID);
 CHECK(coh_wr_tex_seed(r,i,&limits,(CohCancel){0},(CohWrTexSeed*)&limits)==COH_INVALID);
 for(unsigned q=0;q<4;q++){CHECK(coh_wr_tex_seed(q==0?NULL:r,q==1?NULL:i,q==2?NULL:&limits,(CohCancel){0},q==3?NULL:&out)==COH_INVALID&&!memcmp(&out,&saved,sizeof(out)));}
 CohWrTexOptView changed=*v;changed.historical_input_generation=18;CHECK(project(&changed,&changed,sizeof(changed),i,&limits,(CohCancel){0},&out)==COH_STATE&&!memcmp(&out,&saved,sizeof(out)));
 changed=*v;changed.original_CLIENT_postprocessed=0;CHECK(project(&changed,&changed,sizeof(changed),i,&limits,(CohCancel){0},&out)==COH_UNSUPPORTED&&!memcmp(&out,&saved,sizeof(out)));
 changed=*v;changed.layers[0].name="unexpected_old_base";CHECK(project(&changed,&changed,sizeof(changed),i,&limits,(CohCancel){0},&out)==COH_UNSUPPORTED&&!memcmp(&out,&saved,sizeof(out)));
 polls=0;CHECK(coh_wr_tex_seed(r,i,&limits,(CohCancel){cancelled,NULL},&out)==COH_OK);unsigned last=polls;CHECK(last==2);out=saved;
 for(cancel_at=1;cancel_at<=last;cancel_at++){polls=0;CHECK(coh_wr_tex_seed(r,i,&limits,(CohCancel){cancelled,NULL},&out)==COH_CANCELLED&&!memcmp(&out,&saved,sizeof(out)));}cancel_at=0;
}
int main(int argc,char**argv){
 CHECK(argc==4);Source cache=load(argv[1]),states=load(argv[2]),bodies[15];
 CohAssetLoader*loader=NULL,*cache_loader=NULL;CohAssetLimits al={64u<<20,60u<<20,16u<<20,16u<<20,32,32,32};CHECK(coh_asset_create(&al,&loader)==COH_OK);CHECK(coh_asset_create(&al,&cache_loader)==COH_OK);
 CHECK(coh_asset_mount_file(cache_loader,"data/bin/tricks.bin",(CohAssetSource){readat,&cache,cache.size,17})==COH_OK);
 CohWrTexInputPin pins[15];for(unsigned q=0;q<15;q++){char path[2048];CHECK(snprintf(path,sizeof(path),"%s/%s",argv[3],avatar[q].path)>0);bodies[q]=load(path);CHECK(bodies[q].size==avatar[q].bytes);SHA256(bodies[q].data,bodies[q].size,pins[q].sha256);CHECK(!memcmp(pins[q].sha256,avatar[q].sha256,32));pins[q].asset=(CohAssetId){avatar[q].path,17};CHECK(coh_asset_mount_file(loader,avatar[q].path,(CohAssetSource){readat,bodies+q,bodies[q].size,17})==COH_OK);}
 CohWrTexInputs*inputs=NULL;CohWrTexInputsRequest request={pins,NULL,15,0,17,digest,NULL};CohWrTexInputsLimits ib={1u<<20,256u<<20,64u<<20,128u<<20};CHECK(coh_wr_tex_inputs_build(loader,&request,&ib,(CohCancel){0},&inputs)==COH_OK);
 CohWrTexHeaderInput headers[15];const char*keys[15];for(unsigned q=0;q<15;q++){CHECK(coh_wr_tex_inputs_header(inputs,q,headers+q)==COH_OK);keys[q]=headers[q].basic_key;}original_seed_headers(15,keys);
 CohWrSurfaceStates*surface=NULL;CohWrSurfaceLimits sb={200000,400000,1000};CHECK(coh_wr_surface_prepare((CohBytes){states.data,states.size},17,digest,NULL,&sb,(CohCancel){0},&surface)==COH_OK);
 CohWrTexOptCache*texopts=NULL;CohWrTexOptLimits tb={1u<<20,512u<<20,64u<<20,256u<<20};CHECK(coh_wr_texopt_cache_open(cache_loader,(CohAssetId){"data/bin/tricks.bin",17},digest,NULL,&tb,(CohCancel){0},&texopts)==COH_OK);
 CohWrTexSeedLimits limits={512u<<20,384u<<20,0};CohWrTexOptRecord*held=NULL;CohWrTexOptView held_view;unsigned source_refusals=0;
 for(unsigned row=0;row<14715;row++){
  CohWrTexOptRecord*r=NULL;CohStatus status=coh_wr_texopt_record_create(texopts,row,surface,&tb,(CohCancel){0},&r);
  if(row==10499){CHECK(status==COH_UNSUPPORTED&&!r);source_refusals++;continue;}CHECK(status==COH_OK&&r);CohWrTexOptView v;CHECK(coh_wr_texopt_record_view(r,&v)==COH_OK);
  for(unsigned g=0;g<2;g++){limits.guarded_short_key_policy=g;(void)compare(r,&v,inputs,limits,0);}
  if(!held&&!v.layers[2].name){held=r;held_view=v;}else coh_wr_texopt_record_release(&r);
 }
 CHECK(held&&source_refusals==1&&actual_class[0]&&actual_class[1]&&actual_unknown&&actual_unsafe);limits.guarded_short_key_policy=1;
 refusal_controls(held,&held_view,inputs,limits,headers);
 /* Controlled TexOpt views below are explicit source branch inputs, not actual
  * retained rows. Header positives remain the exact fifteen authentic bodies. */
 CohWrTexOptView v=held_view;v.name="__controlled_seed";memset(v.layers,0,sizeof(v.layers));memset(&v.fallback,0,sizeof(v.fallback));
 const char*invalid[]={NULL,"","%parameter","SwApPaBlE","NoNe"};
 for(unsigned base=0;base<15;base++){
  v.layers[2].name=keys[base];for(unsigned q=1;q<13;q++)if(q!=2)v.layers[q].name=keys[(base+q)%15];v.fallback.use_fallback=1;v.fallback.base=keys[(base+13)%15];v.fallback.blend=keys[(base+14)%15];v.fallback.bumpmap=keys[base];
  for(unsigned g=0;g<2;g++){limits.guarded_short_key_policy=g;CHECK(compare(NULL,&v,inputs,limits,1)==COH_OK);}
  for(unsigned slot=1;slot<16;slot++){
   CohWrTexOptView changed=v;const char**target=slot<13?&changed.layers[slot].name:slot==13?&changed.fallback.base:slot==14?&changed.fallback.blend:&changed.fallback.bumpmap;
   for(unsigned n=0;n<5;n++){*target=invalid[n];for(unsigned g=0;g<2;g++){limits.guarded_short_key_policy=g;CHECK(compare(NULL,&changed,inputs,limits,1)==COH_OK);}}
   *target="__not_observed";for(unsigned g=0;g<2;g++){limits.guarded_short_key_policy=g;CHECK(compare(NULL,&changed,inputs,limits,1)==COH_NOT_FOUND);}
  }
 }
 for(unsigned enabled=0;enabled<2;enabled++){v.fallback.use_fallback=(uint8_t)enabled;v.fallback.base="__not_observed";limits.guarded_short_key_policy=1;CHECK(compare(NULL,&v,inputs,limits,1)==(enabled?COH_NOT_FOUND:COH_OK));}
 memset(v.layers,0,sizeof(v.layers));memset(&v.fallback,0,sizeof(v.fallback));v.layers[2].name=keys[0];v.name=keys[0];CHECK(compare(NULL,&v,inputs,limits,1)==COH_OK);
 char prefix_name[256];snprintf(prefix_name,sizeof(prefix_name),"%s.any_extra",keys[0]);v.layers[2].name=prefix_name;CHECK(compare(NULL,&v,inputs,limits,1)==COH_OK);
 v.name="__controlled_seed";v.layers[2].name="!CHEST_LEATHER_03.dds";CHECK(compare(NULL,&v,inputs,limits,1)==COH_OK);
 char longkey[130];memset(longkey,'x',sizeof(longkey)-1);longkey[sizeof(longkey)-1]=0;v.layers[2].name=longkey;CohWrTexSeed bounded_out,bounded_saved;memset(&bounded_out,0xa5,sizeof(bounded_out));bounded_saved=bounded_out;CHECK(project(&v,&v,sizeof(v),inputs,&limits,(CohCancel){0},&bounded_out)==COH_LIMIT&&!memcmp(&bounded_out,&bounded_saved,sizeof(bounded_out)));
 v.layers[2].name="\xff";CHECK(project(&v,&v,sizeof(v),inputs,&limits,(CohCancel){0},&bounded_out)==COH_UNSUPPORTED&&!memcmp(&bounded_out,&bounded_saved,sizeof(bounded_out)));
 v.layers[2].name="white";limits.guarded_short_key_policy=0;CHECK(compare(NULL,&v,inputs,limits,1)==COH_UNSUPPORTED);limits.guarded_short_key_policy=1;CHECK(compare(NULL,&v,inputs,limits,1)==COH_NOT_FOUND);
 v.layers[2].name=keys[0];v.fallback.use_fallback=1;v.fallback.base=keys[1];v.fallback.blend=keys[2];v.fallback.bumpmap=keys[3];CohWrTexSeed out,saved;memset(&out,0x55,sizeof(out));saved=out;polls=0;CHECK(project(&v,&v,sizeof(v),inputs,&limits,(CohCancel){cancelled,NULL},&out)==COH_OK);unsigned last=polls;CHECK(last==6);out=saved;for(cancel_at=1;cancel_at<=last;cancel_at++){polls=0;CHECK(project(&v,&v,sizeof(v),inputs,&limits,(CohCancel){cancelled,NULL},&out)==COH_CANCELLED&&!memcmp(&out,&saved,sizeof(out)));}cancel_at=0;
 /* The compact existing record owns all its source fields: retire the cache,
  * Surface owner and cache provider before exercising this selection again. */
 coh_wr_texopt_cache_release(&texopts);coh_wr_surface_release(&surface);coh_asset_trim(cache_loader);CHECK(coh_asset_stats(cache_loader).resident_bytes==0&&coh_asset_stats(cache_loader).pinned_blobs==0);CHECK(coh_asset_destroy(&cache_loader)==COH_OK);free(cache.data);cache.data=NULL;free(states.data);retirement_phase=1;CHECK(compare(held,&held_view,inputs,limits,0)==COH_OK);
 coh_wr_texopt_record_release(&held);coh_wr_tex_inputs_release(&inputs);CHECK(coh_asset_destroy(&loader)==COH_OK);for(unsigned q=0;q<15;q++)free(bodies[q].data);
 CHECK(controlled_class[2]&&controlled_unknown&&controlled_unsafe);
 printf("{\"passed\":true,\"checks\":%u,\"original_comparisons\":%u,\"actual_cache_rows\":14715,\"actual_record_source_refusals\":%u,\"authentic_header_bodies\":15,\"actual_no_base1\":%u,\"actual_name_prefix_skip\":%u,\"actual_create_candidates\":%u,\"actual_unknown_refusals\":%u,\"actual_unsafe_refusals\":%u,\"actual_policy_column_order\":[\"no_base1\",\"name_prefix_skip\",\"create_candidate\",\"subset_unknown_refusal\",\"unsafe_key_refusal\"],\"actual_strict_policy\":[%u,%u,%u,%u,%u],\"actual_guarded_policy\":[%u,%u,%u,%u,%u],\"controlled_create_candidates\":%u,\"controlled_unknown_refusals\":%u,\"controlled_unsafe_refusals\":%u,\"result_bytes\":%zu,\"current_CLIENT_generation\":false,\"material_authority\":false,\"world_authority\":false}\n",checks,comparisons,source_refusals,actual_class[0],actual_class[1],actual_candidates,actual_unknown,actual_unsafe,actual_policy[0][0],actual_policy[0][1],actual_policy[0][2],actual_policy[0][3],actual_policy[0][4],actual_policy[1][0],actual_policy[1][1],actual_policy[1][2],actual_policy[1][3],actual_policy[1][4],controlled_class[2],controlled_unknown,controlled_unsafe,sizeof(CohWrTexSeed));return 0;
}
