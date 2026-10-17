#include "coh_catalog_snapshot.h"
#include <stdlib.h>
#include <string.h>
struct CohCatalogSnapshot {
    CohCatalogSnapshotBinding binding;
    CohRuntimeSnapshotReport report;
    CohCatalogOwner *catalog;
    uint8_t *bytes;
    size_t size;
    uint32_t references;
};
static int nonzero(const uint8_t p[32]){uint8_t v=0;for(unsigned i=0;i<32;i++)v|=p[i];return v!=0;}
static int same_catalog(const CohCatalogBinding *a,const CohCatalogBinding *b){
    return a->owner_generation==b->owner_generation&&a->catalog_generation==b->catalog_generation&&
        a->asset_generation==b->asset_generation&&a->map_generation==b->map_generation&&
        !memcmp(a->catalog_sha256,b->catalog_sha256,32)&&!memcmp(a->source_sha256,b->source_sha256,32)&&
        !memcmp(a->inventory_sha256,b->inventory_sha256,32)&&!memcmp(a->map_sha256,b->map_sha256,32);
}
size_t coh_catalog_snapshot_owned_bytes(const CohCatalogSnapshot *s){return s?sizeof(*s)+s->size:0;}
CohStatus coh_catalog_snapshot_retain(CohCatalogSnapshot *s){if(!s)return COH_INVALID;if(s->references==UINT32_MAX)return COH_LIMIT;s->references++;return COH_OK;}
void coh_catalog_snapshot_release(CohCatalogSnapshot *s){if(s&&!--s->references){coh_catalog_owner_release(s->catalog);free(s->bytes);free(s);}}
CohStatus coh_catalog_snapshot_create(const CohCatalogSnapshot *old,CohCatalogOwner *catalog,
    CohBytes input,const CohCatalogSnapshotBinding *binding,const CohRuntimeSnapshotBudget *budget,
    const CohCatalogDigest *digest,const CohCancel *cancel,CohCatalogSnapshot **out){
    CohCatalogSnapshot *s=NULL;CohCatalogBinding actual;CohBytes bytes;
    if(!catalog||!input.data||!binding||!budget||!digest||!digest->sha256||!out)return COH_INVALID;
    if(*out)return COH_STATE;
    if(coh_catalog_owner_binding(catalog,&actual)!=COH_OK||coh_catalog_owner_bytes(catalog,&bytes)!=COH_OK)return COH_STATE;
    if(!same_catalog(&actual,&binding->catalog)||!nonzero(binding->snapshot_sha256)||!nonzero(binding->run_sha256)||
       (old&&old->binding.generation==UINT32_MAX)||binding->generation!=(old?old->binding.generation+1:1))return COH_STATE;
    if(old&&(actual.owner_generation<old->binding.catalog.owner_generation||
        actual.catalog_generation<old->binding.catalog.catalog_generation||actual.asset_generation<old->binding.catalog.asset_generation))return COH_STATE;
    if(!budget->aggregate_limit||budget->aggregate_limit>COH_SG_TRANSACTION_MAX||input.size>COH_RUNTIME_SNAPSHOT_INPUT_MAX)return COH_LIMIT;
    /* Audit charges bytes+copied snapshot, report and stack. Add every other
     * retained allocation; aliasing old/new catalog bytes is explicitly handled. */
    size_t retained=budget->retained_bytes,charges[]={sizeof(*s),input.size,
        coh_catalog_owner_owned_bytes(catalog)-bytes.size,coh_catalog_snapshot_owned_bytes(old),
        old&&old->catalog!=catalog?coh_catalog_owner_owned_bytes(old->catalog):0};
    for(unsigned i=0;i<sizeof(charges)/sizeof(charges[0]);i++){
        if(retained>budget->aggregate_limit||charges[i]>budget->aggregate_limit-retained)return COH_LIMIT;
        retained+=charges[i];
    }
    if(bytes.size>budget->aggregate_limit-retained||input.size>budget->aggregate_limit-retained-bytes.size)return COH_LIMIT;
    s=calloc(1,sizeof(*s));if(!s)return COH_LIMIT;
    s->bytes=malloc(input.size?input.size:1);if(!s->bytes){free(s);return COH_LIMIT;}
    s->references=1;s->size=input.size;s->binding=*binding;
    memcpy(s->bytes,input.data,input.size);
    CohRuntimeSnapshotPins pins={0};pins.asset_generation=actual.asset_generation;
    memcpy(pins.catalog_sha256,actual.catalog_sha256,32);memcpy(pins.source_sha256,actual.source_sha256,32);
    memcpy(pins.snapshot_sha256,binding->snapshot_sha256,32);memcpy(pins.run_sha256,binding->run_sha256,32);
    pins.digest=digest->sha256;pins.context=digest->context;
    CohRuntimeSnapshotBudget audit={budget->aggregate_limit,retained};
    CohStatus status=coh_runtime_snapshot_audit(bytes,(CohBytes){s->bytes,s->size},&pins,&audit,cancel,&s->report);
    if(status==COH_OK)status=coh_catalog_owner_retain(catalog);
    if(status!=COH_OK){free(s->bytes);free(s);return status;}
    s->catalog=catalog;*out=s;return COH_OK;
}
CohStatus coh_catalog_snapshot_view(const CohCatalogSnapshot *s,CohBytes *bytes,
    CohCatalogSnapshotBinding *binding,CohRuntimeSnapshotReport *report){
    if(!s||!bytes||!binding||!report)return COH_INVALID;
    *bytes=(CohBytes){s->bytes,s->size};*binding=s->binding;*report=s->report;return COH_OK;
}
