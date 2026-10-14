# Gate 14 UDP source boundary

Original game source as vendored at the accepted native branch revision:
`0a5eed1a388ed53da1e19e7d6b2b571c067b82b9`.
`source-pins.json` records the LF-normalized SHA256 of both complete source
files and both complete unchanged function bodies. `check.py` verifies these
pins before executing the native host proof. The original Windows functions
are source anchors for the socket boundary; they are not compiled or shipped
in the Android adapter, and no unchanged-server handshake is claimed.

| Source | Original behavior | Bounded Android adapter |
|---|---|---|
| `net_socket.c:181`, `SendToSock` | Calls `sendto` with the packet bytes, length and IPv4 destination; returns the sent byte count | Nonblocking IPv4 `sendto`, checks the complete byte count, only ephemeral `127.0.0.1` peers |
| `netio_receive.c:301`, `pktGetUdp` | `recvfrom` supplies raw bytes and sender endpoint; packet bit length must fit the datagram with at most seven extra padding bytes; transfers packet ownership on success | `recvmsg(MSG_TRUNC)` supplies raw bytes and sender endpoint; rejects zero, kernel truncation and oversize before decoding; verifies the actual sender address and port; delegates exact frame checks to accepted gate 12; publishes caller output only on success |

Immutable primary source anchors:

- [SendToSock](https://github.com/Russianranger/coh-android/blob/0a5eed1a388ed53da1e19e7d6b2b571c067b82b9/upstream/ouroboros/libs/UtilitiesLib/src/network/net_socket.c#L181)
- [pktGetUdp](https://github.com/Russianranger/coh-android/blob/0a5eed1a388ed53da1e19e7d6b2b571c067b82b9/upstream/ouroboros/libs/UtilitiesLib/src/network/netio_receive.c#L301)

The legacy receive routine copies a packet header before proving the received
byte count contains one and retains a static packet allocation. Reproducing
those unsafe paths is outside this gate. The adapter uses a fixed local frame
buffer and one worker per operation. It never shares the receive buffer or
closes another thread's descriptor. The exact padded-length policy already
qualified in gate 12 remains stricter than the legacy receive envelope.

Wire production uses unchanged `coh_protocol_encode`; validation uses unchanged
`coh_protocol_decode`, their compiled independent fixtures, and unchanged
`coh_blowfish.c`. This gate neither generates new cryptographic vectors nor
relaxes the accepted wire profile. The host receipt hashes all these inputs.

The new POSIX adapter uses monotonic deadlines and at most 25 ms poll slices.
The UI changes a mutex-protected cancellation epoch. Restoring foreground
permits a new run but cannot revive a worker from the old epoch. Each worker
owns its two descriptors from creation through close. The explicit wait API
is capped at five seconds and reports success only for an interruption of a
wait that actually reached poll. A clean timeout is observable but does not
qualify the Home/return check.

Actual UDP fixtures exercise all 32 accepted clear/encrypted wire cases in
both directions, then inject zero, physically short, oversized and corrupted
datagrams for both cipher modes and directions. Two valid source packets are
also rejected against the wrong peer port. A final clean timeout and two
transfers after close/reopen exercise the descriptor lifecycle. All rejection
and timeout outputs must retain a sentinel pattern.

Host-only checks run twelve explicit-wait and six ordinary-selftest thread
cancellations, including eight immediate background/foreground restorations
and two concurrent workers. A separate
host-only harness closes a real descriptor to inject `POLLNVAL` and verifies
an explicit backend error, untouched output and cleanup. Three temporary
negative-control builds remove source-port validation, ignore cancellation
epochs, or overwrite failure output. Each must be caught by a semantic driver
assertion; sanitizer crashes do not count as successful negative controls.
A further fixture injects an independent parity error after a real datagram
arrives, then cancels at cleanup. The failure must stay sticky; a fourth
negative-control build that waives the error after late cancellation is
rejected. No modified negative-control binary is shipped.
