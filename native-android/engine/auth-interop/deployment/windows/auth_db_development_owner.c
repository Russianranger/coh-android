#include "auth_db_development_owner.h"
#include "../../../session/coh_session_crypto.h"
#include <stdlib.h>
#include <string.h>

/* These identify the bounded private fixture; they do not manufacture a grant. */
#define AD_FIXTURE_UID 900001u
#define AD_TOTAL_MS 30000u
#define AD_REPLY_MS 10000u
#define AD_CONNECT_MS 3000u
struct CohAuthDbDevelopmentOwner {
    CohAuthDbDevelopmentConfig config;
    CohLogin *auth;
    CohDbSession *db;
    CohAuthDbDevelopmentDiagnostics d;
    uint64_t start_ms, clock_ms;
    unsigned busy, chosen;
};
static int overlap(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t ap=(uintptr_t)a,bp=(uintptr_t)b;
    if(an>UINTPTR_MAX-ap||bn>UINTPTR_MAX-bp)return 1;
    return ap<bp+bn&&bp<ap+an;
}
static int loopback(CohNetEndpoint e) {
    static const uint8_t ip[4]={127,0,0,1};
    return !memcmp(e.address,ip,sizeof(ip));
}
static int active(const CohAuthDbDevelopmentOwner *x) {
    return x->d.phase==COH_AUTH_DB_DEV_AUTH||x->d.phase==COH_AUTH_DB_DEV_DB;
}
static int shard_valid(const CohAuthShard *s) {
    CohNetEndpoint e;memcpy(e.address,s->ipv4,sizeof(e.address));e.port=s->port;
    return s->id==1&&s->status==1&&s->port==7000&&loopback(e);
}
static void snapshot(CohAuthDbDevelopmentOwner *x) {
    if(x->auth) {
        CohLoginDiagnostics d={0};coh_login_diagnostics(x->auth,&d);
        x->d.auth_phase=d.state;x->d.auth_frames=d.received_frames;
    }
    if(x->db) {
        CohDbSessionDiagnostics d={0};coh_db_session_diagnostics(x->db,&d);
        x->d.db_phase=d.phase;x->d.db_login_requests=d.login_requests;
        x->d.db_player_lists=d.player_lists;x->d.db_queue_updates=d.queue_updates;
        x->d.db_unsupported=d.unsupported;x->d.db_choices=d.choices;
        x->d.db_handoffs=d.handoffs;
    }
}
static void cleanup(CohAuthDbDevelopmentOwner *x) {
    /* Always snapshot BEFORE cleanup. A terminal snapshot is never resampled. */
    snapshot(x);
    if(x->auth) {
        CohLoginDiagnostics d={0};coh_login_close(x->auth);
        coh_login_diagnostics(x->auth,&d);x->d.auth_final_phase=d.state;
        coh_login_destroy(x->auth);x->auth=NULL;
    }
    if(x->db) {
        CohDbSessionDiagnostics d={0};coh_db_session_cancel(x->db);
        coh_db_session_diagnostics(x->db,&d);x->d.db_final_phase=d.phase;
        x->d.cleanup_cancel_close_used=1;
        coh_db_session_destroy(x->db);x->db=NULL;
    }
    x->d.controllers_destroyed=1;
}
static CohStatus finish(CohAuthDbDevelopmentOwner *x,
    CohAuthDbDevelopmentPhase phase,CohAuthDbDevelopmentFailure failure,CohStatus status) {
    cleanup(x);x->d.phase=phase;x->d.failure=failure;x->d.status=status;return status;
}
static int cancelled(CohCancel cancel) {
    return cancel.poll&&cancel.poll(cancel.context);
}
static CohStatus cancel_now(CohAuthDbDevelopmentOwner *x) {
    return finish(x,COH_AUTH_DB_DEV_CANCELLED,COH_AUTH_DB_DEV_FAILURE_CANCEL,COH_CANCELLED);
}
CohAuthDbDevelopmentOwner *coh_auth_db_development_create(
    const CohAuthDbDevelopmentConfig *c) {
    if(!c||!loopback(c->auth_endpoint)||c->auth_endpoint.port<20000||
       c->auth_endpoint.port>59999||!c->connect_id||!c->crypto||
       !c->crypto->keypair||!c->crypto->shared||!c->crypto->md5||
       !c->crypto->sha512||!c->crypto->rsa_oaep_sha1||
       overlap(c,sizeof(*c),c->crypto,sizeof(*c->crypto)))return NULL;
    CohAuthDbDevelopmentOwner *x=calloc(1,sizeof(*x));if(!x)return NULL;
    x->config=*c;x->d.development_skip_requested=1;return x;
}
CohStatus coh_auth_db_development_begin(CohAuthDbDevelopmentOwner *x,
    const char *account,const char *password,uint64_t now) {
    if(!x)return COH_INVALID;
    if(x->busy||x->d.begun||x->d.phase!=COH_AUTH_DB_DEV_IDLE)return COH_STATE;
    /* Consumption precedes allocation, validation and every fallible API. */
    x->busy=1;x->d.begun=1;x->d.phase=COH_AUTH_DB_DEV_AUTH;
    x->start_ms=x->clock_ms=now;
    CohStatus status=COH_INVALID;
    if(!account||!password||overlap(account,15,x,sizeof(*x))||
       overlap(password,17,x,sizeof(*x))||
       overlap(account,15,x->config.crypto,sizeof(*x->config.crypto))||
       overlap(password,17,x->config.crypto,sizeof(*x->config.crypto))) {
        status=finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_INPUT,status);
    } else {
        CohLoginConfig c=coh_login_default_config(x->config.crypto);
        c.connect_timeout_ms=AD_CONNECT_MS;c.reply_timeout_ms=AD_REPLY_MS;c.receive_budget=4;
        x->auth=coh_login_create(&c);
        if(!x->auth)status=finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_AUTH,COH_LIMIT);
        else {
            status=coh_login_begin(x->auth,x->config.auth_endpoint,account,password,0,0,now);
            if(status!=COH_OK)status=finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_INPUT,status);
            else {snapshot(x);x->d.status=COH_OK;}
        }
    }
    x->busy=0;return status;
}
static CohStatus choose_shard(CohAuthDbDevelopmentOwner *x,uint64_t now,CohCancel cancel) {
    CohAuthShards shards={0};CohLoginDiagnostics d={0};
    coh_login_diagnostics(x->auth,&d);
    CohStatus status=coh_login_shards(x->auth,&shards);
    if(status==COH_OK&&(d.state!=COH_LOGIN_SHARDS_READY||d.protocol!=COH_AUTH_OUROBOROS2||
       d.received_frames!=3||d.pending_send_bytes||d.buffered_receive_bytes||d.password_retained||
       d.remote_failure_command||d.remote_failure_reason||d.last_system_error||
       shards.count!=1||!shard_valid(&shards.shards[0])))status=COH_STATE;
    if(status==COH_OK&&cancelled(cancel))status=COH_CANCELLED;
    if(status==COH_OK)status=coh_login_choose(x->auth,1,now);
    coh_auth_wipe(&shards,sizeof(shards));
    if(status==COH_CANCELLED)return cancel_now(x);
    if(status!=COH_OK)return finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_SHARD,status);
    x->chosen=1;x->d.selected_shard_verified=1;snapshot(x);return COH_OK;
}
static CohStatus bridge(CohAuthDbDevelopmentOwner *x,uint64_t now,CohCancel cancel) {
    CohLoginAuthorization a={0};CohDbLogin login={0};CohDbAuthReceipt receipt={0};
    CohLoginDiagnostics ad={0};CohStatus status;
    coh_login_diagnostics(x->auth,&ad);
    status=coh_login_authorization(x->auth,&a);
    if(status==COH_OK&&(!x->chosen||!x->d.selected_shard_verified||
       ad.state!=COH_LOGIN_AUTHORIZED||ad.protocol!=COH_AUTH_OUROBOROS2||
       ad.received_frames!=4||ad.pending_send_bytes||ad.buffered_receive_bytes||
       ad.password_retained||ad.remote_failure_command||ad.remote_failure_reason||ad.last_system_error||
       a.protocol!=COH_AUTH_OUROBOROS2||a.play.shard_id!=1||
       a.play.user_id!=AD_FIXTURE_UID||!a.play.game_key||!shard_valid(&a.shard)||
       !a.account_name[0]||!memchr(a.account_name,0,sizeof(a.account_name))))status=COH_STATE;
    if(status!=COH_OK)goto done;
    if(cancelled(cancel)){status=COH_CANCELLED;goto done;}
    /* Fresh local generation labels this inaccessible owner, never a grant. */
    x->d.grant_consumed=1;
    memcpy(login.account,a.account_name,sizeof(login.account));
    login.user_id=a.play.user_id;login.cookie=a.play.game_key;
    login.protocol_version=COH_DB_PROTOCOL_VERSION;login.no_version_check=1;
    memcpy(login.patch_version,"dev:owned-auth-db-probe",23);
    memcpy(login.executable_checksum,x->config.executable_checksum,sizeof(login.executable_checksum));
    memcpy(receipt.account,a.account_name,sizeof(receipt.account));
    receipt.user_id=a.play.user_id;receipt.game_cookie=a.play.game_key;
    receipt.generation=1;receipt.verified=1;
    CohDbSessionConfig c={0};c.transport.link=coh_net_default_config();
    c.transport.link.connect_timeout_ms=AD_CONNECT_MS;c.transport.link.idle_timeout_ms=AD_REPLY_MS;
    c.transport.link.fragment_timeout_ms=AD_REPLY_MS;
    c.transport.peer=(CohNetEndpoint){{127,0,0,1},7000};
    c.transport.local=(CohNetEndpoint){{127,0,0,1},0};c.transport.receive_budget=4;
    c.transport.key_exchange=coh_session_key_exchange;
    c.transport.key_context=(void *)(uintptr_t)x->config.crypto;c.transport.encryption_required=1;
    c.request_timeout_ms=AD_REPLY_MS;c.outbound_compressed=0;
    x->db=coh_db_session_create(&c);
    status=x->db?coh_db_session_begin(x->db,&login,&receipt,x->config.connect_id,now):COH_LIMIT;
done:
    coh_auth_wipe(&a,sizeof(a));coh_db_wipe(&login,sizeof(login));coh_db_wipe(&receipt,sizeof(receipt));
    if(status==COH_CANCELLED)return cancel_now(x);
    if(status!=COH_OK)return finish(x,COH_AUTH_DB_DEV_FAILED,
        x->d.grant_consumed?COH_AUTH_DB_DEV_FAILURE_DB_BEGIN:COH_AUTH_DB_DEV_FAILURE_GRANT,status);
    x->d.phase=COH_AUTH_DB_DEV_DB;snapshot(x);return COH_OK;
}
static int list_valid(const CohDbPlayers *p) {
    if(p->user_id!=AD_FIXTURE_UID||!p->max_slots||p->max_slots>COH_DB_SLOTS_MAX||
       !p->base_slots||p->base_slots>p->max_slots||p->selectable_count)return 0;
    for(uint32_t i=0;i<p->max_slots;i++) {
        const CohDbPlayer *s=&p->players[i];
        if(s->wire_slot!=i||s->empty!=1||s->slot_lock||s->visitor||s->invalid)return 0;
    }
    return 1;
}
static CohStatus db_service(CohAuthDbDevelopmentOwner *x,uint64_t now,CohCancel cancel) {
    CohStatus status=coh_db_session_service(x->db,now,cancel);
    snapshot(x);
    if(status==COH_CANCELLED)return cancel_now(x);
    if(status!=COH_OK)return finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_DB,status);
    CohDbSessionDiagnostics d={0};coh_db_session_diagnostics(x->db,&d);
    if(d.unsupported||d.queue_updates||d.choices||d.handoffs||d.player_lists>1||
       d.generation!=1||d.local_development_auth||!d.server_identity_bound||
       d.selection_generation||d.login_requests>1)
        return finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_DB,
            d.unsupported?COH_UNSUPPORTED:COH_STATE);
    if(d.phase!=COH_DB_CONNECTING&&d.phase!=COH_DB_WAIT_PLAYERS&&d.phase!=COH_DB_CHARACTERS)
        return finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_DB,COH_STATE);
    if(d.phase!=COH_DB_CHARACTERS)return COH_OK;
    CohDbPlayers p={0};status=coh_db_session_players(x->db,&p);
    if(status==COH_OK&&(d.player_lists!=1||d.login_requests!=1||!list_valid(&p)))status=COH_STATE;
    uint32_t slots=p.max_slots,base=p.base_slots,bonus=p.bonus_slots;
    coh_db_wipe(&p,sizeof(p));
    if(status!=COH_OK)return finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_LIST,status);
    if(cancelled(cancel))return cancel_now(x);
    /* No caller can see success until retained secrets/controllers are gone. */
    status=finish(x,COH_AUTH_DB_DEV_COMPLETE,COH_AUTH_DB_DEV_FAILURE_NONE,COH_OK);
    x->d.slots=slots;x->d.base_slots=base;x->d.bonus_slots=bonus;
    x->d.complete_matching_list=1;x->d.all_slots_empty_unlocked=1;return status;
}
CohStatus coh_auth_db_development_service(CohAuthDbDevelopmentOwner *x,uint64_t now,CohCancel cancel) {
    if(!x)return COH_INVALID;
    if(x->busy||!active(x))return COH_STATE;
    x->busy=1;CohStatus status;
    if(now<x->clock_ms)status=finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_INPUT,COH_INVALID);
    else if(now-x->start_ms>=AD_TOTAL_MS)status=finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_TIMEOUT,COH_STATE);
    else if(cancelled(cancel))status=cancel_now(x);
    else {
        x->clock_ms=now;
        if(x->d.phase==COH_AUTH_DB_DEV_DB)status=db_service(x,now,cancel);
        else {
            status=coh_login_service(x->auth,now,cancel);snapshot(x);
            if(status==COH_CANCELLED)status=cancel_now(x);
            else if(status!=COH_OK)status=finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_AUTH,status);
            else if(x->d.auth_phase==COH_LOGIN_SHARDS_READY)status=choose_shard(x,now,cancel);
            else if(x->d.auth_phase==COH_LOGIN_AUTHORIZED)status=bridge(x,now,cancel);
            else if(x->d.auth_phase<COH_LOGIN_CONNECTING||x->d.auth_phase>COH_LOGIN_AUTHORIZED)
                status=finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_AUTH,COH_STATE);
        }
    }
    x->busy=0;return status;
}
CohStatus coh_auth_db_development_timeout(CohAuthDbDevelopmentOwner *x) {
    if(!x)return COH_INVALID;
    if(x->busy||!active(x))return COH_STATE;
    x->busy=1;CohStatus status=finish(x,COH_AUTH_DB_DEV_FAILED,COH_AUTH_DB_DEV_FAILURE_TIMEOUT,COH_STATE);
    x->busy=0;return status;
}
CohStatus coh_auth_db_development_cancel(CohAuthDbDevelopmentOwner *x) {
    if(!x)return COH_INVALID;
    if(x->busy||!active(x))return COH_STATE;
    x->busy=1;CohStatus status=cancel_now(x);x->busy=0;return status;
}
CohStatus coh_auth_db_development_close(CohAuthDbDevelopmentOwner *x) {
    if(!x)return COH_INVALID;
    if(x->busy)return COH_STATE;
    x->busy=1;
    if(x->d.phase==COH_AUTH_DB_DEV_IDLE||active(x))
        (void)finish(x,COH_AUTH_DB_DEV_CLOSED,COH_AUTH_DB_DEV_FAILURE_NONE,COH_STATE);
    x->busy=0;return COH_OK;
}
CohStatus coh_auth_db_development_destroy(CohAuthDbDevelopmentOwner **owner) {
    if(!owner)return COH_INVALID;
    CohAuthDbDevelopmentOwner *x=*owner;if(!x)return COH_OK;
    if(overlap(owner,sizeof(*owner),x,sizeof(*x))||
       overlap(owner,sizeof(*owner),x->config.crypto,sizeof(*x->config.crypto)))return COH_INVALID;
    if(x->busy)return COH_STATE;
    (void)coh_auth_db_development_close(x);
    coh_auth_wipe(x,sizeof(*x));free(x);*owner=NULL;return COH_OK;
}
CohStatus coh_auth_db_development_diagnostics(const CohAuthDbDevelopmentOwner *x,
    CohAuthDbDevelopmentDiagnostics *out) {
    if(!x||!out)return COH_INVALID;
    if(x->busy)return COH_STATE;
    if(overlap(out,sizeof(*out),x,sizeof(*x))||
       overlap(out,sizeof(*out),x->config.crypto,sizeof(*x->config.crypto)))return COH_INVALID;
    *out=x->d;return COH_OK;
}
