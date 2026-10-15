# Native DB client wire records (Gate 26 component)

This additive module implements the original DB login and existing-character
selection requests, a complete bounded `DBGAMESERVER_SEND_PLAYERS` record,
queue-position records, and a nonblocking UDP DB session owner. It does not
authenticate accounts, execute remote console commands, invent a DBID, or
assert an authentic live session without server evidence.

`coh_db_login_encode` takes caller-owned account, auth userdata, executable
checksum, cookie, authorized patch/protocol versions and policy flags. These
values must come from the authenticated session and the authorized disposable
server configuration. There is no implicit version/checksum bypass. The result
is sensitive protocol data: send it through the negotiated transport, never
log it, then call `coh_db_wipe`. The caller owns input and output lifetimes.

The `byte_aligned` flag describes the already decompressed NetLink packet:
scalar widths round to bytes and packed values occupy 32 bits in that profile.
The `legacy_commands` flag adds the source's old-command offset of five.
Every function consumes/emits the command as part of the logical packet.

`coh_db_players_parse` parses all source fields, including body scale/color,
map metadata, slot lock and both final 128-byte auth arrays. It bounds the list
at 64 slots and the logical message at 64 KiB. It preserves wire slot indices
even for visitor records; it flags visitors and disallows choosing them. The
source UI removes visitors and compacts its own array, which is inappropriate
as a wire identity. Original DBServer source is not included in the vendor
snapshot, so this behavior still requires real-server qualification.

Remote console strings are consumed and discarded without execution. No such
string is exposed in the result. `coh_db_player_choose` rejects empty, invalid,
visitor or locked records and returns a bounded choice. Source character lists
do **not** carry DBIDs: `wire_slot` and name identify selection; a later
authoritative server message must provide any DBID.

The scalar adapter uses the existing `CohProtocolBits` implementation through
datagram-sized windows. It can parse assembled lists larger than a datagram
without raising or changing the transport kernel's bound. All array fields
align to a byte even in the packed profile; string fields remain bit aligned.
Unknown command/profile tails fail closed; all caller outputs remain unchanged
on error. Parsed player data is only committed after the entire packet passes.

Run from the repository root:

```sh
python native-android/engine/dbclient/check.py --source-root . --sanitize \
  --ndk /path/to/android-ndk-r28c \
  --output native-android/engine/dbclient/evidence/host-android.json
```

`coh_db_session.h` wraps the accepted `CohNetUdp` socket/reliability owner.
The caller supplies the authorized peer, version/checksum policy and a receipt
from a successful independent AuthServer flow. The receipt must agree with
login UID/cookie/account; its `verified` flag is explicitly caller attestation,
not manufactured proof. After actual NetLink establishment, the controller
queues LOGIN once, receives a complete matching-UID list or bounded queue
updates, validates the selected slot, queues CHOOSE_PLAYER and parses the
complete MAP_CONNECT through the accepted `coh_auth_map_handoff_profile`.

The outgoing requests retain the source's reliable/unordered defaults and
use the explicitly selected compression profile. The transport encryption
policy/provider are forwarded unchanged; encryption-required failure never
falls back to a clear login. Diagnostics expose phase/counters and transport
errno only, never packet contents, account names, cookies or auth bytes.

Suspend/cancel/timeout/failure clear the login/list/handoff state. A fresh
monotonic AuthServer receipt generation and fresh connect ID are required to
restart; foreground recovery does not replay the previous login. Selection
generation increases monotonically within the owner. Handoff is one-use,
always has `selected_dbid=0`, and starts graceful DB disconnect; keep pumping
until CLOSED. The parent must explicitly authorize the server-reported map
endpoint before opening a MapServer socket.

The independent parser's 64-KiB logical-message bound does **not** raise the
accepted NetLink transport's 16-KiB reassembly limit. Oversized live lists
remain outside admission; bounded parser tests are not proof that the socket
owner accepts arbitrary maximum-size source lists.

The check pins ten upstream files; compiles the exact unchanged DB login and
choose request producer statement blocks and original bit writer; compares
all four packed/aligned and normalized/legacy output profiles; exercises
complete source-layout character lists (five and 64 slots), all truncations,
unsafe character selection, nonfinite scale, unsupported lock values,
over-limit slot counts and 10,000 deterministic malformed messages. New code
runs in release, ASan and UBSan builds. The controller also runs actual OS UDP
tests against a synthetic source-layout peer: version 0 legacy, version 5
packed/compressed, queue/list/selection/handoff, reliable login retry,
disconnect cleanup, receipt mismatch/staleness, cancellation, suspend,
timeouts, malformed/unsolicited messages and encryption downgrade rejection.
This peer is not a DBServer and does not prove authentic authentication.

The optional NDK check links a complete ARM64 Android shared library with no
undefined symbols. Add `--android-output DIR` to retain ARM64 and x86_64 wire
and socket-controller executables plus `android-build.json` hashes. All
artifacts start with `executed=false`; another runner must actually execute
and validate them before recording Android execution qualification.

Qualification boundaries: implemented, source/host qualified and ARM64 built;
no Android execution qualification, physical Thor acceptance, server capture,
authenticated DB session or actual server interoperability is claimed.

Not implemented here: account inventory/catalog/costume-detail commands,
renaming/deletion/creation, queue-server routing, server-authentication policy,
or MapServer entity replication. Unknown messages
must be dispatched separately or rejected. The final auth bit arrays are
fully parsed; there is no unsupported tail within `SEND_PLAYERS` itself.

## Explicit loopback development entry

`coh_db_local_login_encode` and `coh_db_session_begin_local` reproduce the
original `-db`/UseFakeAuth path without fabricating an AuthServer receipt.
Both initial UID and cookie must be zero; both bind and peer must be loopback.
The first complete SEND_PLAYERS must return a nonzero server UID, and later
lists must retain that UID. Fresh explicit generation is required after every
terminal transition. The ordinary authenticated entry still requires a
nonzero matching verified receipt and rejects UID-zero attempts.

The integrated caller lives in `../local/`; its scoped development version
policy matches the current conventional loopback launcher. It sends no
local-map-IP override, preserving the selected character's saved destination.
