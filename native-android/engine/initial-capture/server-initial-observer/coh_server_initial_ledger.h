#ifndef COH_SERVER_INITIAL_LEDGER_H
#define COH_SERVER_INITIAL_LEDGER_H
#include <stdint.h>
#include <stddef.h>
#define COH_SIO_MAX_EVENTS 1000000u
#define COH_SIO_MAX_JSON 4096u
typedef enum {COH_SIO_NONE,COH_SIO_OWNER,COH_SIO_THREAD,COH_SIO_ORDER,
 COH_SIO_LIMIT,COH_SIO_VALUE,COH_SIO_PACKET,COH_SIO_SINK} CohSIORefusal;
typedef enum {COH_SIO_ACTIVE,COH_SIO_FINAL_RETURN,COH_SIO_REFUSED} CohSIOStop;
typedef enum {COH_SIO_UNUSED,COH_SIO_DISPATCH,COH_SIO_REQUEST_STATE,
 COH_SIO_TICK,COH_SIO_BACKPRESSURE_ENTER,COH_SIO_BACKPRESSURE_PASS,
 COH_SIO_BACKPRESSURE_BLOCK,COH_SIO_MAPXFER_ENTER,COH_SIO_MAPXFER_RETURN,
 COH_SIO_SELECTED,COH_SIO_FULL_ENTER,COH_SIO_ALLENTS_HEADER,
 COH_SIO_CHARACTER_ENTER,COH_SIO_CHARACTER_CORE_ENTER,
 COH_SIO_CHARACTER_CORE_RETURN,COH_SIO_CHARACTER_RETURN,
 COH_SIO_ATTACHED,COH_SIO_FINISH_ENTITY,COH_SIO_SEND_BEGIN,
 COH_SIO_SEND_RETURN,COH_SIO_GROUPS_BOUND} CohSIOEvent;
/* PRIVATE input keys. The source adapter freshly validates registered table
 * membership/backlinks and immutable identity fields before each use. Never
 * serialize this value or derive authority merely from supplied labels. */
typedef struct {const void*link,*client,*entity,*character;uint32_t uid,connection_id,
 connect_id,entity_id,dbid,server_index,auth_id,protocol;} CohSIOKey;
typedef struct {
 unsigned diagnostic_only,valid,groups_owner_bound,owner_retired;
 unsigned dispatch_entered,dispatch_state_written,full_sender_entered,
 full_update_argument,viewed_entity_matches_owner,allents_header_written;
 unsigned character_entered,character_core_entered,character_core_returned,
 character_returned,packet_attached,finish_entity_seen,final_packet_same,
 pkt_send_called,pkt_send_returned,last_sent_self,final_packet_compress,
 final_packet_ordered,final_packet_reliable;
 uint32_t tick_seen,tick_selected,backpressure_entered,backpressure_passed,
 backpressure_blocked,mapxfer_entered,mapxfer_returned;
 uint32_t stage,reached_mask,last_ready,ready_seen_mask,final_packet_bits;
 int pkt_send_result;CohSIORefusal refusal;CohSIOStop stop;
} CohSIOReport;
typedef struct {CohSIOKey key;uintptr_t packet;uint32_t thread,events;
 unsigned send_pending;CohSIOReport report;} CohSIOLedger;
/* All calls are serialized on the original exclusive Map owner thread.
 * No allocation, clock, I/O, original-object read or callback occurs here. */
void coh_sio_init(CohSIOLedger*);
void coh_sio_bind(CohSIOLedger*,const CohSIOKey*,uint32_t thread);
void coh_sio_record(CohSIOLedger*,const CohSIOKey*,uint32_t thread,CohSIOEvent,
 const void*packet,uint32_t a,uint32_t b,uint32_t c);
void coh_sio_send_return(CohSIOLedger*,uint32_t thread,int result);
void coh_sio_refuse(CohSIOLedger*,CohSIORefusal);
void coh_sio_snapshot(const CohSIOLedger*,CohSIOReport*);
int coh_sio_json(const CohSIOReport*,char*,size_t);
#endif
