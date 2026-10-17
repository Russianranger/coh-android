#include "coh_character_outer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"outer check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {const uint8_t*data;size_t bytes,bits,prefix_end,character_end,stats_begin,names_end,start;unsigned mode,scenario;uint32_t words[15];uint8_t auth[128];float stats[16];int32_t integers[6];}InitialFixture;
#include "initial_fixtures.h"
typedef struct {const uint8_t*data;size_t bytes,start,bits;unsigned mode,scenario;uint32_t observed[9];}UiFixture;
#include "ui_fixtures.h"
typedef struct {const uint8_t*data;size_t bytes,start,bits;unsigned mode,scenario;const CohCharacterTail*expected;}TailFixture;
#include "tail_fixtures.h"
static CohCharacterOuter*out,*prior;static CohCharacterOuterWorkspace*workspace;
static CohCharacterInitialPrefix*initial;static CohCharacterInitialWorkspace*initial_workspace;
static CohCharacterUi*ui;static CohCharacterUiWorkspace*ui_workspace;static CohCharacterTail*tail;static CohCharacterTailWorkspace*tail_workspace;
static CohCharacterWireProfile profile(unsigned scenario){CohCharacterWireProfile p={0};unsigned b=scenario<6?scenario:1;p.generation=7;p.shared_set_count_bound=1;p.player=b?1:0;p.shared_set_count=b==5?3:(b==2?0:(b==3?2:1));memset(p.source_profile_sha256,0x11,32);return p;}
static void bitcopy(uint8_t*d,size_t offset,const uint8_t*s,size_t begin,size_t end){for(size_t b=begin;b<end;b++){uint8_t m=(uint8_t)(1u<<((offset+b-begin)%8));if(s[b/8]&(1u<<(b%8)))d[(offset+b-begin)/8]|=m;else d[(offset+b-begin)/8]&=(uint8_t)~m;}}
static CohRepReader reader(const uint8_t*data,size_t bytes,size_t bits,unsigned mode,size_t begin){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){data,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=begin;return r;}
static CohStatus parse(CohRepReader*r,const CohCharacterWireProfile*p){return coh_character_outer_read(r,p,10,out,workspace,COH_CHARACTER_OUTER_RAM_MAX,0);}
static void reject(CohRepReader r,const CohCharacterWireProfile*p){CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CHECK(parse(&r,p)!=COH_OK);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));}
int main(void){
 out=malloc(sizeof(*out));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));initial=malloc(sizeof(*initial));initial_workspace=malloc(sizeof(*initial_workspace));ui=malloc(sizeof(*ui));ui_workspace=malloc(sizeof(*ui_workspace));tail=malloc(sizeof(*tail));tail_workspace=malloc(sizeof(*tail_workspace));CHECK(out&&prior&&workspace&&initial&&initial_workspace&&ui&&ui_workspace&&tail&&tail_workspace);size_t cases=0;
 for(size_t i=0;i<sizeof(initial_fixtures)/sizeof(initial_fixtures[0]);i++){
  const InitialFixture*f=&initial_fixtures[i];if(f->scenario==5||f->scenario==7)continue;
  const UiFixture*u=NULL;for(size_t j=0;j<sizeof(ui_fixtures)/sizeof(ui_fixtures[0]);j++)if(ui_fixtures[j].mode==f->mode&&ui_fixtures[j].start==f->bits%8&&ui_fixtures[j].scenario==f->scenario%6){u=&ui_fixtures[j];break;}CHECK(u);
  size_t creation_end=f->bits+u->bits-u->start;const TailFixture*t=NULL;for(size_t j=0;j<sizeof(tail_fixtures)/sizeof(tail_fixtures[0]);j++)if(tail_fixtures[j].mode==f->mode&&tail_fixtures[j].start==creation_end%8&&tail_fixtures[j].scenario==f->scenario%10){t=&tail_fixtures[j];break;}CHECK(t);size_t bits=creation_end+t->bits-t->start,bytes=(bits+7)/8;uint8_t*data=calloc(bytes+8,1);CHECK(data);bitcopy(data,0,f->data,0,f->bits);bitcopy(data,f->bits,u->data,u->start,u->bits);bitcopy(data,creation_end,t->data,t->start,t->bits);CohCharacterWireProfile p=profile(f->scenario);CohRepReader r=reader(data,bytes,bits,f->mode,f->start);
  CHECK(parse(&r,&p)==COH_OK);CHECK(r.cursor==bits&&out->begin_bit==f->start&&out->creation_end_bit==creation_end&&out->end_bit==bits);CHECK(out->creation.initial_end_bit==f->bits&&out->creation.ui.begin_bit==f->bits&&out->creation.ui.end_bit==creation_end&&out->tail.begin_bit==creation_end&&out->tail.end_bit==bits);
  r=reader(data,bytes,bits,f->mode,f->start);CHECK(coh_character_initial_read(&r,&p,10,initial_workspace,initial,COH_CHARACTER_INITIAL_RAM_MAX,0,NULL)==COH_OK);CHECK(r.cursor==f->bits);CHECK(!memcmp(initial,&out->creation.initial,sizeof(*initial)));CHECK(coh_character_ui_read(&r,ui,ui_workspace,COH_CHARACTER_UI_RAM_MAX,0)==COH_OK);CHECK(!memcmp(ui,&out->creation.ui,sizeof(*ui)));CHECK(coh_character_tail_read(&r,tail,tail_workspace,COH_CHARACTER_TAIL_RAM_MAX,0)==COH_OK);CHECK(!memcmp(tail,&out->tail,sizeof(*tail)));CHECK(!memcmp(&out->tail,t->expected,offsetof(CohCharacterTail,begin_bit)));
  if(f->scenario==0&&f->start==0){
   for(size_t bit=0;bit<bits;bit+=(bit+512<bits?193:1)){r=reader(data,bytes,bit,f->mode,f->start);reject(r,&p);truncations++;}
   for(size_t bit=creation_end-64;bit<creation_end+64;bit++){r=reader(data,bytes,bit,f->mode,f->start);reject(r,&p);truncations++;}
   size_t minimum=sizeof(*out)+sizeof(*workspace)+COH_CHARACTER_OUTER_STACK_RESERVE+bytes;r=reader(data,bytes,bits,f->mode,f->start);CHECK(coh_character_outer_read(&r,&p,10,out,workspace,minimum,0)==COH_OK);CohRepReader before=reader(data,bytes,bits,f->mode,f->start);r=before;*prior=*out;CHECK(coh_character_outer_read(&r,&p,10,out,workspace,minimum-1,0)==COH_LIMIT);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));CHECK(coh_character_outer_read(&r,&p,10,out,workspace,minimum,1)==COH_LIMIT);CHECK(coh_character_outer_read(&r,&p,10,out,(CohCharacterOuterWorkspace*)out,COH_CHARACTER_OUTER_RAM_MAX,0)==COH_INVALID);
  }
  memset(data+bytes,0x7f,8);r=reader(data,bytes+8,(bytes+8)*8,f->mode,f->start);CHECK(parse(&r,&p)==COH_OK&&r.cursor==bits);
  for(size_t byte=0;byte<bytes;byte+=257){data[byte]^=255;r=reader(data,bytes,bits,f->mode,f->start);CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=parse(&r,&p);if(s!=COH_OK)CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));else CHECK(r.cursor<=r.bits);data[byte]^=255;mutations++;}
  free(data);cases++;
 }
 printf("{\"passed\":true,\"checks\":%llu,\"source_component_compositions\":%zu,\"truncations\":%llu,\"mutations\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"aggregate_limit\":%u,\"whole_initial_update_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,cases,(unsigned long long)truncations,(unsigned long long)mutations,sizeof(*out),sizeof(*workspace),COH_CHARACTER_OUTER_RAM_MAX);
 free(out);free(prior);free(workspace);free(initial);free(initial_workspace);free(ui);free(ui_workspace);free(tail);free(tail_workspace);return 0;
}
