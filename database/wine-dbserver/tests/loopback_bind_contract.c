/* Compiles the exact patched sockBind/policy fragment and real startup parser.
 * Real kernel sockets exercise both TCP and UDP; only observation/failure APIs
 * are wrapped so the parent can check refusals and close-before-exit ordering. */
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>
#else
#include <arpa/inet.h>
#include <errno.h>
#include <sys/socket.h>
#include <unistd.h>
#include <windows.h>
DWORD coh_test_error;
typedef int SOCKET;
#define INVALID_SOCKET (-1)
#define SOCKET_ERROR (-1)
#define WSAEAFNOSUPPORT EAFNOSUPPORT
#define WSAEADDRNOTAVAIL EADDRNOTAVAIL
#define WSAEINVAL EINVAL
#define closesocket close
#define WSAGetLastError() errno
#define WSASetLastError(value) (errno = (value))
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wine_loopback.h"

static const char *corruption;
static unsigned bind_calls, name_calls, close_calls;
static SOCKET test_socket = INVALID_SOCKET;

static int native_name(SOCKET sock, struct sockaddr *address, int *length)
{
#ifdef _WIN32
    return getsockname(sock, address, length);
#else
    socklen_t size = (socklen_t)*length;
    int result = getsockname(sock, address, &size);
    *length = (int)size;
    return result;
#endif
}

static int observed_bind(SOCKET sock, const struct sockaddr *address, int length)
{
    ++bind_calls;
    return bind(sock, address, length);
}

static int observed_name(SOCKET sock, struct sockaddr *address, int *length)
{
    struct sockaddr_in *ipv4 = (struct sockaddr_in *)address;
    int result;
    ++name_calls;
    if (!strcmp(corruption, "fail-name")) {
        WSASetLastError(WSAEINVAL);
        return SOCKET_ERROR;
    }
    result = native_name(sock, address, length);
    if (!strcmp(corruption, "wrong-ip")) ipv4->sin_addr.s_addr = htonl(0x0a000001UL);
    if (!strcmp(corruption, "wrong-loopback")) ipv4->sin_addr.s_addr = htonl(0x7f000002UL);
    if (!strcmp(corruption, "wrong-port")) ipv4->sin_port = htons((unsigned short)(ntohs(ipv4->sin_port) + 1));
    if (!strcmp(corruption, "zero-port")) ipv4->sin_port = 0;
    if (!strcmp(corruption, "wrong-family")) ipv4->sin_family = AF_UNSPEC;
    if (!strcmp(corruption, "short-name")) --*length;
    return result;
}

static int observed_close(SOCKET sock)
{
    ++close_calls;
    return closesocket(sock);
}

static int observed_option(SOCKET sock, int level, int option, char *value, int *length)
{
    int result;
    if (!strcmp(corruption, "fail-type")) {
        WSASetLastError(WSAEINVAL);
        return SOCKET_ERROR;
    }
#ifdef _WIN32
    result = getsockopt(sock, level, option, value, length);
#else
    {
        socklen_t size = (socklen_t)*length;
        result = getsockopt(sock, level, option, value, &size);
        *length = (int)size;
    }
#endif
    if (!strcmp(corruption, "wrong-type")) *(int *)value = SOCK_RAW;
    if (!strcmp(corruption, "short-type")) --*length;
    return result;
}

static void observed_exit(unsigned int code)
{
    struct sockaddr_in address;
    int length = (int)sizeof(address);
    int closed = native_name(test_socket, (struct sockaddr *)&address, &length) == SOCKET_ERROR;
    printf("{\"fatal\":%u,\"closed_before_exit\":%s,\"bind_calls\":%u,\"name_calls\":%u,\"close_calls\":%u}\n",
           code, closed ? "true" : "false", bind_calls, name_calls, close_calls);
    fflush(stdout);
#ifdef _WIN32
    ExitProcess(code);
#else
    _Exit((int)code);
#endif
}

#define bind observed_bind
#define getsockname observed_name
#define getsockopt observed_option
#undef closesocket
#define closesocket observed_close
#define ExitProcess observed_exit
#include "loopback_source_fragment.inc"
#undef bind
#undef getsockname
#undef getsockopt
#undef closesocket
#undef ExitProcess
#ifndef _WIN32
#define closesocket close
#endif

int main(int argc, char **argv)
{
    struct sockaddr_in address, actual;
    SOCKET reservation = INVALID_SOCKET;
    int kind, status, bound, length = (int)sizeof(actual), repeated = 0;
    int bind_error, reference_error = 0;
    DWORD error;
    unsigned requested;
#ifdef _WIN32
    WSADATA data;
    if (WSAStartup(MAKEWORD(2, 2), &data)) return 3;
#endif
    if (argc != 5) return 3;
    kind = !strcmp(argv[1], "tcp") ? SOCK_STREAM : SOCK_DGRAM;
    corruption = argv[4];
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(!strcmp(argv[2], "loopback") ? 0x7f000001UL :
        !strcmp(argv[2], "secondary") ? 0x7f000002UL :
        !strcmp(argv[2], "nonloopback") ? 0x0a000001UL : INADDR_ANY);
    if (!strcmp(argv[2], "family")) address.sin_family = AF_UNSPEC;
    test_socket = socket(AF_INET, kind, 0);
    if (test_socket == INVALID_SOCKET) return 3;
    if (!strcmp(argv[3], "late")) {
        if (!sockBind(test_socket, &address)) return 3;
    }
    if (!strcmp(argv[3], "late-failed")) {
        if (sockBind(INVALID_SOCKET, &address)) return 3;
    }
    status = cohDbLoopbackInit();
    error = GetLastError();
    if (!strcmp(argv[3], "repeat") && status == 1) {
        repeated = 1;
        status = cohDbLoopbackInit();
        error = GetLastError();
    }
    if (status < 0) {
        printf("{\"status\":%d,\"error\":%lu,\"invalid_parameter\":%lu,\"invalid_state\":%lu,\"bind_calls\":%u,\"name_calls\":%u,\"repeated\":%d}\n",
               status, error, (DWORD)ERROR_INVALID_PARAMETER, (DWORD)ERROR_INVALID_STATE,
               bind_calls, name_calls, repeated);
        closesocket(test_socket);
        return 0;
    }
    if (!strcmp(argv[2], "occupied") || !strcmp(argv[2], "requested")) {
        reservation = socket(AF_INET, kind, 0);
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (reservation == INVALID_SOCKET || bind(reservation, (struct sockaddr *)&address, sizeof(address))) return 3;
        if (native_name(reservation, (struct sockaddr *)&address, &length)) return 3;
        if (!strcmp(argv[2], "requested")) { closesocket(reservation); reservation = INVALID_SOCKET; }
    }
    requested = ntohs(address.sin_port);
    if (status == 0) {
        SOCKET reference = socket(AF_INET, kind, 0);
        if (reference == INVALID_SOCKET) return 3;
        WSASetLastError(12345);
        bind(reference, (struct sockaddr *)&address, sizeof(address));
        reference_error = WSAGetLastError();
        closesocket(reference);
    }
    WSASetLastError(12345);
    bound = sockBind(test_socket, !strcmp(argv[2], "null") ? NULL : &address);
    bind_error = WSAGetLastError();
    memset(&actual, 0, sizeof(actual));
    length = (int)sizeof(actual);
    if (bound && native_name(test_socket, (struct sockaddr *)&actual, &length)) return 3;
    printf("{\"status\":%d,\"bound\":%d,\"address\":%lu,\"port\":%u,\"requested_port\":%u,\"bind_calls\":%u,\"name_calls\":%u,\"bind_error\":%d,\"reference_error\":%d}\n",
           status, bound, (unsigned long)ntohl(actual.sin_addr.s_addr), (unsigned)ntohs(actual.sin_port),
           requested, bind_calls, name_calls, bind_error, reference_error);
    closesocket(test_socket);
    if (reservation != INVALID_SOCKET) closesocket(reservation);
    return 0;
}
