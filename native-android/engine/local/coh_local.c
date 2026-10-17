#include "coh_local.h"
#include <stdlib.h>
#include <string.h>
struct CohLocal {
    CohLocalConfig config;
    CohLocalDiagnostics diagnostics;
    CohDbSession *db;
    CohMapClient *map;
    uint64_t clock_ms,retired_opened,retired_closed,observed_lists;
    uint32_t db_id,map_id,last_db_id,last_map_id,selected_slot;
    unsigned selected;
};
static int loopback(CohNetEndpoint e){return e.address[0]==127;}
static int active(CohLocalPhase p){return p>=COH_LOCAL_DB_CONNECTING&&p<=COH_LOCAL_SCENE_INCOMPLETE;}
static void snapshot(CohLocal *s){
    CohDbSessionDiagnostics d={0};CohMapDiagnostics m={0};
    if(s->db)coh_db_session_diagnostics(s->db,&d);
    if(s->map)coh_map_client_diagnostics(s->map,&m);
    s->diagnostics.db_phase=d.phase;s->diagnostics.map_phase=m.phase;
    s->diagnostics.map_protocol=m;
    if(d.server_identity_bound)s->diagnostics.server_identity_bound=1;
    s->diagnostics.character_lists+=d.player_lists-s->observed_lists;s->observed_lists=d.player_lists;
    s->diagnostics.opened_sockets=s->retired_opened+d.transport.sockets_opened+m.udp.sockets_opened;
    s->diagnostics.closed_sockets=s->retired_closed+d.transport.sockets_closed+m.udp.sockets_closed;
}
static void close_modules(CohLocal *s){
    if(s->db)coh_db_session_cancel(s->db);
    if(s->map)coh_map_client_close(s->map);
    s->selected=0;s->selected_slot=s->db_id=s->map_id=0;s->diagnostics.server_identity_bound=0;snapshot(s);
}
static CohStatus stop(CohLocal *s,CohLocalPhase phase,CohStatus status){
    snapshot(s);s->diagnostics.terminal_failure=1;
    s->diagnostics.terminal_db_phase=s->diagnostics.db_phase;
    s->diagnostics.terminal_map_phase=s->diagnostics.map_phase;
    close_modules(s);s->diagnostics.phase=phase;s->diagnostics.last_status=status;
    s->diagnostics.failures++;return status;
}
CohLocalConfig coh_local_default_config(void){
    CohLocalConfig c;memset(&c,0,sizeof(c));
    c.db.transport.link=coh_net_default_config();
    c.db.transport.local=(CohNetEndpoint){{127,0,0,1},0};
    c.db.transport.receive_budget=16;c.db.request_timeout_ms=120000;
    c.map.udp.link=coh_net_default_config();
    c.map.udp.local=c.db.transport.local;c.map.udp.receive_budget=16;
    c.map.application_timeout_ms=120000;c.map.message_budget=16;
    return c;
}
CohStatus coh_local_login_policy(CohDbLogin *out){
    if(!out)return COH_INVALID;
    CohDbLogin p;memset(&p,0,sizeof(p));p.protocol_version=COH_DB_PROTOCOL_VERSION;
    p.no_version_check=1;strcpy(p.patch_version,"coh-native-local-development");
    strcpy(p.system_spec,"Disabled");*out=p;return COH_OK;
}
CohLocal *coh_local_create(const CohLocalConfig *c){
    if(!c||c->local_development_enabled!=1||!loopback(c->db.transport.peer)||
        !loopback(c->db.transport.local)||!loopback(c->map.udp.local))return NULL;
    CohMapConfig map=c->map;map.udp.peer=c->db.transport.peer;
    if(coh_net_udp_config_validate(&c->db.transport)!=COH_OK||!c->db.request_timeout_ms||
       (c->db.outbound_compressed!=0&&c->db.outbound_compressed!=1)||
       (c->db.outbound_compressed&&!c->db.transport.link.version)||coh_map_config_validate(&map)!=COH_OK)return NULL;
    CohLocal *s=calloc(1,sizeof(*s));if(!s)return NULL;
    s->config=*c;s->diagnostics.local_development_auth=1;return s;
}
void coh_local_destroy(CohLocal *s){if(s){coh_db_session_destroy(s->db);coh_map_client_destroy(s->map);coh_db_wipe(s,sizeof(*s));free(s);}}
static int valid_account(const char *name){
    if(!name)return 0;
    for(unsigned n=0;n<15;n++){
        unsigned char c=(unsigned char)name[n];if(!c)return n>0;
        if(c<32||c>126)return 0;
    }return 0;
}
CohStatus coh_local_begin(CohLocal *s,const CohDbLogin *policy,const char *name,uint32_t dbid,uint32_t mapid,uint64_t now){
    if(!s||!policy||!valid_account(name)||policy->account[0]||policy->user_id||policy->cookie||
        policy->protocol_version!=COH_DB_PROTOCOL_VERSION||!dbid||!mapid||dbid==mapid)return COH_INVALID;
    if(active(s->diagnostics.phase))return COH_STATE;
    if(now<s->clock_ms||dbid<=s->last_db_id||dbid<=s->last_map_id||mapid<=s->last_db_id||mapid<=s->last_map_id)return COH_INVALID;
    if(s->diagnostics.generation==UINT32_MAX)return COH_LIMIT;
    CohDbSession *db=coh_db_session_create(&s->config.db);if(!db)return COH_LIMIT;
    CohDbLogin login=*policy;memcpy(login.account,name,strlen(name)+1);
    CohStatus status=coh_db_session_begin_local(db,&login,s->diagnostics.generation+1,dbid,now);
    coh_db_wipe(&login,sizeof(login));
    if(status!=COH_OK){coh_db_session_destroy(db);return status;}
    CohDbSessionDiagnostics d={0};CohMapDiagnostics m={0};
    if(s->db)coh_db_session_diagnostics(s->db,&d);
    if(s->map)coh_map_client_diagnostics(s->map,&m);
    s->retired_opened+=d.transport.sockets_opened+m.udp.sockets_opened;
    s->retired_closed+=d.transport.sockets_closed+m.udp.sockets_closed;
    coh_db_session_destroy(s->db);coh_map_client_destroy(s->map);s->db=db;s->map=NULL;s->observed_lists=0;s->diagnostics.server_identity_bound=0;
    s->db_id=s->last_db_id=dbid;s->map_id=s->last_map_id=mapid;s->selected=0;
    s->clock_ms=now;s->diagnostics.attempts++;s->diagnostics.generation++;
    s->diagnostics.terminal_failure=0;s->diagnostics.terminal_db_phase=COH_DB_IDLE;
    s->diagnostics.terminal_map_phase=COH_MAP_IDLE;
    s->diagnostics.phase=COH_LOCAL_DB_CONNECTING;s->diagnostics.last_status=COH_OK;snapshot(s);return COH_OK;
}
CohStatus coh_local_characters(const CohLocal *s,CohLocalCharacters *out){
    if(!s||!out)return COH_INVALID;
    if(s->diagnostics.phase!=COH_LOCAL_CHARACTERS_READY)return COH_STATE;
    CohDbPlayers p;CohStatus status=coh_db_session_players(s->db,&p);
    if(status==COH_OK){CohLocalCharacters c;memset(&c,0,sizeof(c));c.count=p.max_slots;c.selectable_count=p.selectable_count;memcpy(c.players,p.players,sizeof(c.players));*out=c;}
    coh_db_wipe(&p,sizeof(p));return status;
}
CohStatus coh_local_choose_character(CohLocal *s,uint32_t slot,uint64_t now){
    if(!s)return COH_INVALID;
    if(s->diagnostics.phase!=COH_LOCAL_CHARACTERS_READY)return COH_STATE;
    if(now<s->clock_ms)return COH_INVALID;
    if(s->diagnostics.selection_generation==UINT32_MAX)return COH_LIMIT;
    /* Source -db local_map_server is false for the existing independently
     * started MapServer; local_map_ip=0 lets DB select the real destination. */
    CohStatus status=coh_db_session_choose(s->db,slot,0,0,now);
    if(status==COH_OK){s->selected=1;s->selected_slot=slot;s->clock_ms=now;
        s->diagnostics.selection_generation++;s->diagnostics.character_choices++;
        s->diagnostics.phase=COH_LOCAL_DB_CONNECTING;}return status;
}
static CohStatus begin_map(CohLocal *s,uint64_t now){
    CohDbSessionHandoff h;memset(&h,0,sizeof(h));
    CohStatus status=coh_db_session_take_handoff(s->db,&h);if(status!=COH_OK)return status;
    if(!s->selected||h.selected_slot!=s->selected_slot||!h.selection_generation||
       !h.selected_dbid||h.selected_dbid>INT32_MAX||h.selected_dbid!=h.map.link_id){coh_db_wipe(&h,sizeof(h));return COH_INVALID;}
    unsigned index=2;CohNetEndpoint peer={0};
    for(unsigned i=0;i<2;i++){
        CohNetEndpoint e;for(unsigned n=0;n<4;n++)e.address[n]=(uint8_t)(h.map.address[i]>>(8*n));e.port=h.map.udp_port;
        if(loopback(e)&&e.port){peer=e;index=i;break;}
    }
    if(index>1){s->diagnostics.policy_rejections++;coh_db_wipe(&h,sizeof(h));return COH_INVALID;}
    CohMapConfig c=s->config.map;c.udp.peer=peer;s->map=coh_map_client_create(&c);
    if(!s->map){coh_db_wipe(&h,sizeof(h));return COH_LIMIT;}
    /* Map authentication is the actual one-use local DB cookie. This does
     * not represent encrypted AuthServer authentication or Gate26 acceptance. */
    CohMapAuthorization a;memset(&a,0,sizeof(a));a.authenticated=0;a.local_development_authorized=1;a.endpoint_authorized=1;
    a.selected_slot=h.selected_slot;a.selection_generation=s->diagnostics.selection_generation;
    a.selected_dbid=h.selected_dbid;
    a.handoff=h.map;a.address_index=index;
    status=coh_map_client_begin(s->map,&a,s->map_id,now);
    coh_db_wipe(&a,sizeof(a));coh_db_wipe(&h,sizeof(h));
    if(status==COH_OK){s->diagnostics.map_handoffs++;s->diagnostics.phase=COH_LOCAL_MAP_CONNECTING;}
    return status;
}
CohStatus coh_local_service(CohLocal *s,uint64_t now,CohCancel cancel){
    if(!s)return COH_INVALID;
    if(!active(s->diagnostics.phase))return s->diagnostics.phase==COH_LOCAL_CANCELLED?COH_CANCELLED:COH_STATE;
    if(now<s->clock_ms)return COH_INVALID;
    s->clock_ms=now;
    if(cancel.poll&&cancel.poll(cancel.context)){coh_local_cancel(s);return COH_CANCELLED;}
    CohStatus status=COH_OK;
    if(s->db){CohDbSessionPhase p=coh_db_session_phase(s->db);
        if(p>=COH_DB_CONNECTING&&p<=COH_DB_DISCONNECTING){
            status=coh_db_session_service(s->db,now,(CohCancel){0});p=coh_db_session_phase(s->db);
            if(status!=COH_OK)return stop(s,p==COH_DB_TIMED_OUT?COH_LOCAL_TIMED_OUT:COH_LOCAL_FAILED,status);
        }
        if(p==COH_DB_FAILED||p==COH_DB_TIMED_OUT||p==COH_DB_CANCELLED||(p==COH_DB_CLOSED&&!s->map))
            return stop(s,p==COH_DB_TIMED_OUT?COH_LOCAL_TIMED_OUT:COH_LOCAL_FAILED,COH_STATE);
        if(p==COH_DB_CHARACTERS)s->diagnostics.phase=COH_LOCAL_CHARACTERS_READY;
        if(p==COH_DB_HANDOFF_READY){status=begin_map(s,now);if(status!=COH_OK)return stop(s,COH_LOCAL_FAILED,status);}
    }
    if(s->map){status=coh_map_client_service(s->map,now,(CohCancel){0});CohMapDiagnostics m={0};coh_map_client_diagnostics(s->map,&m);
        if(m.phase==COH_MAP_SCENE_INCOMPLETE&&(status==COH_OK||status==COH_UNSUPPORTED)){
            s->diagnostics.phase=COH_LOCAL_SCENE_INCOMPLETE;s->diagnostics.last_status=COH_UNSUPPORTED;snapshot(s);return COH_UNSUPPORTED;
        }
        if(status!=COH_OK)return stop(s,m.phase==COH_MAP_TIMED_OUT?COH_LOCAL_TIMED_OUT:COH_LOCAL_FAILED,status);
        if(m.phase==COH_MAP_CLOSED||m.phase==COH_MAP_FAILED)return stop(s,COH_LOCAL_FAILED,COH_STATE);
    }
    snapshot(s);return COH_OK;
}
void coh_local_suspend(CohLocal *s){if(s){if(s->db)coh_db_session_suspend(s->db);if(s->map)coh_map_client_suspend(s->map);s->selected=0;s->diagnostics.server_identity_bound=0;s->diagnostics.phase=COH_LOCAL_SUSPENDED;s->diagnostics.suspends++;snapshot(s);}}
void coh_local_cancel(CohLocal *s){if(s){close_modules(s);s->diagnostics.phase=COH_LOCAL_CANCELLED;s->diagnostics.cancellations++;}}
void coh_local_close(CohLocal *s){if(s){close_modules(s);s->diagnostics.phase=COH_LOCAL_CLOSED;}}
void coh_local_diagnostics(const CohLocal *s,CohLocalDiagnostics *out){if(s&&out)*out=s->diagnostics;}
