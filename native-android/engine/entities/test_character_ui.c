#include "coh_character_ui.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations,randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"ui check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {const uint8_t *data;size_t bytes,start,bits;unsigned mode,scenario;uint32_t observed[9];}UiFixture;
#include "ui_fixtures.h"
static CohCharacterUi *out,*prior;static CohCharacterUiWorkspace *workspace;
static uint32_t fnv(uint32_t h,const void*p,size_t n){const uint8_t*b=p;for(size_t i=0;i<n;i++){h^=b[i];h*=16777619u;}return h;}
static uint32_t word(uint32_t h,uint32_t x){uint8_t b[4]={(uint8_t)x,(uint8_t)(x>>8),(uint8_t)(x>>16),(uint8_t)(x>>24)};return fnv(h,b,4);}
static const char*str(CohCharacterUiString s){CHECK(s.offset<out->text_bytes&&s.bytes<out->text_bytes-s.offset);CHECK(out->text[s.offset+s.bytes]==0);return out->text+s.offset;}
static CohRepReader reader(const UiFixture*f){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->data,f->bytes},f->bits,(int)f->mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=f->start;return r;}
static CohStatus parse(CohRepReader*r){return coh_character_ui_read(r,out,workspace,COH_CHARACTER_UI_RAM_MAX,0);}
static void refusal(CohRepReader r){CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CHECK(parse(&r)!=COH_OK);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));}
int main(void){
 out=malloc(sizeof(*out));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));CHECK(out&&prior&&workspace);
 for(size_t i=0;i<sizeof(ui_fixtures)/sizeof(ui_fixtures[0]);i++){
  const UiFixture*f=&ui_fixtures[i];CohRepReader r=reader(f);CHECK(parse(&r)==COH_OK);CHECK(r.cursor==f->bits&&out->begin_bit==f->start&&out->end_bit==f->bits);
  for(unsigned j=0;j<4;j++)CHECK(out->current_trays[j]==(f->scenario+j)%9);
  CHECK(out->tray_indexes==f->observed[1]&&out->default_present==f->observed[2]);CHECK((out->tray_mode|(out->tray_mode_alt2<<1))==f->observed[0]);CHECK(!strcmp(out->name,"Oracle character")&&!strcmp(out->motto,"<motto>")&&!strcmp(out->description,"A <description>"));
  uint32_t h=2166136261u;
  for(unsigned j=0;j<720;j++){
   const CohCharacterTraySlot*s=&out->slots[j];unsigned kind=(f->scenario+j)%6;uint32_t type=kind==0?0:kind==1?1:kind==2?2:kind==3?6:kind==4?17:3;CHECK(s->type==type);
   if(type==1||type==2)CHECK(!s->set&&!s->power);
   if(type==6||type==17){CHECK(!strcmp(str(s->command),"say <hello> -- oracle"));CHECK(!strcmp(str(s->short_name),"macro"));CHECK(!strcmp(str(s->icon_name),"icon_oracle"));}
   /* Explicit fixture-only consumer projection; source creates an empty slot
    * for unsupported body-item types, not a native gameplay conversion. */
   h=word(h,type==3?0:type);if(type==1||type==2){h=word(h,s->set);h=word(h,s->power);}else if(type==6||type==17){h=fnv(h,str(s->command),s->command.bytes);h=fnv(h,str(s->short_name),s->short_name.bytes);h=fnv(h,str(s->icon_name),s->icon_name.bytes);}
  }
  CHECK(h==f->observed[3]);CHECK(fnv(2166136261u,out->name,strlen(out->name))==f->observed[4]);CHECK(fnv(2166136261u,out->motto,strlen(out->motto))==f->observed[5]);const char*source_description="A [description]";CHECK(fnv(2166136261u,source_description,strlen(source_description))==f->observed[6]);
  h=2166136261u;for(unsigned j=0;j<128;j++){CHECK(out->help_status[j]==(0xa5a5a5a5u^(f->scenario+j)));h=word(h,out->help_status[j]);}CHECK(h==f->observed[7]);h=2166136261u;for(unsigned j=0;j<5;j++){CHECK(out->help_latest[j]==f->scenario*1024+j);h=word(h,out->help_latest[j]);}CHECK(h==f->observed[8]);
  for(unsigned j=0;j<128;j++){
   const CohCharacterWindow*w=&out->windows[j];CHECK(w->index==j&&w->x==j*100&&w->y==j*50&&w->mode==(j%3==2?4:j%5));CHECK(w->color==0xff000000u+j&&!w->back_color&&!w->locked&&!w->maximized);CHECK(w->dimensions_present==((j%2||j==4)?1u:0u));if(w->dimensions_present)CHECK(w->width==200+j&&w->height==300+j);CHECK(w->scale_present==(j%3?1u:0u));if(w->scale_present)CHECK(w->scale_word==0x3fc00000u);
  }
  if(f->scenario==0&&f->start==0){
   /* Sample the full prefix/body and exhaust the final 512 bits: all late
    * window refusals roll back every prior tray/text/help event atomically. */
   for(size_t bit=0;bit<f->bits;bit+=(bit+512<f->bits?97:1)){CohRepReader cut=reader(f);cut.bits=bit;refusal(cut);truncations++;}
   size_t minimum=sizeof(*out)+sizeof(*workspace)+COH_CHARACTER_UI_STACK_RESERVE+f->bytes;r=reader(f);CHECK(coh_character_ui_read(&r,out,workspace,minimum,0)==COH_OK);*prior=*out;CohRepReader before=reader(f);r=before;CHECK(coh_character_ui_read(&r,out,workspace,minimum-1,0)==COH_LIMIT);CHECK(!memcmp(out,prior,sizeof(*out))&&!memcmp(&r,&before,sizeof(r)));CHECK(coh_character_ui_read(&r,out,workspace,minimum,1)==COH_LIMIT);CHECK(coh_character_ui_read(&r,out,(CohCharacterUiWorkspace*)out,COH_CHARACTER_UI_RAM_MAX,0)==COH_INVALID);
  }
  uint8_t*bytes=malloc(f->bytes+8);CHECK(bytes);memcpy(bytes,f->data,f->bytes);memset(bytes+f->bytes,0xa5,8);r=reader(f);r.bytes=(CohBytes){bytes,f->bytes+8};r.bits=(f->bytes+8)*8;CHECK(parse(&r)==COH_OK&&r.cursor==f->bits);
  for(size_t j=0;j<f->bytes;j+=37){memcpy(bytes,f->data,f->bytes);bytes[j]^=255;r=reader(f);r.bytes.data=bytes;CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=parse(&r);if(s!=COH_OK)CHECK(!memcmp(out,prior,sizeof(*out))&&!memcmp(&r,&before,sizeof(r)));else CHECK(r.cursor<=r.bits&&out->text_bytes<=COH_CHARACTER_UI_TEXT_MAX);mutations++;}free(bytes);
 }
 for(unsigned i=0;i<1000;i++){uint8_t bytes[128];for(unsigned j=0;j<sizeof(bytes);j++)bytes[j]=(uint8_t)(i*17+j*31);CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},sizeof(bytes)*8,i%2)==COH_OK);refusal(r);randomized++;}
 printf("{\"passed\":true,\"checks\":%llu,\"fixtures\":%zu,\"truncations\":%llu,\"mutations\":%llu,\"randomized\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"aggregate_limit\":%u,\"whole_character_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,sizeof(ui_fixtures)/sizeof(ui_fixtures[0]),(unsigned long long)truncations,(unsigned long long)mutations,(unsigned long long)randomized,sizeof(*out),sizeof(*workspace),COH_CHARACTER_UI_RAM_MAX);
 free(out);free(prior);free(workspace);return 0;
}
