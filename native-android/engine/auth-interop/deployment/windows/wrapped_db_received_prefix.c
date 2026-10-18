/* Compile the ordinary DB session TU unchanged; observe its SAME next copy. */
#include "db_received_prefix.h"
#include <stdint.h>
#include <string.h>
static CohStatus received_next(CohNetUdp *,CohNetMessage *);
#define coh_db_session_create received_original_create
#define coh_db_session_service received_original_service
#define coh_db_session_destroy received_original_destroy
#define coh_net_udp_next received_next
#include "../../../dbclient/coh_db_session.c"
#undef coh_net_udp_next
#undef coh_db_session_destroy
#undef coh_db_session_service
#undef coh_db_session_create

static struct {
    CohDevDbReceivedPrefix d;
    CohDbSession *bound,*active;
    CohNetUdp *udp;
    CohNetMessage *message;
    uint32_t generation;
    unsigned version,invalid;
} received;

static int overlaps(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t ap=(uintptr_t)a,bp=(uintptr_t)b;
    if(an>UINTPTR_MAX-ap||bn>UINTPTR_MAX-bp)return 1;
    return ap<bp+bn&&bp<ap+an;
}
static uint32_t known_kind(uint32_t command) {
    switch(command) {
#define COH_DEV_DB_KIND(value,name) case value:return value;
        COH_DEV_DB_COMMANDS(COH_DEV_DB_KIND)
#undef COH_DEV_DB_KIND
    default:return COH_DEV_DB_UNKNOWN;
    }
}
static int bound(const CohDbSession *s) {
    return s&&received.bound==s&&received.udp==s->udp&&
        received.version==s->config.transport.link.version&&
        s->diagnostics.generation==1&&received.generation==1;
}
CohDbSession *coh_db_session_create(const CohDbSessionConfig *config) {
    CohDbSession *s=received_original_create(config);
    if(s) {
        if(received.d.instances<2)received.d.instances++;
        if(received.d.instances!=1||received.bound)received.invalid=1;
        else {
            received.bound=s;received.udp=s->udp;
            received.version=s->config.transport.link.version;
        }
    }
    return s;
}
void coh_db_session_destroy(CohDbSession *s) {
    if(s&&received.bound==s) {
        if(received.active||(received.generation&&!bound(s)))received.invalid=1;
        received.bound=NULL;received.udp=NULL;received.d.retired=1;
    }
    received_original_destroy(s);
}
CohStatus coh_db_session_service(CohDbSession *s,uint64_t now,CohCancel cancel) {
    if(received.active) {
        received.invalid=1;
        return received_original_service(s,now,cancel);
    }
    if(received.d.service_calls<65535)received.d.service_calls++;
    else received.invalid=1;
    if(s&&received.bound==s&&!received.generation&&s->diagnostics.generation==1)
        received.generation=1;
    if(!bound(s))received.invalid=1;
    received.active=s;
    CohStatus status=received_original_service(s,now,cancel);
    if(!bound(s))received.invalid=1;
    received.active=NULL;received.message=NULL;
    return status;
}
static CohStatus received_next(CohNetUdp *udp,CohNetMessage *message) {
    /* Clear the current-message alias BEFORE fetching, including failures. */
    received.message=message;
    CohStatus status=coh_net_udp_next(udp,message);
    if(status==COH_OK&&!received.invalid&&received.active&&bound(received.active)&&udp==received.udp) {
        if(received.d.total_seen<65535)received.d.total_seen++;
        else received.d.truncated=1;
        if(received.d.count<COH_DEV_DB_PREFIX_MAX) {
            CohDevDbPrefixEntry entry={0};uint32_t command=0;
            entry.phase=(uint32_t)received.active->diagnostics.phase;
            entry.legacy=received.version<4;entry.compressed=message->compressed!=0;
            if(message_command(message,(int)entry.legacy,&command)==COH_OK) {
                entry.header_decoded=1;entry.kind=known_kind(command);
            }
            received.d.entries[received.d.count++]=entry;
            coh_db_wipe(&command,sizeof(command));coh_db_wipe(&entry,sizeof(entry));
        } else received.d.truncated=1;
    }
    received.message=NULL;
    return status;
}
CohStatus coh_dev_db_received_prefix(CohDevDbReceivedPrefix *out) {
    if(!out||(uintptr_t)out%_Alignof(CohDevDbReceivedPrefix)||
       overlaps(out,sizeof(*out),&received,sizeof(received))||
       (received.bound&&overlaps(out,sizeof(*out),received.bound,sizeof(*received.bound)))||
       (received.message&&overlaps(out,sizeof(*out),received.message,sizeof(*received.message))))return COH_INVALID;
    if(received.active)return COH_STATE;
    if(received.bound&&received.generation&&!bound(received.bound))received.invalid=1;
    CohDevDbReceivedPrefix d=received.d;
    d.context_verified=!received.invalid&&d.instances==1&&received.generation==1;
    *out=d;coh_db_wipe(&d,sizeof(d));return COH_OK;
}
