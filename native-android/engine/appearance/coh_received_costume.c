#include "coh_received_costume.h"
#include "coh_appearance_material.h"
#include "../renderer/coh_renderer_gles.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define QUERIES 64u
static const CohAppearancePartDef definitions[28]={
#include "huge_body_parts.inc"
};
typedef struct {char name[1025];uint32_t kind;} QueryName;
typedef struct {
 QueryName names[QUERIES];CohAssetZipQuery query[QUERIES];uint32_t count;
 CohAssetZip *zip[COH_RECEIVED_COSTUME_ARCHIVES];uint64_t bytes,reads;CohCancel cancel;
 CohAppearanceCostumeWorkspace appearance;CohAppearanceDraw initial[120];
} Plan;
typedef struct {uint8_t *pixels;size_t bytes;uint32_t width,height;char name[256];} Texture;
struct CohReceivedCostume {
 CohReceivedCostumeStats stats;CohAnimationRig rig;CohAnimationPose pose;
 uint8_t morph_bytes[3028];CohCharacterMorph morph;uint32_t count,surface;
 CohAppearanceMaterialRecipe recipes[120];CohAppearanceDraw draws[120];CohMeshView mesh[120];uint8_t *canonical[120];
 CohAppearanceRenderResource resources[120];CohAppearanceMaterialBinding materials[120];
 uint32_t material_counts[120],bindings[120][2];Texture textures[64];
 CohAppearanceActorWorkspace workspace;CohRenderVertex *vertices;uint32_t *indices;
 CohRenderDraw packets[120];CohAppearanceActorRequest request;
};
static int span_apart(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if((an&&(!a||an>UINTPTR_MAX-x))||(bn&&(!b||bn>UINTPTR_MAX-y)))return 0;return !an||!bn||(x<y?an<=y-x:bn<=x-y);}
static int outside(const CohReceivedCostume*a,const void*p,size_t n){
 if(!span_apart(p,n,a,sizeof*a)||!span_apart(p,n,a->rig.bytes,a->rig.byte_count)||(a->vertices&&!span_apart(p,n,a->vertices,(size_t)a->stats.vertices*sizeof*a->vertices))||(a->indices&&!span_apart(p,n,a->indices,(size_t)a->stats.indices*sizeof*a->indices)))return 0;
 for(unsigned i=0;i<120;i++)if(a->canonical[i]&&!span_apart(p,n,a->canonical[i],a->mesh[i].byte_count))return 0;
 for(unsigned i=0;i<64;i++)if(a->textures[i].pixels&&!span_apart(p,n,a->textures[i].pixels,a->textures[i].bytes))return 0;
 return 1;
}
static int same(const char*a,const char*b){for(unsigned i=0;i<1025;i++){unsigned x=(unsigned char)a[i],y=(unsigned char)b[i];if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;if(!x)return 1;}return 0;}
static int charge(uint64_t parent,uint64_t owned,uint64_t candidate,uint64_t*peak){
 if(parent>COH_RECEIVED_COSTUME_LIMIT||owned>COH_RECEIVED_COSTUME_LIMIT-parent||candidate>COH_RECEIVED_COSTUME_LIMIT-parent-owned)return 0;
 uint64_t total=parent+owned+candidate;if(total>*peak)*peak=total;return 1;
}
static CohStatus missing(CohReceivedCostume*a,const char*name,CohStatus status){snprintf(a->stats.missing,sizeof a->stats.missing,"%s",name);return status;}
static void close_plan(Plan*p){for(unsigned i=0;i<COH_RECEIVED_COSTUME_ARCHIVES;i++)if(p->zip[i]){CohAssetZipStats stats=coh_asset_zip_stats(p->zip[i]);p->reads+=stats.reads;p->bytes+=stats.read_bytes;coh_asset_zip_free(p->zip[i]);p->zip[i]=NULL;}}
static int add_query(Plan*p,const char*name,uint32_t kind){
 for(uint32_t i=0;i<p->count;i++)if(p->names[i].kind==kind&&same(p->names[i].name,name))return (int)i;
 size_t n=strlen(name);if(p->count==QUERIES||!n||n>1024)return -1;
 uint32_t id=p->count++;memcpy(p->names[id].name,name,n+1);p->names[id].kind=kind;p->query[id]=(CohAssetZipQuery){p->names[id].name,0,kind};return (int)id;
}
static CohStatus open_plan(Plan*p,const CohReceivedCostumeInputs*in){for(unsigned i=0;i<COH_RECEIVED_COSTUME_ARCHIVES;i++)if(in->archives[i].read_at){CohStatus s=coh_asset_zip_open_queries(in->archives[i],p->query,p->count,in->cancel,&p->zip[i]);if(s)return s;}return COH_OK;}
static CohStatus locate(Plan*p,uint32_t query,CohAssetZip**zip,const char**path,uint32_t*bytes){
 for(unsigned i=0;i<COH_RECEIVED_COSTUME_ARCHIVES;i++)if(p->zip[i]){uint32_t matches=0;CohStatus status=coh_asset_zip_query(p->zip[i],query,path,bytes,&matches);if(status==COH_NOT_FOUND)continue;if(status)return status;if(!matches)return COH_INVALID;*zip=p->zip[i];return COH_OK;}
 return COH_NOT_FOUND;
}
static int prefix_probe(void*context,uint32_t kind,const char*key){
 Plan*p=context;if(kind!=COH_APPEARANCE_TEXTURE)return 0;size_t n=strlen(key);if(n<4||n>=256)return 0;
 char name[256];memcpy(name,key,n-4);name[n-4]=0;
 for(uint32_t i=0;i<p->count;i++)if(p->names[i].kind==COH_ZIP_QUERY_TEXTURE&&same(name,p->names[i].name))for(unsigned z=0;z<COH_RECEIVED_COSTUME_ARCHIVES;z++)if(p->zip[z]){const char*path;uint32_t bytes,matches;if(coh_asset_zip_query(p->zip[z],i,&path,&bytes,&matches)==COH_OK)return 1;}
 return 0;
}
static CohStatus assembly(const CohReceivedCostumeInputs*in,Plan*p,CohAppearanceDraw*out,size_t*count,int probe){
 CohAppearanceCostumeInputs input={definitions,28,1,NULL,0,probe?prefix_probe:NULL,p,in->cancel};CohAppearanceCostumeDiagnostics diag;
 CohStatus status=coh_appearance_costume_assemble(in->snapshot,&input,&p->appearance,out,120,count,&diag);
 if(status)return status;
 return same(diag.body.ent_type,"huge")?COH_OK:COH_UNSUPPORTED;
}
static CohStatus load_geo(Plan*p,int query,uint8_t*source,size_t capacity,void**header,CohAssetGeo*geo,uint64_t parent,uint64_t owned,uint64_t retained,uint64_t*peak,size_t*header_bytes,int scales){
 CohAssetZip*zip=NULL;const char*path=NULL;uint32_t bytes=0;CohStatus status=locate(p,(uint32_t)query,&zip,&path,&bytes);if(status)return status;
 if(bytes>capacity)return COH_LIMIT;
 status=coh_asset_zip_read(zip,(uint32_t)query,source,bytes);if(status)return status;
 size_t needed=0;status=coh_asset_geo_workspace((CohBytes){source,bytes},&needed);if(status)return status;
 if(!charge(parent,owned,retained+needed,peak))return COH_LIMIT;
 *header_bytes=needed;*header=malloc(needed);if(!*header)return COH_LIMIT;
 status=(scales?coh_asset_geo_open_scales:coh_asset_geo_open)((CohBytes){source,bytes},*header,needed,4096,geo);if(status){free(*header);*header=NULL;}return status;
}
void coh_received_costume_destroy(CohReceivedCostume**value){if(!value||(uintptr_t)value%_Alignof(CohReceivedCostume*)||!*value)return;CohReceivedCostume*a=*value;if(!outside(a,value,sizeof*value))return;for(unsigned i=0;i<120;i++)free(a->canonical[i]);for(unsigned i=0;i<64;i++)free(a->textures[i].pixels);free(a->vertices);free(a->indices);free(a);*value=NULL;}
CohReceivedCostumeStats coh_received_costume_stats(const CohReceivedCostume*a){CohReceivedCostumeStats empty={0};return a?a->stats:empty;}
CohStatus coh_received_costume_prepare(const CohReceivedCostumeInputs*in,CohReceivedCostume**out,CohReceivedCostumeStats*diagnostics){
 if(!in||!out||!diagnostics)return COH_INVALID;
 if((uintptr_t)in%_Alignof(CohReceivedCostumeInputs))return COH_INVALID;
 if(!in->snapshot||!in->rig||!in->archives[0].read_at||!in->source_epoch||!in->entity_index||in->entity_index>10239)return COH_INVALID;
 if((uintptr_t)in%_Alignof(CohReceivedCostumeInputs)||(uintptr_t)out%_Alignof(void*)||(uintptr_t)diagnostics%_Alignof(CohReceivedCostumeStats))return COH_INVALID;
 if((uintptr_t)in->snapshot%_Alignof(CohOriginalCostumeSnapshot)||(uintptr_t)in->rig%_Alignof(CohAnimationRig))return COH_INVALID;
 if(!span_apart(out,sizeof*out,diagnostics,sizeof*diagnostics)||!span_apart(out,sizeof*out,in,sizeof*in)||!span_apart(diagnostics,sizeof*diagnostics,in,sizeof*in)||!span_apart(out,sizeof*out,in->snapshot,sizeof*in->snapshot)||!span_apart(diagnostics,sizeof*diagnostics,in->snapshot,sizeof*in->snapshot)||!span_apart(out,sizeof*out,in->rig,sizeof*in->rig)||!span_apart(diagnostics,sizeof*diagnostics,in->rig,sizeof*in->rig)||!span_apart(out,sizeof*out,in->rig->bytes,in->rig->byte_count)||!span_apart(diagnostics,sizeof*diagnostics,in->rig->bytes,in->rig->byte_count)||*out)return COH_INVALID;
 uint32_t active_archives=0;for(unsigned i=0;i<COH_RECEIVED_COSTUME_ARCHIVES;i++)if(in->archives[i].read_at)active_archives++;
 uint64_t peak=0,fixed=sizeof(CohReceivedCostume)+sizeof(Plan)+COH_RECEIVED_COSTUME_STACK+(uint64_t)active_archives*coh_asset_zip_allocation_bytes(QUERIES);
 if(!charge(in->parent_bytes,0,fixed,&peak))return COH_LIMIT;
 CohReceivedCostume*a=calloc(1,sizeof*a);Plan*p=calloc(1,sizeof*p);uint8_t*source=NULL;void*header=NULL;void*scratch=NULL;size_t header_bytes=0;CohStatus status=COH_LIMIT;
 if(!a||!p){free(p);free(a);return COH_LIMIT;}p->cancel=in->cancel;a->stats.cpu_bytes=sizeof*a;a->stats.source_epoch=in->source_epoch;a->stats.entity_index=in->entity_index;a->stats.bodytype=in->snapshot->bodytype;
 size_t count=0;status=assembly(in,p,p->initial,&count,0);if(status){missing(a,"source Huge Appearance",status);goto end;}
 for(size_t i=0;i<count;i++)for(unsigned j=0;j<2;j++){char name[256];int n=snprintf(name,sizeof name,"SH_%s",p->initial[i].texture[j]);if(n<0||(size_t)n>=sizeof name||add_query(p,name,COH_ZIP_QUERY_TEXTURE)<0){status=missing(a,"source query capacity",COH_LIMIT);goto end;}}
 status=open_plan(p,in);if(status){missing(a,"loaded archive directories",status);goto end;}
 status=assembly(in,p,a->draws,&count,1);if(status)goto end;a->count=(uint32_t)count;close_plan(p);p->count=0;
 int fat=add_query(p,"data/player_library/HUGE_BONES_SCALE_L.geo",COH_ZIP_QUERY_PATH),skinny=add_query(p,"data/player_library/HUGE_BONES_SCALE_S.geo",COH_ZIP_QUERY_PATH);
 for(uint32_t i=0;i<a->count;i++)if(!(a->draws[i].flags&COH_APPEARANCE_CLEAR)){
  if(add_query(p,a->draws[i].geometry_path,COH_ZIP_QUERY_PATH)<0){status=missing(a,a->draws[i].geometry_path,COH_LIMIT);goto end;}
  status=coh_appearance_material_recipe(a->draws[i].texture[0],a->draws[i].texture[1],a->recipes+i);if(status){missing(a,a->draws[i].texture[0],status);goto end;}
  a->stats.material_fallbacks+=a->recipes[i].automatic_fallback;
  for(unsigned j=0;j<2;j++)if(!same(a->recipes[i].basic[j],"none")&&add_query(p,a->recipes[i].basic[j],COH_ZIP_QUERY_TEXTURE)<0){status=missing(a,a->recipes[i].basic[j],COH_LIMIT);goto end;}
 }
 status=open_plan(p,in);if(status){missing(a,"loaded selected sources",status);goto end;}
 size_t source_bytes=0;for(uint32_t i=0;i<p->count;i++){CohAssetZip*zip;const char*path;uint32_t bytes;status=locate(p,i,&zip,&path,&bytes);if(status){missing(a,p->names[i].name,status);goto end;}if(bytes>source_bytes)source_bytes=bytes;}
 if(!charge(in->parent_bytes,a->stats.cpu_bytes,fixed-sizeof*a+source_bytes,&peak)){status=COH_LIMIT;goto end;}source=malloc(source_bytes);if(!source){status=COH_LIMIT;goto end;}
 CohAppearanceHugeScales models;memset(&models,0,sizeof models);
 for(unsigned endpoint=0;endpoint<2;endpoint++){
  int id=endpoint?skinny:fat;CohAssetGeo geo;status=load_geo(p,id,source,source_bytes,&header,&geo,in->parent_bytes,a->stats.cpu_bytes,fixed-sizeof*a+source_bytes,&peak,&header_bytes,1);if(status){missing(a,p->names[id].name,status);goto end;}
  CohAppearanceHugeScales one;status=coh_appearance_huge_scale_models(&geo,&geo,&one);if(!status){if(endpoint){memcpy(models.skinny,one.skinny,sizeof models.skinny);models.skinny_models=one.skinny_models;}else{memcpy(models.fat,one.fat,sizeof models.fat);models.fat_models=one.fat_models;}}
  free(header);header=NULL;if(status)goto end;
 }
 CohAppearanceHugeScaleDiagnostics scale_diag;status=coh_appearance_huge_morph(in->snapshot,&models,a->morph_bytes,&a->morph,&scale_diag);if(status)goto end;a->stats.height_scale=scale_diag.height_scale;
 a->rig=*in->rig;a->rig.motion=a->rig.base;memset(a->rig.animation_delta,0,sizeof a->rig.animation_delta);a->rig.first_frame=0;
 if(coh_character_sample(&a->rig,&a->morph,0,&a->pose)){status=COH_INVALID;goto end;}
 for(uint32_t i=0;i<a->count;i++)if(!(a->draws[i].flags&COH_APPEARANCE_CLEAR)){
  CohAppearanceDraw*d=a->draws+i;int id=add_query(p,d->geometry_path,COH_ZIP_QUERY_PATH);CohAssetGeo geo;status=load_geo(p,id,source,source_bytes,&header,&geo,in->parent_bytes,a->stats.cpu_bytes,fixed-sizeof*a+source_bytes,&peak,&header_bytes,0);if(status){missing(a,d->geometry_path,status);goto end;}
  uint32_t index;CohAssetGeoModel model;status=coh_appearance_geo_model(&geo,d,4096,&index,&model);if(status){missing(a,d->model_name,status);goto end;}
  CohAppearanceMeshRequirements required;status=coh_appearance_mesh_requirements(&geo,index,d->socket,&required);if(status)goto end;
  uint64_t extra=fixed-sizeof*a+source_bytes+header_bytes+required.workspace_bytes+required.canonical_bytes;
  if(!charge(in->parent_bytes,a->stats.cpu_bytes,extra,&peak)){status=COH_LIMIT;goto end;}
  scratch=malloc(required.workspace_bytes);a->canonical[i]=malloc(required.canonical_bytes);if(!scratch||!a->canonical[i]){status=COH_LIMIT;goto end;}
  status=coh_appearance_mesh_build(&geo,index,d->socket,scratch,required.workspace_bytes,a->canonical[i],required.canonical_bytes,a->mesh+i,NULL);if(status)goto end;
  free(scratch);scratch=NULL;free(header);header=NULL;a->stats.cpu_bytes+=required.canonical_bytes;
  a->resources[i]=(CohAppearanceRenderResource){in->entity_index,1,i+1,1,1,4,0,a->mesh[i].index_count,d->geometry_path,d->model_name,a->mesh+i};a->material_counts[i]=required.materials;
  a->materials[i].material=coh_renderer_default_material(COH_MAT_DUAL);a->materials[i].surface_generation=1;
  a->materials[i].material.lighting=COH_LIGHT_DIFFUSE;
  a->materials[i].material.fog_params[2]=1e9f; /* explicit inspection environment: no guessed live fog */
  for(unsigned c=0;c<3;c++){a->materials[i].material.ambient[c]=.6f*a->recipes[i].ambient_scale;a->materials[i].material.diffuse[c]=.7f*a->recipes[i].diffuse_scale;}
  for(unsigned j=0;j<2;j++){
   const char*name=a->recipes[i].basic[j];a->materials[i].source_texture[j]=d->texture[j];uint32_t texture=0;for(;texture<a->stats.textures;texture++)if(same(a->textures[texture].name,name))break;
   if(texture==a->stats.textures){
    if(texture==64){status=COH_LIMIT;goto end;}Texture*t=a->textures+texture;memcpy(t->name,name,strlen(name)+1);
    if(same(name,"none")){t->width=t->height=1;t->bytes=4;if(!charge(in->parent_bytes,a->stats.cpu_bytes,fixed-sizeof*a+source_bytes+4,&peak)){status=COH_LIMIT;goto end;}t->pixels=malloc(4);if(!t->pixels){status=COH_LIMIT;goto end;}memset(t->pixels,255,4);}
    else{
     int q=add_query(p,name,COH_ZIP_QUERY_TEXTURE);CohAssetZip*zip;const char*path;uint32_t bytes;status=locate(p,(uint32_t)q,&zip,&path,&bytes);if(status){missing(a,name,status);goto end;}status=coh_asset_zip_read(zip,(uint32_t)q,source,bytes);if(status)goto end;
     CohAssetTexture view;status=coh_asset_texture((CohBytes){source,bytes},&view);if(status){missing(a,path,status);goto end;}
     t->width=view.width;t->height=view.height;t->bytes=(size_t)view.width*view.height*4u;
     if(!charge(in->parent_bytes,a->stats.cpu_bytes,fixed-sizeof*a+source_bytes+t->bytes,&peak)){status=COH_LIMIT;goto end;}t->pixels=malloc(t->bytes);if(!t->pixels){status=COH_LIMIT;goto end;}status=coh_asset_texture_rgba(&view,0,t->pixels,t->bytes);if(status){missing(a,path,status);goto end;}
    }
    a->stats.textures++;a->stats.cpu_bytes+=t->bytes;a->stats.texture_bytes+=t->bytes;
   }
   a->bindings[i][j]=texture;
  }
 }
 a->request=(CohAppearanceActorRequest){a->draws,a->resources,a->materials,a->material_counts,a->count,1,{in->entity_index,1,4,1,1,1,&a->rig,&a->morph,&a->pose},1,in->cancel};
 CohAppearanceActorDiagnostics requirements;status=coh_appearance_actor_requirements(&a->request,&requirements);if(status){missing(a,"source material ranges",status);goto end;}
 a->stats.parts=requirements.rendered_parts;a->stats.vertices=requirements.vertices;a->stats.indices=requirements.indices;
 a->stats.gpu_reserve_bytes=2u*(requirements.vertex_bytes+requirements.index_bytes)+a->stats.texture_bytes;
 uint64_t buffers=requirements.vertex_bytes+requirements.index_bytes,backend=coh_renderer_gles_allocation_bytes()+coh_renderer_allocation_bytes(120,3);
 if(!charge(in->parent_bytes,a->stats.cpu_bytes,buffers+backend+a->stats.gpu_reserve_bytes+fixed-sizeof*a+source_bytes,&peak)){status=COH_LIMIT;goto end;}
 a->vertices=malloc(requirements.vertex_bytes);a->indices=malloc(requirements.index_bytes);if(!a->vertices||!a->indices){status=COH_LIMIT;goto end;}a->stats.cpu_bytes+=buffers;
 a->stats.prepare_peak_bytes=peak;a->stats.renderer_cpu_reserve_bytes=backend;
 if(in->cancel.poll&&in->cancel.poll(in->cancel.context)){status=COH_CANCELLED;goto end;}
 a->request.cancel=(CohCancel){0};status=COH_OK;
end:
 free(header);free(scratch);free(source);close_plan(p);a->stats.source_reads=p->reads;a->stats.source_bytes=p->bytes;a->stats.prepare_peak_bytes=peak;free(p);
 if(diagnostics)*diagnostics=a->stats;
 if(status==COH_OK){*out=a;return status;}coh_received_costume_destroy(&a);return status;
}
CohStatus coh_received_costume_texture(const CohReceivedCostume*a,uint32_t index,CohBytes*bytes,uint32_t*width,uint32_t*height,const char**name){if(!a||index>=a->stats.textures||!bytes||!width||!height||!name||(uintptr_t)bytes%_Alignof(CohBytes)||(uintptr_t)width%_Alignof(uint32_t)||(uintptr_t)height%_Alignof(uint32_t)||(uintptr_t)name%_Alignof(const char*))return COH_INVALID;if(!outside(a,bytes,sizeof*bytes)||!outside(a,width,sizeof*width)||!outside(a,height,sizeof*height)||!outside(a,name,sizeof*name)||!span_apart(bytes,sizeof*bytes,width,sizeof*width)||!span_apart(bytes,sizeof*bytes,height,sizeof*height)||!span_apart(bytes,sizeof*bytes,name,sizeof*name)||!span_apart(width,sizeof*width,height,sizeof*height)||!span_apart(width,sizeof*width,name,sizeof*name)||!span_apart(height,sizeof*height,name,sizeof*name))return COH_INVALID;const Texture*t=a->textures+index;*bytes=(CohBytes){t->pixels,t->bytes};*width=t->width;*height=t->height;*name=t->name;return COH_OK;}
CohStatus coh_received_costume_bind(CohReceivedCostume*a,uint32_t generation,const uint32_t*handles,uint32_t count){if(!a||!generation||!handles||count!=a->stats.textures||(uintptr_t)handles%_Alignof(uint32_t)||!outside(a,handles,(size_t)count*sizeof*handles))return COH_INVALID;for(uint32_t i=0;i<count;i++)if(!handles[i])return COH_INVALID;for(uint32_t i=0;i<a->count;i++){a->materials[i].surface_generation=generation;for(unsigned j=0;j<2;j++)a->materials[i].material.textures[j]=(CohRenderTexture){handles[a->bindings[i][j]],COH_WRAP_REPEAT,COH_WRAP_REPEAT,COH_FILTER_LINEAR,COH_FILTER_LINEAR};}a->surface=generation;a->request.surface_generation=generation;return COH_OK;}
CohStatus coh_received_costume_draws(CohReceivedCostume*a,const float view[12],const float projection[16],const float position[3],const CohRenderDraw**out,size_t*count){
 if(!a||!view||!projection||!position||!out||!count||!a->surface)return COH_INVALID;
 if((uintptr_t)view%_Alignof(float)||(uintptr_t)projection%_Alignof(float)||(uintptr_t)position%_Alignof(float)||(uintptr_t)out%_Alignof(const CohRenderDraw*)||(uintptr_t)count%_Alignof(size_t))return COH_INVALID;
 if(!span_apart(out,sizeof*out,view,48)||!span_apart(out,sizeof*out,projection,64)||!span_apart(out,sizeof*out,position,12)||!span_apart(count,sizeof*count,view,48)||!span_apart(count,sizeof*count,projection,64)||!span_apart(count,sizeof*count,position,12))return COH_INVALID;
 if(!outside(a,view,48)||!outside(a,projection,64)||!outside(a,position,12)||!outside(a,out,sizeof*out)||!outside(a,count,sizeof*count)||!span_apart(out,sizeof*out,count,sizeof*count))return COH_INVALID;
 float mv[16]={0};for(unsigned col=0;col<3;col++)for(unsigned row=0;row<3;row++)mv[col*4+row]=view[col*3+row];for(unsigned row=0;row<3;row++)mv[12+row]=position[0]*view[row]+position[1]*view[3+row]+position[2]*view[6+row]+view[9+row];mv[15]=1;
 if(coh_character_sample(&a->rig,&a->morph,0,&a->pose))return COH_INVALID;
 if(++a->request.actor.pose_generation==0)a->request.actor.pose_generation=1;
 size_t n=0;CohStatus status=coh_appearance_actor_render(&a->request,mv,projection,&a->workspace,a->vertices,a->stats.vertices,a->indices,a->stats.indices,a->packets,120,&n,NULL);if(status)return status;
 /* Original renderbonedmodel:245 replaces tint alpha with node->alpha.
  * This Ready/base diagnostic uses the original default node alpha255 (:130),
  * not the unused high byte of the packet RGB tint and not a received fade. */
 for(size_t i=0;i<n;i++)a->packets[i].material.const0[3]=1.f;
 a->stats.frames++;a->stats.draws+=n;*out=a->packets;*count=n;return COH_OK;
}
