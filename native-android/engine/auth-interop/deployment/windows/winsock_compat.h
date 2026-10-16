/* Nonshipping, single-owner Windows transport for the unchanged login core. */
#ifndef COH_AUTH_STAGE_WINSOCK_COMPAT_H
#define COH_AUTH_STAGE_WINSOCK_COMPAT_H
#ifdef COH_WINSOCK_TEST
#include "test_winsock_api.h"
#else
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <windows.h>
#endif
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

/* Only the operations actually used by coh_login.c are admitted. SOCKET is
 * never narrowed to int: the core owns a bounded table token instead. */
#define COH_WIN_SLOTS 4
#define COH_WIN_GETFL 1
#define COH_WIN_SETFL 2
#define COH_WIN_GETFD 3
#define COH_WIN_SETFD 4
#define COH_WIN_NONBLOCK 1
#define COH_WIN_CLOEXEC 1
#define COH_WIN_NOSIGNAL 0x4000
#define COH_WIN_DONTWAIT 0x4000
struct CohWinPollfd { int fd; short events, revents; };
int coh_win_initialize(void);
int coh_win_finish(void);
unsigned coh_win_open_handles(void);
int coh_win_limits(unsigned send_limit, unsigned receive_limit, int corrupt_first_frame);
int coh_win_socket(int family, int type, int protocol);
int coh_win_connect(int fd, const struct sockaddr *address, int length);
int coh_win_close(int fd);
int coh_win_fcntl(int fd, int command, int value);
ptrdiff_t coh_win_send(int fd, const void *bytes, size_t size, int flags);
ptrdiff_t coh_win_recv(int fd, void *bytes, size_t size, int flags);
int coh_win_poll(struct CohWinPollfd *fds, size_t count, int timeout);
int coh_win_getsockopt(int fd, int level, int option, void *value, int *size);

#ifdef COH_WRAP_LOGIN
#define socket coh_win_socket
#define connect coh_win_connect
#define close coh_win_close
#define fcntl coh_win_fcntl
#define send coh_win_send
#define recv coh_win_recv
#define poll coh_win_poll
#define getsockopt coh_win_getsockopt
#define pollfd CohWinPollfd
#define ssize_t ptrdiff_t
#define socklen_t int
#define F_GETFL COH_WIN_GETFL
#define F_SETFL COH_WIN_SETFL
#define F_GETFD COH_WIN_GETFD
#define F_SETFD COH_WIN_SETFD
#define O_NONBLOCK COH_WIN_NONBLOCK
#define FD_CLOEXEC COH_WIN_CLOEXEC
#define MSG_NOSIGNAL COH_WIN_NOSIGNAL
#define MSG_DONTWAIT COH_WIN_DONTWAIT
#endif
#endif
