#include "runtime_snapshot.h"
#include "runtime_graph.h"
#include "../scenecatalog/coh_scenecatalog.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define HEADER_BYTES 80u
#define ROOT_BYTES 32u
#define EXTERNAL_BYTES 36u
#define BOUNDS_BYTES 60u
#define RECORD_MAX (4u*1024u*1024u)
#define NO_INDEX UINT32_MAX
#define PROBES 256u
#define TRY(call) do{CohStatus status_=(call);if(status_!=COH_OK)return status_;}while(0)
extern CohStatus coh_runtime_matrix_read(CohRepReader *,CohSgMatrix);
typedef struct {uint32_t first,count;} File;
typedef struct {uint32_t name,external,file,slot,active,first,count;} Node;
typedef struct {uint32_t name,path,wire,bytes,bits,id,model,lookup;} External;
typedef struct {uint32_t wire,bytes,bits,aligned,model,empty_future;} Detail;
struct CohRuntimeGraph {
    CohBytes catalog,snapshot;CohRuntimeGraphBinding binding;CohRuntimeGraphReport report;
    const CohRuntimeGraph *prior;void *pool;File *files;Node *nodes;uint32_t *slots,*names,*edges;
    Detail *details;CohSgMatrix *matrices;CohRuntimeGraphRoot *roots;
    uint8_t *colors;uint32_t capacity;
};
typedef struct {
    CohBytes catalog,snapshot;const CohRuntimeSnapshotPins*pins;
    const CohCancel*cancel;CohRuntimeSnapshotReport*r;
    External external[COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX];
    uint8_t discovered[COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX];
    File*files;Node*nodes;uint32_t*slots,*names,*edges;uint16_t*heights;uint8_t*colors;
    uint32_t capacity,nodes_count,edges_count,file,slot,node,edge,phase,root_end;
    size_t base,available;
    CohRuntimeGraph *graph;
} Audit;
typedef char RuntimeReportFits[sizeof(CohRuntimeSnapshotReport)<64u*1024u?1:-1];
typedef char RuntimeStackReserveFits[
    sizeof(Audit)+sizeof(CohRuntimeSnapshotReport)+(COH_SG_DEPTH_MAX+1u)*128u+8192u
    <=COH_RUNTIME_SNAPSHOT_STACK_RESERVE?1:-1];
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int same(const char*a,const char*b){while(*a&&*b)if(lower((unsigned char)*a++)!=lower((unsigned char)*b++))return 0;return *a==*b;}
static int nonzero(const uint8_t*p){unsigned value=0;for(unsigned i=0;i<32;i++)value|=p[i];return value!=0;}
static CohStatus poll(Audit*a){return a->cancel&&a->cancel->poll&&a->cancel->poll(a->cancel->context)?COH_CANCELLED:COH_OK;}
static const char*node_name(const Audit*a,uint32_t i){const Node*n=&a->nodes[i];return (const char*)(n->external?a->snapshot.data:a->catalog.data)+n->name;}
static CohStatus span(CohBytes in,size_t*at,size_t n,const uint8_t**p){if(*at>in.size||n>in.size-*at)return COH_INVALID;*p=in.data+*at;*at+=n;return COH_OK;}
static CohStatus string(CohBytes in,size_t*at,uint32_t n,uint32_t*out,int path){
    const uint8_t*p;if(n<2||n>COH_REP_NAME_MAX)return COH_INVALID;
    *out=(uint32_t)*at;TRY(span(in,at,n,&p));if(p[n-1])return COH_INVALID;
    for(uint32_t i=0;i+1<n;i++)if(p[i]<32||p[i]>126||p[i]=='\\'||(!path&&p[i]=='/'))return COH_UNSUPPORTED;
    return COH_OK;
}
static CohStatus bounds(const uint8_t*p){
    for(unsigned i=0;i<13;i++){uint32_t bits=u32(p+i*4);float f;memcpy(&f,&bits,4);if(!isfinite(f))return COH_INVALID;}
    if(u32(p+52)>INT32_MAX||(u32(p+56)&~((1u<<26)-1)))return COH_UNSUPPORTED;
    return COH_OK;
}
static CohStatus matrix_pair(const uint8_t*raw,CohBytes wire,uint32_t bits){
    if(!wire.size||wire.size>256u||bits!=wire.size*8u)return COH_INVALID;
    CohRepReader r;CohSgMatrix decoded;TRY(coh_rep_reader_bounded(&r,wire,bits,1,COH_REP_BOUNDED_MESSAGE_MAX));
    TRY(coh_runtime_matrix_read(&r,decoded));if(r.cursor!=bits)return COH_INVALID;
    for(unsigned col=0;col<4;col++)for(unsigned row=0;row<3;row++){
        uint32_t value=u32(raw+(col*3+row)*4);float f;memcpy(&f,&value,4);
        /* Native trigonometry may differ by a few float ULPs from the original
         * compiler. Position is sent exactly; basis uses a fixed relative
         * tolerance, independently checked against unchanged source packMat. */
        if(!isfinite(f)||!isfinite(decoded[col][row]))return COH_INVALID;
        if(col==3){if(f!=decoded[col][row])return COH_INVALID;}
        else if(fabsf(f-decoded[col][row])>0.000002f*fmaxf(1.0f,fabsf(f)))return COH_INVALID;
    }
    return COH_OK;
}
static CohStatus roots_scan(Audit*a,int resolve);
static CohStatus envelope(Audit*a,const CohCatalogReport*scan){
    CohBytes in=a->snapshot;if(in.size<HEADER_BYTES||in.size>COH_RUNTIME_SNAPSHOT_INPUT_MAX)return COH_LIMIT;
    const uint8_t*p=in.data;
    if(memcmp(p,"COHRTS01",8)||u32(p+8)!=1||u32(p+12)!=HEADER_BYTES||u32(p+16)!=in.size)return COH_INVALID;
    if(u32(p+20)!=a->pins->asset_generation||u32(p+24)!=a->catalog.size||u32(p+28)!=scan->files||u32(p+32)!=scan->slots||u32(p+36)!=scan->definitions||u32(p+40)!=scan->children||u32(p+48)!=scan->source_active_roots||u32(p+56)!=scan->source_defs_crc||u32(p+60)!=scan->source_refs_crc)return COH_STATE;
    for(unsigned i=64;i<80;i++)if(p[i])return COH_UNSUPPORTED;
    a->r->root_slots=u32(p+44);a->r->active_roots=u32(p+48);a->r->external_count=u32(p+52);
    if(a->r->root_slots>COH_SG_ROOTS_MAX||a->r->active_roots>a->r->root_slots||a->r->external_count>COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX)return COH_LIMIT;
    TRY(roots_scan(a,0));size_t at=a->root_end;
    for(uint32_t i=0;i<a->r->external_count;i++){
        TRY(poll(a));TRY(span(in,&at,EXTERNAL_BYTES,&p));External*e=&a->external[i];
        if(u32(p)!=i||u32(p+8)!=15||u32(p+12)>1||u32(p+28)>1)return COH_INVALID;
        e->id=u32(p+4);e->model=u32(p+12);e->bits=u32(p+20);e->bytes=u32(p+24);e->lookup=u32(p+28);
        uint32_t name_bytes=u32(p+16),path_bytes=u32(p+32);
        if(e->id>COH_GROUPS_DEF_ID_MAX||!e->bytes||e->bytes>RECORD_MAX||e->bits!=e->bytes*8u)return COH_LIMIT;
        const uint8_t*live,*lookup;TRY(span(in,&at,BOUNDS_BYTES,&live));TRY(span(in,&at,BOUNDS_BYTES,&lookup));TRY(bounds(live));TRY(bounds(lookup));
        /* A lookup miss cannot supply invented cached bounds. A successful
         * lookup is a separate observation: live bounds may have been updated. */
        if(!e->lookup)for(unsigned j=0;j<BOUNDS_BYTES;j++)if(lookup[j])return COH_INVALID;
        TRY(string(in,&at,name_bytes,&e->name,0));
        if(path_bytes){TRY(string(in,&at,path_bytes,&e->path,1));}else e->path=0;
        e->wire=(uint32_t)at;TRY(span(in,&at,e->bytes,&p));
    }
    return at==in.size?COH_OK:COH_INVALID;
}
static uint32_t hash(const char*s){uint32_t h=2166136261u;for(;*s;s++){h^=lower((unsigned char)*s);h*=16777619u;}return h;}
static CohStatus lookup(Audit*a,const char*s,uint32_t*out){
    const char*base=strrchr(s,'/');s=base?base+1:s;if(!*s||strchr(s,'\\'))return COH_UNSUPPORTED;
    uint32_t at=hash(s)&(a->capacity-1);
    for(unsigned p=0;p<PROBES;p++,at=(at+1)&(a->capacity-1)){
        uint32_t n=a->names[at];if(!n)return COH_NOT_FOUND;
        if(same(node_name(a,n-1),s)){*out=n-1;return COH_OK;}
    }
    return COH_NOT_FOUND;
}
static CohStatus add_name(Audit*a,uint32_t n){
    const char*s=node_name(a,n);uint32_t at=hash(s)&(a->capacity-1);
    for(unsigned p=0;p<PROBES;p++,at=(at+1)&(a->capacity-1)){
        if(!a->names[at]){a->names[at]=n+1;return COH_OK;}
        if(same(node_name(a,a->names[at]-1),s))return COH_INVALID;
    }
    return COH_LIMIT;
}
static CohStatus name_offset(const CohCatalogSlotView*v,uint32_t*out){
    CohRepReader r;uint32_t id,active;TRY(coh_rep_reader_bounded(&r,(CohBytes){v->catalog.data+v->wire_offset,v->wire_bytes},v->wire_bits,(int)v->aligned,COH_REP_BOUNDED_MESSAGE_MAX));
    TRY(coh_rep_pack(&r,1,&id));TRY(coh_rep_read(&r,1,&active));
    if(!v->aligned||(r.cursor&7)||id!=v->slot+1||active!=1)return COH_STATE;
    *out=(uint32_t)(v->wire_offset+r.cursor/8);return COH_OK;
}
static CohStatus file_visit(void*context,const CohCatalogFileView*v){
    Audit*a=context;TRY(poll(a));if(v->index!=a->file||v->index>=a->r->files||v->slots>a->r->slots-a->slot)return COH_STATE;
    File*f=&a->files[a->file++];if(a->phase==1){f->first=a->slot;f->count=v->slots;}else if(f->first!=a->slot||f->count!=v->slots)return COH_STATE;
    a->slot+=v->slots;return COH_OK;
}
static CohStatus fill_edges(Audit*a,Node*n,const CohSgDefinition*d){
    if(d->child_count!=n->count||n->first>a->edges_count||n->count>a->edges_count-n->first)return COH_STATE;
    for(uint32_t j=0;j<n->count;j++){
        uint32_t target;TRY(lookup(a,d->children[j].name,&target));
        if(!a->nodes[target].active)return COH_UNSUPPORTED;
        /* The observer proves canonical name-to-pointer identity. Original
         * sendDef emits that target's actual name, not a caller spelling. */
        if(strcmp(node_name(a,target),d->children[j].name))return COH_STATE;
        a->edges[n->first+j]=target;
        if(a->graph)memcpy(a->graph->matrices[n->first+j],d->children[j].matrix,sizeof(CohSgMatrix));
        if(a->nodes[target].external){uint32_t e=target-a->r->definitions;a->r->external[e].referenced++;if(!n->external)a->discovered[e]=1;}
    }
    return COH_OK;
}
static CohStatus slot_visit(void*context,const CohCatalogSlotView*v){
    Audit*a=context;TRY(poll(a));if(v->file->index>=a->r->files||v->slot>=a->files[v->file->index].count)return COH_STATE;
    uint32_t s=a->files[v->file->index].first+v->slot;
    if(!v->allocated)return a->slots[s]?COH_STATE:COH_OK;
    if(a->node>=a->r->definitions||!v->definition)return COH_STATE;
    const CohSgDefinition*d=v->definition;Node*n=&a->nodes[a->node];
    if(a->phase==1){
        if(d->child_count>a->r->children-a->edge)return COH_STATE;
        *n=(Node){0,0,v->file->index,v->slot,d->in_use,a->edge,d->child_count};a->slots[s]=a->node+1;
        if(d->in_use){TRY(name_offset(v,&n->name));if(strcmp(node_name(a,a->node),d->name))return COH_STATE;TRY(add_name(a,a->node));}
        if(a->graph)a->graph->details[a->node]=(Detail){(uint32_t)v->wire_offset,(uint32_t)v->wire_bytes,(uint32_t)v->wire_bits,v->aligned,!!d->geometry[0],0};
    }else{if(n->file!=v->file->index||n->slot!=v->slot||n->active!=d->in_use||n->first!=a->edge||n->count!=d->child_count)return COH_STATE;TRY(fill_edges(a,n,d));}
    a->edge+=d->child_count;a->node++;return COH_OK;
}
static CohStatus external_decode(Audit*a,uint32_t i,CohSgDefinition*d,size_t*owned){
    External*e=&a->external[i];CohRepReader r;
    TRY(coh_rep_reader_bounded(&r,(CohBytes){a->snapshot.data+e->wire,e->bytes},e->bits,1,COH_REP_BOUNDED_MESSAGE_MAX));
    size_t available=a->available;if(available>COH_SG_MEMORY_MAX)available=COH_SG_MEMORY_MAX;
    TRY(coh_scenegraph_definition_read(d,&r,0,available,owned));
    if(r.cursor!=e->bits||d->id!=e->id||d->in_use!=1||strcmp(d->name,(const char*)a->snapshot.data+e->name)||!!d->geometry[0]!=e->model){coh_scenegraph_definition_dispose(d);return COH_INVALID;}
    if(*owned>a->r->peak_record_bytes)a->r->peak_record_bytes=*owned;
    if(a->base+*owned>a->r->aggregate_peak_bytes)a->r->aggregate_peak_bytes=a->base+*owned;
    return COH_OK;
}
static uint32_t adler_string(uint32_t value,const char*s){uint32_t lo=value&65535u,hi=value>>16;for(;*s;s++){lo=(lo+(unsigned char)*s)%65521u;hi=(hi+lo)%65521u;}return hi<<16|lo;}
static uint32_t reverse32(uint32_t n){return n<<24|(n&0xff00u)<<8|(n&0xff0000u)>>8|n>>24;}
static CohStatus visit(Audit*a,uint32_t n,uint32_t depth){
    TRY(poll(a));if(n>=a->nodes_count)return COH_STATE;if(depth>COH_SG_DEPTH_MAX)return COH_LIMIT;
    if(depth>a->r->maximum_depth)a->r->maximum_depth=depth;
    if(a->colors[n]==1)return COH_INVALID;
    if(a->colors[n]==2){if(depth+a->heights[n]>COH_SG_DEPTH_MAX)return COH_LIMIT;if(depth+a->heights[n]>a->r->maximum_depth)a->r->maximum_depth=depth+a->heights[n];return COH_OK;}
    a->colors[n]=1;Node*d=&a->nodes[n];if(!d->active)return COH_UNSUPPORTED;
    if(d->external){a->r->reachable_external++;a->r->external[n-a->r->definitions].reachable=1;}else a->r->reachable_definitions++;
    a->r->reachable_edges+=d->count;
    for(uint32_t i=0;i<d->count;i++){uint32_t child=a->edges[d->first+i];TRY(visit(a,child,depth+1));if(a->heights[child]+1>a->heights[n])a->heights[n]=(uint16_t)(a->heights[child]+1);}
    a->colors[n]=2;return COH_OK;
}
static CohStatus roots_scan(Audit*a,int resolve){
    size_t at=HEADER_BYTES;uint32_t active=0,crc=1;CohBytes in=a->snapshot;
    for(uint32_t i=0;i<a->r->root_slots;i++){
        const uint8_t*p;TRY(poll(a));TRY(span(in,&at,ROOT_BYTES,&p));
        uint32_t present=u32(p+4),kind=u32(p+8),file=u32(p+12),slot=u32(p+16),n=u32(p+20),bits=u32(p+24),bytes=u32(p+28),name;
        if(u32(p)!=i||present>1)return COH_INVALID;
        if(!present){if(kind||file!=NO_INDEX||slot!=NO_INDEX||n||bits||bytes)return COH_INVALID;if(resolve&&a->graph)a->graph->roots[i]=(CohRuntimeGraphRoot){0,NO_INDEX,{{0}}};continue;}
        active++;if(kind!=1&&kind!=2)return COH_UNSUPPORTED;TRY(string(in,&at,n,&name,0));
        const uint8_t*raw,*wire;TRY(span(in,&at,48,&raw));TRY(span(in,&at,bytes,&wire));TRY(matrix_pair(raw,(CohBytes){wire,bytes},bits));
        if(resolve){
            uint32_t node;TRY(lookup(a,(const char*)in.data+name,&node));Node*d=&a->nodes[node];
            if(!d->active)return COH_UNSUPPORTED;
            if(strcmp(node_name(a,node),(const char*)in.data+name))return COH_STATE;
            if(kind==1){if(d->external||file>=a->r->files||slot>=a->files[file].count||a->slots[a->files[file].first+slot]!=node+1)return COH_STATE;}
            else{if(file!=NO_INDEX||slot>=a->r->external_count||node!=a->r->definitions+slot)return COH_STATE;a->r->external[slot].referenced++;a->discovered[slot]=1;}
            crc=adler_string(crc,node_name(a,node));if(d->count)crc=adler_string(crc,node_name(a,a->edges[d->first]));
            TRY(visit(a,node,0));a->r->root_matrices_verified++;
            if(a->graph){CohRuntimeGraphRoot*out=&a->graph->roots[i];out->active=1;out->node=node;
                for(unsigned col=0;col<4;col++)for(unsigned row=0;row<3;row++){uint32_t value=u32(raw+(col*3+row)*4);memcpy(&out->matrix[col][row],&value,4);}}
        }
    }
    if(active!=a->r->active_roots)return COH_STATE;
    if(resolve&&reverse32(crc)!=a->r->source_refs_crc)return COH_STATE;
    a->root_end=(uint32_t)at;return COH_OK;
}
static CohStatus run_audit(Audit*a,const CohRuntimeSnapshotBudget*budget){
    CohCatalogReport scan;TRY(coh_scenecatalog_preflight(a->catalog,a->pins->asset_generation,&scan));
    a->r->files=scan.files;a->r->slots=scan.slots;a->r->definitions=scan.definitions;a->r->children=scan.children;
    a->r->source_defs_crc=scan.source_defs_crc;a->r->source_refs_crc=scan.source_refs_crc;
    TRY(envelope(a,&scan));uint32_t extra_edges=0;
    for(uint32_t i=0;i<a->r->external_count;i++){
        CohSgDefinition d={0};size_t owned;TRY(external_decode(a,i,&d,&owned));
        if(d.child_count>COH_SG_CHILDREN_MAX-scan.children-extra_edges){coh_scenegraph_definition_dispose(&d);return COH_LIMIT;}
        extra_edges+=d.child_count;coh_scenegraph_definition_dispose(&d);
    }
    a->nodes_count=scan.definitions+a->r->external_count;a->edges_count=scan.children+extra_edges;
    a->capacity=1;while(a->capacity<a->nodes_count*2u)a->capacity*=2u;
    size_t owned=(size_t)scan.files*sizeof(File)+(size_t)a->nodes_count*sizeof(Node)+((size_t)scan.slots+a->capacity+a->edges_count)*sizeof(uint32_t)+(size_t)a->nodes_count*(sizeof(uint16_t)+sizeof(uint8_t));
    if(a->graph)owned+=(size_t)a->nodes_count*sizeof(Detail)+(size_t)a->edges_count*sizeof(CohSgMatrix)+(size_t)a->r->root_slots*sizeof(CohRuntimeGraphRoot);
    if(owned>COH_SG_MEMORY_MAX||owned>a->available)return COH_LIMIT;
    void*pool=calloc(1,owned?owned:1);if(!pool)return COH_LIMIT;
    a->r->owned_bytes=owned?owned:1;a->base+=a->r->owned_bytes;a->available-=a->r->owned_bytes;
    a->files=pool;a->nodes=(Node*)(a->files+scan.files);a->slots=(uint32_t*)(a->nodes+a->nodes_count);a->names=a->slots+scan.slots;a->edges=a->names+a->capacity;
    uint8_t*tail=(uint8_t*)(a->edges+a->edges_count);
    if(a->graph){CohRuntimeGraph*g=a->graph;g->details=(Detail*)tail;g->matrices=(CohSgMatrix*)(g->details+a->nodes_count);g->roots=(CohRuntimeGraphRoot*)(g->matrices+a->edges_count);tail=(uint8_t*)(g->roots+a->r->root_slots);}
    a->heights=(uint16_t*)tail;a->colors=(uint8_t*)(a->heights+a->nodes_count);
    CohStatus status=COH_OK;
    for(a->phase=1;a->phase<=2;a->phase++){
        a->file=a->slot=a->node=a->edge=0;
        CohCatalogWalkBudget wb={COH_CATALOG_MEMORY_MAX,budget->aggregate_limit,a->base-a->catalog.size-COH_CATALOG_WALK_STACK_RESERVE};
        CohCatalogVisitor visitor={a,file_visit,slot_visit};CohCatalogWalkReport walked;
        status=coh_scenecatalog_walk(a->catalog,a->pins->asset_generation,&wb,&visitor,&walked);if(status!=COH_OK)goto done;
        if(walked.peak_record_owned_bytes>a->r->peak_record_bytes)a->r->peak_record_bytes=walked.peak_record_owned_bytes;
        if(walked.peak_aggregate_bytes>a->r->aggregate_peak_bytes)a->r->aggregate_peak_bytes=walked.peak_aggregate_bytes;
        if(a->file!=scan.files||a->slot!=scan.slots||a->node!=scan.definitions||a->edge!=scan.children){status=COH_STATE;goto done;}
        for(uint32_t i=0;i<a->r->external_count;i++){
            status=poll(a);if(status!=COH_OK)goto done;CohSgDefinition d={0};size_t bytes;
            status=external_decode(a,i,&d,&bytes);if(status!=COH_OK)goto done;
            Node*n=&a->nodes[scan.definitions+i];External*e=&a->external[i];
            if(a->phase==1){
                *n=(Node){e->name,1,NO_INDEX,e->id,1,a->edge,d.child_count};
                if(a->graph)a->graph->details[scan.definitions+i]=(Detail){e->wire,e->bytes,e->bits,1,e->model,!e->model&&!d.child_count};
                status=add_name(a,scan.definitions+i);
                CohRuntimeExternalDiagnostic*out=&a->r->external[i];strcpy(out->name,d.name);if(e->path)strcpy(out->library_path,(const char*)a->snapshot.data+e->path);
                out->original_id=e->id;out->model_present=e->model;out->bounds_lookup_found=e->lookup;
            }else status=fill_edges(a,n,&d);
            a->edge+=d.child_count;coh_scenegraph_definition_dispose(&d);if(status!=COH_OK)goto done;
        }
        if(a->edge!=a->edges_count){status=COH_STATE;goto done;}
    }
    status=roots_scan(a,1);if(status!=COH_OK)goto done;
    /* The original observer discovers futures from ALL regular source records
     * and roots, then their external closure. A disconnected external cycle
     * cannot justify its own inclusion merely by having incoming edges. */
    {uint32_t queue[COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX],count=0;
        for(uint32_t i=0;i<a->r->external_count;i++)if(a->discovered[i])queue[count++]=i;
        for(uint32_t at=0;at<count;at++){Node*n=&a->nodes[scan.definitions+queue[at]];
            for(uint32_t j=0;j<n->count;j++){uint32_t target=a->edges[n->first+j];
                if(target>=scan.definitions&&!a->discovered[target-scan.definitions]){uint32_t e=target-scan.definitions;a->discovered[e]=1;queue[count++]=e;}}}
        if(count!=a->r->external_count){status=COH_STATE;goto done;}}
    for(uint32_t i=0;i<a->r->external_count;i++)if(!a->r->external[i].referenced){status=COH_STATE;goto done;}
    a->r->definitions_crc_verified=a->r->references_crc_verified=a->r->complete_source_name_closure=1;
done:if(status==COH_OK&&a->graph){CohRuntimeGraph*g=a->graph;g->pool=pool;g->files=a->files;g->nodes=a->nodes;g->slots=a->slots;g->names=a->names;g->edges=a->edges;g->colors=a->colors;g->capacity=a->capacity;}else free(pool);return status;
}
CohStatus coh_runtime_snapshot_audit(CohBytes catalog,CohBytes snapshot,const CohRuntimeSnapshotPins*pins,
    const CohRuntimeSnapshotBudget*budget,const CohCancel*cancel,CohRuntimeSnapshotReport*out){
    if(!pins||!budget||!out||!pins->digest||!catalog.data||!snapshot.data||!pins->asset_generation||!nonzero(pins->catalog_sha256)||!nonzero(pins->snapshot_sha256)||!nonzero(pins->source_sha256)||!nonzero(pins->run_sha256))return COH_INVALID;
    if(catalog.size>COH_CATALOG_INPUT_MAX||snapshot.size>COH_RUNTIME_SNAPSHOT_INPUT_MAX||!budget->aggregate_limit||budget->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_LIMIT;
    size_t available=budget->aggregate_limit,charges[]={budget->retained_bytes,catalog.size,snapshot.size,sizeof(*out),COH_RUNTIME_SNAPSHOT_STACK_RESERVE,COH_CATALOG_WALK_STACK_RESERVE};
    for(unsigned i=0;i<sizeof(charges)/sizeof(*charges);i++){if(charges[i]>available)return COH_LIMIT;available-=charges[i];}
    uint8_t digest[32];TRY(pins->digest(pins->context,catalog,digest));if(memcmp(digest,pins->catalog_sha256,32))return COH_STATE;
    TRY(pins->digest(pins->context,snapshot,digest));if(memcmp(digest,pins->snapshot_sha256,32))return COH_STATE;
    CohRuntimeSnapshotReport candidate;memset(&candidate,0,sizeof(candidate));
    candidate.catalog_bytes=catalog.size;candidate.snapshot_bytes=snapshot.size;candidate.retained_bytes=budget->retained_bytes;candidate.stack_reserve=COH_RUNTIME_SNAPSHOT_STACK_RESERVE+COH_CATALOG_WALK_STACK_RESERVE;
    candidate.aggregate_peak_bytes=budget->aggregate_limit-available;
    Audit a;memset(&a,0,sizeof(a));a.catalog=catalog;a.snapshot=snapshot;a.pins=pins;a.cancel=cancel;a.r=&candidate;a.available=available;a.base=candidate.aggregate_peak_bytes;
    CohStatus status=run_audit(&a,budget);if(status!=COH_OK)return status;
    *out=candidate;return COH_OK;
}

static int same_identity(const CohRuntimeGraphBinding*a,const CohRuntimeGraphBinding*b){
    return a->pins.asset_generation==b->pins.asset_generation &&
        !memcmp(a->pins.catalog_sha256,b->pins.catalog_sha256,32) &&
        !memcmp(a->pins.snapshot_sha256,b->pins.snapshot_sha256,32) &&
        !memcmp(a->pins.source_sha256,b->pins.source_sha256,32) &&
        !memcmp(a->pins.run_sha256,b->pins.run_sha256,32);
}
void coh_runtime_graph_free(CohRuntimeGraph*g){if(g){free(g->pool);free(g);}}
CohStatus coh_runtime_graph_build(const CohRuntimeGraph*prior,CohBytes catalog,CohBytes snapshot,
    const CohRuntimeGraphBinding*binding,const CohRuntimeSnapshotBudget*budget,const CohCancel*cancel,
    CohRuntimeGraph**candidate,CohRuntimeGraphReport*out){
    if(!binding||!budget||!candidate||*candidate||!out||!binding->generation||!binding->catalog_generation)return COH_INVALID;
    const CohRuntimeSnapshotPins*p=&binding->pins;
    if(!p->digest||!catalog.data||!snapshot.data||!p->asset_generation||!nonzero(p->catalog_sha256)||!nonzero(p->snapshot_sha256)||!nonzero(p->source_sha256)||!nonzero(p->run_sha256))return COH_INVALID;
    if(prior){
        if(prior->binding.generation==UINT32_MAX||binding->generation!=prior->binding.generation+1||binding->catalog_generation<prior->binding.catalog_generation||p->asset_generation<prior->binding.pins.asset_generation)return COH_STATE;
        if(binding->catalog_generation==prior->binding.catalog_generation&&!same_identity(binding,&prior->binding))return COH_STATE;
    }else if(binding->generation!=1)return COH_STATE;
    if(catalog.size>COH_CATALOG_INPUT_MAX||snapshot.size>COH_RUNTIME_SNAPSHOT_INPUT_MAX||!budget->aggregate_limit||budget->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_LIMIT;
    size_t old_owned=prior?prior->report.owned_bytes:0,old_inputs=prior?prior->catalog.size+prior->snapshot.size:0;
    size_t available=budget->aggregate_limit;
    size_t charges[]={budget->retained_bytes,old_owned,old_inputs,catalog.size,snapshot.size,sizeof(CohRuntimeGraph),sizeof(*out),COH_RUNTIME_SNAPSHOT_STACK_RESERVE,COH_CATALOG_WALK_STACK_RESERVE};
    for(unsigned i=0;i<sizeof(charges)/sizeof(*charges);i++){if(charges[i]>available)return COH_LIMIT;available-=charges[i];}
    uint8_t digest[32];TRY(p->digest(p->context,catalog,digest));if(memcmp(digest,p->catalog_sha256,32))return COH_STATE;
    TRY(p->digest(p->context,snapshot,digest));if(memcmp(digest,p->snapshot_sha256,32))return COH_STATE;
    CohRuntimeGraph*g=calloc(1,sizeof(*g));if(!g)return COH_LIMIT;
    g->catalog=catalog;g->snapshot=snapshot;g->binding=*binding;g->prior=prior;
    CohRuntimeSnapshotReport*r=&g->report.source;r->catalog_bytes=catalog.size;r->snapshot_bytes=snapshot.size;
    r->retained_bytes=budget->retained_bytes+old_owned+old_inputs+sizeof(*g)+sizeof(*out);
    r->stack_reserve=COH_RUNTIME_SNAPSHOT_STACK_RESERVE+COH_CATALOG_WALK_STACK_RESERVE;r->aggregate_peak_bytes=budget->aggregate_limit-available;
    Audit a;memset(&a,0,sizeof(a));a.catalog=catalog;a.snapshot=snapshot;a.pins=p;a.cancel=cancel;a.r=r;a.available=available;a.base=r->aggregate_peak_bytes;a.graph=g;
    CohStatus status=run_audit(&a,budget);if(status!=COH_OK){coh_runtime_graph_free(g);return status;}
    if(r->owned_bytes>COH_SG_MEMORY_MAX-sizeof(*g)){coh_runtime_graph_free(g);return COH_LIMIT;}
    g->report.generation=binding->generation;g->report.catalog_generation=binding->catalog_generation;g->report.asset_generation=p->asset_generation;
    g->report.nodes=a.nodes_count;g->report.edges=a.edges_count;g->report.owned_bytes=sizeof(*g)+r->owned_bytes;
    g->report.prior_owned_bytes=old_owned;g->report.prior_input_bytes=old_inputs;g->report.aggregate_peak_bytes=r->aggregate_peak_bytes;
    *out=g->report;*candidate=g;return COH_OK;
}
CohStatus coh_runtime_graph_publish(CohRuntimeGraph**current,CohRuntimeGraph**candidate,CohRuntimeGraph**retired){
    if(!current||!candidate||!retired||current==candidate||current==retired||candidate==retired||!*candidate||*retired||*current==*candidate)return COH_INVALID;
    CohRuntimeGraph*old=*current,*next=*candidate;
    if(next->prior!=old)return COH_STATE;
    if(old){if(old->binding.generation==UINT32_MAX||next->binding.generation!=old->binding.generation+1||next->report.prior_owned_bytes!=old->report.owned_bytes)return COH_STATE;
        if(next->binding.catalog_generation<old->binding.catalog_generation||next->binding.pins.asset_generation<old->binding.pins.asset_generation||(next->binding.catalog_generation==old->binding.catalog_generation&&!same_identity(&next->binding,&old->binding)))return COH_STATE;
    }else if(next->binding.generation!=1||next->report.prior_owned_bytes)return COH_STATE;
    *retired=old;*current=next;*candidate=NULL;return COH_OK;
}
CohStatus coh_runtime_graph_report(const CohRuntimeGraph*g,CohRuntimeGraphReport*out){if(!g||!out)return COH_INVALID;*out=g->report;return COH_OK;}
CohStatus coh_runtime_graph_node(const CohRuntimeGraph*g,uint32_t i,CohRuntimeGraphNode*out){
    if(!g||!out)return COH_INVALID;
    if(i>=g->report.nodes)return COH_NOT_FOUND;
    const Node*n=&g->nodes[i];const Detail*d=&g->details[i];const uint8_t*base=n->external?g->snapshot.data:g->catalog.data;
    CohRuntimeGraphNode v={n->file,n->slot,n->external,n->active,g->colors[i]==2,n->first,n->count,d->model,d->empty_future,n->active?(const char*)base+n->name:NULL,{base+d->wire,d->bytes},d->bits,d->aligned};*out=v;return COH_OK;
}
CohStatus coh_runtime_graph_child(const CohRuntimeGraph*g,uint32_t i,CohRuntimeGraphChild*out){if(!g||!out)return COH_INVALID;if(i>=g->report.edges)return COH_NOT_FOUND;out->target=g->edges[i];memcpy(out->matrix,g->matrices[i],sizeof(out->matrix));return COH_OK;}
CohStatus coh_runtime_graph_root(const CohRuntimeGraph*g,uint32_t i,CohRuntimeGraphRoot*out){if(!g||!out)return COH_INVALID;if(i>=g->report.source.root_slots)return COH_NOT_FOUND;*out=g->roots[i];return COH_OK;}
CohStatus coh_runtime_graph_slot(const CohRuntimeGraph*g,uint32_t file,uint32_t slot,uint32_t*out){if(!g||!out)return COH_INVALID;if(file>=g->report.source.files||slot>=g->files[file].count)return COH_NOT_FOUND;uint32_t n=g->slots[g->files[file].first+slot];if(!n)return COH_NOT_FOUND;*out=n-1;return COH_OK;}
CohStatus coh_runtime_graph_name(const CohRuntimeGraph*g,const char*name,uint32_t*out){
    if(!g||!name||!out)return COH_INVALID;
    size_t len=0;while(len<COH_REP_NAME_MAX&&name[len]){if((unsigned char)name[len]<32||(unsigned char)name[len]>126||name[len]=='/'||name[len]=='\\')return COH_INVALID;len++;}if(!len||len==COH_REP_NAME_MAX)return COH_INVALID;
    Audit a;memset(&a,0,sizeof(a));a.catalog=g->catalog;a.snapshot=g->snapshot;a.nodes=g->nodes;a.names=g->names;a.capacity=g->capacity;
    uint32_t n;TRY(lookup(&a,name,&n));if(strcmp(node_name(&a,n),name))return COH_NOT_FOUND;*out=n;return COH_OK;
}
CohStatus coh_runtime_graph_witness(const CohRuntimeGraph*g,uint32_t target,
    CohRuntimeGraphWitnessWork*work,size_t rows,const CohCancel*cancel,CohRuntimeGraphWitness*out){
    if(!g||!out)return COH_INVALID;
    if(target>=g->report.nodes||g->colors[target]!=2)return COH_NOT_FOUND;
    if(!work||rows<g->report.nodes)return COH_LIMIT;
    uint32_t count=0;
    for(uint32_t i=0;i<g->report.nodes;i++){
        if(cancel&&cancel->poll&&cancel->poll(cancel->context))return COH_CANCELLED;
        work[i].parent=NO_INDEX;work[i].edge=NO_INDEX;
    }
    for(uint32_t i=0;i<g->report.source.root_slots;i++){
        const CohRuntimeGraphRoot*r=&g->roots[i];
        if(r->active&&work[r->node].parent==NO_INDEX){
            work[r->node].parent=r->node;work[r->node].edge=i;work[count++].queue=r->node;
        }
    }
    for(uint32_t at=0;at<count;at++){
        if(cancel&&cancel->poll&&cancel->poll(cancel->context))return COH_CANCELLED;
        uint32_t n=work[at].queue;
        if(n==target)break;
        const Node*node=&g->nodes[n];
        for(uint32_t i=0;i<node->count;i++){
            if(cancel&&cancel->poll&&cancel->poll(cancel->context))return COH_CANCELLED;
            uint32_t edge=node->first+i,child=g->edges[edge];
            if(work[child].parent==NO_INDEX){work[child].parent=n;work[child].edge=edge;work[count++].queue=child;}
        }
    }
    if(work[target].parent==NO_INDEX)return COH_STATE;
    CohRuntimeGraphWitness result;memset(&result,0,sizeof(result));
    uint32_t n=target;
    for(;;){
        if(result.length>COH_SG_DEPTH_MAX)return COH_STATE;
        result.nodes[result.length++]=n;
        if(work[n].parent==n){result.root_slot=work[n].edge;break;}
        if(result.length>COH_SG_DEPTH_MAX)return COH_STATE;
        result.edges[result.length-1]=work[n].edge;n=work[n].parent;
    }
    for(uint32_t i=0;i<result.length/2;i++){uint32_t v=result.nodes[i];result.nodes[i]=result.nodes[result.length-1-i];result.nodes[result.length-1-i]=v;}
    for(uint32_t i=0;i<(result.length-1)/2;i++){uint32_t v=result.edges[i];result.edges[i]=result.edges[result.length-2-i];result.edges[result.length-2-i]=v;}
    *out=result;return COH_OK;
}
