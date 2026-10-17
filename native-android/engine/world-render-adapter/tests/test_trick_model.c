#include "../coh_wr_trick_model.h"
#include "trick_model_oracle.h"
#include "trick-model-fixtures.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <openssl/sha.h>
static unsigned checks,cases,allocations,reads,digests;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"TrickModel line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);
void*__wrap_malloc(size_t n){allocations++;return __real_malloc(n);}
void*__wrap_calloc(size_t n,size_t s){allocations++;return __real_calloc(n,s);}
typedef struct {uint8_t*bytes;size_t size;} Source;
static CohStatus readat(void*v,uint64_t off,void*out,size_t n){Source*s=v;reads++;if(off>s->size||n>s->size-off)return COH_IO;memcpy(out,s->bytes+(size_t)off,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;digests++;SHA256(b.data,b.size,out);return COH_OK;}
static int same(const char*a,const char*b){while(*a&&*b){unsigned x=(unsigned char)*a++,y=(unsigned char)*b++;if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;}return *a==*b;}
static int span_same(CohBytes b,const char*s){return b.size==strlen(s)&&(!b.size||!memcmp(b.data,s,b.size));}
static CohWrTrickCache*whole;static CohWrTrickDetached*detached;static int use_detached;
static CohWrTrickModelLimits limits;static CohWrTrickReport source_report;static CohWrTrickDetachedReport detached_report;
static CohStatus select_model(const CohWrTrickModelQuery*q,const CohWrTrickModelLimits*l,CohWrTrickModelSelection*out){return use_detached?coh_wr_trick_detached_model_select(detached,q,l,out):coh_wr_trick_model_select(whole,q,l,out);}
static CohStatus selected_view(uint32_t row,CohWrTrickView*out){return use_detached?coh_wr_trick_detached_view(detached,row,out):coh_wr_trick_view(whole,row,out);}
static CohWrTrickModelSelection compare(const CohWrTrickModelQuery*q){
 TrickModelOracleResult expected;original_trick_model_select(q->model_name,q->source_geo_path,(int)q->report_missing_suffix,&expected);
 CohWrTrickModelSelection out;memset(&out,0x55,sizeof(out));unsigned a=allocations,r=reads,d=digests;
 CHECK(select_model(q,&limits,&out)==COH_OK);CHECK(allocations==a&&reads==r&&digests==d);
 if(out.source_ordinal!=expected.ordinal||out.source_diagnostic!=expected.diagnostic||strcmp(out.lookup_key,expected.key))fprintf(stderr,"model %s: native %u/%u/%s source %u/%u/%s\n",q->model_name,out.source_ordinal,out.source_diagnostic,out.lookup_key,expected.ordinal,expected.diagnostic,expected.key);
 CHECK(expected.lookups==1&&out.source_ordinal==expected.ordinal&&out.source_diagnostic==expected.diagnostic&&!strcmp(out.lookup_key,expected.key));
 CHECK(out.matched==(expected.ordinal!=UINT32_MAX));CHECK(out.branch==(strstr(q->model_name,"__")?COH_WR_TRICK_MODEL_FIRST_SUFFIX:COH_WR_TRICK_MODEL_WHOLE_NAME));
 CHECK(out.historical_input_generation==source_report.historical_input_generation&&!memcmp(out.cache_sha256,source_report.cache_sha256,32));
 CHECK(out.aggregate_reserved_bytes==limits.external_bytes+COH_WR_TRICK_MODEL_QUERY_RESERVE);
 if(out.matched){CohWrTrickView view;CHECK(selected_view(out.source_ordinal,&view)==COH_OK);CHECK(span_same(view.name,trick_fixtures[out.source_ordinal].name)&&span_same(view.source_file,trick_fixtures[out.source_ordinal].file));CHECK(view.table_owner_ordinal==out.source_ordinal&&view.is_table_owner&&view.unresolved_client_semantics&&!view.dictionary_registration_executed);}
 cases++;return out;
}
static void refusal(const CohWrTrickModelQuery*q,const CohWrTrickModelLimits*l,CohStatus expected){CohWrTrickModelSelection old,out;memset(&old,0x66,sizeof(old));out=old;unsigned a=allocations,r=reads,d=digests;CHECK(select_model(q,l,&out)==expected&&!memcmp(&old,&out,sizeof(out)));CHECK(allocations==a&&reads==r&&digests==d);}
static void exercise(void){
 unsigned hits=0,misses=0,suffix=0,unique=0;uint8_t selected[3644]={0};
 for(size_t i=0;i<sizeof(root_fixtures)/sizeof(*root_fixtures);i++){
  const RootTrickFixture*f=&root_fixtures[i];CohWrTrickModelQuery q={f->model,f->geo,1};CohWrTrickModelSelection out=compare(&q);
  CHECK(out.matched==f->info_present);suffix+=out.branch==COH_WR_TRICK_MODEL_FIRST_SUFFIX;
  if(out.matched){CohWrTrickView v;CHECK(selected_view(out.source_ordinal,&v)==COH_OK);char name[260],file[1024];CHECK(v.name.size<sizeof(name)&&v.source_file.size<sizeof(file));memcpy(name,v.name.data,v.name.size);name[v.name.size]=0;memcpy(file,v.source_file.data,v.source_file.size);file[v.source_file.size]=0;CHECK(same(name,f->captured_name)&&same(file,f->captured_file));hits++;selected[out.source_ordinal]=1;}
  else {CHECK(!*f->captured_name&&!*f->captured_file);misses++;}
 }
 for(unsigned i=0;i<3644;i++)unique+=selected[i]!=0;
 CHECK(hits==1959&&misses==1124&&suffix==1958&&unique==528);
 /* Derived name controls use actual independent decoded historical keys. They
  * test source policy, not additional observed model associations. */
 const char*short_key=NULL;
 for(size_t i=0;i<sizeof(trick_fixtures)/sizeof(*trick_fixtures);i++){
  const char*name=trick_fixtures[i].name;char composed[260],upper[260];size_t n=strlen(name);CHECK(n<260);
  CohWrTrickModelQuery q={name,"data/derived.geo",1};compare(&q);
  if(n+3<260){snprintf(composed,sizeof(composed),"p__%s",name);q.model_name=composed;compare(&q);}
  for(size_t j=0;j<=n;j++){unsigned c=(unsigned char)name[j];upper[j]=(char)(c>='a'&&c<='z'?c-32:c);}q.model_name=upper;compare(&q);
  if(!short_key&&n<64&&!strstr(name,"__"))short_key=name;
 }
 CHECK(short_key);char special[260];CohWrTrickModelQuery q={special,"data/derived.geo",1};
 snprintf(special,sizeof(special),"%s__no_such_source_trick_918273",short_key);CohWrTrickModelSelection out=compare(&q);CHECK(!out.matched&&out.source_diagnostic==COH_WR_TRICK_MODEL_FILENAME_DIAGNOSTIC);
 snprintf(special,sizeof(special),"p__no_such_source_trick_918273__%s",short_key);out=compare(&q);CHECK(!out.matched);
 q.model_name="p__";compare(&q);q.report_missing_suffix=0;compare(&q);q.report_missing_suffix=1;q.source_geo_path="";out=compare(&q);CHECK(out.source_diagnostic==COH_WR_TRICK_MODEL_GENERIC_DIAGNOSTIC);
 q.model_name="no_such_source_trick_918273";out=compare(&q);CHECK(!out.matched&&!out.source_diagnostic);
 char boundary[261];memset(boundary,'x',260);boundary[260]=0;boundary[259]=0;q=(CohWrTrickModelQuery){boundary,boundary,1};compare(&q);boundary[259]='x';refusal(&q,&limits,COH_LIMIT);q=(CohWrTrickModelQuery){"world",boundary,1};refusal(&q,&limits,COH_LIMIT);q=(CohWrTrickModelQuery){"world","data/valid.geo",1};
 CohWrTrickModelLimits bad=limits;bad.aggregate_limit=bad.external_bytes+COH_WR_TRICK_MODEL_QUERY_RESERVE-1;refusal(&q,&bad,COH_LIMIT);bad=limits;bad.external_bytes=SIZE_MAX;bad.aggregate_limit=SIZE_MAX;refusal(&q,&bad,COH_LIMIT);
 bad=limits;bad.external_bytes=(use_detached?detached_report.owned_bytes:source_report.owned_bytes+source_report.loader_reservation)-1;refusal(&q,&bad,COH_LIMIT);
 size_t aggregate_limit=limits.aggregate_limit;limits.aggregate_limit=limits.external_bytes+COH_WR_TRICK_MODEL_QUERY_RESERVE;compare(&q);limits.aggregate_limit=aggregate_limit;
 for(unsigned i=0;i<6;i++){CohWrTrickModelQuery badq=q;if(i==0)badq.model_name=NULL;if(i==1)badq.model_name="";if(i==2)badq.model_name="\xff";if(i==3)badq.source_geo_path=NULL;if(i==4)badq.source_geo_path="\x1f";if(i==5)badq.report_missing_suffix=2;refusal(&badq,&limits,i==2||i==4?COH_UNSUPPORTED:COH_INVALID);}
 CohWrTrickModelSelection untouched,saved;memset(&saved,0x77,sizeof(saved));untouched=saved;CHECK(select_model(NULL,&limits,&untouched)==COH_INVALID&&!memcmp(&saved,&untouched,sizeof(saved)));CHECK(select_model(&q,NULL,&untouched)==COH_INVALID&&!memcmp(&saved,&untouched,sizeof(saved)));CHECK(select_model(&q,&limits,NULL)==COH_INVALID);
 union {CohWrTrickModelQuery q;CohWrTrickModelSelection out;} alias;memset(&alias,0,sizeof(alias));alias.q=q;CHECK(select_model(&alias.q,&limits,&alias.out)==COH_INVALID);
 union {CohWrTrickModelLimits l;CohWrTrickModelSelection out;} alias_l;alias_l.l=limits;CHECK(select_model(&q,&alias_l.l,&alias_l.out)==COH_INVALID);
 memset(&untouched,0,sizeof(untouched));strcpy(untouched.lookup_key,"world");q.model_name=untouched.lookup_key;saved=untouched;CHECK(select_model(&q,&limits,&untouched)==COH_INVALID&&!memcmp(&saved,&untouched,sizeof(saved)));q.model_name="world";q.source_geo_path=untouched.lookup_key;CHECK(select_model(&q,&limits,&untouched)==COH_INVALID&&!memcmp(&saved,&untouched,sizeof(saved)));q.source_geo_path="data/valid.geo";
 CHECK(select_model(&q,&limits,(CohWrTrickModelSelection*)(void*)(use_detached?(const void*)detached:(const void*)whole))==COH_INVALID);
 CohWrTrickView borrowed;CHECK(selected_view(0,&borrowed)==COH_OK);CHECK(select_model(&q,&limits,(CohWrTrickModelSelection*)(void*)borrowed.name.data)==COH_INVALID);
}
int main(int argc,char**argv){
 CHECK(argc==2);FILE*f=fopen(argv[1],"rb");CHECK(f);Source source={malloc(13537052),13537052};CHECK(source.bytes&&fread(source.bytes,1,source.size,f)==source.size&&fgetc(f)==EOF&&!fclose(f));
 CohAssetLoader*loader=NULL;CohAssetLimits al={16u<<20,15u<<20,16u<<20,16u<<20,4,4,4};CHECK(coh_asset_create(&al,&loader)==COH_OK&&coh_asset_mount_file(loader,"data/bin/tricks.bin",(CohAssetSource){readat,&source,source.size,17})==COH_OK);CohAssetStats baseline=coh_asset_stats(loader);
 CohWrTexOptCache*texopt=NULL;CohWrTexOptLimits tl={1u<<20,96u<<20,16u<<20,64u<<20};CHECK(coh_wr_texopt_cache_open(loader,(CohAssetId){"data/bin/tricks.bin",17},digest,NULL,&tl,(CohCancel){0},&texopt)==COH_OK);
 CohWrTrickLimits wl={1u<<20,96u<<20,16u<<20,64u<<20};CHECK(coh_wr_trick_open(loader,texopt,digest,NULL,&wl,(CohCancel){0},&whole)==COH_OK&&coh_wr_trick_report(whole,&source_report)==COH_OK);
 limits=(CohWrTrickModelLimits){96u<<20,64u<<20};exercise();unsigned whole_cases=cases;
 CohWrTrickDetachedLimits dl={1u<<20,96u<<20,16u<<20,64u<<20};CHECK(coh_wr_trick_detach(loader,&whole,digest,NULL,&dl,(CohCancel){0},&detached)==COH_OK&&!whole&&coh_wr_trick_detached_report(detached,&detached_report)==COH_OK);
 coh_wr_texopt_cache_release(&texopt);coh_asset_trim(loader);CohAssetStats retired=coh_asset_stats(loader);CHECK(retired.allocated_bytes==baseline.allocated_bytes&&!retired.resident_bytes&&!retired.pinned_blobs&&coh_asset_destroy(&loader)==COH_OK);free(source.bytes);source.bytes=NULL;
 use_detached=1;limits=(CohWrTrickModelLimits){96u<<20,64u<<20};exercise();CHECK(cases==2*whole_cases);coh_wr_trick_detached_release(&detached);CHECK(!detached);
 printf("{\"passed\":true,\"checks\":%u,\"source_comparisons\":%u,\"comparisons_per_owner\":%u,\"actual_root_models_per_owner\":3083,\"suffix_queries\":1958,\"whole_name_queries\":1125,\"historical_matches\":1959,\"historical_misses\":1124,\"distinct_selected_rows\":528,\"actual_name_file_disagreements\":0,\"whole_owner_bytes\":%zu,\"detached_owner_bytes\":%zu,\"selection_output_bytes\":%zu,\"policy_heap_allocations\":0,\"detached_after_actual_loader_provider_retirement\":true,\"SERVER_CLIENT_generation_equality\":false,\"current_material_selection\":false,\"world_authority\":false}\n",checks,cases,whole_cases,source_report.owned_bytes,detached_report.owned_bytes,sizeof(CohWrTrickModelSelection));return 0;
}
