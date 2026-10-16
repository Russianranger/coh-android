#ifndef COH_AUTH_INTEROP_H
#define COH_AUTH_INTEROP_H
#include "../live/coh_live.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_INTEROP_MAPS_MAX 2u
/* Explicit disposable deployment policy. Contains no credentials/session keys.
 * Fields never create proof that a server exists or implements the policy. */
typedef struct {
    CohNetEndpoint auth, db, maps[COH_INTEROP_MAPS_MAX];
    unsigned map_count;
    uint8_t shard_id;
    uint32_t character_slot;
    CohDbLogin db_policy;
    uint64_t timeout_ms;
} CohAuthInteropProfile;
typedef enum {
    COH_INTEROP_POLICY_OK, COH_INTEROP_POLICY_ENDPOINT,
    COH_INTEROP_POLICY_SELECTION, COH_INTEROP_POLICY_PROTOCOL,
    COH_INTEROP_POLICY_VERSION, COH_INTEROP_POLICY_CHECKSUM,
    COH_INTEROP_POLICY_AUTH_INJECTION, COH_INTEROP_POLICY_BYPASS,
    COH_INTEROP_POLICY_TIMEOUT
} CohAuthInteropPolicyFailure;
/* Validates before opening sockets or reading credentials. No output mutation
 * except the numeric failure. Rejects bypass flags and injected auth data. */
CohStatus coh_auth_interop_validate(const CohAuthInteropProfile *,
                                  CohAuthInteropPolicyFailure *);
/* Exact configured endpoint and nonzero-generation check; callback gets no
 * account/session/cookie. The immutable profile must outlive the CohLive owner. */
CohStatus coh_auth_interop_approve_map(void *profile, CohNetEndpoint, uint32_t generation);
/* Fills a new encrypted v5 live config transactionally. Profile lifetime is
 * borrowed; the provider must be the separately qualified public provider. */
CohStatus coh_auth_interop_config(const CohAuthInteropProfile *,
                                const CohAuthCrypto *, CohLiveConfig *);
/* Numeric redacted receipt. Protocol progress never implies independent real
 * server authentication, selected DBID, authoritative rendering or acceptance. */
CohStatus coh_auth_interop_report(const CohLiveDiagnostics *, uint64_t elapsed_ms,
                                int interrupted, char *, size_t, size_t *);
#ifdef __cplusplus
}
#endif
#endif
