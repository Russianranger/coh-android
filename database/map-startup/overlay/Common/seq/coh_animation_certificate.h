/* SERVER-only raw-byte certificate selection. Never included by Game. */
#ifndef COH_ANIMATION_CERTIFICATE_H
#define COH_ANIMATION_CERTIFICATE_H
#include <windows.h>
#include <wincrypt.h>
#include <string.h>
#include <float.h>
#include "coh_animation_certificate_table.h"
#pragma comment(lib, "advapi32.lib")

typedef struct CohAnimationCertificateCounters {
    unsigned int opened, certified, fallback, crypto_failed;
    unsigned __int64 raw_bytes, hash_microseconds, stock_microseconds;
    unsigned __int64 skipped_rotation_keys, skipped_position_keys, scanned_rotation_keys, scanned_position_keys;
} CohAnimationCertificateCounters;
static CohAnimationCertificateCounters cohAnimationCertificateCounters;

static unsigned int cohAnimationDiskU32(const unsigned char *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8) | ((unsigned int)p[2] << 16) | ((unsigned int)p[3] << 24);
}
static unsigned int cohAnimationDiskU16(const unsigned char *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8);
}
static int cohAnimationDiskFinite(const unsigned char *p, int nonnegative)
{
    float value;
    memcpy(&value, p, sizeof(value));
    return _finite((double)value) && (!nonnegative || value >= 0.0f);
}

/* All offsets checked before any native pointer arithmetic or key access.
 * loaded can be only headerSize for LOAD_SKELETONS_ONLY; total is actual file
 * length. These bounds remain mandatory for both certified and stock paths.
 */
static int cohAnimationRawBounds(const unsigned char *raw, unsigned int loaded, unsigned int total)
{
    unsigned int header, table, count, hierarchy, i, capacity = 0;
    unsigned char seen[100] = {0}, bones[100] = {0};
    int stack[201], depth = 0;
    if (!raw || loaded < 596 || total < loaded || total > 8u * 1024u * 1024u)
        return 0;
    header = cohAnimationDiskU32(raw);
    table = cohAnimationDiskU32(raw + 524);
    count = cohAnimationDiskU32(raw + 528);
    hierarchy = cohAnimationDiskU32(raw + 540);
    if (!memchr(raw + 4, 0, 256) || !memchr(raw + 260, 0, 256)
        || !cohAnimationDiskFinite(raw + 516, 0) || !cohAnimationDiskFinite(raw + 520, 1)
        || header < 596 || header > loaded || count < 1 || count > 99
        || table < 596 || table > header || count * 20 != header - table)
        return 0;
    if (hierarchy) {
        if (hierarchy != 596 || table < hierarchy + 16 || (table - hierarchy - 4) % 12)
            return 0;
        capacity = (table - hierarchy - 4) / 12;
        if (capacity > 100)
            return 0;
        stack[depth++] = (int)cohAnimationDiskU32(raw + hierarchy);
        if (stack[0] == -1)
            return 0;
        while (depth) {
            int bone = stack[--depth];
            const unsigned char *link;
            if (bone == -1)
                continue;
            if (bone < 0 || (unsigned int)bone >= capacity || bone >= 99 || seen[bone] || depth > 198)
                return 0;
            seen[bone] = 1;
            link = raw + hierarchy + 4 + 12 * bone;
            if ((int)cohAnimationDiskU32(link + 8) != bone)
                return 0;
            stack[depth++] = (int)cohAnimationDiskU32(link);
            stack[depth++] = (int)cohAnimationDiskU32(link + 4);
        }
    } else if (table != 596)
        return 0;
    for (i = 0; i < count; ++i) {
        const unsigned char *bone = raw + table + i * 20;
        unsigned int ro = cohAnimationDiskU32(bone), po = cohAnimationDiskU32(bone + 4);
        unsigned int rf = cohAnimationDiskU16(bone + 8), pf = cohAnimationDiskU16(bone + 10);
        unsigned int rc = cohAnimationDiskU16(bone + 12), pc = cohAnimationDiskU16(bone + 14);
        unsigned int id = bone[16], flags = bone[17], rotation, position;
        if (id >= 99 || bones[id] || (hierarchy && !seen[id]) || !rf || !pf || !rc || !pc
            || rc > rf || pc > pf || (flags & 0x60))
            return 0;
        bones[id] = 1;
        switch (flags & 0x87) {
            case 1: rotation = 16; break;
            case 2: case 128: rotation = 5; break;
            case 4: rotation = 8; break;
            default: return 0;
        }
        switch (flags & 0x18) {
            case 8: position = 12; break;
            case 16: position = 6; break;
            default: return 0;
        }
        if (ro < header || ro > total || rf * rotation > total - ro
            || po < header || po > total || pf * position > total - po)
            return 0;
    }
    return 1;
}

static int cohAnimationNormalizeName(const char *name, char output[256])
{
    unsigned int i;
    if (!name)
        return 0;
    for (i = 0; i < 255 && name[i]; ++i) {
        unsigned char c = (unsigned char)name[i];
        if (c == '\\') c = '/';
        if (c >= 'A' && c <= 'Z') c = (unsigned char)(c + ('a' - 'A'));
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '&' || c == '-' || c == '/' || c == '.'))
            return 0;
        output[i] = (char)c;
    }
    if (i >= 255 || i < 32 || name[i]) return 0;
    output[i] = 0;
    return !strncmp(output, "player_library/animations/", 26) && !strcmp(output + i - 5, ".anim");
}

static int cohAnimationSha256(const unsigned char *raw, unsigned int bytes, unsigned char digest[32])
{
    static PVOID volatile provider = NULL;
    HCRYPTPROV acquired = 0, active;
    PVOID previous;
    HCRYPTHASH hash = 0;
    DWORD size = 32;
    int success = 0;
#ifdef COH_ANIMATION_CERTIFICATE_TEST
    extern int cohAnimationCertificateTestCryptoFailure;
    if (cohAnimationCertificateTestCryptoFailure)
        return 0;
#endif
    /* No trust is established when CryptoAPI is unavailable. */
    active = (HCRYPTPROV)InterlockedCompareExchangePointer(&provider, NULL, NULL);
    if (!active) {
        if (!CryptAcquireContextA(&acquired, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT))
            return 0;
        previous = InterlockedCompareExchangePointer(&provider, (PVOID)acquired, NULL);
        if (previous) { CryptReleaseContext(acquired, 0); active = (HCRYPTPROV)previous; }
        else active = acquired;
    }
    /* One process-owned provider; each raw read gets an independent hash. */
    if (CryptCreateHash(active, CALG_SHA_256, 0, 0, &hash)
        && CryptHashData(hash, raw, bytes, 0)
        && CryptGetHashParam(hash, HP_HASHVAL, digest, &size, 0) && size == 32)
        success = 1;
    if (hash) CryptDestroyHash(hash);
    return success;
}

static unsigned __int64 cohAnimationClockMicroseconds(void)
{
    LARGE_INTEGER counter, frequency;
    if (!QueryPerformanceFrequency(&frequency) || frequency.QuadPart <= 0 || !QueryPerformanceCounter(&counter))
        return 0;
    return (unsigned __int64)((double)counter.QuadPart * 1000000.0 / (double)frequency.QuadPart);
}

static int cohAnimationCertificateMatch(const char *name, const unsigned char *raw, unsigned int bytes, int pigged)
{
    char normalized[256] = {0};
    unsigned char digest[32];
    unsigned int low = 0, high = COH_ANIMATION_CERTIFICATE_COUNT;
    unsigned __int64 start, end;
    CohAnimationCertificateCounters *stats = &cohAnimationCertificateCounters;
    ++stats->opened;
    if (!pigged || !cohAnimationNormalizeName(name, normalized)) {
        ++stats->fallback;
        return 0;
    }
    while (low < high) {
        unsigned int middle = low + (high - low) / 2;
        const CohAnimationCertificateEntry *entry = &cohAnimationCertificateEntries[middle];
        int order = strcmp(normalized, entry->name);
        if (order < 0) high = middle;
        else if (order > 0) low = middle + 1;
        else {
            if (bytes != entry->bytes) break;
            start = cohAnimationClockMicroseconds();
            if (!cohAnimationSha256(raw, bytes, digest)) {
                ++stats->crypto_failed;
                ++stats->fallback;
                return 0;
            }
            end = cohAnimationClockMicroseconds();
            if (end >= start) stats->hash_microseconds += end - start;
            stats->raw_bytes += bytes;
            if (memcmp(digest, entry->sha256, sizeof(digest))) break;
            ++stats->certified;
            return 1;
        }
    }
    ++stats->fallback;
    return 0;
}

static void cohAnimationCertificateCountKeys(const unsigned char *raw, int certified)
{
    unsigned int table = cohAnimationDiskU32(raw + 524), count = cohAnimationDiskU32(raw + 528), i;
    CohAnimationCertificateCounters *stats = &cohAnimationCertificateCounters;
    for (i = 0; i < count; ++i) {
        const unsigned char *bone = raw + table + 20 * i;
        unsigned int flags = bone[17];
        unsigned int rot = flags & (1 | 2 | 128) ? cohAnimationDiskU16(bone + 8) : 0;
        unsigned int pos = flags & 8 ? cohAnimationDiskU16(bone + 10) : 0;
        if (certified) { stats->skipped_rotation_keys += rot; stats->skipped_position_keys += pos; }
        else { stats->scanned_rotation_keys += rot; stats->scanned_position_keys += pos; }
    }
}

static void cohAnimationCertificatePrint(void)
{
    const CohAnimationCertificateCounters *s = &cohAnimationCertificateCounters;
    printf("COH_ANIM_CERT_V1 schema=1 pack=%s opened=%u certified=%u fallback=%u crypto_failed=%u raw_bytes=%I64u hash_us=%I64u stock_us=%I64u skipped_rot_keys=%I64u skipped_pos_keys=%I64u scanned_rot_keys=%I64u scanned_pos_keys=%I64u\n",
        COH_ANIMATION_CERTIFICATE_PACK_SHA256, s->opened, s->certified, s->fallback, s->crypto_failed,
        s->raw_bytes, s->hash_microseconds, s->stock_microseconds,
        s->skipped_rotation_keys, s->skipped_position_keys, s->scanned_rotation_keys, s->scanned_position_keys);
#ifdef COH_ANIMATION_CERTIFICATE_TEST
    fflush(stdout);
#else
    fflush(fileGetStdout());
#endif
}
#endif
