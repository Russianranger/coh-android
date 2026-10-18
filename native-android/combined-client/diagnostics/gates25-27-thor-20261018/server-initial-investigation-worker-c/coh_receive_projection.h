#ifndef COH_RECEIVE_PROJECTION_H
#define COH_RECEIVE_PROJECTION_H
/* Diagnostic-only projection of existing counters, never a packet or owner. */
#include "../../../../engine/initial-capture/coh_initial_capture.h"
#include <stdio.h>
#include <string.h>
#define COH_RECEIVE_REPORT_MAX 2048u
#define COH_RECEIVE_COUNT_MAX 1000000u
#define COH_RECEIVE_FIELDS(X) \
 X(udp_datagrams_received,u->datagrams_received) \
 X(udp_peer_rejects,u->peer_rejects) X(udp_truncated,u->truncated) \
 X(udp_empty,u->empty) X(udp_malformed,u->malformed) X(udp_unsupported,u->unsupported) \
 X(udp_receive_budget_exhausted,u->receive_budget_exhausted) \
 X(link_received,u->link.received) X(link_duplicates,u->link.duplicates) \
 X(link_malformed,u->link.malformed) X(link_unsupported,u->link.unsupported) \
 X(link_queue_limits,u->link.queue_limits) X(link_fragment_expirations,u->link.fragment_expirations) \
 X(link_timeouts,u->link.timeouts)
typedef struct {
#define COH_RECEIVE_MEMBER(name,value) uint64_t name;
 COH_RECEIVE_FIELDS(COH_RECEIVE_MEMBER)
#undef COH_RECEIVE_MEMBER
 uint64_t decode_compressed_bytes,decode_declared_raw_bytes,decode_output_budget;
 uint32_t rx_pending,fragment_groups,decode_failure_kind,sample_count;
 uint32_t max_rx_pending_sampled,max_fragment_groups_sampled;
 unsigned refusal;
} CohReceiveProjection;
static inline void coh_receive_sample(CohReceiveProjection*p,const CohNetUdpDiagnostics*u){
 if(!p||p->refusal)return;
 if(!u){p->refusal=1;return;}
#define COH_RECEIVE_CHECK(name,value) if((value)>COH_RECEIVE_COUNT_MAX){p->refusal=2;return;}
 COH_RECEIVE_FIELDS(COH_RECEIVE_CHECK)
#undef COH_RECEIVE_CHECK
 if((unsigned)u->link.decode.failure_kind>COH_NET_DECODE_STREAM||u->link.rx_pending>COH_NET_RX_MAX||
    u->link.fragment_groups>COH_NET_GROUP_MAX||u->link.decode.compressed_bytes>COH_NET_MESSAGE_MAX||
    u->link.decode.declared_raw_bytes>UINT32_MAX||u->link.decode.output_budget>COH_NET_DECODED_MAX){p->refusal=1;return;}
 if(p->sample_count==COH_RECEIVE_COUNT_MAX){p->refusal=2;return;}
#define COH_RECEIVE_SET(name,value) p->name=(value);
 COH_RECEIVE_FIELDS(COH_RECEIVE_SET)
#undef COH_RECEIVE_SET
 p->rx_pending=u->link.rx_pending;p->fragment_groups=u->link.fragment_groups;
 if(p->rx_pending>p->max_rx_pending_sampled)p->max_rx_pending_sampled=p->rx_pending;
 if(p->fragment_groups>p->max_fragment_groups_sampled)p->max_fragment_groups_sampled=p->fragment_groups;
 p->decode_failure_kind=(uint32_t)u->link.decode.failure_kind;
 p->decode_compressed_bytes=u->link.decode.compressed_bytes;
 p->decode_declared_raw_bytes=u->link.decode.declared_raw_bytes;p->decode_output_budget=u->link.decode.output_budget;
 p->sample_count++;
}
static inline int coh_receive_json(const CohReceiveProjection*p,unsigned retired,unsigned cleanup,char*out,size_t bytes){
 if(!p||!out||retired>1||cleanup>1)return -1;
 return snprintf(out,bytes,"{\"schema\":\"coh-initial-receive-counters-v1\",\"diagnostic_only\":true,\"valid\":%s,\"refusal\":\"%s\","
#define COH_RECEIVE_FORMAT(name,value) "\""#name"\":%llu,"
 COH_RECEIVE_FIELDS(COH_RECEIVE_FORMAT)
#undef COH_RECEIVE_FORMAT
 "\"rx_pending\":%u,\"fragment_groups\":%u,\"decode_failure_kind\":%u,"
 "\"decode_compressed_bytes\":%llu,\"decode_declared_raw_bytes\":%llu,\"decode_output_budget\":%llu,"
 "\"sample_count\":%u,\"max_rx_pending_sampled\":%u,\"max_fragment_groups_sampled\":%u,"
 "\"observation_retired\":%s,\"cleanup_transport_counters_equal\":%s,"
 "\"command_specific_emission_proved\":false,\"server_receipt_proved\":false,\"source_generation_admitted\":false,"
 "\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",
 p->sample_count&&!p->refusal?"true":"false",p->refusal==0?"NONE":p->refusal==2?"LIMIT":"INPUT",
#define COH_RECEIVE_ARGUMENT(name,value) (unsigned long long)p->name,
 COH_RECEIVE_FIELDS(COH_RECEIVE_ARGUMENT)
#undef COH_RECEIVE_ARGUMENT
 p->rx_pending,p->fragment_groups,p->decode_failure_kind,(unsigned long long)p->decode_compressed_bytes,
 (unsigned long long)p->decode_declared_raw_bytes,(unsigned long long)p->decode_output_budget,p->sample_count,
 p->max_rx_pending_sampled,p->max_fragment_groups_sampled,retired?"true":"false",cleanup?"true":"false");
}
#endif
