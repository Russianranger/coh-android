#include "coh_runtime_instances.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>
struct CohRuntimeGraph {CohRuntimeGraphNode nodes[131];CohRuntimeGraphChild edges[132];CohRuntimeGraphRoot roots[3];CohRuntimeGraphReport report;CohRuntimeGraphBinding binding;};
static unsigned char catalog[8],snapshot[8];
CohStatus coh_runtime_graph_sources(const CohRuntimeGraph*g,CohBytes*c,CohBytes*s){(void)g;*c=(CohBytes){catalog,sizeof(catalog)};*s=(CohBytes){snapshot,sizeof(snapshot)};return COH_OK;}
CohStatus coh_runtime_graph_binding(const CohRuntimeGraph*g,CohRuntimeGraphBinding*b){*b=g->binding;return COH_OK;}
CohStatus coh_runtime_graph_report(const CohRuntimeGraph*g,CohRuntimeGraphReport*r){*r=g->report;return COH_OK;}
CohStatus coh_runtime_graph_node(const CohRuntimeGraph*g,uint32_t n,CohRuntimeGraphNode*r){if(n>=g->report.nodes)return COH_STATE;*r=g->nodes[n];return COH_OK;}
CohStatus coh_runtime_graph_child(const CohRuntimeGraph*g,uint32_t n,CohRuntimeGraphChild*r){if(n>=g->report.edges)return COH_STATE;*r=g->edges[n];return COH_OK;}
CohStatus coh_runtime_graph_root(const CohRuntimeGraph*g,uint32_t n,CohRuntimeGraphRoot*r){if(n>=g->report.source.root_slots)return COH_STATE;*r=g->roots[n];return COH_OK;}
static unsigned allocation_calls,free_calls;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void*,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){allocation_calls++;return __real_malloc(n);}
void *__wrap_calloc(size_t n,size_t m){allocation_calls++;return __real_calloc(n,m);}
void *__wrap_realloc(void*p,size_t n){allocation_calls++;return __real_realloc(p,n);}
void __wrap_free(void*p){free_calls++;__real_free(p);}
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"instances line%d %s\n",__LINE__,#x);exit(1);}}while(0)
static void identity(CohSgMatrix m){memset(m,0,sizeof(CohSgMatrix));for(unsigned i=0;i<3;i++)m[i][i]=1;}
static struct CohRuntimeGraph setup(void){struct CohRuntimeGraph g={0};g.binding.generation=3;g.binding.catalog_generation=9;g.binding.pins.asset_generation=7;g.report.nodes=4;g.report.edges=4;g.report.source.root_slots=3;g.report.source.active_roots=2;g.report.owned_bytes=65536;
 for(unsigned i=0;i<4;i++){g.nodes[i].in_use=1;identity(g.edges[i].matrix);g.edges[i].matrix[3][0]=(float)i+1;}
 g.nodes[0].child_count=2;g.nodes[1].child_first=2;g.nodes[1].child_count=1;g.nodes[2].child_first=3;g.nodes[2].child_count=1;g.nodes[3].source_model_present=1;
 unsigned targets[]={1,2,3,3};for(unsigned i=0;i<4;i++)g.edges[i].target=targets[i];
 for(unsigned i=0;i<2;i++){g.roots[i].active=1;g.roots[i].node=0;identity(g.roots[i].matrix);g.roots[i].matrix[3][0]=10+(float)i*10;}
 return g;}
static int poll(void *context){int*n=context;return --*n==0;}
unsigned original_fixture_walk(uint32_t *,CohSgMatrix *);
void original_instance_compose(const float(*)[3],const float(*)[3],float(*)[3]);
static void begin(const CohRuntimeGraph*g,CohRuntimeInstances*c,CohRuntimeInstancesReport*r){CohRuntimeInstancesConfig config={10000,50000};CohRuntimeInstancesBudget budget={COH_SG_TRANSACTION_MAX,4096};CHECK(coh_runtime_instances_begin(g,&config,&budget,c,r)==COH_OK);}
static uint32_t random_value(uint32_t*s){*s^=*s<<13;*s^=*s>>17;*s^=*s<<5;return*s;}
int main(void){
 struct CohRuntimeGraph g=setup();CohRuntimeInstances cursor,initial;CohRuntimeInstancesReport report,prior;CohRuntimeInstance batch[COH_RUNTIME_INSTANCE_BATCH_MAX],expected[10],collected[10];
 begin(&g,&cursor,&report);CHECK(!report.world_authority&&!report.assets_admitted);initial=cursor;
 unsigned caps[]={1,2,3,17,1024},steps[]={1,2,9,65536};uint64_t final_work=0;
 for(unsigned a=0;a<5;a++)for(unsigned b=0;b<4;b++){
  cursor=initial;unsigned total=0,calls=0;do{CHECK(++calls<1000);CHECK(coh_runtime_instances_next(&cursor,batch,caps[a],steps[b],(CohCancel){0},&report)==COH_OK);CHECK(report.batch_count<=caps[a]&&report.steps<=steps[b]);CHECK(total+report.batch_count<=10);memcpy(collected+total,batch,report.batch_count*sizeof(*batch));total+=report.batch_count;}while(!report.complete);
  CHECK(total==10&&report.occurrences==10&&report.model_occurrences==4&&report.roots_started==2&&report.maximum_depth==2);CHECK(!report.world_authority&&!report.assets_admitted);
  unsigned nodes[]={0,1,3,2,3,0,1,3,2,3};uint64_t parents[]={UINT64_MAX,0,1,0,3,UINT64_MAX,5,6,5,8};float x[]={10,11,14,12,16,20,21,24,22,26};
  for(unsigned i=0;i<10;i++){CHECK(collected[i].node==nodes[i]&&collected[i].ordinal==i&&collected[i].parent_ordinal==parents[i]);CHECK(collected[i].world[3][0]==x[i]&&collected[i].root_slot==i/5);}
  if(!a&&!b){memcpy(expected,collected,sizeof(expected));final_work=report.work;}else{CHECK(!memcmp(expected,collected,sizeof(expected)));CHECK(report.work==final_work);}
  CHECK(coh_runtime_instances_next(&cursor,batch,1,1,(CohCancel){0},&report)==COH_OK&&report.complete&&!report.batch_count&&!report.steps);
 }
 uint32_t original_nodes[10];CohSgMatrix original_worlds[10];CHECK(original_fixture_walk(original_nodes,original_worlds)==10);for(unsigned i=0;i<10;i++){CHECK(original_nodes[i]==expected[i].node);CHECK(!memcmp(original_worlds[i],expected[i].world,sizeof(CohSgMatrix)));}
 /* Whole attempted batch rollback at every cancellation boundary. */
 for(int i=1;i<64;i++){cursor=initial;CohRuntimeInstances before=cursor;memset(&report,0x51,sizeof(report));prior=report;int n=i;CohStatus status=coh_runtime_instances_next(&cursor,batch,17,65536,(CohCancel){poll,&n},&report);if(status==COH_OK)break;CHECK(status==COH_CANCELLED&&!memcmp(&cursor,&before,sizeof(cursor))&&!memcmp(&report,&prior,sizeof(report)));}
 CohRuntimeInstancesConfig config={9,50000};CohRuntimeInstancesBudget budget={COH_SG_TRANSACTION_MAX,4096};CHECK(coh_runtime_instances_begin(&g,&config,&budget,&cursor,&report)==COH_OK);CohRuntimeInstances before=cursor;prior=report;CHECK(coh_runtime_instances_next(&cursor,batch,17,65536,(CohCancel){0},&report)==COH_LIMIT);CHECK(!memcmp(&cursor,&before,sizeof(cursor))&&!memcmp(&report,&prior,sizeof(report)));
 config=(CohRuntimeInstancesConfig){10000,3};CHECK(coh_runtime_instances_begin(&g,&config,&budget,&cursor,&report)==COH_OK);before=cursor;prior=report;CHECK(coh_runtime_instances_next(&cursor,batch,17,65536,(CohCancel){0},&report)==COH_LIMIT);CHECK(!memcmp(&cursor,&before,sizeof(cursor))&&!memcmp(&report,&prior,sizeof(report)));
 cursor=initial;before=cursor;prior=report;CHECK(coh_runtime_instances_next(&cursor,(CohRuntimeInstance*)&cursor,1,10,(CohCancel){0},&report)==COH_INVALID);CHECK(!memcmp(&cursor,&before,sizeof(cursor))&&!memcmp(&report,&prior,sizeof(report)));
 CHECK(coh_runtime_instances_next(&cursor,batch,1,10,(CohCancel){0},(CohRuntimeInstancesReport*)batch)==COH_INVALID);CHECK(!memcmp(&cursor,&before,sizeof(cursor)));
 CHECK(coh_runtime_instances_next(&cursor,(CohRuntimeInstance*)(uintptr_t)(UINTPTR_MAX-2u),1024,10,(CohCancel){0},&report)==COH_INVALID);
 budget.aggregate_limit=initial.base_reserved_bytes+sizeof(*batch)-1;config=(CohRuntimeInstancesConfig){10000,50000};CHECK(coh_runtime_instances_begin(&g,&config,&budget,&cursor,&report)==COH_OK);before=cursor;prior=report;CHECK(coh_runtime_instances_next(&cursor,batch,1,10,(CohCancel){0},&report)==COH_LIMIT);CHECK(!memcmp(&cursor,&before,sizeof(cursor))&&!memcmp(&report,&prior,sizeof(report)));budget.aggregate_limit=COH_SG_TRANSACTION_MAX;
 CHECK(coh_runtime_instances_begin(&g,&config,&budget,(CohRuntimeInstances*)&budget,&report)==COH_INVALID);
 /* Source fixtures deliberately violate graph admission to test defensive caps. */
 g.nodes[3].child_first=4;g.nodes[3].child_count=1;g.edges[4].target=0;identity(g.edges[4].matrix);g.report.edges=5;begin(&g,&cursor,&report);before=cursor;prior=report;CHECK(coh_runtime_instances_next(&cursor,batch,17,65536,(CohCancel){0},&report)==COH_INVALID);CHECK(!memcmp(&cursor,&before,sizeof(cursor))&&!memcmp(&report,&prior,sizeof(report)));
 g=setup();g.edges[1].target=130;begin(&g,&cursor,&report);CHECK(coh_runtime_instances_next(&cursor,batch,17,65536,(CohCancel){0},&report)==COH_STATE);
 g=setup();g.roots[0].matrix[0][0]=FLT_MAX;g.edges[0].matrix[0][0]=2;begin(&g,&cursor,&report);before=cursor;prior=report;CHECK(coh_runtime_instances_next(&cursor,batch,17,65536,(CohCancel){0},&report)==COH_INVALID);CHECK(!memcmp(&cursor,&before,sizeof(cursor))&&!memcmp(&report,&prior,sizeof(report)));
 g=setup();g.report.nodes=130;g.report.edges=129;for(unsigned i=0;i<130;i++){g.nodes[i]=(CohRuntimeGraphNode){0};g.nodes[i].in_use=1;if(i<129){g.nodes[i].child_first=i;g.nodes[i].child_count=1;g.edges[i].target=i+1;identity(g.edges[i].matrix);}}begin(&g,&cursor,&report);before=cursor;prior=report;CHECK(coh_runtime_instances_next(&cursor,batch,1024,65536,(CohCancel){0},&report)==COH_LIMIT);CHECK(!memcmp(&cursor,&before,sizeof(cursor))&&!memcmp(&report,&prior,sizeof(report)));
 /* Exact original matrix operation order, including signed zero. */
 uint32_t seed=0x217ab51;for(unsigned fixture=0;fixture<2048;fixture++){g=setup();for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++){uint32_t v=random_value(&seed);g.roots[0].matrix[i][j]=(float)(int)(v%65)-32;v=random_value(&seed);g.edges[0].matrix[i][j]=(float)(int)(v%65)-32;if(fixture%7==0){g.roots[0].matrix[i][j]=-0.0f;g.edges[0].matrix[i][j]=-0.0f;}}begin(&g,&cursor,&report);CHECK(coh_runtime_instances_next(&cursor,batch,2,65536,(CohCancel){0},&report)==COH_OK&&report.batch_count==2);CohSgMatrix original;original_instance_compose((const float(*)[3])g.roots[0].matrix,(const float(*)[3])g.edges[0].matrix,original);CHECK(!memcmp(original,batch[1].world,sizeof(original)));}
 g=setup();begin(&g,&cursor,&report);CHECK(coh_runtime_instances_next(&cursor,batch,17,65536,(CohCancel){0},&report)==COH_OK);CohRuntimeBoundsRow bounds[4]={0};CohRuntimeBoundsReport br={0};br.graph=cursor.binding;for(unsigned i=0;i<4;i++){bounds[i].result=COH_RB_COMPUTED;bounds[i].bounds.radius=1;}CohRuntimeInstanceSelectionInput selection,sentinel;memset(&selection,0x51,sizeof(selection));sentinel=selection;CHECK(coh_runtime_instance_selection_input(&cursor,&batch[2],&br,bounds,4,&selection)==COH_OK);CHECK(selection.instance.ordinal==2&&selection.instance.node==3&&selection.local_source_bounds.radius==1);bounds[3].result=COH_RB_DEFINITION_MISSING;selection=sentinel;CHECK(coh_runtime_instance_selection_input(&cursor,&batch[2],&br,bounds,4,&selection)==COH_NOT_FOUND);CHECK(!memcmp(&selection,&sentinel,sizeof(selection)));br.graph.generation++;CHECK(coh_runtime_instance_selection_input(&cursor,&batch[2],&br,bounds,4,&selection)==COH_STATE);
 CHECK(!allocation_calls&&!free_calls);
 printf("{\"allocations\":0,\"deallocations\":0,\"passed\":true,\"checks\":%u,\"source_matrix_fixtures\":2048,\"dag_occurrences\":10,\"dag_unique_reachable\":4,\"world_authority\":false}\n",checks);return 0;
}
