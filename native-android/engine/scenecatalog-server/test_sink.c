/* Local WinAPI shim executes the ACTUAL sink include with a mock producer.
 * It is not evidence that MapServer, Windows or Wine has executed. */
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#define SERVER 1
#define _WIN32 1
#define COH_NATIVE_SCENE_CATALOG_TEST_WINAPI 1
typedef unsigned int DWORD;
typedef int HANDLE;
#define INVALID_HANDLE_VALUE (-1)
#define INVALID_FILE_ATTRIBUTES 0xffffffffu
#define FILE_ATTRIBUTE_DIRECTORY 16u
#define FILE_ATTRIBUTE_REPARSE_POINT 1024u
#define FILE_ATTRIBUTE_NORMAL 128u
#define GENERIC_WRITE 0x40000000u
#define CREATE_NEW 1u
#define ERROR_FILE_NOT_FOUND 2u
#define MOVEFILE_WRITE_THROUGH 8u

typedef int (*CohSourceCatalogOutputFn)(void *, const unsigned char *, unsigned int);
typedef struct CohSourceCatalogExportReport
{
    unsigned int status, failure_file, failure_slot, files, definitions, slots;
    unsigned int children, wire_bytes, total_bytes, emitted_bytes;
} CohSourceCatalogExportReport;

static const char *output_environment, *generation_environment;
static unsigned int last_error, calls, producer_calls, creates, writes, flushes;
static unsigned int closes, moves, deletes, final_exists, partial_exists, opened;
static unsigned int fail_create, fail_write, fail_flush, fail_close, fail_move;
static unsigned int fail_delete, lookup_error, parent_reparse, parent_absent;
static unsigned int producer_mode, generation_seen, stored_bytes, final_bytes;
static unsigned int race_destination, move_flags;
static char log_text[2048], created_path[512], moved_path[512], final_prefix[16];
static unsigned char large_bytes[32u * 1024u * 1024u + 1u];

static int mock_printf(const char *format, ...)
{
    int result;
    va_list args;
    va_start(args, format);
    /* Only the fixed numeric sink format reaches this test-only collector. */
    result = vsprintf(log_text, format, args);
    va_end(args);
    return result;
}

static DWORD GetEnvironmentVariableA(const char *name, char *out, DWORD size)
{
    const char *value = !strcmp(name, "COH_NATIVE_SCENE_CATALOG_OUTPUT") ?
        output_environment : generation_environment;
    size_t length;
    ++calls;
    if (!value)
        return 0;
    length = strlen(value);
    if (length >= size)
        return (DWORD)length + 1u;
    memcpy(out, value, length + 1u);
    return (DWORD)length;
}

static DWORD GetFileAttributesA(const char *path)
{
    if (output_environment && !strcmp(path, output_environment))
    {
        last_error = lookup_error ? 5u : ERROR_FILE_NOT_FOUND;
        return final_exists ? FILE_ATTRIBUTE_NORMAL : INVALID_FILE_ATTRIBUTES;
    }
    if (parent_absent)
        return INVALID_FILE_ATTRIBUTES;
    return FILE_ATTRIBUTE_DIRECTORY | (parent_reparse ? FILE_ATTRIBUTE_REPARSE_POINT : 0u);
}

static DWORD GetLastError(void) { return last_error; }

static HANDLE CreateFileA(const char *path, DWORD access, DWORD share,
    void *security, DWORD disposition, DWORD attributes, void *template_file)
{
    (void)security; (void)template_file;
    ++creates;
    if (access != GENERIC_WRITE || share || disposition != CREATE_NEW ||
        attributes != FILE_ATTRIBUTE_NORMAL)
        abort();
    if (fail_create || partial_exists)
        return INVALID_HANDLE_VALUE;
    strcpy(created_path, path);
    partial_exists = opened = 1u;
    return 11;
}

static int WriteFile(HANDLE handle, const unsigned char *bytes, DWORD count,
    DWORD *written, void *overlap)
{
    unsigned int copy;
    (void)overlap;
    if (handle != 11 || !opened || !partial_exists)
        abort();
    ++writes;
    if (fail_write)
    {
        *written = fail_write == 2u ? count / 2u : 0u;
        return fail_write == 2u;
    }
    copy = count < sizeof(final_prefix) ? count : (unsigned int)sizeof(final_prefix);
    if (!stored_bytes)
        memcpy(final_prefix, bytes, copy);
    stored_bytes += count;
    *written = count;
    return 1;
}

static int FlushFileBuffers(HANDLE handle)
{
    if (handle != 11 || !opened)
        abort();
    ++flushes;
    return !fail_flush;
}

static int CloseHandle(HANDLE handle)
{
    if (handle != 11 || !opened)
        abort();
    ++closes;
    if (fail_close)
    {
        --fail_close;
        return 0;
    }
    opened = 0u;
    return 1;
}

static int MoveFileExA(const char *from, const char *to, DWORD flags)
{
    ++moves;
    move_flags = flags;
    if (opened || !partial_exists || strcmp(from, created_path) || flags != MOVEFILE_WRITE_THROUGH)
        abort();
    if (race_destination)
        final_exists = 1u;
    if (fail_move || final_exists)
        return 0;
    strcpy(moved_path, to);
    final_bytes = stored_bytes;
    final_exists = 1u;
    partial_exists = 0u;
    return 1;
}

static int DeleteFileA(const char *path)
{
    ++deletes;
    if (!partial_exists || strcmp(path, created_path))
        abort();
    if (fail_delete || opened)
        return 0;
    partial_exists = 0u;
    return 1;
}

static int coh_source_catalog_export(CohSourceCatalogOutputFn output,
    void *context, unsigned int generation, CohSourceCatalogExportReport *report)
{
    static const unsigned char bytes[] = "COHMOCK1";
    unsigned int size = producer_mode == 3u || producer_mode == 4u ?
        32u * 1024u * 1024u : 8u;
    const unsigned char *data = size == 8u ? bytes : large_bytes;
    ++producer_calls;
    generation_seen = generation;
    report->files = 2u; report->definitions = 3u; report->slots = 4u;
    report->children = 5u; report->wire_bytes = 6u;
    report->total_bytes = size;
    if (producer_mode == 1u)
    {
        report->status = 3u;
        report->failure_file = 7u; report->failure_slot = 9u;
        return 3;
    }
    if (!output(context, data, size))
    {
        report->status = 5u;
        return 5;
    }
    report->emitted_bytes = size;
    if (producer_mode == 2u)
    {
        report->status = 6u;
        return 6;
    }
    if (producer_mode == 3u)
    {
        ++report->total_bytes;
        if (!output(context, bytes, 1u))
        {
            report->status = 5u;
            return 5;
        }
        ++report->emitted_bytes;
    }
    if (producer_mode == 5u)
        ++report->total_bytes;
    return 0;
}

#define printf mock_printf
#include "source_sink.inc"
#undef printf

static unsigned int checks;
#define CHECK(value) do { ++checks; if (!(value)) { fprintf(stderr, "sink check failed line %u\n", (unsigned int)__LINE__); exit(1); } } while (0)

static void reset(void)
{
    output_environment = "C:\\private\\catalog.bin";
    generation_environment = "17";
    last_error = calls = producer_calls = creates = writes = flushes = 0;
    closes = moves = deletes = final_exists = partial_exists = opened = 0;
    fail_create = fail_write = fail_flush = fail_close = fail_move = fail_delete = 0;
    lookup_error = parent_reparse = parent_absent = producer_mode = 0;
    generation_seen = stored_bytes = final_bytes = race_destination = move_flags = 0;
    memset(log_text, 0, sizeof(log_text));
    memset(created_path, 0, sizeof(created_path));
    memset(moved_path, 0, sizeof(moved_path));
    memset(final_prefix, 0, sizeof(final_prefix));
}

static void status(unsigned int expected)
{
    char wanted[64];
    sprintf(wanted, "COH_NATIVE_SCENE_CATALOG_V1 status=%u ", expected);
    CHECK(!strncmp(log_text, wanted, strlen(wanted)));
    CHECK(!strstr(log_text, "private") && !strstr(log_text, "catalog.bin"));
    CHECK(!strstr(log_text, "COHMOCK1") && !strstr(log_text, "C:\\"));
}

static void config_refusal(const char *path, const char *generation, unsigned int code)
{
    reset();
    output_environment = path; generation_environment = generation;
    coh_source_catalog_export_startup();
    status(code);
    CHECK(!creates && !producer_calls && !deletes && !moves && !writes);
}

int main(void)
{
    unsigned int i;
    char overlong[300];
    const char *bad_generations[] = {NULL, "", "0", "-1", "+1", "1x", " 1", "1 ", "4294967296", "999999999999999999999999"};
    const char *bad_paths[] = {"relative.bin", "C:relative.bin", "\\\\server\\share\\out", "\\\\?\\C:\\out", "C:\\private\\..\\out", "C:\\private\\.\\out", "C:\\private\\out.", "C:\\private\\out ", "C:\\private\\out:stream", "C:\\private\\NUL.bin", "C:\\private\\com1.txt", "C:\\private\\aux\\out", "C:\\private\\\\out", "C:\\private\\out?", "C:\\private\\out\n"};
    reset(); output_environment = NULL;
    coh_source_catalog_export_startup();
    CHECK(!producer_calls && !creates && !writes && !log_text[0]);
    reset(); output_environment = "";
    coh_source_catalog_export_startup();
    CHECK(!producer_calls && !creates && !log_text[0]);
    for (i = 0; i < sizeof(bad_generations) / sizeof(bad_generations[0]); ++i)
        config_refusal("C:\\private\\catalog.bin", bad_generations[i], 2u);
    for (i = 0; i < sizeof(bad_paths) / sizeof(bad_paths[0]); ++i)
        config_refusal(bad_paths[i], "17", 3u);
    memset(overlong, 'x', sizeof(overlong)); overlong[sizeof(overlong) - 1u] = 0;
    config_refusal(overlong, "17", 2u);
    reset(); parent_reparse = 1u; coh_source_catalog_export_startup(); status(3u); CHECK(!creates);
    reset(); parent_absent = 1u; coh_source_catalog_export_startup(); status(3u); CHECK(!creates);
    reset(); lookup_error = 1u; coh_source_catalog_export_startup(); status(3u); CHECK(!creates);
    reset(); final_exists = 1u; coh_source_catalog_export_startup(); status(3u); CHECK(!creates && !deletes && final_exists);
    reset(); partial_exists = 1u; coh_source_catalog_export_startup(); status(4u); CHECK(creates == 1u && !deletes && partial_exists);
    reset(); fail_create = 1u; coh_source_catalog_export_startup(); status(4u); CHECK(!deletes && !producer_calls);
    reset(); coh_source_catalog_export_startup(); status(1u);
    CHECK(producer_calls == 1u && creates == 1u && writes == 1u && flushes == 1u && closes == 1u && moves == 1u && !deletes);
    CHECK(generation_seen == 17u && final_exists && !partial_exists && !opened && final_bytes == 8u);
    CHECK(!memcmp(final_prefix, "COHMOCK1", 8u) && !strcmp(moved_path, output_environment));
    CHECK(move_flags == MOVEFILE_WRITE_THROUGH);
    reset(); generation_environment = "4294967295"; coh_source_catalog_export_startup(); status(1u); CHECK(generation_seen == 0xffffffffu);
    for (i = 1u; i <= 2u; ++i)
    {
        reset(); producer_mode = i; coh_source_catalog_export_startup(); status(5u);
        CHECK(!moves && !final_exists && !partial_exists && deletes == 1u && !opened);
    }
    reset(); fail_write = 1u; coh_source_catalog_export_startup(); status(5u); CHECK(!partial_exists && !moves && deletes == 1u);
    reset(); fail_write = 2u; coh_source_catalog_export_startup(); status(5u); CHECK(!partial_exists && !moves && deletes == 1u);
    reset(); fail_flush = 1u; coh_source_catalog_export_startup(); status(6u); CHECK(!partial_exists && !moves && deletes == 1u && !opened);
    reset(); fail_close = 1u; coh_source_catalog_export_startup(); status(7u); CHECK(!partial_exists && !moves && deletes == 1u && !opened && closes == 2u);
    reset(); fail_close = 2u; coh_source_catalog_export_startup(); status(7u); CHECK(partial_exists && !moves && !final_exists && deletes == 1u && opened && strstr(log_text, "partial_remaining=1 partial_removed=0"));
    reset(); fail_move = 1u; coh_source_catalog_export_startup(); status(8u); CHECK(!partial_exists && !final_exists && deletes == 1u && !opened);
    reset(); race_destination = 1u; coh_source_catalog_export_startup(); status(8u); CHECK(!partial_exists && final_exists && !final_bytes && deletes == 1u);
    reset(); producer_mode = 2u; fail_delete = 1u; coh_source_catalog_export_startup(); status(5u); CHECK(partial_exists && !final_exists && deletes == 1u && !opened);
    reset(); producer_mode = 3u; coh_source_catalog_export_startup(); status(5u); CHECK(stored_bytes == 32u * 1024u * 1024u && writes == 1u && !partial_exists && !final_exists);
    reset(); producer_mode = 4u; coh_source_catalog_export_startup(); status(1u); CHECK(final_bytes == 32u * 1024u * 1024u && !partial_exists);
    reset(); producer_mode = 5u; coh_source_catalog_export_startup(); status(5u); CHECK(!final_exists && !partial_exists && !moves);
    printf("{\"passed\":true,\"checks\":%u,\"actual_sink_include\":true,\"mock_producer\":true,\"winapi_shim\":true,\"server_executed\":false}\n", checks);
    return 0;
}
