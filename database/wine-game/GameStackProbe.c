/* Separate PE32 observer for one private Wine prefix. Never launches or stops
 * a game process. Raw context/stack evidence is intentional: DbgHelp can block
 * indefinitely in Wine, and must never run while a target thread is suspended.
 * Build: cl /nologo /W4 /O2 /MT /D_WIN32_WINNT=0x0601 GameStackProbe.c
 * Run under the same Wine prefix: GameStackProbe.exe --runtime-dir Z:\\...\\runtime
 * A timed-out/killed probe is incomplete; its diagnostic run must be torn down,
 * not reused. No userspace finally block can survive external forced killing.
 */
#define _CRT_SECURE_NO_WARNINGS
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#define PROBE_MAX_PROCESSES 8
#define PROBE_MAX_THREADS 128
#define PROBE_MAX_MODULES 384
#define PROBE_STACK_WORDS 64
#define PROBE_OUTPUT_LIMIT (320U * 1024U)
#define PROBE_PATH_LIMIT 2048
#define PROBE_RECORD_LIMIT 16384

static wchar_t path_character(wchar_t value)
{
    if (value == L'/') return L'\\';
    if (value >= L'A' && value <= L'Z') return (wchar_t)(value + L'a' - L'A');
    return value;
}

static int same_path(const wchar_t *left, const wchar_t *right, size_t length)
{
    size_t i;
    for (i = 0; i < length; ++i)
        if (path_character(left[i]) != path_character(right[i])) return 0;
    return 1;
}

/* Deliberately an exact allowlist, not TestClient*.exe (which includes helpers).
 * Both arguments are absolute OS-resolved paths in the real probe. */
static int accepted_path(const wchar_t *path, const wchar_t *runtime)
{
    static const wchar_t *names[] = {
        L"DbServer.exe", L"MapServer.exe", L"TestClient.exe",
        L"TestClientCreate.exe", L"TestClientResume.exe"
    };
    size_t path_length = wcslen(path), runtime_length = wcslen(runtime);
    size_t i;
    while (runtime_length && path_character(runtime[runtime_length - 1]) == L'\\')
        --runtime_length;
    if (!runtime_length || path_length <= runtime_length + 1 ||
        !same_path(path, runtime, runtime_length) ||
        path_character(path[runtime_length]) != L'\\') return 0;
    path += runtime_length + 1;
    for (i = 0; i < sizeof(names) / sizeof(names[0]); ++i) {
        size_t length = wcslen(names[i]);
        if (wcslen(path) == length && same_path(path, names[i], length)) return 1;
    }
    return 0;
}

#ifdef COH_STACK_PROBE_PATH_TEST
/* Portable test entry point; absent from the released Windows binary. */
int main(int argc, char **argv)
{
    wchar_t path[PROBE_PATH_LIMIT], runtime[PROBE_PATH_LIMIT];
    if (argc != 3 || mbstowcs(path, argv[1], PROBE_PATH_LIMIT) >= PROBE_PATH_LIMIT ||
        mbstowcs(runtime, argv[2], PROBE_PATH_LIMIT) >= PROBE_PATH_LIMIT) return 2;
    return accepted_path(path, runtime) ? 0 : 1;
}
#else
#define WIN32_LEAN_AND_MEAN
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
#include <windows.h>
#include <tlhelp32.h>
#include <stdarg.h>

#if !defined(_M_IX86) && !defined(__i386__)
#error GameStackProbe must be compiled as PE32/x86.
#endif

static char record[PROBE_RECORD_LIMIT];
static size_t record_used;
static unsigned output_bytes, process_count, thread_count, module_count, errors;
static int record_failed, truncated, output_failed, unsafe_resume;

static void begin_record(void)
{
    record_used = 0;
    record_failed = 0;
}

static void append(const char *format, ...)
{
    int count;
    va_list args;
    if (record_failed) return;
    va_start(args, format);
    count = vsnprintf(record + record_used, sizeof(record) - record_used, format, args);
    va_end(args);
    if (count < 0 || (size_t)count >= sizeof(record) - record_used) record_failed = 1;
    else record_used += (size_t)count;
}

static void string_value(const wchar_t *value)
{
    append("\"");
    while (*value) {
        unsigned code = (unsigned)*value++;
        if (code == '"' || code == '\\') append("\\%c", (char)code);
        else if (code < 32 || code >= 127) append("\\u%04x", code);
        else append("%c", (char)code);
    }
    append("\"");
}

static void emit(int terminal)
{
    unsigned ceiling = PROBE_OUTPUT_LIMIT - (terminal ? 0U : 1024U);
    if (record_failed || record_used > ceiling - output_bytes) {
        truncated = 1;
        return;
    }
    if (fwrite(record, 1, record_used, stdout) != record_used || fflush(stdout))
        output_failed = 1;
    output_bytes += (unsigned)record_used;
}

static void error_record(const char *stage, DWORD pid, DWORD tid, DWORD code)
{
    ++errors;
    begin_record();
    append("{\"kind\":\"error\",\"stage\":\"%s\",\"pid\":%lu,\"tid\":%lu,\"win32_error\":%lu}\n",
           stage, pid, tid, code);
    emit(0);
}

typedef struct ThreadCapture {
    CONTEXT context;
    DWORD words[PROBE_STACK_WORDS];
    SIZE_T bytes;
    DWORD suspend_count, suspend_error, context_error, read_error, resume_error;
    int context_valid, resume_ok;
} ThreadCapture;

static void capture_thread(HANDLE process, HANDLE thread, ThreadCapture *capture)
{
    memset(capture, 0, sizeof(*capture));
    capture->context.ContextFlags = CONTEXT_FULL;
    capture->suspend_count = SuspendThread(thread);
    if (capture->suspend_count == (DWORD)-1) {
        capture->suspend_error = GetLastError();
        return;
    }
    /* No allocation, formatting, filesystem, DbgHelp or output under suspension.
     * Restore exactly our one suspension, even when context/memory capture fails
     * or MSVC unwinds a structured exception. Preserve pre-existing suspension. */
    __try {
        if (GetThreadContext(thread, &capture->context)) {
            capture->context_valid = 1;
            if (!ReadProcessMemory(process, (LPCVOID)(uintptr_t)capture->context.Esp,
                                   capture->words, sizeof(capture->words), &capture->bytes))
                capture->read_error = GetLastError();
        } else capture->context_error = GetLastError();
    } __finally {
        if (ResumeThread(thread) == (DWORD)-1) capture->resume_error = GetLastError();
        else capture->resume_ok = 1;
    }
}

static void threads_for(HANDLE process, DWORD pid)
{
    THREADENTRY32 entry;
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    DWORD enumeration_error;
    unsigned scanned = 0;
    int stopped = 0;
    if (snapshot == INVALID_HANDLE_VALUE) {
        error_record("thread_snapshot", pid, 0, GetLastError());
        return;
    }
    memset(&entry, 0, sizeof(entry));
    entry.dwSize = sizeof(entry);
    if (!Thread32First(snapshot, &entry)) {
        enumeration_error = GetLastError();
        if (enumeration_error != ERROR_NO_MORE_FILES)
            error_record("thread_first", pid, 0, enumeration_error);
        CloseHandle(snapshot);
        return;
    }
    do {
        HANDLE thread;
        ThreadCapture capture;
        unsigned i;
        if (++scanned > 4096) { stopped = truncated = 1; break; }
        if (entry.th32OwnerProcessID != pid) continue;
        if (thread_count >= PROBE_MAX_THREADS || output_failed) { stopped = truncated = 1; break; }
        ++thread_count;
        thread = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION,
                            FALSE, entry.th32ThreadID);
        if (!thread) { error_record("thread_open", pid, entry.th32ThreadID, GetLastError()); continue; }
        if (GetProcessIdOfThread(thread) != pid) {
            error_record("thread_owner_changed", pid, entry.th32ThreadID, ERROR_INVALID_DATA);
            CloseHandle(thread);
            continue;
        }
        capture_thread(process, thread, &capture);
        CloseHandle(thread);
        if (capture.suspend_error || capture.context_error || capture.read_error || !capture.resume_ok)
            ++errors;
        begin_record();
        append("{\"kind\":\"thread\",\"pid\":%lu,\"tid\":%lu,\"context_valid\":%s,"
               "\"suspend_count_before\":%lu,\"resume_ok\":%s,\"suspend_error\":%lu,"
               "\"context_error\":%lu,\"read_error\":%lu,\"resume_error\":%lu,"
               "\"eip\":\"0x%08lx\",\"esp\":\"0x%08lx\",\"ebp\":\"0x%08lx\","
               "\"eflags\":\"0x%08lx\",\"eax\":\"0x%08lx\",\"ebx\":\"0x%08lx\","
               "\"ecx\":\"0x%08lx\",\"edx\":\"0x%08lx\",\"esi\":\"0x%08lx\","
               "\"edi\":\"0x%08lx\",\"stack_bytes\":%u,\"stack_words\":[",
               pid, entry.th32ThreadID, capture.context_valid ? "true" : "false",
               capture.suspend_count, capture.resume_ok ? "true" : "false", capture.suspend_error,
               capture.context_error, capture.read_error, capture.resume_error,
               capture.context.Eip, capture.context.Esp, capture.context.Ebp, capture.context.EFlags,
               capture.context.Eax, capture.context.Ebx, capture.context.Ecx, capture.context.Edx,
               capture.context.Esi, capture.context.Edi, (unsigned)capture.bytes);
        for (i = 0; i < capture.bytes / sizeof(DWORD) && i < PROBE_STACK_WORDS; ++i)
            append("%s\"0x%08lx\"", i ? "," : "", capture.words[i]);
        append("]}\n");
        emit(0);
        /* A failed resume means the run is unsafe to reuse. Do not take more
         * suspensions; the parent will receive nonzero status and tear it down. */
        if (capture.suspend_count != (DWORD)-1 && !capture.resume_ok) {
            unsafe_resume = 1;
            stopped = 1;
            break;
        }
    } while (Thread32Next(snapshot, &entry));
    enumeration_error = GetLastError();
    if (!stopped && enumeration_error != ERROR_NO_MORE_FILES)
        error_record("thread_next", pid, 0, enumeration_error);
    CloseHandle(snapshot);
}

static int image_identity(HANDLE process, const MODULEENTRY32W *main_module,
                          IMAGE_NT_HEADERS32 *header)
{
    IMAGE_DOS_HEADER dos;
    SIZE_T bytes;
    if (!ReadProcessMemory(process, main_module->modBaseAddr, &dos, sizeof(dos), &bytes) ||
        bytes != sizeof(dos) || dos.e_magic != IMAGE_DOS_SIGNATURE ||
        dos.e_lfanew < (LONG)sizeof(dos) || dos.e_lfanew > 1048576) return 0;
    if (!ReadProcessMemory(process, main_module->modBaseAddr + dos.e_lfanew,
                           header, sizeof(*header), &bytes) || bytes != sizeof(*header)) return 0;
    return header->Signature == IMAGE_NT_SIGNATURE &&
           header->FileHeader.Machine == IMAGE_FILE_MACHINE_I386 &&
           header->OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR32_MAGIC;
}

static void inspect_process(HANDLE process, DWORD pid, const wchar_t *path)
{
    HANDLE snapshot;
    MODULEENTRY32W module;
    IMAGE_NT_HEADERS32 header;
    DWORD enumeration_error;
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (snapshot == INVALID_HANDLE_VALUE) {
        error_record("module_snapshot", pid, 0, GetLastError());
        return;
    }
    memset(&module, 0, sizeof(module));
    module.dwSize = sizeof(module);
    if (!Module32FirstW(snapshot, &module)) {
        error_record("module_first", pid, 0, GetLastError());
        CloseHandle(snapshot);
        return;
    }
    if (wcslen(module.szExePath) != wcslen(path) ||
        !same_path(module.szExePath, path, wcslen(path)) || !image_identity(process, &module, &header)) {
        error_record("image_not_verified_pe32", pid, 0, ERROR_INVALID_DATA);
        CloseHandle(snapshot);
        return;
    }
    ++process_count;
    begin_record();
    append("{\"kind\":\"process\",\"pid\":%lu,\"image_path\":", pid);
    string_value(path);
    append(",\"image_base\":\"0x%08lx\",\"pe_machine\":%u,\"pe_timestamp\":%lu,"
           "\"image_size\":%lu,\"entry_rva\":\"0x%08lx\",\"pe_checksum\":%lu}\n",
           (DWORD)(uintptr_t)module.modBaseAddr, (unsigned)header.FileHeader.Machine,
           header.FileHeader.TimeDateStamp, header.OptionalHeader.SizeOfImage,
           header.OptionalHeader.AddressOfEntryPoint, header.OptionalHeader.CheckSum);
    emit(0);
    threads_for(process, pid);
    do {
        if (module_count >= PROBE_MAX_MODULES || output_failed) { truncated = 1; break; }
        ++module_count;
        begin_record();
        append("{\"kind\":\"module\",\"pid\":%lu,\"base\":\"0x%08lx\",\"bytes\":%lu,\"name\":",
               pid, (DWORD)(uintptr_t)module.modBaseAddr, module.modBaseSize);
        string_value(module.szModule);
        append(",\"path\":");
        string_value(module.szExePath);
        append("}\n");
        emit(0);
    } while (Module32NextW(snapshot, &module));
    enumeration_error = GetLastError();
    if (!truncated && !output_failed && enumeration_error != ERROR_NO_MORE_FILES)
        error_record("module_next", pid, 0, enumeration_error);
    CloseHandle(snapshot);
}

int wmain(int argc, wchar_t **argv)
{
    wchar_t runtime[PROBE_PATH_LIMIT];
    DWORD length, attributes, enumeration_error;
    PROCESSENTRY32W entry;
    HANDLE snapshot;
    unsigned scanned = 0, matched = 0;
    if (argc != 3 || wcscmp(argv[1], L"--runtime-dir")) {
        fputs("Usage: GameStackProbe.exe --runtime-dir <absolute Windows runtime path>\n", stderr);
        return 2;
    }
    if (wcslen(argv[2]) < 3 || argv[2][1] != L':' ||
        (argv[2][2] != L'\\' && argv[2][2] != L'/')) {
        fputs("runtime directory must be an absolute drive path\n", stderr);
        return 2;
    }
    length = GetFullPathNameW(argv[2], PROBE_PATH_LIMIT, runtime, NULL);
    if (!length || length >= PROBE_PATH_LIMIT) return 2;
    attributes = GetFileAttributesW(runtime);
    if (attributes == INVALID_FILE_ATTRIBUTES || !(attributes & FILE_ATTRIBUTE_DIRECTORY)) return 2;
    begin_record();
    append("{\"kind\":\"probe\",\"format\":1,\"pid\":%lu,\"runtime_dir\":", GetCurrentProcessId());
    string_value(runtime);
    append(",\"capture\":\"x86-context-and-stack-words\",\"max_processes\":%u,"
           "\"max_threads\":%u,\"max_modules\":%u,\"max_stack_words\":%u,\"max_output_bytes\":%u}\n",
           PROBE_MAX_PROCESSES, PROBE_MAX_THREADS, PROBE_MAX_MODULES, PROBE_STACK_WORDS, PROBE_OUTPUT_LIMIT);
    emit(0);
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) error_record("process_snapshot", 0, 0, GetLastError());
    else {
        memset(&entry, 0, sizeof(entry));
        entry.dwSize = sizeof(entry);
        if (Process32FirstW(snapshot, &entry)) {
            do {
                HANDLE process;
                wchar_t path[PROBE_PATH_LIMIT];
                DWORD path_length = PROBE_PATH_LIMIT;
                if (++scanned > 4096 || matched >= PROBE_MAX_PROCESSES || output_failed || unsafe_resume) {
                    truncated = 1;
                    break;
                }
                /* Read-only access only; PROCESS_TERMINATE/VM_WRITE are never requested. */
                process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ,
                                      FALSE, entry.th32ProcessID);
                if (!process) continue;
                if (QueryFullProcessImageNameW(process, 0, path, &path_length) && accepted_path(path, runtime)) {
                    ++matched;
                    inspect_process(process, entry.th32ProcessID, path);
                }
                CloseHandle(process);
            } while (Process32NextW(snapshot, &entry));
            enumeration_error = GetLastError();
            if (!truncated && !output_failed && enumeration_error != ERROR_NO_MORE_FILES)
                error_record("process_next", 0, 0, enumeration_error);
        } else error_record("process_first", 0, 0, GetLastError());
        CloseHandle(snapshot);
    }
    begin_record();
    append("{\"kind\":\"complete\",\"format\":1,\"processes\":%u,\"threads\":%u,\"modules\":%u,"
           "\"errors\":%u,\"truncated\":%s,\"bytes_before_complete\":%u}\n",
           process_count, thread_count, module_count, errors, truncated ? "true" : "false", output_bytes);
    emit(1);
    return output_failed || errors || truncated || !process_count ? 1 : 0;
}
#endif
