#include "coh_catalog_seed.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static size_t allocations,alive,fault_at,fault_seen;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){allocations++;if(fault_at&&++fault_seen==fault_at)return NULL;void*p=__real_malloc(n);if(p)alive++;return p;}
void *__wrap_calloc(size_t n,size_t size){allocations++;if(fault_at&&++fault_seen==fault_at)return NULL;void*p=__real_calloc(n,size);if(p)alive++;return p;}
void __wrap_free(void*p){if(p){if(!alive)abort();alive--;}__real_free(p);}
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"runtimegroups line%d %s\n",__LINE__,#x);abort();}}while(0)
static CohBytes load(const char *name){FILE *f=fopen(name,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0);rewind(f);unsigned char *p=malloc((size_t)n);CHECK(p);CHECK(fread(p,1,(size_t)n,f)==(size_t)n);fclose(f);return(CohBytes){p,(size_t)n};}
static CohStatus digest(void *context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_INVALID;}
typedef struct {const CohRuntimeGraph*graph;unsigned seen,emitted,omitted,external,refuse;} SeedStage;
static CohStatus stage(void*ctx,const CohCatalogSeedRecord*r){SeedStage*s=ctx;CohRuntimeGraphNode n;CHECK(coh_runtime_graph_node(s->graph,r->node,&n)==COH_OK);CHECK(r->wire.data==n.wire.data&&r->wire.size==n.wire.size&&r->wire_bits==n.wire_bits&&r->external==n.external);s->seen++;s->emitted+=r->emitted;s->omitted+=!r->emitted&&!r->external;s->external+=r->external;return s->refuse&&s->seen==s->refuse?COH_CANCELLED:COH_OK;}
int main(int argc,char **argv){
 CHECK(argc==6);CohBytes catalog=load(argv[1]),snapshot=load(argv[2]),wire=load(argv[3]),witness=load(argv[4]);
 uint32_t generation=(uint32_t)catalog.data[20]|(uint32_t)catalog.data[21]<<8|(uint32_t)catalog.data[22]<<16|(uint32_t)catalog.data[23]<<24;
 CohCatalogBinding cb={0};cb.owner_generation=1;cb.catalog_generation=1;cb.asset_generation=generation;memset(cb.source_sha256,0x11,32);memset(cb.inventory_sha256,0x33,32);CHECK(digest(NULL,catalog,cb.catalog_sha256)==COH_OK);
 CohCatalogOwner *owner=NULL;CohCatalogOwnerBudget ob={COH_SG_MEMORY_MAX,COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohCatalogDigest d={NULL,digest};CohCatalogOwnerReport or;
 /* Catalog owner catalog_generation is original wire cataloggeneration. */
 cb.catalog_generation=generation;CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&d,&owner,&or)==COH_OK);CohBytes owned;CHECK(coh_catalog_owner_bytes(owner,&owned)==COH_OK);
 CohRuntimeGraphBinding binding={0};binding.generation=1;binding.catalog_generation=generation;binding.pins.asset_generation=generation;memcpy(binding.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(binding.pins.source_sha256,cb.source_sha256,32);memset(binding.pins.run_sha256,0x22,32);binding.pins.digest=digest;CHECK(digest(NULL,snapshot,binding.pins.snapshot_sha256)==COH_OK);
 CohRuntimeSnapshotBudget budget={COH_SG_TRANSACTION_MAX,262144+coh_catalog_owner_owned_bytes(owner)};CohRuntimeGraph *graph=NULL;CohRuntimeGraphReport gr;CHECK(coh_runtime_graph_build(NULL,owned,snapshot,&binding,&budget,NULL,&graph,&gr)==COH_OK);
 CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,wire,wire.size*8,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);uint32_t command;CHECK(coh_rep_pack(&reader,1,&command)==COH_OK&&command==COH_REP_GROUPS);CohRepReader before=reader;
 CohRuntimeGroupsWitnessBinding wb={0};wb.graph_generation=binding.generation;wb.catalog_generation=generation;wb.observation_id=7;wb.map_generation=11;wb.selection_generation=22;wb.selected_dbid=33;memset(wb.session_sha256,0x44,32);memcpy(wb.catalog_sha256,binding.pins.catalog_sha256,32);memcpy(wb.snapshot_sha256,binding.pins.snapshot_sha256,32);memcpy(wb.source_sha256,binding.pins.source_sha256,32);memcpy(wb.run_sha256,binding.pins.run_sha256,32);CHECK(digest(NULL,witness,wb.witness_sha256)==COH_OK);CHECK(digest(NULL,wire,wb.packet_sha256)==COH_OK);
 CohRuntimeGroupsWitnessBudget wbudget={COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohRuntimeGroupsWitnessReport wr;memset(&wr,0x5a,sizeof(wr));CohRuntimeGroupsWitness *wowner=NULL;
 CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&wb,&wbudget,&d,&wowner,&wr)==COH_OK);CHECK(wowner&&!wr.source_generation_admitted&&!wr.world_authority);
 size_t capacity=gr.nodes+3;uint8_t*mask=malloc(capacity);CHECK(mask);memset(mask,0x5a,capacity);CohRuntimeGroupsBudget gb={COH_SG_TRANSACTION_MAX,262144};CohCatalogSeedReport report,prior;memset(&report,0xa5,sizeof(report));prior=report;SeedStage state={graph,0,0,0,0,0};size_t before_allocations=allocations;
 CHECK(coh_catalog_seed_visit(graph,owner,wowner,&wb,&reader,&gb,mask,capacity,stage,&state,&report)==COH_OK);CHECK(allocations==before_allocations);CHECK(state.seen==gr.nodes&&state.emitted==wr.eligible_definitions&&state.omitted==wr.saved_omissions&&state.external==gr.source.external_count);CHECK(report.protocol_wire_inputs_complete&&!report.client_derived_state_complete&&!report.bounds_cache_checksums_recomputed&&!report.source_generation_admitted&&!report.world_authority);CHECK(report.allocated_definitions==gr.source.definitions&&report.applied_equal_updates==state.emitted&&report.omitted_definitions==state.omitted);CHECK(mask[gr.nodes]==0x5a&&mask[gr.nodes+1]==0x5a);
 state=(SeedStage){graph,0,0,0,0,2};report=prior;CHECK(coh_catalog_seed_visit(graph,owner,wowner,&wb,&reader,&gb,mask,capacity,stage,&state,&report)==COH_CANCELLED&&!memcmp(&report,&prior,sizeof(report)));CHECK(state.seen==2); /* discard complete provisional callback stage */
 state=(SeedStage){graph,0,0,0,0,0};memset(mask,0x5a,capacity);unsigned char*p=(unsigned char*)wire.data+wire.size-1;*p^=1;CHECK(coh_catalog_seed_visit(graph,owner,wowner,&wb,&reader,&gb,mask,capacity,stage,&state,&report)!=COH_OK&&!state.seen&&!memcmp(&report,&prior,sizeof(report))&&mask[0]==0x5a);*p^=1;
 CohRuntimeGroupsWitnessBinding changed=wb;changed.selection_generation++;CHECK(coh_catalog_seed_visit(graph,owner,wowner,&changed,&reader,&gb,mask,capacity,stage,&state,&report)!=COH_OK&&!state.seen&&!memcmp(&report,&prior,sizeof(report)));
 CHECK(coh_catalog_seed_visit(graph,owner,wowner,&wb,&reader,&gb,mask,gr.nodes-1,stage,&state,&report)==COH_LIMIT&&!state.seen&&!memcmp(&report,&prior,sizeof(report)));
 CHECK(coh_catalog_seed_visit(graph,owner,wowner,&wb,&reader,&gb,(uint8_t*)&report,capacity,stage,&state,&report)==COH_INVALID&&!state.seen&&!memcmp(&report,&prior,sizeof(report)));
 CHECK(coh_catalog_seed_visit(graph,owner,wowner,&wb,&reader,&gb,mask,capacity,stage,&state,&report)==COH_OK);size_t named=report.aggregate_reserved_bytes;gb.aggregate_limit=named-1;state.seen=0;report=prior;CHECK(coh_catalog_seed_visit(graph,owner,wowner,&wb,&reader,&gb,mask,capacity,stage,&state,&report)==COH_LIMIT&&!state.seen&&!memcmp(&report,&prior,sizeof(report)));CHECK(!memcmp(&reader,&before,sizeof(reader)));
 free(mask);coh_runtime_groups_witness_release(wowner);coh_runtime_graph_free(graph);coh_catalog_owner_release(owner);free((void*)catalog.data);free((void*)snapshot.data);free((void*)wire.data);free((void*)witness.data);CHECK(alive==0);
 printf("{\"passed\":true,\"checks\":%u,\"protocol_wire_inputs_complete\":true,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks);return 0;
}
