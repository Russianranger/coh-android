/* NONSHIPPING actual CLI control flow. A real platform backend is required. */
#include "fresh_probe_platform.h"
#include <stdio.h>
#include <string.h>

static int private_line(char *out,size_t capacity) {
    size_t at=0;int value;
    while((value=fgetc(stdin))!=EOF&&value!='\n') {
        if(value<32||value>126||at+1>=capacity)return 0;
        out[at++]=(char)value;
    }
    return value=='\n'&&at!=0;
}
static int zeroed(const void *p,size_t bytes) {
    const unsigned char *b=p;unsigned char sum=0;size_t i;
    for(i=0;i<bytes;i++)sum|=b[i];
    return sum==0;
}
static void cleanup_failure(CohStatus *status,CohStatus failure) {
    if(*status==COH_OK)*status=failure==COH_OK?COH_STATE:failure;
}
static int expected_limits(const CohFreshCharacterDiagnostics *d) {
    return d->provisional_development_policy==1&&d->development_skip_requested==1&&
        !d->actual_server_development_skip_observed&&!d->normal_version_admitted&&
        !d->checksum_reference_admitted&&!d->initialized_character&&!d->persistent_rollback_claimed&&
        !d->map_socket_opened&&!d->map_character_body_sent&&!d->sends_ready&&
        !d->sends_received_character&&!d->sends_full_update_ack&&!d->current_world_verified&&
        !d->actor_publication&&!d->world_authority;
}
int main(int argc,char **argv) {
    int preflight=argc==2&&!strcmp(argv[1],"--platform-preflight");
    int runtime=argc==3&&!strcmp(argv[1],"--allocate-offer")&&argv[2][0];
    unsigned stage=0,passed=0,owner_clean=1,platform_clean=1;
    char account[15]={0},password[17]={0},name[64]={0};
    CohFreshCharacterConfig config={0};CohFreshCharacterDiagnostics d={0};
    FreshProbePlatformDiagnostics platform={0};
    CohFreshCharacterOwner *owner=NULL;FreshProbeLease *lease=NULL;
    CohStatus status=COH_INVALID;uint64_t start=0;
    if(!preflight&&!runtime)goto cleanup;
    if(runtime&&(!private_line(account,sizeof(account))||!private_line(password,sizeof(password))||
       !private_line(name,sizeof(name))||fgetc(stdin)!=EOF||ferror(stdin)))goto cleanup;
    stage=1;lease=fresh_probe_platform_open(preflight,runtime?argv[2]:NULL);
    if(!lease){platform_clean=0;goto cleanup;}
    status=fresh_probe_platform_config(lease,&config);if(status!=COH_OK)goto cleanup;
    if(preflight){stage=5;status=COH_OK;passed=1;goto cleanup;}
    stage=2;status=fresh_probe_platform_before_begin(lease);if(status!=COH_OK)goto cleanup;
    owner=coh_fresh_character_create(&config);if(!owner){status=COH_LIMIT;goto cleanup;}
    start=fresh_probe_monotonic_ms();
    status=coh_fresh_character_begin(owner,account,password,
        (CohBytes){(const uint8_t*)name,strlen(name)},start);
    coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));
    coh_auth_wipe(name,sizeof(name));coh_auth_wipe(&config,sizeof(config));
    if(status!=COH_OK)goto cleanup;
    stage=3;
    for(;;) {
        uint64_t now=fresh_probe_monotonic_ms();
        if(now<start||now-start>=32000){status=coh_fresh_character_timeout(owner);break;}
        status=coh_fresh_character_service(owner,now,(CohCancel){0});
        CohStatus observed=coh_fresh_character_diagnostics(owner,&d);
        if(observed!=COH_OK){owner_clean=0;cleanup_failure(&status,observed);break;}
        if(status!=COH_OK||(d.phase!=COH_FRESH_CHARACTER_AUTHENTICATING&&
           d.phase!=COH_FRESH_CHARACTER_WAIT_LIST&&d.phase!=COH_FRESH_CHARACTER_WAIT_OFFER))break;
        fresh_probe_pause();
    }
    passed=status==COH_OK&&d.phase==COH_FRESH_CHARACTER_COMPLETE&&d.failure==COH_FRESH_CHARACTER_FAILURE_NONE&&
        d.status==COH_OK&&d.begin_attempted==1&&d.shard_attempted==1&&d.bridge_attempted==1&&
        d.creation_attempted==1&&d.retirement_attempted==1&&d.actual_grant_verified==1&&
        d.matching_empty_list_verified==1&&d.creation_request_queued==1&&d.allocated_offer_observed==1&&
        d.private_offer_retired==1&&d.container_uninitialized==1&&d.persistent_allocation_possible==1&&
        d.private_name_wiped==1&&d.bridge_temporaries_wiped==1&&d.controllers_destroyed==1&&
        d.cleanup_cancel_close_used==1&&d.observed_auth_phase==COH_LOGIN_AUTHORIZED&&
        d.observed_db_phase==COH_DB_HANDOFF_READY&&d.final_auth_phase==COH_LOGIN_CLOSED&&
        d.final_db_phase==COH_DB_CANCELLED&&d.session_generation==1&&d.receipt_generation==1&&
        d.selection_generation==1&&expected_limits(&d);
    if(passed)stage=4;else cleanup_failure(&status,COH_STATE);
cleanup:
    coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));
    coh_auth_wipe(name,sizeof(name));coh_auth_wipe(&config,sizeof(config));
    if(owner) {
        CohStatus closed_status=coh_fresh_character_close(owner);
        if(closed_status!=COH_OK){owner_clean=0;cleanup_failure(&status,closed_status);}
        CohStatus observed=coh_fresh_character_diagnostics(owner,&d);
        if(observed!=COH_OK){owner_clean=0;cleanup_failure(&status,observed);}
        CohStatus destroyed=coh_fresh_character_destroy(&owner);
        if(destroyed!=COH_OK||owner){owner_clean=0;cleanup_failure(&status,destroyed);}
    }
    /* The provider/transport lease is borrowed by both controllers. If an
     * unexpected consuming destroy refuses, retain that dependent lease until
     * process exit; never finalize it beneath a still-live owner. */
    if(lease&&!owner) {
        CohStatus finished=fresh_probe_platform_finish(lease);
        if(finished!=COH_OK){platform_clean=0;cleanup_failure(&status,finished);}
        CohStatus observed=fresh_probe_platform_diagnostics(lease,&platform);
        if(observed!=COH_OK){platform_clean=0;cleanup_failure(&status,observed);}
        CohStatus destroyed=fresh_probe_platform_destroy(&lease);
        if(destroyed!=COH_OK||lease){platform_clean=0;cleanup_failure(&status,destroyed);}
    } else platform_clean=0;
    unsigned sensitive_wiped=zeroed(account,sizeof(account))&&zeroed(password,sizeof(password))&&
        zeroed(name,sizeof(name))&&zeroed(&config,sizeof(config));
    passed=passed&&sensitive_wiped&&owner_clean&&!owner&&platform_clean&&!lease&&platform.initialization_verified==1&&
        platform.checksum_measured_from_actual_probe==1&&platform.fresh_connect_entropy==1&&
        platform.no_live_tcp_handles==1&&platform.no_live_udp_handles==1&&platform.transport_cleanup_complete==1&&
        platform.private_policy_handle_closed==1&&platform.map_process_handle_closed==1&&platform.cleanup_complete==1&&
        (preflight?(!platform.supplied_map_policy_admitted&&!platform.map_process_file_generation_before&&
            !platform.map_process_file_generation_after):(platform.supplied_map_policy_admitted==1&&
            platform.map_process_file_generation_before==1&&platform.map_process_file_generation_after==1));
    if(!passed)cleanup_failure(&status,COH_STATE);
    printf("{\"schema\":\"%s\",\"passed\":%s,\"stage\":%u,\"status\":%d,\"phase\":%d,\"failure\":%d,"
        "\"session_generation\":%u,\"receipt_generation\":%u,\"selection_generation\":%u,"
        "\"offer_retired\":%u,\"container_uninitialized\":%u,\"persistent_allocation_possible\":%u,"
        "\"local_sensitive_buffers_wiped\":%s,\"owner_cleanup_complete\":%s,\"platform_cleanup_complete\":%s,"
        "\"supplied_map_process_file_policy_admitted\":%s,\"Map_READY_observed_by_probe\":false,"
        "\"actual_server_development_skip_observed\":false,\"normal_version_admitted\":false,"
        "\"checksum_reference_admitted\":false,\"persistent_rollback_claimed\":false,"
        "\"Map_socket_or_body_or_READY_or_ACK\":false,\"world_authority\":false}\n",
        preflight?"coh-fresh-character-platform-preflight-v1":"coh-fresh-character-offer-probe-v1",
        passed?"true":"false",stage,status,d.phase,d.failure,d.session_generation,d.receipt_generation,
        d.selection_generation,d.private_offer_retired,d.container_uninitialized,d.persistent_allocation_possible,
        sensitive_wiped?"true":"false",owner_clean&&!owner?"true":"false",platform_clean&&!lease?"true":"false",
        platform.supplied_map_policy_admitted?"true":"false");
    return passed?0:1;
}
