#ifndef COH_WORLD_CAPTURE_H
#define COH_WORLD_CAPTURE_H
#include "../local/coh_local.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_WORLD_CAPTURE_BYTES_MAX COH_NET_DECODED_MAX
#define COH_WORLD_CAPTURE_AGGREGATE_MAX (32u*1024u*1024u)
#define COH_WORLD_CAPTURE_STACK_RESERVE 8192u
/* Caller attestations bind one isolated runtime, its exact source/profile,
 * catalog and independently exported existing-character row. They do not
 * establish server/actor authenticity merely by being nonzero. */
typedef struct {
    uint32_t generation,catalog_generation,expected_slot,expected_dbid,expected_map_id;
    uint32_t footer_files,footer_roots,footer_defs_crc,footer_refs_crc;
    uint8_t source_sha256[32],profile_sha256[32],server_run_sha256[32],catalog_sha256[32],character_row_sha256[32];
} CohWorldCaptureBinding;
typedef struct {
    CohWorldCaptureBinding binding;
    CohGroupsInspection structure;
    uint32_t packet_id,ordered_id,payload_bits,byte_aligned,ordered;
    uint64_t transport_lease_generation;
    size_t body_start_bit,payload_bytes,owned_bytes,aggregate_bytes;
} CohWorldCaptureReceipt;
typedef struct CohWorldCapture CohWorldCapture;
/* One allocation, no I/O, no networking. Exact decoded bytes (including command
 * and original padding) are copied, with logical bits/profile separately kept.
 * Borrowed lease and all control/output objects must be disjoint/immutable.
 * *out must be NULL. Only complete new-world normal GROUPS is supported.
 * Budget includes input lease, candidate, 8KiB stack reserve and all caller
 * retained transport/codec/session/catalog/evidence bytes. No partial output. */
CohStatus coh_world_capture_stage(const CohWorldCaptureBinding *,unsigned legacy,
    const CohNetOwnedMessage *,size_t retained_bytes,size_t aggregate_limit,
    CohWorldCapture **out,CohGroupsFailure *);
/* Requires the unchanged local owner's complete structure boundary and exact
 * byte/count/selection/map receipt. This never verifies expected_dbid: local DB
 * wire carries no DBID; that external row assertion remains explicitly separate.
 * Success is permission to export diagnostic bytes, never READY or an actor. */
CohStatus coh_world_capture_confirm(const CohWorldCapture *,const CohLocalDiagnostics *);
CohStatus coh_world_capture_view(const CohWorldCapture *,CohWorldCaptureReceipt *,CohBytes *);
void coh_world_capture_free(CohWorldCapture *);
#ifdef __cplusplus
}
#endif
#endif
