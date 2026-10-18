# Actual Windows development experiment 39090126094

The single hosted experiment **failed** before a complete DB player list was
admitted. Its retained evidence does establish narrower Windows API, build,
registry and cleanup observations. No command ID/name or packet body was
retained, so the unsupported count does not identify the received commands.

`artifact.zip` is the sole existing public artifact 12122124306, copied without
another download. It has one member, `receipt.json`; all ZIP CRCs pass. The
receipt is preserved byte-for-byte, including 1,565 CRLF line endings. `api.json`
is the already retained run/job/artifact metadata. Identity pins:

| Input | Bytes | SHA256 |
| --- | ---: | --- |
| Artifact ZIP | 16,275 | `4b96a2fe31f1612ab90b47a6371584010f3d862be8a456e6537bbd6f6c732ee3` |
| Raw receipt | 70,557 | `d3d8382330622f4dfc19ae105b5cb87674ce79411f284f6935a159eac33f8889` |
| API metadata | 4,183 | `5b04359ef60a2aa8265a9efc76e26a7a8d774701ce4c385f46a3e9129f4a5ced` |

The receipt and API bind run 39090126094 to commit
`ed77036d1b7f7e47588d74408506d738293643a9`, repository tree
`04d74f572784c3762856267c3ab1b1c32ff888c0` and original source tree
`f634e21e230009fa8edc91d15429cd4da69eee8c`. All 98 recorded deployment source
hashes match exact Git blobs at that commit: 1,441,703 input bytes. This binds
the historical run; it does not establish a current live process generation.
`review.json`'s `passed` means these data checks passed, not that the experiment
passed. No application source/helper was executed by this review.

## Component observations supported by the receipt

- The new x64 probe configured and built. Its measured PE was 3,292,160 bytes,
  SHA256 `b49fd26b2ca9633e0bb4cf985c13dd306bc24c767e5c788bfb4b889267259f85`.
  Exact Chromium zlib tree `62224db151a2af4f2c66110d634ef8dc3607a155` and the
  existing derived CMake input were admitted; the resulting static archive was
  227,166 bytes, SHA256
  `b2ed8f3de6876f8b1d687370c65fc88bb25ab969ba33748bd6606240f62409c0`.
  Neither server nor retained crypto was rebuilt by this experiment.
- Four detailed actual suspended-resume projections pass their exact schema,
  eleven true Boolean checks, previous suspend count one, two snapshots and zero
  close failures. Configure/build examined 3,014/2,992 thread entries; Auth/DB
  launches examined 2,798/2,842. Both service jobs have successful assignment,
  observed empty inventory before close and verified scope closure. These are
  actual API observations under the source-bound fresh suspended-launch path,
  not a full process/module/export mapping or global memory measurement.
- The native platform preflight exited zero with `PLATFORM_READY` and fixed
  cleanup observations. Both that child and the later transaction child have
  source-latched `RESUMED`, assignment and empty-before-close observations. Their
  public fixed observations do not duplicate the full primary-thread projection.
- Actual registry preparation found both views absent and created the nonce and
  parent with ownership. Final cleanup reports both absent, all owned handles
  closed, strict services-stopped confirmation and no close failures. The
  nonce-free snapshots retain the explicit exclusive-writer/no-atomicity scope.
  The getter branch remains a source inference, not an executed-branch witness.
- The native transaction observed four Auth frames and `AUTHORIZED`, one queued
  DB login request, `WAIT_PLAYERS`, zero admitted player lists and unsupported
  count three. It exited one at `OWNER_SERVICE`, phase `FAILED`, failure `DB`,
  status `UNSUPPORTED`. DbServer's ready marker and 99 game DB user tables were
  observed; before/after owned-runtime checks still passed.
- Service, firewall, LocalDB, registry and private-file cleanup all report true,
  as do final candidate/source stability and the owned service-job empty gate.
  These positive component observations survive the overall experiment failure.

Normal version/reference-checksum acceptance, actual server development-skip
branch, complete DB list, selected-shard success, character/Map handoff, current
world/resource namespace and full process memory/module mapping remain absent
or false. Source metadata and the new build do not supply those authorities.

## Original source pipeline: possibilities, not received command identities

`source-pipeline.json` binds ten exact source files and 22 whole-function byte
spans at the run commit. It also binds the exact `comm_backend.h` DBServer enum
span and its finite normalized command catalogue. `COMM_MAX_CMD` is 2;
`DBSERVER_CLIENT_PROTOCOL_VERSION` is 20110614. The old NetLink profile uses a
separate wire offset of five; names below are normalized application commands.

| Normalized ID | Original symbol | Source relevance after login |
| ---: | --- | --- |
| 2 | `DBGAMESERVER_SEND_PLAYERS` | `getEnts_sendPlayers` prepares an async SQL-backed packet; `sqlGetPlayersCallback` completes and sends it. |
| 3 | `DBGAMESERVER_MSG` | Protocol/version/auth/other rejection paths use `sendMsg`; this is separate from account-service notices. |
| 8 | `DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT` | `account_clientCountFailure` emits zero reply shards and the fixed no-server message. |
| 9 | `DBGAMESERVER_ACCOUNTSERVER_CATALOG` | `account_handleProductCatalog` emits it when an AccountServer link exists. |
| 13 | `DBGAMESERVER_ACCOUNTSERVER_INVENTORY` | Cached inventory can relay directly, including after async shard-account loading. |
| 14 | `DBGAMESERVER_ACCOUNTSERVER_UNAVAILABLE` | `account_handleProductCatalog` calls its unavailable producer when no AccountServer link exists. |
| 20 | `DBGAMESERVER_QUEUE_POSITION` | Separate queue-server path; ordinary native session recognizes it. |

After `handleLogin` accepts a direct non-queue login, `clientcomm_PlayerLogin`
calls product catalog, account registration, loyalty update and inventory request,
then `sendPlayers`. If **each relevant AccountServer lookup returns NULL**, the
first three calls can synchronously send normalized **14, 8, 8** in that source
order. The inventory request's no-link count-failure branch is commented out;
cached/async inventory can separately emit 13. The player list waits on the
shard-account/VIP/SQL path. This source-possible sequence is not evidence of
actual AccountServer state, packet order or names in this run.

There are two distinct unsupported policies. The ordinary `application_message`
increments its unsupported counter for unknown commands and returns `COH_OK`.
Known-command parsers can separately return `COH_UNSUPPORTED`, including logical
tail or slot-lock refusals. The exact development owner's `db_service` additionally
rejects **any** unsupported count after an otherwise successful ordinary service
call. Thus three ignored envelopes alone can fail the new owner, and other
source paths can also produce an unsupported result. The count and status cannot
distinguish them. Zero admitted lists does not prove no SEND_PLAYERS envelope
arrived. A new, separately admitted fixed header observation is needed to retain
an actual command identity; no packet body or name is invented here.

This review read only retained public bytes and exact Git source. It downloaded
nothing, ran no tests/compiler/runtime/helper, called no Windows/registry API,
and replayed no capture or previous qualifier.
