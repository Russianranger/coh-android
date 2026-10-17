#include "coh_dynamic.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"dynamic check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t bytes,start,bits;unsigned mode,scenario;uint32_t expected_count;const CohDynamicDiagnostic*expected;}Fixture;
#include "fixtures.h"
static CohDynamicDiagnostic*out,*prior;static CohDynamicWorkspace*workspace;
static CohRepReader reader(const uint8_t*d,size_t bytes,size_t bits,unsigned mode,size_t begin){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){d,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=begin;return r;}
static void refused(CohRepReader r,uint32_t count){CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CHECK(coh_dynamic_diagnostic_read(&r,count,out,workspace,COH_DYNAMIC_RAM_MAX,0)!=COH_OK);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));}
int main(void){out=malloc(sizeof(*out));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));CHECK(out&&prior&&workspace);
 for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
  const Fixture*f=&fixtures[i];CohRepReader r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CHECK(coh_dynamic_diagnostic_read(&r,f->expected_count,out,workspace,COH_DYNAMIC_RAM_MAX,0)==COH_OK);CHECK(r.cursor==f->bits&&out->begin_bit==f->start&&out->end_bit==f->bits);CHECK(out->modified_count==f->expected->modified_count&&out->expected_count==f->expected_count&&out->world_ownership_verified==0);CHECK(out->raw_bytes==f->expected->raw_bytes);CHECK(!memcmp(out->full_status,f->expected->full_status,sizeof(out->full_status))&&!memcmp(out->deltas,f->expected->deltas,sizeof(out->deltas)));CHECK(workspace->arena_used<=COH_DYNAMIC_ZLIB_ARENA_BYTES);
  if(f->start==0){for(size_t bit=0;bit<f->bits;bit++){CohRepReader cut=reader(f->data,f->bytes,bit,f->mode,0);refused(cut,f->expected_count);truncations++;}size_t minimum=sizeof(*out)+sizeof(*workspace)+COH_DYNAMIC_STACK_RESERVE+f->bytes;r=reader(f->data,f->bytes,f->bits,f->mode,0);CHECK(coh_dynamic_diagnostic_read(&r,f->expected_count,out,workspace,minimum,0)==COH_OK);r=reader(f->data,f->bytes,f->bits,f->mode,0);CohRepReader before=r;*prior=*out;CHECK(coh_dynamic_diagnostic_read(&r,f->expected_count,out,workspace,minimum-1,0)==COH_LIMIT);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));CHECK(coh_dynamic_diagnostic_read(&r,f->expected_count,out,(CohDynamicWorkspace*)out,COH_DYNAMIC_RAM_MAX,0)==COH_INVALID);CHECK(coh_dynamic_diagnostic_read(&r,f->expected_count,out,workspace,minimum,1)==COH_LIMIT);if(out->modified_count==UINT32_MAX){r=reader(f->data,f->bytes,f->bits,f->mode,0);refused(r,f->expected_count+1);}}
  uint8_t*d=malloc(f->bytes+8);CHECK(d);memcpy(d,f->data,f->bytes);memset(d+f->bytes,0xa5,8);r=reader(d,f->bytes+8,(f->bytes+8)*8,f->mode,f->start);CHECK(coh_dynamic_diagnostic_read(&r,f->expected_count,out,workspace,COH_DYNAMIC_RAM_MAX,0)==COH_OK&&r.cursor==f->bits);
  for(size_t j=0;j<f->bytes;j++){memcpy(d,f->data,f->bytes);d[j]^=255;r=reader(d,f->bytes,f->bits,f->mode,f->start);CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=coh_dynamic_diagnostic_read(&r,f->expected_count,out,workspace,COH_DYNAMIC_RAM_MAX,0);if(s!=COH_OK)CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));else CHECK(r.cursor<=r.bits&&out->world_ownership_verified==0);mutations++;}free(d);
 }
 {uint8_t d[4]={1,0,1,0};CohRepReader r=reader(d,sizeof(d),32,1,0);refused(r,0);}
 printf("{\"passed\":true,\"checks\":%llu,\"source_fixtures\":%zu,\"truncations\":%llu,\"mutations\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"world_ownership_authenticated\":false,\"whole_initial_update_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,sizeof(fixtures)/sizeof(fixtures[0]),(unsigned long long)truncations,(unsigned long long)mutations,sizeof(*out),sizeof(*workspace));free(out);free(prior);free(workspace);return 0;
}
