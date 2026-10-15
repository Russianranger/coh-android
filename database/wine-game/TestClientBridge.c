/* Diagnostic launcher/observer for unchanged Win32 TestClient executables.
 * No socket, SQL, game packet, entity or save implementation lives here.
 * The parent owns the Wine process tree. This helper owns one Windows child,
 * binds the stock named pipe to that PID, and observes its actual console.
 */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#define _CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "bridge_protocol.h"

#define ROWS 16384
#define WIDTH 200
#define MAX_WIDTH 256
#define CAPTURE_LIMIT 16777216
#define EVENT_LIMIT 8388608
#define PATH_LIMIT 2048

static const char *directory;
static FILE *events;
static HANDLE pipe_handle = INVALID_HANDLE_VALUE, console_handle = INVALID_HANDLE_VALUE;
static PROCESS_INFORMATION child;
static ULONGLONG started;
static unsigned sequence, event_bytes, command_count, snapshots, version_requests;
static int connected, pid_verified, console_attached, ready, disconnected, final_snapshot;
static int forced_stop, framing_complete = 1, console_width, last_y;
static const char *failure;
static char failure_text[256];
static int drain(void);

static int fail(const char *reason)
{
    if (!failure) {
        snprintf(failure_text, sizeof(failure_text), "%s (Win32 error %lu)", reason, GetLastError());
        failure = failure_text;
    }
    return 0;
}

static int path_for(char *path, const char *name)
{
    int n = snprintf(path, PATH_LIMIT, "%s\\%s", directory, name);
    return n > 0 && n < PATH_LIMIT ? 1 : fail("output path exceeds bound");
}

static int ordinary_file(const char *path)
{
    DWORD attr = GetFileAttributesA(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT));
}

static int prepare_directory(void)
{
    DWORD attributes = GetFileAttributesA(directory);
    char pattern[PATH_LIMIT];
    WIN32_FIND_DATAA entry;
    HANDLE search;
    if (attributes == INVALID_FILE_ATTRIBUTES) return CreateDirectoryA(directory, NULL) ? 1 : 0;
    if (!(attributes & FILE_ATTRIBUTE_DIRECTORY) || (attributes & FILE_ATTRIBUTE_REPARSE_POINT)) return 0;
    if (!path_for(pattern, "*")) return 0;
    search = FindFirstFileA(pattern, &entry);
    if (search == INVALID_HANDLE_VALUE) return GetLastError() == ERROR_FILE_NOT_FOUND;
    do {
        if (strcmp(entry.cFileName, ".") && strcmp(entry.cFileName, "..")) {
            FindClose(search); return 0;
        }
    } while (FindNextFileA(search, &entry));
    attributes = GetLastError();
    FindClose(search);
    return attributes == ERROR_NO_MORE_FILES;
}

static int json_string(FILE *out, const char *text)
{
    const unsigned char *p = (const unsigned char *)text;
    fputc('"', out);
    while (*p) {
        if (*p == '"' || *p == '\\') { fputc('\\', out); fputc(*p, out); }
        else if (*p < 32 || *p >= 127) fprintf(out, "\\u%04x", (unsigned)*p);
        else fputc(*p, out);
        ++p;
    }
    fputc('"', out);
    return !ferror(out);
}

static int event(const char *kind, const char *value, const char *raw, unsigned command_sequence)
{
    long size;
    /* Worst-case escaping plus metadata must fit before anything is appended. */
    size_t bound = 6 * (strlen(kind) + strlen(value) + strlen(raw)) + 256;
    if (!events || sequence >= 20000 || bound > EVENT_LIMIT - event_bytes)
        return fail("event evidence exceeds bound");
    fprintf(events, "{\"sequence\":%u,\"kind\":", ++sequence);
    json_string(events, kind);
    fputs(",\"value\":", events); json_string(events, value);
    fputs(",\"raw\":", events); json_string(events, raw);
    fprintf(events, ",\"elapsed_ms\":%llu", (unsigned long long)(GetTickCount64() - started));
    if (command_sequence) fprintf(events, ",\"command_sequence\":%u", command_sequence);
    fputs("}\n", events);
    if (fflush(events) || (size = ftell(events)) < 0) return fail("event write failed");
    event_bytes = (unsigned)size;
    return 1;
}

static int replace_file(const char *temporary, const char *final)
{
    ULONGLONG deadline = GetTickCount64() + 1000;
    while (!MoveFileExA(temporary, final, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        if (GetTickCount64() >= deadline) return fail("atomic evidence replacement failed");
        Sleep(10);
    }
    return 1;
}

static int snapshot(void)
{
    CONSOLE_SCREEN_BUFFER_INFO before, after;
    WCHAR *cells;
    char *utf8;
    DWORD read;
    size_t used = 0;
    int row, count, attempt;
    char path[PATH_LIMIT], temporary[PATH_LIMIT];
    FILE *out;
    if (!console_attached) return 0;
    for (attempt = 0; attempt < 5; ++attempt) {
        if (!GetConsoleScreenBufferInfo(console_handle, &before)) return fail("console query failed");
        if (before.dwSize.X != console_width || before.dwSize.Y != ROWS ||
            before.dwCursorPosition.X < 0 || before.dwCursorPosition.X >= console_width ||
            before.dwCursorPosition.Y < last_y || before.dwCursorPosition.Y >= ROWS - 1)
            return fail("console scrolled or changed outside capture bound");
        count = console_width * (before.dwCursorPosition.Y + 1);
        cells = (WCHAR *)malloc((size_t)count * sizeof(WCHAR));
        if (!cells) return fail("console allocation failed");
        { COORD origin = {0, 0};
          if (!ReadConsoleOutputCharacterW(console_handle, cells, (DWORD)count, origin, &read) || read != (DWORD)count) {
              free(cells); return fail("console snapshot was incomplete");
          }
        }
        if (!GetConsoleScreenBufferInfo(console_handle, &after)) { free(cells); return fail("console requery failed"); }
        if (after.dwCursorPosition.X != before.dwCursorPosition.X || after.dwCursorPosition.Y != before.dwCursorPosition.Y) {
            free(cells); continue;
        }
        utf8 = (char *)malloc((size_t)count * 3 + ROWS + 1);
        if (!utf8) { free(cells); return fail("console encoding allocation failed"); }
        for (row = 0; row <= before.dwCursorPosition.Y; ++row) {
            int length = console_width, bytes;
            WCHAR *line = cells + row * console_width;
            while (length && line[length - 1] == L' ') --length;
            bytes = length ? WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, line, length,
                                                 utf8 + used, count * 3 + ROWS - (int)used, NULL, NULL) : 0;
            if (length && !bytes) { free(utf8); free(cells); return fail("console has invalid Unicode"); }
            used += (size_t)bytes;
            utf8[used++] = '\n';
        }
        free(cells);
        if (used > CAPTURE_LIMIT) { free(utf8); return fail("console evidence exceeds bound"); }
        if (!path_for(path, "console.txt") || !path_for(temporary, "console.txt.tmp")) { free(utf8); return 0; }
        out = fopen(temporary, "wb");
        if (!out) { free(utf8); return fail("console output open failed"); }
        if (fwrite(utf8, 1, used, out) != used) { fclose(out); free(utf8); return fail("console output write failed"); }
        free(utf8);
        if (fclose(out) || !replace_file(temporary, path)) return fail("console publication failed");
        last_y = before.dwCursorPosition.Y;
        ++snapshots;
        return 1;
    }
    /* A changing screen is not an accepted snapshot. Retry in the main loop. */
    return 0;
}

static int attach_console(void)
{
    DWORD peers[32], count, i;
    int found_child = 0, found_self = 0;
    CONSOLE_SCREEN_BUFFER_INFO info;
    COORD dimensions;
    if (!AttachConsole(child.dwProcessId)) {
        if (GetLastError() == ERROR_INVALID_HANDLE) return 1;
        return fail("AttachConsole failed");
    }
    count = GetConsoleProcessList(peers, 32);
    if (!count || count > 32) return fail("console process list exceeds bound");
    for (i = 0; i < count; ++i) {
        if (peers[i] == child.dwProcessId) found_child = 1;
        if (peers[i] == GetCurrentProcessId()) found_self = 1;
    }
    if (!found_child || !found_self) return fail("console child PID mismatch");
    console_handle = CreateFileW(L"CONOUT$", GENERIC_READ | GENERIC_WRITE,
                                 FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
    if (console_handle == INVALID_HANDLE_VALUE || !GetConsoleScreenBufferInfo(console_handle, &info))
        return fail("console open failed");
    if (info.dwSize.X <= 0 || info.dwSize.X > MAX_WIDTH || info.dwSize.Y > ROWS ||
        info.dwCursorPosition.Y >= info.dwSize.Y - 1) return fail("initial console may have scrolled");
    console_width = info.dwSize.X < WIDTH ? WIDTH : info.dwSize.X;
    dimensions.X = (SHORT)console_width; dimensions.Y = ROWS;
    if (!SetConsoleScreenBufferSize(console_handle, dimensions)) return fail("console resize failed");
    console_attached = 1;
    return 1;
}

static int connect_pipe(void)
{
    ULONG peer;
    DWORD error;
    /* PIPE_NOWAIT success means a disconnected instance entered listening.
     * Microsoft specifies ERROR_PIPE_CONNECTED for an established peer. */
    if (ConnectNamedPipe(pipe_handle, NULL)) return 1;
    error = GetLastError();
    if (error == ERROR_PIPE_LISTENING) return 1;
    if (error != ERROR_PIPE_CONNECTED) return fail("launcher pipe connect failed");
    if (!GetNamedPipeClientProcessId(pipe_handle, &peer) || peer != child.dwProcessId)
        return fail("launcher transport child PID mismatch");
    connected = 1;
    return 1;
}

static int stable_snapshot(void)
{
    ULONGLONG deadline = GetTickCount64() + 2000;
    do {
        if (snapshot()) return 1;
        Sleep(10);
    } while (GetTickCount64() < deadline);
    return fail("final console snapshot did not become stable");
}

static int drain_to_disconnect(void)
{
    ULONGLONG deadline = GetTickCount64() + 5000;
    if (!connected) return fail("launcher pipe was never connected");
    do {
        if (!drain()) return 0;
        if (disconnected) return 1;
        Sleep(10);
    } while (GetTickCount64() < deadline);
    return fail("final launcher pipe drain did not reach disconnect");
}

static int drain(void)
{
    char data[COH_BRIDGE_FRAME_LIMIT], kind[80], value[COH_BRIDGE_FRAME_LIMIT];
    DWORD available, read, error;
    int batch;
    if (!connected || disconnected) return 1;
    for (batch = 0; batch < 128; ++batch) {
        char *colon, *end;
        size_t length;
        if (!PeekNamedPipe(pipe_handle, NULL, 0, NULL, &available, NULL)) {
            error = GetLastError();
            if (error == ERROR_BROKEN_PIPE || error == ERROR_PIPE_NOT_CONNECTED || error == ERROR_NO_DATA) {
                disconnected = 1; return 1;
            }
            return fail("launcher pipe peek failed");
        }
        if (!available) return 1;
        if (!ReadFile(pipe_handle, data, sizeof(data), &read, NULL)) {
            framing_complete = 0; return fail("launcher pipe message was partial or exceeded bound");
        }
        if (!coh_bridge_frame(data, read)) {
            framing_complete = 0; return fail("launcher pipe has invalid NUL framing");
        }
        colon = strchr(data, ':');
        if (!colon || colon == data || (size_t)(colon - data) >= sizeof(kind))
            return fail("launcher message has invalid kind");
        length = (size_t)(colon - data);
        while (length && (data[length - 1] == ' ' || data[length - 1] == '\t')) --length;
        memcpy(kind, data, length); kind[length] = 0;
        ++colon;
        while (*colon == ' ' || *colon == '\t') ++colon;
        strcpy(value, colon);
        end = value + strlen(value);
        while (end > value && (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\r' || end[-1] == '\n')) *--end = 0;
        if (!strcmp(kind, "PID")) {
            if (pid_verified || !coh_bridge_pid(value, child.dwProcessId)) return fail("launcher protocol PID mismatch");
            pid_verified = 1;
        } else if (!pid_verified) return fail("launcher message preceded required PID");
        if (!strcmp(kind, "VersionRequest") && ++version_requests != 1)
            return fail("repeated launcher version request");
        if (!event(kind, value, data, 0)) return 0;
    }
    return 1;
}

static int publish_ready(void)
{
    char path[PATH_LIMIT], temporary[PATH_LIMIT];
    FILE *out;
    if (!path_for(path, "ready.json") || !path_for(temporary, "ready.json.tmp")) return 0;
    out = fopen(temporary, "wb");
    if (!out) return fail("readiness output open failed");
    fprintf(out, "{\"format\":1,\"child_pid\":%lu,\"transport_pid\":%lu,"
            "\"console_attached\":true,\"pipe_pid_verified\":true,\"protocol_pid_verified\":true,"
            "\"initial_snapshot\":true,\"version_requests\":1,\"buffer_rows_limit\":%d,"
            "\"capture_byte_limit\":%d,\"event_byte_limit\":%d}\n",
            child.dwProcessId, child.dwProcessId, ROWS, CAPTURE_LIMIT, EVENT_LIMIT);
    if (fclose(out)) return fail("readiness output failed");
    return replace_file(temporary, path);
}

static int send_message(const char *message)
{
    DWORD written, length = (DWORD)strlen(message) + 1;
    ULONGLONG deadline = GetTickCount64() + 3000;
    do {
        if (!WriteFile(pipe_handle, message, length, &written, NULL)) {
            if (GetLastError() != ERROR_NO_DATA) return fail("launcher pipe write failed");
        } else if (written == length) return 1;
        else if (written) return fail("launcher pipe write was partial");
        if (!drain()) return 0;
        Sleep(10);
    } while (GetTickCount64() < deadline);
    return fail("launcher pipe write timed out");
}

static int command_file(void)
{
    char name[64], path[PATH_LIMIT], data[COH_BRIDGE_COMMAND_LIMIT];
    FILE *in;
    size_t bytes;
    DWORD attributes;
    if (command_count >= 128) return fail("command count exceeds bound");
    snprintf(name, sizeof(name), "command-%06u.txt", command_count + 1);
    if (!path_for(path, name)) return 0;
    attributes = GetFileAttributesA(path);
    if (attributes == INVALID_FILE_ATTRIBUTES) {
        if (GetLastError() == ERROR_FILE_NOT_FOUND || GetLastError() == ERROR_PATH_NOT_FOUND) return 1;
        return fail("command file query failed");
    }
    if (!ordinary_file(path)) return fail("command file is not ordinary");
    in = fopen(path, "rb");
    if (!in) return fail("command file open failed");
    bytes = fread(data, 1, sizeof(data), in);
    if (ferror(in)) { fclose(in); return fail("command file read failed"); }
    fclose(in);
    if (!coh_bridge_command(data, bytes)) return fail("command text exceeds ASCII bound");
    data[bytes] = 0;
    if (strncmp(data, "CMD ", 4) || bytes <= 4) return fail("control accepts only stock CMD messages");
    if (!send_message(data)) return 0;
    ++command_count;
    return event("Command", data, data, command_count);
}

static void result(DWORD exit_code, int have_exit_code)
{
    char path[PATH_LIMIT], temporary[PATH_LIMIT];
    FILE *out;
    if (!path_for(path, "result.json") || !path_for(temporary, "result.json.tmp")) return;
    out = fopen(temporary, "wb");
    if (!out) { fail("result output open failed"); return; }
    fprintf(out, "{\"format\":1,\"child_pid\":%lu,\"child_exit_code\":", child.dwProcessId);
    if (have_exit_code) fprintf(out, "%lu", exit_code); else fputs("null", out);
    fprintf(out, ",\"child_forced_stop\":%s,\"final_snapshot\":%s,\"pipe_framing_complete\":%s,"
            "\"pipe_disconnected\":%s,\"version_requests\":%u,\"command_count\":%u,"
            "\"event_count\":%u,\"console_snapshots\":%u,\"capture_byte_limit\":%d,"
            "\"event_byte_limit\":%d,\"error\":",
            forced_stop ? "true" : "false", final_snapshot ? "true" : "false",
            framing_complete ? "true" : "false", disconnected ? "true" : "false",
            version_requests, command_count, sequence, snapshots, CAPTURE_LIMIT, EVENT_LIMIT);
    if (failure) json_string(out, failure); else fputs("null", out);
    fputs("}\n", out);
    if (fclose(out)) fail("result output write failed");
    else replace_file(temporary, path);
}

int main(int argc, char **argv)
{
    const char *version = NULL;
    unsigned timeout = 0;
    int i, child_arg = 0, stopped = 0, exited = 0;
    char path[PATH_LIMIT], command_line[32768] = "", pid_text[32];
    size_t used = 0;
    DWORD exit_code = 0;
    ULONGLONG next_snapshot = 0;
    STARTUPINFOA startup;
    started = GetTickCount64();
    memset(&startup, 0, sizeof(startup)); startup.cb = sizeof(startup);
    for (i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--") && i + 1 < argc) { child_arg = i + 1; break; }
        if (i + 1 >= argc) return 2;
        if (!strcmp(argv[i], "--output")) directory = argv[++i];
        else if (!strcmp(argv[i], "--version")) version = argv[++i];
        else if (!strcmp(argv[i], "--timeout")) {
            char *end;
            unsigned long value = strtoul(argv[++i], &end, 10);
            if (*end || value < 1 || value > 7200) return 2;
            timeout = (unsigned)value;
        } else return 2;
    }
    if (!directory || !version || !timeout || !child_arg ||
        !coh_bridge_command(version, strlen(version)) || strlen(directory) > 1500) return 2;
    if (!prepare_directory()) return 2; /* new or verified empty private directory */
    if (!path_for(path, "events.jsonl")) return 2;
    events = fopen(path, "wb");
    if (!events) return 2;
    for (i = child_arg; i < argc; ++i)
        if (!coh_bridge_quote(command_line, sizeof(command_line), &used, argv[i])) { fail("child arguments exceed bound"); goto cleanup; }
    pipe_handle = CreateNamedPipeW(L"\\\\.\\pipe\\TestClientLauncher",
        PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE,
        PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_NOWAIT | PIPE_REJECT_REMOTE_CLIENTS,
        1, 131072, 131072, 0, NULL);
    if (pipe_handle == INVALID_HANDLE_VALUE) { fail("exclusive launcher pipe creation failed"); goto cleanup; }
    /* The unchanged GUI client allocates and configures its own new console. */
    FreeConsole();
    if (!CreateProcessA(argv[child_arg], command_line, NULL, NULL, FALSE, DETACHED_PROCESS, NULL, NULL, &startup, &child)) {
        fail("TestClient launch failed"); goto cleanup;
    }
    CloseHandle(child.hThread); child.hThread = NULL;
    snprintf(pid_text, sizeof(pid_text), "%lu", child.dwProcessId);
    if (!event("BridgeStarted", pid_text, "", 0)) goto cleanup;
    while (!failure) {
        ULONGLONG now = GetTickCount64();
        if (now - started >= (ULONGLONG)timeout * 1000) { fail("bridge deadline expired"); break; }
        if (!console_attached && !attach_console()) break;
        if (!connected && !connect_pipe()) break;
        if (!drain()) break;
        if (console_attached && now >= next_snapshot) {
            snapshot();
            if (failure) break;
            next_snapshot = now + 100;
        }
        if (!ready && console_attached && snapshots && pid_verified && version_requests == 1) {
            if (!publish_ready()) break;
            ready = 1;
            if (!send_message(version) || !event("VersionReply", version, version, 0)) break;
        }
        if (ready && !disconnected && !command_file()) break;
        if (!path_for(path, "stop")) break;
        if (GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES) {
            if (!ordinary_file(path)) { fail("stop marker is not ordinary"); break; }
            stopped = 1; break;
        }
        if (WaitForSingleObject(child.hProcess, 0) == WAIT_OBJECT_0) { exited = 1; break; }
        if (!ready && now - started > 60000) { fail("launcher readiness timed out"); break; }
        Sleep(10);
    }
cleanup:
    /* A stop request is harness cleanup, never evidence of protocol logout/save. */
    if (console_attached) {
        stable_snapshot();
    } else fail("child console was never captured");
    if (child.hProcess) {
        if (WaitForSingleObject(child.hProcess, 0) != WAIT_OBJECT_0) {
            forced_stop = 1;
            if (!TerminateProcess(child.hProcess, 125) || WaitForSingleObject(child.hProcess, 5000) != WAIT_OBJECT_0)
                fail("child cleanup did not complete");
        }
        if (GetExitCodeProcess(child.hProcess, &exit_code) && exit_code != STILL_ACTIVE) exited = 1;
        else fail("child exit status unavailable");
        drain_to_disconnect();
        if (console_attached) final_snapshot = stable_snapshot();
        CloseHandle(child.hProcess);
    }
    if (!ready) fail("launcher never reached verified readiness");
    if (!stopped && !exited) fail("bridge ended without child exit or explicit stop");
    if (failure && events) event("BridgeError", failure, "", 0);
    if (events) { fclose(events); events = NULL; }
    result(exit_code, exited);
    if (console_handle != INVALID_HANDLE_VALUE) CloseHandle(console_handle);
    FreeConsole();
    if (pipe_handle != INVALID_HANDLE_VALUE) { DisconnectNamedPipe(pipe_handle); CloseHandle(pipe_handle); }
    return failure ? 1 : 0;
}
