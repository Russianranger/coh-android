#include "wine_external_maps.h"
#include <windows.h>
#include <stdio.h>
#include <string.h>

#define REQUEST_BYTES 8192

static int g_mode = -2;    /* not yet decided */
static unsigned int g_sequence;
static char g_directory[MAX_PATH];

static int exactEnabled(const char *name)
{
    char value[2];
    DWORD length = GetEnvironmentVariableA(name, value, sizeof(value));
    return length == 1 && value[0] == '1';
}

static int decideMode(void)
{
    char value[2];
    DWORD length, attributes;

    SetLastError(ERROR_SUCCESS);
    length = GetEnvironmentVariableA(COH_DB_EXTERNAL_MAPS_ENVIRONMENT, value, sizeof(value));
    if (!length && GetLastError() == ERROR_ENVVAR_NOT_FOUND)
        return 0;
    if (length != 1 || value[0] != '1' || !exactEnabled("COH_WINE_DB_MANUAL_ATLAS"))
        return -1;
    length = GetEnvironmentVariableA(COH_DB_EXTERNAL_MAPS_DIRECTORY, g_directory, sizeof(g_directory));
    if (!length || length >= 200 || strchr(g_directory, '"'))
        return -1;
    attributes = GetFileAttributesA(g_directory);
    if (attributes == INVALID_FILE_ATTRIBUTES || !(attributes & FILE_ATTRIBUTE_DIRECTORY)
        || (attributes & FILE_ATTRIBUTE_REPARSE_POINT))
        return -1;
    fprintf(stdout, "\n%s\n", COH_DB_EXTERNAL_MAPS_ACK);
    fflush(stdout);
    return 1;
}

int cohDbExternalMapsMode(void)
{
    if (g_mode == -2)
        g_mode = decideMode();
    return g_mode;
}

/* Appends "key":"escaped" ; returns 0 when the record would overflow. */
static int putString(char *out, size_t *used, const char *key, const char *value, size_t limit)
{
    size_t i, start = *used;
    int written = _snprintf(out + *used, REQUEST_BYTES - *used, "%s\"%s\":\"", *used > 1 ? "," : "", key);
    if (written < 0 || (size_t)written >= REQUEST_BYTES - *used)
        return 0;
    *used += written;
    for (i = 0; value && value[i] && i < limit; i++) {
        unsigned char c = (unsigned char)value[i];
        char escaped[8];
        size_t n;
        if (c == '"' || c == '\\') { escaped[0] = '\\'; escaped[1] = (char)c; n = 2; }
        else if (c < 0x20 || c == 0x7f) { sprintf(escaped, "\\u%04x", c); n = 6; }
        else { escaped[0] = (char)c; n = 1; }
        if (*used + n + 2 >= REQUEST_BYTES) { *used = start; return 0; }
        memcpy(out + *used, escaped, n);
        *used += n;
    }
    if (value && i == limit && value[i]) { *used = start; return 0; }    /* never truncate silently */
    out[(*used)++] = '"';
    out[*used] = 0;
    return 1;
}

static int putInt(char *out, size_t *used, const char *key, int value)
{
    int written = _snprintf(out + *used, REQUEST_BYTES - *used, "%s\"%s\":%d", *used > 1 ? "," : "", key, value);
    if (written < 0 || (size_t)written >= REQUEST_BYTES - *used)
        return 0;
    *used += written;
    return 1;
}

int cohDbPublishMapRequest(int map_id, int cookie, int base_map_id, int is_static, int transient,
    int dont_auto_start, int preload_transient, const char *map_name, const char *mission_info,
    const char *command)
{
    char record[REQUEST_BYTES], path[MAX_PATH], temporary[MAX_PATH];
    size_t used = 1;
    HANDLE file;
    DWORD written = 0;
    int ok;

    if (cohDbExternalMapsMode() != 1 || map_id <= 0 || cookie <= 0) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return 0;
    }
    record[0] = '{';
    record[1] = 0;
    g_sequence++;
    ok = putInt(record, &used, "format", COH_DB_EXTERNAL_MAPS_FORMAT)
        && putInt(record, &used, "sequence", (int)g_sequence)
        && putInt(record, &used, "map_id", map_id) && putInt(record, &used, "cookie", cookie)
        && putInt(record, &used, "base_map_id", base_map_id) && putInt(record, &used, "is_static", is_static ? 1 : 0)
        && putInt(record, &used, "transient", transient ? 1 : 0)
        && putInt(record, &used, "dont_auto_start", dont_auto_start ? 1 : 0)
        && putInt(record, &used, "preload_transient", preload_transient ? 1 : 0)
        && putInt(record, &used, "db_process_id", (int)GetCurrentProcessId())
        && putString(record, &used, "map_name", map_name, 1023)
        && putString(record, &used, "mission_info", mission_info, 1023)
        && putString(record, &used, "command", command, 4096);
    if (!ok || used + 2 >= REQUEST_BYTES) {
        SetLastError(ERROR_INSUFFICIENT_BUFFER);
        return 0;
    }
    record[used++] = '}';
    record[used++] = '\n';
    if (_snprintf(path, sizeof(path), "%s\\map-%d-%d.json", g_directory, map_id, cookie) <= 0
        || _snprintf(temporary, sizeof(temporary), "%s.tmp", path) <= 0) {
        SetLastError(ERROR_BUFFER_OVERFLOW);
        return 0;
    }
    file = CreateFileA(temporary, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return 0;
    ok = WriteFile(file, record, (DWORD)used, &written, NULL) && written == used && FlushFileBuffers(file);
    CloseHandle(file);
    if (!ok || !MoveFileExA(temporary, path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        DeleteFileA(temporary);
        return 0;
    }
    fprintf(stdout, "%s map_id=%d cookie=%d static=%d\n", COH_DB_EXTERNAL_MAPS_REQUEST_MARKER,
        map_id, cookie, is_static ? 1 : 0);
    fflush(stdout);
    return 1;
}
