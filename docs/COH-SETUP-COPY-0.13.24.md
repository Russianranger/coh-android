# 0.13.24: reduce runtime-copy pressure and preserve verified retry work

The supplied .23 report records an Android system low-memory kill during runtime
setup, before Game execution. The matching process is PID 19993; its last durable
checkpoint was `Copying runtime assets`, `1152 / 1275 MiB verified`, after 54.176
seconds. Android records exit reason 3, importance 100, 754 ms after that checkpoint.
The last Java heap value was 44,750,552 bytes of 268,435,456; native allocated heap
was 28,509,200 bytes. The exit-history PSS/RSS values are last sampled statistics,
not exact peaks or necessarily the memory immediately before termination.

This establishes a system low-memory termination. It does not establish Java
heap exhaustion, a particular failing asset, or the source of system pressure.
The checkpoint contains no available-system-memory value or current asset name.
No renderer, movement, saving or FPS test was reached. The .21 successful GPU
startup, smoother gameplay and no-observed-fidelity-loss milestones stay completed;
the .23 movement repair and rendering sampler isolation remain physically pending.

## Actual APK and Android source review

The independently audited public .23 APK has SHA-256
`101780ae658f5adeaced4f5415bb856e6a65962f43175ccb9af2284777863cb2`.
Its runtime manifest describes 70 copied files totaling 1,337,174,625 bytes.
The packaged ordering reaches 1,208,432,645 bytes / 1152.451 MiB immediately before
`server-animations.pigg` (97,084,456 logical bytes, 49,880,567 compressed bytes).
That boundary is consistent with the last checkpoint, but the report does not
record the actual in-flight asset and cannot prove that this member caused the kill.

Android 13's default `AssetManager.open` uses `ACCESS_STREAMING`. Tagged AOSP
source shows large compressed assets using `StreamingZipInflater` with a 64 KiB
output buffer. The .pigg member therefore does not imply a 93 MiB whole-inflate
allocation. Large stored assets, including the 859,075,775-byte visual ZIP, use
file-backed mapped input. The new stored-asset path uses an asset file descriptor
and its bounded input stream; compressed assets retain streaming fallback.
This avoids the large source mapping during the copy, while retaining identical
logical bytes. It does not prove that those mappings caused this termination.

Primary references:

- [ApplicationExitInfo: reason and sampled PSS/RSS](https://developer.android.com/reference/android/app/ApplicationExitInfo)
- [AssetManager streaming and uncompressed descriptors](https://developer.android.com/reference/android/content/res/AssetManager)
- [AssetFileDescriptor bounds and stream ownership](https://developer.android.com/reference/android/content/res/AssetFileDescriptor)
- [Android 13 Asset.cpp](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-13.0.0_r1/libs/androidfw/Asset.cpp)
- [Android 13 StreamingZipInflater.cpp](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-13.0.0_r1/libs/androidfw/StreamingZipInflater.cpp)

## Selected installer change

This release changes the Android shell and DEX, retaining the exact .23 runtime
manifest and all 77 runtime payloads. Existing ready .23 installations keep their
identity and use the existing verification path. An interrupted .23 installation
can retain fully verified, ordinary single-link files from that same generation's
owned staging assets. Missing, truncated, corrupt or unsafe candidates do not
count as completed work. The installer still verifies all pins and required
components before atomic activation. Existing imports, character/profile data,
ready generations and save acceptance remain protected.

Setup reads, writes and verification share a 4 MiB pacing window: 32 MiB/s
combined work under healthy memory, adaptively 8 MiB/s near the existing memory
reserve. A copied byte counts in read, write and hashing work. The full 1275 MiB
asset copy/verification therefore has about a 120-second pacing floor, plus
about 40 seconds for final installed verification; archive preparation is extra.
Verified staging reuse avoids copying and writing those files, but still hashes
them. This is not a setup-speed claim.

The durable checkpoint records current asset/copy/hash progress, Android system
available/total/threshold memory and its low-memory flag, process RSS, low-water
memory values and compact guard counters. This is a resource-pressure mitigation and a
more precise next diagnostic, not a physically proven crash or FPS improvement.
Steadier installation may take longer; gameplay I/O and frame pacing are unchanged.

0.13.24 / version code 39 is published from frozen APK/Java source
`3d73e9b4c71fe3f87de6bf0bb41fc0ce50f3f6ce`, owner `37973264500`.
All five jobs passed: recovery, qualification, APK publication and the separate
actual-public-download SDK audit, with its changes gate. Full qualification:
**1,605 tests / 110 suites / zero skips**, all seven real PostgreSQL fixtures,
9,721 source pins. Root authenticated the five bounded evidence ZIPs, checked a
fresh production qualification reader and independently verified frozen sources,
retained actual .23 donor/native bytes and current receipt/release pins. Root did
not repeat the large .24 APK download, SDK checks or native proof execution.

[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.24/COH-Atlas-Gameplay-0.13.24.apk)
· [Qualification/public audit](https://github.com/Russianranger/coh-android/actions/runs/37973264500).

APK: 1,560,316,680 bytes, SHA-256
`7ae9e8b21e48c30e1d6b9373e676ec7b6eb4727db7fa7b313281fb30a8ab38b0`.
Exact source/runtime/native producer distinction, changed Java/new DEX pins,
all 77 retained payloads, signer and authenticated artifact/member/job evidence:
`android-evidence/setup-copy-0.13.24-publication.json`.
Physical setup completion, crash prevention and FPS improvement remain pending. Device evidence and its interpretation limits are in
`android-evidence/setup-copy-0.13.23-thor-20261009.json`.

## Exact next milestone

Install .24 as an update without clearing app data or importing assets again.
Run Set up / update runtime once and wait for Runtime ready. If it interrupts,
reopen and export the report immediately rather than repeating setup; its durable
memory and asset fields should identify the pressure interval. Once ready,
confirm walking/Jump, then use the already requested short GPU standing/camera/
walking route, ordinary verified Save/Finish and complete outer export. That
still tests .23's same-Game sampler isolation; no FPS gain is claimed. Startup,
zoning and another unchanged long Software comparison remain deferred.
