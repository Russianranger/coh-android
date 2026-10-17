#ifndef COH_ATTRIB_DESCRIPTION_H
#define COH_ATTRIB_DESCRIPTION_H
#include "coh_attrib_monitor.h"
#include "../attribute-dictionary/coh_attribute_dictionary.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ATTRIB_MODIFIERS_MAX 256u
#define COH_ATTRIB_SOURCE_TEXT_MAX 65536u
#define COH_ATTRIB_DESCRIPTION_RAM_MAX (2u*1024u*1024u)
#define COH_ATTRIB_DESCRIPTION_STACK_RESERVE 16384u
typedef struct{CohCancel cancel;size_t context_bytes,scratch_reserve;}CohAttribReadControl;
typedef struct{
 uint32_t key,power_crc,source_type,server_entity_id,chance_word,magnitude_word;
 uint32_t name_offset,name_bytes;
}CohAttribModifier;
typedef struct{
 uint32_t new_target,full,has_target,target_server_index,value_count,modifier_count;
 uint32_t value_words[COH_ATTRIBUTE_DICTIONARY_ROWS_MAX],buff[COH_ATTRIBUTE_DICTIONARY_ROWS_MAX];
 CohAttribModifier modifiers[COH_ATTRIB_MODIFIERS_MAX];
 uint32_t text_bytes;char text[COH_ATTRIB_SOURCE_TEXT_MAX];
 CohAttribMonitor monitor;size_t begin_bit,end_bit;
 uint8_t schema_input_sha256[32];uint64_t schema_input_lease;
 uint32_t raw_description_validated,original_state_applied,dictionary_authority,actor_authority;
}CohAttribDescription;
typedef struct{CohAttribDescription candidate;CohAttribMonitorWorkspace monitor;}CohAttribDescriptionWorkspace;
/* Full sendAttribDescription/getAllMatchingMods producer/consumer wire grammar,
 * plus existing monitor branch unchanged. Full values retain exact source
 * reversed schema row ordinals; no semantic filtering or grouping of duplicate
 * modifier keys occurs. Every raw powerCRC/source identity remains unresolved.
 * Optional target is raw server index, never a selected actor identity.
 * Full profile requires a completely parsed immutable schema candidate and
 * explicit expected schema SHA/lease; absence/refusal never skips values.
 * Offline schema integrity is not a matching live dictionary generation.
 * All floats must be finite, sourceType2/3 carry bounded NUL text+Pack20ID;
 * sourceType0/1 carry no name/id. Every sentinel/modifier validates before
 * reader/output commit. No original UI/attribute/power state is applied.
 * All explicit input/control/context/schema/output/work/expectedSHA/reader spans
 * pairwise disjoint and budget charged with16KiBnative reserve. Schema's whole
 * borrowed input is charged once and must stay immutable/alive under its lease.
 * Control poll is optional and may modify only its declared context. All active
 * callback scratch/retained storage must be pre-reserved and charged; no hidden
 * allocation or packet/output mutation. Poll cancellation rolls back everything.
 * Named2MiB bound, no hidden heap allocation; external callback stack/foreign
 * sanitizer closure is unqualified. Existing monitor ABI is unchanged.
 */
CohStatus coh_attrib_description_read(CohRepReader*,const CohAttributeDictionary*,
 const uint8_t expected_schema_sha256[32],uint64_t expected_schema_lease,
 const CohAttribReadControl*,CohAttribDescription*,CohAttribDescriptionWorkspace*,
 size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
