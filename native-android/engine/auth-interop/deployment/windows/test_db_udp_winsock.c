#include "db_udp_winsock.h"
#include <stdio.h>
#define REQUIRE(x) do {checks++;if(!(x)){fprintf(stderr,"UDP shell control line %d\n",__LINE__);return 1;}}while(0)
static unsigned checks;
static int error,startup_error,bad_version,cleanup_error,close_error,io_error,inherit_error;
static int bind_error,name_error,name_bad,send_error,send_short,recv_error,recv_result=5,recv_bad_length;
static unsigned starts,cleanups,send_calls,recv_calls;
static SOCKET next_socket=UINT64_C(0x8000000000000001),observed_socket;
static struct sockaddr_in remote;
int WSAStartup(unsigned short v,WSADATA *out){starts++;out->wVersion=bad_version?0:v;return startup_error;}
int WSACleanup(void){cleanups++;error=cleanup_error;return error?SOCKET_ERROR:0;}
int WSAGetLastError(void){return error;}
SOCKET socket(int family,int type,int protocol){(void)family;(void)type;(void)protocol;return next_socket++;}
int closesocket(SOCKET s){observed_socket=s;error=close_error;return error?SOCKET_ERROR:0;}
int ioctlsocket(SOCKET s,long c,u_long *v){observed_socket=s;(void)c;(void)v;error=io_error;return error?SOCKET_ERROR:0;}
int SetHandleInformation(HANDLE s,unsigned m,unsigned f){observed_socket=s;(void)m;(void)f;return !inherit_error;}
int bind(SOCKET s,const struct sockaddr *a,int n){observed_socket=s;(void)a;(void)n;error=bind_error;return error?SOCKET_ERROR:0;}
int getsockname(SOCKET s,struct sockaddr *a,int *n){
    observed_socket=s;struct sockaddr_in *v=(struct sockaddr_in *)a;memset(v,0,sizeof(*v));
    v->sin_family=AF_INET;v->sin_port=htons(30000);unsigned char ip[4]={127,0,0,1};memcpy(&v->sin_addr.s_addr,ip,4);
    if(name_bad)v->sin_addr.s_addr=0;
    *n=sizeof(*v);error=name_error;return error?SOCKET_ERROR:0;
}
int sendto(SOCKET s,const char *p,int n,int f,const struct sockaddr *a,int l){
    observed_socket=s;send_calls++;(void)p;(void)f;(void)a;(void)l;error=send_error;return error?SOCKET_ERROR:n-send_short;
}
int recvfrom(SOCKET s,char *p,int n,int f,struct sockaddr *a,int *l){
    observed_socket=s;recv_calls++;(void)f;memset(p,0x5a,(size_t)n);memcpy(a,&remote,sizeof(remote));
    *l=recv_bad_length?1:(int)sizeof(remote);error=recv_error;return error?SOCKET_ERROR:recv_result;
}
static struct sockaddr_in endpoint(unsigned short port){
    struct sockaddr_in v;memset(&v,0,sizeof(v));v.sin_family=AF_INET;v.sin_port=htons(port);
    unsigned char ip[4]={127,0,0,1};memcpy(&v.sin_addr.s_addr,ip,4);return v;
}
int main(void){
    CohDbWinDiagnostics d;coh_db_win_diagnostics(&d);REQUIRE(!d.initialized&&!d.active_handles);
    REQUIRE(coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)==-1);
    startup_error=WSAENOBUFS;REQUIRE(coh_db_win_initialize()==-1&&errno==ENOMEM);startup_error=0;
    bad_version=1;cleanup_error=WSAEINVAL;REQUIRE(coh_db_win_initialize()==-1);
    coh_db_win_diagnostics(&d);REQUIRE(d.initialized&&!d.cleanup_complete&&d.cleanup_failures==1);
    REQUIRE(coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)==-1);
    REQUIRE(coh_db_win_finish()==-1);cleanup_error=0;REQUIRE(coh_db_win_finish()==0);bad_version=0;
    REQUIRE(coh_db_win_initialize()==0);REQUIRE(coh_db_win_initialize()==-1);
    REQUIRE(coh_db_win_socket(AF_INET,1,IPPROTO_UDP)==-1);
    int fd=coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);SOCKET full=next_socket-1;REQUIRE(fd==0&&full>UINT32_MAX);
    struct sockaddr_in local=endpoint(0),peer=endpoint(7000);remote=peer;
    REQUIRE(coh_db_win_bind(fd,(struct sockaddr *)&local,sizeof(local))==-1);
    REQUIRE(coh_db_win_fcntl(fd,COH_DB_WIN_GETFL,0)==0);
    io_error=WSAEINVAL;REQUIRE(coh_db_win_fcntl(fd,COH_DB_WIN_SETFL,COH_DB_WIN_NONBLOCK)==-1);io_error=0;
    REQUIRE(coh_db_win_fcntl(fd,COH_DB_WIN_SETFL,COH_DB_WIN_NONBLOCK)==0&&observed_socket==full);
    inherit_error=1;REQUIRE(coh_db_win_fcntl(fd,COH_DB_WIN_SETFD,COH_DB_WIN_CLOEXEC)==-1);inherit_error=0;
    REQUIRE(coh_db_win_fcntl(fd,COH_DB_WIN_SETFD,COH_DB_WIN_CLOEXEC)==0&&observed_socket==full);
    REQUIRE(coh_db_win_fcntl(fd,COH_DB_WIN_GETFD,0)==COH_DB_WIN_CLOEXEC);
    REQUIRE(coh_db_win_fcntl(fd,999,0)==-1);
    REQUIRE(coh_db_win_bind(fd,(struct sockaddr *)&peer,sizeof(peer))==-1);
    struct sockaddr_in wildcard=local;wildcard.sin_addr.s_addr=0;
    REQUIRE(coh_db_win_bind(fd,(struct sockaddr *)&wildcard,sizeof(wildcard))==-1);
    bind_error=WSAEINVAL;REQUIRE(coh_db_win_bind(fd,(struct sockaddr *)&local,sizeof(local))==-1);bind_error=0;
    REQUIRE(coh_db_win_bind(fd,(struct sockaddr *)&local,sizeof(local))==0&&observed_socket==full);
    REQUIRE(coh_db_win_bind(fd,(struct sockaddr *)&local,sizeof(local))==-1);
    int length=sizeof(local);name_error=WSAEINVAL;REQUIRE(coh_db_win_getsockname(fd,(struct sockaddr *)&local,&length)==-1);name_error=0;
    name_bad=1;REQUIRE(coh_db_win_getsockname(fd,(struct sockaddr *)&local,&length)==-1);name_bad=0;
    REQUIRE(coh_db_win_getsockname(fd,(struct sockaddr *)&local,&length)==0&&ntohs(local.sin_port)==30000&&observed_socket==full);
    unsigned char data[64]={0};
    REQUIRE(coh_db_win_sendto(fd,data,sizeof(data),0,(struct sockaddr *)&peer,sizeof(peer))==sizeof(data)&&observed_socket==full);
    unsigned sent=send_calls;peer.sin_port=htons(7001);
    REQUIRE(coh_db_win_sendto(fd,data,sizeof(data),0,(struct sockaddr *)&peer,sizeof(peer))==-1&&send_calls==sent);peer.sin_port=htons(7000);
    peer.sin_addr.s_addr=0;REQUIRE(coh_db_win_sendto(fd,data,sizeof(data),0,(struct sockaddr *)&peer,sizeof(peer))==-1);peer=endpoint(7000);
    REQUIRE(coh_db_win_sendto(fd,data,1473,0,(struct sockaddr *)&peer,sizeof(peer))==-1);
    send_error=WSAEWOULDBLOCK;REQUIRE(coh_db_win_sendto(fd,data,sizeof(data),0,(struct sockaddr *)&peer,sizeof(peer))==-1&&errno==EAGAIN);send_error=0;
    send_short=1;REQUIRE(coh_db_win_sendto(fd,data,sizeof(data),0,(struct sockaddr *)&peer,sizeof(peer))==-1&&errno==EIO);send_short=0;
    struct sockaddr_in from;struct CohDbWinIovec iov={data,sizeof(data)};
    struct CohDbWinMsghdr m={&from,sizeof(from),&iov,1,0};
    REQUIRE(coh_db_win_recvmsg(fd,&m,0)==-1&&recv_calls==0);
    REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==5&&data[0]==0x5a&&!m.msg_flags&&observed_socket==full);
    REQUIRE(!memcmp(&from,&remote,sizeof(from))&&m.msg_namelen==sizeof(from));
    recv_error=WSAEWOULDBLOCK;REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==-1&&errno==EAGAIN);
    recv_error=WSAEINTR;REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==-1&&errno==EINTR);
    recv_error=WSAECONNRESET;REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==-1&&errno==ECONNRESET);
    recv_error=WSAEMSGSIZE;REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==sizeof(data)&&m.msg_flags==COH_DB_WIN_TRUNC);
    recv_error=0;recv_result=0;REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==0&&!m.msg_flags);
    recv_result=65;REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==-1&&errno==EIO);recv_result=5;
    recv_bad_length=1;REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==5&&m.msg_namelen==1);recv_bad_length=0;m.msg_namelen=sizeof(from);
    m.msg_iovlen=2;REQUIRE(coh_db_win_recvmsg(fd,&m,COH_DB_WIN_DONTWAIT)==-1);m.msg_iovlen=1;
    /* The ordinary UDP owner may forget fd after this failure. The adapter
     * still owns the full SOCKET and refuses to release its WSA reference. */
    close_error=WSAEINVAL;REQUIRE(coh_db_win_close(fd)==-1);coh_db_win_diagnostics(&d);
    REQUIRE(d.active_handles==1&&d.sockets_created==1&&!d.sockets_closed&&d.close_failures==1);
    unsigned cleaned=cleanups;REQUIRE(coh_db_win_finish()==-1&&cleanups==cleaned);
    coh_db_win_diagnostics(&d);REQUIRE(d.initialized&&d.active_handles==1&&!d.cleanup_complete);
    REQUIRE(coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)==-1);
    close_error=0;cleanup_error=WSAEINVAL;REQUIRE(coh_db_win_finish()==-1&&observed_socket==full);
    coh_db_win_diagnostics(&d);REQUIRE(d.initialized&&!d.active_handles&&d.sockets_closed==1&&d.cleanup_failures==1);
    cleanup_error=0;REQUIRE(coh_db_win_finish()==0);coh_db_win_diagnostics(&d);
    REQUIRE(!d.initialized&&!d.active_handles&&d.cleanup_complete&&d.sockets_created==d.sockets_closed);
    REQUIRE(coh_db_win_close(fd)==-1&&errno==EBADF);
    REQUIRE(coh_db_win_initialize()==0);fd=coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);REQUIRE(fd==0);
    REQUIRE(coh_db_win_close(fd)==0);int second=coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);REQUIRE(second==1);
    REQUIRE(coh_db_win_close(fd)==-1&&errno==EBADF);
    REQUIRE(coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)==2);REQUIRE(coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)==3);
    REQUIRE(coh_db_win_socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)==-1&&errno==EMFILE);
    REQUIRE(coh_db_win_finish()==0);coh_db_win_diagnostics(&d);REQUIRE(d.sockets_created==4&&d.sockets_closed==4&&!d.active_handles&&d.cleanup_complete);
    printf("{\"passed\":true,\"checks\":%u,\"real_windows_execution\":false,\"real_db_login_verified\":false}\n",checks);return 0;
}
