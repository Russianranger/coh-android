#include "winsock_compat.h"

typedef struct { SOCKET socket; int active, flags, descriptor_flags; size_t sent; } Slot;
static Slot slots[COH_WIN_SLOTS];
static int initialized, corrupt;
static unsigned send_cap = 1024, receive_cap = 1024;
static int translate(int error) {
    switch (error) {
    case 0: return 0;
    case WSAEWOULDBLOCK: return EAGAIN;
    case WSAEINPROGRESS: case WSAEALREADY: return EINPROGRESS;
    case WSAEINTR: return EINTR;
    case WSAECONNRESET: case WSAECONNABORTED: return ECONNRESET;
    case WSAECONNREFUSED: return ECONNREFUSED;
    case WSAETIMEDOUT: return ETIMEDOUT;
    case WSAENOTSOCK: return EBADF;
    case WSAEINVAL: return EINVAL;
    case WSAENOBUFS: return ENOMEM;
    default: return EIO;
    }
}
static int failed(void) { errno = translate(WSAGetLastError()); return -1; }
static Slot *slot(int fd) {
    if (!initialized || fd < 0 || fd >= COH_WIN_SLOTS || !slots[fd].active) { errno = EBADF; return NULL; }
    return &slots[fd];
}
unsigned coh_win_open_handles(void) { unsigned result = 0; for (unsigned i=0;i<COH_WIN_SLOTS;i++) result += !!slots[i].active; return result; }
int coh_win_initialize(void) {
    WSADATA data;
    if (initialized) { errno=EINVAL; return -1; }
    int result = WSAStartup(MAKEWORD(2,2), &data);
    if (result) { errno=translate(result); return -1; }
    if (data.wVersion != MAKEWORD(2,2)) { WSACleanup(); errno=EINVAL; return -1; }
    memset(slots,0,sizeof(slots)); initialized=1; return 0;
}
int coh_win_finish(void) {
    int clean=1;
    if (!initialized) return 0;
    for (int i=0;i<COH_WIN_SLOTS;i++) if (slots[i].active && coh_win_close(i)) clean=0;
    if (WSACleanup()) clean=0;
    initialized=0;
    return clean && !coh_win_open_handles() ? 0 : -1;
}
int coh_win_limits(unsigned outgoing, unsigned incoming, int fault) {
    if (!outgoing || outgoing>1024 || !incoming || incoming>1024 || (fault!=0 && fault!=1) || coh_win_open_handles()) { errno=EINVAL; return -1; }
    send_cap=outgoing; receive_cap=incoming; corrupt=fault; return 0;
}
int coh_win_socket(int family, int type, int protocol) {
    if (!initialized || family!=AF_INET || type!=SOCK_STREAM || protocol!=IPPROTO_TCP) { errno=EINVAL; return -1; }
    int index; for(index=0;index<COH_WIN_SLOTS && slots[index].active;index++);
    if(index==COH_WIN_SLOTS) { errno=EMFILE; return -1; }
    SOCKET value=socket(family,type,protocol);
    if(value==INVALID_SOCKET) return failed();
    slots[index]=(Slot){value,1,0,0,0}; return index;
}
int coh_win_close(int fd) {
    Slot *s=slot(fd); if(!s) return -1;
    if(closesocket(s->socket)==SOCKET_ERROR) return failed();
    memset(s,0,sizeof(*s)); return 0;
}
int coh_win_connect(int fd, const struct sockaddr *address, int length) {
    Slot *s=slot(fd); if(!s) return -1;
    if (!address || length!=(int)sizeof(struct sockaddr_in) || !(s->flags&COH_WIN_NONBLOCK)) { errno=EINVAL; return -1; }
    if(connect(s->socket,address,length)==SOCKET_ERROR) {
        int error=WSAGetLastError(); errno=error==WSAEWOULDBLOCK?EINPROGRESS:translate(error); return -1;
    }
    return 0;
}
int coh_win_fcntl(int fd, int command, int value) {
    Slot *s=slot(fd); if(!s) return -1;
    if(command==COH_WIN_GETFL) return s->flags;
    if(command==COH_WIN_GETFD) return s->descriptor_flags;
    if(command==COH_WIN_SETFL && value==COH_WIN_NONBLOCK) {
        u_long on=1; if(ioctlsocket(s->socket,FIONBIO,&on)==SOCKET_ERROR) return failed();
        s->flags=value; return 0;
    }
    if(command==COH_WIN_SETFD && value==COH_WIN_CLOEXEC) {
        if(!SetHandleInformation((HANDLE)(uintptr_t)s->socket,HANDLE_FLAG_INHERIT,0)) { errno=EIO; return -1; }
        s->descriptor_flags=value; return 0;
    }
    errno=EINVAL; return -1;
}
ptrdiff_t coh_win_send(int fd, const void *bytes, size_t size, int flags) {
    Slot *s=slot(fd); if(!s) return -1;
    if(!bytes || !size || flags!=COH_WIN_NOSIGNAL || !(s->flags&COH_WIN_NONBLOCK)) { errno=EINVAL; return -1; }
    size_t take=size<send_cap?size:send_cap;
    unsigned char copy[1024]; memcpy(copy,bytes,take);
    /* Explicit negative-control fault; original/native cryptographic code is
     * unchanged. Track successful sends so EAGAIN/partial sends cannot move it. */
    if(corrupt && s->sent<=2 && s->sent+take>2) copy[2-s->sent]^=1;
    int result=send(s->socket,(const char *)copy,(int)take,0);
    SecureZeroMemory(copy,sizeof(copy));
    if(result==SOCKET_ERROR) return failed();
    if(result<0 || (unsigned)result>take) { errno=EIO; return -1; }
    s->sent+=(size_t)result; return result;
}
ptrdiff_t coh_win_recv(int fd, void *bytes, size_t size, int flags) {
    Slot *s=slot(fd); if(!s) return -1;
    if(!bytes || !size || flags!=COH_WIN_DONTWAIT || !(s->flags&COH_WIN_NONBLOCK)) { errno=EINVAL; return -1; }
    size_t take=size<receive_cap?size:receive_cap;
    int result=recv(s->socket,(char *)bytes,(int)take,0);
    if(result==SOCKET_ERROR) return failed();
    return result;
}
int coh_win_poll(struct CohWinPollfd *fds, size_t count, int timeout) {
    if(!fds || count!=1 || timeout!=0 || fds[0].events!=POLLOUT) { errno=EINVAL; return -1; }
    Slot *s=slot(fds[0].fd); if(!s) return -1;
    WSAPOLLFD value={s->socket,POLLOUT,0};
    fds[0].revents=0;
    int result=WSAPoll(&value,1,0);
    if(result==SOCKET_ERROR) return failed();
    fds[0].revents=value.revents; return result;
}
int coh_win_getsockopt(int fd, int level, int option, void *value, int *size) {
    Slot *s=slot(fd); if(!s) return -1;
    if(level!=SOL_SOCKET || option!=SO_ERROR || !value || !size || *size!=(int)sizeof(int)) { errno=EINVAL; return -1; }
    int error=0, length=sizeof(error);
    if(getsockopt(s->socket,level,option,(char *)&error,&length)==SOCKET_ERROR) return failed();
    if(length!=sizeof(error)) { errno=EIO; return -1; }
    *(int *)value=translate(error); *size=sizeof(error); return 0;
}
