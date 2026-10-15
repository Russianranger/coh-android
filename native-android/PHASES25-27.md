# Gates 25–27: native session continuation

This batch advances the native engine libraries while keeping Session Client
0.3.0 and the conventional launcher/client unchanged. No new gate is accepted
as a live client milestone. The [recovery record](RECOVERY-20261015.md) identifies
the actual recovered stopping point and preserves the physical-test handoff.

## Implemented boundary

| Gate | Implemented in this batch | Still required to complete the gate |
|---|---|---|
| 25 — real native networking | Nonblocking IPv4 UDP owner with strict peer/truncation checks, bounded service, retained backpressure, cancellation, timeout, reliable disconnect and fresh-link foreground recovery. Optional source encrypted negotiation; clear CLIENT_ACK, receive decryption after derivation, transmit encryption after final ACK. Existing frame, Blowfish, ACK, ordering and zlib kernels are preserved. | Original controlled-server exchange, exact server profile/version/cookie compatibility, measured loss/reorder/disconnect behavior and required unsupported controls. Android app lifecycle/permission wiring and Thor network execution. |
| 26 — authentication and character handoff | Exact source DH group with validated crypto-provider contract; OpenSSL 3 host implementation; global AuthServer framing/checksum/TCP assembly, source credential derivation/RSA-OAEP envelope, hello/login/play/shard parsing, selection serialization and packed/byte-aligned map endpoint handoff parsing. | Audited Android crypto provider, AuthServer TCP socket/session integration, complete DB login serialization/version/checksum policy, character list/selection and real authenticated handoff. No account login has occurred. |
| 27 — first native live world | Source command IDs and legacy remap; complete connect/shortcut parsing; bounded scene/update prefixes; source quantized position and physics substructure kernels; schema invalidation across reconnects. Unsupported entity/scene tails remain explicit. | Complete bounded scene/entity/character decoding, selected-character identity and authoritative initial pose, render spawn handoff, live controller/camera integration and genuine MapServer evidence. No mock-backed spawn is exposed as a live session. |

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

## Qualification

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
| New Thor acceptance | Pending; gates 22–24 still require the unchanged 0.3.0 test |

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
2. Supply and qualify a vetted Android crypto provider behind `CohAuthCrypto`,
   independently of DB/character serialization work.
3. Implement the complete DB login and character-list/selection path from the
   pinned source, honoring server checksum/version rules without weakening them.
4. Extend bounded scene/entity/character tails and selected-character pose
   validation. Only then bridge authoritative state to the native renderer.
5. Wire audio lifecycle and existing UI/animation frameworks into one coherent
   application path, preserving source assets and existing input/Surface tests.

Streams 1–5 can progress concurrently. Final real login depends on server setup,
crypto and DB/auth integration; real world acceptance additionally depends on
complete replication and render handoff. Ship one consolidated APK once that
integrated behavior can receive a meaningful device test. Until then use the
already qualified [0.3.0 APK/test procedure](session-client/THOR-TEST.md).
