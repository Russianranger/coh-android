/* Narrow owner-replacement regression, using a real private EGL/GLES context.
 * Controlled geometry/textures are not original client assets or a world. */
#include "../coh_renderer_gles.h"
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, allocations, frees;
#define CHECK(value) do { ++checks; if (!(value)) { \
  fprintf(stderr,"ownership check failed at line %u\n",(unsigned)__LINE__); \
  exit(1); } } while (0)
void *__real_calloc(size_t, size_t);
void __real_free(void *);
void *__wrap_calloc(size_t n, size_t size) {
  ++allocations; return __real_calloc(n,size);
}
void __wrap_free(void *p) {
  if (p) ++frees;
  __real_free(p);
}
static const float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
static const CohRenderVertex vertices[3]={
  {{-1,-1,0},{0,0,1},{0,0},{0,0},{.125f,.125f,.125f,1}},
  {{1,-1,0},{0,0,1},{0,0},{0,0},{.125f,.125f,.125f,1}},
  {{0,1,0},{0,0,1},{0,0},{0,0},{.125f,.125f,.125f,1}}
};
static const uint32_t indices[3]={0,1,2};
static void frame(CohRenderer *renderer, uint32_t surface,
                  const GLuint textures[2]) {
  CohRenderDraw draw;
  unsigned char pixel[4];
  memset(&draw,0,sizeof(draw));
  draw.geometry=(CohRenderGeometry){vertices,3,indices,3,1,1};
  draw.material=coh_renderer_default_material(COH_MAT_MULTIPLY);
  draw.material.cull_back=draw.material.depth_test=draw.material.depth_write=0;
  draw.material.fog_params[2]=100;
  draw.material.textures[0].handle=textures[0];
  draw.material.textures[1].handle=textures[1];
  memcpy(draw.model_view,identity,sizeof(identity));
  memcpy(draw.projection,identity,sizeof(identity));
  glClearColor(0,0,0,0); glClear(GL_COLOR_BUFFER_BIT);
  CHECK(coh_renderer_begin(renderer,surface)==COH_OK);
  CHECK(coh_renderer_submit(renderer,&draw)==COH_OK);
  CHECK(coh_renderer_flush(renderer,(CohCancel){0})==COH_OK);
  glReadPixels(4,3,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pixel);
  CHECK(glGetError()==GL_NO_ERROR);
  CHECK(pixel[0]>=126 && pixel[0]<=130 && pixel[1]>=62 && pixel[1]<=66 &&
        pixel[2]>=30 && pixel[2]<=34 && pixel[3]==255);
}
int main(void) {
  const EGLint config_attrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,
    EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,
    EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_NONE};
  const EGLint surface_attrs[]={EGL_WIDTH,8,EGL_HEIGHT,8,EGL_NONE};
  const EGLint context_attrs[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
  EGLDisplay display=eglGetDisplay(EGL_DEFAULT_DISPLAY);
  EGLConfig config;
  EGLint major,minor,count;
  EGLSurface surface;
  EGLContext context;
  CohGlesRenderer *gles=NULL,*saved_gles;
  CohRenderer *renderer=NULL,*saved_renderer;
  CohRenderBackend backend,saved_backend;
  CohRendererConfig limits={4,3,3,1};
  CohRendererStats before,after;
  GLuint textures[2];
  const unsigned char pixels[2][4]={{128,64,32,255},{255,255,255,255}};
  unsigned a,f,i;
  GLint vao,vbo,ibo,observed;
  const GLubyte *version,*gpu;
  char version_copy[192],gpu_copy[192];
  CHECK(display!=EGL_NO_DISPLAY);
  CHECK(eglInitialize(display,&major,&minor)==EGL_TRUE);
  CHECK(eglBindAPI(EGL_OPENGL_ES_API)==EGL_TRUE);
  CHECK(eglChooseConfig(display,config_attrs,&config,1,&count)==EGL_TRUE && count==1);
  surface=eglCreatePbufferSurface(display,config,surface_attrs);
  CHECK(surface!=EGL_NO_SURFACE);
  context=eglCreateContext(display,config,EGL_NO_CONTEXT,context_attrs);
  CHECK(context!=EGL_NO_CONTEXT);
  CHECK(eglMakeCurrent(display,surface,surface,context)==EGL_TRUE);
  version=glGetString(GL_VERSION); gpu=glGetString(GL_RENDERER);
  CHECK(version && gpu && strlen((const char *)version)<sizeof(version_copy) &&
        strlen((const char *)gpu)<sizeof(gpu_copy));
  strcpy(version_copy,(const char *)version); strcpy(gpu_copy,(const char *)gpu);
  CHECK(!strncmp(version_copy,"OpenGL ES 3.",12));
  glViewport(0,0,8,8);
  memset(&backend,0,sizeof(backend));
  CHECK(coh_renderer_gles_create(3,3,&gles,&backend)==COH_OK && gles);
  saved_gles=gles; saved_backend=backend;
  glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&vao);
  glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&vbo);
  glGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING,&ibo);
  CHECK(glGetError()==GL_NO_ERROR);
  a=allocations; f=frees;
  /* A dirty error remains untouched: occupied-owner refusal cannot reach the
   * recreator's glGetError or allocate replacement objects before refusing. */
  glEnable(0xffffffffu);
  CHECK(coh_renderer_gles_create(6,6,&gles,&backend)==COH_STATE);
  CHECK(gles==saved_gles && !memcmp(&backend,&saved_backend,sizeof(backend)));
  CHECK(allocations==a && frees==f);
  CHECK(glGetError()==GL_INVALID_ENUM && glGetError()==GL_NO_ERROR);
  glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&observed); CHECK(observed==vao);
  glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&observed); CHECK(observed==vbo);
  glGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING,&observed); CHECK(observed==ibo);
  CHECK(coh_renderer_create(&limits,&backend,&renderer)==COH_OK && renderer);
  saved_renderer=renderer; before=coh_renderer_stats(renderer);
  a=allocations; f=frees;
  CHECK(coh_renderer_create(&limits,&backend,&renderer)==COH_STATE);
  after=coh_renderer_stats(renderer);
  CHECK(renderer==saved_renderer && !memcmp(&before,&after,sizeof(before)));
  CHECK(allocations==a && frees==f);
  {
    CohRendererConfig overflow=limits;
    overflow.max_draws=(size_t)-1;
    CHECK(coh_renderer_create(&overflow,&backend,&renderer)==COH_LIMIT);
    CHECK(renderer==saved_renderer && allocations==a && frees==f);
  }
  glGenTextures(2,textures);
  for (i=0;i<2;++i) {
    glBindTexture(GL_TEXTURE_2D,textures[i]);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,pixels[i]);
  }
  CHECK(glGetError()==GL_NO_ERROR);
  frame(renderer,0,textures);
  CHECK(coh_renderer_stats(renderer).drawn==1);
  /* The original owners remain valid through the existing actual-GL reset. */
  coh_renderer_surface_lost(renderer,1,1);
  CHECK(coh_renderer_gles_recreate(gles,1)==COH_OK);
  frame(renderer,1,textures);
  CHECK(coh_renderer_stats(renderer).drawn==2);
  coh_renderer_destroy(renderer); coh_renderer_gles_destroy(gles,1);
  CHECK(allocations==frees);
  glDeleteTextures(2,textures);
  CHECK(glGetError()==GL_NO_ERROR);
  CHECK(eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT)==EGL_TRUE);
  CHECK(eglDestroyContext(display,context)==EGL_TRUE);
  CHECK(eglDestroySurface(display,surface)==EGL_TRUE);
  CHECK(eglTerminate(display)==EGL_TRUE);
  /* GL strings are constrained by the Python driver before preserving JSON. */
  printf("{\"passed\":true,\"checks\":%u,\"project_allocations\":%u,"
    "\"project_frees\":%u,\"actual_gles\":true,\"frames\":2,"
    "\"occupied_owner_refusals\":2,\"dirty_error_preserved\":true,"
    "\"cleanup_verified\":true,\"gl_version\":\"%s\",\"gl_renderer\":\"%s\","
    "\"android_executed\":false,\"world_authority\":false,\"actor_authority\":false}\n",
    checks,allocations,frees,version_copy,gpu_copy);
  return 0;
}
