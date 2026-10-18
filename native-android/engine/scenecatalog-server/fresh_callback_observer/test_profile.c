/* New probe code + exact old loader guard, source-shaped FolderCache fixtures.
 * Real host threads/mutexes; no original server, PG, Wine or runtime capture. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <sched.h>
#include <string.h>
typedef int32_t LONG;
typedef uint32_t DWORD;
typedef struct DirChangeInfo {unsigned unused;} DirChangeInfo;
static _Thread_local DWORD test_thread=1;
static DWORD GetCurrentThreadId(void){return test_thread;}
static LONG InterlockedCompareExchange(volatile LONG*p,LONG desired,LONG expected)
{LONG previous=expected;(void)__atomic_compare_exchange_n(p,&previous,desired,0,__ATOMIC_SEQ_CST,__ATOMIC_SEQ_CST);return previous;}
static LONG InterlockedExchange(volatile LONG*p,LONG desired)
{return __atomic_exchange_n(p,desired,__ATOMIC_SEQ_CST);}
static unsigned checks,scenarios;
#define CHECK(v) do{(void)__atomic_add_fetch(&checks,1,__ATOMIC_RELAXED);if(!(v)){fprintf(stderr,"probe control failed at%d\n",__LINE__);assert(v);}}while(0)
typedef struct {pthread_mutex_t mutex;unsigned locks,leaves;} CRITICAL_SECTION;

static unsigned test_initialize_fail;
static int InitializeCriticalSectionAndSpinCount(CRITICAL_SECTION*lock,unsigned spins)
{pthread_mutexattr_t attr;if(test_initialize_fail)return 0;(void)spins;CHECK(!pthread_mutexattr_init(&attr));CHECK(!pthread_mutexattr_settype(&attr,PTHREAD_MUTEX_RECURSIVE));
 CHECK(!pthread_mutex_init(&lock->mutex,&attr));CHECK(!pthread_mutexattr_destroy(&attr));return 1;}
static void EnterCriticalSection(CRITICAL_SECTION*lock)
{CHECK(!pthread_mutex_lock(&lock->mutex));lock->locks++;}
static void SwitchToThread(void){(void)sched_yield();}
static int TryEnterCriticalSection(CRITICAL_SECTION*lock)
{if(pthread_mutex_trylock(&lock->mutex))return 0;lock->locks++;return 1;}
static void LeaveCriticalSection(CRITICAL_SECTION*lock)
{lock->leaves++;CHECK(!pthread_mutex_unlock(&lock->mutex));}
static CRITICAL_SECTION heyThreadLoadAGeo_CriticalSection,heyThreadLODAModel_CriticalSection;
static DWORD threadid=1;
static int folder_cache_update_enable=1,folder_cache_manual_callback_check=1;
static unsigned original_updates,original_callbacks,original_polls,fail_restore,fail_disable;
static unsigned fake_nodes;
#define COH_FRESH_FOLDER_IMPLEMENTATION
#include "coh_fresh_folder_profile_api.h"
static pthread_mutex_t transition_gate=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t transition_changed=PTHREAD_COND_INITIALIZER;
static unsigned pause_setter,pause_poll,original_entered,allow_original,contender_started,transition_result;
static void pause_original(unsigned enabled)
{
 if(!enabled)return;
 CHECK(!pthread_mutex_lock(&transition_gate));original_entered=1;CHECK(!pthread_cond_broadcast(&transition_changed));
 while(!allow_original)CHECK(!pthread_cond_wait(&transition_changed,&transition_gate));
 CHECK(!pthread_mutex_unlock(&transition_gate));
}
static int coh_fresh_original_FolderCacheUpdate(DirChangeInfo **overrun)
{(void)overrun;if(GetCurrentThreadId()!=threadid||!folder_cache_update_enable)return 0;original_updates++;return 0;}
static void coh_fresh_original_doAllCallbacks(void)
{original_callbacks++;while(fake_nodes){fake_nodes--;coh_fresh_folder_queue_removed();}}
static void coh_fresh_original_FolderCacheDoCallbacks(void)
{original_polls++;pause_original(pause_poll);folder_cache_manual_callback_check=1;(void)FolderCacheUpdate(NULL);doAllCallbacks();}
static void coh_fresh_original_FolderCacheEnableCallbacks(int enable)
{pause_original(pause_setter==(unsigned)(enable+1));if(!(fail_restore&&enable==1)&&!(fail_disable&&enable==0))folder_cache_update_enable=enable;}
static void coh_fresh_original_FolderCacheSetManualCallbackMode(int on)
{folder_cache_manual_callback_check=on;}
#include "coh_fresh_folder_profile.inc"
static int initedBackgroundLoader=1,number_of_glds_in_background_loader;
static int number_of_lods_in_background_loader,glds_ready_for_final_processing;
static DWORD background_loader_threadID=99;
static unsigned coh_fp_loader_status,coh_fp_loader_released;
static volatile LONG coh_fp_thread;
#define loader_status coh_fp_loader_status
#define loader_released coh_fp_loader_released
#define SERVER 1
#define _WIN32 1
#include "coh_resource_quiescence.inc"
static void reset(void)
{
 volatile LONG*values[]={&coh_ff_queue,&coh_ff_queue_writers,&coh_ff_updates,&coh_ff_callbacks,&coh_ff_setters,
  &coh_ff_epoch,&coh_ff_failure,&coh_ff_attempted,&coh_ff_sealed,&coh_ff_lease,&coh_ff_private_setter,&coh_ff_owner,&coh_ff_accounting_bad};
 for(unsigned i=0;i<sizeof(values)/sizeof(values[0]);i++)(void)InterlockedExchange(values[i],0);
 coh_ff_started=coh_ff_finished=coh_ff_restored=coh_ff_saved_valid=coh_ff_changed_mode=0;coh_ff_saved_update=0;coh_ff_lease_epoch=0;
 test_thread=threadid=1;InterlockedExchange(&coh_fp_thread,1);folder_cache_update_enable=folder_cache_manual_callback_check=1;
 original_updates=original_callbacks=original_polls=fail_restore=fail_disable=fake_nodes=0;
 pause_setter=pause_poll=original_entered=allow_original=contender_started=transition_result=0;
 initedBackgroundLoader=1;number_of_glds_in_background_loader=number_of_lods_in_background_loader=glds_ready_for_final_processing=0;
 loader_status=loader_released=0;coh_resource_quiet_active=coh_resource_quiet_owner=0;
 heyThreadLoadAGeo_CriticalSection.locks=heyThreadLoadAGeo_CriticalSection.leaves=0;
 heyThreadLODAModel_CriticalSection.locks=heyThreadLODAModel_CriticalSection.leaves=0;
}
static CohFreshFolderProfileView view(void)
{CohFreshFolderProfileView value;coh_fresh_folder_profile_view(&value);return value;}
static void enqueue(void)
{coh_fresh_folder_queue_added();fake_nodes++;coh_fresh_folder_queue_add_finished();}
static void ordinary(void)
{
 reset();enqueue();enqueue();CHECK(coh_ff_read(&coh_ff_queue)==2);
 FolderCacheDoCallbacks();CHECK(!fake_nodes&&!coh_ff_read(&coh_ff_queue));
 CHECK(original_updates==1&&original_callbacks==1&&original_polls==1);
 FolderCacheEnableCallbacks(0);CHECK(folder_cache_update_enable==0);FolderCacheEnableCallbacks(1);
 FolderCacheSetManualCallbackMode(0);CHECK(!folder_cache_manual_callback_check);FolderCacheSetManualCallbackMode(1);
 CHECK(!view().seal_attempted&&view().failure==COH_FRESH_FOLDER_NONE);scenarios++;
}
static void success(void)
{
 reset();CHECK(coh_fresh_folder_profile_seal());CHECK(!folder_cache_update_enable&&view().sealed);
 for(unsigned i=0;i<3;i++)FolderCacheDoCallbacks();
 CHECK(!original_updates&&!original_callbacks&&!original_polls&&view().failure==COH_FRESH_FOLDER_NONE);
 CHECK(coh_resource_quiescence_begin()==1);CHECK(loader_status==1&&!loader_released);
 CHECK(view().observation_started&&view().queue_empty&&view().queue_writers_idle&&view().setters_idle);
 CHECK(coh_resource_quiescence_end()==1);CHECK(loader_released&&view().restored&&!view().sealed);
 CHECK(view().observation_finished&&view().epoch_unchanged&&folder_cache_update_enable==1);
 CHECK(heyThreadLoadAGeo_CriticalSection.locks==1&&heyThreadLoadAGeo_CriticalSection.leaves==1);
 CHECK(heyThreadLODAModel_CriticalSection.locks==1&&heyThreadLODAModel_CriticalSection.leaves==1);
 CHECK(!coh_resource_quiescence_end());CHECK(!coh_fresh_folder_profile_seal());scenarios++;
}
static void rejected_seal(unsigned which)
{
 reset();
 if(which==0)threadid=2;
 else if(which==1)folder_cache_update_enable=0;
 else if(which==2)folder_cache_manual_callback_check=0;
 else if(which==3)enqueue();
 else if(which==4)(void)InterlockedExchange(&coh_ff_updates,1);
 else if(which==5)(void)InterlockedExchange(&coh_ff_callbacks,1);
 else if(which==6)(void)InterlockedExchange(&coh_ff_setters,1);
 else (void)InterlockedExchange(&coh_ff_failure,COH_FRESH_FOLDER_COUNTER_LIMIT);
 CHECK(!coh_fresh_folder_profile_seal());CHECK(view().failure!=COH_FRESH_FOLDER_NONE);
 CHECK(!view().observation_started);CHECK(!coh_resource_quiet_active);
 if(which>=4&&which<=6){
  CHECK(folder_cache_update_enable==1&&view().sealed);
  InterlockedExchange(&coh_ff_updates,0);InterlockedExchange(&coh_ff_callbacks,0);InterlockedExchange(&coh_ff_setters,0);
  coh_fresh_folder_profile_abort();CHECK(!view().sealed&&view().restored);
 }else if(which>=3)CHECK(folder_cache_update_enable==1&&!view().sealed);
 if(which==1)CHECK(folder_cache_update_enable==0);
 scenarios++;
}
static void activity(unsigned which)
{
 reset();CHECK(coh_fresh_folder_profile_seal());CHECK(coh_resource_quiescence_begin()==1);
 if(which==0)(void)FolderCacheUpdate(NULL);
 else if(which==1)doAllCallbacks();
 else if(which==2)FolderCacheDoCallbacks();
 else if(which==3)FolderCacheEnableCallbacks(1);
 else if(which==4)FolderCacheSetManualCallbackMode(0);
 else if(which==5)enqueue();
 else (void)InterlockedExchange(&coh_ff_epoch,1);
 CHECK(!coh_fresh_folder_profile_check());CHECK(!coh_resource_quiescence_end());
 CHECK(!coh_resource_quiet_active&&view().restored&&folder_cache_update_enable==1);
 CHECK(!original_updates&&!original_callbacks&&!original_polls);
 CHECK(heyThreadLoadAGeo_CriticalSection.leaves==1&&heyThreadLODAModel_CriticalSection.leaves==1);
 CHECK(!coh_resource_quiescence_end());scenarios++;
}
static void loader_refusal(unsigned which)
{
 reset();CHECK(coh_fresh_folder_profile_seal());
 if(which==0)initedBackgroundLoader=0;
 else if(which==1)coh_resource_quiet_active=1;
 else if(which==2)background_loader_threadID=1;
 else if(which==3)number_of_glds_in_background_loader=1;
 else if(which==4)number_of_lods_in_background_loader=1;
 else glds_ready_for_final_processing=1;
 CHECK(coh_resource_quiescence_begin()!=1);CHECK(view().restored&&folder_cache_update_enable==1);
 CHECK(!view().sealed);CHECK(heyThreadLoadAGeo_CriticalSection.locks==heyThreadLoadAGeo_CriticalSection.leaves);
 CHECK(heyThreadLODAModel_CriticalSection.locks==heyThreadLODAModel_CriticalSection.leaves);
 background_loader_threadID=99;scenarios++;
}
static pthread_mutex_t gate=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed=PTHREAD_COND_INITIALIZER;
static unsigned entered,released;
static void wait_gate(unsigned*condition)
{while(!*condition)CHECK(!pthread_cond_wait(&changed,&gate));}
static void*writer(void*unused)
{
 (void)unused;test_thread=2;coh_fresh_folder_queue_added();
 CHECK(!pthread_mutex_lock(&gate));entered=1;CHECK(!pthread_cond_broadcast(&changed));wait_gate(&released);CHECK(!pthread_mutex_unlock(&gate));
 fake_nodes++;coh_fresh_folder_queue_add_finished();return NULL;
}
static void threaded_writer(void)
{
 pthread_t thread;reset();entered=released=0;CHECK(coh_fresh_folder_profile_seal());CHECK(coh_resource_quiescence_begin()==1);
 CHECK(!pthread_create(&thread,NULL,writer,NULL));CHECK(!pthread_mutex_lock(&gate));wait_gate(&entered);CHECK(!pthread_mutex_unlock(&gate));
 CHECK(view().queue_count==1&&view().queue_write_depth==1&&!view().queue_writers_idle);
 CHECK(!coh_resource_quiescence_end());CHECK(!coh_resource_quiet_active&&view().sealed&&!view().restored);
 FolderCacheDoCallbacks();CHECK(!original_callbacks&&!original_polls);
 CHECK(!pthread_mutex_lock(&gate));released=1;CHECK(!pthread_cond_broadcast(&changed));CHECK(!pthread_mutex_unlock(&gate));
 CHECK(!pthread_join(thread,NULL));coh_fresh_folder_profile_abort();CHECK(view().restored&&!view().sealed);
 CHECK(heyThreadLoadAGeo_CriticalSection.leaves==1&&heyThreadLODAModel_CriticalSection.leaves==1);
 FolderCacheDoCallbacks();CHECK(!fake_nodes&&!view().queue_count);scenarios++;
}
static void*foreign(void*unused)
{
 (void)unused;test_thread=2;
 CHECK(!coh_fresh_folder_profile_check());CHECK(!coh_resource_quiescence_end());CHECK(view().owner_thread_matched==0);
 FolderCacheEnableCallbacks(1);(void)FolderCacheUpdate(NULL);doAllCallbacks();return NULL;
}
static void threaded_foreign(void)
{
 pthread_t thread;reset();CHECK(coh_fresh_folder_profile_seal());CHECK(coh_resource_quiescence_begin()==1);
 CHECK(!pthread_create(&thread,NULL,foreign,NULL));CHECK(!pthread_join(thread,NULL));
 CHECK(!original_updates&&!original_callbacks);CHECK(coh_resource_quiet_active);
 CHECK(!coh_resource_quiescence_end());CHECK(view().restored&&!coh_resource_quiet_active);scenarios++;
}
static void transition_wait(unsigned*flag)
{CHECK(!pthread_mutex_lock(&transition_gate));while(!*flag)CHECK(!pthread_cond_wait(&transition_changed,&transition_gate));CHECK(!pthread_mutex_unlock(&transition_gate));}
static void transition_release(void)
{CHECK(!pthread_mutex_lock(&transition_gate));allow_original=1;CHECK(!pthread_cond_broadcast(&transition_changed));CHECK(!pthread_mutex_unlock(&transition_gate));}
static void*paused_setter(void*unused)
{(void)unused;test_thread=2;FolderCacheEnableCallbacks(0);return NULL;}
static void*paused_poll(void*unused)
{(void)unused;test_thread=2;FolderCacheDoCallbacks();return NULL;}
static void*seal_contender(void*unused)
{
 (void)unused;test_thread=1;CHECK(!pthread_mutex_lock(&transition_gate));contender_started=1;
 CHECK(!pthread_cond_broadcast(&transition_changed));CHECK(!pthread_mutex_unlock(&transition_gate));
 transition_result=(unsigned)coh_fresh_folder_profile_seal();return NULL;
}
static void*end_owner(void*unused)
{(void)unused;test_thread=1;transition_result=(unsigned)coh_fresh_folder_profile_end();return NULL;}
static void*late_writer(void*unused)
{
 (void)unused;test_thread=2;CHECK(!pthread_mutex_lock(&transition_gate));contender_started=1;
 CHECK(!pthread_cond_broadcast(&transition_changed));CHECK(!pthread_mutex_unlock(&transition_gate));
 coh_fresh_folder_queue_added();fake_nodes++;coh_fresh_folder_queue_add_finished();return NULL;
}
static void paused_setter_seal(void)
{
 pthread_t setter,owner;reset();pause_setter=1;
 CHECK(!pthread_create(&setter,NULL,paused_setter,NULL));transition_wait(&original_entered);
 CHECK(!pthread_create(&owner,NULL,seal_contender,NULL));transition_wait(&contender_started);
 /* Setter owns the guard through its original plain assignment. Seal cannot
  * inspect a stale mode or restore1 ahead of the paused assignment0. */
 transition_release();CHECK(!pthread_join(setter,NULL));CHECK(!pthread_join(owner,NULL));
 CHECK(!transition_result&&folder_cache_update_enable==0&&!view().sealed);
 CHECK(view().failure==COH_FRESH_FOLDER_BAD_UPDATE_MODE&&view().restored);scenarios++;
}
static void paused_poll_seal(void)
{
 pthread_t poll;reset();folder_cache_manual_callback_check=0;pause_poll=1;
 CHECK(!pthread_create(&poll,NULL,paused_poll,NULL));transition_wait(&original_entered);
 CHECK(!coh_fresh_folder_profile_seal());CHECK(view().callback_depth==1&&view().sealed);
 coh_fresh_folder_profile_abort();CHECK(view().sealed&&!view().restored);
 transition_release();CHECK(!pthread_join(poll,NULL));coh_fresh_folder_profile_abort();
 CHECK(!view().sealed&&view().restored&&folder_cache_update_enable==1&&folder_cache_manual_callback_check==1);
 CHECK(view().failure==COH_FRESH_FOLDER_ACTIVE_CALLBACK&&original_polls==1&&!original_updates&&!original_callbacks);scenarios++;
}
static void queue_after_close(void)
{
 pthread_t owner,queue;reset();CHECK(coh_fresh_folder_profile_seal());CHECK(coh_fresh_folder_profile_begin());pause_setter=2;
 CHECK(!pthread_create(&owner,NULL,end_owner,NULL));transition_wait(&original_entered);
 CHECK(!pthread_create(&queue,NULL,late_writer,NULL));transition_wait(&contender_started);
 /* Writer is waiting at reservation; it can enter only after end atomically
  * restores/unseals. That later work is outside the point-snapshot interval. */
 transition_release();CHECK(!pthread_join(owner,NULL));CHECK(!pthread_join(queue,NULL));
 CHECK(transition_result&&view().restored&&!view().sealed&&view().failure==COH_FRESH_FOLDER_NONE);
 CHECK(view().queue_count==1&&view().queue_writers_idle&&view().epoch_unchanged);
 pause_setter=0;FolderCacheDoCallbacks();CHECK(!fake_nodes&&!view().queue_count);scenarios++;
}
static void limit_and_restore(void)
{
 reset();(void)InterlockedExchange(&coh_ff_queue,COH_FRESH_FOLDER_COUNTER_MAX);coh_fresh_folder_queue_added();
 CHECK(coh_ff_read(&coh_ff_queue)==COH_FRESH_FOLDER_COUNTER_MAX);CHECK(!coh_fresh_folder_profile_seal());
 reset();CHECK(coh_fresh_folder_profile_seal());CHECK(coh_resource_quiescence_begin()==1);
 (void)InterlockedExchange(&coh_ff_epoch,COH_FRESH_FOLDER_COUNTER_MAX);FolderCacheDoCallbacks();
 CHECK(view().activity_epoch==COH_FRESH_FOLDER_COUNTER_MAX);CHECK(!coh_resource_quiescence_end());CHECK(!view().restored&&view().sealed);
 reset();CHECK(coh_fresh_folder_profile_seal());CHECK(coh_resource_quiescence_begin()==1);fail_restore=1;
 CHECK(!coh_resource_quiescence_end());CHECK(!view().restored&&view().sealed&&!coh_resource_quiet_active);
 CHECK(view().failure==COH_FRESH_FOLDER_RESTORE_FAILED);scenarios++;
}
static void masked_accounting_loss(void)
{
 reset();coh_ff_fail(COH_FRESH_FOLDER_SETTER_CHANGED);InterlockedExchange(&coh_ff_updates,COH_FRESH_FOLDER_COUNTER_MAX);
 (void)FolderCacheUpdate(NULL);CHECK(original_updates==1&&coh_ff_read(&coh_ff_accounting_bad));
 InterlockedExchange(&coh_ff_updates,0);CHECK(!coh_fresh_folder_profile_seal());
 CHECK(view().sealed&&!view().restored&&view().failure==COH_FRESH_FOLDER_SETTER_CHANGED);
 coh_fresh_folder_profile_abort();CHECK(view().sealed&&!view().restored);
 reset();CHECK(coh_fresh_folder_profile_seal());CHECK(coh_fresh_folder_profile_begin());
 FolderCacheEnableCallbacks(1);CHECK(view().failure==COH_FRESH_FOLDER_SETTER_CHANGED);
 CHECK(coh_ff_lock());coh_ff_decrement(&coh_ff_queue);coh_ff_unlock();
 CHECK(!coh_fresh_folder_profile_end()&&view().sealed&&!view().restored&&coh_ff_read(&coh_ff_accounting_bad));scenarios++;
}
/* Fixed probe emitter qualification uses bounded Win32 I/O stubs and source-
 * shaped hooks. It is not original worldSendUpdate or an actual source sink. */
typedef unsigned NetLink;
typedef unsigned CohGroupsEligibilityReport;
typedef struct {
 unsigned (*begin)(void*,const NetLink*,int);void*record;
 int (*finish)(void*,unsigned,const unsigned char*,unsigned,unsigned,unsigned,const CohGroupsEligibilityReport*);
 void (*abort)(void*,unsigned);void*context;
} CohGroupsTransactionHooks;
static CohGroupsTransactionHooks coh_groups_transaction_hooks;
static struct {unsigned configured,thread;}coh_groups_capture_file;
typedef intptr_t HANDLE;
#define INVALID_HANDLE_VALUE ((HANDLE)-1)
#define INVALID_FILE_ATTRIBUTES ((DWORD)-1)
#define FILE_ATTRIBUTE_DIRECTORY 16u
#define FILE_ATTRIBUTE_REPARSE_POINT 1024u
#define GENERIC_WRITE 1u
#define OPEN_EXISTING 3u
#define FILE_ATTRIBUTE_NORMAL 128u
#define FILE_FLAG_OPEN_REPARSE_POINT 0x00200000u
#define FILE_BEGIN 0u
typedef struct {int64_t QuadPart;} LARGE_INTEGER;
typedef struct {DWORD dwFileAttributes,nNumberOfLinks,nFileSizeHigh,nFileSizeLow,dwVolumeSerialNumber,nFileIndexHigh,nFileIndexLow;} BY_HANDLE_FILE_INFORMATION;
#define COH_CATALOG_SINK_PATH_MAX 1024u
static unsigned fake_sink_config=1,fake_probe_env=1,fake_io_fault,fake_opens,fake_closes;
static unsigned fake_source_opens,fake_source_commits,fake_source_aborts;
static unsigned fake_handle_changed,fake_path_replaced;
static char replacement_bytes[64];
static char probe_bytes[8192];
static DWORD GetEnvironmentVariableA(const char*name,char*out,unsigned n)
{const char*value="C:\\private\\probe.json";(void)name;if(!fake_probe_env)return 0;CHECK(strlen(value)+1<n);memcpy(out,value,strlen(value)+1);return (DWORD)strlen(value);}
static int coh_catalog_sink_path(char*path,unsigned n){return path&&n>3;}
static DWORD GetFileAttributesA(const char*path)
{(void)path;return fake_io_fault==1?INVALID_FILE_ATTRIBUTES:fake_io_fault==2?FILE_ATTRIBUTE_REPARSE_POINT:FILE_ATTRIBUTE_NORMAL;}
static HANDLE CreateFileA(const char*p,unsigned a,unsigned b,void*c,unsigned mode,unsigned flags,void*d)
{(void)p;(void)a;(void)b;(void)c;(void)d;CHECK(mode==OPEN_EXISTING&&!!(flags&FILE_FLAG_OPEN_REPARSE_POINT));if(fake_io_fault==3)return INVALID_HANDLE_VALUE;fake_opens++;return 1;}
static int GetFileInformationByHandle(HANDLE h,BY_HANDLE_FILE_INFORMATION*info)
{(void)h;if(fake_io_fault==9)return 0;memset(info,0,sizeof(*info));info->dwFileAttributes=FILE_ATTRIBUTE_NORMAL;info->nNumberOfLinks=fake_io_fault==10?2:1;info->dwVolumeSerialNumber=7;info->nFileIndexLow=42+fake_handle_changed;return 1;}
static int SetFilePointerEx(HANDLE h,LARGE_INTEGER zero,void*out,unsigned mode)
{(void)h;(void)out;CHECK(!zero.QuadPart&&mode==FILE_BEGIN);return fake_io_fault!=11;}
static int WriteFile(HANDLE h,const char*raw,DWORD n,DWORD*written,void*unused)
{(void)h;(void)unused;if(fake_io_fault==4)return 0;CHECK(n<sizeof(probe_bytes));memcpy(probe_bytes,raw,n);probe_bytes[n]=0;*written=fake_io_fault==5?n-1:n;return 1;}
static int SetEndOfFile(HANDLE h){(void)h;return fake_io_fault!=6;}
static int FlushFileBuffers(HANDLE h){(void)h;return fake_io_fault!=7;}
static int CloseHandle(HANDLE h){(void)h;fake_closes++;return fake_io_fault!=8;}
static unsigned fake_begin(void*context,const NetLink*link,int full)
{
 (void)context;(void)link;
 if(full!=1||folder_cache_update_enable||!folder_cache_manual_callback_check)return 0;
 if(coh_resource_quiescence_begin()!=1)return 0;
 fake_source_opens++;return 1;
}
static int fake_finish(void*context,unsigned id,const unsigned char*raw,unsigned bits,unsigned aligned,unsigned compress,const CohGroupsEligibilityReport*r)
{(void)context;(void)id;(void)raw;(void)bits;(void)aligned;(void)compress;(void)r;if(coh_resource_quiescence_end()!=1)return 0;fake_source_commits++;return 1;}
static void fake_abort(void*context,unsigned id)
{(void)context;(void)id;if(coh_resource_quiet_active)(void)coh_resource_quiescence_end();fake_source_aborts++;}
static void coh_source_groups_capture_install(void)
{
 if(!fake_sink_config)return;
 coh_groups_capture_file.configured=1;coh_groups_capture_file.thread=GetCurrentThreadId();
 coh_groups_transaction_hooks.begin=fake_begin;coh_groups_transaction_hooks.finish=fake_finish;coh_groups_transaction_hooks.abort=fake_abort;
}
#include "coh_fresh_source_profile.inc"
static void reset_probe(void)
{
 if(coh_fp_handle!=INVALID_HANDLE_VALUE){CloseHandle(coh_fp_handle);coh_fp_handle=INVALID_HANDLE_VALUE;}
 reset();memset(&coh_groups_capture_file,0,sizeof(coh_groups_capture_file));memset(&coh_groups_transaction_hooks,0,sizeof(coh_groups_transaction_hooks));
 memset(&coh_fresh_original_hooks,0,sizeof(coh_fresh_original_hooks));
 coh_fp_installed=coh_fp_seal_entered=coh_fp_entered=coh_fp_accepted=coh_fp_committed=0;
 coh_fp_loader_status=coh_fp_loader_released=coh_fp_complete=coh_fp_thread=coh_fp_configured=coh_fp_refusal=0;
 coh_fp_owner_failure=COH_FRESH_OWNER_NONE;
 coh_fp_stage=COH_FRESH_STAGE_INSTALL;coh_fp_path[0]=probe_bytes[0]=0;
 fake_sink_config=fake_probe_env=1;fake_io_fault=fake_opens=fake_closes=fake_source_opens=fake_source_commits=fake_source_aborts=fake_handle_changed=fake_path_replaced=0;replacement_bytes[0]=0;
}
static void probe_success(void)
{
 unsigned id;reset_probe();coh_fresh_source_profile_install();CHECK(coh_groups_capture_file.configured);
 CHECK(strstr(probe_bytes,"\"complete\":false")&&strstr(probe_bytes,"\"stage\":\"INSTALL\""));
 coh_fresh_source_profile_seal_after_normal_enable();CHECK(view().sealed&&!folder_cache_update_enable);
 CHECK(!coh_groups_transaction_hooks.begin(NULL,NULL,0)&&!coh_fp_entered);
 id=coh_groups_transaction_hooks.begin(NULL,NULL,1);CHECK(id==1&&fake_source_opens==1);
 coh_fresh_source_probe_step(COH_FRESH_STAGE_PACKET);
 CHECK(coh_groups_transaction_hooks.finish(NULL,id,NULL,8,1,1,NULL));
 CHECK(coh_fp_committed&&coh_fp_complete&&fake_source_commits==1&&view().restored&&!view().sealed);
 CHECK(strstr(probe_bytes,"\"envelope_committed\":true")&&strstr(probe_bytes,"\"refusal\":\"NONE\""));
 CHECK(!coh_groups_transaction_hooks.begin(NULL,NULL,1)&&fake_source_opens==1);
 CHECK(fake_opens==fake_closes);scenarios++;
}
static void probe_refusals(void)
{
 unsigned id;reset_probe();fake_sink_config=0;coh_fresh_source_profile_install();coh_fresh_source_profile_seal_after_normal_enable();
 CHECK(coh_fp_refusal==1&&!view().sealed&&!view().seal_attempted&&folder_cache_update_enable==1&&!fake_source_opens);
 reset_probe();coh_fresh_source_profile_install();enqueue();coh_fresh_source_profile_seal_after_normal_enable();
 CHECK(coh_fp_refusal==3&&view().restored&&!view().sealed);
 CHECK(!coh_groups_transaction_hooks.begin(NULL,NULL,1)&&!fake_source_opens&&!fake_source_commits);
 CHECK(strstr(probe_bytes,"\"refusal\":\"SEAL_REFUSED\"")&&strstr(probe_bytes,"\"folder_failure\":\"QUEUE_NOT_EMPTY\""));
 reset_probe();coh_fresh_source_profile_install();coh_fresh_source_profile_seal_after_normal_enable();
 id=coh_groups_transaction_hooks.begin(NULL,NULL,1);CHECK(id==1);FolderCacheEnableCallbacks(1);
 CHECK(!coh_groups_transaction_hooks.finish(NULL,id,NULL,8,1,1,NULL)&&!fake_source_commits);
 coh_groups_transaction_hooks.abort(NULL,id);CHECK(coh_fp_complete&&coh_fp_refusal==5&&fake_source_aborts==1&&view().restored);
 CHECK(!coh_resource_quiet_active&&heyThreadLoadAGeo_CriticalSection.leaves==1&&heyThreadLODAModel_CriticalSection.leaves==1);
 CHECK(strstr(probe_bytes,"\"refusal\":\"FINISH_REFUSED\"")&&!strstr(probe_bytes,"\"envelope_committed\":true"));scenarios++;
}
static void probe_io_faults(void)
{
 for(unsigned fault=1;fault<=11;fault++){
  reset_probe();fake_io_fault=fault;coh_fresh_source_profile_install();CHECK(coh_fp_refusal==(fault==8?0u:7u));
  coh_fresh_source_profile_seal_after_normal_enable();CHECK(view().sealed);
  /* Optional diagnostic refusal does not assert or fabricate source output. */
  CHECK(!fake_source_opens&&!fake_source_commits);coh_fresh_folder_profile_abort();CHECK(view().restored);
  if(fault>=4&&fault<=7)CHECK(fake_opens==1&&fake_closes==0);
  coh_fp_complete=1;coh_fp_flush();if(fault==8)CHECK(coh_fp_refusal==7&&fake_closes==1);
 }
 reset_probe();fake_probe_env=0;coh_fresh_source_profile_install();CHECK(!coh_fp_configured&&!fake_opens);
 coh_fresh_source_profile_seal_after_normal_enable();CHECK(view().sealed);coh_fresh_folder_profile_abort();scenarios++;
}
static void probe_same_handle_replacement(void)
{
 reset_probe();coh_fresh_source_profile_install();CHECK(fake_opens==1);
 strcpy(replacement_bytes,"PRIVATE_REPLACEMENT_MUST_SURVIVE");fake_path_replaced=1;
 coh_fresh_source_probe_step(COH_FRESH_STAGE_OWNER);
 CHECK(fake_opens==1&&!strcmp(replacement_bytes,"PRIVATE_REPLACEMENT_MUST_SURVIVE"));
 CHECK(strstr(probe_bytes,"\"stage\":\"OWNER\""));
 fake_handle_changed=1;probe_bytes[0]=0;coh_fresh_source_probe_step(COH_FRESH_STAGE_PACKET);
 CHECK(coh_fp_refusal==7&&!probe_bytes[0]&&!strcmp(replacement_bytes,"PRIVATE_REPLACEMENT_MUST_SURVIVE"));
 coh_fp_complete=1;coh_fp_flush();CHECK(fake_closes==1);scenarios++;
}
static void*foreign_probe(void*unused)
{
 (void)unused;test_thread=2;coh_fresh_source_probe_step(COH_FRESH_STAGE_ABORT);coh_fresh_source_probe_loader(8,1);
 CHECK(!coh_groups_transaction_hooks.begin(NULL,NULL,1));CHECK(!coh_groups_transaction_hooks.finish(NULL,1,NULL,8,1,1,NULL));
 coh_groups_transaction_hooks.abort(NULL,1);coh_fresh_source_profile_install();coh_fresh_source_profile_seal_after_normal_enable();return NULL;
}
static void probe_foreign_immutability(void)
{
 pthread_t thread;reset_probe();coh_fresh_source_profile_install();unsigned opens=fake_opens;char before[8192];strcpy(before,probe_bytes);
 CHECK(!pthread_create(&thread,NULL,foreign_probe,NULL));CHECK(!pthread_join(thread,NULL));
 CHECK(coh_fp_stage==COH_FRESH_STAGE_INSTALL&&!coh_fp_loader_status&&!coh_fp_loader_released&&!coh_fp_entered&&!coh_fp_seal_entered);
 CHECK(!strcmp(before,probe_bytes)&&fake_opens==opens&&!fake_source_opens&&!fake_source_commits&&!fake_source_aborts);scenarios++;
}
static void*foreign_owner_reason(void*unused)
{
 (void)unused;test_thread=2;
 CHECK(coh_fresh_source_owner_failed(1,COH_FRESH_OWNER_LINK_PENDING)==1);return NULL;
}
static void owner_reason_probe(void)
{
 for(unsigned reason=1;reason<COH_FRESH_OWNER_COUNT;reason++){
  pthread_t foreign;char before[8192];unsigned next=reason+1<COH_FRESH_OWNER_COUNT?reason+1:1;
  reset_probe();coh_fresh_source_profile_install();
  CHECK(coh_fresh_source_owner_failed(1,(CohFreshOwnerFailure)reason)==1);
  CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_NONE); /* no active observation */
  coh_fresh_source_profile_seal_after_normal_enable();
  CHECK(coh_groups_transaction_hooks.begin(NULL,NULL,1)==1);
  coh_fresh_source_probe_step(COH_FRESH_STAGE_OWNER);strcpy(before,probe_bytes);
  CHECK(!pthread_create(&foreign,NULL,foreign_owner_reason,NULL));CHECK(!pthread_join(foreign,NULL));
  CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_NONE);
  CHECK(coh_fresh_source_owner_failed(1,COH_FRESH_OWNER_NONE)==1);
  CHECK(coh_fresh_source_owner_failed(1,COH_FRESH_OWNER_COUNT)==1);
  CHECK(coh_fresh_source_owner_failed(1,(CohFreshOwnerFailure)-1)==1);
  CHECK(!coh_fresh_source_owner_failed(0,(CohFreshOwnerFailure)reason));
  CHECK(coh_fp_owner_failure==COH_FRESH_OWNER_NONE&&!strcmp(before,probe_bytes));
  CHECK(coh_fresh_source_owner_failed(3,(CohFreshOwnerFailure)reason)==3);
  CHECK(coh_fp_owner_failure==(CohFreshOwnerFailure)reason&&!strcmp(before,probe_bytes));
  CHECK(coh_fresh_source_owner_failed(1,(CohFreshOwnerFailure)next)==1);
  CHECK(coh_fp_owner_failure==(CohFreshOwnerFailure)reason); /* first failure only */
  coh_groups_transaction_hooks.abort(NULL,1);
  CHECK(coh_fp_complete&&view().restored&&!coh_resource_quiet_active);
  CHECK(coh_fp_owner_failure==(CohFreshOwnerFailure)reason);
  CHECK(strstr(probe_bytes,coh_fp_owner_failures[reason])&&strstr(probe_bytes,"\"source_generation_admitted\":false"));
  CHECK(coh_fresh_source_owner_failed(1,(CohFreshOwnerFailure)next)==1);
  coh_fresh_source_profile_install();CHECK(coh_fp_owner_failure==(CohFreshOwnerFailure)reason);
  CHECK(fake_opens==1&&fake_closes==1&&fake_source_commits==0);
 }
}
int main(int argc,char**argv)
{
 if(argc==2&&!strcmp(argv[1],"--owner-reason")){
  CHECK(!pthread_mutex_init(&heyThreadLoadAGeo_CriticalSection.mutex,NULL));
  CHECK(!pthread_mutex_init(&heyThreadLODAModel_CriticalSection.mutex,NULL));owner_reason_probe();
  CHECK(!pthread_mutex_destroy(&heyThreadLoadAGeo_CriticalSection.mutex));
  CHECK(!pthread_mutex_destroy(&heyThreadLODAModel_CriticalSection.mutex));
  printf("{\"passed\":true,\"checks\":%u,\"owner_reason_cases\":%u,\"old_profile_scenarios_replayed\":false,\"real_server\":false,\"world_authority\":false,\"probe\":%s}\n",checks,(unsigned)COH_FRESH_OWNER_COUNT-1,probe_bytes);return 0;
 }
 if(argc==2&&!strcmp(argv[1],"--sync-fail")){
  test_initialize_fail=1;FolderCacheEnableCallbacks(0);CHECK(!folder_cache_update_enable);
  CHECK(!coh_fresh_folder_profile_seal());CHECK(view().failure==COH_FRESH_FOLDER_SYNC_FAILED);
  CHECK(!view().sealed&&!view().observation_started);CHECK(coh_ff_read(&coh_ff_guard_state)==3);
  printf("{\"passed\":true,\"sync_initialization_refusal\":true,\"ordinary_fallback_preserved\":true}\n");return 0;
 }
 CHECK(argc==1);
 CHECK(!pthread_mutex_init(&heyThreadLoadAGeo_CriticalSection.mutex,NULL));
 CHECK(!pthread_mutex_init(&heyThreadLODAModel_CriticalSection.mutex,NULL));
 ordinary();success();
 for(unsigned i=0;i<8;i++)rejected_seal(i);
 for(unsigned i=0;i<7;i++)activity(i);
 for(unsigned i=0;i<6;i++)loader_refusal(i);
 reset();fail_disable=1;CHECK(!coh_fresh_folder_profile_seal());CHECK(view().failure==COH_FRESH_FOLDER_BAD_UPDATE_MODE&&view().restored&&!view().sealed&&folder_cache_update_enable==1);scenarios++;
 threaded_writer();threaded_foreign();paused_setter_seal();paused_poll_seal();queue_after_close();limit_and_restore();masked_accounting_loss();probe_success();probe_refusals();probe_io_faults();probe_same_handle_replacement();probe_foreign_immutability();
 CHECK(!pthread_mutex_destroy(&heyThreadLoadAGeo_CriticalSection.mutex));CHECK(!pthread_mutex_destroy(&heyThreadLODAModel_CriticalSection.mutex));
 printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"real_host_threads\":true,\"exact_original_loader_guard\":true,\"source_layout_folder_stubs\":true,\"original_foldercache_executed\":false,\"real_server\":false,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks,scenarios);
 return 0;
}
