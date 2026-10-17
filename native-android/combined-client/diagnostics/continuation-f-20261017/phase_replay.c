/* Independent reservation replay. Keys below are synthetic billing keys, NOT
 * actual source owners. No resource, provider, actor or GPU is instantiated. */
#include "working-set/coh_working_set.h"
#include "costs.h"
#include <stdio.h>
#include <stdlib.h>
static unsigned checks;
static unsigned char keys[8];
#define CHECK(v) do {checks++;if(!(v)){fprintf(stderr,"phase replay line %d: %s\n",__LINE__,#v);exit(1);}} while(0)
static CohWsReport report(CohWorkingSet*s){CohWsReport r;CHECK(coh_ws_report(s,&r)==COH_OK);return r;}
static void unchanged(CohWorkingSet*s,CohWsReport old){
 CohWsReport r=report(s);CHECK(r.limit==old.limit&&r.base_reserved==old.base_reserved&&
 r.booked==old.booked&&r.peak==old.peak&&r.preparing==old.preparing&&r.resident==old.resident);
}
static void add(CohWorkingSet*s,size_t bytes,unsigned key,CohWsTicket*out){
 CohWsPlan plan={bytes,0,0,COH_WS_MAX};CHECK(coh_ws_prepare(s,&plan,out)==COH_OK);
 CHECK(coh_ws_commit(s,out,&keys[key],bytes)==COH_OK);
}
int main(void){
 CohWorkingSet*s=NULL;CohWsTicket t[8]={{0}};CHECK(coh_ws_create(COH_WS_MAX,&s)==COH_OK);
 CohWsReport base=report(s);CHECK(base.base_reserved==EXPECTED_PARENT);
 /* Split one receipt's aggregate into mutually exclusive billing partitions;
  * this is arithmetic attribution, not owner discovery/deduplication. */
 add(s,SHARED_SOURCE,0,&t[0]);add(s,PRIOR_ALLOWANCE,1,&t[1]);
 add(s,GEO_RESERVATION,2,&t[2]);add(s,OLD_EXCLUSIVE,3,&t[3]);
 CHECK(report(s).booked==EXPECTED_PARENT+WORLD_OLD);
 add(s,DICTIONARIES,4,&t[4]);
 CohWsReport before=report(s);
 CohWsPlan sets={POWER_SETS,0,0,COH_WS_MAX};
 CHECK(coh_ws_prepare(s,&sets,&t[5])==COH_LIMIT);unchanged(s,before);
 CohWsPlan candidate={SEALED_OWNED,SEAL_CALL_RESERVE,0,COH_WS_MAX};
 CHECK(coh_ws_prepare(s,&candidate,&t[6])==COH_OK);
 CohWsReport preparing=report(s);CHECK(preparing.booked==EXPECTED_TRANSITION);
 CHECK(coh_ws_prepare(s,&sets,&t[5])==COH_LIMIT);unchanged(s,preparing);
 /* A late failure retains every old/candidate charge until caller cleanup. */
 CHECK(coh_ws_commit(s,&t[6],&keys[3],SEALED_OWNED)==COH_STATE);unchanged(s,preparing);
 CHECK(coh_ws_commit(s,&t[6],&keys[6],SEALED_OWNED+1)==COH_LIMIT);unchanged(s,preparing);
 CHECK(coh_ws_destroy(&s)==COH_STATE);unchanged(s,preparing);
 CHECK(coh_ws_abort(s,&t[6])==COH_OK);
 CohWsReport after_abort=report(s);CHECK(after_abort.booked==before.booked&&after_abort.preparing==0);
 CHECK(after_abort.resident==before.resident&&after_abort.peak==EXPECTED_TRANSITION);
 /* Repeat candidate reservation. Committing only retires its temporary call
  * charge. It does NOT retire old GEO/copy keys or prove external cleanup. */
 CHECK(coh_ws_prepare(s,&candidate,&t[6])==COH_OK);
 CHECK(coh_ws_commit(s,&t[6],&keys[6],SEALED_OWNED)==COH_OK);
 CohWsReport sealed=report(s);CHECK(sealed.booked==EXPECTED_TRANSITION-SEAL_CALL_RESERVE);
 CHECK(coh_ws_prepare(s,&sets,&t[5])==COH_LIMIT);unchanged(s,sealed);
 CHECK(coh_ws_release(s,&t[2],&keys[7])==COH_STATE);unchanged(s,sealed);
 /* Synthetic external-cleanup boundary. The real application must actually
  * destroy old owners/provider before making these accounting calls. */
 CHECK(coh_ws_release(s,&t[3],&keys[3])==COH_OK);
 CHECK(coh_ws_release(s,&t[2],&keys[2])==COH_OK);
 CohWsReport retired=report(s);CHECK(retired.booked==EXPECTED_PARENT+WORLD_RETIRED+DICTIONARIES);
 add(s,POWER_SETS,5,&t[5]);CohWsReport final=report(s);
 CHECK(final.booked==EXPECTED_FINAL&&final.peak==EXPECTED_TRANSITION);
 for(unsigned i=0;i<7;i++)if(t[i].serial)CHECK(coh_ws_release(s,&t[i],&keys[i])==COH_OK);
 CHECK(report(s).booked==base.booked);CHECK(coh_ws_destroy(&s)==COH_OK&&!s);
 printf("{\"passed\":true,\"checks\":%u,\"parent_bytes\":%zu,\"old_plus_dictionaries\":%zu,"
 "\"old_candidate_transition\":%zu,\"after_commit_before_external_retirement\":%zu,"
 "\"after_retirement_and_sets\":%zu,\"remaining_named_bytes\":%zu,"
 "\"actual_resource_cleanup_observed\":false,\"module_adapter_qualified\":false,"
 "\"rss_measured\":false,\"world_authority\":false}\n",checks,base.booked,before.booked,
 preparing.booked,sealed.booked,final.booked,final.limit-final.booked);
 return 0;
}
