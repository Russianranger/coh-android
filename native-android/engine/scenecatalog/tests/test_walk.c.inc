typedef struct {CohBytes input;uint32_t files,slots,records,holes,tombstones,current,next,last_slot;size_t callbacks,cancel;} WalkControl;
static CohStatus walk_file(void *context,const CohCatalogFileView *v){
    WalkControl *c=context;CHECK(v->index==c->files&&v->generation==7&&v->name&&*v->name);
    CHECK(v->records<=v->slots);c->current=v->index;c->next=0;c->last_slot=UINT32_MAX;c->files++;c->callbacks++;
    return c->cancel==c->callbacks?COH_CANCELLED:COH_OK;
}
static CohStatus walk_slot(void *context,const CohCatalogSlotView *v){
    WalkControl *c=context;CHECK(v->catalog.data==c->input.data&&v->catalog.size==c->input.size);
    CHECK(v->file->index==c->current&&v->slot==c->next++&&v->slot<v->file->slots);
    c->slots++;c->callbacks++;c->last_slot=v->slot;
    if(v->allocated){
        CHECK(v->definition&&v->definition->file==v->file->index&&v->definition->id==v->slot);
        CHECK(v->aligned==1&&v->wire_bits==v->wire_bytes*8&&v->record_offset+16==v->wire_offset);
        CHECK(v->wire_offset<=c->input.size&&v->wire_bytes<=c->input.size-v->wire_offset);
        const unsigned char *p=c->input.data+v->record_offset;
        CHECK(u32(p)==v->slot&&u32(p+4)==v->wire_bits&&u32(p+8)==v->wire_bytes&&u32(p+12)==v->aligned);
        c->records++;if(!v->definition->in_use)c->tombstones++;
    }else{CHECK(!v->definition&&!v->record_offset&&!v->wire_offset&&!v->wire_bytes&&!v->wire_bits&&!v->aligned);c->holes++;}
    return c->cancel==c->callbacks?COH_CANCELLED:COH_OK;
}
static CohStatus walk_invalid(void *context,const CohCatalogFileView *v){(void)context;(void)v;return (CohStatus)99;}
static void walk_tests(void){
    CohCatalogWalkBudget budget={COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,0};CohCatalogWalkReport report;
    unsigned holes=0,tombstones=0;
    for(size_t i=0;i<sizeof(catalog_fixtures)/sizeof(*catalog_fixtures);i++){
        const CatalogFixture *f=&catalog_fixtures[i];WalkControl control={0};control.input=input(f);
        CohCatalogVisitor visitor={&control,walk_file,walk_slot};peak_bytes=0;
        CHECK(coh_scenecatalog_walk(input(f),7,&budget,&visitor,&report)==COH_OK);
        CHECK(!live&&!live_bytes&&peak_bytes==report.peak_record_owned_bytes);
        CHECK(control.files==f->counts[0]&&control.records==f->counts[1]&&control.slots==f->counts[2]);
        CHECK(report.files_visited==control.files&&report.slots_visited==control.slots&&report.records_validated==control.records);
        CHECK(report.peak_working_bytes==f->bytes+COH_CATALOG_WALK_STACK_RESERVE+report.peak_record_owned_bytes);
        CHECK(report.peak_aggregate_bytes==report.peak_working_bytes&&report.peak_working_bytes<=budget.working_limit);
        CHECK(!report.failed_record_peak_unknown&&report.working_upper_bound==budget.working_limit);
        CHECK(report.catalog.owned_bytes==0&&report.catalog.offset==f->bytes&&report.catalog.status==COH_OK);
        holes+=control.holes;tombstones+=control.tombstones;
    }
    CHECK(holes&&tombstones);const CatalogFixture *f=fixture(2);WalkControl control={0};control.input=input(f);
    CohCatalogVisitor visitor={&control,walk_file,walk_slot};
    CHECK(coh_scenecatalog_walk(input(f),7,&budget,NULL,&report)==COH_OK);size_t exact=report.peak_working_bytes;
    budget.working_limit=exact;CHECK(coh_scenecatalog_walk(input(f),7,&budget,NULL,&report)==COH_OK);
    budget.working_limit--;CHECK(coh_scenecatalog_walk(input(f),7,&budget,NULL,&report)==COH_LIMIT);CHECK(!live&&!live_bytes);
    budget.working_limit=COH_CATALOG_MEMORY_MAX;budget.retained_bytes=1024*1024;budget.aggregate_limit=exact+budget.retained_bytes;
    CHECK(coh_scenecatalog_walk(input(f),7,&budget,NULL,&report)==COH_OK&&report.peak_aggregate_bytes==budget.aggregate_limit);
    budget.aggregate_limit--;CHECK(coh_scenecatalog_walk(input(f),7,&budget,NULL,&report)==COH_LIMIT);CHECK(!live&&!live_bytes);
    budget.retained_bytes=SIZE_MAX;CHECK(coh_scenecatalog_walk(input(f),7,&budget,NULL,&report)==COH_LIMIT);
    budget=(CohCatalogWalkBudget){COH_CATALOG_MEMORY_MAX+1,COH_SG_TRANSACTION_MAX,0};
    CHECK(coh_scenecatalog_walk(input(f),7,&budget,NULL,&report)==COH_INVALID);
    budget=(CohCatalogWalkBudget){COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX+1,0};
    CHECK(coh_scenecatalog_walk(input(f),7,&budget,NULL,&report)==COH_INVALID);
    budget=(CohCatalogWalkBudget){COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,0};
    CHECK(coh_scenecatalog_walk(input(f),7,NULL,NULL,&report)==COH_INVALID);
    /* Budget refusal must precede any preflight access to the input span. */
    CHECK(coh_scenecatalog_walk((CohBytes){(const unsigned char *)(uintptr_t)1,COH_CATALOG_MEMORY_MAX},7,&budget,NULL,&report)==COH_LIMIT);
    CHECK(report.catalog.offset==0&&!report.working_upper_bound);
    for(size_t n=0;n<f->bytes;n++){
        control=(WalkControl){0};control.input=input(f);
        CHECK(coh_scenecatalog_walk((CohBytes){f->catalog,n},7,&budget,&visitor,&report)!=COH_OK);
        CHECK(!control.callbacks&&!live&&!live_bytes);
    }
    for(size_t i=0;i<sizeof(catalog_fixtures)/sizeof(*catalog_fixtures);i++){
        const CatalogFixture *cancel_fixture=&catalog_fixtures[i];if(cancel_fixture->which>=20)continue;
        for(size_t n=1;n<=cancel_fixture->counts[0]+cancel_fixture->counts[2];n++){
            control=(WalkControl){0};control.input=input(cancel_fixture);control.cancel=n;
            CHECK(coh_scenecatalog_walk(control.input,7,&budget,&visitor,&report)==COH_CANCELLED);
            CHECK(control.callbacks==n&&!live&&!live_bytes);
            CHECK(report.catalog.file==control.current&&report.catalog.slot==control.last_slot&&!report.failed_record_peak_unknown);
        }
    }
    CohCatalogVisitor invalid={NULL,walk_invalid,NULL};CHECK(coh_scenecatalog_walk(input(f),7,&budget,&invalid,&report)==COH_INVALID);
    unsigned failures=0;
    for(size_t n=1;n<64;n++){
        calls=0;fail_at=n;CohStatus status=coh_scenecatalog_walk(input(f),7,&budget,NULL,&report);fail_at=0;
        CHECK(!live&&!live_bytes);if(status==COH_OK)break;CHECK(status==COH_LIMIT&&report.failed_record_peak_unknown);
        CHECK(report.working_upper_bound==budget.working_limit&&report.aggregate_upper_bound==budget.working_limit);failures++;
    }CHECK(failures>=3);
    unsigned char *bad=malloc(f->bytes);CHECK(bad);memcpy(bad,f->catalog,f->bytes);
    /* Valid envelope/name checksum but malformed last body flag, after callbacks. */
    bad[f->bytes-1]=2;CohCatalogReport pre;
    CHECK(coh_scenecatalog_preflight((CohBytes){bad,f->bytes},7,&pre)==COH_OK);
    control=(WalkControl){0};control.input=(CohBytes){bad,f->bytes};
    CHECK(coh_scenecatalog_walk(control.input,7,&budget,&visitor,&report)!=COH_OK);
    CHECK(control.callbacks>0&&live==1&&live_bytes==f->bytes); /* caller must discard its staged events */
    __wrap_free(bad);CHECK(!live&&!live_bytes);
}
