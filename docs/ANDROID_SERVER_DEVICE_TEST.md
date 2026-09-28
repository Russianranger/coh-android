# Thor real DbServer candidate — 0.2.0

This is the next physical-device gate after the accepted hosted Atlas Park
create/save/restart/resume test. It exercises the real Windows DbServer through
Wine/FEX against native ARM64 PostgreSQL on Thor. It does not launch Atlas Park
or the graphical City of Heroes client.

The application is **COH Server Test**, package
`io.github.russianranger.cohdiagnostic.m3`. It installs alongside the accepted
**COH Diagnostic 0.1.5**. Keep the old app and its runtime installed. This
candidate uses a separate private runtime and separate disposable test databases.
Its CI signing certificate is temporary, so future candidate updates may need
separate installation instructions.

## Qualified build

[Run 36483331900](https://github.com/Russianranger/coh-android/actions/runs/36483331900)
at `f7dbba42ec29a1c054d856d71810146f5b53bac6` passed tooling, APK build and
all 28 hosted ARM64 runtime stages. Tooling ran 241 tests: 233 passed and eight
Windows-only checks were skipped on Linux. Signature and package identity checks
passed, and all 17 APK runtime entries plus both native libraries independently
matched the downloaded build artifacts. See the
[acceptance receipt](android-evidence/accepted-device-candidate-hosted-36483331900.json).

Download the APK from the run's **coh-server-test-apk** artifact. The APK is
16,668,615 bytes with SHA-256:

```text
cb5cf453af1b81cbaa02917a6d7cb55ab8b8f2a910a46b0a85f4ae399883188b
```

This qualifies the APK build and its packaged guest runtime on hosted ARM64.
Physical Thor execution, listener binding and lifecycle behavior remain pending.

## Inputs and scope

The candidate retains every accepted M2 runtime payload byte from run
`36364550345`, including PostgreSQL, Wine/FEX diagnostic inputs and the Android
PRoot binaries. It adds the independently qualified loopback DbServer package
from run `36460867428`, the accepted 62-file generated-schema input, and the
current guest test script. The original runtime manifest is retained byte-for-byte
inside the new bundle; both identities are verified before packaging.

Every DbServer process in the device policy enables loopback binding before
startup. Both normal-schema passes also enable the qualified fixed-input mode.
The fixture proves 21 persistence check groups; normal DbServer startup and reload
verify 99 tables, 5,935 ordered columns and 58,272 exact attribute IDs/names.
The listener checks require the source-derived local TCP/UDP endpoints.
A fresh test state directory is created per real DbServer run. Cleanup must stop
PostgreSQL, Wine and all owned workers before the app reports success.

The same packaged guest, package and schema are exercised with the device
listener policy on hosted ARM64 before delivery. Hosted execution leaves all
physical Android, gameplay and rendering assertions unvalidated. The Android
support wrapper supplies actual device provenance after a device run.

## Test on Thor

1. Install **COH-Server-Test-0.2.0.apk** and open **COH Server Test**. Allow
   notifications so the active test and Stop control remain visible.
2. Keep at least **5 GiB free** and tap **Setup runtime**. This separate app
   downloads about **641 MiB** of runtime archives on its first setup. It does not
   reuse another app's private storage. Wait for **Runtime ready**.
3. Tap **Run real DbServer test**. The test is bounded to 30 minutes, with extra
   time allowed for shutdown. Progress is shown in the app and notification.
   The normal hosted DbServer test takes a few minutes, but this is not a device
   timing guarantee.
4. After **Real DbServer test passed**, tap **Export latest report** and save the ZIP.
5. Start the real test again. Wait until the progress shows
   `wine_prefix_and_driver` or a `dbserver_` stage, then tap **Stop**. This lets
   the test launch workers before checking their cleanup. Wait for **Stopped**,
   then export that report. A cancelled test must not be reported as passed.
6. Run it again to completion. During this run, switch to another app and return,
   then lock the screen for about 30 seconds and unlock it. Export the final report.
7. Send the completed, stopped and rerun ZIPs, plus any error screenshot. Describe
   whether reopening the app and screen locking affected progress.

Completed reports have unique immutable filenames. Later operations cannot
change an earlier file while its export picker is open. The app exports the
latest operation by default, so export each requested report before starting
the next operation. If setup or a test fails, export its report immediately
before starting another operation. An interrupted process never silently
restarts a test.

The existing **Run diagnostics** and **Run client probe** buttons remain available
as supporting checks; they are not prerequisites to repeat after the accepted
0.1.5 diagnostic. Screen locking here checks the foreground-service behavior
with the app's wake lock; it is not proof of unrestricted execution through every
Android power-management state.

## Next gate

Once the real DbServer and Stop/rerun/background checks pass on Thor, integrate
the qualified local listener package into the Atlas game runtime and requalify
that combined package before delivering a game-server device candidate. Preserve
the accepted Atlas donor and evidence until the replacement has passed.
Physical Atlas execution, interactive rendering, controls, audio, missions and
combat remain separate unvalidated milestones. The separate earlier intermittent
hosted fixture signal-11 failure is not claimed repaired by this candidate.
Peak device memory has not yet been measured.
