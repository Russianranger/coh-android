/* Authentic root-reachable Atlas model candidate geometry; material and loaded
 * generation remain explicit fixtures. No live world/render publication. */
#include "../coh_wr_rigid_source.h"
#include "../coh_wr_rigid_internal.h"
#include "../../scenecatalog/coh_resource_geo_source.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,pins,releases;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"legacy line%d %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {uint8_t*data;size_t size;} Source;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_IO;memcpy(d,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
static CohStatus acquire(void*v,CohAssetId id,const char*model,uint32_t part,const CohAssetGeoMaterial*src,CohWrRigidMaterial*out){
 (void)v;CHECK(id.generation==17);CHECK(!strcmp(model,"_shptlr_K_Roof__FLRSHPS_SHELLS"));
 CHECK(part<(1u));CHECK(!strcmp(src->texture_name,"asphalt_squaremask.tga"));CHECK(src->triangle_count==(2u));
 CHECK(src->texture_id==51&&src->first_triangle==0);
 memset(out,0,sizeof(*out));out->material=coh_renderer_default_material(COH_MAT_DUAL);
 for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++)out->uv_scale[i][j]=1;
 out->texture_id[0]=11;out->texture_id[1]=12;out->geometry_id=100+part;out->generation=19;memset(out->source_sha256,1,32);out->pin=&pins;pins++;return COH_OK;
}
static void release(void*v,void*p){(void)v;CHECK(p==&pins);releases++;}
static Source load(const char*p){FILE*f=fopen(p,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<1024*1024);rewind(f);Source s={malloc((size_t)n),(size_t)n};CHECK(s.data);CHECK(fread(s.data,1,s.size,f)==s.size);CHECK(!fclose(f));return s;}
static const char*path="data/object_library/special_buildings/shop_interiors/shop_tailor/shop_tailor.geo";
static CohAssetLoader*mount(Source*s){CohAssetLoader*l=NULL;CohAssetLimits lim={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&lim,&l)==COH_OK);CHECK(coh_asset_mount_file(l,path,(CohAssetSource){readat,s,s->size,17})==COH_OK);return l;}
static CohWrRigidRequest request(Source*s){CohWrRigidRequest q={{path,17},"_shptlr_K_Roof__FLRSHPS_SHELLS",{0},19,digest,NULL,acquire,release,NULL};digest(NULL,(CohBytes){s->data,s->size},q.geo_sha256);return q;}
static void packet(CohWrRigidResource*r,const char*name){CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK);FILE*f=fopen(name,"wb");CHECK(f);for(unsigned i=0;i<report.parts;i++){CohRenderGeometry g;CohWrRigidMaterial m;CHECK(coh_wr_rigid_part(r,i,&g,&m)==COH_OK);CHECK(fwrite(g.vertices,sizeof(*g.vertices),g.vertex_count,f)==g.vertex_count);CHECK(fwrite(g.indices,sizeof(*g.indices),g.index_count,f)==g.index_count);}CHECK(!fclose(f));}
static unsigned decoder_calls;static size_t previous_record;
static CohStatus observed_open(CohBytes bytes,uint8_t*work,size_t cap,uint32_t max,CohAssetGeo*out){uint32_t zero=0;return coh_resource_geo_source_open(bytes,work,cap,max,out,&zero);}
static CohStatus observed_model(const CohAssetGeo*g,uint32_t row,CohAssetGeoModel*out,uint32_t*zero){
 CHECK(row==0&&g->model_count==1);CHECK(!decoder_calls||g->records_offset>previous_record);previous_record=g->records_offset;decoder_calls++;
 return coh_resource_geo_source_model(g,row,out,zero);
}
static int stop(void*ctx){(void)ctx;return 1;}
int main(int argc,char**argv){
 CHECK(argc==5);Source s=load(argv[1]);CHECK(s.size==252088);
 size_t cap=0;CHECK(coh_asset_geo_workspace((CohBytes){s.data,s.size},&cap)==COH_OK);uint8_t*work=malloc(cap);CHECK(work);CohAssetGeo g;uint32_t zero=0;
 CHECK(coh_resource_geo_source_open((CohBytes){s.data,s.size},work,cap,128,&g,&zero)==COH_OK&&zero==4&&g.model_count==72);
 const char*empty_names[]={"LlegR","FootR","LlegL","FootL"};unsigned seen=0;
 for(uint32_t row=0;row<g.model_count;row++){CohAssetGeoModel model;uint32_t empty=0;CHECK(coh_resource_geo_source_model(&g,row,&model,&empty)==COH_OK);if(empty){CHECK(row==34+seen&&seen<4&&!strcmp(model.name,empty_names[seen]));seen++;}}
 CHECK(seen==4);free(work);CohAssetLoader*l=mount(&s);CohWrRigidResource*r=NULL;CohWrRigidRequest q=request(&s);
 CohWrRigidLimits b={16u<<20,s.size,8u<<20,2u<<20,2u<<20,128,65536,65536,64};
 CHECK(coh_wr_rigid_acquire(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&pins==0);
 CHECK(coh_wr_rigid_acquire_using(l,&q,&b,(CohCancel){0},&r,observed_open,observed_model)==COH_OK&&decoder_calls==72);coh_wr_rigid_release(&r);CHECK(!r&&pins==releases);
 CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);
 CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK&&report.geo_version==8&&report.vertices==4&&report.triangles==2&&report.parts==1);
 packet(r,argv[4]);CohWrRigidResource*old=r;
 CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_STATE&&r==old);
 coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);coh_wr_rigid_release(&r);CHECK(!r&&pins==releases);
 unsigned before=pins;q.model="FootR";
 CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);
 q.model="absent_model";CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_NOT_FOUND&&!r&&pins==before);
 q=request(&s);q.geo_sha256[0]^=1;CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&pins==before);
 q=request(&s);CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){stop,NULL},&r)==COH_CANCELLED&&!r&&pins==before);
 b.max_models=71;CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);
 CHECK(coh_asset_stats(l).pinned_blobs==0);CHECK(coh_asset_destroy(&l)==COH_OK);free(s.data);
 for(unsigned arg=2;arg<=3;arg++){
  s=load(argv[arg]);l=mount(&s);q=request(&s);b.max_models=128;b.external_bytes=s.size;
  CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&pins==before);
  CHECK(coh_asset_stats(l).pinned_blobs==0&&pins==releases);CHECK(coh_asset_destroy(&l)==COH_OK);free(s.data);
 }
 printf("{\"passed\":true,\"checks\":%u,\"ordinary_vertices\":4,\"ordinary_triangles\":2,\"zero_rows_preserved\":4,\"linear_row_zero_decoder_calls\":72,\"selected_zero_refused_before_material\":true,\"material_fixture_only\":true,\"source_generation_established\":false,\"world_authority\":false}\n",checks);
}
