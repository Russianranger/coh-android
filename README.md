# City of Heroes Android

The next device step is the separate [COH Atlas Setup asset-import candidate](docs/ANDROID_ASSET_IMPORT.md). It prepares verified game data; game-server and graphical-client execution are later device gates.

**Latest hosted milestone: MapServer and TestClient local bindings passed.**
[Run 36510836956](https://github.com/Russianranger/coh-android/actions/runs/36510836956)
at `ac4c1f7978be444a893f65f5177641191861d42f` passed all four jobs, 17 native
Windows socket contracts and all 18 ARM64 stages. Both Atlas starts and both
client sessions proved actual loopback UDP bindings alongside the accepted
DbServer bindings. The same character survived committed save, same-cluster
restart, exact-name resume and a second save. All 122 process captures closed,
with zero remaining owned processes or inspection failures. See the
[acceptance receipt](docs/android-evidence/accepted-game-listeners-hosted-36510836956.json),
[raw report](docs/android-evidence/game-listeners-arm64-36510836956.json) and
[preserved evidence](docs/android-evidence/game-listeners-evidence-36510836956.zip).
Next comes verified file-picker asset import and a separate Android Atlas
runtime with lifecycle handling. Keep 0.1.5 and 0.2.0 installed; this hosted
milestone does not provide a new APK or establish physical Android Atlas.

**The primary M2 device diagnostic and headless client capability gate passed on
AYN Thor with 0.1.5.** The [device acceptance record](docs/THOR_DEVICE_ACCEPTANCE.md)
covers a subsequent combined database/client run with all twelve stages passed,
complete owned cleanup and all 30 process input/output captures closed. It reused
the database cluster and ready Wine prefix. The user also reports that the
preceding database-only run passed; the supplied archive contains the combined run.

The headless client fixture verified OpenGL pixel readback through llvmpipe
software rendering and synthetic keyboard/mouse handling. Cleanup observed exited
leaders with live owned workers on the device and finished with zero remaining
helpers. The exact process that held the earlier pipe was not inventoried. See
the [accepted Thor evidence](docs/android-evidence/accepted-thor-20260928.json).
Android presentation, GPU acceleration, physical controls, audible playback and
CoH gameplay remain unvalidated; this diagnostic cannot launch the game.

**The first hosted M3 DbServer gate also passed on ARM64 Wine/FEX.**
[Run 36369485666](https://github.com/Russianranger/coh-android/actions/runs/36369485666)
passed all 21 real persistence check groups across 14 fixture invocations, then
two normal fixture-OFF exports with 99 tables, 5,935 ordered columns and 58,272
exact attribute IDs/names. The catalog remained stable on reload and owned cleanup
completed. See the [qualification and evidence](docs/ANDROID_DBSERVER.md).
Physical Android DbServer execution subsequently passed with 0.2.0, as recorded below.

**The full hosted Atlas Park gate passed on ARM64 Wine/FEX.**
[Run 36460005201](https://github.com/Russianranger/coh-android/actions/runs/36460005201)
passed all three jobs and all 18 runtime stages: character creation, live influence
change, committed protocol save, same-cluster service restart, exact-name resume
and a second committed save. All 123 process captures closed and owned cleanup
completed. See the [Atlas qualification](docs/ANDROID_GAME_RUNTIME.md) and
[acceptance receipt](docs/android-evidence/accepted-game-hosted-36460005201.json).
First service readiness took 18 minutes 38 seconds; restart readiness took
3 minutes 14 seconds. This establishes hosted persistence, not physical Android
game execution or acceptable device startup performance.

The selected baseline is the **original OuroDev-derived source import** from
`Thunderspies/CityOfHeroes`, at commit
`0b75ade0c801735e10c5798f641948a45cc50488`. It includes local server services,
the graphical client and development tools. It is Issue 24/Volume 2 lineage
with downstream changes: source code, not a VM image.

**Validation, 2026-09-27:** all 5,995 imported files pass integrity checks. An
[upstream Windows build of this exact commit](https://github.com/Thunderspies/CityOfHeroes/actions/runs/35934567567)
built the server and client and passed nine utility, archive and codec tests.
CoH gameplay remains unvalidated; the accepted Android diagnostic scope is recorded above.

The complete pinned companion data is now imported under `upstream/i24`: **156,297
files, 1,992,097,492 bytes**, verified against its original Git tree. Runtime
staging tools preserve both snapshots and fix the companion executable-name gap.

The current [matching Windows client/server package](https://github.com/Russianranger/coh-android/actions/runs/36088012664)
passes its hosted build and dependency checks. The supplied base assets have been
assembled with the pinned text: **173,011 data files**, including **16,721 binary
assets**. See the [reference runtime and downloads](docs/REFERENCE_RUNTIME.md).

The current [data-only schema generation](https://github.com/Russianranger/coh-android/actions/runs/36088012666)
also passed, producing all 56 expected files with stable attribute mappings and
zero queued errors. It shares repository commit
`775a0dd770adac045484805dbbb5f68054c7a354` with the reference package.
The [PostgreSQL regression suite](https://github.com/Russianranger/coh-android/actions/runs/36088012670)
passed all four jobs, including 21 real-DbServer persistence check groups.
The [normal fixture-OFF DbServer startup/export/reload check](https://github.com/Russianranger/coh-android/actions/runs/36125829298)
also passed with generated game schemas: 99 tables, 5,935 columns, 58,272 attribute rows,
stable catalog and identifier mappings, and no failure diagnostics across both
passes against a fresh disposable PostgreSQL database.

The [real network save test](https://github.com/Russianranger/coh-android/actions/runs/36125829311)
also passed: normal DbServer/MapServer requests, acknowledgements held until a
blocked two-container save committed, and no acknowledgement after an injected
commit failure. The failed save preserved the previous row and stopped DbServer.
This exercises generic containers; the separate character result is recorded below.

The [asset-backed reference run](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
also passed: ordinary MapServer template generation freshly reproduced all 56
accepted files byte-for-byte in 25.89 seconds. A separate fresh runtime then
kept Atlas Park ready for players, confirmed through DbServer status queries,
for 62.235 seconds. The [recovered reports and archive hashes](docs/reference-runtime-evidence/accepted-gates-36176806895.json)
record those completed gates.

The earlier [character persistence run](https://github.com/Russianranger/coh-android/actions/runs/36282414135)
passed all eight phases: fresh fake-auth creation, live currency change to 12345,
protocol logout and committed SQL verification, service restart and exact-name
short scene resume. Selected character, power and costume rows remained unchanged;
LoginCount advanced from 1 to 2 only after resume. See the
[accepted evidence](docs/postgresql-evidence/accepted-character-persistence-36282414135.json)
and [scope of the test](docs/CHARACTER_PERSISTENCE_VALIDATION.md).

The [sustained-session run](https://github.com/Russianranger/coh-android/actions/runs/36295176484)
then passed all twelve phases using a separately packaged `-resumeonly` diagnostic
TestClient. A missing-name request exited without creating or changing a character.
The original character resumed with creation disabled and remained connected on
Atlas Park for 66.953 seconds, with matching received player identity and current
map heartbeats. Influence 12345 survived restart/resume, then a normal command
changed it to 23456 and a second protocol logout committed the expected state.
The stock reference package is unchanged. See the
[accepted evidence](docs/postgresql-evidence/accepted-character-session-36295176484.json)
and [sustained-session scope](docs/SUSTAINED_SESSION_VALIDATION.md).

The [Atlas transfer job](https://github.com/Russianranger/coh-android/actions/runs/36297542986/job/108560197056)
has now passed all fifteen phases at `5f2c561058a186de59d3f27301eea210bd4bb66d`.
After 64.953 seconds connected, the same character moved from map 1 to its
prestarted clone 101 and back. Fresh player updates, actual peer ports and
independent MapId/SmapId status proved both destinations. Live influence stayed
12345, and each arrival's committed selected SQL state remained unchanged with
LoginCount 2. These state checks do not acknowledge new identical transfer writes.
A final change to 23456 and protocol logout proved the fresh final save before
forced cleanup. See the [accepted evidence](docs/postgresql-evidence/accepted-character-transfer-36297542986.json)
and [transfer scope](docs/MAP_TRANSFER_VALIDATION.md). All five workflow jobs
passed, including the separate sustained-session regression.

The original **0.1.0 M2 diagnostic APK passed its hosted gate**. All four jobs in
[hosted run 36336644450](https://github.com/Russianranger/coh-android/actions/runs/36336644450)
passed at source `0b61d7455f40f05709f912338cd5de8b1d72d750`. Its exact guest
assets passed all eleven stages on Linux ARM64: native PostgreSQL, Wine/FEX Win32
DLL loading, all 65 ODBC connections, SQL/value/metadata checks, durable database
restart and owned-process cleanup. The APK is 13,309,477 bytes, SHA-256
`80e53b03d95ec851623b8b743b067e87642e392a387d24679adcd81d119d38ac`.
See the [accepted hosted evidence](docs/android-evidence/accepted-hosted-36336644450.json)
and [download and Thor steps](docs/ANDROID_DIAGNOSTIC.md).

**COH Server Test 0.2.0 passed physical Thor qualification.**
It uses a separate application ID to preserve the accepted 0.1.5 installation,
adds the real DbServer persistence/schema test with local-only listeners, and
retains immutable reports for Stop/rerun testing. See the
[candidate scope and device steps](docs/ANDROID_SERVER_DEVICE_TEST.md).
Its APK build and all 28 hosted ARM64 device-policy stages passed in
[run 36483331900](https://github.com/Russianranger/coh-android/actions/runs/36483331900).
The [candidate receipt](docs/android-evidence/accepted-device-candidate-hosted-36483331900.json)
binds its exact payloads and reports. The subsequent
[Thor acceptance](docs/android-evidence/accepted-dbserver-thor-20260928.json)
records two full 28-stage passes and a clean Stop between them, with all local
DbServer endpoints and owned cleanup verified. App switching and screen locking
are user-attested; peak memory is unmeasured.
The loopback DbServer package also passed the full hosted Atlas sequence in
[run 36493722153](https://github.com/Russianranger/coh-android/actions/runs/36493722153):
all three jobs and 18 runtime stages, both local DbServer starts, two committed
saves and exact-character resume, with all 122 captures closed and clean cleanup.
The [combined receipt](docs/android-evidence/accepted-game-loopback-hosted-36493722153.json)
preserves independent evidence verification. MapServer/TestClient local binding
qualification subsequently passed in `36510836956`, as recorded above.
Next comes verified asset import and Android Atlas runtime/lifecycle integration.
Keep the existing 0.1.5 APK
and runtime, plus the accepted 0.2.0 server test. See the
[concrete next steps](docs/THOR_DEVICE_ACCEPTANCE.md#next-work). The accepted 0.2.0 app
contains the DbServer test, without Atlas MapServer or graphical client execution.
New-zone assets, missions, automatic
map startup, combat and graphics remain separate unfinished work. The repository
is **not a complete runnable game installation**. Complete asset coverage and
serializer equivalence remain unvalidated. Supplied binary assets stay outside Git.

- [PostgreSQL backend implementation and test instructions](database/postgresql/README.md)
- [Actual DbServer persistence and migration behavior](docs/POSTGRESQL_PERSISTENCE.md)
- [Content imported, download sources and next steps](docs/CONTENT_ACQUISITION.md)
- [Local server and client completeness audit](docs/LOCAL_SERVER_CLIENT_COMPLETENESS.md)
- [Android assessment and implementation proposal](docs/ANDROID_PORT_PROPOSAL.md)
- [Source provenance](docs/SOURCE_PROVENANCE.md) and [validation record](docs/VALIDATION.md)
- [Current server validation and asset-transfer handoff](docs/NEXT_SERVER_VALIDATION.md)
- [Handoff and next implementation steps](docs/HANDOFF.md)
- [Active source selection](source-target.json) and [immutable import lock](upstream-lock.json)

The goal remains an Android app running a local server and matching client on
the AYN Thor. The user has no Windows PC: use hosted Windows builds/reference
tests and Thor device testing. The accepted M2 0.1.5 diagnostic contains no game
binaries; the separate accepted 0.2.0 test includes real DbServer binaries.
Neither diagnostic launches the full game.

The i25 investigation is now a [deferred alternative](docs/I25_SOURCE_ACQUISITION.md).
OuroDev access and the `odtoken` secret are not required for this public snapshot.
