#ifndef COH_WINE_MAP_PROGRESS_H
#define COH_WINE_MAP_PROGRESS_H

#include <windows.h>

#define COH_MAP_PROGRESS_ENVIRONMENT "COH_WINE_MAP_PROGRESS"
#define COH_MAP_PROGRESS_FORMAT 1
#define COH_MAP_PROGRESS_RECORD_BYTES 128
#define COH_MAP_PROGRESS_MAPPING_BYTES 4096
#define COH_MAP_PROGRESS_FLAG_SATURATED 1

/* Explicit values form the separately hash-receipted diagnostic contract.
 * A stage names the operation about to run unless its name says DONE/ED.
 * Publication is observation only; it never establishes protocol readiness. */
typedef enum CohMapProgressStage {
    COH_MAP_STAGE_INITIALIZED = 1,
    COH_MAP_STAGE_STARTUP = 2,
    COH_MAP_STAGE_MAP_LOAD = 3,
    COH_MAP_STAGE_DB_SETUP = 4,
    COH_MAP_STAGE_READY_PUBLISH = 5,
    COH_MAP_STAGE_READY_PUBLISHED = 6,
    COH_MAP_STAGE_RUNTIME_PRIORITY = 7,
    COH_MAP_STAGE_RUNTIME_PRIORITY_DONE = 8,
    COH_MAP_STAGE_HEAP_VALIDATE = 9,
    COH_MAP_STAGE_HEAP_VALIDATED = 10,
    COH_MAP_STAGE_SG_VERIFY = 11,
    COH_MAP_STAGE_SG_VERIFIED = 12,
    COH_MAP_STAGE_CALLBACKS_ENABLE = 13,
    COH_MAP_STAGE_CALLBACKS_ENABLED = 14,
    COH_MAP_STAGE_RANDOM_SEED = 15,
    COH_MAP_STAGE_ITEM_POWER_REQUEST = 16,
    COH_MAP_STAGE_ITEM_POWER_REQUESTED = 17,
    COH_MAP_STAGE_ERROR_QUEUE_DRAIN = 18,
    COH_MAP_STAGE_ERROR_QUEUE_DRAINED = 19,
    COH_MAP_STAGE_READY_STDOUT = 20,
    COH_MAP_STAGE_LAUNCHER_CONTACT = 21,
    COH_MAP_STAGE_LATE_STARTUP_DONE = 22,
    COH_MAP_STAGE_LOOP_PRE_TICK = 23,
    COH_MAP_STAGE_TICK_BEGIN = 24,
    COH_MAP_STAGE_TICK_TOP = 25,
    COH_MAP_STAGE_DB_COMM = 26,
    COH_MAP_STAGE_DB_COMM_DONE = 27,
    COH_MAP_STAGE_FOLDER_CALLBACKS = 28,
    COH_MAP_STAGE_FOLDER_CALLBACKS_DONE = 29,
    COH_MAP_STAGE_TICK_TOP_DONE = 30,
    COH_MAP_STAGE_ENTITY_UPDATE = 31,
    COH_MAP_STAGE_GAME_LOGIC = 32,
    COH_MAP_STAGE_TICK_BOTTOM = 33,
    COH_MAP_STAGE_TICK_DONE = 34,
    COH_MAP_STAGE_LOOP_POST_TICK = 35,
    COH_MAP_STAGE_SLEEP = 36,
    COH_MAP_STAGE_SLEEP_DONE = 37
} CohMapProgressStage;

typedef struct CohMapProgressRecord {
    char magic[8];
    DWORD format;
    DWORD record_bytes;
    DWORD process_id;
    DWORD main_thread_id;
    volatile DWORD sequence;
    volatile DWORD stage;
    volatile DWORD tick_started;
    volatile DWORD tick_completed;
    volatile DWORD flags;
    DWORD stage_count;
    BYTE reserved[80];
} CohMapProgressRecord;

/* Call once on main: 0 disabled, 1 enabled, -1 requested but rejected.
 * On rejection GetLastError contains the initialization error. */
int cohMapProgressInit(void);
/* Only main calls this function. No platform calls or I/O occur in a marker. */
void cohMapProgressMark(CohMapProgressStage stage);
void cohMapProgressClose(void);

#endif
