/* Deterministic syscall shell, not a Windows or AuthServer execution. */
#ifndef COH_TEST_WINSOCK_API_H
#define COH_TEST_WINSOCK_API_H
#include <stdint.h>
#include <stddef.h>
typedef uint64_t SOCKET;
typedef uintptr_t HANDLE;
typedef unsigned long u_long;
typedef struct { unsigned short wVersion; } WSADATA;
typedef struct { SOCKET fd; short events, revents; } WSAPOLLFD;
struct sockaddr { unsigned short family; char bytes[14]; };
struct sockaddr_in { unsigned short family, port; uint32_t address; char zero[8]; };
#define INVALID_SOCKET UINT64_MAX
#define SOCKET_ERROR -1
#define MAKEWORD(a,b) ((unsigned short)((a)|((b)<<8)))
#define AF_INET 2
#define SOCK_STREAM 1
#define IPPROTO_TCP 6
#define FIONBIO 1
#define HANDLE_FLAG_INHERIT 1
#define POLLOUT 16
#define POLLERR 1
#define SOL_SOCKET 65535
#define SO_ERROR 4103
#define WSAEINTR 10004
#define WSAEINVAL 10022
#define WSAEWOULDBLOCK 10035
#define WSAEINPROGRESS 10036
#define WSAEALREADY 10037
#define WSAENOTSOCK 10038
#define WSAECONNABORTED 10053
#define WSAECONNRESET 10054
#define WSAENOBUFS 10055
#define WSAETIMEDOUT 10060
#define WSAECONNREFUSED 10061
int WSAStartup(unsigned short, WSADATA *);
int WSACleanup(void);
int WSAGetLastError(void);
SOCKET socket(int,int,int);
int closesocket(SOCKET);
int connect(SOCKET,const struct sockaddr *,int);
int ioctlsocket(SOCKET,long,u_long *);
int SetHandleInformation(HANDLE,unsigned,unsigned);
int send(SOCKET,const char *,int,int);
int recv(SOCKET,char *,int,int);
int WSAPoll(WSAPOLLFD *,unsigned,int);
int getsockopt(SOCKET,int,int,char *,int *);
static inline void SecureZeroMemory(void *pointer,size_t length) { volatile unsigned char *p=pointer; while(length--) *p++=0; }
#endif
