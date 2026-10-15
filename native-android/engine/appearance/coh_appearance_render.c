#include "coh_appearance_render.h"
#include <math.h>
#include <string.h>
static int same(const char *a,const char *b){if(!a||!b)return 0;for(unsigned i=0;i<COH_APPEARANCE_NAME;i++){unsigned x=(unsigned char)a[i],y=(unsigned char)b[i];if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;if(!x)return i!=0;}return 0;}
static int same_model(const char *a,const char *b){if(!a||!b)return 0;for(unsigned i=0;i<COH_APPEARANCE_NAME;i++){unsigned x=(unsigned char)a[i],y=(unsigned char)b[i];if(i+1u<COH_APPEARANCE_NAME){if(x=='_'&&a[i+1]=='_')x=0;if(y=='_'&&b[i+1]=='_')y=0;}if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;if(!x)return i!=0;}return 0;}
CohStatus coh_appearance_render_part(const CohAppearanceDraw *d,const CohAppearanceRenderResource *r,const CohAppearanceActorPose *a,const CohAppearanceMaterialBinding *binding,uint32_t surface,const float mv[16],const float projection[16],CohRenderVertex *vertices,size_t vcap,uint32_t *indices,size_t icap,CohRenderDraw *out,CohAppearanceRenderDiagnostics *diagnostics){
 if(!d||!r||!a||!binding||!mv||!projection||!vertices||!indices||!out||!r->mesh||!a->rig||!a->pose||!a->actor_id||!a->rig_id||!r->geometry_id||!surface||!a->pose_generation||!a->appearance_generation||!a->rig_generation)return COH_INVALID;
 if(d->flags&COH_APPEARANCE_CLEAR)return COH_NOT_FOUND;
 if(!same(d->geometry_path,r->source_geometry_path)||!same_model(d->model_name,r->source_model_name)||!same(d->texture[0],binding->source_texture[0])||!same(d->texture[1],binding->source_texture[1]))return COH_NOT_FOUND;
 if(a->actor_id!=r->actor_id||a->rig_id!=r->rig_id||a->body_type!=r->body_type||d->generation!=a->appearance_generation||d->generation!=r->appearance_generation||a->rig_generation!=r->rig_generation||binding->surface_generation!=surface)return COH_STATE;
 if(binding->material.family!=COH_MAT_DUAL)return COH_UNSUPPORTED;
 for(unsigned i=0;i<16;i++)if(!isfinite(mv[i])||!isfinite(projection[i]))return COH_INVALID;
 const CohMeshView *m=r->mesh;
 if(!r->index_count||r->first_index%3u||r->index_count%3u||r->first_index>m->index_count||r->index_count>m->index_count-r->first_index)return COH_INVALID;
 if(vcap<m->vertex_count||icap<r->index_count)return COH_LIMIT;
 uint32_t bones[COH_MESH_MAX_BONES];if(!m->bone_count||m->bone_count>COH_MESH_MAX_BONES)return COH_INVALID;
 for(uint32_t i=0;i<m->bone_count;i++)if(coh_mesh_global_bone(m,i,&bones[i]))return COH_INVALID;
 float rows[COH_MESH_MAX_BONES*12u];CohStatus s=coh_appearance_palette(d,a->body_type,a->rig,a->morph,a->pose,bones,m->bone_count,rows,sizeof rows/sizeof rows[0]);if(s)return s;
 for(uint32_t i=0;i<m->vertex_count;i++){
  CohMeshVertex v;CohSkinnedVertex skinned;if(coh_mesh_vertex(m,i,&v)||coh_mesh_skin_vertex(&v,rows,m->bone_count,&skinned))return COH_INVALID;
  CohRenderVertex q;memcpy(q.position,skinned.position,sizeof q.position);memcpy(q.normal,skinned.normal,sizeof q.normal);memcpy(q.uv0,v.uv,sizeof q.uv0);memcpy(q.uv1,v.uv,sizeof q.uv1);for(unsigned j=0;j<4;j++)q.color[j]=1.f;vertices[i]=q;
 }
 for(uint32_t i=0;i<r->index_count;i++)if(coh_mesh_index(m,r->first_index+i,&indices[i]))return COH_INVALID;
 CohRenderDraw result={0};result.geometry=(CohRenderGeometry){vertices,m->vertex_count,indices,r->index_count,r->geometry_id,a->pose_generation};result.material=binding->material;
 for(unsigned i=0;i<4;i++){result.material.const0[i]=(float)d->color[0][i]/255.f;result.material.const1[i]=(float)d->color[1][i]/255.f;}
 memcpy(result.model_view,mv,sizeof result.model_view);memcpy(result.projection,projection,sizeof result.projection);*out=result;
 if(diagnostics)*diagnostics=(CohAppearanceRenderDiagnostics){m->vertex_count,r->index_count,m->bone_count,(size_t)m->vertex_count*sizeof *vertices,(size_t)r->index_count*sizeof *indices};
 return COH_OK;
}
