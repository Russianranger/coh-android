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
4. Complete bounded structural inspection of the supported normal `GROUPS`
   grammar, followed by the existing entity prefix boundary. A known DBID
   uses `CohRepSession`; an unknown DBID uses standalone parsers and keeps
   that session disconnected. Structural inspection returns
   `COH_UNSUPPORTED`, with diagnostic counters, while imported assets,
   footer checksums and authoritative character identity remain unresolved.
5. Application timeout, malformed/unsupported input handling, source refusal,
   cancel, reliable disconnect/ACK, socket cleanup and suspend. Reuse requires
   fresh authorization and a different transport connection ID. No background
   replay or automatic authentication retry occurs.

There is no `LIVE` state. The controller does not send `REQALLENTS`, `READY`,
`ACK_FULL_UPDATE` or `RECEIVED_CHARACTER` based on a prefix. It remains in
`SCENE_INCOMPLETE` while the imported group graph and own-entity decode are
pending.
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

The combined local-server app uses a separate loopback-only development guard.
`local_development_authorized=1` requires `authenticated=0`, explicit endpoint
approval and unknown DBID; ambiguous or remote admission fails. It does not
establish AuthServer account authentication. Normal authenticated admission is unchanged.

### Numeric failure checkpoints

The controller retains the last rejected command's normalized numeric ID,
payload bit count, byte-alignment profile, status and parser checkpoint after
socket cleanup. Checkpoints are 0 none, 1 UDP service, 2 next message /
decompression, 3 command decode, 4 connect response, 5 shortcuts, 6 scene
prefix, 7 entity prefix, 8 command queueing, 9 application timeout, and
10 complete normal GROUPS structural inspection. The
first rejected message ends that service call so later messages cannot erase
its checkpoint. This does not relax malformed or unsupported-message policy.

The source command-catalog regression sends all 915 pinned static names over
actual fragmented UDP datagrams in bitpacked and compressed/byte-aligned
profiles. This is a scripted source-layout peer; it is not a server capture
or authenticated live session.

### Bounded owned GROUPS inspection (0.1.6)

The Map role now explicitly opts into the transport's owned decoded-message
API with a **4 MiB** decoded-body budget before connection. Wire frames,
sibling storage, ordinary receive messages, and DB/Auth roles retain their
existing limits. A decoded body is borrowed for one synchronous inspection
and released before another receive; refusal/close also invalidates the
lease. Large non-GROUPS messages fail with `COH_LIMIT`. A valid large GROUPS
prefix still returns `COH_UNSUPPORTED` and remains `SCENE_INCOMPLETE`.

`last_decoded_bytes` records the inspected body's actual byte count, while
`scene_decoded_bytes` changes only after a valid GROUPS prefix. The transport
adds bounded numeric decode receipts and current/high-water ownership counts.
These diagnostics retain neither message bodies nor credentials. The decoded
bytes are not proof that the unparsed group tail is valid.

The large-body fixture is a 128 KiB decoded body beginning with the pinned
original BitStream writer's GROUPS prefix. Its appended data is an explicitly
synthetic, unparsed tail. The compressed wire body remains below 16 KiB but
spans multiple actual UDP siblings. Tests exercise nonstream and ordered
streaming profiles, known/unknown DBID inspection, unsupported large commands,
over-budget declarations, truncated zlib input, wrong-state delivery, and
close/suspend/cancel/disconnect cleanup. The Android qualification-only peer
uses the same fixture and marks `large_body_fixture=true`,
`scene_tail_parsed=false`, and `real_server_interoperability=false`.

No complete scene/entity parser, authoritative spawn, AuthServer login, or
live-world acceptance is established by this change.

`evidence/scene-owned-016-host.json` records 31,007 checks, 10,661 negative
cases and 29 actual-socket scenarios in each release, ASan and UBSan run.
Complete ARM64 and x86_64 API26 test executables were cross-built; that receipt
does not claim Android execution or physical Thor acceptance.

### Complete normal GROUPS structural inspection (0.1.7)

After accepting a valid source prefix, the Map role synchronously calls
`coh_rep_groups` on the complete borrowed body. The decoder traverses normal
group-file definitions, child and root transforms, material/trick fields,
properties, removals and the four-field footer through the exact logical end.
It retains no strings, matrices or input bytes and allocates no graph. The
transport lease is released on every inspection result before receiving
another body.

`scene_structures` counts completely inspected supported messages.
`scene_inspection` retains bounded numeric counts, consumed bit positions and
the source footer values from the most recent success. Failed inspection
preserves that receipt and updates only `scene_failure` with numeric parser
stage, status and bit offset. The new fields reset on a fresh begin and
remain available after cleanup. Footer CRC values are observed, never
validated against a resolved asset graph.

A supported malformed normal tail fails the local session and closes its
sockets. Base/raid grammar and other unsupported extensions retain
`SCENE_INCOMPLETE` with a specific numeric failure receipt. Even complete
normal structural inspection remains `SCENE_INCOMPLETE`: no application
READY, REQALLENTS, full-update acknowledgement or selected-character spawn is
sent. Normal NetLink transport acknowledgements remain unchanged.

Qualification fixtures come from the pinned original producer and original
BitStream implementation. The large fixture now contains complete meaningful
normal grammar rather than the historical 0.1.6 unparsed synthetic tail.
These controlled peer fixtures are not server captures or evidence of an
authenticated/live-world session.

`evidence/groups-structure-017-host.json` records 31,480 checks, 10,665
negative cases and 33 actual UDP scenarios in each release, ASan and UBSan
mode. The complete fixture has 139,794 decoded bytes / 1,118,352 bits and
3,575 compressed wire bytes. Independent source expectations cover 192
definitions, 384 children/properties/swaps, four roots, 194 raw matrices and
194 packed matrices. Both Android ARM64 and x86_64 API26 complete Map test
executables were cross-built; this evidence does not claim execution on
Android or a new physical server result.


The additive per-call validated GROUPS observer is documented in `evidence/scene-observer-20261017/BOUNDARY.md`. It preserves exact borrowed body representation for future bounded graph correlation, without changing the default controller or its SCENE_INCOMPLETE/ACK boundary.
