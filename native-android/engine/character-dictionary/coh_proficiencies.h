#ifndef COH_PROFICIENCIES_H
#define COH_PROFICIENCIES_H
#include "../costume-import/coh_costume_import.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_PROFICIENCY_ROWS_MAX 512u
#define COH_PROFICIENCY_IDS_MAX 4096u
#define COH_PROFICIENCY_TEXT_MAX 65536u
#define COH_PROFICIENCY_INPUT_MAX 65536u
#define COH_PROFICIENCY_RAM_MAX 524288u
#define COH_PROFICIENCY_STACK_RESERVE 8192u
#define COH_PROFICIENCY_WORK_MAX 16777216u
typedef struct { uint32_t offset,size; } CohProficiencyText;
typedef struct { CohProficiencyText fields[5]; int32_t origin,rarity,id; uint32_t active; } CohProficiency;
typedef struct { int32_t id; CohProficiencyText name; } CohProficiencyIdRow;
typedef struct {
 uint8_t sha256[2][32]; uint64_t provenance;
 uint32_t schema_crc[2],dependencies[2],count,id_count,text_bytes,max_id,slot_count,active_count;
 uint32_t complete,runtime_generation,actor_authority;
 CohProficiency entries[COH_PROFICIENCY_ROWS_MAX];
 CohProficiencyIdRow id_rows[COH_PROFICIENCY_ROWS_MAX];
 uint32_t slots[COH_PROFICIENCY_IDS_MAX]; /* row+1; zero is a hole */
 char text[COH_PROFICIENCY_TEXT_MAX];
} CohProficiencyDictionary;
typedef struct { CohProficiencyDictionary candidate; } CohProficiencyWorkspace;
typedef struct { CohCancel cancel; size_t context_bytes,scratch_reserve; } CohProficiencyControl;
/* Complete Parse6 Proficiencies + ProficiencyIds import and original finalization.
 * All records/strings copied; original array order retained. Default ASCII
 * case-insensitive names: first positive ID-name wins, first definition name
 * wins, different names sharing an ID overwrite that reverse slot in source
 * order. Nonpositive ID rows are preserved but ignored by finalization.
 * Empty/non-ASCII names refuse rather than guess null-key/CRT locale behavior.
 * Origins/rarities are copied opaque signed words, not enum membership claims.
 * Both full expected SHA256 digests must be nonzero. Provenance is historical
 * input identity only; no current cache/shared-memory/actor authority follows.
 * Every input/hash/provider/control/context/output/workspace span is valid,
 * pairwise disjoint, immutable and live through the call. Callbacks may mutate
 * only their declared contexts and, for the digest, its supplied 32-byte output,
 * never other admitted spans or reenter using
 * them. Provider/context/scratch + cancellation context/scratch + retained and
 * native stack are charged before any callback. Scratch reserves must include
 * all callback memory/stack. Fixed work budget covers reads/comparisons/polls.
 * Failure preserves output; workspace is scratch. No allocation. Input and
 * callbacks may retire after successful copy. RAM_MAX is a policy, not RSS fit.
 */
CohStatus coh_proficiencies_read(CohBytes definitions,CohBytes ids,uint64_t provenance,
 const uint8_t expected_sha256[2][32],const CohCostumeImportDigest*,const CohProficiencyControl*,
 CohProficiencyDictionary*,CohProficiencyWorkspace*,size_t budget,size_t retained);
/* Immutable owner must remain live. Indices refer to copied source rows.
 * by_id checks live definition membership, never returns a removed ID-map name.
 * join additionally requires that first name winner owns that reverse slot;
 * a legitimate different-name collision returns NOT_FOUND. Outputs unchanged
 * on every refusal. No pointers into caller input or provider are retained. */
CohStatus coh_proficiencies_find(const CohProficiencyDictionary*,CohBytes name,uint32_t*row);
CohStatus coh_proficiencies_by_id(const CohProficiencyDictionary*,uint32_t id,uint32_t*row);
/* Historical ID-map getters return raw ID-row indices, not live definitions.
 * First positive numeric-ID or ASCII-name winner; retained removed names can
 * appear here. They never satisfy by_id/join membership by themselves. */
CohStatus coh_proficiencies_id_name(const CohProficiencyDictionary*,uint32_t id,uint32_t*id_row);
CohStatus coh_proficiencies_id_find(const CohProficiencyDictionary*,CohBytes name,uint32_t*id_row);
CohStatus coh_proficiencies_join(const CohProficiencyDictionary*,CohBytes name,uint32_t id,uint32_t*row);
#ifdef __cplusplus
}
#endif
#endif
