# Native local development session

This additive owner follows the original client's `-db` route against the
existing Android loopback PostgreSQL / DbServer / MapServer stack. It accepts
no password and creates no `CohDbAuthReceipt`. Full AuthServer authentication
and live-world rendering remain separate, unfinished milestones.

The caller must explicitly enable development mode and authorize a loopback
DB endpoint before creation. The bind address and every selected MapServer
handoff must be IPv4 loopback. Remote, wildcard, multicast and ambiguous
local/authenticated entry points are rejected. No discovery or default server
is contacted.

`coh_local_login_policy()` mirrors the current conventional launcher's scoped
`-noversioncheck 1` policy: protocol **20110614** remains mandatory, the native
build is labelled `coh-native-local-development`, Windows executable checksum
and auth-user-data arrays start zero, and timeout bypass remains disabled.
This is a deliberate development version-stamp exception already used by the
local server profile. It is never injected into the AuthServer flow.

`coh_local_begin()` sends initial UID/cookie zero through the distinct DB
local entry point. The first completely parsed player list must supply an
actual nonzero UID; later lists must retain it. No hash or account UID is
fabricated. A selected existing character is identified by its actual wire
slot/name. Selection sends `local_map_ip=0` and `create_location=0`, preserving
the character's saved destination rather than overriding it with Atlas.

The actual DB map response supplies the one-use cookie, map ID and endpoint.
The owner follows a loopback address from that response, using
`authenticated=0, local_development_authorized=1` at the Map boundary.
The unchanged bounded Map parser stops at `SCENE_INCOMPLETE`; no READY,
REQALLENTS, application full-update acknowledgement, invented DBID or rendered
spawn is generated from a scene/entity prefix.

Public DH/Blowfish transport remains available: production integration must
supply the already-qualified `coh_session_key_exchange` callback and public
crypto provider through **both** transport configurations. Development account
bypass does not disable NetLink encryption. There is no encrypted-to-plaintext
fallback.

A single owner thread calls service and every lifecycle method. Suspend,
cancel, close and terminal failures clear identity/cookie ownership and close
all descriptors. Fresh connection IDs, each above both previous IDs, and a
new explicit begin are required on return. The UI character view omits auth
arrays; exported diagnostics contain numeric states and counters only.

## Qualification

```
python3 native-android/engine/local/check.py --source-root . --sanitize \
  --ndk /path/to/android-ndk-r28c --android-output build/local \
  --output build/local-proof.json
```

The checker audits nine original/source-launcher pins, then exercises all real
native DB/Map owners over actual OS UDP against a controlled source-layout
peer. Its character fixture is generated using the pinned unchanged original
bit writer. Release, ASan and UBSan each cover a complete scripted DB-to-Map
entry, nonzero UID adoption, retained saved-destination routing, one-use map
handoff, explicit incomplete-scene boundary, rejection of remote handoffs,
truncation, cancellation, suspend, timeout, retry freshness and descriptor
cleanup. The separate DB suite adds exact original producer comparisons for
four UID-zero/cookie-zero layouts, UID-rebinding rejection and malformed wire
cases.

This is deterministic host/socket qualification. It is **not** a real server,
AuthServer login, physical Thor or complete live-world result. Android build
receipts identify ARM64 and x86_64 executables; device execution requires
separate evidence.
