/* Authentic root-reachable Atlas model candidate geometry; material and loaded
 * generation remain explicit fixtures. No live world/render publication. */
#include "../coh_wr_rigid.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,pins,releases,authentic;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"legacy line%d %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {uint8_t*data;size_t size;} Source;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_IO;memcpy(d,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
static CohStatus acquire(void*v,CohAssetId id,const char*model,uint32_t part,const CohAssetGeoMaterial*src,CohWrRigidMaterial*out){
 (void)v;CHECK(id.generation==17);CHECK(!strcmp(model,authentic?"_sign_Neon_BarVERT":"fixture_rigid_v0"));
 CHECK(part<(authentic?1u:2u));CHECK(!strcmp(src->texture_name,authentic?"Bar_vert_sign.tga":part?"b.tga":"a.tga"));CHECK(src->triangle_count==(authentic?56u:1u));
 if(authentic)CHECK(src->texture_id==2&&src->first_triangle==0);
 memset(out,0,sizeof(*out));out->material=coh_renderer_default_material(COH_MAT_DUAL);
 for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++)out->uv_scale[i][j]=1;
 out->texture_id[0]=11;out->texture_id[1]=12;out->geometry_id=100+part;out->generation=19;memset(out->source_sha256,1,32);out->pin=&pins;pins++;return COH_OK;
}
static void release(void*v,void*p){(void)v;CHECK(p==&pins);releases++;}
static Source load(const char*p){FILE*f=fopen(p,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<1024*1024);rewind(f);Source s={malloc((size_t)n),(size_t)n};CHECK(s.data);CHECK(fread(s.data,1,s.size,f)==s.size);CHECK(!fclose(f));return s;}
static const char*path="data/object_library/buildings/elements/signs/neon/neon.geo";
static CohAssetLoader*mount(Source*s){CohAssetLoader*l=NULL;CohAssetLimits lim={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&lim,&l)==COH_OK);CHECK(coh_asset_mount_file(l,path,(CohAssetSource){readat,s,s->size,17})==COH_OK);return l;}
static CohWrRigidRequest request(Source*s){CohWrRigidRequest q={{path,17},authentic?"_sign_Neon_BarVERT":"fixture_rigid_v0",{0},19,digest,NULL,acquire,release,NULL};digest(NULL,(CohBytes){s->data,s->size},q.geo_sha256);return q;}
static void packet(CohWrRigidResource*r,const char*name){CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK);FILE*f=fopen(name,"wb");CHECK(f);for(unsigned i=0;i<report.parts;i++){CohRenderGeometry g;CohWrRigidMaterial m;CHECK(coh_wr_rigid_part(r,i,&g,&m)==COH_OK);CHECK(fwrite(g.vertices,sizeof(*g.vertices),g.vertex_count,f)==g.vertex_count);CHECK(fwrite(g.indices,sizeof(*g.indices),g.index_count,f)==g.index_count);}CHECK(!fclose(f));}
int main(int argc,char**argv){
 CHECK(argc==5);char name[4096];CHECK(snprintf(name,sizeof(name),"%s/valid.geo",argv[1])>0);Source s=load(name);CohAssetLoader*l=mount(&s);CohWrRigidResource*r=NULL;CohWrRigidRequest q=request(&s);
 CohWrRigidLimits b={16u<<20,s.size,8u<<20,2u<<20,2u<<20,64,65536,65536,64};CHECK(coh_wr_rigid_acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK&&report.geo_version==0&&report.vertices==4&&report.triangles==2&&report.parts==2);packet(r,argv[3]);coh_wr_rigid_release(&r);CHECK(!r&&pins==releases);CHECK(coh_asset_destroy(&l)==COH_OK);free(s.data);
 const char*kinds[]={"bone","scale","weights","matidx","missing_uv","pivot","bad_index","duplicate_model","flags","trick","grid_cell","ctris","tags","extra","truncated_record"};
 for(unsigned i=0;i<15;i++){
  CHECK(snprintf(name,sizeof(name),"%s/%s.geo",argv[1],kinds[i])>0);s=load(name);l=mount(&s);q=request(&s);b.external_bytes=s.size;
  CohStatus want=(i==6||i==7||i>=9)?COH_INVALID:COH_UNSUPPORTED;
  CHECK(coh_wr_rigid_acquire(l,&q,&b,(CohCancel){0},&r)==want&&!r);CHECK(coh_asset_stats(l).pinned_blobs==0&&pins==releases);CHECK(coh_asset_destroy(&l)==COH_OK);free(s.data);
 }
 authentic=1;s=load(argv[2]);CHECK(s.size==3684);l=mount(&s);q=request(&s);b.external_bytes=s.size;
 static const uint8_t pin[32]={0x83,0x93,0x3b,0x54,0xdb,0x37,0x3b,0xf8,0x3e,0x0a,0x73,0xf1,0x28,0x06,0x8b,0x63,0xb8,0x37,0x5e,0x00,0xf0,0xf2,0x88,0xb6,0xf6,0xe0,0xe0,0x63,0x77,0x92,0xc9,0xe7};CHECK(!memcmp(q.geo_sha256,pin,32));
 CHECK(coh_wr_rigid_acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);CHECK(coh_wr_rigid_report(r,&report)==COH_OK&&report.geo_version==0&&report.vertices==90&&report.triangles==56&&report.parts==1);packet(r,argv[4]);coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);coh_wr_rigid_release(&r);CHECK(!r&&pins==releases);CHECK(coh_asset_destroy(&l)==COH_OK);free(s.data);
 printf("{\"passed\":true,\"checks\":%u,\"legacy_version\":0,\"malformed_legacy_cases\":15,\"authentic_vertices\":90,\"authentic_triangles\":56,\"pins_balanced\":true,\"material_fixture_only\":true,\"loaded_generation_fixture_only\":true,\"same_source_generation_established\":false,\"world_authority\":false}\n",checks);
}
