# New Android admission policy successor — closed research

This directory is **new work after recovery**, not a reconstruction of the missing
39,309-byte `ClientLiveDirectoryAndroidFixture.java` or its 28,269-byte test.
Their historical SHA-256 values remain `64d3aba05ac96103702efa2ea7d467ada86fd83684f6a5b74bf7c72d9e8d272c`
and `1513553cee166c61bfdc7940710efd1bdad1d6c36d613d773897eea2b034811f`.
The handoff says the installed-package correction was never applied to those
bytes. The missing bytes and historical 32 controls are not claimed recovered or
replayed by this successor.

`InstalledPackagePreflight` expresses the missing separation as a dormant,
Android-independent necessary-facts comparator:

* Current package identity includes exact app/context/process UID, version,
  last-update time, active APK signer set, source APK path and nativeLibraryDir.
* Source APK and exactly `nativeLibraryDir/libcoh_live_directory.so` must match
  separately pinned held-object paths, length and SHA-256, and remain unchanged
  across the observations. A system-owned, world-readable packaged library is
  valid under this exact installed-package comparison. An arbitrary readable
  helper elsewhere is refused. There is no blanket app-UID test on packaged code.
* The seven finalized namespace data roots remain separate: `/state`, `/tmp`,
  `/presentation-socket`, `/game-import`, `/opt/coh`, `/opt/coh/pgsql`, `/opt/wine`.
  Every root must be an exact distinct directory below the private files root,
  app-owned, on the explicitly pinned current app-data device, without group or
  world write access. Package ownership never substitutes for data-root custody.
* Exact before/after package and object comparison rejects retargeted paths,
  changed current installation and changed inode/device/owner/mode/date/bytes.
  Arrays/lists are defensively frozen. There is no JSON receipt importer.

`AndroidCurrentPackageState` is only a narrow, read-only source binding to a fresh
`PackageManager.getPackageInfo(...GET_SIGNING_CERTIFICATES)` call. It uses
`getApkContentsSigners()`, not certificate rotation history, and reads the current
PackageInfo ApplicationInfo `sourceDir`, `nativeLibraryDir` and UID. It does not
open files, load JNI, start processes or implement a fixture owner. It is kept
outside the active Android source tree. **No Android SDK is available here; this
source has not been compiled against a real SDK or executed on Android.**

The host harness compiles only the comparator and harness as Java 8-target
bytecode using the installed Java 17 compiler module. Its adversarial controls
are typed host mocks, not Android PackageManager/FD observations. The original
29,992-byte helper hash in the harness is an authentic recovered artifact pin,
not a claim that this test executes or requalifies that ARM binary. A separately
repaired O_PATH helper must use its own future compiled pin.

Run:

```sh
python3 -m unittest discover -s research/native-live-recovery-037/android-adapter-successor/tests -p test_installed_package_preflight.py -v
```

Remaining Android work is intentionally explicit. Trusted current pin derivation,
real SDK compilation, held nofollow ancestor and filesRoot custody, hashing held
APK/helper FDs, current file descriptor/device/inode/UID and packet-parent checks,
exclusive synthetic namespace creation, bounded probe execution/cleanup and the
actual current packaged Android/Wine/FEX/PRoot fixture remain unimplemented. A
before/after host comparison cannot exclude filesystem ABA races or replace
held-ancestor authority. This comparator is not the `OwnedFixture`, `ProbeStarter`
or `PacketMetadata` implementation required by the recovered fixture interface.
Alias, sharing and concurrent-retarget controls remain separately required.

`androidAdmissionAllowed()` always returns false, including after valid mock
facts. No Runtime caller, workflow, qualifier inventory, APK, binary, profile,
database, saved character, assets, runtime component or `native-android` source is
modified. No startup, zoning or device performance improvement is measured here.
