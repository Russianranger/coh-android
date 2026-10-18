#ifndef COH_INITIAL_PROGRESS_H
#define COH_INITIAL_PROGRESS_H
/* NONSHIPPING scalar observation only. No packet/endpoint/credential is copied.
 * This does not identify the request's wire packet or prove server receipt. */
#include "coh_initial_capture.h"
#define COH_INITIAL_PROGRESS_EVENT_MAX 1000000u
#define COH_INITIAL_PROGRESS_REPORT_MAX 1024u
typedef enum { COH_INITIAL_PROGRESS_NONE,COH_INITIAL_PROGRESS_OWNER,
 COH_INITIAL_PROGRESS_CLOCK,COH_INITIAL_PROGRESS_STATE,
 COH_INITIAL_PROGRESS_LIMIT,COH_INITIAL_PROGRESS_CALLBACK } CohInitialProgressRefusal;
typedef struct {
 const CohInitialCapture *owner;
 uint64_t start_ms,last_ms,queue_offset_ms,last_post_queue_service_offset_ms;
 uint64_t groups_generation;
 uint32_t map_generation,selection_generation;
 uint32_t post_queue_services,post_queue_send_callbacks,post_queue_datagrams_emitted;
 uint32_t post_queue_would_block,post_queue_interrupted,post_queue_send_errors,
  post_queue_partial_sends;
 unsigned bound,queued,active,counting,retired;
 CohInitialProgressRefusal refusal;
} CohInitialProgress;
static inline void coh_initial_progress_refuse(CohInitialProgress*w,CohInitialProgressRefusal r){if(w->refusal==COH_INITIAL_PROGRESS_NONE)w->refusal=r;}
static inline void coh_initial_progress_bind(CohInitialProgress*w,const CohInitialCapture*owner,uint64_t now){
 if(!w||!owner)return;
 if(w->bound||w->owner||w->retired){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_OWNER);return;}
 w->owner=owner;w->start_ms=w->last_ms=now;w->bound=1;
}
static inline int coh_initial_progress_identity(const CohInitialProgress*w,const CohInitialCaptureDiagnostics*d){
 return d->groups_observed&&d->groups_observations==1&&d->reqallents_sent==1&&
  d->groups_message_generation&&d->map_generation&&d->selection_generation&&
  (!w->queued||(w->groups_generation==d->groups_message_generation&&
   w->map_generation==d->map_generation&&w->selection_generation==d->selection_generation));
}
static inline void coh_initial_progress_service_begin(CohInitialProgress*w,const CohInitialCapture*owner,uint64_t now,const CohInitialCaptureDiagnostics*d){
 if(!w||!d)return;
 if(w->refusal)return;
 if(!w->bound||w->retired||owner!=w->owner||w->active){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_OWNER);return;}
 if(now<w->last_ms){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_CLOCK);return;}
 w->last_ms=now;w->active=1;w->counting=0;
 if(w->queued){
  /* An already closed DB and this same one-shot owner constrain the observed
   * service scope to Map. Datagrams remain command-unattributed. */
  if(!coh_initial_progress_identity(w,d)||d->phase!=COH_INITIAL_CAPTURE_WAIT_ALLENTS||d->local.db_phase!=COH_DB_CLOSED){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_STATE);return;}
  if(w->post_queue_services==COH_INITIAL_PROGRESS_EVENT_MAX){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_LIMIT);return;}
  w->counting=1;w->post_queue_services++;w->last_post_queue_service_offset_ms=now-w->start_ms;
 }
}
static inline void coh_initial_progress_send(CohInitialProgress*w,size_t bytes,int full,int would_block,int interrupted,int partial,int error){
 if(!w||w->refusal||!w->active||!w->counting)return;
 if(!bytes||bytes>COH_PROTOCOL_FRAME_MAX||full<0||full>1||would_block<0||would_block>1||interrupted<0||interrupted>1||partial<0||partial>1||error<0||error>1||full+would_block+interrupted+partial+error!=1){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_CALLBACK);return;}
 if(w->post_queue_send_callbacks==COH_INITIAL_PROGRESS_EVENT_MAX){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_LIMIT);return;}
 w->post_queue_send_callbacks++;w->post_queue_datagrams_emitted+=(unsigned)full;
 w->post_queue_would_block+=(unsigned)would_block;w->post_queue_interrupted+=(unsigned)interrupted;
 w->post_queue_partial_sends+=(unsigned)partial;w->post_queue_send_errors+=(unsigned)error;
}
static inline void coh_initial_progress_service_end(CohInitialProgress*w,const CohInitialCapture*owner,uint64_t now,const CohInitialCaptureDiagnostics*d){
 if(!w||!d)return;
 if(w->refusal){w->active=w->counting=0;return;}
 if(!w->active||owner!=w->owner||now!=w->last_ms){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_OWNER);w->active=w->counting=0;return;}
 w->active=w->counting=0;
 if(d->reqallents_sent){
  if(!coh_initial_progress_identity(w,d)){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_STATE);return;}
  if(!w->queued){w->queued=1;w->groups_generation=d->groups_message_generation;w->map_generation=d->map_generation;w->selection_generation=d->selection_generation;w->queue_offset_ms=now-w->start_ms;}
 }
 else if(w->queued)coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_STATE);
}
static inline void coh_initial_progress_retire(CohInitialProgress*w,const CohInitialCapture*owner){
 if(!w||!w->bound)return;
 if(w->owner!=owner||w->active){coh_initial_progress_refuse(w,COH_INITIAL_PROGRESS_OWNER);return;}
 w->owner=NULL;w->retired=1;
}
#endif
