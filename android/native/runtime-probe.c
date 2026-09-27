#include <windows.h>
#include <stdio.h>
#include <string.h>

#ifndef LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR
#define LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR 0x00000100
#endif
#ifndef LOAD_LIBRARY_SEARCH_DEFAULT_DIRS
#define LOAD_LIBRARY_SEARCH_DEFAULT_DIRS 0x00001000
#endif

typedef unsigned long (__cdecl *probe_fn)(void);
#define DRIVER_PATH_CAPACITY 1024

struct driver_registration {
    const char *name;
    LONG key_error;
    LONG driver_error;
    DWORD type;
    char path[DRIVER_PATH_CAPACITY];
};

static int driver_failure(const char *stage, DWORD error) {
    fprintf(stderr, "COH_ODBC_DRIVER_V1 FAIL stage=%s error=%lu\n", stage, (unsigned long)error);
    return 10;
}

static int absolute_path(const char *path) {
    unsigned char drive = (unsigned char)path[0];
    if (!path[0] || !path[1]) return 0;
    if (path[0] == '\\' && path[1] == '\\') return 1;
    return ((drive >= 'A' && drive <= 'Z') || (drive >= 'a' && drive <= 'z'))
        && path[1] == ':' && (path[2] == '\\' || path[2] == '/');
}

static void registration(struct driver_registration *entry, const char *name) {
    HKEY key;
    char subkey[256];
    DWORD bytes = sizeof(entry->path), expanded;
    size_t i;
    memset(entry, 0, sizeof(*entry));
    entry->name = name;
    snprintf(subkey, sizeof(subkey), "SOFTWARE\\ODBC\\ODBCINST.INI\\%s", name);
    entry->key_error = RegOpenKeyExA(HKEY_LOCAL_MACHINE, subkey, 0, KEY_QUERY_VALUE | KEY_WOW64_32KEY, &key);
    entry->driver_error = entry->key_error;
    if (entry->key_error != ERROR_SUCCESS) return;
    entry->driver_error = RegQueryValueExA(key, "Driver", NULL, &entry->type, (BYTE *)entry->path, &bytes);
    RegCloseKey(key);
    if (entry->driver_error != ERROR_SUCCESS) { entry->path[0] = 0; return; }
    if (!bytes || bytes >= sizeof(entry->path) || !memchr(entry->path, 0, bytes)
            || (entry->type != REG_SZ && entry->type != REG_EXPAND_SZ)) {
        entry->driver_error = ERROR_INVALID_DATA;
        entry->path[0] = 0;
        return;
    }
    if (entry->type == REG_EXPAND_SZ) {
        char source[DRIVER_PATH_CAPACITY];
        memcpy(source, entry->path, sizeof(source));
        expanded = ExpandEnvironmentStringsA(source, entry->path, sizeof(entry->path));
        if (!expanded || expanded > sizeof(entry->path)) {
            entry->driver_error = expanded ? ERROR_MORE_DATA : GetLastError();
            entry->path[0] = 0;
            return;
        }
    }
    for (i = 0; entry->path[i]; i++) {
        if ((unsigned char)entry->path[i] < 32) {
            entry->driver_error = ERROR_INVALID_DATA;
            entry->path[0] = 0;
            return;
        }
    }
    if (!absolute_path(entry->path)) entry->driver_error = ERROR_BAD_PATHNAME;
}

static int driver_preflight(void) {
    /* The pinned Unicode driver exports the W entry point; Wine's ANSI manager
       dispatch converts to it when the driver has no ANSI connection export. */
    static const char *required_exports[] = { "SQLDriverConnectW", "SQLAllocHandle", "SQLFreeHandle" };
    struct driver_registration entries[2], *selected = NULL;
    HMODULE driver;
    char loaded[DRIVER_PATH_CAPACITY];
    DWORD count, error;
    unsigned int i;
    if (sizeof(void *) != 4) return driver_failure("pointer_bits", ERROR_BAD_EXE_FORMAT);
    registration(&entries[0], "PostgreSQL Unicode");
    registration(&entries[1], "PostgreSQL Unicode(x86)");
    for (i = 0; i < 2; i++) {
        printf("COH_ODBC_DRIVER_V1 REG name=%s view=32 key_error=%ld driver_error=%ld type=%lu path=%s\n",
               entries[i].name, (long)entries[i].key_error, (long)entries[i].driver_error,
               (unsigned long)entries[i].type, entries[i].path);
        if (!selected && entries[i].key_error == ERROR_SUCCESS && entries[i].driver_error == ERROR_SUCCESS)
            selected = &entries[i];
    }
    fflush(stdout);
    if (!selected) return driver_failure("registry_driver", entries[0].driver_error);
    driver = LoadLibraryExA(selected->path, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!driver) { error = GetLastError(); return driver_failure("load_driver", error); }
    for (i = 0; i < sizeof(required_exports) / sizeof(required_exports[0]); i++) {
        if (!GetProcAddress(driver, required_exports[i])) {
            error = GetLastError();
            fprintf(stderr, "COH_ODBC_DRIVER_V1 EXPORT missing=%s\n", required_exports[i]);
            FreeLibrary(driver);
            return driver_failure("driver_export", error ? error : ERROR_PROC_NOT_FOUND);
        }
    }
    count = GetModuleFileNameA(driver, loaded, sizeof(loaded));
    if (!count || count >= sizeof(loaded)) {
        error = count ? ERROR_MORE_DATA : GetLastError();
        FreeLibrary(driver);
        return driver_failure("loaded_path", error);
    }
    printf("COH_ODBC_DRIVER_V1 NAME %s\n", selected->name);
    printf("COH_ODBC_DRIVER_V1 DLL %s\n", loaded);
    FreeLibrary(driver);
    puts("COH_ODBC_DRIVER_V1 PASS bits=32");
    return 0;
}

int main(int argc, char **argv) {
    HMODULE fixture, odbc;
    probe_fn check;
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    if (argc == 2 && strcmp(argv[1], "--odbc-driver") == 0) return driver_preflight();
    if (argc != 1) { fputs("Usage: runtime-probe.exe [--odbc-driver]\n", stderr); return 2; }
    if (sizeof(void *) != 4) return 2;
    fixture = LoadLibraryA("probe.dll");
    if (!fixture) { fprintf(stderr, "FAIL probe DLL load: %lu\n", GetLastError()); return 3; }
    check = (probe_fn)GetProcAddress(fixture, "coh_probe_value");
    if (!check || check() != 0x434f4832UL) { FreeLibrary(fixture); return 4; }
    odbc = LoadLibraryA("odbc32.dll");
    if (!odbc || !GetProcAddress(odbc, "SQLDriverConnect") ||
        !GetProcAddress(odbc, "SQLExecDirect") || !GetProcAddress(odbc, "SQLColumns") ||
        !GetProcAddress(odbc, "SQLGetInfo") || !GetProcAddress(odbc, "SQLGetDiagRecA")) {
        if (odbc) FreeLibrary(odbc);
        FreeLibrary(fixture);
        return 5;
    }
    FreeLibrary(odbc);
    FreeLibrary(fixture);
    puts("COH_RUNTIME_PROBE_V1 PASS bits=32 dll=verified");
    return 0;
}
