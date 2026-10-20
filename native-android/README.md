# Native Android development

See [the current roadmap](../ROADMAP.md) for the accepted Combined 0.1.14
stage, current indexed geometry string blocker, and next three steps. The
sections below retain the original experiment and qualification history.


> Gates 22–24 are physically accepted on AYN Thor for Session Client 0.3.0. See [the acceptance receipt](evidence/phases22-24/thor-acceptance-20261015.json). No repeat of this test is required. Historical qualification sections below retain their original timing.

The new [combined server/native app](combined-client/README.md) imports existing
0.13.36 launcher and CoH Assets 1.0.0 files, starts the existing headless local
server runtime, and opens the native client manually. Follow its
[consolidated Thor test](combined-client/THOR-TEST.md). It installs separately and
preserves the conventional launcher and accepted native clients. Native DB/Map
handoff is an explicit local development path; real AuthServer login and full
server-world render/spawn remain pending.

Latest continuation: [gates 25–27 session libraries](PHASES25-27.md) and
[October 15 recovery](RECOVERY-20261015.md). Networking, authentication and
replication have new source/host-qualified components; genuine account login
and a live native world remain pending. Session Client 0.3.0 is accepted; its
[Thor procedure](session-client/THOR-TEST.md) is retained for regression reference.
The separate [support-client handoff](support-client/README.md) remains available
for its newer offline scope and has not been claimed physically accepted.

The latest [session foundation qualification](https://github.com/Russianranger/coh-android/actions/runs/38752076829)
passes clean source/host/sanitizer, public-crypto ARM64 linkage and five Android 13
x86_64 crypto/TCP/UDP suites. [Exact receipts and limits](evidence/session-live-20261015/hosted-qualification.json)
are preserved. No accepted APK was rebuilt; actual server login and complete
authoritative world replication still require the [next parallel contracts](SESSION-NEXT-CONTRACTS.md).

Isolated C modules for Android Bionic `arm64-v8a`, based on the accepted client
source. These targets are independent of the shipping Game and launcher targets.

Implemented test slices:

- Fixed-width Blowfish with checked key/block lengths and unaligned-safe,
  explicitly little-endian game packet words.
- Fixed 596-byte animation headers and 20-byte bone records, offset/span
  validation and native-width borrowed views.
- Fixed 12-byte geometry pack descriptors and v3-v8 model-record metadata.

This is not a native game or a complete animation/geometry loader. Rotation
expansion, geometry delta/collision decoding, real-asset corpus parity, live
protocol exchange, Android Surface rendering and Thor execution are separate
gates. Results will distinguish host execution from Android cross-compilation.

The upstream sources are immutable. `tools/generate_crypto.py --check` verifies
the crypto derivative against the original source hash and preserves its author
notice. Generated buffers and test data do not access personal profiles.

Phase 3 adds a bounded legacy DXT1/3/5 DDS-to-RGBA decoder. See [PHASE3.md](PHASE3.md) for source contracts, test results and remaining real-asset parity gate.

[PHASE4.md](PHASE4.md) qualifies the selected real DXT1/DXT5 corpus against the original Win32 NVIDIA decoder and explains the separate legacy CPU API.

[PHASE5.md](PHASE5.md) adds an installable ARM64 Surface/EGL texture probe. Android 13 emulator and physical AYN Thor/Adreno740 pixel/lifecycle checks passed. The [Thor acceptance receipt](evidence/phase5/thor-qualification.json) records 12 successful runs, 24 EGL context lifetimes and zero pixel mismatches or GL/EGL errors. The next gate is a real material and skinned fixture with shader, alpha/fog and offscreen-pass validation.

[PHASE6.md](PHASE6.md) reconstructs a real three-bone sleeve mesh and its default dual-color material in a separate native probe. Host source-function and malformed-input checks passed, and Android 13 emulator execution qualified the mesh, pose, material and Surface lifecycle checks. Physical AYN Thor/Adreno 740 acceptance also passed: eight runs, sixteen EGL lifetimes, four Surface generations and zero comparison mismatches. The [Thor material receipt](evidence/phase6/thor-qualification.json) records the audited report. Phase 7 proceeds to original rig, socket and animation playback.

[PHASE7.md](PHASE7.md) adds original compressed huge run keys, full hierarchy, inverse-bind and sleeve-socket reconstruction in a separate native animation probe. Six independent reference checkpoints precede a bounded runtime animation preview and retained material/lifecycle checks. Host original-function and malformed-input tests passed. Android 13 emulator and physical AYN Thor/Adreno 740 execution each passed six runs, twelve EGL lifetimes, 540 runtime animation frames and all CPU/GPU/material/lifecycle comparisons. The [hosted receipt](evidence/phase7/qualification.json) and [Thor animation receipt](evidence/phase7/thor-qualification.json) preserve the separate evidence. The next gate assembles and qualifies the complete character.

[PHASE8.md](PHASE8.md) expands the accepted Thor animation gate into the complete authored Wretch character: eleven draw instances, actual actor morphology, source costume textures and the source-defined low-quality dual-color renderer profile. Host and Android 13 emulator qualification passed, including all pieces, 540 animation frames, twelve EGL lifetimes and lifecycle recovery. The [qualification receipt](evidence/phase8/qualification.json) and [build identity](evidence/phase8/build-receipt.json) preserve the exact ARM64 test package. The [Thor character receipt](evidence/phase8/thor-qualification.json) confirms rendering, animation, materials, resize and explicit recreation across three runs and six contexts. The user accepted the remaining Home/return requirement on October 13 and directed work to Phase 9; this confirmation is recorded separately from measured callback evidence.

[PHASE9.md](PHASE9.md) implements a separate source-world and camera probe for authentic Atlas Park geometry, its complete selected transform chain, two original material families and the source camera convention. Version 0.1.0 [failed on Thor](evidence/phase9/thor-transform-failure-0.1.0.json) at a GPU world-coordinate rounding check. Version 0.1.1 replaces the matrix shortcut with explicit source-order shader arithmetic and supported precise controls. All four host shader paths and updated Android 13 emulator [qualification](evidence/phase9/qualification.json) passed: six qualified runs, twelve EGL lifetimes, 540 camera frames and zero mismatches or GL/EGL errors within those runs. The [ARM64 package](evidence/phase9/build-receipt.json) is version code 2. The full 1,585-file material audit, twenty primary source pins, fixture bytes and comparison limits are preserved. The [Thor world receipt](evidence/phase9/thor-qualification.json) verifies six successful runs, twelve core-precise Adreno740 contexts and measured Home/return recovery. Phase 9 is accepted; the next batch implements native input handling, real-asset audio playback and restricted packet framing.

[PHASES10-12.md](PHASES10-12.md) develops three independent native systems gates together: source input state and editor look, real-asset AAudio playback, and restricted offline packet framing. The isolated `org.coh.systemsprobe` ARM64/x86_64 packages, source/golden and malformed-input checks, Android 13 callback/AAudio tests, and exact Home/return recovery passed. The [qualification receipt](evidence/phases10-12/qualification.json) records all seven native runs and tested APK identities. Physical AYN Thor input, both-stick coverage, audible playback and Home/return recovery are accepted in the [Thor systems receipt](evidence/phases10-12/thor-qualification.json). The original source kernels, hosted qualification and physical report remain preserved separately. Live networking, full native audio mixing/decoding and integrated gameplay remain later gates.

[PHASES13-15.md](PHASES13-15.md) combines on-device compressed Ogg decoding,
real bounded UDP loopback transport and current input controlling the authentic
Atlas scene camera in one new Integration Probe. Source and sanitized host
proofs, build/lint/package verification and Android 13 emulator qualification
passed in the [combined qualification receipt](evidence/phases13-15/qualification.json).
Physical AYN Thor Android 13/Adreno 740 acceptance is recorded separately in the
[Thor qualification receipt](evidence/phases13-15/thor-qualification.json): the
installed ARM64 APK identity and fixtures matched, four native runs and seventeen
complete renderer rounds passed, both sticks reached all directions, decoded
audio was heard, and active audio/blocked-UDP Home interruption cleaned up and
recovered. The raw physical report is preserved. Gates 13–15 are accepted within
this isolated probe scope; integrated character movement, persistent gameplay
state and real server interoperability remain later milestones.

[PHASES16-18.md](PHASES16-18.md) implements the next offline native session batch: a persistent shared Wretch/Atlas scene, source-controlled NOCOLL movement and authored forward Ready/RunCycle/RunPost locomotion. Source host/sanitizer checks, signed ARM64 build/lint/integrity and Android 13 emulator qualification passed in [workflow 38637681649](https://github.com/Russianranger/coh-android/actions/runs/38637681649), with 2,237 frames, real input, held-axis Home cleanup/recovery, export and rendered reset. The [qualified ARM64 artifact](https://github.com/Russianranger/coh-android/actions/runs/38637681649/artifacts/11929666705) and [receipt](evidence/phases16-18/qualification.json) bind the unchanged runtime APK source and corrected driver separately. Physical Thor/controller acceptance was confirmed by the user on October 14, 2026; the [physical receipt](evidence/phases16-18/thor-acceptance-20261014.json) and raw report are retained. The [original Thor test](session-client/THOR-TEST-16-18.md) remains available for regression checks. Earlier accepted probes and the conventional client remain available.


[PHASES19-21.md](PHASES19-21.md) implements authored floor/obstacle geometry,
source WALK and directional locomotion in Session Client 0.2.0. Source/host checks,
the full 1,585-file source trick audit, ARM64/x86_64 builds, lint, signatures and
package integrity passed on runtime
`8629d6a7c4863f492ee50bc030c21c2b2d2f0c3d` in
[build run 38656997946](https://github.com/Russianranger/coh-android/actions/runs/38656997946).
Complete emulator qualification remains pending: the latest
[session run 38663997193](https://github.com/Russianranger/coh-android/actions/runs/38663997193)
passed fresh install/launch, rendering and forward/backward motion, then failed
the left-direction grounded predicate after prolonged travel in the selected
scene. The [manifest](evidence/phases19-21/qualification.json) retains its exact
scope and failed evidence. [Portable-core run 38663997261](https://github.com/Russianranger/coh-android/actions/runs/38663997261)
passed. **Physical gates 19–21 are accepted on AYN Thor as of October 14, 2026**,
from the user's explicit success confirmation and exact-APK
[Thor receipt](evidence/phases19-21/thor-acceptance-20261014.json). The report
contains 6,120 frames, zero transform/non-tie depth mismatches, real both-stick
coverage, six blocked/six sliding ticks and no safety-bound events. Complete
emulator automation remains incomplete; its failed result is preserved separately.

The physically accepted 0.2.0
[CoH-Native-Session-Client-0.2.0-arm64.apk](https://chatgpt.com/api/library/files/libfile_1f69175230b08191b4c8ea65e369139c/download)
is 2,344,055 bytes, SHA256
`2d59e2b39af99facc6f3ac26b310aeba85802542efabb1e71d90e2d33a00de92`
([original artifact 11936304916](https://github.com/Russianranger/coh-android/actions/runs/38656997946/artifacts/11936304916)).
It installs alongside the accepted 0.1.0 app without deleting its data. Use the
[original combined Thor procedure](session-client/THOR-TEST-19-21.md). Gates 13–18 remain
accepted, with the unchanged
[0.1.0 rollback artifact](https://github.com/Russianranger/coh-android/actions/runs/38637681649/artifacts/11929666705)
and [original instructions](session-client/THOR-TEST-16-18.md) available.

The physically accepted gates 22–24 use Session Client 0.3.0:
the indexed loader admits eight pinned original raw assets, a bounded source
Atlas hierarchy selects three model endpoints, and the generic native renderer
draws the authored floor plus ten bench instances. Near/Far view distance selects
six/eleven instances at the reset spawn. The expanded 2,304-triangle collision
scene matches the same visual placements, retaining accepted source WALK and
directional locomotion. This is a controlled neutral-ambient/no-fog station
subset; full Atlas closure, environment lighting and live networking are later
milestones. Host/source/ARM64 qualification is recorded in the
[world module](engine/world/README.md) and [asset/render bridge](engine/bridge/README.md).
The integrated [gates 22–24 implementation and scope](PHASES22-24.md) is committed
on `native-android`. [Session Client 0.3.0](https://chatgpt.com/api/library/files/libfile_7909bc8bae848191911760e360ae9884/download)
uses the same `.walk` application ID and stable signer as 0.2.0. Source/host/GPU,
ARM64/x86 builds, lint and package checks passed. Complete Android 13
[qualification](https://github.com/Russianranger/coh-android/actions/runs/38673357918)
passed with 3,505 frames, five contexts, real input, Near/Far selection,
Home/return, Recreate, export and reset. Physical gates 22–24 are accepted from
the exact APK/report and user confirmation; the [acceptance receipt](evidence/phases22-24/thor-acceptance-20261015.json)
records 29,105 Thor frames and the bounded offline scope.
