/* Nonshipping, opt-in constructor acceleration. This header never enumerates,
 * hashes, opens, drops or substitutes an asset. The ordinary constructor owns
 * the one existing enumeration and every metadata/provider decision. */
#ifndef COH_FOLDER_METADATA_SORT_H
#define COH_FOLDER_METADATA_SORT_H
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#ifndef COH_FOLDER_METADATA_LIMIT
#define COH_FOLDER_METADATA_LIMIT 16384u
#endif
#ifndef COH_FOLDER_METADATA_REALLOC
#define COH_FOLDER_METADATA_REALLOC realloc
#endif
#ifndef COH_FOLDER_METADATA_FREE
#define COH_FOLDER_METADATA_FREE free
#endif
#ifndef COH_FOLDER_METADATA_ENV
#define COH_FOLDER_METADATA_ENV getenv
#endif

typedef struct CohFolderMetadataRow {
    WIN32_FIND_DATAA data;
    unsigned int ordinal;
} CohFolderMetadataRow;

typedef struct CohFolderMetadataBatch {
    CohFolderMetadataRow *rows;
    unsigned int count, capacity, arrival_inversions;
    const char *fallback;
} CohFolderMetadataBatch;

static int cohFolderMetadataEnabled(void)
{
    const char *value = COH_FOLDER_METADATA_ENV("COH_CLIENT_FOLDER_METADATA_SORT");
    return value && !strcmp(value, "1");
}

static int cohFolderMetadataAppend(CohFolderMetadataBatch *batch,
                                   const WIN32_FIND_DATAA *data)
{
    if (batch->count == COH_FOLDER_METADATA_LIMIT) {
        batch->fallback = "entry_limit";
        return 0;
    }
    if (batch->count == batch->capacity) {
        unsigned int capacity = batch->capacity ? batch->capacity * 2u : 128u;
        CohFolderMetadataRow *rows;
        if (capacity > COH_FOLDER_METADATA_LIMIT) capacity = COH_FOLDER_METADATA_LIMIT;
        rows = (CohFolderMetadataRow *)COH_FOLDER_METADATA_REALLOC(
            batch->rows, (size_t)capacity * sizeof(*rows));
        if (!rows) {
            batch->fallback = "allocation_failure";
            return 0;
        }
        batch->rows = rows;
        batch->capacity = capacity;
    }
    if (batch->count && stricmp(batch->rows[batch->count - 1u].data.cFileName,
                               data->cFileName) > 0)
        ++batch->arrival_inversions;
    batch->rows[batch->count].data = *data;
    batch->rows[batch->count].ordinal = batch->count;
    ++batch->count;
    return 1;
}

static int cohFolderMetadataNameCompare(const void *left, const void *right)
{
    const CohFolderMetadataRow *a = (const CohFolderMetadataRow *)left;
    const CohFolderMetadataRow *b = (const CohFolderMetadataRow *)right;
    int order = stricmp(a->data.cFileName, b->data.cFileName);
    if (order) return order;
    return a->ordinal < b->ordinal ? -1 : a->ordinal > b->ordinal;
}

static int cohFolderMetadataOrdinalCompare(const void *left, const void *right)
{
    const CohFolderMetadataRow *a = (const CohFolderMetadataRow *)left;
    const CohFolderMetadataRow *b = (const CohFolderMetadataRow *)right;
    return a->ordinal < b->ordinal ? -1 : a->ordinal > b->ordinal;
}

static int cohFolderMetadataSort(CohFolderMetadataBatch *batch)
{
    unsigned int i;
    if (batch->count < 2u) return 1;
    qsort(batch->rows, batch->count, sizeof(*batch->rows), cohFolderMetadataNameCompare);
    for (i = 1; i < batch->count; ++i) {
        if (!stricmp(batch->rows[i - 1u].data.cFileName,
                     batch->rows[i].data.cFileName)) {
            /* Windows providers normally disallow case aliases. An untrusted
             * provider may contain them, so restore the exact native arrival
             * order and let the ordinary constructor resolve them. */
            qsort(batch->rows, batch->count, sizeof(*batch->rows),
                  cohFolderMetadataOrdinalCompare);
            batch->fallback = "case_alias";
            return 0;
        }
    }
    return 1;
}

static void cohFolderMetadataReport(const CohFolderMetadataBatch *batch,
                                    const char *reason)
{
    static unsigned int rows = 0;
    if ((batch->count >= 128u || strcmp(reason, "sorted")) && rows < 256u) {
        ++rows;
        printf("COH_CLIENT_FOLDER_METADATA_SORT_V1 entries=%u capacity_bytes=%lu "
               "reason=%s arrival_inversions=%u callback_absent=1 limit=%u bounded_rows=256\n",
               batch->count, (unsigned long)((size_t)batch->capacity * sizeof(*batch->rows)),
               reason, batch->arrival_inversions, (unsigned int)COH_FOLDER_METADATA_LIMIT);
    }
}

static void cohFolderMetadataFree(CohFolderMetadataBatch *batch)
{
    if (batch->rows) COH_FOLDER_METADATA_FREE(batch->rows);
    batch->rows = NULL;
    batch->count = batch->capacity = 0;
}
#endif
