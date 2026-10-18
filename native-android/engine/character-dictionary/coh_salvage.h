#ifndef COH_SALVAGE_H
#define COH_SALVAGE_H
#include "../costume-import/coh_costume_import.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SALVAGE_MAX 1024u
#define COH_SALVAGE_DETAILS_MAX 4096u
#define COH_SALVAGE_IDS_MAX 8192u
#define COH_SALVAGE_VALUES_MAX 8192u
#define COH_SALVAGE_TEXT_MAX 262144u
#define COH_SALVAGE_STRING_MAX 12000u
#define COH_SALVAGE_INPUT_MAX 524288u
#define COH_SALVAGE_INPUT_TOTAL_MAX 1048576u
#define COH_SALVAGE_RAM_MAX 16777216u
#define COH_SALVAGE_WORK_MAX 67108864u
#define COH_SALVAGE_STACK_RESERVE 16384u
typedef struct {uint32_t offset,size;} CohSalvageText;
typedef struct {uint32_t first,count;} CohSalvageRange;
typedef struct {CohSalvageText text;uint32_t detail_plus_one;} CohSalvageValue;
typedef struct {
 /* name, UI four strings, tab, drop message, open-failure message, store product */
 CohSalvageText fields[9];
 /* rarity, type, challenge, minimum reverse-engineer level, max inventory, sell, flags */
 uint32_t words[7],id;
 /* workshops, reward tables, open requires, auction requires */
 CohSalvageRange arrays[4];
} CohSalvageItem;
typedef struct {int32_t id;CohSalvageText name;} CohSalvageIdRow;
typedef struct {CohSalvageText name;CohSalvageRange members;} CohSalvageTab;
typedef struct {
 uint8_t sha256[3][32];uint64_t provenance;
 uint32_t schema_crc[3],dependencies[3],count,id_count,details_count,text_bytes,value_count;
 uint32_t max_id,slot_count,tab_count,workshop_joins,complete,runtime_generation,actor_authority;
 CohSalvageItem items[COH_SALVAGE_MAX];CohSalvageIdRow id_rows[COH_SALVAGE_MAX];
 CohSalvageText details[COH_SALVAGE_DETAILS_MAX];CohSalvageValue values[COH_SALVAGE_VALUES_MAX];
 uint32_t slots[COH_SALVAGE_IDS_MAX]; /* item row+1, zero is a hole */
 CohSalvageTab tabs[COH_SALVAGE_MAX];uint32_t tab_members[COH_SALVAGE_MAX];
 char text[COH_SALVAGE_TEXT_MAX];
} CohSalvageDictionary;
typedef struct {CohSalvageDictionary candidate;} CohSalvageWorkspace;
typedef struct {CohBytes bodies[3];uint8_t expected_sha256[3][32];uint64_t provenance;} CohSalvageSources;
typedef struct {CohCancel cancel;size_t context_bytes,scratch_reserve;} CohSalvageControl;
/* Three complete Parse6 inputs in order Salvage.bin/InvSalvage.bin/details.bin.
 * Copied historical CLIENT dictionary and Details NAME identity only. All three
 * full schemas/records are traversed; no field-byte skipping, geometry/Details
 * gameplay finalization, catalog/evaluator/UI or current-generation authority.
 * CLIENT chareval_Validate is a source no-op; this bounded owner nevertheless
 * refuses nonempty Open/AuctionRequires rather than publishing unsupported
 * gameplay expressions. Other string/scalar data is opaque persisted content.
 * ASCII nonempty names and tabs only; Salvage names must be alphanumeric/_ as
 * original finalizer requires. Invalid/duplicate Salvage names refuse as a
 * whole transaction. ID rows retain order, skip nonpositive IDs, first positive
 * name wins and max includes failed duplicates. All item IDs assigned forward;
 * reverse slots written backward, so first item wins a different-name collision.
 * Tab lookup preserves each tab's source item order. Tab ordinals are private
 * first-encounter indices, not original stash hash iteration positions.
 * Workshop links use the complete Details-name array's source reverse lookup.
 * Both original digests and all limits are mandatory native policy, not RSS fit.
 * Sources/config/provider/control/contexts/output/workspace must be valid,
 * pairwise disjoint and immutable through call; callbacks may mutate only own
 * declared context and digest's supplied32B output. No concurrent/reentrant use
 * of these admitted mutable spans. Provider/cancel scratch, stack, all configured
 * spans and caller-retained old owners are charged BEFORE callbacks. No heap.
 * Failure preserves output; workspace may be partial. After success all inputs
 * and providers may retire; only immutable copied owner must outlive getters.
 */
CohStatus coh_salvage_read(const CohSalvageSources*,const CohCostumeImportDigest*,
 const CohSalvageControl*,CohSalvageDictionary*,CohSalvageWorkspace*,size_t budget,size_t retained);
CohStatus coh_salvage_find(const CohSalvageDictionary*,CohBytes name,uint32_t*item);
CohStatus coh_salvage_by_id(const CohSalvageDictionary*,uint32_t id,uint32_t*item);
CohStatus coh_salvage_join(const CohSalvageDictionary*,CohBytes name,uint32_t id,uint32_t*item);
CohStatus coh_salvage_tab(const CohSalvageDictionary*,CohBytes name,uint32_t*tab);
CohStatus coh_salvage_workshop(const CohSalvageDictionary*,uint32_t item,uint32_t ordinal,uint32_t*detail);
#ifdef __cplusplus
}
#endif
#endif
