#ifndef COH_BASEDETAIL_INVENTORY_H
#define COH_BASEDETAIL_INVENTORY_H
#include "coh_salvage.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_BASEDETAIL_ROWS_MAX 4096u
#define COH_BASEDETAIL_IDS_MAX 8192u
#define COH_BASEDETAIL_INPUT_MAX 131072u
#define COH_BASEDETAIL_TEXT_MAX 262144u
#define COH_BASEDETAIL_WORK_MAX 67108864u
#define COH_BASEDETAIL_RAM_MAX 16777216u
#define COH_BASEDETAIL_STACK_RESERVE 16384u
typedef struct {CohSalvageText name;uint32_t id,active;} CohBaseDetailIdentity;
typedef struct {
 uint8_t source_sha256[3][32],ids_sha256[32];uint64_t provenance;
 uint32_t schema_crc,dependencies,count,id_count,text_bytes,max_id,slot_count,active_count;
 uint32_t complete,runtime_generation,actor_authority;
 CohBaseDetailIdentity entries[COH_BASEDETAIL_ROWS_MAX];
 CohSalvageIdRow id_rows[COH_BASEDETAIL_ROWS_MAX];
 uint32_t slots[COH_BASEDETAIL_IDS_MAX];
 char text[COH_BASEDETAIL_TEXT_MAX];
} CohBaseDetailInventory;
typedef struct {CohBaseDetailInventory candidate;} CohBaseDetailInventoryWorkspace;
typedef struct {CohBytes ids;uint8_t expected_ids_sha256[32],expected_details_sha256[32];uint64_t provenance;} CohBaseDetailInventorySources;
typedef struct {CohCancel cancel;size_t context_bytes,scratch_reserve;} CohBaseDetailInventoryControl;
/* Complete fresh CLIENT inventory identity finalization, not Details gameplay.
 * ids is one complete InvBaseDetail Parse6 body. details is the SAME immutable
 * copied complete CohSalvageDictionary, including its full ordered Details-name
 * array. All schema CRCs/nonzero source hashes, Details SHA and provenance must
 * match. No caller-created name/count table or external numeric ID establishes
 * membership. All raw ID rows are copied in order. First positive CI ID-name
 * insertion wins; max includes rejected duplicate insertions. Fresh generic
 * finalization keeps the FIRST CI definition name and overwrites reverse slots
 * forward, so the LAST different-name definition sharing an ID wins. Duplicate
 * definition rows stay present with zero ID/inactive. Empty/no-positive ID maps,
 * non-ASCII/empty/>=128-byte keys and declared policy bounds refuse as a whole.
 * Raw ID-name getters may return removed names; live by_id/join never do.
 * This differs from workshop StructLink LAST-name lookup and Salvage FIRST-ID.
 * No geometry, Details finalizer, inventory mutation/evaluation/UI, current cache
 * family/generation, complete character, actor or ACK authority follows.
 * Every configured source/owner/provider/control/context/output/workspace span
 * must be valid, pairwise disjoint and immutable throughout. The WHOLE source
 * Details owner is charged, not only its selected names. Callback writes are
 * confined to declared contexts and digest's supplied32B output; no reentry or
 * concurrent use of admitted mutable spans. Declared callback scratch includes
 * callback memory/stack. Stack, contexts, scratch and caller-retained old owners
 * are charged before callbacks. No allocation. Failure preserves output; scratch
 * may remain partial. Successful output copies all strings/IDs and scalar source
 * identities, so every input/provider lease may then retire. RAM_MAX is policy,
 * not process RSS/ABI/Android fit. Immutable output must outlive all getters.
 */
CohStatus coh_basedetail_inventory_read(const CohBaseDetailInventorySources*,
 const CohSalvageDictionary*,const CohCostumeImportDigest*,const CohBaseDetailInventoryControl*,
 CohBaseDetailInventory*,CohBaseDetailInventoryWorkspace*,size_t budget,size_t retained);
CohStatus coh_basedetail_inventory_find(const CohBaseDetailInventory*,CohBytes,uint32_t*row);
CohStatus coh_basedetail_inventory_by_id(const CohBaseDetailInventory*,uint32_t id,uint32_t*row);
CohStatus coh_basedetail_inventory_join(const CohBaseDetailInventory*,CohBytes,uint32_t id,uint32_t*row);
CohStatus coh_basedetail_inventory_id_find(const CohBaseDetailInventory*,CohBytes,uint32_t*id_row);
CohStatus coh_basedetail_inventory_id_name(const CohBaseDetailInventory*,uint32_t id,uint32_t*id_row);
#ifdef __cplusplus
}
#endif
#endif
