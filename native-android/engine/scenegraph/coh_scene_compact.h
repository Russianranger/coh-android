#ifndef COH_SCENE_COMPACT_H
#define COH_SCENE_COMPACT_H
#include "coh_scenegraph.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohSgCompact CohSgCompact;
typedef struct {
    uint32_t generation,catalog_generation,asset_generation;
    uint8_t source_sha256[32],catalog_sha256[32];
} CohSgCompactBinding;
typedef struct {size_t aggregate_limit,retained_bytes;} CohSgCompactBudget;
typedef struct {
    uint32_t files,slots,definitions,children,source_defs_crc,source_refs_crc,source_active_roots;
    size_t owned_bytes,input_bytes,prior_owned_bytes,prior_input_bytes,retained_bytes;
    size_t peak_record_bytes,stack_reserve,aggregate_peak_bytes;
    uint32_t roots_bound,assets_bound;
} CohSgCompactReport;
typedef struct {
    uint32_t file,slot,in_use,mod_time,child_first,child_count;
    const char *name;CohBytes wire;size_t wire_bits;unsigned aligned;
} CohSgCompactDefinition;
typedef struct {uint32_t resolved;CohSgMatrix matrix;} CohSgCompactChild;
typedef struct {const char *name;uint32_t bounds_checksum,slots,generation;} CohSgCompactFile;
#define COH_SG_COMPACT_DIAGNOSTICS_MAX 16u
typedef struct {
    uint32_t file,slot,child;
    char file_name[COH_REP_NAME_MAX],definition_name[COH_REP_NAME_MAX],name[COH_REP_NAME_MAX];
} CohSgCompactMissing;
typedef struct {
    CohSgCompactReport topology;
    uint32_t references_checked,missing_references,missing_stored,diagnostics_truncated;
    uint32_t complete_name_closure,definitions_crc_verified,references_crc_verified;
    CohSgCompactMissing missing[COH_SG_COMPACT_DIAGNOSTICS_MAX];
} CohSgCompactAudit;
/* Complete catalog topology only: COHCAT01 does not contain root transforms.
 * roots_bound/assets_bound remain zero. Neither name CRC nor this caller-bound
 * source/digest identity authenticates geometry, material or world admission.
 * Input must be independently authenticated and immutable. The caller retains
 * its entire backing allocation until all snapshots borrowing it are retired.
 * No input copy/pin acquisition occurs. All caller objects are disjoint.
 * Build uses two complete A catalog walks; cancellation or failure leaves
 * *candidate/report unchanged. *candidate must be NULL. Old index+old input,
 * candidate+new input, record scratch and stack reserves are charged even when
 * the old/new spans alias. retained_bytes includes all other graphs/catalogs,
 * lookup indexes, assets/GPU views, input allocation slack and caller scratch.
 * Counts are payload reservations, not allocator metadata or process RSS.
 * Exact next generation and complete prior binding prevent stale publication.
 * Catalog/asset generations cannot regress. A retained catalog generation
 * cannot change catalog bytes or producer-source identity. A fresh owner is
 * required for epoch reset. asset_generation remains a caller label, not an
 * admitted asset manifest; this module never acquires asset resources.
 * Run off the rendering thread. Native owned cap remains32MiB; aggregate96MiB. */
CohStatus coh_sg_compact_build(const CohSgCompact *old,CohBytes,
    const CohSgCompactBinding *,const CohSgCompactBudget *,const CohCancel *,
    CohSgCompact **candidate,CohSgCompactReport *);
/* Separate bounded diagnostic, never a snapshot publisher. Both complete walks
 * must validate before audit output changes. Returns COH_OK for complete name
 * closure or COH_NOT_FOUND with every missing edge counted and the first 16
 * identities copied in original file/slot/child order. No placeholder survives
 * the call; no graph or borrowed views escape. Other errors leave output intact.
 * Missing closure does not establish cycle/depth validity or root reachability.
 * Source definition CRC is recomputed; reference CRC cannot be recomputed
 * without the separately received GROUPS roots. Root/asset flags remain zero.
 * The output object is added to the aggregate reservation; internal temporary
 * audit fits the existing compact stack reserve. Caller input pin and all
 * other retained resources still belong in budget.retained_bytes. */
CohStatus coh_sg_compact_audit(CohBytes,const CohSgCompactBinding *,
    const CohSgCompactBudget *,const CohCancel *,CohSgCompactAudit *);
CohStatus coh_sg_compact_publish(CohSgCompact **current,CohSgCompact **candidate,
    CohSgCompact **retired);
/* Serialized caller publication; no atomics or implicit retirement. Free the
 * returned old snapshot only after all borrowers acknowledge, then release its
 * external catalog pin. Free releases structural pools, never borrowed input. */
void coh_sg_compact_free(CohSgCompact *);
CohStatus coh_sg_compact_report(const CohSgCompact *,CohSgCompactReport *);
CohStatus coh_sg_compact_file(const CohSgCompact *,uint32_t index,CohSgCompactFile *);
CohStatus coh_sg_compact_slot(const CohSgCompact *,uint32_t file,uint32_t slot,uint32_t *index);
CohStatus coh_sg_compact_name(const CohSgCompact *,const char *,uint32_t *index);
/* Name/wire views borrow the catalog until snapshot retirement. Exact retained
 * wire can be decoded through existing definition/metadata parsers off-thread,
 * with explicit scratch budget and normal disposal; it is not render-ready. */
CohStatus coh_sg_compact_definition(const CohSgCompact *,uint32_t index,CohSgCompactDefinition *);
CohStatus coh_sg_compact_child(const CohSgCompact *,uint32_t index,CohSgCompactChild *);
#ifdef __cplusplus
}
#endif
#endif
