#ifndef COH_LOCAL_BODYPART_DEFAULT_H
#define COH_LOCAL_BODYPART_DEFAULT_H
#include "../coh_contracts.h"
/* The retained CLIENT Parse6 cache decodes with original ParseBodyPart tables:
 * 28 ordered rows and every text-defined field match source bodyparts.bp.
 * This CLIENT count is authoritative for the stage41/43 costume consumer.
 * Optional server-file comparison is consistency evidence only; missing or
 * different server bytes never withhold this client default. No runtime
 * generation/producer lease is required. */
#define COH_LOCAL_BODYPART_CACHE_BYTES 2584u
#define COH_LOCAL_BODYPART_COUNT 28u
#define COH_LOCAL_BODYPART_SHA256 "b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb"
/* Read-only content comparison; only Files1 mtime bytes60..63 may differ. Output unchanged on every refusal. Reads
 * exactly2584B plus one EOF check; no world archive or source build is loaded.
 * The fixed input+digest buffers are below the existing16KiB call reserve. */
CohStatus coh_local_bodypart_default_file(const char *,uint32_t *);
#endif
