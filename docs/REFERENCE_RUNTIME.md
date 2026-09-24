# Matching reference runtime

Updated: 2026-09-24. The exact-pin Windows client/server package now builds in
this repository. It is a reference for the Android work, not an Android app or
a gameplay-validated server.

## Build and downloads

[Run 36069123663](https://github.com/Russianranger/coh-android/actions/runs/36069123663)
passed at repository commit `7524c9d894bd49bc83d64c3dbfac0f8d24e57eba`.
Download `reference-win32-runtime` and, for debugging, `reference-win32-symbols`
from that run. Actions artifacts are retained for 30 days; the workflow can
rebuild them. The runtime artifact contains an inner `coh-reference-win32.zip`,
hashes, PE dependency checks and a build receipt. Extract that inner ZIP into
its own directory before staging.

| Item | Value |
| --- | --- |
| Original source pin | `0b75ade0c801735e10c5798f641948a45cc50488` |
| Companion text pin | `d51533ec8e6a9cf726b9214968077a05fdcf19f3` |
| Configuration | OptDebug / Win32 / MSVC hosted Windows |
| PostgreSQL persistence fixture | OFF in this runtime package |
| Runtime artifact SHA-256 | `1f971f3f86579d7dc4da68b471c75039f57e9417b5f33ac8036e5c3e30378c24` |
| Inner runtime ZIP SHA-256 | `23b6b5adf48afc571f5863e3339ae159a734cae19b5234f876fe279aebf52c6b` |

The package includes DbServer, MapServer, CityOfHeroes, TestClient, pig and
Launcher executables, supplied PhysX/Cg DLLs, CrashRpt and app-local x86 MSVC
runtime DLLs. All packaged executable/DLL files passed PE32/x86 and import
closure checks. See [the complete build receipt](reference-runtime-build.json).
The pinned psqlODBC x86 driver is identified there but is not installed or
bundled; PostgreSQL setup remains separate.

## Reproducible assembly

`prepare_runtime.py` verifies both complete immutable imports before copying.
It accepts repeated binary-asset donors, rejects conflicting case-insensitive
paths and incomplete inspections, excludes donor text/generated caches, and
requires exact source/patch/overlay receipts for the runtime binaries. It never
patches the imported snapshots. Use a new output directory:

```sh
python3 tools/prepare_runtime.py \
  --output out/reference-runtime \
  --asset-data out/recovered-base-assets \
  --asset-data /path/to/base-stage1-candidate-assets \
  --binaries out/reference-binaries
```

The asset directories above are outputs of the existing PIGG inspector, not raw
archive folders. The selected base donors are fonts/player/geom/geomBC and
stage1a/stage1b/stage1f. Custom `i26` data and precompiled Parse7 caches are not
part of this assembly. Their original supplied archives remain the inputs for
reproducing extraction.

This assembly completed with **173,011 data files / 2,977,730,517 bytes**:
156,290 text/configuration files and 16,721 selected binary assets, with no
conflicting paths or duplicate donor files. The binary assets comprise 5,878
animations, 1,861 geometry files, 8,936 textures and 46 fonts. Three source DB
configuration files account for the increase over the 173,008-file preflight.
See [the assembly record](runtime-assembly-assessment.json). The stock staged
SQL settings still require the separately generated private PostgreSQL
configuration before DbServer can run; staging does not create credentials,
install a driver or start a database.

## Reference generation

On Windows with a staged runtime, the bounded harness can run:

```sh
python tools/generate_runtime_data.py \
  --runtime out/reference-runtime \
  --output out/reference-generation \
  --phase templates
```

`--phase server-bins`, `--phase client-bins` and `--phase all` are also available.
Under a compatible Linux environment a command prefix can be supplied using
`--runner-json '["wine"]'`; client binning additionally needs working graphics.
These commands are supported paths, not evidence that these runtime phases have
completed here.

The harness checks executable hashes, fresh outputs and process diagnostics.
Templates require all 23 templates, six attribute files and 22 HTML schemas.
Cache phases require completion markers and valid Parse6 outer envelopes;
server binning also requires newly written geometry/map bins. Stale files or a
zero exit without outputs cannot pass. The engine can queue nonfatal errors
before its ordinary early exits, so output checks do not establish complete
definition semantics or gameplay compatibility.

The local execution environment permits Wine version inspection but rejects
the wineserver socket with `Operation not permitted`; it also cannot execute
ELF32 programs. No game-generation process completed locally. Hosted Windows is
the supported execution route for the next checks, without requiring the user
to own a Windows PC.

## Separate data-only schema experiment

The schema workflow builds a separately identified MapServer using the normal
PostgreSQL patch plus `patches/schema-generation`. `-dbtemplatesonly` retains
the normal definition loaders and `containerWriteTemplates`, defers skeletal
track attachment, skips trick texture-animation binding, and omits Mission
Architect animation-selection metadata generation. Those binary-animation
operations do not supply database serializer definitions according to source
review. Ordinary `-templates` behavior is preserved.

The separate mode prints queued definition errors and fails if any are present.
The wrapper requires the exact source/patch receipt, the captured executable
hash, its completion marker and all freshly written schema outputs. Successful
output archives contain templates, HTML schemas and newly written dbidmaps;
incidental parser caches are excluded because this mode deliberately lacks
gameplay assets. Equality with an asset-complete reference `-templates` run
must still be tested. Never substitute this executable for the reference runtime.
