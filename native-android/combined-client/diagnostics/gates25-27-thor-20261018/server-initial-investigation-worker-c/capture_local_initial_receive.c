/* New diagnostic role. Include the exact retained progress role; public API
 * wrappers only read diagnostics and delegate each original operation once. */
#define _POSIX_C_SOURCE 200809L
#include "coh_receive_projection.h"
static CohReceiveProjection receive_projection;
static const CohInitialCapture*receive_owner;
static unsigned receive_bound,receive_retired,receive_cleanup;
static CohStatus receive_begin(CohInitialCapture*,const CohDbLogin*,const char*,uint32_t,uint32_t,uint64_t);
static void receive_diagnostics(const CohInitialCapture*,CohInitialCaptureDiagnostics*);
static void receive_destroy(CohInitialCapture*);
#ifndef COH_INITIAL_RECEIVE_NO_LEGACY
static void receive_write_fd(int);
#endif
#ifndef COH_INITIAL_RECEIVE_NO_LEGACY
/* BEGIN EXACT PROGRESS ROLE WITH FIVE REVERSIBLE IDENTIFIER EDITS */
/* NONSHIPPING receiver-main observation role. The legacy source below is
 * mechanically identical except its main name and three diagnostic call seams.
 * No protocol, deadline, pump count or application ACK behavior is changed. */
#define _POSIX_C_SOURCE 200809L
#include "../../engine/initial-capture/coh_initial_progress.h"
#include <errno.h>
#include <sys/socket.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
static CohInitialProgress progress;
static CohStatus progress_begin(CohInitialCapture*,const CohDbLogin*,const char*,uint32_t,uint32_t,uint64_t);
static CohStatus progress_service(CohInitialCapture*,uint64_t,CohCancel,CohInitialCaptureObserver,void*,size_t);
static void progress_destroy(CohInitialCapture*);
static void progress_write(int);
#ifndef COH_INITIAL_PROGRESS_NO_LEGACY
/* BEGIN EXACT LEGACY ROLE WITH FOUR REVERSIBLE IDENTIFIER EDITS */
/* Nonshipping only: preserve the genuine GROUPS observation and request one
 * raw initial snapshot. Neither observation admits character/world or ACKs. */
#define main coh_groups_capture_original_main
#include "capture_local_scene.c"
#undef main
#include "../../engine/initial-capture/coh_initial_capture.h"

typedef struct {
    Capture groups;
    int initial_owned, initial_report_owned;
    unsigned initial_captured;
    CohStatus initial_status;
    uint64_t groups_message_generation, message_generation;
    size_t bytes, bits, cursor;
    unsigned aligned, ordered;
    uint32_t message_id, ordered_id;
    CohRepSchema schema;
    CohRepUpdatePrefix update;
    char sha256[65];
} InitialOutput;

static int digest_bytes(CohBytes bytes,char out[65]) {
    unsigned char hash[EVP_MAX_MD_SIZE];unsigned count=0;
    if(!EVP_Digest(bytes.data,bytes.size,hash,&count,EVP_sha256(),NULL)||count!=32)return 0;
    static const char hex[]="0123456789abcdef";
    for(unsigned i=0;i<32;i++){out[2*i]=hex[hash[i]>>4];out[2*i+1]=hex[hash[i]&15];}
    out[64]=0;coh_db_wipe(hash,sizeof(hash));return 1;
}
static int packet_file(int directory,const char *name,CohBytes bytes,int *owned) {
    int fd=openat(directory,name,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(fd<0)return 0;
    *owned=1;int ok=write_all(fd,bytes.data,bytes.size)&&!fsync(fd);
    if(close(fd))ok=0;
    return ok;
}
static CohStatus observe_initial(void *context,const CohInitialCapture *owner,
    const CohInitialCaptureEvent *event) {
    InitialOutput *out=context;Capture *g=&out->groups;CohInitialCaptureLease lease;
    CohStatus status=coh_initial_capture_lease(owner,event,&lease);
    if(status!=COH_OK)return status;
    if(!lease.selected_dbid_owner_bound||!lease.selected_dbid||!lease.local_development_authorized||
       lease.source_generation_admitted||lease.complete_initial_character||lease.actor_publication||
       lease.ack_permitted||lease.world_authority)return COH_STATE;
    if(event->kind==COH_INITIAL_CAPTURE_GROUPS){
        if(g->calls++){g->status=COH_STATE;return COH_STATE;}
        if(!digest_bytes(lease.reader.bytes,g->sha256)||
           !packet_file(g->directory,"groups.bin",lease.reader.bytes,&g->packet_owned)){
            g->status=COH_STATE;return COH_STATE;
        }
        g->bytes=lease.reader.bytes.size;g->bits=lease.reader.bits;g->cursor=lease.reader.cursor;
        g->byte_aligned=lease.reader.compressed;g->ordered=lease.ordered;
        g->message_id=lease.message_id;g->ordered_id=lease.ordered_id;
        g->connection_id=lease.connection_id;g->version=lease.transport_version;
        g->map_generation=lease.map_generation;g->selection_generation=lease.selection_generation;
        g->selected_slot=lease.selected_slot;g->selected_dbid=lease.selected_dbid;
        g->map_id=lease.map_id;g->map_link_id=lease.map_link_id;
        g->db_generation=lease.db_session_generation;g->receipt_generation=lease.db_receipt_generation;
        g->inspection=lease.groups;g->captured=1;g->status=COH_OK;
        out->groups_message_generation=lease.message_generation;
        return COH_OK;
    }
    if(event->kind!=COH_INITIAL_CAPTURE_ALLENTS||!g->captured||out->initial_captured||
       lease.groups_message_generation!=out->groups_message_generation||
       lease.message_generation<=out->groups_message_generation||
       lease.connection_id!=g->connection_id||lease.transport_version!=g->version||
       lease.map_generation!=g->map_generation||lease.selection_generation!=g->selection_generation||
       lease.selected_slot!=g->selected_slot||lease.selected_dbid!=g->selected_dbid||
       lease.map_id!=g->map_id||lease.map_link_id!=g->map_link_id||
       lease.db_session_generation!=g->db_generation||lease.db_receipt_generation!=g->receipt_generation||
       lease.reader.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
       lease.schema.count>COH_REP_SHORTCUT_MAX||lease.schema.accessible_commands>COH_REP_ACCESSIBLE_COMMAND_MAX||
       lease.update.command!=COH_REP_ALLENTS)return COH_STATE;
    if(!digest_bytes(lease.reader.bytes,out->sha256)||
       !packet_file(g->directory,"initial-update.bin",lease.reader.bytes,&out->initial_owned)){
        out->initial_status=COH_STATE;return COH_STATE;
    }
    out->bytes=lease.reader.bytes.size;out->bits=lease.reader.bits;out->cursor=lease.reader.cursor;
    out->aligned=lease.reader.compressed;out->ordered=lease.ordered;
    out->message_id=lease.message_id;out->ordered_id=lease.ordered_id;
    out->message_generation=lease.message_generation;out->schema=lease.schema;out->update=lease.update;
    out->initial_status=COH_OK;out->initial_captured=1;return COH_OK;
}
static const char *failure_name(CohInitialCaptureFailure failure) {
    static const char *names[]={"NONE","INPUT","OWNER","PROTOCOL","GROUPS","REQUEST",
        "COMMAND","HEADER","OBSERVER","RELEASE","TIMEOUT","CANCELLED","MEMORY"};
    return (unsigned)failure<sizeof(names)/sizeof(names[0])?names[failure]:"UNKNOWN";
}
static CohInitialCaptureFailure diagnostic_failure(const CohInitialCaptureDiagnostics *d) {
    return d->first_failure.valid?d->first_failure.failure:d->failure;
}
static CohStatus diagnostic_status(const CohInitialCaptureDiagnostics *d) {
    return d->first_failure.valid?d->first_failure.status:d->status;
}
static int initial_report(InitialOutput *out,const CohInitialCaptureDiagnostics *d,unsigned passed) {
    Capture *g=&out->groups;
    int fd=openat(g->directory,"initial-observation.json",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(fd<0)return 0;
    out->initial_report_owned=1;FILE *f=fdopen(fd,"w");if(!f){(void)close(fd);return 0;}
    int ok=fprintf(f,"{\"schema\":\"coh-private-initial-observation-v1\",\"passed\":%s,"
        "\"diagnostic_only\":true,\"groups_capture_verified\":true,\"local_development_auth\":true,"
        "\"authserver_authenticated\":false,\"selected_dbid_owner_bound\":true,"
        "\"source_generation_admitted\":false,\"complete_initial_character\":false,"
        "\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false,"
        "\"sends_ready\":false,\"sends_received_character\":false,\"sends_full_update_ack\":false,"
        "\"reqallents_sent\":%u,\"failure_code\":\"%s\",\"status\":%u,"
        "\"groups_packet_sha256\":\"%s\",\"groups_message_generation\":%llu,\"groups_message_id\":%u,"
        "\"connection_id\":%u,\"transport_version\":%u,\"map_generation\":%u,"
        "\"selection_generation\":%u,\"selected_slot\":%u,\"selected_dbid\":%u,"
        "\"map_id\":%u,\"map_link_id\":%u,\"db_session_generation\":%u,\"db_receipt_generation\":%u,"
        "\"opened_sockets\":%llu,\"closed_sockets\":%llu,\"cleanup_verified\":true,"
        "\"raw_allents_loan_verified\":%s,\"bytes\":%zu,\"payload_bits\":%zu,\"post_command_cursor\":%zu,"
        "\"byte_aligned\":%u,\"ordered\":%u,\"message_id\":%u,\"ordered_id\":%u,"
        "\"message_generation\":%llu,\"packet_sha256\":\"%s\","
        "\"accessible_commands\":%zu,\"shortcuts\":[",
        passed?"true":"false",d->reqallents_sent,passed?"NONE":
            diagnostic_failure(d)==COH_INITIAL_CAPTURE_FAILURE_NONE?"TIMEOUT":failure_name(diagnostic_failure(d)),
        (unsigned)diagnostic_status(d),
        g->sha256,(unsigned long long)out->groups_message_generation,g->message_id,g->connection_id,g->version,
        g->map_generation,g->selection_generation,g->selected_slot,g->selected_dbid,g->map_id,g->map_link_id,
        g->db_generation,g->receipt_generation,(unsigned long long)d->local.opened_sockets,
        (unsigned long long)d->local.closed_sockets,passed?"true":"false",passed?out->bytes:0,
        passed?out->bits:0,passed?out->cursor:0,passed?out->aligned:0,passed?out->ordered:0,
        passed?out->message_id:0,passed?out->ordered_id:0,(unsigned long long)(passed?out->message_generation:0),
        passed?out->sha256:"",passed?out->schema.accessible_commands:0)>=0;
    if(passed)for(size_t i=0;i<out->schema.count;i++)
        if(fprintf(f,"%s[%u,%u]",i?",":"",(unsigned)out->schema.entries[i].id,
            (unsigned)out->schema.entries[i].kind)<0)ok=0;
    const CohRepUpdatePrefix *u=&out->update;
    if(fprintf(f,"],\"update_prefix\":{\"command\":%u,\"full_update_id\":%u,\"odd_send\":%u,"
        "\"abs_time\":%u,\"db_seconds\":%u,\"has_debug_info\":%u,\"interp_level\":%u,"
        "\"interp_precision\":%u,\"command_count\":%u,\"entity_tail_bit\":%zu}}\n",
        passed?u->command:0,passed?u->full_update_id:0,passed?u->odd_send:0,passed?u->abs_time:0,
        passed?u->db_seconds:0,passed?u->has_debug_info:0,passed?u->interp_level:0,
        passed?u->interp_precision:0,passed?u->command_count:0,passed?u->entity_tail_bit:0)<0)ok=0;
    if(fflush(f)||fsync(fd))ok=0;
    if(fclose(f))ok=0;
    return ok&&!fsync(g->directory);
}
int coh_initial_progress_legacy_main(int argc,char **argv) {
    unsigned long port,slot,timeout,version,encrypted,compressed;
    if(argc!=9||!number(argv[1],65535,&port)||!port||
       !number(argv[2],COH_DB_SLOTS_MAX-1,&slot)||!number(argv[5],600000,&timeout)||!timeout||
       !number(argv[6],5,&version)||!number(argv[7],1,&encrypted)||!number(argv[8],1,&compressed))return 2;
    (void)signal(SIGINT,stop_signal);(void)signal(SIGTERM,stop_signal);
    char account[15]={0};if(!account_read(argv[3],account))return 2;
    CohLocalConfig config=coh_local_default_config();config.local_development_enabled=1;
    config.db.transport.peer=(CohNetEndpoint){{127,0,0,1},(uint16_t)port};
    config.db.transport.link.version=config.map.udp.link.version=(unsigned)version;
    config.db.transport.encryption_required=config.map.udp.encryption_required=(int)encrypted;
    config.db.outbound_compressed=(unsigned)compressed;
    config.db.request_timeout_ms=config.map.application_timeout_ms=(uint64_t)timeout;
    config.db.transport.key_exchange=config.map.udp.key_exchange=coh_session_key_exchange;
    config.db.transport.key_context=config.map.udp.key_context=(void *)coh_auth_openssl_provider();
    CohInitialCapture *owner=coh_initial_capture_create(&config);
    if(!owner){coh_db_wipe(account,sizeof(account));return 2;}
    InitialOutput out={0};out.groups.directory=-1;int directory_created=0;
    if(!mkdir(argv[4],0700)){directory_created=1;out.groups.directory=open(argv[4],O_RDONLY|O_DIRECTORY|O_NOFOLLOW);}
    CohStatus status=COH_STATE;CohInitialCaptureDiagnostics d={0};unsigned initial_passed=0,success=0;
    if(out.groups.directory>=0){
        CohDbLogin policy;status=coh_local_login_policy(&policy);uint32_t ids[2]={0};uint64_t now=milliseconds();
        if(now==UINT64_MAX||!RAND_bytes((unsigned char *)ids,sizeof(ids)))status=COH_STATE;
        ids[0]=(ids[0]&UINT32_C(0x7ffffffc))+1;ids[1]=ids[0]+1;
        if(status==COH_OK)status=progress_begin(owner,&policy,account,ids[0],ids[1],now);
        coh_db_wipe(&policy,sizeof(policy));coh_db_wipe(account,sizeof(account));coh_db_wipe(ids,sizeof(ids));
        uint64_t deadline=now+(uint64_t)timeout;unsigned selected=0;
        while(status==COH_OK&&now<deadline&&!interrupted){
            status=progress_service(owner,now,(CohCancel){0},observe_initial,&out,sizeof(out));
            receive_diagnostics(owner,&d);
            if(status==COH_OK&&d.local.phase==COH_LOCAL_CHARACTERS_READY&&!selected){
                status=coh_initial_capture_choose_character(owner,(uint32_t)slot,now);selected=1;
            }
            if(status!=COH_OK)break;
            struct timespec pause={0,1000000};(void)nanosleep(&pause,NULL);now=milliseconds();
        }
        initial_passed=!interrupted&&out.initial_captured&&out.initial_status==COH_OK&&
            d.phase==COH_INITIAL_CAPTURED&&d.raw_allents_observed&&d.allents_observations==1&&d.reqallents_sent==1;
        success=!interrupted&&out.groups.calls==1&&out.groups.captured&&out.groups.status==COH_OK&&
            d.groups_observed&&d.groups_observations==1&&d.groups_message_generation==out.groups_message_generation;
    }
    /* Retire an active caller deadline/signal through the diagnostic owner so
     * its actual phases are latched before close overwrites them. */
    if(!initial_passed&&out.groups.directory>=0){
        if(interrupted)coh_initial_capture_cancel(owner);
        else if(status==COH_OK)coh_initial_capture_timeout(owner);
    }
    coh_db_wipe(account,sizeof(account));coh_initial_capture_close(owner);receive_diagnostics(owner,&d);
    success=success&&d.local.opened_sockets==2&&d.local.closed_sockets==2;
    initial_passed=initial_passed&&success;
    if(!initial_passed&&!d.first_failure.valid&&d.failure==COH_INITIAL_CAPTURE_FAILURE_NONE){
        d.failure=out.groups.directory<0?COH_INITIAL_CAPTURE_FAILURE_INPUT:
            interrupted?COH_INITIAL_CAPTURE_FAILURE_CANCELLED:
            status==COH_OK?COH_INITIAL_CAPTURE_FAILURE_TIMEOUT:COH_INITIAL_CAPTURE_FAILURE_PROTOCOL;
        d.status=interrupted?COH_CANCELLED:status==COH_OK?COH_STATE:status;
    }
    progress_destroy(owner);
    if(!initial_passed&&out.initial_owned){(void)unlinkat(out.groups.directory,"initial-update.bin",0);out.initial_owned=0;}
    if(success&&!initial_report(&out,&d,initial_passed)){
        if(out.initial_owned){(void)unlinkat(out.groups.directory,"initial-update.bin",0);out.initial_owned=0;}
        if(out.initial_report_owned){(void)unlinkat(out.groups.directory,"initial-observation.json",0);out.initial_report_owned=0;}
        initial_passed=0;
    }
    if(success)success=commit_report(&out.groups,&d.local);
    if(!success&&out.groups.directory>=0){
        if(out.groups.packet_owned)(void)unlinkat(out.groups.directory,"groups.bin",0);
        if(out.groups.report_owned)(void)unlinkat(out.groups.directory,"capture.json",0);
        if(out.initial_owned)(void)unlinkat(out.groups.directory,"initial-update.bin",0);
        if(out.initial_report_owned)(void)unlinkat(out.groups.directory,"initial-observation.json",0);
    }
    if(success&&out.groups.directory>=0)receive_write_fd(out.groups.directory);
    if(out.groups.directory>=0)(void)close(out.groups.directory);
    if(!success&&directory_created)(void)rmdir(argv[4]);
    printf("{\"schema\":\"coh-local-initial-capture-status-v2\",\"passed\":%s,\"initial_packet_observed\":%s,\"status\":%u,"
        "\"opened_sockets\":%llu,\"closed_sockets\":%llu,\"source_generation_admitted\":false,"
        "\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false,"
        "\"diagnostic_failure_code\":\"%s\",\"groups_observed\":%s,\"reqallents_sent\":%u,\"local_phase\":%u,"
        "\"terminal_failure\":%s,\"terminal_db_phase\":%u,\"terminal_map_phase\":%u,"
        "\"refused_command_valid\":%s,\"refused_command_kind\":\"%s\"}\n",
        success?"true":"false",initial_passed?"true":"false",(unsigned)diagnostic_status(&d),
        (unsigned long long)d.local.opened_sockets,(unsigned long long)d.local.closed_sockets,
        failure_name(diagnostic_failure(&d)),d.groups_observed?"true":"false",d.reqallents_sent,(unsigned)d.local.phase,
        (d.first_failure.valid||d.local.terminal_failure)?"true":"false",
        (unsigned)(d.first_failure.valid?d.first_failure.db_phase:d.local.terminal_db_phase),
        (unsigned)(d.first_failure.valid?d.first_failure.map_phase:d.local.terminal_map_phase),
        d.refused_command_valid?"true":"false",coh_initial_capture_command_name(d.refused_command_kind));
    return success?0:1;
}
/* END EXACT LEGACY ROLE */
#endif
static CohStatus progress_begin(CohInitialCapture*owner,const CohDbLogin*policy,const char*account,uint32_t db,uint32_t map,uint64_t now){
 CohStatus s=receive_begin(owner,policy,account,db,map,now);
 if(s==COH_OK)coh_initial_progress_bind(&progress,owner,now);
 return s;
}
static CohStatus progress_service(CohInitialCapture*owner,uint64_t now,CohCancel cancel,CohInitialCaptureObserver observer,void*context,size_t context_bytes){
 CohInitialCaptureDiagnostics before={0},after={0};receive_diagnostics(owner,&before);
 coh_initial_progress_service_begin(&progress,owner,now,&before);
 CohStatus s=coh_initial_capture_service(owner,now,cancel,observer,context,context_bytes);
 receive_diagnostics(owner,&after);coh_initial_progress_service_end(&progress,owner,now,&after);return s;
}
static void progress_destroy(CohInitialCapture*owner){coh_initial_progress_retire(&progress,owner);receive_destroy(owner);}
ssize_t __real_sendto(int,const void*,size_t,int,const struct sockaddr*,socklen_t);
ssize_t __wrap_sendto(int fd,const void*data,size_t bytes,int flags,const struct sockaddr*address,socklen_t length){
 ssize_t result=__real_sendto(fd,data,bytes,flags,address,length);int saved=errno;
 int full=result>=0&&(size_t)result==bytes;
 int would_block=result<0&&(saved==EAGAIN||saved==EWOULDBLOCK);
 int signal_=result<0&&saved==EINTR;
 int partial=result>=0&&!full;int error=result<0&&!would_block&&!signal_;
 coh_initial_progress_send(&progress,bytes,full,would_block,signal_,partial,error);errno=saved;return result;
}
static const char*progress_refusal(CohInitialProgressRefusal r){
 static const char*names[]={"NONE","OWNER","CLOCK","STATE","LIMIT","CALLBACK"};return(unsigned)r<sizeof(names)/sizeof(*names)?names[r]:"STATE";
}
static int progress_json(char*out,size_t size){
 return snprintf(out,size,"{\"schema\":\"coh-initial-post-queue-progress-v1\",\"diagnostic_only\":true,\"valid\":%s,\"queue_observed\":%s,\"post_queue_services\":%u,\"post_queue_send_callbacks\":%u,\"post_queue_datagrams_emitted\":%u,\"post_queue_would_block\":%u,\"post_queue_interrupted\":%u,\"post_queue_send_errors\":%u,\"post_queue_partial_sends\":%u,\"queue_service_offset_ms\":%llu,\"last_post_queue_service_offset_ms\":%llu,\"witness_owner_retired\":%s,\"refusal\":\"%s\",\"command_specific_emission_proved\":false,\"server_receipt_proved\":false,\"source_generation_admitted\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",progress.bound&&progress.retired&&!progress.refusal?"true":"false",progress.queued?"true":"false",progress.post_queue_services,progress.post_queue_send_callbacks,progress.post_queue_datagrams_emitted,progress.post_queue_would_block,progress.post_queue_interrupted,progress.post_queue_send_errors,progress.post_queue_partial_sends,(unsigned long long)progress.queue_offset_ms,(unsigned long long)progress.last_post_queue_service_offset_ms,progress.retired?"true":"false",progress_refusal(progress.refusal));
}
#ifndef COH_INITIAL_PROGRESS_NO_LEGACY
static void progress_write(int directory){
 char json[COH_INITIAL_PROGRESS_REPORT_MAX];int n=progress_json(json,sizeof(json));
 if(n<=0||(size_t)n>=sizeof(json))return;
 int file=openat(directory,"request-progress.json",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
 if(file<0)return;
 int ok=write_all(file,json,(size_t)n)&&!fsync(file);
 if(close(file))ok=0;
 if(!ok)(void)unlinkat(directory,"request-progress.json",0);
}
int coh_receive_progress_main(int argc,char**argv){
 int result=coh_initial_progress_legacy_main(argc,argv);
 memset(&progress,0,sizeof(progress));return result;
}
#endif
/* END EXACT PROGRESS ROLE */
#endif
static CohStatus receive_begin(CohInitialCapture*owner,const CohDbLogin*policy,const char*account,uint32_t db,uint32_t map,uint64_t now){
 CohStatus s=coh_initial_capture_begin(owner,policy,account,db,map,now);
 if(s==COH_OK){if(receive_bound)receive_projection.refusal=1;else{receive_owner=owner;receive_bound=1;}}
 return s;
}
static void receive_diagnostics(const CohInitialCapture*owner,CohInitialCaptureDiagnostics*out){
 coh_initial_capture_diagnostics(owner,out);
 if(!receive_bound||receive_retired||owner!=receive_owner){receive_projection.refusal=1;return;}
 coh_receive_sample(&receive_projection,&out->local.map_protocol.udp);
 receive_cleanup=out->local.opened_sockets==out->local.closed_sockets;
}
static void receive_destroy(CohInitialCapture*owner){
 if(!receive_bound||receive_retired||owner!=receive_owner)receive_projection.refusal=1;
 receive_owner=NULL;receive_retired=1;coh_initial_capture_destroy(owner);
}
#ifndef COH_INITIAL_RECEIVE_NO_LEGACY
static void receive_write_fd(int directory){
 progress_write(directory);
 if(!receive_bound||!receive_retired||receive_owner)return;
 char json[COH_RECEIVE_REPORT_MAX];int n=coh_receive_json(&receive_projection,receive_retired,receive_cleanup,json,sizeof(json));
 if(n>0&&(size_t)n<sizeof(json)){
  int file=openat(directory,"receive-counters.json",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
  if(file>=0){struct stat owned,current;int keyed=!fstat(file,&owned);
   int ok=keyed&&write_all(file,json,(size_t)n)&&!fsync(file);if(close(file))ok=0;
   if(ok&&fsync(directory))ok=0;
   if(!ok&&keyed&&!fstatat(directory,"receive-counters.json",&current,AT_SYMLINK_NOFOLLOW)&&
      current.st_dev==owned.st_dev&&current.st_ino==owned.st_ino&&current.st_uid==owned.st_uid)
    (void)unlinkat(directory,"receive-counters.json",0);
  }
 }
 coh_db_wipe(json,sizeof(json));
}
int main(int argc,char**argv){
 int result=coh_receive_progress_main(argc,argv);
 coh_db_wipe(&receive_projection,sizeof(receive_projection));receive_owner=NULL;
 receive_bound=receive_retired=receive_cleanup=0;return result;
}
#endif
