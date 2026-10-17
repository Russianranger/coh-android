#include "coh_gpu_egl_backend.h"
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#define CONTEXTS 4
#define SURFACES 8
#define ES3_BIT 0x0040
/* Handles/generations are recorded only after successful owned EGL creation.
 * Actual EGL current handles and pthread owner are checked at each GL call.
 * Public wrappers enforce one journal/whole-context quarantine. */
typedef struct {EGLContext handle;uint64_t generation,min_surface,max_surface;
 unsigned dead;} Context;
typedef struct {EGLSurface handle;
 unsigned dead;uint64_t context_generation,generation;} Surface;
struct CohGpuEglBackend {
 EGLDisplay display;
 EGLConfig config;pthread_t thread;uint64_t thread_token;
 Context contexts[CONTEXTS];Surface surfaces[SURFACES];
 unsigned active_context,active_surface,mode,initialized,fault_image,fault_delete;
 CohWrGpuJournal journal;
 CohWrGpuOps ops;
 CohGpuEglReport report;
};
static atomic_uint_fast64_t nonce=1;
static atomic_flag claimed=ATOMIC_FLAG_INIT;
static uint64_t next(void){return atomic_fetch_add(&nonce,1);}
static int owner(CohGpuEglBackend*b){return b&&pthread_equal(b->thread,pthread_self());}
static CohWrGpuToken token(CohGpuEglBackend*b){Context*c=b->contexts+b->active_context;
 return(CohWrGpuToken){c->max_surface,c->generation,b->thread_token};}
static Context*find(CohGpuEglBackend*b,CohWrGpuToken t){
 if(t.render_thread!=b->thread_token)return NULL;
 int surface=0;
 for(unsigned i=0;i<b->report.surfaces_created;i++)if(b->surfaces[i].context_generation==t.context_generation&&b->surfaces[i].generation==t.surface_generation)surface=1;
 if(!surface)return NULL;
 for(unsigned i=0;i<b->report.contexts_created;i++)if(b->contexts[i].generation==t.context_generation)return b->contexts+i;
 return NULL;
}
static CohStatus actual(CohGpuEglBackend*b){
 if(!owner(b)||!b->report.contexts_created||!b->report.surfaces_created)return COH_STATE;
 Context*c=b->contexts+b->active_context;
 Surface*s=b->surfaces+b->active_surface;
 if(c->dead||s->dead||eglGetCurrentDisplay()!=b->display||eglGetCurrentContext()!=c->handle||eglGetCurrentSurface(EGL_DRAW)!=s->handle||eglGetCurrentSurface(EGL_READ)!=s->handle)return COH_STATE;
 if(b->journal.pending&&b->mode!=2)return COH_STATE;
 return COH_OK;
}
static CohStatus current(void*v,CohWrGpuToken t){CohGpuEglBackend*b=v;
 CohStatus s=actual(b);
 if(s!=COH_OK)return s;
 CohWrGpuToken now=token(b);
 return now.surface_generation==t.surface_generation&&now.context_generation==t.context_generation&&now.render_thread==t.render_thread?COH_OK:COH_STATE;}
static CohStatus retire(void*v,CohWrGpuToken t){CohGpuEglBackend*b=v;
 if(!owner(b))return COH_STATE;
 if(b->mode==1)b->mode=2; /* Private synchronous uploader rollback/restore. */
 CohStatus s=actual(b);
 if(s!=COH_OK)return s;
 Context*c=find(b,t);
 return c&&!c->dead&&c==b->contexts+b->active_context?COH_OK:COH_STATE;}
static CohStatus destroyed(void*v,CohWrGpuToken t){CohGpuEglBackend*b=v;
 if(!owner(b))return COH_STATE;
 Context*c=find(b,t);
 return c&&c->dead?COH_OK:COH_STATE;}
static CohStatus begin(CohGpuEglBackend*b){CohStatus s=actual(b);
 if(s!=COH_OK)return s;
 return glGetError()==GL_NO_ERROR?COH_OK:COH_IO;}
static CohStatus end(void){return glGetError()==GL_NO_ERROR?COH_OK:COH_IO;}
#define START do{CohStatus s=begin(v);if(s!=COH_OK)return s;}while(0)
static CohStatus integer(void*v,uint32_t p,int32_t*out){START;
 GLint value;
 glGetIntegerv(p,&value);
 CohStatus s=end();
 if(s==COH_OK)*out=value;
 return s;}
static CohStatus generate(void*v,uint32_t*out){START;
 GLuint n=0;
 glGenTextures(1,&n);
 *out=n;
 return end();}
static CohStatus bind(void*v,uint32_t n){START;
 glBindTexture(GL_TEXTURE_2D,n);
 return end();}
static CohStatus buffer(void*v,uint32_t n){START;
 glBindBuffer(GL_PIXEL_UNPACK_BUFFER,n);
 return end();}
static CohStatus pixel(void*v,uint32_t p,int32_t n){START;
 glPixelStorei(p,n);
 return end();}
static CohStatus image(void*v,uint32_t level,uint32_t w,uint32_t h,CohBytes rgba){START;
 if(rgba.size!=(size_t)w*h*4||!rgba.data)return COH_INVALID;
 glTexImage2D(GL_TEXTURE_2D,(GLint)level,GL_RGBA8,(GLsizei)w,(GLsizei)h,0,GL_RGBA,GL_UNSIGNED_BYTE,rgba.data);
 CohStatus s=end();CohGpuEglBackend*b=v;
 if(s==COH_OK&&b->fault_image){b->fault_image=0;return COH_IO;}
 return s;}
static CohStatus parameter(void*v,uint32_t p,int32_t n){START;
 glTexParameteri(GL_TEXTURE_2D,p,n);
 return end();}
static CohStatus delete_texture(void*v,uint32_t*n){START;
 CohGpuEglBackend*b=v;if(b->fault_delete)return COH_IO;
 GLuint name=*n;
 glDeleteTextures(1,&name);
 CohStatus s=end();
 if(s==COH_OK)*n=0;
 return s;}
#undef START
static CohStatus new_surface(CohGpuEglBackend*b){
 if(b->report.surfaces_created>=SURFACES)return COH_LIMIT;
 EGLint attr[]={EGL_WIDTH,16,EGL_HEIGHT,16,EGL_NONE};
 EGLSurface s=eglCreatePbufferSurface(b->display,b->config,attr);
 if(s==EGL_NO_SURFACE)return COH_IO;
 unsigned at=b->report.surfaces_created++;
 b->surfaces[at]=(Surface){s,0,0,0};
 b->active_surface=at;
 Context*c=b->contexts+b->active_context;uint64_t n=next();
 if(!n)return COH_LIMIT;
 if(!c->min_surface)c->min_surface=n;
 c->max_surface=n;b->surfaces[at].context_generation=c->generation;b->surfaces[at].generation=n;
 if(!eglMakeCurrent(b->display,s,s,c->handle))return COH_IO;
 return COH_OK;
}
static CohStatus new_context(CohGpuEglBackend*b){
 if(b->report.contexts_created>=CONTEXTS)return COH_LIMIT;
 EGLint attr[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
 EGLContext c=eglCreateContext(b->display,b->config,EGL_NO_CONTEXT,attr);
 if(c==EGL_NO_CONTEXT)return COH_IO;
 unsigned at=b->report.contexts_created++;
 b->contexts[at]=(Context){c,next(),0,0,0};
 b->active_context=at;
 if(!b->contexts[at].generation)return COH_LIMIT;
 CohStatus s=new_surface(b);
 if(s!=COH_OK)return s;
 GLint major=0;
 glGetIntegerv(GL_MAJOR_VERSION,&major);
 if(glGetError()!=GL_NO_ERROR||major<3)return COH_UNSUPPORTED;
 b->report.gles_major=(uint32_t)major;
 const char*version=(const char*)glGetString(GL_VERSION);
 const char*renderer=(const char*)glGetString(GL_RENDERER);
 if(!version||!renderer||strlen(version)>=sizeof(b->report.gl_version)||strlen(renderer)>=sizeof(b->report.gl_renderer)||glGetError()!=GL_NO_ERROR)return COH_UNSUPPORTED;
 strcpy(b->report.gl_version,version);strcpy(b->report.gl_renderer,renderer);
 return COH_OK;
}
CohStatus coh_gpu_egl_create(CohGpuEglBackend**out){
 if(!out)return COH_INVALID;
 if(*out)return COH_STATE;
 if(atomic_flag_test_and_set(&claimed))return COH_STATE;
 CohGpuEglBackend*b=calloc(1,sizeof(*b));
 if(!b){atomic_flag_clear(&claimed);return COH_LIMIT;}
 b->thread=pthread_self();
 b->thread_token=next();
 b->display=eglGetDisplay(EGL_DEFAULT_DISPLAY);
 *out=b;
 if(!b->thread_token||b->display==EGL_NO_DISPLAY||!eglInitialize(b->display,NULL,NULL))return COH_IO;
 b->initialized=1;
 if(!eglBindAPI(EGL_OPENGL_ES_API))return COH_IO;
 EGLint attr[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,ES3_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_NONE};
 EGLint found=0;
 if(!eglChooseConfig(b->display,attr,&b->config,1,&found)||found!=1)return COH_UNSUPPORTED;
 b->ops=(CohWrGpuOps){b,current,retire,destroyed,integer,generate,bind,buffer,pixel,image,parameter,delete_texture};
 return new_context(b);
}
CohStatus coh_gpu_egl_token(CohGpuEglBackend*b,CohWrGpuToken*out){if(!out)return COH_INVALID;
 CohStatus s=actual(b);
 if(s!=COH_OK)return s;
 *out=token(b);
 return COH_OK;}
CohStatus coh_gpu_egl_upload(CohGpuEglBackend*b,const CohWrTextureResource*cpu,const CohWrSamplerSource*sampler,const CohWrGpuLimits*limits,CohWrGpuTexture**out){
 if(!owner(b)||b->journal.pending)return COH_STATE;
 b->mode=1;
 CohStatus s=coh_wr_gpu_upload(cpu,sampler,token(b),&b->ops,limits,(CohCancel){0},out,&b->journal);
 b->mode=0;
 if(s==COH_OK)b->report.gpu_owners++;
 return s;
}
CohStatus coh_gpu_egl_view(CohGpuEglBackend*b,const CohWrGpuTexture*gpu,CohWrGpuToken t,CohRenderTexture*out){if(!owner(b)||b->journal.pending)return COH_STATE;
 return coh_wr_gpu_view(gpu,t,&b->ops,out);}
CohStatus coh_gpu_egl_release(CohGpuEglBackend*b,CohWrGpuTexture**gpu){
 if(!owner(b)||!gpu)return COH_INVALID;
 if(b->journal.pending)return COH_STATE;
 if(!*gpu)return COH_OK;
 b->mode=2;
 CohStatus s=coh_wr_gpu_release(gpu,&b->ops);
 if(s==COH_STATE)s=coh_wr_gpu_discard_destroyed(gpu,&b->ops);
 b->mode=0;
 if(!*gpu)b->report.gpu_owners--;
 return s;
}
CohStatus coh_gpu_egl_readback(CohGpuEglBackend*b,const CohWrGpuTexture*gpu,uint32_t level,uint8_t*out,size_t capacity){
 if(!owner(b)||b->journal.pending)return COH_STATE;
 CohRenderTexture tex;
 CohStatus status=coh_wr_gpu_view(gpu,token(b),&b->ops,&tex);
 if(status!=COH_OK)return status;
 CohWrGpuReport r;status=coh_wr_gpu_report(gpu,&r);
 if(status!=COH_OK)return status;
 if(level>=r.uploaded_levels)return COH_INVALID;
 uint32_t w=r.source.width>>level,h=r.source.height>>level;
 if(!w)w=1;
 if(!h)h=1;
 if(!out||capacity!=(size_t)w*h*4)return COH_INVALID;
 status=begin(b);
 if(status!=COH_OK)return status;
 GLint saved[7];
 const GLenum names[]={GL_DRAW_FRAMEBUFFER_BINDING,GL_READ_FRAMEBUFFER_BINDING,GL_PIXEL_PACK_BUFFER_BINDING,GL_PACK_ALIGNMENT,GL_PACK_ROW_LENGTH,GL_PACK_SKIP_ROWS,GL_PACK_SKIP_PIXELS};
 for(unsigned i=0;i<7;i++)glGetIntegerv(names[i],saved+i);
 if(end()!=COH_OK)return COH_IO;
 GLuint framebuffer=0;
 glGenFramebuffers(1,&framebuffer);
 glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
 glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex.handle,(GLint)level);
 if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE)status=COH_IO;
 glBindBuffer(GL_PIXEL_PACK_BUFFER,0);
 glPixelStorei(GL_PACK_ALIGNMENT,1);
 glPixelStorei(GL_PACK_ROW_LENGTH,0);
 glPixelStorei(GL_PACK_SKIP_ROWS,0);
 glPixelStorei(GL_PACK_SKIP_PIXELS,0);
 if(status==COH_OK)glReadPixels(0,0,(GLsizei)w,(GLsizei)h,GL_RGBA,GL_UNSIGNED_BYTE,out);
 if(end()!=COH_OK)status=COH_IO;
 glBindFramebuffer(GL_DRAW_FRAMEBUFFER,(GLuint)saved[0]);
 glBindFramebuffer(GL_READ_FRAMEBUFFER,(GLuint)saved[1]);
 glBindBuffer(GL_PIXEL_PACK_BUFFER,(GLuint)saved[2]);
 for(unsigned i=3;i<7;i++)glPixelStorei(names[i],saved[i]);
 if(framebuffer)glDeleteFramebuffers(1,&framebuffer);
 if(end()!=COH_OK)status=COH_IO;
 if(status==COH_OK)b->report.readbacks++;
 return status;
}
CohStatus coh_gpu_egl_test_faults(CohGpuEglBackend*b,unsigned image_error,unsigned deletion_error){
 if(!owner(b)||image_error>1||deletion_error>1)return COH_INVALID;
 b->fault_image=image_error;b->fault_delete=deletion_error;return COH_OK;
}
CohStatus coh_gpu_egl_retry_cleanup(CohGpuEglBackend*b){
 if(!owner(b))return COH_STATE;
 b->mode=2;CohStatus s=coh_wr_gpu_retry_cleanup(&b->journal,&b->ops);b->mode=0;return s;
}
CohStatus coh_gpu_egl_replace_surface(CohGpuEglBackend*b){
 if(!owner(b)||b->journal.pending)return COH_STATE;
 CohStatus s=actual(b);
 if(s!=COH_OK)return s;
 Surface*old=b->surfaces+b->active_surface;
 if(!eglMakeCurrent(b->display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT))return COH_IO;
 if(eglGetCurrentContext()!=EGL_NO_CONTEXT||eglGetCurrentSurface(EGL_DRAW)!=EGL_NO_SURFACE||eglGetCurrentSurface(EGL_READ)!=EGL_NO_SURFACE||eglGetCurrentDisplay()!=EGL_NO_DISPLAY)return COH_IO;
 if(!eglDestroySurface(b->display,old->handle))return COH_IO;
 old->dead=1;
 b->report.surfaces_destroyed++;
 return new_surface(b);
}
CohStatus coh_gpu_egl_destroy_contexts(CohGpuEglBackend*b){
 if(!owner(b))return COH_STATE;
 if(!b->initialized)return COH_OK;
 if(!eglMakeCurrent(b->display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT))return COH_IO;
 if(eglGetCurrentContext()!=EGL_NO_CONTEXT||eglGetCurrentSurface(EGL_DRAW)!=EGL_NO_SURFACE||eglGetCurrentSurface(EGL_READ)!=EGL_NO_SURFACE||eglGetCurrentDisplay()!=EGL_NO_DISPLAY)return COH_IO;
 for(unsigned i=0;i<b->report.surfaces_created;i++)if(!b->surfaces[i].dead){if(!eglDestroySurface(b->display,b->surfaces[i].handle))return COH_IO;
 b->surfaces[i].dead=1;
 b->report.surfaces_destroyed++;}
 for(unsigned i=0;i<b->report.contexts_created;i++)if(!b->contexts[i].dead){if(!eglDestroyContext(b->display,b->contexts[i].handle))return COH_IO;
 b->contexts[i].dead=1;
 b->report.contexts_destroyed++;}
 if(b->journal.pending){b->mode=2;
 CohStatus s=coh_wr_gpu_discard_destroyed_journal(&b->journal,&b->ops);
 b->mode=0;
 if(s!=COH_OK)return s;}return COH_OK;
}
CohStatus coh_gpu_egl_replace_context(CohGpuEglBackend*b){CohStatus s=coh_gpu_egl_destroy_contexts(b);
 return s==COH_OK?new_context(b):s;}
CohStatus coh_gpu_egl_report(CohGpuEglBackend*b,CohGpuEglReport*out){if(!owner(b)||!out)return COH_INVALID;
 *out=b->report;out->pending_cleanup=b->journal.pending;
 return COH_OK;}
CohStatus coh_gpu_egl_close(CohGpuEglBackend**out){
 if(!out)return COH_INVALID;
 if(!*out)return COH_OK;
 CohGpuEglBackend*b=*out;
 if(!owner(b)||b->report.gpu_owners)return COH_STATE;
 CohStatus s=coh_gpu_egl_destroy_contexts(b);
 if(s!=COH_OK)return s;
 if(b->initialized&&!eglTerminate(b->display))return COH_IO;
 free(b);atomic_flag_clear(&claimed);
 *out=NULL;
 return COH_OK;
}
