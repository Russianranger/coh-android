/* NONSHIPPING: one fresh real Auth grant -> original development-policy DB
 * login -> complete matching empty list. Never choose/create/enter a Map. */
#ifdef COH_DB_DEVELOPMENT_PROBE_TEST
#include "test_db_development_probe_api.h"
#else
#include "winsock_compat.h"
#include "db_udp_winsock.h"
#include "auth_db_development_owner.h"
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <stdio.h>
static uint64_t probe_now(void) {return GetTickCount64();}
static void probe_pause(void) {Sleep(2);}
static int probe_entropy(uint32_t *out) {return RAND_bytes((unsigned char *)out,(int)sizeof(*out))==1&&*out!=0;}
/* The digest is measured from this actual executable file, not invented or
 * admitted as a reference. No path, file bytes or digest leave this process. */
static int probe_checksum(uint8_t out[16]) {
    wchar_t path[32768]={0};unsigned char block[16384]={0},digest[EVP_MAX_MD_SIZE]={0};
    HANDLE file=INVALID_HANDLE_VALUE;EVP_MD_CTX *ctx=NULL;int valid=0;unsigned bytes=0;
    DWORD length=GetModuleFileNameW(NULL,path,(DWORD)(sizeof(path)/sizeof(path[0])));
    if(!length||length>=(DWORD)(sizeof(path)/sizeof(path[0])))goto done;
    file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
    if(file==INVALID_HANDLE_VALUE)goto done;
    BY_HANDLE_FILE_INFORMATION info;LARGE_INTEGER size;
    if(!GetFileInformationByHandle(file,&info)||(info.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))||
       !GetFileSizeEx(file,&size)||size.QuadPart<=0||size.QuadPart>16*1024*1024)goto done;
    ctx=EVP_MD_CTX_new();if(!ctx||EVP_DigestInit_ex(ctx,EVP_md5(),NULL)!=1)goto done;
    uint64_t total=0;
    for(;;) {
        DWORD got=0;if(!ReadFile(file,block,(DWORD)sizeof(block),&got,NULL))goto done;
        if(!got)break;
        total+=got;if(total>(uint64_t)size.QuadPart||EVP_DigestUpdate(ctx,block,got)!=1)goto done;
        coh_auth_wipe(block,sizeof(block));
    }
    if(total!=(uint64_t)size.QuadPart||EVP_DigestFinal_ex(ctx,digest,&bytes)!=1||bytes!=16)goto done;
    memcpy(out,digest,16);valid=1;
done:
    EVP_MD_CTX_free(ctx);
    if(file!=INVALID_HANDLE_VALUE&&!CloseHandle(file))valid=0;
    coh_auth_wipe(path,sizeof(path));coh_auth_wipe(block,sizeof(block));coh_auth_wipe(digest,sizeof(digest));
    if(!valid)coh_auth_wipe(out,16);
    return valid;
}
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int zeroed(const void *p,size_t n) {
    const unsigned char *b=p;unsigned char sum=0;for(size_t i=0;i<n;i++)sum|=b[i];return sum==0;
}
static int private_line(char *out,size_t capacity) {
    size_t at=0;int c;
    while((c=fgetc(stdin))!=EOF&&c!='\n') {
        if(c<32||c>126||at+1>=capacity)return 0;
        out[at++]=(char)c;
    }
    return c=='\n'&&at!=0;
}
int main(int argc,char **argv) {
    char account[15]={0},password[17]={0};CohAuthDbDevelopmentConfig config={0};
    CohAuthDbDevelopmentDiagnostics d={0};CohAuthDbDevelopmentOwner *owner=NULL;
    CohDbWinDiagnostics udp={0};CohStatus status=COH_INVALID;
    int tcp_started=0,udp_started=0,transports_clean=1,owner_clean=1,checksum_measured=0,passed=0;
    int stage=0,preflight=argc==2&&!strcmp(argv[1],"--platform-preflight");
    uint64_t start=probe_now();unsigned long port=0;char *end=NULL;
    if(!preflight) {
        if(argc!=2||!argv[1][0])goto cleanup;
        for(const char *p=argv[1];*p;p++)if(*p<'0'||*p>'9')goto cleanup;
        port=strtoul(argv[1],&end,10);if(!end||*end||port<20000||port>59999)goto cleanup;
        if(!private_line(account,sizeof(account))||!private_line(password,sizeof(password))||fgetc(stdin)!=EOF)goto cleanup;
    }
    stage=1;
    if(coh_win_initialize()){transports_clean=0;goto cleanup;}tcp_started=1;
    stage=2;
    if(coh_win_limits(1024,11,0))goto cleanup;
    /* Even a failed UDP initialization may retain an owned WSA reference.
     * Its independent finalizer therefore runs after every attempt. */
    stage=3;udp_started=1;if(coh_db_win_initialize()){transports_clean=0;goto cleanup;}
    config.auth_endpoint=(CohNetEndpoint){{127,0,0,1},(uint16_t)port};
    config.crypto=coh_auth_openssl_provider();
    stage=4;if(!probe_entropy(&config.connect_id))goto cleanup;
    stage=5;if(!probe_checksum(config.executable_checksum))goto cleanup;
    checksum_measured=1;
    if(preflight){stage=10;status=COH_OK;passed=1;goto cleanup;}
    stage=6;
    owner=coh_auth_db_development_create(&config);if(!owner){status=COH_LIMIT;goto cleanup;}
    stage=7;
    status=coh_auth_db_development_begin(owner,account,password,start);
    coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));
    coh_auth_wipe(&config,sizeof(config));
    if(status!=COH_OK)goto cleanup;
    stage=8;for(;;) {
        uint64_t now=probe_now();
        if(now<start||now-start>=32000){status=coh_auth_db_development_timeout(owner);break;}
        status=coh_auth_db_development_service(owner,now,(CohCancel){0});
        if(coh_auth_db_development_diagnostics(owner,&d)!=COH_OK){owner_clean=0;break;}
        if(status!=COH_OK||(d.phase!=COH_AUTH_DB_DEV_AUTH&&d.phase!=COH_AUTH_DB_DEV_DB))break;
        probe_pause();
    }
    if(d.phase==COH_AUTH_DB_DEV_COMPLETE)stage=9;
    passed=status==COH_OK&&d.phase==COH_AUTH_DB_DEV_COMPLETE&&d.failure==COH_AUTH_DB_DEV_FAILURE_NONE&&
        d.status==COH_OK&&d.begun==1&&d.grant_consumed==1&&d.selected_shard_verified==1&&
        d.complete_matching_list==1&&d.all_slots_empty_unlocked==1&&d.controllers_destroyed==1&&
        d.cleanup_cancel_close_used==1&&d.auth_phase==COH_LOGIN_AUTHORIZED&&d.db_phase==COH_DB_CHARACTERS&&
        d.auth_final_phase==COH_LOGIN_CLOSED&&d.db_final_phase==COH_DB_CANCELLED&&
        d.auth_frames==4&&d.db_login_requests==1&&d.db_player_lists==1&&!d.db_queue_updates&&!d.db_unsupported&&
        !d.db_choices&&!d.db_handoffs&&d.slots>0&&d.slots<=COH_DB_SLOTS_MAX&&d.base_slots>0&&d.base_slots<=d.slots&&
        d.development_skip_requested==1&&!d.normal_version_admitted&&!d.checksum_reference_admitted&&
        !d.character_selected&&!d.map_handoff_verified&&!d.current_world_verified;
cleanup:
    coh_auth_wipe(account,sizeof(account));coh_auth_wipe(password,sizeof(password));coh_auth_wipe(&config,sizeof(config));
    if(owner) {
        if(coh_auth_db_development_close(owner)!=COH_OK)owner_clean=0;
        if(coh_auth_db_development_diagnostics(owner,&d)!=COH_OK)owner_clean=0;
        if(coh_auth_db_development_destroy(&owner)!=COH_OK||owner)owner_clean=0;
    }
    if(udp_started&&coh_db_win_finish())transports_clean=0;
    coh_db_win_diagnostics(&udp);
    if(udp_started&&(udp.initialized||udp.active_handles||!udp.cleanup_complete||udp.close_failures||udp.cleanup_failures||
       udp.sockets_created!=udp.sockets_closed))transports_clean=0;
    if(tcp_started) {
        if(coh_win_open_handles())transports_clean=0;
        if(coh_win_finish())transports_clean=0;
        if(coh_win_open_handles())transports_clean=0;
    }
    int wiped=zeroed(account,sizeof(account))&&zeroed(password,sizeof(password))&&zeroed(&config,sizeof(config));
    passed=passed&&wiped&&owner_clean&&!owner&&transports_clean&&tcp_started&&udp_started&&
        checksum_measured&&udp.sockets_created==(unsigned)!preflight&&udp.sockets_closed==(unsigned)!preflight;
    printf("{\"schema\":\"%s\",\"passed\":%s,\"probe_stage\":%d,\"phase\":%d,\"failure\":%d,\"status\":%d,"
        "\"auth_phase\":%d,\"db_phase\":%d,\"auth_final_phase\":%d,\"db_final_phase\":%d,"
        "\"begun\":%u,\"grant_consumed\":%u,\"selected_shard_verified\":%u,\"complete_matching_list\":%u,\"all_slots_empty_unlocked\":%u,"
        "\"cleanup_cancel_close_used\":%u,\"controllers_destroyed\":%u,\"slots\":%u,\"base_slots\":%u,\"bonus_slots\":%u,"
        "\"auth_frames\":%llu,\"db_login_requests\":%llu,\"db_player_lists\":%llu,\"db_queue_updates\":%llu,"
        "\"db_unsupported\":%llu,\"db_choices\":%llu,\"db_handoffs\":%llu,\"elapsed_ms\":%llu,"
        "\"development_skip_requested\":%u,\"normal_version_admitted\":%u,\"checksum_reference_admitted\":%u,"
        "\"character_selected\":%u,\"map_handoff_verified\":%u,\"current_world_verified\":%u,"
        "\"checksum_measured_from_actual_probe\":%s,\"local_sensitive_buffers_wiped\":%s,\"owner_cleanup_complete\":%s,"
        "\"socket_cleanup_complete\":%s,\"udp_created\":%u,\"udp_closed\":%u,\"udp_active\":%u,\"udp_close_failures\":%u,"
        "\"udp_cleanup_failures\":%u,\"udp_cleanup_complete\":%u,\"development_skip_source_inference_only\":true,"
        "\"server_development_skip_observed\":false,\"graceful_peer_disconnect_acknowledged\":false,\"real_server_provenance_verified_by_probe\":false}\n",
        preflight?"coh-auth-db-development-platform-preflight-v1":"coh-auth-db-development-list-probe-v1",
        passed?"true":"false",stage,d.phase,d.failure,status,d.auth_phase,d.db_phase,d.auth_final_phase,d.db_final_phase,
        d.begun,d.grant_consumed,d.selected_shard_verified,d.complete_matching_list,d.all_slots_empty_unlocked,
        d.cleanup_cancel_close_used,d.controllers_destroyed,d.slots,d.base_slots,d.bonus_slots,
        (unsigned long long)d.auth_frames,(unsigned long long)d.db_login_requests,(unsigned long long)d.db_player_lists,
        (unsigned long long)d.db_queue_updates,(unsigned long long)d.db_unsupported,(unsigned long long)d.db_choices,
        (unsigned long long)d.db_handoffs,(unsigned long long)(probe_now()-start),d.development_skip_requested,
        d.normal_version_admitted,d.checksum_reference_admitted,d.character_selected,d.map_handoff_verified,d.current_world_verified,
        checksum_measured?"true":"false",wiped?"true":"false",owner_clean&&!owner?"true":"false",transports_clean?"true":"false",
        udp.sockets_created,udp.sockets_closed,udp.active_handles,udp.close_failures,udp.cleanup_failures,udp.cleanup_complete);
    return passed?0:1;
}
