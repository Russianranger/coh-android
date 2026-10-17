#include "coh_working_set.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
static unsigned allocations,frees;
static size_t actual_parent_bytes;
void *__real_calloc(size_t,size_t);
void __real_free(void *);
void *__wrap_calloc(size_t n,size_t bytes){void*p=__real_calloc(n,bytes);if(p){allocations++;actual_parent_bytes=n*bytes;}return p;}
void __wrap_free(void*p){if(p)frees++;__real_free(p);}
#define CHECK(v) do {checks++;if(!(v)){fprintf(stderr,"check failed line %d: %s\n",__LINE__,#v);exit(1);}}while(0)
static CohWsReport report(CohWorkingSet*s){CohWsReport r;CHECK(coh_ws_report(s,&r)==COH_OK);return r;}
static void same(CohWorkingSet*s,CohWsReport before){CohWsReport after=report(s);CHECK(!memcmp(&before,&after,sizeof(before)));}
int main(void){
 CohWorkingSet*s=NULL,*other=NULL;int world,category,a,b;
 CHECK(coh_ws_create(COH_WS_MAX+1,&s)==COH_LIMIT&&!s);
 CHECK(coh_ws_create(1,&s)==COH_LIMIT&&!s);
 CHECK(coh_ws_create(COH_WS_MAX,&s)==COH_OK);
 CohWsReport initial=report(s);CHECK(initial.booked==initial.base_reserved&&initial.peak==initial.booked&&initial.booked>=16384);
 CHECK(initial.base_reserved==actual_parent_bytes+16384&&allocations==1&&!frees);
 CHECK(coh_ws_create(COH_WS_MAX,&s)==COH_STATE);
 /* Synthetic RESERVATIONS, not allocation/RSS or actual module-adapter proof.
  * A 90MB resident reservation may coexist with an unchanged 1MiB child cap. */
 CohWsTicket w={0},c={0};CohWsPlan wp={90000000,0,0,COH_WS_MAX};
 CHECK(coh_ws_prepare(s,&wp,&w)==COH_OK);CHECK(coh_ws_commit(s,&w,&world,90000000)==COH_OK);
 CohWsPlan cp={374856,374856,65536,1048576};
 CHECK(coh_ws_prepare(s,&cp,&c)==COH_OK);CohWsReport reserved=report(s);
 CHECK(reserved.booked==initial.booked+90000000+374856*2+65536);
 CHECK(coh_ws_destroy(&s)==COH_STATE&&s);
 CHECK(coh_ws_release(s,&c,&category)==COH_STATE);same(s,reserved);
 CHECK(coh_ws_commit(s,&c,&world,374856)==COH_STATE);same(s,reserved);
 CHECK(coh_ws_commit(s,&c,&category,374857)==COH_LIMIT);same(s,reserved);
 CHECK(coh_ws_commit(s,&c,&category,374856)==COH_OK);
 CHECK(report(s).booked==initial.booked+90000000+374856);
 CHECK(coh_ws_abort(s,&c)==COH_STATE);
 CohWsTicket refused={0};CohWsPlan over={11000000,0,0,COH_WS_MAX};reserved=report(s);
 CHECK(coh_ws_prepare(s,&over,&refused)==COH_LIMIT&&!refused.serial);same(s,reserved);
 over=(CohWsPlan){1,1048576,0,1048576};CHECK(coh_ws_prepare(s,&over,&refused)==COH_LIMIT);same(s,reserved);
 over=(CohWsPlan){SIZE_MAX,SIZE_MAX,SIZE_MAX,COH_WS_MAX};CHECK(coh_ws_prepare(s,&over,&refused)==COH_LIMIT);same(s,reserved);
 CHECK(coh_ws_create(COH_WS_MAX,&other)==COH_OK);
 CHECK(coh_ws_commit(other,&c,&a,1)==COH_STATE);
 CHECK(coh_ws_release(other,&c,&category)==COH_STATE);
 CHECK(coh_ws_release(s,&c,&a)==COH_STATE);same(s,reserved);
 CohWsTicket stale=c;CHECK(coh_ws_release(s,&c,&category)==COH_OK&&!c.serial);
 CohWsPlan tiny={1,2,3,6};CHECK(coh_ws_prepare(s,&tiny,&c)==COH_OK);
 CHECK(c.slot==stale.slot&&c.serial!=stale.serial);
 CHECK(coh_ws_abort(s,&stale)==COH_STATE);
 CHECK(coh_ws_commit(s,&stale,&b,1)==COH_STATE);
 CHECK(coh_ws_abort(s,&c)==COH_OK);
 CHECK(coh_ws_release(s,&w,&world)==COH_OK);
 CHECK(report(s).booked==initial.booked);
 /* Exactly full global and child bounds, including parent's own reserve. */
 CohWsPlan exact={COH_WS_MAX-initial.booked,0,0,COH_WS_MAX-initial.booked};
 CHECK(coh_ws_prepare(s,&exact,&w)==COH_OK&&report(s).booked==COH_WS_MAX);
 CHECK(coh_ws_prepare(s,&tiny,&c)==COH_LIMIT);
 CHECK(coh_ws_abort(s,&w)==COH_OK);
 CohWsTicket tickets[COH_WS_SLOTS]={{0}};
 for(unsigned i=0;i<COH_WS_SLOTS;i++)CHECK(coh_ws_prepare(s,&tiny,&tickets[i])==COH_OK);
 reserved=report(s);CHECK(coh_ws_prepare(s,&tiny,&c)==COH_LIMIT);same(s,reserved);
 for(unsigned i=0;i<COH_WS_SLOTS;i++)CHECK(coh_ws_abort(s,&tickets[i])==COH_OK);
 /* Repeated slot reuse cannot revive an old accounting ticket. */
 for(unsigned i=0;i<1024;i++){
  CHECK(coh_ws_prepare(s,&tiny,&c)==COH_OK);stale=c;
  CHECK(coh_ws_commit(s,&c,&a,1)==COH_OK);
  CHECK(coh_ws_commit(s,&c,&a,1)==COH_STATE);
  CHECK(coh_ws_release(s,&c,&a)==COH_OK);
  CHECK(coh_ws_release(s,&stale,&a)==COH_STATE);
 }
 CHECK(coh_ws_prepare(s,&tiny,&c)==COH_OK);stale=c;stale.reserved=1;
 reserved=report(s);CHECK(coh_ws_abort(s,&stale)==COH_STATE);same(s,reserved);
 CHECK(coh_ws_prepare(s,&tiny,&c)==COH_STATE);same(s,reserved);
 CHECK(coh_ws_report(s,(CohWsReport*)s)==COH_INVALID);
 CHECK(coh_ws_prepare(s,(const CohWsPlan*)s,&refused)==COH_INVALID);
 CHECK(coh_ws_prepare(s,&tiny,(CohWsTicket*)s)==COH_INVALID);
 CHECK(coh_ws_abort(s,(CohWsTicket*)s)==COH_INVALID);
 CHECK(coh_ws_abort(s,&c)==COH_OK);
 CHECK(coh_ws_destroy(&s)==COH_OK&&!s);
 CHECK(coh_ws_destroy(&other)==COH_OK&&!other);
 CHECK(allocations==2&&frees==2);
 printf("{\"passed\":true,\"checks\":%u,\"parent_metadata_bytes\":%zu,\"parent_base_reserved_bytes\":%zu,\"parent_allocations\":%u,\"parent_frees\":%u,\"allocation_reservations_only\":true,\"module_adapters_qualified\":false,\"global_pipeline\":false,\"world_authority\":false}\n",checks,actual_parent_bytes,initial.base_reserved,allocations,frees);
 return 0;
}
