/* Synthetic API-composition controls. No TCP/UDP/crypto/server is executed. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
static unsigned checks,scenarios;
#define CHECK(e) do { checks++;if(!(e)){fprintf(stderr,"control:%u:%s\n",__LINE__,#e);exit(1);} } while(0)
typedef struct {void *p;size_t size;} Allocation;
static Allocation allocations[8];
static unsigned alloc_calls,alloc_fail,live_allocations,allocation_cases;
static int zeroed(const void *p,size_t n) {
    const unsigned char *v=p;unsigned sum=0;for(size_t i=0;i<n;i++)sum|=v[i];return !sum;
}
static void *ad_calloc(size_t count,size_t size) {
    alloc_calls++;if(alloc_calls==alloc_fail)return NULL;
    if(size&&count>SIZE_MAX/size)return NULL;
    void *p=calloc(count,size);CHECK(p!=NULL);
    for(unsigned i=0;i<8;i++)if(!allocations[i].p){allocations[i]=(Allocation){p,count*size};live_allocations++;return p;}
    CHECK(0);return NULL;
}
static void ad_free(void *p) {
    if(!p)return;
    for(unsigned i=0;i<8;i++)if(allocations[i].p==p) {
        CHECK(zeroed(p,allocations[i].size));allocations[i]=(Allocation){0};live_allocations--;free(p);return;
    }
    CHECK(0);
}
#define calloc ad_calloc
#define free ad_free
#include "auth_db_development_owner.c"
#undef calloc
#undef free

struct CohLogin {CohLoginDiagnostics d;unsigned step,chosen;};
struct CohDbSession {CohDbSessionDiagnostics d;};
enum { GOOD,AUTH_BEGIN_FAIL,AUTH_SERVICE_FAIL,AUTH_HOLD,AUTH_BAD_STATE,
    SHARDS_FAIL,SHARDS_ZERO,SHARDS_TWO,SHARD_ID,SHARD_DOWN,SHARD_IP,SHARD_PORT,
    AUTH_PROTOCOL,AUTH_PENDING,AUTH_BUFFERED,AUTH_PASSWORD,AUTH_REMOTE,AUTH_ERRNO,
    CHOOSE_FAIL,GRANT_FAIL,GRANT_PROTOCOL,GRANT_SHARD,GRANT_UID_ZERO,GRANT_UID_WRONG,
    GRANT_COOKIE,GRANT_ACCOUNT_EMPTY,GRANT_ACCOUNT_UNTERMINATED,GRANT_ENDPOINT,
    DB_BEGIN_FAIL,DB_SERVICE_FAIL,DB_PARSE_INVALID,DB_PARSE_UNSUPPORTED,DB_KEY_CALLBACK,DB_HOLD,
    DB_QUEUE,DB_UNSUPPORTED,DB_TWO_LISTS,DB_ZERO_LISTS,DB_CHOICE,DB_HANDOFF,DB_LOCAL,DB_IDENTITY,
    DB_GENERATION,DB_SELECTION,DB_TWO_LOGINS,DB_BAD_PHASE,PLAYERS_FAIL,
    LIST_UID,LIST_ZERO,LIST_OVERSIZE,LIST_BASE_ZERO,LIST_BASE_HIGH,LIST_SELECTABLE,
    LIST_INDEX,LIST_NONEMPTY,LIST_LOCK,LIST_VISITOR,LIST_INVALID,MODE_COUNT };
static struct {
    unsigned mode,auth_creates,auth_begins,auth_services,auth_choices,auth_getters;
    unsigned auth_closes,auth_destroys,db_creates,db_begins,db_services,db_getters;
    unsigned db_cancels,db_destroys,polls,cancel_at,reentry,key_callbacks;
    CohNetKeyExchange exchange;
    void *exchange_context;
    CohAuthDbDevelopmentOwner *owner;
} g;
static CohStatus fake_pair(void *c,uint8_t a[64],uint8_t b[64]){(void)c;(void)a;(void)b;CHECK(0);return COH_UNSUPPORTED;}
static CohStatus fake_shared(void *c,const uint8_t a[64],const uint8_t b[64],uint8_t d[64]){(void)c;(void)a;(void)b;(void)d;CHECK(0);return COH_UNSUPPORTED;}
static CohStatus fake_md5(void *c,CohBytes b,uint8_t d[16]){(void)c;(void)b;(void)d;CHECK(0);return COH_UNSUPPORTED;}
static CohStatus fake_sha(void *c,CohBytes b,uint8_t d[64]){(void)c;(void)b;(void)d;CHECK(0);return COH_UNSUPPORTED;}
static CohStatus fake_rsa(void *c,CohBytes a,CohBytes b,CohBytes p,uint8_t *o,size_t n,size_t *s){(void)c;(void)a;(void)b;(void)p;(void)o;(void)n;(void)s;CHECK(0);return COH_UNSUPPORTED;}
static CohAuthCrypto provider={NULL,fake_pair,fake_shared,fake_md5,fake_sha,fake_rsa};
static CohAuthDbDevelopmentConfig configuration(void) {
    CohAuthDbDevelopmentConfig c={0};c.auth_endpoint=(CohNetEndpoint){{127,0,0,1},23456};
    c.crypto=&provider;c.connect_id=0x4312a87fu;
    for(unsigned i=0;i<16;i++)c.executable_checksum[i]=(uint8_t)(i+1);
    return c;
}
void coh_auth_wipe(void *p,size_t n){volatile unsigned char *v=p;if(v)while(n--)*v++=0;}
void coh_db_wipe(void *p,size_t n){coh_auth_wipe(p,n);}
CohNetConfig coh_net_default_config(void){return (CohNetConfig){5,100,8,10000,30000,10000};}
static void reentry_controls(void);
CohStatus coh_session_key_exchange(void *c,const uint8_t p[64],uint8_t o[64],CohBlowfish *b) {
    (void)p;(void)o;(void)b;CHECK(g.mode==DB_KEY_CALLBACK&&c==&provider);
    g.key_callbacks++;reentry_controls();return COH_UNSUPPORTED;
}
CohLoginConfig coh_login_default_config(const CohAuthCrypto *p){return (CohLoginConfig){p,10000,15000,4};}
CohLogin *coh_login_create(const CohLoginConfig *c) {
    g.auth_creates++;CHECK(c->crypto==&provider&&c->connect_timeout_ms==3000&&c->reply_timeout_ms==10000&&c->receive_budget==4);
    return ad_calloc(1,sizeof(CohLogin));
}
CohStatus coh_login_begin(CohLogin *s,CohNetEndpoint e,const char *a,const char *p,uint32_t subscription,uint16_t flags,uint64_t now) {
    g.auth_begins++;CHECK(e.port==23456&&loopback(e)&&!subscription&&!flags&&now==100);
    if(g.mode==AUTH_BEGIN_FAIL||!a||!p||strcmp(a,"fixture")||strcmp(p,"pw"))return COH_INVALID;
    s->d.state=COH_LOGIN_WAIT_HELLO;s->d.sockets_opened=1;return COH_OK;
}
CohStatus coh_login_service(CohLogin *s,uint64_t now,CohCancel cancel) {
    (void)now;g.auth_services++;
    if(cancel.poll&&cancel.poll(cancel.context)){s->d.state=COH_LOGIN_CANCELLED;return COH_CANCELLED;}
    if(g.mode==AUTH_SERVICE_FAIL){s->d.state=COH_LOGIN_FAILED;return COH_IO;}
    if(g.mode==AUTH_HOLD)return COH_OK;
    if(g.mode==AUTH_BAD_STATE){s->d.state=COH_LOGIN_CLOSED;return COH_OK;}
    s->step++;s->d.protocol=g.mode==AUTH_PROTOCOL?COH_AUTH_OUROBOROS1:COH_AUTH_OUROBOROS2;
    s->d.received_frames=s->step==1?3:4;
    s->d.state=s->step==1?COH_LOGIN_SHARDS_READY:COH_LOGIN_AUTHORIZED;
    s->d.pending_send_bytes=g.mode==AUTH_PENDING;
    s->d.buffered_receive_bytes=g.mode==AUTH_BUFFERED;
    s->d.password_retained=g.mode==AUTH_PASSWORD;
    s->d.remote_failure_command=g.mode==AUTH_REMOTE;
    s->d.last_system_error=g.mode==AUTH_ERRNO;
    return COH_OK;
}
static CohAuthShard shard(void) {
    CohAuthShard s={0};s.id=1;s.status=1;s.port=7000;s.ipv4[0]=127;s.ipv4[3]=1;return s;
}
CohStatus coh_login_shards(const CohLogin *s,CohAuthShards *out) {
    CHECK(s->d.state==COH_LOGIN_SHARDS_READY);
    if(g.mode==SHARDS_FAIL)return COH_INVALID;
    CohAuthShards v={0};v.count=g.mode==SHARDS_ZERO?0:(g.mode==SHARDS_TWO?2:1);v.shards[0]=shard();
    if(g.mode==SHARD_ID)v.shards[0].id=2;
    if(g.mode==SHARD_DOWN)v.shards[0].status=0;
    if(g.mode==SHARD_IP)v.shards[0].ipv4[3]=2;
    if(g.mode==SHARD_PORT)v.shards[0].port=7001;
    *out=v;return COH_OK;
}
CohStatus coh_login_choose(CohLogin *s,uint8_t id,uint64_t now) {
    (void)now;g.auth_choices++;CHECK(id==1&&s->d.state==COH_LOGIN_SHARDS_READY);
    if(g.mode==CHOOSE_FAIL)return COH_IO;
    s->chosen=1;s->d.state=COH_LOGIN_WAIT_PLAY;return COH_OK;
}
CohStatus coh_login_authorization(const CohLogin *s,CohLoginAuthorization *out) {
    g.auth_getters++;CHECK(s->chosen&&s->d.state==COH_LOGIN_AUTHORIZED);
    if(g.mode==GRANT_FAIL)return COH_STATE;
    CohLoginAuthorization a={0};a.protocol=COH_AUTH_OUROBOROS2;strcpy(a.account_name,"fixture");
    a.play=(CohAuthPlayOk){0x55667788u,900001u,1};a.shard=shard();
    if(g.mode==GRANT_PROTOCOL)a.protocol=COH_AUTH_GLOBAL;
    if(g.mode==GRANT_SHARD)a.play.shard_id=2;
    if(g.mode==GRANT_UID_ZERO)a.play.user_id=0;
    if(g.mode==GRANT_UID_WRONG)a.play.user_id=900002;
    if(g.mode==GRANT_COOKIE)a.play.game_key=0;
    if(g.mode==GRANT_ACCOUNT_EMPTY)a.account_name[0]=0;
    if(g.mode==GRANT_ACCOUNT_UNTERMINATED)memset(a.account_name,'x',sizeof(a.account_name));
    if(g.mode==GRANT_ENDPOINT)a.shard.port=7001;
    *out=a;coh_auth_wipe(&a,sizeof(a));return COH_OK;
}
void coh_login_diagnostics(const CohLogin *s,CohLoginDiagnostics *out){*out=s->d;}
void coh_login_close(CohLogin *s){g.auth_closes++;s->d.state=COH_LOGIN_CLOSED;s->d.sockets_closed=s->d.sockets_opened;}
void coh_login_destroy(CohLogin *s) {
    g.auth_destroys++;CHECK(!g.owner||!g.owner->d.complete_matching_list);
    coh_auth_wipe(s,sizeof(*s));ad_free(s);
}
CohDbSession *coh_db_session_create(const CohDbSessionConfig *c) {
    g.db_creates++;CHECK(c->transport.link.version==5&&c->transport.link.connect_timeout_ms==3000);
    CHECK(c->transport.link.idle_timeout_ms==10000&&c->transport.link.fragment_timeout_ms==10000);
    CHECK(loopback(c->transport.peer)&&c->transport.peer.port==7000&&loopback(c->transport.local)&&!c->transport.local.port);
    CHECK(c->transport.receive_budget==4&&c->transport.encryption_required==1&&c->transport.key_exchange==coh_session_key_exchange);
    CHECK(c->transport.key_context==&provider&&c->request_timeout_ms==10000&&!c->outbound_compressed);
    g.exchange=c->transport.key_exchange;g.exchange_context=c->transport.key_context;
    CHECK(g.owner&&g.owner->d.grant_consumed==1);
    return ad_calloc(1,sizeof(CohDbSession));
}
CohStatus coh_db_session_begin(CohDbSession *s,const CohDbLogin *l,const CohDbAuthReceipt *r,uint32_t id,uint64_t now) {
    (void)now;g.db_begins++;CohAuthDbDevelopmentConfig c=configuration();
    CHECK(g.owner->d.grant_consumed==1&&id==c.connect_id);
    CHECK(!strcmp(l->account,"fixture")&&!strcmp(r->account,l->account)&&l->user_id==900001&&r->user_id==l->user_id);
    CHECK(l->cookie==0x55667788u&&r->game_cookie==l->cookie&&r->verified==1&&r->generation==1);
    CHECK(l->protocol_version==20110614&&l->no_version_check==1&&!l->no_timeout&&!strcmp(l->patch_version,"dev:owned-auth-db-probe"));
    CHECK(!memcmp(l->executable_checksum,c.executable_checksum,16)&&zeroed(l->auth_user_data,128)&&!l->keyed_access_level);
    if(g.mode==DB_BEGIN_FAIL)return COH_IO;
    s->d.phase=COH_DB_CONNECTING;s->d.generation=1;s->d.server_identity_bound=1;return COH_OK;
}
CohStatus coh_db_session_service(CohDbSession *s,uint64_t now,CohCancel cancel) {
    (void)now;g.db_services++;
    if(cancel.poll&&cancel.poll(cancel.context)){s->d.phase=COH_DB_CANCELLED;return COH_CANCELLED;}
    if(g.mode==DB_SERVICE_FAIL){s->d.phase=COH_DB_FAILED;return COH_IO;}
    if(g.mode==DB_PARSE_INVALID){s->d.phase=COH_DB_FAILED;return COH_INVALID;}
    if(g.mode==DB_PARSE_UNSUPPORTED){s->d.phase=COH_DB_FAILED;return COH_UNSUPPORTED;}
    if(g.mode==DB_KEY_CALLBACK) {
        uint8_t p[64]={0},o[64]={0};CohBlowfish b={0};
        CohStatus status=g.exchange(g.exchange_context,p,o,&b);s->d.phase=COH_DB_FAILED;return status;
    }
    if(g.mode==DB_HOLD)return COH_OK;
    s->d.login_requests=1;
    if(g.db_services==1){s->d.phase=COH_DB_WAIT_PLAYERS;return COH_OK;}
    s->d.phase=COH_DB_CHARACTERS;s->d.player_lists=1;
    if(g.mode==DB_QUEUE)s->d.queue_updates=1;
    if(g.mode==DB_UNSUPPORTED)s->d.unsupported=1;
    if(g.mode==DB_TWO_LISTS)s->d.player_lists=2;
    if(g.mode==DB_ZERO_LISTS)s->d.player_lists=0;
    if(g.mode==DB_CHOICE)s->d.choices=1;
    if(g.mode==DB_HANDOFF)s->d.handoffs=1;
    if(g.mode==DB_LOCAL)s->d.local_development_auth=1;
    if(g.mode==DB_IDENTITY)s->d.server_identity_bound=0;
    if(g.mode==DB_GENERATION)s->d.generation=2;
    if(g.mode==DB_SELECTION)s->d.selection_generation=1;
    if(g.mode==DB_TWO_LOGINS)s->d.login_requests=2;
    if(g.mode==DB_BAD_PHASE)s->d.phase=COH_DB_WAIT_MAP;
    return COH_OK;
}
CohStatus coh_db_session_players(const CohDbSession *s,CohDbPlayers *out) {
    CHECK(s->d.phase==COH_DB_CHARACTERS);g.db_getters++;
    if(g.mode==PLAYERS_FAIL)return COH_STATE;
    CohDbPlayers p={0};p.user_id=900001;p.base_slots=p.max_slots=12;
    for(unsigned i=0;i<12;i++){p.players[i].wire_slot=i;p.players[i].empty=1;strcpy(p.players[i].name,"EMPTY");}
    if(g.mode==LIST_UID)p.user_id++;
    if(g.mode==LIST_ZERO)p.max_slots=0;
    if(g.mode==LIST_OVERSIZE)p.max_slots=65;
    if(g.mode==LIST_BASE_ZERO)p.base_slots=0;
    if(g.mode==LIST_BASE_HIGH)p.base_slots=13;
    if(g.mode==LIST_SELECTABLE)p.selectable_count=1;
    if(g.mode==LIST_INDEX)p.players[11].wire_slot=12;
    if(g.mode==LIST_NONEMPTY)p.players[11].empty=0;
    if(g.mode==LIST_LOCK)p.players[11].slot_lock=1;
    if(g.mode==LIST_VISITOR)p.players[11].visitor=1;
    if(g.mode==LIST_INVALID)p.players[11].invalid=1;
    *out=p;coh_db_wipe(&p,sizeof(p));return COH_OK;
}
void coh_db_session_diagnostics(const CohDbSession *s,CohDbSessionDiagnostics *out){*out=s->d;}
void coh_db_session_cancel(CohDbSession *s){g.db_cancels++;s->d.phase=COH_DB_CANCELLED;}
void coh_db_session_destroy(CohDbSession *s) {
    g.db_destroys++;CHECK(!g.owner->d.complete_matching_list&&g.owner->d.phase!=COH_AUTH_DB_DEV_COMPLETE);
    coh_db_wipe(s,sizeof(*s));ad_free(s);
}
static void reset(unsigned mode) {
    CHECK(!live_allocations);memset(&g,0,sizeof(g));g.mode=mode;
    alloc_calls=alloc_fail=0;scenarios++;
}
static CohAuthDbDevelopmentDiagnostics diagnostic(CohAuthDbDevelopmentOwner *x) {
    CohAuthDbDevelopmentDiagnostics d;memset(&d,0xa5,sizeof(d));
    CHECK(coh_auth_db_development_diagnostics(x,&d)==COH_OK);return d;
}
static void reentry_controls(void) {
        CohAuthDbDevelopmentOwner *saved=g.owner;
        CohAuthDbDevelopmentDiagnostics d,before;memset(&d,0xa5,sizeof(d));before=d;
        CHECK(coh_auth_db_development_begin(g.owner,"fixture","pw",100)==COH_STATE);
        CHECK(coh_auth_db_development_service(g.owner,101,(CohCancel){0})==COH_STATE);
        CHECK(coh_auth_db_development_timeout(g.owner)==COH_STATE);
        CHECK(coh_auth_db_development_cancel(g.owner)==COH_STATE);
        CHECK(coh_auth_db_development_close(g.owner)==COH_STATE);
        CHECK(coh_auth_db_development_destroy(&g.owner)==COH_STATE&&g.owner==saved);
        CHECK(coh_auth_db_development_diagnostics(g.owner,&d)==COH_STATE&&!memcmp(&d,&before,sizeof(d)));
}
static int poll_cancel(void *context) {
    CHECK(context==&g);g.polls++;
    if(g.reentry)reentry_controls();
    return g.cancel_at&&g.polls==g.cancel_at;
}
static CohAuthDbDevelopmentOwner *start(void) {
    CohAuthDbDevelopmentConfig c=configuration();g.owner=coh_auth_db_development_create(&c);CHECK(g.owner);
    CHECK(coh_auth_db_development_begin(g.owner,"fixture","pw",100)==COH_OK);return g.owner;
}
static CohStatus run(CohAuthDbDevelopmentOwner *x) {
    CohStatus status=COH_OK;
    for(unsigned i=0;i<6&&active(x);i++)status=coh_auth_db_development_service(x,101+i,(CohCancel){poll_cancel,&g});
    return status;
}
static void stable_terminal(CohAuthDbDevelopmentOwner *x) {
    CohAuthDbDevelopmentDiagnostics before=diagnostic(x),after;
    CHECK(coh_auth_db_development_begin(x,"fixture","pw",200)==COH_STATE);
    CHECK(coh_auth_db_development_service(x,200,(CohCancel){0})==COH_STATE);
    CHECK(coh_auth_db_development_cancel(x)==COH_STATE);
    CHECK(coh_auth_db_development_timeout(x)==COH_STATE);
    CHECK(coh_auth_db_development_close(x)==COH_OK);
    after=diagnostic(x);CHECK(!memcmp(&before,&after,sizeof(before)));
    CHECK(!x->auth&&!x->db&&before.controllers_destroyed);
    CHECK(coh_auth_db_development_destroy(&g.owner)==COH_OK&&!g.owner&&!live_allocations);
    CHECK(coh_auth_db_development_destroy(&g.owner)==COH_OK);
}
static void mode_case(unsigned mode) {
    reset(mode);CohAuthDbDevelopmentOwner *x=start();g.reentry=1;
    CohStatus status=run(x);CohAuthDbDevelopmentDiagnostics d=diagnostic(x);
    if(mode==GOOD) {
        CHECK(status==COH_OK&&d.phase==COH_AUTH_DB_DEV_COMPLETE&&d.complete_matching_list&&d.all_slots_empty_unlocked);
        CHECK(d.slots==12&&d.base_slots==12&&d.db_player_lists==1&&d.db_login_requests==1);
        CHECK(d.auth_phase==COH_LOGIN_AUTHORIZED&&d.db_phase==COH_DB_CHARACTERS);
        CHECK(d.auth_final_phase==COH_LOGIN_CLOSED&&d.db_final_phase==COH_DB_CANCELLED&&d.cleanup_cancel_close_used);
        CHECK(d.grant_consumed&&g.auth_choices==1&&g.auth_getters==1&&g.db_begins==1);
    } else if(mode==AUTH_HOLD||mode==DB_HOLD) {
        CHECK(status==COH_OK&&active(x));CHECK(coh_auth_db_development_timeout(x)==COH_STATE);
        d=diagnostic(x);CHECK(d.failure==COH_AUTH_DB_DEV_FAILURE_TIMEOUT);
    } else {
        CHECK(status!=COH_OK&&d.phase==COH_AUTH_DB_DEV_FAILED&&!d.complete_matching_list&&!d.all_slots_empty_unlocked);
        CHECK(!d.slots&&!d.base_slots&&!d.bonus_slots);
    }
    if(mode==DB_KEY_CALLBACK)CHECK(g.key_callbacks==1);
    d=diagnostic(x);CHECK(d.development_skip_requested&&!d.normal_version_admitted&&!d.checksum_reference_admitted);
    CHECK(!d.character_selected&&!d.map_handoff_verified&&!d.current_world_verified);
    CHECK(g.auth_creates==g.auth_destroys&&g.db_creates==g.db_destroys&&g.db_begins<=1&&g.auth_begins==1);
    stable_terminal(x);
}
static void null_and_config_controls(void) {
    reset(GOOD);CohAuthDbDevelopmentConfig good=configuration(),c=good;
    CHECK(!coh_auth_db_development_create(NULL));
    for(unsigned i=0;i<10;i++) {
        c=good;
        if(i==0)c.auth_endpoint.address[3]=2;
        if(i==1)c.auth_endpoint.port=19999;
        if(i==2)c.auth_endpoint.port=60000;
        if(i==3)c.connect_id=0;
        if(i==4)c.crypto=NULL;
        CohAuthCrypto p=provider;
        if(i==5)p.keypair=NULL;
        if(i==6)p.shared=NULL;
        if(i==7)p.md5=NULL;
        if(i==8)p.rsa_oaep_sha1=NULL;
        if(i==9)p.sha512=NULL;
        if(i>=5)c.crypto=&p;
        CHECK(!coh_auth_db_development_create(&c));
    }
    CHECK(coh_auth_db_development_begin(NULL,"fixture","pw",100)==COH_INVALID);
    CHECK(coh_auth_db_development_service(NULL,100,(CohCancel){0})==COH_INVALID);
    CHECK(coh_auth_db_development_timeout(NULL)==COH_INVALID&&coh_auth_db_development_cancel(NULL)==COH_INVALID);
    CHECK(coh_auth_db_development_close(NULL)==COH_INVALID&&coh_auth_db_development_destroy(NULL)==COH_INVALID);
    CHECK(coh_auth_db_development_diagnostics(NULL,NULL)==COH_INVALID&&!live_allocations);
}
static void alias_and_idle_controls(void) {
    reset(GOOD);CohAuthDbDevelopmentConfig c=configuration();g.owner=coh_auth_db_development_create(&c);CHECK(g.owner);
    CohAuthDbDevelopmentOwner *x=g.owner;CohAuthDbDevelopmentOwner copy=*x;
    CHECK(coh_auth_db_development_diagnostics(x,(CohAuthDbDevelopmentDiagnostics *)(void *)x)==COH_INVALID&&!memcmp(x,&copy,sizeof(copy)));
    CHECK(coh_auth_db_development_diagnostics(x,(CohAuthDbDevelopmentDiagnostics *)(void *)&provider)==COH_INVALID);
    CHECK(coh_auth_db_development_diagnostics(x,(CohAuthDbDevelopmentDiagnostics *)(uintptr_t)(UINTPTR_MAX-4))==COH_INVALID);
    CHECK(coh_auth_db_development_timeout(x)==COH_STATE&&coh_auth_db_development_cancel(x)==COH_STATE);
    CHECK(!memcmp(x,&copy,sizeof(copy)));
    x->db=(CohDbSession *)(void *)x;
    CHECK(coh_auth_db_development_destroy((CohAuthDbDevelopmentOwner **)(void *)&x->db)==COH_INVALID);
    x->db=NULL;
    CHECK(coh_auth_db_development_close(x)==COH_OK);stable_terminal(x);
    for(unsigned i=0;i<3;i++) {
        reset(GOOD);c=configuration();g.owner=coh_auth_db_development_create(&c);CHECK(g.owner);x=g.owner;
        const char *account=i==0?NULL:(i==1?(const char *)(void *)x:"wrong");
        CHECK(coh_auth_db_development_begin(x,account,"pw",100)==COH_INVALID);
        CHECK(diagnostic(x).begun==1);stable_terminal(x);
    }
}
static void allocation_controls(void) {
    for(unsigned fail=1;fail<=3;fail++) {
        reset(GOOD);alloc_fail=fail;allocation_cases++;CohAuthDbDevelopmentConfig c=configuration();
        g.owner=coh_auth_db_development_create(&c);
        if(fail==1){CHECK(!g.owner&&!live_allocations);continue;}
        CHECK(g.owner);CohStatus status=coh_auth_db_development_begin(g.owner,"fixture","pw",100);
        if(fail==2)CHECK(status==COH_LIMIT);
        else {CHECK(status==COH_OK);CHECK(run(g.owner)==COH_LIMIT&&g.owner->d.grant_consumed);}
        CHECK(diagnostic(g.owner).phase==COH_AUTH_DB_DEV_FAILED);stable_terminal(g.owner);
    }
}
static void cancellation_controls(void) {
    reset(GOOD);CohAuthDbDevelopmentOwner *x=start();CHECK(run(x)==COH_OK);unsigned calls=g.polls;stable_terminal(x);
    CHECK(calls>=10);
    for(unsigned at=1;at<=calls;at++) {
        reset(GOOD);x=start();g.cancel_at=at;g.reentry=1;
        CHECK(run(x)==COH_CANCELLED);CohAuthDbDevelopmentDiagnostics d=diagnostic(x);
        CHECK(d.phase==COH_AUTH_DB_DEV_CANCELLED&&d.failure==COH_AUTH_DB_DEV_FAILURE_CANCEL&&!d.complete_matching_list);
        stable_terminal(x);
    }
    for(unsigned db=0;db<2;db++) {
        reset(GOOD);x=start();if(db){CHECK(coh_auth_db_development_service(x,101,(CohCancel){0})==COH_OK);CHECK(coh_auth_db_development_service(x,102,(CohCancel){0})==COH_OK);}
        CHECK(coh_auth_db_development_cancel(x)==COH_CANCELLED);stable_terminal(x);
    }
}
static void deadline_and_close_controls(void) {
    for(unsigned which=0;which<6;which++) {
        reset(GOOD);CohAuthDbDevelopmentOwner *x=start();
        if(which&1){CHECK(coh_auth_db_development_service(x,101,(CohCancel){0})==COH_OK);CHECK(coh_auth_db_development_service(x,102,(CohCancel){0})==COH_OK);}
        if(which<2)CHECK(coh_auth_db_development_service(x,30100,(CohCancel){0})==COH_STATE&&diagnostic(x).failure==COH_AUTH_DB_DEV_FAILURE_TIMEOUT);
        else if(which<4)CHECK(coh_auth_db_development_service(x,99,(CohCancel){0})==COH_INVALID&&diagnostic(x).failure==COH_AUTH_DB_DEV_FAILURE_INPUT);
        else CHECK(coh_auth_db_development_close(x)==COH_OK&&diagnostic(x).phase==COH_AUTH_DB_DEV_CLOSED);
        stable_terminal(x);
    }
}
int main(void) {
    null_and_config_controls();alias_and_idle_controls();allocation_controls();
    for(unsigned mode=GOOD;mode<MODE_COUNT;mode++)if(mode!=AUTH_BEGIN_FAIL)mode_case(mode);
    reset(AUTH_BEGIN_FAIL);CohAuthDbDevelopmentConfig c=configuration();g.owner=coh_auth_db_development_create(&c);CHECK(g.owner);
    CHECK(coh_auth_db_development_begin(g.owner,"fixture","pw",100)==COH_INVALID);stable_terminal(g.owner);
    cancellation_controls();deadline_and_close_controls();
    CHECK(!live_allocations);
    printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"allocation_failure_cases\":%u,\"live_allocations\":0,\"owner_bytes\":%zu,\"diagnostics_bytes\":%zu,\"config_bytes\":%zu,\"player_scratch_bytes\":%zu,\"synthetic_api_controls_only\":true,\"network_executed\":false,\"crypto_executed\":false,\"actual_auth_db_verified\":false}\n",checks,scenarios,allocation_cases,sizeof(CohAuthDbDevelopmentOwner),sizeof(CohAuthDbDevelopmentDiagnostics),sizeof(CohAuthDbDevelopmentConfig),sizeof(CohDbPlayers));
    return 0;
}
