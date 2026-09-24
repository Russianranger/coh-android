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

The repository is **not a complete runnable installation**. Binary game assets,
database runtime, generated templates/bins and packaging are still needed. All 72
asset URLs returned HTTP 403 to the hosted availability probe; see the acquisition
guide for alternatives and the exact remaining input.

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
