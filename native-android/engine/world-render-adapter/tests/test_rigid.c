#include "../coh_wr_rigid.h"
#ifdef COH_RIGID_FIXTURE_DIGEST
#include "rigid_fixture_digests.h"
#define SHA256 coh_rigid_fixture_digest
#else
#include <openssl/sha.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void*,size_t);void __real_free(void*);
static int fail_after=-1;static unsigned allocs,frees;
static int deny(void){allocs++;if(fail_after<0)return 0;if(!fail_after)return 1;fail_after--;return 0;}
void *__wrap_malloc(size_t n){return deny()?NULL:__real_malloc(n);}
void *__wrap_calloc(size_t n,size_t z){return deny()?NULL:__real_calloc(n,z);}
void *__wrap_realloc(void*p,size_t n){return deny()?NULL:__real_realloc(p,n);}
void __wrap_free(void*p){if(p)frees++;__real_free(p);}
typedef struct{uint8_t*data;size_t size;} Source;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_INVALID;memcpy(d,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
typedef struct {unsigned acquired,released;int failure,unsupported,missing,duplicate;} Materials;
static CohStatus acquire(void*v,CohAssetId id,const char*model,uint32_t part,const CohAssetGeoMaterial*source,CohWrRigidMaterial*out){
    Materials*m=v;CHECK(!strcmp(id.path,"world/rigid.geo")&&id.generation==17);
    CHECK(!strcmp(model,"fixture_rigid_v8"));CHECK(part<2&&source->first_triangle==part&&source->triangle_count==1);
    CHECK(!strcmp(source->texture_name,part?"b.tga":"a.tga"));
    if(m->failure==(int)part)return COH_NOT_FOUND;
    memset(out,0,sizeof(*out));out->material=coh_renderer_default_material(COH_MAT_DUAL);
    for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++)out->uv_scale[i][j]=(float)(part+1);
    out->texture_id[0]=m->missing?0:11;out->texture_id[1]=12;
    out->geometry_id=m->duplicate?101:101+part;out->generation=19;
    out->unsupported_semantics=(uint32_t)m->unsupported;memset(out->source_sha256,(int)part+1,32);
    out->pin=(void*)(uintptr_t)(part+1);m->acquired++;return COH_OK;
}
static void release(void*v,void*p){Materials*m=v;CHECK((uintptr_t)p>=1&&(uintptr_t)p<=2);m->released++;}
static int cancel_at(void*v){return (*(int*)v)--==0;}
static Source load(const char*directory,const char*name){char p[4096];CHECK(snprintf(p,sizeof(p),"%s/%s.geo",directory,name)>0);FILE*f=fopen(p,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0);rewind(f);Source s={malloc((size_t)n),(size_t)n};CHECK(s.data);CHECK(fread(s.data,1,s.size,f)==s.size);CHECK(!fclose(f));return s;}
int main(int argc,char**argv){
    CHECK(argc==3);Source source=load(argv[1],"valid");CohAssetLoader*l=NULL;CohWrRigidResource*r=NULL;
    CohAssetLimits al={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&al,&l)==COH_OK);
    CHECK(coh_asset_mount_file(l,"world/rigid.geo",(CohAssetSource){readat,&source,source.size,17})==COH_OK);
    Materials m={0,0,-1,0,0,0};CohWrRigidRequest q={{"world/rigid.geo",17},"fixture_rigid_v8",{0},19,digest,NULL,acquire,release,&m};
    digest(NULL,(CohBytes){source.data,source.size},q.geo_sha256);
    CohWrRigidLimits b={16u<<20,1024,8u<<20,2u<<20,2u<<20,64,65536,65536,64};CohCancel never={0};
    CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)==COH_OK);CohWrRigidReport report;
    CohWrRigidResource*old=r;CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)==COH_STATE&&r==old);
    CHECK(coh_wr_rigid_report(r,&report)==COH_OK&&report.geo_version==8&&report.parts==2&&report.vertices==4&&report.triangles==2);
    CohAssetId identity;const char*name;CHECK(coh_wr_rigid_identity(r,&identity,&name)==COH_OK);
    CHECK(!strcmp(identity.path,q.geo.path)&&identity.generation==17&&!strcmp(name,q.model));
    CHECK(report.aggregate_peak_bytes<=b.aggregate_limit&&report.owned_bytes&&report.temporary_bytes);
    coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);CHECK(coh_asset_destroy(&l)==COH_STATE);
    FILE*packet=fopen(argv[2],"wb");CHECK(packet);unsigned a=allocs,f=frees;
    for(uint32_t part=0;part<2;part++){
        CohRenderGeometry g;CohWrRigidMaterial material;CHECK(coh_wr_rigid_part(r,part,&g,&material)==COH_OK);
        CHECK(g.vertex_count==4&&g.index_count==3&&g.identity==101+part&&g.generation==17);
        CHECK(material.pin==(void*)(uintptr_t)(part+1)&&material.generation==19);
        CHECK(g.vertices[2].position[0]==1&&g.vertices[2].position[1]==1&&g.vertices[2].normal[2]==1);
        CHECK(g.vertices[0].uv0[1]==(float)(part+1)&&g.vertices[2].uv0[1]==0);
        CHECK(fwrite(g.vertices,sizeof(*g.vertices),g.vertex_count,packet)==g.vertex_count);
        CHECK(fwrite(g.indices,sizeof(*g.indices),g.index_count,packet)==g.index_count);
    }
    CHECK(allocs==a&&frees==f);CHECK(!fclose(packet));coh_wr_rigid_release(&r);CHECK(!r&&m.acquired==m.released);
    b.loader_reservation=1;CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)==COH_LIMIT&&!r);b.loader_reservation=8u<<20;
    q.geo_sha256[0]^=1;CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)==COH_INVALID&&!r);q.geo_sha256[0]^=1;
    q.geo.generation=0;CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)==COH_INVALID&&!r);q.geo.generation=17;
    q.model="FIXTURE_RIGID_V8";CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)==COH_NOT_FOUND&&!r);q.model="fixture_rigid_v8";
    for(int test=0;test<4;test++){
        if(test==0)m.failure=1;
        if(test==1)m.unsupported=1;
        if(test==2)m.missing=1;
        if(test==3)m.duplicate=1;
        CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)!=COH_OK&&!r&&m.acquired==m.released);
        m.failure=-1;m.unsupported=m.missing=m.duplicate=0;
    }
    b.aggregate_limit=report.aggregate_peak_bytes;
    CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)==COH_OK);coh_wr_rigid_release(&r);
    b.aggregate_limit=report.aggregate_peak_bytes-1;CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)==COH_LIMIT&&!r);b.aggregate_limit=16u<<20;
    for(int n=0;n<4;n++){fail_after=n;CHECK(coh_wr_rigid_acquire(l,&q,&b,never,&r)!=COH_OK&&!r);fail_after=-1;CHECK(m.acquired==m.released);}
    for(int n=0;n<9;n++){CohCancel c={cancel_at,&n};int copy=n;c.context=&copy;CohStatus s=coh_wr_rigid_acquire(l,&q,&b,c,&r);CHECK(s==COH_OK||s==COH_CANCELLED);coh_wr_rigid_release(&r);CHECK(m.acquired==m.released);}
    CHECK(coh_asset_destroy(&l)==COH_OK);free(source.data);
    const char*kinds[]={"bone","scale","lightmap","weights","matidx","reflection","missing_uv","reflection_count","pivot","bad_index","duplicate_model"};
    for(unsigned i=0;i<sizeof(kinds)/sizeof(kinds[0]);i++){
        source=load(argv[1],kinds[i]);CHECK(coh_asset_create(&al,&l)==COH_OK);
        CHECK(coh_asset_mount_file(l,"world/rigid.geo",(CohAssetSource){readat,&source,source.size,17})==COH_OK);
        digest(NULL,(CohBytes){source.data,source.size},q.geo_sha256);
        CohStatus refused=coh_wr_rigid_acquire(l,&q,&b,never,&r);
        CHECK(refused==(i>=9?COH_INVALID:COH_UNSUPPORTED)&&!r);
        CHECK(coh_asset_stats(l).pinned_blobs==0&&m.acquired==m.released);CHECK(coh_asset_destroy(&l)==COH_OK);free(source.data);
    }
    printf("{\"passed\":true,\"checks\":%u,\"version\":8,\"parts\":2,\"vertices\":4,\"triangles\":2,\"material_pins_balanced\":true,\"fixture_only\":true,\"world_authority\":false}\n",checks);
}
