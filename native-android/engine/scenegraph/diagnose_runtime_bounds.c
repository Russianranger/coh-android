/* Host-only bounded source bounds diagnostic. Owner setup adapted from the
 * independently qualified scenecatalog/validate_resource_join.c; no GEO I/O. */
#include "../scenecatalog/coh_resource_join.h"
#include "coh_runtime_bounds.h"
#include "coh_scene_metadata.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static CohStatus digest(void *context,CohBytes bytes,uint8_t out[32]){(void)context;return SHA256(bytes.data,bytes.size,out)?COH_OK:COH_IO;}
static int hex(const char *s,uint8_t out[32]){if(strlen(s)!=64)return 0;for(unsigned n=0;n<32;n++){unsigned a=(unsigned char)s[2*n],b=(unsigned char)s[2*n+1];a=a>='0'&&a<='9'?a-'0':a>='a'&&a<='f'?a-'a'+10:16;b=b>='0'&&b<='9'?b-'0':b>='a'&&b<='f'?b-'a'+10:16;if(a>15||b>15)return 0;out[n]=(uint8_t)(16*a+b);}return 1;}
static CohStatus read_file(const char *path,size_t cap,CohBytes *out){FILE *f=fopen(path,"rb");if(!f)return COH_IO;if(fseek(f,0,SEEK_END)){fclose(f);return COH_IO;}long n=ftell(f);if(n<=0||(size_t)n>cap){fclose(f);return COH_LIMIT;}rewind(f);uint8_t *data=malloc((size_t)n);if(!data){fclose(f);return COH_LIMIT;}size_t got=fread(data,1,(size_t)n,f);int closed=fclose(f);if(got!=(size_t)n||closed){free(data);return COH_IO;}*out=(CohBytes){data,(size_t)n};return COH_OK;}
typedef struct {const CohResourceSource *sources;size_t count;uint32_t *map;uint32_t generation,asset_generation;} BoundsContext;
static CohStatus definition_input(void *opaque,uint32_t index,const CohRuntimeGraphNode *node,CohGroupBoundsInput *out){
    BoundsContext *c=opaque;CohResourceView view;CohStatus s;CohRepReader reader;CohSgDefinition d={0};CohSgMetadata metadata;size_t owned=0;
    if(c->map[index]>=c->count)return COH_STATE;
    s=coh_resource_source_view(c->sources[c->map[index]].record,c->asset_generation,&view);if(s!=COH_OK)return s;
    if(view.owner_kind!=1||view.file!=node->file||view.slot!=node->slot||strcmp(view.definition_name,node->name))return COH_STATE;
    s=coh_rep_reader_bounded(&reader,node->wire,node->wire_bits,(int)node->aligned,COH_REP_BOUNDED_MESSAGE_MAX);if(s!=COH_OK)return s;
    s=coh_scenegraph_definition_read(&d,&reader,node->file,8u<<20,&owned);if(s!=COH_OK)return s;
    if(reader.cursor!=node->wire_bits||d.child_count!=node->child_count||strcmp(d.name,node->name)){coh_scenegraph_definition_dispose(&d);return COH_STATE;}
    CohSceneGraph one={0};one.generation=c->generation;one.asset_generation=c->asset_generation;one.definition_count=1;one.definitions=&d;
    s=coh_scenegraph_metadata(&one,0,&metadata);
    if(s==COH_OK){out->model_present=view.model_present;out->has_volume=metadata.has_volume;memcpy(out->box_scale,metadata.box_scale,sizeof(out->box_scale));memcpy(out->model_min,view.source_min,sizeof(out->model_min));memcpy(out->model_max,view.source_max,sizeof(out->model_max));}
    coh_scenegraph_definition_dispose(&d);return s;
}
static void json_name(const char *s){putchar('"');for(;*s;s++){unsigned c=(unsigned char)*s;if(c=='"'||c=='\\')printf("\\%c",c);else if(c<32||c>126)printf("\\u%04x",c);else putchar((int)c);}putchar('"');}
static CohStatus actual_bounds(CohRuntimeGraph *graph,CohResourceJoin *join,CohCatalogOwner *catalog,CohCatalogSnapshot *snapshot,size_t join_owned,CohRuntimeBoundsReport *out){
    CohRuntimeGraphReport gr;CohStatus s=coh_runtime_graph_report(graph,&gr);if(s!=COH_OK)return s;
    size_t max_children=1;for(uint32_t n=0;n<gr.nodes;n++){CohRuntimeGraphNode node;s=coh_runtime_graph_node(graph,n,&node);if(s!=COH_OK)return s;if(node.reachable&&node.child_count>max_children)max_children=node.child_count;}
    CohRuntimeBoundsRow *rows=calloc(gr.nodes,sizeof(*rows));CohGroupBoundsChild *children=calloc(max_children,sizeof(*children));CohRuntimeBoundsFrame *frames=calloc(COH_SG_DEPTH_MAX+1u,sizeof(*frames));uint32_t *map=malloc(gr.nodes*sizeof(*map));
    if(!rows||!children||!frames||!map){s=COH_LIMIT;goto end;}
    for(uint32_t n=0;n<gr.nodes;n++)map[n]=UINT32_MAX;
    BoundsContext context={0};CohResourceBinding rb;
    s=coh_resource_join_sources(join,&context.sources,&context.count,&rb);if(s!=COH_OK)goto end;
    for(size_t n=0;n<context.count;n++){uint32_t node;s=coh_resource_join_node(join,(uint32_t)n,&node);if(s!=COH_OK||node>=gr.nodes||map[node]!=UINT32_MAX){s=COH_STATE;goto end;}map[node]=(uint32_t)n;}
context.map=map;context.generation=gr.generation;context.asset_generation=rb.asset_generation;
    /* Actual live owner payloads, plus map+provider decode budget; caller adds join payload. */
    CohRuntimeBoundsBudget b={96u<<20,coh_catalog_owner_owned_bytes(catalog)+coh_catalog_snapshot_owned_bytes(snapshot)+gr.nodes*sizeof(*map)+(8u<<20)+262144u};
    b.retained_bytes+=join_owned;
    s=coh_runtime_bounds_diagnose(graph,definition_input,&context,&b,(CohCancel){NULL,NULL},rows,gr.nodes,children,max_children,frames,COH_SG_DEPTH_MAX+1u,out);
    if(s==COH_OK){
        int comma=0;printf("{\"blocker_nodes\":[");
        for(uint32_t n=0;n<gr.nodes;n++)if(rows[n].color==2&&rows[n].result!=COH_RB_COMPUTED&&rows[n].result!=COH_RB_CAPTURED_FUTURE){CohRuntimeGraphNode node;coh_runtime_graph_node(graph,n,&node);if(comma++)putchar(',');printf("{\"node\":%u,\"file\":%u,\"slot\":%u,\"external\":%u,\"result\":%u,\"name\":",n,node.file,node.slot,node.external,rows[n].result);json_name(node.name);putchar('}');}
        printf("],\"blocked_root_records\":[");comma=0;
        for(uint32_t n=0;n<gr.source.root_slots;n++){CohRuntimeGraphRoot root;coh_runtime_graph_root(graph,n,&root);if(root.active&&rows[root.node].result!=COH_RB_COMPUTED&&rows[root.node].result!=COH_RB_CAPTURED_FUTURE){if(comma++)putchar(',');printf("{\"root_slot\":%u,\"node\":%u}",n,root.node);}}
        printf("],\"future_bounds\":[");comma=0;
        for(uint32_t n=0;n<gr.nodes;n++){CohRuntimeGraphNode node;coh_runtime_graph_node(graph,n,&node);if(node.external){CohRuntimeExternalBounds e;coh_runtime_graph_external_bounds(graph,n,&e);if(comma++)putchar(',');printf("{\"node\":%u,\"reachable\":%u,\"name\":",n,node.reachable);json_name(node.name);printf(",\"lookup_found\":%u,\"live_wire_hex\":\"",e.lookup_found);for(size_t k=0;k<e.live.wire.size;k++)printf("%02x",e.live.wire.data[k]);printf("\",\"lookup_wire_hex\":\"");for(size_t k=0;k<e.lookup.wire.size;k++)printf("%02x",e.lookup.wire.data[k]);printf("\"}");}}
        printf("]}\n");
    }

end:free(map);free(frames);free(children);free(rows);return s;
}
int main(int argc,char **argv){
    CohStatus status=COH_INVALID;CohBytes input={0},side={0},resources={0},cat={0},snapshot_bytes={0};CohCatalogOwner *catalog=NULL;CohCatalogSnapshot *snapshot=NULL;CohRuntimeGraph *graph=NULL;CohResourceJoin *join=NULL;
    CohCatalogBinding cb={0};CohCatalogSnapshotBinding sb={0};CohResourceJoinPins pins={0};CohCatalogDigest dig={NULL,digest};CohCatalogOwnerReport cr={0};CohRuntimeSnapshotReport sr={0};CohRuntimeGraphReport gr={0};CohResourceJoinReport jr={0};CohRuntimeBoundsReport br={0};
    if(argc!=10)goto done;
    cb.owner_generation=1;cb.catalog_generation=20261016;cb.asset_generation=20261016;
    if(!hex("61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763",cb.catalog_sha256)||!hex(argv[4],cb.source_sha256)||!hex(argv[6],cb.inventory_sha256)||!hex(argv[5],sb.run_sha256)||!hex(argv[7],sb.snapshot_sha256)||!hex(argv[8],pins.resources_sha256)||!hex(argv[9],pins.resource.manifest_sha256))goto done;
    status=read_file(argv[1],COH_CATALOG_INPUT_MAX,&input);if(status!=COH_OK)goto done;
    CohCatalogOwnerBudget cbudget={32u<<20,32u<<20,96u<<20,262144};status=coh_catalog_owner_create(NULL,input,&cb,&cbudget,&dig,&catalog,&cr);if(status!=COH_OK)goto done;free((void *)input.data);input=(CohBytes){0};
    status=read_file(argv[2],COH_RUNTIME_SNAPSHOT_INPUT_MAX,&side);if(status!=COH_OK)goto done;sb.generation=1;sb.catalog=cb;CohRuntimeSnapshotBudget sbudget={96u<<20,262144};status=coh_catalog_snapshot_create(NULL,catalog,side,&sb,&sbudget,&dig,NULL,&snapshot);if(status!=COH_OK)goto done;free((void *)side.data);side=(CohBytes){0};
    status=coh_catalog_owner_bytes(catalog,&cat);if(status!=COH_OK)goto done;status=coh_catalog_snapshot_view(snapshot,&snapshot_bytes,&sb,&sr);if(status!=COH_OK)goto done;
    CohRuntimeGraphBinding gb={0};gb.generation=1;gb.catalog_generation=cb.catalog_generation;gb.pins.asset_generation=cb.asset_generation;gb.pins.digest=digest;memcpy(gb.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(gb.pins.snapshot_sha256,sb.snapshot_sha256,32);memcpy(gb.pins.source_sha256,cb.source_sha256,32);memcpy(gb.pins.run_sha256,sb.run_sha256,32);
    CohRuntimeSnapshotBudget gbudget={96u<<20,coh_catalog_owner_owned_bytes(catalog)-cat.size+coh_catalog_snapshot_owned_bytes(snapshot)-snapshot_bytes.size+262144};status=coh_runtime_graph_build(NULL,cat,snapshot_bytes,&gb,&gbudget,NULL,&graph,&gr);if(status!=COH_OK)goto done;
    status=read_file(argv[3],COH_RESOURCE_INPUT_MAX,&resources);if(status!=COH_OK)goto done;pins.resource.generation=1;pins.resource.asset_generation=cb.asset_generation;memcpy(pins.resource.source_sha256,cb.source_sha256,32);memcpy(pins.resource.run_sha256,sb.run_sha256,32);
    CohResourceJoinBudget budget={32u<<20,96u<<20,262144};CohCancel never={NULL,NULL};status=coh_resource_join_build(NULL,catalog,snapshot,graph,resources,&pins,&budget,digest,NULL,never,&join,&jr);
    if(status==COH_OK){free((void*)resources.data);resources=(CohBytes){0};status=actual_bounds(graph,join,catalog,snapshot,jr.owned_bytes,&br);}
 done:
    if(status==COH_OK)printf("{\"passed\":true,\"visited\":%u,\"computed\":%u,\"captured_future\":%u,\"future_missing\":%u,\"definition_missing\":%u,\"child_blocked\":%u,\"active_roots\":%u,\"computed_roots\":%u,\"blocked_roots\":%u,\"first_visit_depth\":%u,\"bounds_workspace_bytes\":%zu,\"bounds_named_reservation_bytes\":%zu,\"graph_generation\":%u,\"catalog_generation\":%u,\"join_import_peak_bytes\":%zu,\"source_observed_model_bounds_only\":true,\"body_bounds_compared\":false,\"source_generation_admitted\":false,\"assets_admitted\":false,\"world_authority\":false}\n",br.visited,br.computed,br.captured_future,br.future_missing,br.definition_missing,br.child_blocked,br.active_roots,br.computed_roots,br.blocked_roots,br.maximum_first_visit_depth,br.workspace_bytes,br.aggregate_reserved_bytes,br.graph.generation,br.graph.catalog_generation,jr.aggregate_peak_bytes);
    else printf("{\"passed\":false,\"status\":%d,\"assets_admitted\":false,\"world_authority\":false}\n",status);
    coh_resource_join_free(join);coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);free((void *)resources.data);free((void *)side.data);free((void *)input.data);return status==COH_OK?0:2;
}
