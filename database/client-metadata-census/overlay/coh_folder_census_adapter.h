#ifndef COH_FOLDER_CENSUS_ADAPTER_H
#define COH_FOLDER_CENSUS_ADAPTER_H
/* Qualification prototype only. No production caller registers this context.
 * The decoder is a bounded format parser, not provider authentication. A future
 * independently qualified caller must establish a complete current generation,
 * exact native/Wine mapping and an owned quiescent provider lease. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "coh_folder_census.h"

#define COH_CENSUS_NATIVE_PATH_MAX 260u
#define COH_CENSUS_ADAPTER_MARKER "COH_CLIENT_METADATA_CENSUS_PROTOTYPE_V1"
#ifndef COH_CENSUS_CURRENT_THREAD_ID
#define COH_CENSUS_CURRENT_THREAD_ID GetCurrentThreadId
#endif

typedef int (*CohFolderCensusLease)(void *owner, const char *native_root,
    const char *relative_directory, const unsigned char generation_token[32]);

typedef struct CohFolderCensusContext {
    CohFolderCensusView view;
    uint32_t directory_offsets[16384];
    char native_root[COH_CENSUS_NATIVE_PATH_MAX];
    unsigned char generation_token[32];
    const void *cache_owner;
    CohFolderCensusLease lease;
    void *lease_owner;
    uint32_t owner_thread;
    int expected_pig_count;
    int registered;
} CohFolderCensusContext;

typedef struct CohFolderCensusDirectory {
    const CohFolderCensusView *view;
    uint32_t ordinal;
    uint32_t count;
} CohFolderCensusDirectory;

/* Unregistered in all production source. Context/input/index storage must stay
 * owned and immutable until Clear; registrations cannot move by struct copy. */
static CohFolderCensusContext coh_folder_census_context;

static void cohFolderCensusClearContext(CohFolderCensusContext *context)
{
    if (context) memset(context, 0, sizeof(*context));
}

static int cohFolderCensusRoot(const char *input, char output[COH_CENSUS_NATIVE_PATH_MAX])
{
    size_t i, n;
    if (!input || !*input) return 0;
    for (n = 0; n < COH_CENSUS_NATIVE_PATH_MAX && input[n]; ++n) {}
    if (n >= COH_CENSUS_NATIVE_PATH_MAX) return 0;
    for (i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)input[i];
        if (c < 32 || c >= 127 || c == '*' || c == '?' || c == '"' || c == '|') return 0;
        output[i] = c == '\\' ? '/' : (char)c;
    }
    if (n > 1 && output[n - 1] == '/') --n;
    output[n] = 0;
    /* Do not guess aliases, redundant separators or dot components. */
    if (strstr(output, "//") || !strcmp(output, ".") || !strcmp(output, "..") ||
        strstr(output, "/../") || strstr(output, "/./") ||
        (n >= 3 && (!strcmp(output + n - 3, "/.."))) ||
        (n >= 2 && (!strcmp(output + n - 2, "/.")))) return 0;
    return 1;
}

/* Explicit qualification registration. A matching token is identity binding,
 * not a signature and not a substitute for the mandatory authority callback. */
static int cohFolderCensusRegister(CohFolderCensusContext *context,
    const unsigned char *blob, size_t bytes, const char *native_root,
    const unsigned char expected_token[32], const void *cache_owner,
    int expected_pig_count, CohFolderCensusLease lease, void *lease_owner)
{
    CohCensusResult decoded;
    const uint32_t endian_probe = 1;
    size_t root_bytes = 0;
    if (!context) return 0;
    if (native_root) for (; root_bytes < COH_CENSUS_NATIVE_PATH_MAX && native_root[root_bytes]; ++root_bytes) {}
    if ((blob && cohCensusOverlap(context, sizeof(*context), blob, bytes)) ||
        (expected_token && cohCensusOverlap(context, sizeof(*context), expected_token, 32)) ||
        (native_root && cohCensusOverlap(context, sizeof(*context), native_root,
            root_bytes < COH_CENSUS_NATIVE_PATH_MAX ? root_bytes + 1 : root_bytes)))
        return 0; /* Invalid alias inputs remain untouched. */
    cohFolderCensusClearContext(context);
    if (sizeof(WIN32_FIND_DATAA) != 320 || *(const unsigned char *)&endian_probe != 1 ||
        !blob || !expected_token || !cache_owner || !lease || expected_pig_count < 0 ||
        !cohFolderCensusRoot(native_root, context->native_root)) return 0;
    decoded = cohCensusDecode(&context->view, blob, bytes,
        context->directory_offsets, 16384);
    if (decoded != COH_CENSUS_OK || memcmp(context->view.provider_token, expected_token, 32)) {
        cohFolderCensusClearContext(context);
        return 0;
    }
    memcpy(context->generation_token, expected_token, 32);
    context->cache_owner = cache_owner;
    context->expected_pig_count = expected_pig_count;
    context->lease = lease;
    context->lease_owner = lease_owner;
    context->owner_thread = (uint32_t)COH_CENSUS_CURRENT_THREAD_ID();
    if (!context->owner_thread) {
        cohFolderCensusClearContext(context);
        return 0;
    }
    if (lease(lease_owner, context->native_root, "", context->generation_token) != 1) {
        cohFolderCensusClearContext(context);
        return 0;
    }
    context->registered = 1;
    return 1;
}

static int cohFolderCensusBranch(const char *path)
{
    static const char *branches[] = {"texture_library", "object_library", "fx", "scripts", "scripts.loc"};
    size_t i, j;
    for (i = 0; i < sizeof(branches) / sizeof(branches[0]); ++i) {
        size_t n = strlen(branches[i]);
        for (j = 0; j < n; ++j) {
            unsigned char c = (unsigned char)path[j];
            if (!c) break;
            if (c >= 'A' && c <= 'Z') c = (unsigned char)(c + ('a' - 'A'));
            if (c != (unsigned char)branches[i][j]) break;
        }
        if (j == n && (path[n] == 0 || path[n] == '/')) return 1;
    }
    return 0;
}

/* A failed admission returns before any FolderNode/counter/hash mutation.
 * Unknown branches/directories, nonempty/PIG nodes and changed policies retain
 * the original single FindFirst/FindNext/FindClose enumeration. */
static int cohFolderCensusAcquireDirectory(CohFolderCensusContext *context,
    const void *cache, const void *global_cache, const char *basepath,
    const char *current_provider_root, int gdd_count, int pig_count,
    int virtual_location, int siblings_empty, int callbacks_absent,
    int updates_disabled, int dynamic_mode, int all_folder_policy,
    int using_dev_data, CohFolderCensusDirectory *output)
{
    char root[COH_CENSUS_NATIVE_PATH_MAX], base[COH_CENSUS_NATIVE_PATH_MAX];
    const char *relative;
    size_t root_size;
    uint32_t ordinal, count;
    if (output) memset(output, 0, sizeof(*output));
    /* Revoke every failed owned admission before stock recursion reaches a
     * newly eligible child. No partial replay may hide a failed whole branch. */
    if (!output || !context || !context->registered || cache != context->cache_owner) return 0;
    if (!context->view.valid || context->view.directory_offsets != context->directory_offsets ||
        context->owner_thread != (uint32_t)COH_CENSUS_CURRENT_THREAD_ID() ||
        cache != global_cache || gdd_count != 1 ||
        pig_count != context->expected_pig_count || virtual_location != 0 ||
        !siblings_empty || !callbacks_absent || !updates_disabled || !dynamic_mode ||
        !all_folder_policy || !using_dev_data ||
        !cohFolderCensusRoot(current_provider_root, root) ||
        !cohFolderCensusRoot(basepath, base) || strcmp(root, context->native_root)) {
        cohFolderCensusClearContext(context);
        return 0;
    }
    root_size = strlen(root);
    if (strlen(base) <= root_size || memcmp(base, root, root_size) || base[root_size] != '/') return 0;
    relative = base + root_size + 1;
    if (!cohFolderCensusBranch(relative)) return 0;
    if (!cohCensusFindDirectory(&context->view, relative, &ordinal) ||
        !cohCensusDirectoryCount(&context->view, ordinal, &count)) {
        cohFolderCensusClearContext(context);
        return 0;
    }
    if (context->lease(context->lease_owner, root, relative, context->generation_token) != 1) {
        cohFolderCensusClearContext(context);
        return 0;
    }
    output->view = &context->view;
    output->ordinal = ordinal;
    output->count = count;
    return 1;
}

/* The v1 canonical projection exactly fills defined WIN32_FIND_DATAA fields;
 * zeroed reserved/padding bytes are explicitly nonauthoritative. ABI mismatch
 * must prevent registration/replay before this accessor can be called. */
static void cohFolderCensusCopyFindData(const CohFolderCensusDirectory *directory,
    uint32_t arrival, WIN32_FIND_DATAA *output)
{
    const unsigned char *projection = cohCensusProjection(directory->view,
        directory->ordinal, arrival);
    memcpy(output, projection, 320);
}
#endif
