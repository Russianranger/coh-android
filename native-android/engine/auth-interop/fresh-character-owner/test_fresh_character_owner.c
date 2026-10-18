/* NEW controlled public-component doubles. No ordinary controller is run here. */
#include "fresh_character_owner.h"
#include "../../session/coh_session_crypto.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks, scenarios, reentries, owner_frees, cancel_polls;
#define CHECK(x) do { ++checks; if(!(x)) { fprintf(stderr,"fresh owner check %d: %s\n",__LINE__,#x); exit(1); } } while(0)
struct CohLogin { CohLoginDiagnostics d; unsigned chosen; };
struct CohDbSession { CohDbSessionDiagnostics d; };
static struct CohLogin login_double;
static struct CohDbSession db_double;
static CohFreshCharacterOwner *active;
static unsigned fault, hook_enabled, in_hook, alloc_fail, poll_at;
static unsigned login_creates, login_begins, login_services, chooses, grants;
static unsigned db_creates, db_begins, db_services, lists, creates, retires, cancels, login_closes;
static unsigned row_model, db_destroyed, login_destroyed;
static uint32_t captured_slot;
static uint8_t captured_name[64];
static const uint8_t authored_name[] = "New Fixture";
static void *owner_allocation; static size_t owner_bytes;
void *__real_calloc(size_t,size_t); void __real_free(void *);
void *__wrap_calloc(size_t n,size_t size) {
    if(alloc_fail) { alloc_fail=0; return NULL; }
    void *p=__real_calloc(n,size); CHECK(!owner_allocation); owner_allocation=p; owner_bytes=n*size; return p;
}
void __wrap_free(void *p) {
    if(p) { CHECK(p==owner_allocation); for(size_t i=0;i<owner_bytes;i++) CHECK(!((uint8_t*)p)[i]); owner_allocation=NULL; owner_frees++; }
    __real_free(p);
}
void coh_auth_wipe(void *p,size_t n) { volatile uint8_t *q=p; while(n--) *q++=0; }
void coh_db_wipe(void *p,size_t n) { coh_auth_wipe(p,n); }
static CohStatus keypair(void *p,uint8_t a[64],uint8_t b[64]) { (void)p;(void)a;(void)b;
    return COH_UNSUPPORTED; }
static CohStatus shared(void *p,const uint8_t a[64],const uint8_t b[64],uint8_t c[64]) { (void)p;(void)a;(void)b;(void)c;
    return COH_UNSUPPORTED; }
static CohStatus md5(void *p,CohBytes b,uint8_t d[16]) { (void)p;(void)b;(void)d;
    return COH_UNSUPPORTED; }
static CohStatus sha512(void *p,CohBytes b,uint8_t d[64]) { (void)p;(void)b;(void)d;
    return COH_UNSUPPORTED; }
static CohStatus rsa(void *p,CohBytes a,CohBytes b,CohBytes c,uint8_t *d,size_t n,size_t *m) { (void)p;(void)a;(void)b;(void)c;(void)d;(void)n;(void)m;
    return COH_UNSUPPORTED; }
static const CohAuthCrypto provider={NULL,keypair,shared,md5,sha512,rsa};
CohStatus coh_session_key_exchange(void *p,const uint8_t a[64],uint8_t b[64],CohBlowfish *key) {
    (void)p;(void)a;(void)b;(void)key;
    return COH_UNSUPPORTED;
}
CohNetConfig coh_net_default_config(void) { CohNetConfig c={0}; c.version=5; return c; }
static void hook(void) {
    if(!hook_enabled||in_hook||!active) return;
    in_hook=1; CohFreshCharacterDiagnostics d,before; memset(&d,0xa5,sizeof(d)); before=d;
    CohFreshCharacterOwner *copy=active;
    CHECK(coh_fresh_character_diagnostics(active,&d)==COH_STATE&&!memcmp(&d,&before,sizeof(d)));
    CHECK(coh_fresh_character_begin(active,"fixture","password",(CohBytes){authored_name,11},101)==COH_STATE);
    CHECK(coh_fresh_character_service(active,101,(CohCancel){0})==COH_STATE);
    CHECK(coh_fresh_character_timeout(active)==COH_STATE&&coh_fresh_character_cancel(active)==COH_STATE);
    CHECK(coh_fresh_character_close(active)==COH_STATE&&coh_fresh_character_destroy(&copy)==COH_STATE&&copy==active);
    reentries++; in_hook=0;
}
CohLoginConfig coh_login_default_config(const CohAuthCrypto *crypto) { CohLoginConfig c={0}; c.crypto=crypto;
    return c; }
CohLogin *coh_login_create(const CohLoginConfig *c) {
    login_creates++; hook(); CHECK(c->crypto==&provider&&c->connect_timeout_ms==3000&&c->reply_timeout_ms==10000&&c->receive_budget==4);
    return fault==1?NULL:&login_double;
}
CohStatus coh_login_begin(CohLogin *s,CohNetEndpoint ep,const char *account,const char *password,uint32_t sub,uint16_t flags,uint64_t now) {
    login_begins++; hook(); CHECK(s==&login_double&&ep.port==25001&&!strcmp(account,"fixture")&&!strcmp(password,"password")&&!sub&&!flags&&now==100);
    s->d.state=COH_LOGIN_CONNECTING;
    return fault==2?COH_IO:COH_OK;
}
CohStatus coh_login_service(CohLogin *s,uint64_t now,CohCancel c) {
    (void)now;(void)c; login_services++; hook(); s->d.protocol=COH_AUTH_OUROBOROS2;
    s->d.state=s->chosen?COH_LOGIN_AUTHORIZED:COH_LOGIN_SHARDS_READY;s->d.received_frames=s->chosen?4:3;
    if(fault==3) return COH_IO;
    if(fault==4) s->d.state=COH_LOGIN_UNSUPPORTED;
    if(fault==5) s->d.protocol=COH_AUTH_GLOBAL;
    if(fault==6) s->d.received_frames++;
    if(fault==7) s->d.pending_send_bytes=1;
    if(fault==8) s->d.buffered_receive_bytes=1;
    if(fault==9) s->d.password_retained=1;
    if(fault==10) s->d.remote_failure_command=1;
    if(fault==11) s->d.remote_failure_reason=1;
    if(fault==12) s->d.last_system_error=1;
    return COH_OK;
}
CohStatus coh_login_shards(const CohLogin *s,CohAuthShards *out) {
    CHECK(s==&login_double);hook();memset(out,0,sizeof(*out));out->count=1;
    CohAuthShard *p=&out->shards[0];p->id=1;p->status=1;p->port=7000;p->ipv4[0]=127;p->ipv4[3]=1;
    if(fault==13)return COH_IO;
    if(fault==14)out->count=0;
    if(fault==15)out->count=2;
    if(fault==16)p->id=2;
    if(fault==17)p->status=0;
    if(fault==18)p->port=7001;
    if(fault==19)p->ipv4[3]=2;
    return COH_OK;
}
CohStatus coh_login_choose(CohLogin *s,uint8_t shard,uint64_t now) { (void)now;chooses++;hook();CHECK(shard==1);s->chosen=1;s->d.state=COH_LOGIN_WAIT_PLAY;
    return fault==20?COH_IO:COH_OK; }
CohStatus coh_login_authorization(const CohLogin *s,CohLoginAuthorization *out) {
    CHECK(s==&login_double);grants++;hook();memset(out,0,sizeof(*out));out->protocol=COH_AUTH_OUROBOROS2;strcpy(out->account_name,"fixture");
    out->play.user_id=900001;out->play.game_key=0x12345678;out->play.shard_id=1;out->shard.id=1;out->shard.status=1;out->shard.port=7000;out->shard.ipv4[0]=127;out->shard.ipv4[3]=1;
    if(fault==21)return COH_IO;
    if(fault==22)out->protocol=COH_AUTH_GLOBAL;
    if(fault==23)out->play.user_id=900002;
    if(fault==24)out->play.game_key=0;
    if(fault==25)out->play.shard_id=2;
    if(fault==26)out->shard.status=0;
    if(fault==27)out->account_name[0]=0;
    if(fault==28)memset(out->account_name,'x',sizeof(out->account_name));
    return COH_OK;
}
void coh_login_close(CohLogin *s) { login_closes++;hook();CHECK(db_destroyed||!db_creates||fault==29);s->d.state=COH_LOGIN_CLOSED; }
void coh_login_destroy(CohLogin *s) { CHECK(s==&login_double);hook();login_destroyed++; }
void coh_login_diagnostics(const CohLogin *s,CohLoginDiagnostics *out) { hook();*out=s->d; }
CohDbSession *coh_db_session_create(const CohDbSessionConfig *c) {
    db_creates++;hook();CHECK(c->transport.link.version==5&&c->transport.link.connect_timeout_ms==3000&&c->transport.link.idle_timeout_ms==10000&&c->transport.link.fragment_timeout_ms==10000);
    CHECK(c->transport.local.address[0]==127&&c->transport.local.address[3]==1&&!c->transport.local.port&&c->transport.peer.address[0]==127&&c->transport.peer.address[3]==1&&c->transport.peer.port==7000);
    CHECK(c->transport.receive_budget==4&&c->transport.encryption_required==1&&c->transport.key_exchange==coh_session_key_exchange&&c->transport.key_context==&provider&&c->request_timeout_ms==10000&&!c->outbound_compressed);
    return fault==29?NULL:&db_double;
}
CohStatus coh_db_session_begin(CohDbSession *s,const CohDbLogin *v,const CohDbAuthReceipt *a,uint32_t connect_id,uint64_t now) {
    (void)now;db_begins++;hook();CHECK(v->user_id==900001&&v->cookie==0x12345678&&!strcmp(v->account,"fixture")&&v->protocol_version==COH_DB_PROTOCOL_VERSION&&v->no_version_check==1&&!strcmp(v->patch_version,"dev:owned-fresh-character"));
    CHECK(a->user_id==v->user_id&&a->game_cookie==v->cookie&&a->generation==1&&a->verified==1&&!strcmp(a->account,v->account)&&connect_id==123);
    for(unsigned i=0;i<16;i++)CHECK(v->executable_checksum[i]==(uint8_t)(i+1));
    s->d.phase=COH_DB_CONNECTING;s->d.generation=1;s->d.server_identity_bound=1;
    if(fault==30)return COH_IO;
    if(fault==31)s->d.generation=2;
    if(fault==32)s->d.local_development_auth=1;
    if(fault==33)s->d.server_identity_bound=0;
    return COH_OK;
}
CohStatus coh_db_session_service(CohDbSession *s,uint64_t now,CohCancel c) {
    (void)now;(void)c;db_services++;hook();s->d.login_requests=1;s->d.player_lists=1;
    if(!creates)s->d.phase=COH_DB_CHARACTERS;else{s->d.phase=COH_DB_HANDOFF_READY;s->d.handoffs=1;}
    if(fault==34)return COH_IO;
    if(fault==35)s->d.generation=2;
    if(fault==36)s->d.local_development_auth=1;
    if(fault==37)s->d.server_identity_bound=0;
    if(fault==38)s->d.queue_updates=1;
    if(fault==39)s->d.unsupported=1;
    if(fault==40)s->d.login_requests=2;
    if(fault==41)s->d.player_lists=2;
    if(fault==42)s->d.phase=COH_DB_FAILED;
    if(fault==43)s->d.selection_generation=2;
    if(fault==44)s->d.choices=2;
    if(fault==45)s->d.handoffs=2;
    return COH_OK;
}
CohStatus coh_db_session_players(const CohDbSession *s,CohDbPlayers *p) {
    CHECK(s==&db_double);lists++;hook();memset(p,0,sizeof(*p));p->user_id=900001;p->max_slots=3;p->base_slots=3;
    for(unsigned i=0;i<3;i++){p->players[i].wire_slot=i;p->players[i].empty=1;}
    if(fault==46)return COH_IO;
    if(fault==47)p->user_id=900002;
    if(fault==48)p->max_slots=0;
    if(fault==49)p->max_slots=COH_DB_SLOTS_MAX+1;
    if(fault==50)p->base_slots=0;
    if(fault==51)p->base_slots=4;
    if(fault==52)p->selectable_count=1;
    if(fault==53)p->players[2].wire_slot=0;
    if(fault==54)p->players[2].empty=0;
    if(fault==55)p->players[2].slot_lock=1;
    if(fault==56)p->players[2].visitor=1;
    if(fault==57)p->players[2].invalid=1;
    return COH_OK;
}
CohStatus coh_db_session_create_empty(CohDbSession *s,const CohDbEmptyCreationRequest *r,uint64_t now) {
    (void)now;creates++;hook();CHECK(r->wire_slot==0&&r->location==COH_DB_CREATE_PRIMAL_HERO&&r->expected_session_generation==1&&r->expected_receipt_generation==1&&r->expected_list_generation==1);
    CHECK(r->name.size==11&&!memcmp(r->name.data,authored_name,11));captured_slot=r->wire_slot;memcpy(captured_name,r->name.data,r->name.size);
    if(fault==58)return COH_LIMIT;
    row_model=1;s->d.phase=COH_DB_WAIT_MAP;s->d.choices=1;s->d.selection_generation=1;
    if(fault==59)s->d.phase=COH_DB_CHARACTERS;
    if(fault==60)s->d.choices=2;
    if(fault==61)s->d.selection_generation=2;
    if(fault==62)s->d.handoffs=1;
    if(fault==63)s->d.unsupported=1;
    return COH_OK;
}
CohStatus coh_db_session_retire_created_offer(CohDbSession *s,const CohDbCreatedOfferPolicy *p,CohDbCreatedOfferSummary *o) {
    retires++;hook();CHECK(p->expected_session_generation==1&&p->expected_receipt_generation==1&&p->expected_selection_generation==1&&p->owned_map_id==1&&p->owned_map_endpoint.port==7001&&p->owned_map_endpoint.address[3]==1);
    memset(o,0,sizeof(*o));o->server_allocated_offer_observed=o->private_offer_retired=o->container_uninitialized=1;o->session_generation=o->receipt_generation=o->selection_generation=1;s->d.phase=COH_DB_CANCELLED;
    if(fault==64)return COH_STATE;
    if(fault==65)o->server_allocated_offer_observed=0;
    if(fault==66)o->private_offer_retired=0;
    if(fault==67)o->container_uninitialized=0;
    if(fault==68)o->persistent_rollback_claimed=1;
    if(fault==69)o->session_generation=2;
    if(fault==70)o->receipt_generation=2;
    if(fault==71)o->selection_generation=2;
    if(fault==72)s->d.phase=COH_DB_CLOSED;
    return COH_OK;
}
CohDbSessionPhase coh_db_session_phase(const CohDbSession *s) { hook();
    return s->d.phase; }
void coh_db_session_diagnostics(const CohDbSession *s,CohDbSessionDiagnostics *out) { hook();*out=s->d; }
void coh_db_session_cancel(CohDbSession *s) { cancels++;hook();s->d.phase=COH_DB_CANCELLED; }
void coh_db_session_destroy(CohDbSession *s) { CHECK(s==&db_double);hook();db_destroyed++; }

static CohFreshCharacterConfig configuration(void) {
    CohFreshCharacterConfig c={0};c.auth_endpoint=(CohNetEndpoint){{127,0,0,1},25001};c.crypto=&provider;c.connect_id=123;
    c.owned_map_endpoint=(CohNetEndpoint){{127,0,0,1},7001};c.owned_map_id=1;for(unsigned i=0;i<16;i++)c.executable_checksum[i]=(uint8_t)(i+1);
    return c;
}
static CohFreshCharacterDiagnostics observation(void) { CohFreshCharacterDiagnostics d={0};CHECK(coh_fresh_character_diagnostics(active,&d)==COH_OK);
    return d; }
static void reset(unsigned which) {
    CHECK(!active&&!owner_allocation);memset(&login_double,0,sizeof(login_double));memset(&db_double,0,sizeof(db_double));
    fault=which;login_creates=login_begins=login_services=chooses=grants=db_creates=db_begins=db_services=lists=creates=retires=cancels=login_closes=row_model=db_destroyed=login_destroyed=cancel_polls=0;
    hook_enabled=in_hook=alloc_fail=poll_at=0;captured_slot=UINT32_MAX;memset(captured_name,0,sizeof(captured_name));
    CohFreshCharacterConfig c=configuration();active=coh_fresh_character_create(&c);CHECK(active);
}
static void begin(void) { CHECK(coh_fresh_character_begin(active,"fixture","password",(CohBytes){authored_name,11},100)==COH_OK); }
static void limits(const CohFreshCharacterDiagnostics *d) {
    CHECK(d->provisional_development_policy&&d->development_skip_requested&&!d->actual_server_development_skip_observed);
    CHECK(!d->normal_version_admitted&&!d->checksum_reference_admitted&&!d->initialized_character&&!d->persistent_rollback_claimed&&!d->map_socket_opened&&!d->map_character_body_sent&&!d->sends_ready&&!d->sends_received_character&&!d->sends_full_update_ack&&!d->current_world_verified&&!d->actor_publication&&!d->world_authority);
}
static void finish(void) {
    hook_enabled=0;CohFreshCharacterDiagnostics d=observation();limits(&d);
    CHECK(coh_fresh_character_close(active)==COH_OK);CohFreshCharacterDiagnostics after=observation();
    if(d.phase>=COH_FRESH_CHARACTER_COMPLETE)CHECK(after.phase==d.phase&&after.failure==d.failure&&after.status==d.status);
    CHECK(coh_fresh_character_destroy(&active)==COH_OK&&!active&&!owner_allocation);scenarios++;
}
static CohStatus advance(unsigned until,CohCancel c) {
    CohStatus status=COH_OK;for(unsigned step=0;step<until&&status==COH_OK;step++)status=coh_fresh_character_service(active,101+step,c);
    return status;
}
static void good(void) {
    reset(0);hook_enabled=1;begin();CHECK(advance(4,(CohCancel){0})==COH_OK);hook_enabled=0;
    CohFreshCharacterDiagnostics d=observation();CHECK(d.phase==COH_FRESH_CHARACTER_COMPLETE&&!d.failure&&d.status==COH_OK&&d.begin_attempted&&d.shard_attempted&&d.bridge_attempted&&d.creation_attempted&&d.retirement_attempted);
    CHECK(d.actual_grant_verified&&d.matching_empty_list_verified&&d.creation_request_queued&&d.allocated_offer_observed&&d.private_offer_retired&&d.container_uninitialized&&d.persistent_allocation_possible);
    CHECK(d.session_generation==1&&d.receipt_generation==1&&d.selection_generation==1&&d.final_auth_phase==COH_LOGIN_CLOSED&&d.final_db_phase==COH_DB_CANCELLED&&d.observed_auth_phase==COH_LOGIN_AUTHORIZED&&d.observed_db_phase==COH_DB_HANDOFF_READY);
    CHECK(d.private_name_wiped&&d.bridge_temporaries_wiped&&d.controllers_destroyed&&d.cleanup_cancel_close_used&&db_destroyed==1&&login_destroyed==1&&row_model==1&&captured_slot==0&&!memcmp(captured_name,authored_name,11));
    CHECK(chooses==1&&grants==1&&creates==1&&retires==1&&db_begins==1&&login_begins==1);
    CHECK(coh_fresh_character_service(active,105,(CohCancel){0})==COH_STATE&&coh_fresh_character_cancel(active)==COH_STATE&&coh_fresh_character_timeout(active)==COH_STATE);
    CHECK(coh_fresh_character_begin(active,"fixture","password",(CohBytes){authored_name,11},106)==COH_STATE);finish();CHECK(row_model==1);
}
static void bad_component(unsigned which) {
    reset(which);CohStatus status=coh_fresh_character_begin(active,"fixture","password",(CohBytes){authored_name,11},100);
    if(status==COH_OK) { status=advance(4,(CohCancel){0}); }
    CHECK(status!=COH_OK);
    CohFreshCharacterDiagnostics d=observation();CHECK(d.phase==COH_FRESH_CHARACTER_FAILED&&d.failure!=COH_FRESH_CHARACTER_FAILURE_NONE&&d.status==status&&d.controllers_destroyed&&d.private_name_wiped&&d.bridge_temporaries_wiped);
    CHECK(chooses<=1&&grants<=1&&creates<=1&&retires<=1&&login_begins<=1&&db_begins<=1);
    if(creates&&which!=58)CHECK(d.persistent_allocation_possible&&row_model==1);
    CHECK(coh_fresh_character_begin(active,"fixture","password",(CohBytes){authored_name,11},200)==COH_STATE);finish();
}
static int cancellation(void *unused) { (void)unused;hook();
    return ++cancel_polls==poll_at; }
static void cancelled_at(unsigned stage,unsigned poll) {
    reset(0);begin();CHECK(advance(stage,(CohCancel){0})==COH_OK);cancel_polls=0;poll_at=poll;hook_enabled=1;
    CHECK(coh_fresh_character_service(active,101+stage,(CohCancel){cancellation,NULL})==COH_CANCELLED);hook_enabled=0;
    CohFreshCharacterDiagnostics d=observation();CHECK(d.phase==COH_FRESH_CHARACTER_CANCELLED&&d.failure==COH_FRESH_CHARACTER_FAILURE_CANCEL&&d.controllers_destroyed&&d.private_name_wiped);
    CHECK((stage>=3)==(row_model==1));
    if(stage==3&&poll==3)CHECK(d.private_offer_retired&&retires==1&&db_destroyed==1&&login_destroyed==1);
    finish();
}
static void bad_input(unsigned which) {
    reset(0);CohBytes name={authored_name,11};const char *account="fixture",*password="password";static const uint8_t high[]={0xff},control[]={31},del[]={127},nul[]={'a',0,'b'};uint8_t too_long[64]={0};
    switch(which){case 0:account=NULL;break;case 1:password=NULL;break;case 2:name.data=NULL;break;case 3:name.size=0;break;case 4:name=(CohBytes){too_long,64};break;case 5:name=(CohBytes){high,1};break;case 6:name=(CohBytes){control,1};break;case 7:name=(CohBytes){del,1};break;case 8:name=(CohBytes){nul,3};break;case 9:name=(CohBytes){(const uint8_t*)active,1};break;case 10:account=(const char*)active;break;case 11:password=(const char*)&provider;break;case 12:name=(CohBytes){(const uint8_t*)(uintptr_t)(UINTPTR_MAX-1),8};break;default:name=(CohBytes){(const uint8_t*)&provider,1};break;}
    CHECK(coh_fresh_character_begin(active,account,password,name,100)==COH_INVALID);CohFreshCharacterDiagnostics d=observation();CHECK(d.begin_attempted&&d.phase==COH_FRESH_CHARACTER_FAILED&&!login_creates&&d.private_name_wiped);
    CHECK(coh_fresh_character_begin(active,"fixture","password",(CohBytes){authored_name,11},101)==COH_STATE);finish();
}
static void lifecycle(unsigned kind,unsigned stage) {
    reset(0);begin();CHECK(advance(stage,(CohCancel){0})==COH_OK);CohStatus status;
    if(kind==0)status=coh_fresh_character_cancel(active);else if(kind==1)status=coh_fresh_character_timeout(active);else if(kind==2)status=coh_fresh_character_service(active,99,(CohCancel){0});else if(kind==3)status=coh_fresh_character_service(active,30100,(CohCancel){0});else status=coh_fresh_character_close(active);
    CohFreshCharacterDiagnostics d=observation();CHECK(d.controllers_destroyed&&d.private_name_wiped&&d.bridge_temporaries_wiped);
    CHECK(status==(kind==0?COH_CANCELLED:kind==2?COH_INVALID:kind==4?COH_OK:COH_STATE));CHECK(row_model==(stage>=3));finish();
}
static void config_and_alias(void) {
    CohFreshCharacterConfig good_config=configuration();for(unsigned i=0;i<9;i++){CohFreshCharacterConfig c=good_config;switch(i){case 0:c.auth_endpoint.address[3]=2;break;case 1:c.auth_endpoint.port=19999;break;case 2:c.auth_endpoint.port=60000;break;case 3:c.crypto=NULL;break;case 4:c.connect_id=0;break;case 5:c.owned_map_id=2;break;case 6:c.owned_map_endpoint.port=7002;break;case 7:c.owned_map_endpoint.address[3]=2;break;default:c.crypto=(const CohAuthCrypto*)(const void*)&c;break;}CHECK(!coh_fresh_character_create(&c));scenarios++;}
    alloc_fail=1;CHECK(!coh_fresh_character_create(&good_config)&&!owner_allocation);scenarios++;
    reset(0);CohFreshCharacterDiagnostics d,before;memset(&d,0xa5,sizeof(d));before=d;CHECK(coh_fresh_character_diagnostics(NULL,&d)==COH_INVALID&&!memcmp(&d,&before,sizeof(d)));
    CHECK(coh_fresh_character_diagnostics(active,(CohFreshCharacterDiagnostics*)(void*)active)==COH_INVALID);
    CHECK(coh_fresh_character_diagnostics(active,(CohFreshCharacterDiagnostics*)(void*)&provider)==COH_INVALID);
    CHECK(coh_fresh_character_destroy(NULL)==COH_INVALID);CohFreshCharacterOwner *none=NULL;CHECK(coh_fresh_character_destroy(&none)==COH_OK);finish();
}
int main(void) {
    CHECK(coh_fresh_character_begin(NULL,NULL,NULL,(CohBytes){0},0)==COH_INVALID&&coh_fresh_character_service(NULL,0,(CohCancel){0})==COH_INVALID);
    CHECK(coh_fresh_character_timeout(NULL)==COH_INVALID&&coh_fresh_character_cancel(NULL)==COH_INVALID&&coh_fresh_character_close(NULL)==COH_INVALID);
    config_and_alias();good();for(unsigned f=1;f<=72;f++)bad_component(f);for(unsigned f=0;f<14;f++)bad_input(f);
    for(unsigned stage=0;stage<4;stage++){cancelled_at(stage,1);cancelled_at(stage,2);for(unsigned kind=0;kind<5;kind++)lifecycle(kind,stage);}cancelled_at(3,3);
    CHECK(!owner_allocation&&reentries>0&&owner_frees>0);printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"component_fault_cases\":72,\"input_refusals\":14,\"busy_reentry_probes\":%u,\"owner_wiped_frees\":%u,\"controlled_component_doubles\":true,\"ordinary_controllers_executed\":false,\"actual_servers\":false,\"persistent_rollback_claimed\":false}\n",checks,scenarios,reentries,owner_frees);
    return 0;
}
