#ifndef COH_ORIGINAL_INITIAL_TAIL_H
#define COH_ORIGINAL_INITIAL_TAIL_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ORIGINAL_INITIAL_RAM_MAX (8u*1024u*1024u)
#define COH_ORIGINAL_INITIAL_STACK_RESERVE 65536u
enum {COH_ORIGINAL_INITIAL_SENTINEL=1,COH_ORIGINAL_INITIAL_CONTROL,
 COH_ORIGINAL_INITIAL_DELETES,COH_ORIGINAL_INITIAL_CHARACTER,
 COH_ORIGINAL_INITIAL_POWER_INFO,COH_ORIGINAL_INITIAL_POWER_MODES,
 COH_ORIGINAL_INITIAL_BADGES,COH_ORIGINAL_INITIAL_BADGE_MONITOR,
 COH_ORIGINAL_INITIAL_INVENTORY,COH_ORIGINAL_INITIAL_SOCIAL,
 COH_ORIGINAL_INITIAL_ATTRIBUTES,COH_ORIGINAL_INITIAL_DYNAMIC,
 COH_ORIGINAL_INITIAL_VIEW,COH_ORIGINAL_INITIAL_TAIL_COMPLETE};
typedef struct {size_t begin_bit,end_bit;uint32_t values[6];} CohOriginalInitialSpan;
typedef struct {
 CohStatus status;uint32_t stage,stage_count,source_shared_count,
  dynamic_count,dynamic_count_from_wire,entity_list_complete,character_complete,
  source_tail_complete,unexpected_entity_index;
 size_t begin_bit,end_bit,packet_bits,list_end_bit,control_end_bit,
  deletes_end_bit,character_end_bit,peak_mapped_bytes,peak_aggregate_bytes;
 CohOriginalInitialSpan spans[13];
} CohOriginalInitialTailReport;
/* Continue a source-validated fresh selected-self entity suffix at its exact
 * end cursor. The original list sentinel, control/deletes, whole character and
 * global fields are read in entReceiveUpdate order using qualified children.
 * CLIENT shared count26 is independently derived from original normal startup
 * and pinned CLIENT category/set text, NOT selected by fitting this packet.
 * Its content token is not a running-server generation or gameplay owner.
 * Numeric references remain unresolved; no actor state or ACK is published.
 * Source tail ends after sky/slave; enclosing command terminator is separate.
 * Input reader is unchanged. Report records exact completed component cursors;
 * a failing atomic child leaves its component's start as end_bit.
 * Staged mmap storage is page-rounded and admitted before allocation; previous
 * storage is wiped/unmapped before the next stage. Caller retained includes
 * all old/candidate owners, borrowed sources and caller stack outside64KiB.
 * Input+reader+report+current mapping+64KiB+retained stay under existing8MiB;
 * child4MiB caps remain. No resident6MiB union is hidden from badge admission.
 * External libc/zlib implementation stack is not an RSS/PSS measurement.
 */
CohStatus coh_original_initial_tail(const CohRepReader *,uint32_t previous_entity_index,
 uint32_t packet_id,CohOriginalInitialTailReport *,size_t budget,size_t retained);
const char *coh_original_initial_field_name(uint32_t stage);
#ifdef __cplusplus
}
#endif
#endif
