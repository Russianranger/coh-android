# Immutable prerequisite for the next authenticated DB/Map driver

`verify_auth_acceptance.authenticated_handoff_prerequisite(root, archive)` admits
the exact completed runtime AuthServer milestone and returns a frozen dataclass.
This is an interoperability qualification record, not an authentication cookie,
account credential or authorization to reuse the stopped historical session.

The factory verifies artifact12087506300 (6,854 bytes, SHA256
`bd04a2baaee03e3d736e3419686849d4e3551770a020c0e321fe49e4d1151d3e`),
all eight exact native receipts and protocol191021, reused server/probe identities,
source generation, fresh x86 SQL health, complete owned cleanup and unchanged
shipping/checksum policy. It replays the retained candidate build admission and
compares every transitive native probe input to Git blobs at the actual executed
source commit `28fe37cc2432db4adbfe047bd07a1e738d6aa754`.

The immutable result contains only public source/binary/receipt hashes, protocol,
tuple source pins and qualification boundaries. Its selected DBID is `None`,
`fresh_authentication_required=True`, `historical_session_reusable=False`, and
`authenticated_db_map_handoff_verified=False`. No password, account row, cookie,
RSA private value or raw packet is retained or manufactured.

```python
from verify_auth_acceptance import authenticated_handoff_prerequisite
prerequisite = authenticated_handoff_prerequisite(source_root, retained_archive)
assert prerequisite.fresh_authentication_required
assert not prerequisite.authenticated_db_map_handoff_verified
```

The next driver must establish a fresh encrypted login under its own live socket
ownership, admit actual shard registration and the nondevelopment version/client
reference policy, qualify the fail-closed DbServer checksum candidate, verify an
actual selected character DBID and then prove AuthServer → DbServer → MapServer
handoff. It must not synthesize these identities from this historical fixture or
acknowledge a character transaction before its full required grammar closes.
Existing accounts and shipping server profiles need no changes to consume this
read-only prerequisite.

Replaying the seal does not start a service or rebuild a binary:

```sh
python3 native-android/engine/auth-interop/deployment/verify_auth_acceptance.py \
  --source-root . \
  --archive native-android/engine/auth-interop/evidence/auth-success-38996587760/artifact.zip \
  --output /tmp/auth-source-binder.json
python3 -m unittest discover -s native-android/engine/auth-interop/deployment \
  -p test_auth_acceptance.py -v
```

The exact historical Git object must be available. A fresh shallow CI checkout
must fetch commit `28fe37cc2432db4adbfe047bd07a1e738d6aa754` before this replay;
absence fails closed. Five host suites cover actual artifact/source/binary replay,
every case/protocol/cleanup scope mutation, wrong negatives and binary pins,
changed SQL generation/connection health, modified archive bytes and immutability.
No fresh AuthServer, DB/Map or Android qualification is inferred from the replay.
