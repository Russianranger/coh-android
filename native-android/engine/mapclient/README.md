# Native MapServer connection controller

This additive Gate25–27 boundary owns the accepted `CohNetUdp` implementation
and sends the original existing-character MapServer connection sequence. It
does not replace NetLink framing, encryption, ACK, reliability, compression or
ordering kernels.

Implemented:

1. Explicit authorization admission with the selected character **slot** and
   caller-owned selection generation; an optional DBID may be supplied only
   when it was learned authentically. The original DB character list does not
   contain a DBID. No slot, cookie, link ID or dummy value becomes a DBID.
2. Source NetLink connection, followed by `CLIENT_CONNECT(cookie,cod,0)` for an
   existing character. UDP peer bytes/port must match one explicit DB handoff
   address. The map link ID, map ID and selected slot remain separate.
3. Full successful `SERVER_CONNECT_MSG` admission, then `CLIENT_REQSHORTCUTS`;
   full bounded shortcuts admission, then `CLIENT_REQSCENE` with the source
   zero stealth bit.
4. Explicit scene/entity **prefix inspection** using the existing replication
   parsers. A known DBID uses `CohRepSession`; an unknown DBID uses standalone
   parsers and keeps that session disconnected. Prefixes return
   `COH_UNSUPPORTED`, with diagnostic counters, and never prove character
   identity, complete entity data, a spawn or a live session.
5. Application timeout, malformed/unsupported input handling, source refusal,
   cancel, reliable disconnect/ACK, socket cleanup and suspend. Reuse requires
   fresh authorization and a different transport connection ID. No background
   replay or automatic authentication retry occurs.

There is no `LIVE` state. The controller does not send `REQALLENTS`, `READY`,
`ACK_FULL_UPDATE` or `RECEIVED_CHARACTER` based on a prefix. It remains in
`SCENE_INCOMPLETE` while complete group and own-entity parsers are pending.
The ordinary NetLink transport ACK remains enabled so that a parser boundary
does not turn into a retransmission loop.

`coh_map_serialize` separately supplies source-layout CONNECT, shortcuts,
scene, all-entities and READY serializers in modern/legacy command profiles
and bitpacked/byteAligned payload modes. The READY serializer requires the
actual password MD5 bytes; its output is sensitive and must be wiped after
queueing. The current controller cannot emit READY. Diagnostic exports never
contain credentials, cookies, keys, raw message bodies or remote error text.

The caller's `authenticated` and `endpoint_authorized` flags are integration
assertions. They are neither an authentication implementation nor evidence of
successful login. They must come from a real authorized AuthServer/DB session.
Set the existing UDP key-exchange provider and encryption policy before
creation; the pinned normal MapServer client requests encrypted NetLink.

## Qualification

```sh
python native-android/engine/mapclient/check.py --source-root . --sanitize \
  --ndk /path/to/android-ndk-r28c \
  --output native-android/engine/mapclient/evidence/host.json
```

The checked-in evidence records 240 original source producer goldens and
29,514 checks, including 10,652 negative cases, in each release, ASan and
UBSan run. Seventeen scenarios exercise actual OS UDP sockets, all six
NetLink profiles, byteAligned/compressed receive profiles, known/unknown DBID
paths, truncated entity prefixes, refusal, timeout, cancellation, disconnect,
suspend, fresh-authorization guards and descriptor lifetime. Peer traffic is
scripted **synthetic source-layout test data**, never a capture or a real
AuthServer/DB/MapServer session.

The native controller also compiles to an Android ARM64 API26 object with
NDKr28c. This is not a linked APK, emulator execution, Thor acceptance,
authenticated login or live-world qualification. Existing accepted renderer
APKs are unaffected.

Add `--android-output /path/to/output` alongside `--ndk` to cross-build the
complete scripted-peer test for both ARM64 and x86_64. The directory receives
`arm64-v8a/test_mapclient_android`, `x86_64/test_mapclient_android`, a
`receipt.json` beside each binary, the generated original-source `fixtures.h`
and `source-oracle.c`, and an `android-build.json` index with binary, source
and fixture SHA256 values. Both executables use API26 and link
the actual accepted UDP, NetLink, compression, replication, protocol and
Blowfish modules. This option builds only; it never runs a binary or upgrades
emulator/device/server acceptance. An authorized external qualification
driver must verify the receipt, execute the matching ABI and preserve its
separate execution result.

Source constraints and oracle boundaries are documented in `SOURCE-AUDIT.md`.
