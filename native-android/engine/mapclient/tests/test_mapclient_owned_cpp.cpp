#include "coh_mapclient_owned_private.h"
int main(){
 if(coh_map_client_begin_owned(nullptr,nullptr,nullptr,nullptr)!=COH_INVALID)return 1;
 if(coh_map_client_owned_attach(nullptr,nullptr)!=COH_INVALID)return 2;
 if(coh_map_client_owned_preflight(nullptr,nullptr,nullptr)!=COH_INVALID)return 3;
 CohMapConfig config{};config.udp.link=coh_net_default_config();
 config.udp.peer.address[0]=127;config.udp.peer.address[3]=1;config.udp.peer.port=7002;
 config.udp.local.address[0]=127;config.udp.local.address[3]=1;config.udp.receive_budget=1;
 config.application_timeout_ms=1000;config.message_budget=1;
 CohMapClient*client=coh_map_client_create(&config);if(!client)return 4;
 CohDbHandoffMetadata metadata{};CohMapOwnedBegin options{1,1,1,0,0,1};
 if(coh_map_client_handoff_metadata(client,&metadata)!=COH_NOT_FOUND)return 5;
 if(coh_map_client_begin_owned(client,nullptr,&options,nullptr)!=COH_INVALID)return 6;
 coh_map_client_destroy(client);return 0;
}
