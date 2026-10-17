#include "coh_db_session.h"
#include "coh_db_handoff_private.h"
#include <stdlib.h>
#include <string.h>

struct CohDbSession {
    CohDbSessionConfig config;
    CohNetUdp *udp;
    CohDbSessionDiagnostics diagnostics;
    CohDbPlayers players;
    CohDbSessionHandoff handoff;
    uint8_t login[COH_DB_LOGIN_MAX];
    size_t login_bits;
    uint64_t clock_ms,phase_start_ms;
    uint32_t receipt_generation,user_id,selected_slot,connect_id;
    int begun,local_development;
};
static void forget(CohDbSession *s) {
    coh_db_wipe(s->login,sizeof(s->login));s->login_bits=0;
    coh_db_wipe(&s->players,sizeof(s->players));coh_db_wipe(&s->handoff,sizeof(s->handoff));
    s->user_id=0;s->selected_slot=0;
    s->diagnostics.server_identity_bound=0;
}
static CohStatus stop(CohDbSession *s,CohDbSessionPhase phase,CohStatus result) {
    coh_net_udp_close(s->udp);forget(s);s->diagnostics.phase=phase;return result;
}
static int active(CohDbSessionPhase phase) {
    return phase==COH_DB_CONNECTING||phase==COH_DB_WAIT_PLAYERS||phase==COH_DB_QUEUED||
        phase==COH_DB_CHARACTERS||phase==COH_DB_WAIT_MAP||phase==COH_DB_HANDOFF_READY||phase==COH_DB_DISCONNECTING;
}
CohDbSession *coh_db_session_create(const CohDbSessionConfig *c) {
    if(!c||coh_net_udp_config_validate(&c->transport)!=COH_OK||!c->request_timeout_ms||
       (c->outbound_compressed!=0&&c->outbound_compressed!=1)||
       (c->outbound_compressed&&!c->transport.link.version))return NULL;
    CohDbSession *s=calloc(1,sizeof(*s));if(!s)return NULL;
    s->config=*c;s->udp=coh_net_udp_create(&c->transport);
    if(!s->udp){free(s);return NULL;}return s;
}
void coh_db_session_destroy(CohDbSession *s) {
    if(s){coh_net_udp_destroy(s->udp);coh_db_wipe(s,sizeof(*s));free(s);}
}
CohStatus coh_db_session_begin(CohDbSession *s,const CohDbLogin *login,const CohDbAuthReceipt *auth,uint32_t id,uint64_t now) {
    if(!s||!login||!auth)return COH_INVALID;
    if(active(s->diagnostics.phase))return COH_STATE;
    if((s->begun&&now<s->clock_ms)||s->diagnostics.generation==UINT32_MAX)return COH_INVALID;
    if(!auth->user_id||auth->verified!=1||!auth->generation||auth->generation<=s->receipt_generation||
       auth->user_id!=login->user_id||auth->game_cookie!=login->cookie||
       !memchr(auth->account,0,sizeof(auth->account))||!memchr(login->account,0,sizeof(login->account))||strcmp(auth->account,login->account)) {
        s->diagnostics.receipt_rejections++;return COH_STATE;
    }
    uint8_t encoded[COH_DB_LOGIN_MAX];size_t bits=0;
    CohStatus result=coh_db_login_encode(login,s->config.outbound_compressed,s->config.transport.link.version<4,encoded,sizeof(encoded),&bits);
    if(result!=COH_OK){coh_db_wipe(encoded,sizeof(encoded));return result;}
    CohNetUdpState state=coh_net_udp_state(s->udp);
    result=(state==COH_UDP_IDLE||state==COH_UDP_CLOSED)?coh_net_udp_begin(s->udp,id,now):coh_net_udp_resume(s->udp,id,now);
    if(result!=COH_OK){coh_db_wipe(encoded,sizeof(encoded));return result;}
    forget(s);memcpy(s->login,encoded,(bits+7)/8);coh_db_wipe(encoded,sizeof(encoded));
    s->login_bits=bits;s->receipt_generation=auth->generation;s->user_id=auth->user_id;
    s->local_development=0;s->diagnostics.local_development_auth=0;s->diagnostics.server_identity_bound=1;
    s->connect_id=id;s->clock_ms=s->phase_start_ms=now;s->begun=1;s->diagnostics.generation++;
    s->diagnostics.queue_position=s->diagnostics.queue_count=0;s->diagnostics.phase=COH_DB_CONNECTING;return COH_OK;
}
static int loopback(CohNetEndpoint e) {return e.address[0]==127;}
CohStatus coh_db_session_begin_local(CohDbSession *s,const CohDbLogin *login,uint32_t generation,uint32_t id,uint64_t now) {
    if(!s||!login)return COH_INVALID;
    if(active(s->diagnostics.phase))return COH_STATE;
    if(!generation||generation<=s->receipt_generation||login->user_id||login->cookie||
       !loopback(s->config.transport.peer)||!loopback(s->config.transport.local)) {
        s->diagnostics.receipt_rejections++;return COH_STATE;
    }
    if((s->begun&&now<s->clock_ms)||s->diagnostics.generation==UINT32_MAX)return COH_INVALID;
    uint8_t encoded[COH_DB_LOGIN_MAX];size_t bits=0;
    CohStatus result=coh_db_local_login_encode(login,s->config.outbound_compressed,
        s->config.transport.link.version<4,encoded,sizeof(encoded),&bits);
    if(result!=COH_OK){coh_db_wipe(encoded,sizeof(encoded));return result;}
    CohNetUdpState state=coh_net_udp_state(s->udp);
    result=(state==COH_UDP_IDLE||state==COH_UDP_CLOSED)?coh_net_udp_begin(s->udp,id,now):coh_net_udp_resume(s->udp,id,now);
    if(result!=COH_OK){coh_db_wipe(encoded,sizeof(encoded));return result;}
    forget(s);memcpy(s->login,encoded,(bits+7)/8);coh_db_wipe(encoded,sizeof(encoded));
    s->login_bits=bits;s->receipt_generation=generation;s->local_development=1;
    s->diagnostics.local_development_auth=1;s->clock_ms=s->phase_start_ms=now;
    s->connect_id=id;s->begun=1;s->diagnostics.generation++;s->diagnostics.queue_position=s->diagnostics.queue_count=0;
    s->diagnostics.phase=COH_DB_CONNECTING;return COH_OK;
}
static CohStatus message_command(const CohNetMessage *m,int legacy,uint32_t *command) {
    size_t bytes=(m->payload_bits+7)/8;if(bytes>COH_PROTOCOL_FRAME_MAX)bytes=COH_PROTOCOL_FRAME_MAX;
    size_t bits=m->payload_bits;if(bits>bytes*8)bits=bytes*8;
    CohProtocolBits b;
    if(coh_protocol_bits_init(&b,(uint8_t *)(uintptr_t)m->payload,bytes,bits,0))return COH_INVALID;
    uint32_t c;
    if(m->compressed?coh_protocol_read(&b,32,&c):coh_protocol_read_pack(&b,1,&c))return COH_INVALID;
    if(legacy){if(c<5)return COH_INVALID;c-=5;}*command=c;return COH_OK;
}
static CohStatus application_message(CohDbSession *s,const CohNetMessage *m) {
    int legacy=s->config.transport.link.version<4;uint32_t command;
    CohStatus result=message_command(m,legacy,&command);if(result!=COH_OK)return result;
    CohBytes body={m->payload,(m->payload_bits+7)/8};int aligned=m->compressed;
    if(command==COH_DB_MESSAGE) {
        result=coh_db_server_error_parse(body,m->payload_bits,aligned,legacy);
        if(result!=COH_OK)return result;
        s->diagnostics.server_rejections++;return COH_STATE;
    }
    if(command==COH_DB_QUEUE_POSITION) {
        if(s->diagnostics.phase!=COH_DB_WAIT_PLAYERS&&s->diagnostics.phase!=COH_DB_QUEUED)return COH_STATE;
        CohDbQueue queue;result=coh_db_queue_parse(body,m->payload_bits,aligned,legacy,&queue);
        if(result!=COH_OK)return result;
        s->diagnostics.queue_position=queue.position;s->diagnostics.queue_count=queue.count;
        s->diagnostics.queue_updates++;s->diagnostics.phase=queue.position?COH_DB_QUEUED:COH_DB_WAIT_PLAYERS;return COH_OK;
    }
    if(command==COH_DB_SEND_PLAYERS) {
        if(s->diagnostics.phase!=COH_DB_WAIT_PLAYERS&&s->diagnostics.phase!=COH_DB_QUEUED&&s->diagnostics.phase!=COH_DB_CHARACTERS)return COH_STATE;
        CohDbPlayers players;
        result=coh_db_players_parse(body,m->payload_bits,aligned,legacy,&players);
        if(result==COH_OK&&(!players.user_id||
            ((!s->local_development||s->user_id)&&players.user_id!=s->user_id)))result=COH_INVALID;
        if(result==COH_OK&&s->local_development&&!s->user_id){s->user_id=players.user_id;s->diagnostics.server_identity_bound=1;}
        if(result==COH_OK){s->players=players;s->diagnostics.player_lists++;s->diagnostics.phase=COH_DB_CHARACTERS;}
        coh_db_wipe(&players,sizeof(players));return result;
    }
    if(command==COH_DB_MAP_CONNECT) {
        if(s->diagnostics.phase!=COH_DB_WAIT_MAP)return COH_STATE;
        CohAuthMapHandoff map;
        result=coh_db_map_handoff_parse(body,m->payload_bits,aligned,legacy,&map);
        if(result!=COH_OK)return result;
        /* Exact DBGAMESERVER_MAP_CONNECT producer writes EntCon.id first.
         * QueueServer forwards all seven fields unchanged. Only this opaque
         * WAIT_MAP owner can associate that field with its validated choice;
         * the generic CohAuthMapHandoff.link_id remains a raw wire field. */
        if(!s->diagnostics.selection_generation||!s->diagnostics.server_identity_bound||
           !map.link_id||map.link_id>INT32_MAX){coh_db_wipe(&map,sizeof(map));return COH_STATE;}
        s->handoff=(CohDbSessionHandoff){map,s->selected_slot,s->diagnostics.selection_generation,map.link_id};
        coh_db_wipe(&map,sizeof(map));s->diagnostics.handoffs++;s->diagnostics.phase=COH_DB_HANDOFF_READY;return COH_OK;
    }
    /* Other valid DB services (inventory/catalog, etc.) are independent. They
     * never promote this session or provide a character/map handoff. */
    s->diagnostics.unsupported++;return COH_OK;
}
CohStatus coh_db_session_service(CohDbSession *s,uint64_t now,CohCancel cancel) {
    if(!s)return COH_INVALID;
    if(!active(s->diagnostics.phase))return s->diagnostics.phase==COH_DB_CANCELLED?COH_CANCELLED:COH_STATE;
    if(now<s->clock_ms)return COH_INVALID;
    s->clock_ms=now;
    CohStatus result=coh_net_udp_service(s->udp,now,cancel);
    if(result==COH_CANCELLED){forget(s);s->diagnostics.cancellations++;s->diagnostics.phase=COH_DB_CANCELLED;return result;}
    CohNetUdpDiagnostics net;coh_net_udp_diagnostics(s->udp,&net);
    if(net.state==COH_UDP_CLOSED){forget(s);s->diagnostics.phase=COH_DB_CLOSED;return COH_OK;}
    if(net.state==COH_UDP_TIMED_OUT){s->diagnostics.timeouts++;return stop(s,COH_DB_TIMED_OUT,COH_STATE);}
    if(result!=COH_OK)return stop(s,COH_DB_FAILED,result);
    if(s->diagnostics.phase==COH_DB_DISCONNECTING)return COH_OK;
    if(s->diagnostics.phase!=COH_DB_CHARACTERS&&now-s->phase_start_ms>=s->config.request_timeout_ms) {
        s->diagnostics.timeouts++;return stop(s,COH_DB_TIMED_OUT,COH_STATE);
    }
    if(s->diagnostics.phase==COH_DB_CONNECTING&&net.link_state==COH_NET_CONNECTED) {
        result=coh_net_udp_queue(s->udp,(CohBytes){s->login,(s->login_bits+7)/8},(uint32_t)s->login_bits,1,0,s->config.outbound_compressed,now);
        if(result==COH_LIMIT)return COH_OK;
        if(result!=COH_OK)return stop(s,COH_DB_FAILED,result);
        coh_db_wipe(s->login,sizeof(s->login));s->login_bits=0;s->phase_start_ms=now;
        s->diagnostics.login_requests++;s->diagnostics.phase=COH_DB_WAIT_PLAYERS;
    }
    for(unsigned i=0;i<COH_NET_RX_MAX;i++) {
        CohNetMessage message;result=coh_net_udp_next(s->udp,&message);
        if(result==COH_NOT_FOUND)break;
        if(result!=COH_OK)return stop(s,COH_DB_FAILED,result);
        uint64_t rejections=s->diagnostics.server_rejections;
        result=application_message(s,&message);coh_db_wipe(&message,sizeof(message));
        if(result!=COH_OK){if(result==COH_UNSUPPORTED)s->diagnostics.unsupported++;else if(rejections==s->diagnostics.server_rejections)s->diagnostics.malformed++;return stop(s,COH_DB_FAILED,result);}
    }
    return COH_OK;
}
CohStatus coh_db_session_players(const CohDbSession *s,CohDbPlayers *out) {
    if(!s||!out)return COH_INVALID;
    if(s->diagnostics.phase!=COH_DB_CHARACTERS)return COH_STATE;
    *out=s->players;return COH_OK;
}
CohStatus coh_db_session_choose(CohDbSession *s,uint32_t slot,uint32_t ip,uint32_t location,uint64_t now) {
    if(!s)return COH_INVALID;
    if(s->diagnostics.phase!=COH_DB_CHARACTERS)return COH_STATE;
    if(now<s->clock_ms)return COH_INVALID;
    if(s->diagnostics.selection_generation==UINT32_MAX)return COH_LIMIT;
    CohDbChoose choose;CohStatus result=coh_db_player_choose(&s->players,slot,ip,location,&choose);
    if(result!=COH_OK)return result;
    uint8_t data[160];size_t bits=0;
    result=coh_db_choose_encode(&choose,s->config.outbound_compressed,s->config.transport.link.version<4,data,sizeof(data),&bits);
    coh_db_wipe(&choose,sizeof(choose));
    if(result==COH_OK)result=coh_net_udp_queue(s->udp,(CohBytes){data,(bits+7)/8},(uint32_t)bits,1,0,s->config.outbound_compressed,now);
    coh_db_wipe(data,sizeof(data));if(result!=COH_OK)return result;
    coh_db_wipe(&s->players,sizeof(s->players));s->selected_slot=slot;s->clock_ms=s->phase_start_ms=now;
    s->diagnostics.selection_generation++;s->diagnostics.choices++;s->diagnostics.phase=COH_DB_WAIT_MAP;return COH_OK;
}
CohStatus coh_db_session_take_handoff(CohDbSession *s,CohDbSessionHandoff *out) {
    if(!s||!out)return COH_INVALID;
    if(s->diagnostics.phase!=COH_DB_HANDOFF_READY)return COH_STATE;
    CohStatus result=coh_net_udp_disconnect(s->udp,s->clock_ms);if(result!=COH_OK)return result;
    *out=s->handoff;forget(s);s->diagnostics.disconnects++;s->diagnostics.phase=COH_DB_DISCONNECTING;return COH_OK;
}
CohStatus coh_db_session_disconnect(CohDbSession *s,uint64_t now) {
    if(!s)return COH_INVALID;
    if(!active(s->diagnostics.phase)||s->diagnostics.phase==COH_DB_DISCONNECTING)return COH_STATE;
    if(now<s->clock_ms)return COH_INVALID;
    CohNetUdpDiagnostics net;coh_net_udp_diagnostics(s->udp,&net);
    if(net.link_state!=COH_NET_CONNECTED){s->clock_ms=now;s->diagnostics.disconnects++;return stop(s,COH_DB_CLOSED,COH_OK);}
    CohStatus result=coh_net_udp_disconnect(s->udp,now);if(result!=COH_OK)return result;
    forget(s);s->clock_ms=now;s->diagnostics.disconnects++;s->diagnostics.phase=COH_DB_DISCONNECTING;return COH_OK;
}
void coh_db_session_suspend(CohDbSession *s) {
    if(s&&s->diagnostics.phase!=COH_DB_SUSPENDED){coh_net_udp_suspend(s->udp);forget(s);s->diagnostics.suspends++;s->diagnostics.phase=COH_DB_SUSPENDED;}
}
void coh_db_session_cancel(CohDbSession *s) {
    if(s&&s->diagnostics.phase!=COH_DB_CANCELLED){coh_net_udp_cancel(s->udp);forget(s);s->diagnostics.cancellations++;s->diagnostics.phase=COH_DB_CANCELLED;}
}
CohStatus coh_db_session_local_endpoint(const CohDbSession *s,CohNetEndpoint *out) {
    if(!s||!out)return COH_INVALID;
    return coh_net_udp_local_endpoint(s->udp,out);
}
CohDbSessionPhase coh_db_session_phase(const CohDbSession *s){return s?s->diagnostics.phase:COH_DB_FAILED;}
void coh_db_session_diagnostics(const CohDbSession *s,CohDbSessionDiagnostics *out) {
    if(s&&out){*out=s->diagnostics;coh_net_udp_diagnostics(s->udp,&out->transport);}
}

/* This detached one-shot owner survives graceful DB close; callers explicitly
 * retire it on Map cancellation/lifecycle loss. No pointer to a dead session. */
struct CohDbHandoffOwner {
    CohDbHandoffMetadata metadata;
    CohDbSessionHandoff secret;
    CohDbHandoffAllocator allocator;
    uint32_t references;
};
static int owner_overlap(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t ap=(uintptr_t)a,bp=(uintptr_t)b;
    if(an>UINTPTR_MAX-ap||bn>UINTPTR_MAX-bp)return 1;
    return ap<bp+bn&&bp<ap+an;
}
static void *owner_allocate(void *context,size_t bytes) {(void)context;return malloc(bytes);}
static void owner_deallocate(void *context,void *p,size_t bytes) {(void)context;(void)bytes;free(p);}
CohStatus coh_db_handoff_owner_retain(CohDbHandoffOwner *owner) {
    if(!owner)return COH_INVALID;
    if(owner->references==UINT32_MAX)return COH_LIMIT;
    owner->references++;return COH_OK;
}
void coh_db_handoff_owner_retire(CohDbHandoffOwner *owner) {
    if(owner){coh_db_wipe(&owner->secret,sizeof(owner->secret));owner->metadata.retired=1;}
}
void coh_db_handoff_owner_release(CohDbHandoffOwner *owner) {
    if(owner&&!--owner->references){
        CohDbHandoffAllocator allocator=owner->allocator;
        coh_db_wipe(owner,sizeof(*owner));
        allocator.deallocate(allocator.context,owner,sizeof(*owner));
    }
}
CohStatus coh_db_handoff_owner_metadata(const CohDbHandoffOwner *owner,CohDbHandoffMetadata *out) {
    if(!owner||!out||owner_overlap(owner,sizeof(*owner),out,sizeof(*out)))return COH_INVALID;
    *out=owner->metadata;return COH_OK;
}
CohStatus coh_db_handoff_owner_claim(CohDbHandoffOwner *owner,uint32_t generation,
    uint32_t selection,CohDbSessionHandoff *out) {
    if(!owner||!out||owner_overlap(owner,sizeof(*owner),out,sizeof(*out)))return COH_INVALID;
    if(owner->metadata.retired||owner->metadata.claimed||
       owner->metadata.session_generation!=generation||
       owner->metadata.selection_generation!=selection)return COH_STATE;
    *out=owner->secret;coh_db_wipe(&owner->secret,sizeof(owner->secret));
    owner->metadata.claimed=1;return COH_OK;
}
CohStatus coh_db_session_take_handoff_owner_alloc(CohDbSession *s,
    const CohDbHandoffAllocator *allocator,CohDbHandoffOwner **out) {
    if(!s||!out||!allocator)return COH_INVALID;
    if(owner_overlap(s,sizeof(*s),out,sizeof(*out))||
       owner_overlap(s,sizeof(*s),allocator,sizeof(*allocator))||
       owner_overlap(allocator,sizeof(*allocator),out,sizeof(*out)))return COH_INVALID;
    if(*out||!allocator->allocate||!allocator->deallocate)return COH_INVALID;
    if(s->diagnostics.phase!=COH_DB_HANDOFF_READY||!s->user_id||
       !s->diagnostics.server_identity_bound||!s->diagnostics.generation||
       !s->receipt_generation||!s->handoff.selection_generation||
       s->handoff.selection_generation!=s->diagnostics.selection_generation||
       !s->handoff.selected_dbid||s->handoff.selected_dbid>INT32_MAX||
       s->handoff.selected_dbid!=s->handoff.map.link_id)return COH_STATE;
    CohDbHandoffOwner *owner=allocator->allocate(allocator->context,sizeof(*owner));
    if(!owner)return COH_LIMIT;
    memset(owner,0,sizeof(*owner));owner->allocator=*allocator;owner->references=1;
    owner->metadata.user_id=s->user_id;owner->metadata.selected_dbid=s->handoff.selected_dbid;
    owner->metadata.selected_slot=s->handoff.selected_slot;
    owner->metadata.selection_generation=s->handoff.selection_generation;
    owner->metadata.session_generation=s->diagnostics.generation;
    owner->metadata.receipt_generation=s->receipt_generation;owner->metadata.connect_id=s->connect_id;
    owner->metadata.db_peer=s->config.transport.peer;
    owner->metadata.local_development_auth=(unsigned)s->local_development;
    owner->metadata.selected_dbid_owner_bound=1;
    CohStatus result=coh_db_session_take_handoff(s,&owner->secret);
    if(result!=COH_OK){coh_db_handoff_owner_release(owner);return result;}
    *out=owner;return COH_OK;
}
CohStatus coh_db_session_take_handoff_owner(CohDbSession *s,CohDbHandoffOwner **out) {
    const CohDbHandoffAllocator allocator={NULL,owner_allocate,owner_deallocate};
    return coh_db_session_take_handoff_owner_alloc(s,&allocator,out);
}
