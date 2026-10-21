#include "coh_appearance_material.h"
#include <string.h>
static int apart(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x<y?an<=y-x:bn<=x-y);}
static size_t length(const char*s){if(!s)return 0;for(size_t n=0;n<256;n++)if(!s[n])return n;return 0;}
static int same(const char*a,const char*b){for(unsigned i=0;i<256;i++){unsigned x=(unsigned char)a[i],y=(unsigned char)b[i];if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0;if(!x)return 1;}return 0;}
CohStatus coh_appearance_material_recipe(const char primary[256],const char secondary[256],CohAppearanceMaterialRecipe*out){
 if(!primary||!secondary||!out||(uintptr_t)out%_Alignof(CohAppearanceMaterialRecipe))return COH_INVALID;
 size_t p=length(primary),s=length(secondary);if(!p||!s||!apart(primary,p+1,out,sizeof*out)||!apart(secondary,s+1,out,sizeof*out))return COH_INVALID;
 CohAppearanceMaterialRecipe result={{{0}},0,1,1.f,1.f};
 memcpy(result.basic[0],primary,p+1);memcpy(result.basic[1],secondary,s+1);
 /* Original TexOpt records: shader_villain_enforcer:319..383,
  * shader_villain_male_robot:572..635, shader_villain_gear_pads:1..64.
  * All have Base1 + DualColor1, no explicit fallback/water/old-tint.
  * tex.c:978..984 therefore chooses DUAL without BUMPMAPS. Its original
  * fixLightingScalesOnFallback:705..729 scales ambient/diffuse by 0.5.
  * setSwappableInfo:783..823 and rendermodel.c:getSwapX leave fixed DualColor1
  * intact; only the original Swappable leaf accepts the packet generic. */
 if(same(primary,"X_Enforcer_Glove_01_Mask")){
  strcpy(result.basic[0],"Glove_V_Enforcer_01");
  result.automatic_fallback=1;
 }else if(same(primary,"X_FullHelm_Robot_01")){
  strcpy(result.basic[0],"Face_V_Helmet_Robotic_01");strcpy(result.basic[1],"Face_V_Helmet_Robotic_01_dual");result.automatic_fallback=1;result.generic_swappable=0;
 }else if(same(primary,"X_Gear_Pads")){
  strcpy(result.basic[0],"spadr_v_Gears_01");strcpy(result.basic[1],"spadr_v_Gears_01_Mask");result.automatic_fallback=1;result.generic_swappable=0;
 }else if((primary[0]=='x'||primary[0]=='X')&&primary[1]=='_')return COH_UNSUPPORTED;
 if(result.automatic_fallback)result.ambient_scale=result.diffuse_scale=.5f;
 if(same(result.basic[0],"none"))strcpy(result.basic[0],"none");
 if(same(result.basic[1],"none"))strcpy(result.basic[1],"none");
 *out=result;return COH_OK;
}
