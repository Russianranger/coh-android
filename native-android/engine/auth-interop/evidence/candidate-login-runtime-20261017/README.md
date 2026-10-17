# Actual corrected-candidate prerequisite failure

Run [38993564320](https://github.com/Russianranger/coh-android/actions/runs/38993564320)
executed exact source `d949c59fd579bd7256445078cc6aeacc3b331c70`. Linux source
controls succeeded; the Windows account-suite step failed before starting the
candidate. Artifact
[12086206965](https://github.com/Russianranger/coh-android/actions/runs/38993564320/artifacts/12086206965)
is retained byte-for-byte as `artifact.zip`, with its ten original sanitized
files also extracted. The 8,066-byte ZIP has SHA256
`1781e58ffdb870428f0b97284c73f7b2d97312300a8f9528f4e3404c9e93d35d`;
all member CRCs pass. `artifact-identity.json` hashes each exact retained member.

## What actually executed

The four existing candidate/probe/ODBC archives passed reuse admission. No server,
probe or OpenSSL binary was built. LocalDB creation/start, version check, memory
setting, schema installation, owned-PID query and both private known-fixture
SQL commands completed before the required x86 readiness observation. Schema and
fixture outputs were intentionally discarded; reaching the observation means
their subprocesses returned zero, not that raw rows were exported or inspected.

The actual x86 observer reported pointer size 4, one attempted connection, zero
opened connections, no query completion, and successful connection disposal.
Its bounded diagnostic contained two `08S01` / native `233` records and one
`08001` / native `0` record. The driver retained symbolic failure
`candidate_x86_sql_not_ready` and aborted before AuthServer startup.

`candidate_started=false`, the probe-result map and positive-mode list are
empty, and both account-login and authenticated DB/Map flags are false. Thus
this run establishes neither a repaired live receive path nor an encrypted
account exchange. The actual blocker is a SQL prerequisite independent of those
unexecuted operations. No candidate listener or private firewall rule was
created; their cleanup flags describe the uncreated-resource boundary.

The owned SQL process existed before and after the failed observation with the
same PID `6804`, process name `sqlservr`, and UTC start tick identity
`639277996886036331`. Its continued existence did not establish connection
health. There was no AuthServer Job Object to terminate SQL in this run, and no
bounded-command timeout/termination record preceded the failure.

## Cleanup is partly failed

The subsequent independent SQLCMD schema-DROP command returned 1. Its retained
public diagnostic reports the Named Pipes provider's closed-pipe failure, with
communication-link and connection-establishment errors. Owned instance stop and
delete each returned zero. The original aggregate
`owned_localdb_cleanup_complete=false` remains false: successful stop/delete
does not establish that schema DROP ran.

Private temporary-file removal and unchanged tracked source both passed. There
are no raw private AuthServer logs, credential SQL, account rows, packet bodies
or keys in this artifact. The retained SQLCMD failure log contains no fixture
credentials. No subsequent service/workflow experiment was started by this review.

## Source comparison and remaining cause

The previously accepted original x86 ODBC experiment is run 38948147656,
artifact 12066189514, qualified in
`../hosted-odbc-38948147656/`. Its `original-odbc` result establishes a successful
single connection through the source-generated native `SQLDriverConnectA`
harness and unchanged original account conversion methods. Its accepted
x86 ODBC17 DLL is the same exact binary required by this failed run.

`deployment/generate_odbc.py` constructs
`Driver={ODBC Driver 17 for SQL Server};Server=(localdb)\<owned-instance>;Database=cohauth;Trusted_Connection=Yes;Encrypt=No;`
and calls the ANSI ODBC API with explicit 20-second login/connection timeout
attributes. `deployment/auth_readiness.py` constructs the same driver/server/
database/integrated-auth/encryption settings through x86
`System.Data.Odbc.OdbcConnection`. It intends to retain three simultaneous
connections and query only the owned SQL PID; this run failed on its **first**
open, before any three-connection behavior or PID query.

The .NET-managed connection route differs from the historical native ANSI API,
including provider/pooling/API behavior; this is a concrete experimental
difference, not an established root cause. The later independent SQLCMD DROP
also failed, so the evidence cannot safely describe the incident as exclusively
a .NET observer defect. Conversely, the SQL process survived, so neither process
termination nor an AuthServer-owned-job kill explains this run. The precise
server-side close reason was not retained and remains unproven.

The next justified investigation is a separately reviewed SQL-only diagnostic
that distinguishes connection/provider behavior from instance health and
records bounded nonsecret server-side failure classifications. That work must
preserve this failed receipt and cleanup boundary. Neither retrying candidate
login unchanged, raising readiness deadlines, rebuilding known binaries, nor
weakening account/encryption/checksum policy follows from this result.
