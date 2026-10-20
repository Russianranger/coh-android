#include "coh_source_material_plan.h"
static void json_name(const char*s){putchar('"');for(;*s;s++){if(*s=='"'||*s=='\\')putchar('\\');putchar((unsigned char)*s);}putchar('"');}
static void material_tests(CohSourceSealed*sealed,const char*cachepath,const char*statespath){
 CohSourceSealedReport sr;CHECK(coh_source_sealed_report(sealed,&sr)==COH_OK);
 CohSourceMaterialPlan copies[21];unsigned count=0;size_t peak=0;
 const size_t loaderreserve=16u<<20,caller=sizeof(copies)+262144u;
 FILE*fp=fopen(cachepath,"rb");CHECK(fp&&!fseek(fp,0,SEEK_END));long size=ftell(fp);CHECK(size==13537052);rewind(fp);
 CohAssetLoader*loader=NULL;CohAssetLimits ll={16u<<20,16u<<20,16u<<20,16u<<20,4,4,4};CHECK(coh_asset_create(&ll,&loader)==COH_OK);CHECK(coh_asset_mount_file(loader,"data/bin/tricks.bin",(CohAssetSource){read_at,fp,(uint64_t)size,17})==COH_OK);
 CohWrTexOptCache*cache=NULL;CohWrTexOptLimits lim={1u<<20,96u<<20,loaderreserve,sr.owned_bytes+sr.shared_source_bytes+caller};CHECK(coh_wr_texopt_cache_open(loader,(CohAssetId){"data/bin/tricks.bin",17},digest,NULL,&lim,(CohCancel){0},&cache)==COH_OK);
 CohWrTexOptCacheReport cr;CHECK(coh_wr_texopt_cache_report(cache,&cr)==COH_OK);
 CohBytes states=file(statespath,15380);CHECK(states.size==15380);CohWrSurfaceStates*surface=NULL;CohWrSurfaceLimits sl={1u<<20,96u<<20,lim.external_bytes+cr.owned_bytes+loaderreserve+states.size};CHECK(coh_wr_surface_prepare(states,17,digest,NULL,&sl,(CohCancel){0},&surface)==COH_OK);free((void*)states.data);CohWrSurfaceReport sur;CHECK(coh_wr_surface_report(surface,&sur)==COH_OK);
 lim.external_bytes+=cr.owned_bytes+loaderreserve+sur.owned_bytes;
 CohSourceMaterialBudget budget={96u<<20,cr.owned_bytes+loaderreserve+sur.owned_bytes+caller};
 for(unsigned slot=0;slot<2;slot++){
  CohSourceSealedEntry entry;CHECK(coh_source_sealed_entry(sealed,slot,&entry)==COH_OK);
  for(unsigned part=0;part<entry.parts;part++){
   CohSourceMeshPart p;CHECK(coh_source_sealed_part(sealed,slot,part,&p)==COH_OK);uint32_t ordinal=UINT32_MAX;CHECK(coh_wr_texopt_cache_find(cache,p.source_material.texture_name,&ordinal)==COH_OK);
   CohWrTexOptRecord*record=NULL;CHECK(coh_wr_texopt_record_create(cache,ordinal,surface,&lim,(CohCancel){0},&record)==COH_OK);
   CohWrTexOptView view;CHECK(coh_wr_texopt_record_view(record,&view)==COH_OK);
   CohSourceMaterialPlan value,saved;memset(&value,0x45,sizeof(value));saved=value;
   fail_at=1;alloc_count=0;CHECK(coh_source_material_plan(sealed,slot,part,record,&budget,&value)==COH_OK&&!alloc_count);fail_at=0;
   CHECK(value.texopt_ordinal==ordinal&&value.table_owner_ordinal==ordinal&&value.source_ordinal==entry.source_ordinal&&value.source_part==part&&value.texture_index==p.source_material.texture_id&&value.triangles==p.index_count/3u);
   CHECK(value.texopt_source_file.present&&view.source_file&&!strcmp(value.texopt_source_file.name,view.source_file)&&value.texopt_source_age==view.source_age&&value.texopt_flags==view.flags&&value.texopt_blend==view.blend_mode);
   CHECK(value.original_CLIENT_postprocessed&&!value.effective_client_material&&!value.texture_bodies_verified&&!value.gpu_owner&&!value.live_generation_admitted&&!value.world_authority&&value.historical_client_generation==17&&value.source_asset_generation==20261016);
   CHECK(value.aggregate_reserved_bytes==budget.retained_bytes+sr.owned_bytes+sr.shared_source_bytes+view.owned_bytes+sizeof(budget)+sizeof(value)+32768);
   if(value.aggregate_reserved_bytes>peak)peak=value.aggregate_reserved_bytes;
   for(unsigned n=0;n<13;n++){CHECK(value.slots[n].present==(view.layers[n].name!=NULL));if(view.layers[n].name)CHECK(!strcmp(value.slots[n].name,view.layers[n].name));}
   CohSourceMaterialBudget exact=budget;exact.aggregate_limit=value.aggregate_reserved_bytes;CHECK(coh_source_material_plan(sealed,slot,part,record,&exact,&value)==COH_OK);saved=value;
   exact.aggregate_limit--;CHECK(coh_source_material_plan(sealed,slot,part,record,&exact,&value)==COH_LIMIT&&!memcmp(&saved,&value,sizeof(value)));
   exact=budget;exact.retained_bytes=SIZE_MAX;CHECK(coh_source_material_plan(sealed,slot,part,record,&exact,&value)==COH_LIMIT&&!memcmp(&saved,&value,sizeof(value)));
   exact=budget;exact.aggregate_limit=COH_SG_TRANSACTION_MAX+1u;CHECK(coh_source_material_plan(sealed,slot,part,record,&exact,&value)==COH_LIMIT&&!memcmp(&saved,&value,sizeof(value)));
   CHECK(coh_source_material_plan(sealed,slot,part,record,&budget,(CohSourceMaterialPlan*)&budget)==COH_INVALID);
   CHECK(coh_source_material_plan(sealed,slot,part,record,&budget,(CohSourceMaterialPlan*)sealed)==COH_INVALID);
   CHECK(coh_source_material_plan(sealed,slot,part,record,&budget,(CohSourceMaterialPlan*)record)==COH_INVALID);
   CHECK(coh_source_material_plan(sealed,slot,part,record,&budget,(CohSourceMaterialPlan*)entry.original_header.data)==COH_INVALID);
   CHECK(coh_source_material_plan(sealed,slot,part,record,&budget,(CohSourceMaterialPlan*)entry.resource_record.data)==COH_INVALID);
   CHECK(coh_source_material_plan(sealed,slot,part,record,&budget,(CohSourceMaterialPlan*)(uintptr_t)(UINTPTR_MAX-4))==COH_INVALID);
   CHECK(coh_source_material_plan(sealed,slot,entry.parts,record,&budget,&value)==COH_NOT_FOUND&&!memcmp(&saved,&value,sizeof(value)));
   CHECK(coh_source_material_plan(sealed,2,part,record,&budget,&value)==COH_NOT_FOUND&&!memcmp(&saved,&value,sizeof(value)));
   CHECK(coh_source_material_plan(NULL,slot,part,record,&budget,&value)==COH_INVALID&&!memcmp(&saved,&value,sizeof(value)));
   CHECK(coh_source_material_plan(sealed,slot,part,NULL,&budget,&value)==COH_INVALID&&!memcmp(&saved,&value,sizeof(value)));
   CHECK(coh_source_material_plan(sealed,slot,part,record,NULL,&value)==COH_INVALID&&!memcmp(&saved,&value,sizeof(value)));
   CHECK(coh_source_material_plan(sealed,slot,part,record,&budget,NULL)==COH_INVALID);
   CHECK(count<21);copies[count++]=value;coh_wr_texopt_record_release(&record);CHECK(!record);
  }
 }
 CohWrTexOptRecord*wrongrecord=NULL;CHECK(coh_wr_texopt_record_create(cache,0,surface,&lim,(CohCancel){0},&wrongrecord)==COH_OK);CohSourceMaterialPlan refused=copies[0];CHECK(coh_source_material_plan(sealed,0,0,wrongrecord,&budget,&refused)==COH_NOT_FOUND&&!memcmp(&refused,&copies[0],sizeof(refused)));coh_wr_texopt_record_release(&wrongrecord);
 coh_wr_texopt_cache_release(&cache);coh_wr_surface_release(&surface);coh_asset_trim(loader);CHECK(!coh_asset_stats(loader).pinned_blobs&&!coh_asset_stats(loader).resident_bytes&&coh_asset_destroy(&loader)==COH_OK&&!fclose(fp));
 CHECK(count==21);for(unsigned i=0;i<count;i++){
  CohSourceMaterialPlan*v=&copies[i];printf("{\"material_plan\":true,\"source_ordinal\":%u,\"part\":%u,\"texture_id\":%u,\"triangles\":%u,\"texopt_ordinal\":%u,\"partition_key\":",v->source_ordinal,v->source_part,v->texture_index,v->triangles,v->texopt_ordinal);json_name(v->partition_key);printf(",\"texopt_key\":");json_name(v->texopt_key);printf(",\"texopt_source_file\":");json_name(v->texopt_source_file.name);printf(",\"texopt_source_age\":%u,\"texopt_flags\":%u,\"texopt_blend\":%u,\"slots\":[",v->texopt_source_age,v->texopt_flags,v->texopt_blend);for(unsigned n=0;n<16;n++){if(n)putchar(',');if(v->slots[n].present)json_name(v->slots[n].name);else printf("null");}printf("],\"fallback\":%u,\"record_owned\":%zu,\"aggregate\":%zu}\n",v->fallback_enabled,v->record_owned_bytes,v->aggregate_reserved_bytes);
 }
 printf("{\"material_plan_summary\":true,\"plans\":%u,\"peak_named_bytes\":%zu,\"record_cache_surface_loader_actually_released\":true,\"plan_heap_allocations\":0,\"effective_material\":false,\"texture_bodies_verified\":false,\"gpu_owner\":false,\"world_authority\":false}\n",count,peak);
}
