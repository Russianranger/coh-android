# Combined application server-only runtime

`server_runtime.py` is an additive adapter to the exact imported launcher runtime.
It starts the retained **native ARM64 PostgreSQL and actual Wine/FEX DbServer and
MapServer**. The CoH graphical executable and conventional launcher executable
are never launched. Wine registration uses the retained private headless X
server; that is a runtime dependency, not a compatibility client session.

The adapter does not include the server executables, Wine, rootfs or original
game data. Import/setup retains their verified external donor closure. Original
imports and the conventional application's private account/profile are not
modified. All writes occur in this application's isolated state/profile.

## Invocation and binding contract

```text
python3 /opt/combined/server_runtime.py
  --guest-modules /opt/coh
  --assets /opt/coh
  --state /state
  --game-data /game/data
  --session-id <32 lowercase hex>
  --import-generation generation-<32 lowercase hex>
  --timeout-seconds 21600
  [--provision-test-character | --logical-backup /imports/profile.pgdump]
```

Run within one owned PRoot session with `-i 1000:1000`, `--sysvipc`, and the
retained Wine/FEX settings. Bind these private imports:

| Guest path | Imported or owned path |
|---|---|
| `/opt/coh` | Verified donor `assets/` including its exact Python module closure |
| `/opt/coh/pgsql` | Extracted `pg/opt/coh/pgsql` |
| `/opt/wine` | Extracted Wine/FEX directory |
| `/opt/combined` | New application's bundled runtime adapter only |
| `/game` | Completed game import parent, containing `data/` and `complete.properties` |
| `/state` | New application's persistent server state |
| `/tmp` | Fresh session temporary directory |
| `/etc/passwd`, `/etc/group`, `/etc/hosts` | Retained private runtime identity and loopback hosts files |

The rootfs, assets, Wine and PostgreSQL payload layouts match the conventional
launcher's `DiagnosticRuntime` setup. Do not overwrite donor Python modules
without updating and verifying **both** their client/runtime manifest closures.

The minimum known closure is deliberately retained instead of inventing a
smaller unqualified server package: `runtime-lock.json`, `client-manifest.json`,
`runtime-manifest.json`, all their pinned payloads, accepted DbServer package and
schema, `game-package.tar.gz`, PostgreSQL runtime, prepared client prerequisites
and caches, authored avatar/world/beacon/zone/server cache supplements, and the
manual-start DbServer supplement. The graphical client bytes can remain imported
without executing them. They are outside the new APK.

## Fresh disposable profile

`--provision-test-character` is explicit and applies only to a newly owned,
previously empty profile without a logical backup. The retained unchanged
source `TestClientCreate.exe` and `TestClientBridge.exe` create one actual
COHLOCAL character over the real server protocol. Its source-generated name is
preserved. The original host-qualified control sequence observes live Atlas
entry, sends a test influence command, requests ordinary logout, validates the
committed PostgreSQL selected-row snapshot, and closes/reaps the helper before
publishing server readiness. No synthetic character or SQL gameplay insert is
used. This is **source-helper provisioning**, not native character creation.

The helper's raw console/pipe captures are excluded from exports and removed
once its save evidence hashes are retained. Interrupted allocation is not
silently recreated or overwritten. Subsequent starts preserve the resulting
character and skip the helper.

Without this flag, a new profile stays empty and Atlas can run, but no existing
character will be available to the native client's list/selection operation.

## Optional existing character copy

`--logical-backup` accepts a bounded PostgreSQL **custom-format** (`PGDMP`)
backup, not a raw `pgdata` tree. The restore runs as the non-superuser `cohtest`,
with no owner/ACL replay, in one transaction into an empty application-owned
database. It restores only the `dbo` and `coh_meta` schemas. A matching compatible
backup must include the complete contents of those schemas and be created with
`pg_dump --format=custom --no-owner --no-privileges --schema=dbo --schema=coh_meta`.
Credentials are passed privately through the process environment, never command
arguments or exports. The original database is not connected or altered by this
adapter.

An initialized profile cannot be replaced by another backup. Reuse verifies the
same input digest when a backup is supplied again. The first application scope
admits a single COHLOCAL character, ID 1, with finite saved coordinates and saved
static map 1 or 5. Other profiles/maps fail admission while preserving data.
Saved King's Row requires the verified zone/beacon supplement. Saved location
selects the initial server; no SQL relocation or Atlas fallback is performed.

## Readiness, lifecycle and reporting

A process launch or open port is insufficient. Readiness retains the accepted
DbServer fixed-input, loopback-bind and dispatch witnesses plus MapServer
completed-tick and DbServer map-status gates. The manual DbServer supplement is
mandatory so no unused Launcher connection is required.

`server-ready.json` and a `type=server_ready` JSON line expose only owned
loopback endpoints, exact session/import identity and input hashes, the original
`client_version`, local-development auth policy, source-helper usage and bounded
status. A five-second heartbeat requires fresh native dispatch. The native
client must separately validate the current service owner and freshness; the
receipt is never evidence of encrypted AuthServer authentication or live world
entry. Client launch remains a manual application action.

Stop uses `stop-request` in `/state` or SIGINT/SIGTERM. Readiness is revoked before
cleanup. Owned Wine process lineage and prefix shutdown, durable PostgreSQL fast
shutdown, process/pipe reaping, config removal and server cache release reuse the
retained lifecycle methods. No name-based global process kill or profile deletion
is performed. The operation is capped at six hours, including startup.

Stdout contains bounded projected stage messages and endpoint receipts. Process
output, SQL rows, auth identifiers, credentials and cookies are not emitted or
included in the curated `latest-report.json`; the latter records numeric process
completion and cleanup state. The fresh disposable local mode uses `UseFakeAuth
1`; encrypted account authentication remains separate work.

## Qualification

```sh
python3 native-android/combined-client/runtime/check.py --source-root . \
  --donor /path/to/COH-Atlas-Gameplay-0.13.36.apk --output runtime-proof.json
```

Fifteen host test methods exercise malformed saved-map/identity inputs, backup
formats and file ownership, ancestor links, immutable source selection, endpoint
identity, error redaction, retained API availability and private SQL/event
projection. They run against both the current guest sources and the exact pinned
0.13.36 APK's Python closure. These are deterministic **admission/API contract**
tests. They do not execute Wine/FEX/PostgreSQL or prove that this new adapter
started a server, provisioned a player, logged in, or rendered a native live
world. The combined APK's physical Thor run must establish those new boundaries.
