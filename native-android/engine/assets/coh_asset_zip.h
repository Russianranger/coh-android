#ifndef COH_ASSET_ZIP_H
#define COH_ASSET_ZIP_H
#include "coh_asset_loader.h"
typedef struct CohAssetZip CohAssetZip;
typedef struct {const char *path;uint32_t bytes;} CohAssetZipMember;
typedef struct {size_t owned_bytes;uint64_t reads,read_bytes,decoded_bytes;uint32_t members;} CohAssetZipStats;
/* The existing importer verifies the entire immutable archive against the APK
 * manifest. This filtered reader retains only requested original paths, never
 * the complete ZIP directory or extracted world. Source/owner outlive loader.
 * ZIP32 stored/deflate only; exact sizes, local identity and CRC are checked.
 * Single owner thread, no callbacks reenter this reader. */
CohStatus coh_asset_zip_open(CohAssetSource,const CohAssetZipMember *,uint32_t,CohCancel,CohAssetZip **);
CohStatus coh_asset_zip_mount(CohAssetZip *,CohAssetLoader *);
void coh_asset_zip_free(CohAssetZip *); /* destroy the borrowing loader first */
CohAssetZipStats coh_asset_zip_stats(const CohAssetZip *);
/* Exact nonallocating factory charge, including read buffers and zlib arena. */
size_t coh_asset_zip_allocation_bytes(uint32_t members);
#endif
