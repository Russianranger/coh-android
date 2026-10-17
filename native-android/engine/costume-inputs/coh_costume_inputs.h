#ifndef COH_COSTUME_INPUTS_H
#define COH_COSTUME_INPUTS_H
#include "../costume-import/coh_costume_import.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_COSTUME_INPUT_BYTES_MAX 65536u
#define COH_COSTUME_INPUT_PART_MAX 29u
#define COH_COSTUME_INPUT_COLOR_MAX 256u
#define COH_COSTUME_INPUT_DEPENDENCY_MAX 16u
#define COH_COSTUME_INPUT_BUDGET_MAX (1024u*1024u)
#define COH_COSTUME_INPUT_STACK_RESERVE 16384u
enum{COH_COSTUME_INPUT_BODY_PARTS=1,COH_COSTUME_INPUT_SUPER_PALETTE=2};
typedef struct{char path[260];uint32_t timestamp;} CohCostumeInputDependency;
typedef struct{
 char name[260],source_file[260],geometry_name[260],texture_name[260],base_name[260];
 uint32_t bone_count_first,influence_cost,bone_count_last,dont_clear_word,bones[2],part_index;
} CohCostumeInputPart;
typedef struct{
 uint32_t kind,schema_crc,dependency_count,part_count,color_count;
 CohCostumeInputDependency dependencies[COH_COSTUME_INPUT_DEPENDENCY_MAX];
 CohCostumeInputPart parts[COH_COSTUME_INPUT_PART_MAX];
 char palette_name[260];uint32_t colors[COH_COSTUME_INPUT_COLOR_MAX][3];
 uint8_t payload_sha256[32];size_t end_byte;
 uint32_t original_callbacks_applied,authentic_stash_slots,actor_authority;
} CohCostumeInput;
typedef struct{CohCostumeInput candidate;} CohCostumeInputWorkspace;
/* Complete bounded Parse6 serialized bodies for the two pinned source tables,
 * before postload callbacks. CRCs are compared, NOT recomputed from ParseTable.
 * Strings/words are copied, ordering retained, duplicate BoneCount retained as
 * first/last (source later overwrite not silently lost). Raw serialized bones
 * and indices are NOT ParseBoneNames results. No original hash slots or actor.
 * Pins/provider/context/input/workspace/output are disjoint and immutable during
 * callback; workspace is off-stack and may change on refusal. Output commits
 * only after complete syntax + whole-input digest. Callback contract/external
 * qualification is the same as costume-import. Named aggregate <=1MiB includes
 * whole spans, native stack16KiB, provider scratch, caller retained allocations.
 */
CohStatus coh_costume_input_read(CohBytes,uint32_t kind,const uint8_t expected_sha256[32],
 const CohCostumeImportDigest *,CohCostumeInputWorkspace *,CohCostumeInput *,
 size_t budget,size_t retained);
#ifdef __cplusplus
}
#endif
#endif
