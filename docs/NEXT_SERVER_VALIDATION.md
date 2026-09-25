# Next server validation

Updated: 2026-09-25. The previous normal DbServer generated-schema startup/reload
milestone remains recorded in `REFERENCE_RUNTIME.md`. This page separates newly
implemented checks from actual hosted results.

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
Hosted result links are added after execution, not inferred from unit tests.

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

Run the workflow manually with a successful schema run ID and its matching
reference run. It stages a new runtime, verifies all pinned text/binary inputs,
seeds six accepted attribute files plus five generated ID maps, and runs ordinary
`MapServer.exe -nogui -templates`. Acceptance requires all **56 outputs freshly
rewritten and byte-identical** to the accepted data-only outputs. Only verified
schema outputs and diagnostics are archived; incidental caches stay unapproved.
The unmodified reference does not report its queued error count before exiting,
so file equality does not establish absence of queued errors or complete assets.
The evidence includes the exact `comparison-runtime-inputs.json` so the following
map test can verify that its fresh stage uses the same binary assets.

The GitHub connector currently has no large-file upload capability. The available
browser is signed out of GitHub. The package and workflow are prepared, but
hosted asset execution needs an authenticated upload of this exact ZIP to the
repository (a draft release is sufficient), or an accessible URL in the secret
above. Existing supplied PIGGs do not need to be uploaded again.

## Following the comparison

The workflow's `run_one_map` option runs `database/postgresql/tests/run_one_map.py`
after a successful comparison. It requires a separate fresh full runtime stage,
matching comparison evidence and the accepted schema archive. It copies those
inputs into private disposable work, starts PostgreSQL and DbServer, and seeds
only the 56 verified generated files. Comparison caches are not carried forward.

Source-supported one-map commands are:

```text
DbServer.exe -start 0
MapServer.exe -nogui -nosharedmemory -db 127.0.0.1 -map_id 1 -udp 7001 -tcp 0
```

Map 1 is Atlas Park. Independent stock `-dbquery -getstatus 1 1` requests must
observe the initial not-started state, then the map's registered endpoint and
ready state. In the pinned source, DbServer clears the starting flag only upon
the ready-for-players packet after map setup. The test keeps both services alive
for 60 seconds and requires continuing server-status updates. An open port or
SQL row alone does not prove readiness. The evidence records bounded redacted
logs and failure diagnostics, with no game-character claim. Let actual runtime
failures name missing assets before requesting more archives.

The pinned TestClient supports fake-auth creation and exact-name resume without
a graphical client. Default creation is Primal Hero, which targets Atlas Park.
Use a disposable account, record its actual character ID/name, wait for logout
save, restart the services, and resume that exact character with CREATE fallback
disabled. Verify stable character and child-table fields, not volatile timestamps.
Account services, transfers, the customized client and Android execution remain
separate checks. These map/character steps have not been executed yet.
