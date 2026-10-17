# Original AuthServer → DbServer handoff: bounded read-only contract

This module advances the next source prerequisite after actual encrypted
AuthServer-only success. It does not start a service, mint a cookie, alter
accounts, register a shard or claim an authenticated DB/Map login. All shipping,
accepted Auth-only and provisional Combined profiles remain untouched.

## Exact source chain

All audited original functions are pinned to tree
`f634e21e230009fa8edc91d15429cd4da69eee8c`; hashes are retained in
`../evidence/authenticated-handoff-contract-20261017/source-audit.json`.

| Original producer/consumer | Required semantics |
| --- | --- |
| `AuthServer/ServerList::Load` and `SetServerSocketByAddress` | An actual DB-server socket must match an explicitly loaded shard record; unknown-server acceptance is unnecessary. |
| `DBServer/authcomm::handleVersion` and `authSendSetConnect` | Original server version exchange and activation precede shard use. Explicit server-ID registration is a separately configured source path. |
| `AuthServer/SocketServerEx::SelectServerPacket` | Valid authenticated UID/session key, existing account, live selected server and payment rules precede AboutToPlay. |
| `AuthServer/AccountDB::AboutToPlay` | Normal full-userdata producer format is `cdsdddbddd`: opcode, UID, zero-terminated name, remaining/login/warning values, 128 auth bytes, pay status and two loyalty values. |
| `DBServer/authcomm::handleAboutToPlay` | DB allocates its own cookie/cache entry and consumes that full producer grammar, then requests game data. |
| `AuthServer/CSocketServer::ServerReadGameData` | Reads original user game data and returns opcode7, UID and 128 game-data bytes. |
| `DBServer/authcomm::handleRecvGameData` | Matches UID, applies original AuthServer/DBServer auth-bit masks, merges the data, then emits `AS_PLAY_OK` with UID and DB-generated cookie. |
| `AuthServer/CSocketServer::ServerPlayOk` | Finds the authenticated client socket for UID/shard and relays `AC_PLAY_OK(cookie, UID, shard ID)`. |
| `Game/authclient::acGetPlayOK` | Reads cookie into `game_key`, UID and shard ID in that order. |
| `DBServer/clientcomm::handleLogin` | Checks DB-client protocol, version/checksum policy and then the real auth cache; fake auth is a separate bypass and must be disabled. |
| `DBServer/authcomm::authValidLogin` | Matches UID, exact cookie and case-insensitive space-trimmed account name, copies auth data/loyalty/pay fields and clears the whole cache entry after one successful use. |

The cookie comes from DbServer's `authEntryAlloc` (`rule30Rand`/CPU ticks plus the
4096-slot index), not the native adapter, historical receipt or offline actor.
This work does not execute that generator. Original `authValidLogin` has no
standalone age/TTL check; the 30-second comparison is allocation/reuse logic.
Do not claim a source-enforced cookie expiry in the consuming function. Exact
cookie zero can match an occupied entry in the original source; the bounded
adapter preserves that U32 equality rather than inventing a nonzero-cookie rule.

## Concrete profile boundary discovered

The physically bounded Auth-only experiment intentionally used `UserData=false`
and no shard. That branch sends short format `cdsdddd`. Original DB
`handleAboutToPlay` unconditionally reads the full 128-byte auth-data block and
loyalty tail, so that profile cannot simply be relabeled as a full DB handoff.

A separately reviewed disposable nonqueue DB profile must set `UserData=true`,
`useQueue=false`, `sendQueueLevel=false`, preserve encryption/version/checksum
requirements, register an actual owned shard and seed matching public fixture
`user_data` as well as `user_auth`/`user_account`. Original schema uses four
16/112-byte auth/game-data columns; the accepted Auth-only seed did not establish
that full user-data row. No row was added to an existing account here.

`require_original_db_profile` records this source-defined full grammar prerequisite
and refuses the short or queue-tail variants. It explicitly leaves deployment
admission false. No accepted profile was modified.

## Implemented adapter and qualified boundary

`authenticated_handoff_contract.py` parses only already-decrypted/deframed bodies:
full SQ_ABOUT_TO_PLAY, SQ_RECV_GAME_DATA, AS_PLAY_OK and client AC_PLAY_OK. It
bounds account names by the original 14-byte producer limit, auth/game data by
128 bytes and each complete body by its exact size. Truncation, extra bytes,
wrong opcode, zero UID/shard, cross-generation UID/cookie/shard mismatch and
unbounded names fail transactionally. Cookie and account/data fields are hidden
from dataclass repr; errors never include packet/account values.

Matching immutable metadata records does not prove source-channel ownership,
live order, original auth-bit ownership merging or the final cache lookup.
Those flags remain false, as do deployment and authenticated DB login admission;
selected DBID remains None. The live transport owner must supply those proofs.

Qualification executed exact original `Assemble` and `authPutU08/U32` writers
against the bounded parsers in release and ASan/UBSan (five byte-comparison cases
per mode, including refusal of the existing short UserData=false body). Exact
original `trimTrailingWhitespace` and `authValidLogin` ran 544,839 controls per
mode across all4096 slots, copied all128 data bytes, one-shot consumption,
wrong identities, all32 cookie-bit mutations and original zero-cookie semantics.
Five Python suites cover malformed inputs, profile boundaries, immutable records
and mismatches. Fixtures contain only declared synthetic public values; they do
not supply an authentic selected character. No network, SQL, crypto or Windows
service execution was repeated. LeakSanitizer is explicitly disabled.

## Remaining nonprovisional deployment and DB/Map blockers

The fresh encrypted AuthServer prerequisite remains mandatory. Before any new
service run, close the explicit shard fixture and internal Auth/DB connection,
full user/game-data row and ownership-mask merge, live AboutToPlay→game-data→
PlayOK ordering, and one-shot original cache consumption on the actual DB path.

The DB profile must also establish the actual non-`dev:`
`getCompatibleGameVersion` result with `fake_auth=false`, an admitted exact
16-byte client-reference checksum and the separately declared fail-closed
16-byte checksum correction. Original nondevelopment handling overrides the
client's requested version bypass; no client flag closes that dependency.
The existing donor checksum inspection still records deployment admission false
and supplies no normal version.ini/profile by itself. See CHECKSUM-REFERENCE.md.

Only after real authenticated DB login may a driver qualify actual character
list/selected DBID and DB→Map transfer with full source transaction validation.
The historical Auth-only cookie/session is already destroyed and cannot satisfy
any of these live identity or character requirements.

```sh
python3 native-android/engine/auth-interop/deployment/qualify_auth_cache_consumer.py \
  --source-root . --output /tmp/auth-cache-consumer.json
python3 native-android/engine/auth-interop/deployment/qualify_handoff_wire.py \
  --source-root . --output /tmp/auth-handoff-wire.json
python3 -m unittest discover -s native-android/engine/auth-interop/deployment \
  -p test_authenticated_handoff_contract.py -v
```
