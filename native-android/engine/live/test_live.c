#define _POSIX_C_SOURCE 200809L
#ifdef COH_LIVE_CONTRACT_TEST
#define coh_login_create fixture_login_create
#define coh_login_destroy fixture_login_destroy
#define coh_login_begin fixture_login_begin
#define coh_login_service fixture_login_service
#define coh_login_shards fixture_login_shards
#define coh_login_choose fixture_login_choose
#define coh_login_authorization fixture_login_authorization
#define coh_login_close fixture_login_close
#define coh_login_suspend fixture_login_suspend
#define coh_login_cancel fixture_login_cancel
#define coh_login_diagnostics fixture_login_diagnostics
#define coh_db_session_create fixture_db_create
#define coh_db_session_destroy fixture_db_destroy
#define coh_db_session_begin fixture_db_begin
#define coh_db_session_service fixture_db_service
#define coh_db_session_players fixture_db_players
#define coh_db_session_choose fixture_db_choose
#define coh_db_session_take_handoff fixture_db_take
#define coh_db_session_suspend fixture_db_suspend
#define coh_db_session_cancel fixture_db_cancel
#define coh_db_session_phase fixture_db_phase
#define coh_db_session_diagnostics fixture_db_diagnostics
#define coh_map_client_create fixture_map_create
#define coh_map_client_destroy fixture_map_destroy
#define coh_map_client_begin fixture_map_begin
#define coh_map_client_service fixture_map_service
#define coh_map_client_suspend fixture_map_suspend
#define coh_map_client_close fixture_map_close
#define coh_map_client_diagnostics fixture_map_diagnostics
#include "coh_live.c"
#else
#include "coh_live.h"
#endif
#include <arpa/inet.h>
#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
static unsigned checks,scenarios;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"live owner test line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
static CohLiveDiagnostics diagnostics(CohLive *s){CohLiveDiagnostics d;memset(&d,0,sizeof(d));coh_live_diagnostics(s,&d);return d;}
static unsigned descriptors(void){DIR *d=opendir("/proc/self/fd");CHECK(d);unsigned n=0;while(readdir(d))n++;CHECK(!closedir(d));return n;}
static CohNetEndpoint expected_map={{127,0,0,2},7002};static unsigned policy_calls;static int policy_permits=1;
static CohStatus map_policy(void *context,CohNetEndpoint e,uint32_t generation){CHECK(context==&policy_calls);CHECK(generation);policy_calls++;CHECK(!memcmp(e.address,expected_map.address,4)&&e.port==expected_map.port);return policy_permits?COH_OK:COH_STATE;}
static CohLiveConfig config(void){
 CohLiveConfig c;memset(&c,0,sizeof(c));c.login=coh_login_default_config(coh_auth_openssl_provider());c.authorized_auth=(CohNetEndpoint){{127,0,0,1},7001};c.db.transport.link=coh_net_default_config();c.db.transport.peer=(CohNetEndpoint){{127,0,0,1},7000};c.db.transport.receive_budget=8;c.db.request_timeout_ms=5000;c.map.udp.link=coh_net_default_config();c.map.udp.receive_budget=8;c.map.application_timeout_ms=5000;c.map.message_budget=8;c.approve_map=map_policy;c.policy_context=&policy_calls;return c;
}
static CohDbLogin login_policy(void){CohDbLogin p;memset(&p,0,sizeof(p));p.protocol_version=COH_DB_PROTOCOL_VERSION;strcpy(p.patch_version,"source-authorized-fixture");strcpy(p.system_spec,"Disabled");p.executable_checksum[0]=7;return p;}
static int cancel_now(void *p){(void)p;return 1;}
#ifdef COH_LIVE_CONTRACT_TEST
/* These scripted component adapters test OWNER transitions only. No socket,
 * authentication, server or live-world result is inferred from them. */
struct CohLogin {CohLoginState state;unsigned opened,closed;};struct CohDbSession {CohDbSessionPhase phase;unsigned opened,closed;};struct CohMapClient {CohMapPhase phase;unsigned opened,closed;};
static struct CohLogin auth_state;static struct CohDbSession db_state;static struct CohMapClient map_state;
static CohLoginState next_auth=COH_LOGIN_WAIT_HELLO;static CohStatus auth_result=COH_OK,map_result=COH_OK;
static CohDbSessionPhase next_db=COH_DB_CONNECTING;static CohMapPhase next_map=COH_MAP_NET_CONNECTING;
static CohNetEndpoint fixture_shard={{127,0,0,1},7000};static unsigned db_begins,map_begins,login_begins,db_takes;
static CohDbLogin recorded_policy;static CohDbAuthReceipt recorded_receipt;static CohMapAuthorization recorded_map;
static int db_create_fail,map_create_fail,bad_slot,bad_dbid;
CohLogin *coh_login_create(const CohLoginConfig *c){(void)c;memset(&auth_state,0,sizeof(auth_state));return &auth_state;}
void coh_login_destroy(CohLogin *s){(void)s;}
CohStatus coh_login_begin(CohLogin *s,CohNetEndpoint e,const char *name,const char *password,uint32_t subscription,uint16_t flags,uint64_t now){(void)subscription;(void)flags;(void)now;CHECK(e.port==7001&&name&&password);s->state=COH_LOGIN_WAIT_HELLO;s->opened++;login_begins++;return COH_OK;}
CohStatus coh_login_service(CohLogin *s,uint64_t now,CohCancel cancel){(void)now;(void)cancel;s->state=next_auth;return auth_result;}
CohStatus coh_login_shards(const CohLogin *s,CohAuthShards *out){(void)s;memset(out,0,sizeof(*out));out->count=1;out->shards[0].id=1;memcpy(out->shards[0].ipv4,fixture_shard.address,4);out->shards[0].port=fixture_shard.port;return COH_OK;}
CohStatus coh_login_choose(CohLogin *s,uint8_t id,uint64_t now){(void)now;CHECK(id==1);s->state=COH_LOGIN_WAIT_PLAY;return COH_OK;}
CohStatus coh_login_authorization(const CohLogin *s,CohLoginAuthorization *a){CHECK(s->state==COH_LOGIN_AUTHORIZED);memset(a,0,sizeof(*a));strcpy(a->account_name,"fixture");a->play.user_id=42;a->play.game_key=0x12345678;a->play.shard_id=1;memcpy(a->shard.ipv4,fixture_shard.address,4);a->shard.port=fixture_shard.port;return COH_OK;}
void coh_login_close(CohLogin *s){s->state=COH_LOGIN_CLOSED;s->closed=s->opened;}
void coh_login_suspend(CohLogin *s){s->state=COH_LOGIN_SUSPENDED;s->closed=s->opened;}
void coh_login_cancel(CohLogin *s){s->state=COH_LOGIN_CANCELLED;s->closed=s->opened;}
void coh_login_diagnostics(const CohLogin *s,CohLoginDiagnostics *d){memset(d,0,sizeof(*d));d->state=s->state;d->sockets_opened=s->opened;d->sockets_closed=s->closed;}
CohDbSession *coh_db_session_create(const CohDbSessionConfig *c){CHECK(c->transport.key_exchange==coh_session_key_exchange);CHECK(c->transport.key_context==coh_auth_openssl_provider());memset(&db_state,0,sizeof(db_state));return db_create_fail?NULL:&db_state;}
void coh_db_session_destroy(CohDbSession *s){(void)s;}
CohStatus coh_db_session_begin(CohDbSession *s,const CohDbLogin *p,const CohDbAuthReceipt *a,uint32_t id,uint64_t now){(void)now;CHECK(id&&a->verified==1&&a->generation);recorded_policy=*p;recorded_receipt=*a;s->phase=COH_DB_CONNECTING;s->opened++;db_begins++;return COH_OK;}
CohStatus coh_db_session_service(CohDbSession *s,uint64_t now,CohCancel cancel){(void)now;(void)cancel;s->phase=next_db;if(next_db==COH_DB_CLOSED)s->closed=s->opened;return COH_OK;}
CohStatus coh_db_session_players(const CohDbSession *s,CohDbPlayers *out){CHECK(s->phase==COH_DB_CHARACTERS);memset(out,0,sizeof(*out));out->max_slots=1;out->selectable_count=1;out->players[0].wire_slot=0;strcpy(out->players[0].name,"fixture-character");memset(out->auth_user_data,0x6b,sizeof(out->auth_user_data));return COH_OK;}
CohStatus coh_db_session_choose(CohDbSession *s,uint32_t slot,uint32_t ip,uint32_t location,uint64_t now){(void)ip;(void)location;(void)now;CHECK(s->phase==COH_DB_CHARACTERS);if(slot)return COH_STATE;s->phase=COH_DB_WAIT_MAP;return COH_OK;}
CohStatus coh_db_session_take_handoff(CohDbSession *s,CohDbSessionHandoff *out){CHECK(s->phase==COH_DB_HANDOFF_READY);memset(out,0,sizeof(*out));out->map=(CohAuthMapHandoff){23,1,{0x0100007f,0x0200007f},77,7002,7003};out->selection_generation=1;out->selected_slot=bad_slot?2:0;out->selected_dbid=bad_dbid==1?999:bad_dbid==2?0:bad_dbid==3?0x80000000u:23;s->phase=COH_DB_DISCONNECTING;db_takes++;return COH_OK;}
void coh_db_session_suspend(CohDbSession *s){s->phase=COH_DB_SUSPENDED;s->closed=s->opened;}
void coh_db_session_cancel(CohDbSession *s){s->phase=COH_DB_CANCELLED;s->closed=s->opened;}
CohDbSessionPhase coh_db_session_phase(const CohDbSession *s){return s->phase;}
void coh_db_session_diagnostics(const CohDbSession *s,CohDbSessionDiagnostics *out){memset(out,0,sizeof(*out));out->phase=s->phase;out->transport.sockets_opened=s->opened;out->transport.sockets_closed=s->closed;}
CohMapClient *coh_map_client_create(const CohMapConfig *c){CHECK(c->udp.key_exchange==coh_session_key_exchange);CHECK(c->udp.key_context==coh_auth_openssl_provider());CHECK(!memcmp(c->udp.peer.address,expected_map.address,4)&&c->udp.peer.port==expected_map.port);memset(&map_state,0,sizeof(map_state));return map_create_fail?NULL:&map_state;}
void coh_map_client_destroy(CohMapClient *s){(void)s;}
CohStatus coh_map_client_begin(CohMapClient *s,const CohMapAuthorization *a,uint32_t id,uint64_t now){(void)now;CHECK(id);recorded_map=*a;s->phase=COH_MAP_NET_CONNECTING;s->opened++;map_begins++;return COH_OK;}
CohStatus coh_map_client_service(CohMapClient *s,uint64_t now,CohCancel cancel){(void)now;(void)cancel;s->phase=next_map;return map_result;}
void coh_map_client_suspend(CohMapClient *s){s->phase=COH_MAP_SUSPENDED;s->closed=s->opened;}
void coh_map_client_close(CohMapClient *s){s->phase=COH_MAP_CLOSED;s->closed=s->opened;}
void coh_map_client_diagnostics(const CohMapClient *s,CohMapDiagnostics *d){memset(d,0,sizeof(*d));d->phase=s->phase;d->udp.sockets_opened=s->opened;d->udp.sockets_closed=s->closed;}
static CohLive *begin_fixture(void){CohLiveConfig c=config();CohLive *s=coh_live_create(&c);CHECK(s);CohDbLogin p=login_policy();next_auth=COH_LOGIN_WAIT_HELLO;next_db=COH_DB_CONNECTING;next_map=COH_MAP_NET_CONNECTING;auth_result=map_result=COH_OK;CHECK(coh_live_begin(s,&p,"fixture","disposable",0,0,101,102,100)==COH_OK);return s;}
static void to_db(CohLive *s){
 next_auth=COH_LOGIN_SHARDS_READY;CHECK(coh_live_service(s,101,(CohCancel){0})==COH_OK);CHECK(diagnostics(s).phase==COH_LIVE_SHARDS_READY);CHECK(coh_live_choose_shard(s,2,101)==COH_INVALID);
 fixture_shard.port=7999;CHECK(coh_live_choose_shard(s,1,101)==COH_INVALID);fixture_shard.port=7000;fixture_shard.address[3]=2;CHECK(coh_live_choose_shard(s,1,101)==COH_INVALID);fixture_shard.address[3]=1;
 CHECK(coh_live_choose_shard(s,1,102)==COH_OK);next_auth=COH_LOGIN_AUTHORIZED;CHECK(coh_live_service(s,103,(CohCancel){0})==COH_OK);CHECK(diagnostics(s).phase==COH_LIVE_DB_CONNECTING);CHECK(recorded_receipt.verified==1&&recorded_receipt.user_id==42&&recorded_receipt.game_cookie==0x12345678&&!strcmp(recorded_receipt.account,"fixture"));CHECK(!strcmp(recorded_policy.account,"fixture")&&recorded_policy.user_id==42&&recorded_policy.cookie==0x12345678&&recorded_policy.no_version_check==0&&recorded_policy.executable_checksum[0]==7);
}
static void to_handoff(CohLive *s){to_db(s);next_db=COH_DB_CHARACTERS;CHECK(coh_live_service(s,104,(CohCancel){0})==COH_OK);CohLiveCharacters list;CHECK(coh_live_characters(s,&list)==COH_OK&&list.count==1&&list.selectable_count==1&&!strcmp(list.players[0].name,"fixture-character"));CHECK(coh_live_choose_character(s,1,0,0,105)==COH_STATE);CHECK(coh_live_choose_character(s,0,0,0,105)==COH_OK);CHECK(coh_live_choose_character(s,0,0,0,105)==COH_STATE);next_db=COH_DB_HANDOFF_READY;CHECK(coh_live_service(s,106,(CohCancel){0})==COH_OK);CHECK(diagnostics(s).phase==COH_LIVE_MAP_APPROVAL);next_db=COH_DB_CLOSED;}
static void success(void){
 CohLive *s=begin_fixture();CHECK(coh_live_choose_map(s,1,100)==COH_STATE);to_handoff(s);CohNetEndpoint peers[2];CHECK(coh_live_map_candidates(s,peers)==COH_OK&&peers[0].address[3]==1&&peers[1].address[3]==2&&peers[1].port==7002);policy_permits=0;unsigned before=map_begins;CHECK(coh_live_choose_map(s,1,107)==COH_STATE&&map_begins==before);policy_permits=1;CHECK(coh_live_choose_map(s,2,107)==COH_INVALID);CHECK(coh_live_choose_map(s,1,107)==COH_OK);CHECK(recorded_map.authenticated==1&&recorded_map.endpoint_authorized==1&&recorded_map.selected_slot==0&&recorded_map.selected_dbid==23&&recorded_map.handoff.cookie==77&&recorded_map.address_index==1&&recorded_map.selection_generation==1);CHECK(coh_live_choose_map(s,1,107)==COH_STATE);
 next_map=COH_MAP_SCENE_INCOMPLETE;map_result=COH_UNSUPPORTED;CHECK(coh_live_service(s,108,(CohCancel){0})==COH_UNSUPPORTED&&diagnostics(s).phase==COH_LIVE_SCENE_INCOMPLETE);CHECK(diagnostics(s).authentication_generation==1&&diagnostics(s).auth_receipts==1);coh_live_suspend(s);CHECK(diagnostics(s).phase==COH_LIVE_SUSPENDED);CHECK(diagnostics(s).opened_sockets==3&&diagnostics(s).closed_sockets==3);CHECK(coh_live_map_candidates(s,peers)==COH_STATE);CHECK(coh_live_choose_map(s,1,109)==COH_STATE);CHECK(coh_live_service(s,109,(CohCancel){0})==COH_STATE);
 CohDbLogin p=login_policy();CHECK(coh_live_begin(s,&p,"fixture","fresh",0,0,101,103,109)==COH_INVALID);CHECK(coh_live_begin(s,&p,"fixture","fresh",0,0,103,104,109)==COH_OK);next_auth=COH_LOGIN_AUTHORIZED;next_db=COH_DB_CONNECTING;CHECK(coh_live_service(s,110,(CohCancel){0})==COH_OK&&recorded_receipt.generation==2);CHECK(coh_live_service(s,111,(CohCancel){cancel_now,NULL})==COH_CANCELLED);CHECK(coh_live_choose_character(s,0,0,0,111)==COH_STATE);CHECK(diagnostics(s).opened_sockets==5&&diagnostics(s).closed_sockets==5);CHECK(coh_live_begin(s,&p,"fixture","fresh",0,0,101,102,112)==COH_INVALID);coh_live_destroy(s);scenarios++;
}
static void failures(void){
 for(unsigned i=0;i<10;i++){CohLive *s=begin_fixture();if(i<3){next_auth=i==0?COH_LOGIN_FAILED:i==1?COH_LOGIN_TIMED_OUT:COH_LOGIN_UNSUPPORTED;auth_result=i==2?COH_UNSUPPORTED:COH_IO;CHECK(coh_live_service(s,101,(CohCancel){0})!=COH_OK);CHECK(!diagnostics(s).auth_receipts);}
  if(i==3){db_create_fail=1;next_auth=COH_LOGIN_AUTHORIZED;CHECK(coh_live_service(s,101,(CohCancel){0})==COH_LIMIT);db_create_fail=0;}
  if(i==4||i==5||i>=8){to_db(s);next_db=COH_DB_CHARACTERS;CHECK(coh_live_service(s,104,(CohCancel){0})==COH_OK);CHECK(coh_live_choose_character(s,0,0,0,105)==COH_OK);bad_slot=i==4;bad_dbid=i==5?1:i==8?2:i==9?3:0;next_db=COH_DB_HANDOFF_READY;CHECK(coh_live_service(s,106,(CohCancel){0})==COH_INVALID);bad_slot=bad_dbid=0;}
  if(i==6){to_handoff(s);map_create_fail=1;CHECK(coh_live_choose_map(s,1,107)==COH_LIMIT);map_create_fail=0;}
  if(i==7){to_handoff(s);CHECK(coh_live_choose_map(s,1,107)==COH_OK);next_db=COH_DB_TIMED_OUT;CHECK(coh_live_service(s,108,(CohCancel){0})==COH_STATE);CHECK(diagnostics(s).phase==COH_LIVE_TIMED_OUT&&diagnostics(s).map_phase==COH_MAP_CLOSED);}
  CHECK(diagnostics(s).phase>=COH_LIVE_FAILED);coh_live_destroy(s);scenarios++;
 }
}
int main(void){unsigned before=descriptors();CohLiveConfig c=config();CHECK(!coh_live_create(NULL));c.approve_map=NULL;CHECK(!coh_live_create(&c));CohLive *s=begin_fixture();CohDbLogin p=login_policy();CHECK(coh_live_begin(s,&p,"fixture","fresh",0,0,103,104,101)==COH_STATE);coh_live_close(s);p.cookie=3;CHECK(coh_live_begin(s,&p,"fixture","fresh",0,0,103,104,101)==COH_INVALID);p.cookie=0;p.user_id=3;CHECK(coh_live_begin(s,&p,"fixture","fresh",0,0,103,104,101)==COH_INVALID);coh_live_destroy(s);success();failures();CHECK(descriptors()==before);printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"synthetic_component_adapters\":true,\"real_authenticated_session\":false,\"live_world\":false}\n",checks,scenarios);return 0;}
#else
/* All real modules: authorized local TCP startup, cancellation, suspend and
 * timeout. The peer sends no AuthServer success; no receipt can be minted. */
int main(void){
 unsigned before=descriptors();int fd=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);CHECK(fd>=0);struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);CHECK(!bind(fd,(struct sockaddr*)&a,sizeof(a)));CHECK(!listen(fd,4));socklen_t size=sizeof(a);CHECK(!getsockname(fd,(struct sockaddr*)&a,&size));CHECK(!fcntl(fd,F_SETFL,O_NONBLOCK));
 for(unsigned i=0;i<3;i++){CohLiveConfig c=config();c.authorized_auth.port=ntohs(a.sin_port);c.login.connect_timeout_ms=100;c.login.reply_timeout_ms=100;CohLive *s=coh_live_create(&c);CHECK(s);CohDbLogin p=login_policy();CHECK(coh_live_begin(s,&p,"fixture","disposable",0,0,101,102,100)==COH_OK);CHECK(coh_live_service(s,101,(CohCancel){0})==COH_OK);int peer=accept(fd,NULL,NULL);CHECK(peer>=0);CHECK(!diagnostics(s).auth_receipts);
  if(i==0){coh_live_suspend(s);CHECK(diagnostics(s).phase==COH_LIVE_SUSPENDED);CHECK(coh_live_service(s,102,(CohCancel){0})==COH_STATE);}
  if(i==1){CHECK(coh_live_service(s,102,(CohCancel){cancel_now,NULL})==COH_CANCELLED);CHECK(diagnostics(s).phase==COH_LIVE_CANCELLED);}
  if(i==2){CHECK(coh_live_service(s,1000,(CohCancel){0})==COH_STATE);CHECK(diagnostics(s).phase==COH_LIVE_TIMED_OUT);}
  CHECK(diagnostics(s).opened_sockets==1&&diagnostics(s).closed_sockets==1);CHECK(!diagnostics(s).auth_receipts&&diagnostics(s).authentication_generation==0);CHECK(!close(peer));coh_live_destroy(s);scenarios++;
 }CHECK(!close(fd));CHECK(descriptors()==before);printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"actual_os_tcp\":true,\"full_auth_db_map_chain\":false,\"real_authenticated_session\":false,\"descriptor_cleanup\":true}\n",checks,scenarios);return 0;
}
#endif
