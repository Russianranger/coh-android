#ifndef COH_REQUEST_TX_INTERNAL_H
#define COH_REQUEST_TX_INTERNAL_H
#include "coh_request_tx.h"
/* Private synchronous hooks; no hook returns a value to the protocol. */
void coh_request_tx_hook_begin(const void *capture,const void *udp,uint64_t);
void coh_request_tx_hook_end(CohStatus);
void coh_request_tx_hook_link(const void *udp,const void *net);
void coh_request_tx_hook_queue(const void *net,uint32_t id,unsigned parts,
 int reliable,int ordered,int compressed,int connect,int sent,uint64_t);
void coh_request_tx_hook_send_begin(const void *net,uint32_t id,int sent,uint64_t);
void coh_request_tx_hook_send(const void *net,uint32_t id,int sent,CohStatus,uint64_t);
void coh_request_tx_hook_ack(const void *net,uint32_t id,uint64_t);
void coh_request_tx_hook_retire(const void *net,CohRequestTxRetirement);
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
/* Scalar observers for the two concrete continuation Tx IDs. */
void coh_initial_tx_link(const void *udp,const void *net);
void coh_initial_tx_queue(const void *net,uint32_t id,unsigned parts,int reliable,int ordered,int compressed,int connect,int sent);
void coh_initial_tx_send(const void *net,uint32_t id,CohStatus);
#endif
#endif
