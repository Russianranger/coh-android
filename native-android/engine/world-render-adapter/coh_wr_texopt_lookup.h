#ifndef COH_WR_TEXOPT_LOOKUP_H
#define COH_WR_TEXOPT_LOOKUP_H
#include "coh_wr_texopt.h"
typedef struct{
 uint8_t cache_sha256[32];uint32_t historical_input_generation,matched,source_ordinal,direct,attempts,name_flags,unresolved_client_semantics;
 char matched_key[260];
}CohWrTexOptLookup;
/* Source-exact historical lookup only. Requires full, nonempty ASCII texture
 * path with directory separator, <260 bytes (original name-flags stack buffer).
 * Original source bodies are unchanged; unsupported unsafe original domains
 * refuse before execution. Backslashes are accepted as original forwardSlashes
 * inputs. Matching creates an independently retained postprocessed record.
 * A completed miss returns OK, matched=0 and record=NULL, with original derived
 * name flags. Missing direct key is not evidence of missing inherited trick.
 * external_bytes must additionally cover all live cache/Surface/old records as
 * described by coh_wr_texopt. An extra16KiB lookup stack/control reservation is
 * charged before any callback/allocation. Caller supplies disjoint writable
 * outputs outside borrowed loader blobs; all failures leave both unchanged.
 * Not an active Basic/composite namespace, asset or material generation proof. */
CohStatus coh_wr_texopt_lookup(const CohWrTexOptCache*,const CohWrSurfaceStates*,const char*,const CohWrTexOptLimits*,CohCancel,CohWrTexOptLookup*,CohWrTexOptRecord**);
#endif
