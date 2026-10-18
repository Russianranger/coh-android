# Initial MapServer source audit

All files below are SHA256-pinned after LF normalization in `source-pins.json`
against the `365bc1f` integration source. There is no live packet capture or
real-server evidence in this module.

The 0.1.6 capacity regression uses `scene1` from the independently pinned
replication source oracle. Its aligned command and scene prefix are produced
by unchanged `BitStream.c` functions, with field ordering audited against
`groupnetsend.c` / `groupnetrecv.c`. A deterministic synthetic tail expands
the body to 128 KiB without claiming valid complete group data. Test-only
zlib output follows `net_packet.c`'s original convention: 32-bit aligned
command, 32-bit decoded tail length, then compressed tail; ordered data uses
`Z_SYNC_FLUSH`, unordered data uses a complete zlib stream. The existing
source compression oracle remains the separate transport qualification.

Only the Map owned-receive path opts into the 4 MiB decoded budget. This
neither changes the source wire layout nor makes a prefix sufficient to send
REQALLENTS/READY or bind a server character to the renderer.

| Source | Recovered contract |
| --- | --- |
| `Common/comm_game.h` | Normalized client IDs: input2, scene3, shortcuts4, allentities5, ready6, connect9; normalized server update2, allentities3, shortcuts4, connect5, groups6 |
| `net_structdefs.h`, `netio_send.c:pktSendCmd` | `COMM_MAX_CMD=2`, `COMM_OLDMAX_CMD=7`; old profiles add5; disabled cookieSend/cookieEcho adds no framing fields |
| `net_version.c` | Source default/current version5; versions0–3 use legacy command IDs, versions4–5 use separate control commands; compressed payloads use byte alignment |
| `clientcomm.c:commStart` | Encrypted UDP NetLink must connect before CLIENT_CONNECT; cookie packed1, cod bit1, then character-create/resume payload; packet defaults reliable |
| `svr_tick.c:CLIENT_CONNECT` | Enforces configured network version, resolves entity from login cookie, checks cod, then reads newCharacter bit; existing initialized character uses newCharacter0 and no character-creation tail; sends accepted packed1 plus timezone float or rejected packed0 plus error string |
| `clientcomm.c:commConnect`, `commReqShortcuts` | Map connect must succeed before requesting shortcuts; shortcuts command contains no extra fields |
| `clientcomm.c:commReqScene`, `svr_tick.c:CLIENT_REQSCENE` | Scene request carries the zero stealth bit; successful groups reception precedes REQALLENTS; complete allentities handling precedes READY |
| `clientcomm.c:commReqScene`, `svr_tick.c:CLIENT_READY` | READY includes map cookie packed1, console-open packed1, passwordMD5 raw128 bits, initial-login auto bits; it is not emitted by the controller |
| `clientcomm.c:SERVER_ALLENTS`, `clientcomm.h` referenced in source | ACK_FULL_UPDATE is an input subcommand, not the same as transport ACK; merely observing full_update_id must not emit it |
| `Common/entity/entVarUpdate.h` | RECEIVED_CHARACTER and ACK_FULL_UPDATE are application input IDs, separate from transport acknowledgements |
| `dbclient.c:dbOrMapConnect` | Handoff contains link ID, map ID, two IPv4 DWORDs, UDP/TCP ports and map cookie. Those values do not contain the selected character DBID |
| `BitStream.c`, `net_packet.c`, `net_packetutil.c` | Source scalar rounding, packed integers, byte alignment before raw arrays and auto-bin encoding |

The earlier statement that `sendCharacterCreate` was absent is superseded by
the read-only source audit at published
`f3ee9db6bc8a323c896769f0952dd242fc79e2f4` confirms it is present in
`Game/src/gameComm/initClient.c:329`, calling the complete
`Game/src/entity/entrecv.c::sendCharacterToServer` creation sender. Exact file
and whole-function pins, including the original Map receivers, are retained in
[`fresh-character-source-scope-20261018/audit.json`](../auth-interop/evidence/fresh-character-source-scope-20261018/audit.json).
This corrects the source-availability finding; the existing native CONNECT
serializer still supports only `newCharacter=0`. A fresh server-allocated,
uninitialized character requires a separately qualified creation sender and
owner; this existing serializer cannot create it. No old oracle or runtime
claim is upgraded by this source correction.

Normal source `commStart` writes the command directly through `pktCreate`,
matching the source default/current modern version5. The standalone legacy
serializer uses unchanged `pktSendCmd`'s documented +5 conversion. This
explicit adaptation does not claim that an unmodified source legacy
`commStart` interoperates with every historic server. The actual server
checks exact configured NetLink protocol version; the adapter never silently
downgrades.

Original IPv4 DWORDs are Windows little-endian integers containing the four
network-address bytes. Endpoint matching explicitly extracts those bytes,
independently of the native host's integer byte order. The selected DB slot
and its selection generation are caller-owned admission context. A source
own-entity DBID/ownership check remains required before reporting identity
verified or rendering an authoritative spawn.

## Oracle boundary

`check.py` compiles unchanged, hash-pinned original `bsWriteBits`,
`bsWriteBitsPack`, `bsWriteBitsArray`, packet writer wrappers,
`pktSendBitsAuto` and `pktSendCmd` at O0 on trusted padded/aligned buffers.
The wrapper reconstructs the source field call order; it does not compile the
whole original client or claim a complete original server consumer oracle.
The 240 byte/bit-count comparisons cover all supported outgoing commands,
both command remappings, both alignment modes, Boolean variants and large
cookie values. Legacy x86 code is not subjected to sanitizers; all new native
code and the accepted portable transport/parser dependencies are.

The host release baseline uses O1 with all warnings treated as errors, while
the accepted `protocol/coh_protocol.c` dependency is compiled separately at
O0. GCC O2 warns about a potentially uninitialized local in its accepted
`coh_protocol_decode`; that file is outside this worker's ownership and is
unchanged. The Android Clang controller/object and full ARM64/x86_64 test
compilations also treat warnings as errors. No warning suppression is
applied to the new controller. Cross-building is recorded separately from
execution; preserving a full executable never proves it ran on Android.

Actual authenticated source-server interoperability, encrypted real-session
traffic, complete group reference parsing, entity tails, selected-character
ownership, authoritative spawn, ACK_FULL_UPDATE, RECEIVED_CHARACTER and READY
remain pending. Deterministic fixtures and real localhost datagrams cannot
upgrade those statuses.
