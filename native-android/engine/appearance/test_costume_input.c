#include "coh_appearance_costume.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "costume-definitions.h"
static unsigned checks;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"line%d %s\n",__LINE__,#v);exit(1);}}while(0)
static CohOriginalCostumeWorkspace receiver;
static CohOriginalCostumeSnapshot snapshot;
static CohAppearanceCostumeWorkspace workspace;
static CohAppearanceDraw draws[120],previous[120],expected[120];
static uint32_t word(FILE *f){uint8_t b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static int probe(void *context,uint32_t kind,const char *key){
 unsigned inventory=*(unsigned*)context;(void)kind;
 if(inventory==1)return !strcmp(key,"SF_FACE_none.tga")||!strcmp(key,"SH_HIPS_none.tga")||!strcmp(key,"SM_CHEST_skin_01a.tga");
 if(inventory==2)return !strcmp(key,"huge_BACK.GEO_BACK_Armored_Tight")||!strcmp(key,"V_Wretch_FACE_skin_01a.tga");
 return 0;
}
static int cancelled(void *unused){(void)unused;return 1;}
static void borrows_cleared(void){const CohAppearanceRequest zero_request={0};const CohAppearancePart zero_parts[30]={{0}};CHECK(!memcmp(&workspace.request,&zero_request,sizeof(zero_request)));CHECK(!memcmp(workspace.parts,zero_parts,sizeof(zero_parts)));}
static void failures(CohAppearanceCostumeInputs *inputs){
 CohAppearanceCostumeDiagnostics diag,old;size_t count=77;memset(&diag,0xa5,sizeof(diag));old=diag;memcpy(previous,draws,sizeof(draws));
 CHECK(coh_appearance_costume_assemble(&snapshot,inputs,&workspace,draws,SIZE_MAX,&count,&diag)==COH_LIMIT);
 CHECK(coh_appearance_costume_assemble(&snapshot,inputs,&workspace,(CohAppearanceDraw*)(void*)&workspace,120,&count,&diag)==COH_INVALID);
 CHECK(coh_appearance_costume_assemble(&snapshot,inputs,&workspace,draws,120,&count,(CohAppearanceCostumeDiagnostics*)(void*)&snapshot)==COH_INVALID);
 CHECK(coh_appearance_costume_assemble(&snapshot,inputs,(CohAppearanceCostumeWorkspace*)(void*)&snapshot,draws,120,&count,&diag)==COH_INVALID);
 CHECK(coh_appearance_costume_assemble((CohOriginalCostumeSnapshot*)(uintptr_t)(UINTPTR_MAX-3),inputs,&workspace,draws,120,&count,&diag)==COH_INVALID);
 inputs->cancel.poll=cancelled;CHECK(coh_appearance_costume_assemble(&snapshot,inputs,&workspace,draws,120,&count,&diag)==COH_CANCELLED);borrows_cleared();inputs->cancel.poll=NULL;
 CHECK(coh_appearance_costume_assemble(&snapshot,inputs,&workspace,draws,0,&count,&diag)==COH_LIMIT);borrows_cleared();
 uint32_t saved=snapshot.bodytype;snapshot.bodytype=9;CHECK(coh_appearance_costume_assemble(&snapshot,inputs,&workspace,draws,120,&count,&diag)==COH_INVALID);snapshot.bodytype=saved;
 saved=snapshot.part_count;snapshot.part_count=31;CHECK(coh_appearance_costume_assemble(&snapshot,inputs,&workspace,draws,120,&count,&diag)==COH_INVALID);snapshot.part_count=saved;
 saved=snapshot.parts[0].present_mask;snapshot.parts[0].present_mask=64;CHECK(coh_appearance_costume_assemble(&snapshot,inputs,&workspace,draws,120,&count,&diag)==COH_INVALID);snapshot.parts[0].present_mask=saved;
 CHECK(count==77&&!memcmp(&diag,&old,sizeof(diag))&&!memcmp(draws,previous,sizeof(draws)));
}
static void bodytypes(void){
 CohAppearanceCostumeInputs inputs={definitions,28,19,NULL,0,NULL,NULL,{NULL,NULL}};CohAppearanceCostumeDiagnostics diag;size_t count;
 memset(&snapshot,0,sizeof(snapshot));
 for(unsigned type=0;type<9;type++){
  snapshot.bodytype=type;
  CHECK(coh_appearance_costume_assemble(&snapshot,&inputs,&workspace,draws,120,&count,&diag)==(type==6?COH_UNSUPPORTED:COH_OK));
  if(type!=6){CHECK(diag.body.body_type==type&&!strcmp(diag.body.ent_type,source_ent[type])&&!strcmp(diag.body.geometry_prefix,source_ent[type])&&!strcmp(diag.body.texture_prefix,source_texture_prefix[type])&&count==0);borrows_cleared();}
 }
 snapshot.bodytype=6;snapshot.header_present=3;strcpy(snapshot.ent_type,"ActualSourceEntity");strcpy(snapshot.geometry_prefix,"ActualSourcePrefix");
 CHECK(coh_appearance_costume_assemble(&snapshot,&inputs,&workspace,draws,120,&count,&diag)==COH_OK);
 CHECK(diag.body.body_type==6&&!strcmp(diag.body.ent_type,"ActualSourceEntity")&&!strcmp(diag.body.geometry_prefix,"ActualSourcePrefix")&&!strcmp(diag.body.texture_prefix,"ActualSourcePrefix")&&count==0);borrows_cleared();
}
int main(int argc,char **argv){
 CHECK(argc==2);FILE *f=fopen(argv[1],"rb");CHECK(f);unsigned rows=word(f);static const char *links[]={"Armored","Jacket"};
 for(unsigned row=0;row<rows;row++){
  uint8_t bytes[16384];unsigned mode=word(f),begin=word(f),bits=word(f),inventory=word(f),expected_count=word(f);CHECK((bits+7)/8<=sizeof(bytes)&&expected_count<=120);
  CHECK(fread(bytes,1,(bits+7)/8,f)==(bits+7)/8);CohAppearanceBody body;CHECK(fread(&body,1,sizeof(body),f)==sizeof(body));CHECK(fread(expected,sizeof(*expected),expected_count,f)==expected_count);
  CohRepReader reader={{bytes,(bits+7)/8},bits,begin,mode,COH_REP_BOUNDED_MESSAGE_MAX};CohOriginalCostumeReport received;
  CHECK(coh_original_costume_receive_slots_capture(&reader,28,NULL,&receiver,&received,&snapshot)==COH_OK&&received.costume_complete&&received.end_bit==bits);
  CohAppearanceCostumeInputs inputs={definitions,28,19,links,2,probe,&inventory,{NULL,NULL}};CohAppearanceCostumeDiagnostics diag;size_t count=0;
  CHECK(coh_appearance_costume_assemble(&snapshot,&inputs,&workspace,draws,120,&count,&diag)==COH_OK);
  if(count!=expected_count)fprintf(stderr,"row%u count%zu expected%u\n",row,count,expected_count);
  for(size_t i=0;i<count&&i<expected_count;i++)if(memcmp(draws+i,expected+i,sizeof(*draws))){fprintf(stderr,"row%u draw%zu actual=[%s][%s][%s] expected=[%s][%s][%s] flags%u/%u\n",row,i,draws[i].geometry_key,draws[i].texture[0],draws[i].texture[1],expected[i].geometry_key,expected[i].texture[0],expected[i].texture[1],draws[i].flags,expected[i].flags);for(size_t b=0;b<sizeof(*draws);b++)if(((const unsigned char*)(draws+i))[b]!=((const unsigned char*)(expected+i))[b]){fprintf(stderr,"first differing byte%zu values%u/%u\n",b,((const unsigned char*)(draws+i))[b],((const unsigned char*)(expected+i))[b]);break;}break;}
  CHECK(count==expected_count&&!memcmp(draws,expected,count*sizeof(*draws))&&!memcmp(&diag.body,&body,sizeof(body)));
  CHECK(diag.body.body_type==snapshot.bodytype&&diag.workspace_bytes==sizeof(workspace));borrows_cleared();failures(&inputs);
 }
 CHECK(fgetc(f)==EOF&&fclose(f)==0);bodytypes();
 printf("{\"passed\":true,\"checks\":%u,\"whole_original_sender_cases\":%u,\"bodyparts\":28,\"body_type_descriptors\":9,\"workspace_bytes\":%zu,\"snapshot_bytes\":%zu,\"heap_allocations\":0,\"live_actor_substitution\":false}\n",checks,rows,sizeof(workspace),sizeof(snapshot));return 0;
}
