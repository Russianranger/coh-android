#include "coh_wr_model_material.h"
#include <stdint.h>
#include <string.h>
/* Original source bit values. check_model_material.py binds these against the
 * original enum declarations and executes unchanged original policy functions. */
#define OBJ_ALPHASORT (1u<<0)
#define OBJ_FANCYWATER (1u<<1)
#define OBJ_FULLBRIGHT (1u<<2)
#define OBJ_TREEDRAW (1u<<8)
#define OBJ_ALLOW_MULTISPLIT (1u<<9)
#define OBJ_FORCEOPAQUE (1u<<10)
#define OBJ_BUMPMAP (1u<<11)
#define OBJ_WORLDFX (1u<<12)
#define OBJ_DRAWBONED (1u<<14)
#define OBJ_STATICFX (1u<<15)
#define OBJ_HIDE (1u<<16)
#define OBJ_ALPHASORTALL (1u<<18)
#define TRICK_ADDITIVE (1u<<0)
#define TRICK_SUBTRACTIVE (1u<<1)
#define TRICK_ALPHACUTOUT (1u<<4)
#define TRICK_DOUBLESIDED (1u<<6)
#define TRICK_REFLECT_TEX1 (1u<<8)
#define TRICK2_HASADDGLOW (1u<<0)
#define TRICK2_SETCOLOR (1u<<17)
#define TRICK2_NORANDOMADDGLOW (1u<<20)
#define TRICK2_ALWAYSADDGLOW (1u<<21)
#define TRICK2_FALLBACKFORCEOPAQUE (1u<<31)
#define TEXOPT_NORANDOMADDGLOW (1u<<4)
#define TEXOPT_ALWAYSADDGLOW (1u<<8)
#define TEXOPT_FALLBACKFORCEOPAQUE (1u<<29)
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static unsigned fold(unsigned x){return x>='A'&&x<='Z'?x+32:x;}
static int name(const char*s,size_t*n){if(!s)return 0;for(size_t i=0;i<256;i++){unsigned v=(unsigned char)s[i];if(!v){*n=i;return i!=0;}if(v<32||v>126)return 0;}return 0;}
static int starts(const char*s,const char*k){for(;*k;k++,s++)if(!*s||fold((unsigned char)*s)!=fold((unsigned char)*k))return 0;return 1;}
static int equal(const char*s,const char*k){return strlen(s)==strlen(k)&&starts(s,k);}
static int contains(const char*s,const char*k){for(;*s;s++)if(starts(s,k))return 1;return 0;}
static int dual(CohWrModelBlend b){return b.shader==6||b.shader==2||b.shader==8;}
static int bump(CohWrModelBlend b,uint32_t enabled){return enabled&&(b.shader==6||b.shader==5||b.shader==8||b.shader==7);}
static CohWrModelBlend mode(int shader){return(CohWrModelBlend){shader,0};}
static CohWrModelBlend promote(CohWrModelBlend old,CohWrModelBlend next,uint32_t enabled){
 if(!next.shader)return old;
 if(!old.shader)return next;
 if(next.shader==old.shader&&next.bits==old.bits)return old;
 if(next.shader==1)return old;
 if(old.shader==1)return next;
 if(next.shader==8||old.shader==8){if(next.shader==8&&old.shader==8)return(CohWrModelBlend){8,next.bits&old.bits};return next.shader==8?next:old;}
 if(next.shader==6||old.shader==6)return mode(6);
 int has_bump=bump(old,enabled)||bump(next,enabled);
 if(next.shader==3||old.shader==3)return mode(3);
 if(has_bump)return mode(next.shader==2||old.shader==2?6:5);
 if(next.shader==2||old.shader==2)return mode(2);
 return next;
}
static uint32_t alpha_sort(const CohWrModelMaterialPart*p,CohWrModelBlend selected){
 if(p->is_fallback&&p->texopt_present&&(p->texopt_flags&TEXOPT_FALLBACKFORCEOPAQUE))return 0;
 uint32_t alpha=p->layer_alpha_mask;
 if(selected.shader==8){
  if(alpha&((1u<<3)|(1u<<1)))return OBJ_ALPHASORT;
  if(p->mask_is_exact_white)return 0;
  if(alpha&((1u<<8)|(1u<<6)))return OBJ_ALPHASORT;
  if((p->blend.shader==0||p->blend.shader==1)&&(alpha&1u))return OBJ_ALPHASORT;
  return 0;
 }
 if(selected.shader==3)return 0;
 uint32_t first=selected.shader==2||selected.shader==6||selected.shader==4?1u<<1:1u;
 if(alpha&first)return OBJ_ALPHASORT;
 if((selected.shader==0||selected.shader==1||selected.shader==5)&&(alpha&(1u<<1)))return OBJ_ALPHASORT;
 return 0;
}
CohStatus coh_wr_model_material_project(const CohWrModelMaterialInput*q,CohWrModelMaterialProjection*out){
 if(!q||!out||!apart(q,sizeof(*q),out,sizeof(*out)))return COH_INVALID;
 if(!q->parts||!q->part_count||q->part_count>COH_WR_MODEL_MATERIAL_PARTS_MAX||q->selected_trick_present>1||q->bone_info_present>1||q->normals_present>1||q->bumpmaps_enabled>1||q->water_mode>4)return COH_INVALID;
 if(!q->selected_trick_present&&(q->trick_flags1||q->trick_flags2||q->trick_model_flags))return COH_INVALID;
 if(!apart(q->parts,(size_t)q->part_count*sizeof(*q->parts),out,sizeof(*out)))return COH_INVALID;
 size_t length;if(!name(q->model_name,&length)||!apart(q->model_name,length+1,out,sizeof(*out)))return COH_INVALID;
 for(uint32_t i=0;i<q->part_count;i++){
  const CohWrModelMaterialPart*p=&q->parts[i];
  if(!name(p->name,&length)||!apart(p->name,length+1,out,sizeof(*out))||p->blend.shader<0||p->blend.shader>9||p->blend.bits>65535||p->layer_present_mask>2047||p->layer_alpha_mask>2047||!(p->layer_present_mask&1)||p->layer_alpha_mask&~p->layer_present_mask||p->mask_is_exact_white>1||(p->mask_is_exact_white&&!(p->layer_present_mask&(1u<<4)))||p->texopt_present>1||p->multiply1_reflect>1||p->is_fallback>1)return COH_INVALID;
  if(!p->texopt_present&&(p->texopt_flags||p->texopt_model_flags||p->multiply1_reflect))return COH_INVALID;
 }
 CohWrModelMaterialProjection result;memset(&result,0,sizeof(result));
 result.part_count=q->part_count;result.trick_present=q->selected_trick_present;result.trick_info_present=q->selected_trick_present;
 result.trick_flags1=q->trick_flags1;result.trick_flags2=q->trick_flags2;result.model_flags=q->selected_trick_present?q->trick_model_flags:0;
 CohWrModelBlend minimum=mode(1),merged=mode(1);
 int alpha_hack=starts(q->model_name,"GEO_")&&!(result.model_flags&(OBJ_WORLDFX|OBJ_STATICFX));
 if(alpha_hack){minimum=mode(2);if(contains(q->model_name,"eyes")){result.trick_present=1;result.trick_flags1|=TRICK_DOUBLESIDED;}}
 if(q->bone_info_present)result.model_flags|=OBJ_DRAWBONED;
 uint32_t visible=0;
 for(uint32_t i=0;i<q->part_count;i++){
  const CohWrModelMaterialPart*p=&q->parts[i];
  if(p->blend.shader==3)minimum=p->blend;
  if(bump(p->blend,q->bumpmaps_enabled))result.model_flags|=OBJ_BUMPMAP;
  if(dual(p->blend)){result.trick_present=1;result.trick_flags2|=TRICK2_SETCOLOR;}
  if(p->blend.shader==3){result.trick_present=1;result.trick_flags2|=TRICK2_HASADDGLOW|TRICK2_SETCOLOR;}
  if(p->blend.shader==7){result.trick_present=1;result.trick_flags2|=TRICK2_SETCOLOR;}
  if(!starts(p->name,"clearalpha")&&!equal(p->name,"invisible")&&!equal(p->name,"churn_col_alpha_01"))visible++;
  if(p->texopt_present){
   if(p->texopt_flags&TEXOPT_NORANDOMADDGLOW){result.trick_present=1;result.trick_flags2|=TRICK2_NORANDOMADDGLOW;}
   if(p->texopt_flags&TEXOPT_ALWAYSADDGLOW){result.trick_present=1;result.trick_flags2|=TRICK2_ALWAYSADDGLOW;}
   result.model_flags|=p->texopt_model_flags;
   if(p->multiply1_reflect&&(p->blend.shader==1||p->blend.shader==0)){result.trick_present=1;result.trick_flags1|=TRICK_REFLECT_TEX1;}
   if(p->texopt_flags&TEXOPT_FALLBACKFORCEOPAQUE){result.trick_present=1;result.trick_flags2|=TRICK2_FALLBACKFORCEOPAQUE;}
  }
  merged=promote(merged,p->blend,q->bumpmaps_enabled);
 }
 if((result.model_flags&OBJ_FANCYWATER)&&q->water_mode>0)minimum=mode(7);
 if(dual(minimum)){result.trick_present=1;result.trick_flags2|=TRICK2_SETCOLOR;}
 result.common_blend=mode(-1);
 for(uint32_t i=0;i<q->part_count;i++){
  const CohWrModelMaterialPart*p=&q->parts[i];CohWrModelBlend chosen;
  if(minimum.shader<=1&&p->blend.shader>0)chosen=p->blend;
  else if(minimum.shader==2)chosen=dual(p->blend)?p->blend:minimum;
  else if(minimum.shader==3)chosen=p->blend.shader<=1?minimum:p->blend;
  else chosen=minimum;
  if(chosen.shader==2&&bump(p->blend,q->bumpmaps_enabled))chosen=mode(6);
  result.parts[i]=chosen;
  if(result.common_blend.shader==-1)result.common_blend=chosen;
  else if(result.common_blend.shader!=chosen.shader)result.common_blend=mode(0);
 }
 if(merged.shader&&(result.model_flags&(OBJ_FORCEOPAQUE|OBJ_ALLOW_MULTISPLIT))==OBJ_FORCEOPAQUE)result.parts[0]=merged;
 if(!alpha_hack){
  if((result.model_flags&OBJ_TREEDRAW)||(result.trick_present&&(result.trick_flags1&TRICK_ALPHACUTOUT))){
   if((result.model_flags&(OBJ_FORCEOPAQUE|OBJ_ALLOW_MULTISPLIT))!=OBJ_FORCEOPAQUE)result.model_flags|=OBJ_FORCEOPAQUE|OBJ_ALLOW_MULTISPLIT;
  }else for(uint32_t i=0;i<q->part_count;i++)result.model_flags|=alpha_sort(&q->parts[i],result.parts[i]);
 }
 if(!visible)result.model_flags|=OBJ_HIDE;
 if(!q->normals_present)result.model_flags|=OBJ_FULLBRIGHT;
 if(result.trick_present&&(result.trick_flags1&(TRICK_ADDITIVE|TRICK_SUBTRACTIVE)))result.model_flags|=OBJ_ALPHASORT|OBJ_ALPHASORTALL;
 if(result.trick_info_present&&(q->trick_model_flags&OBJ_ALPHASORT))result.model_flags|=OBJ_ALPHASORTALL;
 if(result.model_flags&OBJ_FORCEOPAQUE)result.model_flags&=~OBJ_ALPHASORT;
 if(result.model_flags&(OBJ_WORLDFX|OBJ_STATICFX))result.model_flags&=~OBJ_DRAWBONED;
 for(uint32_t i=0;i<q->part_count;i++){
  CohWrModelBlend b=result.parts[i];if(b.shader<1||b.shader>3)result.unrepresented_shader_mask|=1u<<(unsigned)b.shader;
  result.nonzero_blend_bits|=b.bits;
 }
 *out=result;return COH_OK;
}
