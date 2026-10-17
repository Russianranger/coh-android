#ifndef COH_MAP_SCENE_RECORD_H
#define COH_MAP_SCENE_RECORD_H
#include "runtime_graph.h"
#include "../mapclient/coh_mapclient.h"
#include "../scenecatalog/coh_catalog_owner.h"
typedef struct CohMapSceneRecord CohMapSceneRecord;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;} CohMapSceneRecordBudget;
typedef struct {
 CohMapSceneLease receive;
 uint8_t packet_sha256[32];
 size_t owned_bytes,aggregate_reserved_bytes;
 uint32_t actual_client_loan_verified,session_owner_retained;
} CohMapSceneRecordReport;
/* Synchronous actual receive EVIDENCE only. Must run inside client's actual
 * scene callback; copied/caller-fabricated events cannot pass its opaque getter.
 * Copies and hashes exact decoded allocation, logical end and post-command
 * cursor. Report's reader points into immutable owned storage until last release.
 * Provider hashes actual bytes; callback/provider contexts are caller-charged.
 * Client is NOT retained; derived IDs are local correlation observations, not
 * durable session tokens. selectedDBID provenance/source/world stay unbound.
 * 32MiB owned/96MiB aggregate maximum. Automatically charges actual borrowed
 * network loan + complete copied owner +64KiB local reservation; retained_bytes
 * adds every other live owner/allocation/slack/provider stack. No live/source
 * witness, selected actor, ACK or authority is synthesized by recording bytes.
 * All known controls/event/input spans disjoint. Opaque client/provider/cancel
 * allocations additionally caller-disjoint. Callbacks cannot reenter client or
 * mutate source. Caller serializes access/refs. *out initiallyNULL. Failure
 * preserves out/report/event and releases all candidate allocations. */
CohStatus coh_map_scene_record_create(const CohMapClient *,const CohMapSceneObservation *,
 const CohMapSceneRecordBudget *,const CohCatalogDigest *,const CohCancel *,
 CohMapSceneRecord **out,CohMapSceneRecordReport *);
CohStatus coh_map_scene_record_retain(CohMapSceneRecord *);
void coh_map_scene_record_release(CohMapSceneRecord *);
/* Value copy with immutable owned bytes, borrowed through last record ref.
 * Output cannot overlap record object or its complete allocation. */
CohStatus coh_map_scene_record_view(const CohMapSceneRecord *,CohMapSceneRecordReport *);
#endif
