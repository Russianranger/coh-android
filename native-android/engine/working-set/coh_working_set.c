#include "coh_working_set.h"
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#define CALL_RESERVE (16u*1024u)
typedef struct {uint64_t serial;size_t total,persistent;const void *owner;unsigned phase;} Entry;
struct CohWorkingSet {CohWsReport report;uint64_t parent_serial,next;Entry entries[COH_WS_SLOTS];};
static _Atomic uint64_t parent_next=1;
static int disjoint(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 return a&&b&&an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);
}
static int ticket_zero(const CohWsTicket*t){return !t->parent_serial&&!t->serial&&!t->slot&&!t->reserved;}
static int ticket_valid(const CohWorkingSet*s,const CohWsTicket*t){
 return t->parent_serial==s->parent_serial&&t->serial&&t->slot<COH_WS_SLOTS&&!t->reserved&&s->entries[t->slot].phase&&s->entries[t->slot].serial==t->serial;
}
static int add(size_t*a,size_t b,size_t cap){if(*a>cap||b>cap-*a)return 0;*a+=b;return 1;}
CohStatus coh_ws_create(size_t limit,CohWorkingSet **out){
 size_t base=sizeof(CohWorkingSet)+CALL_RESERVE;
 if(!out)return COH_INVALID;
 if(*out)return COH_STATE;
 if(limit<base||limit>COH_WS_MAX)return COH_LIMIT;
 CohWorkingSet*s=calloc(1,sizeof(*s));if(!s)return COH_LIMIT;
 uint64_t id=atomic_load(&parent_next);
 do {if(id==UINT64_MAX){free(s);return COH_LIMIT;}}while(!atomic_compare_exchange_weak(&parent_next,&id,id+1));
 s->parent_serial=id;s->report=(CohWsReport){limit,base,base,base,0,0};*out=s;return COH_OK;
}
CohStatus coh_ws_prepare(CohWorkingSet*s,const CohWsPlan*p,CohWsTicket*out){
 if(!s||!p||!out)return COH_INVALID;
 if(!disjoint(s,sizeof(*s),p,sizeof(*p))||!disjoint(s,sizeof(*s),out,sizeof(*out))||!disjoint(p,sizeof(*p),out,sizeof(*out)))return COH_INVALID;
 if(!ticket_zero(out))return COH_STATE;
 size_t total=0;
 if(!p->persistent_bytes||!p->child_limit||p->child_limit>s->report.limit||!add(&total,p->persistent_bytes,p->child_limit)||!add(&total,p->temporary_bytes,p->child_limit)||!add(&total,p->call_reserve,p->child_limit)||total>s->report.limit-s->report.booked||s->next==UINT64_MAX)return COH_LIMIT;
 unsigned slot=0;while(slot<COH_WS_SLOTS&&s->entries[slot].phase)slot++;
 if(slot==COH_WS_SLOTS)return COH_LIMIT;
 Entry e={s->next+1,total,p->persistent_bytes,NULL,1};
 CohWsTicket t={s->parent_serial,e.serial,slot,0};
 s->entries[slot]=e;s->next=e.serial;s->report.booked+=total;
 if(s->report.booked>s->report.peak)s->report.peak=s->report.booked;
 s->report.preparing++;*out=t;return COH_OK;
}
CohStatus coh_ws_commit(CohWorkingSet*s,const CohWsTicket*t,const void*owner,size_t actual){
 if(!s||!t||!owner)return COH_INVALID;
 if(!disjoint(s,sizeof(*s),t,sizeof(*t))||!disjoint(s,sizeof(*s),owner,1)||!disjoint(t,sizeof(*t),owner,1))return COH_INVALID;
 if(!ticket_valid(s,t))return COH_STATE;
 Entry *e=&s->entries[t->slot];if(e->phase!=1)return COH_STATE;
 if(!actual||actual>e->persistent)return COH_LIMIT;
 for(unsigned i=0;i<COH_WS_SLOTS;i++)if(s->entries[i].phase==2&&s->entries[i].owner==owner)return COH_STATE;
 s->report.booked-=e->total-actual;e->total=actual;e->owner=owner;e->phase=2;
 s->report.preparing--;s->report.resident++;return COH_OK;
}
static CohStatus finish(CohWorkingSet*s,CohWsTicket*t,const void*owner,unsigned phase){
 if(!s||!t)return COH_INVALID;
 if(!disjoint(s,sizeof(*s),t,sizeof(*t)))return COH_INVALID;
 if(phase==2&&owner&&!disjoint(t,sizeof(*t),owner,1))return COH_INVALID;
 if(!ticket_valid(s,t))return COH_STATE;
 Entry *e=&s->entries[t->slot];if(e->phase!=phase||(phase==2&&(!owner||e->owner!=owner)))return COH_STATE;
 s->report.booked-=e->total;
 if(phase==1)s->report.preparing--;else s->report.resident--;
 memset(e,0,sizeof(*e));memset(t,0,sizeof(*t));return COH_OK;
}
CohStatus coh_ws_abort(CohWorkingSet*s,CohWsTicket*t){return finish(s,t,NULL,1);}
CohStatus coh_ws_release(CohWorkingSet*s,CohWsTicket*t,const void*owner){return finish(s,t,owner,2);}
CohStatus coh_ws_report(const CohWorkingSet*s,CohWsReport*out){
 if(!s||!out)return COH_INVALID;
 if(!disjoint(s,sizeof(*s),out,sizeof(*out)))return COH_INVALID;
 *out=s->report;return COH_OK;
}
CohStatus coh_ws_destroy(CohWorkingSet**out){
 if(!out||!*out)return COH_INVALID;
 CohWorkingSet*s=*out;if(!disjoint(s,sizeof(*s),out,sizeof(*out)))return COH_INVALID;
 if(s->report.preparing||s->report.resident)return COH_STATE;
 memset(s,0,sizeof(*s));free(s);*out=NULL;return COH_OK;
}
