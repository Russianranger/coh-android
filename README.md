# City of Heroes Android

The selected baseline is the **original OuroDev-derived source import** from
`Thunderspies/CityOfHeroes`, at commit
`0b75ade0c801735e10c5798f641948a45cc50488`. It includes local server services,
the graphical client and development tools. It is Issue 24/Volume 2 lineage
with downstream changes: source code, not a VM image.

**Validation, 2026-09-24:** all 5,995 imported files pass integrity checks. An
[upstream Windows build of this exact commit](https://github.com/Thunderspies/CityOfHeroes/actions/runs/35934567567)
built the server and client and passed nine utility, archive and codec tests.
Gameplay and Android execution have not been validated.

The complete pinned companion data is now imported under `upstream/i24`: **156,297
files, 1,992,097,492 bytes**, verified against its original Git tree. Runtime
staging tools preserve both snapshots and fix the companion executable-name gap.

The matching Windows client/server package now passes its hosted build and
dependency checks. The supplied base assets have been assembled with the pinned
text: **173,011 data files**, including **16,721 binary assets**. See the
[reference runtime and downloads](docs/REFERENCE_RUNTIME.md).

The repository is **not a complete runnable installation**. Database deployment,
runtime cache/template generation and gameplay validation remain open. Supplied
asset archives are staged separately from Git; their offline checks do not
establish that every runtime dependency is present.

- [PostgreSQL backend implementation and test instructions](database/postgresql/README.md)
- [Actual DbServer persistence and migration behavior](docs/POSTGRESQL_PERSISTENCE.md)
- [Content imported, download sources and next steps](docs/CONTENT_ACQUISITION.md)
- [Local server and client completeness audit](docs/LOCAL_SERVER_CLIENT_COMPLETENESS.md)
- [Android assessment and implementation proposal](docs/ANDROID_PORT_PROPOSAL.md)
- [Source provenance](docs/SOURCE_PROVENANCE.md) and [validation record](docs/VALIDATION.md)
- [Handoff and next implementation steps](docs/HANDOFF.md)
- [Active source selection](source-target.json) and [immutable import lock](upstream-lock.json)

The goal remains an Android app running a local server and matching client on
the AYN Thor. The user has no Windows PC: use hosted Windows builds/reference
tests and Thor gameplay testing. There is no Android APK yet.

The i25 investigation is now a [deferred alternative](docs/I25_SOURCE_ACQUISITION.md).
OuroDev access and the `odtoken` secret are not required for this public snapshot.
