# City of Heroes Android

The selected baseline is the **original OuroDev-derived source import** from
`Thunderspies/CityOfHeroes`, at commit
`0b75ade0c801735e10c5798f641948a45cc50488`. It includes local server services,
the graphical client and development tools. It is Issue 24/Volume 2 lineage
with downstream changes: source code, not a VM image.

**Validation, 2026-09-26:** all 5,995 imported files pass integrity checks. An
[upstream Windows build of this exact commit](https://github.com/Thunderspies/CityOfHeroes/actions/runs/35934567567)
built the server and client and passed nine utility, archive and codec tests.
Gameplay and Android execution have not been validated.

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
This exercises generic containers; character persistence remains a separate gate.

The [asset-backed reference run](https://github.com/Russianranger/coh-android/actions/runs/36176806895)
also passed: ordinary MapServer template generation freshly reproduced all 56
accepted files byte-for-byte in 25.89 seconds. A separate fresh runtime then
kept Atlas Park ready for players, confirmed through DbServer status queries,
for 62.235 seconds. The [recovered reports and archive hashes](docs/reference-runtime-evidence/accepted-gates-36176806895.json)
record those completed gates.

The repository is **not a complete runnable installation**. The next gate is
the new character persistence harness, under hosted validation: creation,
currency change, protocol logout, committed SQL verification and exact-name
resume after service restart. Runtime cache generation beyond the exercised
paths, complete asset coverage, gameplay, Android execution and complete
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
tests and Thor gameplay testing. There is no Android APK yet.

The i25 investigation is now a [deferred alternative](docs/I25_SOURCE_ACQUISITION.md).
OuroDev access and the `odtoken` secret are not required for this public snapshot.
