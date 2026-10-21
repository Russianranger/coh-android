#include "coh_appearance_scales.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static CohOriginalCostumeSnapshot snapshot;
static CohAppearanceHugeScales scales;
static CohCharacterMorph morph,old;
static uint8_t bytes[COH_APPEARANCE_HUGE_MORPH_BYTES];
static CohAppearanceHugeScaleDiagnostics diagnostics,old_diagnostics;
void source_scale_header(const float input[30],float output[53]);
static float read_float(const uint8_t*p){uint32_t bits=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;float f;memcpy(&f,&bits,4);return f;}
int main(void){
 unsigned tests=0;memset(&snapshot,0,sizeof snapshot);memset(&scales,0,sizeof scales);snapshot.bodytype=4;snapshot.converted_scale=1;
 for(unsigned i=0;i<99;i++)for(unsigned j=0;j<3;j++)scales.fat[i][j]=scales.skinny[i][j]=1.f;
 scales.fat[0][0]=2.f;scales.skinny[0][0]=.75f;scales.fat_models=scales.skinny_models=1;
 for(unsigned test=0;test<73;test++){
  for(unsigned i=0;i<30;i++)snapshot.scales[i]=((float)((test*37+i*23)%181)-90.f)/100.f;
  snapshot.scales[0]=(float)((int)test-36)*.25f;snapshot.scales[7]*=.1f;snapshot.scales[8]*=.1f;
  assert(coh_appearance_huge_morph(&snapshot,&scales,bytes,&morph,&diagnostics)==COH_OK);
  float expected[53];source_scale_header(snapshot.scales,expected);
  for(unsigned i=0;i<53;i++){assert(read_float(bytes+40+i*4)==expected[i]);tests++;}
  assert(morph.body_type==4&&morph.bytes==bytes&&morph.geom_scale[0]==snapshot.scales[0]/100.f+1.f);tests++;
  float ratio=snapshot.scales[1],model=ratio<0.f?.75f:2.f;
  assert(morph.bone_scales[0][0]==1.f+(model-1.f)*fabsf(ratio));tests++;
 }
 snapshot.scales[0]=4.97f;snapshot.scales[1]=-.025f;snapshot.scales[2]=-.4305f;snapshot.scales[3]=.1525f;snapshot.scales[4]=.290375f;snapshot.scales[5]=-.09825f;snapshot.scales[6]=.4865f;
 for(unsigned i=7;i<30;i++)snapshot.scales[i]=0.f;
 assert(coh_appearance_huge_morph(&snapshot,&scales,bytes,&morph,&diagnostics)==COH_OK);
 assert(morph.geom_scale[0]==1.0497f&&morph.shoulder_skinny[0]==-.19f&&morph.shoulder_fat[0]==.14f&&morph.leg_scale_ratio==.70f&&morph.head_scales[0]==0.f);tests++;
 uint8_t saved[COH_APPEARANCE_HUGE_MORPH_BYTES];memcpy(saved,bytes,sizeof bytes);snapshot.converted_scale=0;
 assert(coh_appearance_huge_morph(&snapshot,&scales,bytes,&morph,&diagnostics)==COH_OK&&!memcmp(saved,bytes,sizeof bytes));tests++;
 old=morph;old_diagnostics=diagnostics;
 #define BAD(expected) do{assert(coh_appearance_huge_morph(&snapshot,&scales,bytes,&morph,&diagnostics)==expected);assert(!memcmp(&morph,&old,sizeof morph)&&!memcmp(&diagnostics,&old_diagnostics,sizeof diagnostics));tests++;}while(0)
 snapshot.bodytype=0;BAD(COH_INVALID);snapshot.bodytype=4;
 snapshot.scales[4]=NAN;BAD(COH_INVALID);snapshot.scales[4]=.290375f;
 scales.fat[0][0]=0;BAD(COH_INVALID);scales.fat[0][0]=2;
 scales.fat_models=100;BAD(COH_INVALID);scales.fat_models=1;
 assert(coh_appearance_huge_morph(&snapshot,&scales,(uint8_t*)&snapshot,&morph,&diagnostics)==COH_INVALID);tests++;
 assert(coh_appearance_huge_morph(&snapshot,&scales,bytes,(CohCharacterMorph*)bytes,&diagnostics)==COH_INVALID);tests++;
 printf("{\"passed\":true,\"checks\":%u,\"source_huge_parameters\":true,\"source_appearance_union\":true,\"wretch_substitution\":false}\n",tests);
 return 0;
}
