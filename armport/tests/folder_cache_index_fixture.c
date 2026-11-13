/* Native fixture for ArmPort patch 0122 (saved folder-cache index), driven by
 * armport/tests/folder_cache_index.py. The real FolderNodeAdd, FolderCacheAddFolderToNode,
 * FolderCacheAddFolder and index helpers are extracted from the prepared tree into
 * extracted.inc; Win32 file and find calls are POSIX stand-ins. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <assert.h>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>
#include <time.h>

typedef uint32_t U32; typedef int32_t S32; typedef int32_t __time32_t;
typedef uint32_t DWORD; typedef int BOOL; typedef void *HANDLE;
#define TRUE 1
#define FALSE 0
#define MAX_PATH 260
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define INVALID_FILE_SIZE 0xffffffffu
#define GENERIC_READ 1
#define GENERIC_WRITE 2
#define FILE_SHARE_READ 1
#define CREATE_ALWAYS 2
#define OPEN_EXISTING 3
#define FILE_ATTRIBUTE_NORMAL 0x80
#define FILE_ATTRIBUTE_DIRECTORY 0x10
#define FILE_ATTRIBUTE_READONLY 1
#define FILE_ATTRIBUTE_HIDDEN 2
#define FILE_ATTRIBUTE_SYSTEM 4
#define MOVEFILE_REPLACE_EXISTING 1
#define MOVEFILE_WRITE_THROUGH 8
#define GetFileExInfoStandard 0
#define stricmp strcasecmp
#define xcase break; case
#define xdefault break; default
#define SAFESTR(x) x, sizeof(x)
#define sprintf_s snprintf
#define STR_COMBINE_SS(b, x, y) snprintf(b, sizeof(b), "%s%s", x, y)
#define STR_COMBINE_SSS(b, x, y, z) snprintf(b, sizeof(b), "%s%s%s", x, y, z)
#define verbose_printf(...) ((void)0)
typedef struct { int64_t t; } FILETIME;
typedef struct { DWORD dwFileAttributes; FILETIME ftLastWriteTime; DWORD nFileSizeLow; char cFileName[MAX_PATH]; } WIN32_FIND_DATAA;
typedef struct { DWORD dwFileAttributes; FILETIME ftLastWriteTime; DWORD nFileSizeLow; } WIN32_FILE_ATTRIBUTE_DATA;
static void _FileTimeToUnixTime(FILETIME *ft, __time32_t *out, int local) { (void)local; *out = (__time32_t)ft->t; }

typedef struct FolderNode FolderNode; typedef struct FolderCache FolderCache;
struct FolderNode {
    FolderNode *next, *prev;
    S32 virtual_location:16; U32 is_dir:1, writeable:1, hidden:1, system:1, seen_in_fs:1, in_hash_table:1, delete_if_absent:1;
    int file_index; FolderNode *contents, *contents_tail, *parent; char *name; size_t size; __time32_t timestamp;
};
struct FolderCache { FolderNode *root, *root_tail; void (*nodeCreateCallback)(FolderCache *, FolderNode *); };
typedef enum { FOLDER_CACHE_ALL_FOLDERS, FOLDER_CACHE_EXCLUDE_FOLDER, FOLDER_CACHE_ONLY_FOLDER } FolderCacheExclusion;
enum { FOLDER_CACHE_MODE_I_LIKE_PIGS, FOLDER_CACHE_MODE_PIGS_ONLY, FOLDER_CACHE_MODE_FILESYSTEM_ONLY, FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC };
#define DIR_MON_NO_TIMESTAMPS 1
static FolderCacheExclusion folder_cache_exclusion = FOLDER_CACHE_ALL_FOLDERS;
static const char *folder_cache_exclusion_folder = NULL;
static int folder_cache_debug = 0, update_count = 0, discard_count = 0, count_file = 0, count_folder = 0;
static bool ban_all_overrides = false; static const char *banned_overrides[] = {"/nothing"}; static int banned_overrides_len[1];
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
static int fileIsUsingDevData(void) { return 0; }
static char *firstSlash(char *s) { char *a = strchr(s, '/'), *b = strchr(s, '\\'); return !a ? b : (!b ? a : (a < b ? a : b)); }
static const char *allocAddString(const char *s) { return strdup(s); }
static FolderNode *FolderNodeCreate(void) { return calloc(1, sizeof(FolderNode)); }
static char *vl_paths[8];
static int FolderCache_GetFromVirtualLocation(FolderCache *fc, int vl) { (void)fc; return vl_paths[vl] != NULL; }
static void FolderCache_SetFromVirtualLocation(FolderCache *fc, int vl, char *p) { (void)fc; vl_paths[vl] = p; }
static int FolderCacheGetMode(void) { return FOLDER_CACHE_MODE_I_LIKE_PIGS; }
static void dirMonSetFlags(int f) { (void)f; }
static int dirMonAddDirectory(const char *p, int r, void *c) { (void)p; (void)r; free(c); return 1; }
static void FolderCacheBuildHashTable(FolderCache *fc, FolderNode *n, const char *p) { (void)fc; (void)n; (void)p; }
static void FolderNodeGetCounts(int *a, int *b) { *a = discard_count; *b = update_count; }
static int timerAlloc(void) { return 0; } static void timerStart(int t) { (void)t; } static void timerFree(int t) { (void)t; }
static float timerElapsed(int t) { (void)t; return 0.0f; }
/* Win32 file API over POSIX. */
static HANDLE CreateFileA(const char *p, DWORD access, DWORD share, void *s, DWORD disp, DWORD attr, void *t) {
    (void)share; (void)s; (void)attr; (void)t; (void)disp;
    FILE *f = fopen(p, access == GENERIC_WRITE ? "wb" : "rb"); return f ? (HANDLE)f : INVALID_HANDLE_VALUE; }
static BOOL ReadFile(HANDLE h, void *b, DWORD n, DWORD *got, void *o) { (void)o; *got = (DWORD)fread(b, 1, n, (FILE *)h); return 1; }
static BOOL WriteFile(HANDLE h, const void *b, DWORD n, DWORD *put, void *o) { (void)o; *put = (DWORD)fwrite(b, 1, n, (FILE *)h); return 1; }
static BOOL FlushFileBuffers(HANDLE h) { return fflush((FILE *)h) == 0; }
static BOOL CloseHandle(HANDLE h) { return fclose((FILE *)h) == 0; }
static DWORD GetFileSize(HANDLE h, void *hi) { (void)hi; struct stat s; return fstat(fileno((FILE *)h), &s) ? INVALID_FILE_SIZE : (DWORD)s.st_size; }
static BOOL MoveFileExA(const char *a, const char *b, DWORD f) { (void)f; return rename(a, b) == 0; }
static BOOL DeleteFileA(const char *a) { return unlink(a) == 0; }
static void fill(const char *path, const char *name, WIN32_FIND_DATAA *w) {
    struct stat s; stat(path, &s); memset(w, 0, sizeof(*w)); snprintf(w->cFileName, MAX_PATH, "%s", name);
    w->dwFileAttributes = S_ISDIR(s.st_mode) ? FILE_ATTRIBUTE_DIRECTORY : ((s.st_mode & 0200) ? 0 : FILE_ATTRIBUTE_READONLY);
    w->nFileSizeLow = S_ISDIR(s.st_mode) ? 0 : (DWORD)s.st_size; w->ftLastWriteTime.t = s.st_mtime; }
static BOOL GetFileAttributesExA(const char *p, int level, WIN32_FILE_ATTRIBUTE_DATA *d) {
    (void)level; struct stat s; if (stat(p, &s)) return 0; WIN32_FIND_DATAA w; fill(p, "x", &w);
    d->dwFileAttributes = w.dwFileAttributes; d->ftLastWriteTime = w.ftLastWriteTime; d->nFileSizeLow = w.nFileSizeLow; return 1; }
static int scans = 0;  /* directory listings, i.e. the cost being saved */
typedef struct { DIR *dir; char base[1024]; } Find; static Find finds[64];
static int nextEntry(Find *f, WIN32_FIND_DATAA *w) {
    struct dirent *e; char full[2048];
    while ((e = readdir(f->dir))) { snprintf(full, sizeof(full), "%s/%s", f->base, e->d_name); fill(full, e->d_name, w); return 1; }
    return 0; }
static int fwFindFirstFile(U32 *h, const char *spec, WIN32_FIND_DATAA *w) {
    int i; for (i = 0; finds[i].dir; i++); Find *f = &finds[i];
    snprintf(f->base, sizeof(f->base), "%s", spec); f->base[strlen(f->base) - 2] = 0;
    if (!(f->dir = opendir(f->base))) return 0; scans++; *h = (U32)i; return nextEntry(f, w); }
static int fwFindNextFile(U32 h, WIN32_FIND_DATAA *w) { return nextEntry(&finds[h], w); }
static int fwFindClose(U32 h) { closedir(finds[h].dir); finds[h].dir = NULL; return 1; }
typedef struct DirectoryUpdateContext { FolderCache *fc; int virtual_location; } DirectoryUpdateContext;

#include "extracted.inc"

static void dump(FILE *out, FolderNode *n, const char *prefix) {
    char path[2048];
    for (; n; n = n->next) {
        snprintf(path, sizeof(path), "%s/%s", prefix, n->name);
        fprintf(out, "%s %d %u %d %d%d%d\n", path, n->is_dir, (unsigned)n->size, (int)n->timestamp, n->writeable, n->hidden, n->system);
        if (n->is_dir) dump(out, n->contents, path);
    }
}
int main(int argc, char **argv) {
    FolderCache fc = {0};
    assert(argc == 2);
    FolderCacheAddFolder(&fc, "./data", 0);
    FILE *out = fopen(argv[1], "w"); dump(out, fc.root, ""); fclose(out);
    printf("RESULT files=%d folders=%d skipped=%d listings=%d\n", count_file, count_folder, armport_skipped_folders, scans);
    return 0;
}
