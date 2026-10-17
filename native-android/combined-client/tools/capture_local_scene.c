/* Nonshipping POSIX receive observer. Uses the original local session owner;
 * no caller-supplied DBID, map cookie, raw authorization or application ACK. */
#define _POSIX_C_SOURCE 200809L
#include "../../engine/local/coh_local.h"
#include "../../engine/session/coh_session_crypto.h"
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

typedef struct {
    int directory, packet_owned, report_owned;
    unsigned calls, captured;
    CohStatus status;
    size_t bytes, bits, cursor;
    unsigned byte_aligned, ordered;
    uint32_t message_id, ordered_id, connection_id, version;
    uint32_t map_generation, selection_generation, selected_slot, selected_dbid;
    uint32_t map_id, map_link_id, db_generation, receipt_generation;
    CohGroupsInspection inspection;
    char sha256[65];
} Capture;
static volatile sig_atomic_t interrupted;
static void stop_signal(int value) { (void)value; interrupted=1; }
static uint64_t milliseconds(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t))return UINT64_MAX;
    return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;
}
static int number(const char *text,unsigned long limit,unsigned long *out) {
    if(!text||!*text)return 0;
    for(const char *p=text;*p;p++)if(*p<'0'||*p>'9')return 0;
    errno=0;char *end=NULL;unsigned long value=strtoul(text,&end,10);
    if(errno||!end||*end||value>limit)return 0;
    *out=value;return 1;
}
static int account_read(const char *path,char value[15]) {
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK);
    if(fd<0)return 0;
    struct stat info;
    int ok=!fstat(fd,&info)&&S_ISREG(info.st_mode)&&info.st_uid==getuid()&&
        !(info.st_mode&077)&&info.st_size>0&&info.st_size<=15;
    char bytes[16]={0};ssize_t n=-1;
    if(ok){do { n=read(fd,bytes,sizeof(bytes)); } while(n<0&&errno==EINTR);}
    if(close(fd))ok=0;
    if(ok&&n!=info.st_size)ok=0;
    if(n<1||n>15)ok=0;
    if(ok&&bytes[n-1]=='\n')n--;
    if(n<1||n>14)ok=0;
    if(ok)for(ssize_t i=0;i<n;i++)if((unsigned char)bytes[i]<33||(unsigned char)bytes[i]>126)ok=0;
    if(ok){memcpy(value,bytes,(size_t)n);value[n]=0;}
    coh_db_wipe(bytes,sizeof(bytes));return ok;
}
static int write_all(int fd,const void *bytes,size_t count) {
    const unsigned char *p=bytes;
    while(count){
        ssize_t n=write(fd,p,count);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)return 0;
        p+=(size_t)n;count-=(size_t)n;
    }
    return 1;
}
static void observe(void *context,const CohMapClient *client,const CohMapSceneObservation *event) {
    Capture *c=context;CohMapSceneLease lease;
    if(c->calls++){c->status=COH_STATE;return;}
    c->status=coh_map_client_scene_lease(client,event,&lease);
    if(c->status!=COH_OK)return;
    /* These values come solely from the currently borrowed opaque DB/Map loan. */
    if(!lease.selected_dbid_owner_bound||!lease.selected_dbid||!lease.local_development_authorized||
       lease.source_generation_admitted||lease.world_authority){c->status=COH_STATE;return;}
    unsigned char hash[EVP_MAX_MD_SIZE];unsigned hash_bytes=0;
    if(!EVP_Digest(lease.reader.bytes.data,lease.reader.bytes.size,hash,&hash_bytes,EVP_sha256(),NULL)||
       hash_bytes!=32){c->status=COH_STATE;return;}
    static const char hex[]="0123456789abcdef";
    for(unsigned i=0;i<32;i++){c->sha256[2*i]=hex[hash[i]>>4];c->sha256[2*i+1]=hex[hash[i]&15];}
    coh_db_wipe(hash,sizeof(hash));
    int fd=openat(c->directory,"groups.bin",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(fd<0){c->status=COH_STATE;return;}
    c->packet_owned=1;
    int ok=write_all(fd,lease.reader.bytes.data,lease.reader.bytes.size)&&!fsync(fd);
    if(close(fd))ok=0;
    if(!ok){c->status=COH_STATE;return;}
    /* Store values only. No callback/client/message pointer survives return. */
    c->bytes=lease.reader.bytes.size;c->bits=lease.reader.bits;c->cursor=lease.reader.cursor;
    c->byte_aligned=lease.reader.compressed;c->ordered=lease.ordered;
    c->message_id=lease.message_id;c->ordered_id=lease.ordered_id;
    c->connection_id=lease.connection_id;c->version=lease.transport_version;
    c->map_generation=lease.map_generation;c->selection_generation=lease.selection_generation;
    c->selected_slot=lease.selected_slot;c->selected_dbid=lease.selected_dbid;
    c->map_id=lease.map_id;c->map_link_id=lease.map_link_id;
    c->db_generation=lease.db_session_generation;c->receipt_generation=lease.db_receipt_generation;
    c->inspection=lease.inspection;c->captured=1;
}
static int commit_report(Capture *c,const CohLocalDiagnostics *d) {
    char json[4096];
    int length=snprintf(json,sizeof(json),
        "{\"schema\":\"coh-local-scene-capture-v1\",\"passed\":true,"
        "\"local_development_auth\":true,\"authserver_authenticated\":false,"
        "\"actual_client_loan_verified\":true,\"selected_dbid_owner_bound\":true,"
        "\"source_generation_admitted\":false,\"actor_identity_verified\":false,\"world_authority\":false,"
        "\"bytes\":%zu,\"payload_bits\":%zu,\"post_command_cursor\":%zu,"
        "\"byte_aligned\":%u,\"ordered\":%u,\"packet_sha256\":\"%s\","
        "\"message_id\":%u,\"ordered_id\":%u,\"connection_id\":%u,\"transport_version\":%u,"
        "\"map_generation\":%u,\"selection_generation\":%u,\"selected_slot\":%u,\"selected_dbid\":%u,"
        "\"map_id\":%u,\"map_link_id\":%u,\"db_session_generation\":%u,\"db_receipt_generation\":%u,"
        "\"footer_defs_crc\":%u,\"footer_refs_crc\":%u,\"footer_file_count\":%u,\"footer_active_roots\":%u,"
        "\"groups_consumed_bits\":%llu,\"scene_compressed_bytes\":%llu,\"scene_decoded_bytes\":%u,"
        "\"opened_sockets\":%llu,\"closed_sockets\":%llu,\"cleanup_verified\":true,"
        "\"packet_written_synchronously\":true,\"packet_copy_retained\":false,\"process_rss_measured\":false}\n",
        c->bytes,c->bits,c->cursor,c->byte_aligned,c->ordered,c->sha256,
        c->message_id,c->ordered_id,c->connection_id,c->version,c->map_generation,c->selection_generation,
        c->selected_slot,c->selected_dbid,c->map_id,c->map_link_id,c->db_generation,c->receipt_generation,
        c->inspection.footer_defs_crc,c->inspection.footer_refs_crc,c->inspection.footer_file_count,
        c->inspection.footer_active_roots,(unsigned long long)c->inspection.consumed_bits,
        (unsigned long long)d->map_protocol.udp.link.decode.compressed_bytes,d->map_protocol.scene_decoded_bytes,
        (unsigned long long)d->opened_sockets,(unsigned long long)d->closed_sockets);
    if(length<0||(size_t)length>=sizeof(json))return 0;
    int fd=openat(c->directory,"capture.json",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(fd<0)return 0;
    c->report_owned=1;
    int ok=write_all(fd,json,(size_t)length)&&!fsync(fd);
    if(close(fd))ok=0;
    return ok&&!fsync(c->directory);
}
int main(int argc,char **argv) {
    /* port slot private-account-file fresh-output-dir timeout-ms version encrypted compressed */
    unsigned long port,slot,timeout,version,encrypted,compressed;
    if(argc!=9||!number(argv[1],65535,&port)||!port||
       !number(argv[2],COH_DB_SLOTS_MAX-1,&slot)||!number(argv[5],600000,&timeout)||!timeout||
       !number(argv[6],5,&version)||!number(argv[7],1,&encrypted)||!number(argv[8],1,&compressed))return 2;
    (void)signal(SIGINT,stop_signal);(void)signal(SIGTERM,stop_signal);
    char account[15]={0};
    if(!account_read(argv[3],account))return 2;
    CohLocalConfig config=coh_local_default_config();config.local_development_enabled=1;
    config.db.transport.peer=(CohNetEndpoint){{127,0,0,1},(uint16_t)port};
    config.db.transport.link.version=config.map.udp.link.version=(unsigned)version;
    config.db.transport.encryption_required=config.map.udp.encryption_required=(int)encrypted;
    config.db.outbound_compressed=(unsigned)compressed;
    config.db.request_timeout_ms=config.map.application_timeout_ms=(uint64_t)timeout;
    config.db.transport.key_exchange=config.map.udp.key_exchange=coh_session_key_exchange;
    config.db.transport.key_context=config.map.udp.key_context=(void *)coh_auth_openssl_provider();
    CohLocal *local=coh_local_create(&config);
    if(!local){coh_db_wipe(account,sizeof(account));return 2;}
    Capture capture={0};capture.directory=-1;
    int directory_created=0,success=0;
    if(!mkdir(argv[4],0700)){
        directory_created=1;capture.directory=open(argv[4],O_RDONLY|O_DIRECTORY|O_NOFOLLOW);
    }
    CohStatus status=COH_STATE;CohLocalDiagnostics diagnostics={0};
    if(capture.directory>=0){
        CohDbLogin policy;status=coh_local_login_policy(&policy);
        uint32_t ids[2]={0};uint64_t now=milliseconds();
        if(now==UINT64_MAX||!RAND_bytes((unsigned char *)ids,sizeof(ids)))status=COH_STATE;
        ids[0]=(ids[0]&UINT32_C(0x7ffffffc))+1;ids[1]=ids[0]+1;
        if(status==COH_OK)status=coh_local_begin(local,&policy,account,ids[0],ids[1],now);
        coh_db_wipe(&policy,sizeof(policy));coh_db_wipe(account,sizeof(account));coh_db_wipe(ids,sizeof(ids));
        uint64_t deadline=now+(uint64_t)timeout;unsigned selected=0;
        while(status==COH_OK&&now<deadline&&!interrupted){
            status=coh_local_service_observed(local,now,(CohCancel){0},observe,&capture);
            coh_local_diagnostics(local,&diagnostics);
            if(capture.calls)break;
            if(status==COH_OK&&diagnostics.phase==COH_LOCAL_CHARACTERS_READY&&!selected){
                status=coh_local_choose_character(local,(uint32_t)slot,now);selected=1;
            }
            if(status!=COH_OK)break;
            struct timespec pause={0,1000000};(void)nanosleep(&pause,NULL);now=milliseconds();
        }
        success=!interrupted&&capture.calls==1&&capture.captured&&capture.status==COH_OK&&
            status==COH_UNSUPPORTED&&diagnostics.phase==COH_LOCAL_SCENE_INCOMPLETE;
    }
    coh_db_wipe(account,sizeof(account));coh_local_close(local);coh_local_diagnostics(local,&diagnostics);
    success=success&&diagnostics.opened_sockets==2&&diagnostics.closed_sockets==2;
    coh_local_destroy(local);
    if(success)success=commit_report(&capture,&diagnostics);
    if(!success&&capture.directory>=0){
        if(capture.packet_owned)(void)unlinkat(capture.directory,"groups.bin",0);
        if(capture.report_owned)(void)unlinkat(capture.directory,"capture.json",0);
    }
    if(capture.directory>=0)(void)close(capture.directory);
    if(!success&&directory_created)(void)rmdir(argv[4]);
    printf("{\"passed\":%s,\"status\":%u,\"capture_status\":%u,\"observations\":%u,"
        "\"opened_sockets\":%llu,\"closed_sockets\":%llu,\"source_generation_admitted\":false,\"world_authority\":false}\n",
        success?"true":"false",(unsigned)status,(unsigned)capture.status,capture.calls,
        (unsigned long long)diagnostics.opened_sockets,(unsigned long long)diagnostics.closed_sockets);
    return success?0:1;
}
