#define _POSIX_C_SOURCE 200809L
#include "capture_hooks.h"
#include "../session/coh_session_crypto.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static volatile sig_atomic_t cancelled;
static void cancel_signal(int n){(void)n;cancelled=1;}
static uint64_t now_ms(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
static int number(const char*s,uint32_t max,uint32_t*out){uint64_t n=0;if(!s||!*s)return 0;for(size_t i=0;s[i];i++){if(s[i]<'0'||s[i]>'9')return 0;n=n*10+(unsigned)(s[i]-'0');if(n>max)return 0;}*out=(uint32_t)n;return 1;}
static int hex(char c){return c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;}
static int digest(const char*s,uint8_t*out){if(strlen(s)!=64)return 0;unsigned nonzero=0;for(unsigned i=0;i<32;i++){int a=hex(s[i*2]),b=hex(s[i*2+1]);if(a<0||b<0)return 0;out[i]=(uint8_t)(a*16+b);nonzero|=out[i];}return nonzero!=0;}
static int line(char*out,size_t cap){if(!fgets(out,(int)cap,stdin))return 0;size_t n=strlen(out);if(n<2||out[n-1]!='\n')return 0;out[n-1]=0;for(size_t i=0;i<n-1;i++)if((unsigned char)out[i]<32||(unsigned char)out[i]>126)return 0;return 1;}
static int save(const char*path,CohBytes bytes){
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);if(fd<0)return 0;size_t done=0;int ok=1;
    while(done<bytes.size){ssize_t n=write(fd,bytes.data+done,bytes.size-done);if(n<0&&errno==EINTR)continue;if(n<=0){ok=0;break;}done+=(size_t)n;}
    if(ok&&fsync(fd))ok=0;
    if(close(fd))ok=0;
    if(!ok)unlink(path);
    return ok;
}
int main(int argc,char**argv){
    CohWorldCaptureHooks hooks={0};CohWorldCaptureBinding*b=&hooks.binding;uint32_t dbport,mapport,timeout,id;
    if(argc!=20||!number(argv[1],65535,&dbport)||!dbport||!number(argv[2],65535,&mapport)||!mapport||
       !number(argv[3],63,&b->expected_slot)||!number(argv[4],UINT32_MAX,&b->expected_dbid)||!b->expected_dbid||
       !number(argv[5],UINT32_MAX,&b->expected_map_id)||!b->expected_map_id||!number(argv[6],UINT32_MAX,&b->generation)||!b->generation||
       !number(argv[7],UINT32_MAX,&b->catalog_generation)||!b->catalog_generation||!number(argv[8],COH_GROUPS_FILE_MAX,&b->footer_files)||
       !number(argv[9],COH_GROUPS_ROOT_MAX,&b->footer_roots)||!number(argv[10],UINT32_MAX,&b->footer_defs_crc)||
       !number(argv[11],UINT32_MAX,&b->footer_refs_crc)||!number(argv[12],300000,&timeout)||timeout<1000||
       !number(argv[13],UINT32_MAX-1,&id)||!id||!digest(argv[14],b->source_sha256)||!digest(argv[15],b->profile_sha256)||
       !digest(argv[16],b->server_run_sha256)||!digest(argv[17],b->catalog_sha256)||!digest(argv[18],b->character_row_sha256)||isatty(STDIN_FILENO))return 2;
    char account[16]={0},character[65]={0};
    if(!line(account,sizeof(account))||!line(character,sizeof(character))){coh_db_wipe(account,sizeof(account));coh_db_wipe(character,sizeof(character));return 2;}
    hooks.db=(CohNetEndpoint){{127,0,0,1},(uint16_t)dbport};hooks.map=(CohNetEndpoint){{127,0,0,1},(uint16_t)mapport};hooks.version=5;
    /* Conservative reservation for local/DB/Map owner state, DB transport,
     * crypto provider and external receipts; Map transport+codec measured too. */
    hooks.retained_reservation=8u*1024u*1024u;
    if(coh_world_capture_hooks_begin(&hooks)!=COH_OK){coh_db_wipe(account,sizeof(account));coh_db_wipe(character,sizeof(character));return 2;}
    CohLocalConfig config=coh_local_default_config();config.local_development_enabled=1;config.db.transport.peer=hooks.db;
    config.db.transport.key_exchange=config.map.udp.key_exchange=coh_session_key_exchange;
    config.db.transport.key_context=config.map.udp.key_context=(void*)coh_auth_openssl_provider();
    config.db.request_timeout_ms=config.map.application_timeout_ms=timeout;
    CohLocal*local=coh_local_create(&config);if(!local){coh_world_capture_hooks_end();coh_db_wipe(account,sizeof(account));coh_db_wipe(character,sizeof(character));return 2;}
    CohDbLogin policy;CohStatus status=coh_local_login_policy(&policy);uint64_t start=now_ms();
    if(status==COH_OK)status=coh_local_begin(local,&policy,account,id,id+1,start);
    coh_db_wipe(account,sizeof(account));coh_db_wipe(&policy,sizeof(policy));
    signal(SIGINT,cancel_signal);signal(SIGTERM,cancel_signal);CohLocalDiagnostics d={0};unsigned selected=0;
    while(status==COH_OK&&!cancelled&&now_ms()-start<timeout){
        uint64_t now=now_ms();status=coh_local_service(local,now,(CohCancel){0});coh_local_diagnostics(local,&d);
        if(status==COH_OK&&d.phase==COH_LOCAL_CHARACTERS_READY&&!selected){
            CohLocalCharacters*list=calloc(1,sizeof(*list));if(!list){status=COH_LIMIT;break;}
            status=coh_local_characters(local,list);
            if(status==COH_OK&&(b->expected_slot>=list->count||strcmp(list->players[b->expected_slot].name,character)))status=COH_STATE;
            if(status==COH_OK)status=coh_local_choose_character(local,b->expected_slot,now);
            coh_db_wipe(list,sizeof(*list));free(list);coh_db_wipe(character,sizeof(character));selected=1;
        }
        if(d.phase==COH_LOCAL_SCENE_INCOMPLETE)break;
        struct timespec pause={0,1000000};while(nanosleep(&pause,&pause)&&errno==EINTR&&!cancelled){}
    }
    coh_db_wipe(character,sizeof(character));coh_local_diagnostics(local,&d);
    int ok=!cancelled&&status==COH_UNSUPPORTED&&hooks.capture_status==COH_OK&&hooks.groups_seen==1&&hooks.map_commands==3&&
        !hooks.blocked_commands&&!hooks.blocked_endpoints&&coh_world_capture_confirm(hooks.capture,&d)==COH_OK;
    coh_local_close(local);CohLocalDiagnostics closed={0};coh_local_diagnostics(local,&closed);
    ok=ok&&closed.opened_sockets==2&&closed.closed_sockets==2;
    CohWorldCaptureReceipt receipt={0};CohBytes bytes={0};
    if(ok)ok=coh_world_capture_view(hooks.capture,&receipt,&bytes)==COH_OK&&save(argv[19],bytes);
    printf("{\"schema\":1,\"captured\":%s,\"source_kind\":\"local_native_client_transport\",\"local_development_auth\":true,\"authserver_authenticated\":false,"
        "\"status\":%u,\"phase\":%u,\"capture_status\":%u,\"packet_id\":%u,\"ordered_id\":%u,\"payload_bits\":%u,\"payload_bytes\":%zu,"
        "\"byte_aligned\":%u,\"ordered\":%u,\"body_start_bit\":%zu,\"transport_lease_generation\":%llu,\"owned_bytes\":%zu,\"aggregate_bytes\":%zu,"
        "\"footer_files\":%u,\"footer_roots\":%u,\"footer_defs_crc\":%u,\"footer_refs_crc\":%u,\"transmitted_defs\":%u,\"transmitted_roots\":%u,"
        "\"selected_slot\":%u,\"external_expected_dbid\":%u,\"wire_selected_dbid\":0,\"character_identity_verified\":false,\"world_ready\":false,"
        "\"groups_seen\":%u,\"map_commands\":%u,\"blocked_commands\":%u,\"blocked_endpoints\":%u,\"opened_sockets\":%llu,\"closed_sockets\":%llu}\n",
        ok?"true":"false",status,d.phase,hooks.capture_status,receipt.packet_id,receipt.ordered_id,receipt.payload_bits,receipt.payload_bytes,
        receipt.byte_aligned,receipt.ordered,receipt.body_start_bit,(unsigned long long)receipt.transport_lease_generation,receipt.owned_bytes,receipt.aggregate_bytes,
        d.map_protocol.scene_inspection.footer_file_count,d.map_protocol.scene_inspection.footer_active_roots,d.map_protocol.scene_inspection.footer_defs_crc,
        d.map_protocol.scene_inspection.footer_refs_crc,d.map_protocol.scene_inspection.defs,d.map_protocol.scene_inspection.roots,b->expected_slot,b->expected_dbid,
        hooks.groups_seen,hooks.map_commands,hooks.blocked_commands,hooks.blocked_endpoints,(unsigned long long)closed.opened_sockets,(unsigned long long)closed.closed_sockets);
    coh_local_destroy(local);coh_world_capture_hooks_end();coh_world_capture_free(hooks.capture);coh_db_wipe(&hooks,sizeof(hooks));return ok?0:1;
}
