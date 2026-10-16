#include "coh_appearance_preview.h"
#include "coh_appearance_actor.h"
#include "../renderer/coh_renderer_gles.h"
#include <GLES3/gl3.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define PARTS 8u
#define TEXTURES 8u
_Static_assert(sizeof(CohAppearanceDraw)==1312u,"appearance package ABI changed");
typedef struct {uint32_t width,height;const uint8_t *rgba;GLuint name;} PreviewTexture;
struct CohAppearancePreview {
 CohBytes package;CohAppearancePreviewStats stats;CohAnimationRig rig;CohAnimationPose pose;
 CohAppearanceDraw parts[PARTS];CohMeshView meshes[PARTS];CohAppearanceRenderResource resources[PARTS];
 CohAppearanceMaterialBinding materials[PARTS];uint32_t material_counts[PARTS],bindings[PARTS][2];
 PreviewTexture textures[TEXTURES];CohAppearanceActorRequest request;CohAppearanceActorWorkspace workspace;
 CohRenderDraw draws[PARTS];CohRenderVertex *vertices;uint32_t *indices;
 CohRenderer *renderer;CohGlesRenderer *driver;float center[3],extent[3];
};
static uint32_t read32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int zeros(const uint8_t*p,size_t n){for(size_t i=0;i<n;i++)if(p[i])return 0;return 1;}
static int cancel_flush(void*context){(void)context;return 1;}
static int text(const char *p){for(unsigned i=0;i<256;i++){unsigned c=(unsigned char)p[i];if(!c)return i!=0;if(c<32||c>126)return 0;}return 0;}
static void identity(float m[16]){memset(m,0,16*sizeof *m);m[0]=m[5]=m[10]=m[15]=1;}
void coh_appearance_preview_surface_lost(CohAppearancePreview*p,int alive){
 if(!p)return;
 if(p->renderer){coh_renderer_surface_lost(p->renderer,0,alive);coh_renderer_destroy(p->renderer);p->renderer=NULL;}
 if(p->driver){coh_renderer_gles_destroy(p->driver,alive);p->driver=NULL;}
 for(unsigned i=0;i<TEXTURES;i++){if(alive&&p->textures[i].name)glDeleteTextures(1,&p->textures[i].name);p->textures[i].name=0;}
 p->stats.surface_generation=0;p->stats.gpu_buffer_bytes=0;
}
void coh_appearance_preview_destroy(CohAppearancePreview*p,int alive){if(p){coh_appearance_preview_surface_lost(p,alive);free(p->vertices);free(p->indices);free(p);}}
CohAppearancePreviewStats coh_appearance_preview_stats(const CohAppearancePreview*p){return p?p->stats:(CohAppearancePreviewStats){0};}
CohStatus coh_appearance_preview_create(CohBytes bytes,CohAppearancePreview **out){
 const uint8_t*b=bytes.data;size_t n=bytes.size;
 if(!b||!out||*out||n<64u+PARTS*1328u+TEXTURES*16u||n>4u*1024u*1024u||memcmp(b,"COHAPV01",8)||read32(b+8)!=1||read32(b+12)!=n||read32(b+16)!=PARTS||read32(b+20)!=TEXTURES||read32(b+24)!=64||read32(b+28)!=64+PARTS*1328u||read32(b+32)!=64+PARTS*1328u+TEXTURES*16u||!zeros(b+40,24))return COH_INVALID;
 uint32_t rig_size=read32(b+36);size_t cursor=read32(b+32);if(!rig_size||rig_size>n-cursor)return COH_INVALID;
 CohAppearancePreview*p=calloc(1,sizeof *p);if(!p)return COH_LIMIT;p->package=bytes;
 if(coh_animation_parse(b+cursor,rig_size,&p->rig))goto invalid;
 cursor+=rig_size;
 for(unsigned i=0;i<PARTS;i++){
  const uint8_t*r=b+64+i*1328u;uint32_t off=read32(r),size=read32(r+4);p->bindings[i][0]=read32(r+8);p->bindings[i][1]=read32(r+12);
  if(off!=cursor||!size||size>n-cursor||p->bindings[i][0]>=TEXTURES||p->bindings[i][1]>=TEXTURES||coh_mesh_parse(b+cursor,size,&p->meshes[i]))goto invalid;
  memcpy(&p->parts[i],r+16,1312);CohAppearanceDraw*d=&p->parts[i];
  if(d->generation!=5||d->socket>=99||d->flags&~COH_APPEARANCE_SKIN_COLOR||!text(d->geometry_key)||!text(d->geometry_path)||!text(d->model_name)||!text(d->texture[0])||!text(d->texture[1]))goto invalid;
  cursor+=size;p->resources[i]=(CohAppearanceRenderResource){1,1,100+i,5,1,0,0,p->meshes[i].index_count,d->geometry_path,d->model_name,&p->meshes[i]};p->material_counts[i]=1;
  CohAppearanceMaterialBinding*m=&p->materials[i];m->material=coh_renderer_default_material(COH_MAT_DUAL);m->source_texture[0]=d->texture[0];m->source_texture[1]=d->texture[1];m->surface_generation=1;
  m->material.fog_params[2]=100;m->material.lighting=COH_LIGHT_DIFFUSE;m->material.light[0]=.2f;m->material.light[1]=.4f;m->material.light[2]=.8944272f;
  for(unsigned k=0;k<3;k++){m->material.ambient[k]=.15f;m->material.diffuse[k]=.1f;}m->material.ambient[3]=1;
  /* Original hair mask carries alpha and its reverse face is visible. */
  m->material.cull_back=i==7?0:1;if(i==7)m->material.blend=COH_BLEND_ALPHA;
 }
 for(unsigned i=0;i<TEXTURES;i++){
  const uint8_t*r=b+read32(b+28)+i*16u;uint32_t w=read32(r),h=read32(r+4),off=read32(r+8),size=read32(r+12);
  if(!w||!h||w>512||h>512||off!=cursor||size!=(size_t)w*h*4u||size>n-cursor)goto invalid;
  p->textures[i]=(PreviewTexture){w,h,b+cursor,0};p->stats.texture_bytes+=size;cursor+=size;
 }
 if(cursor!=n||coh_animation_sample(&p->rig,p->rig.first_frame,&p->pose))goto invalid;
 p->request=(CohAppearanceActorRequest){p->parts,p->resources,p->materials,p->material_counts,PARTS,1,{1,1,0,5,1,1,&p->rig,NULL,&p->pose},1,{NULL,NULL}};
 CohAppearanceActorDiagnostics d;if(coh_appearance_actor_requirements(&p->request,&d)||d.vertices>65536||d.indices>196608)goto invalid;
 p->vertices=malloc(d.vertex_bytes);p->indices=malloc(d.index_bytes);if(!p->vertices||!p->indices){coh_appearance_preview_destroy(p,0);return COH_LIMIT;}
 float unit[16];identity(unit);size_t count=0;if(coh_appearance_actor_render(&p->request,unit,unit,&p->workspace,p->vertices,d.vertices,p->indices,d.indices,p->draws,PARTS,&count,NULL)||count!=PARTS)goto invalid;
 float low[3]={INFINITY,INFINITY,INFINITY},high[3]={-INFINITY,-INFINITY,-INFINITY};
 for(unsigned i=0;i<d.vertices;i++)for(unsigned k=0;k<3;k++){float x=p->vertices[i].position[k];if(x<low[k])low[k]=x;if(x>high[k])high[k]=x;}
 if(!(high[1]>low[1]))goto invalid;
 for(unsigned k=0;k<3;k++){p->center[k]=(low[k]+high[k])*.5f;p->extent[k]=high[k]-low[k];}
 p->stats.parts=PARTS;p->stats.vertices=d.vertices;p->stats.indices=d.indices;p->stats.owned_cpu_bytes=sizeof *p+d.vertex_bytes+d.index_bytes;p->stats.borrowed_package_bytes=n;*out=p;return COH_OK;
invalid:coh_appearance_preview_destroy(p,0);return COH_INVALID;
}
static CohStatus upload(CohAppearancePreview*p,uint32_t generation){
 CohRenderBackend backend;CohStatus s=coh_renderer_gles_create(p->stats.vertices,p->stats.indices,&p->driver,&backend);if(s)return s;
 CohRendererConfig config={PARTS,p->stats.vertices,p->stats.indices,3};s=coh_renderer_create(&config,&backend,&p->renderer);if(s){coh_appearance_preview_surface_lost(p,1);return s;}
 for(unsigned i=0;i<TEXTURES;i++){
  PreviewTexture*t=&p->textures[i];glGenTextures(1,&t->name);glBindTexture(GL_TEXTURE_2D,t->name);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,(GLsizei)t->width,(GLsizei)t->height,0,GL_RGBA,GL_UNSIGNED_BYTE,t->rgba);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);
 }
 if(glGetError()!=GL_NO_ERROR){coh_appearance_preview_surface_lost(p,1);return COH_IO;}
 for(unsigned i=0;i<PARTS;i++){p->materials[i].surface_generation=generation;for(unsigned j=0;j<2;j++)p->materials[i].material.textures[j]=(CohRenderTexture){p->textures[p->bindings[i][j]].name,COH_WRAP_REPEAT,COH_WRAP_REPEAT,COH_FILTER_LINEAR,COH_FILTER_LINEAR};}
 coh_renderer_surface_lost(p->renderer,generation,1);p->request.surface_generation=generation;p->stats.surface_generation=generation;p->stats.surface_uploads++;p->stats.gpu_buffer_bytes=coh_renderer_gles_buffer_bytes(p->driver);return COH_OK;
}
CohStatus coh_appearance_preview_draw(CohAppearancePreview*p,uint32_t width,uint32_t height,uint32_t generation,double seconds){
 if(!p||!width||!height||width>8192||height>8192||!generation||!isfinite(seconds)||seconds<0)return COH_INVALID;
 if(p->stats.surface_generation!=generation){coh_appearance_preview_surface_lost(p,0);CohStatus s=upload(p,generation);if(s){p->stats.failures++;return s;}}
 /* This is a neutral costume inspection, not a jump playback camera. Advancing
  * source jump root translation escapes a camera fitted to the initial pose.
  * Keep the exact initial source pose at every application clock value. */
 if(coh_animation_sample(&p->rig,p->rig.first_frame,&p->pose)){p->stats.failures++;return COH_INVALID;}
 if(p->request.actor.pose_generation==UINT32_MAX)p->request.actor.pose_generation=1;else p->request.actor.pose_generation++;
 float mv[16],projection[16];identity(mv);identity(projection);for(unsigned k=0;k<3;k++)mv[12+k]=-p->center[k];
 /* Fit the complete bounds to 70% of either viewport dimension. The margin is
  * generic; applications decide whether their overlays obscure this region. */
 float aspect=(float)height/(float)width;float scale=1.4f/fmaxf(p->extent[1],p->extent[0]*aspect);
 projection[0]=scale*aspect;projection[5]=scale;projection[10]=-.08f;
 size_t count=0;CohStatus s=coh_appearance_actor_render(&p->request,mv,projection,&p->workspace,p->vertices,p->stats.vertices,p->indices,p->stats.indices,p->draws,PARTS,&count,NULL);if(s){p->stats.failures++;return s;}
 glViewport(0,0,(GLsizei)width,(GLsizei)height);glDisable(GL_SCISSOR_TEST);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glDepthMask(GL_TRUE);glClearDepthf(1);glClearColor(.035f,.045f,.065f,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
 s=coh_renderer_begin(p->renderer,generation);
 if(!s){for(size_t i=0;!s&&i<count;i++)s=coh_renderer_submit(p->renderer,&p->draws[i]);if(s)(void)coh_renderer_flush(p->renderer,(CohCancel){cancel_flush,NULL});else s=coh_renderer_flush(p->renderer,(CohCancel){NULL,NULL});}
 if(glGetError()!=GL_NO_ERROR&&!s)s=COH_IO;
 if(s){p->stats.failures++;return s;}p->stats.frames++;p->stats.draws+=count;return COH_OK;
}
