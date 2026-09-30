# Thor device acceptance

**Latest: physical Atlas 0.4.4 passed on 2026-09-30 UTC.** All 18 stages, both
committed saves, exact-character resume and complete owned cleanup are verified.
See the [receipt](android-evidence/accepted-atlas-test-thor-20260930.json).
The user skipped manual Stop/rerun and screen-lock testing for this version;
these remain unvalidated. Advance to the separate visible client presentation
APK without repeating the long server test. Earlier milestones below retain
their original scope.

The **real DbServer and Stop/rerun gate passed with 0.2.0** on 2026-09-28.
Two complete 28-stage passes surround an intentional, cleanly cancelled run.
See the [device results](ANDROID_SERVER_DEVICE_TEST.md#accepted-thor-results)
and [acceptance receipt](android-evidence/accepted-dbserver-thor-20260928.json).
App switching and screen locking passed by user attestation; peak memory is
unmeasured. Keep both accepted installations. The subsequent
[hosted Atlas loopback integration](ANDROID_GAME_RUNTIME.md#accepted-loopback-dbserver-integration)
and [MapServer/TestClient listener qualification](ANDROID_GAME_RUNTIME.md#mapserver-and-testclient-listener-candidate)
also passed. Verified file-picker asset import and separate Android Atlas
runtime/lifecycle integration are the next implementation gates. The latest
hosted result does not provide a new APK or a physical Atlas pass.

## Earlier M2 diagnostic — 0.1.5

On 2026-09-28 at 01:24:05 UTC (September 27, 20:24 CDT), **0.1.5 passed the
physical Thor database and headless client diagnostic gate**. The user reported
both modes passed. The supplied archive contains the later combined client run,
which independently includes the complete database suite. The first database-only
run is user-attested; its separate report was not supplied.

The [selected acceptance receipt](android-evidence/accepted-thor-20260928.json)
preserves report/archive hashes and measured results. The original support archive
remains private. Its Android wrapper identifies AYN Thor, Android API 33 and the
accepted app version. The wrapper's runtime manifest hash matches the
[accepted hosted build](android-evidence/accepted-wine-threads-36364550345.json)
at `9dc58f62c58dc4fc5c01288071429bf2aa06d2f4`. All exported manifest content and
six guest-reported asset hashes match. The support export reformats manifest JSON,
so its raw byte hash differs from the embedded manifest. The installed APK was
not separately pulled and hashed. Guest metadata deliberately does not self-attest
Android execution; the Android wrapper supplies that provenance.

## Verified on the device

All **12 stages passed**, with no failures, in **55.344 seconds**:

- Native ARM64 PostgreSQL 18.6, the existing owned cluster, all 65 simultaneous
  stock DbServer ODBC connections, SQL/value/metadata checks and persisted data
  after a graceful restart of the same cluster.
- PE32 DLL and ODBC driver loading through Wine/FEX. The ready Wine prefix was
  reused with zero registration passes; initialization took 9.666 seconds.
- Headless OpenGL 4.3 through Mesa llvmpipe software rendering. Four RGB samples
  exactly matched red, green, blue and white; buffer swap succeeded.
- Synthetic keyboard/mouse messages and DirectInput device creation. DirectSound
  enumeration completed with zero audio devices; playback was not tested.
- Complete cleanup: all **30 process input/output captures closed**, PostgreSQL
  stopped gracefully, and the Wine prefix lock and socket were inactive.

The thread cleanup path observed **three dead leaders with live tasks** and
three owned worker witnesses. It sent three TERM signals and one KILL through
pidfds, with zero inspection failures and zero remaining owned groups. Wineboot's
capture was open when its leader returned and closed by final cleanup. This
confirms the repaired ownership path is needed and works on Thor. The report does
not inventory the exact device pipe writer; that descriptor-level causal proof
belongs to the separate native regression.

## Next work

Keep **0.1.5** and **COH Server Test 0.2.0** with their separate runtimes.
Their completed diagnostics do not need repeating. The 0.2.0 reports prove
real DbServer execution, local listeners and Stop followed by a successful fresh
run. The user confirms the requested app-switch and screen-lock steps passed.
These actions are not separately instrumented, and peak memory is unmeasured.

The [first hosted M3 DbServer gate](ANDROID_DBSERVER.md) has now passed in
run 36369485666. A separate Wine build overlay applies the ODBC compatibility
changes to the real DbServer. Its persistence fixture and normal fixture-OFF
schema initialization/export/reload passed against ARM64 PostgreSQL; this does
not establish physical Android DbServer execution. The subsequent
[full hosted Atlas gate](ANDROID_GAME_RUNTIME.md#accepted-full-hosted-workflow)
also passed in run 36460005201, including both protocol saves, same-cluster
restart and exact-name resume. Do not repeat that completed gate as an unfinished
milestone. First hosted service readiness took 18 minutes 38 seconds; restart
readiness took 3 minutes 14 seconds, so device startup performance remains open.

The separate loopback DbServer package is
[hosted-qualified](android-evidence/accepted-dbserver-hosted-36460867428.json).
The accepted 0.2.0 app integrates that exact donor and now verifies its physical
Android execution and local listeners. The separately identified
[Atlas loopback profile](android-evidence/accepted-game-loopback-hosted-36493722153.json)
then passed the full hosted game sequence in `36493722153`, preserving the prior
accepted result and default donor `36451873322`. The subsequent
[listener milestone](android-evidence/accepted-game-listeners-hosted-36510836956.json)
passed all four jobs in
[run 36510836956](https://github.com/Russianranger/coh-android/actions/runs/36510836956)
at `ac4c1f7978be444a893f65f5177641191861d42f`: 17 native Windows socket contracts,
all 18 ARM64 stages, both committed saves, same-cluster restart and exact-name
resume. Both Atlas starts and both clients proved actual local UDP bindings;
all 122 captures closed with zero remaining owned processes or inspection failures.
Continue with [verified asset import and Android Atlas preparation](ANDROID_GAME_RUNTIME.md#remaining-preparation-for-a-physical-atlas-candidate).
Preserve the accepted stock Windows reference and immutable upstream source.

This acceptance does not establish CoH gameplay, Android surface presentation,
hardware acceleration, Cg shaders, physical controls or audible playback.
