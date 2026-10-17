/* Actual captured v7 ordinary CPU geometry, explicit fixture materials only. */
#include "../coh_wr_rigid_v7.h"
#include "../coh_wr_rigid_source.h"
#include "../coh_wr_rigid_internal.h"
#include "../../scenecatalog/coh_resource_geo_source.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,pins,releases,fail_material,cancel_after_material;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"v7 line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
static long fail_at=-1,allocations;
void *__wrap_malloc(size_t n){if(fail_at>=0&&allocations++==fail_at)return NULL;return __real_malloc(n);}
void *__wrap_calloc(size_t n,size_t s){if(fail_at>=0&&allocations++==fail_at)return NULL;return __real_calloc(n,s);}
void __wrap_free(void*p){__real_free(p);}
typedef struct {uint8_t*data;size_t size;} Source;
static const char*path="data/object_library/buildings/elements/signs/special_signs/chaser_sign_4to1/chaser_sign_4to1.geo";
static const char*models[]={"_ChaserLight2__SignChaserLights","_ChaserLight1__SignChaserLights","_ChaserLight3__SignChaserLights","_ChaserLight4__SignChaserLights","_ChaserlightBox_df"};
static unsigned selected;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_IO;memcpy(d,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
static CohStatus acquire(void*v,CohAssetId id,const char*model,uint32_t part,const CohAssetGeoMaterial*src,CohWrRigidMaterial*out){
 (void)v;CHECK(id.generation==17&&!strcmp(id.path,path));CHECK(selected<5&&!strcmp(model,models[selected]));CHECK(part==0);CHECK(!strcmp(src->texture_name,selected==4?"Marq_front.tga":"Marq_backlight.tga"));CHECK(src->triangle_count==(selected==4?12u:2u)&&src->texture_id==(selected==4?2u:1u)&&src->first_triangle==0);
 memset(out,0,sizeof(*out));out->material=coh_renderer_default_material(COH_MAT_DUAL);for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++)out->uv_scale[i][j]=1;out->texture_id[0]=11;out->texture_id[1]=12;out->geometry_id=100+part;out->generation=19;memset(out->source_sha256,1,32);out->pin=&pins;pins++;if(fail_material)out->unsupported_semantics=1;return COH_OK;
}
static void release(void*v,void*p){(void)v;CHECK(p==&pins);releases++;}
static int stop(void*v){(void)v;return 1;}
static int after_material(void*v){(void)v;return cancel_after_material&&pins>releases;}
static Source load(const char*p){FILE*f=fopen(p,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<1024*1024);rewind(f);Source s={malloc((size_t)n),(size_t)n};CHECK(s.data);CHECK(fread(s.data,1,s.size,f)==s.size);CHECK(!fclose(f));return s;}
static CohAssetLoader*mount(Source*s){CohAssetLoader*l=NULL;CohAssetLimits lim={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&lim,&l)==COH_OK);CHECK(coh_asset_mount_file(l,path,(CohAssetSource){readat,s,s->size,17})==COH_OK);return l;}
static CohWrRigidRequest request(Source*s){CohWrRigidRequest q={{path,17},models[selected],{0},19,digest,NULL,acquire,release,NULL};digest(NULL,(CohBytes){s->data,s->size},q.geo_sha256);return q;}
static void clean(CohAssetLoader**l,Source*s){CHECK(coh_asset_stats(*l).pinned_blobs==0&&pins==releases);CHECK(coh_asset_destroy(l)==COH_OK);free(s->data);}
static void packet(CohWrRigidResource*r,FILE*f){CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK);for(unsigned i=0;i<report.parts;i++){CohRenderGeometry g;CohWrRigidMaterial m;CHECK(coh_wr_rigid_part(r,i,&g,&m)==COH_OK);CHECK(fwrite(g.vertices,sizeof(*g.vertices),g.vertex_count,f)==g.vertex_count);CHECK(fwrite(g.indices,sizeof(*g.indices),g.index_count,f)==g.index_count);}}
static CohStatus model(const CohAssetGeo*g,uint32_t i,CohAssetGeoModel*m,uint32_t*z){CohStatus s=coh_asset_geo_model(g,i,m);if(s==COH_OK)*z=0;return s;}
int main(int argc,char**argv){
 CHECK(argc==11);Source s=load(argv[1]);CHECK(s.size==1654);CohAssetLoader*l=mount(&s);CohWrRigidResource*r=NULL;CohWrRigidLimits b={16u<<20,s.size,8u<<20,2u<<20,2u<<20,128,65536,65536,64};CohWrRigidRequest q=request(&s);unsigned before=pins;
 CHECK(coh_wr_rigid_acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);
 CHECK(coh_wr_rigid_acquire_policy(l,&q,&b,(CohCancel){0},&r,coh_asset_geo_open,model,(CohWrRigidPolicy)99)==COH_INVALID&&!r&&pins==before);
 FILE*f=fopen(argv[7],"wb");CHECK(f);
 for(selected=0;selected<5;selected++){
  q=request(&s);CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK);CHECK(report.geo_version==7&&report.vertices==(selected==4?24u:4u)&&report.triangles==(selected==4?12u:2u)&&report.parts==1);CHECK(report.aggregate_peak_bytes<=b.aggregate_limit&&report.loader_reservation==b.loader_reservation);packet(r,f);
  CohWrRigidResource*old=r;CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r)==COH_STATE&&r==old);coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);coh_wr_rigid_release(&r);CHECK(!r&&pins==releases);
 }
 CHECK(!fclose(f));selected=1;q=request(&s);before=pins;
 q.model="absent";CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r)==COH_NOT_FOUND&&!r&&pins==before);q=request(&s);q.geo_sha256[0]^=1;CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&pins==before);q=request(&s);q.geo.generation=18;CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r)==COH_NOT_FOUND&&!r&&pins==before);q=request(&s);
 CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){stop,NULL},&r)==COH_CANCELLED&&!r&&pins==before);
 CohWrRigidLimits limits=b;limits.max_models=4;CHECK(coh_wr_rigid_v7_acquire(l,&q,&limits,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);limits=b;limits.max_workspace_bytes=1;CHECK(coh_wr_rigid_v7_acquire(l,&q,&limits,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);limits=b;limits.aggregate_limit=b.external_bytes+b.loader_reservation;CHECK(coh_wr_rigid_v7_acquire(l,&q,&limits,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);limits=b;limits.max_vertices=3;CHECK(coh_wr_rigid_v7_acquire(l,&q,&limits,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);limits=b;limits.max_stream_bytes=1;CHECK(coh_wr_rigid_v7_acquire(l,&q,&limits,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);
 fail_material=1;CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==releases);fail_material=0;cancel_after_material=1;CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){after_material,NULL},&r)==COH_CANCELLED&&!r&&pins==releases);cancel_after_material=0;
 unsigned allocation_failures=0;for(long a=0;a<64;a++){coh_asset_trim(l);fail_at=a;allocations=0;CohStatus st=coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r);fail_at=-1;if(st==COH_OK){coh_wr_rigid_release(&r);break;}CHECK(!r&&pins==releases&&coh_asset_stats(l).pinned_blobs==0);allocation_failures++;}CHECK(allocation_failures>4&&allocation_failures<64);clean(&l,&s);
 for(unsigned arg=2;arg<=6;arg++){s=load(argv[arg]);l=mount(&s);q=request(&s);before=pins;b.external_bytes=s.size;CohStatus st=coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r);if(st!=(arg==2?COH_UNSUPPORTED:COH_INVALID)){fprintf(stderr,"badcase%u status%d\n",arg,st);}CHECK(st==(arg==2?COH_UNSUPPORTED:COH_INVALID)&&!r&&pins==before);clean(&l,&s);}
 for(unsigned arg=8;arg<=10;arg++){s=load(argv[arg]);l=mount(&s);q=request(&s);before=pins;b.external_bytes=s.size;CohStatus st=coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r);CHECK(st==(arg==10?COH_INVALID:COH_UNSUPPORTED)&&!r&&pins==before);clean(&l,&s);}
 printf("{\"passed\":true,\"checks\":%u,\"actual_models\":5,\"allocation_failure_stages\":%u,\"fixture_materials_only\":true,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks,allocation_failures);
}
