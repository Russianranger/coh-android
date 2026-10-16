# Strict encrypted AuthServer interoperability probe

This additive opt-in host probe drives the existing **real** `CohLive` owner and
native TCP/RSA/Blowfish, encrypted NetLink, DB character and Map handoff modules.
It adds no mocked transport, injected login receipt, fake-auth fallback, READY,
RECEIVED_CHARACTER or authoritative-world success path. It does not change or
link into any accepted APK. There is no real account authentication acceptance
in this continuation: no compatible authorized AuthServer deployment was supplied.

The new production policy boundary rejects missing/multicast endpoints,
unapproved Map endpoints, unknown DB protocol, version strings the original
server would truncate, unspecified checksums, timeout bypasses, version bypasses,
injected account/user/cookie/auth data, and privileged keyed-access fields.
It forces normal version-5 NetLink encryption for both DB and Map. Explicit
shard, character wire slot and Map endpoint selection are required. A server's
character DBID is never invented from its wire slot.

The real owner supplies AuthServer account/user/cookie only after completing
its existing source-qualified encrypted login and play exchange. Authentication
and selection generations remain owned by that module. This probe ends at the
existing bounded `SCENE_INCOMPLETE` boundary, closes every owned socket and retains
the original terminal phase/status in its report. A structurally received scene
is not authoritative world entry. There is no automatic credential replay or
retry. The probe is for a fresh disposable deployment; its IDs are fresh per
process and do not prove cross-process uniqueness on a persistent production shard.

## Qualification

```sh
python3 native-android/engine/auth-interop/check.py --source-root . --sanitize \
  --probe-output /tmp/coh-auth-interop-probe --output /tmp/coh-auth-interop.json
```

The 2,147 deterministic policy/redaction checks pass in optimized and ASan/UBSan
builds. The checker additionally executes unmodified original DbServer
`authValidLogin`, `trimTrailingWhitespace` and checksum verification bodies
against synthetic cache/checksum values. This verifies matching ID/cookie/name,
case/trailing-space normalization and one-shot cache consumption; it does not
exercise a database or the server's AuthServer-side cache population.

The optional fully linked probe additionally passes real isolated TCP cancellation
and timeout checks, plus invalid-private-input rejection. The test peer sends
**no authentication response**; the client sends no credential request without a
hello. Original terminal failure diagnostics and 1:1 socket cleanup are checked.
The full probe and native modules run with ASan/UBSan when requested; original
source oracle bodies compile separately at O0. No LeakSanitizer pass is claimed.

`--ndk PATH --android-output PATH` builds the exact standalone admission test for
ARM64 and x86_64/API26 and writes per-ABI binary hashes/receipts. It requires no
crypto because it opens no sockets. Android execution is a separate qualification
receipt. The optional full probe is host-linked using public OpenSSL; no full
Android probe executable or physical device test is claimed here. Existing auth
crypto, login TCP, DB and Map original-source checks retain their own scope.

## Controlled real deployment run

Once the operator has prepared and identified a compatible disposable AuthServer,
DbServer and MapServer as described in [SOURCE-AUDIT.md](SOURCE-AUDIT.md), build the
probe above and run the interactive wrapper with **actual approved public policy
values**:

```sh
python3 native-android/engine/auth-interop/run.py \
  --probe /tmp/coh-auth-interop-probe \
  --auth AUTH_IPV4:AUTH_PORT --db DB_IPV4:DB_PORT --map MAP_IPV4:MAP_PORT \
  --shard SHARD_ID --slot EXISTING_CHARACTER_WIRE_SLOT \
  --version EXACT_SERVER_COMPATIBLE_VERSION --checksum APPROVED_CLIENT_CHECKSUM
```

The placeholders must be replaced from the disposable deployment's verified
configuration, not copied from an unrelated server. Credentials are entered into
an interactive private terminal without echo and passed to native code over an
anonymous stdin pipe. Never put them in argv, environment, checked-in manifests,
packet captures or reports. Native temporary credentials are wiped immediately
after `coh_live_begin`; the existing owner wipes its copy after serialization.
Python immutable strings cannot provide a guaranteed zeroization property.

The one-line JSON report contains numeric phases/counts only. Source-pinned
protocol progress is not proof of server provenance, so `peer_identity_verified`,
`real_account_login_verified`, `native_live_world` and `physical_thor_accepted`
remain false in the standalone report even when the protocol reaches its boundary.
Independent identified server evidence and the corresponding native report must
be reviewed together before accepting authentic interoperability. No real login
has been performed by this continuation.

Rollback is omission of this additive directory and its qualification workflow
step; no APK/runtime/server/profile/database modification needs to be reversed.

The [isolated deployment audit](deployment/README.md) now identifies the existing
2019 `Assets/DBSchemas/cohauth.sql` candidate, distinguishes it from obsolete
11-parameter schema patches, and supplies a bounded read-only metadata inspector.
It independently checks source ODBC bindings and the checksum function's 32-/64-bit
object code. These controls do not establish a real SQL connection or login.
