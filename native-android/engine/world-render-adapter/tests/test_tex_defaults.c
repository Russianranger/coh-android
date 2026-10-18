#include "../coh_wr_tex_defaults.c"
#include "tex_defaults_fixture.h"
#include "defaults_actual.h"
#include <openssl/sha.h>
#include <stdio.h>

typedef struct {uint8_t*data;size_t size;} Memory;
typedef struct {
 Memory memory[20];CohWrTexNamespaceFile files[20];char paths[20][260];
 CohWrTexNamespaceRoot root;CohWrTexNamespace*source;uint32_t count,held;
 size_t bytes;
} Fixture;
static uint32_t checks,comparisons,cases,holds,drops,freed_contexts;
static uint32_t polls,stop_at,digests,fail_digest,mismatch_digest,allocations,fail_allocation;
static uint32_t live_count,final_cancel,observe_reentry,retire_old_final;
static void*live[4096];static CohWrTexDefaults*watched,*older;
static CohWrTexNamespace*observed;
static size_t authentic_owned,authentic_aggregate,authentic_namespace,authentic_external;
static size_t authentic_bodies,old_new_aggregate,old_owned,retired_bytes;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"defaults line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_calloc(size_t,size_t);void __real_free(void*);
void*__wrap_calloc(size_t n,size_t size){
 allocations++;if(fail_allocation&&allocations==fail_allocation)return NULL;
 void*p=__real_calloc(n,size);if(p){CHECK(live_count<4096);live[live_count++]=p;if(n==1&&size==sizeof(CohWrTexDefaults))watched=p;}return p;
}
void __wrap_free(void*p){if(p==watched)watched=NULL;for(uint32_t i=0;i<live_count;i++)if(live[i]==p){live[i]=live[--live_count];break;}__real_free(p);}
static void put(uint8_t*p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
static CohStatus readat(void*v,uint64_t at,void*out,size_t n){Memory*m=v;if(at>m->size||n>m->size-at)return COH_IO;memcpy(out,m->data+(size_t)at,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;digests++;if(fail_digest&&digests==fail_digest)return COH_IO;SHA256(b.data,b.size,out);if(mismatch_digest&&digests==mismatch_digest)out[0]^=1;return COH_OK;}
static CohStatus hold(void*v){Fixture*f=v;CHECK(!f->held);f->held=1;holds++;return COH_OK;}
static void drop(void*v){Fixture*f=v;CHECK(f->held);f->held=0;drops++;}
static int poll(void*v){
 (void)v;polls++;
 if(observe_reentry){
  CohWrTexNamespace*before=observed;CHECK(coh_wr_tex_namespace_destroy(&observed)==COH_STATE&&observed==before);
  if(older){
   CohWrTexNamespaceReport ns;CohStatus state=coh_wr_tex_namespace_report(observed,&ns);
   if(state==COH_STATE){CohWrTexDefaults*saved=older;CHECK(coh_wr_tex_defaults_destroy(&older)==COH_STATE&&older==saved);}
   else {
    CHECK(state==COH_OK); /* final direct poll: only candidate pins guard source */
    if(retire_old_final&&watched&&watched->report.selected_mask==127){
     CHECK(coh_wr_tex_defaults_destroy(&older)==COH_OK&&!older);
     CHECK(coh_wr_tex_namespace_destroy(&observed)==COH_STATE&&observed==before);
    }
   }
  }
 }
 if(final_cancel&&watched&&watched->report.selected_mask==127)return 1;
 return stop_at&&polls==stop_at;
}
static Fixture*fresh(void){Fixture*f=calloc(1,sizeof(*f));CHECK(f);return f;}
static void add_body(Fixture*f,const char*path,const uint8_t*data,size_t size){
 CHECK(f->count<20&&strlen(path)<260);uint32_t i=f->count++;strcpy(f->paths[i],path);
 f->memory[i]=(Memory){malloc(size),size};CHECK(f->memory[i].data);memcpy(f->memory[i].data,data,size);f->bytes+=size;
 f->files[i]=(CohWrTexNamespaceFile){f->paths[i],11,0,{readat,f->memory+i,size,7}};
}
static void add_controlled(Fixture*f,const char*dir,const char*key,uint32_t alpha){
 char name[260],path[260];int n=snprintf(name,sizeof(name),"texture_library/%s/%s.dds",dir,key);CHECK(n>0&&(size_t)n<sizeof(name));
 n=snprintf(path,sizeof(path),"texture_library/%s/%s.texture",dir,key);CHECK(n>0&&(size_t)n<sizeof(path));
 uint8_t body[400]={0};size_t header=32+strlen(name)+1;CHECK(header+1<sizeof(body));
 put(body,(uint32_t)header);put(body+4,1);put(body+8,8);put(body+12,8);body[28]=(uint8_t)alpha;memcpy(body+29,"TX2",3);memcpy(body+32,name,strlen(name)+1);body[header]=91;
 add_body(f,path,body,header+1);
}
static void make_namespace(Fixture*f,uint32_t leases){
 f->root=(CohWrTexNamespaceRoot){f->files,f->count,7,"/controlled/complete/finite/native/data"};
 CohWrTexNamespaceRequest q={0};q.roots=&f->root;q.root_count=1;q.input_generation=33;q.mode=COH_WR_TEX_NS_I_LIKE_PIGS;q.development_data=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;q.provider_context=f;
 CohWrTexNamespaceLimits l={0};l.owned_limit=1024*1024;l.aggregate_limit=16*1024*1024;
 /* Known live heap bodies+provider object, immutable embedded donor16,514,
  * oracle/control arrays, fixture/code/runtime allowance. Policy, not RSS. */
 l.external_bytes=f->bytes+sizeof(*f)+16514+256*1024;
 l.record_limit=64;l.node_limit=128;l.basic_limit=32;l.body_lease_limit=leases;
 l.loader=(CohAssetLimits){1024*1024,128*1024,128*1024,128*1024,32,20,16};
 CHECK(coh_wr_tex_namespace_build(&q,&l,(CohCancel){0},&f->source)==COH_OK);
}
static Fixture*controlled(uint32_t mask,uint32_t duplicate,uint32_t leases){
 Fixture*f=fresh();for(uint32_t i=0;i<7;i++)if(mask&(1u<<i))add_controlled(f,"middle",keys[i],1);
 if(duplicate){add_controlled(f,"aaa","INVISIBLE",1);add_controlled(f,"zzz","invisible",1);add_controlled(f,"aaa","WHITE",0);}
 add_controlled(f,"extras","unrelated",1);make_namespace(f,leases);return f;
}
static Fixture*authentic(uint32_t leases){Fixture*f=fresh();for(uint32_t i=0;i<7;i++)add_body(f,actual_defaults[i].path,actual_defaults[i].data,actual_defaults[i].size);make_namespace(f,leases);return f;}
static void retire(Fixture*f){
 CHECK(coh_wr_tex_namespace_destroy(&f->source)==COH_OK&&!f->source&&!f->held);
 for(uint32_t i=0;i<f->count;i++){memset(f->memory[i].data,0,f->memory[i].size);retired_bytes+=f->memory[i].size;free(f->memory[i].data);}
 memset(f,0,sizeof(*f));free(f);freed_contexts++;
}
static CohWrTexDefaultsLimits limits_for(Fixture*f){CohWrTexNamespaceReport report;CHECK(coh_wr_tex_namespace_report(f->source,&report)==COH_OK);return(CohWrTexDefaultsLimits){1024*1024,32*1024*1024,report.aggregate_reserved_bytes};}
static CohWrTexDefaultsProfile profile={1,1};
static DefaultsOracle oracle_for(Fixture*f){
 CohWrTexNamespaceReport report;CHECK(coh_wr_tex_namespace_report(f->source,&report)==COH_OK&&report.basic_rows<=32);
 const char*names[32];uint32_t flags[32];for(uint32_t i=0;i<report.basic_rows;i++){CohWrTexNamespaceBasic b;CHECK(coh_wr_tex_namespace_basic(f->source,i,&b)==COH_OK);names[i]=b.basic_key;flags[i]=b.initial_basic_flags;}
 DefaultsOracle oracle;original_defaults(names,flags,report.basic_rows,&oracle);CHECK(oracle.lookup_count==7);return oracle;
}
static void compare(Fixture*f,CohWrTexDefaults*r,const DefaultsOracle*o){
 CohWrTexDefaultsReport report;CHECK(coh_wr_tex_defaults_report(r,&report)==COH_OK);CHECK(report.selected_mask==o->selected_mask&&report.cold_initial==1&&report.guarded_short_keys==1&&report.unresolved_client_semantics==1&&report.source_input_generation==33);
 uint32_t count=0;for(uint32_t i=0;i<7;i++){
  CohWrTexDefaultsBasic b;memset(&b,0xa5,sizeof(b));CohWrTexDefaultsBasic before=b;
  CohBytes bytes={(const uint8_t*)1,99},sentinel=bytes;
  if(o->rows[i]==UINT32_MAX){CHECK(coh_wr_tex_defaults_role(r,i,&b)==COH_NOT_FOUND&&!memcmp(&b,&before,sizeof(b)));CHECK(coh_wr_tex_defaults_body(r,i,&bytes)==COH_NOT_FOUND&&!memcmp(&bytes,&sentinel,sizeof(bytes)));continue;}
  count++;CHECK(coh_wr_tex_defaults_role(r,i,&b)==COH_OK);comparisons++;CHECK(b.source.row==o->rows[i]&&b.source.first_owner_row==b.source.row&&b.effective_basic_flags==o->flags[b.source.row]);
  CHECK(coh_wr_tex_defaults_body(r,i,&bytes)==COH_OK);uint8_t hash[32];SHA256(bytes.data,bytes.size,hash);CHECK(!memcmp(hash,b.source.sha256,32)&&b.source.asset.generation==7);
 }
 CHECK(count==report.selected_count);
 for(uint32_t i=0;i<report.basic_rows;i++){
  CohWrTexDefaultsBasic b,alias;CohWrTexNamespaceBasic initial;CHECK(coh_wr_tex_namespace_basic(f->source,i,&initial)==COH_OK);
  CHECK(coh_wr_tex_defaults_basic(r,i,&b)==COH_OK&&coh_wr_tex_defaults_basic(r,i,&alias)==COH_OK);comparisons++;
  CHECK(b.effective_basic_flags==o->flags[i]&&alias.effective_basic_flags==b.effective_basic_flags&&b.source.initial_basic_flags==initial.initial_basic_flags);
  CHECK(b.source.asset.path==initial.asset.path&&!memcmp(b.source.sha256,initial.sha256,32));
  if(i==o->rows[2])CHECK((initial.initial_basic_flags&1u)&&!(b.effective_basic_flags&1u));
  else CHECK(initial.initial_basic_flags==b.effective_basic_flags);
 }
 CHECK(coh_wr_tex_defaults_report(r,&r->report)==COH_INVALID);
 CohWrTexDefaultsBasic b;memset(&b,0x5a,sizeof(b));CohWrTexDefaultsBasic sentinel=b;CHECK(coh_wr_tex_defaults_role(r,7,&b)==COH_INVALID&&!memcmp(&b,&sentinel,sizeof(b)));CHECK(coh_wr_tex_defaults_basic(r,report.basic_rows,&b)==COH_NOT_FOUND&&!memcmp(&b,&sentinel,sizeof(b)));
 CohWrTexNamespace*saved=f->source;CHECK(coh_wr_tex_namespace_destroy(&f->source)==COH_STATE&&f->source==saved);
}
static void case_for(Fixture*f,uint32_t actual){
 cases++;DefaultsOracle o=oracle_for(f);CohWrTexDefaultsLimits l=limits_for(f);CohWrTexDefaults*r=NULL;
 CohStatus status=coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&r);
 if(!o.required_present){CHECK(status==COH_NOT_FOUND&&!r);retire(f);return;}
 CHECK(status==COH_OK&&r);compare(f,r,&o);
 if(actual){CohWrTexDefaultsReport report;CHECK(coh_wr_tex_defaults_report(r,&report)==COH_OK);authentic_owned=report.owned_bytes;authentic_aggregate=report.aggregate_reserved_bytes;authentic_namespace=l.external_bytes;authentic_external=f->bytes+sizeof(*f)+16514+256*1024;authentic_bodies=f->bytes;}
 CHECK(coh_wr_tex_defaults_destroy(&r)==COH_OK&&!r);retire(f);
}
int main(void){
 case_for(authentic(16),1);
 for(uint32_t mask=0;mask<128;mask++)case_for(controlled(mask,0,16),0);
 case_for(controlled(127,1,16),0);
 Fixture*f=authentic(16);CohWrTexDefaultsLimits l=limits_for(f);CohWrTexDefaults*r=NULL;
 CohWrTexDefaultsProfile badp={0,1};uint32_t prior_digests=digests;
 CHECK(coh_wr_tex_defaults_build(f->source,&badp,&l,(CohCancel){poll,NULL},&r)==COH_UNSUPPORTED&&!r&&digests==prior_digests);
 badp=(CohWrTexDefaultsProfile){1,0};CHECK(coh_wr_tex_defaults_build(f->source,&badp,&l,(CohCancel){poll,NULL},&r)==COH_UNSUPPORTED&&!r&&digests==prior_digests);
 CohWrTexDefaultsLimits bad=l;bad.owned_limit=sizeof(CohWrTexDefaults)-1;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&bad,(CohCancel){poll,NULL},&r)==COH_LIMIT&&!r&&digests==prior_digests);
 bad=l;bad.external_bytes--;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&bad,(CohCancel){poll,NULL},&r)==COH_LIMIT&&!r&&digests==prior_digests);
 bad=l;bad.external_bytes=SIZE_MAX;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&bad,(CohCancel){poll,NULL},&r)==COH_LIMIT&&!r&&digests==prior_digests);
 CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&r)==COH_OK);CohWrTexDefaultsReport report;CHECK(coh_wr_tex_defaults_report(r,&report)==COH_OK);CHECK(coh_wr_tex_defaults_destroy(&r)==COH_OK);
 bad=l;bad.aggregate_limit=report.aggregate_reserved_bytes-1;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&bad,(CohCancel){poll,NULL},&r)==COH_LIMIT&&!r&&digests>=prior_digests);
 CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},(CohWrTexDefaults**)&l)==COH_INVALID);
 observed=f->source;observe_reentry=1;polls=0;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){poll,NULL},&r)==COH_OK);uint32_t cancellation_points=polls;CHECK(cancellation_points>=15);CHECK(coh_wr_tex_defaults_destroy(&r)==COH_OK);
 for(uint32_t i=1;i<=cancellation_points;i++){polls=0;stop_at=i;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){poll,NULL},&r)==COH_CANCELLED&&!r);}
 stop_at=0;final_cancel=1;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){poll,NULL},&r)==COH_CANCELLED&&!r&&!watched);final_cancel=0;observe_reentry=0;observed=NULL;
 for(uint32_t i=1;i<=7;i++){
  digests=0;fail_digest=i;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&r)==COH_IO&&!r);fail_digest=0;
  digests=0;mismatch_digest=i;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&r)==COH_INVALID&&!r);mismatch_digest=0;
 }
 allocations=0;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&r)==COH_OK);uint32_t allocation_points=allocations;CHECK(coh_wr_tex_defaults_destroy(&r)==COH_OK);
 for(uint32_t i=1;i<=allocation_points;i++){allocations=0;fail_allocation=i;CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&r)==COH_LIMIT&&!r);}fail_allocation=0;
 CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&older)==COH_OK);CohWrTexDefaultsReport old;CHECK(coh_wr_tex_defaults_report(older,&old)==COH_OK);old_owned=old.owned_bytes;
 l.external_bytes+=old.owned_bytes;observed=f->source;observe_reentry=1;
 CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){poll,NULL},&r)==COH_OK);observe_reentry=0;observed=NULL;
 CHECK(coh_wr_tex_defaults_report(r,&report)==COH_OK);old_new_aggregate=report.aggregate_reserved_bytes;DefaultsOracle o=oracle_for(f);compare(f,older,&o);compare(f,r,&o);
 CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&r)==COH_INVALID&&r);
 CHECK(coh_wr_tex_defaults_destroy(&older)==COH_OK&&!older);compare(f,r,&o);CHECK(coh_wr_tex_defaults_destroy(&r)==COH_OK);
 /* An independent owner may actually retire in the final nonbusy poll. Its
  * retirement is NOT undone by candidate cancellation or own-output rollback. */
 CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&older)==COH_OK);
 observed=f->source;observe_reentry=retire_old_final=final_cancel=1;
 CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){poll,NULL},&r)==COH_CANCELLED&&!r&&!older);
 observe_reentry=retire_old_final=final_cancel=0;observed=NULL;retire(f);
 for(uint32_t capacity=1;capacity<7;capacity++){f=authentic(capacity);l=limits_for(f);CHECK(coh_wr_tex_defaults_build(f->source,&profile,&l,(CohCancel){0},&r)==COH_LIMIT&&!r);retire(f);}
 CHECK(coh_wr_tex_defaults_destroy(NULL)==COH_INVALID&&coh_wr_tex_defaults_destroy(&r)==COH_INVALID);CHECK(holds==drops&&!live_count);
 printf("{\"checks\":%u,\"whole_original_row_and_role_comparisons\":%u,\"finite_provider_cases\":%u,\"cancellation_failure_points\":%u,\"digest_failure_positions\":7,\"digest_mismatch_positions\":7,\"allocation_failure_points\":%u,\"partial_lease_capacity_refusals\":6,\"provider_holds\":%u,\"provider_drops\":%u,\"provider_contexts_and_bodies_actually_freed\":%u,\"tracked_calloc_blocks_live\":%u,\"authentic_seven_body_bytes\":%zu,\"authentic_defaults_owned_bytes\":%zu,\"authentic_namespace_full_aggregate_reserved_bytes\":%zu,\"authentic_defaults_aggregate_reserved_bytes\":%zu,\"authentic_known_provider_and_fixture_external_policy_bytes\":%zu,\"actual_simultaneous_old_defaults_owned_bytes\":%zu,\"actual_old_and_candidate_aggregate_reserved_bytes\":%zu,\"all_freed_provider_body_bytes\":%zu,\"invisible_same_row_alias_clear_and_cold_namespace_preserved\":true,\"last_actual_selection_cancellation_preserves_own_output\":true,\"independent_old_owner_actually_retired_in_final_poll_not_restored\":true,\"old_qualifier_replayed\":false}\n",checks,comparisons,cases,cancellation_points,allocation_points,holds,drops,freed_contexts,live_count,authentic_bodies,authentic_owned,authentic_namespace,authentic_aggregate,authentic_external,old_owned,old_new_aggregate,retired_bytes);
 return 0;
}
