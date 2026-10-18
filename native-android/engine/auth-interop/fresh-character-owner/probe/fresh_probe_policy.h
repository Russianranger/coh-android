/* Private fixed-record parsing only. No process, file or readiness admission. */
#ifndef COH_FRESH_PROBE_POLICY_H
#define COH_FRESH_PROBE_POLICY_H
#include "../fresh_character_owner.h"
#define FRESH_PROBE_POLICY_BYTES 96u
typedef struct {
    CohNetEndpoint auth_endpoint, map_endpoint;
    uint32_t map_id, map_pid;
    uint64_t map_creation_filetime;
    uint8_t map_executable_sha256[32], operation_nonce[16];
} FreshProbeMapPolicy;
/* The caller owns and wipes the private record and result. Fixed LE record;
 * no allocation, text, authentication, Map readiness or executable admission.
 * Misaligned/overlapping output refuses. Failed output is unchanged. */
CohStatus fresh_probe_decode_policy(CohBytes, FreshProbeMapPolicy *);
#endif
