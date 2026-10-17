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
line. Unrecognized, incomplete, timed-out or ownership-changed text yields
unknown/unmatched counts, never copied diagnostic strings. Original source
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
refusals. Run `39072189359` at `81568446e43f56eb1a8aaf0970ab1ede13103f41`
passed that actual Windows smoke and all other 12 pre-service methods. Its
subsequent service attempt still reached the unchanged readiness deadline.
Artifact `12115752164` (7,122 bytes, SHA256
`8acbbeac960d073574a1a902c1b6ba7f1d769d25da167557adb08f4eef730f11`)
confirmed one original assertion body in an owned Static IDC10 control, with
all 12 bounded reads successful and matching service generations. The original
21-expression matcher returned unknown; this identifies an assertion dialog,
not a predicate or repair. Numeric SQL observations again showed no tables or
active requests, and all cleanup checks passed. The exact archive is retained
alongside the earlier failures.

The classifier now indexes all 78 runtime assert call sites in the same nine
pinned original source files. A lexical scan excludes comments and literals,
balances call parentheses/brackets/braces, and extracts the complete first
argument across lines. Invalid or ambiguous lexing refuses the policy; multiple
sites at the same file/line yield a fixed ambiguity enum. A tenth source pin,
SuperAssert.h, binds the original forwarding to `#exp`, `__FILE__` and `__LINE__`.
The original 21 setup IDs remain stable. Other sites use fixed file/ordinal IDs.

The retained exact DbServer PE also contains four macro-expanded expression
spellings: three `INVALID_HANDLE_VALUE` comparisons and `CHUNK_ALIGNMENT`.
Before admission the helper verifies the exact 1,088,820-byte archive, its PE
SHA256 and the presence of every allowed compiled spelling. It builds neither
the PE nor the original server. Source expression matching uses compiler-style
whitespace collapsing outside literals, preserving literal bytes, escapes and
operator boundaries; altered MemoryPool string contents do not match.

Each result independently reports a known file enum, unique-field/line-shape
Booleans, verified call-site enum, source-expression match and compiled-variant
match. A location alone remains `source_assertion_unknown` with no full assertion
match. Unknown filenames, line values, expressions, titles and body text never
leave private storage. The receipt records the fixed 78-site index hash, ten
original source hashes and the retained PE/archive hashes.

Run `39074781897` at `fd213266f1b6665acece877dabb7dab6663e647c` passed
all 17 Windows pre-service methods, including the new index and actual API smoke,
then reached the same readiness deadline. Its artifact `12115784171` is 7,350
bytes, SHA256
`e8d30407df395ec575e831bd1498180eb7a3364b2dd27d723821a95be20b0bb5`.
The complete unchanged-generation modal observation had unique File/Line/
Expression fields and a numeric line shape, but unknown rendered file, site and
predicate. All 12 reads succeeded and all cleanup checks passed. Exact artifact,
member hashes and a fixed test-count/result log projection are retained in the
failure history. No assertion predicate or root cause is identified.

The original SuperAssert.c formatter at lines 1571–1618 shortens File fields to
fit its 60-character line policy and can abbreviate a long basename. A bare
basename lookup can therefore miss an indexed source file. The new policy reads
only exact `__FILE__` candidates from the same pinned PE, requires one candidate
per source file with call sites and verifies its complete original repository
suffix after separator/case normalization. There are eight candidates; the
ninth pinned file, ringchain.cpp, has no call sites or PE candidate. It then
applies the original formatter, including `sizeof(FILEINTRO)=7`, `ffn=52`, strict
branch thresholds and the separator-inclusive suffix count. Only the immutable
exact rendered field can select a source file. Case, path, whitespace or ellipsis
variations do not match; duplicate candidates or alias collisions refuse the
policy. This replaces the earlier basename approximation.

A portable test shell lifts the actual original formatting block and compares
its C99/O2 output against the Python model across 62 inputs, including all eight
retained PE paths, every branch, basename lengths 15/16/17, the 35-character
path boundary, slash/backslash/no-separator forms and the 52/53 and 98/99 length
boundaries. When the original unsigned copy-count arithmetic would underflow,
the bounded model explicitly refuses the candidate; 100/101/1024-character
no-separator controls cover that frontier. This is a model-domain refusal, not
an observed original runtime defect. The eight actual candidates are unaffected.
The C shell builds no server code and is skipped on Windows; the existing owned
Windows Add-Type/API smoke still runs there. Hashes of the fixed formatter block
and compiled-path/rendered-alias index bind the policy without hashing or
exporting any observed GUI field.

All 78 sites are covered by exact rendered-field positives and modified-field
refusals. Location and source/compiled-expression flags remain independent.
Eleven portable modal methods pass with the Windows-only smoke skipped locally;
six affected activation methods also pass, including late diagnostic failure
cleanup. The rendered-file policy has not run against actual services yet. No
root cause, registration, selected play or Db/Map handoff is qualified by this
preparation; binaries, profiles and readiness limits remain unchanged.

Run `39075900631` at `b3fbacf90626e29542e878313c2812eba1e1375b` passed
the three new Linux controls and 19 Windows methods (the portable C oracle was
skipped on Windows), then reached the same readiness deadline. Artifact
`12117415396` is 7,474 bytes, SHA256
`1a98ef8b4788bf2c5a6e2948d17fb9387dd94f8fc0cacaec87ef74dedd4c3a3d`.
The assertion still had unique fields and an unknown rendered filename despite
the eight admitted aliases. Its complete observations and cleanup checks passed.
This exact failure and fixed log projections are retained in the history.

A subsequent finite PE audit found 122 source filename candidates mapping
uniquely to exact upstream files, compared with the eight selected aliases.
Their maximal printable-run catalogue hash is
`f08e6e36bcca6bbf73f7123439f3910ac6898fb9cf1a0001e67b34c51cc1269a`.
Thirteen runs include an adjacent printable `;` byte before the drive path.
The expanded policy binds exact NUL-terminated filename offsets and RVAs in the
retained PE's .rdata section; the 122 upstream literals each have at least one
encoded 32-bit address reference at that start. Their canonical filename
catalogue hash is
`94405b1e0931a6497b17715ede61fdc908aaa2c2f7cd48db47aead972165c4a3`.
No observed field is stripped, case folded, hashed or copied into these indexes.

`db_modal_pe_source_catalog.json` pins all 122 source hashes, literal offsets,
RVAs and reference counts. Four further exact PE paths identify unavailable
Crypto++ source files. They receive fixed opaque external enums and always
remain source/predicate unverified. All 126 original rendered aliases are
distinct and within the model domain. The manifest joins the classifier and
reader in the exact HEAD input guard. Runtime results contain only fixed file
and site enums plus independent verification flags; neither paths nor source
lines are copied from a GUI body.

The 122 pinned sources contain 1,409 lexical assert-family invocations. Their
first arguments pass the existing strict literal/token handling; no two share a
file/line. This source index does not prove which invocations survived the
original compile or can execute in this profile. A separate hashed index records
11 development-only wrapper locations and 17 verify locations. Those 28 can
establish a source location only: neither source nor compiled-expression match
can become true there. All four previously admitted PE expression variants
remain tied to their exact legacy sites. Unknown and ambiguous locations or
expressions remain unverified.

The finite policy limits each filename to 1,024 bytes and their total to 65,536;
each source file to 1MiB and their total to 8MiB; each first-argument literal to
4,096 bytes and their total to 256KiB. The manifest is capped at 128KiB. Exact
counts, pins, candidate uniqueness, source suffixes, alias collisions and model
domain checks must pass before any private GUI observation is admitted. The
actual source total is 3,636,554 bytes. Existing private GUI/process bounds and
generation checks are unchanged.

The C oracle now covers all 126 exact literals plus 54 branch/boundary inputs
(180 cases). Fourteen modal methods run locally: thirteen pass and the actual
Windows API smoke is skipped. They cover all 1,409 source sites, external and
location-only refusal, literal starts, manifest/input identity, byte caps,
modified fields and ambiguity. Six affected activation methods also pass. The
full finite catalogue has not observed a real service yet and supplies no
assertion cause, repair, registration, play or Db/Map handoff qualification.

```sh
python3 -m unittest discover -s native-android/engine/auth-interop/deployment -p test_db_shard_activation.py -v
```
