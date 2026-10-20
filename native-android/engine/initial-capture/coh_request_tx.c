#include "coh_request_tx_internal.h"
#include <stdlib.h>
#include <string.h>
struct CohRequestTxWitness {
 const void *owner,*udp,*net;uint32_t id;
 uint64_t start_ms,last_ms;
 unsigned active,bracket,linked,queue_events,retired,inflight,inflight_sent;
 CohRequestTxDiagnostics d;
};
_Static_assert(sizeof(struct CohRequestTxWitness)<=COH_REQUEST_TX_WITNESS_MAX,"bounded witness");
static _Thread_local CohRequestTxWitness *current;
static void refuse(CohRequestTxWitness*w,CohRequestTxRefusal r){if(w&&w->d.refusal==COH_REQUEST_TX_NONE)w->d.refusal=r;}
static int clock_ok(CohRequestTxWitness*w,uint64_t now){
 if(now<w->start_ms||now<w->last_ms||now-w->start_ms>COH_REQUEST_TX_OFFSET_MAX){refuse(w,COH_REQUEST_TX_CLOCK);return 0;}return 1;
}
static int scope(CohRequestTxWitness*w,const CohInitialCapture*owner,uint64_t now){
 if(!w)return 0;
 if(current||w->active||w->retired||w->owner!=owner){refuse(w,COH_REQUEST_TX_OWNER);if(current)refuse(current,COH_REQUEST_TX_OWNER);return 0;}
 if(w->d.refusal||!clock_ok(w,now))return 0;
 w->last_ms=now;w->active=1;current=w;return 1;
}
static void unscope(CohRequestTxWitness*w,int entered){if(entered){if(w->bracket||w->inflight)refuse(w,COH_REQUEST_TX_STATE);w->active=w->bracket=w->inflight=0;current=NULL;}}
static CohRequestTxWitness *live(void){return current&&!current->d.refusal?current:NULL;}
static int event_time(CohRequestTxWitness*w,uint64_t now){if(now!=w->last_ms){refuse(w,COH_REQUEST_TX_CLOCK);return 0;}return 1;}
CohRequestTxWitness *coh_request_tx_create(const CohInitialCapture*owner,uint64_t start){
 if(!owner)return NULL;
 CohRequestTxWitness*w=calloc(1,sizeof(*w));if(!w)return NULL;
 w->owner=owner;w->start_ms=w->last_ms=start;w->d.diagnostic_only=1;w->d.queue_status=COH_NOT_FOUND;return w;
}
CohStatus coh_request_tx_service(CohRequestTxWitness*w,CohInitialCapture*owner,uint64_t now,CohCancel cancel,CohInitialCaptureObserver observer,void*context,size_t bytes){
 int entered=scope(w,owner,now);CohStatus s=coh_initial_capture_service(owner,now,cancel,observer,context,bytes);unscope(w,entered);return s;
}
void coh_request_tx_close(CohRequestTxWitness*w,CohInitialCapture*owner){int entered=scope(w,owner,w?w->last_ms:0);coh_initial_capture_close(owner);unscope(w,entered);}
void coh_request_tx_cancel(CohRequestTxWitness*w,CohInitialCapture*owner){int entered=scope(w,owner,w?w->last_ms:0);coh_initial_capture_cancel(owner);unscope(w,entered);}
void coh_request_tx_timeout(CohRequestTxWitness*w,CohInitialCapture*owner){int entered=scope(w,owner,w?w->last_ms:0);coh_initial_capture_timeout(owner);unscope(w,entered);}
void coh_request_tx_retire(CohRequestTxWitness*w){
 if(!w)return;
 if(w->active){refuse(w,COH_REQUEST_TX_OWNER);return;}
 w->owner=w->udp=w->net=NULL;w->id=0;w->retired=1;w->d.witness_retired=1;
}
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return a&&b&&an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);}
void coh_request_tx_diagnostics(const CohRequestTxWitness*w,CohRequestTxDiagnostics*out){
 if(w&&out&&disjoint(w,sizeof(*w),out,sizeof(*out))){CohRequestTxDiagnostics d=w->d;d.valid=w->retired&&!d.refusal;*out=d;}
}
void coh_request_tx_destroy(CohRequestTxWitness*w){if(w&&!w->active){coh_request_tx_retire(w);volatile unsigned char*p=(volatile unsigned char*)w;for(size_t i=0;i<sizeof(*w);i++)p[i]=0;free(w);}}
void coh_request_tx_hook_begin(const void*owner,const void*udp,uint64_t now){
 CohRequestTxWitness*w=live();if(!w)return;
 if(owner!=w->owner||!udp||w->bracket||w->d.queue_attempted||w->d.queue_succeeded){refuse(w,COH_REQUEST_TX_OWNER);return;}
 if(!event_time(w,now))return;
 w->bracket=1;w->udp=udp;w->d.queue_attempted=1;
}
void coh_request_tx_hook_link(const void*udp,const void*net){
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
 coh_initial_tx_link(udp,net);
#endif
 CohRequestTxWitness*w=live();if(!w||!w->bracket)return;
 if(udp!=w->udp||!net||w->linked){refuse(w,COH_REQUEST_TX_OWNER);return;}w->net=net;w->linked=1;
}
void coh_request_tx_hook_queue(const void*net,uint32_t id,unsigned parts,int reliable,int ordered,int compressed,int connect,int sent,uint64_t now){
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
 coh_initial_tx_queue(net,id,parts,reliable,ordered,compressed,connect,sent);
#endif
 CohRequestTxWitness*w=live();if(!w||!w->bracket)return;
 if(!w->linked||net!=w->net||!id||parts!=1||reliable!=1||ordered||compressed||connect||sent||w->queue_events){refuse(w,COH_REQUEST_TX_STATE);return;}
 if(!event_time(w,now))return;
 w->id=id;w->queue_events=1;w->d.queue_offset_ms=now-w->start_ms;
}
void coh_request_tx_hook_end(CohStatus status){
 CohRequestTxWitness*w=current;if(!w||!w->bracket)return;
 w->bracket=0;w->d.queue_status=(unsigned)status<=COH_STATE?status:COH_INVALID;
 if((unsigned)status>COH_STATE)refuse(w,COH_REQUEST_TX_CALLBACK);
 if(w->d.refusal)return;
 if(status==COH_OK){if(w->queue_events!=1||!w->linked){refuse(w,COH_REQUEST_TX_STATE);return;}w->d.queue_succeeded=1;}
 else{if(w->queue_events)refuse(w,COH_REQUEST_TX_STATE);w->udp=w->net=NULL;w->id=0;}
}
void coh_request_tx_hook_send_begin(const void*net,uint32_t id,int sent,uint64_t now){
 CohRequestTxWitness*w=live();if(!w||!w->d.queue_succeeded||net!=w->net||id!=w->id)return;
 if(w->inflight||w->bracket||w->d.retirement!=COH_REQUEST_TX_PENDING||(sent!=0&&sent!=1)||sent!=(int)w->d.first_send_accepted){refuse(w,COH_REQUEST_TX_STATE);return;}
 if(!event_time(w,now))return;
 w->inflight=1;w->inflight_sent=(unsigned)sent;
}
void coh_request_tx_hook_send(const void*net,uint32_t id,int sent,CohStatus status,uint64_t now){
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
 coh_initial_tx_send(net,id,status);
#endif
 CohRequestTxWitness*w=live();if(!w||!w->d.queue_succeeded||net!=w->net||id!=w->id)return;
 if(!w->inflight||sent!=(int)w->inflight_sent){refuse(w,COH_REQUEST_TX_STATE);return;}
 w->inflight=0;
 if(!event_time(w,now))return;
 uint64_t total=(uint64_t)w->d.first_send_attempts+w->d.retry_send_attempts;
 if(total==COH_REQUEST_TX_EVENT_MAX){refuse(w,COH_REQUEST_TX_LIMIT);return;}
 if((unsigned)status>COH_STATE){refuse(w,COH_REQUEST_TX_CALLBACK);return;}
 if(sent)w->d.retry_send_attempts++;else w->d.first_send_attempts++;
 w->d.last_send_offset_ms=now-w->start_ms;
 if(status==COH_OK){if(sent)w->d.successful_retries++;else{w->d.first_send_accepted=1;w->d.first_send_offset_ms=now-w->start_ms;}}
 else if(status==COH_NOT_FOUND)w->d.deferred_send_callbacks++;else w->d.failed_send_callbacks++;
 if(w->d.retirement!=COH_REQUEST_TX_PENDING){w->net=w->udp=NULL;w->id=0;}
}
void coh_request_tx_hook_ack(const void*net,uint32_t id,uint64_t now){
 CohRequestTxWitness*w=live();if(!w||!w->d.queue_succeeded||net!=w->net||id!=w->id)return;
 if(!w->d.first_send_accepted||w->d.retirement!=COH_REQUEST_TX_PENDING){refuse(w,COH_REQUEST_TX_STATE);return;}
 if(!event_time(w,now))return;
 w->d.peer_transport_ack_observed=1;w->d.retirement=COH_REQUEST_TX_PEER_ACK;w->d.retirement_offset_ms=now-w->start_ms;
 if(!w->inflight){w->net=w->udp=NULL;w->id=0;}
}
void coh_request_tx_hook_retire(const void*net,CohRequestTxRetirement reason){
 CohRequestTxWitness*w=live();if(!w||!w->d.queue_succeeded||net!=w->net)return;
 /* Close then clear_queues is one source retirement. During an in-flight
  * callback its key remains borrowed until the callback result is captured. */
 if(w->d.retirement!=COH_REQUEST_TX_PENDING)return;
 if(reason<COH_REQUEST_TX_CLOSED||reason>COH_REQUEST_TX_QUEUES_CLEARED){refuse(w,COH_REQUEST_TX_STATE);return;}
 w->d.retirement=reason;w->d.retirement_offset_ms=w->last_ms-w->start_ms;
 if(!w->inflight){w->net=w->udp=NULL;w->id=0;}
}
