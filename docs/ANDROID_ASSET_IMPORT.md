# Verified game-data import for Android

The accepted device importer is **COH Atlas Setup 0.3.0**, application ID
`io.github.russianranger.cohatlas`. It prepares the exact reviewed base data for
the next local server test in Atlas Park. It has no server/client executable,
Wine runtime, native library or network permission. The accepted 0.1.5 and 0.2.0
diagnostics and their private data are unchanged.

Hosted APK and complete-data qualification passed in
[run 36556279364](https://github.com/Russianranger/coh-android/actions/runs/36556279364)
at `2f828ca3e626245ea9fd60055745980bc3f32001`: all 65 contract checks,
signed APK verification and a complete 173,011-file import passed. Every imported
file was independently rehashed on the runner, matching the accepted full-data
inventory; cancelled re-import and abandoned-stage recovery also passed.
Physical Android import/Stop/retry passed on AYN Thor on 2026-09-29, as recorded below.
This is an import milestone; Android MapServer execution and graphical gameplay
remain subsequent milestones.

Download the [qualified APK artifact](https://github.com/Russianranger/coh-android/actions/runs/36556279364/artifacts/11027848275)
while signed into GitHub, extract its ZIP, and install `COH-Atlas-Setup-0.3.0.apk`.
The APK is 321,041,177 bytes; SHA-256
`df25f33f673988d3b0c1c6fea2c4ae95dd776cbf84505e65ba3889159165e9fb`.
The artifact expires 2026-12-28. The
[acceptance receipt](android-evidence/accepted-asset-import-hosted-36556279364.json),
[host report](android-evidence/asset-import-hosted-36556279364.json),
[APK report](android-evidence/asset-import-apk-36556279364.json) and
[preserved evidence](android-evidence/asset-import-evidence-36556279364.zip)
record the exact candidate. The downloaded APK and all four packaged data
payloads were independently rehashed after CI. Hosted qualification took
82.252 seconds; this is not a Thor timing estimate.

## Inputs and publication

The APK includes the pinned repository text as a compressed archive, plus small
streaming inventories and an import contract. The user selects the existing
reviewed `coh-reference-assets.zip` through Android's document picker.

| Input | Identity |
|---|---|
| Source | `0b75ade0c801735e10c5798f641948a45cc50488` |
| Companion data | `d51533ec8e6a9cf726b9214968077a05fdcf19f3` |
| Reviewed asset ZIP | 615,541,018 bytes; SHA-256 `28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07` |
| Binary assets | 16,721 files / 985,644,857 bytes |
| Authoritative text | 156,290 files / 1,992,085,660 bytes |
| Combined base data | 173,011 files / 2,977,730,517 bytes |
| Accepted complete inventory | SHA-256 `b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4` |

The original ZIP is already retained as asset `588984151` in the repository's
[existing draft release](https://github.com/Russianranger/coh-android/releases/tag/untagged-5105ae5e41ef8f13e80d).
The repository owner can access this while signed into GitHub. Choose
`coh-reference-assets.zip`; the similarly named `partial-invalid` file is an
incomplete historical upload and must not be used. This work does not publish
the release, upload another broad asset set, or embed GitHub credentials in the app.

The importer first copies and checks complete archive bytes, then validates ZIP
metadata and each file's exact path, length and SHA-256. Text is installed first
so its canonical directory spelling is preserved for 1,009 binary asset paths
that share directories with text. Source database configuration keeps its
existing precedence. A hosted cross-check requires the assembled inventory to
match the previously accepted full-data digest, including path spelling.

Extraction occurs in private staging. A single atomic pointer update publishes
the completed generation; Stop, an invalid archive, insufficient space or an
interruption cannot replace the prior accepted generation with partial data.
Abandoned work is recovered during the next explicitly started import. Reopening
the app checks the completed receipt; it does not silently repeat all 173,011
file hashes or start another import. Future game startup must verify its selected
inputs and use a separate writable runtime copy for schema, caches and credentials.

## Accepted Thor import/Stop/retry

The three supplied reports from Android 13 / SDK 33 match the exact import
contract embedded in the hosted-qualified APK. Archive integrity, report
identities, counts, revisions and chronological generation continuity passed
independent review. See the
[device acceptance receipt](android-evidence/accepted-asset-import-thor-20260929.json).

| Report | Result | Attempt duration |
|---|---|---|
| [110926](android-evidence/coh-atlas-import-20260929-110926.zip) | Passed: 173,011 files / 2,977,730,517 bytes verified | 56.610 seconds |
| [111012](android-evidence/coh-atlas-import-20260929-111012.zip) | Expected cancellation during extraction; prior completed generation preserved | 9.317 seconds |
| [111126](android-evidence/coh-atlas-import-20260929-111126.zip) | Passed: full verification repeated; new completed generation published | 61.822 seconds |

The cancelled attempt stopped after 4,552 files / 86,958,402 bytes. Its
`CancelledException` is the expected Stop outcome. Its available-content receipt
names the same completed generation as the first run; the final run publishes
a different complete generation. The 9.317 seconds describes the entire stopped
attempt, not Stop response latency. Neither successful report contains an error.

The user reports that all three checks appeared successful. App switching,
screen locking, a separate reopen and process death are not individually
recorded by these reports; they remain outside this acceptance claim. No repeat
of the accepted import/Stop/retry sequence is required. Carry explicit lifecycle
and resource checks into the combined game-service candidate.

## Device check procedure (completed for import/Stop/retry)

1. Keep 0.1.5 and COH Server Test 0.2.0 installed. Install the separate
   `COH-Atlas-Setup-0.3.0.apk` candidate.
2. Have the complete reviewed ZIP available through Android Files. The original
   ZIP is selected directly; do not select a PIGG, a split part, or unzip it first.
3. Have at least **5 GiB free internal storage after APK installation**. The
   importer calculates the required space from its actual archives, full data,
   file-allocation allowance, indexes and reserve. Existing accepted data remains
   in place during a replacement, so a re-import also needs free working space.
4. Tap **Import game assets**, select the ZIP, and allow the operation to finish.
   Progress and Stop remain available in the notification when leaving the app.
   The operation has a 90-minute limit; the two accepted Thor imports took about
   57 and 62 seconds. Success must report **173,011 verified files**.
5. Export that report. Reopen the app and confirm the completed content remains
   available. During a subsequent import, use Stop and export the stopped report;
   verify the prior completed content remains available. Then retry the import
   and export its successful report. App switching and screen locking can be
   checked during that run.

Each attempt has an immutable support ZIP containing its status, progress,
device/application identity and pinned import contract. It excludes the asset
payloads, selected URI and document-provider filename. A failed/stopped attempt
cannot use an older successful report as its latest result.

This development APK uses an ephemeral CI signing certificate. It does not
establish a stable release-update identity; a later differently signed candidate
may require reinstalling and repeating content import.

## Hosted checks and remaining milestone

`.github/workflows/android-atlas-import.yml` runs the Java importer contracts,
package checks and APK verification. It then downloads the existing reviewed ZIP,
extracts the four data payloads from the actual signed APK, runs the same importer
core on a JVM with the full inputs, checks cancelled re-import/recovery, and
independently rehashes every resulting file against the accepted Atlas inventory.
APK, signing/payload report and bounded hosted evidence are separate artifacts.
The raw binary asset ZIP is not uploaded as an Actions artifact.

With import/Stop/retry accepted on Thor, the next implementation combines these prepared
inputs with the qualified runtime, DbServer, MapServer and TestClient in an Android
Atlas test. That candidate must independently pass create/save/restart/resume,
Stop with game services active and a fresh rerun, with measured memory/startup and
complete owned cleanup. Rendering and human controls remain separate work.
