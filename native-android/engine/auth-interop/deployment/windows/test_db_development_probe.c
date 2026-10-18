#define COH_DB_DEVELOPMENT_PROBE_TEST 1
#define main controlled_probe_main
#include "db_development_probe.c"
#undef main

/* These are explicitly synthetic boundary controls, not an Auth/DB server. */
struct CohAuthDbDevelopmentOwner {unsigned marker;};
static struct CohAuthDbDevelopmentOwner object;
static CohAuthDbDevelopmentDiagnostics diagnostics;
static CohAuthDbDevelopmentConfig copied_config;
static const CohAuthDbDevelopmentConfig *caller_config;
static const char *caller_account,*caller_password,*scenario;
static unsigned owner_live,owner_created,owner_closed,owner_destroyed,tcp_finished,udp_finished,failed;
static uint64_t clock_value;
static int is(const char *s){return !strcmp(scenario,s);}
static void check(int value){if(!value)failed=1;}
static uint64_t probe_now(void){uint64_t now=clock_value;clock_value+=250;return now;}
static void probe_pause(void){}
static int probe_entropy(uint32_t *out){*out=is("entropy")?0:12345;return !is("entropy");}
static int probe_checksum(uint8_t out[16]){memset(out,0xa5,16);return !is("checksum");}
void coh_auth_wipe(void *p,size_t size){volatile unsigned char *b=p;while(size--)*b++=0;}
const CohAuthCrypto *coh_auth_openssl_provider(void){static const CohAuthCrypto provider={0};return &provider;}
int coh_win_initialize(void){return is("tcp-init")?-1:0;}
int coh_win_limits(unsigned send,unsigned receive,int fault){check(send==1024&&receive==11&&!fault);return is("tcp-limits")?-1:0;}
unsigned coh_win_open_handles(void){return is("tcp-handles")?1:0;}
int coh_win_finish(void){check(!owner_live||is("owner-destroy"));tcp_finished++;return is("tcp-finish")?-1:0;}
int coh_db_win_initialize(void){return is("udp-init")?-1:0;}
int coh_db_win_finish(void){check(!owner_live||is("owner-destroy"));udp_finished++;return is("udp-finish")?-1:0;}
void coh_db_win_diagnostics(CohDbWinDiagnostics *out){
    *out=(CohDbWinDiagnostics){0};out->cleanup_complete=udp_finished!=0;
    if(owner_created){out->sockets_created=1;out->sockets_closed=1;}
    if(is("udp-handles")){out->active_handles=1;out->initialized=1;out->sockets_closed=0;}
    if(is("udp-close"))out->close_failures=1;
    if(is("udp-cleanup")){out->cleanup_failures=1;out->initialized=1;out->cleanup_complete=0;}
}
CohAuthDbDevelopmentOwner *coh_auth_db_development_create(const CohAuthDbDevelopmentConfig *config){
    static const unsigned char loopback[4]={127,0,0,1};
    check(!memcmp(config->auth_endpoint.address,loopback,4)&&config->auth_endpoint.port==23000&&
        config->crypto==coh_auth_openssl_provider()&&config->connect_id==12345);
    for(unsigned i=0;i<16;i++)check(config->executable_checksum[i]==0xa5);
    if(is("create"))return NULL;
    caller_config=config;copied_config=*config;owner_live=1;owner_created++;object.marker=1;
    diagnostics=(CohAuthDbDevelopmentDiagnostics){0};return &object;
}
CohStatus coh_auth_db_development_begin(CohAuthDbDevelopmentOwner *x,const char *a,const char *p,uint64_t now){
    check(x==&object&&owner_live&&now==0&&!strcmp(a,"probe-account")&&!strcmp(p,"probe-password"));
    caller_account=a;caller_password=p;diagnostics.begun=1;diagnostics.phase=COH_AUTH_DB_DEV_AUTH;
    if(is("begin")){diagnostics.failure=COH_AUTH_DB_DEV_FAILURE_AUTH;diagnostics.phase=COH_AUTH_DB_DEV_FAILED;return COH_IO;}
    return COH_OK;
}
static void success(void){
    diagnostics=(CohAuthDbDevelopmentDiagnostics){0};
    diagnostics.phase=COH_AUTH_DB_DEV_COMPLETE;diagnostics.status=COH_OK;
    diagnostics.auth_phase=COH_LOGIN_AUTHORIZED;diagnostics.db_phase=COH_DB_CHARACTERS;
    diagnostics.auth_final_phase=COH_LOGIN_CLOSED;diagnostics.db_final_phase=COH_DB_CANCELLED;
    diagnostics.begun=diagnostics.grant_consumed=diagnostics.selected_shard_verified=1;
    diagnostics.complete_matching_list=diagnostics.all_slots_empty_unlocked=1;
    diagnostics.cleanup_cancel_close_used=diagnostics.controllers_destroyed=1;
    diagnostics.slots=diagnostics.base_slots=12;diagnostics.auth_frames=4;
    diagnostics.db_login_requests=diagnostics.db_player_lists=1;diagnostics.development_skip_requested=1;
}
CohStatus coh_auth_db_development_service(CohAuthDbDevelopmentOwner *x,uint64_t now,CohCancel cancel){
    check(x==&object&&now>=250&&!cancel.poll&&zeroed(caller_account,15)&&zeroed(caller_password,17)&&
        zeroed(caller_config,sizeof(*caller_config))&&copied_config.connect_id==12345);
    if(is("deadline")){diagnostics.auth_phase=COH_LOGIN_WAIT_LOGIN;return COH_OK;}
    if(is("service")){diagnostics.phase=COH_AUTH_DB_DEV_FAILED;diagnostics.failure=COH_AUTH_DB_DEV_FAILURE_DB;return COH_IO;}
    success();
    if(is("wrong-phase"))diagnostics.phase=COH_AUTH_DB_DEV_FAILED;
    if(is("wrong-failure"))diagnostics.failure=COH_AUTH_DB_DEV_FAILURE_GRANT;
    if(is("wrong-status"))diagnostics.status=COH_IO;
    if(is("wrong-auth"))diagnostics.auth_phase=COH_LOGIN_SHARDS_READY;
    if(is("wrong-db"))diagnostics.db_phase=COH_DB_QUEUED;
    if(is("wrong-auth-final"))diagnostics.auth_final_phase=COH_LOGIN_CANCELLED;
    if(is("wrong-db-final"))diagnostics.db_final_phase=COH_DB_CLOSED;
    if(is("unconsumed"))diagnostics.grant_consumed=0;
    if(is("unselected"))diagnostics.selected_shard_verified=0;
    if(is("no-list"))diagnostics.complete_matching_list=0;
    if(is("nonempty"))diagnostics.all_slots_empty_unlocked=0;
    if(is("not-destroyed"))diagnostics.controllers_destroyed=0;
    if(is("no-close-policy"))diagnostics.cleanup_cancel_close_used=0;
    if(is("wrong-frames"))diagnostics.auth_frames=3;
    if(is("two-login"))diagnostics.db_login_requests=2;
    if(is("two-list"))diagnostics.db_player_lists=2;
    if(is("queue"))diagnostics.db_queue_updates=1;
    if(is("unsupported"))diagnostics.db_unsupported=1;
    if(is("choose"))diagnostics.db_choices=1;
    if(is("handoff"))diagnostics.db_handoffs=1;
    if(is("zero-slots"))diagnostics.slots=0;
    if(is("too-many-slots"))diagnostics.slots=COH_DB_SLOTS_MAX+1;
    if(is("bad-base"))diagnostics.base_slots=diagnostics.slots+1;
    if(is("no-development"))diagnostics.development_skip_requested=0;
    if(is("normal-version"))diagnostics.normal_version_admitted=1;
    if(is("reference"))diagnostics.checksum_reference_admitted=1;
    if(is("character"))diagnostics.character_selected=1;
    if(is("map"))diagnostics.map_handoff_verified=1;
    if(is("world"))diagnostics.current_world_verified=1;
    return COH_OK;
}
CohStatus coh_auth_db_development_timeout(CohAuthDbDevelopmentOwner *x){
    check(x==&object);diagnostics.phase=COH_AUTH_DB_DEV_FAILED;diagnostics.failure=COH_AUTH_DB_DEV_FAILURE_TIMEOUT;return COH_STATE;
}
CohStatus coh_auth_db_development_close(CohAuthDbDevelopmentOwner *x){
    check(x==&object&&zeroed(caller_account,15)&&zeroed(caller_password,17)&&zeroed(caller_config,sizeof(*caller_config)));
    owner_closed++;return is("owner-close")?COH_IO:COH_OK;
}
CohStatus coh_auth_db_development_destroy(CohAuthDbDevelopmentOwner **x){
    check(*x==&object&&owner_closed);owner_destroyed++;
    if(is("owner-destroy"))return COH_STATE;
    owner_live=0;*x=NULL;coh_auth_wipe(&copied_config,sizeof(copied_config));return COH_OK;
}
CohStatus coh_auth_db_development_diagnostics(const CohAuthDbDevelopmentOwner *x,CohAuthDbDevelopmentDiagnostics *out){
    check(x==&object);if(is("diagnostics"))return COH_IO;*out=diagnostics;return COH_OK;
}
int main(int argc,char **argv){
    if(argc!=3)return 2;
    scenario=argv[1];char *probe_argv[]={argv[0],argv[2],NULL};
    int result=controlled_probe_main(2,probe_argv);
    if(owner_created)check(owner_closed&&owner_destroyed);
    if(is("success"))check(result==0&&owner_created==1&&tcp_finished==1&&udp_finished==1);
    else if(is("platform"))check(result==0&&!owner_created&&tcp_finished==1&&udp_finished==1);
    else check(result==1);
    if(failed){fputs("controlled probe invariant failed\n",stderr);return 2;}
    return result;
}
