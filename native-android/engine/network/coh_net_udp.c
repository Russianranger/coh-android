#include "coh_net_udp.h"
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

struct CohNetUdp {
    CohNetUdpConfig config;CohNet *link;int fd;
    struct sockaddr_in peer;CohNetEndpoint local;
    CohNetUdpDiagnostics diagnostics;
    uint32_t connect_id;uint64_t clock_ms;int begun;
    size_t decoded_budget;
    uint64_t owned_generation,link_owned_generation;
};
static int wildcard(const uint8_t a[4]) { return !(a[0]|a[1]|a[2]|a[3]); }
static int unicast(const uint8_t a[4]) {
    return a[0]!=0&&a[0]<224&&!(a[0]==255&&a[1]==255&&a[2]==255&&a[3]==255);
}
CohStatus coh_net_udp_config_validate(const CohNetUdpConfig *c) {
    if(!c||!c->receive_budget||c->receive_budget>64||(c->encryption_required!=0&&c->encryption_required!=1)||!c->peer.port||!unicast(c->peer.address)||
       (!wildcard(c->local.address)&&!unicast(c->local.address)))return COH_INVALID;
    const CohNetConfig *n=&c->link;
    if(n->version>5||!n->max_retries||n->max_retries>64||!n->connect_timeout_ms||!n->idle_timeout_ms||!n->fragment_timeout_ms)return COH_INVALID;
    return COH_OK;
}
static struct sockaddr_in address(CohNetEndpoint endpoint) {
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;
    memcpy(&a.sin_addr.s_addr,endpoint.address,4);a.sin_port=htons(endpoint.port);return a;
}
static void snapshot(CohNetUdp *u) {
    if(u->link){coh_net_diagnostics(u->link,&u->diagnostics.link);u->diagnostics.link_state=coh_net_state(u->link);}
}
static void close_fd(CohNetUdp *u) {
    if(u->fd>=0){/* Linux/Android close releases the fd even on EINTR. Never
                 * retry close: another thread could have reused the number. */
        (void)close(u->fd);u->fd=-1;u->diagnostics.sockets_closed++;
    }
}
static void discard_link(CohNetUdp *u) { snapshot(u);coh_net_destroy(u->link);u->link=NULL; }
static CohStatus io_failure(CohNetUdp *u) {
    u->diagnostics.last_system_error=errno;u->diagnostics.io_errors++;
    close_fd(u);if(u->link)coh_net_close(u->link);snapshot(u);
    u->diagnostics.state=COH_UDP_FAILED;return COH_IO;
}
CohNetUdp *coh_net_udp_create(const CohNetUdpConfig *c) {
    if(coh_net_udp_config_validate(c)!=COH_OK)return NULL;
    CohNetUdp *u=calloc(1,sizeof(*u));if(!u)return NULL;
    u->config=*c;u->peer=address(c->peer);u->fd=-1;u->decoded_budget=COH_NET_MESSAGE_MAX;return u;
}
CohStatus coh_net_udp_set_decoded_budget(CohNetUdp *u,size_t bytes) {
    if(!u||u->diagnostics.state!=COH_UDP_IDLE)return COH_STATE;
    if(bytes<COH_NET_MESSAGE_MAX||bytes>COH_NET_DECODED_MAX)return COH_INVALID;
    u->decoded_budget=bytes;return COH_OK;
}
void coh_net_udp_destroy(CohNetUdp *u) {
    if(u){close_fd(u);discard_link(u);memset(u,0,sizeof(*u));free(u);}
}
static CohStatus start(CohNetUdp *u,uint32_t id,uint64_t now) {
    if(u->begun&&(now<u->clock_ms||id==u->connect_id))return COH_INVALID;
    close_fd(u);discard_link(u);
    u->link=coh_net_create(&u->config.link);if(!u->link){u->diagnostics.state=COH_UDP_FAILED;return COH_LIMIT;}
    CohStatus budget_status=coh_net_set_decoded_budget(u->link,u->decoded_budget);
    if(budget_status!=COH_OK){u->diagnostics.state=COH_UDP_FAILED;return budget_status;}
    CohStatus configured=coh_net_set_key_exchange(u->link,u->config.key_exchange,u->config.key_context,u->config.encryption_required);
    if(configured!=COH_OK){u->diagnostics.state=COH_UDP_FAILED;return configured;}
    u->fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);if(u->fd<0)return io_failure(u);
    u->diagnostics.sockets_opened++;
    int flags=fcntl(u->fd,F_GETFL,0);
    if(flags<0||fcntl(u->fd,F_SETFL,flags|O_NONBLOCK)<0)return io_failure(u);
    flags=fcntl(u->fd,F_GETFD,0);
    if(flags<0||fcntl(u->fd,F_SETFD,flags|FD_CLOEXEC)<0)return io_failure(u);
    struct sockaddr_in local=address(u->config.local);
    if(bind(u->fd,(struct sockaddr*)&local,sizeof(local))<0)return io_failure(u);
    socklen_t length=sizeof(local);
    if(getsockname(u->fd,(struct sockaddr*)&local,&length)<0||length!=sizeof(local)||local.sin_family!=AF_INET)return io_failure(u);
    memcpy(u->local.address,&local.sin_addr.s_addr,4);u->local.port=ntohs(local.sin_port);
    CohStatus s=coh_net_begin(u->link,id,now);
    if(s!=COH_OK){close_fd(u);u->diagnostics.state=COH_UDP_FAILED;return s;}
    u->clock_ms=now;u->connect_id=id;u->begun=1;u->diagnostics.state=COH_UDP_ACTIVE;snapshot(u);return COH_OK;
}
CohStatus coh_net_udp_begin(CohNetUdp *u,uint32_t id,uint64_t now) {
    if(!u)return COH_INVALID;
    if(u->diagnostics.state!=COH_UDP_IDLE&&u->diagnostics.state!=COH_UDP_CLOSED)return COH_STATE;
    return start(u,id,now);
}
static CohStatus send_frame(void *context,CohBytes frame) {
    CohNetUdp *u=context;
    ssize_t sent=sendto(u->fd,frame.data,frame.size,0,(struct sockaddr*)&u->peer,sizeof(u->peer));
    if(sent<0) {
        if(errno==EAGAIN||errno==EWOULDBLOCK){u->diagnostics.send_would_block++;return COH_NOT_FOUND;}
        if(errno==EINTR){u->diagnostics.interrupted++;return COH_NOT_FOUND;}
        return io_failure(u);
    }
    if((size_t)sent!=frame.size){errno=EIO;return io_failure(u);}
    u->diagnostics.datagrams_sent++;return COH_OK;
}
static CohStatus terminal(CohNetUdp *u) {
    if(u->diagnostics.state==COH_UDP_FAILED)return COH_IO;
    CohNetState state=coh_net_state(u->link);snapshot(u);
    if(state==COH_NET_CLOSED&&!u->diagnostics.link.tx_pending){close_fd(u);coh_net_close(u->link);u->diagnostics.state=COH_UDP_CLOSED;return COH_OK;}
    if(state==COH_NET_TIMED_OUT){close_fd(u);u->diagnostics.state=COH_UDP_TIMED_OUT;u->diagnostics.timeouts++;return COH_STATE;}
    if(state==COH_NET_ENCRYPTION_REQUIRED){close_fd(u);u->diagnostics.state=COH_UDP_ENCRYPTION_REQUIRED;return COH_UNSUPPORTED;}
    if(state==COH_NET_FAILED){close_fd(u);u->diagnostics.state=COH_UDP_FAILED;return COH_STATE;}
    return COH_OK;
}
CohStatus coh_net_udp_service(CohNetUdp *u,uint64_t now,CohCancel cancel) {
    if(!u)return COH_INVALID;
    if(u->diagnostics.state==COH_UDP_CANCELLED)return COH_CANCELLED;
    if(u->diagnostics.state!=COH_UDP_ACTIVE)return COH_STATE;
    if(now<u->clock_ms)return COH_INVALID;
    u->clock_ms=now;
    if(cancel.poll&&cancel.poll(cancel.context)){coh_net_udp_cancel(u);return COH_CANCELLED;}
    unsigned read;
    for(read=0;read<u->config.receive_budget;read++) {
        if(cancel.poll&&cancel.poll(cancel.context)){coh_net_udp_cancel(u);return COH_CANCELLED;}
        uint8_t frame[COH_PROTOCOL_FRAME_MAX];struct sockaddr_in peer;memset(&peer,0,sizeof(peer));
        struct iovec iov={frame,sizeof(frame)};struct msghdr message;memset(&message,0,sizeof(message));
        message.msg_name=&peer;message.msg_namelen=sizeof(peer);message.msg_iov=&iov;message.msg_iovlen=1;
        ssize_t size=recvmsg(u->fd,&message,MSG_DONTWAIT);
        if(size<0) {
            if(errno==EAGAIN||errno==EWOULDBLOCK)break;
            if(errno==EINTR){u->diagnostics.interrupted++;break;}
            return io_failure(u);
        }
        u->diagnostics.datagrams_received++;
        if(message.msg_namelen!=sizeof(peer)||peer.sin_family!=AF_INET||peer.sin_port!=u->peer.sin_port||peer.sin_addr.s_addr!=u->peer.sin_addr.s_addr){u->diagnostics.peer_rejects++;continue;}
        if((message.msg_flags&MSG_TRUNC)||(size_t)size>sizeof(frame)){u->diagnostics.truncated++;continue;}
        if(!size){u->diagnostics.empty++;continue;}
        CohStatus s=coh_net_receive(u->link,(CohBytes){frame,(size_t)size},now);
        if(s==COH_INVALID)u->diagnostics.malformed++;
        if(s==COH_UNSUPPORTED)u->diagnostics.unsupported++;
        CohStatus t=terminal(u);if(t!=COH_OK)return t;
        if(u->diagnostics.state==COH_UDP_CLOSED)return COH_OK;
        /* An ordered or reassembly capacity refusal is deliberately unACKed by
         * NetLink; stop this tick so application draining can relieve it. */
        if(s==COH_LIMIT)break;
    }
    if(read==u->config.receive_budget)u->diagnostics.receive_budget_exhausted++;
    CohStatus s=coh_net_pump(u->link,now,send_frame,u,cancel);
    if(s==COH_CANCELLED){coh_net_udp_cancel(u);return s;}
    CohStatus t=terminal(u);if(t!=COH_OK)return t;
    /* EAGAIN/EINTR retain the pending frame and ACKs for next service(). */
    return s==COH_NOT_FOUND?COH_OK:s;
}
CohStatus coh_net_udp_queue(CohNetUdp *u,CohBytes data,uint32_t bits,int reliable,int ordered,int compressed,uint64_t now) {
    if(!u||u->diagnostics.state!=COH_UDP_ACTIVE)return COH_STATE;
    if(now<u->clock_ms)return COH_INVALID;
    CohStatus s=coh_net_queue(u->link,data,bits,reliable,ordered,compressed,now);
    if(s==COH_OK)u->clock_ms=now;
    return s;
}
CohStatus coh_net_udp_next(CohNetUdp *u,CohNetMessage *out) {
    if(!u||!out)return COH_INVALID;
    if(u->diagnostics.state!=COH_UDP_ACTIVE)return COH_STATE;
    CohStatus s=coh_net_next(u->link,out);(void)terminal(u);return s;
}
CohStatus coh_net_udp_next_owned(CohNetUdp *u,CohNetOwnedMessage *out) {
    if(!u||!out)return COH_INVALID;
    if(u->diagnostics.state!=COH_UDP_ACTIVE)return COH_STATE;
    if(u->owned_generation==UINT64_MAX)return COH_LIMIT;
    CohNetOwnedMessage view;CohStatus s=coh_net_next_owned(u->link,&view);
    if(s==COH_OK) {
        /* Preserve lease identity across suspend/resume's fresh NetLink, even
         * when malloc reuses the previous decoded buffer's address. */
        u->link_owned_generation=view.generation;view.generation=++u->owned_generation;*out=view;
    }
    (void)terminal(u);return s;
}
CohStatus coh_net_udp_owned_release(CohNetUdp *u,CohNetOwnedMessage *out) {
    if(!out)return COH_INVALID;
    CohStatus s=COH_STATE;
    if(u&&out->generation==u->owned_generation) {
        CohNetOwnedMessage view=*out;view.generation=u->link_owned_generation;
        s=coh_net_owned_release(u->link,&view);
    }
    memset(out,0,sizeof(*out));return s;
}
CohStatus coh_net_udp_disconnect(CohNetUdp *u,uint64_t now) {
    if(!u||u->diagnostics.state!=COH_UDP_ACTIVE)return COH_STATE;
    if(now<u->clock_ms)return COH_INVALID;
    CohStatus s=coh_net_disconnect(u->link,now);if(s==COH_OK)u->clock_ms=now;return s;
}
void coh_net_udp_suspend(CohNetUdp *u) {
    if(u&&u->diagnostics.state!=COH_UDP_SUSPENDED){close_fd(u);if(u->link)coh_net_cancel(u->link);discard_link(u);u->diagnostics.state=COH_UDP_SUSPENDED;u->diagnostics.suspends++;}
}
CohStatus coh_net_udp_resume(CohNetUdp *u,uint32_t id,uint64_t now) {
    if(!u)return COH_INVALID;
    if(u->diagnostics.state==COH_UDP_ACTIVE||u->diagnostics.state==COH_UDP_IDLE)return COH_STATE;
    CohStatus s=start(u,id,now);if(s==COH_OK)u->diagnostics.resumes++;return s;
}
void coh_net_udp_cancel(CohNetUdp *u) {
    if(u&&u->diagnostics.state!=COH_UDP_CANCELLED){close_fd(u);if(u->link)coh_net_cancel(u->link);snapshot(u);u->diagnostics.state=COH_UDP_CANCELLED;u->diagnostics.cancellations++;}
}
void coh_net_udp_close(CohNetUdp *u) {
    if(u){close_fd(u);if(u->link)coh_net_close(u->link);snapshot(u);u->diagnostics.state=COH_UDP_CLOSED;}
}
CohNetUdpState coh_net_udp_state(const CohNetUdp *u) { return u?u->diagnostics.state:COH_UDP_FAILED; }
CohStatus coh_net_udp_local_endpoint(const CohNetUdp *u,CohNetEndpoint *out) {
    if(!u||!out)return COH_INVALID;
    if(u->fd<0)return COH_STATE;
    *out=u->local;return COH_OK;
}
void coh_net_udp_diagnostics(const CohNetUdp *u,CohNetUdpDiagnostics *out) {
    if(u&&out){*out=u->diagnostics;if(u->link){coh_net_diagnostics(u->link,&out->link);out->link_state=coh_net_state(u->link);}}
}
