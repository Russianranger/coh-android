/* Explicit platform/owner doubles for the NEW CLI only. No controller/socket,
 * original server, private file, Windows API or qualified owner executes. */
#define _GNU_SOURCE
#include "fresh_probe_platform.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct FreshProbeLease {int preflight;};
struct CohFreshCharacterOwner {CohFreshCharacterDiagnostics result;};
static struct FreshProbeLease platform;
static struct CohFreshCharacterOwner character;
static unsigned opened,configured,before,created,begun,serviced,timed_out;
static unsigned closed,owner_destroyed,finished,platform_destroyed,ticks,diags;
static const char *account_storage,*password_storage;
static const uint8_t *name_storage;
static size_t name_bytes;
static const CohFreshCharacterConfig *config_storage;
static int is(const char *name) {
    const char *which=getenv("FRESH_PROBE_TEST_CASE");return which&&!strcmp(which,name);
}
static void check(int value) {if(!value)abort();}
static int wiped(const void *p,size_t n) {
    const uint8_t *b=p;uint8_t sum=0;size_t i;for(i=0;i<n;i++)sum|=b[i];return sum==0;
}
void coh_auth_wipe(void *p,size_t n) {volatile uint8_t *b=p;while(n--)*b++=0;}
static void local_wipes(void) {
    if(begun) {
        check(wiped(account_storage,15)&&wiped(password_storage,17)&&wiped(name_storage,name_bytes));
        check(wiped(config_storage,sizeof(*config_storage)));
    }
}
FreshProbeLease *fresh_probe_platform_open(int preflight,const char *path) {
    check(!opened++);platform.preflight=preflight;
    check(preflight?path==NULL:path&&!strcmp(path,"PRIVATE_POLICY_SENTINEL"));
    return is("open-null")?NULL:&platform;
}
CohStatus fresh_probe_platform_config(FreshProbeLease *p,CohFreshCharacterConfig *out) {
    check(p==&platform&&opened==1&&!configured++&&!finished);
    memset(out,0x5a,sizeof(*out));
    return is("config-fail")?COH_IO:COH_OK;
}
CohStatus fresh_probe_platform_before_begin(FreshProbeLease *p) {
    check(p==&platform&&!platform.preflight&&configured==1&&!before++&&!created);
    return is("before-fail")?COH_NOT_FOUND:COH_OK;
}
uint64_t fresh_probe_monotonic_ms(void) {
    check(!platform.preflight&&created&&ticks<4);ticks++;
    if(ticks==1)return 100;
    if(is("timeout"))return 32100;
    if(is("clock-backwards"))return 99;
    return 101;
}
void fresh_probe_pause(void) {check(0);}
CohFreshCharacterOwner *coh_fresh_character_create(const CohFreshCharacterConfig *config) {
    check(before==1&&!created++&&!finished);config_storage=config;
    memset(&character,0,sizeof(character));return is("create-null")?NULL:&character;
}
CohStatus coh_fresh_character_begin(CohFreshCharacterOwner *p,const char *account,
    const char *password,CohBytes name,uint64_t now) {
    check(p==&character&&now==100&&!begun++&&!finished);
    check(account[0]&&password[0]&&name.size>0&&name.size<=63);
    account_storage=account;password_storage=password;name_storage=name.data;name_bytes=name.size;
    p->result.begin_attempted=1;
    if(is("begin-fail")) {
        p->result.phase=COH_FRESH_CHARACTER_FAILED;p->result.failure=COH_FRESH_CHARACTER_FAILURE_INPUT;
        p->result.status=COH_INVALID;return COH_INVALID;
    }
    return COH_OK;
}
static void result(CohFreshCharacterDiagnostics *d) {
    memset(d,0,sizeof(*d));d->phase=COH_FRESH_CHARACTER_COMPLETE;d->status=COH_OK;
    d->begin_attempted=d->shard_attempted=d->bridge_attempted=d->creation_attempted=d->retirement_attempted=1;
    d->actual_grant_verified=d->matching_empty_list_verified=d->creation_request_queued=d->allocated_offer_observed=1;
    d->private_offer_retired=d->container_uninitialized=d->persistent_allocation_possible=1;
    d->private_name_wiped=d->bridge_temporaries_wiped=d->controllers_destroyed=d->cleanup_cancel_close_used=1;
    d->observed_auth_phase=COH_LOGIN_AUTHORIZED;d->observed_db_phase=COH_DB_HANDOFF_READY;
    d->final_auth_phase=COH_LOGIN_CLOSED;d->final_db_phase=COH_DB_CANCELLED;
    d->session_generation=d->receipt_generation=d->selection_generation=1;
    d->provisional_development_policy=d->development_skip_requested=1;
#define BAD_ONE(field) if(is("owner-bad-" #field))d->field=0
#define BAD_ZERO(field) if(is("owner-bad-" #field))d->field=1
    BAD_ONE(begin_attempted);BAD_ONE(shard_attempted);BAD_ONE(bridge_attempted);
    BAD_ONE(creation_attempted);BAD_ONE(retirement_attempted);BAD_ONE(actual_grant_verified);
    BAD_ONE(matching_empty_list_verified);BAD_ONE(creation_request_queued);BAD_ONE(allocated_offer_observed);
    BAD_ONE(private_offer_retired);BAD_ONE(container_uninitialized);BAD_ONE(persistent_allocation_possible);
    BAD_ONE(private_name_wiped);BAD_ONE(bridge_temporaries_wiped);BAD_ONE(controllers_destroyed);
    BAD_ONE(cleanup_cancel_close_used);BAD_ONE(session_generation);BAD_ONE(receipt_generation);
    BAD_ONE(selection_generation);BAD_ONE(provisional_development_policy);BAD_ONE(development_skip_requested);
    BAD_ZERO(actual_server_development_skip_observed);BAD_ZERO(normal_version_admitted);
    BAD_ZERO(checksum_reference_admitted);BAD_ZERO(initialized_character);BAD_ZERO(persistent_rollback_claimed);
    BAD_ZERO(map_socket_opened);BAD_ZERO(map_character_body_sent);BAD_ZERO(sends_ready);
    BAD_ZERO(sends_received_character);BAD_ZERO(sends_full_update_ack);BAD_ZERO(current_world_verified);
    BAD_ZERO(actor_publication);BAD_ZERO(world_authority);
#undef BAD_ONE
#undef BAD_ZERO
    if(is("owner-bad-phase"))d->phase=COH_FRESH_CHARACTER_FAILED;
    if(is("owner-bad-status"))d->status=COH_IO;
    if(is("owner-bad-failure"))d->failure=COH_FRESH_CHARACTER_FAILURE_OFFER;
    if(is("owner-bad-observed_auth_phase"))d->observed_auth_phase=COH_LOGIN_CLOSED;
    if(is("owner-bad-observed_db_phase"))d->observed_db_phase=COH_DB_CANCELLED;
    if(is("owner-bad-final_auth_phase"))d->final_auth_phase=COH_LOGIN_AUTHORIZED;
    if(is("owner-bad-final_db_phase"))d->final_db_phase=COH_DB_HANDOFF_READY;
}
CohStatus coh_fresh_character_service(CohFreshCharacterOwner *p,uint64_t now,CohCancel cancellation) {
    check(p==&character&&now==101&&!cancellation.poll&&!cancellation.context&&!serviced++&&!closed);
    local_wipes();result(&p->result);
    if(is("service-fail")||is("first-failure")) {
        p->result.phase=COH_FRESH_CHARACTER_FAILED;p->result.failure=COH_FRESH_CHARACTER_FAILURE_DB;
        p->result.status=COH_IO;return COH_IO;
    }
    return COH_OK;
}
CohStatus coh_fresh_character_timeout(CohFreshCharacterOwner *p) {
    check(p==&character&&!serviced&&!timed_out++&&!closed);local_wipes();
    p->result.phase=COH_FRESH_CHARACTER_FAILED;p->result.failure=COH_FRESH_CHARACTER_FAILURE_TIMEOUT;
    p->result.status=COH_STATE;return COH_STATE;
}
CohStatus coh_fresh_character_close(CohFreshCharacterOwner *p) {
    check(p==&character&&!closed++&&!finished);local_wipes();
    return is("owner-close-fail")?COH_IO:COH_OK;
}
CohStatus coh_fresh_character_diagnostics(const CohFreshCharacterOwner *p,CohFreshCharacterDiagnostics *out) {
    check(p==&character&&!owner_destroyed);diags++;
    if(is("owner-diag-fail"))return COH_IO;
    *out=p->result;return COH_OK;
}
CohStatus coh_fresh_character_destroy(CohFreshCharacterOwner **p) {
    check(p&&*p==&character&&closed==1&&!owner_destroyed++&&!finished);local_wipes();
    if(is("owner-destroy-fail"))return COH_IO;
    *p=NULL;return COH_OK;
}
CohStatus fresh_probe_platform_finish(FreshProbeLease *p) {
    check(p==&platform&&!finished++&&(!begun||owner_destroyed==1));local_wipes();
    return is("finish-fail")||is("first-failure")?COH_NOT_FOUND:COH_OK;
}
CohStatus fresh_probe_platform_diagnostics(const FreshProbeLease *p,FreshProbePlatformDiagnostics *out) {
    check(p==&platform&&finished==1&&!platform_destroyed);memset(out,0,sizeof(*out));
    out->initialization_verified=out->checksum_measured_from_actual_probe=out->fresh_connect_entropy=1;
    out->no_live_tcp_handles=out->no_live_udp_handles=out->transport_cleanup_complete=1;
    out->private_policy_handle_closed=out->map_process_handle_closed=out->cleanup_complete=1;
    if(!platform.preflight)out->supplied_map_policy_admitted=out->map_process_file_generation_before=
        out->map_process_file_generation_after=1;
#define BAD(field) if(is("platform-bad-" #field))out->field=!out->field
    BAD(initialization_verified);BAD(supplied_map_policy_admitted);
    BAD(map_process_file_generation_before);BAD(map_process_file_generation_after);
    BAD(checksum_measured_from_actual_probe);BAD(fresh_connect_entropy);
    BAD(no_live_tcp_handles);BAD(no_live_udp_handles);BAD(transport_cleanup_complete);
    BAD(private_policy_handle_closed);BAD(map_process_handle_closed);BAD(cleanup_complete);
#undef BAD
    return is("platform-diag-fail")?COH_IO:COH_OK;
}
CohStatus fresh_probe_platform_destroy(FreshProbeLease **p) {
    check(p&&*p==&platform&&finished==1&&!platform_destroyed++);
    if(is("platform-destroy-fail"))return COH_IO;
    *p=NULL;return COH_OK;
}
/* Verify every independent finalizer was attempted without adding receipt
 * fields or turning a test-control result into real platform admission. */
static void verify(void) {
    if(is("input-refusal")){check(!opened&&!created&&!begun);return;}
    if(is("input-refusal-io")) {
        check(!opened&&!created&&!begun&&ferror(stdin));check(fclose(stdin)==0);return;
    }
    check(opened==1);
    if(is("open-null")){check(!configured&&!finished&&!platform_destroyed);return;}
    if(is("owner-destroy-fail")) {
        check(configured==1&&created==1&&begun==1&&closed==1&&owner_destroyed==1&&
              !finished&&!platform_destroyed);return;
    }
    check(configured==1&&finished==1&&platform_destroyed==1);
    if(platform.preflight){check(!before&&!created&&!begun);return;}
    if(is("config-fail")){check(!before&&!created&&!begun);return;}
    check(before==1);
    if(is("before-fail")){check(!created&&!begun);return;}
    check(created==1);
    if(is("create-null")){check(!begun&&!closed&&!owner_destroyed);return;}
    check(begun==1&&closed==1&&owner_destroyed==1&&diags>=1);
}
/* Registration is test-only and has no platform effect. */
#if defined(__GNUC__)
static ssize_t input_error(void *cookie,char *out,size_t capacity) {
    static const char input[]="FixtureUser\nPrivatePassword\nFresh Fixture\n";
    size_t *at=cookie,remaining=sizeof(input)-1-*at;
    if(!remaining){errno=EIO;return -1;}
    if(capacity>remaining)capacity=remaining;
    memcpy(out,input+*at,capacity);*at+=capacity;return (ssize_t)capacity;
}
__attribute__((constructor)) static void install_verify(void) {
    check(atexit(verify)==0);
    if(is("input-refusal-io")) {
        static size_t at;
        cookie_io_functions_t operations={input_error,NULL,NULL,NULL};
        stdin=fopencookie(&at,"r",operations);check(stdin!=NULL);
    }
}
#else
#error This explicit host-only test double requires its admitted GCC constructor.
#endif
