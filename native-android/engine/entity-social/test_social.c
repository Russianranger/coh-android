#include "coh_social.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"social check failed %d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct{const uint8_t*data;size_t bytes,start,bits;unsigned mode,kind,scenario;const CohTeamList*expected;}TeamFixture;
#include "team_fixtures.h"
typedef struct{const uint8_t*data;size_t bytes,start,bits;unsigned mode,scenario;const CohSuperStats*expected;}SgFixture;
#include "sg_fixtures.h"
typedef struct{const uint8_t*data;size_t bytes,start,team_end,sg_end,bits;unsigned mode,team_skip,league_skip;const TeamFixture*team;const SgFixture*sg;const TeamFixture*league;}SocialFixture;
#include "social_fixtures.h"
static CohSocialPhase*out,*prior;static CohSocialWorkspace*workspace;
static CohRepReader reader(const uint8_t*d,size_t bytes,size_t bits,unsigned mode,size_t begin){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){d,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=begin;return r;}
static void refusal(CohRepReader r){CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CHECK(coh_social_phase_read(&r,out,workspace,COH_SOCIAL_RAM_MAX,0)!=COH_OK);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));}
int main(void){out=malloc(sizeof(*out));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));CHECK(out&&prior&&workspace);
 for(size_t i=0;i<sizeof(social_fixtures)/sizeof(social_fixtures[0]);i++){
  const SocialFixture*f=&social_fixtures[i];CohRepReader r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CHECK(coh_social_phase_read(&r,out,workspace,COH_SOCIAL_RAM_MAX,0)==COH_OK);CHECK(r.cursor==f->bits&&out->begin_bit==f->start&&out->team_end_bit==f->team_end&&out->superstats_end_bit==f->sg_end&&out->end_bit==f->bits);CHECK(out->team_up_to_date==f->team_skip&&out->league_up_to_date==f->league_skip);if(f->team)CHECK(!memcmp(&out->team,f->team->expected,offsetof(CohTeamList,begin_bit)));else CHECK(out->team.id==0&&out->team.count==0);CHECK(!memcmp(&out->superstats,f->sg->expected,offsetof(CohSuperStats,begin_bit)));if(f->league)CHECK(!memcmp(&out->league,f->league->expected,offsetof(CohTeamList,begin_bit)));else CHECK(out->league.id==0&&out->league.count==0);
  if(i%100==0){for(size_t bit=f->start;bit<f->bits;bit+=31){CohRepReader cut=reader(f->data,f->bytes,bit,f->mode,f->start);refusal(cut);truncations++;}size_t minimum=sizeof(*out)+sizeof(*workspace)+COH_SOCIAL_STACK_RESERVE+f->bytes;r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CHECK(coh_social_phase_read(&r,out,workspace,minimum,0)==COH_OK);r=reader(f->data,f->bytes,f->bits,f->mode,f->start);CohRepReader before=r;*prior=*out;CHECK(coh_social_phase_read(&r,out,workspace,minimum-1,0)==COH_LIMIT);CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));CHECK(coh_social_phase_read(&r,out,(CohSocialWorkspace*)out,COH_SOCIAL_RAM_MAX,0)==COH_INVALID);CHECK(coh_social_phase_read(&r,out,workspace,minimum,1)==COH_LIMIT);}
  if(f->bits>f->start){CohRepReader cut=reader(f->data,f->bytes,f->bits-1,f->mode,f->start);refusal(cut);truncations++;}
  if(i%10==0){uint8_t*d=malloc(f->bytes+8);CHECK(d);memcpy(d,f->data,f->bytes);memset(d+f->bytes,0xa5,8);r=reader(d,f->bytes+8,(f->bytes+8)*8,f->mode,f->start);CHECK(coh_social_phase_read(&r,out,workspace,COH_SOCIAL_RAM_MAX,0)==COH_OK&&r.cursor==f->bits);for(size_t j=0;j<f->bytes;j+=71){memcpy(d,f->data,f->bytes);d[j]^=255;r=reader(d,f->bytes,f->bits,f->mode,f->start);CohRepReader before=r;memset(out,0xa5,sizeof(*out));*prior=*out;CohStatus s=coh_social_phase_read(&r,out,workspace,COH_SOCIAL_RAM_MAX,0);if(s!=COH_OK)CHECK(!memcmp(&before,&r,sizeof(r))&&!memcmp(out,prior,sizeof(*out)));else CHECK(r.cursor<=r.bits);mutations++;}free(d);}
 }
 printf("{\"passed\":true,\"checks\":%llu,\"composed_source_fragments\":%zu,\"sampled_truncations\":%llu,\"sampled_mutations\":%llu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"whole_initial_update_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,sizeof(social_fixtures)/sizeof(social_fixtures[0]),(unsigned long long)truncations,(unsigned long long)mutations,sizeof(*out),sizeof(*workspace));free(out);free(prior);free(workspace);return 0;
}
