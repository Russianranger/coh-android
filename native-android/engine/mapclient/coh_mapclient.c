#include "coh_mapclient.h"
#include <stdlib.h>
#include <string.h>

static void wipe(void *p,size_t n) {volatile uint8_t *b=p;while(n--)*b++=0;}
void coh_map_packet_wipe(CohMapPacket *p) {if(p)wipe(p,sizeof(*p));}
static int scalar(CohProtocolBits *b,CohMapProfile p,unsigned width,uint32_t v) {
    return coh_protocol_write(b,p.byte_aligned?(width+7u)&~7u:width,v);
}
static int packed(CohProtocolBits *b,CohMapProfile p,uint32_t v) {
    return p.byte_aligned?coh_protocol_write(b,32,v):coh_protocol_write_pack(b,1,v);
}
CohStatus coh_map_serialize(unsigned cmd,CohMapProfile p,const CohMapFields *f,CohMapPacket *out) {
    if(!out||p.legacy_commands>1||p.byte_aligned>1)return COH_INVALID;
    if(cmd!=COH_MAP_CONNECT&&cmd!=COH_MAP_REQSHORTCUTS&&cmd!=COH_MAP_REQSCENE&&
       cmd!=COH_MAP_REQALLENTS&&cmd!=COH_MAP_READY)return COH_UNSUPPORTED;
    if((cmd==COH_MAP_CONNECT||cmd==COH_MAP_READY)&&(!f||f->cookie<2))return COH_INVALID;
    if(cmd==COH_MAP_CONNECT&&f->cod>1)return COH_INVALID;
    if(cmd==COH_MAP_READY&&(!f->password_md5||f->console_open>1||f->initial_login>1))return COH_INVALID;
    CohMapPacket packet;memset(&packet,0,sizeof(packet));CohProtocolBits b;
    if(coh_protocol_bits_init(&b,packet.data,sizeof(packet.data),0,1))return COH_INVALID;
    if(packed(&b,p,cmd+(p.legacy_commands?5u:0u)))return COH_LIMIT;
    if(cmd==COH_MAP_CONNECT) {
        if(packed(&b,p,f->cookie)||scalar(&b,p,1,f->cod)||scalar(&b,p,1,0))return COH_LIMIT;
    } else if(cmd==COH_MAP_REQSCENE) {
        if(scalar(&b,p,1,0))return COH_LIMIT; /* source stealth bit */
    } else if(cmd==COH_MAP_READY) {
        if(packed(&b,p,f->cookie)||packed(&b,p,f->console_open))return COH_LIMIT;
        /* pktSendBitsArray(128) aligns to a byte before raw bytes. */
        while(b.cursor&7u)if(coh_protocol_write(&b,1,0))return COH_LIMIT;
        for(unsigned i=0;i<16;i++)if(coh_protocol_write(&b,8,f->password_md5[i]))return COH_LIMIT;
        /* pktSendBitsAuto: the value 0/1 uses bin0 and a two-bit scalar. */
        if(scalar(&b,p,2,0)||scalar(&b,p,2,f->initial_login))return COH_LIMIT;
    }
    packet.bits=(uint32_t)b.bit_length;*out=packet;wipe(&packet,sizeof(packet));return COH_OK;
}

struct CohMapClient {
    CohMapConfig config;CohNetUdp *udp;CohMapDiagnostics diag;
    CohRepSession inspector;CohRepSchema schema;
    uint32_t cookie,last_connect_id;uint64_t last_ms,phase_ms;
    unsigned authorized;
};
CohStatus coh_map_config_validate(const CohMapConfig *c) {
    if(!c||!c->application_timeout_ms||!c->message_budget||c->message_budget>16||c->cod>1)return COH_INVALID;
    return coh_net_udp_config_validate(&c->udp);
}
CohMapClient *coh_map_client_create(const CohMapConfig *c) {
    if(coh_map_config_validate(c)!=COH_OK)return NULL;
    CohMapClient *m=calloc(1,sizeof(*m));if(!m)return NULL;
    m->config=*c;coh_rep_session_init(&m->inspector);return m;
}
static void clear_authorization(CohMapClient *m) {
    m->cookie=0;m->authorized=0;coh_rep_session_disconnect(&m->inspector);
    memset(&m->schema,0,sizeof(m->schema));m->diag.selected_dbid=0;
    m->diag.selected_slot=0;m->diag.selection_generation=0;m->diag.character_identity_verified=0;
    m->diag.map_id=0;m->diag.map_link_id=0;m->diag.local_development_authorized=0;
}
void coh_map_client_close(CohMapClient *m) {
    if(!m)return;
    if(m->udp)coh_net_udp_close(m->udp);
    clear_authorization(m);m->diag.phase=COH_MAP_CLOSED;
}
void coh_map_client_destroy(CohMapClient *m) {
    if(m){coh_net_udp_destroy(m->udp);wipe(m,sizeof(*m));free(m);}
}
static CohStatus authorization(const CohMapClient *m,const CohMapAuthorization *a) {
    if(!a||(a->authenticated!=0&&a->authenticated!=1)||(a->endpoint_authorized!=0&&a->endpoint_authorized!=1)||
       (a->local_development_authorized!=0&&a->local_development_authorized!=1))return COH_INVALID;
    if(a->authenticated&&a->local_development_authorized)return COH_INVALID;
    if((!a->authenticated&&!a->local_development_authorized)||!a->endpoint_authorized)return COH_STATE;
    if(!a->selection_generation||a->selected_slot>=64||a->handoff.cookie<2||a->address_index>1)return COH_INVALID;
    uint32_t ip=a->handoff.address[a->address_index];
    if(a->local_development_authorized&&(m->config.udp.peer.address[0]!=127||(ip&255u)!=127||a->selected_dbid))return COH_INVALID;
    for(unsigned i=0;i<4;i++)if(m->config.udp.peer.address[i]!=(uint8_t)(ip>>(8*i)))return COH_INVALID;
    if(m->config.udp.peer.port!=a->handoff.udp_port)return COH_INVALID;
    return COH_OK;
}
CohStatus coh_map_client_begin(CohMapClient *m,const CohMapAuthorization *a,uint32_t id,uint64_t now) {
    if(!m)return COH_INVALID;
    if(m->diag.phase!=COH_MAP_IDLE&&m->diag.phase!=COH_MAP_CLOSED&&m->diag.phase!=COH_MAP_SUSPENDED&&
       m->diag.phase!=COH_MAP_TIMED_OUT&&m->diag.phase!=COH_MAP_FAILED)return COH_STATE;
    CohStatus s=authorization(m,a);if(s!=COH_OK)return s;
    if(!id||id==m->last_connect_id||now<m->last_ms)return COH_INVALID;
    if(m->diag.generation==UINT32_MAX)return COH_LIMIT;
    CohNetUdp *udp=coh_net_udp_create(&m->config.udp);if(!udp)return COH_LIMIT;
    s=coh_net_udp_begin(udp,id,now);if(s!=COH_OK){coh_net_udp_destroy(udp);return s;}
    coh_net_udp_destroy(m->udp);m->udp=udp;
    clear_authorization(m);
    /* The DB character list does NOT contain a DBID. Never seed the inspector
     * with the slot, link_id, cookie or a dummy DBID. Its standalone decoders
     * are used until authentic identity is supplied by a complete decoder. */
    if(a->selected_dbid) {
        s=coh_rep_session_begin(&m->inspector,a->selected_dbid);
        if(s!=COH_OK){coh_map_client_close(m);return s;}
    }
    m->diag.selected_slot=a->selected_slot;m->diag.selection_generation=a->selection_generation;
    m->diag.local_development_authorized=(unsigned)a->local_development_authorized;
    m->diag.selected_dbid=a->selected_dbid;m->diag.map_id=a->handoff.map_id;m->diag.map_link_id=a->handoff.link_id;
    m->cookie=a->handoff.cookie;m->authorized=1;m->last_connect_id=id;
    m->diag.generation++;m->diag.phase=COH_MAP_NET_CONNECTING;m->phase_ms=m->last_ms=now;return COH_OK;
}
static CohStatus send_command(CohMapClient *m,unsigned command,uint64_t now) {
    CohMapPacket packet;CohMapFields fields={m->cookie,m->config.cod,0,0,NULL};
    /* Outbound is deliberately uncompressed. Source version1 defaults to
     * compression but permits explicit uncompressed packets. */
    CohMapProfile profile={m->config.udp.link.version<4,0};
    CohStatus s=coh_map_serialize(command,profile,&fields,&packet);
    if(s==COH_OK)s=coh_net_udp_queue(m->udp,(CohBytes){packet.data,(packet.bits+7)/8},packet.bits,1,0,0,now);
    coh_map_packet_wipe(&packet);return s;
}
static CohStatus inspect(CohMapClient *m,const CohNetMessage *message,uint64_t now) {
    if(!m->authorized)return COH_STATE;
    CohBytes b={message->payload,(message->payload_bits+7)/8};CohRepReader reader;uint32_t cmd;
    CohStatus s=coh_rep_reader(&reader,b,message->payload_bits,message->compressed);
    if(s==COH_OK)s=coh_rep_pack(&reader,1,&cmd);
    if(s!=COH_OK)goto rejected;
    if(m->config.udp.link.version<4){if(cmd<7){s=COH_UNSUPPORTED;goto rejected;}cmd-=5;}
    if(cmd==COH_REP_CONNECT_MSG) {
        CohRepConnect v;s=coh_rep_connect(&reader,&v);
        if(s!=COH_OK)goto rejected;
        if(reader.cursor!=reader.bits){s=COH_UNSUPPORTED;goto rejected;}
        if(!v.accepted){coh_map_client_close(m);m->diag.disconnects++;s=COH_STATE;goto rejected;}
        if(m->diag.phase!=COH_MAP_WAIT_CONNECT){s=COH_STATE;goto rejected;}
    } else if(cmd==COH_REP_SHORTCUTS) {
        if(m->diag.phase!=COH_MAP_WAIT_SHORTCUTS){s=COH_STATE;goto rejected;}
    } else if(cmd==COH_REP_GROUPS) {
        if(m->diag.phase!=COH_MAP_WAIT_SCENE&&m->diag.phase!=COH_MAP_SCENE_INCOMPLETE){s=COH_STATE;goto rejected;}
    } else if(cmd==COH_REP_UPDATE||cmd==COH_REP_ALLENTS) {
        if(m->diag.phase!=COH_MAP_SCENE_INCOMPLETE){s=COH_STATE;goto rejected;}
    } else {s=COH_UNSUPPORTED;goto rejected;}
    if(m->diag.selected_dbid) {
        s=coh_rep_session_message(&m->inspector,&m->schema,b,message->payload_bits,
            message->compressed,m->config.udp.link.version<4,(int)m->authorized);
    } else if(cmd==COH_REP_CONNECT_MSG) {
        /* Already completely parsed above. Identity remains unverified. */
        s=COH_OK;
    } else if(cmd==COH_REP_SHORTCUTS) {
        CohRepSchema schema;s=coh_rep_shortcuts(&reader,&schema);
        if(s==COH_OK&&reader.cursor!=reader.bits)s=COH_UNSUPPORTED;
        if(s==COH_OK)m->schema=schema;
    } else if(cmd==COH_REP_GROUPS) {
        CohRepScenePrefix prefix;s=coh_rep_scene_prefix(&reader,&prefix);
    } else {
        CohRepUpdatePrefix prefix;s=coh_rep_update_prefix(&reader,&m->schema,cmd,&prefix);
    }
    if(s!=COH_OK)goto rejected;
    if(cmd==COH_REP_GROUPS) {
        m->diag.scene_prefixes++;m->diag.phase=COH_MAP_SCENE_INCOMPLETE;
        /* Group filename/reference records are unparsed even if their bytes
         * happen to be empty. A prefix never proves a complete scene. */
        s=COH_UNSUPPORTED;goto rejected;
    }
    if(cmd==COH_REP_UPDATE||cmd==COH_REP_ALLENTS) {
        m->diag.entity_prefixes++;s=COH_UNSUPPORTED;goto rejected;
    }
    if(cmd==COH_REP_CONNECT_MSG) {
        s=send_command(m,COH_MAP_REQSHORTCUTS,now);
        if(s==COH_OK){m->diag.phase=COH_MAP_WAIT_SHORTCUTS;m->phase_ms=now;}
    } else {
        s=send_command(m,COH_MAP_REQSCENE,now);
        if(s==COH_OK){m->diag.phase=COH_MAP_WAIT_SCENE;m->phase_ms=now;}
    }
    if(s!=COH_OK){coh_map_client_close(m);m->diag.phase=COH_MAP_FAILED;goto rejected;}
    m->diag.accepted_messages++;return COH_OK;
rejected:
    m->diag.rejected_messages++;
    if(s==COH_INVALID||s==COH_LIMIT)m->diag.malformed++;
    if(s==COH_UNSUPPORTED)m->diag.unsupported++;
    return s;
}
CohStatus coh_map_client_service(CohMapClient *m,uint64_t now,CohCancel cancel) {
    if(!m||now<m->last_ms)return COH_INVALID;
    if(!m->udp||m->diag.phase==COH_MAP_IDLE||m->diag.phase==COH_MAP_CLOSED||m->diag.phase==COH_MAP_SUSPENDED||
       m->diag.phase==COH_MAP_TIMED_OUT||m->diag.phase==COH_MAP_FAILED)return COH_STATE;
    m->last_ms=now;CohStatus s=coh_net_udp_service(m->udp,now,cancel);CohNetUdpDiagnostics udp;
    coh_net_udp_diagnostics(m->udp,&udp);
    if(udp.state!=COH_UDP_ACTIVE) {
        clear_authorization(m);
        if(udp.state==COH_UDP_TIMED_OUT){m->diag.phase=COH_MAP_TIMED_OUT;m->diag.timeouts++;}
        else m->diag.phase=udp.state==COH_UDP_CLOSED?COH_MAP_CLOSED:COH_MAP_FAILED;
        return s;
    }
    if(s!=COH_OK)return s;
    if(m->diag.phase==COH_MAP_NET_CONNECTING&&udp.link_state==COH_NET_CONNECTED) {
        s=send_command(m,COH_MAP_CONNECT,now);m->cookie=0;
        if(s!=COH_OK){coh_map_client_close(m);m->diag.phase=COH_MAP_FAILED;return s;}
        m->diag.phase=COH_MAP_WAIT_CONNECT;m->phase_ms=now;
    }
    CohStatus result=COH_OK;
    for(unsigned i=0;i<m->config.message_budget;i++) {
        CohNetMessage message;s=coh_net_udp_next(m->udp,&message);
        if(s==COH_NOT_FOUND)break;
        if(s!=COH_OK)return s;
        s=inspect(m,&message,now);wipe(&message,sizeof(message));
        if(s!=COH_OK)result=s;
        if(!m->authorized)break;
    }
    if(m->diag.phase!=COH_MAP_DISCONNECTING&&now-m->phase_ms>=m->config.application_timeout_ms) {
        coh_map_client_close(m);m->diag.phase=COH_MAP_TIMED_OUT;m->diag.timeouts++;return COH_STATE;
    }
    return result;
}
CohStatus coh_map_client_disconnect(CohMapClient *m,uint64_t now) {
    if(!m||now<m->last_ms)return COH_INVALID;
    if(!m->udp||!m->authorized)return COH_STATE;
    CohStatus s=coh_net_udp_disconnect(m->udp,now);m->last_ms=now;
    if(s!=COH_OK){coh_map_client_close(m);return s;}
    clear_authorization(m);m->diag.phase=COH_MAP_DISCONNECTING;m->diag.disconnects++;return COH_OK;
}
void coh_map_client_suspend(CohMapClient *m) {
    if(!m||!m->udp||m->diag.phase==COH_MAP_SUSPENDED)return;
    coh_net_udp_suspend(m->udp);clear_authorization(m);m->diag.phase=COH_MAP_SUSPENDED;m->diag.suspends++;
}
CohStatus coh_map_client_local_endpoint(const CohMapClient *m,CohNetEndpoint *out) {
    return m&&m->udp?coh_net_udp_local_endpoint(m->udp,out):COH_STATE;
}
void coh_map_client_diagnostics(const CohMapClient *m,CohMapDiagnostics *out) {
    if(!m||!out)return;
    *out=m->diag;out->inspector_phase=m->inspector.phase;
    if(m->udp)coh_net_udp_diagnostics(m->udp,&out->udp);
}
