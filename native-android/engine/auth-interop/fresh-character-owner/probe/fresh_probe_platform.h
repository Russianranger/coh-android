/* NONSHIPPING platform contract. Windows backend is a separate obligation. */
#ifndef COH_FRESH_PROBE_PLATFORM_H
#define COH_FRESH_PROBE_PLATFORM_H
#include "../fresh_character_owner.h"
typedef struct FreshProbeLease FreshProbeLease;
typedef struct {
    unsigned initialization_verified, supplied_map_policy_admitted;
    unsigned map_process_file_generation_before, map_process_file_generation_after;
    unsigned checksum_measured_from_actual_probe, fresh_connect_entropy;
    unsigned no_live_tcp_handles, no_live_udp_handles, transport_cleanup_complete;
    unsigned private_policy_handle_closed, map_process_handle_closed, cleanup_complete;
} FreshProbePlatformDiagnostics;
/* No import/constructor effects. Open returns a lease on partial failure when
 * teardown is required; config then refuses. No raw policy value may escape.
 * Backend must reject any allocation runtime until actual private policy and
 * independently owned same-realm Map process/file generations are admitted. */
FreshProbeLease *fresh_probe_platform_open(int preflight,const char *private_policy_path);
CohStatus fresh_probe_platform_config(FreshProbeLease *,CohFreshCharacterConfig *);
uint64_t fresh_probe_monotonic_ms(void);
void fresh_probe_pause(void);
CohStatus fresh_probe_platform_before_begin(FreshProbeLease *);
/* After controller destruction; attempts independent cleanup on every path.
 * Does not remove external Map/profile/SQL or imply allocation rollback.
 * A failed finish retains any still-owned handle for consuming destroy. */
CohStatus fresh_probe_platform_finish(FreshProbeLease *);
CohStatus fresh_probe_platform_diagnostics(const FreshProbeLease *,FreshProbePlatformDiagnostics *);
CohStatus fresh_probe_platform_destroy(FreshProbeLease **);
#endif
