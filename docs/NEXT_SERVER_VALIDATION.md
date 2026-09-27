# Next server validation

Updated: 2026-09-27. Normal DbServer startup/reload, real network save
acknowledgements, asset-backed template comparison and Atlas Park readiness
have passed. The corrected hosted run 36176806895 freshly matched all 56
template outputs and observed Atlas Park ready for 62.235 seconds. Character
run 36282414135 passed fresh fake-auth creation, live currency change,
protocol logout/save, service restart and exact-name short scene resume.
Sustained-session run 36295176484 then passed missing-name refusal, 66.953 seconds
connected after exact-name resume and a second protocol save. The next proposed
server gate is a transfer round trip between two prestarted Atlas Park instances.

Continuation on 2026-09-26 recovered the run that had completed on 2026-09-25
at 19:16:38 UTC while the committed handoff still said it was running. No queued
or running GitHub workflow was found at recovery. This establishes the repository
and workflow state, not another Codex session's internal status.

## PostgreSQL network acknowledgement correction

Source review found that an ordinary network container acknowledgement could
be sent before the SQL FIFO completed its write. The existing persistence fixture
proved commit-before-worker-completion, not commit-before-network-ACK.

The PostgreSQL patch now drains completed FIFO work before explicit container
ACKs are sent. Packet IDs are captured before callbacks run; the original link
UID is checked afterward. SQL-backed requests collect explicit ACK IDs locally
and send one batch after processing all entries, including delete/unload work.
This also fixes the prior partial/repeated batch ACK array for PostgreSQL saves.
Other database providers retain their existing send behaviour.

The drain is synchronous and can delay DbServer while SQL is pending. This is a
correctness-first implementation, not a throughput optimization. Group and
autocommand broadcasts retain separate legacy semantics. A batch is not one
transaction: a prefix can commit before a later item fails, without a success
ACK for the batch.

`MapServer -dbquery` gains a query-only received-ACK diagnostic, plus a bounded
`-setbatch LIST ID1 FILE1 ID2 FILE2` operation for two distinct positive IDs.
Put `-timeout` before `-setbatch`; timeout values are **milliseconds**. This uses
the normal save protocol and does not load game definitions or a map.

The new `PostgreSQL network save acknowledgements` workflow builds on a successful
schema run and its matching fixture-OFF reference package. Its driver:

1. Starts normal DbServer on a fresh disposable PostgreSQL cluster.
2. Creates two MiningAccumulator containers through normal MapServer queries.
3. Requires actual received ACK diagnostics and independently committed SQL rows.
4. Restarts DbServer, then updates a saved container.
5. Locks the second row in PostgreSQL and sends a two-container batch; requires
   an observed SQL writer lock wait and no received ACK while the write is blocked.
6. Releases the lock, requires one two-ID ACK and both committed values.
7. Injects a deferred constraint failure at COMMIT; requires no ACK, DbServer
   failure exit, the expected SQLSTATE and the unchanged committed row.

Credentials, raw configuration and private work stay outside uploaded evidence.
These diagnostics do not create a game character or prove gameplay persistence.

[Network run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
passed at `a0ae66d72648d33a7f70b3116d1e1800d9164184`, using reference run
36088012664 and schema run 36088012666 (both built at `775a0dd...`). It verified
creation, a modified saved container after restart, and the two-container batch.
The actual SQL writer remained blocked for **2.078 seconds without an ACK**;
after release, both rows were independently confirmed committed. A deferred
COMMIT failure with SQLSTATE `42501` produced **zero ACKs**, preserved the prior
row, and stopped DbServer with exit 3. The report has no failures. Preserve the
[summary/report](postgresql-evidence/network-ack-36125829311.json) and
[complete redacted evidence](postgresql-evidence/network-ack-36125829311.zip).

The refreshed [normal schema startup/reload run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
also passed. Earlier runs 36089560076/36089560078 stopped because the C logger
labels expected PostgreSQL NOTICE messages as `SQLERROR`. The driver now
recognizes only the exact observed catalog-maintenance notices, retains them in
the report, and still rejects all other SQL errors. Forty-four driver acceptance
tests passed. Driver-only pushes can reuse an accepted schema/reference pair;
the exact source receipt checks remain mandatory.

The source patch passed the [PostgreSQL regression run 36088012670](https://github.com/Russianranger/coh-android/actions/runs/36088012670)
at `775a0dd770adac045484805dbbb5f68054c7a354`: all four jobs, including 21
real-DbServer check groups across 14 processes. The [persistence report](postgresql-evidence/network-ack-build/dbserver-persistence-36088012670.json)
is retained. That controlled fixture remains separate from the new network test.

## Asset-backed template comparison

`tools/runtime_asset_bundle.py` reconstructs the reviewed input package from
fonts/player/geom/geomBC/stage1a/stage1b/stage1f PIGGs. It verifies each original
archive against prior assessment hashes, performs integrity inspection, and
selects only binary assets. There are **16,721 files / 985,644,857 bytes**.
No custom i26 caches, generated parser bins, credentials or save data enter it.

The compressed package is **615,541,018 bytes**, SHA-256:

```text
28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07
```

The checked manifest and receipt are under `assets/reference-inputs-*.json`.
Payload paths, sizes and hashes are checked again during extraction, with ZIP
metadata/decompression bounds, Windows path/case checks and an incomplete marker.
Both stored and compressed versions were independently extracted and verified.
Only metadata and tools are committed; binary assets remain outside Git.

The exact reviewed ZIP is uploaded to unpublished draft release **396839391**
as asset **588984151**, with the size and SHA-256 above independently confirmed
through GitHub's asset metadata. Earlier incomplete asset **588979946** is not
an accepted input and must be ignored. No new upload or original PIGG transfer
is required.

The downloadable package is also preserved as three byte parts. Place them in
the same Android Download directory and reconstruct without a Windows PC:

```sh
cd ~/storage/downloads
cat coh-reference-assets.zip.part01 coh-reference-assets.zip.part02 coh-reference-assets.zip.part03 > coh-reference-assets.zip
sha256sum coh-reference-assets.zip
```

The expected hash is above; per-part hashes are in
`assets/reference-inputs-parts.json`. Fixed order and timestamps preserve stable
payloads; DEFLATE archive bytes can vary with zlib, so the receipt identifies the
exact reviewed transfer file.

The `Asset-backed reference templates` workflow accepts either a repository
release asset ID (including an unpublished draft release) or a download URL from
the `COH_ASSET_BUNDLE_URL` repository secret. The downloader enforces the exact
archive size/hash, rejects insecure redirects, and does not forward GitHub
credentials to redirected hosts. Private URLs are never placed in commits or
printed in diagnostics.

Run the workflow manually with `schema_run=36088012666`,
`reference_run=36088012664`, `release_asset_id=588984151` and
`run_one_map=true`. It stages a new runtime,
verifies all pinned text/binary inputs,
seeds six accepted attribute files plus five generated ID maps, and runs ordinary
`MapServer.exe -nogui -templates`. Acceptance requires all **56 outputs freshly
rewritten and byte-identical** to the accepted data-only outputs. Only verified
schema outputs and diagnostics are archived; incidental caches stay unapproved.
The unmodified reference does not report its queued error count before exiting,
so file equality does not establish absence of queued errors or complete assets.
The evidence includes the exact `comparison-runtime-inputs.json` so the following
map test can verify that its fresh stage uses the same binary assets.

The browser connection recovered and the upload completed. The first manual
[run 36174562963](https://github.com/Russianranger/coh-android/actions/runs/36174562963)
passed tooling checks but stopped at the asset download with an HTTP error,
before extraction or any game process. Its read-only job token is the suspected
cause: draft releases require push access, although public release assets can
be read with a read-only token. The original downloader suppressed the numeric
HTTP status, so the exact rejection was not recorded.

[Fix 5f37d7c](https://github.com/Russianranger/coh-android/commit/5f37d7c)
grants `contents: write` only to the manually invoked comparison job; global and
tooling permissions remain read-only. This permits draft access without
publishing the release or copying raw assets into Actions artifacts. Download
failures now report only numeric HTTP status and a fixed API/download-stage
label; URLs and server response details remain suppressed. All 12 downloader
tests passed, including six diagnostic/privacy regressions, and the subsequent
[tooling run 36175800522](https://github.com/Russianranger/coh-android/actions/runs/36175800522)
passed.

The corrected manual [run 36175960917](https://github.com/Russianranger/coh-android/actions/runs/36175960917)
at `5f37d7c674c9d1205138f6e7dbfc04a6ff2b9ea8` downloaded the exact
615,541,018-byte ZIP and verified the accepted SHA-256. Hosted draft access is
therefore working. The next stage stopped with `Manifest must use canonical JSON`
before any game process. Windows Git checkout converted the canonical manifest's
LF line endings to CRLF:

| Manifest bytes | Size | CRLF count | SHA-256 |
| --- | --- | --- | --- |
| Accepted canonical input | 3,832,869 | 0 | `cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f` |
| Rejected Windows checkout | 3,933,249 | 100,380 | `d1b3a48a283b9c103191e13f71328026e85bc604e12ff3ffb3b7567e4d3c315c` |

[Fix fe98dd5](https://github.com/Russianranger/coh-android/commit/fe98dd5a9761fb05d79b9b3f9f39a771eb9ea687)
adds `assets/reference-inputs-*.json -text` to preserve the reviewed metadata
bytes during checkout. The manifest verifier and accepted hashes are unchanged.
A temporary Git checkout with `core.autocrlf=true` reproduced the exact accepted
canonical bytes; [push tooling run 36176404244](https://github.com/Russianranger/coh-android/actions/runs/36176404244)
passed. This is a checkout correction, not an asset or game-code modification.

Manual [run 36176806895](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
used `fe98dd5a9761fb05d79b9b3f9f39a771eb9ea687` and the same accepted inputs
with Atlas Park enabled. Asset extraction verified all 16,721 files and the
exact canonical manifest hash; both source/data snapshots and full runtime
staging passed. The ordinary template comparison then freshly matched all
**56 expected files** in **25.89 seconds**, with no output differences or
reported failures. Its report finished at 2026-09-25 19:06:09 UTC. Atlas Park
subsequently passed the independent readiness gate below. See the historical
[transfer/setup evidence](reference-runtime-evidence/asset-transfer-20260925.json),
the recovered [comparison report](reference-runtime-evidence/reference-template-comparison-36176806895.json)
and [complete comparison artifact](reference-runtime-evidence/reference-template-comparison-36176806895.zip).

After workspace maintenance, the saved three parts were restored and the joined
ZIP hash reverified. All 16,721 asset payloads passed extraction checks again.
The current 29-file reference package was assembled with the pinned source/data
and those assets. Offline assembly does not execute MapServer. Earlier push
workflow runs correctly skipped the manual-only comparison job; the successful
manual run executed both comparison and one-map validation.

## Passed Atlas Park readiness gate

The workflow's `run_one_map` option runs `database/postgresql/tests/run_one_map.py`
after a successful comparison. It requires a separate fresh full runtime stage,
matching comparison evidence and the accepted schema archive. It copies those
inputs into private disposable work, starts PostgreSQL and DbServer, and seeds
only the 56 verified generated files. Comparison caches are not carried forward.

Source-supported one-map commands are:

```text
DbServer.exe -start 0
MapServer.exe -nogui -nosharedmemory -nostats -db 127.0.0.1 -map_id 1 -udp 7001 -tcp 0
```

Map 1 is Atlas Park. Independent stock `-dbquery -getstatus 1 1` requests must
observe the initial not-started state, then the map's registered endpoint and
ready state. In the pinned source, DbServer clears the starting flag only upon
the ready-for-players packet after map setup. The test keeps both services alive
for 60 seconds and requires continuing server-status updates. An open port or
SQL row alone does not prove readiness. The evidence records bounded redacted
logs and failure diagnostics, with no game-character claim. Let actual runtime
failures name missing assets before requesting more archives.

Run 36176806895 observed **62.235 seconds** of ready status with continuing
updates, exceeding the requested 60 seconds. Its map report finished at
2026-09-25 19:16:14 UTC and contains no failures. It used a separate fresh
runtime and the same accepted identifiers, without reusing comparison caches.
The [map report](postgresql-evidence/one-map-36176806895.json),
[complete map artifact](postgresql-evidence/postgresql-one-map-36176806895.zip)
and [accepted gate identities and archive hashes](reference-runtime-evidence/accepted-gates-36176806895.json)
are preserved. This proves the bounded readiness observation, not complete
asset coverage or a character session. Normal executables do not expose their
queued startup error count.

## Passed character persistence and sustained session

The [character persistence harness](CHARACTER_PERSISTENCE_VALIDATION.md)
passed all eight phases in [run 36282414135](https://github.com/Russianranger/coh-android/actions/runs/36282414135)
at `86e512e85c8350714bc7b58668bf11443dc164f8`, with no failures. Stock TestClient
created `TEST20636` (ID 1) on Atlas Park, observed influence 12345 through the live
MapServer response, requested protocol logout and verified committed selected
SQL rows. Service restart preserved those rows and LoginCount 1; the exact-name
short resume preserved them again and advanced LoginCount to 2. The selected
snapshot contains one `ents`, one `ents2`, seven power and thirteen costume-part
rows. Preserve the [report](postgresql-evidence/character-persistence-36282414135.json),
[redacted archive](postgresql-evidence/character-persistence-36282414135.zip) and
[acceptance/provenance receipt](postgresql-evidence/accepted-character-persistence-36282414135.json).
Earlier status-parser and console-capture attempts remain historical in the
character validation record.

Stock `-justlogin -character NAME` disables CREATE fallback but also exits after
the scene exchange; it provides a short resume probe, not a second sustained
session. That accepted result retains its scope. The separate opt-in
`-resumeonly` diagnostic client now preserves STAY_CONNECTED, disables CREATE
and explicitly refuses a missing requested name. It is staged beside the stock
client as `TestClientResume.exe`; the accepted stock runtime is unchanged.

[Sustained-session run 36295176484](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
passed all twelve phases at `4e8058c3ffe20acda61b55023202d409ed1d0df1` with no
failures. The missing-name probe exited naturally with code 3 and left the one
original character, selected SQL rows and LoginCount unchanged. The resumed
`TEST-37762` (ID 1) matched the processed player update and stayed connected on
MapId 1 for 66.953 seconds across ten samples with current map heartbeats. Live
influence was 12345 before and after observation, then changed normally to 23456
and committed after the second protocol logout. Identity and selected rows stayed
unchanged except for the intended currency change; LoginCount advanced to 2.
See the [report](postgresql-evidence/character-session-36295176484.json),
[redacted archive](postgresql-evidence/character-session-36295176484.zip),
[acceptance receipt](postgresql-evidence/accepted-character-session-36295176484.json)
and [scope/attempt record](SUSTAINED_SESSION_VALIDATION.md).

## Proposed Atlas instance transfer and separate Android gate

The next bounded experiment will start two owned MapServers for Atlas Park map 1
and its pinned clone 101 on distinct ports, then move the same connected character
1 → 101 → 1 through `CMD mapmove`. Pinned `maps.db` defines 101 with `BaseMapID 1`,
so this uses the reviewed Atlas assets. Each leg must show the expected DbServer
MapId, connected status without `InMapXfer`, a fresh destination `SERVER_UPDATE`
identifying the same character, current map heartbeats and a live currency reply.
Both instances share MapName, so that text alone cannot identify the destination.
The current one-shot resume-update diagnostic needs a transfer-specific renewal
before it can establish a fresh update on each leg.

Final protocol logout must commit the expected currency and unchanged selected
identity/power/costume rows, without another login or character. This is proposed
and unvalidated: it would exercise handoff between two prestarted Atlas instances,
not new-zone assets, mission transfers or automatic Launcher startup. Broader
player-session callbacks and auxiliary services remain separate checks.

The separate [Android milestone](ANDROID_PORT_PROPOSAL.md#stages-and-acceptance-criteria)
is a diagnostic APK running ARM64 PostgreSQL under its own UID and the existing
Win32 ODBC probe through Wine/translation. It must prove initialization,
transaction round trips, restart and owned-process shutdown on Thor without
Termux or root. No Android shell or verified runtime is implemented here yet.
Graphical/custom-client compatibility, gameplay and Android execution remain
unvalidated.
