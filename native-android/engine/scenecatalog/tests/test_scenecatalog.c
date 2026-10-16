#include "coh_scenecatalog.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "catalog_fixtures.h"
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed %s:%d: %s\n",__FILE__,__LINE__,#x);abort();}}while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void *);
typedef struct {void *p;size_t n;} Allocation;
static Allocation allocations[131072];static size_t live,live_bytes,peak_bytes,calls,fail_at;
static size_t index_(void *p){return ((uintptr_t)p>>4u)%131072u;}
static void track(void *p,size_t n){if(!p)return;size_t i=index_(p);while(allocations[i].p&&allocations[i].p!=(void *)(uintptr_t)1)i=(i+1)%131072;allocations[i]=(Allocation){p,n};live++;live_bytes+=n;if(live_bytes>peak_bytes)peak_bytes=live_bytes;}
void *__wrap_malloc(size_t n){calls++;if(fail_at&&calls==fail_at)return NULL;void *p=__real_malloc(n);track(p,n);return p;}
void *__wrap_calloc(size_t n,size_t z){calls++;if(fail_at&&calls==fail_at)return NULL;void *p=__real_calloc(n,z);track(p,n*z);return p;}
void __wrap_free(void *p){if(!p)return;size_t i=index_(p);while(allocations[i].p!=p){assert(allocations[i].p);i=(i+1)%131072;}live--;live_bytes-=allocations[i].n;allocations[i].p=(void *)(uintptr_t)1;__real_free(p);}
static CohBytes input(const CatalogFixture *f){return (CohBytes){f->catalog,f->bytes};}
static const CatalogFixture *fixture(unsigned which){for(size_t i=0;i<sizeof(catalog_fixtures)/sizeof(*catalog_fixtures);i++)if(catalog_fixtures[i].which==which&&catalog_fixtures[i].aligned==1&&!catalog_fixtures[i].legacy)return &catalog_fixtures[i];abort();}
static CohRepReader wire(const CatalogFixture *f){CohRepReader r;uint32_t command;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->wire,f->wire_bytes},f->wire_bits,(int)f->aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);CHECK(coh_rep_pack(&r,1,&command)==COH_OK&&command==(f->legacy?11u:6u));return r;}
static unsigned asset_calls;static int reject_asset;
static CohStatus asset(void *context,CohSgAssetKind kind,const char *name,uint32_t generation){(void)context;CHECK(generation==7&&kind>=1&&kind<=3&&name&&*name);asset_calls++;return reject_asset?COH_NOT_FOUND:COH_OK;}
static CohStatus apply(CohSceneCatalog *c,const CatalogFixture *f,CohSceneGraph **g){CohRepReader r=wire(f),old=r;CohSceneGraph *prior=*g;CohSgImports imports={c,coh_scenecatalog_file,asset,7};CohStatus s=coh_scenegraph_apply(g,&r,&imports,prior?prior->generation+1:1,NULL);if(s!=COH_OK){CHECK(*g==prior&&memcmp(&r,&old,sizeof(r))==0);}else CHECK(r.cursor==f->wire_bits);return s;}
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put(unsigned char *p,uint32_t n){p[0]=(unsigned char)n;p[1]=(unsigned char)(n>>8);p[2]=(unsigned char)(n>>16);p[3]=(unsigned char)(n>>24);}
int main(void){
    unsigned accepted=0,allocation_failures=0;size_t large_owned=0,large_peak=0;
    for(size_t i=0;i<sizeof(catalog_fixtures)/sizeof(*catalog_fixtures);i++){
        const CatalogFixture *f=&catalog_fixtures[i];CohSceneCatalog *c=NULL;CohCatalogReport pre,r;CohSceneGraph *g=NULL;
        CHECK(coh_scenecatalog_preflight(input(f),7,&pre)==COH_OK);
        CHECK(pre.files==f->counts[0]&&pre.definitions==f->counts[1]&&pre.slots==f->counts[2]&&pre.children==f->counts[3]&&pre.wire_bytes==f->counts[4]);
        if(f->which==22){
            CHECK(pre.children==60945);
            CHECK(pre.exceeds_graph_definitions==(pre.definitions>COH_SG_DEFS_MAX)&&pre.exceeds_graph_children==(pre.children>COH_SG_CHILDREN_MAX));
            CHECK(coh_scenecatalog_load(&c,input(fixture(1)),7,&r)==COH_OK);CohSceneCatalog *prior=c;size_t retained=live_bytes;
            CHECK(coh_scenecatalog_load(&c,input(f),7,&r)==COH_LIMIT&&c==prior&&r.stage==COH_CATALOG_DECODE);
            CHECK(live_bytes==retained&&r.owned_bytes<=COH_CATALOG_MEMORY_MAX);coh_scenecatalog_free(c);CHECK(!live&&!live_bytes);accepted++;continue;
        }
        CHECK(coh_scenecatalog_load(&c,input(f),7,&r)==COH_OK);CHECK(r.owned_bytes<=COH_CATALOG_MEMORY_MAX);CHECK(live_bytes==r.owned_bytes);
        if(f->which==20){
            CHECK(r.files==508&&r.definitions==12192&&r.slots==12192&&r.source_active_roots==33&&r.children==36567);
            CHECK(r.exceeds_graph_definitions==(r.definitions>COH_SG_DEFS_MAX)&&r.exceeds_graph_children==(r.children>COH_SG_CHILDREN_MAX));large_owned=r.owned_bytes;peak_bytes=live_bytes;
            CHECK(coh_scenecatalog_load(&c,input(f),7,&r)==COH_OK);large_peak=peak_bytes;CHECK(large_peak<=2u*COH_CATALOG_MEMORY_MAX);
            CHECK(apply(c,f,&g)==COH_LIMIT&&g==NULL);
        }else if(f->which!=21){
            CohRepReader rr=wire(f);CohGroupsInspection inspect;CHECK(coh_rep_groups(&rr,&inspect,NULL)==COH_OK);CHECK(coh_scenecatalog_match(c,&inspect)==COH_OK);
            CHECK(apply(c,f,&g)==COH_OK);CHECK(g->definitions_crc==r.source_defs_crc&&g->references_crc==r.source_refs_crc&&g->active_roots==r.source_active_roots);
            if(f->which==2||f->which==8){CohSgImportedFile file;CHECK(coh_scenecatalog_file(c,"OBJECT_LIBRARY/ORACLE_SAVED.TXT",0x11223345u,7,&file)==COH_OK);CHECK(file.definition_count==1&&strcmp(file.definitions[0].name,"oracle_saved_library")==0);CHECK(file.definitions[0].wire_bytes>0);CHECK(g->definition_count==5&&g->definitions[0].child_count==2&&g->definitions[0].swap_count==2);CHECK(strcmp(g->definitions[0].textures[1],"oracle_texture_b")==0);CHECK(g->definitions[0].children[0].matrix[0][1]==0.125f);}
        }else{CHECK(r.slots==5&&r.definitions==4);}
        coh_scenegraph_free(g);coh_scenecatalog_free(c);CHECK(!live&&!live_bytes);accepted++;
    }
    const CatalogFixture *rich=fixture(2);CohSceneCatalog *c=NULL;CohCatalogReport r;
    CHECK(coh_scenecatalog_load(&c,input(rich),7,&r)==COH_OK);CohSceneCatalog *old=c;CohCatalogReport before;coh_scenecatalog_report(c,&before);
    /* Every truncation keeps a previously published catalog intact. */
    for(size_t n=0;n<rich->bytes;n++){CHECK(coh_scenecatalog_load(&c,(CohBytes){rich->catalog,n},7,&r)!=COH_OK);CHECK(c==old);CohCatalogReport after;coh_scenecatalog_report(c,&after);CHECK(memcmp(&before,&after,sizeof(before))==0);}
    /* New shared decoder fails at every logical truncation boundary without
     * publishing candidate pointers, advancing input, or changing its count. */
    {size_t record=48+20+u32(rich->catalog+64);uint32_t n=u32(rich->catalog+record+8);CohBytes span={rich->catalog+record+16,n};
     for(size_t bits=0;bits<(size_t)n*8;bits++){CohRepReader rr,prior;CohSgDefinition d,prior_d;size_t bytes=123;
        CHECK(coh_rep_reader_bounded(&rr,span,bits,1,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);prior=rr;memset(&d,0xa5,sizeof(d));prior_d=d;
        CHECK(coh_scenegraph_definition_read(&d,&rr,0,COH_CATALOG_MEMORY_MAX,&bytes)!=COH_OK);CHECK(memcmp(&d,&prior_d,sizeof(d))==0&&memcmp(&rr,&prior,sizeof(rr))==0&&bytes==123);
     }}
    unsigned char *bad=malloc(rich->bytes+1);CHECK(bad!=NULL);
    size_t first_record=48+20+u32(rich->catalog+64); /* first filename size */
    for(unsigned kind=0;kind<15;kind++){
        memcpy(bad,rich->catalog,rich->bytes);size_t n=rich->bytes;
        switch(kind){case 0:bad[0]^=1;break;case 1:put(bad+8,2);break;case 2:put(bad+12,44);break;case 3:put(bad+20,8);break;case 4:bad[32]^=1;break;case 5:put(bad+24,1025);break;case 6:put(bad+28,65537);break;case 7:put(bad+48,1);break;case 8:put(bad+60,4);break;case 9:put(bad+first_record,5);break;case 10:put(bad+first_record+12,0);break;case 11:put(bad+first_record+4,1);break;case 12:put(bad+first_record+16,99);break;case 13:put(bad+44,1);break;case 14:bad[n++]=0;put(bad+16,(uint32_t)n);break;}
        CHECK(coh_scenecatalog_load(&c,(CohBytes){bad,n},7,&r)!=COH_OK&&c==old);
    }
    /* Valid envelope/name CRC with an invalid body flag reaches the shared
     * decoder, proving preflight is not mislabeled complete record validation. */
    memcpy(bad,rich->catalog,rich->bytes);bad[first_record+16+u32(bad+first_record+8)-1]=2;
    CHECK(coh_scenecatalog_preflight((CohBytes){bad,rich->bytes},7,&r)==COH_OK);
    CHECK(coh_scenecatalog_load(&c,(CohBytes){bad,rich->bytes},7,&r)!=COH_OK&&c==old&&r.stage==COH_CATALOG_DECODE);
    free(bad);
    CohSgImportedFile untouched={0},saved=untouched;CHECK(coh_scenecatalog_file(c,"missing",0,7,&untouched)==COH_NOT_FOUND);CHECK(memcmp(&saved,&untouched,sizeof(saved))==0);
    CHECK(coh_scenecatalog_file(c,"maps/oracle_world.txt",0,7,&untouched)==COH_STATE);CHECK(coh_scenecatalog_file(c,"maps/oracle_world.txt",0x11223344u,8,&untouched)==COH_STATE);
    /* Every candidate allocation failure leaves old ownership and its import
     * data unchanged; do not run O(N^2) failure injection on the stress corpus. */
    for(size_t fail=1;fail<64;fail++){
        calls=0;fail_at=fail;size_t retained=live_bytes;CohStatus s=coh_scenecatalog_load(&c,input(rich),7,&r);fail_at=0;
        if(s==COH_OK)break;
        CHECK(s==COH_LIMIT&&c==old&&live_bytes==retained);allocation_failures++;
    }
    CHECK(allocation_failures>=3);coh_scenecatalog_free(c);CHECK(!live&&!live_bytes);
    /* Full imported metadata survives releasing and modifying the envelope. */
    bad=malloc(rich->bytes);CHECK(bad);memcpy(bad,rich->catalog,rich->bytes);c=NULL;CHECK(coh_scenecatalog_load(&c,(CohBytes){bad,rich->bytes},7,&r)==COH_OK);memset(bad,0,rich->bytes);free(bad);
    CHECK(coh_scenecatalog_file(c,"maps/oracle_world.txt",0x11223344u,7,&untouched)==COH_OK);CHECK(untouched.definitions[0].wire_bytes>100&&untouched.definitions[0].swap_count==2);
    CohSceneGraph *g=NULL;reject_asset=1;CHECK(apply(c,rich,&g)==COH_NOT_FOUND&&g==NULL);reject_asset=0;CHECK(apply(c,rich,&g)==COH_OK);coh_scenecatalog_free(c);CHECK(g->definitions[0].wire_bytes>100);coh_scenegraph_free(g);
    CHECK(!live&&!live_bytes);CHECK(asset_calls>0);
    printf("{\"passed\":true,\"checks\":%u,\"source_fixtures_accepted\":%u,\"allocation_failure_points\":%u,\"large_files\":508,\"large_definitions\":12192,\"large_children\":36567,\"large_owned_bytes\":%zu,\"large_replacement_peak_bytes\":%zu,\"catalog_budget_bytes\":%u,\"graph_limit_preserved\":true,\"live_world\":false}\n",checks,accepted,allocation_failures,large_owned,large_peak,COH_CATALOG_MEMORY_MAX);
    return 0;
}
