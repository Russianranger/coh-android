# DbServer PostgreSQL persistence

The actual DbServer persistence implementation is validated in two complementary
ways: controlled fixtures exercise its container parser, SQL generator, worker
queues, reader and template updater; ordinary fixture-OFF DbServer and MapServer
processes exercise network save acknowledgements against generated game schemas.
Neither test creates a playable character or starts a game map.

The [21-group fixture regression](https://github.com/Russianranger/coh-android/actions/runs/36074139842)
passed across 14 process invocations, including the first-start foreign-key cleanup
case. Its [report](postgresql-evidence/fk-cold-start/dbserver-persistence.json)
preserves the result. The earlier validation at
`0827ccc992daa7530d9f98d742122238197847df`,
[run 35962572993](https://github.com/Russianranger/coh-android/actions/runs/35962572993),
passed all four jobs and 20 fixture groups; its
[report](postgresql-evidence/persistence-v2/dbserver-persistence.json) and
[build receipt](postgresql-evidence/persistence-v2/win32-build.json) remain historical.

The [normal schema run 36125829298](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
and [network acknowledgement run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
passed using the matching fixture-OFF reference build 36088012664 and accepted
schema build 36088012666. See [the matching runtime](REFERENCE_RUNTIME.md) for
those exact input receipts and the [network evidence summary](postgresql-evidence/network-ack-36125829311.json).

## Transaction behavior

For PostgreSQL, every FIFO command runs in a manual transaction. The worker
waits for a successful commit before returning its completion to the main
thread. A save spanning multiple ODBC batches is one transaction. Container
deletion also groups all child-table and parent-table deletes into one command.

The first SQLSTATE is retained across a failed operation. Statement-level retry
is disabled inside these transactions. Serialization failures (`40001`) and
deadlocks (`40P01`) roll back and replay the entire FIFO command, at most five
attempts. Commit-time failures use the same policy. Constraint violations,
unknown failures and exhausted retries stop the process without acknowledging
the failed command. Automatic reconnect/replay after an uncertain connection
loss is deliberately absent: the application cannot assume whether that commit
reached the database. The supervisor/operator must resolve and restart it.

For explicit PostgreSQL network save acknowledgements, DbServer now drains
pending SQL work before sending the reply. It snapshots the reply and container
IDs before running completion callbacks, then rechecks the link identity before
sending. SQL-backed multi-container requests defer a single acknowledgement
batch until the whole request has been processed. The drain is synchronous and
can block the main thread; this is a correctness change, not a throughput result.
Each queued save keeps its own transaction. An earlier save in a batch can commit
before a later one fails, even though no batch acknowledgement is sent. This does
not make the batch atomic or extend the claim to every broadcast/session callback.

The previous SQL Server path retains its existing transaction behavior. The
PostgreSQL worker always uses transactions, including when the legacy runtime
option requests untransacted FIFO operations.

See [PostgreSQL's complete-transaction retry requirement](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html).

## Schema and lookup compatibility

- PostgreSQL template changes use a transactional table replacement. It copies
  shared columns, retains the container sequence high-water mark (including
  deleted/rolled-back high IDs), and recreates indexes and foreign keys.
- Failed conversion or an unhandled dependency aborts the replacement, preserving
  the original table. The legacy destructive rebuild fallback is disabled for
  PostgreSQL. This is atomic per table, not across an entire schema update.
- Rebuilds target ordinary game-generated tables. Custom triggers, grants, row
  security, inheritance, generated/identity columns and unsupported defaults or
  NOT NULL customizations require a reviewed migration; they are not silently
  discarded. Rebuilds run during schema startup after the queue is drained.
- `Name`/`AuthName` equality paths use explicit ASCII case folding, matching the
  tested game cache behavior. Stored spelling, accented bytes and trailing
  spaces remain distinct. This does not claim complete Unicode case folding or
  reproduce every SQL Server collation. Database-enforced case-insensitive
  uniqueness and arbitrary custom/wildcard queries remain separate considerations.
- The auction activity filter uses PostgreSQL timestamp/interval syntax. This
  fixes DbServer's query, not the entire AuctionServer service.

## Existing development databases

Stop DbServer before changing the compatibility functions. With PostgreSQL
running, back up and apply the idempotent migration:

```sh
python3 database/postgresql/pg_local.py backup --root "$HOME/coh-pg" --file "$HOME/coh-before-migration-2.backup"
python3 database/postgresql/pg_local.py migrate --root "$HOME/coh-pg"
```

Migration 2 introduces the name and rebuild functions. DbServer checks for it
before loading templates. The helper refuses to apply these functions over a
newer migration version. Initial setup and restore apply the current functions
automatically. Keep one DbServer writer per shard.

## Reproduction

The hosted PostgreSQL workflow builds the source pin with its patch/overlay and
`COH_PG_PERSISTENCE_TESTS=ON`. Ordinary CMake builds leave the diagnostic entry
point disabled. The test requires the matching **32-bit Windows Unicode ODBC**
driver and a fresh, disposable PostgreSQL cluster:

```powershell
python database/postgresql/tests/run_dbserver.py --bin "$env:PGBIN" --dbserver out/pg-source/out/build/vs2026/bin/OptDebug/DbServer.exe --root "$env:RUNNER_TEMP/coh-pg-fifo" --report out/dbserver-persistence.json --driver "PostgreSQL Unicode"
```

Use the installed driver's exact name. The runner creates its own cluster,
restricted game role, test database and guard table; it never accepts a player's
save database. The test executable additionally checks a `coh_test_` name,
non-superuser role and guard table. Fault-injection fixtures deliberately cause
some child processes to exit with a failed-save status; the runner checks both
the expected status and database rollback before continuing.

Coverage includes 512 child rows crossing SQL batching boundaries, repeated
writes, multiple worker queues, read-after-write callbacks, non-ASCII text,
rollback/retry during a late update and at commit, permanent failures, retry
exhaustion, atomic deletion, lost connections, process/database restart, WAL recovery, table
rebuild and backup/restore. Trigger-raised SQLSTATEs exercise the real PostgreSQL
error path; they do not establish real-world deadlock frequency or performance.
The connection-loss fixture terminates its own test backend during an
uncommitted write; it checks rollback and process exit without replay. It does
not simulate every possible network outage or ambiguous commit result.

The legacy utility layer may report that it cannot find a game data directory
during these fixtures. That is expected here: the diagnostic entry intentionally
does not load game assets. Pass/fail is checked against the database contents,
required completion markers and exact process exit statuses.

## Normal network acknowledgement validation

`database/postgresql/tests/run_network_ack.py` starts ordinary fixture-OFF
DbServer and MapServer processes in a fresh disposable PostgreSQL cluster.
MapServer's `-dbquery` path sends normal container protocol requests for list 23
(`MiningAccumulator`), a SQL-backed generic container in the accepted generated
schemas. It does not require game asset archives. The driver checks receipts,
actual SQL catalogs, flushed network reply markers and independent SQL reads;
process exit alone cannot satisfy its acknowledgement checks.

[Run 36125829311](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
passed with no reported failures:

- Created generic containers 1 and 2, then modified an existing container after
  restarting DbServer to clear cached container state.
- Held a real PostgreSQL row lock on the second item of a two-container request.
  The writer was observed waiting for that lock, and no acknowledgement arrived
  during a 2.078-second blocked interval. Releasing the lock allowed the reply;
  independent SQL reads confirmed both new row values within 0.094 seconds of
  observing the acknowledgement.
- Forced an update to fail at commit with a deferred constraint trigger raising
  SQLSTATE `42501`. DbServer exited 3, the client received no acknowledgement and
  the previously committed row remained unchanged.

The [summary](postgresql-evidence/network-ack-36125829311.json) and
[complete redacted evidence](postgresql-evidence/network-ack-36125829311.zip)
preserve the exact inputs, observations and logs. Startup's known catalog
maintenance notices are retained and narrowly classified; SQL failures remain
blocking outside the deliberately injected failure phase.

## Remaining game validation

Ordinary asset-backed template comparison, actual character/account creation,
player-session save/logout, map transfers, auxiliary services, SQL Server data
migration and Thor/Wine/Android behavior still need separate validation. The
network diagnostic covers generic container acknowledgements; it does not call
the player-session completion callback or test a disconnected game client.
Template customization outside the supported generated-table shape is not an
automatic migration path.
