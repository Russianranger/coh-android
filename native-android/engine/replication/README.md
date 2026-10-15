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
cmake -S native-android/engine/replication -B /tmp/coh-replication-build
cmake --build /tmp/coh-replication-build
```

The source checker verifies 18 SHA256-pinned original files. It compiles the
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
at most 256 shortcuts and accessible commands, 32 loadscreen pages, 256-byte
NUL-terminated strings, and 16,384 message bytes. Exceeding a bound rejects the
input; production admission must treat that as unsupported rather than omit
data and continue.

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
