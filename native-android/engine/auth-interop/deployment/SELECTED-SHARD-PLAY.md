# Original selected-shard play probe

`hosted_selected_shard_play.py` is a separate owned experiment for one fresh
encrypted account login, selection of actual shard 1, and original AC_PLAY_OK.
The native probe retains the received authorization only in memory, wipes it,
closes the session and stops before any DB client login. The shared registration
driver has explicit optional preparation/exercise hooks; its default invocation
still creates no account and sends no client login.

This is prepared source, not a successful runtime claim. Original Windows
registration run `39068923933` stopped at `shard_db_ready_deadline`; the separate
startup diagnostic must establish readiness before selected play can qualify.
No Auth-only negative cases, original server rebuild, crypto rebuild, donor
build, production profile mutation or remote push is part of this scope.

## Original transition and owned fixture

The original Auth `SelectServerPacket` resolves the current logged-in UID and
session, checks shard availability and calls `AccountDB::AboutToPlay`. With
`UserData=true` and queues disabled, it sends the complete 128-byte Auth data and
retains the current client socket. Original Db `handleAboutToPlay` allocates the
current auth entry and cookie and requests game data. Original
`handleRecvGameData` finds that same entry, merges the original Auth masks and
sends AS_PLAY_OK. Auth `ServerPlayOk` resolves that shard/socket and sends
AC_PLAY_OK. The cookie and UID observed by the probe are parsed from this live
response; the driver supplies no network identity or grant.

The stage reuses the existing deliberately known disposable password tool and
unchanged normal paid `user_account` insert in its fresh private database. It
adds one UserData row with all four original 16+112-byte Auth/game columns
explicitly zero initialized. The complete non-NULL widths are checked before
services start and again immediately before selection: the original routines
otherwise zero fill a missing row and still progress, which is insufficient
evidence. No account or credential value is printed, passed on argv, included in
the linked executable, or copied into exported receipts.

The new native owner requires exactly one up shard with ID 1 and advertised
endpoint `127.0.0.1:7000`, protocol 191021, the expected three frames before
selection and fourth AC_PLAY_OK frame afterward, a nonzero returned cookie,
the exact known SQL fixture UID, and matching selected-shard fields. A wrong
nonzero UID, including an exchanged UID/cookie field, is refused privately.
It wipes its local credential, shard
and `CohLoginAuthorization` buffers on every exit. It then closes the unchanged
controller (which wipes its retained session/update/play keys, receive/transmit
buffers and credentials), confirms authorization is unavailable after close,
destroys the controller, and checks its one Auth socket was closed. Only fixed
typed Booleans and numeric counters leave the executable. The receipt itself
does not assert server provenance; the driver establishes exact service PEs,
current generations, original reverse loopback interserver TCP pair, active
shard SQL state and owned DB listener before and after the probe.

Original DB logs can contain generated cookie/UID values. All service log files,
private credential SQL, stdout and probe pipes remain beneath the private owned
temporary directory. Job Object termination, explicit stdin-pipe close, all
firewall and SQL cleanup, directory removal and unchanged source checks are
required before a successful outer receipt. Raw logs, grants and packet bodies
are not uploaded. The receipt admits no extra output keys that could carry them.

## Exact retained crypto and narrow link

Coordinator input artifact `12078663003` is 71,999,000 bytes, ZIP SHA256
`aa7a1badbeb8926cec15009f7f87ebb797aa2345c0c97a183cd1e23866a3499b`.
After safe bounded extraction into a new `retained-intact` directory, the driver
validates its exact 58,665-byte `intact-openssl-reuse/manifest.json` SHA256
`1c1c05eb10132e4d1d172d29a04d36311981e6c7023c7ee388348339c460896b`,
every one of its 384 retained member hashes/sizes, its 105,629,748-byte total,
inventory, original OpenSSL source/build policy and qualified x64 static library
SHA256 `95aec97b796992a58f8745e1bbbc6eac634931420f13b0763d2db57537543698`.
It checks all qualified unchanged login/Auth/transport/header source hashes and
revalidates retained inputs after linking. The outer ZIP hash in the receipt is
explicitly a coordinator-verified historical reference, not a measurement made
from an archive supplied to this invocation.

The only new link uses `windows/shard_play_probe.c`, unchanged Winsock wrapper,
unchanged login/Auth/Blowfish/protocol C, and retained OpenSSL headers/libcrypto.
It uses the qualified VS 2026 x64 Release/static-CRT policy. Neither DB client nor
Map client is linked. Both the helper and new probe must exist as exact tracked
blobs at current HEAD. Normal send cap 1024 is the default; an explicit cap 7 is
available for a separately requested fresh positive experiment. Receive cap 11
is shared by both. These are syscall/application fragmentation controls, not a
claim about TCP packet segmentation or general network behavior.

## Coordinator invocation

Reuse the registration stage's exact corrected Auth candidate input and clean
fresh hosted Windows environment, source history, accepted schema recovery and
committed compiled Db PE. Download and safely extract the pinned retained crypto
artifact once; do not rebuild it or run its old Auth-only executable.

```powershell
python native-android/engine/auth-interop/deployment/hosted_selected_shard_play.py `
  --source-root . --expected-commit $env:GITHUB_SHA `
  --auth-success-archive native-android/engine/auth-interop/evidence/auth-success-38996587760/artifact.zip `
  --auth-candidate-stage "$env:RUNNER_TEMP/auth-candidate" `
  --retained-intact-stage "$env:RUNNER_TEMP/retained-intact" `
  --output "$env:RUNNER_TEMP/selected-shard-play"
```

Upload only `selected-shard-play` on success or refusal: sanitized receipt, new
credential-free executable and public build/firewall logs. Allow the existing
bounded service startup/cleanup plus at most six minutes for the new probe link.
DB login, auth-cache consumption, normal version acceptance, checksum reference
admission and Map handoff remain false. In particular no `Ouroboros.exe` alias,
version override or checksum exception is installed.

The six targeted host methods exercise the new owner across 16 synthetic API
outcomes in optimized and ASan/UBSan modes, strict receipt type/scope refusals,
private pipe and Job cleanup failures, complete UserData guards, exact source
ownership, current service-generation checks around the probe and narrow link
inputs. The synthetic shell does not establish encryption, SQL, cookie provenance
or service success. Shared activation orchestration separately covers successful
optional exercise, refusal and cleanup. No real login is claimed by host tests.

```sh
python3 -m unittest discover -s native-android/engine/auth-interop/deployment -p test_selected_shard_play.py -v
```
