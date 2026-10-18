#include "db_udp_winsock.h"
#include "../../../../protocol/coh_protocol.h"

typedef struct { SOCKET value; int active, flags, descriptor_flags, bound; } Slot;
static Slot slots[COH_DB_WIN_SLOTS];
static CohDbWinDiagnostics diagnostics;
static unsigned next_slot;
static int ready;
static int translate(int error) {
    switch(error) {
    case 0:return 0;
    case WSAEWOULDBLOCK:return EAGAIN;
    case WSAEINTR:return EINTR;
    case WSAENOTSOCK:return EBADF;
    case WSAEINVAL:return EINVAL;
    case WSAENOBUFS:return ENOMEM;
    case WSAECONNRESET:case WSAECONNABORTED:return ECONNRESET;
    case WSAECONNREFUSED:return ECONNREFUSED;
    case WSAETIMEDOUT:return ETIMEDOUT;
    default:return EIO;
    }
}
static int failed(void) {errno=translate(WSAGetLastError());return -1;}
static Slot *owned(int fd) {
    if(!diagnostics.initialized||fd<0||fd>=COH_DB_WIN_SLOTS||!slots[fd].active){errno=EBADF;return NULL;}
    return &slots[fd];
}
static int configured(const Slot *s) {
    return ready&&s->flags==COH_DB_WIN_NONBLOCK&&s->descriptor_flags==COH_DB_WIN_CLOEXEC;
}
static int loopback(const struct sockaddr *a,int length,unsigned port) {
    static const unsigned char local[4]={127,0,0,1};
    if(!a||length!=(int)sizeof(struct sockaddr_in))return 0;
    const struct sockaddr_in *v=(const struct sockaddr_in *)a;
    return v->sin_family==AF_INET&&!memcmp(&v->sin_addr.s_addr,local,4)&&v->sin_port==htons((unsigned short)port);
}
void coh_db_win_diagnostics(CohDbWinDiagnostics *out) {if(out)*out=diagnostics;}
int coh_db_win_initialize(void) {
    if(diagnostics.initialized){errno=EINVAL;return -1;}
    WSADATA data;int result=WSAStartup(MAKEWORD(2,2),&data);
    if(result){errno=translate(result);return -1;}
    memset(slots,0,sizeof(slots));memset(&diagnostics,0,sizeof(diagnostics));next_slot=0;
    diagnostics.initialized=1;ready=0;
    if(data.wVersion!=MAKEWORD(2,2)) {
        /* Retain the acquired WSA reference if its release fails. */
        if(WSACleanup())diagnostics.cleanup_failures++;
        else {diagnostics.initialized=0;diagnostics.cleanup_complete=1;}
        errno=EINVAL;return -1;
    }
    ready=1;return 0;
}
int coh_db_win_socket(int family,int type,int protocol) {
    if(!ready||family!=AF_INET||type!=SOCK_DGRAM||protocol!=IPPROTO_UDP){errno=EINVAL;return -1;}
    /* Tokens are never reused during one initialization, including after a
     * successful close. A stale core token cannot close a later socket. */
    if(next_slot==COH_DB_WIN_SLOTS){errno=EMFILE;return -1;}
    SOCKET value=socket(family,type,protocol);if(value==INVALID_SOCKET)return failed();
    unsigned token=next_slot++;slots[token]=(Slot){value,1,0,0,0};
    diagnostics.active_handles++;diagnostics.sockets_created++;return (int)token;
}
int coh_db_win_close(int fd) {
    Slot *s=owned(fd);if(!s)return -1;
    if(closesocket(s->value)==SOCKET_ERROR){diagnostics.close_failures++;return failed();}
    memset(s,0,sizeof(*s));diagnostics.active_handles--;diagnostics.sockets_closed++;return 0;
}
int coh_db_win_finish(void) {
    ready=0;
    if(!diagnostics.initialized)return diagnostics.active_handles?-1:0;
    for(int i=0;i<COH_DB_WIN_SLOTS;i++)if(slots[i].active)(void)coh_db_win_close(i);
    if(diagnostics.active_handles){errno=EIO;return -1;}
    if(WSACleanup()){diagnostics.cleanup_failures++;return failed();}
    diagnostics.initialized=0;diagnostics.cleanup_complete=1;return 0;
}
int coh_db_win_fcntl(int fd,int command,int value) {
    Slot *s=owned(fd);if(!s)return -1;
    if(!ready){errno=EINVAL;return -1;}
    if(command==COH_DB_WIN_GETFL)return s->flags;
    if(command==COH_DB_WIN_GETFD)return s->descriptor_flags;
    if(command==COH_DB_WIN_SETFL&&value==COH_DB_WIN_NONBLOCK){
        u_long on=1;if(ioctlsocket(s->value,FIONBIO,&on)==SOCKET_ERROR)return failed();
        s->flags=value;return 0;
    }
    if(command==COH_DB_WIN_SETFD&&value==COH_DB_WIN_CLOEXEC){
        if(!SetHandleInformation((HANDLE)(uintptr_t)s->value,HANDLE_FLAG_INHERIT,0)){errno=EIO;return -1;}
        s->descriptor_flags=value;return 0;
    }
    errno=EINVAL;return -1;
}
int coh_db_win_bind(int fd,const struct sockaddr *a,int length) {
    Slot *s=owned(fd);if(!s)return -1;
    if(!configured(s)||s->bound||!loopback(a,length,0)){errno=EINVAL;return -1;}
    if(bind(s->value,a,length)==SOCKET_ERROR)return failed();
    s->bound=1;return 0;
}
int coh_db_win_getsockname(int fd,struct sockaddr *a,int *length) {
    Slot *s=owned(fd);if(!s)return -1;
    if(!configured(s)||!s->bound||!a||!length||*length!=(int)sizeof(struct sockaddr_in)){errno=EINVAL;return -1;}
    if(getsockname(s->value,a,length)==SOCKET_ERROR)return failed();
    const struct sockaddr_in *v=(const struct sockaddr_in *)a;
    if(*length!=(int)sizeof(*v)||!v->sin_port||!loopback(a,*length,ntohs(v->sin_port))){errno=EIO;return -1;}
    return 0;
}
ptrdiff_t coh_db_win_sendto(int fd,const void *bytes,size_t count,int flags,const struct sockaddr *a,int length) {
    Slot *s=owned(fd);if(!s)return -1;
    if(!configured(s)||!s->bound||!bytes||!count||count>COH_PROTOCOL_FRAME_MAX||flags||!loopback(a,length,7000)){errno=EINVAL;return -1;}
    int result=sendto(s->value,(const char *)bytes,(int)count,0,a,length);
    if(result==SOCKET_ERROR)return failed();
    if(result<0||(size_t)result!=count){errno=EIO;return -1;}
    return result;
}
ptrdiff_t coh_db_win_recvmsg(int fd,struct CohDbWinMsghdr *m,int flags) {
    Slot *s=owned(fd);if(!s)return -1;
    if(!configured(s)||!s->bound||!m||flags!=COH_DB_WIN_DONTWAIT||!m->msg_name||m->msg_namelen!=(int)sizeof(struct sockaddr_in)||
       !m->msg_iov||m->msg_iovlen!=1||!m->msg_iov[0].iov_base||!m->msg_iov[0].iov_len||m->msg_iov[0].iov_len>COH_PROTOCOL_FRAME_MAX){errno=EINVAL;return -1;}
    m->msg_flags=0;int length=m->msg_namelen,capacity=(int)m->msg_iov[0].iov_len;
    int result=recvfrom(s->value,(char *)m->msg_iov[0].iov_base,capacity,0,(struct sockaddr *)m->msg_name,&length);
    m->msg_namelen=length;
    if(result==SOCKET_ERROR){
        int error=WSAGetLastError();
        /* Winsock UDP drops the remainder on WSAEMSGSIZE. Preserve the POSIX
         * truncation flag so the unchanged UDP core discards this datagram. */
        if(error==WSAEMSGSIZE){m->msg_flags=COH_DB_WIN_TRUNC;return capacity;}
        errno=translate(error);return -1;
    }
    if(result<0||result>capacity){errno=EIO;return -1;}
    return result;
}
