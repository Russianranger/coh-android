#ifndef COH_DYNAMIC_H
#define COH_DYNAMIC_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_DYNAMIC_COUNT_MAX 65536u
#define COH_DYNAMIC_ZIP_MAX (1024u*1024u)
#define COH_DYNAMIC_ZLIB_ARENA_BYTES (256u*1024u)
#define COH_DYNAMIC_RAM_MAX (8u*1024u*1024u)
#define COH_DYNAMIC_STACK_RESERVE 4096u
typedef struct{uint32_t index,hp,repair;}CohDynamicDelta;
typedef struct{
 uint32_t modified_count,expected_count,raw_bytes,compressed_bytes,world_ownership_verified;
 uint8_t full_status[COH_DYNAMIC_COUNT_MAX+1];CohDynamicDelta deltas[COH_DYNAMIC_COUNT_MAX];
 size_t begin_bit,end_bit;
}CohDynamicDiagnostic;
typedef union{long double alignment;void*pointer;uint8_t bytes[COH_DYNAMIC_ZLIB_ARENA_BYTES];}CohDynamicArena;
typedef struct{CohDynamicDiagnostic candidate;CohDynamicArena arena;size_t arena_used;}CohDynamicWorkspace;
/* Whole original groupDynSend producer diagnostic wire body. Expected count is
 * caller-provided diagnostic bound, NEVER world ownership/generation authority.
 * world_ownership_verified always0. Full zipped status bytes require exact raw
 * count and zlib input/output/stream end; deltas retain order/duplicates and
 * require index<expected count. No state/graph application, actor or ACK.
 * Pairwise disjoint reader/input/output/workspace, heap/arena-owned PODs. Budget
 * input+bothPODs+fixedzlibarena+4096stack+retained<=8MiB. No system allocation;
 * custom zlib allocation confined to workspace arena. Failure atomic.
 * The4096 reserve/check covers native wrapper frames only. External zlib stack
 * is unmeasured and library not rebuilt with sanitizers; whole dependency
 * budget/sanitizer closure is NOT qualified. Diagnostic use only. */
CohStatus coh_dynamic_diagnostic_read(CohRepReader *,uint32_t expected_count,
 CohDynamicDiagnostic *,CohDynamicWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
