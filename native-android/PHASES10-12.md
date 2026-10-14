# Phases 10–12: input, audio output and packet framing

Phase 9 is accepted on the physical AYN Thor. Gates 10–12 now have one source-qualified diagnostic app, `org.coh.systemsprobe`, version `0.1.0-phases10-12`. Both ARM64 and x86_64 APKs passed build, lint, ABI, fixture, manifest and signature checks. The Android 13 emulator passed all three engine gates and actual Home/return recovery; the [qualification receipt](evidence/phases10-12/qualification.json) binds those results to the exact tested packages. Physical Thor stick coverage and speaker audibility remain separate device checks.

| Gate | Implemented slice | Qualification boundary |
|---|---|---|
| 10: native input | Source joystick thresholds, key edges/held levels, editor-look angle arithmetic; Android touch, controller and keyboard callbacks; clear on cancel/focus loss | Android stick rate/deadzone is an explicit adapter. Gameplay camera obstruction, character movement, bindings and collision are separate. Physical controller coverage is reported separately from emulator callbacks. |
| 11: native audio output | Authentic recovered headset sound, source memory callbacks and signed PCM preparation, original volume curve, bounded AAudio playback, partial writes, cancellation/close/reopen | Ogg decoding is currently prepared on the host. Native compressed decoding, full mixer, spatial audio and sound catalog are separate. Frame counters do not prove speaker audibility; user confirmation is separate. |
| 12: packet framing | Source LSB-first bitstream and packed integers, restricted packet envelope, Adler32, accepted fixed-width Blowfish, bounded parsing | Offline frames only. The selected profile excludes debug/sibling/ACK/compression/ordering branches. No live server, authentication, command decoding or gameplay synchronization is qualified. |

The accepted Phase 6–9 implementations and original source trees remain separate. Generated audio assets stay outside git and are recovered from pinned release members by CI.

## Source evidence

The input [contract](input/README.md) preserves the original DirectInput integer range and strict thresholds, source key-level behavior, single-wrap angle semantics and source editor look. Host proof compares 96 camera cases, 2,048 key events and 8,004 joystick cases against unchanged source code, then runs 909 native checks with sanitizers. Android normalization, pointer-ID handling, analog rate and deadzone are declared adapter policies. The actual Java adapter passes 43 host checks and a negative control reproducing the missing final-UP direction counter. Real Android evidence requires signed native movement after release and two later settled frames; final-UP movement contributes direction coverage without fabricating MOVE events. The preview is a diagnostic arrow rather than a player or game camera.

The audio [contract](audio/README.md) uses `data/sound/ogg/player/headset_incoming_02.ogg`, 12,930 bytes, SHA256 `82bec697f9e824d192cac90f32a01421e4a3875aada64fc709862bc4d3ae9198`. Exact release member CRC/SHA and bounded ZIP envelopes are checked. Four unchanged original memory callbacks and `ov_read(...,0,2,1)` prepare 44,100 Hz stereo signed 16-bit PCM: 18,168 frames, 72,672 bytes, SHA256 `0e9a0cb2fb36575c890cea7ad8b933a732a7e6c970723e5e198dd00fc578fcd5`. The 64-byte `COHAUD11` envelope yields a 72,736-byte fixture, SHA256 `440361125d7420a1730ecd742271d8b2a67808dffcfa9dc435f2357d59931823`. Host proof checks 40 source gain components, 83 malformed spans and 145,344 PCM scaling components. Playback repeats the clip three times with 0.15-second gaps; the middle clip is quieter. Runtime format, channels, sample rate, submitted/read frames, partial writes, cancellation and object cleanup are recorded.

The protocol [contract](protocol/README.md) pins ten source files and 24 original function bodies. Sixteen source-wrapped plaintext frames compare across 1,736 bytes; 32 clear/encrypted wire goldens and 330 bit cases qualify the derivative. Host sanitizers pass 23,467 checks, including 8,989 malformed cases and 256 unaligned cases; another 12,000 exact-allocation fuzz cases pass. Independent zlib/OpenSSL checks validate checksums/encryption and authenticated negative fixtures. Zero-filled producer padding is selected; incidental original writes into unused backing storage and extra UDP tail bytes are outside this bounded contract.

The [REA-assisted seam receipt](evidence/phases10-12/rea-systems-seams.json) retains raw input/audio/protocol anchors, five import candidates and two bounded candidate function instruction lists from the matching client checkpoint. Decompilation attempts did not complete. The ten original checkpoint files remained unchanged; Ghidra created runtime lock/temp files, which are recorded separately. No target execution, autoanalysis, ownership-check bypass or new source-to-binary function identity is claimed.

## Combined probe

The app verifies pinned audio bytes, executes the three native source checks and records real Android callback transport. Synthetic dispatch is explicitly separated from external touch/key events. Both stick direction masks and device audibility have independent fields. A successful system-engine result requires current checks, two input-view sizes, recreation, actual touch/key callbacks, clear input on pause, cancellation of the specifically active audio run, stop/close, foreground recovery and a fresh complete audio playback. Audio errors cannot be cleared by a later success; obsolete lifecycle work is identified separately. Export is an immutable snapshot taken before the file picker.

The dedicated workflow runs source oracles and malformed-input checks, builds separate ARM64/x86_64 packages, checks ELF/manifest/signature/asset identity and exercises Android13 input, AAudio and lifecycle callbacks. Physical stick motion and speaker audibility remain device evidence.

## Qualified Android evidence

[Workflow 38498917836](https://github.com/Russianranger/coh-android/actions/runs/38498917836) passed from source commit `9b6fb2799ff2ea405e0db0905a44ba8619fd4512`; the separate portable-core workflow also passed. Seven native runs covered three input-view generations and two actual sizes. They executed 6,363 native input checks, 672 source-camera cases, 231 source-gain checks, 224 offline wire cases, 2,310 bit cases, 62,923 malformed cases and 1,792 unaligned cases. Four settled, signed touch gestures generated 30 genuine MOVE samples and complete direction mask 15; six keyboard down/up pairs reached the native adapter.

Two complete AAudio plays submitted and consumed 135,468 frames. The specifically active second stream was interrupted by Home, cancelled, stopped and closed; a fresh full stream completed after resume. Foreground resize/recreate actions used measured, clipped real Button bounds and matched their listener events. Exactly one pause/stop/resume Home cycle occurred. Backend errors and session failures were zero. One xrun was observed on each complete play; sustained underrun-free audio and latency remain unqualified.

The downloaded evidence ZIP, both package/ELF identities, authentic audio bytes, source receipts and lifecycle reports passed a strict offline audit and independent artifact review. The screenshot displayed the green SYSTEM GATES PASSED banner and the native-look arrow. Emulator controller and audible-confirmation fields remain false.

The delivered ARM64 APK is 176,145 bytes, SHA256 `e21604e5c80d29a8e103e6a149b6dee51feb1fa960a4e8c018e46fd24e3a0ec0`, min SDK 26. The [build receipt](evidence/phases10-12/build-receipt.json) records its native library and isolated CI debug signature. This package requests no permissions.

The earlier [API-floor compile failure](evidence/phases10-12/first-native-build-failure.json) and [first emulator failure](evidence/phases10-12/first-emulator-failure.json) remain recorded. The first removed two optional API28 routing calls while preserving default MEDIA/MUSIC routing and API26 support. The second corrected final-UP direction accounting and replaced foreground lifecycle intents with real UI actions. Source C kernels, golden fixtures and qualification requirements were retained.


## Device sequence

Install **CoH Native Systems Probe**. Run checks, drag the arrow, press and release a controller button, and circle both sticks. Play the sound and confirm hearing the three sounds. Resize and recreate the input view. Start sound, press Home while it is playing, return and play again. Export the JSON report after the system-engine banner passes; the separate controller-coverage and audible-confirmation fields should also be true on the Thor.

## Recovery continuation: Systems Probe 0.1.1

Recovery started from `dd3403fd5fb4e61d0542766eda16bae43a1e4d2f`.
The prior agent had completed gates 10–12 and recorded the qualified 0.1.0
packages; it stopped before the physical Thor delivery/acceptance step. No
Phase 13 implementation existed. The accepted Phase 9 and original 0.1.0
source, build and emulator evidence remain retained.

Version 0.1.1 changes only the diagnostic Android adapter, reporting and
delivery checks. Right-stick axes follow the device's declared motion ranges:
prefer Z/RZ, falling back per axis to RX/RY, matching the production launcher's
existing policy. A centered preferred axis stays centered even when an alternate
axis carries another value. Native input kernels are unchanged.

Cancelled audio now preserves backend and cleanup failures as session failures;
a later clean playback or Home cycle cannot erase them. Normal clean user/Home
cancellation remains allowed. The status exposes current audio playback and
the separate stick/audibility observations. The native audio sink, authentic
PCM fixture, packet kernels and wire goldens are unchanged.

The [0.1.1 qualification receipt](evidence/phases10-12/recovery-0.1.1/qualification.json)
records successful [workflow 38587763042](https://github.com/Russianranger/coh-android/actions/runs/38587763042)
and portable-core workflow 38587762974 from source commit
`5cfd1b88d0f8312517ee83a2be89952835ee606e`. The downloaded archive and both
APKs passed byte/ELF/fixture/manifest/signature-receipt checks. The actual adapter
passed 59 host checks and two negative controls; actual Java receipt validation
passed 78 checks. The final Android 13 report passed seven source runs across
three view generations/two sizes, two complete AAudio plays consuming 135,468
frames, one exact active-stream cancellation/stop/close and fresh Home/return
recovery, with zero session failures. Both physical observation fields remain
false in emulator evidence.

The unchanged native sink's clean late-cancellation behavior was reproduced
under bounded host AAudio stubs: Home arriving during successful cleanup can
produce result OK plus cancellation after all three clips complete. The Android
receipt helper permits that clean retry while the Home gate still requires the
native CANCELLED result. Backend errors remain sticky. The
[host witness](evidence/phases10-12/recovery-0.1.1/native-late-cancel-proof.json)
records this distinction separately from Android execution.

The delivered ARM64 APK is 176,149 bytes, SHA256
`4e915b8d51575f1901647b9ce80aade3b59560c6ebc74094051049def9a09573`,
version code 2. Its native library and authentic audio bytes remain identical
to the original qualified 0.1.0 package. Physical controller coverage and
speaker audibility remain pending until the
[Thor device sequence](systems-probe/THOR-TEST.md) and its JSON are reviewed.
