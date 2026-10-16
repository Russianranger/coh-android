#include "coh_appearance_actor.h"
#include <string.h>
static int cancelled(const CohAppearanceActorRequest *r){return r->cancel.poll&&r->cancel.poll(r->cancel.context);}
CohStatus coh_appearance_actor_requirements(const CohAppearanceActorRequest *r,CohAppearanceActorDiagnostics *out){
 if(!r||!out||r->snapshot_complete!=1u||!r->count||r->count>COH_APPEARANCE_DRAWS||!r->draws||!r->resources||!r->materials||!r->source_material_counts)return COH_INVALID;
 if(!r->actor.actor_id||!r->actor.rig_id||!r->actor.rig||!r->actor.pose||!r->actor.appearance_generation||!r->actor.rig_generation||!r->actor.pose_generation||!r->surface_generation)return COH_INVALID;
 CohAppearanceActorDiagnostics d={0};
 for(uint32_t i=0;i<r->count;i++){
  if(cancelled(r))return COH_CANCELLED;
  const CohAppearanceDraw *part=&r->draws[i];const CohAppearanceRenderResource *resource=&r->resources[i];
  if(part->flags&~(COH_APPEARANCE_CLEAR|COH_APPEARANCE_SKIN_COLOR)||part->socket>=99u)return COH_INVALID;
  if(part->generation!=r->actor.appearance_generation)return COH_STATE;
  for(uint32_t j=0;j<i;j++)if(r->draws[j].socket==part->socket)return COH_INVALID;
  if(part->flags&COH_APPEARANCE_CLEAR){d.cleared_parts++;continue;}
  if(!resource->mesh)return COH_NOT_FOUND;
  if(r->source_material_counts[i]!=1u||resource->first_index||resource->index_count!=resource->mesh->index_count)return COH_UNSUPPORTED;
  uint32_t nv=resource->mesh->vertex_count,ni=resource->mesh->index_count;
  if(!nv||!ni||nv>UINT32_MAX-d.vertices||ni>UINT32_MAX-d.indices)return COH_LIMIT;
  d.vertices+=nv;d.indices+=ni;d.rendered_parts++;
 }
#if SIZE_MAX <= UINT32_MAX
 if(d.vertices>SIZE_MAX/sizeof(CohRenderVertex)||d.indices>SIZE_MAX/sizeof(uint32_t))return COH_LIMIT;
#endif
 d.vertex_bytes=(size_t)d.vertices*sizeof(CohRenderVertex);d.index_bytes=(size_t)d.indices*sizeof(uint32_t);*out=d;return COH_OK;
}
CohStatus coh_appearance_actor_render(const CohAppearanceActorRequest *r,const float mv[16],const float projection[16],CohAppearanceActorWorkspace *w,CohRenderVertex *vertices,size_t vcap,uint32_t *indices,size_t icap,CohRenderDraw *out,size_t capacity,size_t *count,CohAppearanceActorDiagnostics *diagnostics){
 if(!mv||!projection||!w||!vertices||!indices||!out||!count)return COH_INVALID;
 CohAppearanceActorDiagnostics d;CohStatus status=coh_appearance_actor_requirements(r,&d);if(status)return status;
 if(vcap<d.vertices||icap<d.indices||capacity<d.rendered_parts)return COH_LIMIT;
 size_t vo=0,io=0,n=0;
 for(uint32_t i=0;i<r->count;i++){
  if(cancelled(r))return COH_CANCELLED;
  if(r->draws[i].flags&COH_APPEARANCE_CLEAR)continue;
  CohAppearanceRenderDiagnostics part;
  status=coh_appearance_render_part(&r->draws[i],&r->resources[i],&r->actor,&r->materials[i],r->surface_generation,mv,projection,vertices+vo,vcap-vo,indices+io,icap-io,&w->draws[n],&part);
  if(status)return status;
  vo+=part.vertices;io+=part.indices;n++;
 }
 if(cancelled(r))return COH_CANCELLED;
 memcpy(out,w->draws,n*sizeof *out);*count=n;if(diagnostics)*diagnostics=d;return COH_OK;
}
