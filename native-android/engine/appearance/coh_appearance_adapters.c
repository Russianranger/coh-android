#include "coh_appearance.h"
#include <string.h>
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+32u:c;}
static size_t identity_length(const char *s){const char *p=strstr(s,"__");return p?(size_t)(p-s):strlen(s);}
CohStatus coh_appearance_geo_model(const CohAssetGeo *geo,const CohAppearanceDraw *d,uint32_t maximum,uint32_t *index,CohAssetGeoModel *out){
 if(!geo||!d||!index||!out||!maximum||!memchr(d->model_name,0,sizeof d->model_name))return COH_INVALID;
 if(d->flags&COH_APPEARANCE_CLEAR)return COH_NOT_FOUND;
 if(geo->model_count>maximum)return COH_LIMIT;
 size_t wanted=identity_length(d->model_name);if(!wanted)return COH_INVALID;
 for(uint32_t i=0;i<geo->model_count;i++){
  CohAssetGeoModel m;CohStatus status=coh_asset_geo_model(geo,i,&m);if(status)return status;
  if(identity_length(m.name)!=wanted)continue;
  size_t j=0;while(j<wanted&&lower((unsigned char)m.name[j])==lower((unsigned char)d->model_name[j]))j++;
  if(j==wanted){*out=m;*index=i;return COH_OK;}
 }
 return COH_NOT_FOUND;
}
CohStatus coh_appearance_palette(const CohAppearanceDraw *d,uint32_t body,const CohAnimationRig *r,const CohCharacterMorph *m,const CohAnimationPose *pose,const uint32_t *ids,uint32_t count,float *rows,size_t capacity){
 if(!d||!r||!pose||!ids||!rows||body>=9||d->socket>=99||!count||count>15||d->flags&COH_APPEARANCE_CLEAR)return COH_INVALID;
 if(capacity<(size_t)count*12u)return COH_LIMIT;
 if(m&&(body!=4u||m->body_type!=4u))return COH_UNSUPPORTED;
 int status=m?coh_character_palette(r,m,pose,d->socket,ids,count,rows):coh_animation_palette(r,pose,d->socket,ids,count,rows);
 return status?COH_INVALID:COH_OK;
}
