/* Real x86 Windows CryptoAPI fixture, using the exact stock validator body. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <float.h>
#include "coh_animation_certificate.h"
typedef unsigned char U8;
typedef unsigned short U16;
typedef float F32;
typedef struct {
    const void *rot_idx, *pos_idx;
    U16 rot_fullkeycount, pos_fullkeycount, rot_count, pos_count;
    char id, flags;
    unsigned short pack_pad;
} BoneAnimTrack;
#define ROTATION_UNCOMPRESSED 1
#define ROTATION_COMPRESSED_TO_5_BYTES 2
#define ROTATION_COMPRESSED_NONLINEAR 128
#define POSITION_UNCOMPRESSED 8
#define POS_BIGGEST 2000000
static int failures;
int cohAnimationCertificateTestCryptoFailure;
static int finiteVec3(const float *v) { return _finite(v[0]) && _finite(v[1]) && _finite(v[2]); }
static int finiteVec4(const float *v) { return finiteVec3(v) && _finite(v[3]); }
static void FatalErrorFilenamef(const char *file, const char *message, ...) { (void)file; (void)message; ++failures; }
static void FatalErrorf(const char *file, const char *message, ...) { (void)file; (void)message; ++failures; }
#include "coh_animation_stock_validator.inc"

static int fixture(const char *name, const char *path, int pigged, int cryptoFailure, int summarize)
{
    FILE *stream;
    long length;
    unsigned char *body;
    unsigned int i, table, count;
    int bounded, certified = 0;
    unsigned __int64 begin, end;
    stream = fopen(path, "rb");
    if (!stream || fseek(stream, 0, SEEK_END) || (length = ftell(stream)) < 0 || length > 8 * 1024 * 1024)
        return 2;
    rewind(stream);
    body = (unsigned char *)malloc(length ? (size_t)length : 1);
    if (!body || fread(body, 1, (size_t)length, stream) != (size_t)length) return 3;
    fclose(stream);
    failures = 0;
    bounded = cohAnimationRawBounds(body, (unsigned int)length, (unsigned int)length);
    cohAnimationCertificateTestCryptoFailure = cryptoFailure;
    if (bounded) {
        table = cohAnimationDiskU32(body + 524);
        count = cohAnimationDiskU32(body + 528);
        /* Baseline is the actual unchanged stock validator on all opened keys.
         * Build must be Win32: the on-disk pointers and BoneAnimTrack are 20B.
         */
        begin = cohAnimationClockMicroseconds();
        for (i = 0; i < count; ++i) {
            BoneAnimTrack bone;
            memcpy(&bone, body + table + i * 20, sizeof(bone));
            bone.rot_idx = body + cohAnimationDiskU32(body + table + i * 20);
            bone.pos_idx = body + cohAnimationDiskU32(body + table + i * 20 + 4);
            animDebugCheckBoneTrackOnLoad(&bone, name);
        }
        end = cohAnimationClockMicroseconds();
        if (end >= begin) cohAnimationCertificateCounters.stock_microseconds += end - begin;
        certified = cohAnimationCertificateMatch(name, body, (unsigned int)length, pigged);
        cohAnimationCertificateCountKeys(body, certified);
    }
    if (summarize)
        printf("CASE bounded=%d certified=%d stock_errors=%d\n", bounded, certified, failures);
    free(body);
    return 0;
}

int main(int argc, char **argv)
{
    volatile unsigned int pointerSize = (unsigned int)sizeof(void *);
    volatile unsigned int boneSize = (unsigned int)sizeof(BoneAnimTrack);
    if (pointerSize != 4 || boneSize != 20) return 10;
    if (argc == 7 && !strcmp(argv[1], "--case")) {
        int status = fixture(argv[2], argv[3], atoi(argv[4]), atoi(argv[5]), 1);
        cohAnimationCertificatePrint();
        return status;
    }
    if (argc == 2) {
        FILE *list = fopen(argv[1], "rb");
        char line[2048];
        unsigned int count = 0;
        if (!list) return 11;
        while (fgets(line, sizeof(line), list)) {
            char *path = strchr(line, '\t'), *end;
            if (!path) return 12;
            *path++ = 0;
            end = strpbrk(path, "\r\n"); if (end) *end = 0;
            if (fixture(line, path, 1, 0, 0) || failures) return 13;
            ++count;
        }
        fclose(list);
        cohAnimationCertificatePrint();
        printf("ALL tracks=%u actual_stock_validator_errors=0\n", count);
        return count == COH_ANIMATION_CERTIFICATE_COUNT && cohAnimationCertificateCounters.certified == count
            && !cohAnimationCertificateCounters.fallback ? 0 : 14;
    }
    return 15;
}
