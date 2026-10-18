The new private Windows UDP adapter compiles the ordinary `coh_net_udp.c`
translation unit unchanged. It is a prerequisite for the separate provisional
Auth-to-DB-list experiment. It neither admits a DB login nor changes a profile.
The accepted Auth TCP adapter remains unchanged.

Only IPv4 UDP, a nonblocking and noninheritable socket, an explicit
127.0.0.1 ephemeral bind, and the fixed 127.0.0.1:7000 destination are admitted.
One initialization owns at most four full-width SOCKET values. Successful
closes do not recycle their integer tokens during that initialization. Raw
datagrams stay within the ordinary protocol's 1472-byte cap; the separate
decoded/copied DB message limit remains 16KiB.

The adapter supplies the ordinary core's single-iovec `recvmsg` subset with
Winsock `recvfrom`. The documented UDP `WSAEMSGSIZE` result means the datagram
was truncated and its excess discarded. The adapter returns a truncation flag
so the ordinary core discards the partial datagram. It preserves the returned
source-address length for the ordinary peer-validation gate. EAGAIN, EINTR,
empty datagrams and fatal receive errors retain separate behavior.
Reference: https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-recvfrom

The ordinary POSIX core intentionally forgets its integer fd after `close`,
including an error. Windows `closesocket` may leave its handle open on error,
so the adapter independently retains it. Final teardown retries retained
handles, refuses `WSACleanup` while any remain, and retains an unsuccessful
WSA cleanup reference for a later cleanup attempt. Fixed counters distinguish
owned handles from the ordinary core's opened/closed counters. Calling finish
disables all new sockets and I/O for that initialization. A successful finish
requires no retained handles and a successful `WSACleanup`.

`test_db_udp_winsock.py` is a deterministic syscall shell, with optimized and
ASan/UBSan configurations, plus a private wrapper compilation of the ordinary
UDP TU. It exercises full-width handles, stale tokens, endpoint and flag
refusals, truncation, short sends, receive errors, failed closes retained after
the core could forget its fd, and failed WSA cleanup. It claims no real Windows
API execution, network exchange, Auth grant, DB character list or Map state.
