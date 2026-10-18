#ifndef COH_FRESH_FOLDER_PROFILE_API_H
#define COH_FRESH_FOLDER_PROFILE_API_H
/* NONSHIPPING fresh disposable observer only. No identifiers are exported.
 * All API calls synchronize state. Only original FolderCache owner may
 * seal/begin/check/end/abort successfully; view is safe on any thread. */
typedef enum {
 COH_FRESH_FOLDER_NONE, COH_FRESH_FOLDER_WRONG_THREAD,
 COH_FRESH_FOLDER_REENTRY, COH_FRESH_FOLDER_BAD_UPDATE_MODE,
 COH_FRESH_FOLDER_BAD_MANUAL_MODE, COH_FRESH_FOLDER_QUEUE_NOT_EMPTY,
 COH_FRESH_FOLDER_ACTIVE_UPDATE, COH_FRESH_FOLDER_ACTIVE_CALLBACK, COH_FRESH_FOLDER_ACTIVE_SETTER,
 COH_FRESH_FOLDER_QUEUE_CHANGED, COH_FRESH_FOLDER_SETTER_CHANGED,
 COH_FRESH_FOLDER_ACTIVITY_CHANGED, COH_FRESH_FOLDER_COUNTER_LIMIT,
 COH_FRESH_FOLDER_RESTORE_FAILED, COH_FRESH_FOLDER_SYNC_FAILED
} CohFreshFolderFailure;
typedef struct {
 unsigned seal_attempted,sealed,observation_started,observation_finished,restored;
 unsigned owner_thread_matched,queue_empty,queue_writers_idle,update_idle,callbacks_idle,setters_idle,epoch_unchanged;
 unsigned queue_count,queue_write_depth,update_depth,callback_depth,setter_depth,activity_epoch;
 CohFreshFolderFailure failure;
} CohFreshFolderProfileView;
int coh_fresh_folder_profile_seal(void);
int coh_fresh_folder_profile_begin(void);
int coh_fresh_folder_profile_check(void);
int coh_fresh_folder_profile_end(void);
void coh_fresh_folder_profile_abort(void);
void coh_fresh_folder_profile_view(CohFreshFolderProfileView *);
/* Only the exact transformed original FolderCache.c uses these wrappers. */
#ifdef COH_FRESH_FOLDER_IMPLEMENTATION
static void coh_fresh_folder_queue_added(void);
static void coh_fresh_folder_queue_add_finished(void);
static void coh_fresh_folder_queue_removed(void);
static int FolderCacheUpdate(DirChangeInfo **);
static void doAllCallbacks(void);
#endif
#endif
