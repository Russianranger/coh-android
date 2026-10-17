#include "coh_social.h"
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static CohStatus flag(CohRepReader*r,uint32_t*out){CohStatus s=coh_rep_read(r,1,out);return s==COH_OK&&*out>1?COH_INVALID:s;}
CohStatus coh_social_phase_read(CohRepReader*reader,CohSocialPhase*out,CohSocialWorkspace*workspace,size_t budget,size_t retained){
 CohRepReader r;CohStatus status;uint32_t ignored;size_t fixed,extra;
 if(!reader||!out||!workspace||!budget||budget>COH_SOCIAL_RAM_MAX)return COH_INVALID;
 r=*reader;status=coh_rep_read(&r,0,&ignored);if(status!=COH_OK)return status;
 const void*objects[]={reader,out,workspace,r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_SOCIAL_STACK_RESERVE;if(fixed>budget||r.bytes.size>budget-fixed||retained>budget-fixed-r.bytes.size)return COH_LIMIT;
 CohSocialPhase*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=r.cursor;
 status=flag(&r,&v->team_up_to_date);if(status!=COH_OK)return status;
 if(!v->team_up_to_date){extra=fixed-sizeof(v->team)-sizeof(workspace->team)-COH_TEAM_STACK_RESERVE+retained;status=coh_team_list_read(&r,0,&v->team,&workspace->team,budget,extra);if(status!=COH_OK)return status;}v->team_end_bit=r.cursor;
 extra=fixed-sizeof(v->superstats)-sizeof(workspace->superstats)-COH_SG_STACK_RESERVE+retained;status=coh_superstats_read(&r,&v->superstats,&workspace->superstats,budget,extra);if(status!=COH_OK)return status;v->superstats_end_bit=r.cursor;
 status=flag(&r,&v->league_up_to_date);if(status!=COH_OK)return status;
 if(!v->league_up_to_date){extra=fixed-sizeof(v->league)-sizeof(workspace->team)-COH_TEAM_STACK_RESERVE+retained;status=coh_team_list_read(&r,1,&v->league,&workspace->team,budget,extra);if(status!=COH_OK)return status;}
 v->end_bit=r.cursor;*out=*v;*reader=r;return COH_OK;
}
