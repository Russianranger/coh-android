# Nonshipping original AuthServer receive-offset candidate

The unpublished `receive_candidate.py` was recovered byte-for-byte from the
preserved `/workspace/scratch/142ad4bc669b/worker-d` tree. Recovery provenance,
original source identities and qualification receipts are in
`../evidence/receive-candidate-20261017/`. No historical tree was changed.
Integration base is `3e8b5c9f5b794b58a66c6d8c62a593b926a10873`.

The isolated source correction changes exactly one call in the source-pinned
`CSocketServerEx::OnRead`: `DecPacket(inBuf+2, ...)` becomes
`DecPacket(inBuf+pi, ...)`. `pi` is the current body's offset: two after an initial
header, zero after `CIOSocket::Read` compacts a partial body, and the running
cursor for coalesced messages. The unchanged parser already uses that cursor for
length bounds, opcode validation and dispatch. Encryption, length policy,
original buffer management and account/checksum policy remain unchanged.

```sh
python3 native-android/engine/auth-interop/deployment/qualify_receive_candidate.py \
  --source-root . --output /tmp/auth-receive-candidate.json
python3 native-android/engine/auth-interop/deployment/receive_candidate.py \
  --source-root . --output /tmp/new-external-auth-receive-candidate
```

The stager requires a nonexistent directory outside the source tree. It writes
the two complete pinned original source files (one modified), an exact patch and
a manifest. It rejects source drift, duplicate application and an existing
output directory. It does not alter or build the shipping server.

Release and ASan/UBSan executions each passed 5,139 controls. They cover all 169
two-part frame splits, send caps 1 through 170 over three frames, 100 deterministic
random schedules, three coalesced frames, every incomplete prefix, invalid
lengths, corrupted opaque bodies and invalid opcodes. The test harness uses the
exact candidate `OnRead` and unchanged original `Read`; platform IO, dispatch and
the decoder boundary are fixtures. The original defective `OnRead` fails this
same suite. The existing original-defect oracle still passes its 344 controls
per mode and retains evidence of 167 incorrect original body offsets.

These controls do not execute cryptography, accounts, Windows IOCP or a real
service. They establish a bounded source correction and retain negative decoder
controls. Wrong-password and missing-account service tests remain pending, as do
patched Windows compilation and real encrypted account login. No general TCP,
Gate 26, Android, Thor or authenticated DB/Map success is claimed. LeakSanitizer
is disabled explicitly.

## Readiness investigation before a service retry

The actual receipt for normal-send run `38974164017` was inspected. It failed
`original_authserver_listener_deadline` after successful AuthServer launch and
probe compilation. The AuthServer process was still alive before owned stop;
the SQL process remained alive before and after that stop and was not a member
of the AuthServer Job Object. This evidence does not establish SQL termination
by that job as the reason for the earlier closed prelogin pipe. LocalDB cleanup
remained false. The private service logs were removed; their five files totaled
217 bytes. Their contents and the exact service close/startup cause cannot be
recovered from that receipt. The selected numeric observations and complete
receipt identity are retained in `recovery.json`.

Before another Windows experiment, independently review the correction and
admit a separate nonshipping patched AuthServer binary with exact source and
binary hashes. Preserve the original binary and seven-byte probe as controls.
Reuse the exact already-built probes and retained OpenSSL library only after
existing identity/source admission; rebuilding crypto is unnecessary if those
artifacts pass admission. Independently probe the owned SQL connection using a
credential-free numeric result before AuthServer launch and again at listener
timeout; record bounded listener inventory, owned process identity, startup
phase and exit status. Preserve the failed deadline receipt. Never export raw
configuration, SQL rows, keys or packet bodies to recover a startup diagnosis.

Only after listener/SQL readiness is explained should the patched disposable
service run the valid, wrong-password, missing-account and corrupted-frame cases
under both normal and deliberately fragmented delivery, followed by complete
owned-service/SQL/firewall/private-file cleanup. No expensive Windows/service
experiment was started by this recovery.

## Minimum/maximum body and state observer continuation

A second exact-function oracle now adds 206 controls per release and ASan/UBSan
mode across 134 delivery schedules. It tests body lengths 1, 2, 167, 168, 169,
4094, 4095 and 4096, including header splits, coalesced/partial frames and mixed
1 → 4096 → 1 messages on one socket. Its deterministic decoder observer verifies
call ordering and per-socket state advancement only after an exact payload match.
This is an opaque logical key counter, not cryptographic key qualification.
Maximum body 4096 has encoded frame length 4098; delivery respects the original
4096-byte receive buffer and exercises compaction before completing that body.
Async IOCP dispatch/refcount execution remains a platform fixture.

## Runnable Windows compilation stage (no service execution)

`hosted_receive_candidate.py` supplies an isolated compile/admission operation.
It requires the same clean pinned GitHub-hosted Windows contract as the existing
original build. It reuses a caller-SHA-pinned Linux release/sanitizer receipt,
checks the source and oracle identities, archives the exact original subtree,
applies the one-call correction only in an external temporary source tree, and
builds the original Win32 `AuthServer` target with its existing OptDebug policy.
It never starts AuthServer, SQL, DbServer or MapServer. It retains the candidate
sources/patch, source archive hash, bounded build logs, CMake cache, PE32 identity
and complete artifact hashes. Its copied binary and the two patched/unchanged IO
source files must retain their exact identities through the build. Owned source
and build scratch is removed by the temporary-directory context.

```powershell
python native-android/engine/auth-interop/deployment/hosted_receive_candidate.py build `
  --source-root . --expected-commit "$env:GITHUB_SHA" `
  --output "$env:RUNNER_TEMP/coh-auth-receive-build" `
  --host-qualification native-android/engine/auth-interop/evidence/receive-candidate-20261017/candidate-qualification.json `
  --expected-host-qualification-sha256 c611112e498e3c18a8a5ebfafcfff3c09ffa75f618273e267f758ba0e7f1b90a
```

After independent review pins the resulting receipt and executable hashes, a
later operation can admit those exact bytes (the admission itself executes no
binary):

```powershell
python native-android/engine/auth-interop/deployment/hosted_receive_candidate.py admit `
  --stage "$env:RUNNER_TEMP/coh-auth-receive-build" `
  --expected-receipt-sha256 <reviewed-receipt-sha256> `
  --expected-binary-sha256 <reviewed-candidate-exe-sha256>
```

Six host suites check exact staging, compile-only commands, host-receipt
mutations, artifact/receipt/binary mutations, and complete mocked compilation
orchestration. The mocked PE fixture is never executed and proves no Windows
compilation. The actual Windows build remains pending coordinator-owned CI;
actual encrypted login remains pending a separately admitted service driver.

## Strict recovered corpus admission and readiness continuation

The later original `auth-isolated` files were recovered without modifying that
worktree. Both compile-input admission and later artifact admission now require
the complete original corpus, exact 5,139/206 control-result shapes in both
release and ASan/UBSan, all mode/binary identities, four source-mutation refusals,
the original-defect regression, and explicit noncrypto/nonservice scope. A
receipt with `passed=true` and missing or altered coverage cannot inherit build
qualification. Recovery provenance and fresh controls are retained under
`../evidence/readiness-recovery-20261017/`.

The independently recovered original startup oracle establishes two concrete
alive-without-listeners branches: a modal database initialization error before
`exit(0)`, and successful initial login followed by a completely empty SQL pool,
which blocks the original `CDBConn` constructor. Fresh release and ASan/UBSan
controls each pass 15 checks. They explain possible control flow, not the exact
historical failed run's cause. The original 90-second readiness bound alone
cannot distinguish these branches from slow initial connection attempts.

`auth_readiness.py` prepares a read-only diagnostic for the *next* coordinator
service experiment. It does not create or start a service/instance. With the
existing disposable `cohauth` schema in place, it uses Windows' x86 PowerShell
and ODBC17 to hold three simultaneous integrated-auth connections (initial login
plus two pool-sized connections), queries only the SQL process ID, compares it
with the owned instance's previously recorded process, and closes all three.
The whole child has a 50-second external deadline; its query has five seconds.
It retains only Boolean/numeric fields and bounded SQLSTATE/native error codes,
never ODBC exception messages, connection rows, credentials or private logs.
The observer does not inspect the actual AuthServer connection pool.

```powershell
python native-android/engine/auth-interop/deployment/auth_readiness.py `
  --instance <owned-cohauth-ci-instance> --expected-sql-pid <previously-recorded-pid> `
  --output <new-readiness-receipt.json>
```

The prepared diagnostic has seven host receipt/command-boundary suites; these
use a mocked child and do **not** qualify real PowerShell, x86 ODBC or SQL
execution. It is intentionally separate from the existing service driver until
the coordinator incorporates observations immediately before AuthServer launch
and at a readiness failure. A healthy observation must not be substituted for
owned-listener readiness, actual account login, AuthServer internal pool
inspection, or SQL schema cleanup. Preserve the original failure and cleanup
flags if a diagnostic itself fails.

The next Windows action remains the compile-only candidate command above, with
the exact unchanged historical host-qualification receipt/hash. Review/pin the
resulting executable and receipt before any service use. No new Windows or
service experiment was executed in this continuation. Reuse original binaries,
probes and OpenSSL after exact existing admission; no crypto rebuild is needed
for this compile-only step. A future service driver must separately admit the
patched binary and retain both ordinary-send and seven-byte-send account cases,
wrong-password/missing-account/corruption refusals, complete cleanup, and the
unchanged shipping-server boundary.
Independent review tightened host-receipt admission to require exact 5,139-control
and 206-control result maps for both release and ASan/UBSan modes, all corpus
counts/bounds, per-execution SHA256 syntax and explicit scope flags. Every result
field has a mutation refusal control, including Boolean/integer substitutions.
Both the compilation stage and subsequent artifact admission apply this check.
The pinned host receipt remains unchanged. On Windows, configure
`git config --global core.autocrlf false` **before checkout** so raw fixture and
qualifier hashes match the admitted Git bytes; the helper fails closed otherwise.
