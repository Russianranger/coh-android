/* GLES callback model only; no Android, GL driver, material or world execution. */
#include "../coh_wr_gpu_texture.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;static int fail_calloc;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"GPU line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_calloc(size_t,size_t);
void*__wrap_calloc(size_t n,size_t s){return fail_calloc?NULL:__real_calloc(n,s);}
typedef struct {uint8_t*data;size_t size;} Source;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_IO;memcpy(d,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;SHA256(b.data,b.size,out);return COH_OK;}
static CohWrGpuToken oldtoken={1,11,111},newtoken={2,22,111};
static int equal(CohWrGpuToken a,CohWrGpuToken b){return a.surface_generation==b.surface_generation&&a.context_generation==b.context_generation&&a.render_thread==b.render_thread;}
typedef struct {
 CohWrGpuToken current;unsigned calls,fail_at,lose_at,fail_delete,consume_error,old_dead;
 int32_t state[2][6];unsigned next[2],live[2][64],images,deleted;
 int32_t parameters[4],max_texture;const CohWrTextureResource*cpu;
} Mock;
static unsigned index_context(Mock*m){return m->current.context_generation==oldtoken.context_generation?0:1;}
static CohStatus current(void*v,CohWrGpuToken t){Mock*m=v;if(m->lose_at&&m->calls+1==m->lose_at){m->current=newtoken;m->lose_at=0;}return equal(m->current,t)?COH_OK:COH_STATE;}
static CohStatus retire_current(void*v,CohWrGpuToken t){Mock*m=v;if(m->lose_at&&m->calls+1==m->lose_at){m->current=newtoken;m->lose_at=0;}return m->current.context_generation==t.context_generation&&m->current.render_thread==t.render_thread?COH_OK:COH_STATE;}
static CohStatus destroyed(void*v,CohWrGpuToken t){Mock*m=v;return equal(t,oldtoken)&&m->old_dead?COH_OK:COH_STATE;}
static CohStatus tick(Mock*m){m->calls++;return m->calls==m->fail_at?COH_IO:COH_OK;}
static int state_index(uint32_t p){switch(p){case 0x8069:return 0;case 0x88ef:return 1;case 0xcf5:return 2;case 0xcf2:return 3;case 0xcf3:return 4;case 0xcf4:return 5;default:return -1;}}
static CohStatus get(void*v,uint32_t p,int32_t*out){Mock*m=v;CohStatus s=tick(m);if(s!=COH_OK)return s;if(p==0xd33){*out=m->max_texture;return COH_OK;}int i=state_index(p);CHECK(i>=0);*out=m->state[index_context(m)][i];return COH_OK;}
static CohStatus generate(void*v,uint32_t*out){Mock*m=v;unsigned c=index_context(m),n=++m->next[c];CHECK(n<64&&!m->live[c][n]);m->live[c][n]=1;*out=n;return tick(m);}
static CohStatus bind(void*v,uint32_t name){Mock*m=v;m->state[index_context(m)][0]=(int32_t)name;return tick(m);}
static CohStatus buffer(void*v,uint32_t name){Mock*m=v;m->state[index_context(m)][1]=(int32_t)name;return tick(m);}
static CohStatus pixel(void*v,uint32_t p,int32_t value){Mock*m=v;int i=state_index(p);CHECK(i>=2);m->state[index_context(m)][i]=value;return tick(m);}
static CohStatus image(void*v,uint32_t level,uint32_t w,uint32_t h,CohBytes bytes){
 Mock*m=v;unsigned c=index_context(m);CHECK(m->state[c][0]>0&&m->live[c][m->state[c][0]]);CHECK(!m->state[c][1]&&m->state[c][2]==1&&!m->state[c][3]&&!m->state[c][4]&&!m->state[c][5]);
 uint32_t rw,rh;CohBytes rgba;CHECK(coh_wr_texture_mip(m->cpu,level,&rw,&rh,&rgba)==COH_OK);CHECK(rw==w&&rh==h&&rgba.size==bytes.size&&!memcmp(rgba.data,bytes.data,bytes.size));m->images++;return tick(m);
}
static CohStatus parameter(void*v,uint32_t p,int32_t value){Mock*m=v;unsigned i=p==0x2802?0:p==0x2803?1:p==0x2801?2:p==0x2800?3:99;CHECK(i<4);m->parameters[i]=value;return tick(m);}
static CohStatus delete_name(void*v,uint32_t*name){Mock*m=v;unsigned c=index_context(m);CHECK(*name>0&&*name<64&&m->live[c][*name]);CohStatus s=tick(m);if(m->fail_delete)return COH_IO;if(s!=COH_OK&&!m->consume_error)return s;m->live[c][*name]=0;m->deleted++;*name=0;return s;}
static CohWrGpuOps operations(Mock*m){return(CohWrGpuOps){m,current,retire_current,destroyed,get,generate,bind,buffer,pixel,image,parameter,delete_name};}
static Mock fresh(const CohWrTextureResource*cpu){Mock m={0};m.current=oldtoken;m.cpu=cpu;m.max_texture=4096;for(unsigned c=0;c<2;c++){int32_t initial[]={51,52,8,17,3,5};memcpy(m.state[c],initial,sizeof(initial));}return m;}
static void clean_state(Mock*m){int32_t initial[]={51,52,8,17,3,5};CHECK(!memcmp(m->state[0],initial,sizeof(initial)));for(unsigned c=0;c<2;c++)for(unsigned n=1;n<64;n++)CHECK(!m->live[c][n]);}
static int cancel_at(void*v){return (*(int*)v)--==0;}
int main(int argc,char**argv){
 CHECK(argc==2);FILE*f=fopen(argv[1],"rb");CHECK(f);Source source={malloc(43990),43990};CHECK(source.data);CHECK(fread(source.data,1,source.size,f)==source.size);CHECK(!fclose(f));
 CohAssetLimits al={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CohAssetLoader*l=NULL;CHECK(coh_asset_create(&al,&l)==COH_OK);
 const char*path="data/texture_library/npcs/objects/praetorian_box/box-1.texture";CHECK(coh_asset_mount_file(l,path,(CohAssetSource){readat,&source,source.size,17})==COH_OK);
 CohWrTextureRequest request={{path,17},{0},digest,NULL};CHECK(digest(NULL,(CohBytes){source.data,source.size},request.sha256)==COH_OK);
 CohWrTextureLimits cpu_limits={16u<<20,source.size,8u<<20,1u<<20,1024,16};CohWrTextureResource*cpu=NULL;CHECK(coh_wr_texture_acquire(l,&request,&cpu_limits,(CohCancel){0},&cpu)==COH_OK);
 CohWrTextureReport cpureport;CHECK(coh_wr_texture_report(cpu,&cpureport)==COH_OK);
 CohWrGpuLimits limits={16u<<20,cpureport.aggregate_peak_bytes,cpureport.rgba_bytes,1024};CohWrSamplerSource sampler={192,0xde1,256,256,9,9,1,1.f};
 Mock m=fresh(cpu);CohWrGpuOps ops=operations(&m);CohWrGpuTexture*gpu=NULL;CohWrGpuJournal journal={0};
 CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_OK);unsigned upload_calls=m.calls;
 CHECK(gpu&&!journal.pending&&m.images==9&&m.parameters[0]==0x812f&&m.parameters[1]==0x812f&&m.parameters[2]==0x2703&&m.parameters[3]==0x2601);
 CohWrGpuReport report;CHECK(coh_wr_gpu_report(gpu,&report)==COH_OK&&report.uploaded_levels==9&&report.source.rgba_bytes==349524&&equal(report.token,oldtoken));
 CohAssetId id;CHECK(coh_wr_gpu_identity(gpu,&id)==COH_OK&&!strcmp(id.path,path)&&id.generation==17);
 CohRenderTexture view;CHECK(coh_wr_gpu_view(gpu,oldtoken,&ops,&view)==COH_OK&&view.handle==1&&view.min_filter==COH_FILTER_MIP_LINEAR);
 CohWrGpuTexture*before=gpu;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_STATE&&gpu==before);
 CohWrGpuToken wrong=oldtoken;wrong.render_thread++;CohRenderTexture sentinel=view;CHECK(coh_wr_gpu_view(gpu,wrong,&ops,&view)==COH_STATE&&!memcmp(&view,&sentinel,sizeof(view)));
 wrong=oldtoken;wrong.surface_generation++;CHECK(coh_wr_gpu_view(gpu,wrong,&ops,&view)==COH_STATE);
 Mock other=fresh(cpu);CohWrGpuOps wrongops=operations(&other);CHECK(coh_wr_gpu_release(&gpu,&wrongops)==COH_STATE&&gpu==before);
 m.current=newtoken;unsigned called=m.calls;CHECK(coh_wr_gpu_release(&gpu,&ops)==COH_STATE&&gpu==before&&m.calls==called);CHECK(coh_wr_gpu_view(gpu,oldtoken,&ops,&view)==COH_STATE);CHECK(coh_wr_gpu_discard_destroyed(&gpu,&ops)==COH_STATE&&gpu==before);
 m.current=oldtoken;m.current.surface_generation=2;CHECK(coh_wr_gpu_view(gpu,oldtoken,&ops,&view)==COH_STATE);
 CHECK(coh_wr_gpu_release(&gpu,&ops)==COH_OK&&!gpu);
 CohWrGpuToken replacement_surface=m.current;CHECK(coh_wr_gpu_upload(cpu,&sampler,replacement_surface,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_OK);
 CHECK(coh_wr_gpu_view(gpu,replacement_surface,&ops,&view)==COH_OK&&view.handle==2);CHECK(coh_wr_gpu_view(gpu,oldtoken,&ops,&view)==COH_STATE);CHECK(coh_wr_gpu_release(&gpu,&ops)==COH_OK&&!gpu);m.current=oldtoken;clean_state(&m);
 /* Every query/mutation/restore callback failure must leave no partial owner.
  * Generated partial names and mutation-after-error paths are exercised. */
 for(unsigned i=1;i<=upload_calls;i++){
   m=fresh(cpu);ops=operations(&m);m.fail_at=i;memset(&journal,0,sizeof(journal));
   CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_IO&&!gpu&&!journal.pending);clean_state(&m);
 }
 /* Persistent deletion failure retains exact old-context ownership. */
 m=fresh(cpu);ops=operations(&m);m.fail_at=15;m.fail_delete=1;
 CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_STATE&&!gpu&&journal.pending&&journal.name);
 called=m.calls;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_STATE&&m.calls==called);
 CHECK(coh_wr_gpu_retry_cleanup(&journal,&wrongops)==COH_STATE&&journal.pending);
 m.fail_delete=0;CHECK(coh_wr_gpu_retry_cleanup(&journal,&ops)==COH_OK&&!journal.pending);clean_state(&m);
 /* Loss at each phase cannot touch the replacement context's names/state. */
 for(unsigned i=8;i<=upload_calls+1;i++){
   m=fresh(cpu);ops=operations(&m);m.lose_at=i;
   CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_STATE&&!gpu);
   if(journal.pending){
     unsigned deletes=m.deleted;CHECK(coh_wr_gpu_retry_cleanup(&journal,&ops)==COH_STATE&&m.deleted==deletes);
     CHECK(coh_wr_gpu_discard_destroyed_journal(&journal,&ops)==COH_STATE&&journal.pending);
     m.current=oldtoken;CHECK(coh_wr_gpu_retry_cleanup(&journal,&ops)==COH_OK&&!journal.pending);clean_state(&m);
   }
 }
 /* Verified context destruction drops old names without deleting reused IDs. */
 m=fresh(cpu);ops=operations(&m);m.lose_at=15;
 CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_STATE&&journal.pending);
 m.old_dead=1;memset(m.live[0],0,sizeof(m.live[0]));CHECK(coh_wr_gpu_discard_destroyed_journal(&journal,&ops)==COH_OK&&!journal.pending);
 CHECK(coh_wr_gpu_upload(cpu,&sampler,newtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_OK);CHECK(coh_wr_gpu_view(gpu,newtoken,&ops,&view)==COH_OK&&view.handle==1);CHECK(coh_wr_gpu_view(gpu,oldtoken,&ops,&view)==COH_STATE);
 coh_wr_texture_release(&cpu);CHECK(!cpu&&coh_asset_stats(l).pinned_blobs==0);CHECK(coh_wr_gpu_view(gpu,newtoken,&ops,&view)==COH_OK);CHECK(coh_wr_gpu_release(&gpu,&ops)==COH_OK&&!gpu);
 /* Recreate CPU fixture for budget/cancellation and verified-dead ready owner. */
 CHECK(coh_wr_texture_acquire(l,&request,&cpu_limits,(CohCancel){0},&cpu)==COH_OK);
 m=fresh(cpu);ops=operations(&m);CohWrGpuLimits exact=limits;exact.aggregate_limit=report.aggregate_reserved_bytes;
 CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&exact,(CohCancel){0},&gpu,&journal)==COH_OK);CHECK(coh_wr_gpu_release(&gpu,&ops)==COH_OK);
 exact.aggregate_limit--;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&exact,(CohCancel){0},&gpu,&journal)==COH_LIMIT&&!gpu);
 m=fresh(cpu);ops=operations(&m);m.max_texture=128;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_LIMIT&&!gpu);clean_state(&m);
 m=fresh(cpu);ops=operations(&m);m.state[0][2]=3;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_INVALID&&!gpu&&!m.next[0]);
 m=fresh(cpu);ops=operations(&m);CohWrSamplerSource mismatch=sampler;mismatch.width=128;CHECK(coh_wr_gpu_upload(cpu,&mismatch,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_INVALID&&!m.calls);
 CohWrGpuLimits bad=limits;bad.aggregate_limit=1;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&bad,(CohCancel){0},&gpu,&journal)==COH_LIMIT&&!m.calls);
 bad=limits;bad.gpu_reservation--;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&bad,(CohCancel){0},&gpu,&journal)==COH_LIMIT&&!m.calls);
 bad=limits;bad.external_bytes=SIZE_MAX;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&bad,(CohCancel){0},&gpu,&journal)==COH_LIMIT&&!m.calls);
 fail_calloc=1;CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_LIMIT&&!gpu);fail_calloc=0;clean_state(&m);
 for(int i=0;i<13;i++){
   m=fresh(cpu);ops=operations(&m);int counter=i;CohStatus status=coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){cancel_at,&counter},&gpu,&journal);
   CHECK(status==COH_OK||status==COH_CANCELLED);CHECK(!journal.pending);CHECK(coh_wr_gpu_release(&gpu,&ops)==COH_OK);clean_state(&m);
 }
 m=fresh(cpu);ops=operations(&m);CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_OK);
 m.current=newtoken;m.old_dead=1;memset(m.live[0],0,sizeof(m.live[0]));CHECK(coh_wr_gpu_discard_destroyed(&gpu,&wrongops)==COH_STATE&&gpu);called=m.calls;CHECK(coh_wr_gpu_discard_destroyed(&gpu,&ops)==COH_OK&&!gpu&&m.calls==called);
 m=fresh(cpu);ops=operations(&m);CHECK(coh_wr_gpu_upload(cpu,&sampler,oldtoken,&ops,&limits,(CohCancel){0},&gpu,&journal)==COH_OK);
 m.fail_at=m.calls+1;m.consume_error=1;CHECK(coh_wr_gpu_release(&gpu,&ops)==COH_IO&&gpu);CHECK(coh_wr_gpu_view(gpu,oldtoken,&ops,&view)==COH_STATE);CHECK(coh_wr_gpu_release(&gpu,&ops)==COH_OK&&!gpu);clean_state(&m);
 coh_wr_texture_release(&cpu);CHECK(coh_asset_destroy(&l)==COH_OK);free(source.data);
 printf("{\"passed\":true,\"checks\":%u,\"callback_failure_positions\":%u,\"uploaded_levels\":9,\"injected_gles_only\":true,\"android_execution\":false,\"material_authority\":false}\n",checks,upload_calls);
}
