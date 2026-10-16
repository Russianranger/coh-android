#include "winsock_compat.h"
#include <stdio.h>
#define REQUIRE(x) do { checks++; if(!(x)) { fprintf(stderr,"adapter control line %d\n",__LINE__); return 1; } } while(0)
static unsigned checks;
static int error, startup_error, close_error, connect_error, io_error, inherit_error;
static int send_result=INT_MAX, poll_error, socket_error, getsock_error, startup_count, cleanup_count;
static SOCKET next_socket=UINT64_C(0x8000000000000001), observed_socket;
static unsigned char outgoing[1024]; static int outgoing_length;
int WSAStartup(unsigned short version,WSADATA *data) { startup_count++; data->wVersion=version; return startup_error; }
int WSACleanup(void) { cleanup_count++; return 0; }
int WSAGetLastError(void) { return error; }
SOCKET socket(int a,int b,int c) { (void)a;(void)b;(void)c; return next_socket++; }
int closesocket(SOCKET value) { observed_socket=value; error=close_error;return error?SOCKET_ERROR:0; }
int connect(SOCKET value,const struct sockaddr *a,int n) { observed_socket=value;(void)a;(void)n;error=connect_error;return error?SOCKET_ERROR:0; }
int ioctlsocket(SOCKET value,long command,u_long *on) { observed_socket=value;(void)command;(void)on;error=io_error;return error?SOCKET_ERROR:0; }
int SetHandleInformation(HANDLE value,unsigned mask,unsigned flags) { observed_socket=value;(void)mask;(void)flags;return !inherit_error; }
int send(SOCKET value,const char *data,int count,int flags) { observed_socket=value;(void)flags;memcpy(outgoing,data,count);outgoing_length=count;return send_result==INT_MAX?count:send_result; }
int recv(SOCKET value,char *data,int count,int flags) { observed_socket=value;(void)flags;memset(data,0x5a,count);return count; }
int WSAPoll(WSAPOLLFD *p,unsigned n,int timeout) { observed_socket=p->fd;(void)n;(void)timeout;error=poll_error;p->revents=POLLOUT;return error?SOCKET_ERROR:1; }
int getsockopt(SOCKET value,int level,int option,char *out,int *size) { observed_socket=value;(void)level;(void)option;*(int*)out=socket_error;*size=sizeof(int);error=getsock_error;return error?SOCKET_ERROR:0; }
int main(void) {
    REQUIRE(coh_win_socket(AF_INET,SOCK_STREAM,IPPROTO_TCP)==-1);
    startup_error=WSAENOBUFS;REQUIRE(coh_win_initialize()==-1 && errno==ENOMEM);
    startup_error=0;REQUIRE(coh_win_initialize()==0);REQUIRE(coh_win_initialize()==-1);
    REQUIRE(coh_win_limits(0,1,0)==-1);REQUIRE(coh_win_limits(1025,1,0)==-1);
    REQUIRE(coh_win_limits(7,11,1)==0);
    int fd=coh_win_socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);REQUIRE(fd==0);
    SOCKET full=next_socket-1;REQUIRE(full>UINT32_MAX);
    REQUIRE(coh_win_limits(7,11,0)==-1);REQUIRE(coh_win_open_handles()==1);
    REQUIRE(coh_win_fcntl(fd,COH_WIN_GETFL,0)==0);
    REQUIRE(coh_win_fcntl(fd,COH_WIN_SETFL,0)==-1);
    io_error=WSAEINVAL;REQUIRE(coh_win_fcntl(fd,COH_WIN_SETFL,COH_WIN_NONBLOCK)==-1 && errno==EINVAL);
    io_error=0;REQUIRE(coh_win_fcntl(fd,COH_WIN_SETFL,COH_WIN_NONBLOCK)==0 && observed_socket==full);
    REQUIRE(coh_win_fcntl(fd,COH_WIN_GETFL,0)==COH_WIN_NONBLOCK);
    inherit_error=1;REQUIRE(coh_win_fcntl(fd,COH_WIN_SETFD,COH_WIN_CLOEXEC)==-1);
    inherit_error=0;REQUIRE(coh_win_fcntl(fd,COH_WIN_SETFD,COH_WIN_CLOEXEC)==0 && observed_socket==full);
    REQUIRE(coh_win_fcntl(fd,COH_WIN_GETFD,0)==COH_WIN_CLOEXEC);
    struct sockaddr_in address={0};
    connect_error=WSAEWOULDBLOCK;REQUIRE(coh_win_connect(fd,(struct sockaddr*)&address,sizeof(address))==-1 && errno==EINPROGRESS);
    connect_error=WSAECONNREFUSED;REQUIRE(coh_win_connect(fd,(struct sockaddr*)&address,sizeof(address))==-1 && errno==ECONNREFUSED);
    connect_error=0;REQUIRE(coh_win_connect(fd,(struct sockaddr*)&address,sizeof(address))==0 && observed_socket==full);
    unsigned char bytes[20]={0},input[20]={0};
    error=WSAEWOULDBLOCK;send_result=SOCKET_ERROR;
    REQUIRE(coh_win_send(fd,bytes,sizeof(bytes),COH_WIN_NOSIGNAL)==-1 && errno==EAGAIN && outgoing[2]==1);
    send_result=2;REQUIRE(coh_win_send(fd,bytes,sizeof(bytes),COH_WIN_NOSIGNAL)==2 && outgoing[2]==1);
    send_result=1;REQUIRE(coh_win_send(fd,bytes+2,sizeof(bytes)-2,COH_WIN_NOSIGNAL)==1 && outgoing[0]==1);
    send_result=INT_MAX;REQUIRE(coh_win_send(fd,bytes+3,sizeof(bytes)-3,COH_WIN_NOSIGNAL)==7 && outgoing[0]==0 && outgoing_length==7 && observed_socket==full);
    REQUIRE(bytes[2]==0);REQUIRE(coh_win_send(fd,bytes,sizeof(bytes),0)==-1);
    REQUIRE(coh_win_recv(fd,input,sizeof(input),COH_WIN_DONTWAIT)==11 && input[10]==0x5a && input[11]==0 && observed_socket==full);
    REQUIRE(coh_win_recv(fd,input,sizeof(input),0)==-1);
    struct CohWinPollfd p={fd,POLLOUT,0};
    REQUIRE(coh_win_poll(&p,2,0)==-1);REQUIRE(coh_win_poll(&p,1,1)==-1);
    REQUIRE(coh_win_poll(&p,1,0)==1 && p.revents==POLLOUT && observed_socket==full);
    poll_error=WSAEINTR;REQUIRE(coh_win_poll(&p,1,0)==-1 && errno==EINTR);poll_error=0;
    int value,length=sizeof(value);socket_error=WSAECONNRESET;
    REQUIRE(coh_win_getsockopt(fd,SOL_SOCKET,SO_ERROR,&value,&length)==0 && value==ECONNRESET && observed_socket==full);
    getsock_error=WSAENOTSOCK;REQUIRE(coh_win_getsockopt(fd,SOL_SOCKET,SO_ERROR,&value,&length)==-1 && errno==EBADF);getsock_error=0;
    for(int i=1;i<COH_WIN_SLOTS;i++) REQUIRE(coh_win_socket(AF_INET,SOCK_STREAM,IPPROTO_TCP)==i);
    REQUIRE(coh_win_socket(AF_INET,SOCK_STREAM,IPPROTO_TCP)==-1 && errno==EMFILE);
    close_error=WSAEINVAL;REQUIRE(coh_win_close(fd)==-1 && coh_win_open_handles()==COH_WIN_SLOTS);close_error=0;
    REQUIRE(coh_win_close(fd)==0 && observed_socket==full);REQUIRE(coh_win_close(fd)==-1 && errno==EBADF);
    REQUIRE(coh_win_finish()==0 && coh_win_open_handles()==0 && cleanup_count==1);
    REQUIRE(startup_count==2);REQUIRE(coh_win_finish()==0 && cleanup_count==1);
    printf("{\"passed\":true,\"checks\":%u,\"real_windows_execution\":false,\"real_account_login_verified\":false}\n",checks);
    return 0;
}
