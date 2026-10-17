#include "coh_resource_join.h"
#include <stdlib.h>
#include <string.h>
#define STACK_RESERVE (128u*1024u)
struct CohResourceJoin {
    uint32_t refs;CohResourceJoinPins pins;CohResourceJoinReport report;
    CohCatalogOwner *catalog;CohCatalogSnapshot *snapshot;const CohRuntimeGraph *graph;
    uint8_t *bytes;size_t size;CohResourceSource *sources;uint32_t *nodes;
};
typedef struct {CohResourceJoin *join;const CohRuntimeGraph *graph;CohResourceDigest digest;void *context;CohCancel cancel;size_t at;uint32_t ordinal;} Match;
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int nz(const uint8_t *p){uint8_t n=0;for(unsigned i=0;i<32;i++)n|=p[i];return n!=0;}
static int catalog_equal(const CohCatalogBinding *a,const CohCatalogBinding *b){return a->owner_generation==b->owner_generation&&a->catalog_generation==b->catalog_generation&&a->asset_generation==b->asset_generation&&a->map_generation==b->map_generation&&!memcmp(a->catalog_sha256,b->catalog_sha256,32)&&!memcmp(a->source_sha256,b->source_sha256,32)&&!memcmp(a->inventory_sha256,b->inventory_sha256,32)&&!memcmp(a->map_sha256,b->map_sha256,32);}
static int resources_equal(const CohResourceBinding *a,const CohResourceBinding *b){return a->generation==b->generation&&a->asset_generation==b->asset_generation&&!memcmp(a->source_sha256,b->source_sha256,32)&&!memcmp(a->run_sha256,b->run_sha256,32)&&!memcmp(a->manifest_sha256,b->manifest_sha256,32);}
static int graph_equal(const CohRuntimeGraphBinding *g,const CohCatalogSnapshotBinding *s){return g->catalog_generation==s->catalog.catalog_generation&&g->pins.asset_generation==s->catalog.asset_generation&&!memcmp(g->pins.catalog_sha256,s->catalog.catalog_sha256,32)&&!memcmp(g->pins.snapshot_sha256,s->snapshot_sha256,32)&&!memcmp(g->pins.source_sha256,s->catalog.source_sha256,32)&&!memcmp(g->pins.run_sha256,s->run_sha256,32);}
CohStatus coh_resource_join_retain(CohResourceJoin *j){if(!j)return COH_INVALID;if(!j->refs||j->refs==UINT32_MAX)return COH_LIMIT;j->refs++;return COH_OK;}
void coh_resource_join_free(CohResourceJoin *j){if(!j)return;if(j->refs>1){j->refs--;return;}coh_catalog_snapshot_release(j->snapshot);coh_catalog_owner_release(j->catalog);free(j->nodes);free(j->sources);free(j->bytes);free(j);}
static CohStatus next(Match *m,uint32_t node,uint32_t kind,uint32_t file,uint32_t slot,uint32_t id,const char *name,const char *geometry){
    if(m->cancel.poll&&m->cancel.poll(m->cancel.context))return COH_CANCELLED;
    CohResourceJoin *j=m->join;if(m->ordinal>=j->report.rows||j->size-m->at<192)return COH_INVALID;
    size_t size=u32(j->bytes+m->at+16);if(size<192||size>j->size-m->at||size>COH_RESOURCE_RECORD_MAX)return COH_INVALID;
    CohBytes bytes={j->bytes+m->at,size};CohResourceView v;CohStatus st=coh_resource_source_view(bytes,j->pins.resource.asset_generation,&v);if(st!=COH_OK)return st;
    if(v.owner_kind!=kind||v.file!=file||v.slot!=slot||v.original_id!=id||strcmp(v.definition_name,name)||
       v.model_present!=!!geometry[0]||(v.model_present&&strcmp(v.model_name,geometry)))return COH_STATE;
    CohResourceSource *source=&j->sources[m->ordinal];source->record=bytes;st=m->digest(m->context,bytes,source->sha256);if(st!=COH_OK)return st;
    j->nodes[m->ordinal]=node;m->ordinal++;m->at+=size;j->report.models+=v.model_present;if(kind==1)j->report.regular++;else j->report.external++;return COH_OK;
}
static CohStatus slot(void *context,const CohCatalogSlotView *v){Match *m=context;uint32_t index;CohRuntimeGraphNode node;CohCatalogRecordIdentity owner;
    if(m->cancel.poll&&m->cancel.poll(m->cancel.context))return COH_CANCELLED;
    CohStatus st=coh_catalog_owner_record(m->join->catalog,v->file->index,v->slot,&owner);if(st!=COH_OK)return st;
    if(owner.allocated!=v->allocated)return COH_STATE;
    st=coh_runtime_graph_slot(m->graph,v->file->index,v->slot,&index);
    if(!v->allocated)return st==COH_NOT_FOUND?COH_OK:COH_STATE;
    if(st!=COH_OK)return st;
    st=coh_runtime_graph_node(m->graph,index,&node);if(st!=COH_OK)return st;
    const CohSgDefinition *d=v->definition;
    if(d->file!=v->file->index||d->id!=v->slot||node.external||node.file!=v->file->index||node.slot!=v->slot||node.in_use!=d->in_use||
       node.wire.data!=v->catalog.data+v->wire_offset||node.wire.size!=v->wire_bytes||node.wire_bits!=v->wire_bits||node.aligned!=v->aligned||
       owner.wire_offset!=v->wire_offset||owner.wire_bytes!=v->wire_bytes||owner.in_use!=d->in_use||strcmp(owner.name,d->name))return COH_STATE;
    if(!d->in_use)return COH_OK;
    if(!node.name||strcmp(node.name,d->name)||node.source_model_present!=!!d->geometry[0])return COH_STATE;
    return next(m,index,1,d->file,d->id,d->id,d->name,d->geometry);
}
static CohStatus add(size_t *total,size_t n,size_t limit){if(*total>limit||n>limit-*total)return COH_LIMIT;*total+=n;return COH_OK;}
CohStatus coh_resource_join_build(const CohResourceJoin *old,CohCatalogOwner *catalog,CohCatalogSnapshot *snapshot,const CohRuntimeGraph *graph,CohBytes input,const CohResourceJoinPins *pins,const CohResourceJoinBudget *budget,CohResourceDigest digest,void *context,CohCancel cancel,CohResourceJoin **out,CohResourceJoinReport *report){
    if(!catalog||!snapshot||!graph||!input.data||!pins||!budget||!digest||!out||!report)return COH_INVALID;
    if(*out||!nz(pins->resources_sha256)||!nz(pins->resource.manifest_sha256))return COH_STATE;
    if(!budget->owned_limit||budget->owned_limit>COH_RESOURCE_INPUT_MAX||!budget->aggregate_limit||budget->aggregate_limit>COH_SG_TRANSACTION_MAX||input.size>COH_RESOURCE_INPUT_MAX)return COH_LIMIT;
    CohCatalogBinding cb;CohCatalogSnapshotBinding sb;CohRuntimeSnapshotReport sr;CohBytes cat,side,gcat,gside,owned_cat;CohRuntimeGraphBinding gb;CohRuntimeGraphReport gr;
    if(coh_catalog_owner_binding(catalog,&cb)!=COH_OK||coh_catalog_owner_bytes(catalog,&cat)!=COH_OK||coh_catalog_snapshot_view(snapshot,&side,&sb,&sr)!=COH_OK||coh_catalog_snapshot_catalog(snapshot,&owned_cat)!=COH_OK||
       coh_runtime_graph_binding(graph,&gb)!=COH_OK||coh_runtime_graph_sources(graph,&gcat,&gside)!=COH_OK||coh_runtime_graph_report(graph,&gr)!=COH_OK)return COH_STATE;
    if(owned_cat.data!=cat.data||owned_cat.size!=cat.size||!catalog_equal(&cb,&sb.catalog)||!graph_equal(&gb,&sb)||gcat.data!=cat.data||gcat.size!=cat.size||gside.data!=side.data||gside.size!=side.size||
       pins->resource.asset_generation!=cb.asset_generation||memcmp(pins->resource.source_sha256,cb.source_sha256,32)||memcmp(pins->resource.run_sha256,sb.run_sha256,32)||
       !pins->resource.generation||!sr.complete_source_name_closure||!sr.definitions_crc_verified||!sr.references_crc_verified||gr.nodes>COH_RESOURCE_ROWS_MAX)return COH_STATE;
    if(old){if(old->pins.resource.generation==UINT32_MAX||pins->resource.generation!=old->pins.resource.generation+1||pins->resource.asset_generation<old->pins.resource.asset_generation)return COH_STATE;
        if(pins->resource.asset_generation==old->pins.resource.asset_generation&&(memcmp(pins->resources_sha256,old->pins.resources_sha256,32)||memcmp(pins->resource.source_sha256,old->pins.resource.source_sha256,32)||memcmp(pins->resource.run_sha256,old->pins.resource.run_sha256,32)||memcmp(pins->resource.manifest_sha256,old->pins.resource.manifest_sha256,32)))return COH_STATE;
    }else if(pins->resource.generation!=1)return COH_STATE;
    uint32_t active=0;for(uint32_t n=0;n<gr.nodes;n++){if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;CohRuntimeGraphNode node;CohStatus st=coh_runtime_graph_node(graph,n,&node);if(st!=COH_OK)return st;if(node.in_use)active++;}
    if(!active||active>COH_RESOURCE_ROWS_MAX)return COH_LIMIT;
    size_t owned=sizeof(CohResourceJoin)+input.size+(size_t)active*(sizeof(CohResourceSource)+sizeof(uint32_t));if(owned>budget->owned_limit)return COH_LIMIT;
    size_t fixed=budget->retained_bytes;CohStatus st;size_t charges[]={owned,input.size,coh_catalog_owner_owned_bytes(catalog),coh_catalog_snapshot_owned_bytes(snapshot),gr.owned_bytes,STACK_RESERVE,old?old->report.owned_bytes:0};
    for(unsigned n=0;n<sizeof(charges)/sizeof(charges[0]);n++)if((st=add(&fixed,charges[n],budget->aggregate_limit))!=COH_OK)return st;
    if(old){if(old->catalog!=catalog&&(st=add(&fixed,coh_catalog_owner_owned_bytes(old->catalog),budget->aggregate_limit))!=COH_OK)return st;if(old->snapshot!=snapshot&&(st=add(&fixed,coh_catalog_snapshot_owned_bytes(old->snapshot),budget->aggregate_limit))!=COH_OK)return st;if(old->graph!=graph){CohRuntimeGraphReport prior;if(coh_runtime_graph_report(old->graph,&prior)!=COH_OK)return COH_STATE;if((st=add(&fixed,prior.owned_bytes,budget->aggregate_limit))!=COH_OK)return st;}}
    if(COH_CATALOG_WALK_STACK_RESERVE>budget->aggregate_limit-fixed)return COH_LIMIT;
    CohResourceJoin *j=calloc(1,sizeof(*j));if(!j)return COH_LIMIT;j->refs=1;j->pins=*pins;j->size=input.size;j->graph=graph;j->report.rows=active;j->report.owned_bytes=owned;j->report.graph_generation=gr.generation;j->report.catalog_generation=cb.catalog_generation;
    j->bytes=malloc(input.size);j->sources=calloc(active,sizeof(*j->sources));j->nodes=calloc(active,sizeof(*j->nodes));st=COH_LIMIT;if(!j->bytes||!j->sources||!j->nodes)goto fail;
    memcpy(j->bytes,input.data,input.size);uint8_t hash[32];st=digest(context,(CohBytes){j->bytes,j->size},hash);if(st!=COH_OK)goto fail;if(memcmp(hash,pins->resources_sha256,32)){st=COH_STATE;goto fail;}
    /* Store borrowed catalog for callbacks; acquire real references only after
     * complete validation so rollback never drops an unowned reference. */
    j->catalog=catalog;Match m={j,graph,digest,context,cancel,0,0};CohCatalogVisitor visitor={&m,NULL,slot};
    CohCatalogWalkBudget walk={COH_CATALOG_MEMORY_MAX,budget->aggregate_limit,fixed-cat.size};CohCatalogWalkReport wr;
    st=coh_scenecatalog_walk(cat,cb.catalog_generation,&walk,&visitor,&wr);if(st!=COH_OK)goto fail_borrow;
    j->report.peak_record_bytes=wr.peak_record_owned_bytes;j->report.aggregate_peak_bytes=wr.peak_aggregate_bytes;
    for(uint32_t ordinal=0;ordinal<sr.external_count;ordinal++){
        /* Graph externals are kept after every original saved slot; name lookup
         * ties the exact captured sidecar owner to its own distinct graph node. */
        uint32_t index;if((st=coh_runtime_graph_name(graph,sr.external[ordinal].name,&index))!=COH_OK)goto fail_borrow;CohRuntimeGraphNode node;if((st=coh_runtime_graph_node(graph,index,&node))!=COH_OK)goto fail_borrow;
        if(index!=gr.source.definitions+ordinal||!node.external||node.file!=UINT32_MAX||node.slot!=sr.external[ordinal].original_id||!node.in_use){st=COH_STATE;goto fail_borrow;}
        size_t available=budget->aggregate_limit-fixed;if(available>COH_SG_MEMORY_MAX)available=COH_SG_MEMORY_MAX;
        CohSgDefinition definition={0};CohRepReader reader;size_t bytes=0;st=coh_rep_reader_bounded(&reader,node.wire,node.wire_bits,node.aligned,COH_REP_BOUNDED_MESSAGE_MAX);if(st!=COH_OK)goto fail_borrow;
        st=coh_scenegraph_definition_read(&definition,&reader,0,available,&bytes);
        if(st==COH_OK&&(reader.cursor!=node.wire_bits||definition.id!=sr.external[ordinal].original_id||!definition.in_use||strcmp(definition.name,node.name)||node.source_model_present!=!!definition.geometry[0]))st=COH_STATE;
        if(st==COH_OK)st=next(&m,index,2,UINT32_MAX,ordinal,definition.id,definition.name,definition.geometry);
        if(bytes>j->report.peak_record_bytes)j->report.peak_record_bytes=bytes;
        if(fixed+bytes>j->report.aggregate_peak_bytes)j->report.aggregate_peak_bytes=fixed+bytes;
        coh_scenegraph_definition_dispose(&definition);if(st!=COH_OK)goto fail_borrow;
    }
    if(m.ordinal!=active||m.at!=j->size){st=COH_STATE;goto fail_borrow;}
    j->catalog=NULL;st=coh_catalog_owner_retain(catalog);if(st!=COH_OK)goto fail;j->catalog=catalog;
    st=coh_catalog_snapshot_retain(snapshot);if(st!=COH_OK)goto fail;j->snapshot=snapshot;j->report.source_association_verified=1;*report=j->report;*out=j;return COH_OK;
fail_borrow:j->catalog=NULL;
fail:coh_resource_join_free(j);return st;
}
CohStatus coh_resource_join_sources(const CohResourceJoin *j,const CohResourceSource **sources,size_t *count,CohResourceBinding *binding){if(!j||!sources||!count||!binding)return COH_INVALID;*sources=j->sources;*count=j->report.rows;*binding=j->pins.resource;return COH_OK;}
CohStatus coh_resource_join_node(const CohResourceJoin *j,uint32_t ordinal,uint32_t *out){if(!j||!out)return COH_INVALID;if(ordinal>=j->report.rows)return COH_NOT_FOUND;*out=j->nodes[ordinal];return COH_OK;}
CohStatus coh_resource_join_match_index(const CohResourceJoin *j,const CohResourceIndex *index,CohCancel cancel){if(!j||!index)return COH_INVALID;CohResourceBinding binding;CohResourceReport report;CohStatus st=coh_resource_index_metadata(index,&binding,&report);if(st!=COH_OK)return st;if(!resources_equal(&binding,&j->pins.resource)||report.rows!=j->report.rows)return COH_STATE;for(uint32_t n=0;n<j->report.rows;n++){if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;CohBytes bytes;CohResourceView view;st=coh_resource_index_record(index,n,&bytes,&view);if(st!=COH_OK)return st;if(bytes.size!=j->sources[n].record.size||memcmp(bytes.data,j->sources[n].record.data,bytes.size))return COH_STATE;}return COH_OK;}

static int identity_disjoint(const void *a,size_t an,const void *b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!an||!bn)return 1;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;
 return x+an<=y||y+bn<=x;
}
CohStatus coh_resource_join_identity(const CohResourceJoin *j,CohResourceJoinIdentity *out){
 if(!j||!out)return COH_INVALID;
 CohResourceJoinIdentity v={0};CohRuntimeGraphReport graph;CohCatalogSnapshotBinding sb;CohRuntimeSnapshotReport sr;
 if(!j->refs||!j->catalog||!j->snapshot||!j->graph||!j->report.source_association_verified)return COH_STATE;
 if(coh_catalog_owner_bytes(j->catalog,&v.catalog_bytes)!=COH_OK||coh_catalog_snapshot_view(j->snapshot,&v.snapshot_bytes,&sb,&sr)!=COH_OK||coh_runtime_graph_report(j->graph,&graph)!=COH_OK)return COH_STATE;
 const void *starts[]={j,j->bytes,j->sources,j->nodes,v.catalog_bytes.data,v.snapshot_bytes.data};
 size_t sizes[]={sizeof(*j),j->size,(size_t)j->report.rows*sizeof(*j->sources),(size_t)j->report.rows*sizeof(*j->nodes),v.catalog_bytes.size,v.snapshot_bytes.size};
 for(unsigned k=0;k<6;k++)if(!identity_disjoint(out,sizeof(*out),starts[k],sizes[k]))return COH_INVALID;
 v.pins=j->pins;v.report=j->report;v.catalog_identity=j->catalog;v.snapshot_identity=j->snapshot;v.graph_identity=j->graph;
 v.catalog_owned_bytes=coh_catalog_owner_owned_bytes(j->catalog);v.snapshot_owned_bytes=coh_catalog_snapshot_owned_bytes(j->snapshot);v.graph_owned_bytes=graph.owned_bytes;v.resource_bytes=(CohBytes){j->bytes,j->size};*out=v;return COH_OK;
}
