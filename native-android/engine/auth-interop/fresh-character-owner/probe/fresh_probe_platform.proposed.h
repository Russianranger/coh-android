/* SOURCE/API PROPOSAL ONLY. No backend, build or Windows execution exists. */
#ifndef COH_FRESH_PROBE_PLATFORM_PROPOSED_H
#define COH_FRESH_PROBE_PLATFORM_PROPOSED_H
#include "../fresh_character_owner.h"
typedef struct FreshProbeLease FreshProbeLease;
typedef struct {
    unsigned initialization_verified, supplied_map_policy_admitted;
    unsigned map_process_file_generation_before, map_process_file_generation_after;
    unsigned checksum_measured_from_actual_probe, fresh_connect_entropy;
    unsigned no_live_tcp_handles, no_live_udp_handles, transport_cleanup_complete;
    unsigned private_policy_handle_closed, map_process_handle_closed, cleanup_complete;
} FreshProbePlatformDiagnostics;
/* Import/constructor has no platform side effect. open is one-shot and returns
 * an opaque lease even on partial failure when independent teardown is needed.
 * No raw private policy contents or process/file selectors escape this API. */
FreshProbeLease *fresh_probe_platform_open(int preflight, const char *private_policy_path);
CohStatus fresh_probe_platform_config(FreshProbeLease *, CohFreshCharacterConfig *);
uint64_t fresh_probe_monotonic_ms(void);
void fresh_probe_pause(void);
/* Reobserve the retained exact Map process/file generation; no Map socket or
 * registry/profile/SQL action. preflight requires no Map input/observation. */
CohStatus fresh_probe_platform_before_begin(FreshProbeLease *);
/* Called after controller destruction. Attempts ALL independent cleanup paths,
 * preserves fixed failure status and does not delete external Map/profile/DB.
 * It must retain failed owned handle references for the consuming destroy. */
CohStatus fresh_probe_platform_finish(FreshProbeLease *);
CohStatus fresh_probe_platform_diagnostics(const FreshProbeLease *, FreshProbePlatformDiagnostics *);
CohStatus fresh_probe_platform_destroy(FreshProbeLease **);
#endif
