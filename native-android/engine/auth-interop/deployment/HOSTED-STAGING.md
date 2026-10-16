# Disposable hosted AuthServer staging

The exact original source can be built on a fresh `windows-2025-vs2026` runner.
The original AuthServer target already compiled in the preserved upstream run,
but there is no currently recoverable AuthServer binary artifact from that run.
This candidate builds it again without changing any accepted APK or server.
The executable staging tool is **not yet Windows executed or ODBC qualified**.
Its Linux qualification covers source extraction, admission and checksum policy
controls only. It does not start AuthServer or attempt a real login.

## Verified inputs and feasibility

| Input | Identity / observation |
| --- | --- |
| Imported original source | Commit `0b75ade0c801735e10c5798f641948a45cc50488`; subtree `f634e21e230009fa8edc91d15429cd4da69eee8c` |
| Prior original AuthServer compile | [Upstream run 35934567567](https://github.com/Thunderspies/CityOfHeroes/actions/runs/35934567567), job `107428594341`, OptDebug Win32; preserved `docs/local-completeness-evidence.json` contains the AuthServer output line |
| Prior run artifacts | [Artifacts API](https://api.github.com/repos/Thunderspies/CityOfHeroes/actions/runs/35934567567/artifacts) returned `total_count: 0` on 2026-10-16; no binary identity is invented |
| Existing reference packages | `tools/package_reference_runtime.py` packages DbServer, MapServer, CityOfHeroes, TestClient, pig and Launcher, not AuthServer |
| Public upstream release examined previously | `v2i3/CoX-OptDebug-Win32.zip`, SHA256 `443523af489e3c60f2bed352e3b4fab4dd0103338c3e1649000d2109a24c1b74`; source `3724da475a470926b006dbf73e2e21fd0e7ec856`, no AuthServer, unsuitable source identity |
| Hosted image feasibility | [Official VS2026 image inventory](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-VS2026-Readme.md), observed image `20261007.264.1`, blob `1160761b05c9ea544eb270f6e3cd07a0d58892cd`; includes VS18/CMake4.4.4, MSODBC.SQL, MSSQL.CMDLnUtils and SQL.LocalDB.Runtime components |
| Original account schema | `upstream/ouroboros/Assets/DBSchemas/cohauth.sql`; decoded UTF8/LF SHA256 `d18756ba04f9f16d40a5f6d55772d19ed430a6438316327aa51fde818a349cbf`; exact tracked bytes retained in staged source |
| Crypto dependency | Original `cmake/dependencies/CryptoPP.cmake` pins `weidai11/cryptopp` commit `b5242667a24e3db8e4600e77b2e502ef204e5280` and checked-in CMake patch |

The image inventory is an availability lead, not proof of a running SQL instance
or installed x86 driver. The runner checks those actual components. No production
endpoint, profile, account, secret or user-supplied credential is required for this
stage. Network downloads are only the original CMake build dependencies.

## Run contract for coordinator-owned CI

Use a clean checkout at an exact `native-android` commit on a fresh GitHub-hosted
Windows runner. Do not reuse a self-hosted runner. The coordinator owns workflow
creation and dispatch; this directory changes no workflow.

```powershell
python native-android/engine/auth-interop/deployment/hosted_auth_stage.py `
  --source-root . --expected-commit "$env:GITHUB_SHA" `
  --output "$env:RUNNER_TEMP/coh-auth-staging"
```

Archive `coh-auth-staging/receipt.json`, logs, source controls, patch and executable
hashes/binaries even on failure. The directory must not already exist. Source is
copied from the exact pinned Git subtree using `git archive`; the checkout and
accepted runtime are never patched. Build commands have 15/25-minute bounds,
control commands have 30–180-second bounds, and each logfile has a monitored
64-MiB cutoff plus a final size check. Excess output fails even if the process
exited between polls; a declared 64-MiB prefix is retained after child exit. This
is not an OS disk-write quota. Timeout handling attempts to kill the owned process
tree, then waits for the child, with a direct-child fallback. Receipts distinguish
attempted termination from observed child exit; a failed tree termination cannot
prove descendant cleanup and remains failure. The SQL memory
setting is 256 MiB for the new instance; this is SQL's buffer-pool setting, not a
total process RSS or Windows memory cap. No runtime speed claim follows.

The sequence is:

1. Refuse non-Windows, non-hosted environments, dirty inputs, source-tree or
   commit mismatches, and existing output locations. Verify all source pins.
2. Build the **unchanged** original AuthServer target using VS2026 Win32 and
   OptDebug. Record its exact SHA256 and limited PE header identity. Do not run it.
3. Compile and execute original/corrected checksum-policy controls as x86
   executables. The corrected policy remains a separate generated patch and
   test function; no patched DbServer is built or deployed here.
4. Create a fresh random, previously absent `cohauth-ci-<96-bit hex>` LocalDB
   instance. The only SQL endpoint accepted is that named local instance, with
   Windows integrated authentication. SQL uses a per-user local pipe and
   `Encrypt=No` for this driver experiment; this does not configure AuthServer's
   game protocol or qualify encrypted account login. Run the unchanged original
   `cohauth.sql` in that instance. Do not apply legacy patches afterward.
5. Seed only deterministic ODBC fixture rows, containing a byte-pattern password
   field and no supplied login credential. Compile and execute unchanged original
   `CAccount` constructor/destructor, `LoadPassword`, `Load`, `CDBConn::Fetch` and
   `ResetHtmt`, with original class headers. The statement owner and logger are
   minimal harness shells, not the original server connection pool. Test both
   hash-type outputs, 128 password bytes, salt, all statistics/loyalty/region
   outputs, timestamp conversion and absent-account rejection. Strictly report
   failures; do not turn successful metadata into successful account semantics.
6. Capture critical schema metadata. Always attempt to drop the owned `cohauth`
   database, stop and delete the owned LocalDB instance, including after failure.
   Report incomplete cleanup as failure. The fresh hosted VM is the outer
   isolation boundary; no accepted profile is accessed.

`admit_schema.py` still refuses the known int/tinyint and datetime2 conversions.
A successful real-driver receipt needs review before changing that admission
contract. The runner also checks missing `user_account` behavior: original
`CAccount::Load` does not inspect every output indicator, and `CDBConn::Fetch`
treats errors differently when passed a `nodata` pointer. A failure here is a
source compatibility result, not permission to fabricate an account result.

## Explicit checksum correction and required next gate

`DBServer/src/clientcomm.c::handleLogin` reads 16 checksum bytes and calls
`clientCommLoginVerifyChecksum` before `authValidLogin` checks the real auth-cache
binding. The original helper compares `sizeof(game_checksum)` (4 on Win32) with
the 16-byte static checksum array, then returns zero on inequality. The caller
interprets zero as acceptable. Independently, missing `Ouroboros.exe` makes
`initGameChecksum` set `ignore_checksum=1`. Neither behavior is acceptable proof
of normal checksum policy for the proposed isolated auth deployment.
`AppVersion.c::checksumFile` hashes the entire file using the original MD5
functions. Original Game CMake outputs `CityOfHeroes.exe`, and the existing
reference package does not provide the hardcoded `Ouroboros.exe` name. An isolated
deployment must explicitly stage and identify its approved reference checksum
file; it must not treat a missing file as successful validation.

`checksum_candidate.py` declares a separate nonshipping candidate: compare all
16 bytes and return failure when `ignore_checksum` is set. It preserves the
caller's success/failure polarity. It never modifies the working source. It
executes the original helper and corrected helper against the unchanged first
policy block from `handleLogin`; field getters are synthetic harness functions,
not original packet/crypto execution. Each executable has 135 controls, including
all 128 single-bit checksum changes, zero checksum, missing-file policy, invalid
version, client no-version flag and wrong DB protocol. The original defect is an
expected observation; corrected rejection is a separately named result.

Run local controls with:

```sh
python3 -m unittest discover -s native-android/engine/auth-interop/deployment -p 'test_*.py' -v
python3 native-android/engine/auth-interop/deployment/checksum_candidate.py \
  --source-root . --sanitize --output /tmp/auth-checksum-candidate.json
```

Before an actual account run, the coordinator must build a separately versioned
DbServer candidate with the declared correction and exact original client
`Ouroboros.exe` checksum file; independently verify that checksum and the non-dev
compatible version. Preserve an original/candidate binary pair and patch hashes.
Execute exact original-client/native crypto packet controls with that binary,
including wrong password/account, corrupt encrypted frame, incorrect protocol,
incorrect version, every checksum byte, missing checksum file, stale/reused auth
cookie and DBID binding. Do not omit the checksum file or enable fake auth to
make the test pass. The accepted development-auth path remains unchanged.

Full real login still needs the bounded native probe to execute alongside the
Windows services (the existing probe/socket backend is POSIX; WSL or a Windows
adapter needs independent qualification), a source-qualified generated disposable
password hash/account and region/shard records, and a disposable existing character
with exact DbServer/MapServer provenance. Those are test setup requirements, not
a request for the user's production credentials. The staged SQL fixture is not
that account, and this runner cannot claim encrypted login or DB-to-Map handoff.
