#include "coh_character_tail.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations,randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"tail check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {const uint8_t*data;size_t bytes,start,bits;unsigned mode,scenario;const CohCharacterTail*expected;}TailFixture;
#include "tail_fixtures.h"
#include "character_tail_test_writer.h"
static CohCharacterTail*out,*prior;static CohCharacterTailWorkspace*workspace;
static CohRepReader reader(const uint8_t*data,size_t bytes,size_t bits,unsigned mode,size_t start){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){data,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=start;return r;}
static CohStatus parse(CohRepReader*r){return coh_character_tail_read(r,out,workspace,COH_CHARACTER_TAIL_RAM_MAX,0);}
static void refuse(CohRepReader r,CohStatus expected){CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=parse(&r);CHECK(s!=COH_OK);if(expected!=COH_OK)CHECK(s==expected);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));}
int main(void){
 out=malloc(sizeof(*out));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));TailWriter*w=calloc(1,sizeof(*w));CHECK(out&&prior&&workspace&&w);
 for(size_t i=0;i<sizeof(tail_fixtures)/sizeof(tail_fixtures[0]);i++){
  const TailFixture*f=&tail_fixtures[i];CohRepReader r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CHECK(parse(&r)==COH_OK);CHECK(r.cursor==f->bits&&out->begin_bit==f->start&&out->end_bit==f->bits);
  /* Exact complete metadata/string-pool comparison against the independent
   * original producer/consumer projection, excluding cursor-only POD suffix. */
  if(memcmp(out,f->expected,offsetof(CohCharacterTail,begin_bit))){const uint8_t*a=(const uint8_t*)out,*b=(const uint8_t*)f->expected;for(size_t j=0;j<offsetof(CohCharacterTail,begin_bit);j++)if(a[j]!=b[j]){fprintf(stderr,"source projection mismatch scenario%u mode%u byte%zu native%u expected%u\n",f->scenario,f->mode,j,a[j],b[j]);break;}CHECK(0);}
  CHECK(out->rewards_end_bit>out->begin_bit&&out->chat_end_bit>out->rewards_end_bit&&out->keybinds_end_bit>out->chat_end_bit&&out->options_end_bit>out->keybinds_end_bit&&out->end_bit>out->options_end_bit);
  if(f->scenario==1&&f->start==0){
   size_t late=out->options_end_bit;for(size_t bit=0;bit<f->bits;bit+=(bit<late?113:1)){CohRepReader cut=reader(f->data,f->bytes,bit,f->mode,0);refuse(cut,COH_OK);truncations++;}
   size_t minimum=sizeof(*out)+sizeof(*workspace)+COH_CHARACTER_TAIL_STACK_RESERVE+f->bytes;r=reader(f->data,f->bytes,f->bits,f->mode,0);CHECK(coh_character_tail_read(&r,out,workspace,minimum,0)==COH_OK);*prior=*out;CohRepReader before=reader(f->data,f->bytes,f->bits,f->mode,0);r=before;CHECK(coh_character_tail_read(&r,out,workspace,minimum-1,0)==COH_LIMIT);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));CHECK(coh_character_tail_read(&r,out,workspace,minimum,1)==COH_LIMIT);CHECK(coh_character_tail_read(&r,out,(CohCharacterTailWorkspace*)out,COH_CHARACTER_TAIL_RAM_MAX,0)==COH_INVALID);
  }
  uint8_t*data=malloc(f->bytes+8);CHECK(data);memcpy(data,f->data,f->bytes);memset(data+f->bytes,0x7f,8);r=reader(data,f->bytes+8,(f->bytes+8)*8,f->mode,f->start);CHECK(parse(&r)==COH_OK&&r.cursor==f->bits);
  for(size_t j=0;j<f->bytes;j+=29){memcpy(data,f->data,f->bytes);data[j]^=255;r=reader(data,f->bytes,f->bits,f->mode,f->start);CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=parse(&r);if(s!=COH_OK)CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));else CHECK(r.cursor<=r.bits&&out->text_bytes<=COH_CHARACTER_TAIL_TEXT_MAX&&out->friend_count<=25);mutations++;}free(data);
 }
 for(unsigned mode=0;mode<2;mode++){
  memset(w,0,sizeof(*w));w->mode=mode;zero_tail(w);CohRepReader r=reader(w->bytes,(w->bits+7)/8,w->bits,mode,0);CHECK(parse(&r)==COH_OK&&r.cursor==w->bits);CHECK(!out->reward_count&&!out->active_reward_count&&!out->friend_count);CHECK(out->mouse_invert==1&&out->mouse_speed_word==0x3f800000&&out->turn_speed_word==0x40000000);
  /* Explicit deep corruptions of a complete local reference body. */
  size_t options_end=out->options_end_bit,keybinds_end=out->keybinds_end_bit,original_bits=w->bits;
  w->bits=options_end-64;put(w,32,0x7fc00000);w->bits=original_bits;r=reader(w->bytes,(w->bits+7)/8,w->bits,mode,0);refuse(r,COH_INVALID);
  memset(w,0,sizeof(*w));w->mode=mode;zero_tail(w);w->bits=options_end;for(unsigned j=0;j<8;j++)packed(w,9,0);put(w,1,0);put(w,2,0);packed(w,1,1);packed(w,1,26);r=reader(w->bytes,(w->bits+7)/8,w->bits,mode,0);refuse(r,COH_LIMIT);
  memset(w,0,sizeof(*w));w->mode=mode;zero_tail(w);w->bits=keybinds_end-256u*72u;for(unsigned j=0;j<256;j++)put(w,8,'x');put(w,8,0);r=reader(w->bytes,(w->bits+7)/8,w->bits,mode,0);refuse(r,COH_LIMIT);
  memset(w,0,sizeof(*w));w->mode=mode;automatic(w,257);r=reader(w->bytes,(w->bits+7)/8,w->bits,mode,0);refuse(r,COH_LIMIT);
  memset(w,0,sizeof(*w));w->mode=mode;automatic(w,1);for(unsigned j=0;j<1024;j++)put(w,8,'x');put(w,8,0);r=reader(w->bytes,(w->bits+7)/8,w->bits,mode,0);refuse(r,COH_LIMIT);
 }
 for(unsigned i=0;i<1000;i++){uint8_t data[256];for(unsigned j=0;j<sizeof(data);j++)data[j]=(uint8_t)(i*37+j*17);CohRepReader r=reader(data,sizeof(data),sizeof(data)*8,i%2,0);refuse(r,COH_OK);randomized++;}
 printf("{\"passed\":true,\"checks\":%llu,\"fixtures\":%zu,\"truncations\":%llu,\"mutations\":%llu,\"randomized\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"aggregate_limit\":%u,\"whole_initial_update_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,sizeof(tail_fixtures)/sizeof(tail_fixtures[0]),(unsigned long long)truncations,(unsigned long long)mutations,(unsigned long long)randomized,sizeof(*out),sizeof(*workspace),COH_CHARACTER_TAIL_RAM_MAX);
 free(out);free(prior);free(workspace);free(w);return 0;
}
