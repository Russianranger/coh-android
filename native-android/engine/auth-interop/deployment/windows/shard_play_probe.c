/* Nonshipping scope: fresh encrypted Auth login -> shard 1 -> AC_PLAY_OK.
 * Credentials arrive only on the private stdin pipe. Grant values never leave
 * this process. No DB login/UDP/Map client is linked into this executable. */
#ifdef _WIN32
#include "winsock_compat.h"
static uint64_t now_ms(void) { return GetTickCount64(); }
static void pause_ms(void) { Sleep(2); }
#else
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <time.h>
static uint64_t now_ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000; }
static void pause_ms(void) { struct timespec t={0,2000000}; nanosleep(&t,NULL); }
#endif
#include "../../../login/coh_login.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int zeroed(const void *value,size_t size) {
    const unsigned char *p=value;unsigned char sum=0;
    for(size_t i=0;i<size;i++) sum|=p[i];
    return sum==0;
}
static int line(char *out,size_t size) {
    size_t at=0;int c;
    while((c=fgetc(stdin))!=EOF && c!='\n') {
        if(c<32 || c>126 || at+1>=size) return 0;
        out[at++]=(char)c;
    }
    return c=='\n' && at!=0;
}
static int shard_valid(const CohAuthShard *s) {
    static const unsigned char loopback[4]={127,0,0,1};
    return s->id==1 && s->status==1 && s->port==7000 && !memcmp(s->ipv4,loopback,4);
}

int main(int argc,char **argv) {
    char account[15]={0},password[17]={0};
    CohAuthShards shards={0};CohLoginAuthorization authorization={0};
    CohLoginDiagnostics before={0},after={0};CohLogin *session=NULL;
    int passed=0,transport_started=0,transport_clean=1,list_valid=0,grant_valid=0;
    int chosen=0,invalidated=0;unsigned send_cap=0;uint64_t start=now_ms();
    CohStatus status=COH_INVALID;char *end=NULL;unsigned long port=0;
    if(argc!=3) goto cleanup;
    port=strtoul(argv[1],&end,10);
    if(!argv[1][0] || !end || *end || port<20000 || port>59999) goto cleanup;
    if(!strcmp(argv[2],"1024"))send_cap=1024;
    else if(!strcmp(argv[2],"7"))send_cap=7;
    else goto cleanup;
    if(!line(account,sizeof(account)) || !line(password,sizeof(password)) || fgetc(stdin)!=EOF) goto cleanup;
#ifdef _WIN32
    if(coh_win_initialize()) {transport_clean=0;goto cleanup;}
    transport_started=1;
    if(coh_win_limits(send_cap,11,0)) goto cleanup;
#else
    (void)transport_started;
#endif
    CohLoginConfig config=coh_login_default_config(coh_auth_openssl_provider());
    config.connect_timeout_ms=3000;config.reply_timeout_ms=10000;
    session=coh_login_create(&config);
    CohNetEndpoint endpoint={{127,0,0,1},(uint16_t)port};
    status=session?coh_login_begin(session,endpoint,account,password,0,0,start):COH_IO;
    coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));
    if(status!=COH_OK) goto cleanup;
    for(;;) {
        status=coh_login_service(session,now_ms(),(CohCancel){0});
        coh_login_diagnostics(session,&before);
        if(status!=COH_OK || now_ms()-start>=20000) break;
        if(before.state==COH_LOGIN_SHARDS_READY && !chosen) {
            list_valid=coh_login_shards(session,&shards)==COH_OK && shards.count==1 && shard_valid(&shards.shards[0]);
            if(!list_valid || before.protocol!=191021 || before.received_frames!=3 || before.password_retained) break;
            if(coh_login_choose(session,1,now_ms())!=COH_OK) break;
            chosen=1;
        }
        if(before.state==COH_LOGIN_AUTHORIZED) break;
        pause_ms();
    }
    grant_valid=chosen && before.state==COH_LOGIN_AUTHORIZED &&
        coh_login_authorization(session,&authorization)==COH_OK &&
        authorization.protocol==191021 && authorization.play.shard_id==1 &&
        /* Public fixture UID was resolved by original SQL account login; never
         * accept another nonzero UID or a swapped UID/cookie field. */
        authorization.play.game_key!=0 && authorization.play.user_id==900001 &&
        shard_valid(&authorization.shard);
    passed=status==COH_OK && list_valid && grant_valid && before.received_frames==4 &&
        before.protocol==191021 && before.shard_count==1 && before.sent_bytes>0 &&
        !before.pending_send_bytes && !before.buffered_receive_bytes && !before.password_retained &&
        !before.remote_failure_command && !before.remote_failure_reason && !before.last_system_error;
cleanup:
    /* Wipe caller copies even on input, transport, parser or allocation failure. */
    coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));
    coh_auth_wipe(&authorization,sizeof(authorization));coh_auth_wipe(&shards,sizeof(shards));
    if(session) {
        coh_login_close(session);coh_login_diagnostics(session,&after);
        invalidated=coh_login_authorization(session,&authorization)==COH_STATE && zeroed(&authorization,sizeof(authorization));
        coh_auth_wipe(&authorization,sizeof(authorization));
        coh_login_destroy(session);
    }
#ifdef _WIN32
    transport_clean=transport_clean && coh_win_open_handles()==0;
    if(transport_started && coh_win_finish()) transport_clean=0;
#endif
    int wiped=zeroed(account,sizeof(account)) && zeroed(password,sizeof(password)) &&
        zeroed(&authorization,sizeof(authorization)) && zeroed(&shards,sizeof(shards));
    int closed=after.state==COH_LOGIN_CLOSED && after.sockets_opened==1 && after.sockets_closed==1 &&
        !after.pending_send_bytes && !after.buffered_receive_bytes && !after.password_retained;
    passed=passed && wiped && invalidated && closed && transport_clean;
    printf("{\"schema\":\"coh-selected-shard-play-probe-v1\",\"passed\":%s,\"state\":%d,\"protocol\":%u,\"shards\":%u,\"received_frames\":%llu,\"sent_bytes\":%llu,\"elapsed_ms\":%llu,\"send_cap\":%u,\"selected_shard_verified\":%s,\"live_grant_retained_then_wiped\":%s,\"local_sensitive_buffers_wiped\":%s,\"authorization_invalid_after_close\":%s,\"socket_cleanup_complete\":%s,\"password_retained_after_close\":false,\"db_login_attempted\":false,\"authenticated_db_map_handoff_verified\":false,\"checksum_policy_relaxed\":false,\"nondevelopment_version_admitted\":false,\"real_server_provenance_verified_by_probe\":false}\n",
        passed?"true":"false",before.state,before.protocol,before.shard_count,
        (unsigned long long)before.received_frames,(unsigned long long)before.sent_bytes,
        (unsigned long long)(now_ms()-start),send_cap,list_valid && chosen?"true":"false",
        grant_valid && wiped && invalidated?"true":"false",wiped?"true":"false",
        invalidated?"true":"false",closed && transport_clean?"true":"false");
    return passed?0:1;
}
