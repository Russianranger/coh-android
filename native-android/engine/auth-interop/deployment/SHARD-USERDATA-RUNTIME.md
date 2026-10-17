# Disposable original shard and UserData SQL execution

`hosted_shard_userdata.py` is an executable Windows prerequisite for the next
authenticated shard experiment. It prepares the original `server`, `worldstatus`
and four `user_data` columns in a **new** disposable LocalDB instance, compiles a
small x86 diagnostic and executes it through the exact qualified ODBC Driver 17.
It replays the sealed successful Auth-only source/artifact prerequisite without
repeating account login, starting AuthServer or rebuilding any accepted binary.

The generated diagnostic contains twelve complete unchanged original function
bodies plus all six original `CDBConn::Bind` overloads. These include
`CServerList::Load`, `SetServerSocketByAddress`, `AccountDB::AboutToPlay`,
`ServerReadGameData`, original SQL Execute/Fetch and the original Assemble writer.
Every original source byte comes from pinned tree
`f634e21e230009fa8edc91d15429cd4da69eee8c`. Its SQL statement owner, lock/logger
and send captures are diagnostic shells. No source-required runtime account or
session is manufactured. The in-memory transport is a declared fixture; loading
a shard SQL row and testing source address matching does **not** register a live
DbServer or establish `AC_PLAY_OK`.

The real-driver diagnostic checks the original eight-column shard query,
loopback address association, unknown-address refusal, the exact full nonqueue
`SQ_ABOUT_TO_PLAY` body and the full `SQ_GAME_DATA` reply. All 128 bytes in each
data body must equal the two original SQL columns in source order. The public
fixture has no password/user-auth row and never attempts login. Only strict
Boolean/numeric results leave the diagnostic.

Both original data producers ignore the result of `Fetch()` after zeroing their
128-byte buffer. An absent row therefore produces zero bytes instead of a
protocol refusal. The diagnostic explicitly observes that original behavior and
qualifies a separate positive row/cardinality/non-NULL/16+112-byte guard. A future
live authentication driver must enforce that guard before using the data; a
successful connection or a zero-filled body cannot establish full UserData
readiness. No accepted server/profile is patched to change this behavior.

The shard client port uses SQL `smallint` and the original signed-short ODBC
binding. This bounded fixture requires 20000–32767 and does not silently truncate
a port above 32767. UserData is enabled and both queue-tail settings are disabled
inside this diagnostic's configuration shell. Those settings still need a
separate full live-service profile and current process ownership evidence.

## Coordinator-owned Windows execution

Use a fresh `windows-2025-vs2026` hosted runner with Python 3.12 and the original
qualified LocalDB 17.0.4025.3/x86 ODBC Driver 17. Checkout the reviewed commit with
`core.autocrlf=false`. Fetch historical commit
`28fe37cc2432db4adbfe047bd07a1e738d6aa754` if the checkout is shallow; the existing
Auth-only seal requires its actual Git blobs.

```powershell
python native-android/engine/auth-interop/deployment/hosted_shard_userdata.py `
  --source-root . --expected-commit $env:GITHUB_SHA `
  --auth-success-archive native-android/engine/auth-interop/evidence/auth-success-38996587760/artifact.zip `
  --output "$env:RUNNER_TEMP/shard-userdata"
```

Upload only `shard-userdata` with an always-run artifact step. It contains the
public generated source/SQL, x86 executable/cache/build logs and final receipt.
SQL consoles are suppressed, including schema, fixture and cleanup errors. The
driver always attempts drop/stop/delete of its owned instance and removes its
private temporary directory. Incomplete cleanup blocks success. Compiler and
diagnostic subprocesses have bounded execution and retained-log limits through
the existing command owner. There are no AuthServer/DbServer listeners or
production-profile changes. The SQL 1024 MiB buffer-pool setting is not a process
RSS limit.

## Qualification completed here

Five new host suites pass. The exact generated original bodies execute in
optimized and ASan/UBSan builds against an explicitly synthetic SQL/Win32 API.
That execution verifies the complete source control flow and byte comparisons;
it is 64-bit host testing, does not execute ODBC, and is deliberately refused by
the actual x86 runtime-receipt admission. Other controls verify every receipt
field mutation, source copies and fixture columns, signed port limits,
build-before-SQL ordering, success/failure cleanup and local-host refusal before
side effects. LeakSanitizer is disabled. The Windows stage has **not** executed
in this local Linux environment.

Remaining full-session dependencies are fresh encrypted authentication, a real
owned registered DbServer channel/shard activation, actual nondevelopment version
and full-checksum admission, authentic PlayOK/cache consumption, selected DBID
and Map handoff. Current source checkouts contain only DB configuration, without
the required `server/db/templates/vars.attribute`, `badgestats.attribute` or
`pophelp.attribute` runtime corpus. Those exact input bodies need recovery and
provenance before running the complete compiled MSSQL DbServer. No current
service, Android, Thor, selected-shard or authenticated DB/Map acceptance is
claimed by this source/diagnostic addition.

```sh
python3 -m unittest discover -s native-android/engine/auth-interop/deployment -p test_shard_userdata.py -v
```
