# Disposable corrected AuthServer encrypted-login suite

The receive-cursor candidate has now compiled successfully on Windows in run
`38991372131`, artifact `12085517046`, source `234d9c7`. Reuse that exact build;
this service driver never rebuilds it. Candidate PE SHA256:
`9cd262dd862d14bf2d696de65cb70f155f25473503d7fd0968de9969e0ac8003`.
Candidate receipt SHA256:
`25ee2415a280e7b3800808824d95d05b862acca9d4d4879f5fccb5605d6a2451`.

`hosted_auth_login.py --receive-candidate-stage` explicitly selects this isolated
nonshipping executable. The existing unmodified-server route remains available.
The new schema is `coh-hosted-auth-receive-candidate-login-v1`, with separate
candidate launch/start fields. The original-server launch flags remain false in
candidate mode. Both caller-pinned receipt and PE must pass the existing strict
build admission before resources are created, and again before executable copy.
The shipping server, accepted Android apps and account/checksum policy stay intact.

## Reused inputs

Prepare flat artifact directories as specified in `AUTH-ONLY-LOGIN.md`:

- `auth-original-reuse`: original build artifact `12064402579` from run
  `38943674226`. Its unchanged binary is admitted as historical evidence but
  **not executed** in candidate mode.
- `auth-odbc-reuse`: successful SQL/ODBC artifact `12066189514`, run `38948147656`.
- `auth-probe-reuse`: seven-byte-send-cap probe artifact `12076876614`, run
  `38970381430`. Existing exact binary/source/header/generator admission applies.
- `auth-intact-reuse`: run `38974164017` artifact, containing `coh-auth-intact.exe`,
  receipt, four intact build logs, intact CMake cache/project, and
  `intact-openssl-reuse/manifest.json`. Its outer ZIP is 71,999,000 bytes, SHA256
  `aa7a1badbeb8926cec15009f7f87ebb797aa2345c0c97a183cd1e23866a3499b`.
  `intact-build-reuse-pins.json` binds all nine admitted files, the historical
  source generation, every transitive local source/header and all three project
  generator/build functions. The generated fixture-header identity includes the
  original Windows text-mode CRLF translation. The normal-send probe PE SHA256 is
  `7cb5672c32c1d304efea9590366250437687e3b0c8c1fafae5e4ec7cf536f29c`.
- `auth-receive-candidate`: the already-qualified corrected server artifact above.

No OpenSSL build/download or library relink occurs. The normal probe's retained
crypto manifest binds its original OpenSSL source and linked static-library
identity; the currently executed immutable probe bytes are independently pinned.
The library itself is not loaded from the artifact or executed separately. The
prior failed service receipt conveys no real-login qualification.

Use a fresh `windows-2025-vs2026` hosted runner, Python 3.12, original required
ODBC17 x86 DLL/LocalDB version and active firewall. Set `core.autocrlf=false`
**before checkout**. Do not pass `--intact-baseline` or `--openssl-archive` in
candidate mode; exact reuse is mandatory.

```powershell
python native-android/engine/auth-interop/deployment/hosted_auth_login.py `
  --source-root . --expected-commit "$env:GITHUB_SHA" `
  --output "$env:RUNNER_TEMP/coh-auth-candidate-login" `
  --reuse-auth-stage "$env:RUNNER_TEMP/auth-original-reuse" `
  --reuse-odbc-stage "$env:RUNNER_TEMP/auth-odbc-reuse" `
  --reuse-probe-stage "$env:RUNNER_TEMP/auth-probe-reuse" `
  --reuse-intact-stage "$env:RUNNER_TEMP/auth-intact-reuse" `
  --receive-candidate-stage "$env:RUNNER_TEMP/auth-receive-candidate" `
  --candidate-receipt-sha256 25ee2415a280e7b3800808824d95d05b862acca9d4d4879f5fccb5605d6a2451 `
  --candidate-binary-sha256 9cd262dd862d14bf2d696de65cb70f155f25473503d7fd0968de9969e0ac8003
```

## What the real run must establish

The driver creates one uniquely owned disposable LocalDB/schema/account, checks
its SQL process identity, and calls the existing numeric x86 ODBC observer before
AuthServer launch. It observes three independent connections plus a process-ID
query, separately from the internal AuthServer pool. A fresh observation also
runs during listener readiness and after all owned listeners appear. At the
90-second listener deadline, it retains an explicit deadline flag, last numeric
listener ports/poll count and one final independent ODBC observation. Each ODBC
child has its existing 50-second bound; timeout diagnosis may add that bounded
interval after the listener deadline. Driver errors never export credential SQL,
configuration, raw logs or ODBC exception text.

After readiness, the exact seven-byte probe and the exact 1024-byte-cap probe
each execute all four cases: encrypted valid account plus complete empty shard
list, wrong password/reason 3, missing account/reason 2, and corrupted encrypted
frame refusal. Every case requires the original strict numeric native receipt
and surviving PID-owned listeners both before and after execution. Results stay
separate by delivery schedule. Any later failure retains a proven positive
exchange independently, but cannot claim the eight-case suite completed.

Complete success also requires owned Job Object termination, listener absence,
firewall deletion, full existing SQL/schema cleanup, private-file removal and
unchanged tracked sources. This remains AuthServer-only: no DbServer, MapServer,
registered shard, selected character, Android or Thor success is inferred. Real
TCP syscall caps do not deterministically control receiver segmentation, so
`general_tcp_segmentation_accepted` remains false. Source-oracle coverage and
real capped-send execution are recorded as separate evidence.

## Local qualification

Seven new host suites passed, including actual candidate and intact-probe
artifact admission, every reused intact-artifact mutation, CLI dependency/refusal
controls, mocked eight-case schedule execution, lost-ownership refusal,
partial-positive/later-negative handling and private-error suppression. Existing
31 auth-only host suites and release/ASan/UBSan controls still pass: 46 WinSock,
56 original-parser, eight native cleanup and 23 intact-wrapper controls per mode.
The separate seven readiness suites pass. No local control executes Windows,
cryptography against a live service or the admitted PE binaries. Receipts are in
`../evidence/candidate-service-20261017/`.
