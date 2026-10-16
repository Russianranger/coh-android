#ifndef COH_PROCESS_MEMORY_H
#define COH_PROCESS_MEMORY_H
#include "coh_perf_bridge.h"
#ifdef __cplusplus
extern "C" {
#endif

#define COH_PROCESS_MEMORY_TEXT_LIMIT 16384u
#define COH_PROCESS_MEMORY_READ_LIMIT 32u
typedef enum {
    COH_PROCESS_MEMORY_NONE,
    COH_PROCESS_MEMORY_SMAPS_ROLLUP,
    COH_PROCESS_MEMORY_STATUS
} CohProcessMemorySource;
typedef struct {
    uint64_t bytes;
    CohStatus status; /* COH_OK means measured, including a real zero. */
    int system_error; /* errno for OS failures; zero for parser/limit failures. */
    CohProcessMemorySource source;
} CohProcessMemoryValue;
typedef struct {
    CohProcessMemoryValue rss, pss;
    CohStatus rollup_status, status_file_status;
    int rollup_errno, status_file_errno;
    uint32_t files_opened, read_calls;
    uint64_t bytes_read;
} CohProcessMemorySnapshot;

/* Pure, bounded parser of an entire proc file. smaps_rollup requires exactly one
 * Rss and Pss; status requires exactly one VmRSS. Units must be literal kB
 * (1024 bytes), unsigned decimal, no trailing junk/embedded NUL. Unknown lines
 * are skipped; malformed/duplicate required fields reject the entire input.
 * A missing required field returns COH_NOT_FOUND. Output unchanged on error.
 * This is OS measurement syntax, not an original game algorithm. */
CohStatus coh_process_memory_parse(CohProcessMemorySource, const char *, size_t,
                                  CohProcessMemorySnapshot *);
/* Linux/Android only: fixed /proc/self/smaps_rollup, then status for RSS if
 * rollup fails. No smaps walk, subprocess, PID parameter, heap allocation or
 * guessed PSS. Each file is capped at TEXT_LIMIT bytes and READ_LIMIT read
 * attempts (EINTR counts). Opens/close are not application-time-bounded syscalls.
 * Run on a control/export worker, NEVER GL-frame/audio/simulation hot paths.
 * Writes an explicit snapshot even on failure. COH_OK means at least RSS was
 * measured, NOT that PSS is known. Unsupported platforms return COH_UNSUPPORTED.
 * status-file RSS is a kernel approximate resident count; rollup is preferred.
 * Sampling two proc files is not atomic. Caller owns timestamp/generation. */
CohStatus coh_process_memory_sample(CohProcessMemorySnapshot *);
/* Only measured fields are submitted. Validate all fields before any mutation.
 * Serialize with bridge owner or copy the snapshot through a bounded mailbox.
 * Failed samples do not replace historical bridge gauges with fake zero. A
 * bridge known flag describes prior accepted observations; export this latest
 * snapshot alongside it to distinguish unavailable/stale current measurements.
 * Returns COH_NOT_FOUND if neither field was measured. */
CohStatus coh_process_memory_apply(const CohProcessMemorySnapshot *, CohPerfBridge *);
/* Bounded export/control-thread JSON. Known/source/status/errno are explicit.
 * needed includes NUL. COH_LIMIT empties output when cap>0. */
CohStatus coh_process_memory_json(const CohProcessMemorySnapshot *, char *, size_t,
                                 size_t *needed);
#ifdef __cplusplus
}
#endif
#endif
