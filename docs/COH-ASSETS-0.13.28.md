# COH 0.13.28: external assets and Kings Row

This implementation separates APK **0.13.28 / code 43** from asset pack
**1.0.0**. Publication and physical qualification are recorded in the CURRENT
section of `HANDOFF.md`; this design document does not establish either.

## Installation and compatibility

The asset release has four independently importable parts: **Base, Reference,
Zones and Audio**. Every part carries the same descriptor, whose exact bytes
are also pinned by the APK. Activation requires all four parts and their exact
payload hashes. Completed imports survive a later failed or interrupted part.
Future APKs can retain this descriptor and explicitly reuse Assets 1.0.0; a
changed resource set requires a new asset version. The Reference part includes
the original Atlas reference archive.

Imports stream bounded buffers into private staging files. Completed objects
are addressed by their hashes and reused; setup links immutable archives into
each runtime generation instead of copying those archives again. A verified
reimport can atomically repair a corrupt object path without modifying an
existing runtime's linked inode. Ordinary writable runtime files and character
databases are not shared this way.

The storage scan previously leaked descriptors because Android's
`FileInputStream(FileDescriptor)` did not own the `Os.open` descriptor. Explicit
ownership and closure now cover both successful reads and failures. Repeated
read fixtures reproduce the old leak and pass with the repair. Scan failures
also identify a bounded path and errno when available. This is a confirmed code
defect; the older generic error alone cannot prove it caused every device
storage failure or Android installation interruption.

## Resource coverage

The accepted baseline resources remain unchanged. The Zones supplement adds
**23,876 original files**: 1,689 geometry files, 18,145 textures and 4,042 sounds.
The separate Audio supplement adds **2,177 original sounds** from fifteen
additional original archives. The combined 6,219 sound names have no basename
collisions and fit the native path buffer. All 5,878 accepted animations remain
in the Base part.

Each selected resource is checked against pinned original archive metadata,
bounded byte ranges, stored/decoded sizes, hashes and format structure. Audio
container validation does not prove physical playback. The archives retain
original payloads; no replacement models or invented media fill source gaps.

All 66 named zone map source files are present. Sixty source group graphs resolve
completely. All resolved world geometry files and requested submodels are
available; these six maps retain authored source-resolution gaps:

| Map | Source gap |
| --- | --- |
| 14, Dark Astoria old | `dark_astoria_sun__`, `dark_astoria_sunglow__` |
| 36, Nova Praetoria | `Imperial_skydm_02_predawn` |
| 43, Dark Astoria | `dark_astoria_sun__`, `dark_astoria_sunglow__` |
| 70, Breakout | `moonglow__` |
| 82, Croatoa | `dark_astoria_sun__`, `dark_astoria_sunglow__` |
| 85, Rikti War Zone | Authored `EG_DJ_Architect_H_Universal` and `EG_DJ_Hospital_H_Universal` references |

Kings Row's missing ambient-layer sounds are included. Conservative whole-library
references still include original-source gaps such as `city_presence` and
`mission16c_loop`; availability is not complete dynamic FX/appearance closure.
Nine original geometry placeholders contain no models and cannot count as
collision witnesses. The pack includes the original Flag_01 geometry and both
flag models missing in the supplied .27 log.

The asset release publishes the detailed per-zone audit and source provenance.
Resource availability does not enable or physically qualify travel to every
zone. This milestone enables only the Atlas Park–Kings Row station pair.

## Preparation and transfer

The actual stock monorail menu queues preparation when Kings Row or Atlas Park
is selected. A private request/reply exchange binds the request to the session,
character, station process, sequence and target. After preparation, native code
resumes the ordinary door validation and transfer. Walking away can invalidate
the request. There is no replacement `/mapmove` button for this station path.

One-time client resource installation occurs after Atlas server readiness and
before Game starts. Reports record it separately from destination preparation.
On-demand Kings Row preparation installs only its 52 required original
collision GEO files (3,329,935 bytes), verifies the separately qualified native
beacon graph, and uses an isolated server working tree. Retained definition
caches require the explicit native compatibility receipt. Later preparation
can reuse a validated server data cache; a destination already running in the
same session is a distinct resident case.

Immediate native readiness events avoid waiting for buffered console output.
Arrival still requires the exact destination endpoint, preserved character
identity and three fresh Android destination views. Submitted input events do
not establish that walking, Jump, camera or clicking worked physically.

The accepted .25 Game executable, graphics settings, GPU drivers, Software
fallback, DbServer and persistence acceptance remain. Only the shipping
MapServer and a separate nonshippable beacon generator require new native
compilation. Windows graph generation/readback and host tests do not demonstrate
Thor loading improvement, visual correctness or sustained 30 FPS.

Focused device instructions: `COH-Atlas-Gameplay-0.13.28-testing.txt`.
