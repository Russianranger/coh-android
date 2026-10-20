#ifndef COH_CLIENT_COSTUME_SLOTS_H
#define COH_CLIENT_COSTUME_SLOTS_H
#include "../costume-import/coh_costume_import.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CLIENT_COSTUME_RAW_BYTES 641477u
#define COH_CLIENT_COSTUME_INDEX_COUNT (32768u+256u+512u)
#define COH_CLIENT_COSTUME_INDEX_BYTES (COH_CLIENT_COSTUME_INDEX_COUNT*sizeof(uint32_t))
#define COH_CLIENT_COSTUME_PREPARE_STACK_RESERVE 1024u
/* Exact original builder primary slots, including holes and first duplicate
 * spelling. The view borrows raw and index until the last receive completes.
 * No runtime producer, generation or MapServer association is required for this
 * source-pinned local CLIENT default. Do not modify either borrowed span. */
typedef struct {
 CohBytes raw;
 const uint32_t *index;
 uint32_t capacity[3],present[3];
 size_t charged_bytes;
} CohClientCostumeSlots;
/* Caller supplies exactly INDEX_COUNT offsets. Original raw bytes are validated
 * in two bounded passes; the existing digest provider must compute SHA-256 of
 * the entire raw image. All spans (including callback context) are disjoint.
 * Preflight accounts raw, full index, output view, digest/context, its scratch,
 * this stack reserve and retained old/candidate state under the existing8MiB
 * ceiling before callback or mutation. No allocation occurs. On any failure,
 * index and output remain unchanged. Outputs publish together on success. */
CohStatus coh_client_costume_slots_prepare(CohBytes raw,uint32_t *index,
 size_t index_count,const CohCostumeImportDigest *,CohClientCostumeSlots *,
 size_t budget,size_t retained);
#ifdef __cplusplus
}
#endif
#endif
