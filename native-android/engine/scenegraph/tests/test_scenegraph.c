#include "coh_scenegraph.h"
#include <assert.h>
#include <math.h>
#include <float.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "scenegraph_fixtures.h"
static unsigned checks;
static size_t live_allocations, allocation_calls, fail_at;
void *__real_malloc(size_t);
void *__real_calloc(size_t,size_t);
void __real_free(void *);
void *__wrap_malloc(size_t n){allocation_calls++;if(fail_at&&allocation_calls==fail_at)return NULL;void *p=__real_malloc(n);if(p)live_allocations++;return p;}
void *__wrap_calloc(size_t n,size_t z){allocation_calls++;if(fail_at&&allocation_calls==fail_at)return NULL;void *p=__real_calloc(n,z);if(p)live_allocations++;return p;}
void __wrap_free(void *p){if(p){assert(live_allocations);live_allocations--;__real_free(p);}}
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
    CohRepReader r=reader(f),before=r;CohSceneGraph *old=*g;CohSgImports imports={control,load_file,load_asset,7};
    uint32_t generation=*g?(*g)->generation+1:1;
    CohStatus status=coh_scenegraph_apply(g,&r,&imports,generation,failure);
    if(status!=COH_OK){CHECK(*g==old);CHECK(memcmp(&r,&before,sizeof(r))==0);}else{CHECK(r.cursor==f->bits);CHECK((*g)->generation==generation);CHECK((*g)->owned_bytes<=COH_SG_MEMORY_MAX);}
    return status;
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
            size_t retained=live_allocations;CohSceneGraph *prior=g;CohSceneGraph snapshot={0};CohSgDefinition defs[5];
            if(g){snapshot=*g;memcpy(defs,g->definitions,sizeof(defs));}
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
     for(size_t bits=0;bits<f->bits;bits++){CohRepReader r=reader(f);r.bits=bits;CohRepReader old=r;CHECK(coh_scenegraph_apply(&g,&r,&imports,1,NULL)!=COH_OK);CHECK(g==NULL);CHECK(memcmp(&r,&old,sizeof(r))==0);}}
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
    printf("{\"passed\":true,\"checks\":%u,\"allocation_failure_points\":%u,\"source_fixtures_accepted\":%u,\"source_fixtures_rejected\":%u,\"live_world\":false}\n",checks,allocation_failures,accepted,rejected);
    return 0;
}
