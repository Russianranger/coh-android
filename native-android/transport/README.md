# Gate 14: bounded native UDP transport

This diagnostic executes real IPv4 UDP sockets on `127.0.0.1`, with two
ephemeral ports. It brings the already accepted gate 12 packet profile across
the Android socket boundary. It does not establish a game-server session or
qualify authentication, character login, ACKs, retransmission, reliable
ordering, entities or gameplay.

`coh_transport_selftest` opens two nonblocking sockets, sends every accepted
clear/encrypted golden in both directions, validates actual sender endpoints,
compares received wire bytes, and decodes their payloads. It sends real zero,
short, oversized and corrupt datagrams and verifies transactional rejection.
Oversized UDP uses `recvmsg(MSG_TRUNC)` to prevent silently accepting a valid
prefix. It also checks wrong source ports, one bounded empty receive, then
closes/reopens and completes two additional transfers.

A normal passing proof records 84 datagrams sent and received, 66 matching
wire/payload frames (33 clear, 33 encrypted), 18 expected rejects, four actual
truncated datagrams, four zero datagrams, one expected timeout and four sockets
opened and closed. `backend_errors` must remain zero. The normal loopback
selftest takes about 42 ms on this Linux host; this is not a Thor performance
claim.

An ordinary Home press can cancel a partially completed selftest. The report
distinguishes `cancelled`, `expected_cancel` and `session_failure`: only an
explicit cancelled socket operation is a retryable lifecycle abort. Every
observed frame, payload, byte-parity, backend and cleanup error remains a
sticky failure even if cancellation arrives afterward. Ordinary selftests
always report `interrupted_blocked_poll=0`, so they cannot become the explicit
Home witness. A prestart background abort can open zero sockets and remains
retryable; it cannot qualify any gate.

`coh_transport_wait(5000, &proof)` opens an empty native receive and waits at
most five seconds. Once `coh_transport_active()` becomes true, the user can
press Android Home. `coh_transport_foreground(0)` changes the cancellation
epoch and the worker notices within a 25 ms poll slice; the worker itself
closes both sockets. Returning to the app calls `coh_transport_foreground(1)`
for new runs. Only a blocked wait interrupted by cancellation passes. A clean
timeout remains retryable and cannot qualify the Home check.

Host proof, separate from device acceptance:

```sh
python3 native-android/tools/transport_fixture/check.py --output native-android/transport/evidence/host-proof.json
```

The test uses ASan/UBSan, actual UDP malformed injections, timeouts, twelve
explicit-wait and six ordinary-selftest thread cancellations, eight immediate
foreground restorations, concurrent workers, real backend-error injection,
descriptor accounting, a parity error followed by a later UI cancellation,
and four semantic negative controls. The ordinary-selftest cancellation
harness observes a genuinely empty kernel poll using host-only linker wrappers
for `poll` and its fortified libc entry; the Android module has no test hook.
LeakSanitizer is disabled on the restricted host; opened
and closed counts and `/proc/self/fd` must agree. Original socket function
anchors and hashes are in `tools/transport_fixture/SOURCE-AUDIT.md` and
`source-pins.json`. The accepted protocol and Blowfish kernels are unchanged.
