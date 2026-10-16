# Support qualification recovery and next build

Worker A started at `3c5da1d8cd501d778e270d395109d40666fbe37a` in its own
detached worktree. It did not edit runtime C/Java, shared build files, workflows,
the accepted Session Client, or primary gates 25–27. Its public interfaces are
the artifact recovery checker, build receipt, emulator report identity check,
and pending physical review template. No worker branch was published.

The previously qualified source is
`b69bbf232e1746f1fb35ef1aa624a636f2cce490`. Its exact signed ARM64 APK is
available in [artifact 11957750066](https://github.com/Russianranger/coh-android/actions/runs/38702695275/artifacts/11957750066).
Its SHA256 is
`4cf976478654ab5005257923a177a9c56126bc323871429ca73e70f0439ffde0`.
The exact archive, APK, signer, source and accepted asset identities are pinned
in `baseline-artifact-pins.json` and independently checked in
`baseline-recovery.json`. Seven original accepted assets were compared byte for
byte with the retained, SHA256-verified Session Client 0.3.0 APK. No accepted
APK/report was changed. Both APKs pass current Android v2/v3 signature checks;
their certificate SHA256 is
`74872f53c9a805dc1dd054c579e299686b4b5584dceec27fb03cf0904e7397c5`.

The recovery audit additionally checks 105 tracked C/Java/manifest/shader inputs,
including 47 recursively included local headers. Header drift fails closed.
The old build receipt listed C files but omitted included headers, so comparing
only its source list would provide incomplete source binding. Retained external
codec/generated inputs are bound by the exact original artifact and native
library hashes; this recovery does not claim independently reacquired codec
source or host font regeneration. The original range-based acquisition receipts
do not establish complete remote archive hashes.

Run from the repository root, supplying downloaded/extracted immutable inputs:

```sh
python native-android/support-client/tools/verify_qualified_artifact.py \
  --artifact-dir /absolute/path/to/extracted-artifact \
  --archive /absolute/path/to/artifact.zip \
  --accepted-apk /absolute/path/to/CoH-Native-Session-Client-0.3.0-arm64.apk \
  --sdk /absolute/path/to/android-sdk \
  --source-root . \
  --output /absolute/path/to/recovery.json
```

The checker describes retained qualification and never launches an emulator or
grants physical acceptance. A runtime/header/shader change requires fresh Android
qualification. Documentation/tool-only changes do not invalidate the original
APK's historical result. Negative controls independently rejected an isolated
header mutation, corrupt APK identity, and five incorrect app identity fields.

The baseline report has one confirmed diagnostic defect: it reports
`app.version_code=1`, while its verified manifest has `versionCode=100`. The
coordinator owns the Java correction. The emulator driver now requires the app's
package, version name/code and installed APK digest/size to match the explicit
build receipt. This catches the original bug. Upcoming packaging uses
`0.2.0-gameplay`, code `200`; these tool changes alone are not an Android build
qualification. The build receipt now also records the verified certificate and
compiler `-MMD` dependency closure, including non-system/generated headers, and
checks header changes when reporting source cleanliness. NDK system headers are
bound by the recorded NDK revision.

| Acceptance level | Recovered 0.1.0 artifact | Upcoming integrated 0.2.0 |
|---|---|---|
| Implemented | Bounded original Wretch/offline scene and support adapters | Coordinator integration in progress |
| Host qualified | Existing module/source/sanitizer receipts preserved | Recheck changed adapters |
| ARM64 built | Exact signed APK independently recovered | Pending new source-bound build |
| Emulator qualified | 13 retained framework scenarios passed | Pending new source-bound execution |
| Physical Thor accepted | Pending | Pending |

`thor-physical-review-template.json` maps every required device check to exported
counters and explicit human observations. The original app renders authentic
source font glyphs, but original icon/skin resource closure is incomplete. Its
character choices are mock data and do not render full Male/Female/Huge models.
No retained evidence closes those gates. The latest render lifetime's
`native.total_ms` resets after lifecycle restarts and must not be used alone to
claim aggregate ten-minute active coverage. New runtime integration should use
one consolidated Thor test after Android qualification.

Rollback: revert Worker A's additive tools/docs commit if necessary, or use the
unchanged pinned 0.1.0 artifact for its historical bounded test scope. Never reset
the integration branch. Device rollback removes only `org.coh.nativesupport`;
preserve accepted 0.3.0 and the conventional launcher. Discarding this worker's
tools does not alter session/network/server behavior or user character data.

## Independent integration fault checks

`tools/check_audio_owner.py` copies and hashes the coordinator's actual audio
owner before compiling it with ASan/UBSan and controlled dependencies. It runs
the real owner thread, latest-state mailbox, pause/resume and cleanup logic.
Nine scenarios cover listener delivery, route reopening, device errors, retained
failed close during both pause and desired-running route recovery, failed destroy
plus cleanup-worker retry, and partial initialization. The final run recorded
five opens/five closes and zero tracked asset/mixer/music/backend residue.
Fake dependencies do not establish real AAudio callbacks, codec execution,
Android focus events or physical route changes. LeakSanitizer is disabled; ASan,
UBSan and explicit owner counts provide the stated bounded evidence.

`tools/check_snapshot_bound.py` independently invokes the actual support/perf
JSON exporters with mocked maximum-width subsystem counters and finite maximum
listener floats. The JSON parses correctly at 7,697 bytes inside the actual
16,384-byte JNI buffer under ASan/UBSan. This tests the current field layout;
adding diagnostic fields warrants rerunning it. Both checkers pin tested source
SHA256 identities in their receipts. `--listener-root` can explicitly reference
the audio worker's isolated tree before coordinator integration; omit it after
the header is integrated. They do not modify any tested runtime source.

## Third coordinator recovery of the already-qualified 0.2.0

The paragraphs above preserve the earlier 0.1.0 recovery history; their upcoming
0.2.0 status is superseded. At pinned checkout
`58caf1d4ab3b39757190f194100ccbc697d57857`, Worker A independently recovered the
0.2.0 Actions archive and rechecked its exact ZIP, both APK signatures, installed
package metadata in all 15 initial/step/final reports, native library identities,
packaged assets and current tracked source/header/shader closure. The seven
accepted Session Client asset payloads match byte for byte.

- Qualified source: `c14a831b55163dbcf2b3e63b4c52805785fceafa`.
- [Exact artifact 11990195263](https://github.com/Russianranger/coh-android/actions/runs/38765087744/artifacts/11990195263).
- ARM64 SHA256: `26bad28b029fef86931108b531f883c9a948a16aff1dc2cdba9d8447c6c4d935`.
- Version: `0.2.0-gameplay`, code `200`, package `org.coh.nativesupport`.
- Android 13 x86_64 emulator: 13 retained scenarios; no new execution inferred.
- Physical Thor acceptance: pending actual device report and observations.

Use the checker command above with the additional argument
`--pins native-android/support-client/qualification-next/gameplay-artifact-pins.json`.
`gameplay-recovery.json` records 113 compared tracked inputs, 50 recursive quoted
headers and 15 package identities. Compiler-recorded inputs additionally cover
angle-bracket/macro includes; generated/external inputs remain identified by the
retained receipt and artifact. `gameplay-recovery-negative.json` records six
actual rejections: five report identity mutations and a forged compiler-recorded
header digest. No runtime source or old artifact was modified for these checks.

The original source build and emulator APK are preserved. New runtime integrations
must receive a distinct manifest code and source-bound Android qualification.


## Code201 third-batch continuation

The third coordinator's runtime continuation stays in this standalone support
package. It adds five offline presentation panels with copied typed intents,
mock damage/target highlights, an authentic Huge punch cue, sampled process
RSS/PSS diagnostics, compact landscape controls, and an optional complete
authentic eight-part Male neutral costume preview. The default Wretch and seven
accepted asset payloads remain unchanged. Female and other full Huge costumes,
complete zones, multi-actor gameplay and authentic impact sound remain incomplete.

The preview owns its immutable copied asset package until its GL owner has ended
and resources are destroyed. Android controls publish only selection flags;
preview rendering/statistics stay on the render owner, and reports consume copied
statistics. Hidden Wretch WALK/skinning pauses during the fixed-camera preview.
Music/ambience is explicitly labeled retained Wretch-scene background audio in
this mode; camera-relative audio correctness is only evaluated in Wretch mode.

`process_memory` reports the independent observer, including per-field known and
error states, sample age, and collection duration. Java publishes the JSON and
timestamps together in one immutable holder; each export task handles one report
and reschedules, allowing memory sampling to interleave. This does not claim to
fill legacy perf bridge process gauges or measure full device/driver memory.

The code201 APK filenames include `gameplay-code201` to distinguish them from the
retained qualified code200. `third-batch-presentation.json` and
`third-batch-snapshot.json` record actual host GLES and sanitizer regression;
`third-batch-integration.json` records actual forbidden-import rejections and
protected-path checks. A fresh source-bound Android13 run must pass the expanded
scenario, including landscape, typed panel interactions, mock impact binding,
Male rendering, Male Home/resume and restoration of Wretch. Local compilation
never establishes emulator or physical acceptance. The README procedure and
physical review template describe the single consolidated Thor session.
