#ifndef COH_CHARACTER_CREATION_H
#define COH_CHARACTER_CREATION_H
#include "coh_character_initial.h"
#include "coh_character_ui.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CHARACTER_CREATION_RAM_MAX (8u*1024u*1024u)
#define COH_CHARACTER_CREATION_STACK_RESERVE 16384u
typedef struct {
 CohCharacterInitialPrefix initial;
 CohCharacterUi ui;
 size_t begin_bit,initial_end_bit,end_bit;
} CohCharacterCreationPrefix;
typedef struct {
 CohCharacterCreationPrefix candidate;
 CohCharacterInitialWorkspace initial;
 CohCharacterUiWorkspace ui;
} CohCharacterCreationWorkspace;
/* Atomic original outer-character groups1..4, through all windows, immediately
 * BEFORE reward-token count. This remains incomplete outer character staging:
 * groups5..6, global tails, dictionaries, selected identity and message end
 * cannot be omitted before actor publication or any completion acknowledgment.
 * Exact ordered child parsing only, no offsets supplied by caller/scanning.
 * Entire input/output/workspace+stackreserve+retained ownership charged once;
 * no allocation. All spans pairwise disjoint. Output/reader unchanged on every
 * refusal; workspace unspecified. Account bytes sensitive, never log by default. */
CohStatus coh_character_creation_read(CohRepReader *,const CohCharacterWireProfile *,
 uint32_t packet_id,CohCharacterCreationPrefix *,CohCharacterCreationWorkspace *,
 size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
