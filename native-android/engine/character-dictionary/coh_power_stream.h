#ifndef COH_POWER_STREAM_H
#define COH_POWER_STREAM_H
#include "coh_origins.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_POWER_STREAM_MAX (64u*1024u*1024u)
#define COH_POWER_STREAM_RECORD_MAX 32768u
#define COH_POWER_STREAM_SLOT_MAX 65536u
#define COH_POWER_STREAM_RAM_MAX (4u*1024u*1024u)
#define COH_POWER_STREAM_STACK_RESERVE 16384u
#define COH_POWER_STREAM_WORK_MAX (64u*1024u*1024u)
/* Provider is immutable and synchronous. read_at must fill EXACTLY requested
 * bytes or refuse. All context, digest state, handles and callback scratch must
 * be pre-reserved and included in context_bytes/scratch_reserve before entry.
 * No callback may allocate beyond that reservation. abort is called after EVERY
 * attempted begin that does not reach a successful finish; it cannot fail.
 * Cancellation is checked between reads, after parsing, during indexing, before
 * finish and immediately after successful finish. A post-finish cancellation
 * preserves output without calling abort on the already retired digest.
 * Context/file lease remains alive and immutable until the owner retires.
 * Input size is streamed/file-backed; it is not a retained heap byte span. */
typedef struct {
 void *context;size_t context_bytes,scratch_reserve;
 uint32_t input_bytes;uint64_t lease;
 CohStatus (*read_at)(void*,uint32_t,uint8_t*,size_t);
 CohStatus (*begin)(void*);
 CohStatus (*update)(void*,CohBytes);
 CohStatus (*finish)(void*,uint8_t[32]);
 void (*abort)(void*);
 int (*cancelled)(void*);
} CohPowerStreamProvider;
typedef struct {uint32_t begin,end,full_name,short_name,crc;uint16_t full_name_bytes,short_name_bytes;} CohPowerStreamEntry;
typedef struct {
 CohPowerStreamProvider provider;uint8_t input_sha256[32];
 uint32_t observed_schema_crc,count,dependency_count,table_counts[5];
 uint32_t index_slots,unique_count,duplicate_count;
 uint8_t raw_schema_validated,source_crc_recomputed,runtime_generation,actor_authority;
 CohPowerStreamEntry entries[COH_POWER_STREAM_RECORD_MAX];
 uint32_t slots[COH_POWER_STREAM_SLOT_MAX];
} CohPowerStreamDictionary;
typedef struct {CohPowerStreamDictionary candidate;uint8_t buffer[4096];} CohPowerStreamWorkspace;
/* Raw historical import: full static binary grammar and individual original
 * fullname CRC matching are NOT original ParseTableCRC or runtime admission.
 * Caller output unchanged on all failures; workspace/provider digest may change.
 * Entire fixed output/workspace/context/descriptors/reserves/retained charged
 * before callbacks. Module cap is literal; no implied global memory partition. */
CohStatus coh_power_stream_read(const CohPowerStreamProvider*,const uint8_t[32],CohPowerStreamDictionary*,CohPowerStreamWorkspace*,size_t,size_t);
CohStatus coh_power_stream_find_crc(const CohPowerStreamDictionary*,uint32_t,uint32_t*);
#ifdef __cplusplus
}
#endif
#endif
