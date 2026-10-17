#include "coh_runtime_bounds.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct CohRuntimeGraph {CohRuntimeGraphNode nodes[5];CohRuntimeGraphChild edges[5];CohRuntimeGraphRoot roots[3];CohRuntimeGraphReport report;CohRuntimeGraphBinding binding;};
CohStatus coh_runtime_graph_report(const CohRuntimeGraph*g,CohRuntimeGraphReport*r){*r=g->report;return COH_OK;}
static unsigned char catalog_bytes[8],snapshot_bytes[8];
CohStatus coh_runtime_graph_sources(const CohRuntimeGraph*g,CohBytes*c,CohBytes*s){(void)g;*c=(CohBytes){catalog_bytes,sizeof(catalog_bytes)};*s=(CohBytes){snapshot_bytes,sizeof(snapshot_bytes)};return COH_OK;}
CohStatus coh_runtime_graph_binding(const CohRuntimeGraph*g,CohRuntimeGraphBinding*b){*b=g->binding;return COH_OK;}
CohStatus coh_runtime_graph_node(const CohRuntimeGraph*g,uint32_t n,CohRuntimeGraphNode*v){if(n>=g->report.nodes)return COH_NOT_FOUND;*v=g->nodes[n];return COH_OK;}
CohStatus coh_runtime_graph_child(const CohRuntimeGraph*g,uint32_t n,CohRuntimeGraphChild*v){if(n>=g->report.edges)return COH_NOT_FOUND;*v=g->edges[n];return COH_OK;}
CohStatus coh_runtime_graph_root(const CohRuntimeGraph*g,uint32_t n,CohRuntimeGraphRoot*v){if(n>=g->report.source.root_slots)return COH_NOT_FOUND;*v=g->roots[n];return COH_OK;}
static unsigned checks,calls[5];static int captured_future;
CohStatus coh_runtime_graph_external_bounds(const CohRuntimeGraph*g,uint32_t n,CohRuntimeExternalBounds*b){(void)g;(void)n;if(!captured_future)return COH_NOT_FOUND;memset(b,0,sizeof(*b));return COH_OK;}static int missing=-1,bad=-1,cancel_at;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"line%d\n",__LINE__);abort();}}while(0)
static int poll(void*p){(void)p;return --cancel_at<=0;}
static CohStatus provider(void*p,uint32_t n,const CohRuntimeGraphNode*v,CohGroupBoundsInput*i){(void)p;calls[n]++;CHECK(v->reachable);if((int)n==missing)return COH_NOT_FOUND;i->model_present=v->source_model_present;i->model_max[0]=i->model_max[1]=i->model_max[2]=2;if((int)n==bad)i->model_present=!i->model_present;return COH_OK;}
static CohStatus diagnose(CohRuntimeGraph*g,CohRuntimeBoundsBudget b,CohCancel c,CohRuntimeBoundsRow*r,CohRuntimeBoundsReport*out){CohGroupBoundsChild children[5];CohRuntimeBoundsFrame stack[COH_SG_DEPTH_MAX+1u];return coh_runtime_bounds_diagnose(g,provider,NULL,&b,c,r,5,children,5,stack,COH_SG_DEPTH_MAX+1u,out);}
int main(void){
 CohRuntimeGraph g={0};CohRuntimeBoundsRow rows[5];CohRuntimeBoundsReport out,sentinel;CohRuntimeBoundsBudget budget={96u<<20,51u<<20};CohCancel no={NULL,NULL};
 g.report.nodes=5;g.report.edges=5;g.report.owned_bytes=1024;g.report.source.root_slots=3;g.binding.generation=3;g.binding.catalog_generation=9;
 for(unsigned n=0;n<5;n++){g.nodes[n].in_use=g.nodes[n].reachable=1;g.nodes[n].source_model_present=1;g.nodes[n].name="fixture";}
 /* Shared child DAG:0->1,2;1->3;2->3. Node4 deliberately disconnected cycle. */
 g.nodes[0].child_count=2;g.nodes[1].child_first=2;g.nodes[1].child_count=1;g.nodes[2].child_first=3;g.nodes[2].child_count=1;g.nodes[4].reachable=0;g.nodes[4].child_first=4;g.nodes[4].child_count=1;g.edges[4].target=4;
 unsigned targets[]={1,2,3,3};for(unsigned n=0;n<4;n++){g.edges[n].target=targets[n];for(unsigned k=0;k<3;k++)g.edges[n].matrix[k][k]=1;}
 g.edges[1].matrix[3][0]=10;g.roots[0].active=g.roots[1].active=1;g.roots[0].node=0;g.roots[1].node=2;
 CHECK(diagnose(&g,budget,no,rows,&out)==COH_OK);CHECK(out.visited==4&&out.computed==4&&out.active_roots==2&&out.computed_roots==2);CHECK(calls[3]==1&&!calls[4]);CHECK(out.graph.generation==3&&out.graph.catalog_generation==9&&!out.assets_admitted&&!out.world_authority);CHECK(rows[0].bounds.min[0]==0&&rows[0].bounds.max[0]==12);
 size_t peak=out.aggregate_reserved_bytes;budget.aggregate_limit=peak-1;memset(&sentinel,0x51,sizeof(sentinel));out=sentinel;CHECK(diagnose(&g,budget,no,rows,&out)==COH_LIMIT);CHECK(!memcmp(&out,&sentinel,sizeof(out)));budget.aggregate_limit=peak;CHECK(diagnose(&g,budget,no,rows,&out)==COH_OK);
 budget.aggregate_limit=96u<<20;g.nodes[3].external=1;memset(calls,0,sizeof(calls));CHECK(diagnose(&g,budget,no,rows,&out)==COH_OK);CHECK(out.future_missing==1&&out.child_blocked==3&&!out.computed&&out.blocked_roots==2);CHECK(!calls[0]&&!calls[3]);
 captured_future=1;CHECK(diagnose(&g,budget,no,rows,&out)==COH_OK);CHECK(out.captured_future==1&&out.computed==3&&!out.future_missing&&!out.child_blocked&&out.computed_roots==2);captured_future=0;
 g.nodes[3].external=0;missing=3;CHECK(diagnose(&g,budget,no,rows,&out)==COH_OK);CHECK(out.definition_missing==1&&out.child_blocked==3);missing=-1;
 bad=3;out=sentinel;CHECK(diagnose(&g,budget,no,rows,&out)==COH_STATE);CHECK(!memcmp(&out,&sentinel,sizeof(out)));bad=-1;
 g.edges[2].target=0;CHECK(diagnose(&g,budget,no,rows,&out)==COH_INVALID);CHECK(!memcmp(&out,&sentinel,sizeof(out)));g.edges[2].target=3;
 g.edges[2].target=5;CHECK(diagnose(&g,budget,no,rows,&out)==COH_STATE);g.edges[2].target=3;
 for(cancel_at=1;cancel_at<128;){int n=cancel_at;CohCancel c={poll,NULL};out=sentinel;CohStatus status=diagnose(&g,budget,c,rows,&out);if(status==COH_OK){CHECK(n>10);break;}CHECK(status==COH_CANCELLED);CHECK(!memcmp(&out,&sentinel,sizeof(out)));cancel_at=n+1;}
 {CohGroupBoundsChild children[5];CohRuntimeBoundsFrame stack[COH_SG_DEPTH_MAX+1u];unsigned char before[sizeof(rows)];
  memset(rows,0x53,sizeof(rows));memcpy(before,rows,sizeof(rows));out=sentinel;
  CHECK(coh_runtime_bounds_diagnose(&g,provider,NULL,&budget,no,rows,5,(CohGroupBoundsChild*)rows,5,stack,COH_SG_DEPTH_MAX+1u,&out)==COH_INVALID);
  CHECK(!memcmp(rows,before,sizeof(rows))&&!memcmp(&out,&sentinel,sizeof(out)));
  CHECK(coh_runtime_bounds_diagnose(&g,provider,NULL,&budget,no,rows,5,children,5,(CohRuntimeBoundsFrame*)rows,COH_SG_DEPTH_MAX+1u,&out)==COH_INVALID);
  CHECK(!memcmp(rows,before,sizeof(rows))&&!memcmp(&out,&sentinel,sizeof(out)));
  CHECK(coh_runtime_bounds_diagnose(&g,provider,NULL,&budget,no,rows,5,children,5,stack,COH_SG_DEPTH_MAX+1u,(CohRuntimeBoundsReport*)rows)==COH_INVALID);
  CHECK(!memcmp(rows,before,sizeof(rows)));
  CHECK(coh_runtime_bounds_diagnose(&g,provider,NULL,(CohRuntimeBoundsBudget*)rows,no,rows,5,children,5,stack,COH_SG_DEPTH_MAX+1u,&out)==COH_INVALID);
  CHECK(!memcmp(rows,before,sizeof(rows)));
  CHECK(coh_runtime_bounds_diagnose(&g,provider,NULL,&budget,no,(CohRuntimeBoundsRow*)catalog_bytes,5,children,5,stack,COH_SG_DEPTH_MAX+1u,&out)==COH_INVALID);
  CHECK(!memcmp(&out,&sentinel,sizeof(out)));
  CHECK(coh_runtime_bounds_diagnose(&g,provider,NULL,&budget,no,rows,5,(CohGroupBoundsChild*)(uintptr_t)(UINTPTR_MAX-2u),5,stack,COH_SG_DEPTH_MAX+1u,&out)==COH_INVALID);
  CHECK(!memcmp(rows,before,sizeof(rows)));
 }
 printf("{\"passed\":true,\"checks\":%u,\"named_peak\":%zu,\"authority\":false}\n",checks,peak);return 0;
}
