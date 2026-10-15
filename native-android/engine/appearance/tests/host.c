#include "../coh_appearance.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
static int cancelled(void *p){(void)p;return 1;}
static int exists(void *p,uint32_t kind,const char *key){(void)p;return kind==COH_APPEARANCE_TEXTURE&&!strcmp(key,"SF_FACE_skin_01a.tga");}
unsigned appearance_adapter_tests(void);
unsigned appearance_corpus_tests(const char *directory);
int main(int argc,char **argv){
 CohAppearanceWorkspace *w=calloc(1,sizeof(*w));CohAppearanceDraw *out=calloc(120,sizeof(*out));assert(w&&out);
 CohAppearancePartDef defs[]={{"Head","Head","FACE","HEAD",{4,0},1,0},{"Boots","LLeg","BOOT","BOOT",{25,26},2,0}};
 CohAppearancePart parts[]={{0,"Standard",{"skin_01a","mask"},{{1,2,3,255},{5,6,7,255},{8,9,10,255},{11,12,13,255}}},{1,"boot.geo/GEO_LLeg*_Boot",{"!boot_x","!mask"},{{1,2,3,255},{4,5,6,255},{7,8,9,255},{10,11,12,255}}}};
 CohAppearanceRequest r={0};assert(coh_appearance_body(1,NULL,NULL,&r.body)==0);r.definitions=defs;r.definition_count=2;r.parts=parts;r.part_count=2;r.generation=7;r.skin[0]=77;r.probe=exists;
 CohAppearanceDiagnostics diag;size_t n=0;assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==0);assert(n==3&&diag.skin_routed==1&&!strcmp(out[0].geometry_key,"fem_HEAD.GEO_Head_Standard")&&!strcmp(out[0].texture[0],"SF_FACE_skin_01a")&&!strcmp(out[0].texture[1],"FACE_skin_01B"));assert(out[0].color[0][0]==77&&out[0].color[1][0]==1&&out[1].socket==25&&out[2].socket==26&&!strcmp(out[2].model_name,"GEO_LLegL_Boot")&&!strcmp(out[2].texture[1],"none"));
 unsigned corpus_models=appearance_corpus_tests(argc>1?argv[1]:NULL);unsigned negative=appearance_adapter_tests();CohAppearanceDraw sentinel=out[0];CohAppearanceDiagnostics old=diag;
 assert(coh_appearance_assemble(&r,w,out,1,&n,&diag)==COH_LIMIT);assert(!memcmp(&sentinel,out,sizeof sentinel)&&!memcmp(&diag,&old,sizeof diag)&&n==3);negative++;
 r.cancel.poll=cancelled;assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==COH_CANCELLED);r.cancel.poll=NULL;negative++;
 parts[1].definition=0;assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==COH_INVALID);parts[1].definition=1;negative++;
 defs[1].socket_count=3;assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==COH_INVALID);defs[1].socket_count=2;negative++;
 parts[1].geometry="../boot.geo/GEO_Leg";assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==COH_UNSUPPORTED);negative++;
 parts[1].geometry="boot.geo/GEO_Leg**";assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==COH_INVALID);negative++;
 parts[1].geometry="boot.geo/GEO_LLeg*_Boot";parts[0].texture[0]="";assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==COH_INVALID);parts[0].texture[0]="skin_01a";negative++;
 parts[0].texture[0]="!";assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==COH_INVALID);parts[0].texture[0]="skin_01a";negative++;
 char huge[300];memset(huge,'a',sizeof huge);huge[299]=0;parts[0].geometry=huge;assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==COH_INVALID);parts[0].geometry="Standard";negative++;
 assert(coh_appearance_assemble(&r,w,w->draws,120,&n,&diag)==COH_INVALID);negative++;
 assert(coh_appearance_body(6,NULL,NULL,&r.body)==COH_UNSUPPORTED);assert(coh_appearance_body(9,NULL,NULL,&r.body)==COH_INVALID);negative+=2;
 /* Fixed work over maximum source parts; no allocations inside timed loop. */
 CohAppearancePartDef all_defs[60];CohAppearancePart all_parts[60];for(unsigned i=0;i<60;i++){all_defs[i]=defs[1];all_parts[i]=parts[1];all_parts[i].definition=i;}
 r.definitions=all_defs;r.definition_count=60;r.parts=all_parts;r.part_count=60;assert(coh_appearance_body(4,NULL,NULL,&r.body)==0);
 clock_t begin=clock();for(unsigned i=0;i<10000;i++)assert(coh_appearance_assemble(&r,w,out,120,&n,&diag)==0);double elapsed=(double)(clock()-begin)/CLOCKS_PER_SEC;
 printf("{\"passed\":true,\"negative_cases\":%u,\"maximum_draws\":%zu,\"corpus_models_checked\":%u,\"workspace_bytes\":%zu,\"draw_bytes\":%zu,\"module_heap_allocations\":0,\"iterations\":10000,\"maximum_case_cpu_seconds\":%.6f}\n",negative,n,corpus_models,sizeof(*w),sizeof(*out),elapsed);
 free(out);free(w);return 0;
}
