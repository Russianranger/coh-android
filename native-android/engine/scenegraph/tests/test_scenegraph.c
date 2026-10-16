#include "coh_scenegraph.h"
#include "coh_scene_metadata.h"
#include "../../scenecatalog/coh_scenecatalog.h"
#include <assert.h>
#include <math.h>
#include <float.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scenegraph_fixtures.h"
static unsigned checks;
static size_t live_allocations, allocation_calls, fail_at, live_bytes, peak_bytes;
void *__real_malloc(size_t);
void *__real_calloc(size_t,size_t);
void __real_free(void *);
typedef struct {void *p;size_t n;} Allocation;
static Allocation allocations[131072];
static size_t allocation_index(void *p){return ((uintptr_t)p>>4u)%131072u;}
static void track(void *p,size_t n){
    if(!p)return;
    size_t i=allocation_index(p);while(allocations[i].p&&allocations[i].p!=(void *)(uintptr_t)1)i=(i+1)%131072;
    allocations[i]=(Allocation){p,n};live_allocations++;live_bytes+=n;if(live_bytes>peak_bytes)peak_bytes=live_bytes;
}
void *__wrap_malloc(size_t n){allocation_calls++;if(fail_at&&allocation_calls==fail_at)return NULL;void *p=__real_malloc(n);track(p,n);return p;}
void *__wrap_calloc(size_t n,size_t z){allocation_calls++;if(fail_at&&allocation_calls==fail_at)return NULL;void *p=__real_calloc(n,z);track(p,n*z);return p;}
void coh_lookup_test_fail_next(void){fail_at=allocation_calls+1;}
void coh_compact_test_fail_next(void){fail_at=allocation_calls+1;}
unsigned coh_scene_compact_tests(CohBytes,uint32_t);
unsigned coh_scene_lookup_tests(void);
void __wrap_free(void *p){if(p){size_t i=allocation_index(p);while(allocations[i].p!=p){assert(allocations[i].p);i=(i+1)%131072;}assert(live_allocations);live_allocations--;live_bytes-=allocations[i].n;allocations[i].p=(void *)(uintptr_t)1;__real_free(p);}}
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed %s:%d: %s\n",__FILE__,__LINE__,#x);abort();}}while(0)
typedef struct {int missing_file,missing_asset,bad_checksum,bad_generation,duplicate,cycle,missing_child,bad_matrix,cancel,extra_tombstone;unsigned imported,assets;} Control;
static CohSgDefinition imported_def[2];static CohSgChild imported_child;
static CohStatus load_file(void *context,const char *name,uint32_t checksum,uint32_t generation,CohSgImportedFile *out) {
    Control *c=context;c->imported++;if(c->cancel)return COH_CANCELLED;if(c->missing_file)return COH_NOT_FOUND;
    *out=(CohSgImportedFile){name,checksum,generation,NULL,0};
    if(c->bad_checksum)out->bounds_checksum++;
    if(c->bad_generation)out->asset_generation++;
    memset(imported_def,0,sizeof(imported_def));memset(&imported_child,0,sizeof(imported_child));
    if(strstr(name,"oracle_saved")){
        imported_def[0].in_use=1;strcpy(imported_def[0].name,"oracle_saved_library");
        out->definitions=imported_def;out->definition_count=1;
        if(c->extra_tombstone){imported_def[1].id=1;out->definition_count=2;}
        if(c->duplicate){imported_def[1]=imported_def[0];imported_def[1].id=1;out->definition_count=2;}
        if(c->cycle||c->missing_child||c->bad_matrix){
            imported_def[0].children=&imported_child;imported_def[0].child_count=1;
            strcpy(imported_child.name,c->missing_child?"missing":"oracle_saved_library");
            if(c->bad_matrix)imported_child.matrix[0][0]=NAN;
        }
    }
    return COH_OK;
}
static CohStatus load_asset(void *context,CohSgAssetKind kind,const char *name,uint32_t generation){Control *c=context;(void)kind;(void)name;CHECK(generation==7);c->assets++;return c->missing_asset?COH_NOT_FOUND:COH_OK;}
static CohRepReader reader(const Fixture *f) {
    CohRepReader r;uint32_t command;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->data,f->bytes},f->bits,(int)f->aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
    CHECK(coh_rep_pack(&r,1,&command)==COH_OK);CHECK(command==(f->legacy?11u:6u));return r;
}
static const Fixture *fixture(unsigned which,unsigned aligned,unsigned legacy) {
    for(size_t i=0;i<sizeof(fixtures)/sizeof(*fixtures);i++)if(fixtures[i].which==which&&fixtures[i].aligned==aligned&&fixtures[i].legacy==legacy)return &fixtures[i];
    abort();
}
static CohStatus apply(CohSceneGraph **g,const Fixture *f,Control *control,CohSgFailure *failure) {
    CohRepReader r=reader(f);unsigned char before[sizeof(r)];memcpy(before,&r,sizeof(r));CohSceneGraph *old=*g;CohSgImports imports={control,load_file,load_asset,7};
    uint32_t generation=*g?(*g)->generation+1:1;
    CohStatus status=coh_scenegraph_apply(g,&r,&imports,generation,failure);
    if(status!=COH_OK){CHECK(*g==old);CHECK(memcmp(&r,&before,sizeof(r))==0);}else{CHECK(r.cursor==f->bits);CHECK((*g)->generation==generation);CHECK((*g)->owned_bytes<=COH_SG_MEMORY_MAX);}
    return status;
}
static CohRepReader stress_reader(void){
    CohRepReader r;uint32_t command;
    CHECK(coh_rep_reader_bounded(&r,(CohBytes){stress_wire,sizeof(stress_wire)},stress_wire_bits,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
    CHECK(coh_rep_pack(&r,1,&command)==COH_OK&&command==6);return r;
}
static size_t stress_graph_bytes,stress_candidate_peak,stress_aggregate_peak;
static unsigned stress_controls;
static void stress(void){
    CohSceneCatalog *catalog=NULL;CohCatalogReport cr;CohSceneGraph *g=NULL;CohSgFailure failure;CohSgMemoryReport report;
    CHECK(coh_scenecatalog_load(&catalog,(CohBytes){stress_catalog,sizeof(stress_catalog)},7,&cr)==COH_OK);
    CHECK(cr.files==508&&cr.definitions==12192&&cr.children==36567&&cr.source_active_roots==33);
    CHECK(live_bytes==cr.owned_bytes);
    CohSgImports imports={catalog,coh_scenecatalog_file,NULL,7};
    CohSgBudget budget={COH_SG_TRANSACTION_MAX,cr.owned_bytes+sizeof(stress_catalog),cr.definitions,cr.source_active_roots};
    CohRepReader r=stress_reader();CohGroupsInspection inspection;CohRepReader check=r;
    CHECK(coh_rep_groups(&check,&inspection,NULL)==COH_OK&&coh_scenecatalog_match(catalog,&inspection)==COH_OK);
    peak_bytes=live_bytes;
    CHECK(coh_scenegraph_apply_bounded(&g,&r,&imports,1,&budget,&report,&failure)==COH_OK);
    CHECK(r.cursor==stress_wire_bits&&g->definition_count==12192&&g->root_count==33&&g->active_roots==33);
    CHECK(g->definitions_crc==cr.source_defs_crc&&g->references_crc==cr.source_refs_crc);
    CHECK(report.candidate_peak_bytes==peak_bytes-cr.owned_bytes);
    CHECK(report.aggregate_peak_bytes==peak_bytes+sizeof(stress_catalog)+sizeof(stress_wire)+COH_SG_FIXED_SCRATCH_BYTES);
    CHECK(live_bytes==cr.owned_bytes+g->owned_bytes&&report.aggregate_peak_bytes<=budget.aggregate_limit);
    stress_graph_bytes=g->owned_bytes;stress_candidate_peak=report.candidate_peak_bytes;
    for(uint32_t i=0;i<g->definition_count;i++){
        CohSgDefinition *d=&g->definitions[i];uint32_t found;char mixed[COH_REP_NAME_MAX];
        CHECK(d->file==i/24&&d->id==i%24);
        CHECK(coh_scenegraph_find_definition(g,d->file,d->id,&found)==COH_OK&&found==i);
        if(d->in_use){
            snprintf(mixed,sizeof(mixed),"object_library/CATALOG_STRESS_%05u",i);
            CHECK(coh_scenegraph_find_name(g,mixed,&found)==COH_OK&&found==i);
            for(uint32_t j=0;j<d->child_count;j++){CHECK(d->children[j].resolved==12191);CHECK(d->children[j].matrix[0][0]==1);}
        }
    }
    for(uint32_t i=0;i<g->root_count;i++){uint32_t found;CHECK(coh_scenegraph_find_root(g,g->roots[i].id,&found)==COH_OK&&found==i);CHECK(g->roots[i].resolved==i*24);}
    /* New-world replacement accounts for simultaneously retained catalog, old
     * graph, candidate, transient indexes/DFS scratch and both input buffers. */
    size_t prior_bytes=g->owned_bytes;peak_bytes=live_bytes;r=stress_reader();
    CHECK(coh_scenegraph_apply_bounded(&g,&r,&imports,2,&budget,&report,&failure)==COH_OK);
    CHECK(report.prior_bytes==prior_bytes&&report.aggregate_peak_bytes==peak_bytes+sizeof(stress_catalog)+sizeof(stress_wire)+COH_SG_FIXED_SCRATCH_BYTES);
    CHECK(report.aggregate_peak_bytes<=COH_SG_TRANSACTION_MAX);stress_aggregate_peak=report.aggregate_peak_bytes;
    /* Refuse one byte below measured peak, malformed external reservations and
     * adversarial preallocation hints without changing any published bytes. */
    CohSceneGraph *old=g;unsigned char snapshot[sizeof(*g)];memcpy(snapshot,g,sizeof(*g));size_t retained=live_bytes;
    for(unsigned kind=0;kind<6;kind++){
        CohSgBudget bad=budget;r=stress_reader();unsigned char before[sizeof(r)];memcpy(before,&r,sizeof(r));
        if(kind==0)bad.aggregate_limit=stress_aggregate_peak-1;
        if(kind==1)bad.external_bytes=SIZE_MAX;
        if(kind==2)bad.aggregate_limit=COH_SG_TRANSACTION_MAX+1u;
        if(kind==3)bad.reserve_definitions=COH_SG_DEFS_MAX+1u;
        if(kind==4)bad.reserve_roots=COH_SG_ROOTS_MAX+1u;
        if(kind==5)bad.aggregate_limit=bad.external_bytes+sizeof(stress_wire)+g->owned_bytes;
        CHECK(coh_scenegraph_apply_bounded(&g,&r,&imports,3,&bad,&report,&failure)!=COH_OK);
        CHECK(g==old&&memcmp(g,&snapshot,sizeof(snapshot))==0&&memcmp(&r,&before,sizeof(r))==0&&live_bytes==retained);stress_controls++;
    }
    /* Fail representative growth/import/resolve allocations across large world
     * preparation. Small-world tests exhaust every allocation separately. */
    const size_t points[]={1,2,3,4,5,6,7,31,511,4096,16000,24000};
    for(size_t i=0;i<sizeof(points)/sizeof(*points);i++){
        r=stress_reader();unsigned char before[sizeof(r)];memcpy(before,&r,sizeof(r));allocation_calls=0;fail_at=points[i];
        CohStatus status=coh_scenegraph_apply_bounded(&g,&r,&imports,3,&budget,&report,&failure);fail_at=0;
        CHECK(status==COH_LIMIT&&g==old&&live_bytes==retained&&memcmp(g,&snapshot,sizeof(snapshot))==0&&memcmp(&r,&before,sizeof(r))==0);stress_controls++;
    }
    /* Graph retains all consumed catalog records after catalog release. */
    coh_scenecatalog_free(catalog);CHECK(live_bytes==g->owned_bytes);
    CHECK(strcmp(g->definitions[12191].name,"catalog_stress_12191")==0&&g->definitions[0].children[0].resolved==12191);
    coh_scenegraph_free(g);CHECK(live_allocations==0&&live_bytes==0);
}
static unsigned metadata_checks,metadata_truncations;
static void metadata(void){
    unsigned before_checks=checks;
    for(size_t i=0;i<sizeof(metadata_fixtures)/sizeof(*metadata_fixtures);i++){
        const MetadataFixture *f=&metadata_fixtures[i];CohSgDefinition d={0};CohRepReader r;size_t owned=0;
        CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->wire,f->bytes},f->bits,(int)f->aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
        CHECK(coh_scenegraph_definition_read(&d,&r,0,COH_SG_MEMORY_MAX,&owned)==COH_OK&&r.cursor==r.bits);
        CohSceneGraph g={0};g.generation=19;g.asset_generation=7;g.definition_count=1;g.definitions=&d;
        CohSgMetadata m={0};size_t allocations_before=allocation_calls;
        CHECK(coh_scenegraph_metadata(&g,0,&m)==COH_OK&&allocation_calls==allocations_before);
        CHECK(m.scene_generation==19&&m.asset_generation==7&&m.file==0&&m.slot==d.id);
        METADATA_COMPARE_U32(&m,f,CHECK);METADATA_COMPARE_FLOAT(&m,f,CHECK);METADATA_COMPARE_STRING(&m,f,CHECK);
        CHECK(memcmp(m.color,f->colors,8)==0);
        CHECK(m.unresolved_requirements&COH_SG_META_BOUNDS_LOD);
        CohSgPropertyCursor cursor;CohSgProperty prop={0};CHECK(coh_scenegraph_property_begin(&m,&cursor)==COH_OK);
        if(f->which==0||f->which==5||f->which==6){
            CHECK(m.property_count==2&&m.swap_count==2&&m.has_geometry==1);
            CHECK(m.unresolved_requirements==(COH_SG_META_BOUNDS_LOD|COH_SG_META_GEOMETRY|COH_SG_META_TEXTURES|COH_SG_META_COMPOSITE|COH_SG_META_PROPERTIES|COH_SG_META_TYPE|COH_SG_META_LIGHTING|COH_SG_META_FOG|COH_SG_META_CUBEMAP|COH_SG_META_SOUND|COH_SG_META_VOLUME|COH_SG_META_BEACON|COH_SG_META_VISIBILITY|COH_SG_META_MODEL_TRICKS));
            CHECK(coh_scenegraph_property_next(&cursor,&prop)==COH_OK&&prop.type==0);
            CHECK(strcmp(prop.name,f->which==6?"TexWordLayout":"OracleString")==0);
            if(f->which==6)CHECK(strcmp(prop.value,"layouts/original_fixture.texword")==0);else CHECK(strlen(prop.value)==192);
            CHECK(coh_scenegraph_property_next(&cursor,&prop)==COH_OK&&prop.type==1&&strcmp(prop.name,"OracleRadius")==0&&strcmp(prop.value,"12.5")==0);
        }else CHECK(m.property_count==0);
        unsigned char last[sizeof(prop)],last_cursor[sizeof(cursor)],old[sizeof(m)];
        memcpy(last,&prop,sizeof(prop));memcpy(last_cursor,&cursor,sizeof(cursor));
        CHECK(coh_scenegraph_property_next(&cursor,&prop)==COH_NOT_FOUND);
        CHECK(memcmp(&prop,last,sizeof(prop))==0&&memcmp(&cursor,last_cursor,sizeof(cursor))==0);
        /* Snapshot object bytes immediately before the rejected operation.
         * Struct assignment need not preserve padding; successful decodes need
         * not reproduce previous padding even when all member values agree. */
        size_t complete=d.wire_bits;
        for(size_t bit=0;bit<complete;bit++){
            d.wire_bits=bit;memcpy(old,&m,sizeof(m));
            CHECK(coh_scenegraph_metadata(&g,0,&m)!=COH_OK);
            CHECK(memcmp(&m,old,sizeof(m))==0);metadata_truncations++;
        }
        d.wire_bits=complete;CHECK(coh_scenegraph_metadata(&g,0,&m)==COH_OK);
        d.mod_time++;memcpy(old,&m,sizeof(m));
        CHECK(coh_scenegraph_metadata(&g,0,&m)==COH_STATE);
        CHECK(memcmp(&m,old,sizeof(m))==0);d.mod_time--;
        g.asset_generation=0;memcpy(old,&m,sizeof(m));
        CHECK(coh_scenegraph_metadata(&g,0,&m)==COH_INVALID);
        CHECK(memcmp(&m,old,sizeof(m))==0);g.asset_generation=7;
        memcpy(old,&m,sizeof(m));CHECK(coh_scenegraph_metadata(&g,1,&m)==COH_INVALID);
        CHECK(memcmp(&m,old,sizeof(m))==0);
        g.definitions=NULL;memcpy(old,&m,sizeof(m));
        CHECK(coh_scenegraph_metadata(&g,0,&m)==COH_INVALID);
        CHECK(memcmp(&m,old,sizeof(m))==0);g.definitions=&d;
        if(d.swap_count){
            CohSgSwap *swaps=d.swaps;d.swaps=NULL;memcpy(old,&m,sizeof(m));
            CHECK(coh_scenegraph_metadata(&g,0,&m)==COH_INVALID);
            CHECK(memcmp(&m,old,sizeof(m))==0);d.swaps=swaps;
        }
        if(m.property_count){
            CHECK(coh_scenegraph_property_begin(&m,&cursor)==COH_OK);cursor.reader.bits=cursor.reader.cursor;
            memcpy(last_cursor,&cursor,sizeof(cursor));memcpy(last,&prop,sizeof(prop));
            CHECK(coh_scenegraph_property_next(&cursor,&prop)!=COH_OK);
            CHECK(memcmp(&prop,last,sizeof(prop))==0&&memcmp(&cursor,last_cursor,sizeof(cursor))==0);
        }
        CHECK(allocation_calls==allocations_before);
        coh_scenegraph_definition_dispose(&d);CHECK(!live_allocations&&!live_bytes);
    }
    /* Long properties use the existing4096-byte policy, not name length256. */
    {CohSceneGraph *g=NULL;Control c={0};CHECK(apply(&g,fixture(12,1,0),&c,NULL)==COH_OK);
     CohSgMetadata m;CohSgPropertyCursor cursor;CohSgProperty property;
     CHECK(coh_scenegraph_metadata(g,0,&m)==COH_OK&&coh_scenegraph_property_begin(&m,&cursor)==COH_OK);
     CHECK(coh_scenegraph_property_next(&cursor,&property)==COH_OK&&strlen(property.value)==1023);
     coh_scenegraph_free(g);CHECK(!live_allocations&&!live_bytes);}
    metadata_checks=checks-before_checks;
}
int main(void) {
    unsigned accepted=0,rejected=0;
    for(size_t i=0;i<sizeof(fixtures)/sizeof(*fixtures);i++) {
        const Fixture *f=&fixtures[i];CohSceneGraph *g=NULL;Control control={0};CohSgFailure failure;
        if(f->which==3)CHECK(apply(&g,fixture(2,f->aligned,f->legacy),&control,&failure)==COH_OK);
        if(f->which==4)CHECK(apply(&g,fixture(11,f->aligned,f->legacy),&control,&failure)==COH_OK);
        CohStatus want=f->which==5?COH_LIMIT:f->which==6?COH_UNSUPPORTED:COH_OK;
        CohStatus got=apply(&g,f,&control,&failure);
        if(got!=want){fprintf(stderr,"fixture %s case %u expected %u got %u stage %u bit %zu\n",f->name,f->which,want,got,failure.stage,failure.bit);abort();}
        CHECK(got==want);
        if(got==COH_OK){accepted++;
            if(f->which==2||f->which==8||f->which==12){CHECK(g->definition_count==5);CHECK(g->definitions[3].file==1);CHECK(g->definitions[3].in_use);CHECK(g->definitions[0].children[1].resolved==3);CHECK(g->active_roots==3);CHECK(g->definitions[0].wire_bytes>100);CHECK(control.assets>0);CHECK(strcmp(g->definitions[0].geometry,"oracle_geometry__source_fixture")==0);CHECK(strcmp(g->definitions[0].textures[0],"oracle_texture_a")==0);CHECK(strcmp(g->definitions[0].textures[1],"oracle_texture_b")==0);CHECK(strcmp(g->definitions[0].swaps[0].replacement,"oracle_replacement_a")==0);CHECK(g->definitions[0].swaps[1].composite==1);CHECK(g->definitions[0].children[0].matrix[0][1]==0.125f);CHECK(g->definitions[0].children[1].matrix[3][2]==3.125f);}
            if(f->which==4){CHECK(g->definition_count==3);CHECK(g->definitions[1].in_use==0);CHECK(g->active_roots==2);CHECK(g->roots[1].active==0);CHECK(g->roots[3].resolved==2);}
            if(f->which==7)for(unsigned root=0;root<3;root++)for(unsigned row=0;row<4;row++)for(unsigned col=0;col<3;col++)CHECK(fabsf(g->roots[root].matrix[row][col]-source_matrices[root][row][col])<0.000002f);
        }else rejected++;
        coh_scenegraph_free(g);
    }
    /* Every dependency failure preserves already published topology and cursor. */
    for(unsigned kind=0;kind<10;kind++) {
        Control control={0};CohSceneGraph *g=NULL;CohSgFailure f;
        CHECK(apply(&g,fixture(1,1,0),&control,&f)==COH_OK);
        switch(kind){case 0:control.missing_file=1;break;case 1:control.missing_asset=1;break;case 2:control.bad_checksum=1;break;case 3:control.bad_generation=1;break;case 4:control.duplicate=1;break;case 5:control.cycle=1;break;case 6:control.missing_child=1;break;case 7:control.bad_matrix=1;break;case 8:control.cancel=1;break;case 9:control.extra_tombstone=1;break;}
        CHECK(apply(&g,fixture(2,1,0),&control,&f)!=COH_OK);CHECK(g->active_roots==1);CHECK(strcmp(g->definitions[0].name,"oracle_root")==0);
        coh_scenegraph_free(g);
    }
    /* Fail each owned allocation in fresh and incremental preparation. The
     * previous graph object and owned arrays stay byte-identical and leak-free. */
    unsigned allocation_failures=0;
    for(unsigned incremental=0;incremental<2;incremental++) {
        int completed=0;
        for(size_t fail=1;fail<256;fail++) {
            Control c={0};CohSceneGraph *g=NULL;CohSgFailure failure;
            if(incremental)CHECK(apply(&g,fixture(2,1,0),&c,&failure)==COH_OK);
            size_t retained=live_allocations;CohSceneGraph *prior=g;unsigned char snapshot[sizeof(*g)];CohSgDefinition defs[5];
            if(g){memcpy(snapshot,g,sizeof(*g));memcpy(defs,g->definitions,sizeof(defs));}
            allocation_calls=0;fail_at=fail;
            CohStatus status=apply(&g,fixture(incremental?3:2,1,0),&c,&failure);
            fail_at=0;
            if(status==COH_OK){completed=1;coh_scenegraph_free(g);CHECK(live_allocations==0);break;}
            CHECK(status==COH_LIMIT);CHECK(g==prior);CHECK(live_allocations==retained);
            if(g){CHECK(memcmp(&snapshot,g,sizeof(snapshot))==0);CHECK(memcmp(defs,g->definitions,sizeof(defs))==0);}
            allocation_failures++;coh_scenegraph_free(g);CHECK(live_allocations==0);
        }
        CHECK(completed);
    }
    /* Truncation at every logical bit of minimal fixture stays transactional. */
    {const Fixture *f=fixture(1,0,0);Control c={0};CohSceneGraph *g=NULL;CohSgImports imports={&c,load_file,load_asset,7};
     for(size_t bits=0;bits<f->bits;bits++){CohRepReader r=reader(f);r.bits=bits;unsigned char old[sizeof(r)];memcpy(old,&r,sizeof(r));CHECK(coh_scenegraph_apply(&g,&r,&imports,1,NULL)!=COH_OK);CHECK(g==NULL);CHECK(memcmp(&r,&old,sizeof(r))==0);}}
    /* CRC mismatch, generation mismatch, missing previous incremental world. */
    {Control c={0};CohSceneGraph *g=NULL;CohSgFailure failure;CHECK(apply(&g,fixture(3,1,0),&c,&failure)==COH_STATE);
     const Fixture *f=fixture(1,1,0);unsigned char *bad=malloc(f->bytes);CHECK(bad!=NULL);memcpy(bad,f->data,f->bytes);bad[f->bytes-1]^=1;
     Fixture changed=*f;changed.data=bad;CHECK(apply(&g,&changed,&c,&failure)==COH_INVALID);CHECK(failure.stage==COH_SG_CHECKSUM);free(bad);
     CHECK(apply(&g,f,&c,&failure)==COH_OK);CohRepReader r=reader(f);CohSgImports imports={&c,load_file,load_asset,7};
     CHECK(coh_scenegraph_apply(&g,&r,&imports,4,&failure)==COH_STATE);
     CHECK(coh_scenegraph_apply(&g,&r,&imports,0,&failure)==COH_INVALID);imports.generation=0;
     CHECK(coh_scenegraph_apply(&g,&r,&imports,2,&failure)==COH_INVALID);imports.generation=7;g->generation=UINT32_MAX;
     CHECK(coh_scenegraph_apply(&g,&r,&imports,1,&failure)==COH_STATE);g->generation=1;
     r=reader(fixture(3,1,0));imports.generation=8;CHECK(coh_scenegraph_apply(&g,&r,&imports,2,&failure)==COH_STATE);coh_scenegraph_free(g);}
    /* The map identity repeated in prefix and file0 must agree independently
     * of names-only footer checksums. Byte-aligned fixture permits an exact
     * bounded first occurrence mutation. */
    {const Fixture *f=fixture(1,1,0);unsigned char *bad=malloc(f->bytes);CHECK(bad!=NULL);memcpy(bad,f->data,f->bytes);
     const char *needle="maps/oracle_world.txt";size_t at=0;for(;at+strlen(needle)<=f->bytes;at++)if(memcmp(bad+at,needle,strlen(needle))==0)break;
     CHECK(at+strlen(needle)<=f->bytes);bad[at]='X';Fixture changed=*f;changed.data=bad;Control c={0};CohSceneGraph *g=NULL;CohSgFailure failure;
     CHECK(apply(&g,&changed,&c,&failure)==COH_INVALID);CHECK(failure.stage==COH_SG_DECODE);free(bad);}
    /* Owned data survives importer mutation and input release; source original
     * transform composition plus alias/overflow boundary. */
    {CohSceneGraph *g=NULL;Control c={0};CHECK(apply(&g,fixture(2,1,0),&c,NULL)==COH_OK);memset(imported_def,0,sizeof(imported_def));CHECK(strcmp(g->definitions[3].name,"oracle_saved_library")==0);coh_scenegraph_free(g);}
    {const Fixture *f=fixture(2,1,0);Fixture owned_fixture=*f;unsigned char *owned_packet=malloc(f->bytes);CHECK(owned_packet!=NULL);memcpy(owned_packet,f->data,f->bytes);owned_fixture.data=owned_packet;
     CohSceneGraph *g=NULL;Control c={0};CHECK(apply(&g,&owned_fixture,&c,NULL)==COH_OK);free(owned_packet);
     CHECK(g->definitions[0].wire_bytes>100);unsigned char first=g->definitions[0].wire[0];CHECK(first==1);coh_scenegraph_free(g);}
    {CohSgMatrix p={{1,0,0},{0,1,0},{0,0,1},{3,4,5}},c={{2,0,0},{0,2,0},{0,0,2},{1,2,3}},out;
     CHECK(coh_scenegraph_compose((const float (*)[3])p,(const float (*)[3])c,out)==COH_OK);CHECK(out[3][0]==4&&out[3][1]==6&&out[3][2]==8);CHECK(out[0][0]==2);
     CHECK(coh_scenegraph_compose((const float (*)[3])p,(const float (*)[3])c,p)==COH_OK);CHECK(memcmp(p,out,sizeof(out))==0);
     c[0][0]=INFINITY;CHECK(coh_scenegraph_compose((const float (*)[3])p,(const float (*)[3])c,out)==COH_INVALID);CHECK(memcmp(p,out,sizeof(out))==0);}
    /* Noncommuting basis transforms: parent rotates Z +90 and translates,
     * child rotates X +90 and translates. Columns below are independent
     * transformed unit axes and origin; reversed order has different origin. */
    {CohSgMatrix p={{0,1,0},{-1,0,0},{0,0,1},{10,20,30}},c={{1,0,0},{0,0,1},{0,-1,0},{1,2,3}},out;
     CohSgMatrix expected={{0,1,0},{0,0,1},{1,0,0},{8,21,33}};
     CHECK(coh_scenegraph_compose((const float (*)[3])p,(const float (*)[3])c,out)==COH_OK);CHECK(memcmp(out,expected,sizeof(out))==0);
     p[0][0]=FLT_MAX;c[0][0]=2;CHECK(coh_scenegraph_compose((const float (*)[3])p,(const float (*)[3])c,out)==COH_INVALID);CHECK(memcmp(out,expected,sizeof(out))==0);}
    CHECK(live_allocations==0);CHECK(allocation_failures>0);
    /* A smaller incremental file table must reject before copying old files
     * into the smaller candidate allocation. */
    {CohSceneGraph *g=NULL;Control c={0};CohSgFailure failure;
     CHECK(apply(&g,fixture(2,1,0),&c,&failure)==COH_OK);
     CHECK(apply(&g,fixture(4,1,0),&c,&failure)==COH_UNSUPPORTED);
     CHECK(g->file_count==3);coh_scenegraph_free(g);CHECK(!live_bytes);}
    stress();
    metadata();
    unsigned lookup_checks=coh_scene_lookup_tests();checks+=lookup_checks;CHECK(live_allocations==0);
    unsigned compact_checks=coh_scene_compact_tests((CohBytes){stress_catalog,sizeof(stress_catalog)},7);checks+=compact_checks;CHECK(live_allocations==0);
    printf("{\"passed\":true,\"checks\":%u,\"allocation_failure_points\":%u,\"source_fixtures_accepted\":%u,\"source_fixtures_rejected\":%u,\"stress_controls\":%u,\"stress_definitions\":12192,\"stress_children\":36567,\"stress_graph_bytes\":%zu,\"stress_candidate_peak_bytes\":%zu,\"stress_aggregate_peak_bytes\":%zu,\"lookup_checks\":%u,\"compact_checks\":%u,\"metadata_checks\":%u,\"metadata_truncations\":%u,\"live_world\":false}\n",checks,allocation_failures,accepted,rejected,stress_controls,stress_graph_bytes,stress_candidate_peak,stress_aggregate_peak,lookup_checks,compact_checks,metadata_checks,metadata_truncations);
    return 0;
}
