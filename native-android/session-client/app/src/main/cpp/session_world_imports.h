#ifndef COH_SESSION_WORLD_IMPORTS_H
#define COH_SESSION_WORLD_IMPORTS_H
#include "session_stream_world.h"
typedef struct CohSessionWorldImports CohSessionWorldImports;
/* index: an uncompressed APK asset span; archives: complete immutable imported
 * ZIP files at offset0. The caller established APK/import manifest identities.
 * File descriptors are borrowed only during open; successful open owns dup FDs.
 * No archive or placement index is copied, mapped or extracted. */
CohStatus coh_session_world_imports_open(const CohSessionWorldFd inputs[3],CohSessionWorldImports **);
CohSessionWorldSources coh_session_world_imports_sources(CohSessionWorldImports *,uint64_t parent_bytes);
uint64_t coh_session_world_imports_owned_bytes(const CohSessionWorldImports *);
uint64_t coh_session_world_imports_allocation_bytes(void);
void coh_session_world_imports_io(const CohSessionWorldImports *,uint64_t *reads,uint64_t *bytes);
void coh_session_world_imports_free(CohSessionWorldImports *);
#endif
