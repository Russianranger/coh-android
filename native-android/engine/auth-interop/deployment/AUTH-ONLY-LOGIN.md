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

The coordinator validates those archive identities before extraction. The driver
independently validates the expected files and receipts inside both directories.
No prior real-login claim is inherited from either artifact.

```powershell
python native-android/engine/auth-interop/deployment/hosted_auth_login.py `
  --source-root . --expected-commit "$env:GITHUB_SHA" `
  --output "$env:RUNNER_TEMP/coh-auth-login" `
  --reuse-auth-stage "$env:RUNNER_TEMP/auth-original-reuse" `
  --reuse-odbc-stage "$env:RUNNER_TEMP/auth-odbc-reuse" `
  --openssl-archive "$env:RUNNER_TEMP/openssl-3.5.9.tar.gz"
```

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

Current local result: 20 admission suites; 46 WinSock syscall-shell controls,
56 unchanged-original tokenizer/getter comparisons, and eight compiled native
probe argument/refused-loopback cleanup controls per release and ASan/UBSan run.
The whole Config::Load filesystem/platform/date logic is not executed by the
tokenizer oracle. The POSIX probe tests do not run Windows or an original service.
LeakSanitizer is not claimed. Prior successful x86 SQL/ODBC evidence is reused.

At this source checkpoint, Windows compilation, actual AuthServer execution and
encrypted account login remain **pending**. The Linux environment has no usable
Windows runtime/SDK; the hosted job is the next exact-source gate. Android/Thor
qualification is not inherited from these desktop controls.

Even after an AuthServer-only success, the complete authentication path still
requires a separately admitted nondevelopment version/reference policy, the
declared fail-closed 16-byte checksum DbServer candidate and full packet/binary
negative controls, actual shard registration, disposable selected-character DBID,
and AuthServer → DbServer → MapServer handoff. The unchanged development-auth
path and all physically accepted APKs remain intact.
