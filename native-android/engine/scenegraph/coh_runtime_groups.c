#include "coh_runtime_groups.h"
#include <string.h>
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
typedef struct {const CohRuntimeGraph *graph;const CohCatalogOwner *owner;CohBytes snapshot;size_t root_offset;uint32_t root_slot,file0_emitted;CohRuntimeGroupsReport report;} Match;
static uint32_t u32(const uint8_t *p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int span(size_t n,size_t at,size_t bytes){return at<=n&&bytes<=n-at;}
static int disjoint(const void *a,size_t an,const void *b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static CohStatus observe(void *context,const CohGroupsEvent *event){
    Match *m=context;CohRepReader r=event->span;uint32_t n;char name[COH_REP_NAME_MAX];
    if(event->kind==COH_GROUPS_FILE_HEADER){
        CohCatalogFileView file;TRY(coh_catalog_owner_file(m->owner,event->file,&file));
        TRY(coh_rep_read(&r,1,&n));if(n!=1)return COH_UNSUPPORTED;
        TRY(coh_rep_string(&r,name,sizeof(name)));if(strcmp(name,file.name))return COH_STATE;
        TRY(coh_rep_read(&r,32,&n));if(n!=file.bounds_checksum)return COH_STATE;
        TRY(coh_rep_read(&r,1,&n));if(n||r.cursor!=r.bits)return COH_STATE;
        m->report.files_equal++;return COH_OK;
    }
    if(event->kind==COH_GROUPS_DEFINITION){
        uint32_t index;CohRuntimeGraphNode node;TRY(coh_runtime_graph_slot(m->graph,event->file,event->slot,&index));TRY(coh_runtime_graph_node(m->graph,index,&node));
        size_t bits=r.bits-r.cursor;if(!node.aligned||(r.cursor&7)||bits!=node.wire_bits||bits%8||bits/8!=node.wire.size)return COH_STATE;
        if(memcmp(r.bytes.data+r.cursor/8,node.wire.data,node.wire.size))return COH_STATE;
        if(!event->file)m->file0_emitted++;
        m->report.emitted_definitions_equal++;return COH_OK;
    }
    if(event->kind!=COH_GROUPS_ROOT||event->slot!=m->root_slot)return COH_STATE;
    const uint8_t *p;size_t at=m->root_offset;if(!span(m->snapshot.size,at,32))return COH_STATE;p=m->snapshot.data+at;at+=32;
    uint32_t active=u32(p+4),names=u32(p+20),bits=u32(p+24),bytes=u32(p+28);
    if(u32(p)!=m->root_slot||active>1)return COH_STATE;
    TRY(coh_rep_pack(&r,1,&n));if(n!=m->root_slot)return COH_STATE;
    TRY(coh_rep_string(&r,name,sizeof(name)));
    if(!active){if(name[0]||r.cursor!=r.bits)return COH_STATE;}
    else {
        if(!names||!span(m->snapshot.size,at,names)||m->snapshot.data[at+names-1])return COH_STATE;
        if(strlen(name)+1!=names||memcmp(name,m->snapshot.data+at,names))return COH_STATE;
        at+=names;
        if(!span(m->snapshot.size,at,48))return COH_STATE;
        at+=48;
        if(!span(m->snapshot.size,at,bytes)||bits!=(size_t)bytes*8||(r.cursor&7)||r.bits-r.cursor!=bits)return COH_STATE;
        if(memcmp(r.bytes.data+r.cursor/8,m->snapshot.data+at,bytes))return COH_STATE;
        at+=bytes;
        m->report.root_wires_equal++;
    }
    m->root_offset=at;m->root_slot++;return COH_OK;
}
CohStatus coh_runtime_graph_compare_groups(const CohRuntimeGraph *graph,const CohCatalogOwner *owner,
    const CohRepReader *reader,const CohRuntimeGroupsBudget *budget,CohRuntimeGroupsReport *out){
    if(!graph||!owner||!reader||!budget||!out)return COH_INVALID;
    CohBytes catalog,snapshot,owned;CohRuntimeGraphBinding binding;CohCatalogBinding cb;CohRuntimeGraphReport gr;
    TRY(coh_runtime_graph_sources(graph,&catalog,&snapshot));TRY(coh_catalog_owner_bytes(owner,&owned));
    const void *p[]={reader,budget,out,reader->bytes.data,catalog.data,snapshot.data};
    size_t n[]={sizeof(*reader),sizeof(*budget),sizeof(*out),reader->bytes.size,catalog.size,snapshot.size};
    for(unsigned i=0;i<6;i++)for(unsigned j=i+1;j<6;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;
    if(owned.data!=catalog.data||owned.size!=catalog.size)return COH_STATE;
    TRY(coh_runtime_graph_binding(graph,&binding));TRY(coh_catalog_owner_binding(owner,&cb));TRY(coh_runtime_graph_report(graph,&gr));
    if(binding.catalog_generation!=cb.catalog_generation||binding.pins.asset_generation!=cb.asset_generation||memcmp(binding.pins.catalog_sha256,cb.catalog_sha256,32)||memcmp(binding.pins.source_sha256,cb.source_sha256,32))return COH_STATE;
    if(!reader->compressed)return COH_UNSUPPORTED;
    size_t total=budget->retained_bytes,limit=budget->aggregate_limit;
    if(!limit||limit>COH_SG_TRANSACTION_MAX||total>limit)return COH_LIMIT;
    size_t add[]={gr.owned_bytes,coh_catalog_owner_owned_bytes(owner),snapshot.size,reader->bytes.size,COH_SG_FIXED_SCRATCH_BYTES,sizeof(CohRuntimeGroupsReport)};
    for(unsigned i=0;i<sizeof(add)/sizeof(add[0]);i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];}
    CohRepReader copy=*reader;CohGroupsInspection inspection;TRY(coh_rep_groups(&copy,&inspection,NULL));
    if(!inspection.new_world||inspection.files!=gr.source.files||inspection.present_files!=inspection.files||inspection.roots!=gr.source.root_slots||inspection.footer_active_roots!=gr.source.active_roots||inspection.footer_defs_crc!=gr.source.source_defs_crc||inspection.footer_refs_crc!=gr.source.source_refs_crc)return COH_STATE;
    CohRepReader prefix_reader=*reader;CohRepScenePrefix prefix;TRY(coh_rep_scene_prefix(&prefix_reader,&prefix));
    CohCatalogFileView mapfile={0};if(gr.source.files){TRY(coh_catalog_owner_file(owner,0,&mapfile));if(strcmp(mapfile.name,prefix.map_path))return COH_STATE;}else if(prefix.map_path[0])return COH_STATE;
    Match m;memset(&m,0,sizeof(m));m.report.prefix=prefix;m.graph=graph;m.owner=owner;m.snapshot=snapshot;m.root_offset=80;
    m.report.graph_generation=binding.generation;m.report.catalog_generation=binding.catalog_generation;m.report.aggregate_reserved_bytes=total;
    CohGroupsVisitor visitor={&m,observe};copy=*reader;TRY(coh_rep_groups_visit(&copy,&visitor,&m.report.groups,NULL));
    if(m.file0_emitted!=mapfile.records||m.report.files_equal!=gr.source.files||m.root_slot!=gr.source.root_slots||m.report.root_wires_equal!=gr.source.active_roots||m.report.emitted_definitions_equal!=inspection.defs)return COH_STATE;
    *out=m.report;return COH_OK;
}
