#ifndef COH_RECEIVED_COSTUME_FD_H
#define COH_RECEIVED_COSTUME_FD_H
#include "../assets/coh_asset_loader.h"
typedef struct CohReceivedCostumeFds CohReceivedCostumeFds;
typedef struct {int fd;uint64_t offset,bytes;} CohReceivedArchiveFd;
/* Whole immutable archive descriptors already authenticated by AssetPackStore.
 * Duplicates two read-only descriptors; no mapping or full catalog allocation.
 * Sources are borrowed only during off-GL preparation, then all FDs are closed.
 * The original ZIP byte/CRC checks run in coh_asset_zip, not here. */
CohStatus coh_received_costume_fds_open(const CohReceivedArchiveFd [2],
 CohReceivedCostumeFds **);
CohStatus coh_received_costume_fds_sources(CohReceivedCostumeFds *,
 CohAssetSource [2]);
size_t coh_received_costume_fds_allocation_bytes(void);
void coh_received_costume_fds_destroy(CohReceivedCostumeFds **);
#endif
