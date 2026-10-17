/* Host-only controller-API shell for the new probe owner. Synthetic grants are
 * test memory only; no encryption, network, SQL or real service is exercised. */
#define main shard_probe_main
#include "shard_play_probe.c"
#undef main
#include <assert.h>

struct CohLogin { CohLoginDiagnostics diagnostics;unsigned chosen;unsigned char sensitive[128]; };
static const char *scenario;
static unsigned created,destroyed,closed,authorization_wiped,invalidated_calls,choose_calls;
static CohAuthCrypto crypto;

const CohAuthCrypto *coh_auth_openssl_provider(void) {return &crypto;}
void coh_auth_wipe(void *memory,size_t size) {
    if(size==sizeof(CohLoginAuthorization) && !zeroed(memory,size)) authorization_wiped++;
    volatile unsigned char *p=memory;for(size_t i=0;i<size;i++)p[i]=0;
    assert(zeroed(memory,size));
}
CohLoginConfig coh_login_default_config(const CohAuthCrypto *p) {CohLoginConfig c={p,1,1,1};return c;}
CohLogin *coh_login_create(const CohLoginConfig *c) {
    assert(c->crypto==&crypto);
    if(!strcmp(scenario,"allocation-failure"))return NULL;
    created++;return calloc(1,sizeof(CohLogin));
}
CohStatus coh_login_begin(CohLogin *s,CohNetEndpoint endpoint,const char *account,const char *password,uint32_t subscription,uint16_t flags,uint64_t now) {
    (void)now;assert(endpoint.address[0]==127 && endpoint.address[3]==1 && endpoint.port==23000);
    assert(!strcmp(account,"test-account") && !strcmp(password,"test-password"));
    assert(!subscription && !flags);memset(s->sensitive,0xa5,sizeof(s->sensitive));
    s->diagnostics.sockets_opened=1;s->diagnostics.state=COH_LOGIN_WAIT_HELLO;
    return !strcmp(scenario,"begin-failure")?COH_IO:COH_OK;
}
CohStatus coh_login_service(CohLogin *s,uint64_t now,CohCancel cancel) {
    (void)now;(void)cancel;s->diagnostics.protocol=191021;s->diagnostics.sent_bytes=200;
    if(!strcmp(scenario,"login-failure")){s->diagnostics.state=COH_LOGIN_FAILED;return COH_IO;}
    s->diagnostics.shard_count=1;
    s->diagnostics.state=s->chosen?COH_LOGIN_AUTHORIZED:COH_LOGIN_SHARDS_READY;
    s->diagnostics.received_frames=s->chosen?4:3;
    if(s->chosen && !strcmp(scenario,"play-failure")){s->diagnostics.state=COH_LOGIN_FAILED;return COH_IO;}
    return COH_OK;
}
static CohAuthShard test_shard(void) {
    CohAuthShard shard={0};shard.id=1;shard.status=1;shard.port=7000;
    shard.ipv4[0]=127;shard.ipv4[3]=1;return shard;
}
CohStatus coh_login_shards(const CohLogin *s,CohAuthShards *out) {
    assert(s->diagnostics.state==COH_LOGIN_SHARDS_READY);out->count=1;out->shards[0]=test_shard();
    if(!strcmp(scenario,"wrong-endpoint"))out->shards[0].ipv4[0]=192;
    if(!strcmp(scenario,"down-shard"))out->shards[0].status=0;
    if(!strcmp(scenario,"wrong-port"))out->shards[0].port=7001;
    if(!strcmp(scenario,"wrong-id"))out->shards[0].id=2;
    if(!strcmp(scenario,"empty-shards"))out->count=0;
    if(!strcmp(scenario,"extra-shards"))out->count=2;
    return COH_OK;
}
CohStatus coh_login_choose(CohLogin *s,uint8_t id,uint64_t now) {
    (void)now;assert(id==1 && s->diagnostics.state==COH_LOGIN_SHARDS_READY);
    choose_calls++;if(!strcmp(scenario,"choose-failure"))return COH_IO;
    s->chosen=1;return COH_OK;
}
CohStatus coh_login_authorization(const CohLogin *s,CohLoginAuthorization *out) {
    if(s->diagnostics.state==COH_LOGIN_CLOSED){invalidated_calls++;assert(zeroed(out,sizeof(*out)));return COH_STATE;}
    assert(s->diagnostics.state==COH_LOGIN_AUTHORIZED);memset(out,0xa5,sizeof(*out));
    out->protocol=191021;out->play.shard_id=1;out->play.user_id=900001;out->shard=test_shard();
    if(!strcmp(scenario,"zero-cookie"))out->play.game_key=0;
    if(!strcmp(scenario,"zero-uid"))out->play.user_id=0;
    if(!strcmp(scenario,"wrong-uid"))out->play.user_id=900002;
    if(!strcmp(scenario,"wrong-play-shard"))out->play.shard_id=2;
    return COH_OK;
}
void coh_login_close(CohLogin *s) {
    assert(!zeroed(s->sensitive,sizeof(s->sensitive)));
    coh_auth_wipe(s->sensitive,sizeof(s->sensitive));closed++;
    s->diagnostics.state=COH_LOGIN_CLOSED;s->diagnostics.sockets_closed=1;
}
void coh_login_diagnostics(const CohLogin *s,CohLoginDiagnostics *out) {*out=s->diagnostics;}
void coh_login_destroy(CohLogin *s) {
    assert(s->diagnostics.state==COH_LOGIN_CLOSED && zeroed(s->sensitive,sizeof(s->sensitive)));
    destroyed++;coh_auth_wipe(s,sizeof(*s));free(s);
}
int main(int argc,char **argv) {
    assert(argc==4);scenario=argv[1];
    char *arguments[]={argv[0],argv[2],argv[3],NULL};
    int result=shard_probe_main(3,arguments);
    assert(created==destroyed && closed==created && invalidated_calls==created);
    if(!strcmp(scenario,"success")){assert(result==0 && choose_calls==1 && authorization_wiped);}
    else assert(result==1);
    return result;
}
