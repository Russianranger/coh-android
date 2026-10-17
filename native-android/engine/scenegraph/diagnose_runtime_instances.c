#include "coh_runtime_instances.h"
#include "../scenecatalog/coh_scenecatalog.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
typedef struct {uint64_t total,models;} Counts;
typedef struct {uint32_t node,next;Counts count;} CountFrame;
static CohStatus digest(void*context,CohBytes bytes,uint8_t out[32]){(void)context;return SHA256(bytes.data,bytes.size,out)?COH_OK:COH_INVALID;}
static int hex(const char*s,uint8_t*out){if(strlen(s)!=64)return 0;for(unsigned i=0;i<32;i++){unsigned value;if(sscanf(s+i*2,"%2x",&value)!=1)return 0;out[i]=(uint8_t)value;}return 1;}
static CohStatus load(const char*path,size_t max,CohBytes*out){FILE*f=fopen(path,"rb");if(!f)return COH_IO;if(fseek(f,0,SEEK_END)){fclose(f);return COH_IO;}long size=ftell(f);if(size<=0||(unsigned long)size>max){fclose(f);return COH_LIMIT;}rewind(f);uint8_t*p=malloc((size_t)size);if(!p){fclose(f);return COH_LIMIT;}size_t read=fread(p,1,(size_t)size,f);int error=ferror(f);fclose(f);if(error||read!=(size_t)size){free(p);return COH_IO;}*out=(CohBytes){p,(size_t)size};return COH_OK;}
/* Independent bounded DAG recurrence, never a per-occurrence flattening.
 * A shared node is memoized once, then its multiplicity is added at EVERY edge. */
static CohStatus count_root(const CohRuntimeGraph*g,uint32_t root,uint32_t nodes,uint64_t limit,
 Counts*memo,uint8_t*color,CountFrame*stack,Counts*out){
 uint32_t depth=1;CohRuntimeGraphNode node;TRY(coh_runtime_graph_node(g,root,&node));if(root>=nodes)return COH_STATE;
 if(color[root]==2){*out=memo[root];return COH_OK;}
 stack[0]=(CountFrame){root,0,{1,node.source_model_present}};color[root]=1;
 while(depth){CountFrame*f=&stack[depth-1];TRY(coh_runtime_graph_node(g,f->node,&node));
  if(f->next==node.child_count){memo[f->node]=f->count;color[f->node]=2;depth--;continue;}
  CohRuntimeGraphChild child;TRY(coh_runtime_graph_child(g,node.child_first+f->next,&child));if(child.target>=nodes)return COH_STATE;
  if(color[child.target]==1)return COH_INVALID;
  if(color[child.target]==2){Counts add=memo[child.target];if(add.total>limit-f->count.total||add.models>limit-f->count.models)return COH_LIMIT;f->count.total+=add.total;f->count.models+=add.models;f->next++;continue;}
  if(depth==COH_SG_DEPTH_MAX+1u)return COH_LIMIT;
  TRY(coh_runtime_graph_node(g,child.target,&node));stack[depth++]=(CountFrame){child.target,0,{1,node.source_model_present}};color[child.target]=1;
 }
 *out=memo[root];return COH_OK;
}
static uint64_t hash_value(uint64_t h,uint64_t v,unsigned bytes){for(unsigned n=0;n<bytes;n++){h^=(uint8_t)(v>>(n*8));h*=UINT64_C(1099511628211);}return h;}
static CohStatus diagnose(CohRuntimeGraph*g,const CohRuntimeGraphReport*graph,uint64_t maximum){
 size_t bytes=(size_t)graph->nodes*(sizeof(Counts)+1)+(size_t)graph->source.root_slots*sizeof(Counts)*2+(COH_SG_DEPTH_MAX+1u)*sizeof(CountFrame);
 Counts*memo=calloc(graph->nodes,sizeof(*memo)),*expected=calloc(graph->source.root_slots,sizeof(*expected)),*observed=calloc(graph->source.root_slots,sizeof(*observed));uint8_t*color=calloc(graph->nodes,1);CountFrame*stack=calloc(COH_SG_DEPTH_MAX+1u,sizeof(*stack));CohStatus status=COH_LIMIT;Counts total={0};uint32_t unique=0,unique_models=0;
 if(!memo||!color||!stack||(graph->source.root_slots&&(!expected||!observed)))goto end;
 for(uint32_t root=0;root<graph->source.root_slots;root++){CohRuntimeGraphRoot r;status=coh_runtime_graph_root(g,root,&r);if(status!=COH_OK)goto end;if(!r.active)continue;status=count_root(g,r.node,graph->nodes,maximum,memo,color,stack,&expected[root]);if(status!=COH_OK)goto end;if(expected[root].total>maximum-total.total||expected[root].models>maximum-total.models){status=COH_LIMIT;goto end;}total.total+=expected[root].total;total.models+=expected[root].models;}
 for(uint32_t i=0;i<graph->nodes;i++)if(color[i]==2){CohRuntimeGraphNode n;status=coh_runtime_graph_node(g,i,&n);if(status!=COH_OK)goto end;unique++;unique_models+=n.source_model_present;}
 if(unique!=graph->source.reachable_definitions+graph->source.reachable_external){status=COH_STATE;goto end;}
 CohRuntimeInstances cursor;CohRuntimeInstancesConfig config={maximum,COH_RUNTIME_INSTANCE_WORK_MAX};CohRuntimeInstancesBudget budget={COH_SG_TRANSACTION_MAX,262144+bytes};CohRuntimeInstancesReport report;CohRuntimeInstance batch[256];
 status=coh_runtime_instances_begin(g,&config,&budget,&cursor,&report);if(status!=COH_OK)goto end;
 uint64_t next=0,hash=UINT64_C(1469598103934665603);uint32_t batches=0;size_t peak=0;
 do {status=coh_runtime_instances_next(&cursor,batch,256,4096,(CohCancel){0},&report);if(status!=COH_OK)goto end;batches++;if(report.aggregate_reserved_bytes>peak)peak=report.aggregate_reserved_bytes;
  for(uint32_t i=0;i<report.batch_count;i++){const CohRuntimeInstance*r=&batch[i];if(r->ordinal!=next++||r->root_slot>=graph->source.root_slots||((r->depth==0)!=(r->parent_ordinal==UINT64_MAX))||(r->depth&&r->parent_ordinal>=r->ordinal)){status=COH_STATE;goto end;}observed[r->root_slot].total++;observed[r->root_slot].models+=r->model_present;hash=hash_value(hash,r->node,4);hash=hash_value(hash,r->root_slot,4);hash=hash_value(hash,r->ordinal,8);hash=hash_value(hash,r->parent_ordinal,8);for(unsigned c=0;c<4;c++)for(unsigned j=0;j<3;j++){uint32_t value;memcpy(&value,&r->world[c][j],4);hash=hash_value(hash,value,4);}}
 }while(!report.complete);
 if(next!=total.total||report.occurrences!=total.total||report.model_occurrences!=total.models){status=COH_STATE;goto end;}
 for(uint32_t i=0;i<graph->source.root_slots;i++)if(observed[i].total!=expected[i].total||observed[i].models!=expected[i].models){status=COH_STATE;goto end;}
 printf("{\"passed\":true,\"unique_reachable_nodes\":%u,\"unique_reachable_model_nodes\":%u,\"occurrences\":%llu,\"model_occurrences\":%llu,\"external_occurrences\":%llu,\"work\":%llu,\"maximum_depth\":%u,\"active_roots\":%u,\"batches\":%u,\"independent_dag_count_equal\":true,\"ordered_transform_fnv64\":\"%016llx\",\"count_workspace_bytes\":%zu,\"named_reservation_bytes\":%zu,\"per_root\":[",unique,unique_models,(unsigned long long)report.occurrences,(unsigned long long)report.model_occurrences,(unsigned long long)report.external_occurrences,(unsigned long long)report.work,report.maximum_depth,report.roots_started,batches,(unsigned long long)hash,bytes,peak);
 for(uint32_t i=0;i<graph->source.root_slots;i++)printf("%s{\"root\":%u,\"occurrences\":%llu,\"model_occurrences\":%llu}",i?",":"",i,(unsigned long long)observed[i].total,(unsigned long long)observed[i].models);
 printf("],\"source_generation_admitted\":false,\"assets_admitted\":false,\"world_authority\":false}\n");status=COH_OK;
 end:free(stack);free(color);free(observed);free(expected);free(memo);return status;
}
int main(int argc,char**argv){
 CohBytes catalog={0},snapshot={0};CohRuntimeGraph*g=NULL;CohRuntimeGraphBinding binding={0};CohRuntimeGraphReport report;CohStatus status=COH_INVALID;
 if(argc!=9)goto end;
 binding.generation=1;binding.catalog_generation=(uint32_t)strtoul(argv[3],NULL,10);binding.pins.asset_generation=binding.catalog_generation;binding.pins.digest=digest;
 if(!hex(argv[4],binding.pins.catalog_sha256)||!hex(argv[5],binding.pins.snapshot_sha256)||!hex(argv[6],binding.pins.source_sha256)||!hex(argv[7],binding.pins.run_sha256))goto end;
 char*tail=NULL;unsigned long maximum=strtoul(argv[8],&tail,10);if(!tail||*tail||!maximum||maximum>COH_RUNTIME_INSTANCE_COUNT_MAX)goto end;
 status=load(argv[1],COH_CATALOG_INPUT_MAX,&catalog);if(status!=COH_OK)goto end;status=load(argv[2],COH_RUNTIME_SNAPSHOT_INPUT_MAX,&snapshot);if(status!=COH_OK)goto end;
 CohRuntimeSnapshotBudget budget={COH_SG_TRANSACTION_MAX,262144};status=coh_runtime_graph_build(NULL,catalog,snapshot,&binding,&budget,NULL,&g,&report);if(status!=COH_OK)goto end;status=diagnose(g,&report,maximum);
 end:if(status!=COH_OK)printf("{\"passed\":false,\"status\":%u,\"complete\":false,\"world_authority\":false}\n",(unsigned)status);coh_runtime_graph_free(g);free((void*)snapshot.data);free((void*)catalog.data);return status==COH_OK?0:2;
}
