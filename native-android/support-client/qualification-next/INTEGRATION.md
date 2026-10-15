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
