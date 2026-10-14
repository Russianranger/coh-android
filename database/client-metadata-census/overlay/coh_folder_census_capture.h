#ifndef COH_FOLDER_CENSUS_CAPTURE_H
#define COH_FOLDER_CENSUS_CAPTURE_H
/* Capture-only qualification bridge. These observations do not register a
 * census, select a provider, authorize cache reuse or change any native node.
 * The outer qualifier must bind exact archive bytes, mount/mode/generation,
 * this native consumer and a fresh post-capture metadata vector. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include <errno.h>
#include "coh_folder_census_observation.h"

#define COH_CAPTURE_MARKER "COH_NATIVE_PIG_INDEX_CAPTURE_V1"
#define COH_CAPTURE_MAX_PROVIDERS 64u
#define COH_CAPTURE_MAX_ROWS 200000u
#define COH_CAPTURE_MAX_BYTES (8u * 1024u * 1024u)
#ifndef COH_CAPTURE_ENV
#define COH_CAPTURE_ENV getenv
#endif
#ifndef COH_CAPTURE_WRITE
#define COH_CAPTURE_WRITE(line) printf("%s %s\n", COH_CAPTURE_MARKER, line)
#endif

typedef struct CohPigCaptureOutput {
    uint32_t bytes, rows;
    int failed;
} CohPigCaptureOutput;

typedef struct CohClientCensusStatCounts {
    uint64_t calls, returns_ok, returns_failed;
    uint64_t create_calls, create_ok, info_calls, info_ok;
} CohClientCensusStatCounts;
#if defined(_WIN32)
__declspec(align(8)) static CohClientCensusStatCounts coh_client_census_stat_counts[6];
#else
_Alignas(8) static CohClientCensusStatCounts coh_client_census_stat_counts[6];
#endif
COH_CENSUS_THREAD_LOCAL int coh_client_census_stat_scope;
static unsigned int coh_client_census_flushes;
static int coh_client_census_observation_enabled = -1;
static uint32_t coh_client_census_capture_thread;

static void cohCensusCountIncrement(uint64_t *value)
{
#if defined(_WIN32)
    InterlockedIncrement64((volatile LONG64 *)value);
#else
    __sync_fetch_and_add(value, 1);
#endif
}
static uint64_t cohCensusCountRead(uint64_t *value)
{
#if defined(_WIN32)
    return (uint64_t)InterlockedCompareExchange64((volatile LONG64 *)value, 0, 0);
#else
    return __sync_fetch_and_add(value, 0);
#endif
}

void cohClientCensusObserveStatStage(int stage, int succeeded)
{
    int scope = coh_client_census_stat_scope;
    if (scope <= 0 || scope >= 6) return;
    if (stage == COH_CENSUS_STAT_CREATE) {
        cohCensusCountIncrement(&coh_client_census_stat_counts[scope].create_calls);
        if (succeeded) cohCensusCountIncrement(&coh_client_census_stat_counts[scope].create_ok);
    } else if (stage == COH_CENSUS_STAT_FILE_INFORMATION) {
        cohCensusCountIncrement(&coh_client_census_stat_counts[scope].info_calls);
        if (succeeded) cohCensusCountIncrement(&coh_client_census_stat_counts[scope].info_ok);
    }
}

static int cohClientCensusStatBranch(const char *relative)
{
    static const char *names[] = {"texture_library", "object_library", "fx", "scripts", "scripts.loc"};
    unsigned int i;
    if (!relative) return 0;
    for (i = 0; i < 5; ++i) {
        size_t j, n = strlen(names[i]);
        for (j = 0; j < n; ++j) {
            unsigned char c = (unsigned char)relative[j];
            if (!c) break;
            if (c >= 'A' && c <= 'Z') c = (unsigned char)(c + 'a' - 'A');
            if (c != (unsigned char)names[i][j]) break;
        }
        if (j == n && (!relative[n] || relative[n] == '/' || relative[n] == '\\')) return (int)i + 1;
    }
    return 0;
}

static int cohFolderCensusObservedAltStat(FolderCache *fc, const char *filename,
    struct _stat32 *stat_result, const char *relative)
{
    int prior_scope = coh_client_census_stat_scope;
    int scope = coh_client_census_observation_enabled == 1 && fc == folder_cache ? cohClientCensusStatBranch(relative) : 0;
    int result, saved_errno;
    unsigned long saved_error;
    if (!scope) {
        if (!prior_scope) return _AltStat(filename, stat_result);
        coh_client_census_stat_scope = 0;
        result = _AltStat(filename, stat_result);
        coh_client_census_stat_scope = prior_scope;
        return result;
    }
    coh_client_census_stat_scope = scope;
    result = _AltStat(filename, stat_result);
    saved_errno = errno;
    saved_error = (unsigned long)GetLastError();
    if (scope) {
        cohCensusCountIncrement(&coh_client_census_stat_counts[scope].calls);
        cohCensusCountIncrement(result == -1 ? &coh_client_census_stat_counts[scope].returns_failed : &coh_client_census_stat_counts[scope].returns_ok);
    }
    coh_client_census_stat_scope = prior_scope;
    SetLastError(saved_error);
    errno = saved_errno;
    return result;
}

static void cohFolderCensusFlushStatObservations(void)
{
    static const char *names[] = {"unknown", "texture_library", "object_library", "fx", "scripts", "scripts.loc"};
    unsigned int i;
    int saved_errno;
    unsigned long saved_error;
    if (coh_client_census_observation_enabled != 1 ||
        (uint32_t)GetCurrentThreadId() != coh_client_census_capture_thread ||
        coh_client_census_flushes >= 16) return;
    saved_errno = errno; saved_error = (unsigned long)GetLastError();
    ++coh_client_census_flushes;
    for (i = 1; i < 6; ++i) {
        CohClientCensusStatCounts *counts = &coh_client_census_stat_counts[i];
        printf("COH_NATIVE_FOLDER_STAT_COUNTS_V1 {\"snapshot\":%u,\"branch\":\"%s\",\"calls\":%llu,\"returns_ok\":%llu,\"returns_failed\":%llu,\"create_calls\":%llu,\"create_ok\":%llu,\"info_calls\":%llu,\"info_ok\":%llu,\"scope\":\"cumulative_all_thread_local_FolderCache_override_calls_after_PIG_capture_begin\",\"cached_stat_reuse\":false}\n",
            coh_client_census_flushes, names[i],
            (unsigned long long)cohCensusCountRead(&counts->calls), (unsigned long long)cohCensusCountRead(&counts->returns_ok),
            (unsigned long long)cohCensusCountRead(&counts->returns_failed), (unsigned long long)cohCensusCountRead(&counts->create_calls),
            (unsigned long long)cohCensusCountRead(&counts->create_ok), (unsigned long long)cohCensusCountRead(&counts->info_calls),
            (unsigned long long)cohCensusCountRead(&counts->info_ok));
    }
    SetLastError(saved_error); errno = saved_errno;
}

static int cohPigCaptureLine(CohPigCaptureOutput *output, const char *format, ...)
{
    char line[2048];
    int n;
    va_list args;
    if (output->failed) return 0;
    va_start(args, format);
    n = vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    if (n < 0 || (size_t)n >= sizeof(line) ||
        (uint32_t)n + (uint32_t)sizeof(COH_CAPTURE_MARKER) + 1u > COH_CAPTURE_MAX_BYTES - output->bytes) {
        output->failed = 1;
        return 0;
    }
    if (COH_CAPTURE_WRITE(line) < 0) {
        output->failed = 1;
        return 0;
    }
    output->bytes += (uint32_t)n + (uint32_t)sizeof(COH_CAPTURE_MARKER) + 1u;
    return 1;
}

/* Escape actual native path bytes without locale conversion or truncation.
 * Unknown/overlong names cause an incomplete capture, never an absent member. */
static int cohPigCaptureString(const char *input, char output[1600])
{
    static const char hex[] = "0123456789abcdef";
    size_t i, at = 0;
    if (!input) { memcpy(output, "null", 5); return 1; }
    output[at++] = '"';
    for (i = 0; i < 260u && input[i]; ++i) {
        unsigned char c = (unsigned char)input[i];
        if (c == '"' || c == '\\') { output[at++] = '\\'; output[at++] = (char)c; }
        else if (c < 32u || c >= 127u) {
            output[at++] = '\\'; output[at++] = 'u'; output[at++] = '0'; output[at++] = '0';
            output[at++] = hex[c >> 4]; output[at++] = hex[c & 15u];
        } else output[at++] = (char)c;
    }
    if (i == 260u) return 0;
    output[at++] = '"'; output[at] = 0;
    return 1;
}

static int cohPigCaptureGeneration(char output[65])
{
    const char *value = COH_CAPTURE_ENV("COH_CLIENT_CENSUS_CAPTURE_GENERATION");
    size_t i;
    if (!value) return 0;
    for (i = 0; i < 64u; ++i) {
        char c = value[i];
        if (!c || !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
        output[i] = c;
    }
    if (value[64]) return 0;
    output[64] = 0;
    return 1;
}

/* Called only after the unmodified stock AddAllPigs loop completed. Each
 * actual provider is locked across its full native index observation. */
static void cohFolderCensusCapturePigIndexImpl(FolderCache *fc)
{
    const char *enabled = COH_CAPTURE_ENV("COH_CLIENT_CENSUS_CAPTURE");
    char generation[65], root[1600];
    CohPigCaptureOutput output = {0};
    int providers, mode, p;
    uint32_t total = 0;
    if (!enabled || strcmp(enabled, "1") || !cohPigCaptureGeneration(generation)) return;
    if (fc != folder_cache || FolderCache_GetNumGDDs(fc) != 1 ||
        FolderCacheGetMode() != FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC ||
        folder_cache_update_enable || fc->nodeCreateCallback || fc->nodeDeleteCallback ||
        folder_cache_exclusion != FOLDER_CACHE_ALL_FOLDERS || folder_cache_exclusion_folder ||
        !fileIsUsingDevData()) return;
    mode = (int)FolderCacheGetMode();
    providers = PigSetGetNumPigs();
    if (providers < 0 || (unsigned int)providers > COH_CAPTURE_MAX_PROVIDERS ||
        FolderCache_GetNumPiggs(fc) != providers ||
        !cohPigCaptureString(FolderCache_GetFromVirtualLocation(fc, 0), root)) {
        COH_CAPTURE_WRITE("{\"event\":\"refused\",\"reason\":\"provider_admission\",\"native_registration_allowed\":false}");
        return;
    }
    if (!cohPigCaptureLine(&output,
        "{\"event\":\"begin\",\"generation\":\"%s\",\"providers\":%d,\"mode\":%d,\"gdd_root\":%s,\"windows_pid\":%lu,\"windows_thread\":%lu,\"native_registration_allowed\":false}",
        generation, providers, mode, root, (unsigned long)GetCurrentProcessId(), (unsigned long)GetCurrentThreadId())) return;
    coh_client_census_observation_enabled = 1;
    coh_client_census_capture_thread = (uint32_t)GetCurrentThreadId();
    for (p = 0; p < providers && !output.failed; ++p) {
        PigFile *pig = PigSetGetPigFile(p);
        uint32_t count, i;
        char archive[1600], mount[1600];
        if (!pig) { output.failed = 1; break; }
        PigFileLock(pig);
        count = PigFileGetNumFiles(pig);
        if (count > COH_CAPTURE_MAX_ROWS - total ||
            !cohPigCaptureString(PigFileGetArchiveFileName(pig), archive) ||
            !cohPigCaptureString(FolderCache_GetFromVirtualLocation(fc, PIG_INDEX_TO_VIRTUAL_LOCATION(p)), mount)) output.failed = 1;
        if (!output.failed) cohPigCaptureLine(&output,
            "{\"event\":\"provider\",\"ordinal\":%d,\"virtual_location\":%d,\"archive\":%s,\"folder_cache_mount\":%s,\"members\":%lu}",
            p, PIG_INDEX_TO_VIRTUAL_LOCATION(p), archive, mount, (unsigned long)count);
        for (i = 0; i < count && !output.failed; ++i) {
            const char *name = PigFileGetFileName(pig, (int)i);
            char member[1600];
            int special = PigFileIsSpecialFile(pig, (int)i) ? 1 : 0;
            uint32_t timestamp = 0, size = 0;
            if (!cohPigCaptureString(name, member)) { output.failed = 1; break; }
            /* Empty HOGG slots have no member. GetFileSize can assert for an
             * unused slot, so do not invent/read metadata the stock loop skips. */
            if (!name) {
                if (cohPigCaptureLine(&output,
                    "{\"event\":\"member\",\"provider\":%d,\"file_index\":%lu,\"name\":null,\"name_present\":false,\"special\":%s,\"timestamp\":null,\"size\":null,\"metadata_available\":false}",
                    p, (unsigned long)i, special ? "true" : "false")) ++output.rows;
                continue;
            }
            timestamp = PigFileGetFileTimestamp(pig, (int)i);
            size = PigFileGetFileSize(pig, (int)i);
            if (cohPigCaptureLine(&output,
                "{\"event\":\"member\",\"provider\":%d,\"file_index\":%lu,\"name\":%s,\"name_present\":%s,\"special\":%s,\"timestamp\":%lu,\"size\":%lu,\"metadata_available\":true}",
                p, (unsigned long)i, member, name ? "true" : "false", special ? "true" : "false",
                (unsigned long)timestamp, (unsigned long)size)) ++output.rows;
        }
        if (PigFileGetNumFiles(pig) != count) output.failed = 1;
        PigFileUnlock(pig);
        total += count;
    }
    if (PigSetGetNumPigs() != providers || FolderCache_GetNumGDDs(fc) != 1 ||
        FolderCache_GetNumPiggs(fc) != providers || FolderCacheGetMode() != mode ||
        output.rows != total) output.failed = 1;
    if (output.failed) {
        COH_CAPTURE_WRITE("{\"event\":\"end\",\"complete\":false,\"native_registration_allowed\":false}");
    } else {
        cohPigCaptureLine(&output,
            "{\"event\":\"end\",\"complete\":true,\"providers\":%d,\"rows\":%lu,\"native_registration_allowed\":false}",
            providers, (unsigned long)total);
    }
}

static void cohFolderCensusCapturePigIndex(FolderCache *fc)
{
    int saved_errno = errno;
    unsigned long saved_error = (unsigned long)GetLastError();
    cohFolderCensusCapturePigIndexImpl(fc);
    SetLastError(saved_error);
    errno = saved_errno;
}
#endif
