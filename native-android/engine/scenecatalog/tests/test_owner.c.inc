/* Deterministic exact-byte fixture allowlist, not a production SHA provider.
 * Python hashlib hashes the unchanged original producer's fixtures. */
typedef struct {unsigned calls;CohStatus fail;} OwnerDigestControl;
static CohStatus fixture_digest(void *context,CohBytes bytes,uint8_t out[32]){
    OwnerDigestControl *control=context;control->calls++;
    if(control->fail)return control->fail;
    for(size_t i=0;i<sizeof(catalog_fixtures)/sizeof(*catalog_fixtures);i++){
        const CatalogFixture *f=&catalog_fixtures[i];
        if(bytes.size==f->bytes&&!memcmp(bytes.data,f->catalog,bytes.size)){memcpy(out,f->sha256,32);return COH_OK;}
    }return COH_STATE;
}
static CohCatalogBinding owner_binding(const CatalogFixture *f){
    CohCatalogBinding b={0};b.owner_generation=1;b.catalog_generation=7;b.asset_generation=9;b.map_generation=11;
    memcpy(b.catalog_sha256,f->sha256,32);memset(b.source_sha256,1,32);memset(b.inventory_sha256,2,32);memset(b.map_sha256,3,32);return b;
}
static CohStatus owner_slot_compare(void *context,const CohCatalogSlotView *v){
    CohCatalogOwner *o=context;CohCatalogRecordIdentity id;CohCatalogFileView f;
    CHECK(coh_catalog_owner_record(o,v->file->index,v->slot,&id)==COH_OK);
    CHECK(id.file==v->file->index&&id.slot==v->slot&&id.allocated==v->allocated);
    CHECK(id.record_offset==v->record_offset&&id.wire_offset==v->wire_offset&&id.wire_bytes==v->wire_bytes);
    CHECK(coh_catalog_owner_file(o,v->file->index,&f)==COH_OK&&f.index==v->file->index&&f.slots==v->file->slots&&f.records==v->file->records);
    CHECK(f.bounds_checksum==v->file->bounds_checksum&&!strcmp(f.name,v->file->name));
    CHECK(id.in_use==(v->definition?v->definition->in_use:0));
    CHECK(id.child_count==(v->definition?v->definition->child_count:0));
    CHECK(!strcmp(id.name,v->definition&&v->definition->in_use?v->definition->name:""));
    return COH_OK;
}
static void owner_tests(void){
    CohCatalogOwnerBudget budget={COH_CATALOG_MEMORY_MAX,COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,0};
    OwnerDigestControl control={0};CohCatalogDigest digest={&control,fixture_digest};CohCatalogOwnerReport report;
    for(size_t i=0;i<sizeof(catalog_fixtures)/sizeof(*catalog_fixtures);i++){
        const CatalogFixture *f=&catalog_fixtures[i];CohCatalogBinding b=owner_binding(f),observed;CohCatalogOwner *owner=NULL;
        peak_bytes=0;CHECK(coh_catalog_owner_create(NULL,input(f),&b,&budget,&digest,&owner,&report)==COH_OK);
        CHECK(owner&&report.status==COH_OK&&live_bytes==report.owned_bytes&&report.owned_bytes==coh_catalog_owner_owned_bytes(owner));
        CHECK(report.index_bytes==(size_t)f->counts[0]*20+(size_t)f->counts[2]*8);
        CHECK(report.peak_aggregate_bytes==f->bytes+peak_bytes+COH_CATALOG_WALK_STACK_RESERVE);
        CHECK(coh_catalog_owner_binding(owner,&observed)==COH_OK&&!memcmp(&b,&observed,sizeof(b)));
        CohBytes owned;CHECK(coh_catalog_owner_bytes(owner,&owned)==COH_OK&&owned.data!=f->catalog&&owned.size==f->bytes&&!memcmp(owned.data,f->catalog,f->bytes));
        CohCatalogWalkBudget walk={COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,report.owned_bytes};
        CohCatalogVisitor visitor={owner,NULL,owner_slot_compare};CohCatalogWalkReport wr;
        CHECK(coh_scenecatalog_walk(owned,7,&walk,&visitor,&wr)==COH_OK);
        if(f->which!=20&&f->which!=21&&f->which!=22){
            CohRepReader reader=wire(f),before=reader;CohCatalogGroupsMatch match;
            CHECK(coh_catalog_owner_compare_groups(owner,&b,&reader,&match)==COH_OK&&match.mismatches==0);
            CHECK(!memcmp(&reader,&before,sizeof(reader))&&match.groups.consumed_bits==f->wire_bits);
            b.map_sha256[0]^=1;CHECK(coh_catalog_owner_compare_groups(owner,&b,&reader,&match)==COH_STATE&&match.mismatches==COH_CATALOG_MISMATCH_BINDING);b.map_sha256[0]^=1;
            reader.bits--;CHECK(coh_catalog_owner_compare_groups(owner,&b,&reader,&match)!=COH_OK);
            if(f->which==2&&f->aligned){
                unsigned char *changed=malloc(f->wire_bytes);CHECK(changed);memcpy(changed,f->wire,f->wire_bytes);
                reader=wire(f);reader.bytes.data=changed;
                changed[f->wire_bytes-8]^=1;
                CHECK(coh_catalog_owner_compare_groups(owner,&b,&reader,&match)==COH_STATE&&match.mismatches==COH_CATALOG_MISMATCH_DEFS_CRC);
                changed[f->wire_bytes-8]^=1;changed[f->wire_bytes-4]^=1;
                CHECK(coh_catalog_owner_compare_groups(owner,&b,&reader,&match)==COH_STATE&&match.mismatches==COH_CATALOG_MISMATCH_REFS_CRC);
                free(changed);
            }
        }
        CohCatalogFileView untouched={0},saved=untouched;
        CHECK(coh_catalog_owner_file(owner,f->counts[0],&untouched)==COH_NOT_FOUND&&!memcmp(&untouched,&saved,sizeof(saved)));
        CohCatalogRecordIdentity id,prior;memset(&id,0xa5,sizeof(id));memcpy(&prior,&id,sizeof(id));
        CHECK(coh_catalog_owner_record(owner,f->counts[0],0,&id)==COH_NOT_FOUND&&!memcmp(&id,&prior,sizeof(id)));
        CHECK(coh_catalog_owner_retain(owner)==COH_OK);coh_catalog_owner_release(owner);
        CHECK(coh_catalog_owner_bytes(owner,&owned)==COH_OK);coh_catalog_owner_release(owner);CHECK(!live&&!live_bytes);
    }
    const CatalogFixture *f=fixture(2);CohCatalogBinding b=owner_binding(f);CohCatalogOwner *old=NULL,*candidate=NULL;
    CHECK(coh_catalog_owner_create(NULL,input(f),&b,&budget,&digest,&old,&report)==COH_OK);
    size_t baseline=live_bytes;b.owner_generation=2;peak_bytes=baseline;
    CHECK(coh_catalog_owner_create(old,input(f),&b,&budget,&digest,&candidate,&report)==COH_OK);
    CHECK(report.previous_bytes==baseline&&report.peak_aggregate_bytes==f->bytes+peak_bytes+COH_CATALOG_WALK_STACK_RESERVE);
    size_t exact=report.peak_aggregate_bytes,owned_size=report.owned_bytes;
    CHECK(coh_catalog_owner_create(old,input(f),&b,&budget,&digest,&candidate,&report)==COH_STATE);
    coh_catalog_owner_release(candidate);candidate=NULL;CHECK(live_bytes==baseline);
    /* Every allocation refusal rolls back the new owner and all indexes. */
    unsigned rejected=0;
    for(size_t n=1;n<64;n++){
        calls=0;fail_at=n;CohStatus status=coh_catalog_owner_create(old,input(f),&b,&budget,&digest,&candidate,&report);fail_at=0;
        if(status==COH_OK){coh_catalog_owner_release(candidate);candidate=NULL;break;}
        CHECK(status==COH_LIMIT&&!candidate&&live_bytes==baseline);rejected++;
    }CHECK(rejected>=7);
    budget.aggregate_limit=exact;CHECK(coh_catalog_owner_create(old,input(f),&b,&budget,&digest,&candidate,&report)==COH_OK);coh_catalog_owner_release(candidate);candidate=NULL;
    budget.aggregate_limit--;CHECK(coh_catalog_owner_create(old,input(f),&b,&budget,&digest,&candidate,&report)==COH_LIMIT&&!candidate&&live_bytes==baseline);
    budget.aggregate_limit=COH_SG_TRANSACTION_MAX;budget.owned_limit=owned_size-1;
    CHECK(coh_catalog_owner_create(old,input(f),&b,&budget,&digest,&candidate,&report)==COH_LIMIT&&!candidate&&live_bytes==baseline);
    budget.owned_limit=COH_CATALOG_MEMORY_MAX;
    for(unsigned i=0;i<12;i++){
        CohCatalogBinding bad=b;
        switch(i){case 0:bad.owner_generation=1;break;case 1:bad.owner_generation=3;break;case 2:bad.catalog_generation=6;break;
        case 3:bad.asset_generation--;break;case 4:bad.map_generation--;break;case 5:bad.catalog_sha256[0]^=1;break;
        case 6:bad.source_sha256[0]^=1;break;case 7:bad.inventory_sha256[0]^=1;break;case 8:bad.map_sha256[0]^=1;break;
        case 9:memset(bad.source_sha256,0,32);break;case 10:memset(bad.catalog_sha256,0,32);break;case 11:bad.catalog_generation=8;break;}
        CHECK(coh_catalog_owner_create(old,input(f),&bad,&budget,&digest,&candidate,&report)==COH_STATE&&!candidate&&live_bytes==baseline);
    }
    for(size_t n=0;n<f->bytes;n++){
        CHECK(coh_catalog_owner_create(old,(CohBytes){f->catalog,n},&b,&budget,&digest,&candidate,&report)!=COH_OK&&!candidate&&live_bytes==baseline);
    }
    for(unsigned i=0;i<3;i++){
        control.fail=i==0?COH_CANCELLED:i==1?COH_LIMIT:(CohStatus)99;
        CHECK(coh_catalog_owner_create(old,input(f),&b,&budget,&digest,&candidate,&report)==(i==0?COH_CANCELLED:i==1?COH_LIMIT:COH_INVALID));
        CHECK(!candidate&&live_bytes==baseline);
    }control.fail=COH_OK;
    unsigned provider_calls=control.calls;
    CHECK(coh_catalog_owner_create(old,(CohBytes){(const uint8_t *)(uintptr_t)1,COH_CATALOG_MEMORY_MAX},&b,&budget,&digest,&candidate,&report)==COH_LIMIT&&control.calls==provider_calls);
    budget.retained_bytes=SIZE_MAX;CHECK(coh_catalog_owner_create(old,input(f),&b,&budget,&digest,&candidate,&report)==COH_LIMIT);budget.retained_bytes=0;
    /* Caller input can be destroyed immediately; all file/record views survive. */
    unsigned char *mutable=malloc(f->bytes);CHECK(mutable);memcpy(mutable,f->catalog,f->bytes);
    CHECK(coh_catalog_owner_create(old,(CohBytes){mutable,f->bytes},&b,&budget,&digest,&candidate,&report)==COH_OK);
    memset(mutable,0,f->bytes);free(mutable);coh_catalog_owner_release(old);
    CohCatalogRecordIdentity id;CHECK(coh_catalog_owner_record(candidate,0,0,&id)==COH_OK&&id.in_use&&*id.name);
    coh_catalog_owner_release(candidate);CHECK(!live&&!live_bytes);
    CHECK(coh_catalog_owner_retain(NULL)==COH_INVALID);
    b=owner_binding(f);b.map_generation=0;memset(b.map_sha256,0,32);candidate=NULL;
    CHECK(coh_catalog_owner_create(NULL,input(f),&b,&budget,&digest,&candidate,&report)==COH_OK);
    CohRepReader unbound_reader=wire(f);CohCatalogGroupsMatch match;
    CHECK(coh_catalog_owner_compare_groups(candidate,&b,&unbound_reader,&match)==COH_STATE&&match.mismatches==COH_CATALOG_MISMATCH_BINDING);
    coh_catalog_owner_release(candidate);CHECK(!live&&!live_bytes);
}
