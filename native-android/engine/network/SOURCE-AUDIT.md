# Original protocol provenance

The full original files in `source-pins.json` are read-only from repository
revision `9ee2f8c74e3efdd2593d514bf8d32a75dcbc8de9`. The manifest verifies each
whole file before the host oracle runs. Existing accepted bitstream/Blowfish
files are reused unchanged; their earlier goldens and receipts remain owned by
their original gates.

| Original source under `upstream/ouroboros/` | Audited behavior |
|---|---|
| `libs/UtilitiesLib/src/components/BitStream.c` | LSB-first bits, sentinel/subtraction packed integers, byte-aligned field mode, array alignment, first-command-preserving zlib packet/stream compression |
| `libs/UtilitiesLib/src/network/net_packet.c` | Untyped dispatch, compression/ordered compatibility flags |
| `libs/UtilitiesLib/src/network/net_packetutil.c` | Ordered IDs encode bin index2 then 2/10/24/32 bits |
| `libs/UtilitiesLib/src/network/netio_core.c` | Packet wrap, sorted delta ACKs, sibling metadata, dedup slot semantics, ordered delivery, merge metadata |
| `libs/UtilitiesLib/src/network/netio_send.c` | Fragment after compression, fixed part boundaries, same logical packet ID on retry, bounded source timeout equation, checksum/encryption offsets |
| `libs/UtilitiesLib/src/network/netio_receive.c` | Merge and order before persistent stream inflate; untyped compressed payload layout |
| `libs/UtilitiesLib/src/network/net_version.c` | Versions0–5 compression, ordering and control subchannel capabilities; default5 |
| `libs/UtilitiesLib/src/network/net_link.c` | Initial CONNECT always v0 header; negotiated ACKs, three-step finish, disconnect and encrypted DH/MD5 transition |
| `libs/UtilitiesLib/src/network/crypt.cpp` | Exact DH group, public/shared secret width and MD5-derived Blowfish key conventions delegated to optional Gate26 provider |
| `Game/src/clientcomm/authclient.c` | Distinct TCP AuthServer state sequence and development-mode alternative |
| `Game/src/clientcomm/dbclient.c` | DB login fields, character selection, map endpoint/cookie handoff |
| `Game/src/clientcomm/clientcomm.c` | UDP MapServer connect, CLIENT_CONNECT body, SERVER_CONNECT_MSG and initial data dependencies |

The test extracts and compiles complete unchanged original function bodies via
the accepted source extraction helper. Type/platform/logging shims provide
minimal trusted test storage and trap unsupported typed branches. Native code
does not link these legacy oracle bodies. The original writer has known
x86-oriented stores and signed shifts; sanitizer results apply exclusively to
the new code and accepted byte-safe dependencies. The complete original source
files remain in their existing repository location with their original notices.

Source/reference parity validates specific producer behavior; it does not prove
that a running server accepts a packet, that credentials authenticate, or that
any gameplay command is complete. Random deterministic payload tails in wire
fixtures are opaque framing data, not captured authenticated game sessions.

New safety limits differ intentionally from the source's unsafe paths: no
unbounded sibling arrays, unchecked packed arithmetic, >1GB allocation permits,
stale padding copies or logging credentials. Native zero-filled producer
padding matches the original producer supplied defined zero-filled storage.

## Additive UDP and encrypted lifecycle continuation

The accepted framing, bitstream, Blowfish and zlib bodies remain unchanged.
The new POSIX `coh_net_udp.c` is an owner adapter around those accepted APIs;
its exact peer and truncation checks follow the existing accepted Gate14
transport contract without changing Gate14's endpoint restriction. The adapter
opens only explicitly requested numeric IPv4 endpoints. Host qualification
uses local OS sockets and a controlled source-shaped peer, not a live game
server. Android compilation is recorded separately from execution.

`net_link.c:netAckConnect` and `handleControlCommand` are the provenance for the
optional callback sequence: encrypted flag and byte-aligned public512 in the
clear CLIENT_ACK, derive shared secret and enable receive decryption, then
enable send encryption at SERVER_ACK_ACK. No native DH claim is made by the
fixed provider in this module's tests. The callback contract requires the
separate Gate26 provider to generate fresh private entropy, validate the exact
source public value and derive MD5(shared64) into accepted Blowfish bytes.
Setting required-encryption explicitly forbids a clear fallback. Private/shared
values remain provider-owned; key-schedule cleanup uses volatile writes.

`net_link.c:handleControlCommand` control5/6 and `netAckDisconnect` define the
graceful disconnect/ACK path. Dropping queued gameplay before requesting close
and bounding shutdown by the configured connection deadline are intentional
native ownership limits. Suspend/resume destroys and recreates transport and
codec state on its owner thread; an authenticated reconnect still requires
Gate26/coordinator work and real-server evidence.
