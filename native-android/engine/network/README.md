# Gate 25: bounded native NetLink continuation

This opt-in C99 library extends the accepted bitstream/Blowfish kernels with
source-compatible NetLink framing, reliable queues and a client session state
machine. It has no Wine, Box64 or FEX dependency. It is outside all APK, JNI,
launcher, Session Client and production-server execution paths.

**Status: implemented and host qualified within the boundary below. Gate 25 is
not passed: no actual server exchange, Android execution or physical Thor
network qualification has occurred.** A clear-handshake scenario between host
test adapters is a state-machine test, not evidence of server interoperability.

## Public API and ownership

`coh_net.h` is the only public header. Compile `coh_net.c`, `coh_net_frame.c`,
`coh_net_zip.c`, the existing `native-android/protocol/coh_protocol.c` and
`native-android/src/coh_blowfish.c`; link zlib. Include
`native-android/include` and `native-android/protocol`. No other existing
module changes are required. Local `CMakeLists.txt` provides an optional static
library target; the coordinator owns any higher-level build integration.

- `coh_net_frame_encode/decode` implement original untyped v0–v5 wire headers,
  byte alignment, CryptoPP Adler digest order and optional accepted Blowfish
  transform. Callers supply the already-negotiated key. Decoder and encoder
  outputs remain unchanged on failure. Typed/debug packets are unsupported.
- `coh_net_create/default_config/destroy` own one bounded link and its zlib
  dictionaries. One thread owns all calls. Input spans are borrowed for a call;
  successful `queue` and `receive` copy retained bytes. Teardown follows stopped
  producers. `destroy(NULL)` is harmless; never reuse a freed pointer.
- `begin` queues original `CONNECT`, connect ID and requested version.
  `receive` handles clear `SERVER_ACK`, `CLIENT_ACK` reply, final server ACK,
  idle and disconnect. It never fabricates an authentication success.
- `queue` accepts an opaque game payload including its original command and
  logical bit count. For compressed messages the caller must already use the
  source byte-aligned payload form: packed fields become 32-bit values and
  other bit fields round to whole bytes. This API does not serialize game
  command structures or translate legacy command offsets.
- `pump` invokes a caller-supplied complete-datagram send callback. Callback
  failure preserves the pending packet and piggyback ACKs. It must not reenter
  the link. The caller's socket adapter must validate peer endpoints, prohibit
  truncation, provide a monotonic clock, and close its own descriptors. The
  accepted Gate14 loopback adapter is reused as a transport contract reference;
  this module does not widen its endpoint restriction or alter it.
- `next` returns caller-owned messages after sibling reassembly and ordered
  delivery. Compressed ordered messages are inflated in delivery order, with
  independent standalone compression contexts for unordered traffic. Mixed
  ordered/unordered compression must not reset the ordered dictionary.
- Cancellation is cooperative in `pump`, including between datagrams.
  `cancel/close` clear retained queues. A remotely requested disconnect clears
  gameplay queues and preserves one close reply; it never retransmits old game
  traffic after closure. Do not poll or close sockets on another thread here.

## Implemented protocol behavior

| Original behavior | Checked native boundary |
|---|---|
| `pktWrap/pktUnwrap`: ID, sibling count/part/group | Same bit encodings; up to 16 sibling parts and four live groups |
| `pktSendAcks`: full first ID, packed positive deltas | Up to 31 unique IDs; sorted ACKs, bounded parsing, overflow rejection |
| v1–v5 compression bit; v5 ordered bit and auto integer | Same negotiated flags and `{2,10,24,32}` ordered-ID bins |
| Initial CONNECT omits all negotiated header flags | Explicit `connect` flag retained for retries |
| Sender fragment splitting, then `mergeSibs` | Sender splits at a conservative 1,200 bytes; receiver permits 1,440-byte parts, including the source default 1,228 and maximum configured 1,436-byte payloads |
| `lnkAddOrderedPacket`: deliver contiguous ordered IDs | Bounded wait queue; duplicate ordered IDs rejected |
| Original 16,384-slot received-ID set | Same bounded per-slot deduplication and very-late rejection; sender refuses packet-ID wraparound |
| `calcTimeout`: ping factor and capped exponential retries | Exact function parity for retry delays, 250–5,000 ms; fixed configured ping, explicit retry/idle/connect budgets |
| `bsCompress`: command remains clear; length then zlib tail | Independent original-producer and Python-zlib parity; tiny tails stay unchanged |
| Ordered/reliable UDP uses persistent `Z_SYNC_FLUSH` | Separate persistent dictionaries; decompression follows ordered assembly |
| Source unbounded sibling/decoded allocations | Strict queue/message/zlib budgets with diagnostic counters |

The low-level frame API permits any fitting ACK count. Session sending reduces
piggyback ACKs to preserve the source's 28-byte nondebug header allowance where
possible. Packet IDs are never reassigned on retransmission. ACKs only retire
already-sent queued frames. Backpressure never marks a refused receive as
accepted: a reliable sender can retry after the application drains capacity.

Resource limits intentionally improve unsafe source failure behavior. Expiring
an incomplete group, or exceeding the message cap after ACKed fragments were
retained, closes/fails the link and clears queues. Silently dropping previously
ACKed pieces while remaining connected would permanently lose that message.
Malformed compressed ordered data fails the link; a corrupted dictionary must
not be reused. Unsupported encrypted handshake never falls back to clear text.

## Memory and diagnostics

Limits are compile-time visible: 32 pending send frames, 16 received messages,
four sibling groups, 16 parts/group, 16,384 bytes/message and a 16,384-slot
dedup table. One host link uses **482,296 fixed bytes** plus **275,504 initial
codec bytes** on the tested 64-bit host. zlib allocations have a separate hard
768 KiB ceiling, use overflow-checked allocator accounting, and are freed on
teardown. Temporary standalone codec contexts do not disturb streaming state.
The fixed structure size is ABI-dependent; use diagnostics on Android.

There are no per-frame heap allocations in framing/reliable queues. zlib can
allocate a bounded window when first needed and standalone codec calls may
allocate/free bounded work storage. This is not a realtime audio callback.
Receive and dispatch copy at most the fixed message cap; an Android transport
thread adapter and tighter measured allocation policy remain later work.

Diagnostics expose sent/received/retry/ACK counts, duplicate and malformed
counts, queue/fragment/timeouts, current retained objects, fixed storage, codec
allocation and retained-byte high water. No credential, key or packet-body
logging occurs. Test CPU timing is a host test diagnostic, not a Thor latency,
throughput or game-performance benchmark.

## Reproduction

```sh
python3 native-android/engine/network/check.py \
  --source-root /path/to/full/coh-android \
  --sanitize \
  --output /tmp/gate25-host.json
```

`source-pins.json` verifies complete LF-normalized original files before any
oracle compiles. The unchanged legacy writer is used only on trusted aligned
zero-filled host storage at `-O0`, without sanitizers; it is never linked into
the new library. New native code compiles with `-Wall -Wextra -Werror` and runs
with ASan/UBSan. LeakSanitizer is disabled on the restricted host. Current
receipt: `evidence/host.json`; it explicitly sets real-server interoperability,
Android build and Android execution false.

Reference coverage includes 80 original producer profiles, independent Python
bit-list/zlib headers, 40 unchanged original `bsCompress` comparisons, 70
unchanged `calcTimeout` cases, 640 unaligned native wire comparisons, exact
allocation truncations, 12,000 checksum-valid parser mutations, 500 mixed
stream/standalone codec cycles, handshakes at each supported source version,
fragment reordering, packet loss/retry/ACK retirement, ordered compression,
queue caps, cancellation, timeout, oversized ACKed groups and disconnect
regressions. Encryption uses the accepted Blowfish kernel; no new DH claim is
made by frame round trips.

## Required next interoperability and Gate 26 work

1. **Controlled server prerequisite:** provide an isolated build/configuration
   matching the user's server, its NetLink network version and encrypted-link
   policy, and a disposable account/character. No production server was changed
   or contacted. Wire captures must redact credentials and retain packet IDs,
   capability transitions and exact binary/source identities.
2. **Encrypted NetLink handshake:** port `crypt.cpp`'s exact DER DH group and
   fixed 64-byte public/private/shared-secret conventions; validate peers;
   derive MD5 over the 64-byte shared secret, then reproduce
   `cryptBlowfishInitU32` key byte order. Verify the CLIENT_ACK public key is
   sent clear, enable decrypt after shared-key derivation, and enable encrypt
   at final SERVER_ACK_ACK. Currently an authenticated, fully present
   encryption request returns `COH_UNSUPPORTED` and
   `COH_NET_ENCRYPTION_REQUIRED`; incomplete key payload returns invalid.
3. **Authentication is a different protocol:** `authLogin/authclient.c` uses
   TCP AuthServer framing, initial protocol/key setup, credential packet,
   server list and play/queue replies. These are not NetLink CONNECT. Support
   the configured development/no-AuthServer path only when that exact server
   mode is independently verified; never infer it from a clear handshake.
4. **DBServer login:** source `dbConnect` sends `DBGAMECLIENT_LOGIN`, account
   name, user ID, `DBSERVER_CLIENT_PROTOCOL_VERSION=20110614`, auth-user-data,
   version/checksum policy, patch version, executable checksum, cookie,
   no-timeout flag, patch/telemetry fields and keyed access metadata. Port the
   exact per-field serializers plus queue/error/start replies; determine an
   approved native executable checksum/version policy with the controlled
   server. Do not disable checks on the user's production server.
5. **Character/MapServer handoff:** `dbChoosePlayer` requests a selected slot
   and parses map endpoint/cookie/error. Open a separately owned UDP NetLink;
   `commStart` then sends `CLIENT_CONNECT`, map cookie, COD bit and
   `sendCharacterCreate` state, and waits for `SERVER_CONNECT_MSG` followed by
   shortcuts/groups/entity initialization. None is implemented here.
6. **Gate25 completion witnesses:** demonstrate original controlled-server
   clear/encrypted exchange (as configured), authentic loss/reorder/fragment
   behavior, disconnect/reconnect, and source-defined compressed packet
   traces. Implement RTT sampling, source cookie echo, version fallback policy,
   buffer resize handling, typed packets if required and nonblocking socket
   integration only as measured server behavior requires. Version3 is an
   original explicitly nonpublic profile; frame compatibility is not a claim
   of usable v3 login.

The library does not yet implement AuthServer, DH/MD5 negotiation, DB/game
commands, cookie echo, source buffer-resize control, live RTT estimation,
server version fallback, credentials, map-transfer state or entity replication.
Those are explicit remaining requirements, not simulated successes.

## Integration and rollback

Coordinator may build this isolated static library and run host/ARM64 checks
without waiting for gates19–21. No scene, renderer, Session Client, common
workflow or existing gate files are touched. Before wiring it to a game session,
implement the controlled transport and Gate26 boundaries above and record
separate Android/emulator/Thor results. Keep accepted conventional/native APKs
and receipts unchanged.

One local commit contains only `native-android/engine/network/`. Integration is
a coordinator-reviewed cherry-pick onto freshly fetched `native-android`,
followed by cross-module regression and a fast-forward-safe push. Roll back by
removing the opt-in build edge and additive-reverting this module commit after
dependency review. No migration, server data or external asset changes occur.
