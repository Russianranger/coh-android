# Native AuthServer TCP controller

Opt-in single-owner controller around the accepted authentication serializers,
global Blowfish framing/stream assembler and crypto provider. It uses actual
nonblocking numeric-IPv4 TCP sockets, bounded read/send work, monotonic timeouts,
partial writes, backpressure, cancellation and explicit suspend/close cleanup.
No server address or account is supplied implicitly. Retry requires fresh
credentials. Password bytes are erased immediately after request serialization;
the normalized account identifier and session receipt are retained only for
DB handoff and erased at close. Diagnostics contain state, counts and numeric
failure codes, never credentials, keys, cookies or packet bodies.

The source sequence is protocol hello → source RSA credential request → login
reply → normal shard list → explicit selected shard → play reply. Unsupported
queue-server traffic fails explicitly. The pinned source uses a two-byte
inclusive packet length; unsupported framing is not guessed. A completed play
receipt remains available before a following FIN or coalesced notification,
matching source `authWaitFor(AC_PLAY_OK)`. This controller ends at handoff and
does not monitor account revocation. The owner copies the sensitive receipt,
then closes it. It must also authorize any subsequent DB/Map endpoint.

`CohLoginAuthorization.account_name`, `.play.user_id` and `.play.game_key` feed
the source DB account/user ID/cookie fields. Server version/checksum policy,
auth-user-data and later DB/Map selection are separate explicit inputs; the
controller does not invent them or bypass authentication.

Host tests use real OpenSSL RSA and actual TCP with a **scripted test peer**.
They cover opaque/empty passwords, normalization, fragmented headers/bodies,
short sends/EAGAIN, invalid phase, unsupported packets, errors, malformed length,
partial EOF, timeout, cancel, suspend, play-reply+FIN and coalesced notices,
unchanged failed output and descriptor cleanup. Existing authentication oracles
independently qualify credential/framing bytes. This is not an authentic
AuthServer/database/account session and does not complete gate 26.

Reproduce:

```sh
python3 native-android/engine/login/check.py --source-root . --sanitize \
  --ndk /path/to/android-ndk-r28c --crypto-root /path/to/crypto-build \
  --android-output /tmp/login-android --output /tmp/login-proof.json
```

Android linkage uses the pinned public static OpenSSL provider. Execution and
physical acceptance are separate receipts. No accepted APK, native renderer,
fallback launcher, server database, character or imported asset is changed.
