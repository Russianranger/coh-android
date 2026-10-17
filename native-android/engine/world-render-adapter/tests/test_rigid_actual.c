/* Authentic GEO geometry with explicitly synthetic material/texture bindings.
 * This does not qualify actual material, trick, loaded generation or world use. */
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
static unsigned checks,pins,releases;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"actual line%d %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{uint8_t*data;size_t size;} Source;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_INVALID;memcpy(d,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
static CohStatus acquire(void*v,CohAssetId id,const char*model,uint32_t part,const CohAssetGeoMaterial*source,CohWrRigidMaterial*out){
    (void)v;CHECK(id.generation==17&&!strcmp(model,"FX_PraetorianBox_Open")&&part==0);
    CHECK(!strcmp(source->texture_name,"Box-1.tga")&&source->triangle_count==28&&source->first_triangle==0);
    memset(out,0,sizeof(*out));out->material=coh_renderer_default_material(COH_MAT_DUAL);
    for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++)out->uv_scale[i][j]=1;
    out->texture_id[0]=11;out->texture_id[1]=12;out->geometry_id=101;out->generation=19;
    memset(out->source_sha256,1,32);out->pin=&pins;pins++;return COH_OK;
}
static void release(void*v,void*pin){(void)v;CHECK(pin==&pins);releases++;}
int main(int argc,char**argv){
    CHECK(argc==3);FILE*file=fopen(argv[1],"rb");CHECK(file);CHECK(!fseek(file,0,SEEK_END));long n=ftell(file);CHECK(n==1289);rewind(file);
    Source source={malloc((size_t)n),(size_t)n};CHECK(source.data);CHECK(fread(source.data,1,source.size,file)==source.size);CHECK(!fclose(file));
    CohAssetLoader*l=NULL;CohAssetLimits al={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&al,&l)==COH_OK);
    const char*path="data/object_library/worldnpcs/praetorian_box/g_praetorianbox_open.geo";
    CHECK(coh_asset_mount_file(l,path,(CohAssetSource){readat,&source,source.size,17})==COH_OK);
    CohWrRigidRequest q={{path,17},"FX_PraetorianBox_Open",{0},19,digest,NULL,acquire,release,NULL};
    /* Independent caller pins the exact qualified public payload SHA; source
     * generation and material IDs here remain explicit test fixture labels. */
    static const uint8_t expected[32]={0x21,0x8d,0x1b,0x2f,0xf8,0x90,0x67,0x8c,0xca,0x25,0xb0,0x05,0xd2,0x95,0xaf,0xf8,0xf7,0x6c,0x6f,0x55,0x1a,0xca,0xd6,0xb2,0x14,0x4d,0x17,0x86,0x72,0x32,0x39,0xb5};
    memcpy(q.geo_sha256,expected,32);CohWrRigidLimits b={16u<<20,source.size,8u<<20,2u<<20,2u<<20,64,65536,65536,64};
    CohWrRigidResource*r=NULL;CHECK(coh_wr_rigid_acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);
    CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK&&report.geo_version==8&&report.parts==1&&report.vertices==56&&report.triangles==28);
    CohRenderGeometry g;CohWrRigidMaterial m;CHECK(coh_wr_rigid_part(r,0,&g,&m)==COH_OK&&g.vertex_count==56&&g.index_count==84);
    file=fopen(argv[2],"wb");CHECK(file);CHECK(fwrite(g.vertices,sizeof(*g.vertices),g.vertex_count,file)==g.vertex_count);CHECK(fwrite(g.indices,sizeof(*g.indices),g.index_count,file)==g.index_count);CHECK(!fclose(file));
    coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);coh_wr_rigid_release(&r);CHECK(!r&&pins==1&&releases==1);CHECK(coh_asset_destroy(&l)==COH_OK);free(source.data);
    printf("{\"passed\":true,\"checks\":%u,\"geo_version\":8,\"vertices\":56,\"triangles\":28,\"authentic_geo_bytes\":true,\"material_fixture_only\":true,\"generation_fixture_only\":true,\"world_authority\":false}\n",checks);
}
