# Source audit

Snapshot: integration baseline `365bc1f`; exact LF-normalized SHA256 values
are in `source-pins.json`. Source is read from `upstream/ouroboros/`.

* `Game/src/clientcomm/dbclient.c:dbConnect`: exact request order is command,
  auth name, packed UID and protocol, aligned 128-byte auth array, packed
  no-version-check, patch version string, aligned 16-byte executable checksum,
  fixed32 cookie, bit no-timeout, patch message, empty telemetry prefix,
  zipped system-spec record, packed keyed-access level and conditional issued-to
  string. `pktSendZipped` uses zlib level five and includes the input string's
  terminating NUL. The original header defines `DISABLE_RENDER_TELEMETRY` and
  the unchanged source oracle consequently uses `Disabled` as its fixture.
* `dbChoosePlayer`: packed slot, packed local-map IPv4 value, name string,
  auto-width create-location. No DBID is emitted. The serializer accepts
  explicit caller policy; the guarded helper only chooses an unlocked,
  nonempty, nonvisitor record with required class/origin/name.
* `handleSendPlayers` then `receivePlayersCommon`: UID auto-width, command
  string, three flags, base slots, max/bonus slots, VIP and nag, then each
  original slot's level/name/class/origin/flags/type/subtype/location-type/
  Praetorian status/power names/body type/two F32 scales/skin color/map name/
  map time/offline time/last-online/2-bit lock; finally auth userdata and
  overridden auth arrays. The parser verifies full exhaustion of logical bits.
  The console string is deliberately never executed, as an independent native
  client must not execute arbitrary server-provided client console commands.
* `handleSendQueueInfo`: position and count are both `pktGetBitsAuto`.
* `Common/auth/auth.h`: `AUTH_BYTES=128`.
* `Common/comm_backend.h`: DB protocol version `20110614`; normalized DB
  client LOGIN=2/CHOOSE_PLAYER=3 and server SEND_PLAYERS=2/QUEUE_POSITION=20.
* `Common/entity/gametypes.h`: defined lock values are NONE=0, VIP_FREE=1,
  OFFLINE=2. An unknown lock value is unsupported and never selected.
* `net_structdefs.h`: old NetLink command maximum=7 and current maximum=2.
  Old-profile command mapping adds five, never guesses based on payload.
* `net_packetutil.c:pktSendBitsAuto/pktGetBitsAuto`: selector is two bits and
  widths are 2/10/24/32. Both selector and value honor aligned scalar widths.
* `BitStream.c`: `bsWriteBitsPack` stores fixed32 values in byteAlignedMode;
  `bsWriteBits` rounds scalar width to a byte; `bsWriteBitsArray` and
  `bsReadBitsArray` always align before copying; strings do not add alignment.

Oracle handling: only original source functions/statements selected by exact
names/markers are compiled. The login/choose producer blocks are unchanged;
surrounding global getters are deterministic, authorized fixture values. The
original bit writer runs with trusted, zeroed, DWORD-aligned storage at O0 and
`-fwrapv`, outside sanitizers. Native code and accepted scalar dependencies run
separately under ASan/UBSan; the immutable accepted scalar dependencies compile
at O0 to avoid a preexisting GCC13 inlining warning in unused frame decoding.

The source-layout list fixtures are synthetic and explicitly not packet
captures. There is no vendor DBServer implementation in this source snapshot.
These tests qualify wire serialization/parsing against the available client
oracle, not compatibility with a running server or acceptance of native client
version/checksum policy. Those remain integration gates.

The additive DB session controller schedules those same request records through
the accepted NetLink UDP owner. It uses reliable delivery and unordered
requests, matching `pktCreateImp`'s reliable default and the link's unordered
default. It does not replace connect/key/ACK/retry/fragment/compression kernels.
`coh_db_map_handoff_parse` strips only the whole message's command, copies its
remaining exact bit span through `CohProtocolBits`, and calls the previously
qualified auth-module handoff parser. No alternate handoff schema is invented.
The raw source AuthServer receipt is supplied by the independently authenticated
parent; explicit matching and monotonic-generation checks prevent accidentally
using a different account or replaying stale foreground state. They are not
cryptographic authentication proof.

Actual OS socket tests use original-source-layout fixture packets and a
controlled synthetic UDP peer. They demonstrate bounded session behavior,
reliability and cleanup, not an authenticated session with a real DBServer.

## MAP_CONNECT identity correction

See ../entity-bootstrap/CONTRACT.md and its pinned whole original producer/queue
oracle. DBServer mapxfer.sendLoginInfoToGameClient writes EntCon.id in the first
MAP_CONNECT field; queue relays it unchanged. Game dbOrMapConnect misleadingly
names the ignored local field link_id. The opaque DB session now exports that
positive signed32 ID as selected_dbid only in its validated WAIT_MAP selection
flow; generic raw handoff parsing is unchanged. This supersedes earlier unknown-
DBID claims for this exact command/producer context and confers no actor/ACK.
