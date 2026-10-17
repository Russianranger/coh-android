# Actual original DbServer shard activation experiment

`hosted_db_shard_activation.py` prepares and runs the exact retained corrected
AuthServer and compiled MSSQL DbServer against a fresh LocalDB instance. It uses
the existing accepted schema recovery helper rather than regenerating templates,
rebuilding a donor or unpacking a large asset corpus. No accepted profile,
character or database is touched.

## Recovered input dependency

The missing unpacked template files were already present in committed immutable
artifact `docs/schema-generation-evidence/accepted-36088012666.zip`, artifact
10845505221, 665,051 bytes, SHA256
`62da453ef5673238e11b4b418692117ea7692597a079119b3aaf72504a2502ae`.
Its nested `schema-evidence/schema-outputs.zip` has 56 generated files, 682,745
bytes, SHA256 `a7bb94cd936198850f1a35ac58df925b3638caae29c02f47dca1cb3e21dbc132`.

The existing helper verifies this complete acceptance/source/data chain, combines
six pinned supplemental inputs and stages 62 exact files with manifest SHA256
`b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92`.
This is the same manifest pinned by accepted Android runtime/Atlas packaging.
The required files are real recovered bodies:

| Path beneath `data/server/db/templates/` | Bytes | SHA256 |
| --- | ---: | --- |
| `vars.attribute` | 1,928,476 | `26c5f2bba77ab66ef7619c995f343633dc1748297dc9963605734ef3aa1053bb` |
| `badgestats.attribute` | 62,106 | `ec57e497c6c044269d8d7e207b0869400ceeb18a03b94bda1a9d00a9d99cced2` |
| `pophelp.attribute` | 2,185 | `34195086d3223c717dca5e1cd00bc35a947a05d5fe31b2408a863e85aea617a1` |

All three bodies also match both earlier accepted schema artifacts. Original
ordinary MapServer `-templates` run 36176806895 subsequently compared all 56
outputs byte for byte with these accepted data-only outputs; its retained
`docs/reference-runtime-evidence/reference-template-comparison-36176806895.json`
records that equality. The schema is sufficient input to a new DB experiment;
historical PostgreSQL/Wine runtime acceptance does not qualify a new MSSQL service.

The complete compiled checksum PE is already committed inside
`evidence/independent-db-build-39000395572/artifact.zip`: SHA256
`2eb66715cb8b35d82580971b60734a92b48c91e2a557cb253d39b7fdafef6ee7`.
The existing strict build admission replays the exact retained receipt/PE hashes,
original source map, sole checksum correction and original compilation inputs.
The new recovery checks the actual PE import table: only eight Windows platform
DLLs occur. No donor VC or CrashRpt DLL is required for static imports, and the
owned profile disables the original optional CrashRpt preload.

## Runtime observation and its limit

The driver creates a new game database and original Auth schema in one owned
LocalDB instance. The original full-userdata, nonqueue Auth profile loads an
explicit loopback shard with unknown-server and explicit-ID bypasses disabled.
`supportReconnect=true` leaves the shard inactive when its address is attached;
the original `CSocketServer::ServerSetActive` handling of `AS_SET_CONNECT` must
make it active. This is a new isolated configuration; the accepted Auth-only
profile is unchanged.

The exact copied DbServer uses `UseFakeAuth 0`, ordinary encrypted startup and
the recovered schema. The experiment requires its original `DbServer Ready.`
marker, creation of all 99 game tables, original `worldstatus` transition from
zero before the DB process to one afterward, the actual reverse TCP endpoint
pair owned by these two live processes, and DB ownership of the original UDP
7000 game listener. Those observations must occur within the same process
lifetimes. A dedicated service observer validates the expected AuthServer and
DbServer process names and exact executable paths, rehashes their copied PEs,
checks the original Popen handle before and after observation, and compares
initial/final PID and UTC start ticks. Exported path identities are hashes. The
existing SQL-only process observer remains unchanged and its initial/final
generation must also match. The driver records numeric diagnostics.
It neither creates nor consumes an account grant.

Both executables receive owned inbound and outbound firewall rules for every
protocol on their original IPv4 service surfaces, blocking IPv4 addresses outside
127/8. This does not claim IPv6 isolation. Raw service/SQL consoles stay in a
private directory and are removed after owned Job Objects terminate the services.
Only fixed marker-presence Booleans, process/port/count values and artifact hashes
are retained. Source inputs, both database drops, instance stop/delete, firewall
removal and private-file cleanup must all succeed. Stream-close failure is
recorded without preventing subsequent firewall, database and private-file
cleanup attempts. The source marker and file
bounds are monitored; they are not OS memory/disk quotas.

No account-login suite is repeated. No client version is invented, no
`Ouroboros.exe` alias/reference is installed, and no checksum/version bypass is
enabled. Missing reference still causes the reviewed checksum correction to
refuse client login. The driver explicitly leaves selected-shard **play**,
nondevelopment-version admission, authenticated DB login and Map transfer false.
Successful actual registration/readiness is a useful independent next stage,
not complete Gate 26 or a playable world.

## Coordinator-owned execution

Use fresh `windows-2025-vs2026`, Python 3.12, the qualified LocalDB/ODBC17 image
and a clean reviewed checkout with `core.autocrlf=false`. Historical Git commits
`28fe37cc2432db4adbfe047bd07a1e738d6aa754` and
`8f4117e154fa7d9d9a8eb3f4f6b11bd50ab1c919` must be available for existing
source/binary admission. The already-built corrected AuthServer artifact is
12085517046, 427,525 bytes, ZIP SHA256
`da7fa3172867eabd9a652d36a4545cb78e91983123f85d894d18a9b3bac8d04d`.
Download that exact archive and extract it to a fresh `auth-candidate` directory;
the driver independently admits its retained receipt, source and binary.

```powershell
python native-android/engine/auth-interop/deployment/hosted_db_shard_activation.py `
  --source-root . --expected-commit $env:GITHUB_SHA `
  --auth-success-archive native-android/engine/auth-interop/evidence/auth-success-38996587760/artifact.zip `
  --auth-candidate-stage "$env:RUNNER_TEMP/auth-candidate" `
  --output "$env:RUNNER_TEMP/db-shard-activation"
```

Always upload only `db-shard-activation`. It contains the sanitized receipt and
firewall command logs, including failure/cleanup status. Allow approximately
15 minutes for bounded SQL startup, service readiness and cleanup. This Linux
session recovered and verified the real accepted schema/PE and passed six
new host suites, including realistic service observer/name/path/PID-generation
refusals, success and early/late failure cleanup orchestration, and nonfatal
stream-close failures. The independent C/F review caught and reproduced the
initial misuse of the SQL-only observer before any service execution; its
dedicated replacement is covered by the new real-shaped observation controls.
No Windows service execution is claimed until that new workflow actually runs.

The first actual Windows service execution, run `39068923933` at
`a4cc6b61443cecf6394b0500028277874be6cf82`, refused with
`shard_db_ready_deadline`. Artifact `12114885725` is 5,822 bytes, SHA256
`b47cfea3b2af04634a1802b889010756058bf2211f2ea7ddc87a7bb2342f459e`.
It recorded healthy original SQL bindings, both exact service processes alive,
the required inactive shard before DB start, and complete cleanup. The private
console contained 389 bytes and its fixed SQL-connected marker was present;
readiness, Auth-version and checksum markers were absent. This does not qualify
registration or selected play. It does not establish whether the original
64-worker SQL FIFO initialization, later template/DDL work, or another startup
step was blocked. The original SQL-connected print precedes `sqlFifoInit()`.

On a subsequent actual refusal, `db_startup_diagnostic.py` observes only the
owned DB process and already owned SQL instance before cleanup. It returns user
and attribute-table counts; counts of the original `App=DBSERVER` sessions with
the exact DB PID; active, blocked and waiting request counts grouped into fixed
wait categories; and DB CPU milliseconds plus aggregated numeric .NET thread
state/wait-reason enums. It exports no submitted SQL, account data, provider
messages, window titles, thread IDs or stacks. Same service generation/path/PE
checks surround the observation. Diagnostic failure is recorded without stopping
cleanup. The existing readiness deadline is unchanged, and new allowlisted
template/table/cleanup/launcher console markers export only presence Booleans.
This is diagnostic instrumentation, not a startup or policy fix. `AssertMode
Exit` in servers.cfg controls launched MapServer arguments; the original DB
startup sets its own assertion mode, so this config does not prove absence of a
blocked original assertion UI.

The observed follow-up run `39070610385` (artifact `12115307153`, 6,148 bytes,
SHA256 `f9d3b02dbd3f3661044312fc29ba8c06c46c26e6d21bb769ff6e355e2a5c4889`)
again reached the deadline. Its complete owned diagnostic showed no user or
attribute tables, all 65 original DB sessions sleeping, no active/waiting/blocked
SQL requests, and only nine waiting DB threads with 1,047 CPU milliseconds. Both
service generation observations matched and every cleanup check passed. The
389-byte console had SQL-connected but no template-loading or later marker.
This localizes the failure before template/DDL work and before the expected
64-worker population; the specific assertion or exception is still unobserved.
Both exact runtime refusal archives and the separate pre-service test refusal
are retained under `evidence/db-shard-startup-refusals-20261017`.

A subsequent **failure-only** `db_modal_diagnostic.py` observer reads current
desktop top-level/child controls owned by that exact DB PID. The existing
name/path/start-generation/PE observer surrounds it. Its in-memory C# reader
checks PID before and after each bounded read, uses only WM_GETTEXTLENGTH and
WM_GETTEXT through 100ms `SendMessageTimeout` calls, and stops at eight seconds,
512 enumerated top-level windows, 16 owned top-level windows, 64 owned child
controls and 65,536 total text characters. Individual reads are at most 32,768
characters; the private PowerShell process has a 30-second outer timeout and
1MiB output limit. It never sends a command, dismisses a dialog or modifies UI.

All raw classes, titles, bodies, filenames and stack/extra-info text remain in
private transient storage and are removed with the owned directory. Only fixed
class/status counts and source matches are exported. Twenty-two exception names
come from the exact pinned original SuperAssert table. Assertion matches require
the original `Assertion failed`, `File:`, `Line:` and `Expression:` structure,
a fixed approved source basename/expression, and a verified original source
line. Twenty-one setup assertion IDs cover the observed FIFO/task/ring/allocator
boundary. Unrecognized, incomplete, timed-out or ownership-changed text yields
unknown/unmatched counts, never copied diagnostic strings. Nine original source
hashes and exact current HEAD blobs of the classifier/reader bind this policy.
Observer failure cannot stop cleanup or change a failed stage into success.
This adds observability only: binaries, profile, checksum/version guards and the
300-second readiness bound are unchanged. Absence on the current desktop does
not prove that no assertion exists elsewhere.

Source-body matching is limited to the pinned original `Static` child control
`IDC_MAINTEXT=10`; titles, buttons, edit controls and other IDs stay unmatched.
An unexpected unsuccessful top-level enumeration is an observer failure rather
than evidence of an empty inventory. Bound-driven stops are explicit flags.

Run the new `test_db_modal_diagnostic.py` suite in the focused Windows job before
creating SQL or starting the services. Its Windows-only smoke compiles the exact
C# reader in-process with Add-Type inside a fresh owned PowerShell Job Object,
observes only that benign child's own PID, validates its unchanged process start
ticks and exact PID against the Popen handle, privately admits its result, and
requires Job cleanup. No other PID's text is read. An empty self inventory is
valid. This catches compiler/PInvoke/enumeration/JSON incompatibility before the
five-minute service wait. Host tests also cover timeout/generation/job-cleanup
refusals. The Linux session cannot execute this Windows smoke; its four portable
methods pass and the Windows-only method is explicitly skipped until CI.

```sh
python3 -m unittest discover -s native-android/engine/auth-interop/deployment -p test_db_shard_activation.py -v
```
