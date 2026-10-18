/* NONSHIPPING fresh disposable profile. Included AFTER the unchanged old sink.
 * No private identifiers/paths/pointers are serialized. The caller precreates
 * and owns the private diagnostic file; it is not an authority receipt. */
#ifndef COH_FRESH_SOURCE_PROFILE_INCLUDED
#define COH_FRESH_SOURCE_PROFILE_INCLUDED
#include "../../../libs/UtilitiesLib/src/utils/coh_fresh_source_profile_api.h"
#define COH_FRESH_PROBE_MAX 8192u
static CohGroupsTransactionHooks coh_fresh_original_hooks;
static unsigned coh_fp_installed,coh_fp_seal_entered,coh_fp_entered,coh_fp_accepted,coh_fp_committed;
static unsigned coh_fp_loader_status,coh_fp_loader_released,coh_fp_complete,coh_fp_configured;
static volatile LONG coh_fp_thread;
static unsigned coh_fp_refusal;
static CohFreshOwnerFailure coh_fp_owner_failure;
static CohFreshSourceStage coh_fp_stage;
static char coh_fp_path[COH_CATALOG_SINK_PATH_MAX+1u];
static HANDLE coh_fp_handle=INVALID_HANDLE_VALUE;
static BY_HANDLE_FILE_INFORMATION coh_fp_file_info;
static const char*coh_fp_stages[]={"INSTALL","NORMAL_ENABLE","SEAL","BOUNDARY","QUIET","OWNER","OPEN","CATALOG","RUNTIME","RESOURCES","BOUNDS","ELIGIBILITY","PACKET","QUIET_RELEASE","COMMIT","ABORT"};
static const char*coh_fp_refusals[]={"NONE","NOT_CONFIGURED","WRONG_THREAD","SEAL_REFUSED","BOUNDARY_REFUSED","FINISH_REFUSED","ABORTED","PROBE_IO"};
static const char*coh_fp_failures[]={"NONE","WRONG_THREAD","REENTRY","BAD_UPDATE_MODE","BAD_MANUAL_MODE","QUEUE_NOT_EMPTY","ACTIVE_UPDATE","ACTIVE_CALLBACK","ACTIVE_SETTER","QUEUE_CHANGED","SETTER_CHANGED","ACTIVITY_CHANGED","COUNTER_LIMIT","RESTORE_FAILED","SYNC_FAILED"};
static const char*coh_fp_owner_failures[]={"NONE",
#define COH_FRESH_OWNER_NAME(name,expression) #name,
 COH_FRESH_OWNER_PREDICATES(COH_FRESH_OWNER_NAME)
#undef COH_FRESH_OWNER_NAME
#define COH_FRESH_INITIAL_OWNER_NAME(name) #name,
 COH_FRESH_INITIAL_OWNER_FAILURES(COH_FRESH_INITIAL_OWNER_NAME)
#undef COH_FRESH_INITIAL_OWNER_NAME
};
static int coh_fp_owner(void){LONG owner=InterlockedCompareExchange(&coh_fp_thread,0,0);return owner&&GetCurrentThreadId()==(DWORD)owner;}
int coh_fresh_source_owner_failed(int refused,CohFreshOwnerFailure reason)
{
 /* Observe the original result once, in its original short-circuit position.
  * No file I/O, original-object reread, callback or allocation occurs here.
  * One fresh observation only; later cleanup cannot replace its first cause. */
 if(refused&&coh_fp_owner()&&coh_fp_entered&&!coh_fp_complete
  &&coh_fp_owner_failure==COH_FRESH_OWNER_NONE
  &&reason>COH_FRESH_OWNER_NONE&&reason<COH_FRESH_OWNER_COUNT)coh_fp_owner_failure=reason;
 return refused;
}
static const char*coh_fp_bool(unsigned v){return v?"true":"false";}
static void coh_fp_refuse(unsigned refusal){if(!coh_fp_refusal)coh_fp_refusal=refusal;}
static int coh_fp_file_valid(BY_HANDLE_FILE_INFORMATION*info)
{
 return !(info->dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))&&info->nNumberOfLinks==1u;
}
static int coh_fp_open(void)
{
 BY_HANDLE_FILE_INFORMATION info;DWORD attrs;
 attrs=GetFileAttributesA(coh_fp_path);
 if(attrs==INVALID_FILE_ATTRIBUTES||(attrs&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)))return 0;
 coh_fp_handle=CreateFileA(coh_fp_path,GENERIC_WRITE,0,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
 if(coh_fp_handle==INVALID_HANDLE_VALUE)return 0;
 if(!GetFileInformationByHandle(coh_fp_handle,&info)||!coh_fp_file_valid(&info)||info.nFileSizeHigh||info.nFileSizeLow){
  (void)CloseHandle(coh_fp_handle);coh_fp_handle=INVALID_HANDLE_VALUE;return 0;
 }
 coh_fp_file_info=info;return 1;
}
static int coh_fp_same_file(void)
{
 BY_HANDLE_FILE_INFORMATION info;
 return coh_fp_handle!=INVALID_HANDLE_VALUE&&GetFileInformationByHandle(coh_fp_handle,&info)&&coh_fp_file_valid(&info)
  &&info.dwVolumeSerialNumber==coh_fp_file_info.dwVolumeSerialNumber
  &&info.nFileIndexHigh==coh_fp_file_info.nFileIndexHigh&&info.nFileIndexLow==coh_fp_file_info.nFileIndexLow;
}
static int coh_fp_write(void)
{
 CohFreshFolderProfileView v;DWORD written=0;LARGE_INTEGER zero;char raw[COH_FRESH_PROBE_MAX];int n;unsigned ok;
 if(!coh_fp_owner())return 0;
 if(!coh_fp_path[0])return 0;
 coh_fresh_folder_profile_view(&v);
 if((unsigned)coh_fp_stage>=sizeof(coh_fp_stages)/sizeof(coh_fp_stages[0])||coh_fp_refusal>=sizeof(coh_fp_refusals)/sizeof(coh_fp_refusals[0])||(unsigned)v.failure>=sizeof(coh_fp_failures)/sizeof(coh_fp_failures[0])||(unsigned)coh_fp_owner_failure>=COH_FRESH_OWNER_COUNT)return 0;
 n=snprintf(raw,sizeof(raw),"{\"schema\":\"coh-fresh-source-profile-probe-v2\",\"complete\":%s,\"stage\":\"%s\",\"refusal\":\"%s\",\"loader_status\":%u,\"loader_released\":%s,\"installer_entered\":%s,\"sink_configured\":%s,\"installation_thread_matched\":%s,\"seal_hook_entered\":%s,\"boundary_entered\":%s,\"boundary_accepted\":%s,\"envelope_committed\":%s,\"seal_attempted\":%s,\"sealed\":%s,\"observation_started\":%s,\"observation_finished\":%s,\"restored\":%s,\"owner_thread_matched\":%s,\"queue_empty\":%s,\"queue_writers_idle\":%s,\"update_idle\":%s,\"callbacks_idle\":%s,\"setters_idle\":%s,\"epoch_unchanged\":%s,\"queue_count\":%u,\"queue_write_depth\":%u,\"update_depth\":%u,\"callback_depth\":%u,\"setter_depth\":%u,\"activity_epoch\":%u,\"folder_failure\":\"%s\",\"owner_failure\":\"%s\",\"diagnostic_only\":true,\"source_generation_admitted\":false,\"world_authority\":false}\n",
 coh_fp_bool(coh_fp_complete),coh_fp_stages[coh_fp_stage],coh_fp_refusals[coh_fp_refusal],coh_fp_loader_status,coh_fp_bool(coh_fp_loader_released),coh_fp_bool(coh_fp_installed),coh_fp_bool(coh_groups_capture_file.configured),coh_fp_bool(GetCurrentThreadId()==coh_groups_capture_file.thread),coh_fp_bool(coh_fp_seal_entered),coh_fp_bool(coh_fp_entered),coh_fp_bool(coh_fp_accepted),coh_fp_bool(coh_fp_committed),coh_fp_bool(v.seal_attempted),coh_fp_bool(v.sealed),coh_fp_bool(v.observation_started),coh_fp_bool(v.observation_finished),coh_fp_bool(v.restored),coh_fp_bool(v.owner_thread_matched),coh_fp_bool(v.queue_empty),coh_fp_bool(v.queue_writers_idle),coh_fp_bool(v.update_idle),coh_fp_bool(v.callbacks_idle),coh_fp_bool(v.setters_idle),coh_fp_bool(v.epoch_unchanged),v.queue_count,v.queue_write_depth,v.update_depth,v.callback_depth,v.setter_depth,v.activity_epoch,coh_fp_failures[v.failure],coh_fp_owner_failures[coh_fp_owner_failure]);
 if(n<=0||(unsigned)n>=sizeof(raw))return 0;
 /* Same admitted handle throughout. A replaced path is never reopened or
  * overwritten; host collection independently refuses its changed identity. */
 if(!coh_fp_same_file())return 0;
 zero.QuadPart=0;
 ok=SetFilePointerEx(coh_fp_handle,zero,NULL,FILE_BEGIN)
  &&WriteFile(coh_fp_handle,raw,(DWORD)n,&written,NULL)&&written==(DWORD)n
  &&SetEndOfFile(coh_fp_handle)&&FlushFileBuffers(coh_fp_handle)&&coh_fp_same_file();
 return (int)ok;
}
static void coh_fp_flush(void)
{
 if(!coh_fp_owner())return;
 if(coh_fp_configured&&!coh_fp_write())coh_fp_refuse(7);
 if(coh_fp_complete&&coh_fp_handle!=INVALID_HANDLE_VALUE){
  if(!CloseHandle(coh_fp_handle))coh_fp_refuse(7);
  coh_fp_handle=INVALID_HANDLE_VALUE;
 }
}
void coh_fresh_source_probe_step(CohFreshSourceStage stage)
{if(!coh_fp_owner())return;coh_fp_stage=stage;coh_fp_flush();}
void coh_fresh_source_probe_loader(unsigned status,unsigned released)
{if(!coh_fp_owner())return;coh_fp_loader_status=status>8u?8u:status;coh_fp_loader_released=!!released;coh_fp_flush();}
static unsigned coh_fp_begin(void*context,const NetLink*link,int full)
{
 unsigned id;
 if(!coh_fp_owner())return 0;
 if(full!=1)return coh_fresh_original_hooks.begin(context,link,full);
 if(coh_fp_entered)return 0;
 coh_fp_entered=1;coh_fresh_source_probe_step(COH_FRESH_STAGE_BOUNDARY);
 id=coh_fresh_original_hooks.begin(context,link,full);
 coh_fp_accepted=!!id;
 if(!id){coh_fp_complete=1;coh_fp_refuse(4);coh_fresh_folder_profile_abort();}
 coh_fp_flush();return id;
}
static int coh_fp_finish(void*context,unsigned id,const unsigned char*raw,unsigned bits,unsigned aligned,unsigned compress,const CohGroupsEligibilityReport*report)
{
 int ok;
 if(!coh_fp_owner())return 0;
 ok=coh_fresh_original_hooks.finish(context,id,raw,bits,aligned,compress,report);
 if(ok){coh_fp_committed=1;coh_fp_complete=1;coh_fp_stage=COH_FRESH_STAGE_COMMIT;}
 else coh_fp_refuse(5);
 coh_fp_flush();return ok;
}
static void coh_fp_abort(void*context,unsigned id)
{
 if(!coh_fp_owner())return;
 coh_fresh_original_hooks.abort(context,id);
 /* Original end may already have retired real loader locks on refusal. Retry
  * ONLY folder restoration here, never another real critical-section leave. */
 coh_fresh_folder_profile_abort();coh_fp_complete=1;coh_fp_refuse(6);coh_fp_flush();
}
void coh_fresh_source_profile_install(void)
{
 DWORD n,thread=GetCurrentThreadId();LONG previous;
 if(!thread)return;
 previous=InterlockedCompareExchange(&coh_fp_thread,(LONG)thread,0);
 if(previous&&(DWORD)previous!=thread)return;
 if(coh_fp_installed)return;
 coh_fp_installed=1;coh_fp_stage=COH_FRESH_STAGE_INSTALL;
 n=GetEnvironmentVariableA("COH_NATIVE_GROUPS_PROFILE_PROBE_OUTPUT",coh_fp_path,sizeof(coh_fp_path));
 if(n&&n<sizeof(coh_fp_path)&&coh_catalog_sink_path(coh_fp_path,n)){coh_fp_configured=1;if(!coh_fp_open())coh_fp_refuse(7);}
 else coh_fp_path[0]=0;
 coh_source_groups_capture_install();
 if(!coh_groups_capture_file.configured||coh_groups_capture_file.thread!=(DWORD)coh_fp_thread){coh_fp_refuse(1);coh_fp_complete=1;coh_fp_flush();return;}
 coh_fresh_original_hooks=coh_groups_transaction_hooks;
 coh_groups_transaction_hooks.begin=coh_fp_begin;coh_groups_transaction_hooks.finish=coh_fp_finish;coh_groups_transaction_hooks.abort=coh_fp_abort;
 coh_fp_flush();
}
void coh_fresh_source_profile_seal_after_normal_enable(void)
{
 if(!coh_fp_owner())return;
 coh_fp_seal_entered=1;coh_fp_stage=COH_FRESH_STAGE_NORMAL_ENABLE;
 if(!coh_groups_capture_file.configured){coh_fp_refuse(1);coh_fp_complete=1;coh_fp_flush();return;}
 if(GetCurrentThreadId()!=(DWORD)coh_fp_thread||coh_groups_capture_file.thread!=(DWORD)coh_fp_thread){coh_fp_refuse(2);coh_fp_complete=1;coh_fp_flush();return;}
 coh_fp_stage=COH_FRESH_STAGE_SEAL;
 if(!coh_fresh_folder_profile_seal()){coh_fp_refuse(3);coh_fp_complete=1;coh_fresh_folder_profile_abort();}
 coh_fp_flush();
}
#endif
