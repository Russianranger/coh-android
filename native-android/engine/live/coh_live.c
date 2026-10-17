#include "coh_live.h"
#include "../session/coh_session_crypto.h"
#include <stdlib.h>
#include <string.h>
struct CohLive {
 CohLiveConfig config;
 CohLiveDiagnostics diagnostics;
 CohLogin *login;
 CohDbSession *db;
 CohMapClient *map;
 CohDbLogin policy;
 CohDbSessionHandoff pending;
 uint64_t clock_ms,retired_opened,retired_closed;uint32_t db_id,map_id,last_db_id,last_map_id,selected_slot;
 int auth_consumed,selected;
};
static int endpoint_valid(CohNetEndpoint e){return e.port&&e.address[0]&&e.address[0]<224;}
static int endpoint_equal(CohNetEndpoint a,CohNetEndpoint b){return a.port==b.port&&!memcmp(a.address,b.address,4);}
static int active(CohLivePhase p){return p>=COH_LIVE_AUTHENTICATING&&p<=COH_LIVE_SCENE_INCOMPLETE;}
static void forget(CohLive *s){coh_db_wipe(&s->policy,sizeof(s->policy));coh_db_wipe(&s->pending,sizeof(s->pending));
 s->auth_consumed=s->selected=0;
 s->selected_slot=0;
 s->db_id=s->map_id=0;}
static void snapshot(CohLive *s){
 CohLoginDiagnostics a={0};
 CohDbSessionDiagnostics b={0};
 CohMapDiagnostics m={0};
 if(s->login)coh_login_diagnostics(s->login,&a);
 if(s->db)coh_db_session_diagnostics(s->db,&b);
 if(s->map)coh_map_client_diagnostics(s->map,&m);
 s->diagnostics.auth_state=a.state;
 s->diagnostics.db_phase=b.phase;
 s->diagnostics.map_phase=m.phase;
 s->diagnostics.opened_sockets=s->retired_opened+a.sockets_opened+b.transport.sockets_opened+m.udp.sockets_opened;
 s->diagnostics.closed_sockets=s->retired_closed+a.sockets_closed+b.transport.sockets_closed+m.udp.sockets_closed;
}
static void close_modules(CohLive *s){
 if(s->login)coh_login_close(s->login);
 if(s->db)coh_db_session_cancel(s->db);
 if(s->map)coh_map_client_close(s->map);
 forget(s);
 snapshot(s);
}
static CohStatus stop(CohLive *s,CohLivePhase phase,CohStatus status){close_modules(s);
 s->diagnostics.phase=phase;
 s->diagnostics.last_status=status;
 s->diagnostics.failures++;
 return status;}
CohLive *coh_live_create(const CohLiveConfig *c){
 if(!c||!endpoint_valid(c->authorized_auth)||!c->approve_map||!c->login.crypto||!c->login.crypto->keypair||!c->login.crypto->shared)return NULL;
 CohMapConfig map=c->map;map.udp.peer=c->db.transport.peer;
 if(coh_net_udp_config_validate(&c->db.transport)!=COH_OK||!c->db.request_timeout_ms||
    (c->db.outbound_compressed!=0&&c->db.outbound_compressed!=1)||
    (c->db.outbound_compressed&&!c->db.transport.link.version)||coh_map_config_validate(&map)!=COH_OK)return NULL;
 CohLive *s=calloc(1,sizeof(*s));
 if(!s)return NULL;
 s->config=*c;
 s->config.db.transport.key_exchange=coh_session_key_exchange;
 s->config.db.transport.key_context=(void*)c->login.crypto;
 s->config.map.udp.key_exchange=coh_session_key_exchange;
 s->config.map.udp.key_context=(void*)c->login.crypto;
 s->login=coh_login_create(&c->login);
 if(!s->login){coh_auth_wipe(s,sizeof(*s));free(s);
 return NULL;}return s;
}
void coh_live_destroy(CohLive *s){if(s){coh_login_destroy(s->login);coh_db_session_destroy(s->db);coh_map_client_destroy(s->map);coh_auth_wipe(s,sizeof(*s));free(s);}}
CohStatus coh_live_begin(CohLive *s,const CohDbLogin *policy,const char *name,const char *password,uint32_t subscription,uint16_t flags,uint32_t dbid,uint32_t mapid,uint64_t now){
 if(!s||!policy||!dbid||!mapid||dbid==mapid||policy->account[0]||policy->user_id||policy->cookie)return COH_INVALID;
 if(active(s->diagnostics.phase))return COH_STATE;
 if(now<s->clock_ms||dbid<=s->last_db_id||dbid<=s->last_map_id||mapid<=s->last_db_id||mapid<=s->last_map_id)return COH_INVALID;
 if(s->diagnostics.authentication_generation==UINT32_MAX)return COH_LIMIT;
 CohStatus status=coh_login_begin(s->login,s->config.authorized_auth,name,password,subscription,flags,now);
 if(status!=COH_OK)return status;
 CohDbSessionDiagnostics retired_db={0};CohMapDiagnostics retired_map={0};
 if(s->db)coh_db_session_diagnostics(s->db,&retired_db);
 if(s->map)coh_map_client_diagnostics(s->map,&retired_map);
 s->retired_opened+=retired_db.transport.sockets_opened+retired_map.udp.sockets_opened;
 s->retired_closed+=retired_db.transport.sockets_closed+retired_map.udp.sockets_closed;
 coh_db_session_destroy(s->db);
 s->db=NULL;coh_map_client_destroy(s->map);
 s->map=NULL;
 forget(s);
 s->policy=*policy;
 s->db_id=s->last_db_id=dbid;
 s->map_id=s->last_map_id=mapid;
 s->clock_ms=now;
 s->diagnostics.attempts++;
 s->diagnostics.phase=COH_LIVE_AUTHENTICATING;
 s->diagnostics.last_status=COH_OK;
 snapshot(s);
 return COH_OK;
}
CohStatus coh_live_shards(const CohLive *s,CohAuthShards *out){if(!s||!out)return COH_INVALID;
 if(s->diagnostics.phase!=COH_LIVE_SHARDS_READY)return COH_STATE;
 return coh_login_shards(s->login,out);}
CohStatus coh_live_choose_shard(CohLive *s,uint8_t id,uint64_t now){
 if(!s)return COH_INVALID;
 if(s->diagnostics.phase!=COH_LIVE_SHARDS_READY)return COH_STATE;
 if(now<s->clock_ms)return COH_INVALID;
 CohAuthShards shards;
 CohStatus status=coh_login_shards(s->login,&shards);
 if(status!=COH_OK)return status;
 int found=0;for(unsigned i=0;i<shards.count;i++)if(shards.shards[i].id==id){CohNetEndpoint e;memcpy(e.address,shards.shards[i].ipv4,4);e.port=shards.shards[i].port;found=endpoint_equal(e,s->config.db.transport.peer);break;}
 coh_auth_wipe(&shards,sizeof(shards));
 if(!found){s->diagnostics.policy_rejections++;
 return COH_INVALID;}
 status=coh_login_choose(s->login,id,now);
 if(status==COH_OK){s->clock_ms=now;
 s->diagnostics.shard_choices++;
 s->diagnostics.phase=COH_LIVE_AUTHENTICATING;}return status;
}
static CohStatus begin_db(CohLive *s,uint64_t now){
 CohLoginAuthorization auth;memset(&auth,0,sizeof(auth));
 CohStatus status=coh_login_authorization(s->login,&auth);
 if(status!=COH_OK)return status;
 CohNetEndpoint endpoint;memcpy(endpoint.address,auth.shard.ipv4,4);endpoint.port=auth.shard.port;
 if(!endpoint_equal(endpoint,s->config.db.transport.peer)){coh_auth_wipe(&auth,sizeof(auth));
 return COH_INVALID;}
 CohDbAuthReceipt receipt;memset(&receipt,0,sizeof(receipt));receipt.user_id=auth.play.user_id;receipt.game_cookie=auth.play.game_key;receipt.generation=++s->diagnostics.authentication_generation;receipt.verified=1;
 memcpy(receipt.account,auth.account_name,sizeof(receipt.account));memcpy(s->policy.account,auth.account_name,sizeof(s->policy.account));
 s->policy.user_id=auth.play.user_id;
 s->policy.cookie=auth.play.game_key;
 s->db=coh_db_session_create(&s->config.db);status=s->db?coh_db_session_begin(s->db,&s->policy,&receipt,s->db_id,now):COH_LIMIT;
 coh_db_wipe(&receipt,sizeof(receipt));coh_auth_wipe(&auth,sizeof(auth));coh_db_wipe(&s->policy,sizeof(s->policy));coh_login_close(s->login);
 if(status==COH_OK){s->auth_consumed=1;
 s->diagnostics.auth_receipts++;
 s->diagnostics.phase=COH_LIVE_DB_CONNECTING;}return status;
}
CohStatus coh_live_characters(const CohLive *s,CohLiveCharacters *out){
 if(!s||!out)return COH_INVALID;
 if(s->diagnostics.phase!=COH_LIVE_CHARACTERS_READY)return COH_STATE;
 CohDbPlayers players;
 CohStatus status=coh_db_session_players(s->db,&players);
 if(status==COH_OK){CohLiveCharacters result;memset(&result,0,sizeof(result));result.count=players.max_slots;result.selectable_count=players.selectable_count;memcpy(result.players,players.players,sizeof(result.players));*out=result;}coh_db_wipe(&players,sizeof(players));
 return status;
}
CohStatus coh_live_choose_character(CohLive *s,uint32_t slot,uint32_t ip,uint32_t location,uint64_t now){
 if(!s)return COH_INVALID;
 if(s->diagnostics.phase!=COH_LIVE_CHARACTERS_READY||!s->auth_consumed)return COH_STATE;
 if(now<s->clock_ms)return COH_INVALID;
 if(s->diagnostics.selection_generation==UINT32_MAX)return COH_LIMIT;
 CohStatus status=coh_db_session_choose(s->db,slot,ip,location,now);
 if(status==COH_OK){s->selected_slot=slot;
 s->selected=1;
 s->clock_ms=now;
 s->diagnostics.selection_generation++;
 s->diagnostics.character_choices++;
 s->diagnostics.phase=COH_LIVE_DB_CONNECTING;}return status;
}
static CohNetEndpoint map_endpoint(const CohLive *s,unsigned i){CohNetEndpoint e;for(unsigned n=0;n<4;n++)e.address[n]=(uint8_t)(s->pending.map.address[i]>>(8*n));e.port=s->pending.map.udp_port;
 return e;}
CohStatus coh_live_map_candidates(const CohLive *s,CohNetEndpoint out[2]){if(!s||!out)return COH_INVALID;
 if(s->diagnostics.phase!=COH_LIVE_MAP_APPROVAL)return COH_STATE;
 out[0]=map_endpoint(s,0);
 out[1]=map_endpoint(s,1);
 return COH_OK;}
CohStatus coh_live_choose_map(CohLive *s,unsigned i,uint64_t now){
 if(!s||i>1)return COH_INVALID;
 if(s->diagnostics.phase!=COH_LIVE_MAP_APPROVAL||!s->auth_consumed||!s->selected)return COH_STATE;
 if(now<s->clock_ms)return COH_INVALID;
 CohNetEndpoint endpoint=map_endpoint(s,i);
 if(!endpoint_valid(endpoint)){s->diagnostics.policy_rejections++;
 return COH_INVALID;}
 CohStatus status=s->config.approve_map(s->config.policy_context,endpoint,s->diagnostics.authentication_generation);
 if(status!=COH_OK){s->diagnostics.policy_rejections++;
 return status;}
 CohMapConfig config=s->config.map;config.udp.peer=endpoint;
 s->map=coh_map_client_create(&config);
 if(!s->map)return stop(s,COH_LIVE_FAILED,COH_LIMIT);
 CohMapAuthorization auth;memset(&auth,0,sizeof(auth));auth.authenticated=auth.endpoint_authorized=1;auth.selected_slot=s->pending.selected_slot;auth.selection_generation=s->diagnostics.selection_generation;auth.selected_dbid=s->pending.selected_dbid;auth.handoff=s->pending.map;auth.address_index=i;
 status=coh_map_client_begin(s->map,&auth,s->map_id,now);coh_auth_wipe(&auth,sizeof(auth));coh_db_wipe(&s->pending,sizeof(s->pending));
 if(status!=COH_OK)return stop(s,COH_LIVE_FAILED,status);
 s->clock_ms=now;
 s->diagnostics.map_approvals++;
 s->diagnostics.phase=COH_LIVE_MAP_CONNECTING;
 snapshot(s);
 return COH_OK;
}
CohStatus coh_live_service(CohLive *s,uint64_t now,CohCancel cancel){
 if(!s)return COH_INVALID;
 if(!active(s->diagnostics.phase))return s->diagnostics.phase==COH_LIVE_CANCELLED?COH_CANCELLED:COH_STATE;
 if(now<s->clock_ms)return COH_INVALID;
 s->clock_ms=now;
 if(cancel.poll&&cancel.poll(cancel.context)){coh_live_cancel(s);
 return COH_CANCELLED;}
 CohStatus status=COH_OK;
 if(s->diagnostics.phase==COH_LIVE_AUTHENTICATING||s->diagnostics.phase==COH_LIVE_SHARDS_READY){
  status=coh_login_service(s->login,now,(CohCancel){0});
 CohLoginDiagnostics auth={0};coh_login_diagnostics(s->login,&auth);
  if(status!=COH_OK){CohLivePhase phase=auth.state==COH_LOGIN_TIMED_OUT?COH_LIVE_TIMED_OUT:status==COH_UNSUPPORTED?COH_LIVE_UNSUPPORTED:COH_LIVE_FAILED;
 return stop(s,phase,status);}
  if(auth.state==COH_LOGIN_SHARDS_READY)s->diagnostics.phase=COH_LIVE_SHARDS_READY;
  if(auth.state==COH_LOGIN_AUTHORIZED){status=begin_db(s,now);
 if(status!=COH_OK)return stop(s,COH_LIVE_FAILED,status);}
 }
 if(s->db){CohDbSessionPhase phase=coh_db_session_phase(s->db);
  if(phase>=COH_DB_CONNECTING&&phase<=COH_DB_DISCONNECTING){status=coh_db_session_service(s->db,now,(CohCancel){0});phase=coh_db_session_phase(s->db);
 if(status!=COH_OK)return stop(s,phase==COH_DB_TIMED_OUT?COH_LIVE_TIMED_OUT:COH_LIVE_FAILED,status);}
  if((phase==COH_DB_FAILED||phase==COH_DB_TIMED_OUT||phase==COH_DB_CANCELLED)||(phase==COH_DB_CLOSED&&!s->pending.selection_generation&&!s->map))return stop(s,phase==COH_DB_TIMED_OUT?COH_LIVE_TIMED_OUT:COH_LIVE_FAILED,COH_STATE);
  if(phase==COH_DB_CHARACTERS)s->diagnostics.phase=COH_LIVE_CHARACTERS_READY;
  if(phase==COH_DB_HANDOFF_READY){if(!s->selected||!s->auth_consumed)return stop(s,COH_LIVE_FAILED,COH_STATE);status=coh_db_session_take_handoff(s->db,&s->pending);
 if(status!=COH_OK)return stop(s,COH_LIVE_FAILED,status);
 if(s->pending.selected_slot!=s->selected_slot||!s->pending.selection_generation||!s->pending.selected_dbid||
    s->pending.selected_dbid>INT32_MAX||s->pending.selected_dbid!=s->pending.map.link_id)return stop(s,COH_LIVE_FAILED,COH_INVALID);
 s->diagnostics.phase=COH_LIVE_MAP_APPROVAL;}
 }
 if(s->map){status=coh_map_client_service(s->map,now,(CohCancel){0});
 CohMapDiagnostics map={0};coh_map_client_diagnostics(s->map,&map);
  if(map.phase==COH_MAP_SCENE_INCOMPLETE&&status==COH_UNSUPPORTED){s->diagnostics.phase=COH_LIVE_SCENE_INCOMPLETE;
 s->diagnostics.last_status=COH_UNSUPPORTED;
 snapshot(s);
 return COH_UNSUPPORTED;}
  if(status!=COH_OK)return stop(s,map.phase==COH_MAP_TIMED_OUT?COH_LIVE_TIMED_OUT:COH_LIVE_FAILED,status);
  if(map.phase==COH_MAP_CLOSED||map.phase==COH_MAP_FAILED)return stop(s,COH_LIVE_FAILED,COH_STATE);
  if(map.phase==COH_MAP_SCENE_INCOMPLETE)s->diagnostics.phase=COH_LIVE_SCENE_INCOMPLETE;
 }
 snapshot(s);
 return COH_OK;
}
void coh_live_suspend(CohLive *s){if(s){if(s->login)coh_login_suspend(s->login);
 if(s->db)coh_db_session_suspend(s->db);
 if(s->map)coh_map_client_suspend(s->map);
 forget(s);
 s->diagnostics.phase=COH_LIVE_SUSPENDED;
 s->diagnostics.suspends++;
 snapshot(s);}}
void coh_live_cancel(CohLive *s){if(s){if(s->login)coh_login_cancel(s->login);
 if(s->db)coh_db_session_cancel(s->db);
 if(s->map)coh_map_client_close(s->map);
 forget(s);
 s->diagnostics.phase=COH_LIVE_CANCELLED;
 s->diagnostics.cancellations++;
 snapshot(s);}}
void coh_live_close(CohLive *s){if(s){close_modules(s);
 s->diagnostics.phase=COH_LIVE_CLOSED;}}
void coh_live_diagnostics(const CohLive *s,CohLiveDiagnostics *out){if(s&&out)*out=s->diagnostics;}
