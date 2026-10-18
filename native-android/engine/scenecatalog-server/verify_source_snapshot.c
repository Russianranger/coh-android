/* Private host verifier. This consumes observations, never grants provenance,
 * cache/CLIENT/actor/render/world authority or a current-after-release lease.
 * The existing complete GROUPS grammar is included once. During a definition
 * event its reads are mirrored against the corresponding catalog record, so
 * every original scalar (including optional metadata and properties) agrees
 * without adding a second sendDef grammar or equating wire representations.
 * Serialized host process only; mirror is disabled outside that second walk. */
#include "../scenecatalog/coh_resource_join.h"
#include "../scenegraph/coh_public_bounds.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static CohRepReader *v_mirror;
static size_t v_scalars;
static CohStatus v_read(CohRepReader *r,unsigned width,uint32_t *out){
    CohStatus s=coh_rep_read(r,width,out);uint32_t other;
    if(s==COH_OK&&v_mirror){s=coh_rep_read(v_mirror,width,&other);if(s==COH_OK&&other!=*out)s=COH_STATE;v_scalars++;}return s;
}
static CohStatus v_pack(CohRepReader *r,unsigned width,uint32_t *out){
    CohStatus s=coh_rep_pack(r,width,out);uint32_t other;
    if(s==COH_OK&&v_mirror){s=coh_rep_pack(v_mirror,width,&other);if(s==COH_OK&&other!=*out)s=COH_STATE;v_scalars++;}return s;
}
#define coh_rep_read v_read
#define coh_rep_pack v_pack
#include "../replication/coh_groups.c"
#undef coh_rep_read
#undef coh_rep_pack
#undef TRY
#define V_TRY(x) do{CohStatus vs_=(x);if(vs_!=COH_OK)return vs_;}while(0)
#define V_NEED(x) do{if(!(x))return COH_STATE;}while(0)
#define V_LIMIT (96u*1024u*1024u)
#define V_RESERVE (512u*1024u)
#define V_ELIGIBILITY_MAX ((2u+4096u+65536u+65536u)*64u)
extern CohStatus coh_runtime_matrix_read(CohRepReader *,CohSgMatrix);
static uint32_t v_u32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t v_word(CohBytes b,size_t n){return v_u32(b.data+n*4u);}
static int v_zero(const uint8_t*p,size_t n){for(size_t i=0;i<n;i++)if(p[i])return 0;return 1;}
static CohStatus v_digest(void *context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
/* The retained owner validates every complete definition through the same
 * decoder while retaining one record at a time. Match only its successful
 * report: these are exactly the five eager-catalog compatibility predicates,
 * without requiring a second fully materialized definition graph. This is a
 * private observation comparison, not the map-bound live admission API. */
static CohStatus v_catalog_match(const CohCatalogReport *c,const CohGroupsInspection *g){
    if(!c||!g)return COH_INVALID;
    return g->new_world&&g->files==c->files&&g->footer_defs_crc==c->source_defs_crc&&g->footer_refs_crc==c->source_refs_crc&&g->footer_active_roots==c->source_active_roots?COH_OK:COH_STATE;
}
static size_t v_peak;
static CohStatus v_charge(size_t n){if(n>V_LIMIT)return COH_LIMIT;if(n>v_peak)v_peak=n;return COH_OK;}
static CohStatus v_file(const char *directory,const char *name,size_t cap,size_t retained,CohBytes *out){
    char path[4096];int count_=snprintf(path,sizeof(path),"%s/%s",directory,name);if(count_<0||(size_t)count_>=sizeof(path))return COH_LIMIT;
    FILE*f=fopen(path,"rb");if(!f)return COH_IO;
    if(fseek(f,0,SEEK_END)){fclose(f);return COH_IO;}long n=ftell(f);
    if(n<=0||(size_t)n>cap||retained>V_LIMIT||(size_t)n>V_LIMIT-retained){fclose(f);return COH_LIMIT;}
    rewind(f);uint8_t*p=malloc((size_t)n);if(!p){fclose(f);return COH_LIMIT;}
    size_t got=fread(p,1,(size_t)n,f);int end=fgetc(f),closed=fclose(f);
    if(got!=(size_t)n||end!=EOF||closed){free(p);return COH_IO;}
    *out=(CohBytes){p,(size_t)n};return v_charge(retained+(size_t)n);
}
static void v_drop(CohBytes *b){free((void*)b->data);*b=(CohBytes){0};}
typedef struct {
    CohCatalogOwner *catalog;CohRuntimeGraph *graph;CohBytes cat,eligibility,snapshot;
    uint32_t file_at[COH_GROUPS_FILE_MAX],root_at,files,slots,roots,present,definitions,emitted_roots;
    uint32_t root_header[COH_SG_ROOTS_MAX];
    uint32_t visit_files,visit_definitions,visit_roots,expected_file,expected_slot,expected_root;
} VContext;
static CohBytes v_record(const VContext*c,uint32_t record){return(CohBytes){c->eligibility.data+(size_t)record*64u,64};}
static CohStatus v_ledger(VContext*c,const CohRuntimeSnapshotReport*sr,CohBytes owner,CohBytes meta){
    CohBytes in=c->eligibility;V_NEED(in.size>=128&&!(in.size%64));CohBytes b=v_record(c,0);
    V_NEED(v_word(b,0)==1&&v_word(b,1)==1&&v_word(b,2)==v_u32(c->cat.data+20)&&v_word(b,3)==1);
    V_NEED(v_word(b,4)==v_word(owner,30)&&v_word(b,5)==v_word(owner,31)&&v_word(b,6)==v_word(owner,32));
    V_NEED(v_word(b,7)==sr->files&&v_word(b,8)==sr->slots&&v_word(b,9)==sr->root_slots&&v_word(b,10)==sr->active_roots);
    V_NEED(!v_word(b,11)&&!v_word(b,12)&&v_word(b,13)==(v_word(b,5)!=v_word(b,6))&&v_word(b,13)==1&&!v_word(b,14)&&!v_word(b,15));
    uint32_t at=1,seen_slots=0;
    for(uint32_t f=0;f<sr->files;f++){
        uint32_t index=f+1==sr->files?0:f+1;V_NEED((size_t)at*64u<in.size);b=v_record(c,at);c->file_at[index]=at++;
        CohCatalogFileView file;V_TRY(coh_catalog_owner_file(c->catalog,index,&file));
        V_NEED(v_word(b,0)==2&&v_word(b,1)==index&&v_word(b,3)<=1&&v_word(b,4)<=1&&v_word(b,5)==file.slots&&v_word(b,6)==file.bounds_checksum&&v_word(b,7)==1&&v_zero(b.data+32,32));
        c->present++;
        for(uint32_t slot=0;slot<file.slots;slot++){
            V_NEED((size_t)at*64u<in.size);CohBytes d=v_record(c,at++);CohCatalogRecordIdentity identity;
            V_TRY(coh_catalog_owner_record(c->catalog,index,slot,&identity));
            V_NEED(v_word(d,0)==3&&v_word(d,1)==index&&v_word(d,2)==slot&&v_word(d,3)==slot&&v_word(d,6)<=1&&v_word(d,7)<=1&&v_word(d,8)<=1&&v_zero(d.data+36,28));
            /* The original eligibility producer requires every slot pointer.
             * Allocated tombstones are retained; holes cannot impersonate them. */
            V_NEED(identity.allocated&&identity.in_use==v_word(d,7));
            if(identity.in_use){CohRepReader r;uint32_t ignored,mod;
                V_TRY(coh_rep_reader_bounded(&r,(CohBytes){c->cat.data+identity.wire_offset,identity.wire_bytes},identity.wire_bytes*8u,1,COH_REP_BOUNDED_MESSAGE_MAX));
                V_TRY(coh_rep_pack(&r,1,&ignored));V_TRY(coh_rep_read(&r,1,&ignored));char name[COH_REP_NAME_MAX];V_TRY(coh_rep_string(&r,name,sizeof(name)));V_TRY(coh_rep_read(&r,32,&mod));V_NEED(mod==v_word(d,4));
            }
            uint32_t emit=v_word(b,3)||!(!v_word(b,4)&&v_word(d,5)&&v_word(d,6));
            V_NEED(v_word(d,8)==emit);c->definitions+=emit;seen_slots++;
        }
    }
    c->root_at=at;size_t root_bytes=80;
    for(uint32_t root=0;root<sr->root_slots;root++){
        V_NEED((size_t)at*64u<in.size);b=v_record(c,at++);CohRuntimeGraphRoot r;V_TRY(coh_runtime_graph_root(c->graph,root,&r));
        V_NEED(v_word(b,0)==4&&v_word(b,1)==root&&v_word(b,3)==r.active&&v_word(b,4)==1&&v_zero(b.data+20,44));c->emitted_roots++;
        V_NEED(root_bytes<=c->snapshot.size&&c->snapshot.size-root_bytes>=32);c->root_header[root]=(uint32_t)root_bytes;
        const uint8_t*h=c->snapshot.data+root_bytes;size_t size=32u+(size_t)v_u32(h+20)+(r.active?48u:0u)+v_u32(h+28);
        V_NEED(size<=c->snapshot.size-root_bytes);root_bytes+=size;
    }
    V_NEED((size_t)(at+1u)*64u==in.size);b=v_record(c,at);
    V_NEED(v_word(b,0)==5&&v_word(b,1)==at+1&&v_word(b,2)==sr->files&&v_word(b,3)==seen_slots&&v_word(b,4)==sr->root_slots&&v_word(b,5)==c->present&&v_word(b,6)==c->definitions&&v_word(b,7)==c->emitted_roots&&v_zero(b.data+32,32));
    const uint32_t actual[]={at+1,sr->files,seen_slots,sr->root_slots,c->present,c->definitions,c->emitted_roots};
    for(unsigned i=0;i<7;i++)V_NEED(actual[i]==v_word(meta,8u+i)); /* meta words6..12 after its8B magic */
    c->files=sr->files;c->slots=seen_slots;c->roots=sr->root_slots;return COH_OK;
}
static CohStatus v_finish_file(VContext*c){
    if(!c->visit_files)return COH_OK;
    CohCatalogFileView file;V_TRY(coh_catalog_owner_file(c->catalog,c->expected_file,&file));
    for(uint32_t slot=c->expected_slot;slot<file.slots;slot++)V_NEED(!v_word(v_record(c,c->file_at[c->expected_file]+1u+slot),8));
    c->expected_slot=file.slots; /* Finish once, including across many root events. */
    return COH_OK;
}
static CohStatus v_event(void *opaque,const CohGroupsEvent*e){
    VContext*c=opaque;CohRepReader r=e->span;uint32_t n;char name[COH_REP_NAME_MAX];
    if(e->kind==COH_GROUPS_FILE_HEADER){
        V_TRY(v_finish_file(c));V_NEED(c->visit_files<c->files&&e->file==(c->visit_files+1u==c->files?0:c->visit_files+1u));
        c->visit_files++;c->expected_file=e->file;c->expected_slot=0;CohCatalogFileView f;V_TRY(coh_catalog_owner_file(c->catalog,e->file,&f));
        V_TRY(coh_rep_read(&r,1,&n));V_NEED(n==1);V_TRY(coh_rep_string(&r,name,sizeof(name)));V_NEED(!strcmp(name,f.name));V_TRY(coh_rep_read(&r,32,&n));V_NEED(n==f.bounds_checksum);V_TRY(coh_rep_read(&r,1,&n));V_NEED(!n&&r.cursor==r.bits);return COH_OK;
    }
    if(e->kind==COH_GROUPS_DEFINITION){
        V_NEED(c->visit_files&&e->file==c->expected_file&&e->slot>=c->expected_slot);CohCatalogFileView f;V_TRY(coh_catalog_owner_file(c->catalog,e->file,&f));V_NEED(e->slot<f.slots);
        for(uint32_t slot=c->expected_slot;slot<e->slot;slot++)V_NEED(!v_word(v_record(c,c->file_at[e->file]+1u+slot),8));
        V_NEED(v_word(v_record(c,c->file_at[e->file]+1u+e->slot),8)==1);CohCatalogRecordIdentity d;V_TRY(coh_catalog_owner_record(c->catalog,e->file,e->slot,&d));
        CohRepReader other;V_TRY(coh_rep_reader_bounded(&other,(CohBytes){c->cat.data+d.wire_offset,d.wire_bytes},d.wire_bytes*8u,1,COH_REP_BOUNDED_MESSAGE_MAX));
        uint32_t id;V_TRY(coh_rep_pack(&r,1,&id));V_NEED(id==e->slot+1u);V_TRY(coh_rep_pack(&other,1,&n));V_NEED(n==id);
        Groups g={0};g.reader=r;v_mirror=&other;CohStatus s=definition(&g);v_mirror=NULL;V_TRY(s);V_NEED(g.reader.cursor==r.bits&&other.cursor==other.bits);
        c->visit_definitions++;c->expected_slot=e->slot+1u;return COH_OK;
    }
    V_NEED(e->kind==COH_GROUPS_ROOT&&e->slot==c->expected_root&&e->slot<c->roots);V_TRY(v_finish_file(c));
    CohRuntimeGraphRoot root;V_TRY(coh_runtime_graph_root(c->graph,e->slot,&root));V_TRY(coh_rep_pack(&r,1,&n));V_NEED(n==e->slot);V_TRY(coh_rep_string(&r,name,sizeof(name)));
    if(root.active){CohRuntimeGraphNode node;V_TRY(coh_runtime_graph_node(c->graph,root.node,&node));V_NEED(!strcmp(name,node.name));
        const uint8_t*h=c->snapshot.data+c->root_header[e->slot];uint32_t bytes=v_u32(h+28),bits_=v_u32(h+24);const uint8_t*wire=h+32u+v_u32(h+20)+48u;CohRepReader other;
        V_TRY(coh_rep_reader_bounded(&other,(CohBytes){wire,bytes},bits_,1,COH_REP_BOUNDED_MESSAGE_MAX));Groups g={0};g.reader=r;size_t definition_scalars=v_scalars;v_mirror=&other;CohStatus s=matrix(&g);v_mirror=NULL;v_scalars=definition_scalars;V_TRY(s);V_NEED(other.cursor==other.bits);r=g.reader;
    }else V_NEED(!name[0]);
    V_NEED(r.cursor==r.bits);c->expected_root++;c->visit_roots++;return COH_OK;
}

int main(int argc,char **argv){
    CohStatus status=COH_INVALID;unsigned stage=0;const char *operation=NULL;CohBytes meta={0},owner={0},packet={0},input={0},side={0},resources={0},raw={0},eligibility={0},cat={0},snapshot_bytes={0};
    CohCatalogOwner *catalog=NULL;CohCatalogSnapshot *snapshot=NULL;CohRuntimeGraph *graph=NULL;CohResourceJoin *join=NULL;CohPublicBounds *bounds=NULL;
    CohCatalogBinding cb={0};CohCatalogSnapshotBinding sb={0};CohCatalogDigest digest_={NULL,v_digest};CohCatalogOwnerReport cr={0};CohCatalogReport er={0};CohRuntimeSnapshotReport sr={0};CohRuntimeGraphReport gr={0};CohResourceJoinReport jr={0};CohPublicBoundsReport br={0};CohGroupsInspection groups={0};CohGroupsFailure failure={0};VContext c={0};size_t retained=V_RESERVE;
#define DO(x) do{status=(x);if(status!=COH_OK)goto done;}while(0)
#define NEED(x) do{if(!(x)){status=COH_STATE;goto done;}}while(0)
    if(argc!=2)goto done;
    stage=1;DO(v_file(argv[1],"packet-metadata.bin",192,retained,&meta));NEED(meta.size==192&&!memcmp(meta.data,"COHGPAK1",8)&&v_word(meta,2)==1&&v_word(meta,3)==192&&v_zero(meta.data+160,32));retained+=meta.size;
    DO(v_file(argv[1],"owner.cohown",192,retained,&owner));NEED(owner.size==192&&!memcmp(owner.data,"COHOWN01",8)&&v_word(owner,2)==1&&v_word(owner,3)==192&&v_word(owner,4)&&v_word(owner,5)&&v_word(owner,6));retained+=owner.size;
    NEED(v_word(meta,6)<=1&&v_word(meta,7)==1&&!v_word(meta,33)&&!v_word(meta,34));DO(v_file(argv[1],"packet.bin",COH_REP_BOUNDED_MESSAGE_MAX,retained,&packet));NEED(packet.size==((uint64_t)v_word(meta,5)+7u)/8u);retained+=packet.size;
    NEED(v_word(owner,12)==4||v_word(owner,12)==5);
    CohRepReader reader;DO(coh_rep_reader_bounded(&reader,packet,v_word(meta,5),v_word(meta,6),COH_REP_BOUNDED_MESSAGE_MAX));uint32_t command;DO(coh_rep_pack(&reader,1,&command));NEED(command==COH_REP_GROUPS);CohRepReader body=reader;DO(coh_rep_groups(&reader,&groups,&failure));
    /* Fixed source-defined operation names expose no path, record, count,
     * allocation size or original packet data. Keep each assignment immediately
     * before its call so a refusal identifies the actual first failed call. */
    stage=2;operation="CATALOG_INPUT";DO(v_file(argv[1],"catalog.cohcat",COH_CATALOG_INPUT_MAX,retained,&input));
    operation="CATALOG_HEADER";NEED(input.size>=48&&v_u32(input.data+20)==v_word(meta,4));
    operation="CATALOG_PREFLIGHT";DO(coh_scenecatalog_preflight(input,v_word(meta,4),&er));
    /* These private join labels distinguish the exact observed byte sets only.
     * They do not admit a source provenance/run/asset manifest. The external
     * source-pinned supervisor/admitter must independently establish that chain
     * before deriving its separate immutable source-only snapshot token. */
    cb.owner_generation=1;cb.catalog_generation=v_word(meta,4);cb.asset_generation=cb.catalog_generation;
    operation="CATALOG_DIGEST";DO(v_digest(NULL,input,cb.catalog_sha256));
    operation="OWNER_DIGEST";DO(v_digest(NULL,owner,cb.source_sha256));
    operation="METADATA_DIGEST";DO(v_digest(NULL,meta,cb.inventory_sha256));
    CohCatalogOwnerBudget cbudget={32u<<20,32u<<20,V_LIMIT,retained};
    operation="CATALOG_OWNER_CREATE";DO(coh_catalog_owner_create(NULL,input,&cb,&cbudget,&digest_,&catalog,&cr));
    operation="GROUPS_MATCH";DO(v_catalog_match(&cr.walk.catalog,&groups));
    operation="CATALOG_OWNER_RESERVATION";DO(v_charge(cr.peak_aggregate_bytes));v_drop(&input);
    operation="CATALOG_OWNER_VIEW";DO(coh_catalog_owner_bytes(catalog,&cat));
    stage=3;DO(v_file(argv[1],"runtime.cohrts",COH_RUNTIME_SNAPSHOT_INPUT_MAX,retained+coh_catalog_owner_owned_bytes(catalog),&side));sb.generation=1;sb.catalog=cb;DO(v_digest(NULL,side,sb.snapshot_sha256));DO(v_digest(NULL,meta,sb.run_sha256));CohRuntimeSnapshotBudget sbudget={V_LIMIT,retained};DO(coh_catalog_snapshot_create(NULL,catalog,side,&sb,&sbudget,&digest_,NULL,&snapshot));v_drop(&side);DO(coh_catalog_snapshot_view(snapshot,&snapshot_bytes,&sb,&sr));DO(v_charge(sr.aggregate_peak_bytes));
    CohRuntimeGraphBinding gb={0};gb.generation=1;gb.catalog_generation=cb.catalog_generation;gb.pins.asset_generation=cb.asset_generation;gb.pins.digest=v_digest;memcpy(gb.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(gb.pins.snapshot_sha256,sb.snapshot_sha256,32);memcpy(gb.pins.source_sha256,cb.source_sha256,32);memcpy(gb.pins.run_sha256,sb.run_sha256,32);
    CohRuntimeSnapshotBudget gbudget={V_LIMIT,retained+coh_catalog_owner_owned_bytes(catalog)-cat.size+coh_catalog_snapshot_owned_bytes(snapshot)-snapshot_bytes.size};DO(coh_runtime_graph_build(NULL,cat,snapshot_bytes,&gb,&gbudget,NULL,&graph,&gr));DO(v_charge(gr.aggregate_peak_bytes));
    stage=4;size_t owners=coh_catalog_owner_owned_bytes(catalog)+coh_catalog_snapshot_owned_bytes(snapshot)+gr.owned_bytes;
    DO(v_file(argv[1],"eligibility.bin",V_ELIGIBILITY_MAX,retained+owners,&eligibility));c.catalog=catalog;c.graph=graph;c.cat=cat;c.eligibility=eligibility;c.snapshot=snapshot_bytes;DO(v_ledger(&c,&sr,owner,meta));
    CohGroupsVisitor visitor={&c,v_event};reader=body;DO(coh_rep_groups_visit(&reader,&visitor,&groups,&failure));DO(v_finish_file(&c));NEED(c.visit_files==c.files&&c.visit_definitions==c.definitions&&c.visit_roots==c.emitted_roots);v_drop(&eligibility);
    stage=5;DO(v_file(argv[1],"resources.cohres",COH_RESOURCE_INPUT_MAX,retained+owners,&resources));CohResourceJoinPins pins={0};pins.resource.generation=1;pins.resource.asset_generation=cb.asset_generation;memcpy(pins.resource.source_sha256,cb.source_sha256,32);memcpy(pins.resource.run_sha256,sb.run_sha256,32);memcpy(pins.resource.manifest_sha256,cb.inventory_sha256,32);DO(v_digest(NULL,resources,pins.resources_sha256));CohResourceJoinBudget rbudget={32u<<20,V_LIMIT,retained};DO(coh_resource_join_build(NULL,catalog,snapshot,graph,resources,&pins,&rbudget,v_digest,NULL,(CohCancel){NULL,NULL},&join,&jr));DO(v_charge(jr.aggregate_peak_bytes));NEED(jr.source_association_verified&&jr.rows==v_word(meta,27)&&jr.models==v_word(meta,28)&&jr.rows-jr.models==v_word(meta,29));
    const CohResourceSource *rows;size_t row_count;CohResourceBinding resource_binding;DO(coh_resource_join_sources(join,&rows,&row_count,&resource_binding));size_t textures=0;for(size_t i=0;i<row_count;i++)textures+=v_u32(rows[i].record.data+96);NEED(textures==v_word(meta,30));coh_resource_join_free(join);join=NULL;v_drop(&resources);
    /* Raw prefix bytes remain opaque. This validates owner/header/file/slot/
     * public-name decisions; it deliberately does not assert stale cache tokens
     * equal recomputation, nor infer Win32 layout merely from a self-label. */
    stage=6;DO(v_file(argv[1],"public-bounds.cohrbw",COH_PUBLIC_BOUNDS_INPUT_MAX,retained+owners,&raw));CohPublicBoundsBinding bb={0};bb.generation=1;bb.catalog=cb;memcpy(bb.run_sha256,sb.run_sha256,32);DO(v_digest(NULL,raw,bb.raw_sha256));CohPublicBoundsBudget bbudget={32u<<20,V_LIMIT,retained+coh_catalog_snapshot_owned_bytes(snapshot)+gr.owned_bytes};DO(coh_public_bounds_create(NULL,catalog,raw,&bb,&bbudget,&digest_,&bounds,&br));DO(v_charge(br.aggregate_reserved_bytes));NEED(br.files==sr.files&&br.files==v_word(meta,35)&&br.slots==sr.slots&&br.slots==v_word(meta,36)&&br.public_rows==v_word(meta,37));
    stage=7;NEED(sr.files==v_word(meta,15)&&sr.definitions==v_word(meta,16)&&sr.slots==v_word(meta,17)&&sr.children==v_word(meta,18)&&sr.root_slots==v_word(meta,20)&&sr.active_roots==v_word(meta,21)&&sr.external_count==v_word(meta,22)&&gr.edges==(uint64_t)sr.children+v_word(meta,23)&&sr.source_defs_crc==v_word(meta,24)&&sr.source_refs_crc==v_word(meta,25));
done:
    printf("{\"schema\":\"coh-source-snapshot-native-result-v1\",\"passed\":%s,\"status\":%d,\"stage\":%u,\"source_generation_admitted\":false,\"world_authority\":false",status==COH_OK?"true":"false",status,stage);
    if(status!=COH_OK&&stage==2&&operation)printf(",\"operation\":\"%s\"",operation);
    if(status==COH_OK)printf(",\"checks\":{\"catalog_groups_match\":true,\"runtime_catalog_associations\":true,\"resource_catalog_associations\":true,\"raw_bounds_catalog_associations\":true,\"eligibility_groups_associations\":true},\"counts\":{\"files\":%u,\"slots\":%u,\"definitions\":%u,\"children\":%u,\"root_slots\":%u,\"active_roots\":%u,\"external_owners\":%u,\"resource_rows\":%u,\"model_rows\":%u,\"public_bounds_rows\":%u,\"emitted_definitions\":%u,\"emitted_roots\":%u,\"definition_scalars_compared\":%zu,\"named_peak_reservation_bytes\":%zu,\"named_aggregate_limit_bytes\":%u}",sr.files,sr.slots,sr.definitions,sr.children,sr.root_slots,sr.active_roots,sr.external_count,jr.rows,jr.models,br.public_rows,c.visit_definitions,c.visit_roots,v_scalars,v_peak,V_LIMIT);
    puts("}");coh_public_bounds_release(bounds);coh_resource_join_free(join);coh_runtime_graph_free(graph);coh_catalog_snapshot_release(snapshot);coh_catalog_owner_release(catalog);v_drop(&raw);v_drop(&resources);v_drop(&eligibility);v_drop(&side);v_drop(&input);v_drop(&packet);v_drop(&owner);v_drop(&meta);return status==COH_OK?0:2;
}
