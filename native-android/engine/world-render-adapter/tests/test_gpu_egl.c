#include "coh_gpu_egl_backend.h"
#include <GLES3/gl3.h>
#ifdef COH_EGL_FIXTURE_DIGEST
#include "egl_fixture_digest.h"
#define SHA256 coh_egl_fixture_digest
#else
#include <openssl/sha.h>
#endif
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __ANDROID__
#define PLATFORM "android"
#else
#define PLATFORM "host-linux"
#endif
static unsigned checks;static int failure_line;
#define CHECK(x) do{checks++;if(!(x)){failure_line=__LINE__;goto cleanup;}}while(0)
typedef struct {uint8_t*data;size_t size;} Source;
static CohStatus readat(void*v,uint64_t o,void*d,size_t n){Source*s=v;if(o>s->size||n>s->size-o)return COH_IO;memcpy(d,s->data+(size_t)o,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes bytes,uint8_t out[32]){(void)v;return SHA256(bytes.data,bytes.size,out)?COH_OK:COH_INVALID;}
static const GLenum state_names[]={GL_TEXTURE_BINDING_2D,GL_PIXEL_UNPACK_BUFFER_BINDING,GL_UNPACK_ALIGNMENT,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_ROWS,GL_UNPACK_SKIP_PIXELS};
static int capture(GLint out[6]){for(unsigned i=0;i<6;i++)glGetIntegerv(state_names[i],out+i);return glGetError()==GL_NO_ERROR;}
typedef struct {CohGpuEglBackend*backend;CohWrGpuTexture*gpu;CohWrGpuToken token;CohStatus result;} Thread;
static void*wrong_thread(void*v){Thread*t=v;CohRenderTexture out;t->result=coh_gpu_egl_view(t->backend,t->gpu,t->token,&out);return NULL;}
static void string(const char*p){putchar('"');for(;*p;p++){unsigned c=(unsigned char)*p;if(c=='"'||c=='\\'){putchar('\\');putchar((int)c);}else if(c>=32&&c<127)putchar((int)c);else printf("\\u%04x",c);}putchar('"');}
int main(int argc,char**argv){
 CohAssetLoader*loader=NULL;CohWrTextureResource*cpu=NULL;CohGpuEglBackend*backend=NULL;CohWrGpuTexture*gpu[3]={0};
 Source source={0};FILE*input=NULL,*packet=NULL;uint8_t*readback=NULL;unsigned cleanup_ok=0;CohGpuEglReport report={0};uint32_t old_name=0,new_name=0;
 CHECK(argc==3);input=fopen(argv[1],"rb");CHECK(input);source.size=43990;source.data=malloc(source.size);CHECK(source.data);CHECK(fread(source.data,1,source.size,input)==source.size);CHECK(fgetc(input)==EOF);CHECK(!fclose(input));input=NULL;
 CohAssetLimits asset_limits={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&asset_limits,&loader)==COH_OK);
 const char*path="data/texture_library/npcs/objects/praetorian_box/box-1.texture";CHECK(coh_asset_mount_file(loader,path,(CohAssetSource){readat,&source,source.size,17})==COH_OK);
 CohWrTextureRequest request={{path,17},{0},digest,NULL};CHECK(digest(NULL,(CohBytes){source.data,source.size},request.sha256)==COH_OK);
 CohWrTextureLimits cpu_limits={16u<<20,source.size,8u<<20,1u<<20,1024,16};CHECK(coh_wr_texture_acquire(loader,&request,&cpu_limits,(CohCancel){0},&cpu)==COH_OK);
 CohWrTextureReport cpureport;CHECK(coh_wr_texture_report(cpu,&cpureport)==COH_OK&&cpureport.levels==9&&cpureport.rgba_bytes==349524);
 CHECK(coh_gpu_egl_create(&backend)==COH_OK);CohGpuEglBackend*duplicate=NULL;CHECK(coh_gpu_egl_create(&duplicate)==COH_STATE&&!duplicate);CohWrGpuToken initial;CHECK(coh_gpu_egl_token(backend,&initial)==COH_OK);
 /* Explicit fixture effective sampler values, NOT inferred CLIENT authority. */
 CohWrSamplerSource sampler={192,GL_TEXTURE_2D,256,256,9,9,1,1.f};CohWrGpuLimits limits={16u<<20,cpureport.aggregate_peak_bytes+(2u<<20),cpureport.rgba_bytes,1024};
 GLuint sentinel_texture=0,sentinel_buffer=0;glGenTextures(1,&sentinel_texture);glBindTexture(GL_TEXTURE_2D,sentinel_texture);glGenBuffers(1,&sentinel_buffer);glBindBuffer(GL_PIXEL_UNPACK_BUFFER,sentinel_buffer);glBufferData(GL_PIXEL_UNPACK_BUFFER,16,NULL,GL_STATIC_DRAW);
 glPixelStorei(GL_UNPACK_ALIGNMENT,8);glPixelStorei(GL_UNPACK_ROW_LENGTH,17);glPixelStorei(GL_UNPACK_SKIP_ROWS,3);glPixelStorei(GL_UNPACK_SKIP_PIXELS,5);CHECK(glGetError()==GL_NO_ERROR);
 GLint before[6],after[6];CHECK(capture(before));
 /* Real driver error must cause refusal rather than silently clearing it. */
 glPixelStorei(0xffffffffu,0);CHECK(coh_gpu_egl_upload(backend,cpu,&sampler,&limits,&gpu[0])==COH_IO&&!gpu[0]);CHECK(capture(after)&&!memcmp(before,after,sizeof(before)));
 packet=fopen(argv[2],"wb");CHECK(packet);readback=malloc(256u*256u*4u);CHECK(readback);
 for(unsigned stage=0;stage<3;stage++){
   CHECK(coh_gpu_egl_upload(backend,cpu,&sampler,&limits,&gpu[stage])==COH_OK);CHECK(capture(after));if(stage<2)CHECK(!memcmp(before,after,sizeof(before)));
   CohWrGpuToken current;CHECK(coh_gpu_egl_token(backend,&current)==COH_OK);CohRenderTexture texture;CHECK(coh_gpu_egl_view(backend,gpu[stage],current,&texture)==COH_OK);
   if(stage==0)old_name=texture.handle;
   if(stage==2)new_name=texture.handle;
   for(unsigned level=0;level<9;level++){
     uint32_t w,h;CohBytes rgba;CHECK(coh_wr_texture_mip(cpu,level,&w,&h,&rgba)==COH_OK);
     CHECK(coh_gpu_egl_readback(backend,gpu[stage],level,readback,rgba.size)==COH_OK);CHECK(!memcmp(readback,rgba.data,rgba.size));CHECK(fwrite(readback,1,rgba.size,packet)==rgba.size);
   }
   Thread t={backend,gpu[stage],current,COH_OK};pthread_t thread;CHECK(!pthread_create(&thread,NULL,wrong_thread,&t));CHECK(!pthread_join(thread,NULL));CHECK(t.result==COH_STATE);
   if(stage==0){
     /* A real context with an intentionally failed candidate deletion retains
      * its journal. ALL other GL work, including existing-owner release, refuses. */
     glBindTexture(GL_TEXTURE_2D,texture.handle);CHECK(glGetError()==GL_NO_ERROR);
     CohWrGpuTexture*failed=NULL;CHECK(coh_gpu_egl_test_faults(backend,1,0)==COH_OK);
     CHECK(coh_gpu_egl_upload(backend,cpu,&sampler,&limits,&failed)==COH_IO&&!failed);
     CHECK(coh_gpu_egl_view(backend,gpu[0],current,&texture)==COH_OK);CohGpuEglReport rollback;CHECK(coh_gpu_egl_report(backend,&rollback)==COH_OK&&!rollback.pending_cleanup&&rollback.gpu_owners==1);
     CHECK(coh_gpu_egl_test_faults(backend,1,1)==COH_OK);
     CHECK(coh_gpu_egl_upload(backend,cpu,&sampler,&limits,&failed)==COH_STATE&&!failed);
     CHECK(coh_gpu_egl_release(backend,&gpu[0])==COH_STATE&&gpu[0]);
     CHECK(coh_gpu_egl_view(backend,gpu[0],current,&texture)==COH_STATE);
     CHECK(coh_gpu_egl_readback(backend,gpu[0],0,readback,256u*256u*4u)==COH_STATE);
     CHECK(coh_gpu_egl_replace_surface(backend)==COH_STATE);
     CHECK(coh_gpu_egl_upload(backend,cpu,&sampler,&limits,&failed)==COH_STATE&&!failed);
     CHECK(coh_gpu_egl_test_faults(backend,0,0)==COH_OK);CHECK(coh_gpu_egl_retry_cleanup(backend)==COH_OK);
     glBindTexture(GL_TEXTURE_2D,sentinel_texture);CHECK(glGetError()==GL_NO_ERROR);
     CHECK(coh_gpu_egl_replace_surface(backend)==COH_OK);CohWrGpuToken replacement;CHECK(coh_gpu_egl_token(backend,&replacement)==COH_OK&&replacement.surface_generation!=current.surface_generation&&replacement.context_generation==current.context_generation);
     CHECK(coh_gpu_egl_view(backend,gpu[0],current,&texture)==COH_STATE);CHECK(coh_gpu_egl_release(backend,&gpu[0])==COH_OK&&!gpu[0]);
   }
   if(stage==1){
     CHECK(coh_gpu_egl_replace_context(backend)==COH_OK);CohWrGpuToken replacement;CHECK(coh_gpu_egl_token(backend,&replacement)==COH_OK&&replacement.context_generation!=current.context_generation);
     CHECK(coh_gpu_egl_view(backend,gpu[1],current,&texture)==COH_STATE);CHECK(coh_gpu_egl_release(backend,&gpu[1])==COH_OK&&!gpu[1]);
   }
 }
 CHECK(!fclose(packet));packet=NULL;coh_wr_texture_release(&cpu);CHECK(!cpu&&coh_asset_stats(loader).pinned_blobs==0);
 CohWrGpuToken current;CohRenderTexture texture;CHECK(coh_gpu_egl_token(backend,&current)==COH_OK);CHECK(coh_gpu_egl_view(backend,gpu[2],current,&texture)==COH_OK);
 CHECK(coh_gpu_egl_release(backend,&gpu[2])==COH_OK&&!gpu[2]);CHECK(coh_gpu_egl_destroy_contexts(backend)==COH_OK);
 CHECK(coh_gpu_egl_report(backend,&report)==COH_OK&&report.contexts_created==2&&report.contexts_destroyed==2&&report.surfaces_created==3&&report.surfaces_destroyed==3&&report.readbacks==27&&!report.gpu_owners&&!report.pending_cleanup);
 CHECK(coh_gpu_egl_close(&backend)==COH_OK&&!backend);CHECK(coh_asset_destroy(&loader)==COH_OK&&!loader);cleanup_ok=1;
cleanup:
 if(packet)fclose(packet);
 if(input)fclose(input);
 free(readback);
 if(backend){(void)coh_gpu_egl_destroy_contexts(backend);for(unsigned i=0;i<3;i++)(void)coh_gpu_egl_release(backend,gpu+i);(void)coh_gpu_egl_close(&backend);}
 coh_wr_texture_release(&cpu);if(loader)(void)coh_asset_destroy(&loader);free(source.data);
 printf("{\"passed\":%s,\"checks\":%u,\"failure_line\":%d,\"cleanup_verified\":%s,\"gles_major\":%u,\"contexts_created\":%u,\"contexts_destroyed\":%u,\"surfaces_created\":%u,\"surfaces_destroyed\":%u,\"readbacks\":%u,\"levels_per_upload\":9,\"rgba_bytes_per_upload\":349524,\"context_name_reused\":%s,\"gl_version\":",failure_line?"false":"true",checks,failure_line,cleanup_ok?"true":"false",report.gles_major,report.contexts_created,report.contexts_destroyed,report.surfaces_created,report.surfaces_destroyed,report.readbacks,old_name&&old_name==new_name?"true":"false");string(report.gl_version);printf(",\"gl_renderer\":");string(report.gl_renderer);printf(",\"platform\":");string(PLATFORM);printf(",\"generation_fixture_only\":true,\"sampler_fixture_only\":true,\"material_authority\":false,\"world_authority\":false}\n");return failure_line?1:0;
}
