/* NONSHIPPING: appended to unchanged Common/seq/anim.c, where original private
 * loader counters/queues/critical sections are visible. No load, finalization,
 * force-complete, wait, cancellation, queue or gameplay state is changed.
 * Try-only locks reject contention; successful owner retains both until end.
 * Main owner must schedule no new loads/callbacks during the observation lease.
 */
#ifndef COH_RESOURCE_QUIESCENCE_INCLUDED
#define COH_RESOURCE_QUIESCENCE_INCLUDED
#if defined(SERVER) && defined(_WIN32)
static unsigned coh_resource_quiet_active;
static DWORD coh_resource_quiet_owner;
int coh_resource_quiescence_begin(void)
{
    if(!initedBackgroundLoader)return 2;
    if(coh_resource_quiet_active)return 3;
    if(GetCurrentThreadId()==background_loader_threadID)return 4;
    if(!TryEnterCriticalSection(&heyThreadLoadAGeo_CriticalSection))return 5;
    if(!TryEnterCriticalSection(&heyThreadLODAModel_CriticalSection))
    {LeaveCriticalSection(&heyThreadLoadAGeo_CriticalSection);return 6;}
    if(number_of_glds_in_background_loader||number_of_lods_in_background_loader||glds_ready_for_final_processing)
    {
        LeaveCriticalSection(&heyThreadLODAModel_CriticalSection);
        LeaveCriticalSection(&heyThreadLoadAGeo_CriticalSection);return 7;
    }
    coh_resource_quiet_owner=GetCurrentThreadId();coh_resource_quiet_active=1;
    return 1;
}
int coh_resource_quiescence_end(void)
{
    if(!coh_resource_quiet_active||coh_resource_quiet_owner!=GetCurrentThreadId())return 0;
    coh_resource_quiet_active=0;coh_resource_quiet_owner=0;
    LeaveCriticalSection(&heyThreadLODAModel_CriticalSection);
    LeaveCriticalSection(&heyThreadLoadAGeo_CriticalSection);return 1;
}
#else
int coh_resource_quiescence_begin(void){return 0;}
int coh_resource_quiescence_end(void){return 0;}
#endif
#endif
