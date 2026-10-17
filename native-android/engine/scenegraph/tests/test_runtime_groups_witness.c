#include "coh_runtime_groups_witness.h"
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
typedef struct {size_t positions[128],remove_at,remove_bytes;unsigned count;} Positions;
static CohStatus positions(void *context,const CohGroupsEvent *e){Positions *p=context;size_t at=e->span.cursor/8;
 if(e->kind==COH_GROUPS_DEFINITION&&!e->file&&!p->remove_bytes){p->remove_at=at;p->remove_bytes=(e->span.bits-e->span.cursor)/8;}
 if(p->count<128){if(e->kind==COH_GROUPS_FILE_HEADER)at+=1;else if(e->kind==COH_GROUPS_DEFINITION)at+=5;else at+=4;
  if(at<e->span.bits/8&&e->span.bytes.data[at])p->positions[p->count++]=at;}
 return COH_OK;}
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
 CohRuntimeGroupsWitnessBudget wbudget={COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohRuntimeGroupsWitnessReport wr,wrprior;memset(&wr,0x5a,sizeof(wr));wrprior=wr;CohRuntimeGroupsWitness *wowner=NULL;
 CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&wb,&wbudget,&d,&wowner,&wr)==COH_OK);CHECK(wowner&&!wr.source_generation_admitted&&!wr.world_authority);
 CohRuntimeGroupsReport report,prior;memset(&report,0x41,sizeof(report));prior=report;CohRuntimeGroupsBudget gb={COH_SG_TRANSACTION_MAX,262144};
 size_t before_allocations=allocations;CHECK(coh_runtime_graph_compare_groups_witness(graph,owner,wowner,&wb,&reader,&gb,&report)==COH_OK);CHECK(allocations==before_allocations);CHECK(!memcmp(&reader,&before,sizeof(reader))&&!report.source_generation_admitted&&!report.world_authority&&!report.assets_admitted);
 CHECK((coh_runtime_graph_compare_groups(graph,owner,&reader,&gb,&report)==COH_OK)==(argv[5][0]!='1'));
 {unsigned char*p=(unsigned char*)witness.data;*p^=1;CHECK(coh_runtime_graph_compare_groups_witness(graph,owner,wowner,&wb,&reader,&gb,&report)==COH_OK);*p^=1;}
 {unsigned char*p=(unsigned char*)wire.data+wire.size-1;*p^=1;report=prior;CHECK(coh_runtime_graph_compare_groups_witness(graph,owner,wowner,&wb,&reader,&gb,&report)!=COH_OK&&!memcmp(&report,&prior,sizeof(report)));*p^=1;}
 CHECK(coh_runtime_groups_witness_retain(wowner)==COH_OK);coh_runtime_groups_witness_release(wowner);
 CohRuntimeGroupsWitness *bad=NULL;CohRuntimeGroupsWitnessBinding changed=wb;changed.run_sha256[0]^=1;
 CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&changed,&wbudget,&d,&bad,&wrprior)!=COH_OK&&!bad);
 for(unsigned field=0;field<7;field++){changed=wb;if(field==0)changed.selected_dbid++;if(field==1)changed.selection_generation++;if(field==2)changed.map_generation++;if(field==3)changed.run_sha256[0]^=1;if(field==4)changed.observation_id++;if(field==5)changed.packet_sha256[0]^=1;if(field==6)changed.graph_generation++;report=prior;CHECK(coh_runtime_graph_compare_groups_witness(graph,owner,wowner,&changed,&reader,&gb,&report)!=COH_OK&&!memcmp(&report,&prior,sizeof(report)));}
 for(size_t end=0;end<witness.size;end++){CohRuntimeGroupsWitnessReport unchanged=wrprior;CohBytes shortw={witness.data,end};changed=wb;CHECK(digest(NULL,shortw,changed.witness_sha256)==COH_OK);CHECK(coh_runtime_groups_witness_create(graph,owner,shortw,&reader,&changed,&wbudget,&d,&bad,&wrprior)!=COH_OK&&!bad&&!memcmp(&wrprior,&unchanged,sizeof(unchanged)));}
 for(unsigned f=1;f<=4;f++){size_t oldalive=alive;CohRuntimeGroupsWitnessReport unchanged=wrprior;fault_at=f;fault_seen=0;CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&wb,&wbudget,&d,&bad,&wrprior)==COH_LIMIT&&!bad);fault_at=0;CHECK(alive==oldalive&&!memcmp(&wrprior,&unchanged,sizeof(unchanged)));}
 size_t saved_limit=wbudget.owned_limit;wbudget.owned_limit=wr.owned_bytes-1;CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&wb,&wbudget,&d,&bad,&wrprior)==COH_LIMIT&&!bad);wbudget.owned_limit=saved_limit;
 CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&wb,&wbudget,&d,&bad,(CohRuntimeGroupsWitnessReport*)witness.data)==COH_INVALID&&!bad);
 {unsigned char*late=malloc(wire.size+1);CHECK(late);memcpy(late,wire.data,wire.size);late[wire.size]=0;CohRepReader late_reader;CHECK(coh_rep_reader_bounded(&late_reader,(CohBytes){late,wire.size+1},(wire.size+1)*8,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);late_reader.cursor=before.cursor;changed=wb;CHECK(digest(NULL,late_reader.bytes,changed.packet_sha256)==COH_OK);CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&late_reader,&changed,&wbudget,&d,&bad,&wrprior)!=COH_OK&&!bad);free(late);}
 changed=wb;changed.selected_dbid=0x80000000u;CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&changed,&wbudget,&d,&bad,&wrprior)==COH_STATE&&!bad);
 /* The exact SHA is over copied bytes, not accepted caller labels. */
 changed=wb;changed.witness_sha256[0]^=1;CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&changed,&wbudget,&d,&bad,&wrprior)!=COH_OK&&!bad);
 /* Rehashing malformed producer predicates cannot make them admissible. */
 for(unsigned record=0;record<witness.size/64;record++){
  unsigned char *p=(unsigned char*)witness.data+record*64;uint32_t kind=(uint32_t)p[0];unsigned at=kind==1?12:kind==2?28:kind==3?32:kind==4?16:24;unsigned char old=p[at];p[at]^=1;changed=wb;CHECK(digest(NULL,witness,changed.witness_sha256)==COH_OK);CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&changed,&wbudget,&d,&bad,&wrprior)!=COH_OK&&!bad);p[at]=old;
 }
 Positions points={0};CohGroupsVisitor visitor={&points,positions};CohGroupsInspection inspection;CohRepReader scanned=before;CHECK(coh_rep_groups_visit(&scanned,&visitor,&inspection,NULL)==COH_OK);
 if(points.remove_bytes){unsigned char*removed=malloc(wire.size);CHECK(removed);memcpy(removed,wire.data,wire.size);memmove(removed+points.remove_at,removed+points.remove_at+points.remove_bytes,wire.size-points.remove_at-points.remove_bytes);CohRepReader missing;size_t size=wire.size-points.remove_bytes;CHECK(coh_rep_reader_bounded(&missing,(CohBytes){removed,size},size*8,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);missing.cursor=before.cursor;scanned=missing;CHECK(coh_rep_groups(&scanned,&inspection,NULL)==COH_OK);changed=wb;CHECK(digest(NULL,missing.bytes,changed.packet_sha256)==COH_OK);CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&missing,&changed,&wbudget,&d,&bad,&wrprior)!=COH_OK&&!bad);free(removed);}
 CohCatalogOwner*other=NULL;CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&d,&other,&or)==COH_OK);report=prior;CHECK(coh_runtime_graph_compare_groups_witness(graph,other,wowner,&wb,&reader,&gb,&report)==COH_STATE&&!memcmp(&report,&prior,sizeof(report)));changed=wb;CHECK(coh_runtime_groups_witness_create(graph,other,witness,&reader,&changed,&wbudget,&d,&bad,&wrprior)==COH_STATE&&!bad);coh_catalog_owner_release(other);
 CHECK(coh_runtime_graph_compare_groups_witness(graph,owner,wowner,&wb,&reader,&gb,(CohRuntimeGroupsReport*)&reader)==COH_INVALID&&!memcmp(&reader,&before,sizeof(reader)));
 CHECK(coh_runtime_graph_compare_groups_witness(graph,owner,wowner,&wb,&reader,&gb,&report)==COH_OK);gb.aggregate_limit=report.aggregate_reserved_bytes-1;report=prior;CHECK(coh_runtime_graph_compare_groups_witness(graph,owner,wowner,&wb,&reader,&gb,&report)==COH_LIMIT&&!memcmp(&report,&prior,sizeof(report)));
 coh_runtime_groups_witness_release(wowner);coh_runtime_graph_free(graph);coh_catalog_owner_release(owner);free((void*)catalog.data);free((void*)snapshot.data);free((void*)wire.data);free((void*)witness.data);
 CHECK(alive==0);
 printf("{\"passed\":true,\"checks\":%u,\"saved_omissions\":%u,\"eligible_definitions\":%u,\"owned_bytes\":%zu,\"import_peak\":%zu,\"source_generation_admitted\":false,\"live_groups_received\":false,\"world_authority\":false}\n",checks,wr.saved_omissions,wr.eligible_definitions,wr.owned_bytes,wr.aggregate_reserved_bytes);return 0;
}
