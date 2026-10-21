#ifndef COH_RECEIVED_COSTUME_FD_H
#define COH_RECEIVED_COSTUME_FD_H
#include "coh_received_costume.h"
typedef struct CohReceivedCostumeFds CohReceivedCostumeFds;
typedef struct {int fd;uint64_t offset,bytes;} CohReceivedArchiveFd;
/* Whole immutable archive descriptors already authenticated by AssetPackStore.
 * Duplicates the supplied loaded read-only descriptors; no mapping or full catalog allocation.
 * Sources are borrowed only during off-GL preparation, then all FDs are closed.
 * The original ZIP byte/CRC checks run in coh_asset_zip, not here. */
CohStatus coh_received_costume_fds_open(const CohReceivedArchiveFd *,uint32_t count,
 CohReceivedCostumeFds **);
CohStatus coh_received_costume_fds_sources(CohReceivedCostumeFds *,
 CohAssetSource [COH_RECEIVED_COSTUME_ARCHIVES]);
size_t coh_received_costume_fds_allocation_bytes(void);
void coh_received_costume_fds_destroy(CohReceivedCostumeFds **);
#endif
