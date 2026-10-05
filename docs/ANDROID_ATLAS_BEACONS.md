# Native Atlas beacon graph

The October 5 physical 0.13.13 test retained level across reopen, completed
training without a crash, and still displayed the native unbeaconized warning.
This pass produces a genuine graph for the current Atlas world. Zoning remains
a later pass. The warning is not patched or hidden.

## Native proof checkpoint on October 5

Run `37363692462` at generation commit
`57515789dfafab5c4eab3273c63e28beef20264c` passed 106 preflight tests,
fresh native compilation, both exact input inventories and all four owned
roles. It completed real generation and graph readback, reporting 163,544
combat beacons, 163,527 connected beacons, 1,805,050 ground connections,
2,698,868 raised connections, 602 grid blocks and 32 native routes. The
generation server exited zero. This is a native generation milestone, not an
accepted package.

Qualification then rejected its CRC witness before the two fresh input-profile
processes. Authenticated failed-artifact inspection recovered a fresh ordinary
world traversal with 4,569,858 triangles and full CRC `0xb0c21ded`; its native
date matcher accepted. The later marker recomputed CRC after graph reload and
route searches and reported `0xfe75bab6`. The original v9 layout is exactly
S32 version + U32 newest-data time + U32 full-world CRC, twelve bytes. There is
no format exception or relaxed CRC check. The precise reason for the later
runtime-state CRC change remains unproved.

The host proof now calls the fresh matcher unconditionally, rejects false with
an explicit fatal exit, and captures its newly calculated full-world CRC
immediately before graph readback. A distinct preceding
`COH_ATLAS_BEACON_FRESH_WORLD_V1` marker and the final count/route marker must
both equal the unchanged native v9 sidecar CRC. Reader version, populated
connections/blocks and all 32 native routes have explicit fatal guards that do
not depend on assertion macros or optimized-build flags. Both fresh profile
processes remain mandatory and must agree. Changing this host C wrapper
invalidates the earlier compile receipt and requires a fresh native binary;
generation/collision/file/path algorithms and the shipped gameplay binary
remain unchanged.

The failed-run evidence artifact is `11370824751` (16,790,903 bytes),
SHA256 `f5ea6e160a16fcd37971daf3fb8ee1e60f63ab03420da6e360b57d144dce79f1`.
It retains all role logs, host EXE/PDB and build receipts, but the old producer
did not preserve graph/date bytes before Python qualification failed. No
qualified graph or graph pins can be recovered from that artifact.

The producer now saves bounded regular graph/date copies, exact byte pins,
date hex and native markers as explicitly **unqualified** always-evidence
before CRC validation, and also when a native qualification guard fails after
writing them. It records the actual server exit status and never rewrites the
native sidecar. Owned-role progress emits bounded ASCII heartbeat lines every
60 seconds. These diagnostics supply neither profile proof nor publication
approval. The next actual native run and both fresh profiles still gate the
APK.

## Native producer and qualification

The prior `atlas-beacon-input-preflight.json` remains accurate about the input
inventories: they contain no generated `.bcn`. The authored Atlas beacon layer
is placement source rather than a generated combat graph. The legacy
`beaconProcessCombatBeacons` body and generator wrapper are compiled out. This
pass leaves those functions unchanged and uses the active native Beacon master,
server, sentry and worker roles in a separately built host-only MapServer.

`tools/prepare_atlas_beacon_generator_source.py` stages the accepted MapServer
progress base plus a finite containment patch. The host executable rejects
ordinary gameplay and production-mode startup. It cannot install itself, write
an autorun registration, spawn workers or read personal/global map lists. Four
owned processes use one worker, loopback-bound/admitted native ports and exactly
`maps/city_zones/city_01_01/city_01_01.txt`. The server completes one pass. Native
generation, collision connection, graph writer, graph reader and pathfinder
algorithm files retain their original hashes. This binary never enters an APK.

`tools/android/interactive/generate_atlas_beacons.py` reconstructs the same
private native world using the exact 0.13.13 APK, reviewed base asset ZIP and
unmodified Java importer. It applies the retained world supplement with the
shipped missing-only precedence, then exposes only the original visual
supplement's 406 object-library GEOs (16,559,517 bytes) to host collision loading.
No visual textures or player-library GEOs are imported into the host server.
The generator pins the physical GEOs,
object-library group text, Atlas placement/layer text and trick text before and
after generation. UI-only texture additions do not change this graph identity.

After native generation and connection, the server freshly loads the ordinary
Atlas map without the generator's missing-definition cleanup. It compares the
v9 date-sidecar full-world CRC with that fresh world, captures that freshly
verified CRC before graph operations, fully rereads the v8 graph,
requires populated connected combat/grid data and exercises 32 real native
pathfinder routes. The same graph must then pass two additional fresh native
processes: base/world inputs with none of the optional 406 GEOs, and base/world
inputs with all 406. Each must produce the identical full collision CRC, graph
counts and 32 successful native routes. The cold tree is captured before visual
overlay/generation, shares readonly input leaves through hardlinks and keeps
definition, geometry and server caches private. Existing native full-CRC model
witness logging helps identify exact collision differences if these proofs fail.
Failure prevents a qualified package. Six process logs and a
source/input/build receipt accompany the output. A finite 90-minute deadline
and log bounds apply; all owned roles are stopped before publication.

The standalone `android-atlas-beacon-generation.yml` workflow builds under a
short Windows source path to stay below the historical utility diagnostic
thread-name buffer boundary; owned native runtimes are also short `C:/bcn-run/r`
and `C:/bcn-run/c`. It emits `atlas-beacons.zip`, `atlas-beacon-manifest.json`,
`atlas-beacon-generation-report.json` and bounded evidence. A completed graph
may be reused in a later documentation/UI commit only while every generation
implementation pin, native build input and world identity still matches. The
receipt continues to name the actual generation commit.

The first compiled run, `37343908071`, failed before the master's readiness
marker. Its mixed-drive evidence upload also failed, so that run supplies no
accepted graph or native role log. A source audit found that its host child
environment set `COH_WINE_MAP_PROGRESS` to an empty string, which native progress
initialization rejects. This is consistent with the early exit; the lost log
prevents proving which branch actually ended that process. The producer now removes that host-only request,
uses the native FileWrapper stdout API for unbuffered readiness/qualification
logging, retains exit codes and bounded log tails on failure, and gathers the
short-path C-drive build evidence onto the repository drive before upload.
Generation paths are explicitly absolute. These host fixes preserve the
shipped Android observer and require a fresh native generation.

Run `37347246417` passed master and sentry readiness, then the sentry exited
with heap-corruption status `0xc0000374`. Its native role logs are retained.
A source audit found a concrete overflow in the unused legacy relocation
argument builder: its 54-character EString had capacity 64 plus two terminator
bytes, but an unreserved common-argument append extended it to about 85 bytes.
Stubbing the relocation callee did not prevent eager argument evaluation. The
host patch now removes that entire callsite, removes unused server relocation
argument evaluation, and rejects executable self-update. These are audited
defects consistent with the failure; a native stack was not recovered to prove
the precise failing instruction. Failure JSON is now written before rendering
ASCII-safe bounded tails, captures pre-cleanup process exit status, and the
workflow retains host symbols and bounded native internal logs/minidumps.


Run `37357540374` passed all 88 hosted preflight tests and audited the exact
public donor manifest. All 406 optional GEO records already contained only
`bytes` and `sha256`; their physical SHA-256 was
`c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43`.
The earlier metadata-projection hypothesis did not explain the actual failure.
The Windows producer then stopped before starting any native role: its 5,231
common inputs exactly matched the cold mirror, but 405 optional inputs appeared
under imported canonical directory spellings such as `FX/AnimatedCharacterParts`
instead of the donor's lowercase logical directory keys. There were no changed
byte pins. Artifact `11366950301` retains the bounded inventory diagnostic and
compiled host evidence; it contains no accepted graph or successful role proof.

The producer now uses the exact `real_directory` and `resolve_targets` function
bodies from the existing `atlas_world_assets.py` policy. Its source is an
additional pinned generation dependency. Logical inventory keys normalize
directory components only and retain the original immutable leaf spelling.
Physical overlay destinations reuse the imported directory spellings, reject
case-conflicting directory or leaf aliases, and preserve strict leaf names.
Cold mirror cache-root classification also reuses directory case safely while
keeping bin, geometry and server caches private. These changes do not alter
native algorithms or rename the imported assets. A fresh qualified graph and
both native profile proofs remain required.


The next workflow can reuse only the host executable and symbols from that
completed successful compile. It checks the exact earlier run/head and
successful compile step, artifact ID/digest/size, unchanged staged native source
receipt and Win32 executable identity. A different native source forces a fresh
compile. The compile-origin receipt is retained with generation evidence. The
failed run supplies no graph, native readiness, readback, CRC or route proof;
all those proofs must be produced anew.


Run `37361394686` passed all 104 preflight tests, recovered the exact compatible
host compile, and proved the 5,231 common plus 406 optional physical inputs with
zero inventory differences. Native master and sentry readiness then succeeded,
but the server exited with assertion status 3 during network initialization.
Its retained stack identifies `beaconServerInitNetwork`: it could not bind any
port in the 48812–48912 range. This was not heap corruption.

The host containment patch had incorrectly supplied an IP address integer as
`netInit`'s second argument. The authoritative signature is
`netInit(NetLinkList *, int udp_port, int tcp_port)`; master and server therefore
requested the same unintended UDP listener, and each server attempt repeated
that collision before reaching its TCP bind. The patch now retains the original
`netInit(&beacon_server.clients, 0, portToTry)` call. Owned child environments
activate the already accepted `COH_GAME_LOOPBACK_ONLY=1` policy before native
startup. Its existing socket wrapper constrains IPv4 bindings to loopback and
verifies each actual endpoint with `getsockname` and `SO_TYPE`; no networking
algorithm or port range is changed. Source tests bind the API signature and
startup order, and host tests verify inherited environment values are overridden.
Artifact `11367521746` retains the actual role logs and stack. The changed native
source receipt requires a fresh compile, then new graph/readback/CRC/route proofs.

## Private installation and startup

`android/guest/atlas_beacon_package.py` accepts only the frozen qualified graph
and v9 sidecar. Its published SHA-256 constants remain pending until a real
hosted generation succeeds. The installer requires the retained gameplay
MapServer and the already qualified readonly private world. It hashes the
physical collision/group/Atlas/trick inputs on the first successful install.
Current server caching can retain a cold base/world mirror even after client
visual installation; a later cache miss can mirror all supplemental object GEOs.
The installer therefore selects only one of the two complete, independently
proved inventories. A partial optional inventory, extra source leaves, differing
cold/warm collision CRC or incomplete fresh-process proof is refused. It never
adds those GEOs to server startup just to satisfy a package assertion.
Existing different graphs and linked target paths are preserved and refused.
Only the two server-only files and an owned proof receipt are written.
Input and graph destinations use the same existing world resolver to recover
actual directory spelling while requiring exact leaf names. The warm proof
also binds each input's actual relative path, so physical directory-case changes
invalidate reuse rather than silently introducing aliases.

The ordinary Atlas preparation path installs the package for saved and fresh
characters. The unmodified gameplay MapServer discovers and loads the graph
through `beaconReload`; no client gameplay or persistence semantics change.
The ordinary loader reads the v8 graph directly and does not compare the date
sidecar or source-file timestamps. The optional v9 freshness check accepts a
matching full-world CRC; its timestamp-only fallback remains compiled out.
Android import/copy timestamps and cache-directory renames therefore do not
cause graph regeneration. The installer still checks actual source bytes and
fingerprint freshness independently.
The server data cache carries the graph and proof across clean shutdown/reopen.
Warm reuse still performs bounded source-inventory and readonly fingerprint
walks, but skips input
payload hashing and ZIP decoding. Both first preparation and warm reuse expose
`atlas_beacon_graph.preparation_elapsed_seconds`, the input count/bytes hashed
and whether the archive was decoded. The receipt also names the actual
`server_geometry_profile`. A native graph proof does not certify
physical NPC behavior on the AYN Thor.

## Tests and physical check

Source tests prove containment scope, unchanged active algorithms and clean
patch application. Producer tests reject missing/duplicate graph receipts,
empty connections, absent native routes and mismatched sidecar CRC/version.
Installer tests cover first install, warm reuse without archive decoding,
changed geometry, invalidated input fingerprints, preservation of different
existing graphs, linked targets, writable inputs and incomplete native proofs.
Synthetic unit fixtures are explicitly not native generation evidence.
Cold-mirror tests verify cache isolation. Production cache tests reproduce both
the retained cold mirror and later full-visual fallback; profile tests refuse
mixed geometry and inconsistent cold/warm proof metadata. Real filesystem
fixtures cover mixed imported directory case, exact leaf names, ambiguous
source aliases, graph target aliases, a 406-file optional overlay, warm proof
reuse and private mixed-case cache roots.

After publication, install the next APK over the current app and reopen the
saved THORHERO. Record setup/preparation, local Atlas, client, login and world
entry separately. Observe whether the native unbeaconized warning disappears,
then test normal NPC pursuit/pathing around nearby obstacles while retaining
combat, movement and targeting. Save normally, finish/export, reopen and verify
level/XP/powers plus graph reuse. Inspect the exported native log and
`atlas_beacon_graph` receipt before accepting beaconization or a startup claim.


### Runtime date reads and warm reuse

A focused review of the pinned original `beaconFile.c` confirms that normal
map loading does not rewrite the navigation sidecar. The fresh matcher
`beaconDoesTheBeaconFileMatchTheMap` (2621–2631) delegates to
`beaconFileMatchesMapCRC`, which opens the date with `rb` (2544), reads the
version/time/CRC and changes only in-memory `beaconFileTime`.
`beaconFileIsUpToDate` (2592–2619) likewise reads the graph/date; its timestamp
freshness branch is explicitly disabled by `else if (0 && ...)`.
The sole `beaconWriteDateFile` call belongs to `writeBeaconFile` (578),
reached by `beaconWriteCurrentFile` (1543) during native generation.
Ordinary `beaconReload` (1580) reads the graph directly. Device/import mtime
differences therefore do not cause legitimate sidecar rewriting or repeated
extraction in these paths.

The guest installs graph/date/marker as regular files with mode 0400. Its
warm receipt binds path, inode, size, mtime, ctime and mode, excluding atime,
and rewalks the exact allowed geometry inventory. Normal native reads preserve
these fingerprints. Changed graph/date bytes trigger validation and refusal,
rather than silent overwrite. This source review justifies retaining current
cache semantics; physical warm-start timing remains to be measured.
