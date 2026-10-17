#ifndef COH_MAPCLIENT_OWNED_H
#define COH_MAPCLIENT_OWNED_H
#include "coh_mapclient.h"
#include "../dbclient/coh_db_handoff_owner.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
 uint32_t expected_db_session_generation,expected_selection_generation;
 uint32_t connect_id,address_index;uint64_t now_ms;unsigned endpoint_authorized;
} CohMapOwnedBegin;
/* Optional strong bridge TU. Requires actual opaque DBSession handoff owner;
 * no raw DTO/DBID/metadata setter exists. Expected generations are stale guards,
 * not replacement labels. Explicit endpoint authorization remains required.
 * Receipt generation is caller attestation, not proof of encrypted AuthServer.
 * Preflight/stale refusal leaves owner unclaimed. Cancellation or any failure
 * AFTER successful claim retires/wipes owner; retry is forbidden. A successful
 * client retains the owner through terminal lifecycle, even after DB destruction.
 * All APIs serialized; callbacks only mutate their own context. Controls and
 * opaque client/owner allocations caller-disjoint. Never entity/world authority.
 * Link this bridge TU when using this API; its strong DB references deliberately
 * extract DBSession from a static archive. Raw MapClient APIs do not require it. */
CohStatus coh_map_client_begin_owned(CohMapClient *,CohDbHandoffOwner *,
 const CohMapOwnedBegin *,const CohCancel *);
/* Actual retained owner metadata, nonsecret. Refuses raw begin/unbound/retired
 * owners. Output unchanged on failure; client/output disjoint. */
CohStatus coh_map_client_handoff_metadata(const CohMapClient *,CohDbHandoffMetadata *);
#ifdef __cplusplus
}
#endif
#endif
