# AuthServer deployment and original-source policy audit

All references are to repository-owned original source at `fbc1aa0718`; complete
LF-normalized file hashes are in `source-pins.json`. They are source observations,
not assertions about an already deployed binary or unseen server configuration.

| Original source | Required policy or boundary |
| --- | --- |
| `AuthServer/src/Config.cpp`, `.h` | Two-byte inclusive framing (`PacketSizeType=3` internal convention), explicit Encrypt/DesApply/protocol, ODBC connection string; normal shard lists require queue-server mode disabled for the currently supported client path. |
| `AuthServer/src/SocketServerEx.cpp` | Real global encrypted framing, RSA 1152-bit hello/key policy and 94-byte credential plaintext; secure login requires `DesApply`; source login/read list/play are separate phases. |
| `AuthServer/src/Account.cpp`, `DBConn.cpp` | ODBC `SQLDriverConnectA`; account password retrieval via `dbo.ap_GPwd`, account/stat load via `dbo.ap_GStat`, region load via `get_server_groups`. SHA512/legacy password formats are account DB state, not a fabricated client receipt. |
| `AuthServer/src/schema` | SQL Server/T-SQL tables/procedures and versioned patches including server-group support and 128-byte user-data expansion. PostgreSQL character storage alone does not implement this service. The checked-in base schema plus patches must be reconciled against the exact deployed schema; blindly rerunning ALTER scripts is not authorized. |
| `DBServer/src/clientcomm.c`, `handleLogin` | Exact DB protocol `20110614`, 128 test-auth bytes ignored in real auth mode, version copied into 100-byte buffer, checksum then version policy, and `authValidLogin` unless `fake_auth` is enabled. |
| `DBServer/src/authcomm.c`, `authValidLogin` | Nonzero auth ID, exact game cookie, case-insensitive account identity after trailing-space trim, server-owned auth/loyalty/pay data and one-shot cache consumption. A client-supplied cookie by itself is insufficient. |
| `Common/ClientLogin/clientcommLogin.c` | Checksum policy has the source defect documented below; do not infer checksum enforcement from sending a checksum or successfully logging in. |

The native AuthServer parser supports only its explicit implemented protocol set:
0/global 30810, reactivation 100903 and Ouroboros 190516/191021. Asia/USA or future
versions are not guessed. The actual hello selects the implemented protocol
branch; this probe does not impose a narrower single-version pin. Record and
check the deployment's configured protocol independently. Current normal list
support does not establish queued login interoperability.

## Source checksum defect found during this continuation

The original function is declared
`clientCommLoginVerifyChecksum(U32 game_checksum[])`. Its parameter is a pointer
in C, but it first compares `sizeof(game_checksum)` with the size of a four-U32
array. On the selected Win32 source target (4-byte pointer), and on the current
64-bit host (8-byte pointer), those sizes differ from the array's 16 bytes and the
function returns zero before comparing values.

The original caller in `DBServer/src/clientcomm.c::handleLogin` treats **nonzero**
as a bad checksum and replaces the received version with a rejection marker.
Thus this pinned source path cannot supply checksum-derived rejection, while
its subsequent patch-version comparison and real `authValidLogin` remain intact.
This is **not demonstrated authentication bypass, a deployed vulnerability,
or evidence that any current shipped binary contains exactly this behavior**.

The unchanged-function oracle reproduces zero for both matching and mismatching
checksum arrays with `ignore_checksum=0`. No server code was repaired or runtime
policy changed. The new client probe still requires an explicit nonzero checksum
and prohibits its own version bypass flag. Actual qualification must separately
record trusted source, executable, config and checksum identities. A server
checksum correction requires an isolated experiment and matching negative
qualification, not a silent modification of the accepted runtime.

## Deployment blocker and next concrete setup

The current executor exposes C/C++ compilers but no Wine, SQL Server command
client, PostgreSQL client, container engine or MSVC runtime in its command path.
No authorized AuthServer endpoint, disposable account credentials, matched
AuthServer/ODBC account database, or proof that the AuthServer has registered the
DbServer was supplied. Host process inventory is incomplete (`ps` fails); this
is not proof that another inaccessible agent/environment is inactive.

A compatible test environment needs:

1. Exact matching Windows AuthServer/DbServer/MapServer binaries and source IDs,
   under an authorized Windows or separately qualified compatibility runtime.
2. An isolated SQL Server-compatible account DB and verified ODBC configuration,
   account password/stat/region procedures, schema version and server registration.
   The accepted local PostgreSQL `UseFakeAuth` profile remains untouched.
3. Explicit real-auth DbServer policy (`UseFakeAuth 0`), matching auth protocol,
   encrypted public client policy, normal shard-list behavior, matching version
   and recorded approved executable checksum. Verify endpoints advertised by the
   shard list and both Map candidates before authorizing the probe.
4. A pre-existing disposable account/character whose DB identity can be checked
   independently in the subsequent entity state. Do not copy the accepted Thor
   player's saved profile/database into an experimental auth service.
5. Sanitized server-side session evidence plus this probe's numeric report,
   identified runtime/config/schema hashes, exact native binary hash, and proper
   socket cleanup. Do not retain credential/secret packet bodies, auth arrays,
   password hashes, cookies, session/update keys or raw verbose AuthServer logs.

AuthServer's existing verbose/debug messages can include account/challenge data;
set up suitable log redaction before recording a real test. Merely inventing an
AuthServer-success peer or changing local UseFakeAuth cannot meet this boundary.

## October 16 deployment continuation

The expanded [source and schema audit](deployment/README.md) also checks
`Assets/DBSchemas/cohauth.sql`, which is in the repository tree even when hidden
by sparse checkout. It supplies the current 13-parameter `ap_GStat` and loyalty
columns; the older `AuthServer/src/schema/patch_2.sql` supplies only 11. The
existing 2019 candidate therefore avoids inventing a new account schema.
Its `int` hash-type output and `datetime2(3)` timestamp still require actual
x86 ODBC conversion tests against the original bindings. The read-only metadata
inspector refuses these unqualified conversions and never claims a complete
schema/login from column/parameter shapes alone.

An independent object experiment compiles the unchanged original checksum
function for 32- and 64-bit x86 and verifies an unconditional-zero return with
no `memcmp` reference. These generated experiment objects are not the deployed
DbServer binary. Source, version/checksum policy and login acceptance remain
distinct; neither checksum policy nor production source was changed.
