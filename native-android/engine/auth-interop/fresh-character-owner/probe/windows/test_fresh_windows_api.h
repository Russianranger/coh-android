/* Host test declarations only: no Windows ABI/header/runtime claim. */
#ifndef COH_TEST_FRESH_WINDOWS_API_H
#define COH_TEST_FRESH_WINDOWS_API_H
#include <stddef.h>
#include <stdint.h>
#include <wchar.h>
typedef void *HANDLE;
typedef uint32_t DWORD;
typedef int BOOL;
typedef struct { DWORD dwLowDateTime,dwHighDateTime; } FILETIME;
typedef struct { int64_t QuadPart; } LARGE_INTEGER;
typedef struct {
    DWORD dwFileAttributes;
    FILETIME ftCreationTime,ftLastAccessTime,ftLastWriteTime;
    DWORD dwVolumeSerialNumber,nFileSizeHigh,nFileSizeLow,nNumberOfLinks,nFileIndexHigh,nFileIndexLow;
} BY_HANDLE_FILE_INFORMATION;
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define GENERIC_READ 0x80000000u
#define FILE_SHARE_READ 1u
#define OPEN_EXISTING 3u
#define FILE_ATTRIBUTE_NORMAL 0x80u
#define FILE_ATTRIBUTE_DIRECTORY 0x10u
#define FILE_ATTRIBUTE_REPARSE_POINT 0x400u
#define FILE_FLAG_OPEN_REPARSE_POINT 0x200000u
#define FILE_TYPE_DISK 1u
#define FILE_BEGIN 0u
#define PROCESS_QUERY_LIMITED_INFORMATION 0x1000u
#define SYNCHRONIZE 0x100000u
#define FALSE 0
#define WAIT_TIMEOUT 258u
#define WAIT_FAILED 0xffffffffu
HANDLE CreateFileA(const char *,DWORD,DWORD,void *,DWORD,DWORD,HANDLE);
HANDLE CreateFileW(const wchar_t *,DWORD,DWORD,void *,DWORD,DWORD,HANDLE);
DWORD GetFileType(HANDLE);
BOOL GetFileInformationByHandle(HANDLE,BY_HANDLE_FILE_INFORMATION *);
BOOL GetFileSizeEx(HANDLE,LARGE_INTEGER *);
BOOL SetFilePointerEx(HANDLE,LARGE_INTEGER,LARGE_INTEGER *,DWORD);
BOOL ReadFile(HANDLE,void *,DWORD,DWORD *,void *);
BOOL CloseHandle(HANDLE);
DWORD GetModuleFileNameW(HANDLE,wchar_t *,DWORD);
HANDLE OpenProcess(DWORD,BOOL,DWORD);
DWORD WaitForSingleObject(HANDLE,DWORD);
DWORD GetProcessId(HANDLE);
BOOL GetProcessTimes(HANDLE,FILETIME *,FILETIME *,FILETIME *,FILETIME *);
BOOL QueryFullProcessImageNameW(HANDLE,DWORD,wchar_t *,DWORD *);
uint64_t GetTickCount64(void);
void Sleep(DWORD);
int coh_win_initialize(void);
int coh_win_limits(unsigned,unsigned,int);
int coh_win_finish(void);
unsigned coh_win_open_handles(void);
typedef struct {
    unsigned initialized,active_handles,sockets_created,sockets_closed;
    unsigned close_failures,cleanup_failures,cleanup_complete;
} CohDbWinDiagnostics;
int coh_db_win_initialize(void);
int coh_db_win_finish(void);
void coh_db_win_diagnostics(CohDbWinDiagnostics *);
/* The backend executes actual EVP file digests over synthetic file bytes.
 * Deterministic entropy here is explicitly a double, never OS entropy proof. */
#define RAND_bytes fresh_test_RAND_bytes
#endif
