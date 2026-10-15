#ifndef COH_NATIVE_LOGIN_H
#define COH_NATIVE_LOGIN_H
#include "../auth/coh_auth.h"
#include "../network/coh_net_udp.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum { COH_LOGIN_IDLE, COH_LOGIN_CONNECTING, COH_LOGIN_WAIT_HELLO,
    COH_LOGIN_WAIT_LOGIN, COH_LOGIN_WAIT_SHARDS, COH_LOGIN_SHARDS_READY,
    COH_LOGIN_WAIT_PLAY, COH_LOGIN_AUTHORIZED, COH_LOGIN_CLOSED,
    COH_LOGIN_SUSPENDED, COH_LOGIN_CANCELLED, COH_LOGIN_TIMED_OUT,
    COH_LOGIN_FAILED, COH_LOGIN_UNSUPPORTED } CohLoginState;
typedef struct {
    const CohAuthCrypto *crypto; /* borrowed for controller lifetime */
    uint64_t connect_timeout_ms, reply_timeout_ms;
    unsigned receive_budget; /* 1..16 nonblocking reads of at most1024 bytes */
} CohLoginConfig;
typedef struct CohLogin CohLogin;
typedef struct {
    CohLoginState state;
    uint64_t sockets_opened, sockets_closed, sent_bytes, received_bytes,
        received_frames, failures, cancellations, suspends;
    size_t pending_send_bytes, buffered_receive_bytes;
    uint32_t protocol, shard_count;
    uint8_t remote_failure_command, remote_failure_reason;
    int last_system_error, password_retained;
} CohLoginDiagnostics;
/* Sensitive result; caller owns it and must wipe after DB handoff. This is
 * protocol receipt state, NOT an independent proof of a real account login.
 * Session/update keys, cookies, names and packet bodies never enter diagnostics. */
typedef struct {
    uint32_t protocol;
    char account_name[15];
    CohAuthLoginOk account;
    CohAuthPlayOk play;
    CohAuthShard shard;
} CohLoginAuthorization;
CohLoginConfig coh_login_default_config(const CohAuthCrypto *);
CohLogin *coh_login_create(const CohLoginConfig *);
void coh_login_destroy(CohLogin *);
/* Numeric authorized unicast endpoint only; no default shard, DNS or fake-auth
 * fallback. Account <=14 ASCII bytes/password <=16 bytes are copied only until
 * the source login request is serialized. The normalized account identifier
 * remains in memory for DB handoff and is never logged. begin/retry requires fresh
 * credentials; suspend/close/cancel destroys retained secrets and socket state.
 * Only one owner thread calls this API; Android UI must enqueue owner requests. */
CohStatus coh_login_begin(CohLogin *, CohNetEndpoint authorized_endpoint,
    const char *account, const char *password, uint32_t subscription,
    uint16_t source_platform_flags, uint64_t now_ms);
/* Bounded nonblocking TCP connect/send/receive. Supports global-auth framing,
 * the pinned two-byte inclusive length convention, and normal shard lists.
 * Queue-server messages and unsupported profiles fail explicitly. Times are
 * monotonic; cancellation is polled between system calls, never on another fd
 * owner. No automatic credential retry or background authentication replay. */
CohStatus coh_login_service(CohLogin *, uint64_t now_ms, CohCancel);
CohStatus coh_login_shards(const CohLogin *, CohAuthShards *);
CohStatus coh_login_choose(CohLogin *, uint8_t shard_id, uint64_t now_ms);
CohStatus coh_login_authorization(const CohLogin *, CohLoginAuthorization *);
void coh_login_close(CohLogin *);
void coh_login_suspend(CohLogin *);
void coh_login_cancel(CohLogin *);
void coh_login_diagnostics(const CohLogin *, CohLoginDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
