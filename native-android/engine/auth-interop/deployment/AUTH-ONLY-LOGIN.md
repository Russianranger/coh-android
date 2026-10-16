# Exact original AuthServer encrypted account experiment

This continuation recovers the previous worker's unpublished Windows transport,
auth-only profile and probe. Their exact original bytes and prior 46-control
receipt are preserved under `../evidence/auth-only-recovery-20261016/`. The old
worktree survives but its Git metadata points at an unavailable repository. Its
last recovered committed tip is `06c256f771d0b2b794e53b444839f99e455ae397`; the new
integration base is `66146bbee161304ba4e4e14cbb53cba6958fb03b`. No original file was
overwritten during recovery.

The new executable service driver is `hosted_auth_login.py`. Unlike the previously
successful SQL-only stage, it starts the unchanged original AuthServer and attempts
the existing native encrypted protocol against an actual disposable account. It
never starts DbServer or MapServer, supplies no shard, and never changes checksum
or version enforcement. Passing an empty authenticated shard list is a distinct
AuthServer account milestone; it is not complete Gate 26 or a selected character.

## Qualified inputs preserved

- Original AuthServer PE32: 864,256 bytes, SHA256
  `6d4d6a9f16104a8327fb90467f0d00fc1e3fad2a7af17ec839e7a8cfe3094ea8`.
  The exact run 38943674226 build artifact, receipt and logs are admitted by the
  existing `original-build-reuse-pins.json`. The server is never rebuilt.
- Successful original x86 ODBC/schema evidence: run 38948147656, artifact
  12066189514, ZIP SHA256
  `0f032ce2232e0501b47918db55c41a3f35a92fda290252bd18d4c1c9ff209c4b`.
  All ten retained receipt/log identities and their success scope must match.
  The completed SQL-only controls are not repeated. The service experiment does
  create its own fresh SQL instance and install the original schema because its
  account exchange must actually execute the original connection pool and methods.
- Exact original source subtree: `f634e21e230009fa8edc91d15429cd4da69eee8c`.
  The original Config tokenizer/map parser and getters independently parse the
  generated 42-key service configuration. Encryption and RSA password handling
  are enabled, protocol is 191021, queue mode is off, and ordinary paid-account
  policy is retained. Neither FreeServer nor PayStatOverride creates success.
- Qualified ODBC17 x86 DLL SHA256
  `319b6c3b0ab08dd92dc1e5ee6daf3def82503ebbc85944fc1c614cd7a1c7b729`
  and SQL LocalDB `17.0.4025.3` remain required. A changed hosted image/driver is
  an explicit new compatibility dependency, not automatically inherited success.
- Native desktop probe uses the unchanged native login/auth/OpenSSL controller
  sources and an isolated bounded WinSock wrapper. It builds as Windows x64;
  the original AuthServer remains x86. OpenSSL 3.5.9 source SHA256 is
  `603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a`.
  Native Android source and accepted APKs are unchanged.

## Runnable hosted contract

Use a fresh `windows-2025-vs2026` GitHub-hosted runner at an exact clean
`native-android` commit, Python 3.12, MSVC x64, CMake, Perl and enabled Windows
firewall with rule-management permission. Recover these flat artifact directories:

| Directory | Artifact | Outer ZIP bytes | Outer ZIP SHA256 |
| --- | --- | ---: | --- |
| `auth-original-reuse` | 12064402579 | 428036 | `eda726ddc281b2e6b29e8c4d3c0f5e0805f505a8542c0ef80f5dad6208eb570d` |
| `auth-odbc-reuse` | 12066189514 | 872480 | `0f032ce2232e0501b47918db55c41a3f35a92fda290252bd18d4c1c9ff209c4b` |
| `auth-probe-reuse` | 12076876614 | 1437572 | `b02c3f81e6c77aa2c5f48df6f0adefccb88b66fe98624bd6eeebfd631b35d3c7` |

The coordinator validates those archive identities before extraction. The driver
independently validates the expected files and receipts inside all directories.
No prior real-login claim is inherited from any artifact. The third artifact is
the successful probe build from the failed first service experiment described
below; it supplies no executed-probe or completed-service qualification.

```powershell
python native-android/engine/auth-interop/deployment/hosted_auth_login.py `
  --source-root . --expected-commit "$env:GITHUB_SHA" `
  --output "$env:RUNNER_TEMP/coh-auth-login" `
  --reuse-auth-stage "$env:RUNNER_TEMP/auth-original-reuse" `
  --reuse-odbc-stage "$env:RUNNER_TEMP/auth-odbc-reuse" `
  --reuse-probe-stage "$env:RUNNER_TEMP/auth-probe-reuse"
```

A fresh probe build instead omits `--reuse-probe-stage` and requires
`--openssl-archive` pointing to the exact pinned OpenSSL archive. The narrow retry
reuses the probe and does not download, extract or rebuild OpenSSL. Its receipt
explicitly says that the source archive was not revalidated in that run.

Only archive `coh-auth-login/`. It contains bounded build logs, the probe binary,
native numeric receipts, source/binary identities and aggregate cleanup results.
The probe deliberately embeds the publicly known disposable fixture already in
`password_fixture.py`; it accepts only a local port and one of four fixed cases.
It cannot accept user credentials, remote addresses or arbitrary account names.
It never prints password material, cookies, RSA keys or packet bodies. Credential
SQL/configuration and raw server logs live outside the artifact directory and
are removed after the service and SQL instance stop. SQL fixture command output
is discarded because driver errors can repeat account rows.

Original AuthServer binds INADDR_ANY. Before starting it, the driver creates a
uniquely owned Windows firewall rule refusing nonloopback inbound IPv4 addresses
for that exact private executable. The firewall must already be active; the driver
does not alter global policy. It reserves three distinct ports, checks that all
three listeners belong to the exact spawned PID, and places the process in a
kill-on-close Job Object. The standalone profile has no external services enabled.

The native probe limits sends to seven bytes and receives to eleven bytes per
syscall, exercising partial I/O with the real WinSock backend. The four cases are:

1. Valid RSA-encrypted account/password, login response, then complete normal
   empty shard list, with exact protocol and three received frames.
2. Wrong password: original `AC_LOGIN_FAIL`/reason 3.
3. Missing account: original `AC_LOGIN_FAIL`/reason 2.
4. Corrupted encrypted frame: adapter changes the first encrypted payload byte
   exactly once across partial sends; no authenticated list is admitted.

After each probe, its socket, buffered data and retained password must be cleared.
An actual positive exchange is preserved separately if a later negative control
finds a defect, but overall `passed` requires every control, surviving owned
listeners, complete process/firewall/LocalDB/private-file cleanup, and unchanged
tracked source. No success is inferred from listening ports alone.

Build/control commands use existing bounded process/log handling. Readiness is
limited to 90 seconds; each probe has a 25-second external bound and a 15-second
internal limit. Raw private logs have a monitored 16-MiB aggregate bound, not a
filesystem quota. SQL's 256-MiB buffer setting is not a process RSS cap.

## Local evidence and remaining boundary

```sh
python3 native-android/engine/auth-interop/deployment/qualify_auth_only.py \
  --source-root . --sanitize --output /tmp/auth-only-qualification.json
```

Current local result: 31 admission suites; 46 WinSock syscall-shell controls,
56 unchanged-original tokenizer/getter comparisons, and eight compiled native
probe argument/refused-loopback cleanup controls per release and ASan/UBSan run.
The whole Config::Load filesystem/platform/date logic is not executed by the
tokenizer oracle. The POSIX probe tests do not run Windows or an original service.
LeakSanitizer is not claimed. Prior successful x86 SQL/ODBC evidence is reused.

The first hosted run, [38970381430](https://github.com/Russianranger/coh-android/actions/runs/38970381430),
built the Windows x64 probe successfully, installed the exact original schema and
started the unchanged original x86 AuthServer. Source commit was
`41b4f585f90023e06ea2c8e7c50f4d505deb8e4f`. Windows service admission then failed
with `listener_inventory_shape` before any native probe ran. Its complete receipt
and small logs remain under `../evidence/hosted-auth-listeners-38970381430/`;
the exact original artifact retains the executable and 1.6-MiB OpenSSL build log.
The executable is 3,185,664 bytes, SHA256
`454814a2659944cf7958d10d89f2bdf49a7e5a778ad75d941077ef8d17d672ec`.
OpenSSL compilation took 255.359 seconds, so this successful build is reused.

That failure left AuthServer cleanup **unverified** because cleanup also called
the rejected listener projection; SQL, firewall, private-file and source cleanup
checks passed. Do not retroactively turn the failed receipt into success. Empty
PowerShell member projection was the suspected cause. The corrected code projects
each existing pipeline object before building the JSON array, and a real
PowerShell empty/single/three-object control now runs before starting any service.
Only its next hosted result can establish the exact PowerShell behavior. Host
controls reject `[null]`, scalar, Boolean, string, invalid-port and oversized
inventories; they do not claim PowerShell execution. The retry records Job Object
termination and listener absence separately.

`probe-build-reuse-pins.json` binds seven artifact files, all 27 local native,
adapter, profile and fixture inputs (including 15 headers), each exact historical
Git blob, the unchanged generated CMake-project function, generated fixture
header, original OpenSSL source hash, and compile/configuration policy. This
covers the wrapped original login C file, its transitive native headers, every
Windows compatibility header, `/MT`, Windows API defines, static link libraries,
VS18 x64 Release, and OpenSSL VC-WIN64A options. Receipt C-input and profile-input
maps are independently cross-checked after Windows path normalization. No
binary is rebuilt if any source or policy has changed: admission fails instead.
The exact archive passed ZIP CRC and SHA256 checks; seven one-byte artifact
mutations were rejected. See `listener-recovery-host-qualification.json`.

The narrow retry [38972290813](https://github.com/Russianranger/coh-android/actions/runs/38972290813)
ran source `194895e720aa9670a01496bd0f2851e8f1e8f99d`, reused every binary and
completed in the service step in about 38 seconds. Actual PowerShell established
`[null]` from the old empty projection and `[]` from the corrected pipeline; all
three original AuthServer listeners belonged to the spawned process. The native
probe executed against that process, received protocol 191021, sent 170 bytes
using the deliberate seven-byte send cap, then received a reset after 375 ms.
It had one received frame and no login response. The positive case failed;
wrong-password, missing-account and corruption probes were not reached.

This second failure and its exact numeric probe output are preserved under
`../evidence/hosted-auth-fragment-38972290813/`. Artifact 12077123568 is 1,444,434
bytes, ZIP SHA256
`24a1aca2216620b942e2df3baaf5ae886ed06940cf6a41beace4fcae2ee40cf5`.
Its CRC check passed. AuthServer Job Object stop, listener absence, firewall and
private-file cleanup all passed. SQL schema DROP could not reconnect because the
LocalDB prelogin pipe had closed; instance stop and deletion both succeeded.
The aggregate SQL cleanup flag remains false; deletion is not retroactive proof
that schema DROP ran. No raw private service log, account row or key was exported.

A focused source oracle, `qualify_original_receive.py`, compiles the exact
original `CSocketServerEx::OnRead` and `CIOSocket::Read` with bounded platform
fixtures. It proves the original fragmented-body offset defect: `Read(ri-pi)`
compacts the body to offset zero after consuming the header, but the next
`OnRead` decrypts from `inBuf+2`. The decoder-boundary fixture compares every byte
of a deterministic opaque 168-byte body. A complete 170-byte frame and splits
after the first or second header byte match. Every one of the 167 body splits
at positions 3 through 169 and the seven-byte delivery schedule present incorrect
bytes to the decoder. Release and ASan/UBSan each passed 344 checks. The oracle
runs neither cryptography nor a live service, and makes no encrypted-login claim.
The source defect is consistent with the hosted reset; the exact live close
reason cannot be recovered from the intentionally removed private server logs.

```sh
python3 native-android/engine/auth-interop/deployment/qualify_original_receive.py \
  --source-root . --output /tmp/original-auth-receive-offset.json
```

Next diagnostics must keep this failed fragmentation test visible. A separately
labeled normal-send baseline can determine whether the remaining native crypto,
account schema and empty-shard exchange interoperate on loopback, but cannot
qualify arbitrary TCP segmentation. Full transport acceptance requires an
independently reviewed original-server receive fix or other source-proven
resolution; it must not be hidden by changing account/version/checksum policy.
The next owned service run should also record numeric AuthServer exit status,
LocalDB process identity and Job Object process membership before termination to
distinguish a service failure from SQL process cleanup interaction. Existing
receipts do not establish that cause.

Windows compilation, owned listeners, real protocol handshake and AuthServer
cleanup are established. Actual encrypted account login and complete SQL cleanup
remain **pending**. No desktop control establishes Android/Thor qualification.

## Normal-send baseline continuation

The next isolated experiment uses `--intact-baseline`. It retains the exact
historical seven-byte-cap probe and adds `windows/intact_probe.c`, a checked
wrapper around the unchanged original probe translation unit. Only the expected
`coh_win_limits(7,11,fault)` request changes to `(1024,11,fault)`. Unknown caps and
fault values are rejected; no native protocol, credential, return value, server
executable, encryption or version policy is rewritten. The separate project
generator preserves the old generator and its historical reuse hash unchanged.

```powershell
python native-android/engine/auth-interop/deployment/hosted_auth_login.py `
  --source-root . --expected-commit "$env:GITHUB_SHA" `
  --output "$env:RUNNER_TEMP/coh-auth-login" `
  --reuse-auth-stage "$env:RUNNER_TEMP/auth-original-reuse" `
  --reuse-odbc-stage "$env:RUNNER_TEMP/auth-odbc-reuse" `
  --reuse-probe-stage "$env:RUNNER_TEMP/auth-probe-reuse" `
  --openssl-archive "$env:RUNNER_TEMP/openssl-3.5.9.tar.gz" `
  --intact-baseline
```

A 1024-byte syscall cap does **not** guarantee one server receive or prevent TCP
segmentation. The schema is `coh-hosted-auth-only-intact-baseline-v1`, scope is
loopback normal sends, and `receiver_segmentation_controlled` and
`general_tcp_segmentation_accepted` remain false. The fresh baseline runs all four
positive/negative account cases. The exact old binary then retains a capped-send
observation, whether it resets as before or happens to receive a valid login
response under that run's TCP delivery. Neither outcome repairs the proven
original receive defect. An unexpected server exit or lost listener revokes
overall success; an actual positive encrypted exchange remains separate evidence.

The necessary new link requires the pinned OpenSSL build once because no prior
artifact retained `libcrypto.lib`. The original AuthServer and accepted APKs are
not rebuilt. New receipts bind all 27 unchanged inputs plus the wrapper, both
project-generator functions, fixture header, generated CMake project, build
policy, original OpenSSL archive, static library and exact executed output binary.
Built and copied binary identities must match. Crypto source, generated headers,
static library, configuration and per-file manifest are retained for later exact
reuse if their aggregate is at most 128 MiB and 2048 files; a future reuse still
requires independent admission. Ordinary build logs and receipts are retained
alongside that bounded directory.

The same run records the owned SQL process ID obtained from that instance,
process name/start identity, original AuthServer exit status, and the AuthServer
Job Object's bounded process-ID list before termination. SQL presence is checked
again after that Job Object stops. These diagnostics determine whether the closed
SQL pipe is associated with the owned process lifetime; they do not silently
convert a failed schema DROP into cleanup success.

Local qualification passed 31 suites, 23 extracted wrapper controls per release
and ASan/UBSan mode, and the retained 46 WinSock, 56 original-parser and eight
native cleanup controls. The original receive oracle separately passed 344
checks per mode. The new normal-send executable and service baseline remain
pending their exact-source Windows run.

Even after an AuthServer-only success, the complete authentication path still
requires a separately admitted nondevelopment version/reference policy, the
declared fail-closed 16-byte checksum DbServer candidate and full packet/binary
negative controls, actual shard registration, disposable selected-character DBID,
and AuthServer → DbServer → MapServer handoff. The unchanged development-auth
path and all physically accepted APKs remain intact.
