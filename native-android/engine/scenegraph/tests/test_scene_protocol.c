#include "coh_scene_protocol.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static size_t allocations,alive,fault_at,fault_seen,target_pool,target_pool_calls;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){allocations++;if(fault_at&&++fault_seen==fault_at)return NULL;void*p=__real_malloc(n);if(p)alive++;return p;}
void *__wrap_calloc(size_t n,size_t size){allocations++;if(n==1&&size==target_pool)target_pool_calls++;if(fault_at&&++fault_seen==fault_at)return NULL;void*p=__real_calloc(n,size);if(p)alive++;return p;}
void __wrap_free(void*p){if(p){if(!alive)abort();alive--;}__real_free(p);}
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"runtimegroups line%d %s\n",__LINE__,#x);abort();}}while(0)
static CohBytes load(const char *name){FILE *f=fopen(name,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0);rewind(f);unsigned char *p=malloc((size_t)n);CHECK(p);CHECK(fread(p,1,(size_t)n,f)==(size_t)n);fclose(f);return(CohBytes){p,(size_t)n};}
static CohStatus digest(void *context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_INVALID;}
typedef struct {unsigned calls,at;} CancelState;
static int cancel_at(void*ctx){CancelState*s=ctx;s->calls++;return s->calls==s->at;}
int main(int argc,char **argv){
 CHECK(argc==6);CohBytes catalog=load(argv[1]),snapshot=load(argv[2]),wire=load(argv[3]),witness=load(argv[4]);
 uint32_t generation=(uint32_t)catalog.data[20]|(uint32_t)catalog.data[21]<<8|(uint32_t)catalog.data[22]<<16|(uint32_t)catalog.data[23]<<24;
 CohCatalogBinding cb={0};cb.owner_generation=1;cb.catalog_generation=1;cb.asset_generation=generation;memset(cb.source_sha256,0x11,32);memset(cb.inventory_sha256,0x33,32);CHECK(digest(NULL,catalog,cb.catalog_sha256)==COH_OK);
 CohCatalogOwner *owner=NULL;CohCatalogOwnerBudget ob={COH_SG_MEMORY_MAX,COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohCatalogDigest d={NULL,digest};CohCatalogOwnerReport or;
 /* Catalog owner catalog_generation is original wire cataloggeneration. */
 cb.catalog_generation=generation;CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&d,&owner,&or)==COH_OK);CohBytes owned;CHECK(coh_catalog_owner_bytes(owner,&owned)==COH_OK);
 CohRuntimeGraphBinding binding={0};binding.generation=1;binding.catalog_generation=generation;binding.pins.asset_generation=generation;memcpy(binding.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(binding.pins.source_sha256,cb.source_sha256,32);memset(binding.pins.run_sha256,0x22,32);binding.pins.digest=digest;CHECK(digest(NULL,snapshot,binding.pins.snapshot_sha256)==COH_OK);
 CohCatalogSnapshotBinding sb={0};sb.generation=1;sb.catalog=cb;memcpy(sb.snapshot_sha256,binding.pins.snapshot_sha256,32);memcpy(sb.run_sha256,binding.pins.run_sha256,32);CohRuntimeSnapshotBudget sbudget={COH_SG_TRANSACTION_MAX,262144};CohCatalogSnapshot*sowner=NULL;CHECK(coh_catalog_snapshot_create(NULL,owner,snapshot,&sb,&sbudget,&d,NULL,&sowner)==COH_OK);CohBytes snapshot_owned;CohCatalogSnapshotBinding observed;CohRuntimeSnapshotReport sr;CHECK(coh_catalog_snapshot_view(sowner,&snapshot_owned,&observed,&sr)==COH_OK);
 CohRuntimeSnapshotBudget budget={COH_SG_TRANSACTION_MAX,262144+coh_catalog_owner_owned_bytes(owner)+coh_catalog_snapshot_owned_bytes(sowner)};CohRuntimeGraph *graph=NULL;CohRuntimeGraphReport gr;CHECK(coh_runtime_graph_build(NULL,owned,snapshot_owned,&binding,&budget,NULL,&graph,&gr)==COH_OK);
 CohRuntimeGraph*limited=NULL;CohRuntimeGraphReport limitedreport;memset(&limitedreport,0x6b,sizeof(limitedreport));CohRuntimeGraphReport limitedguard=limitedreport;target_pool=gr.source.owned_bytes;target_pool_calls=0;size_t limitbaseline=alive;
 CHECK(coh_runtime_graph_build_limited(NULL,owned,snapshot_owned,&binding,&budget,NULL,gr.owned_bytes-1,&limited,&limitedreport)==COH_LIMIT&&!limited&&target_pool_calls==0&&alive==limitbaseline&&!memcmp(&limitedreport,&limitedguard,sizeof(limitedreport)));
 CHECK(coh_runtime_graph_build_limited(NULL,owned,snapshot_owned,&binding,&budget,NULL,gr.owned_bytes,&limited,&limitedreport)==COH_OK&&target_pool_calls==1&&limitedreport.owned_bytes==gr.owned_bytes);coh_runtime_graph_free(limited);target_pool=0;
 CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,wire,wire.size*8,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);uint32_t command;CHECK(coh_rep_pack(&reader,1,&command)==COH_OK&&command==COH_REP_GROUPS);CohRepReader before=reader;
 CohRuntimeGroupsWitnessBinding wb={0};wb.graph_generation=binding.generation;wb.catalog_generation=generation;wb.observation_id=7;wb.map_generation=11;wb.selection_generation=22;wb.selected_dbid=33;memset(wb.session_sha256,0x44,32);memcpy(wb.catalog_sha256,binding.pins.catalog_sha256,32);memcpy(wb.snapshot_sha256,binding.pins.snapshot_sha256,32);memcpy(wb.source_sha256,binding.pins.source_sha256,32);memcpy(wb.run_sha256,binding.pins.run_sha256,32);CHECK(digest(NULL,witness,wb.witness_sha256)==COH_OK);CHECK(digest(NULL,wire,wb.packet_sha256)==COH_OK);
 CohRuntimeGroupsWitnessBudget wbudget={COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohRuntimeGroupsWitnessReport wr;memset(&wr,0x5a,sizeof(wr));CohRuntimeGroupsWitness *wowner=NULL;
 CHECK(coh_runtime_groups_witness_create(graph,owner,witness,&reader,&wb,&wbudget,&d,&wowner,&wr)==COH_OK);CHECK(wowner&&!wr.source_generation_admitted&&!wr.world_authority);
 CohSceneProtocolBudget pb={COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohSceneProtocol *seed=NULL,*current=NULL,*retired=NULL,*candidate=NULL;CohSceneProtocolReport state_report,prior;memset(&state_report,0x5a,sizeof(state_report));prior=state_report;
 CHECK(coh_scene_protocol_create(NULL,graph,owner,sowner,NULL,1,&pb,NULL,&seed,&state_report)==COH_OK);CHECK(state_report.records==gr.nodes&&!state_report.binding.groups_compatibility_checked&&state_report.protocol_wire_inputs_complete&&!state_report.source_generation_admitted&&!state_report.world_authority&&!state_report.client_derived_state_complete&&!state_report.bounds_cache_checksums_recomputed);CHECK(state_report.dependencies_bytes==gr.owned_bytes+coh_catalog_owner_owned_bytes(owner)+coh_catalog_snapshot_owned_bytes(sowner));CHECK(coh_scene_protocol_publish(&current,&seed,&retired)==COH_OK&&current&&!seed&&!retired);
 CohSceneProtocolGroups group={wowner,&wb,&reader};CohSceneProtocolReport grouped_report;CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,2,&pb,NULL,&candidate,&grouped_report)==COH_OK);CHECK(grouped_report.binding.groups_compatibility_checked&&grouped_report.equal_wire_updates==wr.eligible_definitions&&grouped_report.verified_omissions==wr.saved_omissions);CHECK(grouped_report.dependencies_bytes==state_report.dependencies_bytes+coh_runtime_groups_witness_owned_bytes(wowner));
 CohSceneProtocol *wrongcurrent=NULL;CHECK(coh_scene_protocol_publish(&wrongcurrent,&candidate,&retired)==COH_STATE&&!wrongcurrent&&candidate&&!retired);CHECK(coh_scene_protocol_publish(&current,&candidate,&retired)==COH_OK&&current&&!candidate&&retired);coh_scene_protocol_release(retired);retired=NULL;
 size_t before_allocations=allocations;for(uint32_t i=0;i<gr.nodes;i++){CohSceneProtocolRecord rec;CohRuntimeGraphNode node;CHECK(coh_scene_protocol_record(current,i,&rec)==COH_OK);CHECK(coh_runtime_graph_node(graph,i,&node)==COH_OK&&rec.source.node==i&&rec.source.wire.data==node.wire.data&&rec.source.wire.size==node.wire.size&&rec.update_presence_known==!node.external);if(!node.external){CohSceneProtocolRecord byslot;CHECK(coh_scene_protocol_slot(current,node.file,node.slot,&byslot)==COH_OK&&!memcmp(&rec,&byslot,sizeof(rec)));}}
 CHECK(allocations==before_allocations);const CohRuntimeGraph*samegraph=NULL;CHECK(coh_scene_protocol_graph(current,&samegraph)==COH_OK&&samegraph==graph);CHECK(coh_scene_protocol_retain(current)==COH_OK);coh_scene_protocol_release(current);
 CHECK(coh_scene_protocol_create(current,graph,owner,sowner,NULL,3,&pb,NULL,&candidate,&prior)==COH_STATE&&!candidate);CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,4,&pb,NULL,&candidate,&prior)==COH_STATE&&!candidate);
 CohSceneProtocolGroups partial=group;partial.binding=NULL;CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&partial,3,&pb,NULL,&candidate,&prior)==COH_INVALID&&!candidate);
 CohRuntimeGroupsWitnessBinding changed=wb;changed.selection_generation++;CohSceneProtocolGroups stale={wowner,&changed,&reader};CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&stale,3,&pb,NULL,&candidate,&prior)==COH_STATE&&!candidate);
 /* Borrowed equal bytes do not substitute another actual snapshot owner. */
 CohCatalogSnapshot*other_snapshot=NULL;CHECK(coh_catalog_snapshot_create(NULL,owner,snapshot,&sb,&sbudget,&d,NULL,&other_snapshot)==COH_OK);CHECK(coh_scene_protocol_create(current,graph,owner,other_snapshot,&group,3,&pb,NULL,&candidate,&prior)==COH_STATE&&!candidate);coh_catalog_snapshot_release(other_snapshot);
 CohCatalogOwner*other=NULL;CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&d,&other,&or)==COH_OK);CHECK(coh_scene_protocol_create(current,graph,other,sowner,&group,3,&pb,NULL,&candidate,&prior)==COH_STATE&&!candidate);coh_catalog_owner_release(other);
 for(unsigned at=1;at<=gr.nodes+2;at++){CancelState cs={0,at};CohCancel cancellation={.poll=cancel_at,.context=&cs};CohSceneProtocolReport guard=prior;size_t baseline=alive;CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,3,&pb,&cancellation,&candidate,&prior)==COH_CANCELLED&&!candidate&&!memcmp(&prior,&guard,sizeof(prior))&&alive==baseline);}
 for(unsigned f=1;f<=3;f++){size_t baseline=alive;CohSceneProtocolReport guard=prior;fault_at=f;fault_seen=0;CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,3,&pb,NULL,&candidate,&prior)==COH_LIMIT&&!candidate);fault_at=0;CHECK(alive==baseline&&!memcmp(&prior,&guard,sizeof(prior)));}
 size_t saved=pb.owned_limit;pb.owned_limit=grouped_report.owned_bytes-1;CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,3,&pb,NULL,&candidate,&prior)==COH_LIMIT&&!candidate);pb.owned_limit=saved;
 CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,3,&pb,NULL,&candidate,(CohSceneProtocolReport*)current)==COH_INVALID&&!candidate);CHECK(coh_scene_protocol_report(current,(CohSceneProtocolReport*)current)==COH_INVALID);
 CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,3,&pb,NULL,&candidate,(CohSceneProtocolReport*)wire.data)==COH_INVALID&&!candidate);CHECK(!memcmp(&reader,&before,sizeof(reader)));
 CohSceneProtocolRecord record,record_guard;memset(&record,0xa5,sizeof(record));record_guard=record;CHECK(coh_scene_protocol_record(current,gr.nodes,&record)==COH_NOT_FOUND&&!memcmp(&record,&record_guard,sizeof(record)));CHECK(coh_scene_protocol_slot(current,0,65535,&record)==COH_NOT_FOUND&&!memcmp(&record,&record_guard,sizeof(record)));
 /* Same catalog generation cannot silently rebind a different run. */
 CohSceneProtocol *source_old=NULL;CHECK(coh_scene_protocol_create(NULL,graph,owner,sowner,NULL,1,&pb,NULL,&source_old,&prior)==COH_OK);
 CohCatalogSnapshotBinding alt_sb=sb;memset(alt_sb.run_sha256,0x55,32);CohCatalogSnapshot*alt_snapshot=NULL;CHECK(coh_catalog_snapshot_create(NULL,owner,snapshot,&alt_sb,&sbudget,&d,NULL,&alt_snapshot)==COH_OK);CohBytes alt_bytes;CHECK(coh_catalog_snapshot_view(alt_snapshot,&alt_bytes,&observed,&sr)==COH_OK);CohRuntimeGraphBinding alt_binding=binding;memcpy(alt_binding.pins.run_sha256,alt_sb.run_sha256,32);CohRuntimeGraph*alt_graph=NULL;CHECK(coh_runtime_graph_build(NULL,owned,alt_bytes,&alt_binding,&budget,NULL,&alt_graph,&gr)==COH_OK);CHECK(coh_scene_protocol_create(source_old,alt_graph,owner,alt_snapshot,NULL,2,&pb,NULL,&candidate,&prior)==COH_STATE&&!candidate);coh_scene_protocol_release(source_old);coh_runtime_graph_free(alt_graph);coh_catalog_snapshot_release(alt_snapshot);
 /* Competing candidates cannot replace a newer local preparation generation. */
 CohSceneProtocol *second=NULL;CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,3,&pb,NULL,&candidate,&prior)==COH_OK);CHECK(coh_scene_protocol_create(current,graph,owner,sowner,&group,3,&pb,NULL,&second,&prior)==COH_OK);CHECK(coh_scene_protocol_publish(&current,&candidate,&retired)==COH_OK&&retired);CHECK(coh_scene_protocol_publish(&current,&second,&candidate)==COH_STATE&&second&&!candidate);coh_scene_protocol_release(second);coh_scene_protocol_release(retired);retired=NULL;
 CohSceneProtocolReport final;CHECK(coh_scene_protocol_report(current,&final)==COH_OK&&final.binding.generation==3&&!final.source_generation_admitted&&!final.world_authority);CHECK(coh_scene_protocol_record(current,0,(CohSceneProtocolRecord*)owned.data)==COH_INVALID);

 /* Real source-owner graph lease: exact preallocation cap, failures, then state
  * remains usable after the caller releases its creator GraphOwner reference. */
 CohRuntimeGraphOwnerBudget gob={COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohRuntimeGraphOwner*go=NULL,*nextgo=NULL;CohRuntimeGraphOwnerReport gor,go_guard;memset(&gor,0x5a,sizeof(gor));go_guard=gor;
 size_t baseline=alive;
 CHECK(coh_runtime_graph_owner_create(NULL,owner,sowner,2,&gob,&d,NULL,&go,&gor)==COH_STATE&&!go&&alive==baseline&&!memcmp(&gor,&go_guard,sizeof(gor)));
 CHECK(coh_runtime_graph_owner_create(NULL,owner,sowner,1,&gob,&d,NULL,&go,&gor)==COH_OK);
 const CohRuntimeGraph*ownedgraph;CohCatalogOwner*oc;CohCatalogSnapshot*os;CHECK(coh_runtime_graph_owner_view(go,&ownedgraph,&oc,&os,&gor)==COH_OK&&oc==owner&&os==sowner&&ownedgraph!=graph&&gor.nodes==gr.nodes);
 CHECK(gor.graph_bytes+gor.owner_bytes<=gob.owned_limit&&gor.dependencies_bytes==coh_catalog_owner_owned_bytes(owner)+coh_catalog_snapshot_owned_bytes(sowner));
 size_t savedlimit=gob.owned_limit;gob.owned_limit=gor.owner_bytes+gor.graph_bytes-1;go_guard=gor;baseline=alive;
 CHECK(coh_runtime_graph_owner_create(go,owner,sowner,2,&gob,&d,NULL,&nextgo,&gor)==COH_LIMIT&&!nextgo&&alive==baseline&&!memcmp(&gor,&go_guard,sizeof(gor)));gob.owned_limit=savedlimit;
 CHECK(coh_runtime_graph_owner_create(go,owner,sowner,2,&gob,&d,NULL,&nextgo,&gor)==COH_OK);coh_runtime_graph_owner_release(nextgo);nextgo=NULL;
 fault_at=SIZE_MAX;fault_seen=0;CHECK(coh_runtime_graph_owner_create(NULL,owner,sowner,1,&gob,&d,NULL,&nextgo,&gor)==COH_OK);size_t graph_allocations=fault_seen;fault_at=0;coh_runtime_graph_owner_release(nextgo);nextgo=NULL;
 for(size_t f=1;f<=graph_allocations;f++){baseline=alive;fault_at=f;fault_seen=0;CohStatus st=coh_runtime_graph_owner_create(NULL,owner,sowner,1,&gob,&d,NULL,&nextgo,&gor);fault_at=0;if(st==COH_OK){coh_runtime_graph_owner_release(nextgo);nextgo=NULL;}else CHECK(st==COH_LIMIT&&!nextgo);CHECK(alive==baseline);}
 CancelState gc={0,UINT32_MAX};CohCancel gcan={.poll=cancel_at,.context=&gc};CHECK(coh_runtime_graph_owner_create(NULL,owner,sowner,1,&gob,&d,&gcan,&nextgo,&gor)==COH_OK);unsigned graph_polls=gc.calls;coh_runtime_graph_owner_release(nextgo);nextgo=NULL;for(unsigned at=1;at<=graph_polls;at++){gc=(CancelState){0,at};baseline=alive;CohRuntimeGraphOwnerReport guard=gor;CHECK(coh_runtime_graph_owner_create(NULL,owner,sowner,1,&gob,&d,&gcan,&nextgo,&gor)==COH_CANCELLED&&!nextgo&&alive==baseline&&!memcmp(&gor,&guard,sizeof(gor)));}
 CohSceneProtocol*ownedstate=NULL;CohSceneProtocolReport ownedreport;CHECK(coh_scene_protocol_create_owned(NULL,go,NULL,1,&pb,NULL,&ownedstate,&ownedreport)==COH_OK&&ownedreport.owned_graph_lease&&!ownedreport.source_generation_admitted&&!ownedreport.world_authority);
 CHECK(ownedreport.dependencies_bytes==go_guard.graph_bytes+go_guard.dependencies_bytes+go_guard.owner_bytes);
 CHECK(coh_scene_protocol_create_owned(NULL,go,NULL,1,&pb,NULL,&candidate,(CohSceneProtocolReport*)go)==COH_INVALID&&!candidate);

 CHECK(coh_runtime_graph_owner_view(go,(const CohRuntimeGraph**)go,&oc,&os,&gor)==COH_INVALID);
 CHECK(coh_runtime_graph_owner_create(NULL,owner,sowner,1,&gob,&d,NULL,&nextgo,(CohRuntimeGraphOwnerReport*)owned.data)==COH_INVALID&&!nextgo);
 CohCatalogOwner*wrongowner=NULL;CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&d,&wrongowner,&or)==COH_OK);CHECK(coh_runtime_graph_owner_create(NULL,wrongowner,sowner,1,&gob,&d,NULL,&nextgo,&gor)==COH_STATE&&!nextgo);coh_catalog_owner_release(wrongowner);
 size_t savedaggregate=gob.aggregate_limit;gob.aggregate_limit=1;baseline=alive;before_allocations=allocations;CHECK(coh_runtime_graph_owner_create(NULL,owner,sowner,1,&gob,&d,NULL,&nextgo,&gor)==COH_LIMIT&&!nextgo&&alive==baseline&&allocations==before_allocations);gob.aggregate_limit=savedaggregate;
 CohRuntimeGroupsWitness*ownedwitness=NULL;CHECK(coh_runtime_groups_witness_create(ownedgraph,owner,witness,&reader,&wb,&wbudget,&d,&ownedwitness,&wr)==COH_OK);CohSceneProtocolGroups ownedgroups={ownedwitness,&wb,&reader};CohSceneProtocol*ownedgroupstate=NULL;
 CHECK(coh_scene_protocol_create_owned(ownedstate,go,&ownedgroups,2,&pb,NULL,&ownedgroupstate,&ownedreport)==COH_OK&&ownedreport.owned_graph_lease&&ownedreport.binding.groups_compatibility_checked);
 for(unsigned f=1;f<=3;f++){baseline=alive;fault_at=f;fault_seen=0;CohStatus st=coh_scene_protocol_create_owned(ownedstate,go,&ownedgroups,2,&pb,NULL,&candidate,&prior);fault_at=0;CHECK(st==COH_LIMIT&&!candidate&&alive==baseline);}
 /* The witness is itself graph-borrowing: retire its external reference before
  * the last owned state, whose owner keeps the graph alive through teardown. */
 coh_runtime_groups_witness_release(ownedwitness);
 coh_scene_protocol_release(ownedstate);ownedstate=ownedgroupstate;
 coh_scene_protocol_release(current);coh_runtime_groups_witness_release(wowner);coh_runtime_graph_free(graph);coh_catalog_snapshot_release(sowner);coh_catalog_owner_release(owner);
 coh_runtime_graph_owner_release(go);go=NULL;
 CHECK(coh_scene_protocol_graph(ownedstate,&samegraph)==COH_OK&&samegraph==ownedgraph);
 for(uint32_t i=0;i<ownedreport.records;i++){CohSceneProtocolRecord rec;CHECK(coh_scene_protocol_record(ownedstate,i,&rec)==COH_OK);CohRuntimeGraphNode node;CHECK(coh_runtime_graph_node(samegraph,i,&node)==COH_OK&&rec.source.wire.data==node.wire.data);if(!node.external)CHECK(coh_scene_protocol_slot(ownedstate,node.file,node.slot,&record)==COH_OK);}
 coh_scene_protocol_release(ownedstate);
 free((void*)catalog.data);free((void*)snapshot.data);free((void*)wire.data);free((void*)witness.data);CHECK(alive==0);
 printf("{\"passed\":true,\"checks\":%u,\"state_owned_bytes\":%zu,\"state_dependencies\":%zu,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks,final.owned_bytes,final.dependencies_bytes);return 0;
}
