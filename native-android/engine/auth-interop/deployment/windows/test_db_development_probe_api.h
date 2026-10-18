/* Controlled probe shell: no actual platform, entropy, digest or controller. */
#ifndef COH_TEST_DB_DEVELOPMENT_PROBE_API_H
#define COH_TEST_DB_DEVELOPMENT_PROBE_API_H
#define COH_DB_WIN_TEST 1
#include "db_udp_winsock.h"
#include "auth_db_development_owner.h"
int coh_win_initialize(void);
int coh_win_finish(void);
unsigned coh_win_open_handles(void);
int coh_win_limits(unsigned,unsigned,int);
static uint64_t probe_now(void);
static void probe_pause(void);
static int probe_entropy(uint32_t *);
static int probe_checksum(uint8_t[16]);
#endif
