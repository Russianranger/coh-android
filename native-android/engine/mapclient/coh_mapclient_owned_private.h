#ifndef COH_MAPCLIENT_OWNED_PRIVATE_H
#define COH_MAPCLIENT_OWNED_PRIVATE_H
#include "coh_mapclient_owned.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Trusted typed bridge only. No caller metadata/callback admission. Attach
 * rechecks the ACTUAL owner and exact just-begun client fields. Success transfers
 * the bridge's already-retained reference; refusal leaves that reference owned
 * by the bridge. Never call with an arbitrary/fabricated opaque pointer. */
CohStatus coh_map_client_owned_attach(CohMapClient *,CohDbHandoffOwner *);
CohStatus coh_map_client_owned_preflight(const CohMapClient *,const CohMapOwnedBegin *,const CohCancel *);
#ifdef __cplusplus
}
#endif
#endif
