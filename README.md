# City of Heroes Android

Source preservation and implementation planning for a self-contained City of
Heroes server and client app, initially targeting the AYN Thor Max (Android 13,
Snapdragon 8 Gen 2, 16 GB RAM).

**Status: source imported and assessed; no Android port or APK exists yet.**

The repository contains all **5,995 files / 173,081,714 bytes** from the pinned
[Thunderspies/CityOfHeroes](https://github.com/Thunderspies/CityOfHeroes/tree/0b75ade0c801735e10c5798f641948a45cc50488)
source tree, a public downstream fork that explicitly documents its OuroDev
ancestry. Direct access to OuroDev failed during this import. This is an
Issue 24/Volume 2 lineage baseline with downstream changes, not a verified copy
of the current canonical OuroDev branch or an Issue 25/Homecoming checkout.

- [Android assessment and implementation proposal](docs/ANDROID_PORT_PROPOSAL.md)
- [Source provenance, contents, and reproduction](docs/SOURCE_PROVENANCE.md)
- [Next implementation work and handoff](docs/HANDOFF.md)
- [Validation performed](docs/VALIDATION.md)
- [Imported source](upstream/ouroboros/README.md)
- [Pinned source and companion data references](upstream-lock.json)

## Proposed direction

Retain the Windows x86 game processes initially, test an app-owned Wine/FEX
runtime, and move persistence to a repaired PostgreSQL backend running on ARM64.
Prove the server with a desktop client, then integrate the matching game client
using its desktop OpenGL/Cg renderer. Native ARM64 conversion is a later workstream.
These are proposed choices, not demonstrated CoH compatibility or performance.

The imported tree includes client/server source, tools, CMake definitions,
configuration examples, and vendored SDK files. It does not include the full
game content, all dependencies fetched by CMake, or a populated database.
The companion data revision is recorded separately and still needs compatibility
testing with this source revision.

## Verify the import

From the repository root, with Python 3:

```sh
python3 tools/verify_source.py
```

This checks every imported file, executable bit, and the absence of extra files
against the committed manifest. It does not test building or running the game.
The snapshot is intentionally unchanged so future port patches can be reviewed
separately. Preserve upstream notices; this import does not relicense the source
or bundled third-party SDKs.
