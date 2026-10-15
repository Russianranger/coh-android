/* Header-only, little-endian decoder. No graphics or game state dependencies.
 * The guest validates SHA256 and private asset-generation ownership before use;
 * this decoder independently checks the format, identity, CRC and every bound.
 * Entries contain the exact original TextureFileHeader + name + cached mip.
 */
#ifndef COH_TEXTURE_HEADER_INDEX_H
#define COH_TEXTURE_HEADER_INDEX_H
#include <stdlib.h>
#include <string.h>
#include <stddef.h>

#define COH_THI_FORMAT 1
#define COH_THI_MAX_BYTES (64u * 1024u * 1024u)
#define COH_THI_MAX_RECORDS 65536u
#define COH_THI_TEXTURE_STRUCT_BYTES 32u
#define COH_THI_MAX_HEADER_BYTES 1056u
typedef struct CohTextureHeaderEntry {
    char *path;
    const unsigned char *header;
    unsigned int bytes;
} CohTextureHeaderEntry;
typedef struct CohTextureHeaderIndex {
    CohTextureHeaderEntry *entries;
    unsigned int count;
} CohTextureHeaderIndex;

static unsigned int cohThiU32(const unsigned char *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8) |
        ((unsigned int)p[2] << 16) | ((unsigned int)p[3] << 24);
}
static unsigned int cohThiU16(const unsigned char *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8);
}
static unsigned int cohThiCrc(const unsigned char *p, size_t bytes)
{
    unsigned int crc = ~0u;
    unsigned int table[256];
    size_t i;
    unsigned int n, bit;
    for (n = 0; n < 256; ++n) {
        unsigned int value = n;
        for (bit = 0; bit < 8; ++bit)
            value = (value >> 1) ^ (0xedb88320u & (0u - (value & 1u)));
        table[n] = value;
    }
    for (i = 0; i < bytes; ++i) {
        crc = (crc >> 8) ^ table[(crc ^ p[i]) & 255u];
    }
    return ~crc;
}
static void cohThiFree(CohTextureHeaderIndex *index)
{
    unsigned int i;
    if (index->entries) {
        for (i = 0; i < index->count; ++i) free(index->entries[i].path);
        free(index->entries);
    }
    memset(index, 0, sizeof(*index));
}
static int cohThiHex(unsigned char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}
static int cohThiParse(CohTextureHeaderIndex *index, const unsigned char *data,
    size_t bytes, const char *identity)
{
    size_t position = 64;
    unsigned int count, i;
    memset(index, 0, sizeof(*index));
    if (!identity || strlen(identity) != 64 || bytes < 64 || bytes > COH_THI_MAX_BYTES ||
        memcmp(data, "COHTHI1\0", 8) || cohThiU32(data + 8) != COH_THI_FORMAT ||
        cohThiU32(data + 12) != COH_THI_TEXTURE_STRUCT_BYTES ||
        cohThiU32(data + 20) != bytes - 64 || cohThiU32(data + 28) != 0 ||
        cohThiU32(data + 24) != cohThiCrc(data + 64, bytes - 64)) return 0;
    for (i = 0; i < 32; ++i) {
        int high = cohThiHex((unsigned char)identity[i * 2]);
        int low = cohThiHex((unsigned char)identity[i * 2 + 1]);
        if (high < 0 || low < 0 || data[32 + i] != ((high << 4) | low)) return 0;
    }
    count = cohThiU32(data + 16);
    if (!count || count > COH_THI_MAX_RECORDS || count > (bytes - 64) / 38) return 0;
    index->entries = (CohTextureHeaderEntry *)calloc(count, sizeof(*index->entries));
    if (!index->entries) return 0;
    index->count = count;
    for (i = 0; i < count; ++i) {
        unsigned int path_bytes, header_bytes, j;
        CohTextureHeaderEntry *entry = index->entries + i;
        if (bytes - position < 4) goto invalid;
        path_bytes = cohThiU16(data + position);
        header_bytes = cohThiU16(data + position + 2);
        position += 4;
        if (path_bytes < 25 || path_bytes >= 260 || header_bytes <= 32 ||
            header_bytes > COH_THI_MAX_HEADER_BYTES ||
            path_bytes + header_bytes > bytes - position) goto invalid;
        entry->path = (char *)malloc(path_bytes + 1);
        if (!entry->path) goto invalid;
        memcpy(entry->path, data + position, path_bytes);
        entry->path[path_bytes] = 0;
        for (j = 0; j < path_bytes; ++j) {
            unsigned char c = (unsigned char)entry->path[j];
            if (c < 32 || c > 126 || c == ':' || c == '\\' ||
                (c >= 'A' && c <= 'Z')) goto invalid;
        }
        if (strncmp(entry->path, "texture_library/", 16) ||
            strcmp(entry->path + path_bytes - 8, ".texture") ||
            strstr(entry->path, "//") || strstr(entry->path, "/../") ||
            strstr(entry->path, "/./") ||
            (i && strcmp(index->entries[i - 1].path, entry->path) >= 0)) goto invalid;
        position += path_bytes;
        entry->header = data + position;
        entry->bytes = header_bytes;
        if (cohThiU32(entry->header) != header_bytes ||
            !cohThiU32(entry->header + 8) || cohThiU32(entry->header + 8) > 16384 ||
            !cohThiU32(entry->header + 12) || cohThiU32(entry->header + 12) > 16384 ||
            !memchr(entry->header + 32, 0, header_bytes - 32)) goto invalid;
        position += header_bytes;
    }
    if (position != bytes) goto invalid;
    return 1;
invalid:
    cohThiFree(index);
    return 0;
}
static const CohTextureHeaderEntry *cohThiFind(const CohTextureHeaderIndex *index,
    const char *path)
{
    char search[260];
    unsigned int i, first = 0, last = index->count;
    size_t length = strlen(path);
    if (length >= sizeof(search)) return NULL;
    for (i = 0; i <= length; ++i) {
        unsigned char c = (unsigned char)path[i];
        search[i] = (c == '\\') ? '/' : ((c >= 'A' && c <= 'Z') ? c + 32 : c);
    }
    while (first < last) {
        unsigned int middle = first + (last - first) / 2;
        int result = strcmp(search, index->entries[middle].path);
        if (result == 0) return index->entries + middle;
        if (result < 0) last = middle;
        else first = middle + 1;
    }
    return NULL;
}
#endif
