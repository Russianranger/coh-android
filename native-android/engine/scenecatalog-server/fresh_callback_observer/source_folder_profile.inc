/* NONSHIPPING. Exact original queue add/free sites supply reservations. No
 * queue node is read here. This recursive Win32 lock protects bookkeeping and
 * transitions ONLY. Allocation, update/callback bodies and model locks remain
 * outside it. Its release after restore is the observation's atomic close. */
#ifndef COH_FRESH_FOLDER_PROFILE_INCLUDED
#define COH_FRESH_FOLDER_PROFILE_INCLUDED
#define COH_FRESH_FOLDER_COUNTER_MAX 65535L
static CRITICAL_SECTION coh_ff_guard;
static volatile LONG coh_ff_guard_state;
static volatile LONG coh_ff_queue,coh_ff_queue_writers,coh_ff_updates,coh_ff_callbacks,coh_ff_setters,coh_ff_epoch;
static volatile LONG coh_ff_failure,coh_ff_attempted,coh_ff_sealed,coh_ff_lease;
static volatile LONG coh_ff_private_setter,coh_ff_owner,coh_ff_accounting_bad;
static unsigned coh_ff_started,coh_ff_finished,coh_ff_restored,coh_ff_saved_valid,coh_ff_changed_mode;
static int coh_ff_saved_update;
static LONG coh_ff_lease_epoch;
static LONG coh_ff_read(volatile LONG *value)
{return InterlockedCompareExchange(value,0,0);}
static void coh_ff_fail(CohFreshFolderFailure failure)
{(void)InterlockedCompareExchange(&coh_ff_failure,(LONG)failure,0);}
static int coh_ff_lock(void)
{
 LONG state=InterlockedCompareExchange(&coh_ff_guard_state,1,0);
 if(!state){
  if(InitializeCriticalSectionAndSpinCount(&coh_ff_guard,4000))InterlockedExchange(&coh_ff_guard_state,2);
  else InterlockedExchange(&coh_ff_guard_state,3);
 }else while(state==1){SwitchToThread();state=coh_ff_read(&coh_ff_guard_state);}
 if(coh_ff_read(&coh_ff_guard_state)!=2){coh_ff_fail(COH_FRESH_FOLDER_SYNC_FAILED);return 0;}
 EnterCriticalSection(&coh_ff_guard);return 1;
}
static void coh_ff_unlock(void){LeaveCriticalSection(&coh_ff_guard);}
/* The following bookkeeping helpers are called with the guard held. */
static int coh_ff_increment(volatile LONG *value)
{
 LONG previous=coh_ff_read(value);
 if(previous<0||previous>=COH_FRESH_FOLDER_COUNTER_MAX){InterlockedExchange(&coh_ff_accounting_bad,1);coh_ff_fail(COH_FRESH_FOLDER_COUNTER_LIMIT);return 0;}
 InterlockedExchange(value,previous+1);return 1;
}
static void coh_ff_decrement(volatile LONG *value)
{
 LONG previous=coh_ff_read(value);
 if(previous<=0){InterlockedExchange(&coh_ff_accounting_bad,1);coh_ff_fail(COH_FRESH_FOLDER_COUNTER_LIMIT);return;}
 InterlockedExchange(value,previous-1);
}
static int coh_ff_owner_thread(void)
{return threadid&&GetCurrentThreadId()==threadid&&GetCurrentThreadId()==(DWORD)coh_ff_read(&coh_ff_owner);}
static void coh_ff_changed(CohFreshFolderFailure failure)
{coh_ff_fail(failure);(void)coh_ff_increment(&coh_ff_epoch);}
static void coh_fresh_folder_queue_added(void)
{
 if(!coh_ff_lock())return;
 /* Reservation precedes list insertion and lasts through field initialization. */
 (void)coh_ff_increment(&coh_ff_queue_writers);(void)coh_ff_increment(&coh_ff_queue);
 if(coh_ff_read(&coh_ff_sealed))coh_ff_changed(COH_FRESH_FOLDER_QUEUE_CHANGED);
 coh_ff_unlock();
}
static void coh_fresh_folder_queue_add_finished(void)
{if(coh_ff_lock()){coh_ff_decrement(&coh_ff_queue_writers);coh_ff_unlock();}}
static void coh_fresh_folder_queue_removed(void)
{
 if(!coh_ff_lock())return;
 coh_ff_decrement(&coh_ff_queue);
 if(coh_ff_read(&coh_ff_sealed))coh_ff_changed(COH_FRESH_FOLDER_QUEUE_CHANGED);
 coh_ff_unlock();
}
static int FolderCacheUpdate(DirChangeInfo **overrun)
{
 int tracked,result;
 if(!coh_ff_lock())return coh_fresh_original_FolderCacheUpdate(overrun);
 tracked=coh_ff_increment(&coh_ff_updates);
 if(coh_ff_read(&coh_ff_sealed)){
  if(coh_ff_read(&coh_ff_lease))coh_ff_changed(COH_FRESH_FOLDER_ACTIVITY_CHANGED);
  if(tracked)coh_ff_decrement(&coh_ff_updates);
  coh_ff_unlock();return 0;
 }
 coh_ff_unlock();result=coh_fresh_original_FolderCacheUpdate(overrun);
 if(coh_ff_lock()){if(tracked)coh_ff_decrement(&coh_ff_updates);coh_ff_unlock();}
 return result;
}
static void doAllCallbacks(void)
{
 int tracked;
 if(!coh_ff_lock()){coh_fresh_original_doAllCallbacks();return;}
 tracked=coh_ff_increment(&coh_ff_callbacks);
 if(coh_ff_read(&coh_ff_sealed)){
  if(coh_ff_read(&coh_ff_queue)||coh_ff_read(&coh_ff_lease))coh_ff_changed(COH_FRESH_FOLDER_ACTIVITY_CHANGED);
  if(tracked)coh_ff_decrement(&coh_ff_callbacks);
  coh_ff_unlock();return;
 }
 coh_ff_unlock();coh_fresh_original_doAllCallbacks();
 if(coh_ff_lock()){if(tracked)coh_ff_decrement(&coh_ff_callbacks);coh_ff_unlock();}
}
void FolderCacheDoCallbacks(void)
{
 int tracked;
 if(!coh_ff_lock()){coh_fresh_original_FolderCacheDoCallbacks();return;}
 /* Covers original direct manual-mode assignment and pre-inner Query work. */
 tracked=coh_ff_increment(&coh_ff_callbacks);
 if(coh_ff_read(&coh_ff_sealed)){
  if(coh_ff_read(&coh_ff_queue)||coh_ff_read(&coh_ff_lease))coh_ff_changed(COH_FRESH_FOLDER_ACTIVITY_CHANGED);
  if(tracked)coh_ff_decrement(&coh_ff_callbacks);
  coh_ff_unlock();return;
 }
 coh_ff_unlock();coh_fresh_original_FolderCacheDoCallbacks();
 if(coh_ff_lock()){if(tracked)coh_ff_decrement(&coh_ff_callbacks);coh_ff_unlock();}
}
void FolderCacheEnableCallbacks(int enable)
{
 int tracked;
 if(!coh_ff_lock()){coh_fresh_original_FolderCacheEnableCallbacks(enable);return;}
 tracked=coh_ff_increment(&coh_ff_setters);
 if(coh_ff_read(&coh_ff_sealed)&&!(coh_ff_owner_thread()&&coh_ff_read(&coh_ff_private_setter)))coh_ff_changed(COH_FRESH_FOLDER_SETTER_CHANGED);
 else coh_fresh_original_FolderCacheEnableCallbacks(enable);
 if(tracked)coh_ff_decrement(&coh_ff_setters);
 coh_ff_unlock();
}
void FolderCacheSetManualCallbackMode(int on)
{
 int tracked;
 if(!coh_ff_lock()){coh_fresh_original_FolderCacheSetManualCallbackMode(on);return;}
 tracked=coh_ff_increment(&coh_ff_setters);
 if(coh_ff_read(&coh_ff_sealed))coh_ff_changed(COH_FRESH_FOLDER_SETTER_CHANGED);
 else coh_fresh_original_FolderCacheSetManualCallbackMode(on);
 if(tracked)coh_ff_decrement(&coh_ff_setters);
 coh_ff_unlock();
}
static int coh_ff_idle(void)
{
 if(coh_ff_read(&coh_ff_accounting_bad)){coh_ff_fail(COH_FRESH_FOLDER_COUNTER_LIMIT);return 0;}
 /* Must precede every plain mode read: original public poll writes manual_mode
  * outside this guard, but reserves callback depth before starting its body. */
 if(coh_ff_read(&coh_ff_queue_writers)){coh_ff_fail(COH_FRESH_FOLDER_QUEUE_CHANGED);return 0;}
 if(coh_ff_read(&coh_ff_updates)){coh_ff_fail(COH_FRESH_FOLDER_ACTIVE_UPDATE);return 0;}
 if(coh_ff_read(&coh_ff_callbacks)){coh_ff_fail(COH_FRESH_FOLDER_ACTIVE_CALLBACK);return 0;}
 if(coh_ff_read(&coh_ff_setters)){coh_ff_fail(COH_FRESH_FOLDER_ACTIVE_SETTER);return 0;}
 return 1;
}
static int coh_ff_conditions(void)
{
 if(!coh_ff_owner_thread()){coh_ff_fail(COH_FRESH_FOLDER_WRONG_THREAD);return 0;}
 if(!coh_ff_idle())return 0;
 if(folder_cache_manual_callback_check!=1){coh_ff_fail(COH_FRESH_FOLDER_BAD_MANUAL_MODE);return 0;}
 if(folder_cache_update_enable!=0){coh_ff_fail(COH_FRESH_FOLDER_BAD_UPDATE_MODE);return 0;}
 if(coh_ff_read(&coh_ff_queue)){coh_ff_fail(COH_FRESH_FOLDER_QUEUE_NOT_EMPTY);return 0;}
 return !coh_ff_read(&coh_ff_failure);
}
static int coh_ff_restore(void)
{
 /* Caller holds reservation lock through all checks, assignment and unseal. */
 if(!coh_ff_owner_thread()){coh_ff_fail(COH_FRESH_FOLDER_WRONG_THREAD);return 0;}
 if(!coh_ff_idle()){coh_ff_finished=1;return 0;}
 if(coh_ff_changed_mode){
  InterlockedExchange(&coh_ff_private_setter,1);FolderCacheEnableCallbacks(coh_ff_saved_update);
  InterlockedExchange(&coh_ff_private_setter,0);
  if(folder_cache_update_enable!=coh_ff_saved_update){coh_ff_fail(COH_FRESH_FOLDER_RESTORE_FAILED);coh_ff_finished=1;return 0;}
 }
 /* If rejected before reading modes, no original mode was changed. Do not
  * overwrite an in-flight original setter's legitimate result on later abort. */
 coh_ff_restored=1;coh_ff_finished=1;InterlockedExchange(&coh_ff_lease,0);InterlockedExchange(&coh_ff_sealed,0);return 1;
}
int coh_fresh_folder_profile_seal(void)
{
 int result=0;
 if(!coh_ff_lock())return 0;
 if(coh_ff_read(&coh_ff_attempted)){coh_ff_fail(COH_FRESH_FOLDER_REENTRY);coh_ff_unlock();return 0;}
 InterlockedExchange(&coh_ff_attempted,1);InterlockedExchange(&coh_ff_owner,(LONG)GetCurrentThreadId());
 if(!coh_ff_owner_thread()){coh_ff_fail(COH_FRESH_FOLDER_WRONG_THREAD);coh_ff_unlock();return 0;}
 InterlockedExchange(&coh_ff_sealed,1);
 if(!coh_ff_idle()){coh_ff_unlock();return 0;}
 coh_ff_saved_update=folder_cache_update_enable;coh_ff_saved_valid=1;
 if(folder_cache_update_enable!=1)coh_ff_fail(COH_FRESH_FOLDER_BAD_UPDATE_MODE);
 else if(folder_cache_manual_callback_check!=1)coh_ff_fail(COH_FRESH_FOLDER_BAD_MANUAL_MODE);
 else if(coh_ff_read(&coh_ff_queue))coh_ff_fail(COH_FRESH_FOLDER_QUEUE_NOT_EMPTY);
 if(!coh_ff_read(&coh_ff_failure)){
  coh_ff_changed_mode=1;InterlockedExchange(&coh_ff_private_setter,1);FolderCacheEnableCallbacks(0);
  InterlockedExchange(&coh_ff_private_setter,0);result=coh_ff_conditions();
 }
 if(!result)(void)coh_ff_restore();
 coh_ff_unlock();return result;
}
int coh_fresh_folder_profile_begin(void)
{
 int result;
 if(!coh_ff_lock())return 0;
 if(!coh_ff_owner_thread()){coh_ff_fail(COH_FRESH_FOLDER_WRONG_THREAD);coh_ff_unlock();return 0;}
 if(!coh_ff_read(&coh_ff_sealed)||coh_ff_finished||coh_ff_read(&coh_ff_lease)){
  coh_ff_fail(COH_FRESH_FOLDER_REENTRY);coh_ff_unlock();return 0;
 }
 InterlockedExchange(&coh_ff_lease,1);coh_ff_started=1;coh_ff_lease_epoch=coh_ff_read(&coh_ff_epoch);
 result=coh_ff_conditions();coh_ff_unlock();return result;
}
static int coh_ff_check(void)
{
 if(!coh_ff_read(&coh_ff_sealed)||!coh_ff_read(&coh_ff_lease)){coh_ff_fail(COH_FRESH_FOLDER_REENTRY);return 0;}
 if(coh_ff_read(&coh_ff_epoch)!=coh_ff_lease_epoch){coh_ff_fail(COH_FRESH_FOLDER_ACTIVITY_CHANGED);return 0;}
 return coh_ff_conditions();
}
int coh_fresh_folder_profile_check(void)
{int result;if(!coh_ff_lock())return 0;result=coh_ff_check();coh_ff_unlock();return result;}
int coh_fresh_folder_profile_end(void)
{
 int valid,restored;
 if(!coh_ff_lock())return 0;
 valid=coh_ff_check();restored=coh_ff_restore();
 /* No new reservation can cross the check/restore/unseal close point. */
 valid=valid&&restored&&!coh_ff_read(&coh_ff_failure);
 coh_ff_unlock();return valid;
}
void coh_fresh_folder_profile_abort(void)
{if(coh_ff_lock()){if(coh_ff_read(&coh_ff_sealed))(void)coh_ff_restore();coh_ff_unlock();}}
void coh_fresh_folder_profile_view(CohFreshFolderProfileView *out)
{
 if(!out)return;
 memset(out,0,sizeof(*out));
 if(!coh_ff_lock()){out->failure=COH_FRESH_FOLDER_SYNC_FAILED;return;}
 out->seal_attempted=!!coh_ff_read(&coh_ff_attempted);out->sealed=!!coh_ff_read(&coh_ff_sealed);
 out->observation_started=coh_ff_started;out->observation_finished=coh_ff_finished;out->restored=coh_ff_restored;
 out->owner_thread_matched=coh_ff_owner_thread();out->queue_count=(unsigned)coh_ff_read(&coh_ff_queue);
 out->queue_write_depth=(unsigned)coh_ff_read(&coh_ff_queue_writers);out->queue_writers_idle=out->queue_write_depth==0;
 out->update_depth=(unsigned)coh_ff_read(&coh_ff_updates);out->callback_depth=(unsigned)coh_ff_read(&coh_ff_callbacks);
 out->setter_depth=(unsigned)coh_ff_read(&coh_ff_setters);out->setters_idle=out->setter_depth==0;
 out->activity_epoch=(unsigned)coh_ff_read(&coh_ff_epoch);out->queue_empty=out->queue_count==0;
 out->update_idle=out->update_depth==0;out->callbacks_idle=out->callback_depth==0;
 out->epoch_unchanged=coh_ff_started&&out->activity_epoch==(unsigned)coh_ff_lease_epoch;
 out->failure=(CohFreshFolderFailure)coh_ff_read(&coh_ff_failure);coh_ff_unlock();
}
#endif
