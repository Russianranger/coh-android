#include "../coh_appearance_render.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint8_t *read_file(const char *path,size_t *n){FILE *f=fopen(path,"rb");if(!f)return NULL;assert(!fseek(f,0,SEEK_END));long size=ftell(f);assert(size>0&&size<16*1024*1024&&!fseek(f,0,SEEK_SET));uint8_t *b=malloc((size_t)size);assert(b&&fread(b,1,(size_t)size,f)==(size_t)size);fclose(f);*n=(size_t)size;return b;}
static void identity(float *r){memset(r,0,12u*sizeof *r);r[0]=r[5]=r[10]=1.f;}
static unsigned authentic_palette(const CohMeshView *mesh,const CohAnimationRig *rig,uint32_t socket,uint32_t body){
 /* Genuine neutral source rig/mesh pairing only. No authored costume, original
  * material, new body morphology or GPU image is implied by this CPU check. */
 CohAppearanceDraw d={0};d.socket=socket;uint32_t ids[15];float rows[180];for(uint32_t i=0;i<mesh->bone_count;i++)assert(!coh_mesh_global_bone(mesh,i,&ids[i]));
 for(unsigned frame=0;frame<3;frame++){
  float at=rig->first_frame+(rig->last_frame-rig->first_frame)*(float)frame/2.f;CohAnimationPose pose;assert(!coh_animation_sample(rig,at,&pose));
  assert(coh_appearance_palette(&d,body,rig,NULL,&pose,ids,mesh->bone_count,rows,sizeof rows/sizeof rows[0])==COH_OK);
  for(uint32_t i=0;i<mesh->vertex_count;i++){CohMeshVertex v;CohSkinnedVertex result;assert(!coh_mesh_vertex(mesh,i,&v)&&!coh_mesh_skin_vertex(&v,rows,mesh->bone_count,&result));}
 }
 return 3u;
}
static unsigned bridge(const CohMeshView *mesh){
 /* Structural neutral test rig; this is intentionally not an authentic actor.
  * Authentic Wretch palette regression remains separately recorded. */
 CohAnimationRig rig={0};CohAnimationPose pose={0};rig.node_count=99;for(unsigned i=0;i<99;i++){rig.parent[i]=-1;rig.order[i]=(uint8_t)i;identity(pose.world_rows[i]);}
 CohAppearanceDraw d={0};d.generation=5;strcpy(d.geometry_path,"player_library/example.geo");strcpy(d.model_name,"GEO_example");strcpy(d.texture[0],"first");strcpy(d.texture[1],"none");d.color[0][0]=255;d.color[1][1]=255;
 CohAppearanceActorPose a={11,22,0,5,7,1,&rig,NULL,&pose};
 CohAppearanceRenderResource resource={11,22,33,5,7,0,0,mesh->index_count,"player_library/example.geo","GEO_example",mesh};
 CohAppearanceMaterialBinding material={0};material.material.family=COH_MAT_DUAL;material.surface_generation=9;material.source_texture[0]="first";material.source_texture[1]="none";
 float matrix[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
 CohRenderVertex *vertices=malloc((size_t)mesh->vertex_count*sizeof *vertices);uint32_t *indices=malloc((size_t)mesh->index_count*sizeof *indices);assert(vertices&&indices);CohRenderDraw output={0},old=output;CohAppearanceRenderDiagnostics stats={0};
 assert(coh_appearance_render_part(&d,&resource,&a,&material,9,matrix,matrix,vertices,mesh->vertex_count,indices,mesh->index_count,&output,&stats)==COH_OK);
 assert(output.geometry.vertex_count==mesh->vertex_count&&output.geometry.generation==1&&output.material.const0[0]==1&&output.material.const1[1]==1);
 old=output;unsigned negatives=0;
#define BAD(status) do{assert(coh_appearance_render_part(&d,&resource,&a,&material,9,matrix,matrix,vertices,mesh->vertex_count,indices,mesh->index_count,&output,&stats)==status);assert(!memcmp(&output,&old,sizeof old));negatives++;}while(0)
 resource.rig_id++;BAD(COH_STATE);resource.rig_id--;
 a.appearance_generation++;BAD(COH_STATE);a.appearance_generation--;
 a.rig_generation++;BAD(COH_STATE);a.rig_generation--;
 a.body_type=1;BAD(COH_STATE);a.body_type=0;
 material.surface_generation++;BAD(COH_STATE);material.surface_generation--;
 material.source_texture[1]="missing";BAD(COH_NOT_FOUND);material.source_texture[1]="none";
 resource.source_model_name="other";BAD(COH_NOT_FOUND);resource.source_model_name="GEO_example";
 material.material.family=COH_MAT_MULTIPLY;BAD(COH_UNSUPPORTED);material.material.family=COH_MAT_DUAL;
 d.flags=COH_APPEARANCE_CLEAR;BAD(COH_NOT_FOUND);d.flags=0;
 a.pose_generation=0;BAD(COH_INVALID);a.pose_generation=1;
 resource.first_index=1;BAD(COH_INVALID);resource.first_index=0;
 resource.index_count=0;BAD(COH_INVALID);resource.index_count=mesh->index_count;
 assert(coh_appearance_render_part(&d,&resource,&a,&material,9,matrix,matrix,vertices,mesh->vertex_count-1u,indices,mesh->index_count,&output,&stats)==COH_LIMIT);negatives++;
 free(vertices);free(indices);return negatives;
}
int main(int argc,char **argv){
 assert(argc==2||argc==3);const char *names[]={"fem_pants.geo","fem_shirt.geo","huge_pants.geo","huge_shirt.geo","v_fem_head.geo","v_male_pants.geo","v_male_shirt.geo"};
 const char *family[]={"fem","fem","huge","huge","fem","male","male"};uint32_t bodies[]={1,1,4,4,1,0,0},sockets[]={0,2,0,2,4,0,2};
 unsigned models=0,vertices=0,indices=0,rigid=0,negative=0,source_poses=0;size_t high_water=0;
 for(unsigned f=0;f<7;f++){
  char path[4096];int length=snprintf(path,sizeof path,"%s/%s",argv[1],names[f]);assert(length>0&&(size_t)length<sizeof path);size_t n;uint8_t *raw=read_file(path,&n);assert(raw);
  size_t arena_size;assert(coh_asset_geo_workspace((CohBytes){raw,n},&arena_size)==COH_OK);uint8_t *arena=malloc(arena_size);assert(arena);CohAssetGeo geo;assert(coh_asset_geo_open((CohBytes){raw,n},arena,arena_size,4096,&geo)==COH_OK);
  CohAnimationRig source_rig;uint8_t *rig_raw=NULL;if(argc==3){length=snprintf(path,sizeof path,"%s/%s-jump_n_smash.bin",argv[2],family[f]);assert(length>0&&(size_t)length<sizeof path);size_t rig_size;rig_raw=read_file(path,&rig_size);assert(rig_raw&&!coh_animation_parse(rig_raw,rig_size,&source_rig));}
  for(uint32_t i=0;i<geo.model_count;i++){
   CohAppearanceMeshRequirements requirements;assert(coh_appearance_mesh_requirements(&geo,i,0,&requirements)==COH_OK);void *scratch=malloc(requirements.workspace_bytes);uint8_t *dst=malloc(requirements.canonical_bytes);assert(scratch&&dst);memset(dst,0xa5,requirements.canonical_bytes);
   CohMeshView mesh={0},old=mesh;assert(coh_appearance_mesh_build(&geo,i,0,scratch,requirements.workspace_bytes-1u,dst,requirements.canonical_bytes,&mesh,NULL)==COH_LIMIT);assert(dst[0]==0xa5&&!memcmp(&mesh,&old,sizeof old));negative++;
   assert(coh_appearance_mesh_build(&geo,i,0,scratch,requirements.workspace_bytes,dst,requirements.canonical_bytes,&mesh,NULL)==COH_OK);models++;vertices+=mesh.vertex_count;indices+=mesh.index_count;rigid+=requirements.rigid_socket_fallback;if(requirements.workspace_bytes>high_water)high_water=requirements.workspace_bytes;
   if(rig_raw)source_poses+=authentic_palette(&mesh,&source_rig,sockets[f],bodies[f]);
   if(i==0){
    negative+=bridge(&mesh);CohAppearanceMeshRequirements unchanged=requirements;
    assert(coh_appearance_mesh_requirements(&geo,i,99,&requirements)==COH_INVALID&&!memcmp(&requirements,&unchanged,sizeof unchanged));negative++;
    CohAssetGeoModel model;assert(coh_asset_geo_model(&geo,i,&model)==COH_OK);
    if(model.bone_info_offset){
     uint8_t *info=(uint8_t*)geo.payload.data+model.bone_info_offset;uint8_t saved=info[0];info[0]=0;
     assert(coh_appearance_mesh_requirements(&geo,i,0,&requirements)==COH_LIMIT&&!memcmp(&requirements,&unchanged,sizeof unchanged));negative++;info[0]=saved;
     uint8_t pointers[8];memcpy(pointers,info+64,8);info[64]=1;
     assert(coh_appearance_mesh_requirements(&geo,i,0,&requirements)==COH_UNSUPPORTED&&!memcmp(&requirements,&unchanged,sizeof unchanged));negative++;memcpy(info+64,pointers,8);
     old=mesh;memset(dst,0xa5,requirements.canonical_bytes);saved=info[4];info[4]=255;
     assert(coh_appearance_mesh_build(&geo,i,0,scratch,requirements.workspace_bytes,dst,requirements.canonical_bytes,&mesh,NULL)==COH_INVALID&&dst[0]==0xa5&&!memcmp(&mesh,&old,sizeof old));negative++;info[4]=saved;
    }
   }
   free(scratch);free(dst);
  }
  free(rig_raw);free(arena);free(raw);
 }
 printf("{\"passed\":true,\"authentic_models_converted\":%u,\"vertices\":%u,\"indices\":%u,\"rigid_models\":%u,\"negative_cases\":%u,\"authentic_neutral_part_poses\":%u,\"largest_workspace_bytes\":%zu,\"module_heap_allocations\":0,\"render_bridge_rig\":\"structural neutral rig, not body qualification\"}\n",models,vertices,indices,rigid,negative,source_poses,high_water);return 0;
}
