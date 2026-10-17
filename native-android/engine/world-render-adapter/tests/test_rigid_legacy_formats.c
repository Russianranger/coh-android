/* Exact authentic v2/v3/v4 CPU grammar; fixture material callbacks only. */
#include "../coh_wr_rigid_legacy_formats.h"
#include "../coh_wr_rigid_source.h"
#include "../coh_wr_rigid_v5.h"
#include "../coh_wr_rigid_v7.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,pins,releases,bad_material;static long fail_at=-1,allocations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"v234 line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){if(fail_at>=0&&allocations++==fail_at)return NULL;return __real_malloc(n);}
void *__wrap_calloc(size_t n,size_t s){if(fail_at>=0&&allocations++==fail_at)return NULL;return __real_calloc(n,s);}
void __wrap_free(void*p){__real_free(p);}
typedef struct {uint32_t texture,triangles;const char*name;} ExpectedPart;
typedef struct {uint32_t version;const char*path,*model;uint32_t vertices,triangles,parts;ExpectedPart material[7];} Fixture;
#include "rigid_legacy_formats_pins.inc"
static const Fixture*current;
typedef CohStatus(*Acquire)(CohAssetLoader*,const CohWrRigidRequest*,const CohWrRigidLimits*,CohCancel,CohWrRigidResource**);
static const Acquire exact[]={coh_wr_rigid_v2_acquire,coh_wr_rigid_v3_acquire,coh_wr_rigid_v4_acquire};
typedef struct {uint8_t*data;size_t size;} Source;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_IO;memcpy(d,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
static CohStatus material(void*v,CohAssetId id,const char*model,uint32_t part,const CohAssetGeoMaterial*src,CohWrRigidMaterial*out){
 (void)v;CHECK(id.generation==17&&!strcmp(id.path,current->path)&&!strcmp(model,current->model)&&part<current->parts);uint32_t first=0;for(uint32_t p=0;p<part;p++)first+=current->material[p].triangles;CHECK(src->texture_id==current->material[part].texture&&src->first_triangle==first&&src->triangle_count==current->material[part].triangles&&!strcmp(src->texture_name,current->material[part].name));
 memset(out,0,sizeof(*out));out->material=coh_renderer_default_material(COH_MAT_DUAL);for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++)out->uv_scale[i][j]=1;out->texture_id[0]=11;out->texture_id[1]=12;out->geometry_id=100+part;out->generation=19;memset(out->source_sha256,1,32);out->pin=&pins;out->unsupported_semantics=bad_material;pins++;return COH_OK;
}
static void release(void*v,void*p){(void)v;CHECK(p==&pins);releases++;}
static int after_material(void*v){(void)v;return pins>releases;}
static Source load(const char*p){FILE*f=fopen(p,"rb");CHECK(f&&!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<1024*1024);rewind(f);Source s={malloc((size_t)n),(size_t)n};CHECK(s.data&&fread(s.data,1,s.size,f)==s.size&&!fclose(f));return s;}
static CohAssetLoader*mount(Source*s){CohAssetLoader*l=NULL;CohAssetLimits b={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&b,&l)==COH_OK);CHECK(coh_asset_mount_file(l,current->path,(CohAssetSource){readat,s,s->size,17})==COH_OK);return l;}
static CohWrRigidRequest request(Source*s){CohWrRigidRequest q={{current->path,17},current->model,{0},19,digest,NULL,material,release,NULL};digest(NULL,(CohBytes){s->data,s->size},q.geo_sha256);return q;}
static void clean(CohAssetLoader**l,Source*s){CHECK(pins==releases&&coh_asset_stats(*l).pinned_blobs==0);CHECK(coh_asset_destroy(l)==COH_OK);free(s->data);}
static void packet(CohWrRigidResource*r,const char*path){CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK);FILE*f=fopen(path,"wb");CHECK(f);for(uint32_t p=0;p<report.parts;p++){CohRenderGeometry g;CohWrRigidMaterial m;CHECK(coh_wr_rigid_part(r,p,&g,&m)==COH_OK);CHECK(fwrite(g.vertices,sizeof(*g.vertices),g.vertex_count,f)==g.vertex_count&&fwrite(g.indices,sizeof(*g.indices),g.index_count,f)==g.index_count);}CHECK(!fclose(f));}
int main(int argc,char**argv){
 CHECK(argc==4);unsigned allocation_failures=0,mutations=0;
 for(unsigned k=0;k<sizeof(fixtures)/sizeof(fixtures[0]);k++){
  current=&fixtures[k];Acquire acquire=exact[current->version-2];char path[8192];CHECK(snprintf(path,sizeof(path),"%s/%s",argv[1],current->path)>0);Source s=load(path);CohAssetLoader*l=mount(&s);CohWrRigidResource*r=NULL;CohWrRigidRequest q=request(&s);CohWrRigidLimits b={16u<<20,s.size,8u<<20,2u<<20,2u<<20,128,65536,65536,64};unsigned before=pins;
  CHECK(coh_wr_rigid_acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);CHECK(coh_wr_rigid_source_acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);CHECK(coh_wr_rigid_v5_acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);CHECK(coh_wr_rigid_v7_acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);for(unsigned other=0;other<3;other++)if(other!=current->version-2)CHECK(exact[other](l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);
  CHECK(acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);CohWrRigidReport report;CHECK(coh_wr_rigid_report(r,&report)==COH_OK&&report.geo_version==current->version&&report.vertices==current->vertices&&report.triangles==current->triangles&&report.parts==current->parts&&report.aggregate_peak_bytes<=b.aggregate_limit&&report.loader_reservation==b.loader_reservation);CHECK(snprintf(path,sizeof(path),"%s/%u.packet",argv[2],k)>0);packet(r,path);CohWrRigidResource*old=r;CHECK(acquire(l,&q,&b,(CohCancel){0},&r)==COH_STATE&&r==old);coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);coh_wr_rigid_release(&r);CHECK(!r&&pins==releases);before=pins;
  q.model="absent";CHECK(acquire(l,&q,&b,(CohCancel){0},&r)==COH_NOT_FOUND&&!r&&pins==before);q=request(&s);q.geo_sha256[0]^=1;CHECK(acquire(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&pins==before);q=request(&s);q.geo.generation=18;CHECK(acquire(l,&q,&b,(CohCancel){0},&r)==COH_NOT_FOUND&&!r&&pins==before);q=request(&s);
  CohWrRigidLimits tight=b;tight.max_vertices=1;CHECK(acquire(l,&q,&tight,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);tight=b;tight.max_parts=current->parts-1;CHECK(acquire(l,&q,&tight,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);tight=b;tight.max_workspace_bytes=1;CHECK(acquire(l,&q,&tight,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);tight=b;tight.max_stream_bytes=1;CHECK(acquire(l,&q,&tight,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);tight=b;tight.aggregate_limit=tight.external_bytes+tight.loader_reservation;CHECK(acquire(l,&q,&tight,(CohCancel){0},&r)==COH_LIMIT&&!r&&pins==before);
  bad_material=1;CHECK(acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==releases);bad_material=0;CHECK(acquire(l,&q,&b,(CohCancel){after_material,NULL},&r)==COH_CANCELLED&&!r&&pins==releases);
  unsigned failures=0;for(long a=0;a<64;a++){coh_asset_trim(l);fail_at=a;allocations=0;CohStatus st=acquire(l,&q,&b,(CohCancel){0},&r);fail_at=-1;if(st==COH_OK){coh_wr_rigid_release(&r);break;}CHECK(!r&&pins==releases&&coh_asset_stats(l).pinned_blobs==0);failures++;}CHECK(failures>4&&failures<64);allocation_failures+=failures;clean(&l,&s);
  const char*names[]={"bad-channel","bad-pack","bad-lod","nan-lod","short-lod","duplicate-model","wrong-layout","unsupported-pivot"};for(unsigned m=0;m<8;m++){
   CHECK(snprintf(path,sizeof(path),"%s/%u-%s.geo",argv[3],k,names[m])>0);s=load(path);l=mount(&s);q=request(&s);b.external_bytes=s.size;before=pins;CohStatus st=acquire(l,&q,&b,(CohCancel){0},&r);if(m==6)CHECK(st!=COH_OK);else CHECK(st==((m==3||m==7)?COH_UNSUPPORTED:COH_INVALID));CHECK(!r&&pins==before);clean(&l,&s);mutations++;
  }
  if(current->version==2){CHECK(snprintf(path,sizeof(path),"%s/%u-legacy-flags.geo",argv[3],k)>0);s=load(path);l=mount(&s);q=request(&s);b.external_bytes=s.size;before=pins;CHECK(acquire(l,&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&pins==before);clean(&l,&s);mutations++;}
  if(current->version==4){CHECK(snprintf(path,sizeof(path),"%s/%u-obsolete-slots.geo",argv[3],k)>0);s=load(path);l=mount(&s);q=request(&s);b.external_bytes=s.size;CHECK(acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);CHECK(snprintf(path,sizeof(path),"%s/%u-skipped.packet",argv[2],k)>0);packet(r,path);coh_wr_rigid_release(&r);clean(&l,&s);mutations++;}
 }
 printf("{\"passed\":true,\"checks\":%u,\"authentic_cases\":%zu,\"versions\":[2,3,4],\"allocation_failure_stages\":%u,\"grammar_controls\":%u,\"fixture_materials_only\":true,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks,sizeof(fixtures)/sizeof(fixtures[0]),allocation_failures,mutations);
}
