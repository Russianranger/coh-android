#include "wine_dispatch_progress.h"
#include <stddef.h>
#include <string.h>

/* This observer is built into the existing x86 Wine DbServer only. x86 orders
 * aligned stores; compiler barriers prevent moving payload stores outside the
 * seqlock. No interlocked operation, clock, flush, or OS call is in the loop. */
#if defined(_MSC_VER) && defined(_M_IX86)
#include <intrin.h>
#pragma intrinsic(_ReadWriteBarrier)
#define COH_PROGRESS_BARRIER() _ReadWriteBarrier()
#elif defined(__GNUC__) && defined(__i386__)
#define COH_PROGRESS_BARRIER() __asm__ __volatile__("" ::: "memory")
#else
#error The dispatch progress record requires the qualified x86 build
#endif

typedef char coh_progress_size_check[
    sizeof(CohDbProgressRecord) == COH_DB_PROGRESS_RECORD_BYTES ? 1 : -1];
typedef char coh_progress_sequence_check[
    offsetof(CohDbProgressRecord, sequence) == 24 ? 1 : -1];
typedef char coh_progress_reserved_check[
    offsetof(CohDbProgressRecord, reserved) == 44 ? 1 : -1];

static HANDLE progress_file = INVALID_HANDLE_VALUE;
static HANDLE progress_mapping;
static CohDbProgressRecord *progress_record;
static int progress_initialized;

void cohDbProgressClose(void)
{
    CohDbProgressRecord *record = progress_record;
    progress_record = NULL;
    if (record)
        UnmapViewOfFile(record);
    if (progress_mapping)
        CloseHandle(progress_mapping);
    if (progress_file != INVALID_HANDLE_VALUE)
        CloseHandle(progress_file);
    progress_mapping = NULL;
    progress_file = INVALID_HANDLE_VALUE;
}

int cohDbProgressInit(void)
{
    char path[32768];
    DWORD length, error;
    CohDbProgressRecord *record;

    if (progress_initialized) {
        SetLastError(ERROR_ALREADY_EXISTS);
        return -1;
    }
    progress_initialized = 1;
    SetLastError(ERROR_SUCCESS);
    length = GetEnvironmentVariableA(COH_DB_PROGRESS_ENVIRONMENT, path, sizeof(path));
    if (!length && GetLastError() == ERROR_ENVVAR_NOT_FOUND)
        return 0;
    /* Reject relative, drive-relative, UNC, and device paths. The launcher owns
     * the private parent directory; CREATE_NEW never replaces prior evidence. */
    if (length < 3 || length >= sizeof(path) ||
        !((path[0] >= 'A' && path[0] <= 'Z') || (path[0] >= 'a' && path[0] <= 'z')) ||
        path[1] != ':' || (path[2] != '\\' && path[2] != '/')) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return -1;
    }
    progress_file = CreateFileA(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ,
                                NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
    if (progress_file == INVALID_HANDLE_VALUE)
        return -1;
    progress_mapping = CreateFileMappingA(progress_file, NULL, PAGE_READWRITE, 0,
                                          COH_DB_PROGRESS_MAPPING_BYTES, NULL);
    if (!progress_mapping)
        goto failed;
    record = (CohDbProgressRecord *)MapViewOfFile(progress_mapping, FILE_MAP_WRITE,
                                                0, 0, COH_DB_PROGRESS_MAPPING_BYTES);
    if (!record)
        goto failed;
    memset(record, 0, COH_DB_PROGRESS_MAPPING_BYTES);
    memcpy(record->magic, "COHDBP1", 8);
    record->format = COH_DB_PROGRESS_FORMAT;
    record->record_bytes = COH_DB_PROGRESS_RECORD_BYTES;
    record->process_id = GetCurrentProcessId();
    record->main_thread_id = GetCurrentThreadId();
    record->stage_count = COH_DB_STAGE_READY;
    progress_record = record;
    cohDbProgressMark(COH_DB_STAGE_INITIALIZED);
    return 1;

failed:
    error = GetLastError();
    cohDbProgressClose();
    SetLastError(error);
    return -1;
}

void cohDbProgressMark(CohDbProgressStage stage)
{
    CohDbProgressRecord *record = progress_record;
    DWORD sequence;
    if (!record)
        return;
    sequence = record->sequence;
    if (sequence >= 0xfffffffeUL || record->flags) {
        /* Saturate instead of wrapping: readers reject flagged samples. */
        record->flags = COH_DB_PROGRESS_FLAG_SATURATED;
        return;
    }
    record->sequence = sequence + 1;
    COH_PROGRESS_BARRIER();
    record->stage = (DWORD)stage;
    if (stage == COH_DB_STAGE_MAIN_LOOP)
        record->loop_count++;
    COH_PROGRESS_BARRIER();
    record->sequence = sequence + 2;
}
