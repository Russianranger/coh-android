#include "coh_appearance_scales.h"
#include <math.h>
#include <string.h>
typedef struct {const void *p;size_t n;} Span;
static int valid(Span s){return !s.n||(s.p&&s.n<=UINTPTR_MAX-(uintptr_t)s.p);}
static int apart(Span a,Span b){return !a.n||!b.n||((uintptr_t)a.p<(uintptr_t)b.p?a.n<=(uintptr_t)b.p-(uintptr_t)a.p:b.n<=(uintptr_t)a.p-(uintptr_t)b.p);}
static int same(const char*a,const char*b){for(size_t i=0;i<256;i++){unsigned x=(unsigned char)a[i],y=(unsigned char)b[i];if(x>='a'&&x<='z')x-=32;if(y>='a'&&y<='z')y-=32;if(x!=y)return 0;if(!x)return 1;}return 0;}
static const char *const bones[99]={
#include "huge_bone_names.inc"
};
static int separate_geo(const CohAssetGeo *g,Span write){Span s[]={{g,sizeof *g},{g->header.data,g->header.size},{g->payload.data,g->payload.size}};for(unsigned i=0;i<3;i++)if(!valid(s[i])||!apart(s[i],write))return 0;return 1;}
static CohStatus endpoints(const CohAssetGeo *g,float out[99][3],uint32_t *models){
 unsigned char found[99]={0};if(!g||g->model_count>4096u)return COH_INVALID;
 for(unsigned i=0;i<99;i++)for(unsigned j=0;j<3;j++)out[i][j]=1.f;
 *models=0;
 for(uint32_t i=0;i<g->model_count;i++){
  CohAssetGeoModel m;CohStatus status=coh_asset_geo_scale_model(g,i,&m);if(status)return status;
  for(unsigned bone=0;bone<99;bone++)if(same(m.name,bones[bone])){
   if(found[bone])break; /* animFindBoneInHeader returns its first match. */
   for(unsigned j=0;j<3;j++)if(!isfinite(m.scale[j])||m.scale[j]<=0.f||m.scale[j]>16.f)return COH_INVALID;
   memcpy(out[bone],m.scale,sizeof m.scale);found[bone]=1;(*models)++;break;
  }
 }
 return COH_OK;
}
CohStatus coh_appearance_huge_scale_models(const CohAssetGeo *fat,const CohAssetGeo *skinny,CohAppearanceHugeScales*out){
 if(!fat||!skinny||!out||(uintptr_t)out%_Alignof(CohAppearanceHugeScales))return COH_INVALID;
 Span write={out,sizeof *out};if(!valid(write)||!separate_geo(fat,write)||!separate_geo(skinny,write))return COH_INVALID;
 CohAppearanceHugeScales candidate;CohStatus status=endpoints(fat,candidate.fat,&candidate.fat_models);if(status)return status;
 status=endpoints(skinny,candidate.skinny,&candidate.skinny_models);if(status)return status;
 *out=candidate;return COH_OK;
}
static void u32(uint8_t *p,uint32_t value){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(value>>(i*8));}
static void f32(uint8_t*p,float value){uint32_t bits;memcpy(&bits,&value,4);u32(p,bits);}
CohStatus coh_appearance_huge_morph(const CohOriginalCostumeSnapshot*s,const CohAppearanceHugeScales*scales,uint8_t bytes[COH_APPEARANCE_HUGE_MORPH_BYTES],CohCharacterMorph*out,CohAppearanceHugeScaleDiagnostics*diag){
 if(!s||!scales||!bytes||!out||!diag)return COH_INVALID;
 Span read[]={{s,sizeof *s},{scales,sizeof *scales}},write[]={{bytes,COH_APPEARANCE_HUGE_MORPH_BYTES},{out,sizeof *out},{diag,sizeof *diag}};
 for(unsigned i=0;i<3;i++){if(!valid(write[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(write[i],write[j]))return COH_INVALID;for(unsigned j=0;j<2;j++)if(!valid(read[j])||!apart(write[i],read[j]))return COH_INVALID;}
 if((uintptr_t)s%_Alignof(CohOriginalCostumeSnapshot)||(uintptr_t)scales%_Alignof(CohAppearanceHugeScales)||(uintptr_t)out%_Alignof(CohCharacterMorph)||(uintptr_t)diag%_Alignof(CohAppearanceHugeScaleDiagnostics))return COH_INVALID;
 if(s->bodytype!=4||s->converted_scale<0||s->converted_scale>1||scales->fat_models>99||scales->skinny_models>99)return COH_INVALID;
 for(unsigned i=0;i<30;i++)if(!isfinite(s->scales[i]))return COH_INVALID;
 float height=(s->scales[0]/100.f)+1.f;
 if(!isfinite(height)||height<=0.f||height>32.f)return COH_INVALID;
 /* scaleHero/changeScale: Huge GeomScale is exactly 1,1,1. */
 float h[53]={height,height,height,s->scales[1],s->scales[3],s->scales[4],s->scales[5],s->scales[6],s->scales[7],s->scales[8],s->scales[9],s->scales[10],s->scales[11],.70f,
  -.19f,.06f,0.f,.14f,-.05f,0.f,.04f,0.f,0.f,0.f,-.01f,.05f,.05f,.07f,.05f,.065f,.075f,.055f};
 for(unsigned i=0;i<21;i++)h[32+i]=s->scales[9+i];
 memset(bytes,0,COH_APPEARANCE_HUGE_MORPH_BYTES);memcpy(bytes,"COHMOR01",8);
 const uint32_t header[]={1,256,99,256,28,3028,4,0};for(unsigned i=0;i<8;i++)u32(bytes+8+i*4,header[i]);
 for(unsigned i=0;i<53;i++)f32(bytes+40+i*4,h[i]);
 for(unsigned bone=0;bone<99;bone++){uint8_t*p=bytes+256+bone*28;u32(p,bone);for(unsigned j=0;j<3;j++){f32(p+4+j*4,scales->fat[bone][j]);f32(p+16+j*4,scales->skinny[bone][j]);}}
 CohCharacterMorph candidate;if(coh_character_parse_morph(bytes,COH_APPEARANCE_HUGE_MORPH_BYTES,&candidate))return COH_INVALID;
 *out=candidate;*diag=(CohAppearanceHugeScaleDiagnostics){s->bodytype,(uint32_t)s->converted_scale,scales->fat_models,scales->skinny_models,height};return COH_OK;
}
