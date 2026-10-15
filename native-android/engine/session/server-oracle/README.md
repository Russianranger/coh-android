# Original NetLink function oracle over real UDP

This additive host qualification runs the native UDP client against **40 pinned
original source function bodies**, in a separate process reached through actual
loopback UDP sockets. It replaces no accepted transport kernel and links into no
APK, launcher or production server.

**Passed boundary:** original control negotiation, original header/ACK parsing,
original outbound producer framing, native reliable retirement/retry, encrypted
NetLink key establishment, one test application payload, and disconnect/cleanup.
**Pending:** full AuthServer/DbServer/MapServer interoperability, authentication,
character selection, compression/fragmentation against a real server, Android
execution and physical Thor networking. This oracle does not pass gate 25 or 26.

## Source boundary

`source-pins.json` pins complete source files and all 40 extracted bodies. No
function body is edited. The generated C translation unit adds only build
annotations (`no_sanitize_address`, `no_sanitize_undefined`) on those declarations
in the sanitizer configuration. The original functions retain their own bit
reader/writer, `pktWrap`, `pktUnwrap`, `pktSendAcks`, version policy,
`pktCreateControlCmd`, `netAckConnect`, `netAckDisconnect` and
`handleControlCommand` logic. The tests do not manufacture a SERVER_ACK or ACK
list from the native frame encoder.

The new host shims are explicit:

- Packet allocation uses zero-filled, aligned fixed-capacity host storage.
- The socket wrapper replaces Windows completion ports with one local UDP
  socket. It binds **127.0.0.1 and an ephemeral port**; no endpoint is supplied
  by a configuration file or discovered on a network.
- `pktSend` uses original `pktWrap` and checksum conventions; emission occurs
  after the handler completes. This ordering matters: the original server
  queues final ACK before setting `encrypt_on`, then encrypts at send/flush.
- The original receive ID-set algorithm uses a bounded 16,384-slot host table.
  Packet history, logs, unrelated buffer updates and unused allocation paths
  are inert or trap if reached. `pktProcessAck` records observations only; it
  **does not qualify the original server's reliable send queue**. Native
  reliable queue retirement is checked by the client separately.
- Source CryptoPP DH/MD5 functions use the separately host-qualified OpenSSL
  provider with the original 64-byte DH group/encoding; Blowfish uses the
  accepted native kernel. This is not a freshly built CryptoPP server, nor an
  Android crypto result. The source crypto files and wrapper semantics are
  pinned for audit. Every encrypted case generates real fresh keypairs.
- Test commands 10/11 carry a fixed public integer through source packet
  functions. They are a test-only application dispatch witness, not an
  authenticated game command, character, entity or world snapshot.

Original x86-oriented pointer/bit operations receive only trusted output from
the native writer. They compile at O0 with explicit sanitizer exclusions.
The **new shims, socket wrapper and native client** execute with ASan/UBSan.
Malformed traffic goes solely to the new native parser: each scenario receives
one short frame, one empty datagram and one checksum-invalid frame. The old
function oracle is never offered arbitrary malformed inputs or public traffic.
LeakSanitizer is disabled in this restricted environment; no LSan pass is claimed.

## Reproduce

```sh
python3 native-android/engine/session/server-oracle/check.py \
  --source-root . --sanitize --output /tmp/coh-original-netlink.json
```

Dependencies: GCC-compatible `cc`, Python 3, zlib development files and the
existing host OpenSSL 3 development package. The retained receipt records
OpenSSL 3.0.13; it does not claim Android deployment of that host library.
The checker verifies source pins before compilation, builds separate source
and native processes, and runs 16 scenarios: versions 0, 2, 4 and 5, each clear
and encrypted, each with and without loss of the initial native CONNECT.
Version 1 source default compressed payloads and never-public version 3 are
intentionally outside this oracle. Existing kernel tests cover them separately.

Every scenario requires source-produced negotiation, both encryption transition
flags as configured, original ACK callback observations, the test payload,
source disconnect handling, bounded native cleanup, and one matched open/close
per process. Loss cases require a native retransmit; loss-free cases require
none. Receipts store lengths, states and counters only: no keys, credentials,
public/private DH material, packet bodies or encrypted transcript is recorded.
Timing-dependent polling check counts are diagnostics, not golden evidence.
The protocol obligations, configured cases and source identities are deterministic.

## Full server feasibility and next evidence

The retained [reference workflow](../../../../.github/workflows/reference-runtime.yml)
builds actual DbServer, MapServer and TestClient with MSVC Win32.
`upstream/ouroboros/CMakeLists.txt` explicitly rejects non-MSVC MapServer builds.
The historical package receipt
`docs/reference-runtime-evidence/artifact-36088012664.json` identifies run
36088012664, artifact 10843979104, source `775a0dd...`, and inner archive SHA256
`dd551750de26765297a45310bba51817b36a942d23f97d4da7f0d1365f49d3aa`.
These are **historical repository receipts**, not freshly downloaded binaries.
No artifact validity/expiration or execution in this host is inferred.

Existing docs also preserve actual original DbServer execution through the
accepted ARM64 PRoot/Wine/FEX package, native PostgreSQL and x86 ODBC. The
accepted fixed-input donor is run 36451873322; a separate loopback-qualified
profile is run 36460867428. These older receipts do not establish that the native
client speaks to that server. Reuse a currently available exact qualified donor
with all receipt checks rather than rebuilding unchanged binaries.

This host has GCC/OpenSSL but no Wine, x86 Windows runtime, PostgreSQL tools or
MSVC. Building a full original Linux server is a separate port, not a useful
shortcut around those prerequisites. No original full server was launched in
this work. No production account, database, save, runtime or listener was touched.

The immediate authentic-server route is a fresh disposable matching environment
using existing qualified binaries on Windows, or the accepted compatibility
runtime on a suitable host/device. Keep the **client native** and record server
source/binary/config/SQL identities. A development `UseFakeAuth` path can qualify
DB/Map protocol behavior but cannot qualify real AuthServer login. See
[CAPTURE-CONTRACT.md](CAPTURE-CONTRACT.md) before recording that next exchange.
