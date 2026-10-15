# Native integrated authentication/DB/Map owner

This additive single-threaded owner connects the existing native
[AuthServer TCP controller](../login/coh_login.h),
[DB socket session](../dbclient/coh_db_session.h), and
[MapServer controller](../mapclient/coh_mapclient.h). It changes no accepted
transport, crypto, graphics, movement, camera, audio or replication kernel.
It links into no currently accepted APK.

The owner follows this sequence:

1. `begin` uses only the configured authorized AuthServer endpoint and fresh
   caller credentials. Login framing and credential encryption use the supplied
   real crypto provider. Explicit patch/checksum/version fields are preserved;
   there is no fake-auth or checksum bypass fallback.
2. `SHARDS_READY` requires an explicit shard choice. Its exact IPv4 bytes and
   host-order port must match the authorized DB endpoint in the configuration.
   No default shard or arbitrary server-provided endpoint is followed.
3. A completed AuthServer protocol result is consumed internally once. The
   normalized account, `play.user_id` and `play.game_key` populate DB account,
   user ID and game cookie. The owner mints a nonzero monotonic authentication
   generation. No public method accepts an external authenticated receipt.
4. The existing DB controller receives the fresh owned protocol receipt;
   `verified=1` describes this provenance, **not independent evidence of a real
   account login**. The serialized DB request and temporary receipt are wiped.
   Character lists expose only UI records, never the trailing auth arrays.
5. `CHARACTERS_READY` requires an explicit valid existing wire-slot choice.
   The DB handoff must match that slot and a valid selection generation. A DBID
   is not present in the source list/handoff: the owner keeps it zero and rejects
   invented identity. The owner keeps a separate monotonic selection generation.
6. `MAP_APPROVAL` exposes only two public numeric endpoint candidates. The
   caller explicitly selects an address and the configured policy callback must
   approve its exact bytes/port for this authentication generation. The packed
   source IPv4 integer is expanded low byte first, matching
   [the MapServer controller](../mapclient/coh_mapclient.c); AuthServer shard
   IPv4 fields already contain network address bytes and are copied directly.
   Cookies and session secrets never reach that callback.
7. The actual MapServer controller starts native NetLink and the bounded source
   connection/shortcuts/scene sequence. `SCENE_INCOMPLETE` remains explicit for
   prefix-only replication. There is **no LIVE phase, authoritative spawn,
   REQALLENTS/READY promotion or gameplay acceptance** in this owner.

All methods and the policy callback have one owner thread. Android UI/input
threads must enqueue requests. The provider is borrowed for the owner's
lifetime; DB and map sockets use the existing `coh_session_key_exchange` bridge.
The caller selects encryption policy explicitly for its authorized server;
production normal-server tests must use the pinned encrypted profile.

Suspend, cancel, close, timeout or failure closes all owned sockets and wipes
pending policy/auth/handoff secrets. Foreground recovery cannot replay a
password, authorization, selection or cookie: call `begin` with fresh credentials.
Both transport IDs must exceed both IDs used by the previous attempt, remain
nonzero and distinct, and never wrap within the owner lifetime. Cross-process
ID uniqueness remains an application policy. The owner also preserves monotonic
authentication/selection generations across attempts and cumulative socket counts.
Any DB failure, including graceful DB disconnect timeout after map handoff,
conservatively closes the map and requires fresh authentication. This explicit
fail-closed policy may later be relaxed only with authentic server evidence.

Diagnostic output contains phases, statuses, generations and counters only;
no endpoint, account, password, auth arrays, key, cookie, body or server text.
A future full-world READY contract must supply and securely own its actual
password-MD5 requirement: the current login receipt does not contain that value,
and this owner deliberately cannot send READY.

## Qualification

```sh
python3 native-android/engine/live/check.py --source-root . --sanitize \
  --ndk /path/to/android-ndk-r28c --output /tmp/coh-native-live-owner.json
```

The first suite uses clearly labeled synthetic component adapters to exercise
owner admission, exact endpoint policy, secret receipt mapping, explicit choices,
fresh generations/IDs, rejected invented identity, map failure and lifecycle
cleanup. Its adapters exist only in the test build; production has no receipt
injection seam. It does not replace a real socket protocol qualification.

The second suite links **all real modules** and opens an actual isolated TCP
listener, exercising AuthServer connection, suspend, cancellation, timeout and
matched socket cleanup without sending an authentication-success reply.
The native owner, adapters and real-module boundary run with ASan/UBSan.
LeakSanitizer is disabled on the restricted host; descriptor cleanup is checked.
An optional NDK check compiles the owner to an ARM64 Android API26 object;
aggregate qualification separately owns full crypto/module linkage.

Implemented, host qualified and ARM64 object built are separate from a full
scripted Auth/DB/Map socket chain, real authenticated server interoperability,
Android execution, authoritative-world qualification and physical Thor
acceptance. All of those latter claims remain false in this checker.
Source field/layout provenance remains with each pinned underlying module's
source audit and original-function checks. Accepted Session Client 0.3.0 remains
the physically accepted graphics/movement baseline.
