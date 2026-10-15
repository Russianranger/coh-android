/* The frozen index stores relative paths. The ordinary legacy scanner supplies
 * absolute paths, so accept those only under the exact verified private root.
 * No suffix matching, alternate roots or parent traversal is permitted. */
#ifndef COH_TEXTURE_HEADER_ROOT_H
#define COH_TEXTURE_HEADER_ROOT_H
#include "coh_texture_header_index.h"

static int cohThiCanonicalPath(char output[260], const char *input)
{
    size_t length, i, first = 0;
    if (!input) return 0;
    length = strlen(input);
    if (!length || length >= 260) return 0;
    for (i = 0; i <= length; ++i) {
        unsigned char value = (unsigned char)input[i];
        if (value && (value < 32 || value > 126)) return 0;
        output[i] = value == '\\' ? '/' :
            ((value >= 'A' && value <= 'Z') ? value + 32 : value);
    }
    /* The scanner never produces dot components. Refuse them instead of
     * resolving them into a different generation or source search root. */
    for (i = 0; i <= length; ++i) {
        if (output[i] == '/' || !output[i]) {
            size_t component = i - first;
            if ((component == 1 && output[first] == '.') ||
                (component == 2 && output[first] == '.' && output[first + 1] == '.')) return 0;
            if (!component && i && i != length) return 0;
            first = i + 1;
        }
    }
    return 1;
}

static const CohTextureHeaderEntry *cohThiFindVerifiedRoot(
    const CohTextureHeaderIndex *index, const char *path, const char *root)
{
    char search[260], prefix[260];
    size_t length;
    if (!cohThiCanonicalPath(search, path)) return NULL;
    /* Preserve the frozen relative lookup and its exact matching semantics. */
    if (!strncmp(search, "texture_library/", 16)) return cohThiFind(index, search);
    if (!cohThiCanonicalPath(prefix, root)) return NULL;
    length = strlen(prefix);
    while (length > 3 && prefix[length - 1] == '/') prefix[--length] = 0;
    /* The guest supplies a drive-qualified Windows path, never UNC or a
     * relative data directory. Require the same syntax independently here. */
    if (length < 4 || prefix[0] < 'a' || prefix[0] > 'z' ||
        prefix[1] != ':' || prefix[2] != '/' || strchr(prefix + 2, ':')) return NULL;
    if (strncmp(search, prefix, length) || search[length] != '/') return NULL;
    return cohThiFind(index, search + length + 1);
}
#endif
