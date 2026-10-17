#include "coh_runtime_groups_witness.h"
#include <stdlib.h>
#include <string.h>
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
typedef struct {uint32_t record,first,slots,eligible;} WFile;
struct CohRuntimeGroupsWitness {
 const CohRuntimeGraph *graph;CohCatalogOwner *owner;CohBytes catalog,snapshot;
 CohRuntimeGroupsWitnessBinding binding;CohRuntimeGroupsWitnessReport report;
 CohRepReader packet;uint8_t *records,*bytes;WFile *files;uint32_t refs;
};
static uint32_t u32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t w(const uint8_t*p,unsigned i){return u32(p+i*4);}
static int nonzero(const uint8_t*p){unsigned x=0;for(unsigned i=0;i<32;i++)x|=p[i];return x!=0;}
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static int equal(const CohRuntimeGroupsWitnessBinding*a,const CohRuntimeGroupsWitnessBinding*b){
 return a->graph_generation==b->graph_generation&&a->catalog_generation==b->catalog_generation&&a->observation_id==b->observation_id&&a->map_generation==b->map_generation&&a->selection_generation==b->selection_generation&&a->selected_dbid==b->selected_dbid&&!memcmp(a->witness_sha256,b->witness_sha256,32)&&!memcmp(a->packet_sha256,b->packet_sha256,32)&&!memcmp(a->session_sha256,b->session_sha256,32)&&!memcmp(a->catalog_sha256,b->catalog_sha256,32)&&!memcmp(a->snapshot_sha256,b->snapshot_sha256,32)&&!memcmp(a->source_sha256,b->source_sha256,32)&&!memcmp(a->run_sha256,b->run_sha256,32);
}
static CohStatus owners(const CohRuntimeGraph*g,const CohCatalogOwner*o,const CohRuntimeGroupsWitnessBinding*b,CohBytes*cat,CohBytes*snap,CohRuntimeGraphReport*gr){
 CohRuntimeGraphBinding gb;CohCatalogBinding cb;CohBytes bytes;TRY(coh_runtime_graph_sources(g,cat,snap));TRY(coh_catalog_owner_bytes(o,&bytes));if(bytes.data!=cat->data||bytes.size!=cat->size)return COH_STATE;
 TRY(coh_runtime_graph_binding(g,&gb));TRY(coh_catalog_owner_binding(o,&cb));TRY(coh_runtime_graph_report(g,gr));
 if(b->graph_generation!=gb.generation||b->catalog_generation!=gb.catalog_generation||cb.catalog_generation!=gb.catalog_generation||cb.asset_generation!=gb.pins.asset_generation||memcmp(cb.catalog_sha256,gb.pins.catalog_sha256,32)||memcmp(cb.source_sha256,gb.pins.source_sha256,32)||memcmp(b->catalog_sha256,gb.pins.catalog_sha256,32)||memcmp(b->snapshot_sha256,gb.pins.snapshot_sha256,32)||memcmp(b->source_sha256,gb.pins.source_sha256,32)||memcmp(b->run_sha256,gb.pins.run_sha256,32))return COH_STATE;
 return COH_OK;
}
static CohStatus decode(CohRuntimeGroupsWitness*t,size_t size){
 const uint8_t*p=t->records,*h=p;CohRuntimeGraphReport gr;TRY(coh_runtime_graph_report(t->graph,&gr));
 if(size<128||size%64||size>COH_GROUPS_WITNESS_INPUT_MAX||w(h,0)!=1||w(h,1)!=1||w(h,2)!=t->binding.observation_id||w(h,3)!=1||w(h,5)==w(h,6)||w(h,7)!=gr.source.files||w(h,8)!=gr.source.slots||w(h,9)!=gr.source.root_slots||w(h,10)!=gr.source.active_roots||w(h,11)||w(h,12)||w(h,13)!=1||w(h,14)||w(h,15))return COH_STATE;
 uint32_t files=w(h,7),slots=w(h,8),roots=w(h,9);size_t expected=2u+(size_t)files+slots+roots;if(files>4096||slots>65536||roots>65536||expected!=size/64)return COH_LIMIT;
 uint32_t at=1,defs=0,saved=0,time=0; /* narrow full-update initial scope */
 for(uint32_t order=0;order<files;order++){
  uint32_t f=(order+1)%files;CohCatalogFileView fv;TRY(coh_catalog_owner_file(t->owner,f,&fv));p=t->records+(size_t)at*64;
  if(w(p,0)!=2||w(p,1)!=f||w(p,5)!=fv.slots||w(p,6)!=fv.bounds_checksum||w(p,7)!=1||w(p,3)>1||w(p,4)>1)return COH_STATE;
  for(unsigned j=8;j<16;j++)if(w(p,j))return COH_STATE;
  WFile*wf=&t->files[f];*wf=(WFile){at,at+1,fv.slots,0};at++;
  for(uint32_t slot=0;slot<fv.slots;slot++,at++){
   const uint8_t*d=t->records+(size_t)at*64;CohCatalogRecordIdentity ci;TRY(coh_catalog_owner_record(t->owner,f,slot,&ci));
   if(!ci.allocated||w(d,0)!=3||w(d,1)!=f||w(d,2)!=slot||w(d,3)!=slot||w(d,7)!=ci.in_use||w(d,5)>65535||w(d,6)>1)return COH_STATE;
   for(unsigned j=9;j<16;j++)if(w(d,j))return COH_STATE;
   uint32_t node,id,live,mod;CohRuntimeGraphNode n;TRY(coh_runtime_graph_slot(t->graph,f,slot,&node));TRY(coh_runtime_graph_node(t->graph,node,&n));CohRepReader r;TRY(coh_rep_reader_bounded(&r,n.wire,n.wire_bits,n.aligned,COH_REP_BOUNDED_MESSAGE_MAX));TRY(coh_rep_pack(&r,1,&id));TRY(coh_rep_read(&r,1,&live));
   if(id!=slot+1||live!=w(d,7))return COH_STATE;
   if(live){char name[COH_REP_NAME_MAX];TRY(coh_rep_string(&r,name,sizeof(name)));TRY(coh_rep_read(&r,32,&mod));if(mod!=w(d,4))return COH_STATE;}
   int eligible=1;
   /* Full update bypasses source time filters, but not saved omission. */
   if(!w(p,3)&&!w(p,4)&&w(d,5)&&w(d,6)){eligible=0;saved++;}
   if(w(d,8)!=(uint32_t)eligible)return COH_STATE;
   wf->eligible+=(uint32_t)eligible;defs+=(uint32_t)eligible;
  }
 }
 for(uint32_t i=0;i<roots;i++,at++){
  p=t->records+(size_t)at*64;CohRuntimeGraphRoot r;TRY(coh_runtime_graph_root(t->graph,i,&r));
  if(w(p,0)!=4||w(p,1)!=i||w(p,3)!=r.active||w(p,4)!=1)return COH_STATE;
  for(unsigned j=5;j<16;j++)if(w(p,j))return COH_STATE;
 }
 p=t->records+(size_t)at*64;
 if(w(p,0)!=5||w(p,1)!=expected||w(p,2)!=files||w(p,3)!=slots||w(p,4)!=roots||w(p,5)!=files||w(p,6)!=defs||w(p,7)!=roots)return COH_STATE;
 for(unsigned j=8;j<16;j++)if(w(p,j))return COH_STATE;
 t->report.records=(uint32_t)expected;t->report.files=files;t->report.slots=slots;t->report.roots=roots;t->report.eligible_definitions=defs;t->report.saved_omissions=saved;t->report.time_omissions=time;return COH_OK;
}
void coh_runtime_groups_witness_release(CohRuntimeGroupsWitness*t){if(!t)return;if(--t->refs)return;coh_catalog_owner_release(t->owner);free(t->files);free(t->records);free(t->bytes);free(t);}
CohStatus coh_runtime_groups_witness_retain(CohRuntimeGroupsWitness*t){if(!t)return COH_INVALID;if(t->refs==UINT32_MAX)return COH_LIMIT;t->refs++;return COH_OK;}
CohStatus coh_runtime_groups_witness_create(const CohRuntimeGraph*g,CohCatalogOwner*o,CohBytes input,const CohRepReader*packet,const CohRuntimeGroupsWitnessBinding*b,const CohRuntimeGroupsWitnessBudget*budget,const CohCatalogDigest*d,CohRuntimeGroupsWitness**out,CohRuntimeGroupsWitnessReport*report){
 if(!g||!o||!input.data||!packet||!b||!budget||!d||!d->sha256||!out||!report)return COH_INVALID;
 const void*p[]={input.data,packet,packet->bytes.data,b,budget,d,out,report};size_t z[]={input.size,sizeof(*packet),packet->bytes.size,sizeof(*b),sizeof(*budget),sizeof(*d),sizeof(*out),sizeof(*report)};
 for(unsigned i=0;i<8;i++)for(unsigned j=i+1;j<8;j++)if(!disjoint(p[i],z[i],p[j],z[j]))return COH_INVALID;
 if(*out)return COH_STATE;
 if(!b->observation_id||!b->map_generation||!b->selection_generation||(!b->selected_dbid||b->selected_dbid>INT32_MAX)||!nonzero(b->session_sha256)||!nonzero(b->witness_sha256)||!nonzero(b->packet_sha256))return COH_STATE;
 CohBytes cat,snap;CohRuntimeGraphReport gr;TRY(owners(g,o,b,&cat,&snap,&gr));if(gr.source.files>4096||gr.source.slots>65536||gr.source.root_slots>65536)return COH_LIMIT;
 for(unsigned i=0;i<8;i++)if(!disjoint(p[i],z[i],cat.data,cat.size)||!disjoint(p[i],z[i],snap.data,snap.size))return COH_INVALID;
 if(!packet->bytes.data||!packet->bytes.size||input.size<128||input.size%64||input.size>COH_GROUPS_WITNESS_INPUT_MAX||packet->bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||packet->bits!=packet->bytes.size*8||packet->cursor>packet->bits||packet->compressed!=1||(packet->bits&7u)||(packet->cursor&7u))return COH_LIMIT;
 size_t owned=sizeof(CohRuntimeGroupsWitness)+input.size+packet->bytes.size+(size_t)gr.source.files*sizeof(WFile),total=budget->retained_bytes,limit=budget->aggregate_limit;
 if(!limit||limit>COH_SG_TRANSACTION_MAX||owned>budget->owned_limit||budget->owned_limit>COH_SG_MEMORY_MAX||total>limit)return COH_LIMIT;
 size_t add[]={owned,input.size,packet->bytes.size,gr.owned_bytes,coh_catalog_owner_owned_bytes(o),snap.size,COH_GROUPS_WITNESS_FIXED_SCRATCH_BYTES,sizeof(CohRuntimeGroupsReport)};for(unsigned i=0;i<sizeof(add)/sizeof(add[0]);i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];}
 CohRuntimeGroupsWitness*t=calloc(1,sizeof(*t));if(!t)return COH_LIMIT;t->refs=1;t->graph=g;t->catalog=cat;t->snapshot=snap;t->binding=*b;t->packet=*packet;t->report.owned_bytes=owned;t->report.aggregate_reserved_bytes=total;
 t->records=malloc(input.size);t->bytes=malloc(packet->bytes.size?packet->bytes.size:1);t->files=gr.source.files?calloc(gr.source.files,sizeof(WFile)):NULL;if(!t->records||!t->bytes||(gr.source.files&&!t->files)){coh_runtime_groups_witness_release(t);return COH_LIMIT;}
 memcpy(t->records,input.data,input.size);memcpy(t->bytes,packet->bytes.data,packet->bytes.size);t->packet.bytes.data=t->bytes;
 CohStatus status;uint8_t hash[32];status=d->sha256(d->context,(CohBytes){t->records,input.size},hash);if(status==COH_OK&&memcmp(hash,b->witness_sha256,32))status=COH_STATE;
 if(status==COH_OK){status=d->sha256(d->context,t->packet.bytes,hash);if(status==COH_OK&&memcmp(hash,b->packet_sha256,32))status=COH_STATE;}
 if(status==COH_OK)status=coh_catalog_owner_retain(o);
 if(status==COH_OK){t->owner=o;status=decode(t,input.size);}
 if(status==COH_OK){CohRuntimeGroupsBudget gb={limit,budget->retained_bytes+input.size};CohRuntimeGroupsReport matched;status=coh_runtime_graph_compare_groups_witness(g,o,t,b,packet,&gb,&matched);}
 if(status!=COH_OK){coh_runtime_groups_witness_release(t);return status;}*report=t->report;*out=t;return COH_OK;
}

typedef struct {const CohRuntimeGraph *graph;const CohCatalogOwner *owner;CohBytes snapshot;size_t root_offset;uint32_t root_slot,current_file,next_slot;unsigned have_file;const CohRuntimeGroupsWitness *witness;CohRuntimeGroupsReport report;} Match;
static int span(size_t n,size_t at,size_t bytes){return at<=n&&bytes<=n-at;}
static CohStatus observe_witness(void *context,const CohGroupsEvent *event){
    Match *m=context;CohRepReader r=event->span;uint32_t n;char name[COH_REP_NAME_MAX];
    if(event->kind==COH_GROUPS_FILE_HEADER){
        if(m->have_file){const WFile*wf=&m->witness->files[m->current_file];while(m->next_slot<wf->slots&&!w(m->witness->records+(size_t)(wf->first+m->next_slot)*64,8))m->next_slot++;if(m->next_slot!=wf->slots)return COH_STATE;}
        m->have_file=1;m->current_file=event->file;m->next_slot=0;
        CohCatalogFileView file;TRY(coh_catalog_owner_file(m->owner,event->file,&file));
        TRY(coh_rep_read(&r,1,&n));if(n!=1)return COH_UNSUPPORTED;
        TRY(coh_rep_string(&r,name,sizeof(name)));if(strcmp(name,file.name))return COH_STATE;
        TRY(coh_rep_read(&r,32,&n));if(n!=file.bounds_checksum)return COH_STATE;
        TRY(coh_rep_read(&r,1,&n));if(n||r.cursor!=r.bits)return COH_STATE;
        m->report.files_equal++;return COH_OK;
    }
    if(event->kind==COH_GROUPS_DEFINITION){
        if(!m->have_file||event->file!=m->current_file)return COH_STATE;
        const WFile*wf=&m->witness->files[event->file];while(m->next_slot<wf->slots&&!w(m->witness->records+(size_t)(wf->first+m->next_slot)*64,8))m->next_slot++;
        if(m->next_slot>=wf->slots||event->slot!=m->next_slot)return COH_STATE;
        m->next_slot++;
        uint32_t index;CohRuntimeGraphNode node;TRY(coh_runtime_graph_slot(m->graph,event->file,event->slot,&index));TRY(coh_runtime_graph_node(m->graph,index,&node));
        size_t bits=r.bits-r.cursor;if(!node.aligned||(r.cursor&7)||bits!=node.wire_bits||bits%8||bits/8!=node.wire.size)return COH_STATE;
        if(memcmp(r.bytes.data+r.cursor/8,node.wire.data,node.wire.size))return COH_STATE;
        m->report.emitted_definitions_equal++;return COH_OK;
    }
    if(m->have_file){const WFile*wf=&m->witness->files[m->current_file];while(m->next_slot<wf->slots&&!w(m->witness->records+(size_t)(wf->first+m->next_slot)*64,8))m->next_slot++;if(m->next_slot!=wf->slots)return COH_STATE;m->have_file=0;}
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
CohStatus coh_runtime_graph_compare_groups_witness(const CohRuntimeGraph*graph,const CohCatalogOwner*owner,const CohRuntimeGroupsWitness*t,const CohRuntimeGroupsWitnessBinding*b,const CohRepReader*reader,const CohRuntimeGroupsBudget*budget,CohRuntimeGroupsReport*out){
 if(!graph||!owner||!t||!b||!reader||!budget||!out)return COH_INVALID;
 const void*p[]={b,reader,budget,out,reader->bytes.data,t,t->records,t->bytes,t->files,t->catalog.data,t->snapshot.data};
 size_t z[]={sizeof(*b),sizeof(*reader),sizeof(*budget),sizeof(*out),reader->bytes.size,sizeof(*t),(size_t)t->report.records*64,t->packet.bytes.size,(size_t)t->report.files*sizeof(WFile),t->catalog.size,t->snapshot.size};
 /* Internal immutable spans may contain the same source allocation as a graph
  * owner, but public controls/reader may never alias them or one another. */
 for(unsigned i=0;i<5;i++)for(unsigned j=i+1;j<11;j++)if(!disjoint(p[i],z[i],p[j],z[j]))return COH_INVALID;
 if(t->graph!=graph||t->owner!=owner||!equal(&t->binding,b))return COH_STATE;
 CohBytes catalog,snapshot;CohRuntimeGraphReport gr;TRY(owners(graph,owner,b,&catalog,&snapshot,&gr));if(catalog.data!=t->catalog.data||catalog.size!=t->catalog.size||snapshot.data!=t->snapshot.data||snapshot.size!=t->snapshot.size)return COH_STATE;
 if(reader->bytes.size!=t->packet.bytes.size||reader->bits!=t->packet.bits||reader->cursor!=t->packet.cursor||reader->compressed!=t->packet.compressed||memcmp(reader->bytes.data,t->bytes,reader->bytes.size))return COH_STATE;
 size_t total=budget->retained_bytes,limit=budget->aggregate_limit;if(!limit||limit>COH_SG_TRANSACTION_MAX||total>limit)return COH_LIMIT;
 size_t add[]={t->report.owned_bytes,gr.owned_bytes,coh_catalog_owner_owned_bytes(owner),snapshot.size,reader->bytes.size,COH_GROUPS_WITNESS_FIXED_SCRATCH_BYTES,sizeof(CohRuntimeGroupsReport)};for(unsigned i=0;i<sizeof(add)/sizeof(add[0]);i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];}
 CohRepReader copy=*reader;CohGroupsInspection inspection;TRY(coh_rep_groups(&copy,&inspection,NULL));
 if(!inspection.new_world||inspection.files!=gr.source.files||inspection.present_files!=inspection.files||inspection.roots!=gr.source.root_slots||inspection.footer_active_roots!=gr.source.active_roots||inspection.footer_defs_crc!=gr.source.source_defs_crc||inspection.footer_refs_crc!=gr.source.source_refs_crc||inspection.defs!=t->report.eligible_definitions)return COH_STATE;
 CohRepReader pr=*reader;CohRepScenePrefix prefix;TRY(coh_rep_scene_prefix(&pr,&prefix));CohCatalogFileView mapfile={0};if(gr.source.files){TRY(coh_catalog_owner_file(owner,0,&mapfile));if(strcmp(mapfile.name,prefix.map_path))return COH_STATE;}else if(prefix.map_path[0])return COH_STATE;
 Match m;memset(&m,0,sizeof(m));m.report.prefix=prefix;m.graph=graph;m.owner=owner;m.witness=t;m.snapshot=snapshot;m.root_offset=80;m.report.graph_generation=b->graph_generation;m.report.catalog_generation=b->catalog_generation;m.report.aggregate_reserved_bytes=total;
 CohGroupsVisitor visitor={&m,observe_witness};copy=*reader;TRY(coh_rep_groups_visit(&copy,&visitor,&m.report.groups,NULL));
 if(m.have_file){const WFile*wf=&t->files[m.current_file];while(m.next_slot<wf->slots&&!w(t->records+(size_t)(wf->first+m.next_slot)*64,8))m.next_slot++;if(m.next_slot!=wf->slots)return COH_STATE;}
 if(m.report.files_equal!=gr.source.files||m.root_slot!=gr.source.root_slots||m.report.root_wires_equal!=gr.source.active_roots||m.report.emitted_definitions_equal!=inspection.defs)return COH_STATE;
 *out=m.report;return COH_OK;
}

size_t coh_runtime_groups_witness_owned_bytes(const CohRuntimeGroupsWitness*t){return t?t->report.owned_bytes:0;}
