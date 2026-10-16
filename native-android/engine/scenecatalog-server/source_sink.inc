/* NONSHIPPING startup-only catalog sink. Include after source_export.inc, itself
 * appended after the unchanged original groupnetsend.c in the same TU.
 *
 * The operator MUST provide a private, exclusively owned output parent and a
 * stable single-owner GroupInfo/property-serialization snapshot. Directory
 * reparse checks reject obvious aliases; they cannot make an attacker-writable
 * parent safe against rename races. No directories are created here.
 *
 * 32 MiB bounds emitted output, NOT process peak memory: the trusted upstream
 * Packet allocator can transiently grow before source-export admission.
 */
#ifndef COH_NATIVE_SCENE_CATALOG_SINK_INCLUDED
#define COH_NATIVE_SCENE_CATALOG_SINK_INCLUDED

#if defined(SERVER) && defined(_WIN32)
#ifndef COH_NATIVE_SCENE_CATALOG_TEST_WINAPI
#include <utilitieslib/utils/wininclude.h>
#endif
#include <stdio.h>
#include <string.h>

#define COH_CATALOG_SINK_PATH_MAX 240u
#define COH_CATALOG_SINK_BYTES_MAX (32u * 1024u * 1024u)

typedef struct CohCatalogSinkWriter
{
    HANDLE handle;
    unsigned int bytes;
    unsigned int failed;
} CohCatalogSinkWriter;

static int coh_catalog_sink_output(void *context, const unsigned char *bytes,
    unsigned int size)
{
    CohCatalogSinkWriter *writer = (CohCatalogSinkWriter *)context;
    DWORD written = 0;
    if (writer->failed || (!bytes && size) ||
        size > COH_CATALOG_SINK_BYTES_MAX - writer->bytes)
    {
        writer->failed = 1;
        return 0;
    }
    if (!size)
        return 1;
    if (!WriteFile(writer->handle, bytes, (DWORD)size, &written, NULL) ||
        written != size)
    {
        writer->failed = 1;
        return 0;
    }
    writer->bytes += size;
    return 1;
}

static int coh_catalog_sink_generation(const char *text, unsigned int *out)
{
    unsigned int value = 0, digit, i;
    if (!text || !text[0])
        return 0;
    for (i = 0; text[i]; ++i)
    {
        if (i >= 10u || text[i] < '0' || text[i] > '9')
            return 0;
        digit = (unsigned int)(text[i] - '0');
        if (value > (0xffffffffu - digit) / 10u)
            return 0;
        value = value * 10u + digit;
    }
    if (!value)
        return 0;
    *out = value;
    return 1;
}

static int coh_catalog_sink_reserved(const char *part, unsigned int length)
{
    char base[5];
    unsigned int i, n = 0;
    while (n < length && part[n] != '.')
        ++n;
    if (n > 4u)
        return 0;
    for (i = 0; i < n; ++i)
    {
        base[i] = part[i];
        if (base[i] >= 'a' && base[i] <= 'z')
            base[i] = (char)(base[i] - 'a' + 'A');
    }
    base[n] = 0;
    return !strcmp(base, "CON") || !strcmp(base, "PRN") ||
        !strcmp(base, "AUX") || !strcmp(base, "NUL") ||
        (n == 4u && (!memcmp(base, "COM", 3) || !memcmp(base, "LPT", 3)) &&
         base[3] >= '1' && base[3] <= '9');
}

/* Only a drive-absolute visible-ASCII path with ordinary components is admitted.
 * UNC, device paths, ADS, dot aliases and DOS device names are refused. */
static int coh_catalog_sink_path(char *path, unsigned int length)
{
    unsigned int i, begin = 3u, count;
    char saved;
    DWORD attributes;
    if (length < 4u || length > COH_CATALOG_SINK_PATH_MAX ||
        !((path[0] >= 'A' && path[0] <= 'Z') ||
          (path[0] >= 'a' && path[0] <= 'z')) || path[1] != ':' ||
        (path[2] != '\\' && path[2] != '/'))
        return 0;
    for (i = 3u; i <= length; ++i)
    {
        if (path[i] && path[i] != '\\' && path[i] != '/')
        {
            if ((unsigned char)path[i] < 33u || (unsigned char)path[i] > 126u ||
                strchr(":<>\"|?*", path[i]))
                return 0;
            continue;
        }
        count = i - begin;
        if (!count || path[i - 1u] == '.' || path[i - 1u] == ' ' ||
            coh_catalog_sink_reserved(path + begin, count))
            return 0;
        if (path[i])
        {
            saved = path[i];
            path[i] = 0;
            attributes = GetFileAttributesA(path);
            path[i] = saved;
            if (attributes == INVALID_FILE_ATTRIBUTES ||
                !(attributes & FILE_ATTRIBUTE_DIRECTORY) ||
                (attributes & FILE_ATTRIBUTE_REPARSE_POINT))
                return 0;
        }
        begin = i + 1u;
    }
    saved = path[3];
    path[3] = 0;
    attributes = GetFileAttributesA(path);
    path[3] = saved;
    return attributes != INVALID_FILE_ATTRIBUTES &&
        (attributes & FILE_ATTRIBUTE_DIRECTORY) &&
        !(attributes & FILE_ATTRIBUTE_REPARSE_POINT);
}

/* Called only by the opt-in staged normal-map startup hook, after groupLoadMap
 * and dbSetupMap, before dbReadyForPlayers. No exit, network send, persistence
 * action or server-state mutation occurs, including all failure paths. */
void coh_source_catalog_export_startup(void)
{
    char path[COH_CATALOG_SINK_PATH_MAX + 1u];
    char partial[COH_CATALOG_SINK_PATH_MAX + 9u];
    char generation_text[12];
    DWORD length, generation_length;
    unsigned int generation = 0, status = 0, created = 0, removed = 0;
    CohSourceCatalogExportReport report;
    CohCatalogSinkWriter writer;
    int result = 0;
    memset(&report, 0, sizeof(report));
    report.failure_file = report.failure_slot = 0xffffffffu;
    memset(&writer, 0, sizeof(writer));
    writer.handle = INVALID_HANDLE_VALUE;
    length = GetEnvironmentVariableA("COH_NATIVE_SCENE_CATALOG_OUTPUT",
        path, sizeof(path));
    if (!length)
        return;
    status = 2u;
    if (length >= sizeof(path))
        goto done;
    generation_length = GetEnvironmentVariableA(
        "COH_NATIVE_SCENE_CATALOG_GENERATION", generation_text,
        sizeof(generation_text));
    if (!generation_length || generation_length >= sizeof(generation_text) ||
        !coh_catalog_sink_generation(generation_text, &generation))
        goto done;
    status = 3u;
    if (!coh_catalog_sink_path(path, length))
        goto done;
    /* Fail closed for an existing destination or an unexpected lookup error. */
    if (GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES ||
        GetLastError() != ERROR_FILE_NOT_FOUND)
        goto done;
    memcpy(partial, path, length);
    memcpy(partial + length, ".partial", 9u);
    status = 4u;
    writer.handle = CreateFileA(partial, GENERIC_WRITE, 0, NULL, CREATE_NEW,
        FILE_ATTRIBUTE_NORMAL, NULL);
    if (writer.handle == INVALID_HANDLE_VALUE)
        goto done;
    created = 1u;
    status = 5u;
    result = coh_source_catalog_export(coh_catalog_sink_output, &writer,
        generation, &report);
    if (result || report.status || writer.failed ||
        report.total_bytes != writer.bytes || report.emitted_bytes != writer.bytes)
        goto cleanup;
    status = 6u;
    if (!FlushFileBuffers(writer.handle))
        goto cleanup;
    status = 7u;
    if (!CloseHandle(writer.handle))
        goto cleanup;
    writer.handle = INVALID_HANDLE_VALUE;
    status = 8u;
    /* MOVEFILE_REPLACE_EXISTING is deliberately absent. */
    if (!MoveFileExA(partial, path, MOVEFILE_WRITE_THROUGH))
        goto cleanup;
    created = 0u;
    status = 1u;
    goto done;
cleanup:
    if (writer.handle != INVALID_HANDLE_VALUE)
    {
        CloseHandle(writer.handle);
        writer.handle = INVALID_HANDLE_VALUE;
    }
    if (created)
        removed = DeleteFileA(partial) ? 1u : 0u;
done:
    /* Only static labels and unsigned numeric observations: never names, paths,
     * raw OS error strings, credentials, source records or packet contents. */
    printf("COH_NATIVE_SCENE_CATALOG_V1 status=%u producer_status=%u "
        "failure_file=%u failure_slot=%u files=%u definitions=%u slots=%u "
        "children=%u wire_bytes=%u total_bytes=%u emitted_bytes=%u "
        "written_bytes=%u partial_remaining=%u partial_removed=%u\n",
        status, report.status, report.failure_file, report.failure_slot,
        report.files, report.definitions, report.slots, report.children,
        report.wire_bytes, report.total_bytes, report.emitted_bytes,
        writer.bytes, created && !removed ? 1u : 0u, removed);
}
#else
void coh_source_catalog_export_startup(void) { }
#endif
#endif
