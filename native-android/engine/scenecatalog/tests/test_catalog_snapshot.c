#include "coh_catalog_snapshot.h"
#include "../scenegraph/runtime_graph.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed %d: %s\n",__LINE__,#x);abort();}}while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void *);
static size_t live,calls,fail_at;
void *__wrap_malloc(size_t n){calls++;if(calls==fail_at)return NULL;void *p=__real_malloc(n);if(p)live++;return p;}
void *__wrap_calloc(size_t n,size_t z){calls++;if(calls==fail_at)return NULL;void *p=__real_calloc(n,z);if(p)live++;return p;}
void __wrap_free(void *p){if(p){CHECK(live);live--;}__real_free(p);}
static CohStatus digest(void *c,CohBytes b,uint8_t out[32]){(void)c;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
static CohStatus failed_digest(void *c,CohBytes b,uint8_t out[32]){(void)c;(void)b;(void)out;return COH_IO;}
static int cancelled(void *c){(void)c;return 1;}
static CohBytes readfile(const char *path){FILE *f=fopen(path,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0);rewind(f);uint8_t *p=malloc((size_t)n);CHECK(p);CHECK(fread(p,1,(size_t)n,f)==(size_t)n);CHECK(!fclose(f));return (CohBytes){p,(size_t)n};}
static void hex(const char *s,uint8_t out[32]){for(unsigned i=0;i<32;i++){unsigned n;CHECK(sscanf(s+2*i,"%2x",&n)==1);out[i]=(uint8_t)n;}}
static void refuse(CohCatalogSnapshot *old,CohCatalogOwner *owner,CohBytes bytes,const CohCatalogSnapshotBinding *b,const CohRuntimeSnapshotBudget *budget,const CohCatalogDigest *d){size_t before=live;CohCatalogSnapshot *out=NULL;CHECK(coh_catalog_snapshot_create(old,owner,bytes,b,budget,d,NULL,&out)!=COH_OK);CHECK(!out);CHECK(live==before);}
int main(int argc,char **argv){CHECK(argc==3);CohBytes cat=readfile(argv[1]),snap=readfile(argv[2]);
    CohCatalogBinding cb={0};cb.owner_generation=1;cb.catalog_generation=20261016;cb.asset_generation=20261016;
    CHECK(digest(NULL,cat,cb.catalog_sha256)==COH_OK);
    hex("a5517f1ca0c5f1ce8aa2c39bfa70f76d0c913ef9a27634c16ad361b3770ff3f0",cb.source_sha256);
    memset(cb.inventory_sha256,1,32); /* explicit fixture provenance label, not inventory admission */
    CohCatalogDigest d={NULL,digest};CohCatalogOwner *owner=NULL;
    CohCatalogOwnerBudget ob={COH_CATALOG_MEMORY_MAX,COH_CATALOG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};
    CohCatalogOwnerReport or;CHECK(coh_catalog_owner_create(NULL,cat,&cb,&ob,&d,&owner,&or)==COH_OK);
    CohCatalogSnapshotBinding b={0};b.generation=1;b.catalog=cb;CHECK(digest(NULL,snap,b.snapshot_sha256)==COH_OK);
    hex("2e3b459686f769ac18519e7ec93cecff691854411c8c5dd7db70a62182868588",b.run_sha256);
    CohRuntimeSnapshotBudget budget={COH_SG_TRANSACTION_MAX,cat.size+262144};CohCatalogSnapshot *s=NULL;
    size_t start=calls;CHECK(coh_catalog_snapshot_create(NULL,owner,snap,&b,&budget,&d,NULL,&s)==COH_OK);size_t build_calls=calls-start;
    CHECK(build_calls>=3);for(size_t i=1;i<=3;i++){fail_at=calls+i;refuse(NULL,owner,snap,&b,&budget,&d);fail_at=0;}
    CohCatalogDigest bad={NULL,failed_digest};refuse(NULL,owner,snap,&b,&budget,&bad);
    CohCancel stop={cancelled,NULL};CohCatalogSnapshot *cancelled_out=NULL;
    size_t prior_live=live;CHECK(coh_catalog_snapshot_create(NULL,owner,snap,&b,&budget,&d,&stop,&cancelled_out)==COH_CANCELLED);CHECK(!cancelled_out&&live==prior_live);
    CohBytes view;CohCatalogSnapshotBinding vb;CohRuntimeSnapshotReport report;
    CHECK(coh_catalog_snapshot_view(s,&view,&vb,&report)==COH_OK);CHECK(view.data!=snap.data);CHECK(view.size==snap.size);CHECK(!memcmp(view.data,snap.data,snap.size));
    CHECK(report.active_roots==33&&report.external_count==7&&report.reachable_external==1&&report.reachable_definitions==15352);
    CHECK(report.definitions_crc_verified&&report.references_crc_verified&&!report.world_authority&&!report.graph_published);
    for(unsigned field=0;field<8;field++){CohCatalogSnapshotBinding wrong=b;
        switch(field){case 0:wrong.generation=0;break;case 1:wrong.catalog.owner_generation++;break;case 2:wrong.catalog.asset_generation++;break;case 3:wrong.catalog.catalog_generation++;break;case 4:wrong.catalog.source_sha256[0]^=1;break;case 5:wrong.catalog.inventory_sha256[0]^=1;break;case 6:wrong.snapshot_sha256[0]^=1;break;default:memset(wrong.run_sha256,0,32);}
        refuse(NULL,owner,snap,&wrong,&budget,&d);
    }
    for(size_t n=0;n<snap.size;n+=17)refuse(NULL,owner,(CohBytes){snap.data,n},&b,&budget,&d);
    CohRuntimeSnapshotBudget tight={report.aggregate_peak_bytes-1,budget.retained_bytes};refuse(NULL,owner,snap,&b,&tight,&d);
    tight.aggregate_limit++;CohCatalogSnapshot *exact=NULL;CHECK(coh_catalog_snapshot_create(NULL,owner,snap,&b,&tight,&d,NULL,&exact)==COH_OK);coh_catalog_snapshot_release(exact);
    uint8_t *mut=(uint8_t *)snap.data;for(unsigned i=0;i<80;i++){mut[i]^=1;refuse(NULL,owner,snap,&b,&budget,&d);mut[i]^=1;}
    refuse(s,owner,snap,&b,&budget,&d);b.generation=2;CohCatalogSnapshot *next=NULL;
    CHECK(coh_catalog_snapshot_create(s,owner,snap,&b,&budget,&d,NULL,&next)==COH_OK);
    CohCatalogBinding cb2=cb;cb2.owner_generation=2;CohCatalogOwner *owner2=NULL;
    CHECK(coh_catalog_owner_create(owner,cat,&cb2,&ob,&d,&owner2,&or)==COH_OK);
    CohCatalogSnapshotBinding b2=b;b2.generation=3;b2.catalog=cb2;CohCatalogSnapshot *distinct=NULL;
    CHECK(coh_catalog_snapshot_create(next,owner2,snap,&b2,&budget,&d,NULL,&distinct)==COH_OK);
    CohCatalogSnapshotBinding regress=b;regress.generation=4;refuse(distinct,owner,snap,&regress,&budget,&d);
    coh_catalog_owner_release(owner2);coh_catalog_snapshot_release(distinct);
    /* A pins both spans while B borrows them; graph budget excludes the borrowed
     * spans but includes A descriptors/indexes, original caller inputs and next. */
    CHECK(coh_catalog_snapshot_view(s,&view,&vb,&report)==COH_OK);CohBytes owned_cat;
    CHECK(coh_catalog_owner_bytes(owner,&owned_cat)==COH_OK);CHECK(coh_catalog_snapshot_retain(s)==COH_OK);
    CohRuntimeGraphBinding gb={0};gb.generation=1;gb.catalog_generation=cb.catalog_generation;
    gb.pins.asset_generation=cb.asset_generation;gb.pins.digest=digest;
    memcpy(gb.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(gb.pins.source_sha256,cb.source_sha256,32);
    memcpy(gb.pins.snapshot_sha256,vb.snapshot_sha256,32);memcpy(gb.pins.run_sha256,vb.run_sha256,32);
    CohRuntimeSnapshotBudget composed={COH_SG_TRANSACTION_MAX,
        coh_catalog_owner_owned_bytes(owner)-owned_cat.size+coh_catalog_snapshot_owned_bytes(s)-view.size+
        coh_catalog_snapshot_owned_bytes(next)+cat.size+snap.size+262144};
    CohRuntimeGraph *graph=NULL,*candidate=NULL,*retired=NULL;CohRuntimeGraphReport gr;
    CHECK(coh_runtime_graph_build(NULL,owned_cat,view,&gb,&composed,NULL,&candidate,&gr)==COH_OK);
    CHECK(gr.nodes==40232&&gr.edges==130314&&gr.source.active_roots==33);
    CHECK(coh_runtime_graph_publish(&graph,&candidate,&retired)==COH_OK);CHECK(!candidate&&!retired);
    CohRuntimeGraphBinding badgb=gb;badgb.generation=2;badgb.pins.snapshot_sha256[0]^=1;
    size_t before_graph=live;CHECK(coh_runtime_graph_build(graph,owned_cat,view,&badgb,&composed,NULL,&candidate,&gr)!=COH_OK);
    CHECK(!candidate&&live==before_graph);gb.generation=2;
    CHECK(coh_runtime_graph_build(graph,owned_cat,view,&gb,&composed,NULL,&candidate,&gr)==COH_OK);
    CHECK(coh_runtime_graph_publish(&graph,&candidate,&retired)==COH_OK);CHECK(retired&&!candidate);
    coh_runtime_graph_free(retired);
    coh_catalog_owner_release(owner);CHECK(coh_catalog_snapshot_view(s,&view,&vb,&report)==COH_OK);
    CHECK(coh_catalog_snapshot_retain(s)==COH_OK);coh_catalog_snapshot_release(s);coh_catalog_snapshot_release(s);
    /* One explicit A lease still pins the live B graph after caller retire. */
    CohRuntimeGraphRoot root;CHECK(coh_runtime_graph_root(graph,0,&root)==COH_OK);CHECK(root.active);
    coh_runtime_graph_free(graph);coh_catalog_snapshot_release(s);
    CHECK(coh_catalog_snapshot_view(next,&view,&vb,&report)==COH_OK);CHECK(vb.generation==2);coh_catalog_snapshot_release(next);
    free((void *)snap.data);free((void *)cat.data);CHECK(!live);printf("{\"passed\":true,\"checks\":%u}\n",checks);return 0;
}
