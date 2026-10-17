#include "coh_mapclient_owned_private.h"
#include "../dbclient/coh_db_handoff_private.h"
#include <string.h>
static void owned_wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static int stopped(const CohCancel*c){return c&&c->poll&&c->poll(c->context);}
CohStatus coh_map_client_begin_owned(CohMapClient*m,CohDbHandoffOwner*owner,const CohMapOwnedBegin*options,const CohCancel*cancel){
 if(!m||!owner||!options)return COH_INVALID;
 CohStatus status=coh_map_client_owned_preflight(m,options,cancel);if(status!=COH_OK)return status;
 CohDbHandoffMetadata metadata;status=coh_db_handoff_owner_metadata(owner,&metadata);if(status!=COH_OK)return status;
 if(metadata.retired||metadata.claimed||!metadata.selected_dbid_owner_bound||!metadata.selected_dbid||metadata.selected_dbid>INT32_MAX||metadata.session_generation!=options->expected_db_session_generation||metadata.selection_generation!=options->expected_selection_generation)return COH_STATE;
 status=coh_db_handoff_owner_retain(owner);if(status!=COH_OK)return status;
 if(stopped(cancel)){coh_db_handoff_owner_retire(owner);coh_db_handoff_owner_release(owner);return COH_CANCELLED;}
 CohDbSessionHandoff handoff;CohMapAuthorization authorization;memset(&handoff,0,sizeof(handoff));memset(&authorization,0,sizeof(authorization));
 status=coh_db_handoff_owner_claim(owner,options->expected_db_session_generation,options->expected_selection_generation,&handoff);
 if(status==COH_OK){
  authorization.authenticated=!metadata.local_development_auth;authorization.local_development_authorized=(int)metadata.local_development_auth;authorization.endpoint_authorized=(int)options->endpoint_authorized;
  authorization.selected_slot=metadata.selected_slot;authorization.selection_generation=metadata.selection_generation;authorization.selected_dbid=metadata.selected_dbid;authorization.handoff=handoff.map;authorization.address_index=options->address_index;
  if(handoff.selected_dbid!=metadata.selected_dbid||handoff.selected_slot!=metadata.selected_slot||handoff.selection_generation!=metadata.selection_generation)status=COH_STATE;
  else status=coh_map_client_begin(m,&authorization,options->connect_id,options->now_ms);
  owned_wipe(&handoff,sizeof(handoff));owned_wipe(&authorization,sizeof(authorization));
  if(status==COH_OK&&stopped(cancel)){coh_map_client_close(m);status=COH_CANCELLED;}
  if(status==COH_OK)status=coh_map_client_owned_attach(m,owner);
  if(status!=COH_OK){coh_map_client_close(m);coh_db_handoff_owner_retire(owner);}
 }
 owned_wipe(&handoff,sizeof(handoff));owned_wipe(&authorization,sizeof(authorization));
 if(status!=COH_OK)coh_db_handoff_owner_release(owner);
 return status;
}
