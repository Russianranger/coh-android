/* Deterministic Windows API shell; no socket or Windows execution. */
#ifndef COH_TEST_DB_UDP_WINSOCK_API_H
#define COH_TEST_DB_UDP_WINSOCK_API_H
#include <stddef.h>
#include <stdint.h>
typedef uint64_t SOCKET;
typedef uintptr_t HANDLE;
typedef unsigned long u_long;
typedef struct { unsigned short wVersion; } WSADATA;
struct sockaddr {unsigned short sa_family;char sa_data[14];};
struct in_addr {uint32_t s_addr;};
struct sockaddr_in {short sin_family;unsigned short sin_port;struct in_addr sin_addr;char sin_zero[8];};
#define INVALID_SOCKET UINT64_MAX
#define SOCKET_ERROR -1
#define MAKEWORD(a,b) ((unsigned short)((a)|((b)<<8)))
#define AF_INET 2
#define SOCK_DGRAM 2
#define IPPROTO_UDP 17
#define FIONBIO 1
#define HANDLE_FLAG_INHERIT 1
#define WSAEINTR 10004
#define WSAEINVAL 10022
#define WSAEWOULDBLOCK 10035
#define WSAENOTSOCK 10038
#define WSAEMSGSIZE 10040
#define WSAECONNABORTED 10053
#define WSAECONNRESET 10054
#define WSAENOBUFS 10055
#define WSAETIMEDOUT 10060
#define WSAECONNREFUSED 10061
int WSAStartup(unsigned short,WSADATA *);
int WSACleanup(void);
int WSAGetLastError(void);
SOCKET socket(int,int,int);
int closesocket(SOCKET);
int ioctlsocket(SOCKET,long,u_long *);
int SetHandleInformation(HANDLE,unsigned,unsigned);
int bind(SOCKET,const struct sockaddr *,int);
int getsockname(SOCKET,struct sockaddr *,int *);
int sendto(SOCKET,const char *,int,int,const struct sockaddr *,int);
int recvfrom(SOCKET,char *,int,int,struct sockaddr *,int *);
static inline unsigned short htons(unsigned short n) {return (unsigned short)((n<<8)|(n>>8));}
static inline unsigned short ntohs(unsigned short n) {return htons(n);}
#endif
