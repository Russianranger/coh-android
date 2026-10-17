/* Exact authentic texture owner with explicitly fixture-only source generation. */
#include "../coh_wr_texture.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,reads;static int fail_after=-1;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"owner line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void*,size_t);void __real_free(void*);
static int deny(void){if(fail_after<0)return 0;if(!fail_after)return 1;fail_after--;return 0;}
void *__wrap_malloc(size_t n){return deny()?NULL:__real_malloc(n);}
void *__wrap_calloc(size_t n,size_t z){return deny()?NULL:__real_calloc(n,z);}
void *__wrap_realloc(void*p,size_t n){return deny()?NULL:__real_realloc(p,n);}
void __wrap_free(void*p){__real_free(p);}
typedef struct {uint8_t*bytes;size_t size;} Source;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;reads++;if(o>s->size||n>s->size-o)return COH_IO;memcpy(d,s->bytes+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){if(v)return COH_IO;SHA256(b.data,b.size,out);return COH_OK;}
static int cancel_at(void*v){return (*(int*)v)--==0;}
int main(int argc,char**argv){
 CHECK(argc==3);FILE*f=fopen(argv[1],"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n==43990);rewind(f);
 Source source={malloc((size_t)n),(size_t)n};CHECK(source.bytes);CHECK(fread(source.bytes,1,source.size,f)==source.size);CHECK(!fclose(f));
 CohAssetLoader*l=NULL;CohAssetLimits al={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&al,&l)==COH_OK);
 const char*path="data/texture_library/npcs/objects/praetorian_box/box-1.texture";
 CHECK(coh_asset_mount_file(l,path,(CohAssetSource){readat,&source,source.size,17})==COH_OK);
 CohWrTextureRequest q={{path,17},{0},digest,NULL};CHECK(digest(NULL,(CohBytes){source.bytes,source.size},q.sha256)==COH_OK);
 static const uint8_t pin[32]={0xc3,0x60,0x01,0x85,0x4f,0x75,0xff,0x7e,0x8e,0xf5,0x30,0x41,0x38,0x53,0x7f,0x1d,0xe4,0xb7,0x1d,0xcc,0x35,0x29,0xa9,0xa4,0x0f,0x60,0x93,0xfd,0xe9,0x59,0xdf,0x9a};CHECK(!memcmp(q.sha256,pin,32));
 CohWrTextureLimits b={16u<<20,source.size,8u<<20,1u<<20,1024,16};CohWrTextureResource*r=NULL;
 CohWrTextureLimits tiny=b;tiny.aggregate_limit=1;unsigned before=reads;CHECK(coh_wr_texture_acquire(l,&q,&tiny,(CohCancel){0},&r)==COH_LIMIT&&!r&&reads==before);
 fail_after=0;CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_LIMIT&&!r);fail_after=-1;CHECK(coh_asset_stats(l).pinned_blobs==0);
 CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);CohWrTextureResource*original=r;
 CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_STATE&&r==original);
 CohWrTextureReport report;CHECK(coh_wr_texture_report(r,&report)==COH_OK);CHECK(report.width==256&&report.height==256&&report.levels==9&&report.format==1&&report.rgba_bytes==349524&&report.cached_texopt_flags==192);
 CHECK(report.owned_bytes>report.rgba_bytes&&report.aggregate_peak_bytes==b.external_bytes+b.loader_reservation+report.owned_bytes);
 CohAssetId id;CHECK(coh_wr_texture_identity(r,&id)==COH_OK&&id.generation==17&&!strcmp(id.path,path));
 coh_asset_trim(l);CHECK(coh_asset_stats(l).pinned_blobs==1);CHECK(coh_asset_destroy(&l)==COH_STATE);
 f=fopen(argv[2],"wb");CHECK(f);
 for(unsigned i=0;i<report.levels;i++){
   uint32_t w,h;CohBytes rgba;CHECK(coh_wr_texture_mip(r,i,&w,&h,&rgba)==COH_OK);CHECK(w==(256u>>i)&&h==w&&rgba.size==(size_t)w*h*4);
   CHECK(fwrite(rgba.data,1,rgba.size,f)==rgba.size);
 }
 CHECK(!fclose(f));uint32_t w=7,h=8;CohBytes bytes={(const uint8_t*)"sentinel",8},old=bytes;
 CHECK(coh_wr_texture_mip(r,9,&w,&h,&bytes)==COH_INVALID&&w==7&&h==8&&bytes.data==old.data&&bytes.size==old.size);
 coh_wr_texture_release(&r);CHECK(!r&&coh_asset_stats(l).pinned_blobs==0);
 b.aggregate_limit=report.aggregate_peak_bytes;CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_OK);coh_wr_texture_release(&r);
 b.aggregate_limit--;CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_LIMIT&&!r&&coh_asset_stats(l).pinned_blobs==0);b.aggregate_limit=16u<<20;
 q.sha256[0]^=1;CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r);q.sha256[0]^=1;
 q.digest_context=&checks;CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_IO&&!r);q.digest_context=NULL;
 q.asset.path="DATA/texture_library/npcs/objects/praetorian_box/box-1.texture";CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r);q.asset.path=path;
 q.asset.generation=18;CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)!=COH_OK&&!r);q.asset.generation=17;
 q.asset.generation=0;CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r);q.asset.generation=17;
#define LIMIT(field,value) do{CohWrTextureLimits bad=b;bad.field=value;CHECK(coh_wr_texture_acquire(l,&q,&bad,(CohCancel){0},&r)==COH_LIMIT&&!r);CHECK(coh_asset_stats(l).pinned_blobs==0);}while(0)
 LIMIT(loader_reservation,1);LIMIT(max_rgba_bytes,349523);LIMIT(max_dimension,255);LIMIT(max_levels,8);LIMIT(external_bytes,SIZE_MAX);LIMIT(max_levels,33);
 fail_after=0;CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==COH_LIMIT&&!r);fail_after=-1;CHECK(coh_asset_stats(l).pinned_blobs==0);
 for(int i=0;i<25;i++){
   int counter=i;CohStatus status=coh_wr_texture_acquire(l,&q,&b,(CohCancel){cancel_at,&counter},&r);
   CHECK(status==COH_OK||status==COH_CANCELLED);coh_wr_texture_release(&r);CHECK(!r&&coh_asset_stats(l).pinned_blobs==0);
 }
 CHECK(coh_asset_destroy(&l)==COH_OK);
 /* Explicitly corrupted test copies, each rehashed to test parser rollback
  * after digest admission; never authentic source/material claims. */
 for(unsigned kind=0;kind<3;kind++){
   Source bad={malloc(source.size),source.size};CHECK(bad.bytes);memcpy(bad.bytes,source.bytes,source.size);
   uint32_t hs=(uint32_t)bad.bytes[0]|(uint32_t)bad.bytes[1]<<8|(uint32_t)bad.bytes[2]<<16|(uint32_t)bad.bytes[3]<<24;
   if(kind==0)bad.bytes[hs+84]=0; /* unsupported FOURCC */
   if(kind==1)bad.bytes[8]^=1; /* wrapper/DDS dimensions disagree */
   if(kind==2)bad.bytes[hs+28]=10; /* impossible declared mip count */
   CHECK(coh_asset_create(&al,&l)==COH_OK);CHECK(coh_asset_mount_file(l,path,(CohAssetSource){readat,&bad,bad.size,17})==COH_OK);
   CHECK(digest(NULL,(CohBytes){bad.bytes,bad.size},q.sha256)==COH_OK);
   CHECK(coh_wr_texture_acquire(l,&q,&b,(CohCancel){0},&r)==(kind==0?COH_UNSUPPORTED:COH_INVALID)&&!r);
   CHECK(coh_asset_stats(l).pinned_blobs==0);CHECK(coh_asset_destroy(&l)==COH_OK);free(bad.bytes);
 }
 free(source.bytes);
 printf("{\"passed\":true,\"checks\":%u,\"levels\":9,\"rgba_bytes\":349524,\"pins_balanced\":true,\"generation_fixture_only\":true,\"material_authority\":false}\n",checks);
}
