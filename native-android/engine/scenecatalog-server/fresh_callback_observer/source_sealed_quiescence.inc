/* NONSHIPPING fresh callback-sealed role only. The original loader guard is
 * copied byte-exactly to this private source tree, then renamed here. */
#define coh_resource_quiescence_begin coh_fresh_original_resource_quiescence_begin
#define coh_resource_quiescence_end coh_fresh_original_resource_quiescence_end
#include "coh_fresh_original_resource_quiescence.inc"
#undef coh_resource_quiescence_begin
#undef coh_resource_quiescence_end
#include "coh_fresh_folder_profile_api.h"
void coh_fresh_source_probe_loader(unsigned,unsigned);
int coh_resource_quiescence_begin(void)
{
 int result;
 if(!coh_fresh_folder_profile_begin()){
  coh_fresh_folder_profile_abort();coh_fresh_source_probe_loader(0,0);return 8;
 }
 result=coh_fresh_original_resource_quiescence_begin();
 coh_fresh_source_probe_loader((unsigned)result,0);
 if(result!=1)coh_fresh_folder_profile_abort();
 return result;
}
int coh_resource_quiescence_end(void)
{
 int valid,released,restored;
 /* An old boundary abort can retry end after a failed end-check. Never leave
  * either original critical section twice. Only the real original owner may
  * retire locks; a foreign end refuses and leaves the owner able to abort. */
 if(!coh_resource_quiet_active||coh_resource_quiet_owner!=GetCurrentThreadId())return 0;
 valid=coh_fresh_folder_profile_check();
 released=coh_fresh_original_resource_quiescence_end();
 restored=coh_fresh_folder_profile_end();
 coh_fresh_source_probe_loader(1,released==1);
 return valid&&released==1&&restored;
}
