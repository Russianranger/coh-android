/* POSIX stand-ins for the few Win32 file calls the header makes. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#define MAX_PATH 260
typedef unsigned long DWORD_; typedef unsigned int DWORD; typedef void *HANDLE; typedef void *LPVOID;
#define INVALID_HANDLE_VALUE ((HANDLE)(long)-1)
#define INVALID_FILE_SIZE 0xffffffffu
#define GENERIC_READ 1
#define GENERIC_WRITE 2
#define FILE_SHARE_READ 1
#define OPEN_EXISTING 3
#define CREATE_ALWAYS 2
#define FILE_ATTRIBUTE_NORMAL 0
#define MOVEFILE_REPLACE_EXISTING 1
static int shim_fail_write, shim_fail_move;
static HANDLE CreateFileA(const char *path, int access, int share, void *sa, int mode, int flags, void *t)
{ int fd; (void)share; (void)sa; (void)flags; (void)t;
  fd = open(path, access == GENERIC_READ ? O_RDONLY : (O_WRONLY | O_CREAT | O_TRUNC), 0600); (void)mode;
  return fd < 0 ? INVALID_HANDLE_VALUE : (HANDLE)(long)(fd + 1); }
static DWORD GetFileSize(HANDLE h, void *high) { struct stat s; (void)high; return fstat((int)(long)h - 1, &s) ? INVALID_FILE_SIZE : (DWORD)s.st_size; }
static int ReadFile(HANDLE h, void *data, DWORD n, DWORD *got, void *o) { ssize_t r = read((int)(long)h - 1, data, n); (void)o; *got = r < 0 ? 0 : (DWORD)r; return r >= 0; }
static int WriteFile(HANDLE h, const void *data, DWORD n, DWORD *put, void *o) { ssize_t r; (void)o; if (shim_fail_write) { *put = 0; return 0; } r = write((int)(long)h - 1, data, n); *put = r < 0 ? 0 : (DWORD)r; return r >= 0; }
static int CloseHandle(HANDLE h) { return !close((int)(long)h - 1); }
static int MoveFileExA(const char *a, const char *b, int flags) { (void)flags; return shim_fail_move ? 0 : !rename(a, b); }
static int DeleteFileA(const char *a) { return !unlink(a); }
