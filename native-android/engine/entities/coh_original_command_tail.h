#ifndef COH_ORIGINAL_COMMAND_TAIL_H
#define COH_ORIGINAL_COMMAND_TAIL_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ORIGINAL_COMMAND_STACK_RESERVE 16384u
#define COH_ORIGINAL_COMMAND_AGGREGATE_MAX (8u*1024u*1024u)
typedef union { long double alignment; unsigned char bytes[262144]; } CohOriginalCommandTailWorkspace;
typedef struct {
 CohStatus status;size_t begin_bit,end_bit,failure_bit,packet_bits,command_begin_bit;
 uint32_t active_command,commands_read,terminator,tail_complete,trace_count,
  trace_omitted,command_ids[16],alignment_markers,game_markers,static_map_messages,
  static_map_rows,static_map_cells,static_map_words,static_map_dbid,static_map_checksum,contact_messages,contact_updates,contact_rows;
}CohOriginalCommandTailReport;
/* Original application command order from actual post-global cursor; only wire
 * staging, never UI/filesystem mutation, actor publication, READY or ACK. Reader
 * unchanged, raw unknown command payload left unread. Optional trace omission
 * never changes parsing. Fixed workspace/stack/report/input/retained owners charged under
 * the existing 8 MiB initial aggregate; decoded 4 MiB cap remains in reader.
 * tail_complete requires original zero-command terminator at actual logical end.
 */
CohStatus coh_original_command_tail_receive(const CohRepReader *,
 CohOriginalCommandTailWorkspace *, CohOriginalCommandTailReport *,size_t budget,size_t retained);
#ifdef __cplusplus
}
#endif
#endif
