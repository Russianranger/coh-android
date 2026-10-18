#ifndef COH_REQUEST_TX_H
#define COH_REQUEST_TX_H
/* NONSHIPPING diagnostic role. All access is on one caller thread. */
#include "coh_initial_capture.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_REQUEST_TX_EVENT_MAX 1000000u
#define COH_REQUEST_TX_WITNESS_MAX 256u
#define COH_REQUEST_TX_OFFSET_MAX UINT64_C(600000)
typedef struct CohRequestTxWitness CohRequestTxWitness;
typedef enum { COH_REQUEST_TX_NONE,COH_REQUEST_TX_OWNER,COH_REQUEST_TX_CLOCK,
 COH_REQUEST_TX_STATE,COH_REQUEST_TX_LIMIT,COH_REQUEST_TX_CALLBACK
} CohRequestTxRefusal;
typedef enum { COH_REQUEST_TX_PENDING,COH_REQUEST_TX_PEER_ACK,
 COH_REQUEST_TX_CLOSED,COH_REQUEST_TX_CANCELLED,COH_REQUEST_TX_TIMED_OUT,
 COH_REQUEST_TX_DISCONNECTED,COH_REQUEST_TX_DESTROYED,COH_REQUEST_TX_QUEUES_CLEARED
} CohRequestTxRetirement;
/* No packet ID, payload, endpoint, account, DBID, generation or pointer escapes.
 * A send acceptance is the actual CohNetSend result for this exact queued Tx.
 * In the unchanged UDP adapter COH_OK means one full successful sendto.
 * A matching peer transport ACK is NOT an application/full-update ACK, server
 * request dispatch, complete character, actor publication or world authority. */
typedef struct {
 unsigned diagnostic_only,valid,witness_retired,queue_attempted,queue_succeeded;
 unsigned first_send_accepted,peer_transport_ack_observed;
 CohStatus queue_status;CohRequestTxRefusal refusal;CohRequestTxRetirement retirement;
 uint32_t first_send_attempts,retry_send_attempts,successful_retries;
 uint32_t deferred_send_callbacks,failed_send_callbacks;
 uint64_t queue_offset_ms,first_send_offset_ms,last_send_offset_ms,retirement_offset_ms;
 unsigned server_receipt_proved;
 unsigned source_generation_admitted,complete_initial_character,actor_publication,
  ack_permitted,world_authority; /* always zero */
} CohRequestTxDiagnostics;
/* Call after successful begin. This bounded owner borrows capture only as an
 * identity key; it never dereferences or destroys capture. NULL is optional. */
CohRequestTxWitness *coh_request_tx_create(const CohInitialCapture *,uint64_t start_ms);
/* Always delegates once to the existing operation with unchanged arguments and
 * result. Witness refusal cannot suppress protocol service or close. Use these
 * wrappers for every service and final close of this capture transaction. */
CohStatus coh_request_tx_service(CohRequestTxWitness *,CohInitialCapture *,uint64_t,
 CohCancel,CohInitialCaptureObserver,void *,size_t);
void coh_request_tx_close(CohRequestTxWitness *,CohInitialCapture *);
void coh_request_tx_cancel(CohRequestTxWitness *,CohInitialCapture *);
void coh_request_tx_timeout(CohRequestTxWitness *,CohInitialCapture *);
/* Retire BEFORE capture destroy. Do not retire/destroy during a callback.
 * Outputs are valid only after retirement with refusal NONE. */
void coh_request_tx_retire(CohRequestTxWitness *);
void coh_request_tx_diagnostics(const CohRequestTxWitness *,CohRequestTxDiagnostics *);
void coh_request_tx_destroy(CohRequestTxWitness *);
#ifdef __cplusplus
}
#endif
#endif
