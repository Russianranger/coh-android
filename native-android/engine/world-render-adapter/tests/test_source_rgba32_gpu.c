/* Standalone qualification only: real source owners and GL, fixture sampler
 * and provider catalog. No application/current/default/material/world permit. */
#include "coh_gpu_egl_backend.c"
#include "../coh_wr_gpu_lease.h"
#include <stdio.h>
#include <stdatomic.h>
static unsigned checks,live_blocks,failed_allocation;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"source_gpu:%d:%s\n",__LINE__,#v);exit(1);}}while(0)
static void *blocks[256];
void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_calloc(size_t n,size_t z){
 if(failed_allocation){failed_allocation=0;return NULL;}
 void*p=__real_calloc(n,z);if(p){unsigned i=0;while(i<256&&blocks[i])i++;if(i==256)abort();blocks[i]=p;live_blocks++;}return p;
}
void __wrap_free(void*p){if(p)for(unsigned i=0;i<256;i++)if(blocks[i]==p){blocks[i]=NULL;live_blocks--;break;}__real_free(p);}
typedef struct {const char*name,*path;const uint8_t*data;size_t size;uint8_t sha256[32];} SourceFixture;
#include "source_rgba32_fixture.h"
typedef struct {uint8_t*bytes[3];unsigned holds,hold_calls,drop_calls,reads,retired;} Provider;
typedef struct {Provider*owner;unsigned index;} FileSource;
static CohStatus source_read(void*v,uint64_t at,void*out,size_t size){
 FileSource*f=v;Provider*p=f->owner;if(!p->holds||p->retired||at>source_fixtures[f->index].size||size>source_fixtures[f->index].size-at)return COH_STATE;
 p->reads++;memcpy(out,p->bytes[f->index]+(size_t)at,size);return COH_OK;
}
static CohStatus source_hold(void*v){Provider*p=v;if(p->retired)return COH_STATE;p->holds++;p->hold_calls++;return COH_OK;}
static void source_drop(void*v){Provider*p=v;CHECK(p->holds>0);p->holds--;p->drop_calls++;}
static CohStatus fixture_digest(void*v,CohBytes bytes,uint8_t sha[32]){
 (void)v;for(unsigned i=0;i<3;i++)if(bytes.size==source_fixtures[i].size&&!memcmp(bytes.data,source_fixtures[i].data,bytes.size)){memcpy(sha,source_fixtures[i].sha256,32);return COH_OK;}return COH_INVALID;
}
static void source_open(Provider*p,char**paths){for(unsigned i=0;i<3;i++){
 FILE*f=fopen(paths[i],"rb");CHECK(f);p->bytes[i]=malloc(source_fixtures[i].size);CHECK(p->bytes[i]);
 CHECK(fread(p->bytes[i],1,source_fixtures[i].size,f)==source_fixtures[i].size&&fgetc(f)==EOF&&fclose(f)==0);
 CHECK(!memcmp(p->bytes[i],source_fixtures[i].data,source_fixtures[i].size));
}}
static void source_retire(Provider*p){CHECK(!p->holds&&!p->retired);for(unsigned i=0;i<3;i++){memset(p->bytes[i],0,source_fixtures[i].size);free(p->bytes[i]);p->bytes[i]=NULL;}p->retired=1;}
typedef struct {
 CohGpuEglBackend*egl;CohWrGpuOps base;atomic_uint pins,retains,releases;
 CohWrGpuToken gate_token,cleanup_token;CohWrGpuJournal*pending;
 unsigned gate,cleanup,fail_delete,images,deleted,generated;
} Registry;
static int same_token(CohWrGpuToken a,CohWrGpuToken b){return a.surface_generation==b.surface_generation&&a.context_generation==b.context_generation&&a.render_thread==b.render_thread;}
static CohStatus normal(Registry*r){if(!owner(r->egl)||r->gate||(r->pending&&r->pending->pending))return COH_STATE;return r->base.current(r->base.context,token(r->egl));}
static CohStatus s_current(void*v,CohWrGpuToken t){Registry*r=v;return normal(r)==COH_OK?r->base.current(r->base.context,t):COH_STATE;}
static CohStatus s_retire(void*v,CohWrGpuToken t){Registry*r=v;if(!owner(r->egl)||(r->gate&&!same_token(t,r->gate_token)))return COH_STATE;CohStatus s=r->base.retire_current(r->base.context,t);if(s==COH_OK){r->cleanup_token=t;r->cleanup=1;}return s;}
static CohStatus s_dead(void*v,CohWrGpuToken t){Registry*r=v;return r->base.destroyed(r->base.context,t);}
static CohStatus s_integer(void*v,uint32_t p,int32_t*out){Registry*r=v;return normal(r)==COH_OK?r->base.get_integer(r->base.context,p,out):COH_STATE;}
static CohStatus s_generate(void*v,uint32_t*out){Registry*r=v;if(normal(r)!=COH_OK)return COH_STATE;CohStatus s=r->base.generate(r->base.context,out);if(*out)r->generated++;return s;}
static CohStatus cleanup_or_normal(Registry*r){if(r->cleanup){r->cleanup=0;return r->base.retire_current(r->base.context,r->cleanup_token);}return normal(r);}
static CohStatus s_bind(void*v,uint32_t n){Registry*r=v;return cleanup_or_normal(r)==COH_OK?r->base.bind_texture(r->base.context,n):COH_STATE;}
static CohStatus s_buffer(void*v,uint32_t n){Registry*r=v;return cleanup_or_normal(r)==COH_OK?r->base.bind_unpack_buffer(r->base.context,n):COH_STATE;}
static CohStatus s_pixel(void*v,uint32_t p,int32_t n){Registry*r=v;return cleanup_or_normal(r)==COH_OK?r->base.pixel_store(r->base.context,p,n):COH_STATE;}
static CohStatus s_image(void*v,uint32_t l,uint32_t w,uint32_t h,CohBytes b){Registry*r=v;if(normal(r)!=COH_OK)return COH_STATE;CohStatus s=r->base.image_rgba8(r->base.context,l,w,h,b);r->images++;return s;}
static CohStatus s_parameter(void*v,uint32_t p,int32_t n){Registry*r=v;return normal(r)==COH_OK?r->base.parameter(r->base.context,p,n):COH_STATE;}
static CohStatus s_delete(void*v,uint32_t*n){Registry*r=v;if(!r->cleanup||cleanup_or_normal(r)!=COH_OK)return COH_STATE;if(r->fail_delete)return COH_IO;CohStatus s=r->base.delete_texture(r->base.context,n);if(!*n)r->deleted++;return s;}
static CohStatus s_retain(void*v){Registry*r=v;atomic_fetch_add(&r->pins,1);atomic_fetch_add(&r->retains,1);return COH_OK;}
static void s_release(void*v){Registry*r=v;CHECK(atomic_load(&r->pins)>0);atomic_fetch_sub(&r->pins,1);atomic_fetch_add(&r->releases,1);}
static CohStatus s_gate(void*v,CohWrGpuToken t){Registry*r=v;if(!owner(r->egl)||r->gate||(r->pending&&r->pending->pending)||r->base.retire_current(r->base.context,t)!=COH_OK)return COH_STATE;r->gate=1;r->gate_token=t;return COH_OK;}
static CohStatus s_end(void*v,CohWrGpuToken t){Registry*r=v;if(!owner(r->egl)||!r->gate||!same_token(t,r->gate_token))return COH_STATE;r->gate=0;r->cleanup=0;return COH_OK;}
static CohWrGpuLeaseBackend backend(Registry*r){return(CohWrGpuLeaseBackend){{r,s_current,s_retire,s_dead,s_integer,s_generate,s_bind,s_buffer,s_pixel,s_image,s_parameter,s_delete},s_retain,s_release,s_gate,s_end};}
static CohWrSamplerSource sampler(uint32_t w,uint32_t h,uint32_t n){return(CohWrSamplerSource){0,0x0de1,w,h,n>1?n:0,n,1,1.0f};}
typedef struct {unsigned at,calls;} CancelPoint;
static int cancellation(void*v){CancelPoint*c=v;return ++c->calls==c->at;}
static void saved_state(Registry*r,int32_t out[6]){const uint32_t p[]={0x8069,0x88ef,0x0cf5,0x0cf2,0x0cf3,0x0cf4};for(unsigned i=0;i<6;i++)CHECK(s_integer(r,p[i],out+i)==COH_OK);}
static unsigned rgba_controls(CohWrTexRgba32*cpu,Registry*r,CohWrGpuLeaseBackend*b,CohWrGpuLimits limits,CohWrSamplerSource*s){
 CohWrTexRgba32View view;CHECK(coh_wr_tex_rgba32_view(cpu,&view)==COH_OK);CohWrGpuTexture*out=NULL;CohWrGpuJournal j={0};unsigned before=r->generated;
 CohWrGpuLimits low=limits;low.external_bytes=view.aggregate_reserved_bytes-1;
 CHECK(coh_wr_gpu_upload_rgba32(cpu,s,token(r->egl),&b->gpu,&low,(CohCancel){0},&out,&j)==COH_LIMIT&&!out&&!j.pending&&r->generated==before);
 CHECK(coh_wr_gpu_upload_rgba32(cpu,s,token(r->egl),&b->gpu,&limits,(CohCancel){0},(CohWrGpuTexture**)&limits,&j)==COH_INVALID);
 CHECK(coh_wr_gpu_upload_rgba32(cpu,s,token(r->egl),&b->gpu,&limits,(CohCancel){0},&out,(CohWrGpuJournal*)(uintptr_t)view.mips[0].rgba.data)==COH_INVALID);
 CHECK(coh_wr_gpu_upload_rgba32(cpu,(const CohWrSamplerSource*)(uintptr_t)view.mips[0].rgba.data,token(r->egl),&b->gpu,&limits,(CohCancel){0},&out,&j)==COH_INVALID);
 failed_allocation=1;CHECK(coh_wr_gpu_upload_rgba32(cpu,s,token(r->egl),&b->gpu,&limits,(CohCancel){0},&out,&j)==COH_LIMIT&&!out&&!j.pending);
 unsigned cancelled=0;for(unsigned at=1;at<=view.mip_count+2;at++){
  int32_t old[6],after[6];saved_state(r,old);CancelPoint c={at,0};r->pending=&j;
  CHECK(coh_wr_gpu_upload_rgba32(cpu,s,token(r->egl),&b->gpu,&limits,(CohCancel){cancellation,&c},&out,&j)==COH_CANCELLED&&!out&&!j.pending&&!j.name&&!j.restore_needed);
  r->pending=NULL;saved_state(r,after);CHECK(!memcmp(old,after,sizeof(old)));cancelled++;
 }
 int32_t old[6],after[6];saved_state(r,old);r->pending=&j;r->fail_delete=1;r->egl->fault_image=1;
 CHECK(coh_wr_gpu_upload_rgba32(cpu,s,token(r->egl),&b->gpu,&limits,(CohCancel){0},&out,&j)==COH_STATE&&!out&&j.pending&&j.name);
 uint32_t doomed=j.name;CHECK(normal(r)==COH_STATE);r->fail_delete=0;
 CHECK(coh_wr_gpu_retry_cleanup(&j,&b->gpu)==COH_OK&&!j.pending&&!j.name&&!j.restore_needed);r->pending=NULL;
 CHECK(glIsTexture(doomed)==GL_FALSE&&glGetError()==GL_NO_ERROR);saved_state(r,after);CHECK(!memcmp(old,after,sizeof(old)));
 return cancelled;
}
enum {W_ATTACH=1,W_HOLD,W_DROP,W_RETIRE,W_DRAIN,W_COLLECT,W_QUIT};
typedef struct {pthread_t thread;pthread_mutex_t mutex;pthread_cond_t condition;unsigned command,done;CohStatus result;CohWrGpuLease*lease;CohWrPresentationResources resources;} Control;
static void*control(void*v){Control*c=v;pthread_mutex_lock(&c->mutex);for(;;){while(!c->command)pthread_cond_wait(&c->condition,&c->mutex);unsigned command=c->command;pthread_mutex_unlock(&c->mutex);CohStatus s=COH_STATE;
 if(command==W_ATTACH)s=coh_wr_gpu_lease_resources(c->lease,&c->resources);
 if(command==W_HOLD)s=c->resources.hold(c->resources.context);
 if(command==W_DROP){c->resources.drop(c->resources.context);s=COH_OK;}
 if(command==W_RETIRE)s=coh_wr_gpu_lease_retire(c->lease);
 if(command==W_DRAIN)s=coh_wr_gpu_lease_drain(c->lease);
 if(command==W_COLLECT)s=coh_wr_gpu_lease_collect(&c->lease);
 pthread_mutex_lock(&c->mutex);c->result=s;c->command=0;c->done=1;pthread_cond_broadcast(&c->condition);if(command==W_QUIT)break;
 }pthread_mutex_unlock(&c->mutex);return NULL;}
static CohStatus command(Control*c,unsigned what){pthread_mutex_lock(&c->mutex);c->done=0;c->command=what;pthread_cond_broadcast(&c->condition);while(!c->done)pthread_cond_wait(&c->condition,&c->mutex);CohStatus s=c->result;pthread_mutex_unlock(&c->mutex);return s;}
/* sizeof-only ABI probe of the exact pre-tranche private field layout at
 * e54ceb26c. No instance is constructed or treated as a GPU owner. */
typedef struct {CohWrGpuToken token;CohWrTextureReport source;size_t gpu_reservation,aggregate_reserved_bytes;uint32_t uploaded_levels;} PriorGpuReportLayout;
typedef struct {PriorGpuReportLayout report;CohRenderTexture texture;CohWrGpuOps operations;char path[COH_ASSET_PATH_MAX+1];} PriorGpuOwnerLayout;
typedef struct {uint32_t count,w[15],h[15];size_t bytes[15],offset[15],total;uint8_t data[1024];} Expected;
static void capture_expected(Expected*e,const CohWrTexRgba32View*v){e->count=v->mip_count;for(uint32_t i=0;i<e->count;i++){e->w[i]=v->mips[i].width;e->h[i]=v->mips[i].height;e->bytes[i]=v->mips[i].rgba.size;e->offset[i]=e->total;CHECK(e->bytes[i]<=sizeof(e->data)-e->total);memcpy(e->data+e->total,v->mips[i].rgba.data,e->bytes[i]);e->total+=e->bytes[i];}}
static void probe_read(Registry*r,uint32_t name,unsigned level,uint32_t w,uint32_t h,uint8_t*out){
 GLint saved[7];const GLenum names[]={GL_DRAW_FRAMEBUFFER_BINDING,GL_READ_FRAMEBUFFER_BINDING,GL_PIXEL_PACK_BUFFER_BINDING,GL_PACK_ALIGNMENT,GL_PACK_ROW_LENGTH,GL_PACK_SKIP_ROWS,GL_PACK_SKIP_PIXELS};
 CHECK(normal(r)==COH_OK);for(unsigned i=0;i<7;i++)glGetIntegerv(names[i],saved+i);CHECK(glGetError()==GL_NO_ERROR);
 GLuint fbo=0;glGenFramebuffers(1,&fbo);CHECK(fbo&&glGetError()==GL_NO_ERROR);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,name,(GLint)level);CHECK(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE&&glGetError()==GL_NO_ERROR);
 glBindBuffer(GL_PIXEL_PACK_BUFFER,0);glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_PACK_ROW_LENGTH,0);glPixelStorei(GL_PACK_SKIP_ROWS,0);glPixelStorei(GL_PACK_SKIP_PIXELS,0);CHECK(glGetError()==GL_NO_ERROR);
 glReadPixels(0,0,(GLsizei)w,(GLsizei)h,GL_RGBA,GL_UNSIGNED_BYTE,out);CHECK(glGetError()==GL_NO_ERROR);
 glBindFramebuffer(GL_DRAW_FRAMEBUFFER,(GLuint)saved[0]);glBindFramebuffer(GL_READ_FRAMEBUFFER,(GLuint)saved[1]);glDeleteFramebuffers(1,&fbo);glBindBuffer(GL_PIXEL_PACK_BUFFER,(GLuint)saved[2]);for(unsigned i=3;i<7;i++)glPixelStorei(names[i],saved[i]);CHECK(glGetError()==GL_NO_ERROR);
}
static unsigned read_chain(Registry*r,const CohWrGpuTexture*gpu,const Expected*e,FILE*out){
 uint8_t pixels[1024];for(uint32_t i=0;i<e->count;i++){CohRenderTexture view;CohWrGpuLeaseBackend b=backend(r);CHECK(coh_wr_gpu_view(gpu,token(r->egl),&b.gpu,&view)==COH_OK);probe_read(r,view.handle,i,e->w[i],e->h[i],pixels);CHECK(!memcmp(pixels,e->data+e->offset[i],e->bytes[i]));CHECK(fwrite(pixels,1,e->bytes[i],out)==e->bytes[i]);}return e->count;
}
static void json_string(const char*s){putchar('"');for(;*s;s++){unsigned c=(unsigned char)*s;if(c=='"'||c=='\\')putchar('\\');if(c>=32&&c<127)putchar((int)c);else printf("\\u%04x",c);}putchar('"');}
int main(int argc,char**argv){
 CHECK(argc==5);Provider provider={0};source_open(&provider,argv+1);FileSource files[3]={{&provider,0},{&provider,1},{&provider,2}};CohWrTexNamespaceFile entries[3];
 for(unsigned i=0;i<3;i++)entries[i]=(CohWrTexNamespaceFile){source_fixtures[i].path,0,0,{source_read,files+i,source_fixtures[i].size,7}};
 CohWrTexNamespaceRoot root={entries,3,7,"/standalone-controlled-complete-three-file-provider/data"};
 CohWrTexNamespaceRequest q={0};q.roots=&root;q.root_count=1;q.input_generation=41;q.mode=2;q.development_data=1;q.digest=fixture_digest;q.provider_hold=source_hold;q.provider_drop=source_drop;q.provider_context=&provider;
 CohAssetLimits asset_limits={262144,16384,4096,4096,8,8,8};
 CohWrTexNamespaceLimits ns_limits={1048576,16u<<20,262144,asset_limits,16,64,8,4};CohWrTexNamespace*ns=NULL;
 CHECK(coh_wr_tex_namespace_build(&q,&ns_limits,(CohCancel){0},&ns)==COH_OK&&provider.holds==1);
 CohWrTexNamespaceReport ns_report;CHECK(coh_wr_tex_namespace_report(ns,&ns_report)==COH_OK&&ns_report.basic_rows==3);
 CohWrTexRgba32*cpu[2]={0};Expected expected[3]={0};CohWrTexRgba32View views[2];
 for(unsigned i=0;i<2;i++){CohWrTexNamespaceBasic row;CHECK(coh_wr_tex_namespace_find(ns,i?"pattern":"grey",&row)==COH_OK);CHECK(!memcmp(row.sha256,source_fixtures[i].sha256,32));CohWrTexRgba32Limits l={1048576,16u<<20,ns_report.aggregate_reserved_bytes+262144};CHECK(coh_wr_tex_rgba32_build(ns,row.row,0,&l,(CohCancel){0},cpu+i)==COH_OK);CHECK(coh_wr_tex_rgba32_view(cpu[i],views+i)==COH_OK);capture_expected(expected+i,views+i);}
 Registry registry={0};CHECK(coh_gpu_egl_create(&registry.egl)==COH_OK);registry.base=registry.egl->ops;CohWrGpuLeaseBackend ops=backend(&registry);CohWrGpuToken t=token(registry.egl);
 CohWrGpuTexture*gpu[3]={0};CohWrGpuReport reports[3];uint32_t names[3];FILE*readback=fopen(argv[4],"wb");CHECK(readback);unsigned readbacks=0,cancelled=0;
 /* A real legacy owner smoke establishes kind0 and unchanged entry behavior.
  * Its own provider hold is balanced before the whole provider is retired. */
 CHECK(source_hold(&provider)==COH_OK);CohAssetLoader*loader=NULL;CHECK(coh_asset_create(&asset_limits,&loader)==COH_OK);CHECK(coh_asset_mount_file(loader,source_fixtures[2].path,entries[2].bytes)==COH_OK);
 CohWrTextureRequest request={{source_fixtures[2].path,7},{0},fixture_digest,NULL};memcpy(request.sha256,source_fixtures[2].sha256,32);CohWrTextureLimits legacy_limits={16u<<20,1048576,262144,4096,64,15};CohWrTextureResource*legacy=NULL;
 CHECK(coh_wr_texture_acquire(loader,&request,&legacy_limits,(CohCancel){0},&legacy)==COH_OK);uint32_t w,h;CohBytes rgba;CHECK(coh_wr_texture_mip(legacy,0,&w,&h,&rgba)==COH_OK);expected[2].count=1;expected[2].w[0]=w;expected[2].h[0]=h;expected[2].bytes[0]=expected[2].total=rgba.size;CHECK(rgba.size<=1024);memcpy(expected[2].data,rgba.data,rgba.size);
 CohWrSamplerSource legacy_sampler=sampler(w,h,1);CohWrGpuLimits limits={64u<<20,32u<<20,4096,64};CohWrGpuJournal journal={0};
 CohWrGpuLimits legacy_small=limits;legacy_small.aggregate_limit=limits.external_bytes+limits.gpu_reservation+sizeof(PriorGpuOwnerLayout);
 CHECK(coh_wr_gpu_upload(legacy,&legacy_sampler,t,&ops.gpu,&legacy_small,(CohCancel){0},gpu+2,&journal)==COH_LIMIT&&!gpu[2]&&!journal.pending&&!registry.generated);
 CHECK(coh_wr_gpu_upload(legacy,&legacy_sampler,t,&ops.gpu,&limits,(CohCancel){0},gpu+2,&journal)==COH_OK&&!journal.pending);CHECK(coh_wr_gpu_report(gpu[2],reports+2)==COH_OK&&reports[2].source_kind==COH_WR_GPU_SOURCE_LEGACY_DXT&&reports[2].source.format==1&&reports[2].owner_bytes>sizeof(PriorGpuOwnerLayout));
 readbacks+=read_chain(&registry,gpu[2],expected+2,readback);coh_wr_texture_release(&legacy);CHECK(coh_asset_destroy(&loader)==COH_OK);source_drop(&provider);
 CHECK(coh_wr_tex_namespace_destroy(&ns)==COH_OK&&!ns&&provider.holds==0);source_retire(&provider);
 for(unsigned i=0;i<2;i++){
  CohWrTexRgba32View v;CHECK(provider.retired&&coh_wr_tex_rgba32_view(cpu[i],&v)==COH_OK);CHECK(!memcmp(v.sha256,source_fixtures[i].sha256,32)&&!strcmp(v.asset.path,source_fixtures[i].path));CohWrSamplerSource sample=sampler(v.mips[0].width,v.mips[0].height,v.mip_count);
  if(!i)cancelled=rgba_controls(cpu[i],&registry,&ops,limits,&sample);
  CHECK(coh_wr_gpu_upload_rgba32(cpu[i],&sample,t,&ops.gpu,&limits,(CohCancel){0},gpu+i,&journal)==COH_OK&&!journal.pending);
  CHECK(coh_wr_gpu_report(gpu[i],reports+i)==COH_OK&&reports[i].source_kind==COH_WR_GPU_SOURCE_NAMESPACE_RGBA32&&reports[i].source.format==0&&reports[i].source.cached_texopt_flags==0&&reports[i].source.loader_reservation==0&&reports[i].source.external_bytes==0);
  CHECK(reports[i].rgba32.aggregate_reserved_bytes==v.aggregate_reserved_bytes&&reports[i].rgba32.row==v.source_row&&reports[i].rgba32.input_generation==v.source_input_generation&&reports[i].owner_bytes==reports[2].owner_bytes);
  CHECK(reports[i].aggregate_reserved_bytes==limits.external_bytes+limits.gpu_reservation+reports[i].owner_bytes+COH_WR_GPU_RGBA32_PREPARATION_RESERVE);
  readbacks+=read_chain(&registry,gpu[i],expected+i,readback);CHECK(coh_wr_tex_rgba32_destroy(cpu+i)==COH_OK&&!cpu[i]);
 }
 CohWrGpuLeaseInput input[3];for(unsigned i=0;i<3;i++){CohAssetId id;CohRenderTexture texture;CHECK(coh_wr_gpu_identity(gpu[i],&id)==COH_OK&&coh_wr_gpu_view(gpu[i],t,&ops.gpu,&texture)==COH_OK);names[i]=texture.handle;input[i]=(CohWrGpuLeaseInput){11u+11u*i,id,{0},gpu+i};memcpy(input[i].source_sha256,source_fixtures[i].sha256,32);}
 Control c={0};CohWrGpuLeaseLimits lease_limits={96u<<20,48u<<20,3*reports[0].owner_bytes,65536};input[0].source_sha256[0]^=1;
 CHECK(coh_wr_gpu_lease_adopt(input,3,&ops,&lease_limits,(CohCancel){0},&c.lease)==COH_STATE&&!c.lease&&gpu[0]&&gpu[1]&&gpu[2]);input[0].source_sha256[0]^=1;
 CHECK(coh_wr_gpu_lease_adopt(input,3,&ops,&lease_limits,(CohCancel){0},&c.lease)==COH_OK&&!gpu[0]&&!gpu[1]&&!gpu[2]&&atomic_load(&registry.pins)==1);
 CHECK(!pthread_mutex_init(&c.mutex,NULL)&&!pthread_cond_init(&c.condition,NULL)&&!pthread_create(&c.thread,NULL,control,&c));CHECK(command(&c,W_ATTACH)==COH_OK&&command(&c,W_HOLD)==COH_OK);
 /* All CPU/source/provider storage has retired. Resolve and exact GL readback
  * use only the immutable GPU lease and actual context/thread registry. */
 const unsigned order[]={2,0,1};for(unsigned k=0;k<3;k++){unsigned i=order[k];uint32_t name=0;CHECK(c.resources.resolve(c.resources.context,11+11*i,7,(uint32_t)t.surface_generation,&name)==COH_OK&&name==names[i]);
  uint8_t pixels[1024];for(unsigned level=0;level<expected[i].count;level++){
   probe_read(&registry,name,level,expected[i].w[level],expected[i].h[level],pixels);CHECK(!memcmp(pixels,expected[i].data+expected[i].offset[level],expected[i].bytes[level]));CHECK(fwrite(pixels,1,expected[i].bytes[level],readback)==expected[i].bytes[level]);readbacks++;
  }
 }
 CHECK(!fclose(readback));CHECK(command(&c,W_RETIRE)==COH_OK&&command(&c,W_HOLD)==COH_STATE);unsigned deleted=registry.deleted;
 CHECK(coh_wr_gpu_lease_drain(c.lease)==COH_STATE&&registry.deleted==deleted);CHECK(command(&c,W_DROP)==COH_OK&&command(&c,W_DRAIN)==COH_STATE&&registry.deleted==deleted);
 registry.fail_delete=1;CHECK(coh_wr_gpu_lease_drain(c.lease)==COH_IO&&registry.gate&&normal(&registry)==COH_STATE);CHECK(command(&c,W_COLLECT)==COH_STATE&&atomic_load(&registry.pins)==1);
 registry.fail_delete=0;CHECK(coh_wr_gpu_lease_drain(c.lease)==COH_OK&&!registry.gate);for(unsigned i=0;i<3;i++)CHECK(glIsTexture(names[i])==GL_FALSE);CHECK(glGetError()==GL_NO_ERROR);
 CHECK(command(&c,W_COLLECT)==COH_OK&&!c.lease&&!atomic_load(&registry.pins));(void)command(&c,W_QUIT);CHECK(!pthread_join(c.thread,NULL));pthread_cond_destroy(&c.condition);pthread_mutex_destroy(&c.mutex);
 CHECK(provider.hold_calls==2&&provider.drop_calls==2&&atomic_load(&registry.retains)==1&&atomic_load(&registry.releases)==1&&cancelled==6&&registry.images==20&&readbacks==18&&registry.generated==9&&registry.deleted==9);
 CohGpuEglReport report;CHECK(coh_gpu_egl_destroy_contexts(registry.egl)==COH_OK&&coh_gpu_egl_report(registry.egl,&report)==COH_OK);CHECK(report.contexts_created==1&&report.contexts_destroyed==1&&report.surfaces_created==1&&report.surfaces_destroyed==1);CHECK(coh_gpu_egl_close(&registry.egl)==COH_OK&&!registry.egl&&!live_blocks);
 printf("{\"schema\":\"coh-source-rgba32-gpu-v1\",\"passed\":true,\"checks\":%u,\"actual_gles\":true,\"cleanup_verified\":true,\"rgba32_uploads\":2,\"legacy_uploads\":1,\"images\":20,\"readbacks\":18,\"cancelled_uploads\":6,\"pending_journal_recovered\":true,\"provider_holds\":2,\"provider_drops\":2,\"source_retired_before_rgba32_upload\":true,\"all_cpu_retired_before_lease_readback\":true,\"registry_retains\":1,\"registry_releases\":1,\"generated\":9,\"deleted\":9,\"tracked_calloc_blocks_live\":0,\"gpu_owner_bytes\":%zu,\"gpu_report_bytes\":%zu,\"prior_gpu_owner_bytes\":%zu,\"gpu_owner_growth_bytes\":%zu,\"rgba32_preparation_reserve\":16384,\"gpu_external_reservation\":33554432,\"lease_external_reservation\":50331648,\"contexts_created\":1,\"contexts_destroyed\":1,\"surfaces_created\":1,\"surfaces_destroyed\":1,\"finite_fixture_digest_only\":true,\"sampler_fixture_only\":true,\"provider_fixture_only\":true,\"current_namespace\":false,\"default_identity\":false,\"material_authority\":false,\"actor_authority\":false,\"world_authority\":false,\"source_generation_admitted\":false,\"production_prepare_executed\":false,\"app_context_adopted\":false,\"gl_version\":",checks,reports[0].owner_bytes,sizeof(CohWrGpuReport),sizeof(PriorGpuOwnerLayout),reports[0].owner_bytes-sizeof(PriorGpuOwnerLayout));json_string(report.gl_version);printf(",\"gl_renderer\":");json_string(report.gl_renderer);puts("}");return 0;
}
