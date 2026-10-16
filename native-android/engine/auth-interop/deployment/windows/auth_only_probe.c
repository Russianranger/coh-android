/* Only the deliberately known disposable fixture is supported. No arbitrary
 * account, credential or remote endpoint input; stdout is redacted diagnostics. */
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
#include "fixture_constants.h"
#include <openssl/crypto.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc,char **argv) {
    if(argc!=3) return 2;
    char *end=NULL; unsigned long port=strtoul(argv[1],&end,10);
    if(!argv[1][0] || !end || *end || port<20000 || port>59999) return 2;
    int valid=!strcmp(argv[2],"valid"),wrong=!strcmp(argv[2],"wrong-password"),missing=!strcmp(argv[2],"missing-account"),bad=!strcmp(argv[2],"corrupt-frame");
    if(!valid && !wrong && !missing && !bad) return 2;
    int transport_clean=1;
#ifdef _WIN32
    if(coh_win_initialize() || coh_win_limits(7,11,bad)) return 3;
#else
    if(bad) return 2; /* Fault injection belongs only to the isolated adapter. */
#endif
    char account[15]=COH_FIXTURE_ACCOUNT,password[17]=COH_FIXTURE_PASSWORD;
    if(wrong) password[0]^=1;
    if(missing) memcpy(account,"cohabsent01",12);
    CohLoginConfig config=coh_login_default_config(coh_auth_openssl_provider());
    config.connect_timeout_ms=3000;config.reply_timeout_ms=10000;
    CohLogin *session=coh_login_create(&config);
    CohLoginDiagnostics before={0},after={0};
    CohAuthShards shards={0};
    CohNetEndpoint endpoint={{127,0,0,1},(uint16_t)port};
    uint64_t start=now_ms();
    CohStatus status=session?coh_login_begin(session,endpoint,account,password,0,0,start):COH_IO;
    coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));
    if(status==COH_OK) for(;;) {
        status=coh_login_service(session,now_ms(),(CohCancel){0});
        coh_login_diagnostics(session,&before);
        if(status!=COH_OK || before.state==COH_LOGIN_SHARDS_READY || now_ms()-start>=15000) break;
        pause_ms();
    }
    int list_valid=session && before.state==COH_LOGIN_SHARDS_READY && coh_login_shards(session,&shards)==COH_OK && shards.count==0;
    int passed=0;
    if(valid) passed=status==COH_OK && list_valid && before.protocol==191021 && before.received_frames==3 && before.sent_bytes>0 && !before.pending_send_bytes && !before.password_retained;
    if(wrong || missing) passed=before.state==COH_LOGIN_FAILED && before.protocol==191021 && before.remote_failure_command==1 && before.remote_failure_reason==(wrong?3:2);
    if(bad) passed=before.state==COH_LOGIN_FAILED && before.protocol==191021 && before.received_frames==1 && before.remote_failure_command==0 && !list_valid;
    if(session) { coh_login_close(session);coh_login_diagnostics(session,&after);coh_login_destroy(session); }
#ifdef _WIN32
    transport_clean=coh_win_open_handles()==0;
    if(coh_win_finish()) transport_clean=0;
#endif
    passed=passed && transport_clean && after.state==COH_LOGIN_CLOSED && after.sockets_opened==1 && after.sockets_closed==1 && !after.password_retained && !after.pending_send_bytes && !after.buffered_receive_bytes;
    printf("{\"schema\":\"coh-auth-only-probe-v1\",\"passed\":%s,\"case\":\"%s\",\"state\":%d,\"protocol\":%u,\"shards\":%u,\"received_frames\":%llu,\"sent_bytes\":%llu,\"failure_command\":%u,\"failure_reason\":%u,\"system_error\":%d,\"elapsed_ms\":%llu,\"socket_cleanup_complete\":%s,\"password_retained_after_close\":false,\"db_handoff_attempted\":false,\"real_server_provenance_verified_by_probe\":false,\"openssl_runtime\":\"%s\"}\n",
       passed?"true":"false",argv[2],before.state,before.protocol,before.shard_count,(unsigned long long)before.received_frames,(unsigned long long)before.sent_bytes,before.remote_failure_command,before.remote_failure_reason,before.last_system_error,(unsigned long long)(now_ms()-start),transport_clean && after.sockets_opened==after.sockets_closed?"true":"false",OpenSSL_version(OPENSSL_VERSION));
    coh_auth_wipe(&shards,sizeof(shards));
    return passed?0:1;
}
