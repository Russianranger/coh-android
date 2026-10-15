/* Game-only, opt-in cap selection and repeated custom-texture diagnostics.
 * This header never loads/caches textures or alters appearance assignments.
 * Exact full keys prevent suppression of the first error for another asset.
 * Oversized/null keys and a full table preserve the original Errorf call.
 */
#ifndef COH_CLIENT_GAMEPLAY_PERFORMANCE_H
#define COH_CLIENT_GAMEPLAY_PERFORMANCE_H
#pragma push_macro("printf")
#pragma push_macro("snprintf")
#pragma push_macro("fflush")
#pragma push_macro("FILE")
#undef printf
#undef snprintf
#undef fflush
#undef FILE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#define COH_GP_TEXTURE_KEYS 64u
#define COH_GP_TEXTURE_BYTES 256u
#define COH_GP_NAME_BYTES 128u
#define COH_GP_MAX_TEXTURE_REPORTS 32u

typedef struct CohGpTextureKey {
    unsigned int used, slot, hash, suppressed;
    char sequence[COH_GP_NAME_BYTES];
    char texture[COH_GP_TEXTURE_BYTES];
    char bone[COH_GP_NAME_BYTES];
} CohGpTextureKey;
typedef struct CohGpState {
    int profile_reported, texture_initialized, texture_enabled;
    unsigned int unique_keys, original_errors, untracked_errors;
    unsigned int suppressed, texture_reports, next_report;
    CohGpTextureKey keys[COH_GP_TEXTURE_KEYS];
} CohGpState;
/* parseArgs and changeTexture each run on the Game main thread. Each native
 * translation unit owns its state; no mutable state crosses threads. */
static CohGpState coh_gp_state;

#ifdef COH_GAMEPLAY_PERFORMANCE_TEST
static __inline const char *cohGpEnvironment(const char *name) {
    return cohGpTestEnvironment(name);
}
static __inline void cohGpEmit(const char *line) { cohGpTestEmit(line); }
#else
#ifndef _WIN32
#error Production gameplay performance diagnostics require the retained Win32 Game runtime
#endif
static __inline const char *cohGpEnvironment(const char *name) { return getenv(name); }
static __inline void cohGpEmit(const char *line) {
    printf("%s\n", line); fflush(stdout);
}
#endif

static void cohGpIncrement(unsigned int *value) {
    if (*value < UINT_MAX) ++*value;
}

/* Called once, after command-line parsing; later /maxfps commands still work.
 * Menu/background caps are observed only. The existing launcher sets both 10.
 * create_bins is deliberately an entirely unchanged execution path. */
static void cohGpApplyProfile(int *maxfps, int create_bins, int menu_cap, int inactive_cap) {
    const char *value;
    const char *texture_option;
    int requested = 0;
    char line[1024];
    if (create_bins || !maxfps || coh_gp_state.profile_reported) return;
    value = cohGpEnvironment("COH_CLIENT_GAMEPLAY_FPS");
    if (value && strcmp(value, "10") == 0) requested = 10;
    else if (value && strcmp(value, "30") == 0) requested = 30;
    if (requested) *maxfps = requested;
    coh_gp_state.profile_reported = 1;
    texture_option = cohGpEnvironment("COH_CLIENT_BOUNDED_TEXTURE_ERRORS");
    snprintf(line, sizeof(line),
        "COH_CLIENT_GAMEPLAY_PROFILE_V1 {\"requested_cap\":%d,\"effective_cap\":%d,\"override_applied\":%d,\"menu_cap\":%d,\"inactive_cap\":%d,\"create_bins\":0,\"bounded_texture_errors\":%d,\"texture_key_limit\":64,\"texture_report_limit\":32,\"asset_loading_unchanged\":1}",
        requested, *maxfps, requested != 0, menu_cap, inactive_cap,
        texture_option && strcmp(texture_option, "1") == 0);
    cohGpEmit(line);
}

static int cohGpKeyLength(const char *value, unsigned int capacity, unsigned int *length) {
    unsigned int i;
    if (!value) return 0;
    for (i = 0; i < capacity; ++i) {
        if (!value[i]) { *length = i; return 1; }
    }
    return 0;
}

static unsigned int cohGpHashString(unsigned int hash, const char *value, unsigned int length) {
    unsigned int i;
    for (i = 0; i <= length; ++i) hash = (hash ^ (unsigned char)value[i]) * 16777619u;
    return hash;
}

static void cohGpTextureSuppressed(CohGpTextureKey *key, unsigned int key_index) {
    char line[1024];
    cohGpIncrement(&key->suppressed);
    cohGpIncrement(&coh_gp_state.suppressed);
    /* Count-based powers-of-two progress needs no clock calls and emits at
     * most 32 records for a process, even if errors recur indefinitely. */
    if (coh_gp_state.texture_reports >= COH_GP_MAX_TEXTURE_REPORTS ||
        coh_gp_state.suppressed != coh_gp_state.next_report) return;
    ++coh_gp_state.texture_reports;
    snprintf(line, sizeof(line),
        "COH_CLIENT_TEXTURE_ERRORS_V1 {\"suppressed_total\":%u,\"original_errors\":%u,\"unique_tracked\":%u,\"untracked_errors\":%u,\"key_index\":%u,\"texture_slot\":%u,\"key_suppressed\":%u,\"ordinal\":%u,\"report_limit\":32,\"key_limit\":64,\"first_error_preserved\":1,\"asset_loading_unchanged\":1}",
        coh_gp_state.suppressed, coh_gp_state.original_errors, coh_gp_state.unique_keys,
        coh_gp_state.untracked_errors, key_index, key->slot, key->suppressed,
        coh_gp_state.texture_reports);
    cohGpEmit(line);
    if (coh_gp_state.next_report <= UINT_MAX / 2u) coh_gp_state.next_report *= 2u;
    else coh_gp_state.next_report = UINT_MAX;
}

/* Return 1 only when the original Errorf must run. texLoad/texLoadBasic and
 * fallback/assignment side effects remain outside this diagnostic predicate. */
static int cohGpTextureError(unsigned int slot, const char *sequence, const char *texture, const char *bone) {
    const char *option;
    unsigned int sequence_length, texture_length, bone_length, hash, i, index;
    CohGpTextureKey *key;
    if (!coh_gp_state.texture_initialized) {
        option = cohGpEnvironment("COH_CLIENT_BOUNDED_TEXTURE_ERRORS");
        coh_gp_state.texture_enabled = option && strcmp(option, "1") == 0;
        coh_gp_state.texture_initialized = 1;
        coh_gp_state.next_report = 1u;
    }
    if (!coh_gp_state.texture_enabled) return 1;
    if ((slot != 1u && slot != 2u) ||
        !cohGpKeyLength(sequence, COH_GP_NAME_BYTES, &sequence_length) ||
        !cohGpKeyLength(texture, COH_GP_TEXTURE_BYTES, &texture_length) ||
        !cohGpKeyLength(bone, COH_GP_NAME_BYTES, &bone_length)) {
        cohGpIncrement(&coh_gp_state.untracked_errors);
        cohGpIncrement(&coh_gp_state.original_errors);
        return 1;
    }
    hash = cohGpHashString(2166136261u ^ slot, sequence, sequence_length);
    hash = cohGpHashString(hash, texture, texture_length);
    hash = cohGpHashString(hash, bone, bone_length);
    for (i = 0; i < COH_GP_TEXTURE_KEYS; ++i) {
        index = (hash + i) % COH_GP_TEXTURE_KEYS;
        key = &coh_gp_state.keys[index];
        if (!key->used) {
            key->used = 1u; key->slot = slot; key->hash = hash;
            memcpy(key->sequence, sequence, sequence_length + 1u);
            memcpy(key->texture, texture, texture_length + 1u);
            memcpy(key->bone, bone, bone_length + 1u);
            ++coh_gp_state.unique_keys;
            cohGpIncrement(&coh_gp_state.original_errors);
            return 1;
        }
        if (key->hash == hash && key->slot == slot &&
            strcmp(key->sequence, sequence) == 0 && strcmp(key->texture, texture) == 0 &&
            strcmp(key->bone, bone) == 0) {
            cohGpTextureSuppressed(key, index);
            return 0;
        }
    }
    cohGpIncrement(&coh_gp_state.untracked_errors);
    cohGpIncrement(&coh_gp_state.original_errors);
    return 1;
}

#pragma pop_macro("FILE")
#pragma pop_macro("fflush")
#pragma pop_macro("snprintf")
#pragma pop_macro("printf")
#endif
