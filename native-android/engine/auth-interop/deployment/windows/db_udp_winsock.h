/* Nonshipping, single-owner loopback UDP adapter for the unchanged DB core. */
#ifndef COH_DB_UDP_WINSOCK_H
#define COH_DB_UDP_WINSOCK_H
#ifdef COH_DB_WIN_TEST
#include "test_db_udp_winsock_api.h"
#else
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <windows.h>
#endif
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#define COH_DB_WIN_SLOTS 4
#define COH_DB_WIN_GETFL 1
#define COH_DB_WIN_SETFL 2
#define COH_DB_WIN_GETFD 3
#define COH_DB_WIN_SETFD 4
#define COH_DB_WIN_NONBLOCK 1
#define COH_DB_WIN_CLOEXEC 1
#define COH_DB_WIN_DONTWAIT 0x4000
#define COH_DB_WIN_TRUNC 0x20
struct CohDbWinIovec { void *iov_base; size_t iov_len; };
struct CohDbWinMsghdr {
    void *msg_name; int msg_namelen;
    struct CohDbWinIovec *msg_iov; size_t msg_iovlen;
    int msg_flags;
};
typedef struct {
    unsigned initialized, active_handles, sockets_created, sockets_closed;
    unsigned close_failures, cleanup_failures, cleanup_complete;
} CohDbWinDiagnostics;
int coh_db_win_initialize(void);
/* Failed closes remain independently owned even after the POSIX core forgets
 * its integer token. finish retries those handles, but never calls WSACleanup
 * while an active handle remains. A failed WSACleanup is retryable too. */
int coh_db_win_finish(void);
void coh_db_win_diagnostics(CohDbWinDiagnostics *);
int coh_db_win_socket(int family,int type,int protocol);
int coh_db_win_close(int fd);
int coh_db_win_fcntl(int fd,int command,int value);
int coh_db_win_bind(int fd,const struct sockaddr *,int length);
int coh_db_win_getsockname(int fd,struct sockaddr *,int *length);
ptrdiff_t coh_db_win_sendto(int fd,const void *,size_t,int,
    const struct sockaddr *,int length);
ptrdiff_t coh_db_win_recvmsg(int fd,struct CohDbWinMsghdr *,int flags);

#ifdef COH_WRAP_DB_UDP
#define socket coh_db_win_socket
#define close coh_db_win_close
#define fcntl coh_db_win_fcntl
#define bind coh_db_win_bind
#define getsockname coh_db_win_getsockname
#define sendto coh_db_win_sendto
#define recvmsg coh_db_win_recvmsg
#define iovec CohDbWinIovec
#define msghdr CohDbWinMsghdr
#define ssize_t ptrdiff_t
#define socklen_t int
#define F_GETFL COH_DB_WIN_GETFL
#define F_SETFL COH_DB_WIN_SETFL
#define F_GETFD COH_DB_WIN_GETFD
#define F_SETFD COH_DB_WIN_SETFD
#define O_NONBLOCK COH_DB_WIN_NONBLOCK
#define FD_CLOEXEC COH_DB_WIN_CLOEXEC
#ifdef MSG_DONTWAIT
#undef MSG_DONTWAIT
#endif
#define MSG_DONTWAIT COH_DB_WIN_DONTWAIT
#ifdef MSG_TRUNC
#undef MSG_TRUNC
#endif
#define MSG_TRUNC COH_DB_WIN_TRUNC
#endif
#endif
