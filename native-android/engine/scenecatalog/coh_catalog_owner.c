#include "coh_catalog_owner.h"
#include <stdlib.h>
#include <string.h>
typedef struct {uint32_t name_offset,bounds_checksum,slots,records,first;} OwnerFile;
typedef struct {uint32_t record_offset,wire_bytes;} OwnerSlot;
struct CohCatalogOwner {
    CohCatalogBinding binding;CohCatalogReport catalog;
    size_t owned_bytes,index_bytes;uint32_t references,next_slot;
    uint8_t *bytes;OwnerFile *files;OwnerSlot *slots;
};
static int nonzero(const uint8_t *p){uint8_t x=0;for(unsigned i=0;i<32;i++)x|=p[i];return x!=0;}
static int equal(const CohCatalogBinding *a,const CohCatalogBinding *b){
    return a->owner_generation==b->owner_generation&&a->catalog_generation==b->catalog_generation&&
        a->asset_generation==b->asset_generation&&a->map_generation==b->map_generation&&
        !memcmp(a->catalog_sha256,b->catalog_sha256,32)&&!memcmp(a->source_sha256,b->source_sha256,32)&&
        !memcmp(a->inventory_sha256,b->inventory_sha256,32)&&!memcmp(a->map_sha256,b->map_sha256,32);
}
static CohStatus binding(const CohCatalogOwner *old,const CohCatalogBinding *b){
    if(!b->catalog_generation||!b->asset_generation||
       !nonzero(b->catalog_sha256)||!nonzero(b->source_sha256)||!nonzero(b->inventory_sha256)||
       (!!b->map_generation!=!!nonzero(b->map_sha256)))return COH_STATE;
    uint32_t previous=old?old->binding.owner_generation:0;
    if(previous==UINT32_MAX||b->owner_generation!=previous+1)return COH_STATE;
    if(old){const CohCatalogBinding *a=&old->binding;
        if(b->catalog_generation<a->catalog_generation||b->asset_generation<a->asset_generation||b->map_generation<a->map_generation)return COH_STATE;
        if(b->catalog_generation==a->catalog_generation&&
           (memcmp(b->catalog_sha256,a->catalog_sha256,32)||memcmp(b->source_sha256,a->source_sha256,32)))return COH_STATE;
        if(b->asset_generation==a->asset_generation&&memcmp(b->inventory_sha256,a->inventory_sha256,32))return COH_STATE;
        if(b->map_generation==a->map_generation&&memcmp(b->map_sha256,a->map_sha256,32))return COH_STATE;
    }return COH_OK;
}
static CohStatus index_file(void *context,const CohCatalogFileView *v){
    CohCatalogOwner *o=context;OwnerFile *f=&o->files[v->index];
    *f=(OwnerFile){(uint32_t)((const uint8_t *)v->name-o->bytes),v->bounds_checksum,v->slots,v->records,o->next_slot};
    o->next_slot+=v->slots;return COH_OK;
}
static CohStatus index_slot(void *context,const CohCatalogSlotView *v){
    CohCatalogOwner *o=context;OwnerSlot *s=&o->slots[o->files[v->file->index].first+v->slot];
    *s=(OwnerSlot){(uint32_t)v->record_offset,(uint32_t)v->wire_bytes};return COH_OK;
}
void coh_catalog_owner_release(CohCatalogOwner *o){
    if(!o)return;
    if(--o->references)return;
    free(o->slots);free(o->files);free(o->bytes);free(o);
}
CohStatus coh_catalog_owner_retain(CohCatalogOwner *o){if(!o)return COH_INVALID;if(o->references==UINT32_MAX)return COH_LIMIT;o->references++;return COH_OK;}
size_t coh_catalog_owner_owned_bytes(const CohCatalogOwner *o){return o?o->owned_bytes:0;}
CohStatus coh_catalog_owner_create(const CohCatalogOwner *old,CohBytes input,
    const CohCatalogBinding *b,const CohCatalogOwnerBudget *budget,const CohCatalogDigest *digest,
    CohCatalogOwner **out,CohCatalogOwnerReport *report){
    CohCatalogOwnerReport r={0};CohCatalogOwner *o=NULL;CohStatus status=COH_INVALID;
    CohCatalogReport pre={0};size_t fixed,extra;uint8_t actual[32]={0};
    r.input_bytes=input.size;r.previous_bytes=coh_catalog_owner_owned_bytes(old);
    if(!out||!b||!budget||!digest||!digest->sha256||!input.data)goto done;
    if(*out){status=COH_STATE;goto done;}
    if(budget->owned_limit>COH_CATALOG_MEMORY_MAX||budget->working_limit>COH_CATALOG_MEMORY_MAX||
       budget->aggregate_limit>COH_SG_TRANSACTION_MAX)goto done;
    status=binding(old,b);if(status!=COH_OK)goto done;
    r.retained_bytes=budget->retained_bytes;
    /* Refuse impossible spans before touching caller input or invoking provider. */
    status=COH_LIMIT;
    if(input.size>COH_CATALOG_INPUT_MAX||input.size>budget->owned_limit||
       sizeof(*o)>budget->owned_limit-input.size||input.size>budget->working_limit||
       COH_CATALOG_WALK_STACK_RESERVE>budget->working_limit-input.size)goto done;
    if(budget->retained_bytes>budget->aggregate_limit||r.previous_bytes>budget->aggregate_limit-budget->retained_bytes)goto done;
    extra=budget->retained_bytes+r.previous_bytes;
    if(input.size>budget->aggregate_limit-extra)goto done;
    extra+=input.size;
    fixed=sizeof(*o)+input.size;
    if(fixed>budget->aggregate_limit-extra||COH_CATALOG_WALK_STACK_RESERVE>budget->aggregate_limit-extra-fixed)goto done;
    o=calloc(1,sizeof(*o));if(!o)goto done;
    o->references=1;o->binding=*b;o->owned_bytes=fixed;
    o->bytes=malloc(input.size);if(!o->bytes)goto done;
    memcpy(o->bytes,input.data,input.size);
    status=digest->sha256(digest->context,(CohBytes){o->bytes,input.size},actual);
    if(status<COH_OK||status>COH_STATE)status=COH_INVALID;
    if(status!=COH_OK)goto done;
    if(memcmp(actual,b->catalog_sha256,32)){status=COH_STATE;goto done;}
    status=coh_scenecatalog_preflight((CohBytes){o->bytes,input.size},b->catalog_generation,&pre);
    if(status!=COH_OK){r.walk.catalog=pre;goto done;}
    o->index_bytes=(size_t)pre.files*sizeof(*o->files)+(size_t)pre.slots*sizeof(*o->slots);
    status=COH_LIMIT;
    if(o->index_bytes>budget->owned_limit-fixed||o->index_bytes>budget->aggregate_limit-extra-fixed||
       COH_CATALOG_WALK_STACK_RESERVE>budget->aggregate_limit-extra-fixed-o->index_bytes)goto done;
    o->owned_bytes+=o->index_bytes;
    if(pre.files)o->files=calloc(pre.files,sizeof(*o->files));
    if(pre.slots)o->slots=calloc(pre.slots,sizeof(*o->slots));
    if((pre.files&&!o->files)||(pre.slots&&!o->slots))goto done;
    CohCatalogWalkBudget walk={budget->working_limit,budget->aggregate_limit,extra+sizeof(*o)+o->index_bytes};
    CohCatalogVisitor visitor={o,index_file,index_slot};
    status=coh_scenecatalog_walk((CohBytes){o->bytes,input.size},b->catalog_generation,&walk,&visitor,&r.walk);
    r.peak_aggregate_bytes=r.walk.peak_aggregate_bytes;
    if(status!=COH_OK)goto done;
    o->catalog=r.walk.catalog;r.owned_bytes=o->owned_bytes;r.index_bytes=o->index_bytes;
    *out=o;o=NULL;
done:
    if(o){r.owned_bytes=o->owned_bytes;r.index_bytes=o->index_bytes;coh_catalog_owner_release(o);}
    r.status=status;if(report)*report=r;return status;
}
CohStatus coh_catalog_owner_bytes(const CohCatalogOwner *o,CohBytes *out){if(!o||!out)return COH_INVALID;*out=(CohBytes){o->bytes,o->catalog.input_bytes};return COH_OK;}
CohStatus coh_catalog_owner_binding(const CohCatalogOwner *o,CohCatalogBinding *out){if(!o||!out)return COH_INVALID;*out=o->binding;return COH_OK;}
CohStatus coh_catalog_owner_file(const CohCatalogOwner *o,uint32_t id,CohCatalogFileView *out){
    if(!o||!out)return COH_INVALID;
    if(id>=o->catalog.files)return COH_NOT_FOUND;
    const OwnerFile *f=&o->files[id];
    *out=(CohCatalogFileView){(const char *)o->bytes+f->name_offset,id,f->bounds_checksum,f->slots,f->records,o->binding.catalog_generation};return COH_OK;
}
CohStatus coh_catalog_owner_record(const CohCatalogOwner *o,uint32_t file,uint32_t slot,CohCatalogRecordIdentity *out){
    if(!o||!out)return COH_INVALID;
    if(file>=o->catalog.files||slot>=o->files[file].slots)return COH_NOT_FOUND;
    const OwnerSlot *s=&o->slots[o->files[file].first+slot];CohCatalogRecordIdentity r={0};
    r.file=file;r.slot=slot;r.allocated=s->record_offset!=0;r.record_offset=s->record_offset;r.wire_bytes=s->wire_bytes;
    if(r.allocated){
        CohRepReader reader;uint32_t id,mod_time;CohStatus status;r.wire_offset=r.record_offset+16;
        status=coh_rep_reader_bounded(&reader,(CohBytes){o->bytes+r.wire_offset,r.wire_bytes},r.wire_bytes*8,1,COH_REP_BOUNDED_MESSAGE_MAX);
        if(status==COH_OK)status=coh_rep_pack(&reader,1,&id);
        if(status==COH_OK&&id!=slot+1)status=COH_STATE;
        if(status==COH_OK)status=coh_rep_read(&reader,1,&r.in_use);
        if(status==COH_OK&&r.in_use)status=coh_rep_string(&reader,r.name,sizeof(r.name));
        if(status==COH_OK&&r.in_use)status=coh_rep_read(&reader,32,&mod_time);
        if(status==COH_OK&&r.in_use)status=coh_rep_pack(&reader,1,&r.child_count);
        if(status!=COH_OK)return status;
    }*out=r;return COH_OK;
}
CohStatus coh_catalog_owner_compare_groups(const CohCatalogOwner *o,const CohCatalogBinding *b,
    const CohRepReader *reader,CohCatalogGroupsMatch *out){
    CohCatalogGroupsMatch r={0};r.status=COH_INVALID;
    if(!o||!b||!reader)goto done;
    if(!o->binding.map_generation||!equal(&o->binding,b)){r.mismatches=COH_CATALOG_MISMATCH_BINDING;r.status=COH_STATE;goto done;}
    CohRepReader copy=*reader;r.status=coh_rep_groups(&copy,&r.groups,&r.failure);
    if(r.status!=COH_OK)goto done;
    if(!r.groups.new_world)r.mismatches|=COH_CATALOG_MISMATCH_NEW_WORLD;
    if(r.groups.files!=o->catalog.files)r.mismatches|=COH_CATALOG_MISMATCH_FILES;
    if(r.groups.footer_defs_crc!=o->catalog.source_defs_crc)r.mismatches|=COH_CATALOG_MISMATCH_DEFS_CRC;
    if(r.groups.footer_refs_crc!=o->catalog.source_refs_crc)r.mismatches|=COH_CATALOG_MISMATCH_REFS_CRC;
    if(r.groups.footer_active_roots!=o->catalog.source_active_roots||
       r.groups.roots-r.groups.removed_roots!=o->catalog.source_active_roots)r.mismatches|=COH_CATALOG_MISMATCH_ROOTS;
    if(r.mismatches)r.status=COH_STATE;
done:
    if(out)*out=r;
    return r.status;
}
