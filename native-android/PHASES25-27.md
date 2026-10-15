# Gates 25–27: native session continuation

> Gates 22–24 are physically accepted on AYN Thor for Session Client 0.3.0. See [the acceptance receipt](evidence/phases22-24/thor-acceptance-20261015.json). No repeat of this test is required. Historical qualification sections below retain their original timing.

The latest continuation adds the [native AuthServer TCP owner](engine/login/README.md),
[public Android crypto provider](engine/auth/android/README.md),
[complete DB character wire records and UDP session](engine/dbclient/README.md),
[bounded MapServer entry](engine/mapclient/README.md), and an
[original-function NetLink server oracle](engine/session/server-oracle/README.md).
The [integrated session owner](engine/live/README.md) now joins those stages,
requires explicit shard/character/map choices and fresh credentials after
interruption, and keeps diagnostics free of account and session secrets.
The combined ARM64 library links the public crypto provider. Source/host,
ASan/UBSan and both Android ABI test builds pass in the
[local aggregate receipt](evidence/session-live-20261015/local/qualification.json).
That local receipt explicitly records a dirty working tree; clean hosted source
and actual Android execution are separate qualification steps. No new APK or
actual authenticated server session follows from these library tests.

These changes advance the native engine libraries while keeping Session Client
0.3.0 and the conventional launcher/client unchanged. No new gate is accepted
as a live client milestone. The [recovery record](RECOVERY-20261015.md) identifies
the actual recovered stopping point and preserves the physical-test handoff.

## Implemented boundary

| Gate | Implemented in this batch | Still required to complete the gate |
|---|---|---|
| 25 — real native networking | Original pinned NetLink handlers now serve actual encrypted/clear UDP oracle exchanges across versions0/2/4/5, including lost CONNECT, ACK retirement, malformed input and cleanup. Nonblocking IPv4 UDP owner with strict peer/truncation checks, bounded service, retained backpressure, cancellation, timeout, reliable disconnect and fresh-link foreground recovery. Optional source encrypted negotiation; clear CLIENT_ACK, receive decryption after derivation, transmit encryption after final ACK. Existing frame, Blowfish, ACK, ordering and zlib kernels are preserved. | Complete authorized server-binary exchange/capture, deployed profile/version/cookie compatibility, wider loss/reorder behavior and required unsupported controls. Original-function oracle coverage does not qualify a full server deployment. Android app lifecycle/permission wiring and Thor network execution. |
| 26 — authentication and character handoff | Exact source DH group with validated crypto-provider contract; OpenSSL 3 host implementation; global AuthServer framing/checksum/TCP assembly, source credential derivation/RSA-OAEP envelope, hello/login/play/shard parsing, selection serialization and packed/byte-aligned map endpoint handoff parsing. | Public pinned OpenSSL provider, native AuthServer TCP owner, exact DB login/choose serialization, complete bounded character-list parser and DB socket handoff are now implemented and host qualified. Real authorized account authentication, deployed version/checksum policy and authentic character/map handoff remain pending. No real account login has occurred. |
| 27 — first native live world | Native UDP owner for existing-character CONNECT → SHORTCUTS → SCENE entry; source command IDs and legacy remap; complete connect/shortcut parsing; bounded scene/update prefixes; source quantized position and physics substructure kernels; schema invalidation across reconnects. Unsupported entity/scene tails remain explicit. | Complete bounded scene/entity/character decoding, selected-character identity and authoritative initial pose, render spawn handoff, live controller/camera integration and genuine MapServer evidence. No mock-backed spawn is exposed as a live session. |

Worker D additionally supplies an opt-in [audio lifecycle controller](engine/audio/coh_audio_session.h)
for foreground/focus changes, callback lifetime during failed closes, latched
device failures and explicit recovery. Surface loss alone does not reset audio.
The accepted audio corpus and mixer behavior remain unchanged.

## Cross-module integration

[The crypto bridge](engine/session/coh_session_crypto.h) adapts the network key
callback to the authentication provider without a network-to-auth module
dependency. It creates a fresh keypair for each negotiation, publishes results
only after successful derivation and securely wipes temporary private/key data.
Android has no implicitly selected provider. Stock NDK linkage does not make
the host-only OpenSSL backend available on a device.

The combined host contract establishes an encrypted exchange with a synthetic
test peer using actual OpenSSL DH, then dispatches a source-layout connect reply
through NetLink and the replication inspector. It verifies that transport
connection alone cannot satisfy the authorization guard. The explicit authorized
test seam is not an authentication result. Replication intentionally has no LIVE
phase and emits no spawn or ready acknowledgement after accepting only prefixes.

Review corrected authentic AuthServer pooled-buffer padding handling, fixed
provider-span bounds/overlap, admitted source byte-aligned map handoffs and
invalidated stale shortcut schemas across reconnects. Original-function oracles
and failure-output tests cover these corrections. No credentials or secrets are
written to diagnostics.

## Current continuation qualification

| Contract | Executed evidence |
|---|---|
| Android crypto | Public static provider and full test binaries built for ARM64 and x86_64; 80 original credential, 64 independent DH and 140 original framing comparisons; host1,920 checks plus10,000 malformed inputs |
| AuthServer TCP owner | Release and ASan/UBSan each523 checks/11 actual TCP scenarios with scripted replies, partial writes/reads, timeout/cancel/suspend and descriptor cleanup |
| DB records and UDP owner | Release, ASan and UBSan each95,925 wire checks/10,000 malformed cases plus715 controller checks/10 actual UDP scenarios; no invented DBID |
| MapServer entry | 240 source producer golden packets; release, ASan and UBSan each29,514 checks/10,652 negatives/17 UDP scenarios; explicit scene-incomplete stop |
| Integrated stage owner | 229 synthetic adapter checks/9 admission scenarios plus41 real-module TCP checks/3 lifecycle scenarios; ASan/UBSan and ARM64 object build; full scripted socket chain and Android owner execution remain pending |
| Original NetLink peer | 40 unchanged source functions;16 clear/encrypted version/loss scenarios;48 malformed datagrams; fresh DH and original final-ACK flush order |
| Combined engine | ARM64 Bionic/public crypto/GLES/AAudio linkage with no undefined symbols; sanitized host integration passes6 groups |
| Actual shard/login/live world | Pending; no server, account, character or controlled capture available |
| Accepted APKs | No accepted APK rebuilt, reinstalled or migrated |

The test executables use scripted peers or extracted unchanged source functions.
Neither is a complete AuthServer/DbServer/MapServer deployment. Native shell
execution also does not qualify JNI/application permissions or Android Activity
lifecycle callbacks. Complete scene/entity tails, self identity, authoritative
pose and renderer publication remain pending; there is no LIVE state.

## Prior foundation qualification

The individual receipts distinguish implementation, host execution, Android
build, emulator execution, physical Thor acceptance and actual server exchange.
Original-source fixtures are synthetic layout witnesses; no controlled capture
or authenticated server transcript was available.

| Evidence | Result |
|---|---|
| Network host ASan/UBSan | 114,147 core checks; 53,484 negative cases; 27 session scenarios |
| Real OS UDP adapter tests | 886 checks, 49 negatives, 16 scenarios including descriptor cleanup; synthetic peer |
| Authentication source/oracle | 80 full 94-byte credential derivations, 64 independent Python DH comparisons, 140 original-source clean/dirty framing cases |
| Authentication ASan/UBSan | 1,920 checks plus 10,000 malformed inputs; 1,855 portable checks without OpenSSL separately passed |
| Replication release/ASan/UBSan | 73,099 checks per build, 38 source-layout fixtures, 4,300 truncations and 30,000 randomized cases |
| Authentic audio worker qualification | 53,980 checks, 5,000 source comparisons, zero callback allocations; 19 matched lifecycle backend opens/closes and three latched failures |
| Coordinator crypto/transport/replication contract | Synthetic cross-module host integration; see recorded receipt |
| Combined ARM64 | NDK 28.2.13676358, API 26, ELF64 AArch64 with Bionic/GLES/AAudio linkage and no undefined symbols |
| New Android socket runtime | Android 13/API 33 x86_64 passed all 886 checks, 49 negatives and 16 synthetic-peer socket scenarios, including descriptor cleanup. No APK, account, actual shard or ARM64 device execution. |
| Gate 25/26/27 actual server acceptance | Pending |
| New gates 25–27 Thor acceptance | Pending; gates 22–24 are already accepted |

LeakSanitizer task enumeration is unavailable in this execution environment;
ASan memory-access and UBSan checks ran. Explicit socket descriptor and wrapped
audio allocation cleanup checks remain enabled. No LSan pass is claimed.
The clean hosted runner additionally completed its audio checks with LSan
enabled; that job explicitly omitted the recovered authentic audio corpus.
Authentic decoder/mixer parity remains separately recorded by the worker.

The [successful hosted session workflow 38696578546](https://github.com/Russianranger/coh-android/actions/runs/38696578546)
qualifies source `1fa4f080b74846602310ce71c9713eb6471384d4`. Its
[host/ARM64 artifact](https://github.com/Russianranger/coh-android/actions/runs/38696578546/artifacts/11954530644)
and [Android socket artifact](https://github.com/Russianranger/coh-android/actions/runs/38696578546/artifacts/11954686503)
were downloaded and their archive digests independently checked. The hosted
combined ARM64 library is byte-identical to the local library: SHA256
`0c1b6849503de70f4767a1ed9d69f17e7e85e08f2f638b1eb34edc99cb67b5e4`.
The [portable core workflow 38696578514](https://github.com/Russianranger/coh-android/actions/runs/38696578514)
also passed. [Hosted receipts](evidence/session-continuation-20261015/hosted-qualification.json)
preserve exact source, binary, artifact and execution identities.

The first two new hosted attempts failed because the audio check implicitly
used an earlier task's scratch corpus directories. The coordinator now requires
explicit `--audio-codec-root` and `--audio-asset-root` together for that scope;
otherwise it runs explicitly partial source/lifecycle checks. A separate review
also corrected the boundary wrapper to validate the C driver's actual explicit
result fields. Those driver fixes left the native ARM64 library unchanged.
The [driver recovery receipt](evidence/session-continuation-20261015/qualification-driver-recovery.json)
and original hosted error remain alongside the successful evidence.

The unchanged renderer also passed host source equations, real Mesa GLES output
and context recreation, plus ARM64 linkage; the accepted packet and UDP kernels
passed their sanitized regression suites. Existing asset/sequencer/UI suites
passed. The initial aggregate renderer attempt ran while NDK extraction was
unfinished; a follow-up using the complete, absolute NDK path passed. This was
a local toolchain/path setup failure, not a runtime regression. The initial
aggregate failure receipt is retained separately from the successful follow-up.

Reproduce the current combined protocol qualification:

```sh
python3 native-android/engine/qualify_session.py \
  --source-root . --sanitize --ndk /path/to/android-ndk-r28c \
  --output /tmp/coh-session-qualification
python3 native-android/engine/session/android_boundary.py \
  --ndk /path/to/android-ndk-r28c --output /tmp/coh-session-boundary
```

[The dedicated workflow](../.github/workflows/native-session-protocol.yml) repeats
source/host/sanitizer and ARM64 checks, then executes the new x86_64 native UDP
boundary on Android 13. It does not install or rebuild Session Client 0.3.0.
Android shell socket evidence does not qualify application permissions, JNI,
Android lifecycle callbacks, Android cryptography or real server login.

## Next parallel milestones

1. Prepare an authorized disposable matching AuthServer/DbServer/MapServer
   environment and account/character, with source/binary/config receipts and
   redacted control captures. Real AuthServer authentication is a distinct
   prerequisite from the server's development `UseFakeAuth` path.
2. Wire the qualified public Android crypto and session owners into the Android
   application owner/JNI and lifecycle, with explicit endpoint policy and
   foreground reauthentication; preserve the working offline client.
3. Verify the implemented DB login/list/selection against the authorized server,
   honoring checksum/version rules. Source lists beyond the accepted16-KiB
   NetLink reassembly bound remain unsupported; no transport cap was widened.
4. Extend bounded scene/entity/character tails and selected-character pose
   validation. Only then bridge authoritative state to the native renderer.
5. Wire audio lifecycle and existing UI/animation frameworks into one coherent
   application path, preserving source assets and existing input/Surface tests.

Streams 1–5 can progress concurrently. Final real login depends on server setup,
crypto and DB/auth integration; real world acceptance additionally depends on
complete replication and render handoff. Ship one consolidated APK once that
integrated behavior can receive a meaningful device test. Until then use the
physically accepted [0.3.0 APK/test procedure](session-client/THOR-TEST.md) as
regression reference. No repeat is required. The independent newer offline
[support-client handoff](support-client/README.md) remains available in its
separate application package.
