#ifndef COH_DB_HANDOFF_PRIVATE_H
#define COH_DB_HANDOFF_PRIVATE_H
#include "coh_db_handoff_owner.h"
/* Trusted integration seam only. A successful claim consumes and wipes the
 * owner's cookie; caller must wipe output after Map begin, including failures.
 * Wrong/stale generations refuse without consuming. No retry after success.
 * session_generation denotes DBSession's monotonic transport incarnation;
 * receipt_generation is caller attestation, not cryptographic provenance. */
CohStatus coh_db_handoff_owner_claim(CohDbHandoffOwner *, uint32_t session_generation,
    uint32_t selection_generation, CohDbSessionHandoff *);
/* Private bounded allocator seam for embedding/negative qualification. Both
 * callbacks required; allocate returns fresh disjoint storage of the requested
 * size (or NULL), deallocate observes zeroed storage. Callbacks must not reenter
 * session/owner APIs. Output must initially be NULL. No source DTO input. */
typedef struct {
    void *context;
    void *(*allocate)(void *, size_t);
    void (*deallocate)(void *, void *, size_t);
} CohDbHandoffAllocator;
CohStatus coh_db_session_take_handoff_owner_alloc(CohDbSession *,
    const CohDbHandoffAllocator *, CohDbHandoffOwner **);
#endif
