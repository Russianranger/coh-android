/* COHCNS1 is a bounded canonical projection of observed Win32 metadata.
 * Decoding grants NO provider, source, timestamp or cache authority. The caller
 * must authenticate the complete immutable blob and provider generation before
 * native construction. This module never invokes callbacks or mutates a cache.
 *
 * Header64: magic8, version32, totalBytes32, dirCount32, rowCount32,
 * recordOffset32, flags32=0, opaqueProviderToken32.
 * Directory: pathBytes16, reserved16=0, firstRow32, count32, ordinal32,
 * exact ASCII relative path followed by zero bytes to a four-byte boundary.
 * Row328: directoryOrdinal32, arrivalOrdinal32, canonical WFD projection320.
 * WFD: attributes32; creation/access/write FILETIME64; sizeHigh/Low32;
 * reserved0/1 MUST zero; longName260; shortName14; trailingPadding2 MUST zero.
 * Bytes after each string's terminator MUST zero. Reserved/padding bytes are
 * nonauthoritative because the pinned Wine APIs leave them uninitialized.
 * Access time is an observation, not a current-consumed-field parity claim.
 */
#ifndef COH_FOLDER_CENSUS_H
#define COH_FOLDER_CENSUS_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define COH_CENSUS_HEADER_BYTES 64u
#define COH_CENSUS_WFD_BYTES 320u
#define COH_CENSUS_ROW_BYTES 328u
#define COH_CENSUS_MAX_BYTES (64u * 1024u * 1024u)
#define COH_CENSUS_MAX_DIRS 16384u
#define COH_CENSUS_MAX_ROWS 200000u
#define COH_CENSUS_MAX_PATH 259u
#define COH_CENSUS_DIRECTORY_ATTRIBUTE 16u
#define COH_CENSUS_SEEN 0x80000000u
#define COH_CENSUS_OFFSET_MASK 0x7fffffffu

typedef enum CohCensusResult {
    COH_CENSUS_OK = 1,
    COH_CENSUS_BAD_HEADER = -1,
    COH_CENSUS_BOUNDS = -2,
    COH_CENSUS_BAD_DIRECTORY = -3,
    COH_CENSUS_BAD_RECORD = -4,
    COH_CENSUS_AMBIGUOUS = -5,
    COH_CENSUS_MEMBERSHIP = -6,
    COH_CENSUS_SCRATCH = -7
} CohCensusResult;

typedef struct CohFolderCensusView {
    const unsigned char *data;
    size_t bytes;
    const unsigned char *provider_token; /* Opaque; this decoder cannot verify it. */
    uint32_t directory_count, row_count, record_offset;
    const uint32_t *directory_offsets; /* Borrowed caller storage; immutable after decode. */
    int valid;
} CohFolderCensusView;

static uint16_t cohCensusU16(const unsigned char *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t cohCensusU32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
        ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static unsigned char cohCensusFold(unsigned char value)
{
    return value >= 'A' && value <= 'Z' ? (unsigned char)(value + ('a' - 'A')) : value;
}

static int cohCensusCompare(const unsigned char *a, size_t an,
                            const unsigned char *b, size_t bn)
{
    size_t i, n = an < bn ? an : bn;
    for (i = 0; i < n; ++i) {
        unsigned char av = cohCensusFold(a[i]), bv = cohCensusFold(b[i]);
        if (av != bv) return av < bv ? -1 : 1;
    }
    return an < bn ? -1 : an > bn;
}

static int cohCensusOverlap(const void *a, size_t an, const void *b, size_t bn)
{
    uintptr_t av = (uintptr_t)a, bv = (uintptr_t)b;
    if (an > UINTPTR_MAX - av || bn > UINTPTR_MAX - bv) return 1;
    return av < bv + bn && bv < av + an;
}

static int cohCensusComponent(const unsigned char *name, size_t length)
{
    size_t i;
    if (!length || length > COH_CENSUS_MAX_PATH) return 0;
    for (i = 0; i < length; ++i) {
        unsigned char value = name[i];
        if (value < 32u || value > 126u || value == '/' || value == '\\' ||
            value == ':' || value == '*' || value == '?' || value == '"' ||
            value == '<' || value == '>' || value == '|') return 0;
    }
    return 1;
}

static int cohCensusPath(const unsigned char *path, size_t length)
{
    size_t i, first = 0;
    if (length > COH_CENSUS_MAX_PATH) return 0;
    if (!length) return 1; /* A census may represent an exact data root. */
    for (i = 0; i <= length; ++i) {
        if (i == length || path[i] == '/') {
            size_t component = i - first;
            if (!cohCensusComponent(path + first, component) ||
                (component == 1u && path[first] == '.') ||
                (component == 2u && path[first] == '.' && path[first + 1u] == '.')) return 0;
            first = i + 1u;
        }
    }
    return 1;
}

static int cohCensusProjectionString(const unsigned char *p, size_t capacity,
                                     int require_name, size_t *length)
{
    size_t i, end = capacity;
    for (i = 0; i < capacity; ++i) if (!p[i]) { end = i; break; }
    if (end == capacity || (require_name && !end)) return 0;
    if (end && !cohCensusComponent(p, end)) return 0;
    for (i = end; i < capacity; ++i) if (p[i]) return 0;
    *length = end;
    return 1;
}

/* Internal functions operate only on a bounded partially validated view. */
static const unsigned char *cohCensusDirectory(const CohFolderCensusView *view,
                                              uint32_t ordinal)
{
    uint32_t offset;
    if (!view || !view->data || !view->directory_offsets || ordinal >= view->directory_count) return NULL;
    offset = view->directory_offsets[ordinal] & COH_CENSUS_OFFSET_MASK;
    if (offset < COH_CENSUS_HEADER_BYTES || offset > view->record_offset ||
        view->record_offset - offset < 16u || view->record_offset > view->bytes) return NULL;
    return view->data + offset;
}

static int cohCensusFind(const CohFolderCensusView *view,
                         const unsigned char *path, size_t length, uint32_t *ordinal)
{
    uint32_t first = 0, last = view->directory_count;
    while (first < last) {
        uint32_t mid = first + (last - first) / 2u;
        const unsigned char *entry = cohCensusDirectory(view, mid);
        size_t n;
        int order;
        if (!entry) return 0;
        n = cohCensusU16(entry);
        if (n > COH_CENSUS_MAX_PATH || (size_t)(entry - view->data) + 16u + n > view->record_offset) return 0;
        order = cohCensusCompare(entry + 16u, n, path, length);
        if (!order) { *ordinal = mid; return 1; }
        if (order < 0) first = mid + 1u;
        else last = mid;
    }
    return 0;
}

/* The entire file and directory graph are checked before *output becomes valid.
 * Scratch contains at most 64KiB of directory offsets. No heap allocation,
 * filesystem access, native callback or FolderCache mutation occurs here.
 * Input and scratch must be disjoint and remain private/immutable for view use.
 */
static CohCensusResult cohCensusDecode(CohFolderCensusView *output,
                                      const unsigned char *data, size_t bytes,
                                      uint32_t *scratch, size_t scratch_count)
{
    CohFolderCensusView view;
    uint32_t i, first_row = 0;
    size_t offset = COH_CENSUS_HEADER_BYTES;
    const unsigned char *previous = NULL;
    size_t previous_length = 0;
    if (!output) return COH_CENSUS_BAD_HEADER;
    /* Alias misuse must not zero the caller's immutable input/index. A view
     * cannot be cleared without changing those bytes when storage overlaps. */
    if ((data && cohCensusOverlap(output, sizeof(*output), data, bytes)) ||
        (scratch && cohCensusOverlap(output, sizeof(*output), scratch,
            (scratch_count < COH_CENSUS_MAX_DIRS ? scratch_count : COH_CENSUS_MAX_DIRS) * sizeof(*scratch))))
        return COH_CENSUS_SCRATCH;
    memset(output, 0, sizeof(*output));
    memset(&view, 0, sizeof(view));
    if (!data || bytes < COH_CENSUS_HEADER_BYTES || bytes > COH_CENSUS_MAX_BYTES ||
        memcmp(data, "COHCNS1\0", 8u) || cohCensusU32(data + 8u) != 1u ||
        cohCensusU32(data + 12u) != bytes || cohCensusU32(data + 28u) != 0u) return COH_CENSUS_BAD_HEADER;
    view.data = data; view.bytes = bytes; view.provider_token = data + 32u;
    view.directory_count = cohCensusU32(data + 16u);
    view.row_count = cohCensusU32(data + 20u);
    view.record_offset = cohCensusU32(data + 24u);
    view.directory_offsets = scratch;
    if (!view.directory_count || view.directory_count > COH_CENSUS_MAX_DIRS ||
        view.row_count > COH_CENSUS_MAX_ROWS || view.record_offset < COH_CENSUS_HEADER_BYTES ||
        view.record_offset > bytes || (view.record_offset & 3u) ||
        (size_t)view.row_count * COH_CENSUS_ROW_BYTES != bytes - view.record_offset) return COH_CENSUS_BOUNDS;
    if (!scratch || scratch_count < view.directory_count ||
        cohCensusOverlap(data, bytes, scratch, (size_t)view.directory_count * sizeof(*scratch))) return COH_CENSUS_SCRATCH;
    for (i = 0; i < view.directory_count; ++i) {
        const unsigned char *entry;
        uint32_t rows;
        size_t path_length, next, j;
        if (offset > view.record_offset || view.record_offset - offset < 16u) return COH_CENSUS_BAD_DIRECTORY;
        entry = data + offset;
        path_length = cohCensusU16(entry);
        if (path_length > COH_CENSUS_MAX_PATH || cohCensusU16(entry + 2u) ||
            cohCensusU32(entry + 12u) != i || cohCensusU32(entry + 4u) != first_row ||
            path_length > view.record_offset - offset - 16u ||
            !cohCensusPath(entry + 16u, path_length)) return COH_CENSUS_BAD_DIRECTORY;
        rows = cohCensusU32(entry + 8u);
        if (rows > view.row_count - first_row) return COH_CENSUS_BAD_DIRECTORY;
        first_row += rows;
        next = (offset + 16u + path_length + 3u) & ~(size_t)3u;
        if (next > view.record_offset) return COH_CENSUS_BAD_DIRECTORY;
        for (j = offset + 16u + path_length; j < next; ++j) if (data[j]) return COH_CENSUS_BAD_DIRECTORY;
        if (previous && cohCensusCompare(previous, previous_length, entry + 16u, path_length) >= 0)
            return COH_CENSUS_AMBIGUOUS;
        scratch[i] = (uint32_t)offset;
        previous = entry + 16u; previous_length = path_length;
        offset = next;
    }
    if (offset != view.record_offset || first_row != view.row_count) return COH_CENSUS_BAD_DIRECTORY;
    for (i = 0; i < view.directory_count; ++i) {
        const unsigned char *entry = cohCensusDirectory(&view, i);
        const unsigned char *directory_path = entry + 16u;
        size_t directory_length = cohCensusU16(entry);
        uint32_t count = cohCensusU32(entry + 8u), first = cohCensusU32(entry + 4u), row;
        for (row = 0; row < count; ++row) {
            const unsigned char *record = data + view.record_offset + (size_t)(first + row) * COH_CENSUS_ROW_BYTES;
            const unsigned char *wfd = record + 8u;
            size_t name_length = 0, short_length = 0;
            unsigned char child[COH_CENSUS_MAX_PATH + 1u];
            size_t child_length;
            uint32_t child_ordinal;
            if (cohCensusU32(record) != i || cohCensusU32(record + 4u) != row ||
                cohCensusU32(wfd + 36u) || cohCensusU32(wfd + 40u) || wfd[318u] || wfd[319u] ||
                !cohCensusProjectionString(wfd + 44u, 260u, 1, &name_length) ||
                !cohCensusProjectionString(wfd + 304u, 14u, 0, &short_length)) return COH_CENSUS_BAD_RECORD;
            (void)short_length;
            /* Only traversal aliases are graph-special. Named hidden files and
             * directories retain full membership, even when the later stock
             * constructor ignores their leading-dot names. */
            if ((name_length == 1u && wfd[44u] == '.') ||
                (name_length == 2u && wfd[44u] == '.' && wfd[45u] == '.')) continue;
            child_length = directory_length + (directory_length ? 1u : 0u) + name_length;
            if (child_length > COH_CENSUS_MAX_PATH) return COH_CENSUS_BOUNDS;
            if (directory_length) memcpy(child, directory_path, directory_length);
            if (directory_length) child[directory_length] = '/';
            memcpy(child + directory_length + (directory_length ? 1u : 0u), wfd + 44u, name_length);
            if (cohCensusFind(&view, child, child_length, &child_ordinal)) {
                if (!(cohCensusU32(wfd) & COH_CENSUS_DIRECTORY_ATTRIBUTE)) return COH_CENSUS_AMBIGUOUS;
                if (scratch[child_ordinal] & COH_CENSUS_SEEN) return COH_CENSUS_AMBIGUOUS;
                scratch[child_ordinal] |= COH_CENSUS_SEEN;
            } else if (cohCensusU32(wfd) & COH_CENSUS_DIRECTORY_ATTRIBUTE) return COH_CENSUS_MEMBERSHIP;
        }
    }
    /* The first path names one exact subtree. Every other directory must be
     * reached exactly once from a native directory entry, including empty dirs.
     * A second independent root, orphan, cycle or dot-only edge fails closed. */
    if (scratch[0] & COH_CENSUS_SEEN) return COH_CENSUS_MEMBERSHIP;
    for (i = 1; i < view.directory_count; ++i)
        if (!(scratch[i] & COH_CENSUS_SEEN)) return COH_CENSUS_MEMBERSHIP;
    for (i = 0; i < view.directory_count; ++i) scratch[i] &= COH_CENSUS_OFFSET_MASK;
    view.valid = 1;
    *output = view;
    return COH_CENSUS_OK;
}

static int cohCensusFindDirectory(const CohFolderCensusView *view,
                                  const char *relative_path, uint32_t *ordinal)
{
    size_t length;
    if (!view || !view->valid || !relative_path || !ordinal) return 0;
    for (length = 0; length <= COH_CENSUS_MAX_PATH && relative_path[length]; ++length) { }
    if (length > COH_CENSUS_MAX_PATH) return 0;
    if (!cohCensusPath((const unsigned char *)relative_path, length)) return 0;
    return cohCensusFind(view, (const unsigned char *)relative_path, length, ordinal);
}

static const unsigned char *cohCensusProjection(const CohFolderCensusView *view,
                                              uint32_t directory, uint32_t arrival)
{
    const unsigned char *entry;
    uint32_t first, count;
    size_t offset;
    if (!view || !view->valid || !(entry = cohCensusDirectory(view, directory))) return NULL;
    first = cohCensusU32(entry + 4u); count = cohCensusU32(entry + 8u);
    if (first > view->row_count || count > view->row_count - first || arrival >= count) return NULL;
    offset = view->record_offset + (size_t)(first + arrival) * COH_CENSUS_ROW_BYTES;
    if (offset > view->bytes || view->bytes - offset < COH_CENSUS_ROW_BYTES) return NULL;
    return view->data + offset + 8u;
}

static int cohCensusDirectoryCount(const CohFolderCensusView *view,
                                  uint32_t directory, uint32_t *count)
{
    const unsigned char *entry;
    if (!view || !view->valid || !count || !(entry = cohCensusDirectory(view, directory))) return 0;
    *count = cohCensusU32(entry + 8u);
    return 1;
}

static void cohCensusClear(CohFolderCensusView *view)
{
    if (view) memset(view, 0, sizeof(*view));
}
#endif
