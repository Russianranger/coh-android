# Phases 10–12: input, audio output and packet framing

Phase 9 is accepted on the physical AYN Thor. The [world receipt](evidence/phase9/thor-qualification.json) records the successful precision correction and measured background/return recovery. These three successor gates are developed together in an isolated package, `org.coh.systemsprobe`, version `0.1.0-phases10-12`. Actual Android qualification is pending the dedicated build and emulator workflow.

| Gate | Implemented slice | Qualification boundary |
|---|---|---|
| 10: native input | Source joystick thresholds, key edges/held levels, editor-look angle arithmetic; Android touch, controller and keyboard callbacks; clear on cancel/focus loss | Android stick rate/deadzone is an explicit adapter. Gameplay camera obstruction, character movement, bindings and collision are separate. Physical controller coverage is reported separately from emulator callbacks. |
| 11: native audio output | Authentic recovered headset sound, source memory callbacks and signed PCM preparation, original volume curve, bounded AAudio playback, partial writes, cancellation/close/reopen | Ogg decoding is currently prepared on the host. Native compressed decoding, full mixer, spatial audio and sound catalog are separate. Frame counters do not prove speaker audibility; user confirmation is separate. |
| 12: packet framing | Source LSB-first bitstream and packed integers, restricted packet envelope, Adler32, accepted fixed-width Blowfish, bounded parsing | Offline frames only. The selected profile excludes debug/sibling/ACK/compression/ordering branches. No live server, authentication, command decoding or gameplay synchronization is qualified. |

The accepted Phase 6–9 implementations and original source trees remain separate. Generated audio assets stay outside git and are recovered from pinned release members by CI.

## Source evidence

The input [contract](input/README.md) preserves the original DirectInput integer range and strict thresholds, source key-level behavior, single-wrap angle semantics and source editor look. Host proof compares 96 camera cases, 2,048 key events and 8,004 joystick cases against unchanged source code, then runs 909 native checks with sanitizers. Android normalization, pointer-ID handling, analog rate and deadzone are declared adapter policies. The preview is a diagnostic arrow rather than a player or game camera.

The audio [contract](audio/README.md) uses `data/sound/ogg/player/headset_incoming_02.ogg`, 12,930 bytes, SHA256 `82bec697f9e824d192cac90f32a01421e4a3875aada64fc709862bc4d3ae9198`. Exact release member CRC/SHA and bounded ZIP envelopes are checked. Four unchanged original memory callbacks and `ov_read(...,0,2,1)` prepare 44,100 Hz stereo signed 16-bit PCM: 18,168 frames, 72,672 bytes, SHA256 `0e9a0cb2fb36575c890cea7ad8b933a732a7e6c970723e5e198dd00fc578fcd5`. The 64-byte `COHAUD11` envelope yields a 72,736-byte fixture, SHA256 `440361125d7420a1730ecd742271d8b2a67808dffcfa9dc435f2357d59931823`. Host proof checks 40 source gain components, 83 malformed spans and 145,344 PCM scaling components. Playback repeats the clip three times with 0.15-second gaps; the middle clip is quieter. Runtime format, channels, sample rate, submitted/read frames, partial writes, cancellation and object cleanup are recorded.

The protocol [contract](protocol/README.md) pins ten source files and 24 original function bodies. Sixteen source-wrapped plaintext frames compare across 1,736 bytes; 32 clear/encrypted wire goldens and 330 bit cases qualify the derivative. Host sanitizers pass 23,467 checks, including 8,989 malformed cases and 256 unaligned cases; another 12,000 exact-allocation fuzz cases pass. Independent zlib/OpenSSL checks validate checksums/encryption and authenticated negative fixtures. Zero-filled producer padding is selected; incidental original writes into unused backing storage and extra UDP tail bytes are outside this bounded contract.

The [REA-assisted seam receipt](evidence/phases10-12/rea-systems-seams.json) retains raw input/audio/protocol anchors, five import candidates and two bounded candidate function instruction lists from the matching client checkpoint. Decompilation attempts did not complete. The ten original checkpoint files remained unchanged; Ghidra created runtime lock/temp files, which are recorded separately. No target execution, autoanalysis, ownership-check bypass or new source-to-binary function identity is claimed.

## Combined probe

The app verifies pinned audio bytes, executes the three native source checks and records real Android callback transport. Synthetic dispatch is explicitly separated from external touch/key events. Both stick direction masks and device audibility have independent fields. A successful system-engine result requires current checks, two input-view sizes, recreation, actual touch/key callbacks, clear input on pause, cancellation of the specifically active audio run, stop/close, foreground recovery and a fresh complete audio playback. Audio errors cannot be cleared by a later success; obsolete lifecycle work is identified separately. Export is an immutable snapshot taken before the file picker.

The dedicated workflow runs source oracles and malformed-input checks, builds separate ARM64/x86_64 packages, checks ELF/manifest/signature/asset identity and exercises Android13 input, AAudio and lifecycle callbacks. Physical stick motion and speaker audibility remain device evidence.

## Device sequence

Install **CoH Native Systems Probe**. Run checks, drag the arrow, press and release a controller button, and circle both sticks. Play the sound and confirm hearing the three clicks. Resize and recreate the input view. Start sound, press Home while it is playing, return and play again. Export the JSON report after the system-engine banner passes; the separate controller-coverage and audible-confirmation fields should also be true on the Thor.
