/* Closed, read-only constructor metadata backend. No production admission. */
#ifndef COH_LIVE_DIRECTORY_CORE_H
#define COH_LIVE_DIRECTORY_CORE_H
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

#define COH_LIVE_ROOT_MAX 32u
#define COH_LIVE_CURSOR_MAX 16u
#define COH_LIVE_HEAP_MAX (32u * 1024u * 1024u)
#define COH_LIVE_PATH_MAX 1024u
#define COH_LIVE_NAME_MAX 259u
#define COH_LIVE_NAMES_MAX 8192u
#define COH_LIVE_WIRE_MAX 27944u
#define COH_LIVE_SYMLINK_MAX 16u

/* Only directory bindings from an independently authenticated finalized PRoot
 * descriptor may be supplied. These pins are real host values, not guest UID. */
typedef struct CohLiveRootSpec {
    const char *guest_prefix, *host_root;
    uint64_t device, inode;
    uint32_t uid;
} CohLiveRootSpec;
typedef struct CohLiveNamespace CohLiveNamespace;
typedef struct CohLiveDirectory CohLiveDirectory;
typedef struct CohLiveError {
    int error_number;
    uint64_t rows_emitted;
    int fallback_allowed;
} CohLiveError;
typedef struct CohLiveStats {
    uint64_t metadata_requests, names_opened, batches, skipped_missing;
    size_t owned_heap_bytes, peak_heap_bytes;
} CohLiveStats;

/* Return 1 on success, 0 on refusal. Caller must serialize operations on a
 * namespace. A namespace closes all of its owned cursors. No borrowed FD is
 * closed; all internal descriptors are O_CLOEXEC and ownership is exclusive. */
int coh_live_namespace_open(CohLiveNamespace **out, const CohLiveRootSpec *roots,
    size_t count, uint32_t native_uid, uint32_t guest_uid,
    int show_dot_files, int case_sensitive, CohLiveError *error);
int coh_live_directory_open(CohLiveNamespace *space, CohLiveDirectory **out,
    const char *guest_directory, const unsigned char operation[16],
    const unsigned char directory[16], CohLiveError *error);
/* A successful final frame is explicit. Asking again after final is an error.
 * Returned wire bytes are an owned cursor buffer, valid until the next call.
 * Failure never emits a partial frame. After any successful nonempty frame,
 * every later failure is terminal and stock fallback is forbidden. */
int coh_live_directory_next(CohLiveDirectory *cursor,
    const unsigned char **wire, size_t *length, CohLiveError *error);
void coh_live_directory_close(CohLiveDirectory *cursor);
void coh_live_namespace_close(CohLiveNamespace *space);
int coh_live_namespace_validate(CohLiveNamespace *space, CohLiveError *error);
void coh_live_namespace_stats(const CohLiveNamespace *space, CohLiveStats *out);
int coh_live_directory_identity(CohLiveDirectory *cursor, uint64_t *device,
    uint64_t *inode, uint32_t *uid, CohLiveError *error);
const char *coh_live_directory_guest_path(const CohLiveDirectory *cursor);

/* Constructor-only projection: long ASCII name, size low, last-write
 * FILETIME, and DIRECTORY/READONLY/HIDDEN/SYSTEM are current authoritative
 * fields. Size high is emitted from current stat but is nonauthoritative for
 * this consumer. Creation/access/short-name/reserved fields are canonical zero and
 * deliberately nonauthoritative. This is not a general WFD API replacement. */
#endif
