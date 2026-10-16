# Gate 27: bounded source replication inspection

This opt-in C99 module adds native parsing contracts for the initial MapServer
exchange. It has no socket, JNI, global game state, heap allocation or credential
storage. It does not change any APK or the accepted Session Client 0.3.0.

**Implemented and host qualified within the explicit boundaries below. Gate 27
is pending. No authenticated server, complete entity replication, authoritative
render spawn, Android execution or physical Thor acceptance is claimed.**

| Source behavior | Implemented boundary |
|---|---|
| `SERVER_CONNECT_MSG` accepted flag and timezone / rejection string | Complete body parser; rejection text discarded |
| `SERVER_CMDSHORTCUTS` ID/name list and accessible commands | Complete body parser; bounded IDs/strings/count; only ten original server-visible variable schemas admitted |
| `SERVER_GROUPS` editor counts and map metadata | Prefix through original map path and beacon availability; reports exact group-file tail offset |
| `SERVER_GROUPS` complete normal-file wire body | Separate opt-in structural inspection of files, defs, conditional material/property fields, affine matrix encodings, sparse roots and footer; no graph publication |
| `SERVER_ALLENTS` full-update ID, odd bit, command values, clocks, debug/interpolation settings | Prefix through exact entity-tail offset; never emits an ACK for an unparsed full update |
| `SERVER_UPDATE` same header without full-update ID | Same bounded prefix, dynamic source shortcut schema required |
| `entGetPosition` full and partial quantized position | Exact 24-bit, scale-64 kernel with per-bit packet ordering; starts at the position substructure only |
| `playerReceiveServerPhysicsPositions` control correction | Exact changed/ID/position/optional-velocity prefix; debug recording tail rejected |
| Old/new NetLink application command numbering | Explicit old `+5` wire remap vs normalized IDs from `Common/comm_game.h` |
| Bitstream compression representation | Both packed LSB-first bits and decompressed source `byteAlignedMode`; input must already be inflated by transport |

The `CohRepScenePrefix` and `CohRepUpdatePrefix` structures are inspection
results. Successfully reading them proves only those prefixes were decoded.
The unparsed tail may still be malformed or unsupported. The session inspector
therefore stops at `COH_REP_ENTITY_PREFIX_SEEN`, has no live-world state, never
creates an actor, and never emits `CLIENT_READY`, `CLIENTINP_RECEIVED_CHARACTER`
or `CLIENTINP_ACK_FULL_UPDATE`. The selected DB ID identifies the caller's
intended character; it has not yet been matched against a parsed self entity.

`CohRepPosition` and `CohRepPhysics` are useful independent decoder kernels,
not offsets that can be guessed into a complete packet. Their call site must
first traverse and validate the preceding original entity/control structures.
The host tests deliberately call them at known synthetic fixture boundaries.

## Build and verification

```sh
python native-android/engine/replication/check.py --source-root . --sanitize \
  --output native-android/engine/replication/qualification.json
python native-android/engine/replication/groups_check.py --source-root . --sanitize \
  --output /tmp/coh-groups-qualification.json
cmake -S native-android/engine/replication -B /tmp/coh-replication-build
cmake --build /tmp/coh-replication-build
```

The source checker verifies 19 SHA256-pinned original files. It compiles the
unchanged original `initBitStream`, bit writer/reader and packed writer as the
fixture producer. It separately compiles the original `entGetPosition` client
consumer to produce expected full/partial/out-of-order position state. The old
x86 code runs at `-O0` on padded aligned trusted inputs; only new code and its
harness are sanitizer qualified. Fixtures are synthetic source-layout packets,
never network captures. Source statement order for larger prefixes is audited
against both original sender and receiver; a complete original MapServer is
not built by this test.

Release, ASan and UBSan each exercise deterministic positive cases, every-bit
truncation of supported bodies, unknown variable schemas, repeated shortcut
IDs, oversized strings, nonfinite floats, rejected physics recordings,
unauthorized/out-of-sequence inspection, disconnect/reconnect/schema generation
and 30,000 bounded randomized cases. All decoder outputs and cursors remain
unchanged on failure; session diagnostic counters may increment. LeakSanitizer
is disabled because this sandbox denies its `/proc` task traversal. The module
does not allocate memory; ASan memory-access checking remains enabled.

## Integration contract

One owner thread calls all APIs. Inputs are borrowed for one synchronous call;
successful prefix/session results copy their retained state. Transport must
validate endpoint and reliable/ordered delivery, decompress the original
payload, preserve the logical bit count, and supply the negotiated command
numbering profile. Typed/debug bitstreams and optional NetLink cookie fields
must be resolved before this module's command boundary; those fields are not
silently skipped. `compressed=1` means source byte-aligned scalar encoding,
even after the zlib data has been inflated.

Call `session_begin` only after the auth/DB handoff selects an existing character;
pass `link_authenticated=1` only for the genuine Gate 26 authorization result.
That flag is a caller contract guard and does not establish authentication.
The complete `SERVER_CONNECT_MSG` then moves the inspector from wait to map
connected. A complete shortcuts message establishes a schema for this generation.
Reconnect invalidates it. Scene and entity prefixes may be inspected after
their ordering prerequisites. `session_disconnect` clears selected/map/update
state. The external schema may retain bytes, but cannot authorize a new
generation until a new complete shortcuts packet is consumed.

All command/field bounds are deliberate native resource limits, rather than
claims that every original server configuration fits. In particular there are
at most 256 shortcuts, 1,024 separately streamed accessible command names,
32 loadscreen pages, 256-byte
NUL-terminated strings, and 16,384 message bytes. Exceeding a bound rejects the
input; production admission must treat that as unsupported rather than omit
data and continue.

### Explicit larger scene inspection

`coh_rep_reader_bounded(reader, bytes, bits, compressed, max_bytes)` adds a
caller-selected finite budget from 1 byte through 4 MiB. It borrows the already
inflated body for synchronous parsing; it does not allocate, copy, retain a
queue or change `COH_REP_MESSAGE_MAX`. The existing reader still rejects bodies
above 16 KiB. A zero `CohRepReader.max_bytes` retains that original limit, so a
manually zero-initialized reader cannot silently gain the larger budget. All
parsers check the effective reader budget before multiplying bytes by eight.
Invalid budgets/arguments return `COH_INVALID`; an input above an explicit
valid budget returns `COH_LIMIT`, leaving the reader untouched.

The existing `coh_rep_scene_prefix` consumes a bounded reader without a second
grammar. `coh_rep_session_message_bounded` accepts the same explicit budget,
but only a `SERVER_GROUPS` body may exceed 16 KiB. Larger shortcuts, connect,
update or unknown command bodies return `COH_LIMIT` without changing copied
schema, phase or scene state. Session diagnostic counters may increment.
The original command profile remapping and authorization/order guards remain
required. Neither bounded entry point declares the unparsed tail valid.

Source-written scene prefixes are tested with 16,385, 65,536, 1,048,576 and
4,194,304-byte borrowed buffers in both bit profiles, plus the legacy command
remap. Their zero-filled tails are synthetic, unparsed and never asserted to
be authentic complete scenes. Tests cover prefix truncation at every bit,
logical-end reads, 4 MiB + 1 rejection, `SIZE_MAX` claims, invalid budgets,
reader corruption and 4,000 additional randomized large-buffer prefix cases.
Release, ASan and UBSan exercise the same cases. The existing prefix APIs remain
prefix-only. Complete normal-file structural traversal is a separate entry point
below; no readiness, full-update acknowledgement or authoritative actor follows
from accepting either result.

### Complete normal GROUPS structural inspection

`coh_rep_groups(reader, inspection, failure)` in `coh_groups.h` starts immediately
after the GROUPS command. It reuses the accepted bounded prefix parser, then
traverses the complete supported normal-world grammar through the four-field
footer and exact logical end. Both scalar representations are supported. In
source `byteAlignedMode` all scalar widths round to whole bytes, so the complete
grammar ends at a byte boundary; packed-mode callers must preserve transport's
logical payload bit count. Extra zero bits are not silently accepted as padding.

The inspector validates flags and packed ranges, finite floats, optional
definition blocks, both raw and packed 4-by-3 affine matrix representations,
texture swaps and all conditional tricks fields, property names/values/types,
removal records and sparse root IDs. Forward definition names and definitions
omitted from saved libraries are permitted. File slot order is the producer's
implicit `1..N-1,0`. Definition IDs increase within each file; root update IDs
increase within their list. Duplicate or decreasing IDs are rejected without
an identity table or allocation. Unsupported base/raid bodies and unknown
texture-mask bits fail closed. Matrices are traversed for structural validity
and finite values; their transforms are not reconstructed by this inspection.

Admission policies are explicit: 1,024 file slots, 65,536 transmitted definitions
with per-file IDs at most 65,535, 262,144 total children, 65,536 root updates
with sparse IDs at most 1,048,575, 65,536 properties and 65,536 swaps. Names use
the existing 256-byte bound, property names the source 64-byte bound, and
property values a 4,096-byte bound, all including NUL. Tail strings have a
3 MiB cumulative byte ceiling, and a separate 1,048,576 scalar-work ceiling
can reject smaller bodies with too many small operations. These are finite
native admission policies, not claims that every original map fits them.

Only numeric counts, observed footer checksums and bit boundaries are retained.
The footer file count must match the transmitted file-slot count; active roots
are bounded but are not incorrectly compared to the number of changed root
records. Both checksum values are metadata. Matching definitions may reside in
imported libraries, so neither checksums nor a resolved graph can be validated
from the transmitted records alone. The parser allocates nothing, retains no
body pointers or strings, and uses no large local arrays. On failure its reader
and inspection output remain unchanged. The optional failure receipt gives a
numeric stage, status and last completed read boundary; a prefix failure reports
the prefix start because the reused prefix parser is transactional. Tail scalar
validation failures report the boundary after that scalar was read.

The separate checker compiles 41 exact functions from 16 pinned original source
files, including the original `worldSendUpdate`, `sendGroupFile`, `sendDef`,
property writer, BitStream and matrix helpers. Its engine/services fixture shim
is explicit and bounded. The exact original compression/alignment helpers run;
packed fixtures use incremental sends, while full updates set compression and
select byte-aligned mode. Initial-world incremental fixtures use a zero
last-update time; the existing changed-only fixture retains its older checkpoint.
The original group
count/CRC traversal executes with
an independent zlib Adler32 adapter matching the source Crypto++ digest byte
order; Crypto++ itself is not executed. The native parser only reports those
values and makes no checksum-match claim. Forty-four deterministic fixtures
cover modern/legacy commands and both scalar profiles, including all optional
definition blocks, forward names, omitted saved definitions, deletions, raw and
packed matrices (including original PYR and singular-scale branches), force
reload of saved definitions, incremental absent slots, alternate light/ambient
tricks and four unsupported-base header cases.
The complete large source fixture is 139,794 decoded bytes, with 192 definitions,
384 children, 384 properties and 384 swaps. This is synthetic source execution,
not a captured server body or authenticated scene.

Release, ASan and UBSan run every-bit truncation for the small complete fixtures,
sampled boundaries plus every bit of the final 128 bits for large fixtures,
malformed counts/IDs/flags, nonfinite transforms, duplicate/decreasing IDs,
unknown masks, resource ceilings, exact-end checks and 40,000 deterministic
random/mutated cases. Wrapped allocation/free functions check that every parser
call performs zero allocations and deallocations. The team-area prefix field is
structural numeric metadata; values 5 through 7 do not change this grammar and
are tested without granting team semantics. Existing reader/session/prefix
tests remain independent.
Successful structural inspection does not advance the session prefix state,
send `REQALLENTS`, acknowledge full updates, emit `READY`, resolve assets or
publish an authoritative actor. Those remain later integration milestones.

## Exact source sequence and remaining work

The original existing-character sequence is:

1. AuthServer authentication; DbServer character listing/selection and map
   endpoint/cookie handoff (Gate 26 owns these).
2. UDP NetLink establishment, then `CLIENT_CONNECT` containing the cookie,
   `cod` bit, and `newCharacter=0`; server validates protocol/cookie/character
   and replies `SERVER_CONNECT_MSG`.
3. `CLIENT_REQSHORTCUTS` / `SERVER_CMDSHORTCUTS`, then reliable
   `CLIENT_REQSCENE` with the source zero stealth bit / `SERVER_GROUPS`.
4. Reliable `CLIENT_REQALLENTS` / `SERVER_ALLENTS`. The original client ACKs
   the full-update ID via `CLIENT_INPUT` and decodes all entities.
5. `CLIENT_READY` contains cookie, console state, password MD5 and initial-login
   flag. The server enters its normal loop and pushes another full self update.
   `CLIENTINP_RECEIVED_CHARACTER` finishes the character receive notification.

The source makes this substantially larger than a position-only message.
`SERVER_GROUPS` continues with dynamic group definitions, root transforms and
map metadata. `SERVER_ALLENTS` continues through delta-indexed entity creates,
class/origin/name/title/phase/pet fields, optional state, position/orientation,
animation/costume/FX, entity list termination, global debug, control physics,
deletes, full character definition, powers, inventory, team and further state.
Embedded game commands follow. There is no generic byte length around these
structures that permits skipping unknown fields safely.

Next work must implement bounded traversal of these authentic tails, negotiate
and validate all required asset/data schemas, identify the self entity by DB ID,
and only then atomically publish a validated selected actor pose to the native
renderer and emit the original readiness/receive acknowledgements. A real
authorized disposable server must provide authenticated end-to-end evidence.
Until then the controller/camera and accepted local scene remain untouched.

## Source references

The exact file hashes are in `source-pins.json` at recovery checkpoint
`2c32f5686246fa28cf3341e8e89dd1014eacd5f4`.

- `Common/comm_game.h`, `net_structdefs.h`: normalized and legacy command IDs.
- `MapServer/src/svr/svr_tick.c`: connect, scene/all-entity requests and ready.
- `Game/src/clientcomm/clientcomm.c`: matching message dispatch and request order.
- `Game/src/clientcomm/clientcommreceive.c`, `cmdoldparse.c`,
  `Common/cmdparse/cmdcommon.c`: shortcut transport and ten authentic variable schemas.
- `MapServer/src/group/groupnetsend.c`, `Game/src/group/groupnetrecv.c`: scene metadata.
- `MapServer/src/entity/entsend.c`, `Game/src/entity/entrecv.c`: update header and positions.
- `Game/src/player/player.c`: server-authoritative control physics correction.

Remove this optional library or revert its additive commit to roll back. There
is no APK, launcher, asset, account, character or report migration.

The accessible command list after the shortcut terminator is independent of
its schema. The pinned `cmdserver.c:cmdOldServerSendCommands` filters a static
table with 915 named entries; the conservative unfiltered name inventory is
14,264 bytes including terminators. The parser now permits up to 1,024 names,
reading and discarding one bounded string at a time. It retains only the
numeric count. It still permits at most 256 shortcut definitions and 16KiB
per message. Names do not register or authorize native command execution.
Original bit-writer fixtures exercise the entire pinned 915-name inventory in
both payload profiles, the 1,024 boundary, 1,025 rejection, and truncated tails.
The earlier shared 256 cap was incompatible with valid privileged command
lists. Existing Thor reports do not identify the failing packet; this fix
alone does not prove its exact cause or a complete real MapServer connection.
