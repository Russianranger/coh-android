/* NONSHIPPING replacement TU; ordinary source bytes remain unchanged. */
#include "../local/coh_local.c"
#include "coh_initial_capture_private.h"
struct CohInitialCapture {
 CohLocal *local;CohInitialMap *map;CohInitialCaptureDiagnostics d;
 CohInitialCaptureObserver observer;void *context;size_t context_bytes;
 unsigned busy,observing,begun;
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
 uint8_t local_password_md5[16];unsigned local_password_set;
#endif
};
static int il_disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static void il_snapshot(CohInitialCapture*x){if(x->map){CohLocalDiagnostics local=x->d.local;CohInitialCaptureFailureSnapshot first=x->d.first_failure;coh_initial_map_diagnostics(x->map,&x->d);x->d.local=local;x->d.first_failure=first;}coh_local_diagnostics(x->local,&x->d.local);}
static void il_first_failure(CohInitialCapture*x,CohStatus status,CohInitialCaptureFailure why){
 if(x->d.first_failure.valid)return;
 snapshot(x->local);CohLocalDiagnostics local={0};coh_local_diagnostics(x->local,&local);
 CohInitialMapFailurePhase map=coh_initial_map_failure_phase(x->map);
 x->d.first_failure=(CohInitialCaptureFailureSnapshot){1,local.phase,local.db_phase,map.valid?map.phase:local.map_phase,status,why};
}
static CohStatus il_stop(CohInitialCapture*x,CohStatus status,CohInitialCaptureFailure why){
 il_first_failure(x,status,why);
 il_snapshot(x);x->d.status=status;x->d.failure=why;x->d.phase=status==COH_CANCELLED?COH_INITIAL_CAPTURE_CANCELLED:COH_INITIAL_CAPTURE_FAILED;
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
 coh_initial_map_forget_ready(x->map);coh_db_wipe(x->local_password_md5,16);x->local_password_set=0;
#endif
 coh_local_close(x->local);coh_local_diagnostics(x->local,&x->d.local);return status;
}
CohInitialCapture *coh_initial_capture_create(const CohLocalConfig*config){
 CohLocal*s=coh_local_create(config);if(!s)return NULL;
 CohInitialCapture*x=calloc(1,sizeof(*x));if(!x){coh_local_destroy(s);return NULL;}x->local=s;return x;
}
CohStatus coh_initial_capture_begin(CohInitialCapture*x,const CohDbLogin*policy,const char*account,uint32_t db_id,uint32_t map_id,uint64_t now){
 if(!x)return COH_INVALID;
 if(x->busy||x->begun)return COH_STATE;
 CohStatus s=coh_local_begin(x->local,policy,account,db_id,map_id,now);
 if(s==COH_OK){x->begun=1;x->d.phase=COH_INITIAL_CAPTURE_CONNECTING;}il_snapshot(x);return s;
}
CohStatus coh_initial_capture_characters(const CohInitialCapture*x,CohLocalCharacters*out){
 if(!x||!out)return COH_INVALID;
 if(x->busy)return COH_STATE;
 if(!il_disjoint(out,sizeof(*out),x,sizeof(*x))||!il_disjoint(out,sizeof(*out),x->local,sizeof(*x->local))||(x->map&&!coh_initial_map_output_disjoint(x->map,out,sizeof(*out))))return COH_INVALID;
 return coh_local_characters(x->local,out);
}
CohStatus coh_initial_capture_choose_character(CohInitialCapture*x,uint32_t slot,uint64_t now){
 if(!x)return COH_INVALID;
 if(x->busy)return COH_STATE;
 CohStatus s=coh_local_choose_character(x->local,slot,now);il_snapshot(x);return s;
}
static CohStatus il_observe(void*context,const CohInitialCaptureEvent*event){
 CohInitialCapture*x=context;x->observing=1;x->local->observing=1;
 CohStatus s=x->observer(x->context,x,event);
 x->local->observing=0;x->observing=0;return s;
}
CohStatus coh_initial_capture_service(CohInitialCapture*x,uint64_t now,CohCancel cancel,
 CohInitialCaptureObserver observer,void*context,size_t context_bytes){
 if(!x||!observer||!context||!context_bytes||context_bytes>UINTPTR_MAX-(uintptr_t)context)return COH_INVALID;
 if(x->busy||!x->begun||x->d.phase==COH_INITIAL_CAPTURED||x->d.phase==COH_INITIAL_CAPTURE_FAILED||x->d.phase==COH_INITIAL_CAPTURE_CANCELLED||x->d.phase==COH_INITIAL_CAPTURE_CLOSED)return COH_STATE;
 CohLocal*s=x->local;
 if(!il_disjoint(context,context_bytes,x,sizeof(*x))||!il_disjoint(context,context_bytes,s,sizeof(*s)))return COH_INVALID;
 if(now<s->clock_ms)return COH_INVALID;
 x->busy=1;x->observer=observer;x->context=context;x->context_bytes=context_bytes;s->clock_ms=now;
 CohStatus status=COH_OK;CohInitialCaptureFailure failure=COH_INITIAL_CAPTURE_FAILURE_PROTOCOL;
 if(cancel.poll&&cancel.poll(cancel.context)){status=COH_CANCELLED;failure=COH_INITIAL_CAPTURE_FAILURE_CANCELLED;goto done;}
 if(s->db){CohDbSessionPhase p=coh_db_session_phase(s->db);
  if(p>=COH_DB_CONNECTING&&p<=COH_DB_DISCONNECTING){status=coh_db_session_service(s->db,now,(CohCancel){0});p=coh_db_session_phase(s->db);if(status!=COH_OK){if(p==COH_DB_TIMED_OUT)failure=COH_INITIAL_CAPTURE_FAILURE_TIMEOUT;goto done;}}
  if(p==COH_DB_FAILED||p==COH_DB_TIMED_OUT||p==COH_DB_CANCELLED||(p==COH_DB_CLOSED&&!s->map)){status=COH_STATE;if(p==COH_DB_TIMED_OUT)failure=COH_INITIAL_CAPTURE_FAILURE_TIMEOUT;goto done;}
  if(p==COH_DB_CHARACTERS)s->diagnostics.phase=COH_LOCAL_CHARACTERS_READY;
  if(p==COH_DB_HANDOFF_READY){status=begin_map(s,now);if(status!=COH_OK)goto done;x->map=coh_initial_map_create(s->map);if(!x->map){status=COH_STATE;failure=COH_INITIAL_CAPTURE_FAILURE_OWNER;goto done;}
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
   if(x->local_password_set){status=coh_initial_map_local_password_digest(x->map,x->local_password_md5);coh_db_wipe(x->local_password_md5,16);x->local_password_set=0;if(status!=COH_OK)goto done;}
#endif
  }
 }
 if(s->map){
  if(!x->map){status=COH_STATE;failure=COH_INITIAL_CAPTURE_FAILURE_OWNER;goto done;}
  status=coh_initial_map_service(x->map,now,cancel,il_observe,x,x,sizeof(*x),context,context_bytes);
  il_snapshot(x);
  if(x->d.phase==COH_INITIAL_CAPTURED){coh_local_close(s);snapshot(s);il_snapshot(x);goto done;}
  if(status!=COH_OK){failure=x->d.failure;goto done;}
 }
 snapshot(s);il_snapshot(x);
 done:
 if(status!=COH_OK&&x->d.phase!=COH_INITIAL_CAPTURED)il_stop(x,status,failure);
 x->observer=NULL;x->context=NULL;x->context_bytes=0;x->busy=0;return status;
}
CohStatus coh_initial_capture_lease(const CohInitialCapture*x,const CohInitialCaptureEvent*event,CohInitialCaptureLease*out){
 if(!x||!event||!out)return COH_INVALID;
 if(!x->busy||!x->observing||!x->map)return COH_STATE;
 if(!il_disjoint(out,sizeof(*out),x,sizeof(*x))||!il_disjoint(out,sizeof(*out),x->local,sizeof(*x->local)))return COH_INVALID;
 return coh_initial_map_lease(x->map,event,out);
}
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
CohStatus coh_initial_capture_local_password_digest(CohInitialCapture*x,const uint8_t digest[16]){
 if(!x||!digest||!il_disjoint(digest,16,x,sizeof(*x)))return COH_INVALID;
 if(x->busy||x->begun||x->local_password_set)return COH_STATE;
 memcpy(x->local_password_md5,digest,16);x->local_password_set=1;return COH_OK;
}
CohStatus coh_initial_capture_finish_initial(const CohInitialCapture*x,const CohInitialCaptureEvent*event,size_t end){
 if(!x||!event)return COH_INVALID;
 if(!x->busy||!x->observing||!x->map)return COH_STATE;
 return coh_initial_map_finish_initial(x->map,event,end);
}
size_t coh_initial_capture_continuation_bytes(const CohInitialCapture*x){return x?sizeof(*x)-offsetof(CohInitialCapture,local_password_md5)+coh_initial_map_continuation_bytes():0;}
#endif
void coh_initial_capture_diagnostics(const CohInitialCapture*x,CohInitialCaptureDiagnostics*out){
 if(x&&out&&il_disjoint(out,sizeof(*out),x,sizeof(*x))&&il_disjoint(out,sizeof(*out),x->local,sizeof(*x->local))&&(!x->map||coh_initial_map_output_disjoint(x->map,out,sizeof(*out))))*out=x->d;
}
void coh_initial_capture_timeout(CohInitialCapture*x){if(x&&!x->busy&&x->begun&&x->d.phase>=COH_INITIAL_CAPTURE_CONNECTING&&x->d.phase<=COH_INITIAL_CAPTURE_WAIT_ALLENTS)il_stop(x,COH_STATE,COH_INITIAL_CAPTURE_FAILURE_TIMEOUT);}
void coh_initial_capture_cancel(CohInitialCapture*x){if(x&&!x->busy){
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
coh_initial_map_abort_reason(x->map,COH_INITIAL_ABORT_CANCELLED);
#endif
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
coh_initial_map_forget_ready(x->map);coh_db_wipe(x->local_password_md5,16);x->local_password_set=0;
#endif
if(x->begun&&((x->d.phase>=COH_INITIAL_CAPTURE_CONNECTING&&x->d.phase<=COH_INITIAL_CAPTURE_WAIT_ALLENTS)||x->d.phase==COH_INITIAL_CAPTURE_WAIT_UPDATES)){il_first_failure(x,COH_CANCELLED,COH_INITIAL_CAPTURE_FAILURE_CANCELLED);}
coh_local_cancel(x->local);il_snapshot(x);x->d.phase=COH_INITIAL_CAPTURE_CANCELLED;x->d.failure=COH_INITIAL_CAPTURE_FAILURE_CANCELLED;x->d.status=COH_CANCELLED;}}
void coh_initial_capture_close(CohInitialCapture*x){if(x&&!x->busy){
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
coh_initial_map_forget_ready(x->map);coh_db_wipe(x->local_password_md5,16);x->local_password_set=0;
#endif
coh_local_close(x->local);il_snapshot(x);if(x->d.phase!=COH_INITIAL_CAPTURED&&x->d.phase!=COH_INITIAL_CAPTURE_FAILED&&x->d.phase!=COH_INITIAL_CAPTURE_CANCELLED)x->d.phase=COH_INITIAL_CAPTURE_CLOSED;}}
void coh_initial_capture_destroy(CohInitialCapture*x){if(x&&!x->busy){coh_local_close(x->local);coh_initial_map_destroy(x->map);coh_local_destroy(x->local);coh_db_wipe(x,sizeof(*x));free(x);}}
