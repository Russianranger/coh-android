# Local server and client completeness audit

Checked 2026-09-24. Baseline: `upstream/ouroboros` at
`0b75ade0c801735e10c5798f641948a45cc50488` from
[Thunderspies/CityOfHeroes](https://github.com/Thunderspies/CityOfHeroes/tree/0b75ade0c801735e10c5798f641948a45cc50488).

**Verdict: the original import contains buildable source for both the local
server and the graphical game client. It does not contain everything needed
for a runnable installation or Android app.** Matching content, a database and
runtime preparation are still required. This is the selected baseline again;
the i25 search is deferred.

## What is present and what is missing

| Component | In the import? | Validation and remaining work |
| --- | --- | --- |
| Local server core | Yes | `DBServer`, `MapServer`, shared libraries and configs. Exact-commit upstream build succeeded; database/content startup is untested here. |
| Graphical player client | Yes | `Game` builds `CityOfHeroes.exe`, including UI, rendering, input, audio and networking. This is the actual game client. Build succeeded; no visual/gameplay validation. |
| Additional server services | Yes, source | Auth, Account, Chat, Auction, Launcher, Beacon, Mission, Queue, Arena, Raid, Stat and Turnstile built upstream. Their schemas/configuration and feature behavior need integration tests. |
| Development tools | Yes | `pig`, `StructParser`, `TestClient` and other utilities. TestClient supports hosted headless smoke tests. |
| Build dependencies | Partial | Bundled SDKs/libraries are preserved; CPM fetches other dependencies. MSVC, Windows SDK and CMake are external. |
| Runtime DLLs | Vendor inputs/build rules | Package matching DLLs from build outputs. Included Win32 PhysX/Cg binaries are not Android ARM64 libraries. |
| Complete text game data | No | Imported `data/` has only three DB configuration files. A separate pinned `Thunderspies/i24` checkout is the candidate text baseline. |
| Binary game content | No | Maps, meshes, textures, fonts and audio must be acquired separately. Complete asset availability/integrity remains unverified. |
| Database engine/driver | No | Stock setup uses SQL Server/LocalDB and 32-bit ODBC Driver 17. DBServer is the game's persistence service, not an embedded SQL engine. |
| Templates and bins | No complete runtime set | Generate database templates with matching MapServer/data. Generate matching client/server bins; production clients require bins. |
| Android runtime/app | No | No APK, native ARM64 game, embedded database integration or verified graphics/translation runtime yet. |

Source evidence: [README](../upstream/ouroboros/README.md),
[build rules](../upstream/ouroboros/cmake/CoXTargets.cmake),
[client target](../upstream/ouroboros/Game/CMakeLists.txt),
[default configuration](../upstream/ouroboros/data/server/db/servers.cfg) and
[companion data README](https://github.com/Thunderspies/i24/blob/d51533ec8e6a9cf726b9214968077a05fdcf19f3/README.md).

## Validation performed

- Reran `python3 tools/verify_source.py`: **PASS**, 5,995 files and 173,081,714
  bytes. No imported files are missing or changed. The original tree is
  `f634e21e230009fa8edc91d15429cd4da69eee8c`; no source exclusions or submodules.
- Inspected [upstream run 35934567567](https://github.com/Thunderspies/CityOfHeroes/actions/runs/35934567567)
  and [job 107428594341](https://github.com/Thunderspies/CityOfHeroes/actions/runs/35934567567/job/107428594341).
  Its `head_sha` exactly matches our import. Configure, build and tests succeeded
  on 2026-09-23 using `windows-2025-vs2026`, Win32, OptDebug.
- Logs explicitly record `DbServer.exe`, `MapServer.exe`, `CityOfHeroes.exe`,
  `TestClient.exe`, `pig.exe` and auxiliary services. This establishes more than
  the presence of source/project files alone.
- **Nine tests passed:** UtilitiesLibIntegration, TokenizerLineEndings,
  DevelopmentMode_loose, DevelopmentMode_packaged, PigUsage, PigRoundTrip,
  PigIncremental, GameOggIntegration and GameJpegIntegration.
- Downloaded the [v2i3 runtime release](https://github.com/Thunderspies/CityOfHeroes/releases/tag/v2i3)
  ZIP (12,326,250 bytes) and matched SHA-256
  `443523af489e3c60f2bed352e3b4fab4dd0103338c3e1649000d2109a24c1b74`
  against its published checksum file. Inspected the archive and `build-info.txt`
  without executing the binaries. It contains an older source revision, as below.

The Windows build/tests above were **upstream results inspected by us**, not a
fresh build in this repository. They do not demonstrate a running shard, database
integration, character creation, graphics or Android compatibility. See
[machine-readable evidence](local-completeness-evidence.json).

## What a local server requires

The documented minimum is a SQL database plus **DBServer + one MapServer + the
matching client**, with `UseFakeAuth 1`. This bypasses a separate authentication
service for a local developer test. The default configuration grants new
characters access level 9: it is a development profile, not normal player
account behavior.

The source README starts map ID 1 and launches `CityOfHeroes.exe` with
`-localmapserver 1`. Characters are forced into that MapServer. This is a useful
initial connection test but does not establish normal zoning, mission instance
startup, bases or the complete server feature set. A broader local shard needs
Launcher/MapServer lifecycle configuration and each selected service's database
and configuration. Test overlapping source/destination maps during transfers;
a single permanently fixed map is not the full local-game goal.

TestClient's `-disconnect` smoke exits after connecting to a map. It does not
verify combat, mission completion, rendering or durable saves by itself.

## Concrete companion setup gaps

The candidate data repository is pinned at
[`d51533ec8e6a9cf726b9214968077a05fdcf19f3`](https://github.com/Thunderspies/i24/tree/d51533ec8e6a9cf726b9214968077a05fdcf19f3).
It points to this source project, but the exact source/data pair has not been
executed here.

1. **Executable naming:** `start-local.ps1`, `client.ps1` and `create-bins.ps1`
   expect `Game.exe`. Our source outputs `CityOfHeroes.exe` without a `Game.exe`
   alias. The downloaded v2i3 ZIP also contains `CityOfHeroes.exe` and no
   `Game.exe`. Adapt the companion scripts or stage an explicit alias in the
   runtime package; preserve the immutable imported source.
2. **Mixed revisions:** `fetch_release.ps1` defaults to `v2i3`. Both the Git tag
   and the downloaded ZIP's build metadata identify
   `3724da475a470926b006dbf73e2e21fd0e7ec856`, not our imported commit. The script
   fetches DB configs from moving `master`. Build our pin and copy its own
   configs to make a reproducible runtime.
3. **Release scope:** the inspected ZIP contains `MapServer.exe`,
   `CityOfHeroes.exe`, `DbServer.exe`, `pig.exe`, 11 DLLs and build metadata.
   It does not include TestClient, Launcher or the auxiliary service executables.
   A complete test/expanded-shard bundle needs a broader output list.
4. **External assets:** `fetch_data.ps1` downloads named archives from
   `https://dists.thunderspy.org/piggs/` and extracts them with `pig`. It has no
   per-archive cryptographic hash manifest. Sample HEAD and ranged GET requests
   for `fonts.pigg` returned HTTP 403 here. The complete set was not acquired.
   This does not establish availability elsewhere; verify access and hash a
   compatible set before describing the runtime as complete.
5. **Generated content:** run `MapServer -templates` before DBServer initializes
   its schema. Rebuild templates/bins after relevant source/data changes.
   Do not mix unrelated i25 or other-server bins with this fork.
6. **Narrow smoke coverage:** the companion map script selects map 29 and
   disables shared memory; its client disables audio. That recipe would not
   validate shared-memory behavior, sound or the README's map-1 scenario.

Primary evidence: companion
[release fetcher](https://github.com/Thunderspies/i24/blob/d51533ec8e6a9cf726b9214968077a05fdcf19f3/tools/fetch_release.ps1),
[asset fetcher](https://github.com/Thunderspies/i24/blob/d51533ec8e6a9cf726b9214968077a05fdcf19f3/tools/fetch_data.ps1),
[local startup](https://github.com/Thunderspies/i24/blob/d51533ec8e6a9cf726b9214968077a05fdcf19f3/tools/start-local.ps1),
[client launcher](https://github.com/Thunderspies/i24/blob/d51533ec8e6a9cf726b9214968077a05fdcf19f3/tools/client.ps1),
[map launcher](https://github.com/Thunderspies/i24/blob/d51533ec8e6a9cf726b9214968077a05fdcf19f3/tools/map.ps1),
[bin generator](https://github.com/Thunderspies/i24/blob/d51533ec8e6a9cf726b9214968077a05fdcf19f3/tools/create-bins.ps1),
[release tag](https://api.github.com/repos/Thunderspies/CityOfHeroes/git/ref/tags/v2i3)
and imported [packager](../upstream/ouroboros/.github/scripts/package-optdebug.ps1).

## Client and Android implications

The actual graphical client source is present; a client does not have to be
recreated from scratch. Its supported build is **32-bit Windows/MSVC**, with
desktop OpenGL/WGL/Cg, Windows input/audio and legacy PhysX dependencies.
Switching to an Android CMake toolchain is insufficient. Keep client, server,
protocol and content aligned; compatibility with an arbitrary Homecoming/i25
client is not assumed.

A self-contained Android server also needs a different database solution from
the stock SQL Server recipe. PostgreSQL code exists but has known source-level
defects and remains unvalidated. It is a porting candidate, not a ready Android
database backend. The [proposal](ANDROID_PORT_PROPOSAL.md) details database
work and Wine/translation/graphics experiments.

## Completion gates without a Windows PC

1. **Hosted reference build:** build our source pin on a Windows GitHub runner.
   Retain executables, TestClient, DLLs, configuration and checksums. The upstream
   run demonstrates this build route exists.
2. **Matched content:** acquire pinned text data and compatible assets, fix
   launcher naming/version selection, generate templates/bins and record hashes.
   Verify a fresh runtime directory is sufficient.
3. **Server integration:** initialize SQL Server/ODBC on the hosted reference
   environment, launch DBServer/MapServer, create/connect with TestClient, then
   explicitly verify save/reload across restarts. Add normal map/mission
   transfers and selected auxiliary-service tests. Hosted CI is a temporary
   test environment, not the eventual game server.
4. **Thor validation:** establish the diagnostic client/runtime and portable
   database path, then test graphics, sound, controllers, combat, missions and
   persistence with both server and client on the device. Measure memory, frame
   times and thermals before choosing the final package/runtime design.

Current boundary: source integrity and exact-commit upstream build are verified;
complete assets, database/gameplay integration and Android execution are not.
