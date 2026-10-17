#include "coh_superstats.h"
#include <string.h>
typedef struct{CohRepReader r;CohStatus status;}SgReader;
static int overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static uint32_t scalar(SgReader*p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,n,&v);if(p->status==COH_OK&&n<32&&v>=(UINT32_C(1)<<n))p->status=COH_INVALID;return v;}
static uint32_t pack(SgReader*p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,n,&v);return v;}
static uint32_t automatic(SgReader*p){static const unsigned widths[]={2,10,24,32};uint32_t tag=scalar(p,2);return p->status==COH_OK?scalar(p,widths[tag]):0;}
static void string(SgReader*p,char*out,size_t cap){for(size_t i=0;i<cap&&p->status==COH_OK;i++){uint32_t c=scalar(p,8);if(p->status!=COH_OK)return;out[i]=(char)c;if(!c)return;}if(p->status==COH_OK)p->status=COH_LIMIT;}
CohStatus coh_superstats_read(CohRepReader*reader,CohSuperStats*out,CohSuperStatsWorkspace*workspace,size_t budget,size_t retained){
 SgReader p;uint32_t ignored;size_t fixed;
 if(!reader||!out||!workspace||!budget||budget>COH_SG_RAM_MAX)return COH_INVALID;
 p.r=*reader;p.status=coh_rep_read(&p.r,0,&ignored);if(p.status!=COH_OK)return p.status;
 const void*objects[]={reader,out,workspace,p.r.bytes.data};const size_t sizes[]={sizeof(*reader),sizeof(*out),sizeof(*workspace),p.r.bytes.size};for(unsigned i=0;i<4;i++)for(unsigned j=0;j<i;j++)if(overlap(objects[i],sizes[i],objects[j],sizes[j]))return COH_INVALID;
 fixed=sizeof(*out)+sizeof(*workspace)+COH_SG_STACK_RESERVE;if(fixed>budget||p.r.bytes.size>budget-fixed||retained>budget-fixed-p.r.bytes.size)return COH_LIMIT;
 CohSuperStats*v=&workspace->candidate;memset(v,0,sizeof(*v));v->begin_bit=p.r.cursor;v->count=pack(&p,1);if(p.status==COH_OK&&v->count>COH_SG_MEMBERS_MAX)p.status=COH_LIMIT;
 if(v->count){for(unsigned i=0;i<7;i++)v->financial[i]=pack(&p,1);v->update=scalar(&p,1);
  if(v->update){for(uint32_t i=0;i<v->count&&p.status==COH_OK;i++){CohSuperMember*m=&v->members[i];string(&p,m->name,sizeof(m->name));m->dbid=pack(&p,1);m->rank=pack(&p,1);m->level=pack(&p,1);m->last_online=scalar(&p,32);m->online=scalar(&p,1);string(&p,m->arch,sizeof(m->arch));string(&p,m->origin,sizeof(m->origin));m->member_since=scalar(&p,32);m->prestige=scalar(&p,32);m->player_type=pack(&p,1);if(m->online)string(&p,m->zone,sizeof(m->zone));}
   string(&p,v->name,sizeof(v->name));string(&p,v->motto,sizeof(v->motto));string(&p,v->message,sizeof(v->message));string(&p,v->emblem,sizeof(v->emblem));string(&p,v->description,sizeof(v->description));for(unsigned i=0;i<4;i++)v->colors_tithe_spaces[i]=pack(&p,1);v->demote_timeout=scalar(&p,32);
   for(unsigned i=0;i<COH_SG_RANKS&&p.status==COH_OK;i++){CohSuperRank*r=&v->ranks[i];string(&p,r->name,sizeof(r->name));if(p.status==COH_OK){size_t skip=(8-p.r.cursor%8)%8;if(skip>p.r.bits-p.r.cursor)p.status=COH_INVALID;else p.r.cursor+=skip;}for(unsigned j=0;j<4;j++)r->permission_bytes[j]=(uint8_t)scalar(&p,8);}
   v->entry_permission=automatic(&p);v->memberrank_count=pack(&p,1);if(p.status==COH_OK&&v->memberrank_count>COH_SG_MEMBERS_MAX)p.status=COH_LIMIT;for(uint32_t i=0;i<v->memberrank_count&&p.status==COH_OK;i++){v->memberranks[i][0]=pack(&p,22);v->memberranks[i][1]=pack(&p,1);}
   for(unsigned i=0;i<COH_SG_ALLIES&&p.status==COH_OK;i++){CohSuperAlly*a=&v->allies[i];a->dbid=scalar(&p,32);if(a->dbid){a->dont_talk=scalar(&p,1);a->min_display_rank=automatic(&p);string(&p,a->name,sizeof(a->name));}}v->alliance_min_talk_rank=automatic(&p);
  }
 }
 if(p.status!=COH_OK)return p.status;
 v->end_bit=p.r.cursor;*out=*v;*reader=p.r;return COH_OK;
}
