#include "../coh_appearance.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
unsigned appearance_corpus_tests(const char *directory){
 if(!directory)return 0;
 const char *names[]={"fem_pants.geo","fem_shirt.geo","huge_pants.geo","huge_shirt.geo","v_fem_head.geo","v_male_pants.geo","v_male_shirt.geo"};unsigned models=0;
 for(unsigned f=0;f<7;f++){
  char path[4096];int n=snprintf(path,sizeof path,"%s/%s",directory,names[f]);assert(n>0&&(size_t)n<sizeof path);FILE *file=fopen(path,"rb");if(!file)continue;
  assert(fseek(file,0,SEEK_END)==0);long length=ftell(file);assert(length>0&&length<2*1024*1024&&fseek(file,0,SEEK_SET)==0);uint8_t *bytes=malloc((size_t)length);assert(bytes&&fread(bytes,1,(size_t)length,file)==(size_t)length);fclose(file);
  CohBytes span={bytes,(size_t)length};size_t needed=0;assert(coh_asset_geo_workspace(span,&needed)==COH_OK);uint8_t *arena=malloc(needed);assert(arena);CohAssetGeo geo;assert(coh_asset_geo_open(span,arena,needed,4096,&geo)==COH_OK);
  for(uint32_t i=0;i<geo.model_count;i++){
   CohAssetGeoModel m,found;assert(coh_asset_geo_model(&geo,i,&m)==COH_OK);CohAppearanceDraw d={0};assert(strlen(m.name)<sizeof d.model_name);strcpy(d.model_name,m.name);uint32_t index=999;assert(coh_appearance_geo_model(&geo,&d,4096,&index,&found)==COH_OK&&index==i&&!strcmp(m.name,found.name));models++;
  }
  /* Caller supplies parsed validated GEO, but malformed record contents must
   * still be rejected by the existing bounded reader, not dereferenced blindly. */
  CohAssetGeo broken=geo;broken.records_offset=SIZE_MAX;CohAppearanceDraw d={0};strcpy(d.model_name,"missing");CohAssetGeoModel found;uint32_t index=999;assert(coh_appearance_geo_model(&broken,&d,4096,&index,&found)!=COH_OK);
  free(arena);free(bytes);
 }
 return models;
}
