#ifndef COH_LOCAL_BODYPART_DEFAULT_H
#define COH_LOCAL_BODYPART_DEFAULT_H
#include "../coh_contracts.h"
/* Exact retained Parse6 cache independently compared to source bodyparts.bp:
 * 28 ordered rows and every source-defined field match. A local server may use
 * this default only after its actual common data/bin/BodyParts.bin matches the
 * complete SHA256 and size, allowing only the exact source-defined four-byte
 * dependency mtime word to differ. No runtime generation/producer lease is required. */
#define COH_LOCAL_BODYPART_CACHE_BYTES 2584u
#define COH_LOCAL_BODYPART_COUNT 28u
#define COH_LOCAL_BODYPART_SHA256 "b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb"
/* Read-only content comparison; only Files1 mtime bytes60..63 may differ. Output unchanged on every refusal. Reads
 * exactly2584B plus one EOF check; no world archive or source build is loaded.
 * The fixed input+digest buffers are below the existing16KiB call reserve. */
CohStatus coh_local_bodypart_default_file(const char *,uint32_t *);
#endif
