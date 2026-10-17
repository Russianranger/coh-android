/* Explicit orchestration substitutions, NOT real quiet/export/owner proofs. */
#include "source_groups_eligibility.inc"
#include "source_groups_transaction.inc"
BOUNDARY_REPORT_TYPES
static unsigned checks,quiet,quiet_begin_status=1,quiet_end_status=1,owner_fail,export_fail,events,aborts,commits,fail_kind,open_calls,write_calls,packet_calls,mutation,reenter;
int folder_cache_update_enable=0,folder_cache_manual_callback_check=1;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"boundary line%d: %s\n",__LINE__,#x);abort();}}while(0)
int coh_resource_quiescence_begin(void){CHECK(!quiet);events++;if(quiet_begin_status==1)quiet=1;return (int)quiet_begin_status;}
int coh_resource_quiescence_end(void){CHECK(quiet);events++;if(quiet_end_status==1)quiet=0;return (int)quiet_end_status;}
static int coh_source_groups_prepare_owner(const NetLink*l,CohSourceGroupsOwner*out){CHECK(quiet);if(owner_fail)return 0;memset(out,0,sizeof(*out));memcpy(out->wire,"fixture-owner",13);memcpy(out->wire+120,&l->last_update_time,4);memcpy(out->wire+124,&l->last_world_id,4);out->wire[20]=(unsigned char)mutation;return 1;}
static int coh_source_catalog_export(CohSourceCatalogOutputFn fn,void*c,unsigned gen,CohSourceCatalogExportReport*r){unsigned char raw[48]={0};CHECK(quiet&&gen);if(export_fail==1)return 3;r->total_bytes=r->emitted_bytes=48;return fn(c,raw,48)?0:5;}
static int coh_source_runtime_snapshot_export(CohSourceCatalogOutputFn fn,void*c,const unsigned char*head,const CohSourceCatalogExportReport*cat,CohSourceSnapshotReport*r){unsigned char raw[80]={0};CHECK(quiet&&head&&cat->emitted_bytes==48);if(export_fail==2)return 3;r->total_bytes=r->emitted_bytes=80;return fn(c,raw,80)?0:5;}
static int coh_source_resources_export(CohSourceCatalogOutputFn fn,void*c,const unsigned char*head,const CohSourceCatalogExportReport*cat,unsigned char*scratch,unsigned size,CohSourceResourceReport*r){unsigned char raw[192]={0};CHECK(quiet&&head&&cat->emitted_bytes==48&&scratch&&size==131072);if(export_fail==3)return 3;r->total_bytes=r->emitted_bytes=192;return fn(c,raw,192)?0:5;}
#include "source_groups_boundary.inc"
static unsigned char packet_copy[1<<20];static unsigned packet_bits;
static int sink_open(void*c,unsigned id){CohGroupsTransactionHooks out;CohGroupsBoundarySink empty; (void)c;CHECK(quiet&&id&&coh_groups_boundary.phase==1);open_calls++;memset(&empty,0,sizeof(empty));CHECK(!coh_groups_boundary_prepare(&empty,&out));CHECK(!coh_groups_boundary_begin(NULL,coh_groups_boundary.link,1));return fail_kind!=1;}
static int sink_write(void*c,unsigned id,unsigned kind,const unsigned char*p,unsigned n){(void)c;CHECK(quiet&&id&&p&&n&&kind>=1&&kind<=5);write_calls++;events++;if(reenter)CHECK(!coh_groups_boundary_begin(NULL,coh_groups_boundary.link,1));return fail_kind!=kind+1;}
static int sink_packet(void*c,unsigned id,const unsigned char*p,unsigned bits,unsigned aligned,unsigned compress,const CohGroupsEligibilityReport*r,const CohSourceCatalogExportReport*cat,const CohSourceSnapshotReport*snap,const CohSourceResourceReport*res){(void)c;CHECK(quiet&&id&&p&&bits&&aligned==1&&compress==1&&r&&r->records&&cat->emitted_bytes==48&&snap->emitted_bytes==80&&res->emitted_bytes==192);packet_calls++;CHECK((bits+7)/8<sizeof(packet_copy));memcpy(packet_copy,p,(bits+7)/8);packet_bits=bits;return fail_kind!=7;}
static int sink_commit(void*c,unsigned id){(void)c;CHECK(!quiet&&id);commits++;return fail_kind!=8;}
static void sink_abort(void*c,unsigned id){(void)c;CHECK(id);aborts++;}
static void reset_boundary(void){CohGroupsBoundarySink sink={sink_open,sink_write,sink_packet,sink_commit,sink_abort,NULL};CHECK(!quiet);memset(&coh_groups_boundary,0,sizeof(coh_groups_boundary));memset(&coh_groups_transaction_hooks,0,sizeof(coh_groups_transaction_hooks));coh_groups_transaction_active=0;quiet_begin_status=quiet_end_status=1;owner_fail=export_fail=events=aborts=commits=fail_kind=open_calls=write_calls=packet_calls=mutation=reenter=packet_bits=0;folder_cache_update_enable=0;folder_cache_manual_callback_check=1;CHECK(coh_groups_boundary_prepare(&sink,&coh_groups_transaction_hooks));CHECK(!open_calls&&!write_calls&&!quiet&&!coh_groups_boundary.phase);}
BOUNDARY_ORIGINAL_WORLD
int main(void){unsigned i,bits,footer[4];unsigned char wire[1<<20];NetLink link;CohGroupsBoundarySink bad;CohGroupsTransactionHooks out,save;
 reset_boundary();CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(!quiet&&open_calls==1&&packet_calls==1&&commits==1&&!aborts&&!coh_groups_boundary.phase);CHECK(bits==packet_bits&&!memcmp(wire,packet_copy,(bits+7)/8));
 for(i=1;i<=8;i++){reset_boundary();fail_kind=i;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(!quiet&&!coh_groups_boundary.phase&&aborts==1);CHECK(commits==(i==8));}
 for(i=1;i<=3;i++){reset_boundary();export_fail=i;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(aborts==1&&!packet_calls&&!quiet);}
 reset_boundary();owner_fail=1;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(!open_calls&&!packet_calls&&!aborts&&!quiet);
 reset_boundary();quiet_begin_status=7;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(!open_calls&&!packet_calls&&!quiet);
 reset_boundary();folder_cache_update_enable=1;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(!events&&!quiet);folder_cache_update_enable=0;
 reset_boundary();folder_cache_manual_callback_check=0;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(!events&&!quiet);folder_cache_manual_callback_check=1;
 reset_boundary();reenter=1;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(commits==1&&!aborts&&!quiet);
 reset_boundary();coh_groups_boundary.next=0xffffffffu;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(!events&&!open_calls);
 reset_boundary();memset(&bad,0,sizeof(bad));memset(&out,0xa5,sizeof(out));save=out;CHECK(!coh_groups_boundary_prepare(&bad,&out)&&!memcmp(&save,&out,sizeof(out)));
 /* Late source owner change and malformed packet retain provisional outputs. */
 reset_boundary();link.last_update_time=0;link.last_world_id=0;coh_groups_transaction_begin(&link,1);CHECK(quiet&&coh_groups_transaction_active);mutation=1;coh_groups_transaction_finish(&oracle_packet);CHECK(!quiet&&aborts==1&&!commits);
 reset_boundary();coh_groups_transaction_begin(&link,1);CHECK(quiet);oracle_packet.stream.bitLength=0;coh_groups_transaction_finish(&oracle_packet);CHECK(!quiet&&aborts==1&&!commits);
 /* Aggregate output budget check occurs before sink callback/read. */
 reset_boundary();CHECK(coh_groups_boundary_begin(NULL,&link,1));i=write_calls;coh_groups_boundary.bytes=COH_GROUPS_BOUNDARY_MAX_BYTES;CHECK(!coh_groups_boundary_record(NULL,(const unsigned char*)"x",64)&&write_calls==i);coh_groups_boundary_abort(NULL,coh_groups_boundary.id);CHECK(!quiet&&aborts==1);
 /* Failed real release cannot be forged successful; helper is quarantined. */
 reset_boundary();quiet_end_status=0;CHECK(groups_original(8,1,0,wire,&bits,footer));CHECK(quiet&&coh_groups_boundary.blocked&&aborts==1&&!commits);CHECK(!coh_groups_boundary_begin(NULL,&link,1));quiet_end_status=1;CHECK(coh_resource_quiescence_end()==1);CHECK(!quiet);CHECK(!coh_groups_boundary_prepare(&bad,&out));
 printf("{\"passed\":true,\"checks\":%u,\"static_helper_bytes\":%zu,\"original_world_producer_executed\":true,\"quiet_export_owner_dependencies_substituted\":true,\"real_server_executed\":false,\"live_groups_captured\":false}\n",checks,sizeof(coh_groups_boundary));return 0;}
