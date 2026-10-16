#ifndef COH_NET_ZIP_INTERNAL_H
#define COH_NET_ZIP_INTERNAL_H
#include "coh_net.h"
/* Internal one-allocation decoder. Command remains source byte-aligned32.
 * Neither output pointer nor byte count changes on failure. Receipt is numeric
 * and is completed/normalized by the link, never includes packet bodies. */
CohStatus coh_net_zip_decode_owned(CohNetZip *, int streaming, CohBytes input,
    size_t budget, uint8_t **output, size_t *bytes, CohNetDecodeReceipt *);
#endif
