#include "coh_superstats.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations,randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"superstats check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t bytes,start,bits;unsigned mode,scenario;const CohSuperStats*expected;}Fixture;
#include "fixtures.h"
static CohSuperStats*out,*prior;static CohSuperStatsWorkspace*workspace;
static CohRepReader reader(const uint8_t*d,size_t bytes,size_t bits,unsigned mode,size_t begin){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){d,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=begin;return r;}
static void refused(CohRepReader r,CohStatus expected){CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=coh_superstats_read(&r,out,workspace,COH_SG_RAM_MAX,0);CHECK(s!=COH_OK);if(expected!=COH_OK)CHECK(s==expected);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));}
int main(void){out=malloc(sizeof(*out));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));CHECK(out&&prior&&workspace);
 for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
  const Fixture*f=&fixtures[i];CohRepReader r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CHECK(coh_superstats_read(&r,out,workspace,COH_SG_RAM_MAX,0)==COH_OK);CHECK(r.cursor==f->bits&&out->begin_bit==f->start&&out->end_bit==f->bits);CHECK(!memcmp(out,f->expected,offsetof(CohSuperStats,begin_bit)));
  if(f->scenario==5&&f->start==0){for(size_t bit=0;bit<f->bits;bit+=13){CohRepReader cut=reader(f->data,f->bytes,bit,f->mode,0);refused(cut,COH_OK);truncations++;}size_t minimum=sizeof(*out)+sizeof(*workspace)+COH_SG_STACK_RESERVE+f->bytes;r=reader(f->data,f->bytes,f->bits,f->mode,0);CHECK(coh_superstats_read(&r,out,workspace,minimum,0)==COH_OK);r=reader(f->data,f->bytes,f->bits,f->mode,0);CohRepReader before=r;*prior=*out;CHECK(coh_superstats_read(&r,out,workspace,minimum-1,0)==COH_LIMIT);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));CHECK(coh_superstats_read(&r,out,(CohSuperStatsWorkspace*)out,COH_SG_RAM_MAX,0)==COH_INVALID);CHECK(coh_superstats_read(&r,out,workspace,minimum,1)==COH_LIMIT);}
  if(f->bits>f->start){CohRepReader cut=reader(f->data,f->bytes,f->bits-1,f->mode,f->start);refused(cut,COH_OK);truncations++;}
  uint8_t*d=malloc(f->bytes+8);CHECK(d);memcpy(d,f->data,f->bytes);memset(d+f->bytes,0xa5,8);r=reader(d,f->bytes+8,(f->bytes+8)*8,f->mode,f->start);CHECK(coh_superstats_read(&r,out,workspace,COH_SG_RAM_MAX,0)==COH_OK&&r.cursor==f->bits);
  for(size_t j=0;j<f->bytes;j+=31){memcpy(d,f->data,f->bytes);d[j]^=255;r=reader(d,f->bytes,f->bits,f->mode,f->start);CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=coh_superstats_read(&r,out,workspace,COH_SG_RAM_MAX,0);if(s!=COH_OK)CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));else CHECK(r.cursor<=r.bits&&out->count<=COH_SG_MEMBERS_MAX);mutations++;}free(d);
 }
 /* Aligned Pack1 excessive member count refuses before members access. */
 {uint8_t d[4]={151,0,0,0};CohRepReader r=reader(d,sizeof(d),32,1,0);refused(r,COH_LIMIT);}
 for(unsigned i=0;i<1000;i++){uint8_t d[512];for(unsigned j=0;j<sizeof(d);j++)d[j]=(uint8_t)(i*37+j*19);CohRepReader r=reader(d,sizeof(d),sizeof(d)*8,i%2,0),before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=coh_superstats_read(&r,out,workspace,COH_SG_RAM_MAX,0);if(s!=COH_OK)CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));else CHECK(r.cursor<=r.bits);randomized++;}
 printf("{\"passed\":true,\"checks\":%llu,\"source_fixtures\":%zu,\"truncations\":%llu,\"mutations\":%llu,\"randomized\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"whole_initial_update_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,sizeof(fixtures)/sizeof(fixtures[0]),(unsigned long long)truncations,(unsigned long long)mutations,(unsigned long long)randomized,sizeof(*out),sizeof(*workspace));free(out);free(prior);free(workspace);return 0;
}
