#include "capture_hooks.h"
#include <string.h>
static CohWorldCaptureHooks *active;
static int equal_endpoint(CohNetEndpoint a,CohNetEndpoint b){return a.port==b.port&&!memcmp(a.address,b.address,4);}
CohStatus coh_world_capture_hooks_begin(CohWorldCaptureHooks*h){
    if(!h||active||h->capture||h->db_udp||h->map_udp||h->db_creates||h->map_creates||
       h->db.address[0]!=127||h->map.address[0]!=127||!h->db.port||!h->map.port||equal_endpoint(h->db,h->map)||
       (h->version!=0&&h->version!=2&&h->version!=4&&h->version!=5)||
       h->retained_reservation>COH_WORLD_CAPTURE_AGGREGATE_MAX)return COH_INVALID;
    h->capture_status=COH_NOT_FOUND;active=h;return COH_OK;
}
void coh_world_capture_hooks_end(void){active=NULL;}
CohNetUdp *__real_coh_net_udp_create(const CohNetUdpConfig*);
CohNetUdp *__wrap_coh_net_udp_create(const CohNetUdpConfig*c){
    if(!active||!c)return NULL;
    CohWorldCaptureHooks*h=active;
    if(c->local.address[0]!=127||c->link.version!=h->version){h->blocked_endpoints++;return NULL;}
    int db=equal_endpoint(c->peer,h->db),map=equal_endpoint(c->peer,h->map);
    if((!db&&!map)||(db&&h->db_creates)||(map&&(!h->db_creates||h->map_creates))){h->blocked_endpoints++;return NULL;}
    CohNetUdp*u=__real_coh_net_udp_create(c);
    if(u){if(db){h->db_udp=u;h->db_creates++;}else{h->map_udp=u;h->map_creates++;}}return u;
}
CohStatus __real_coh_net_udp_queue(CohNetUdp*,CohBytes,uint32_t,int,int,int,uint64_t);
CohStatus __wrap_coh_net_udp_queue(CohNetUdp*u,CohBytes b,uint32_t bits,int reliable,int ordered,int compressed,uint64_t now){
    if(!active)return COH_STATE;
    CohWorldCaptureHooks*h=active;
    if(u!=h->db_udp&&u!=h->map_udp){h->blocked_commands++;return COH_STATE;}
    if(u==h->map_udp){
        CohRepReader r;uint32_t command=0;CohStatus s=coh_rep_reader(&r,b,bits,0);
        if(s==COH_OK)s=coh_rep_pack(&r,1,&command);
        unsigned offset=h->version<4?5u:0u;
        if(compressed||ordered||reliable!=1||s!=COH_OK||
           (command!=COH_MAP_CONNECT+offset&&command!=COH_MAP_REQSHORTCUTS+offset&&command!=COH_MAP_REQSCENE+offset)){
            h->blocked_commands++;return COH_UNSUPPORTED;
        }
    }
    CohStatus status=__real_coh_net_udp_queue(u,b,bits,reliable,ordered,compressed,now);
    if(status==COH_OK&&u==h->map_udp)h->map_commands++;
    return status;
}
CohStatus __real_coh_net_udp_next_owned(CohNetUdp*,CohNetOwnedMessage*);
CohStatus __wrap_coh_net_udp_next_owned(CohNetUdp*u,CohNetOwnedMessage*out){
    if(!active||u!=active->map_udp)return COH_STATE;
    CohStatus status=__real_coh_net_udp_next_owned(u,out);if(status!=COH_OK)return status;
    CohRepReader r;uint32_t command=0;
    status=coh_rep_reader_bounded(&r,(CohBytes){out->payload,out->payload_bytes},out->payload_bits,out->compressed,COH_NET_DECODED_MAX);
    if(status==COH_OK)status=coh_rep_pack(&r,1,&command);
    if(status==COH_OK&&command==COH_REP_GROUPS+(active->version<4?5u:0u)){
        active->groups_seen++;
        if(active->groups_seen!=1){active->capture_status=COH_STATE;return COH_OK;}
        CohNetUdpDiagnostics d={0};coh_net_udp_diagnostics(u,&d);
        size_t retained=active->retained_reservation;
        if(d.link.storage_bytes>COH_WORLD_CAPTURE_AGGREGATE_MAX-retained){active->capture_status=COH_LIMIT;return COH_OK;}
        retained+=d.link.storage_bytes;
        if(d.link.codec_bytes>COH_WORLD_CAPTURE_AGGREGATE_MAX-retained){active->capture_status=COH_LIMIT;return COH_OK;}
        retained+=d.link.codec_bytes;
        active->capture_status=coh_world_capture_stage(&active->binding,active->version<4,out,retained,COH_WORLD_CAPTURE_AGGREGATE_MAX,&active->capture,&active->capture_failure);
    }
    /* The unchanged MapClient still validates and releases this exact lease. */
    return COH_OK;
}
