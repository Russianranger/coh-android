#include "coh_appearance_material.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,cases;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"huge-material:%d: %s\n",__LINE__,#x);exit(1);}}while(0)
void source_material_recipe(unsigned,const char *,const char *,CohAppearanceMaterialRecipe *);
static void compare(unsigned recipe,const char *primary,const char *secondary){
 char p[256]={0},s[256]={0};CohAppearanceMaterialRecipe actual,expected;
 CHECK(strlen(primary)<sizeof p&&strlen(secondary)<sizeof s);strcpy(p,primary);strcpy(s,secondary);
 memset(&actual,0xa5,sizeof actual);CHECK(coh_appearance_material_recipe(p,s,&actual)==COH_OK);source_material_recipe(recipe,p,s,&expected);
 CHECK(!strcmp(actual.basic[0],expected.basic[0]));CHECK(!strcmp(actual.basic[1],expected.basic[1]));
 CHECK(actual.automatic_fallback==expected.automatic_fallback);CHECK(actual.generic_swappable==expected.generic_swappable);
 CHECK(actual.ambient_scale==expected.ambient_scale&&actual.diffuse_scale==expected.diffuse_scale);cases++;
}
static void rejected(const char *primary,const char *secondary,CohStatus expected){
 CohAppearanceMaterialRecipe output,saved;memset(&output,0xa5,sizeof output);saved=output;
 CHECK(coh_appearance_material_recipe(primary,secondary,&output)==expected);CHECK(!memcmp(&output,&saved,sizeof output));
}
int main(void){
 static const char *const names[]={"X_Enforcer_Glove_01_Mask","X_FullHelm_Robot_01","X_Gear_Pads"};
 static const char *const secondary[]={"None","NONE","Packet_Secondary_MiXeD"};
 for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++){
  compare(i+1,names[i],secondary[j]);char folded[256]={0};strcpy(folded,names[i]);
  for(unsigned k=0;folded[k];k++)if(folded[k]>='A'&&folded[k]<='Z')folded[k]=(char)(folded[k]-'A'+'a');
  compare(i+1,folded,secondary[j]);
 }
 compare(0,"Ordinary_Primary","Packet_Secondary_MiXeD");compare(0,"SH_HIPS_Pants","None");compare(0,"NoNe","nOnE");compare(0,"X","ordinary");
 char longest[256];memset(longest,'p',255);longest[255]=0;compare(0,longest,longest);
 char missing[256];memset(missing,'q',sizeof missing);
 rejected(NULL,"none",COH_INVALID);rejected("none",NULL,COH_INVALID);rejected("","none",COH_INVALID);rejected("none","",COH_INVALID);
 rejected(missing,"none",COH_INVALID);rejected("none",missing,COH_INVALID);rejected("X_Unknown_Composite","none",COH_UNSUPPORTED);rejected("x_not_a_supported_recipe","none",COH_UNSUPPORTED);
 char none[256]="none",ordinary[256]="ordinary";CHECK(coh_appearance_material_recipe(none,none,NULL)==COH_INVALID);
 CohAppearanceMaterialRecipe alias,saved;memset(&alias,0xa5,sizeof alias);strcpy(alias.basic[0],"Ordinary_Primary");saved=alias;
 CHECK(coh_appearance_material_recipe(alias.basic[0],none,&alias)==COH_INVALID);CHECK(!memcmp(&alias,&saved,sizeof alias));
 strcpy(alias.basic[1],"Packet_Secondary");saved=alias;CHECK(coh_appearance_material_recipe(ordinary,alias.basic[1],&alias)==COH_INVALID);CHECK(!memcmp(&alias,&saved,sizeof alias));
 union {max_align_t align;unsigned char bytes[sizeof(CohAppearanceMaterialRecipe)+16];} misaligned;
 memset(&misaligned,0xa5,sizeof misaligned);unsigned char before[sizeof misaligned];memcpy(before,&misaligned,sizeof before);
 CHECK(coh_appearance_material_recipe(ordinary,none,(CohAppearanceMaterialRecipe*)(misaligned.bytes+1))==COH_INVALID);CHECK(!memcmp(&misaligned,before,sizeof before));
 struct {CohAppearanceMaterialRecipe output;char primary[256],secondary[256];} adjacent={0};strcpy(adjacent.primary,"Adjacent_Primary");strcpy(adjacent.secondary,"Adjacent_Secondary");
 CHECK(coh_appearance_material_recipe(adjacent.primary,adjacent.secondary,&adjacent.output)==COH_OK);CHECK(!strcmp(adjacent.output.basic[0],adjacent.primary)&&!strcmp(adjacent.output.basic[1],adjacent.secondary));
 printf("{\"passed\":true,\"checks\":%u,\"source_cases\":%u,\"original_helper_bodies\":3,\"original_automatic_fallback_branch\":true,\"multitex_enabled\":false,\"bumpmaps_enabled\":false,\"renderer_or_asset_availability_claim\":false}\n",checks,cases);return 0;
}
