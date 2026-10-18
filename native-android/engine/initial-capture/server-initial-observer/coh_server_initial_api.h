#ifndef COH_SERVER_INITIAL_API_H
#define COH_SERVER_INITIAL_API_H
#include "coh_server_initial_ledger.h"
/* Original-source hooks only. Arguments are synchronous borrowed identities.
 * No return value can influence the original protocol/control path. */
void coh_sio_source_bind_groups(const void*link);
void coh_sio_source_event(unsigned event,const void*link,const void*entity,
 const void*packet,uint32_t a,uint32_t b,uint32_t c);
void coh_sio_source_character(unsigned event,const void*entity,const void*packet);
void coh_sio_source_finish_entity(const void*entity,const void*packet);
void coh_sio_source_retire_entity(const void*entity);
void coh_sio_source_send_return(uintptr_t pre_call_packet,int original_result);
#endif
