#include "coh_team.h"
#include <string.h>
typedef struct{CohRepReader r;CohStatus status;}TeamReader;
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static uint32_t scalar(TeamReader*p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,n,&v);if(p->status==COH_OK&&n<32&&v>=(UINT32_C(1)<<n))p->status=COH_INVALID;return v;}
static uint32_t pack(TeamReader*p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,n,&v);return v;}
static uint32_t automatic(TeamReader*p){static const unsigned widths[]={2,10,24,32};uint32_t tag=scalar(p,2);return p->status==COH_OK?scalar(p,widths[tag]):0;}
static void string(TeamReader*p,char*out,size_t capacity){if(p->status==COH_OK)p->status=coh_rep_string(&p->r,out,capacity);}
CohStatus coh_team_list_read(CohRepReader*reader,unsigned kind,CohTeamList*out,CohTeamWorkspace*workspace,size_t budget,size_t retained){
 TeamReader p;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||kind>1||!budget||budget>COH_TEAM_RAM_MAX)return COH_INVALID;
 p.r=*reader;p.status=coh_rep_read(&p.r,0,&ignored);if(p.status!=COH_OK)return p.status;
 const void*objects[]={reader,out,workspace,p.r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),p.r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_TEAM_STACK_RESERVE;if(fixed>budget||p.r.bytes.size>budget-fixed||retained>budget-fixed-p.r.bytes.size)return COH_LIMIT;
 CohTeamList*v=&workspace->candidate;memset(v,0,sizeof(*v));v->league=kind;v->begin_bit=p.r.cursor;v->identity_present=scalar(&p,1);if(v->identity_present)v->id=pack(&p,22);
 if(!kind){v->taskforce=scalar(&p,2);v->lfg=scalar(&p,10);}
 if(v->id){v->leader=pack(&p,32);v->count=pack(&p,1);if(p.status==COH_OK&&v->count>(kind?COH_LEAGUE_MEMBERS_MAX:COH_TEAM_MEMBERS_MAX))p.status=COH_LIMIT;
  if(!kind){v->level=automatic(&p);v->mentor=automatic(&p);v->active=automatic(&p);}
  for(uint32_t i=0;i<v->count&&p.status==COH_OK;i++){CohTeamMember*m=&v->members[i];m->dbid=scalar(&p,32);m->on_map=scalar(&p,1);if(!m->on_map){m->changed=scalar(&p,1);if(m->changed){string(&p,m->name,sizeof(m->name));string(&p,m->map,sizeof(m->map));}}if(kind){m->team_leader=scalar(&p,32);m->locked=scalar(&p,32);}}
 }
 if(p.status!=COH_OK)return p.status;
 v->end_bit=p.r.cursor;*out=*v;*reader=p.r;return COH_OK;
}
