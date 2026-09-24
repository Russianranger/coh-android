# City of Heroes i25 Android

The selected target is **canonical OuroDev i25/SCoRE source**, not Volume 2 or
a prebuilt VM. The goal is an Android app for a local server and matching client
on the AYN Thor. The user has no Windows PC: use hosted Windows builds and Thor
gameplay testing.

**Status, 2026-09-24: i25 acquisition is blocked by OuroDev's expired TLS certificate.**
The `odtoken` Actions secret is present, but has not been authenticated against
OuroDev. No canonical i25 source has been imported yet.

- Source: [OuroDev SCoRE](https://git.ourodev.com/score/SCoRE)
- Documented branch candidate: `Lexicon-Project(Co)X`; remote verification pending
- [Acquisition findings](docs/I25_SOURCE_ACQUISITION.md)
- [Active i25 proposal](docs/ANDROID_PORT_PROPOSAL.md)
- [Handoff](docs/HANDOFF.md)
- [Current source selection](source-target.json)

## Historical source

`upstream/ouroboros/` contains the earlier **Volume 2-derived public fork** import
(5,995 files). It is historical reference, not the selected i25 source. Its old
lock, manifest and `tools/verify_source.py` still describe that snapshot only.
The complete prior state is also preserved on
[`archive/volume2-assessment-2026-09-23`](https://github.com/Russianranger/coh-android/tree/archive/volume2-assessment-2026-09-23).

The [Volume 2 assessment](docs/VOLUME2_PORT_PROPOSAL.md) is retained for comparison.
Its modern CMake/Win32 findings must not be attributed to canonical i25 without
inspecting that code. No Android APK or gameplay validation exists yet.
