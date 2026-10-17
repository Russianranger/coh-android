#include "coh_view.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"view check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t bytes,start,sky_end,bits;unsigned mode,scenario,variant;CohWorldView expected;}Fixture;
#include "fixtures.h"
static CohWorldView out,prior;static CohWorldViewWorkspace workspace;
static CohRepReader reader(const uint8_t*d,size_t bytes,size_t bits,unsigned mode,size_t begin){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){d,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=begin;return r;}
static void refusal(CohRepReader r){CohRepReader before=r;memset(&out,0xa5,sizeof(out));prior=out;CHECK(coh_world_view_read(&r,&out,&workspace,COH_VIEW_RAM_MAX,0)!=COH_OK);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(&out,&prior,sizeof(out)));}
int main(void){
 for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
  const Fixture*f=&fixtures[i];CohRepReader r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CHECK(coh_world_view_read(&r,&out,&workspace,COH_VIEW_RAM_MAX,0)==COH_OK);CHECK(r.cursor==f->bits&&out.begin_bit==f->start&&out.sky_end_bit==f->sky_end&&out.end_bit==f->bits);CHECK(!memcmp(&out,&f->expected,offsetof(CohWorldView,begin_bit)));
  for(size_t bit=f->start;bit<f->bits;bit++){CohRepReader cut=reader(f->data,f->bytes,bit,f->mode,f->start);refusal(cut);truncations++;}
  size_t minimum=sizeof(out)+sizeof(workspace)+COH_VIEW_STACK_RESERVE+f->bytes;r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CHECK(coh_world_view_read(&r,&out,&workspace,minimum,0)==COH_OK);r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CohRepReader before=r;prior=out;CHECK(coh_world_view_read(&r,&out,&workspace,minimum-1,0)==COH_LIMIT);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(&out,&prior,sizeof(out)));CHECK(coh_world_view_read(&r,&out,(CohWorldViewWorkspace*)&out,COH_VIEW_RAM_MAX,0)==COH_INVALID);CHECK(coh_world_view_read(&r,&out,&workspace,minimum,1)==COH_LIMIT);
  uint8_t*d=malloc(f->bytes+8);CHECK(d);memcpy(d,f->data,f->bytes);memset(d+f->bytes,0xa5,8);r=reader(d,f->bytes+8,(f->bytes+8)*8,f->mode,f->start);CHECK(coh_world_view_read(&r,&out,&workspace,COH_VIEW_RAM_MAX,0)==COH_OK&&r.cursor==f->bits);
  for(size_t j=0;j<f->bytes;j++){for(unsigned bit=0;bit<8;bit++){memcpy(d,f->data,f->bytes);d[j]^=(uint8_t)(1u<<bit);r=reader(d,f->bytes,f->bits,f->mode,f->start);CohRepReader before=r;memset(&out,0xa5,sizeof(out));prior=out;CohStatus s=coh_world_view_read(&r,&out,&workspace,COH_VIEW_RAM_MAX,0);if(s!=COH_OK)CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(&out,&prior,sizeof(out)));else CHECK(r.cursor<=r.bits);mutations++;}}free(d);
 }
 {uint8_t d[18]={1,0,0,128,127,0,0,0,0,0,0,0,0,0,0,0,0,0};CohRepReader r=reader(d,sizeof(d),sizeof(d)*8,1,0);refusal(r);d[0]=0;d[1]=1;d[2]=0;d[3]=0;d[4]=128;d[5]=127;r=reader(d,sizeof(d),sizeof(d)*8,1,0);refusal(r);}
 printf("{\"passed\":true,\"checks\":%llu,\"composed_source_fragments\":%zu,\"truncations\":%llu,\"mutations\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"whole_initial_update_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,sizeof(fixtures)/sizeof(fixtures[0]),(unsigned long long)truncations,(unsigned long long)mutations,sizeof(out),sizeof(workspace));return 0;
}
