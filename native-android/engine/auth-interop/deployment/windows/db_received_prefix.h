/* NONSHIPPING: scalar command-header observations, never a body/grant API. */
#ifndef COH_DEV_DB_RECEIVED_PREFIX_H
#define COH_DEV_DB_RECEIVED_PREFIX_H
#include "../../../dbclient/coh_db_session.h"
#define COH_DEV_DB_PREFIX_MAX 16u
/* Exact DBServer->client prefix of Common/comm_backend.h, COMM_MAX_CMD=2.
 * QueueServer-only commands after this enum prefix are intentionally UNKNOWN. */
#define COH_DEV_DB_COMMANDS(X) \
 X(2,SEND_PLAYERS) X(3,MSG) X(4,MAP_CONNECT) X(5,DELETE_OK) \
 X(6,SEND_COSTUME) X(7,SEND_POWERSET_NAMES) X(8,ACCOUNTSERVER_CHARCOUNT) \
 X(9,ACCOUNTSERVER_CATALOG) X(10,ACCOUNTSERVER_CLIENTAUTH) \
 X(11,ACCOUNTSERVER_PLAYNC_AUTH_KEY) X(12,ACCOUNTSERVER_NOTIFYREQUEST) \
 X(13,ACCOUNTSERVER_INVENTORY) X(14,ACCOUNTSERVER_UNAVAILABLE) X(15,CONPRINT) \
 X(16,RENAME_RESPONSE) X(17,UNLOCK_CHARACTER_RESPONSE) X(18,CHECK_NAME_RESPONSE) \
 X(19,LOGIN_DIALOG_RESPONSE) X(20,QUEUE_POSITION) X(21,CAN_START_STATIC_MAP_RESPONSE)
enum { COH_DEV_DB_NO_HEADER=0, COH_DEV_DB_UNKNOWN=1 };
typedef struct {
    uint32_t kind,phase;
    unsigned header_decoded,legacy,compressed;
} CohDevDbPrefixEntry;
typedef struct {
    uint32_t count,total_seen,instances,service_calls;
    unsigned context_verified,retired,truncated;
    CohDevDbPrefixEntry entries[COH_DEV_DB_PREFIX_MAX];
} CohDevDbReceivedPrefix;
/* Read only between service calls. No session/raw message/identity selector.
 * First16 successful copied-message headers survive destroy. They are NOT
 * a first-unsupported witness or body parser/transport acceptance evidence.
 * A second lifetime, generation/transport-version change or reentry invalidates binding.
 * Outputs remain unchanged on failure; observer/session/current-message
 * storage aliases refuse. The opaque UDP allocation is not a getter output. */
CohStatus coh_dev_db_received_prefix(CohDevDbReceivedPrefix *out);
static inline const char *coh_dev_db_command_name(uint32_t kind) {
    switch(kind) {
    case COH_DEV_DB_NO_HEADER:return "NONE";
    case COH_DEV_DB_UNKNOWN:return "UNKNOWN";
#define COH_DEV_DB_NAME(value,name) case value:return "DBGAMESERVER_" #name;
    COH_DEV_DB_COMMANDS(COH_DEV_DB_NAME)
#undef COH_DEV_DB_NAME
    default:return "UNKNOWN";
    }
}
#endif
