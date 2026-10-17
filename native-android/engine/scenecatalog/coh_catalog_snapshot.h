#ifndef COH_CATALOG_SNAPSHOT_H
#define COH_CATALOG_SNAPSHOT_H
#include "coh_catalog_owner.h"
#include "../scenegraph/runtime_snapshot.h"
typedef struct CohCatalogSnapshot CohCatalogSnapshot;
typedef struct {
    uint32_t generation;
    CohCatalogBinding catalog;
    uint8_t snapshot_sha256[32],run_sha256[32];
} CohCatalogSnapshotBinding;
/* Preparation-side immutable source import, never a live generation permit.
 * Pins must come from independently admitted capture receipts. Exact catalog,
 * source and asset identities are checked against the retained owner. The run
 * digest identifies the capture; it does not authenticate a live session.
 * Input, old, caller retained state and catalog indexes are all budgeted. The
 * catalog span is charged once. Caller serializes ownership/access, keeps input
 * stable, and supplies disjoint output/control storage. Digest scratch belongs
 * in retained_bytes. On refusal old and *out remain unchanged. */
CohStatus coh_catalog_snapshot_create(const CohCatalogSnapshot *old,
    CohCatalogOwner *catalog,CohBytes snapshot,const CohCatalogSnapshotBinding *,
    const CohRuntimeSnapshotBudget *,const CohCatalogDigest *,const CohCancel *,
    CohCatalogSnapshot **out);
CohStatus coh_catalog_snapshot_retain(CohCatalogSnapshot *);
void coh_catalog_snapshot_release(CohCatalogSnapshot *);
size_t coh_catalog_snapshot_owned_bytes(const CohCatalogSnapshot *);
/* Actual retained catalog span, borrowed through last snapshot release. Use
 * pointer+extent comparison to distinguish equal labels on separate owners. */
CohStatus coh_catalog_snapshot_catalog(const CohCatalogSnapshot *,CohBytes *);
/* Borrowed immutable view remains valid through the last owner release. Views
 * are source topology only: no assets, actor, GROUPS, ACK or renderer authority. */
CohStatus coh_catalog_snapshot_view(const CohCatalogSnapshot *,CohBytes *,
    CohCatalogSnapshotBinding *,CohRuntimeSnapshotReport *);
#endif
