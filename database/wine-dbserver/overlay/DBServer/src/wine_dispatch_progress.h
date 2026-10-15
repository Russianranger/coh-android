#ifndef COH_WINE_DISPATCH_PROGRESS_H
#define COH_WINE_DISPATCH_PROGRESS_H

#include <windows.h>

#define COH_DB_PROGRESS_ENVIRONMENT "COH_WINE_DB_PROGRESS"
#define COH_DB_PROGRESS_FORMAT 1
#define COH_DB_PROGRESS_RECORD_BYTES 128
#define COH_DB_PROGRESS_MAPPING_BYTES 4096
#define COH_DB_PROGRESS_FLAG_SATURATED 1

/* Explicit values are part of the versioned, hash-receipted diagnostic format.
 * A stage names the operation about to run, never its successful completion. */
typedef enum CohDbProgressStage {
    COH_DB_STAGE_INITIALIZED = 1,
    COH_DB_STAGE_STARTUP = 2,
    COH_DB_STAGE_DB_INIT = 3,
    COH_DB_STAGE_MAIN_LOOP = 4,
    COH_DB_STAGE_MSG_SCAN = 5,
    COH_DB_STAGE_SQL_KEEPALIVE_CHECK = 6,
    COH_DB_STAGE_SQL_KEEPALIVE_FOREGROUND = 7,
    COH_DB_STAGE_SQL_KEEPALIVE_QUEUE = 8,
    COH_DB_STAGE_SQL_FIFO_TICK = 9,
    COH_DB_STAGE_DELINK_MAPS = 10,
    COH_DB_STAGE_DELINK_LAUNCHERS = 11,
    COH_DB_STAGE_SQL_MEMORY_PRESSURE = 12,
    COH_DB_STAGE_NM_MONITOR = 13,
    COH_DB_STAGE_SVRMON_UPDATES = 14,
    COH_DB_STAGE_AUTO_START = 15,
    COH_DB_STAGE_AUTH_STATUS = 16,
    COH_DB_STAGE_AUTH_RECONNECT = 17,
    COH_DB_STAGE_WAITING_ENTITIES = 18,
    COH_DB_STAGE_DB_RELAY = 19,
    COH_DB_STAGE_CLIENT_LINKS = 20,
    COH_DB_STAGE_BEACON_LAUNCHERS = 21,
    COH_DB_STAGE_STATS = 22,
    COH_DB_STAGE_SHARD_CHAT = 23,
    COH_DB_STAGE_LOG_STATS = 24,
    COH_DB_STAGE_AUCTION = 25,
    COH_DB_STAGE_OVERLOAD = 26,
    COH_DB_STAGE_TEMP_LOCKS = 27,
    COH_DB_STAGE_CONSOLE_TITLE = 28,
    COH_DB_STAGE_EXIT_REQUEST = 29,
    COH_DB_STAGE_FOLDER_CALLBACKS = 30,
    COH_DB_STAGE_POOL_COMPACT = 31,
    COH_DB_STAGE_SHUTDOWN_TICK = 32,
    COH_DB_STAGE_CONSOLE_POLL = 33,
    COH_DB_STAGE_CONSOLE_READ = 34,
    COH_DB_STAGE_CONSOLE_COMMAND = 35,
    COH_DB_STAGE_LOOP_DONE = 36,
    COH_DB_STAGE_READY = 37
} CohDbProgressStage;

typedef struct CohDbProgressRecord {
    char magic[8];
    DWORD format;
    DWORD record_bytes;
    DWORD process_id;
    DWORD main_thread_id;
    volatile DWORD sequence;
    volatile DWORD stage;
    volatile DWORD loop_count;
    volatile DWORD flags;
    DWORD stage_count;
    BYTE reserved[84];
} CohDbProgressRecord;

/* Call once from main: 0 disabled, 1 enabled, -1 requested but rejected.
 * On rejection GetLastError contains the initialization error. */
int cohDbProgressInit(void);
/* Only main calls this function. No platform calls or I/O occur in a marker. */
void cohDbProgressMark(CohDbProgressStage stage);
void cohDbProgressClose(void);

#endif
